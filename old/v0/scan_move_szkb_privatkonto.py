#!/usr/bin/env python3
import re
import csv
import shutil
import pdfplumber
from pathlib import Path

from settings import BASE_DIR, SZKB_DIR, SZKB_CSV

# Keywords zur Erkennung von Kontoauszügen
STATEMENT_KEYWORDS = [
    "Schwyzer Kantonalbank",
    "Privatkonto",
    "812186-0560",
]

# Worte rund um den Schlusssaldo
SALDO_KEYWORDS = [
    "Schlusssaldo",
]


# -------------------------------------------------------------
# Helper
# -------------------------------------------------------------

def extract_text_from_pdf(pdf_path: Path) -> str:
    text = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            text.append(t)
    return "\n".join(text)


def is_statement(text: str) -> bool:
    upper = text.upper()
    return any(k.upper() in upper for k in STATEMENT_KEYWORDS)


def find_all_dates(text: str) -> list[str]:
    """Findet alle Datumsangaben im Format TT.MM.JJJJ."""
    return re.findall(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)


def find_period_from_dates(dates: list[str]) -> tuple[str | None, str | None]:
    """Ermittelt den Zeitraum (von, bis)."""
    if not dates:
        return None, None
    dates_sorted = sorted(dates)
    return dates_sorted[0], dates_sorted[-1]


def find_saldo(text: str) -> str | None:
    """
    Sucht den Schlusssaldo in Zeilen mit 'Saldo...'.
    """
    lines = []
    for line in text.splitlines():
        if any(k.upper() in line.upper() for k in SALDO_KEYWORDS):
            lines.append(line)

    # Fallback: breit im Text suchen
    if not lines:
        fallback = re.findall(r"(Saldo.*)", text, flags=re.IGNORECASE)
        lines.extend(fallback)

    if not lines:
        return None

    last_line = lines[-1]

    m = re.search(r"([+-]?\s*CHF\s*)?([+-]?[0-9' ]+\.\d{2})", last_line)
    if not m:
        return None

    return m.group(2).strip()


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


# -------------------------------------------------------------
# MAIN
# -------------------------------------------------------------

def main():

    SZKB_DIR.mkdir(parents=True, exist_ok=True)

    # Nur PDFs direkt im BASE_DIR
    pdf_files = list(f for f in BASE_DIR.glob("*.pdf") if f.is_file())

    recognized = 0
    moved_files = []

    csv_exists = SZKB_CSV.exists()
    with SZKB_CSV.open(mode="a", newline="", encoding="utf-8") as csv_file:

        writer = csv.writer(csv_file, delimiter=";")
        if not csv_exists:
            writer.writerow([
                "Von_Datum",
                "Bis_Datum",
                "Schlusssaldo_roh",
                "Schlusssaldo_num",
                "Datei",
            ])

        for pdf_path in pdf_files:

            try:
                text = extract_text_from_pdf(pdf_path)
            except Exception as e:
                print(f"[WARNUNG] Fehler beim Lesen von '{pdf_path.name}': {e}")
                continue

            if not is_statement(text):
                continue

            recognized += 1

            # Zeitraum bestimmen
            dates = find_all_dates(text)
            von, bis = find_period_from_dates(dates)

            # Saldo extrahieren
            saldo_str = find_saldo(text)
            if saldo_str:
                saldo_num = normalize_amount(saldo_str)
            else:
                saldo_num = None
                print(f"[WARNUNG] Kein Schlusssaldo in '{pdf_path.name}' gefunden.")

            # In CSV
            writer.writerow([
                von or "",
                bis or "",
                saldo_str or "",
                saldo_num if saldo_num is not None else "",
                pdf_path.name,
            ])

            # Datei verschieben
            target_path = SZKB_DIR / pdf_path.name
            try:
                shutil.move(str(pdf_path), str(target_path))
                moved_files.append(pdf_path.name)
            except Exception as e:
                print(f"[WARNUNG] Verschieben fehlgeschlagen für '{pdf_path.name}': {e}")

    # -------------------------------------------------------------
    # Zusammenfassung
    # -------------------------------------------------------------

    print("\n========== SZKB PRIVATKONTO – Zusammenfassung ==========")
    print(f"Gefundene PDF-Dateien:             {len(pdf_files)}")
    print(f"Erkannte Kontoauszüge:             {recognized}")
    print(f"Verschobene Kontoauszüge:          {len(moved_files)}")

    if moved_files:
        for f in moved_files:
            print("  -", f)


if __name__ == "__main__":
    main()
