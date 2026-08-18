#!/usr/bin/env python3
"""
anonymizer_cli.py
Command-line interface for anonymization and decryption.
Use this for batch processing or scripting.

Usage examples:
    # Anonymize (encrypt):
    python anonymizer_cli.py anonymize -i data.xlsx -o output.xlsx -m encrypt -p "mypassword"

    # Anonymize (mask, no passphrase needed):
    python anonymizer_cli.py anonymize -i data.xlsx -o output.xlsx -m mask

    # Anonymize specific columns only:
    python anonymizer_cli.py anonymize -i data.xlsx -o output.xlsx -m encrypt -p "mypassword" -c "Name,Mobile_No,AadharNo"

    # List detected PII columns without anonymizing:
    python anonymizer_cli.py detect -i data.xlsx

    # Decrypt:
    python anonymizer_cli.py decrypt -i output.xlsx -o restored.xlsx -p "mypassword"
"""

import argparse
import sys
import os
from anonymizer_engine import (
    detect_pii_columns, anonymize_dataframe, decrypt_dataframe,
    read_file, write_file, embed_salt, extract_salt, generate_salt,
)


def cmd_detect(args):
    print(f"[>>] Reading: {args.input}")
    df = read_file(args.input)
    pii = detect_pii_columns(df)
    print(f"\nTotal columns  : {len(df.columns)}")
    print(f"Rows           : {len(df):,}")
    print(f"\nAuto-detected PII columns ({len(pii)}):")
    for col in pii:
        print(f"  • {col}")
    non_pii = [c for c in df.columns if c not in pii]
    print(f"\nOther columns ({len(non_pii)}):")
    for col in non_pii:
        print(f"  - {col}")


def cmd_anonymize(args):
    if not os.path.exists(args.input):
        print(f"[ERROR] Input file not found: {args.input}")
        sys.exit(1)

    method     = args.method
    passphrase = args.passphrase or ""

    if method in ("encrypt", "hash") and not passphrase:
        print(f"[ERROR] Passphrase (-p) required for method '{method}'")
        sys.exit(1)

    print(f"[>>] Reading: {args.input}")
    df = read_file(args.input)
    print(f"     {len(df):,} rows · {len(df.columns)} columns")

    if args.columns:
        columns = [c.strip() for c in args.columns.split(",")]
        missing = [c for c in columns if c not in df.columns]
        if missing:
            print(f"[WARN] Columns not found in file: {missing}")
            columns = [c for c in columns if c in df.columns]
    else:
        columns = detect_pii_columns(df)
        print(f"[>>] Auto-detected {len(columns)} PII column(s): {columns}")

    if not columns:
        print("[ERROR] No columns to anonymize.")
        sys.exit(1)

    print(f"[>>] Method: {method}  |  Columns: {len(columns)}")

    salt   = generate_salt()
    result = anonymize_dataframe(df, columns, method, passphrase, salt)
    if method == "encrypt":
        result = embed_salt(salt, result)

    write_file(result, args.output)
    print(f"[OK] Saved: {args.output}")
    if method == "encrypt":
        print(f"     ⚠  Remember your passphrase — required for decryption!")


def cmd_decrypt(args):
    if not os.path.exists(args.input):
        print(f"[ERROR] Input file not found: {args.input}")
        sys.exit(1)
    if not args.passphrase:
        print("[ERROR] Passphrase (-p) required for decryption.")
        sys.exit(1)

    print(f"[>>] Reading: {args.input}")
    df = read_file(args.input)
    df, salt = extract_salt(df)

    enc_cols = [c for c in df.columns
                if df[c].astype(str).str.startswith("ENC::").any()]
    if not enc_cols:
        print("[WARN] No ENC:: encrypted columns found in this file.")
        print("       Only files encrypted with the 'encrypt' method can be decrypted.")
        sys.exit(1)

    print(f"[>>] Encrypted columns ({len(enc_cols)}): {enc_cols}")
    result, errors = decrypt_dataframe(df, args.passphrase, salt)
    write_file(result, args.output)

    if errors:
        print(f"[WARN] {errors} cell(s) failed to decrypt — check your passphrase.")
        print(f"       Those cells contain [DECRYPT_FAILED] in the output.")
    else:
        print(f"[OK] Fully decrypted!  Saved: {args.output}")


def main():
    parser = argparse.ArgumentParser(
        description="Data Anonymizer CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # detect
    p_detect = sub.add_parser("detect", help="List PII columns in a file")
    p_detect.add_argument("-i", "--input", required=True, help="Input file path")

    # anonymize
    p_anon = sub.add_parser("anonymize", help="Anonymize a dataset")
    p_anon.add_argument("-i", "--input",    required=True)
    p_anon.add_argument("-o", "--output",   required=True)
    p_anon.add_argument("-m", "--method",   required=True,
                        choices=["encrypt", "hash", "mask", "pseudonymize"])
    p_anon.add_argument("-p", "--passphrase", default="")
    p_anon.add_argument("-c", "--columns",  default="",
                        help="Comma-separated column names. Defaults to auto-detected PII.")

    # decrypt
    p_dec = sub.add_parser("decrypt", help="Decrypt an encrypted anonymized file")
    p_dec.add_argument("-i", "--input",      required=True)
    p_dec.add_argument("-o", "--output",     required=True)
    p_dec.add_argument("-p", "--passphrase", required=True)

    args = parser.parse_args()

    if args.command == "detect":
        cmd_detect(args)
    elif args.command == "anonymize":
        cmd_anonymize(args)
    elif args.command == "decrypt":
        cmd_decrypt(args)


if __name__ == "__main__":
    main()
