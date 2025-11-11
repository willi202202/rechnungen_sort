#!/usr/bin/env python3
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt

# === EINSTELLUNGEN ANPASSEN ===
BASE_DIR = r"D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage\swisscom"  # z.B. r"C:\Users\Roman\Documents\Rechnungen"
CSV_NAME = "swisscom.csv"                    # oder "swisscom.cvs" falls du das so genannt hast

MONTH_LABELS = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
                "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


def load_data(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV-Datei nicht gefunden: {csv_path}")

    df = pd.read_csv(csv_path, sep=";", encoding="utf-8")

    # Erwartete Spalten:
    # "Rechnungsdatum", "Betrag_roh", "Betrag_num", "Datei"
    if "Rechnungsdatum" not in df.columns or "Betrag_num" not in df.columns:
        raise ValueError("CSV enthaelt nicht die erwarteten Spalten 'Rechnungsdatum' und 'Betrag_num'.")

    # Datum parsen (TT.MM.JJJJ)
    df["Rechnungsdatum"] = pd.to_datetime(
        df["Rechnungsdatum"],
        dayfirst=True,
        errors="coerce"
    )

    # Betrag als float
    df["Betrag_num"] = pd.to_numeric(df["Betrag_num"], errors="coerce")

    # Nur gueltige Zeilen behalten
    df = df.dropna(subset=["Rechnungsdatum", "Betrag_num"])

    return df


def create_yearly_overview(df: pd.DataFrame, year: int, output_path: str):
    # Daten fuer das angegebene Jahr filtern
    df_year = df[df["Rechnungsdatum"].dt.year == year]

    if df_year.empty:
        raise ValueError(f"Keine Daten fuer das Jahr {year} gefunden.")

    # Monatsweise summieren
    df_year["Monat"] = df_year["Rechnungsdatum"].dt.month
    monthly = df_year.groupby("Monat")["Betrag_num"].sum()

    # Sicherstellen, dass alle 12 Monate vorhanden sind
    monthly = monthly.reindex(range(1, 13), fill_value=0.0)

    total = monthly.sum()

    # ----------------- Plot / PDF -----------------
    plt.figure(figsize=(10, 6))

    # Balkendiagramm
    x = range(1, 13)
    plt.bar(x, monthly.values)
    plt.xticks(x, MONTH_LABELS)
    plt.ylabel("Betrag [CHF]")
    plt.title(f"Swisscom-Jahresübersicht {year} (Total: {total:.2f} CHF)")

    # Gitterlinien
    plt.grid(axis="y", linestyle=":", linewidth=0.5)

    # Etwas Text mit Totalsumme unten im Plot
    text = (
        f"Jahr: {year}\n"
        f"Total Swisscom-Zahlungen: {total:.2f} CHF\n"
        f"Anzahl Rechnungen: {len(df_year)}"
    )
    # Text in der Grafik platzieren
    plt.gcf().text(
        0.02, 0.02, text,
        fontsize=9,
        va="bottom",
        ha="left"
    )

    # Als PDF speichern
    plt.tight_layout(rect=(0, 0.06, 1, 1))  # Platz fuer den Text unten lassen
    plt.savefig(output_path, format="pdf")
    plt.close()

    print(f"PDF gespeichert als: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Erzeuge Swisscom-Jahresübersicht als PDF.")
    parser.add_argument(
        "--year",
        type=int,
        help="Jahr fuer die Auswertung (z.B. 2025). Wenn nicht gesetzt, wird das juengste Jahr im CSV genommen.",
    )
    args = parser.parse_args()

    base_dir = BASE_DIR
    csv_path = os.path.join(base_dir, CSV_NAME)

    df = load_data(csv_path)

    # Verfuegbare Jahre ermitteln
    years = sorted(df["Rechnungsdatum"].dt.year.unique())
    if not years:
        print("Keine gueltigen Daten im CSV gefunden.")
        return

    if args.year is not None:
        year = args.year
        if year not in years:
            print(f"Warnung: Jahr {year} nicht im CSV enthalten. Verfuegbare Jahre: {years}")
    else:
        # Standard: juengstes Jahr
        year = years[-1]
        print(f"Kein Jahr angegeben, verwende automatisch: {year}")

    output_name = f"swisscom_report_{year}.pdf"
    output_path = os.path.join(base_dir, output_name)

    create_yearly_overview(df, year, output_path)


if __name__ == "__main__":
    main()
