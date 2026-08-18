# %% [markdown]
# # NIMH All-Disabilities Dataset — Insight Analysis
# Reproduces every finding from the leadership report using pandas.
# Each `# %%` marks a separate cell — run top to bottom in Jupyter or
# VSCode's "Run Cell" (VSCode/PyCharm/Spyder all recognise this format).

# %%
# --- Imports & config ---
import pandas as pd
import openpyxl
import csv
import os

SRC_XLSX = r"D:\NIMH\NIMH_ALL_DISABILITIES.xlsx"
CSV_DIR = r"D:\NIMH\csv"
os.makedirs(CSV_DIR, exist_ok=True)

SHEETS_NEEDED = [
    "Registered_Students",
    "Hms_FamilyHistory",
    "Hms_DevelopmentHistory",
    "Hms_DST_Test",
    "Hms_VSMS_Test",
]

# %%
# --- Step 0: Stream large sheets to CSV first -----------------------------
# The workbook is ~200MB with 23 sheets. Loading it directly with
# pd.read_excel() (or openpyxl in normal mode) tries to pull the whole
# file into memory and can crash/hang. read_only=True streams row by row
# instead, so we extract just the 5 sheets we need to CSV once, then use
# fast, memory-light pandas from here on.

def extract_sheets_to_csv(sheets):
    wb = openpyxl.load_workbook(SRC_XLSX, read_only=True, data_only=True)
    for sheet_name in sheets:
        out_path = os.path.join(CSV_DIR, f"{sheet_name}.csv")
        if os.path.exists(out_path):
            continue  # already extracted, skip
        ws = wb[sheet_name]
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in ws.iter_rows(values_only=True):
                writer.writerow(row)
        print(f"Extracted {sheet_name} -> {out_path}")

extract_sheets_to_csv(SHEETS_NEEDED)

# %%
# --- Load CSVs into pandas --------------------------------------------
students = pd.read_csv(os.path.join(CSV_DIR, "Registered_Students.csv"), low_memory=False)
fh = pd.read_csv(os.path.join(CSV_DIR, "Hms_FamilyHistory.csv"), low_memory=False)
dh = pd.read_csv(os.path.join(CSV_DIR, "Hms_DevelopmentHistory.csv"), low_memory=False)
dst = pd.read_csv(os.path.join(CSV_DIR, "Hms_DST_Test.csv"), low_memory=False)
vsms = pd.read_csv(os.path.join(CSV_DIR, "Hms_VSMS_Test.csv"), low_memory=False)

print("Sheets loaded:", students.shape, fh.shape, dh.shape, dst.shape, vsms.shape)

# %%
# --- Data quality: drop fully-blank placeholder rows -------------------
print("Raw row count:", len(students))
students = students[students["Name"].notna()].copy()
print("Valid student rows after cleaning:", len(students))
# ~20,437 rows in the raw sheet are blank export artifacts.
# Real dataset = 20,422 students, not 40,859 — flag this to leadership.

# Normalise the join key used across every sheet
for df in (students, fh, dh, dst, vsms):
    df["Reg_No_norm"] = df["Reg_No"].astype(str).str.lower().str.strip()

# %%
# ============================================================
# FINDING 1 — Case mix is dominated by Intellectual Disability
# ============================================================
disability_counts = (
    students["Disabilitie_Name"]
    .value_counts(dropna=True)
    .rename_axis("Disability")
    .reset_index(name="Count")
)
disability_counts["Pct"] = (
    100 * disability_counts["Count"] / disability_counts["Count"].sum()
).round(1)

print("=== Finding 1: Disability distribution ===")
print(disability_counts.head(10))
# -> Intellectual Disability = 18,300 / 20,422 classified cases = 89.6%

# %%
# ==================================================================
# FINDING 2 — Gender gap in registration, reversed gap in severity
# ==================================================================
gender_counts = students["Gender"].value_counts(dropna=True)
print("=== Finding 2a: Gender distribution ===")
print(gender_counts)
# -> Male 14,615 (72%) vs Female 5,658 (28%) -> 2.6 : 1 ratio

# Get ONE DQ/IQ-category value per student from the DST test
# (each test has many repeated rows per student — one per sub-item — so
#  take the distinct (Reg_No, IQ_Category) pairs, then collapse to one row)
dst_clean = dst[dst["IQ_Category"].notna()]
dst_one_per_student = (
    dst_clean.drop_duplicates(subset=["Reg_No_norm", "IQ_Category"])
    .groupby("Reg_No_norm")["IQ_Category"]
    .first()
    .reset_index()
)

