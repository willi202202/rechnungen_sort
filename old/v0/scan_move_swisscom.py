#!/usr/bin/env python3
import re
import csv
import shutil
import pdfplumber
from pathlib import Path

from settings import BASE_DIR, SWISSCOM_DIR, SWISSCOM_CSV

SWISSCOM_KEYWORDS = [
    "Swisscom (Schweiz) AG",
    "Rechnungstotal in CHF inkl. MWST",
    "Rechnungsbetrag inkl. MWST",
]


def extract_text_from_pdf(pdf_path: Path) -> str:
    text = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            text.append(t)
    return "\n".join(text)


def is_swisscom_invoice(text: str) -> bool:
    upper = text.upper()
    return any(k.upper() in upper for k in SWISSCOM_KEYWORDS)


def parse_german_date(date_str: str) -> str | None:
    MONTHS = {
        "JANUAR": 1,
        "FEBRUAR": 2,
        "MAERZ": 3,
        "MÄRZ": 3,
        "APRIL": 4,
        "MAI": 5,
        "JUNI": 6,
        "JULI": 7,
        "AUGUST": 8,
        "SEPTEMBER": 9,
        "OKTOBER": 10,
        "NOVEMBER": 11,
        "DEZEMBER": 12,
    }

    m = re.match(r"\s*(\d{1,2})\.\s+([A-Za-zÄÖÜäöü]+)\s+(\d{4})\s*$", date_str)
    if not m:
        return None

    day = int(m.group(1))
    month_name = m.group(2).upper().replace("Ä", "AE").replace("Ö", "OE").replace("Ü", "UE")
    year = int(m.group(3))

    month = MONTHS.get(month_name)
    if not month:
        return None

    return f"{day:02d}.{month:02d}.{year}"


def find_datum(text: str) -> str | None:
    m = re.search(r"Datum[: ]+(\d{1,2}\.\s+[A-Za-zÄÖÜäöü]+\s+\d{4})", text)
    if not m:
        return None
    return parse_german_date(m.group(1))


def find_amount(text: str) -> str | None:
    m = re.search(r"Rechnungstotal in CHF inkl\. MWST\s+([0-9' ]+\.\d{2})", text)
    if m:
        return m.group(1).strip()

    m = re.search(
        r"Rechnungsbetrag\s+inkl\. MWST\s+CHF\s+([0-9' ]+\.\d{2})",
        text,
        re.S,
    )
    if m:
        return m.group(1).strip()

    m = re.search(r"Währung\s+CHF\s+Betrag\s+([0-9' ]+\.\d{2})", text, re.S)
    if m:
        return m.group(1).strip()

    return None


def normalize_amount_for_number(amount_str: str) -> float | None:
    try:
        s = amount_str.replace("'", "").replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return None

def main():
    SWISSCOM_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = list(BASE_DIR.glob("*.pdf"))

    recognized = 0
    moved_files = []

    csv_exists = SWISSCOM_CSV.exists()
    with SWISSCOM_CSV.open(mode="a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, delimiter=";")
        if not csv_exists:
            writer.writerow(["Rechnungsdatum", "Betrag_roh", "Betrag_num", "Datei"])

        for pdf_path in pdf_files:
            try:
                text = extract_text_from_pdf(pdf_path)
            except Exception as e:
                print(f"[WARNUNG] Fehler beim Lesen von: {pdf_path.name}: {e}")
                continue

            if not is_swisscom_invoice(text):
                continue  # keine Konsole, einfach überspringen

            recognized += 1

            date_str = find_datum(text)
            amount_str = find_amount(text)
            if not amount_str:
                print(f"[WARNUNG] Betrag fehlt in {pdf_path.name}, überspringe.")
                continue

            amount_num = normalize_amount_for_number(amount_str)

            writer.writerow([
                date_str or "",
                amount_str,
                amount_num if amount_num is not None else "",
                pdf_path.name,
            ])

            # Datei verschieben
            target_path = SWISSCOM_DIR / pdf_path.name
            try:
                shutil.move(str(pdf_path), str(target_path))
                moved_files.append(pdf_path.name)
            except Exception as e:
                print(f"[WARNUNG] Fehler beim Verschieben von {pdf_path.name}: {e}")

    # ----------------------------------------------------------
    # Zusammenfassung
    # ----------------------------------------------------------
    
    print()
    print("========== SWISSCOM – Zusammenfassung ==========")
    print(f"Gefundene PDF-Dateien:           {len(pdf_files)}")
    print(f"Gefundene Swisscom-Rechnungen:   {recognized}")
    print(f"Verschobene Swisscom-Rechnungen: {len(moved_files)}")

    if moved_files:
        for f in moved_files:
            print("  -", f)

if __name__ == "__main__":
    main()
