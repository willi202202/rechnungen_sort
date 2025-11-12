#!/usr/bin/env python3
import os
import re
import csv
import shutil
import pdfplumber

# === EINSTELLUNGEN ANPASSEN ===
BASE_DIR = r"D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage"  # z.B. r"C:\Users\Roman\Documents\Rechnungen"
SWISSCOM_SUBFOLDER = "swisscom"
CSV_NAME = "swisscom.csv"  # wenn du unbedingt .cvs willst: "swisscom.cvs"

# Erkennungsmerkmale fuer Swisscom-Rechnungen
SWISSCOM_KEYWORDS = [
    "Swisscom (Schweiz) AG",
    "Rechnungstotal in CHF inkl. MWST",
    "Rechnungsbetrag inkl. MWST",
]


# ---------------- Hilfsfunktionen ----------------

def extract_text_from_pdf(pdf_path: str) -> str:
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            text.append(t)
    return "\n".join(text)


def is_swisscom_invoice(text: str) -> bool:
    upper = text.upper()
    return any(k.upper() in upper for k in SWISSCOM_KEYWORDS)


def parse_german_date(date_str: str) -> str | None:
    """
    Wandelt '6. November 2025' -> '06.11.2025' um.
    """
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

    # z.B. "6. November 2025" oder "06. November 2025"
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
    """
    Sucht nach 'Datum 6. November 2025' oder 'Datum: 6. November 2025'.
    Gibt Datum als 'TT.MM.JJJJ' zurück.
    """
    m = re.search(r"Datum[: ]+(\d{1,2}\.\s+[A-Za-zÄÖÜäöü]+\s+\d{4})", text)
    if not m:
        return None
    raw = m.group(1)
    return parse_german_date(raw)


def find_amount(text: str) -> str | None:
    """
    Sucht zuerst nach 'Rechnungstotal in CHF inkl. MWST 11.70'
    und, falls nicht gefunden, nach 'Rechnungsbetrag inkl. MWST CHF 11.70'.
    Gibt den Betrag als String, z.B. '11.70', zurück.
    """
    # Variante 1: Zusammenfassung
    m = re.search(
        r"Rechnungstotal in CHF inkl\. MWST\s+([0-9' ]+\.\d{2})",
        text
    )
    if m:
        return m.group(1).strip()

    # Variante 2: eBill-Block
    m = re.search(
        r"Rechnungsbetrag\s+inkl\. MWST\s+CHF\s+([0-9' ]+\.\d{2})",
        text,
        re.S,
    )
    if m:
        return m.group(1).strip()

    # Fallback: letzter Betrag vor 'Betrag' im Zahlteil (sehr grob)
    m = re.search(r"Währung\s+CHF\s+Betrag\s+([0-9' ]+\.\d{2})", text, re.S)
    if m:
        return m.group(1).strip()

    return None


def normalize_amount_for_number(amount_str: str) -> float | None:
    """
    Betrag in float umwandeln.
    z.B. "1'234.50" oder "1'234,50" -> 1234.5
    """
    try:
        s = amount_str.replace("'", "").replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return None


# ---------------- Hauptfunktion ----------------

def main():
    base_dir = BASE_DIR
    csv_path = os.path.join(base_dir, SWISSCOM_SUBFOLDER, CSV_NAME)
    swisscom_dir = os.path.join(base_dir, SWISSCOM_SUBFOLDER)

    os.makedirs(swisscom_dir, exist_ok=True)

    csv_exists = os.path.exists(csv_path)
    csv_file = open(csv_path, mode="a", newline="", encoding="utf-8")
    writer = csv.writer(csv_file, delimiter=";")

    if not csv_exists:
        # Spalten: Datum, Betrag (Text), Betrag_num, Datei
        writer.writerow(["Rechnungsdatum", "Betrag_roh", "Betrag_num", "Datei"])

    for fname in os.listdir(base_dir):
        if not fname.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(base_dir, fname)
        if not os.path.isfile(pdf_path):
            continue

        print(f"Verarbeite {fname} ...")
        try:
            text = extract_text_from_pdf(pdf_path)
        except Exception as e:
            print(f"  Fehler beim Lesen von {fname}: {e}")
            continue

        if not is_swisscom_invoice(text):
            print("  keine Swisscom-Rechnung erkannt.")
            continue

        date_str = find_datum(text)
        if not date_str:
            print("  Konnte Datum nicht finden!")

        amount_str = find_amount(text)
        if not amount_str:
            print("  Konnte Betrag nicht finden, ueberspringe.")
            continue

        amount_num = normalize_amount_for_number(amount_str)

        # In CSV schreiben
        writer.writerow([
            date_str or "",
            amount_str,
            amount_num if amount_num is not None else "",
            fname,
        ])

        # PDF in Unterordner verschieben
        target_path = os.path.join(swisscom_dir, fname)
        try:
            shutil.move(pdf_path, target_path)
            print(f"  nach {target_path} verschoben.")
        except Exception as e:
            print(f"  Fehler beim Verschieben von {fname}: {e}")

    csv_file.close()
    print("Fertig.")


if __name__ == "__main__":
    main()