merged = students.merge(dst_one_per_student, on="Reg_No_norm", how="inner")
merged = merged[merged["Gender"].isin(["Male", "Female"])]

severe_profound = merged.assign(
    is_severe_profound=merged["IQ_Category"].isin(["Severe", "Profound"])
)
gender_severity = severe_profound.groupby("Gender").agg(
    total=("Reg_No", "count"), severe_profound=("is_severe_profound", "sum")
)
gender_severity["pct_severe_profound"] = (
    100 * gender_severity["severe_profound"] / gender_severity["total"]
).round(1)

print("\n=== Finding 2b: % Severe/Profound by gender ===")
print(gender_severity)
# -> Female 20.4% Severe/Profound vs Male 15.2%

# %%
# ============================================================
# FINDING 3 — Severity mix skews Moderate/Mild, not Profound
# ============================================================
severity_dist = dst_one_per_student["IQ_Category"].value_counts()
severity_pct = (100 * severity_dist / severity_dist.sum()).round(1)
print("=== Finding 3a: Overall DQ/IQ severity distribution ===")
print(pd.DataFrame({"count": severity_dist, "pct": severity_pct}))

# Average age at assessment, by severity category
age_by_severity = (
    students.merge(dst_one_per_student, on="Reg_No_norm", how="inner")
    .assign(Age=lambda d: pd.to_numeric(d["Age"], errors="coerce"))
    .query("1 <= Age <= 60")
    .groupby("IQ_Category")["Age"]
    .mean()
    .round(2)
    .sort_values(ascending=False)
)
print("\n=== Finding 3b: Average age at assessment, by severity ===")
print(age_by_severity)
# -> Severe ~10.7 yrs > Moderate ~9.7 > Profound ~8.0 > Average ~7.6
#    > Mild ~6.9 > Borderline ~6.7

# %%
# ======================================================================
# FINDING 4 — Speech/language milestones are the strongest early signal
# ======================================================================
MILESTONES = [
    "Rolling:(3-5 Months)", "Head Control:(3-5 Months)",
    "Bilateral Holding Of Toys(3-6 Months)", "Babbling(4-8 Months)",
    "Independent Sitting:(6-8 Months)", "Crawling(6-8Months)",
    "Responds to Name(7-12 Months)", "Walking(11-14 Months)",
    "First Words(11-12 Months)", "Two words phrases(18-24 months)",
    "Sentences(2yrs 6 months-3 years)",
]

milestone_rows = dh[dh["Sub_Prof_Name"].isin(MILESTONES)]
delay_summary = (
    milestone_rows.groupby("Sub_Prof_Name")["SubProfile_Info_Name"]
    .value_counts()
    .unstack(fill_value=0)
)
delay_summary["pct_delayed"] = (
    100
    * delay_summary.get("Delayed", 0)
    / (delay_summary.get("Delayed", 0) + delay_summary.get("OnTime", 0))
).round(1)
delay_summary = delay_summary.sort_values("pct_delayed", ascending=False)

print("=== Finding 4a: % of children delayed, by milestone ===")
print(delay_summary[["pct_delayed"]])
# -> Sentences (2.5-3yrs) 84.0% delayed, Two-word phrases 81.5% delayed
#    vs Head Control 38.4%, Rolling 39.9% (motor milestones)

# % of children with AT LEAST ONE delayed milestone, by disability
delay_flag = (
    milestone_rows.assign(is_delayed=lambda d: d["SubProfile_Info_Name"] == "Delayed")
    .groupby("Reg_No_norm")["is_delayed"]
    .max()
    .reset_index()
)
any_delay_by_disability = (
    students.merge(delay_flag, on="Reg_No_norm", how="inner")
    .groupby("Disabilitie_Name")["is_delayed"]
    .agg(["count", "sum"])
)
any_delay_by_disability["pct_any_delay"] = (
    100 * any_delay_by_disability["sum"] / any_delay_by_disability["count"]
).round(1)

print("\n=== Finding 4b: % with at least one delayed milestone, by disability ===")
print(any_delay_by_disability[any_delay_by_disability["count"] > 20])

# %%
# ==========================================================
# FINDING 5 — DQ (DST) and SQ (VSMS) severity scores agree
# ==========================================================
vsms_clean = vsms[vsms["IQ_Category"].notna()]
vsms_one_per_student = (
    vsms_clean.drop_duplicates(subset=["Reg_No_norm", "IQ_Category"])
    .groupby("Reg_No_norm")["IQ_Category"]
    .first()
    .reset_index()
    .rename(columns={"IQ_Category": "SQ_Category"})
)

