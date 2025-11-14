#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from settings import SWISSCARD_DIR, SWISSCARD_CSV
from providers.swisscard_provider import SwisscardProvider, extract_text_from_pdf


def main():
    provider = SwisscardProvider()

    pdf_dir: Path = SWISSCARD_DIR
    csv_path: Path = SWISSCARD_CSV

    if not pdf_dir.exists():
        print(f"[HINWEIS] Swisscard-Ordner existiert nicht: {pdf_dir}")
        return

    pdf_files = sorted(p for p in pdf_dir.glob("*.pdf") if p.is_file())

    print("========== Swisscard CSV Builder ==========")
    print(f"PDF-Ordner: {pdf_dir}")
    print(f"CSV-Ziel:   {csv_path}")
    print(f"Gefundene PDFs: {len(pdf_files)}")

    # CSV neu schreiben (überschreiben)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(provider.csv_header)

        written = 0
        skipped_not_matching = 0
        errors = 0

        for pdf_path in pdf_files:
            try:
                text = extract_text_from_pdf(pdf_path)
            except Exception as e:
                print(f"[WARNUNG] Fehler beim Lesen von '{pdf_path.name}': {e}")
                errors += 1
                continue

            if not provider.matches(text):
                skipped_not_matching += 1
                continue

            data = provider.parse_invoice(text, pdf_path.name)

            date_str = data.get("date", "") or ""
            amount = data.get("amount", None)
            filename = data.get("file", pdf_path.name)

            if amount is None:
                amount_str_num = ""
            else:
                amount_str_num = f"{float(amount):.2f}"

            # ["Rechnungsdatum", "Betrag", "Datei"]
            writer.writerow([date_str, amount_str_num, filename])
            written += 1

    print("\n========== Zusammenfassung ==========")
    print(f"Verarbeitete PDFs insgesamt:      {len(pdf_files)}")
    print(f"Erkannte Swisscard-Dokumente:    {written + skipped_not_matching}")
    print(f" -> Davon in CSV geschrieben:    {written}")
    print(f" -> Nicht passend (kein Match):  {skipped_not_matching}")
    print(f"Lesefehler:                      {errors}")
    print(f"CSV neu erzeugt: {csv_path}")


if __name__ == "__main__":
    main()
