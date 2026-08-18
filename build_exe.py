#!/usr/bin/env python3
"""
build_exe.py
Run this script to package data_anonymizer_app.py into a standalone .exe (Windows)
or binary (Linux/macOS) that your client can run without installing Python.

Usage:
    python build_exe.py

Output:
    dist/DataAnonymizer/DataAnonymizer.exe   (Windows)
    dist/DataAnonymizer/DataAnonymizer       (Linux/macOS)
"""

import subprocess
import sys
import os

# ── Separator for --add-data (Windows = semicolon, Linux/Mac = colon) ────────
SEP = ";" if sys.platform == "win32" else ":"


def main():
    print("=" * 60)
    print("  Data Anonymizer — Executable Builder")
    print("  Developed by C-DAC Bangalore")
    print("=" * 60)

    # ── Ensure PyInstaller is available ──────────────────────────────────────
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("[!!] PyInstaller not found. Installing…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # ── Check / install required packages ────────────────────────────────────
    required = ["cryptography", "pandas", "openpyxl", "PIL"]
    pip_names = {"PIL": "Pillow"}          # import name → pip package name
    for pkg in required:
        try:
            __import__(pkg)
            print(f"[OK] {pkg}")
        except ImportError:
            pip_pkg = pip_names.get(pkg, pkg)
            print(f"[!!] {pip_pkg} missing — installing…")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_pkg])

    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_script = os.path.join(script_dir, "data_anonymizer_app.py")
    engine     = os.path.join(script_dir, "anonymizer_engine.py")

    if not os.path.exists(app_script):
        print(f"\n[ERROR] data_anonymizer_app.py not found at: {app_script}")
        sys.exit(1)
    if not os.path.exists(engine):
        print(f"\n[ERROR] anonymizer_engine.py not found at: {engine}")
        sys.exit(1)

    # ── Locate C-DAC logo ─────────────────────────────────────────────────────
    logo_file = None
    for name in ["cdac_logo.png", "cdac_logo.jpg", "images__1_.jpg"]:
        candidate = os.path.join(script_dir, name)
        if os.path.exists(candidate):
            logo_file = candidate
            print(f"[OK] Logo found: {name}")
            break

    if not logo_file:
        print("[WARN] No C-DAC logo file found in this folder.")
        print("       Place cdac_logo.jpg next to build_exe.py and rebuild")
        print("       to have the logo appear in the app header.")
    else:
        print(f"[OK] Logo will be bundled: {os.path.basename(logo_file)}")

    # ── Build PyInstaller command ─────────────────────────────────────────────
    print("\n[>>] Building executable… (this may take 1-3 minutes)\n")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",          # folder bundle — faster startup than --onefile
        "--windowed",        # no console window on Windows
        "--name", "DataAnonymizer",

        # ── Bundle source files ───────────────────────────────────────────
        "--add-data", f"{engine}{SEP}.",

        # ── Bundle logo if found ──────────────────────────────────────────
        *( ["--add-data", f"{logo_file}{SEP}."] if logo_file else [] ),

        # ── Hidden imports — cryptography ─────────────────────────────────
        "--collect-all", "cryptography",
        "--hidden-import", "cryptography",
        "--hidden-import", "cryptography.hazmat.primitives.kdf.pbkdf2",
        "--hidden-import", "cryptography.hazmat.primitives.hashes",
        "--hidden-import", "cryptography.fernet",

        # ── Hidden imports — data / image ─────────────────────────────────
        "--hidden-import", "openpyxl",
        "--hidden-import", "pandas",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageTk",

        # ── Hidden imports — tkinter ──────────────────────────────────────
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "tkinter.filedialog",
        "--hidden-import", "tkinter.messagebox",

        "--clean",
        app_script,
    ]

    result = subprocess.run(cmd, cwd=script_dir)

    if result.returncode == 0:
        dist_path = os.path.join(script_dir, "dist", "DataAnonymizer")
        print("\n" + "=" * 60)
        print("  BUILD SUCCESSFUL!")
        print("=" * 60)
        print(f"\n  Executable folder: {dist_path}")
        print("\n  Share the entire 'DataAnonymizer' folder with your client.")
        print("  They should run:  DataAnonymizer.exe  (Windows)")
        print("                or  ./DataAnonymizer    (Linux/macOS)")
        print("\n  NOTE: Run the .exe from inside the dist/DataAnonymizer/")
        print("        folder — NOT from the build/ folder.")
        print("\n  No Python installation needed on the client machine.")
    else:
        print("\n[ERROR] Build failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()