"""
anonymizer_engine.py
Core logic for PII detection, encryption, decryption, masking, hashing.
Uses AES-256-CBC (via Fernet / cryptography library) for reversible encryption.
"""

import os
import base64
import hashlib
import pandas as pd
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# ── PII keyword patterns ────────────────────────────────────────────────────
PII_KEYWORDS = [
    "name", "mobile", "phone", "aadhar", "aadhaar", "email", "dob",
    "birth", "address", "income", "father", "mother", "guardian",
    "pin", "town", "post", "house", "residence", "ration", "udid",
    "registration", "regis", "informate", "intime", "outtime",
    "subcaste", "caste", "religion", "gender", "age", "nationality",
    "occupation", "occ", "refby", "student", "client", "source",
    "disability", "tlm", "reg_no", "reg_date", "supporting",
    "document", "n_name", "pre_", "per_", "_no", "_name",
]

ENCRYPT_PREFIX = "ENC::"
HASH_PREFIX = "HSH::"

# ── Key derivation ──────────────────────────────────────────────────────────
def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 32-byte key from passphrase using PBKDF2-HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def get_fernet(passphrase: str, salt: bytes) -> Fernet:
    key = derive_key(passphrase, salt)
    return Fernet(key)


# ── PII detection ────────────────────────────────────────────────────────────
def detect_pii_columns(df: pd.DataFrame) -> list:
    """Return list of column names that look like PII."""
    found = []
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in PII_KEYWORDS):
            found.append(col)
    return found


# ── Cell-level transforms ────────────────────────────────────────────────────
def encrypt_value(value, fernet: Fernet) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return str(value)
    return ENCRYPT_PREFIX + fernet.encrypt(str(value).encode()).decode()


def decrypt_value(value, fernet: Fernet) -> str:
    s = str(value)
    if not s.startswith(ENCRYPT_PREFIX):
        return value  # not encrypted, leave as-is
    try:
        return fernet.decrypt(s[len(ENCRYPT_PREFIX):].encode()).decode()
    except Exception:
        return "[DECRYPT_FAILED]"


def hash_value(value, passphrase: str) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return str(value)
    raw = passphrase + str(value)
    return HASH_PREFIX + hashlib.sha256(raw.encode()).hexdigest()


def mask_value(value) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return str(value)
    s = str(value)
    if len(s) <= 2:
        return "*" * len(s)
    return s[0] + "*" * (len(s) - 2) + s[-1]


_pseudo_map: dict = {}
_pseudo_counters: dict = {}

def pseudonymize_value(value, col: str) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return str(value)
    key = f"{col}::{value}"
    if key not in _pseudo_map:
        col_lower = col.lower()
        if any(k in col_lower for k in ["name"]):
            prefix = "PERSON"
        elif any(k in col_lower for k in ["mobile", "phone"]):
            prefix = "PHONE"
        elif "email" in col_lower:
            prefix = "EMAIL"
        elif any(k in col_lower for k in ["aadhar", "aadhaar"]):
            prefix = "AADHAR"
        elif any(k in col_lower for k in ["address", "town", "house", "pin"]):
            prefix = "ADDR"
        else:
            prefix = "FIELD"
        _pseudo_counters[prefix] = _pseudo_counters.get(prefix, 0) + 1
        _pseudo_map[key] = f"{prefix}_{str(_pseudo_counters[prefix]).zfill(4)}"
    return _pseudo_map[key]


# ── Main anonymize ────────────────────────────────────────────────────────────
def anonymize_dataframe(
    df: pd.DataFrame,
    columns: list,
    method: str,          # "encrypt" | "hash" | "mask" | "pseudonymize"
    passphrase: str,
    salt: bytes,
) -> pd.DataFrame:
    """Return a new DataFrame with selected columns anonymized."""
    _pseudo_map.clear()
    _pseudo_counters.clear()

    result = df.copy()
    fernet = get_fernet(passphrase, salt) if method == "encrypt" else None

    for col in columns:
        if col not in result.columns:
            continue
        if method == "encrypt":
            result[col] = result[col].apply(lambda v: encrypt_value(v, fernet))
        elif method == "hash":
            result[col] = result[col].apply(lambda v: hash_value(v, passphrase))
        elif method == "mask":
            result[col] = result[col].apply(mask_value)
        elif method == "pseudonymize":
            result[col] = result[col].apply(lambda v: pseudonymize_value(v, col))

    return result


# ── Main decrypt ──────────────────────────────────────────────────────────────
def decrypt_dataframe(
    df: pd.DataFrame,
    passphrase: str,
    salt: bytes,
) -> tuple:
    """
    Decrypt all ENC:: prefixed cells.
    Returns (decrypted_df, error_count).
    """
    fernet = get_fernet(passphrase, salt)
    result = df.copy()
    error_count = 0

    for col in result.columns:
        def _dec(v):
            nonlocal error_count
            s = str(v)
            if s.startswith(ENCRYPT_PREFIX):
                out = decrypt_value(s, fernet)
                if out == "[DECRYPT_FAILED]":
                    error_count += 1
                return out
            return v
        result[col] = result[col].apply(_dec)

    return result, error_count


# ── File I/O ──────────────────────────────────────────────────────────────────
def read_file(path: str) -> pd.DataFrame:
    if path.lower().endswith(".csv"):
        return pd.read_csv(path, dtype=str)
    else:
        return pd.read_excel(path, dtype=str)


def write_file(df: pd.DataFrame, path: str):
    if path.lower().endswith(".csv"):
        df.to_csv(path, index=False)
    else:
        df.to_excel(path, index=False)


def embed_salt(salt: bytes, df: pd.DataFrame) -> pd.DataFrame:
    """Store salt as a hidden metadata column (last column, prefixed)."""
    df = df.copy()
    df["__SALT__"] = base64.b64encode(salt).decode()
    return df


def extract_salt(df: pd.DataFrame) -> tuple:
    """Extract and remove the __SALT__ column. Returns (df, salt)."""
    if "__SALT__" in df.columns:
        salt_b64 = df["__SALT__"].iloc[0]
        salt = base64.b64decode(salt_b64)
        df = df.drop(columns=["__SALT__"])
        return df, salt
    # fallback: fixed salt (for old files)
    return df, b"default_salt_v1_"


def generate_salt() -> bytes:
    return os.urandom(16)
