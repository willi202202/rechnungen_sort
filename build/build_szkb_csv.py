#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

from settings import SZKB_DIR, SZKB_CSV
from providers.szkb_provider import SZKBProvider, extract_text_from_pdf


def main():
    provider = SZKBProvider()

    pdf_dir: Path = SZKB_DIR
    csv_path: Path = SZKB_CSV

    if not pdf_dir.exists():
        print(f"[HINWEIS] SZKB-Ordner existiert nicht: {pdf_dir}")
        return

    pdf_files = sorted(p for p in pdf_dir.glob("*.pdf") if p.is_file())

    print("========== SZKB CSV Builder ==========")
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

            from_date = data.get("from_date", "") or ""
            to_date = data.get("to_date", "") or ""
            saldo_num = data.get("saldo", None)
            filename = data.get("file", pdf_path.name)

            if saldo_num is None:
                saldo_str_num = ""
            else:
                saldo_str_num = f"{float(saldo_num):.2f}"

            # ["Von_Datum", "Bis_Datum", "Schlusssaldo_num", "Datei"]
            writer.writerow([from_date, to_date, saldo_str_num, filename])
            written += 1

    print("\n========== Zusammenfassung ==========")
    print(f"Verarbeitete PDFs insgesamt:      {len(pdf_files)}")
    print(f"Erkannte SZKB-Dokumente:         {written + skipped_not_matching}")
    print(f" -> Davon in CSV geschrieben:    {written}")
    print(f" -> Nicht passend (kein Match):  {skipped_not_matching}")
    print(f"Lesefehler:                      {errors}")
    print(f"CSV neu erzeugt: {csv_path}")


if __name__ == "__main__":
    main()