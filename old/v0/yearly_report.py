#!/usr/bin/env python3
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

MONTH_LABELS = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
                "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


def load_data(csv_path: str, sep: str = ";") -> tuple[pd.DataFrame, str]:
    """
    Lädt Daten aus einer CSV und erkennt automatisch den Modus:

    - Modus 'invoice':
        Spalten: 'Rechnungsdatum', 'Betrag_num'
        -> wird auf generische Spalten 'Datum', 'Wert' abgebildet

    - Modus 'statement':
        Spalten: 'Bis_Datum', 'Schlusssaldo_num'
        -> wird auf 'Datum', 'Wert' abgebildet

    Rückgabe: (DataFrame mit Spalten 'Datum', 'Wert', mode)
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV-Datei nicht gefunden: {csv_path}")

    df = pd.read_csv(csv_path, sep=sep, encoding="utf-8")

    mode = None

    # Fall 1: Rechnungen
    if "Rechnungsdatum" in df.columns and "Betrag_num" in df.columns:
        mode = "invoice"

        df["Rechnungsdatum"] = pd.to_datetime(
            df["Rechnungsdatum"], dayfirst=True, errors="coerce"
        )
        df["Betrag_num"] = pd.to_numeric(df["Betrag_num"], errors="coerce")

        df = df.dropna(subset=["Rechnungsdatum", "Betrag_num"]).copy()
        df["Datum"] = df["Rechnungsdatum"]
        df["Wert"] = df["Betrag_num"]

    # Fall 2: Kontoauszug
    elif "Bis_Datum" in df.columns and "Schlusssaldo_num" in df.columns:
        mode = "statement"

        df["Bis_Datum"] = pd.to_datetime(
            df["Bis_Datum"], dayfirst=True, errors="coerce"
        )
        df["Schlusssaldo_num"] = pd.to_numeric(df["Schlusssaldo_num"], errors="coerce")

        df = df.dropna(subset=["Bis_Datum", "Schlusssaldo_num"]).copy()
        df["Datum"] = df["Bis_Datum"]
        df["Wert"] = df["Schlusssaldo_num"]

    if mode is None:
        raise ValueError(
            "CSV wird nicht erkannt.\n"
            "Erwartet entweder:\n"
            "  - 'Rechnungsdatum' + 'Betrag_num' (Rechnungen) oder\n"
            "  - 'Bis_Datum' + 'Schlusssaldo_num' (Kontoauszug)."
        )

    return df, mode


def create_yearly_overview(df: pd.DataFrame, year: int, label: str,
                           output_path: str, mode: str):
    # Daten fuer das angegebene Jahr filtern
    df_year = df[df["Datum"].dt.year == year].copy()

    if df_year.empty:
        raise ValueError(f"Keine Daten fuer das Jahr {year} gefunden.")

    # ----------------- Modus: Rechnungen (Monatssummen) -----------------
    if mode == "invoice":
        df_year["Monat"] = df_year["Datum"].dt.month
        monthly = df_year.groupby("Monat")["Wert"].sum()
        monthly = monthly.reindex(range(1, 13), fill_value=0.0)
        total = monthly.sum()

        plt.figure(figsize=(10, 6))

        x = range(1, 13)
        plt.bar(x, monthly.values)
        plt.xticks(x, MONTH_LABELS)
        plt.ylabel("Betrag [CHF]")
        plt.title(f"{label} – Jahresübersicht {year} (Total: {total:.2f} CHF)")

        plt.grid(axis="y", linestyle=":", linewidth=0.5)

        text = (
            f"Jahr: {year}\n"
            f"Total Zahlungen: {total:.2f} CHF\n"
            f"Anzahl Einträge: {len(df_year)}"
        )
        plt.gcf().text(
            0.02, 0.02, text,
            fontsize=9,
            va="bottom",
            ha="left"
        )

        plt.tight_layout(rect=(0, 0.06, 1, 1))
        plt.savefig(output_path, format="pdf")
        plt.close()

    # ----------------- Modus: Kontoauszug (Saldo-Verlauf + Ableitung) -----------------
    elif mode == "statement":
        # nach Datum sortieren
        df_year = df_year.sort_values("Datum").copy()

        # Differenz (Ableitung) berechnen
        df_year["Delta"] = df_year["Wert"].diff()
        last_saldo = df_year["Wert"].iloc[-1]
        min_saldo = df_year["Wert"].min()
        max_saldo = df_year["Wert"].max()

        fig, ax1 = plt.subplots(figsize=(10, 6))

        # --- Hauptplot: Kontostand ---
        ax1.plot(df_year["Datum"], df_year["Wert"], marker="o", color="tab:blue", label="Kontostand")
        ax1.set_ylabel("Kontostand [CHF]", color="tab:blue")
        ax1.tick_params(axis="y", labelcolor="tab:blue")
        ax1.grid(True, linestyle=":", linewidth=0.5)

        # --- Zweitachse: Delta (Ableitung) ---
        ax2 = ax1.twinx()
        ax2.bar(df_year["Datum"], df_year["Delta"], width=10, color="tab:red", alpha=0.3, label="Δ Saldo")
        ax2.set_ylabel("Δ Saldo [CHF]", color="tab:red")
        ax2.tick_params(axis="y", labelcolor="tab:red")

        # X-Achse: Monate
        ax1.xaxis.set_major_locator(mdates.MonthLocator())
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

        # Titel + Text
        fig.suptitle(f"{label} – Kontostandverlauf {year}", fontsize=14)

        text = (
            f"Jahr: {year}\n"
            f"Letzter Saldo: {last_saldo:.2f} CHF\n"
            f"Min. Saldo: {min_saldo:.2f} CHF\n"
            f"Max. Saldo: {max_saldo:.2f} CHF\n"
            f"Anzahl Auszüge: {len(df_year)}"
        )
        fig.text(0.02, 0.02, text, fontsize=9, va="bottom", ha="left")

        fig.tight_layout(rect=(0, 0.06, 1, 1))
        fig.savefig(output_path, format="pdf")
        plt.close(fig)
    else:
        raise ValueError(f"Unbekannter Modus: {mode}")

    print(f"PDF gespeichert als: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generischer Jahresreport aus CSV.\n"
            "- Rechnungen: 'Rechnungsdatum' + 'Betrag_num'\n"
            "- Kontoauszug: 'Bis_Datum' + 'Schlusssaldo_num'"
        )
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Pfad zur CSV-Datei (z.B. swisscom.csv, swisscard.csv, kontoauszug.csv, ...)",
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Jahr fuer die Auswertung (z.B. 2025). "
             "Wenn nicht gesetzt, wird das juengste Jahr im CSV genommen.",
    )
    parser.add_argument(
        "--label",
        help="Label/Firmenname fuer Titel (z.B. 'Swisscom', 'Swisscard', 'Konto'). "
             "Standard: Dateiname ohne Endung.",
    )
    parser.add_argument(
        "--out",
        help="Pfad zur Ausgabedatei (PDF). "
             "Standard: <label>_report_<year>.pdf im gleichen Ordner wie die CSV.",
    )
    parser.add_argument(
        "--sep",
        default=";",
        help="CSV-Separator (Standard: ';').",
    )
    args = parser.parse_args()

    csv_path = os.path.abspath(args.csv)
    base_dir = os.path.dirname(csv_path)

    # Label bestimmen
    if args.label:
        label = args.label
    else:
        label = os.path.splitext(os.path.basename(csv_path))[0]

    df, mode = load_data(csv_path, sep=args.sep)

    years = sorted(df["Datum"].dt.year.unique())
    if not years:
        print("Keine gueltigen Daten im CSV gefunden.")
        return

    # Jahr bestimmen
    if args.year is not None:
        year = args.year
        if year not in years:
            print(f"Warnung: Jahr {year} nicht im CSV enthalten. Verfuegbare Jahre: {years}")
    else:
        year = years[-1]
        print(f"Kein Jahr angegeben, verwende automatisch: {year}")

    # Output-Pfad bestimmen
    if args.out:
        output_path = os.path.abspath(args.out)
    else:
        safe_label = label.replace(" ", "_")
        output_name = f"{safe_label}_report_{year}.pdf"
        output_path = os.path.join(base_dir, output_name)

    create_yearly_overview(df, year, label, output_path, mode)


if __name__ == "__main__":
    main()
