"""
Join all sheets of NIMH_ALL_DISABILITIES.xlsx on Reg_No.

Strategy:
  1. Normalize Reg_No in every sheet (strip/upper/remove stray chars).
  2. Registered_Students = base table (one row per student registration).
  3. Each Hms_* checklist sheet is long-format (Profile_Name / Sub_Prof_Name /
     IF_YES per row) -> pivot to one row per Reg_No, one column per
     (Profile_Name, Sub_Prof_Name) combo.
  4. Sheets with numeric test results (DST, VSMS) -> take latest test per
     Reg_No instead of pivoting flags.
  5. Left-merge everything onto the base table.
"""
import os
import pandas as pd

# ---- Portable paths: everything relative to this script's folder ---------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(SCRIPT_DIR, "NIMH_ALL_DISABILITIES.xlsx")  # put the xlsx next to this script, or edit this path
CACHE_DIR = os.path.join(SCRIPT_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def norm_regno(s):
    if pd.isna(s):
        return s
    s = str(s).strip().upper()
    return s.replace("'", "").replace(" ", "")


def load(sheet, usecols=None):
    df = pd.read_excel(FILE, sheet_name=sheet, usecols=usecols)
    df["Reg_No"] = df["Reg_No"].apply(norm_regno)
    return df


# ---- 1. Base table -------------------------------------------------------
base = load("Registered_Students")
# collapse duplicate Reg_No rows (keep most recent registration)
base = base.sort_values("Reg_Date").drop_duplicates("Reg_No", keep="last")
print("Base students:", base.shape)

# ---- 2. Checklist-style sheets: pivot Profile/SubProfile flags to wide ---
CHECKLIST_SHEETS = [
    "Hms_FamilyHistory", "Hms_DevelopmentHistory", "Hms_History",
    "Hms_Academics_Assessment", "Hms_Psychological_Assessement",
    "Hms_Cognitive_Assessment", "Hms_Finemotor_skills",
    "Hms_FunctionalEvalution", "HMS_Indian_Test_Of_Intelligence",
    "HMS_M_Selfhelp_Assessment", "Hms_Medical_Assessment",
    "Hms_Motor_Assessment", "Hms_Motorevolution",
    "Hms_OccupationalTherapy_Assessm", "Hms_Opthalmology",
    "Hms_Oro_motor_evolution", "Hms_Physiotherapy_Assessment",
    "Hms_Social_Assessment",
]

wide_frames = []
for sheet in CHECKLIST_SHEETS:
    cache = os.path.join(CACHE_DIR, f"cache_{sheet}.pkl")
    if os.path.exists(cache):
        pivot = pd.read_pickle(cache)
    else:
        df = load(sheet)
        if "Sub_Prof_Name" not in df.columns or "IF_YES" not in df.columns:
            continue
        df["flag_name"] = sheet.replace("Hms_", "").replace("HMS_", "") + "__" + df["Sub_Prof_Name"].astype(str)
        df["IF_YES"] = df["IF_YES"].astype(str)  # normalize mixed float/str values first
        pivot = (
            df.pivot_table(index="Reg_No", columns="flag_name", values="IF_YES",
                            aggfunc=lambda x: x.max())  # "ever flagged yes" per student
        )
        pivot.to_pickle(cache)
    wide_frames.append(pivot)
    print(f"{sheet}: pivoted to {pivot.shape}")

# ---- 3. Test-score sheets: take latest score per student -----------------
def latest_scores(sheet, cols, prefix):
    cache = os.path.join(CACHE_DIR, f"cache_{sheet}_scores.pkl")
    if os.path.exists(cache):
        return pd.read_pickle(cache)
    df = load(sheet)
    d = df.sort_values("Reg_Date").drop_duplicates("Reg_No", keep="last")
    d = d.set_index("Reg_No")[cols]
    d.columns = [prefix + c for c in d.columns]
    d.to_pickle(cache)
    return d

dst_latest = latest_scores("Hms_DST_Test", ["DA", "DQ", "IQ_Category", "Percentages"], "DST_")
vsms_latest = latest_scores("Hms_VSMS_Test", ["SQ", "IQ_Category", "Percentages"], "VSMS_")
print("DST latest:", dst_latest.shape, " VSMS latest:", vsms_latest.shape)

# ---- 4. Merge everything onto the base table ------------------------------
final = base.set_index("Reg_No")
for w in wide_frames + [dst_latest, vsms_latest]:
    final = final.join(w, how="left")

final = final.reset_index()
print("\nFinal joined shape:", final.shape)
out_path = os.path.join(SCRIPT_DIR, "joined_student_features.csv")
final.to_csv(out_path, index=False)
print("Saved -> joined_student_features.csv")