compare = dst_one_per_student.rename(columns={"IQ_Category": "DQ_Category"}).merge(
    vsms_one_per_student, on="Reg_No_norm", how="inner"
)

# Ordinal rank so we can measure "how far apart" two categories are
RANK = {
    "Profound": 0, "Severe": 1, "Moderate": 2, "Mild": 3,
    "Borderline intelligence": 4, "Average intelligence": 5,
    "Above average": 6,
}
compare["diff"] = (
    compare["DQ_Category"].map(RANK) - compare["SQ_Category"].map(RANK)
).abs()

total = len(compare)
exact_match = (compare["diff"] == 0).sum()
adjacent = (compare["diff"] == 1).sum()
far_apart = (compare["diff"] >= 2).sum()

print("=== Finding 5: DQ vs SQ agreement ===")
print(f"Total compared: {total}")
print(f"Exact match:     {100*exact_match/total:.1f}%")
print(f"Adjacent (±1):   {100*adjacent/total:.1f}%")
print(f"2+ categories apart: {100*far_apart/total:.1f}%")
# -> 66.0% exact match, 32.0% adjacent, 2.0% far apart

# %%
# ==================================================================
# FINDING 6 — Reported hereditary / consanguinity link is low
# ==================================================================
# Consanguinity: flag = 1 if a non-"no" answer was recorded for that student
consang_rows = fh[fh["Sub_Prof_Name"] == "Consanguinity"].copy()
consang_rows["flag"] = (
    consang_rows["SubProfile_Info_Name"].notna()
    & ~consang_rows["SubProfile_Info_Name"].str.strip().str.lower().str.startswith("no", na=False)
)
consang_flag = consang_rows.groupby("Reg_No_norm")["flag"].max().reset_index()

consang_by_disability = (
    students.merge(consang_flag, on="Reg_No_norm", how="inner")
    .groupby("Disabilitie_Name")["flag"]
    .agg(["count", "sum"])
)
consang_by_disability["pct_consanguineous"] = (
    100 * consang_by_disability["sum"] / consang_by_disability["count"]
).round(1)

print("=== Finding 6a: % reporting consanguinity, by disability ===")
print(consang_by_disability[consang_by_disability["count"] > 20])

# Family history of a similar disability/delay
famhist_rows = fh[fh["Sub_Prof_Name"].str.startswith("Any Family history", na=False)].copy()
famhist_rows["flag"] = (
    famhist_rows["SubProfile_Info_Name"].notna()
    & ~famhist_rows["SubProfile_Info_Name"].str.strip().str.lower().str.startswith("no", na=False)
)
famhist_flag = famhist_rows.groupby("Reg_No_norm")["flag"].max().reset_index()

famhist_by_disability = (
    students.merge(famhist_flag, on="Reg_No_norm", how="inner")
    .groupby("Disabilitie_Name")["flag"]
    .agg(["count", "sum"])
)
famhist_by_disability["pct_family_history"] = (
    100 * famhist_by_disability["sum"] / famhist_by_disability["count"]
).round(1)

print("\n=== Finding 6b: % reporting family history of similar condition ===")
print(famhist_by_disability[famhist_by_disability["count"] > 20])
# -> Both ~2-3% across disability types -> most cases have no reported
#    hereditary/consanguinity link in the data

# %%
# ==========================================================================
# FINDING 7 — Who we serve: payment category & geographic concentration
# ==========================================================================
payment_counts = students["RationCard"].value_counts(dropna=True)
payment_pct = (100 * payment_counts / payment_counts.sum()).round(1)
print("=== Finding 7a: Paying vs Non-Paying families ===")
print(pd.DataFrame({"count": payment_counts, "pct": payment_pct}))
# -> Non Paying 55% vs Full Paying 45%

district_counts = students["District_Name"].value_counts(dropna=True).head(10)
district_pct = (100 * district_counts / len(students)).round(1)
print("\n=== Finding 7b: Top districts by registration ===")
print(pd.DataFrame({"count": district_counts, "pct_of_total": district_pct}))

top3_pct = district_pct.iloc[:3].sum()
print(f"\nTop 3 districts = {top3_pct:.1f}% of all registrations")
# -> Hyderabad + Ranga Reddy + Medchal-Malkajgiri = ~48% of registrations
