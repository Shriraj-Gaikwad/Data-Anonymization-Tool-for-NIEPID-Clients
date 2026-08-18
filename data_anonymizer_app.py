
"""
data_anonymizer_app.py
Desktop GUI application for data anonymization and decryption.
Run directly with Python or package with PyInstaller.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from PIL import Image, ImageTk

# Ensure engine is importable whether run as script or frozen exe
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
    sys.path.insert(0, BASE_DIR)

from anonymizer_engine import (
    detect_pii_columns, anonymize_dataframe, decrypt_dataframe,
    read_file, write_file, embed_salt, extract_salt, generate_salt,
)

# ── Color palette ─────────────────────────────────────────────────────────────
BG         = "#F5F7FA"
CARD_BG    = "#FFFFFF"
ACCENT     = "#1A73E8"
ACCENT_DK  = "#1558B0"
TEXT       = "#1A1A2E"
TEXT_MUTED = "#6B7280"
BORDER     = "#E2E8F0"
SUCCESS_BG = "#ECFDF5"
SUCCESS_FG = "#065F46"
ERROR_BG   = "#FEF2F2"
ERROR_FG   = "#991B1B"
WARN_BG    = "#FFFBEB"
WARN_FG    = "#92400E"
TAG_BG     = "#DBEAFE"
TAG_FG     = "#1E40AF"
BTN_FG     = "#FFFFFF"

FONT_TITLE  = ("Segoe UI", 20, "bold")
FONT_HEAD   = ("Segoe UI", 13, "bold")
FONT_BODY   = ("Segoe UI", 11)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 9)
FONT_BTN    = ("Segoe UI", 11, "bold")


class DataAnonymizerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Data Anonymizer  ·  C-DAC Bangalore  ·  Secure PII Protection Tool")
        self.geometry("860x720")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(700, 580)

        self._anon_df    = None
        self._anon_path  = None
        self._dec_df     = None
        self._dec_path   = None
        self._col_vars   = {}     # {col_name: BooleanVar}
        self._pii_cols   = []
        self._method_var = tk.StringVar(value="encrypt")

        self._build_header()
        self._build_footer()
        self._build_notebook()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_header(self):
        HDR_BG     = "#FFFFFF"
        HDR_NAVY   = "#0A6B8A"
        HDR_BORDER = "#0A6B8A"

        tk.Frame(self, bg=HDR_BORDER, height=4).pack(fill="x")

        hdr = tk.Frame(self, bg=HDR_BG, pady=6)
        hdr.pack(fill="x")

        logo_frame = tk.Frame(hdr, bg=HDR_BG, padx=16)
        logo_frame.pack(side="left")

        logo_path = self._find_logo()
        if logo_path:
            try:
                img = Image.open(logo_path).convert("RGBA")
                w, h = img.size
                new_h = 65
                new_w = int(w * new_h / h)
                img = img.resize((new_w, new_h), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(logo_frame, image=self._logo_img, bg=HDR_BG).pack()
            except Exception:
                self._logo_fallback(logo_frame, HDR_NAVY, HDR_BG)
        else:
            self._logo_fallback(logo_frame, HDR_NAVY, HDR_BG)

        tk.Frame(hdr, bg="#E2E8F0", width=1).pack(side="left", fill="y", padx=10, pady=8)

        center_frame = tk.Frame(hdr, bg=HDR_BG)
        center_frame.pack(side="left", expand=True, fill="x", padx=8, pady=4)

        tk.Label(center_frame,
                 text="🔒  Data Anonymizer",
                 font=("Segoe UI", 18, "bold"),
                 bg=HDR_BG, fg=HDR_NAVY).pack(anchor="w")

        tk.Label(center_frame,
                 text="Encrypt  ·  Pseudonymize  ·  Decrypt  ·  Secure PII Protection",
                 font=("Segoe UI", 9),
                 bg=HDR_BG, fg="#6B7280").pack(anchor="w")

        right_frame = tk.Frame(hdr, bg=HDR_BG, padx=16)
        right_frame.pack(side="right")

        tk.Label(right_frame,
                 text="Developed by",
                 font=("Segoe UI", 8),
                 bg=HDR_BG, fg="#9CA3AF").pack(anchor="e")

        tk.Label(right_frame,
                 text="C-DAC Bangalore",
                 font=("Segoe UI", 12, "bold"),
                 bg=HDR_BG, fg=HDR_NAVY).pack(anchor="e")

        tk.Frame(self, bg=HDR_BORDER, height=4).pack(fill="x")

    def _find_logo(self):
        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "cdac_logo.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "cdac_logo.jpg"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "images__1_.jpg"),
            os.path.join(getattr(sys, "_MEIPASS", ""), "cdac_logo.png"),
            os.path.join(getattr(sys, "_MEIPASS", ""), "cdac_logo.jpg"),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    def _logo_fallback(self, parent, color, bg):
        tk.Label(parent, text="C-DAC", font=("Segoe UI", 20, "bold"),
                 bg=bg, fg=color).pack()

    def _build_notebook(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",           background=BG, borderwidth=0)
        style.configure("TNotebook.Tab",       font=FONT_BODY, padding=[18, 8],
                        background=BORDER, foreground=TEXT_MUTED)
        style.map("TNotebook.Tab",
                  background=[("selected", CARD_BG)],
                  foreground=[("selected", ACCENT)])
        style.configure("Treeview",            font=FONT_SMALL, rowheight=22)
        style.configure("Treeview.Heading",    font=("Segoe UI", 9, "bold"))
        style.configure("TProgressbar",        troughcolor=BORDER, background=ACCENT)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=8)

        self._tab_anon = tk.Frame(nb, bg=BG)
        self._tab_dec  = tk.Frame(nb, bg=BG)
        self._tab_help = tk.Frame(nb, bg=BG)
        nb.add(self._tab_anon, text="  🛡  Anonymize  ")
        nb.add(self._tab_dec,  text="  🔓  Decrypt  ")
        nb.add(self._tab_help, text="  ℹ  Help  ")

        self._build_anonymize_tab()
        self._build_decrypt_tab()
        self._build_help_tab()

    def _build_footer(self):
        tk.Frame(self, bg="#0A6B8A", height=2).pack(side="bottom", fill="x")
        footer = tk.Frame(self, bg="#F0F7FA")
        footer.pack(side="bottom", fill="x")
        tk.Label(footer,
                 text="All processing happens locally on your machine. No data is sent anywhere.",
                 font=FONT_SMALL, bg="#F0F7FA", fg=TEXT_MUTED).pack(side="left", padx=14, pady=6)
        tk.Label(footer,
                 text="Copyright \u00a9 CDAC Bengaluru 2025",
                 font=("Segoe UI", 9, "bold"), bg="#F0F7FA", fg="#0A6B8A").pack(side="right", padx=14, pady=6)

    # ── Anonymize tab ─────────────────────────────────────────────────────────
    def _build_anonymize_tab(self):
        parent = self._tab_anon
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self._anon_scroll_frame = tk.Frame(canvas, bg=BG)
        self._anon_scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._anon_scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        p = self._anon_scroll_frame

        # Step 1 — Upload
        self._card(p, "Step 1 — Upload your dataset (.xlsx or .csv)", row=0)
        s1 = self._last_card_body
        self._upload_btn = self._big_button(s1, "📂  Browse File…", self._browse_anon_file)
        self._upload_btn.pack(pady=6)
        self._anon_file_lbl = tk.Label(s1, text="No file selected", font=FONT_SMALL,
                                        bg=CARD_BG, fg=TEXT_MUTED)
        self._anon_file_lbl.pack()
        self._anon_rows_lbl = tk.Label(s1, text="", font=FONT_SMALL, bg=CARD_BG, fg=TEXT_MUTED)
        self._anon_rows_lbl.pack()

        # Step 2 — Columns
        self._card(p, "Step 2 — Select columns to anonymize  (auto-detected PII highlighted)", row=1)
        s2 = self._last_card_body
        self._col_frame_outer = tk.Frame(s2, bg=CARD_BG)
        self._col_frame_outer.pack(fill="x")
        btn_row = tk.Frame(s2, bg=CARD_BG)
        btn_row.pack(fill="x", pady=(6, 0))
        tk.Button(btn_row, text="Select All", font=FONT_SMALL, bg=BORDER, fg=TEXT,
                  bd=0, padx=8, pady=3, cursor="hand2",
                  command=self._select_all_cols).pack(side="left", padx=4)
        tk.Button(btn_row, text="Deselect All", font=FONT_SMALL, bg=BORDER, fg=TEXT,
                  bd=0, padx=8, pady=3, cursor="hand2",
                  command=self._deselect_all_cols).pack(side="left", padx=4)
        tk.Button(btn_row, text="PII Only", font=FONT_SMALL, bg=TAG_BG, fg=TAG_FG,
                  bd=0, padx=8, pady=3, cursor="hand2",
                  command=self._select_pii_only).pack(side="left", padx=4)

        # Step 3 — Method
        self._card(p, "Step 3 — Choose anonymization method", row=2)
        s3 = self._last_card_body
        methods = [
            ("encrypt",      "🔐  Encrypt (reversible)",    "AES-256 encryption. Can be fully decrypted later with your passphrase."),
            ("hash",         "#  One-way Hash",             "SHA-256 hash (salted). Cannot be reversed. Identical values hash identically."),
            ("mask",         "***  Mask",                   "Replaces characters with *, keeping first and last visible."),
            ("pseudonymize", "👤  Pseudonymize",            "Replaces values with consistent fake IDs (PERSON_0001, PHONE_0002 …)."),
        ]
        for val, label, desc in methods:
            row_f = tk.Frame(s3, bg=CARD_BG)
            row_f.pack(fill="x", pady=2)
            rb = tk.Radiobutton(row_f, text=label, variable=self._method_var, value=val,
                                font=FONT_BODY, bg=CARD_BG, fg=TEXT, activebackground=CARD_BG,
                                selectcolor=CARD_BG, cursor="hand2")
            rb.pack(side="left")
            tk.Label(row_f, text="  —  " + desc, font=FONT_SMALL, bg=CARD_BG, fg=TEXT_MUTED).pack(side="left")

        # Step 4 — Passphrase
        self._card(p, "Step 4 — Set a passphrase (required for Encrypt; used as salt for Hash)", row=3)
        s4 = self._last_card_body
        pf = tk.Frame(s4, bg=CARD_BG)
        pf.pack(fill="x")
        tk.Label(pf, text="Passphrase:", font=FONT_BODY, bg=CARD_BG, fg=TEXT).pack(side="left")
        self._anon_pass_var = tk.StringVar()
        self._anon_pass_entry = tk.Entry(pf, textvariable=self._anon_pass_var, show="●",
                                          font=FONT_BODY, width=32, bg="#F8FAFC",
                                          relief="solid", bd=1)
        self._anon_pass_entry.pack(side="left", padx=8)
        self._show_pass_var = tk.BooleanVar()
        tk.Checkbutton(pf, text="Show", variable=self._show_pass_var, bg=CARD_BG,
                       font=FONT_SMALL, command=self._toggle_pass_vis).pack(side="left")
        tk.Label(s4, text="⚠  Keep your passphrase safe — it's needed to decrypt the file later.",
                 font=FONT_SMALL, bg=WARN_BG, fg=WARN_FG,
                 padx=8, pady=4, relief="flat").pack(fill="x", pady=(6, 0))

        # Step 5 — Run
        self._card(p, "Step 5 — Run anonymization", row=4)
        s5 = self._last_card_body
        self._anon_run_btn = self._big_button(s5, "🛡  Anonymize & Save File", self._run_anonymize,
                                               bg=ACCENT, fg=BTN_FG, hover=ACCENT_DK)
        self._anon_run_btn.pack(pady=6)
        self._anon_progress = ttk.Progressbar(s5, length=400, mode="indeterminate")
        self._anon_status = tk.Label(s5, text="", font=FONT_BODY, bg=CARD_BG,
                                      wraplength=700, justify="left")
        self._anon_status.pack(pady=4)

        # Preview
        self._card(p, "Preview (first 5 rows after anonymization)", row=5)
        s6 = self._last_card_body
        self._preview_tree_frame = tk.Frame(s6, bg=CARD_BG)
        self._preview_tree_frame.pack(fill="both", expand=True)

    # ── Decrypt tab ───────────────────────────────────────────────────────────
    def _build_decrypt_tab(self):
        parent = self._tab_dec
        p = tk.Frame(parent, bg=BG)
        p.pack(fill="both", expand=True, padx=10, pady=10)

        self._card(p, "Step 1 — Upload the anonymized file (.xlsx or .csv)", row=0)
        s1 = self._last_card_body
        self._big_button(s1, "📂  Browse Anonymized File…", self._browse_dec_file).pack(pady=6)
        self._dec_file_lbl = tk.Label(s1, text="No file selected", font=FONT_SMALL,
                                       bg=CARD_BG, fg=TEXT_MUTED)
        self._dec_file_lbl.pack()
        self._dec_enc_cols_lbl = tk.Label(s1, text="", font=FONT_SMALL, bg=CARD_BG, fg=TAG_FG)
        self._dec_enc_cols_lbl.pack(pady=(4, 0))

        self._card(p, "Step 2 — Enter passphrase used during encryption", row=1)
        s2 = self._last_card_body
        pf = tk.Frame(s2, bg=CARD_BG)
        pf.pack(fill="x")
        tk.Label(pf, text="Passphrase:", font=FONT_BODY, bg=CARD_BG, fg=TEXT).pack(side="left")
        self._dec_pass_var = tk.StringVar()
        self._dec_pass_entry = tk.Entry(pf, textvariable=self._dec_pass_var, show="●",
                                         font=FONT_BODY, width=32, bg="#F8FAFC",
                                         relief="solid", bd=1)
        self._dec_pass_entry.pack(side="left", padx=8)
        self._show_dec_pass_var = tk.BooleanVar()
        tk.Checkbutton(pf, text="Show", variable=self._show_dec_pass_var, bg=CARD_BG,
                       font=FONT_SMALL,
                       command=lambda: self._dec_pass_entry.config(
                           show="" if self._show_dec_pass_var.get() else "●"
                       )).pack(side="left")

        self._card(p, "Step 3 — Decrypt & save", row=2)
        s3 = self._last_card_body
        self._dec_run_btn = self._big_button(s3, "🔓  Decrypt & Save File", self._run_decrypt,
                                              bg="#065F46", fg=BTN_FG, hover="#047857")
        self._dec_run_btn.pack(pady=6)
        self._dec_progress = ttk.Progressbar(s3, length=400, mode="indeterminate")
        self._dec_status = tk.Label(s3, text="", font=FONT_BODY, bg=CARD_BG,
                                     wraplength=700, justify="left")
        self._dec_status.pack(pady=4)

    # ── Help tab ──────────────────────────────────────────────────────────────
    def _build_help_tab(self):
        p = self._tab_help
        text_widget = tk.Text(p, font=FONT_BODY, bg=BG, fg=TEXT, wrap="word",
                              relief="flat", padx=20, pady=20, spacing1=4)
        text_widget.pack(fill="both", expand=True)

        help_content = [
            ("TITLE", "How Data Anonymizer Works\n"),
            ("HEAD", "🔍  Auto-detection of PII columns\n"),
            ("BODY", "When you upload a file, the tool scans all column headers for known PII keywords "
                     "(name, mobile, phone, aadhar, email, DOB, address, income, father, mother, "
                     "guardian, PIN, house, ration, etc.) and highlights them automatically. "
                     "You can toggle any column on or off.\n\n"),
            ("HEAD", "🔐  Encrypt (reversible)\n"),
            ("BODY", "Uses AES-256 encryption via PBKDF2-derived keys. Each cell is encrypted and stored "
                     "with an ENC:: prefix. The salt is embedded in the file. Upload the file in the "
                     "Decrypt tab with the same passphrase to fully restore the original data.\n\n"),
            ("HEAD", "#  One-way Hash\n"),
            ("BODY", "Uses HMAC-SHA256 (salted with your passphrase). Cannot be reversed. "
                     "Identical values always produce identical hashes — useful for linking records "
                     "without exposing the actual data.\n\n"),
            ("HEAD", "***  Mask\n"),
            ("BODY", "Replaces every character with *, keeping only the first and last character visible. "
                     "Quick and simple — no passphrase needed. Cannot be reversed.\n\n"),
            ("HEAD", "👤  Pseudonymize\n"),
            ("BODY", "Replaces real values with consistent fake identifiers (PERSON_0001, PHONE_0002, "
                     "ADDR_0003 …). The same original value always maps to the same fake ID within "
                     "the file. Cannot be reversed.\n\n"),
            ("HEAD", "🔓  Decryption\n"),
            ("BODY", "Only AES-256 encrypted files can be decrypted. Upload the anonymized file in the "
                     "Decrypt tab and enter the exact passphrase used during encryption. The tool "
                     "detects all ENC:: prefixed cells and restores them.\n\n"),
            ("HEAD", "🔒  Security\n"),
            ("BODY", "All processing happens entirely on your local machine. No data is sent to any "
                     "server or cloud service. The passphrase is never stored anywhere — keep it safe.\n"),
        ]

        text_widget.tag_config("TITLE", font=("Segoe UI", 16, "bold"), foreground=ACCENT)
        text_widget.tag_config("HEAD",  font=("Segoe UI", 12, "bold"), foreground=TEXT)
        text_widget.tag_config("BODY",  font=FONT_BODY,                foreground=TEXT_MUTED)

        for tag, content in help_content:
            text_widget.insert("end", content, tag)
        text_widget.config(state="disabled")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _card(self, parent, title, row=0, container=None):
        p = container if container is not None else parent
        frame = tk.Frame(p, bg=CARD_BG, bd=0,
                         highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="x", pady=5, padx=2)
        tk.Label(frame, text=title, font=FONT_HEAD, bg=CARD_BG, fg=TEXT,
                 pady=8, padx=14).pack(anchor="w")
        sep = tk.Frame(frame, bg=BORDER, height=1)
        sep.pack(fill="x")
        body = tk.Frame(frame, bg=CARD_BG, padx=14, pady=10)
        body.pack(fill="x")
        self._last_card_body = body

    def _big_button(self, parent, text, command, bg=BORDER, fg=TEXT, hover=None):
        hover = hover or "#D1D5DB"
        btn = tk.Button(parent, text=text, font=FONT_BTN,
                        bg=bg, fg=fg, relief="flat",
                        padx=18, pady=9, cursor="hand2",
                        activebackground=hover, activeforeground=fg,
                        command=command)
        btn.bind("<Enter>", lambda e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def _set_status(self, label, msg, kind="info"):
        colors = {
            "info":    (BG, TEXT_MUTED),
            "success": (SUCCESS_BG, SUCCESS_FG),
            "error":   (ERROR_BG, ERROR_FG),
            "warn":    (WARN_BG, WARN_FG),
        }
        bg_c, fg_c = colors.get(kind, (BG, TEXT))
        label.config(text=msg, bg=bg_c, fg=fg_c)

    def _toggle_pass_vis(self):
        self._anon_pass_entry.config(show="" if self._show_pass_var.get() else "●")

    # ── Column checkboxes ─────────────────────────────────────────────────────
    def _render_col_checkboxes(self, df):
        for w in self._col_frame_outer.winfo_children():
            w.destroy()
        self._col_vars.clear()
        self._pii_cols = detect_pii_columns(df)

        canvas = tk.Canvas(self._col_frame_outer, bg=CARD_BG,
                           height=180, highlightthickness=0)
        vsb = ttk.Scrollbar(self._col_frame_outer, orient="vertical",
                             command=canvas.yview)
        inner = tk.Frame(canvas, bg=CARD_BG)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        cols = list(df.columns)
        ncols = 3
        for i, col in enumerate(cols):
            is_pii = col in self._pii_cols
            var = tk.BooleanVar(value=is_pii)
            self._col_vars[col] = var

            cell = tk.Frame(inner, bg=TAG_BG if is_pii else CARD_BG,
                            padx=4, pady=2,
                            highlightbackground=BORDER, highlightthickness=1)
            cell.grid(row=i // ncols, column=i % ncols, padx=3, pady=2, sticky="ew")
            inner.columnconfigure(i % ncols, weight=1)

            cb = tk.Checkbutton(cell, text=col[:28], variable=var,
                                font=FONT_SMALL, bg=TAG_BG if is_pii else CARD_BG,
                                fg=TAG_FG if is_pii else TEXT,
                                activebackground=TAG_BG if is_pii else CARD_BG,
                                selectcolor=CARD_BG, wraplength=160, anchor="w")
            cb.pack(side="left")
            if is_pii:
                tk.Label(cell, text="PII", font=("Segoe UI", 7, "bold"),
                         bg="#BFDBFE", fg=TAG_FG, padx=4).pack(side="right")

    def _select_all_cols(self):
        for v in self._col_vars.values():
            v.set(True)

    def _deselect_all_cols(self):
        for v in self._col_vars.values():
            v.set(False)

    def _select_pii_only(self):
        for col, v in self._col_vars.items():
            v.set(col in self._pii_cols)

    # ── Browse / load ─────────────────────────────────────────────────────────
    def _browse_anon_file(self):
        path = filedialog.askopenfilename(
            title="Select dataset file",
            filetypes=[("Excel/CSV files", "*.xlsx *.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            df = read_file(path)
            self._anon_df   = df
            self._anon_path = path
            fname = os.path.basename(path)
            self._anon_file_lbl.config(
                text=f"✓  {fname}", fg=SUCCESS_FG)
            self._anon_rows_lbl.config(
                text=f"{len(df):,} rows  ·  {len(df.columns)} columns", fg=TEXT_MUTED)
            self._render_col_checkboxes(df)
            self._set_status(self._anon_status, "", "info")
        except Exception as e:
            messagebox.showerror("File Error", f"Could not read file:\n{e}")

    def _browse_dec_file(self):
        path = filedialog.askopenfilename(
            title="Select anonymized file",
            filetypes=[("Excel/CSV files", "*.xlsx *.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            df = read_file(path)
            df, salt = extract_salt(df)
            self._dec_df    = df
            self._dec_salt  = salt
            self._dec_path  = path
            fname = os.path.basename(path)
            self._dec_file_lbl.config(text=f"✓  {fname}", fg=SUCCESS_FG)
            enc_cols = [c for c in df.columns
                        if df[c].astype(str).str.startswith("ENC::").any()]
            if enc_cols:
                self._dec_enc_cols_lbl.config(
                    text=f"Encrypted columns found: {', '.join(enc_cols[:8])}"
                         + (" …" if len(enc_cols) > 8 else ""),
                    fg=TAG_FG)
            else:
                self._dec_enc_cols_lbl.config(
                    text="⚠  No ENC:: encrypted columns found. "
                         "Only Encrypt-method files can be decrypted.",
                    fg=WARN_FG)
        except Exception as e:
            messagebox.showerror("File Error", f"Could not read file:\n{e}")

    # ── Run anonymize ─────────────────────────────────────────────────────────
    def _run_anonymize(self):
        if self._anon_df is None:
            self._set_status(self._anon_status, "⚠  Please upload a file first.", "warn")
            return
        selected = [c for c, v in self._col_vars.items() if v.get()]
        if not selected:
            self._set_status(self._anon_status, "⚠  Select at least one column.", "warn")
            return
        method   = self._method_var.get()
        passphrase = self._anon_pass_var.get().strip()
        if method in ("encrypt", "hash") and not passphrase:
            self._set_status(self._anon_status,
                             "⚠  Please enter a passphrase for Encrypt / Hash methods.", "warn")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save anonymized file as",
            defaultextension=".xlsx",
            initialfile="anonymized_data.xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")]
        )
        if not save_path:
            return

        self._anon_run_btn.config(state="disabled")
        self._anon_progress.pack(pady=4)
        self._anon_progress.start(10)
        self._set_status(self._anon_status, "Processing…", "info")

        def worker():
            try:
                salt = generate_salt()
                result = anonymize_dataframe(
                    self._anon_df, selected, method, passphrase, salt
                )
                if method == "encrypt":
                    result = embed_salt(salt, result)
                write_file(result, save_path)
                self.after(0, self._anon_done,
                           f"✓  Saved: {os.path.basename(save_path)}\n"
                           f"  Anonymized {len(selected)} column(s) · {len(result):,} rows · Method: {method}",
                           result, "success")
            except Exception as e:
                self.after(0, self._anon_done, f"✗  Error: {e}", None, "error")

        threading.Thread(target=worker, daemon=True).start()

    def _anon_done(self, msg, result, kind):
        self._anon_progress.stop()
        self._anon_progress.pack_forget()
        self._anon_run_btn.config(state="normal")
        self._set_status(self._anon_status, msg, kind)
        if result is not None:
            self._render_preview(result)

    # ── Run decrypt ───────────────────────────────────────────────────────────
    def _run_decrypt(self):
        if self._dec_df is None:
            self._set_status(self._dec_status, "⚠  Please upload an anonymized file first.", "warn")
            return
        passphrase = self._dec_pass_var.get().strip()
        if not passphrase:
            self._set_status(self._dec_status, "⚠  Please enter the passphrase.", "warn")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save decrypted file as",
            defaultextension=".xlsx",
            initialfile="decrypted_data.xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")]
        )
        if not save_path:
            return

        self._dec_run_btn.config(state="disabled")
        self._dec_progress.pack(pady=4)
        self._dec_progress.start(10)
        self._set_status(self._dec_status, "Decrypting…", "info")

        def worker():
            try:
                salt   = getattr(self, "_dec_salt", b"default_salt_v1_")
                result, errors = decrypt_dataframe(self._dec_df, passphrase, salt)
                write_file(result, save_path)
                if errors:
                    msg  = (f"⚠  Decrypted with {errors} error(s). "
                            f"Some cells may contain [DECRYPT_FAILED] — "
                            f"check your passphrase.")
                    kind = "warn"
                else:
                    msg  = (f"✓  Fully decrypted!  Saved: {os.path.basename(save_path)}\n"
                            f"  {len(result):,} rows restored.")
                    kind = "success"
                self.after(0, self._dec_done, msg, kind)
            except Exception as e:
                self.after(0, self._dec_done, f"✗  Error: {e}", "error")

        threading.Thread(target=worker, daemon=True).start()

    def _dec_done(self, msg, kind):
        self._dec_progress.stop()
        self._dec_progress.pack_forget()
        self._dec_run_btn.config(state="normal")
        self._set_status(self._dec_status, msg, kind)

    # ── Preview table ─────────────────────────────────────────────────────────
    def _render_preview(self, df):
        for w in self._preview_tree_frame.winfo_children():
            w.destroy()

        preview_df = df.head(5)
        show_cols  = list(preview_df.columns[:10])  # max 10 cols in preview

        tree = ttk.Treeview(self._preview_tree_frame,
                            columns=show_cols, show="headings", height=6)
        xsb = ttk.Scrollbar(self._preview_tree_frame,
                             orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=xsb.set)

        for col in show_cols:
            tree.heading(col, text=col)
            tree.column(col, width=120, minwidth=60, anchor="w")

        for _, row in preview_df.iterrows():
            vals = [str(row[c])[:40] for c in show_cols]
            tree.insert("", "end", values=vals)

        tree.pack(fill="both", expand=True)
        xsb.pack(fill="x")
        if len(df.columns) > 10:
            tk.Label(self._preview_tree_frame,
                     text=f"Showing first 10 of {len(df.columns)} columns",
                     font=FONT_SMALL, bg=CARD_BG, fg=TEXT_MUTED).pack(anchor="w", pady=2)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = DataAnonymizerApp()
    app.mainloop()