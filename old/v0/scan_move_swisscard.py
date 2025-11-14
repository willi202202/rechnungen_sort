#!/usr/bin/env python3
import re
import csv
import shutil
import pdfplumber
from pathlib import Path

from settings import BASE_DIR, SWISSCARD_DIR, SWISSCARD_CSV

# Soll die Mindestzahlung statt dem vollen Betrag geloggt werden?
USE_MINDESTZAHLUNG = False

# Erkennungsmerkmale fuer Swisscard-Rechnungen
SWISSCARD_KEYWORDS = [
    "Swisscard AECS",
    "Cashback Cards",
]


# -------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: Path) -> str:
    text = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            text.append(t)
    return "\n".join(text)


def is_swisscard_invoice(text: str) -> bool:
    upper = text.upper()
    return any(k.upper() in upper for k in SWISSCARD_KEYWORDS)


def find_rechnungsdatum(text: str) -> str | None:
    m = re.search(r"Rechnungsdatum\s+(\d{2}\.\d{2}\.\d{4})", text)
    if m:
        return m.group(1)

    m = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
    if m:
        return m.group(1)

    return None


def find_betraege_block(text: str) -> list[str] | None:
    """
    Extrahiert die 5 CHF-Betraege nach 'Mindestzahlung':
    [Saldo alt, Ihre Zahlungen, Neue Transaktionen, Neuer Saldo, Mindestzahlung]
    """
    m = re.search(
        r"Mindestzahlung.*?(CHF\s*[0-9' .]+\d{2}(?:\s+CHF\s*[0-9' .]+\d{2}){4})",
        text,
        re.S,
    )
    if not m:
        return None

    line = m.group(1)
    amounts = re.findall(r"CHF\s*([0-9' .]+\d{2})", line)
    return amounts if len(amounts) == 5 else None


def normalize_amount(amount_str: str) -> float | None:
    try:
        s = amount_str.replace("'", "").replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return None


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

def main():

    SWISSCARD_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = list(f for f in BASE_DIR.glob("*.pdf") if f.is_file())

    recognized = 0
    moved_files = []

    csv_exists = SWISSCARD_CSV.exists()
    with SWISSCARD_CSV.open(mode="a", newline="", encoding="utf-8") as csv_file:

        writer = csv.writer(csv_file, delimiter=";")
        if not csv_exists:
            writer.writerow(["Rechnungsdatum", "Betrag_roh", "Betrag_num", "Art", "Datei"])

        for pdf_path in pdf_files:

            try:
                text = extract_text_from_pdf(pdf_path)
            except Exception as e:
                print(f"[WARNUNG] Fehler beim Lesen von '{pdf_path.name}': {e}")
                continue

            if not is_swisscard_invoice(text):
                continue

            recognized += 1

            rechnungsdatum = find_rechnungsdatum(text)
            betraege = find_betraege_block(text)

            if not betraege:
                print(f"[WARNUNG] Betragsblock nicht gefunden in '{pdf_path.name}', übersprungen.")
                continue

            saldo_alt, zahlungen, trans_total, neuer_saldo, mindest = betraege

            if USE_MINDESTZAHLUNG:
                betrag_str = mindest
                art = "Mindestzahlung"
            else:
                betrag_str = neuer_saldo
                art = "Neuer Saldo"

            betrag_num = normalize_amount(betrag_str)

            writer.writerow([
                rechnungsdatum or "",
                betrag_str,
                betrag_num if betrag_num is not None else "",
                art,
                pdf_path.name,
            ])

            target_path = SWISSCARD_DIR / pdf_path.name
            try:
                shutil.move(str(pdf_path), str(target_path))
                moved_files.append(pdf_path.name)
            except Exception as e:
                print(f"[WARNUNG] Fehler beim Verschieben von '{pdf_path.name}': {e}")

    # -------------------------------------------------------------------
    # Zusammenfassung
    # -------------------------------------------------------------------

    print("\n========== SWISSCARD – Zusammenfassung ==========")
    print(f"Gefundene PDF-Dateien:           {len(pdf_files)}")
    print(f"Gefundene Swisscard-Rechnungen:  {recognized}")
    print(f"Verschobene Swisscard-Rechnungen:{len(moved_files)}")

    if moved_files:
        for f in moved_files:
            print("  -", f)


if __name__ == "__main__":
    main()
