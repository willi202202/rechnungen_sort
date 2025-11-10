#!/usr/bin/env python3
import os
import re
import csv
import argparse
from pathlib import Path

import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

BASE_DIR_DEFAULT = r"D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage"
STATEMENT_SUBFOLDER_DEFAULT = "szkb_privatkonto"
DEFAULT_TYPES = ["E-Banking-Auftrag", "Gutschrift", "Belastung", "eBill-Rechnung"]


# ---------------- Hilfsfunktionen ----------------

def extract_text_from_pdf(pdf_path: str) -> str:
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            text.append(t)
    return "\n".join(text)


def normalize_date_ddmmyy(date_str: str) -> str:
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{2}|\d{4})$", date_str.strip())
    if not m:
        return date_str
    d, mth, y = int(m.group(1)), int(m.group(2)), m.group(3)
    year = 2000 + int(y) if len(y) == 2 else int(y)
    return f"{d:02d}.{mth:02d}.{year}"


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


def parse_booking_line(line: str, trigger_types: list[str]):
    escaped = [re.escape(t) for t in trigger_types]
    trigger_words = "(?:" + "|".join(escaped) + ")"
    pattern = rf"""
        (?P<date1>\d{{2}}\.\d{{2}}\.(?:\d{{2}}|\d{{4}}))
        \s+{trigger_words}\s+
        (?P<date2>\d{{2}}\.\d{{2}}\.(?:\d{{2}}|\d{{4}}))
        \s+(?P<amount>[0-9' ]+[.,]\d{{2}})
    """
    m = re.search(pattern, line, flags=re.IGNORECASE | re.VERBOSE)
    if not m:
        return None, None, None
    date_raw = m.group("date1")
    amt_str = m.group("amount")
    return normalize_date_ddmmyy(date_raw), amt_str, normalize_amount(amt_str)


# ---------------- Hauptfunktion ----------------

def scan_payee_bookings(base_dir: str, subfolder: str, payee: str,
                        trigger_types: list[str], output_dir: str) -> Path:
    statement_dir = Path(base_dir) / subfolder
    statement_dir.mkdir(parents=True, exist_ok=True)

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", payee).strip("_")
    csv_path = outdir / f"konto_{safe_name}.csv"

    payee_lower = payee.lower()

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Datum", "Betrag_roh", "Betrag_num", "Zeile", "Datei"])

        for pdf_file in sorted(statement_dir.glob("*.pdf")):
            print(f"Scanne {pdf_file.name} ...")
            try:
                text = extract_text_from_pdf(str(pdf_file))
            except Exception as e:
                print(f"  Fehler beim Lesen von {pdf_file.name}: {e}")
                continue

            lines = text.splitlines()
            last_date_generic = None
            hits = 0

            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    continue

                # letztes Datum merken
                dates = re.findall(r"\b(\d{2}\.\d{2}\.(\d{2}|\d{4}))\b", line_stripped)
                if dates:
                    last_date_generic = normalize_date_ddmmyy(dates[-1][0])

                if payee_lower not in line_stripped.lower():
                    continue

                datum = None
                amt_str = None
                amt_num = None

                # Variante A: Betrag am Ende der Zeile
                m_same = re.search(r"([0-9' ]+[.,]\d{2})\s*$", line_stripped)
                if m_same:
                    amt_str = m_same.group(1)
                    amt_num = normalize_amount(amt_str)
                    datum = last_date_generic

                # Variante B: Zeile darüber
                if amt_num is None and i > 0:
                    prev_line = lines[i - 1].strip()
                    d2, a2_str, a2_num = parse_booking_line(prev_line, trigger_types)
                    if a2_num is not None:
                        datum, amt_str, amt_num = d2, a2_str, a2_num

                if amt_num is None:
                    continue

                writer.writerow([datum or "", amt_str, amt_num, line_stripped, pdf_file.name])
                hits += 1

            print(f"  Gefundene Buchungen: {hits}")

    print(f"CSV gespeichert unter: {csv_path}")
    return csv_path


# ---------------- Plot / Report ----------------

def plot_payee_report(csv_path: Path, label: str, outdir: Path):
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8")
    df["Datum"] = pd.to_datetime(df["Datum"], dayfirst=True, errors="coerce")
    df["Betrag_num"] = pd.to_numeric(df["Betrag_num"], errors="coerce")
    df = df.dropna(subset=["Datum", "Betrag_num"])
    if df.empty:
        print("Keine Daten für Plot.")
        return

    df = df.sort_values("Datum")
    df["Jahr"] = df["Datum"].dt.year
    df["Monat"] = df["Datum"].dt.month
    monthly = df.groupby(["Jahr", "Monat"])["Betrag_num"].sum().reset_index()
    monthly["Monatsdatum"] = pd.to_datetime(
        dict(year=monthly["Jahr"], month=monthly["Monat"], day=15)
    )

    total = df["Betrag_num"].sum()
    years = sorted(df["Jahr"].unique())
    jahr_text = f"{years[0]}–{years[-1]}" if len(years) > 1 else f"{years[0]}"

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(monthly["Monatsdatum"], monthly["Betrag_num"], width=20)
    ax.set_ylabel("Betrag [CHF]")
    ax.set_title(f"{label} – Ausgabenanalyse ({jahr_text}), Total: {total:.2f} CHF")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.xticks(rotation=45, ha="right")
    ax.grid(axis="y", linestyle=":", linewidth=0.5)
    fig.tight_layout(rect=(0, 0.06, 1, 1))

    pdf_path = outdir / f"{label.replace(' ', '_')}_report.pdf"
    fig.savefig(pdf_path, format="pdf")
    plt.close(fig)
    print(f"PDF gespeichert unter: {pdf_path}")


# ---------------- main() ----------------

def main():
    parser = argparse.ArgumentParser(description="Extrahiert Buchungen eines bestimmten Payees.")
    parser.add_argument("--base", default=BASE_DIR_DEFAULT)
    parser.add_argument("--subfolder", default=STATEMENT_SUBFOLDER_DEFAULT)
    parser.add_argument("--payee", required=True, help="z.B. 'Agrisano Krankenkasse AG'")
    parser.add_argument("--types", default=",".join(DEFAULT_TYPES))
    parser.add_argument("--label", help="Titel im Report (Standard: Payee)")
    parser.add_argument("--outdir", required=True, help="Speicherort für CSV und PDF")

    args = parser.parse_args()
    trigger_types = [t.strip() for t in args.types.split(",") if t.strip()]

    csv_path = scan_payee_bookings(
        base_dir=args.base,
        subfolder=args.subfolder,
        payee=args.payee,
        trigger_types=trigger_types,
        output_dir=args.outdir,
    )
    plot_payee_report(csv_path, label=args.label or args.payee, outdir=Path(args.outdir))


if __name__ == "__main__":
    main()
