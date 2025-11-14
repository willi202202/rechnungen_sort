#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


MONTH_FMT = mdates.DateFormatter("%b %y")   # Jan 24, Feb 24, …
MONTH_LOC = mdates.MonthLocator()           # Monatstakte


def load_and_normalize(csv_path: str, sep: str = ";"):
    """
    Erkennt automatisch:
    - Rechnungen:   Rechnungsdatum + Betrag_num
    - Kontoauszug:  Bis_Datum + Schlusssaldo_num

    Gibt DataFrame mit Spalten:
      Datum (datetime64)
      Wert (float)
      mode ("invoice" oder "statement")
    """
    df = pd.read_csv(csv_path, sep=sep, encoding="utf-8")

    # Rechnungen
    if "Rechnungsdatum" in df.columns and "Betrag" in df.columns:
        mode = "invoice"
        df = df.copy()
        df["Datum"] = pd.to_datetime(df["Rechnungsdatum"], dayfirst=True, errors="coerce")
        df["Wert"] = pd.to_numeric(df["Betrag"], errors="coerce")

    # Kontoauszug
    elif "Bis_Datum" in df.columns and "Schlusssaldo" in df.columns:
        mode = "statement"
        df = df.copy()
        df["Datum"] = pd.to_datetime(df["Bis_Datum"], dayfirst=True, errors="coerce")
        df["Wert"] = pd.to_numeric(df["Schlusssaldo"], errors="coerce")

    else:
        raise ValueError(
            f"CSV {csv_path} wird nicht erkannt. "
            "Erwartet entweder (Rechnungsdatum,Betrag_num) oder (Bis_Datum,Schlusssaldo_num)."
        )

    df = df.dropna(subset=["Datum", "Wert"])
    df = df.sort_values("Datum")

    return df, mode


def parse_iso_date(s: str | None):
    """
    None → None
    '2024-05-01' → Timestamp
    """
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    return pd.to_datetime(s, format="%Y-%m-%d", errors="raise")


def determine_range(df, von, bis):
    """
    Bestimmt den effektiven Zeitraum:
    - wenn von fehlt   -> min Datum
    - wenn bis fehlt   -> max Datum
    """
    dmin = df["Datum"].min()
    dmax = df["Datum"].max()

    if von is None:
        von = dmin
    if bis is None:
        bis = dmax

    if von > bis:
        raise ValueError(f"von-Datum {von.date()} liegt nach bis-Datum {bis.date()}!")

    return von, bis


def plot_invoice(df, von, bis, label, outpath):
    """
    Monatsaggregation über beliebigen Zeitraum.
    """
    df = df[(df["Datum"] >= von) & (df["Datum"] <= bis)]

    if df.empty:
        raise ValueError("Keine Daten im gewählten Zeitraum.")

    # Monatssumme
    df["Monat"] = df["Datum"].dt.to_period("M")
    monthly = df.groupby("Monat")["Wert"].sum()

    # Index als echte Timestamps für Plotten
    x = monthly.index.to_timestamp()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x, monthly.values, width=20)  # breite Balken

    ax.set_title(f"{label} – Zeitraum {von.date()} bis {bis.date()}")
    ax.set_ylabel("Betrag [CHF]")
    ax.xaxis.set_major_locator(MONTH_LOC)
    ax.xaxis.set_major_formatter(MONTH_FMT)
    ax.grid(axis="y", linestyle=":", linewidth=0.5)

    # Textblock unten
    text = (
        f"Von: {von.date()}\n"
        f"Bis: {bis.date()}\n"
        f"Gesamt: {monthly.sum():.2f} | min: {monthly.min():.2f} | max: {monthly.max():.2f} CHF\n"
        f"Einträge: {len(df)}"
    )
    fig.text(0.02, 0.02, text)

    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(outpath)
    plt.close(fig)


def plot_statement(df, von, bis, label, outpath):
    """
    Saldo-Verlauf + Ableitung.
    """
    df = df[(df["Datum"] >= von) & (df["Datum"] <= bis)]
    if df.empty:
        raise ValueError("Keine Daten im gewählten Zeitraum.")

    df = df.sort_values("Datum")
    df["Delta"] = df["Wert"].diff()

    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Saldo-Linie
    ax1.plot(df["Datum"], df["Wert"], marker="o", color="tab:blue", label="Saldo")
    ax1.set_ylabel("Kontostand [CHF]", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.grid(True, linestyle=":", linewidth=0.5)

    # Delta-Achse
    ax2 = ax1.twinx()
    ax2.bar(df["Datum"], df["Delta"], width=10, alpha=0.3, color="tab:red")
    ax2.set_ylabel("Δ Saldo [CHF]", color="tab:red")
    ax2.tick_params(axis="y", labelcolor="tab:red")

    ax1.xaxis.set_major_locator(MONTH_LOC)
    ax1.xaxis.set_major_formatter(MONTH_FMT)

    fig.suptitle(f"{label} – Saldoverlauf\n{von.date()} bis {bis.date()}")

    text = (
        f"Von: {von.date()}\n"
        f"Bis: {bis.date()}\n"
        f"Letzter Saldo: {df['Wert'].iloc[-1]:.2f} CHF\n"
        f"Min: {df['Wert'].min():.2f} CHF\n"
        f"Max: {df['Wert'].max():.2f} CHF\n"
        f"Einträge: {len(df)}"
    )
    fig.text(0.02, 0.02, text)

    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(outpath)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Report über beliebigen Zeitraum.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--von", help="Startdatum YYYY-MM-DD")
    parser.add_argument("--bis", help="Enddatum YYYY-MM-DD")
    parser.add_argument("--label", help="Titel")
    parser.add_argument("--out", help="PDF-Ausgabepfad")
    parser.add_argument("--sep", default=";")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    df, mode = load_and_normalize(csv_path, sep=args.sep)

    von = parse_iso_date(args.von)
    bis = parse_iso_date(args.bis)
    von, bis = determine_range(df, von, bis)

    label = args.label or csv_path.stem

    # Ausgabedatei
    if args.out:
        outpath = Path(args.out)
    else:
        if args.von or args.bis:
            outname = f"{label}_report_{von.date()}_{bis.date()}.pdf"
        else:
            outname = f"{label}_report_full_range.pdf"
        outpath = csv_path.parent / outname

    if mode == "invoice":
        plot_invoice(df, von, bis, label, outpath)
    else:
        plot_statement(df, von, bis, label, outpath)

    print(f"[OK] Report gespeichert in: {outpath}")


if __name__ == "__main__":
    main()
