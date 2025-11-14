#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import List

import pdfplumber
import shutil

from settings import BASE_DIR, SWISSCOM_DIR, SWISSCARD_DIR, SZKB_DIR
from providers.swisscom_provider import SwisscomProvider
from providers.swisscard_provider import SwisscardProvider
from providers.szkb_provider import SZKBProvider


def extract_text(pdf_path: Path) -> str:
    """PDF -> reiner Text (alle Seiten)."""
    chunks: List[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def main():
    base: Path = BASE_DIR  # dein Hauptordner mit den PDFs
    inbox: Path = base     # wenn du später einen Unterordner willst, z.B. base / "inbox"

    providers = [
         SZKBProvider(),
        SwisscomProvider(),
        SwisscardProvider(),
        # später: StromProvider(), ...
    ]

    print("========== PDF Sorter ==========")
    print(f"BASE_DIR / INBOX: {inbox}")
    print("Zielordner:")
    print(f"  Swisscom:    {SWISSCOM_DIR}")
    print(f"  Swisscard:   {SWISSCARD_DIR}")
    print(f"  SZKB Konto:  {SZKB_DIR}")
    print("================================\n")

    # nur PDFs direkt im inbox-Ordner (keine Unterordner)
    pdf_files = sorted(p for p in inbox.glob("*.pdf") if p.is_file())

    print(f"Gefundene PDFs im Inbox-Ordner: {len(pdf_files)}\n")

    moved = 0
    unmatched = []

    for pdf_path in pdf_files:
        print(f"📄 {pdf_path.name}")

        try:
            text = extract_text(pdf_path)
        except Exception as e:
            print(f"  [WARNUNG] Fehler beim Lesen: {e}")
            unmatched.append(pdf_path)
            continue

        matched_provider = None

        for provider in providers:
            if provider.matches(text):
                matched_provider = provider
                break

        if matched_provider is None:
            print("  ⚠ Kein Provider erkannt – Datei bleibt im Inbox-Ordner.")
            unmatched.append(pdf_path)
            continue

        target_dir = matched_provider.target_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / pdf_path.name

        try:
            shutil.move(str(pdf_path), str(target_path))
            print(f"  ✔ Erkannt als: {matched_provider.name}, verschoben nach: {target_path}")
            moved += 1
        except Exception as e:
            print(f"  [WARNUNG] Fehler beim Verschieben: {e}")
            unmatched.append(pdf_path)

    print("\n========== Zusammenfassung ==========")
    print(f"Verschobene PDFs:         {moved}")
    print(f"Nicht zugeordnete PDFs:   {len(unmatched)}")
    if unmatched:
        print("Unmatched Dateien:")
        for p in unmatched:
            print(f"  - {p.name}")
    print("=====================================")


if __name__ == "__main__":
    main()
