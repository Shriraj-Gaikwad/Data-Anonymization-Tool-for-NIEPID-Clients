import pandas as pd
import hashlib

# ---------------------------------
# Load Dataset
# ---------------------------------
df = pd.read_excel(r"D:\NIMH\NIMH_ALL_DISABILITIES.xlsx")

# ---------------------------------
# Helper Functions
# ---------------------------------

# Mask Aadhaar / phone numbers safely
def mask_number(num):

    # Handle missing values
    if pd.isna(num):
        return ""

    try:
        # Convert float -> int -> string
        num = str(int(float(num)))
    except:
        # Remove unwanted .0 if present
        num = str(num).replace(".0", "")

    # Mask all except last 4 digits
    if len(num) <= 4:
        return "XXXX"

    return "X" * (len(num) - 4) + num[-4:]


# Optional hash function
def hash_value(value):

    if pd.isna(value):
        return ""

    return hashlib.sha256(
        str(value).encode()
    ).hexdigest()


# ---------------------------------
# Generate Anonymous IDs
# ---------------------------------

df['Anonymous_ID'] = [
    f'CHILD_{str(i).zfill(5)}'
    for i in range(1, len(df) + 1)
]

# ---------------------------------
# Replace Sensitive Columns
# ---------------------------------

# Replace child names
if 'Name' in df.columns:
    df['Name'] = df['Anonymous_ID']

# Replace registration numbers
if 'Reg_No' in df.columns:
    df['Reg_No'] = [
        f'REG_{str(i).zfill(5)}'
        for i in range(1, len(df) + 1)
    ]

# Mask Aadhaar Number
if 'AadharNo' in df.columns:
    df['AadharNo'] = df['AadharNo'].apply(mask_number)

# Mask UDID Number
if 'UDID_NO' in df.columns:
    df['UDID_NO'] = df['UDID_NO'].apply(mask_number)

# ---------------------------------
# Mask Phone Numbers
# ---------------------------------

mobile_cols = [
    'Pre_Mobile_No',
    'Per_Mobile_No',
    'Pre_Phone_Residence',
    'Per_Phone_Residence',
    'Pre_Phone_Work',
    'Per_Phone_Work'
]

for col in mobile_cols:

    if col in df.columns:
        df[col] = df[col].apply(mask_number)

# ---------------------------------
# Remove Address Columns
# ---------------------------------

address_cols = [
    'Pre_HNo',
    'Per_HNo',
    'Pre_EmailID',
    'Per_EmailID',
    'Pre_PIN_No',
    'Per_PIN_No',
    'Pre_Town',
    'Per_Town',
    'Pre_Post_No',
    'Per_Post_No'
]

df.drop(
    columns=address_cols,
    inplace=True,
    errors='ignore'
)

# ---------------------------------
# Remove Parent / Guardian Names
# ---------------------------------

parent_cols = [
    'Father_Name',
    'Mother_Name',
    'Guardian_Name',
    'Name_informate'
]

df.drop(
    columns=parent_cols,
    inplace=True,
    errors='ignore'
)

# ---------------------------------
# Generalize DOB
# ---------------------------------

if 'DOB' in df.columns:

    df['DOB'] = pd.to_datetime(
        df['DOB'],
        errors='coerce'
    )

    # Keep only birth year
    df['DOB_Year'] = df['DOB'].dt.year

    # Remove original DOB
    df.drop(columns=['DOB'], inplace=True)

# ---------------------------------
# Optional: Remove Exact Timestamp
# ---------------------------------

time_cols = [
    'InTime',
    'OutTime'
]

df.drop(
    columns=time_cols,
    inplace=True,
    errors='ignore'
)

# ---------------------------------
# Remove Temporary Column
# ---------------------------------

df.drop(
    columns=['Anonymous_ID'],
    inplace=True,
    errors='ignore'
)

# ---------------------------------
# Save Anonymized Dataset
# ---------------------------------

output_path = r"D:\NIMH\anonymized_dataset_v2.xlsx"

df.to_excel(
    output_path,
    index=False
)

print("PII Anonymization Completed Successfully")
print(f"Saved File: {output_path}")