#!/usr/bin/env python3
import os
import re
import csv
import shutil
import pdfplumber

# === EINSTELLUNGEN ANPASSEN ===
BASE_DIR = r"D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage"  # z.B. r"C:\Users\Roman\Documents\Rechnungen"
SWISSCARD_SUBFOLDER = "swisscard"
CSV_NAME = "swisscard.csv"


# Soll statt dem vollen Betrag ("Neuer Saldo zu unseren Gunsten")
# die Mindestzahlung in die CSV geschrieben werden?
USE_MINDESTZAHLUNG = False   # True = Mindestzahlung, False = voller Saldo


# Erkennungsmerkmale fuer Swisscard-Rechnungen
SWISSCARD_KEYWORDS = [
    "Swisscard AECS",      # steht oben im Briefkopf
    "Cashback Cards",      # dein Kartentyp
]


def extract_text_from_pdf(pdf_path: str) -> str:
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            text.append(t)
    return "\n".join(text)


def is_swisscard_invoice(text: str) -> bool:
    upper = text.upper()
    return any(k.upper() in upper for k in SWISSCARD_KEYWORDS)


def find_rechnungsdatum(text: str) -> str | None:
    """
    Sucht explizit nach 'Rechnungsdatum 24.10.2025'.
    Fallback: erstes Datum im Format TT.MM.JJJJ.
    """
    m = re.search(r"Rechnungsdatum\s+(\d{2}\.\d{2}\.\d{4})", text)
    if m:
        return m.group(1)

    # Fallback: erstes Datum irgendwo
    m = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
    if m:
        return m.group(1)

    return None


def find_betraege_block(text: str) -> list[str] | None:
    """
    Sucht den Block mit den 5 CHF-Betraegen nach 'Mindestzahlung'
    und gibt eine Liste mit 5 Strings zurueck:
    [Saldo letzte Rechnung, Ihre Zahlungen, Total neue Transaktionen,
     Neuer Saldo, Mindestzahlung]
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
    if len(amounts) != 5:
        return None
    return amounts


def normalize_amount_for_number(amount_str: str) -> float | None:
    """
    Betrag in float umwandeln.
    z.B. "1'234.50" oder "1'234,50" -> 1234.5
    """
    try:
        s = amount_str.replace("'", "").replace(" ", "")
        # Punkt/Komma aufraeumen
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return None


def main():
    base_dir = BASE_DIR
    csv_path = os.path.join(base_dir, SWISSCARD_SUBFOLDER, CSV_NAME)
    swisscard_dir = os.path.join(base_dir, SWISSCARD_SUBFOLDER)

    os.makedirs(swisscard_dir, exist_ok=True)

    csv_exists = os.path.exists(csv_path)
    csv_file = open(csv_path, mode="a", newline="", encoding="utf-8")
    writer = csv.writer(csv_file, delimiter=";")

    if not csv_exists:
        # Spalten: Datum, Betrag (als Text), Betrag_num (float), Voll/Mindest, Datei
        writer.writerow(["Rechnungsdatum", "Betrag_roh", "Betrag_num", "Art", "Datei"])

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

        if not is_swisscard_invoice(text):
            print("  keine Swisscard-Rechnung erkannt.")
            continue

        # Datum suchen
        rechnungsdatum = find_rechnungsdatum(text)
        if not rechnungsdatum:
            print("  Konnte Rechnungsdatum nicht finden!")
        
        # Betraege-Block holen
        betraege = find_betraege_block(text)
        if not betraege:
            print("  Konnte Betragsblock nicht finden, ueberspringe.")
            continue

        saldo_letzte, zahlungen, total_trans, neuer_saldo, mindest = betraege

        if USE_MINDESTZAHLUNG:
            betrag_str = mindest
            art = "Mindestzahlung"
        else:
            betrag_str = neuer_saldo
            art = "Neuer Saldo"

        betrag_num = normalize_amount_for_number(betrag_str)

        # In CSV schreiben
        writer.writerow([
            rechnungsdatum or "",
            betrag_str,
            betrag_num if betrag_num is not None else "",
            art,
            fname,
        ])

        # PDF in Unterordner verschieben
        target_path = os.path.join(swisscard_dir, fname)
        try:
            shutil.move(pdf_path, target_path)
            print(f"  nach {target_path} verschoben.")
        except Exception as e:
            print(f"  Fehler beim Verschieben von {fname}: {e}")

    csv_file.close()
    print("Fertig.")


if __name__ == "__main__":
    main()
