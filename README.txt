=============================================================
  DATA ANONYMIZER — Quick Start Guide
=============================================================

FILES INCLUDED:
  anonymizer_engine.py     — Core encryption/anonymization logic
  data_anonymizer_app.py   — Desktop GUI application
  anonymizer_cli.py        — Command-line tool (for scripting)
  build_exe.py             — Builds a standalone .exe for clients

-------------------------------------------------------------
OPTION A: Run the GUI directly (needs Python installed)
-------------------------------------------------------------
  pip install cryptography pandas openpyxl

  python data_anonymizer_app.py

-------------------------------------------------------------
OPTION B: Build a standalone .exe for your client
-------------------------------------------------------------
  pip install pyinstaller cryptography pandas openpyxl

  python build_exe.py

  This creates:  dist/DataAnonymizer/DataAnonymizer.exe
  Share the entire 'DataAnonymizer' folder — client just
  double-clicks DataAnonymizer.exe. No Python needed.

-------------------------------------------------------------
OPTION C: Command-line usage
-------------------------------------------------------------
  # Detect PII columns:
  python anonymizer_cli.py detect -i mydata.xlsx

  # Encrypt (reversible):
  python anonymizer_cli.py anonymize -i mydata.xlsx -o encrypted.xlsx -m encrypt -p "YourPassphrase"

  # Mask (no passphrase needed):
  python anonymizer_cli.py anonymize -i mydata.xlsx -o masked.xlsx -m mask

  # Decrypt:
  python anonymizer_cli.py decrypt -i encrypted.xlsx -o restored.xlsx -p "YourPassphrase"

-------------------------------------------------------------
ANONYMIZATION METHODS:
-------------------------------------------------------------
  encrypt       AES-256, reversible with passphrase
  hash          SHA-256 HMAC, one-way, irreversible
  mask          Replaces chars with *, keeps first/last
  pseudonymize  Consistent fake IDs (PERSON_0001 etc.)

-------------------------------------------------------------
SECURITY NOTE:
-------------------------------------------------------------
  All processing is 100% local. No data is sent anywhere.
  Keep your passphrase safe — it cannot be recovered.
=============================================================
