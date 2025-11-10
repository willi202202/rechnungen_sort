#!/usr/bin/env python3
import argparse
import pdfplumber
from pathlib import Path

def pdf_to_text(pdf_path: str, out_path: str | None = None):
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise SystemExit(f"PDF nicht gefunden: {pdf_file}")

    all_text = []

    with pdfplumber.open(pdf_file) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            txt = page.extract_text() or ""
            all_text.append(f"===== SEITE {i} =====\n{txt}\n")

    full_text = "\n".join(all_text)

    if out_path:
        out_file = Path(out_path)
        out_file.write_text(full_text, encoding="utf-8")
        print(f"Text nach {out_file} geschrieben.")
    else:
        # direkt auf stdout ausgeben
        print(full_text)


def main():
    parser = argparse.ArgumentParser(
        description="Gibt den Textinhalt eines PDFs aus (Debug fuer Kontoauszug-Parsing)."
    )
    parser.add_argument("pdf", help="Pfad zum PDF (z.B. kontoauszug-2025-10.pdf)")
    parser.add_argument(
        "--out",
        help="Optionaler Pfad fuer eine .txt-Datei. Wenn nicht gesetzt, wird der Text auf stdout ausgegeben.",
    )
    args = parser.parse_args()

    pdf_to_text(args.pdf, args.out)


if __name__ == "__main__":
    main()
