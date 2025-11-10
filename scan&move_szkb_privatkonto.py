#!/usr/bin/env python3
import os
import re
import csv
import shutil
import pdfplumber

# === EINSTELLUNGEN ANPASSEN ===
BASE_DIR = r"D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage"  # dein Rechnungs-/Doku-Ordner
SUBFOLDER = "szkb_privatkonto"
CSV_NAME = "szkb_privatkonto.csv"

# Keywords zur Erkennung von Kontoauszügen
# -> hier kannst du Banknamen ergänzen, z.B. "Zürcher Kantonalbank", "Raiffeisen", ...
STATEMENT_KEYWORDS = [
    "Schwyzer Kantonalbank",
    "Privatkonto",
    "812186-0560",
]

# Mögliche Wörter rund um Schlusssaldo
SALDO_KEYWORDS = [
    "Schlusssaldo"
]


def extract_text_from_pdf(pdf_path: str) -> str:
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            text.append(t)
    return "\n".join(text)


def is_statement(text: str) -> bool:
    upper = text.upper()
    return any(k.upper() in upper for k in STATEMENT_KEYWORDS)


def find_all_dates(text: str):
    """
    Findet alle Datumsangaben im Format TT.MM.JJJJ.
    Gibt eine Liste von Strings zurück.
    """
    return re.findall(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)


def find_period_from_dates(dates: list[str]) -> tuple[str | None, str | None]:
    """
    Nimmt eine Liste von Datumsstrings (TT.MM.JJJJ),
    sortiert sie lexikographisch (funktioniert hier),
    und gibt (von, bis) zurück.
    """
    if not dates:
        return None, None
    dates_sorted = sorted(dates)
    return dates_sorted[0], dates_sorted[-1]


def find_saldo(text: str) -> str | None:
    """
    Sucht nach einer Zeile mit 'Schlusssaldo', 'Saldo neu', etc.
    und extrahiert den letzten gefundenen Betrag.

    Betragsformat z.B.:
        CHF 1'234.50
        -1'234.50
        1'234.50
    """
    # Erst alle Zeilen mit 'Saldo...' sammeln
    lines = []
    for line in text.splitlines():
        if any(k.upper() in line.upper() for k in SALDO_KEYWORDS):
            lines.append(line)

    if not lines:
        # Fallback: irgendwo im Text nach 'Saldo' suchen
        saldos_in_text = re.findall(r"(Saldo.*)", text, flags=re.IGNORECASE)
        lines.extend(saldos_in_text)

    if not lines:
        return None

    # Wir nehmen die letzte gefundene Zeile als Schlusssaldo-Zeile
    last_line = lines[-1]

    # Betrag herausparsen
    m = re.search(r"([+-]?\s*CHF\s*)?([+-]?[0-9' ]+\.\d{2})", last_line)
    if not m:
        return None

    amount_str = m.group(2)
    return amount_str.strip()


def normalize_amount_for_number(amount_str: str) -> float | None:
    """
    Betragstring in float umwandeln.
    z.B. "1'234.50" oder "- 1'234.50" -> 1234.5 / -1234.5
    """
    try:
        s = amount_str.replace("'", "").replace(" ", "")
        # Komma-Fälle abfangen, falls Bank mit , arbeitet
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return None


def main():
    base_dir = BASE_DIR
    csv_path = os.path.join(base_dir, SUBFOLDER, CSV_NAME)
    target_dir = os.path.join(base_dir, SUBFOLDER)

    os.makedirs(target_dir, exist_ok=True)

    csv_exists = os.path.exists(csv_path)
    csv_file = open(csv_path, mode="a", newline="", encoding="utf-8")
    writer = csv.writer(csv_file, delimiter=";")

    if not csv_exists:
        # Spalten: von/bis, Schlusssaldo, Datei
        writer.writerow([
            "Von_Datum",
            "Bis_Datum",
            "Schlusssaldo_roh",
            "Schlusssaldo_num",
            "Datei",
        ])

    for fname in os.listdir(base_dir):
        if not fname.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(base_dir, fname)
        if not os.path.isfile(pdf_path):
            continue

        # Kontoauszug-Unterordner überspringen
        if os.path.dirname(pdf_path) == target_dir:
            continue

        print(f"Verarbeite {fname} ...")

        try:
            text = extract_text_from_pdf(pdf_path)
        except Exception as e:
            print(f"  Fehler beim Lesen von {fname}: {e}")
            continue

        if not is_statement(text):
            print("  kein Kontoauszug erkannt.")
            continue

        # Datumsbereich bestimmen
        dates = find_all_dates(text)
        von, bis = find_period_from_dates(dates)
        if not von and not bis:
            print("  Konnte keine Datumsangaben finden.")

        # Schlusssaldo bestimmen
        saldo_str = find_saldo(text)
        if not saldo_str:
            print("  Konnte Schlusssaldo nicht finden, ueberspringe CSV-Eintrag.")
            # du kannst hier auch continue machen, wenn ohne Betrag nicht sinnvoll
            saldo_num = None
        else:
            saldo_num = normalize_amount_for_number(saldo_str)

        # CSV-Eintrag schreiben
        writer.writerow([
            von or "",
            bis or "",
            saldo_str or "",
            saldo_num if saldo_num is not None else "",
            fname,
        ])

        # PDF verschieben
        target_path = os.path.join(target_dir, fname)
        try:
            shutil.move(pdf_path, target_path)
            print(f"  nach {target_path} verschoben.")
        except Exception as e:
            print(f"  Fehler beim Verschieben von {fname}: {e}")

    csv_file.close()
    print("Fertig.")


if __name__ == "__main__":
    main()
