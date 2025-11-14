#!/usr/bin/env python3
from pathlib import Path

from providers.swisscom_provider import SwisscomProvider, extract_text_from_pdf


def test_pdf(path: str):
    pdf_path = Path(path)
    if not pdf_path.exists():
        print("PDF nicht gefunden:", pdf_path)
        return

    provider = SwisscomProvider()

    print("\n===== TEST: SwisscomProvider =====")
    print("PDF:", pdf_path)

    # 1) PDF → Text
    text = extract_text_from_pdf(pdf_path)
    print("\n--- Auszug PDF-Text (erste 500 Zeichen) ---")
    print(text)
    print("-------------------------------------------")

    # 2) Matched?
    if provider.matches(text):
        print("[OK] Provider erkennt das PDF als Swisscom-Rechnung")
    else:
        print("[X] Provider erkennt das PDF NICHT als Swisscom!")
        return

    # 3) Parsing
    result = provider.parse_invoice(text, pdf_path.name)

    print("\n--- PARSE RESULT ---")
    for key, value in result.items():
        print(f"{key}: {value}")

    print("\nFERTIG – Test abgeschlossen.\n")


if __name__ == "__main__":
    # HIER ein Swisscom-PDF eintragen:
    test_pdf(r"D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage\swisscom-schweiz-ag-2025-09-30-13059880-11.pdf")