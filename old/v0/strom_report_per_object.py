#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import math
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def num(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0.0
    s = str(x).strip().replace("\u00A0", "").replace("'", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def to_date(s):
    if pd.isna(s):
        return None
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(str(s), fmt)
        except ValueError:
            continue
    return None


def ensure_dates(df):
    # Preferiere Zeitraum_bis als X-Achse; fallback: Zeitraum_von
    df = df.copy()
    df["Date_X"] = df["Zeitraum_bis"].apply(to_date)
    missing = df["Date_X"].isna()
    if missing.any():
        df.loc[missing, "Date_X"] = df.loc[missing, "Zeitraum_von"].apply(to_date)
    return df.dropna(subset=["Date_X"]).sort_values("Date_X")


def add_computed_columns(df):
    df = df.copy()

    # Verbrauch
    df["HT_kWh"] = df.get("HT_Bezug_kWh", 0).apply(num)
    # toleranter Spaltenname für NT
    df["NT_kWh"] = (df["NT_Bezug_kWh"] if "NT_Bezug_kWh" in df.columns else df.get("NT_Bezug_KWh", 0)).apply(num)
    df["TOT_kWh"] = df["HT_kWh"] + df["NT_kWh"]

    # Sätze (CHF/kWh)
    df["HT_Energie_Satz"] = df.get("HT_Energie_Ansatz_CHF_kWh", 0).apply(num)
    df["NT_Energie_Satz"] = df.get("NT_Energie_Ansatz_CHF_kWh", 0).apply(num)
    df["HT_Netz_Satz"]    = df.get("HT_Netznutzung_Ansatz_CHF_kWh", 0).apply(num)
    df["NT_Netz_Satz"]    = df.get("NT_Netznutzung_Ansatz_CHF_kWh", 0).apply(num)

    # Abgaben-Satz (Summe, CHF/kWh)
    df["Abgaben_Satz"] = (
        df.get("Systemdienstleistungen_Ansatz_CHF", 0).apply(num)
        + df.get("KEV_Ansatz_CHF", 0).apply(num)
        + df.get("Abgabe_Gemeinde_Ansatz_CHF", 0).apply(num)
        + df.get("Stromreserve_Ansatz_CHF", 0).apply(num)
    )

    # Kosten (exkl. MWST) – aus strom_verified.csv nehmen, falls vorhanden; sonst selbst berechnen
    if {"Exkl_Energie_CHF", "Exkl_Netznutzung_CHF", "Exkl_Abgaben_CHF"}.issubset(df.columns):
        df["Kosten_Energie"]     = df["Exkl_Energie_CHF"].apply(num)
        df["Kosten_Netznutzung"] = df["Exkl_Netznutzung_CHF"].apply(num)
        df["Kosten_Abgaben"]     = df["Exkl_Abgaben_CHF"].apply(num)
    else:
        df["Kosten_Energie"]     = df["HT_kWh"] * df["HT_Energie_Satz"] + df["NT_kWh"] * df["NT_Energie_Satz"]
        df["Kosten_Netznutzung"] = df["HT_kWh"] * df["HT_Netz_Satz"]    + df["NT_kWh"] * df["NT_Netz_Satz"]
        df["Kosten_Abgaben"]     = (df["HT_kWh"] + df["NT_kWh"]) * df["Abgaben_Satz"]

    # Total inkl. MWST – nimm den Rechnungswert, wenn vorhanden (robuster)
    if "Total_Objekt_CHF" in df.columns:
        df["Kosten_Total_inkl"] = df["Total_Objekt_CHF"].apply(num)
    elif "Recalc_Total_Inkl_CHF" in df.columns:
        df["Kosten_Total_inkl"] = df["Recalc_Total_Inkl_CHF"].apply(num)
    else:
        # Fallback: exkl + MWST
        mwst_rate = df.get("MWST_Satz_prozent", 0).apply(num) / 100.0
        exkl_sum = df["Kosten_Energie"] + df["Kosten_Netznutzung"] + df["Kosten_Abgaben"]
        df["Kosten_Total_inkl"] = exkl_sum * (1.0 + mwst_rate)

    # MWST-Satz
    df["MWST_%"] = df.get("MWST_Satz_prozent", 0).apply(num)

    return df


def plot_consumption(ax, df, obj_label):
    ax.plot(df["Date_X"], df["HT_kWh"], marker="o", label="Hochtarif kWh")
    ax.plot(df["Date_X"], df["NT_kWh"], marker="o", label="Niedertarif kWh")
    ax.plot(df["Date_X"], df["TOT_kWh"], marker="o", label="Total kWh")
    ax.set_title(f"{obj_label} – Stromverbrauch")
    ax.set_ylabel("kWh")
    ax.grid(True, axis="both", linestyle=":", linewidth=0.5)
    ax.legend()
    ax.tick_params(axis="x", rotation=45)


def plot_costs(ax, df, obj_label):
    ax.plot(df["Date_X"], df["Kosten_Energie"], marker="o", label="Energie (exkl.)")
    ax.plot(df["Date_X"], df["Kosten_Netznutzung"], marker="o", label="Netznutzung (exkl.)")
    ax.plot(df["Date_X"], df["Kosten_Abgaben"], marker="o", label="Abgaben (exkl.)")
    ax.plot(df["Date_X"], df["Kosten_Total_inkl"], marker="o", label="Total (inkl. MWST)")
    ax.set_title(f"{obj_label} – Kostenentwicklung")
    ax.set_ylabel("CHF")
    ax.grid(True, axis="both", linestyle=":", linewidth=0.5)
    ax.legend()
    ax.tick_params(axis="x", rotation=45)


def _rel_change(series):
    s0 = series.iloc[0] if len(series) else 0.0
    if s0 == 0:
        return pd.Series([0.0]*len(series), index=series.index)
    return (series / s0 - 1.0) * 100.0


def plot_rates(ax, df, obj_label):
    # MWST-Satz direkt (in %)
    ax.plot(df["Date_X"], df["MWST_%"], marker="o", label="MWST-Satz [%]")

    # Relative Änderung (in %) der CHF/kWh-Sätze ggü. erster Periode
    for col, label in [
        ("HT_Energie_Satz", "HT Energie-Satz Δ%"),
        ("NT_Energie_Satz", "NT Energie-Satz Δ%"),
        ("HT_Netz_Satz",    "HT Netznutzung-Satz Δ%"),
        ("NT_Netz_Satz",    "NT Netznutzung-Satz Δ%"),
        ("Abgaben_Satz",    "Abgaben-Satz Δ%"),
    ]:
        rel = _rel_change(df[col])
        ax.plot(df["Date_X"], rel, marker="o", label=label)

    ax.set_title(f"{obj_label} – Veränderung der Sätze")
    ax.set_ylabel("%")
    ax.grid(True, axis="both", linestyle=":", linewidth=0.5)
    ax.legend()
    ax.tick_params(axis="x", rotation=45)


def make_report_for_object(df_obj, out_pdf_path, obj_label):
    # Drei getrennte Figuren (je eine Seite) – keine Subplots in einer Figure
    with PdfPages(out_pdf_path) as pdf:
        # 1) Verbrauch
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        plot_consumption(ax1, df_obj, obj_label)
        fig1.tight_layout()
        pdf.savefig(fig1)
        plt.close(fig1)

        # 2) Kosten
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        plot_costs(ax2, df_obj, obj_label)
        fig2.tight_layout()
        pdf.savefig(fig2)
        plt.close(fig2)

        # 3) Sätze
        fig3, ax3 = plt.subplots(figsize=(10, 6))
        plot_rates(ax3, df_obj, obj_label)
        fig3.tight_layout()
        pdf.savefig(fig3)
        plt.close(fig3)


def main():
    ap = argparse.ArgumentParser(description="Erzeugt pro Objekt einen Mehrseiten-Report (Verbrauch, Kosten, Sätze) aus strom_verified.csv.")
    ap.add_argument("--csv", required=True, help="Pfad zur strom_verified.csv")
    ap.add_argument("--outdir", required=True, help="Zielordner für die Reports")
    ap.add_argument("--sep", default=";", help="CSV-Separator (Default: ';')")
    ap.add_argument("--only", nargs="*", help="Optional: Liste von Objekt-Teilstrings zum Filtern (case-insensitive)")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path, sep=args.sep, encoding="utf-8")

    if "Objekt" not in df.columns:
        raise SystemExit("Spalte 'Objekt' wurde nicht gefunden.")

    # Datums- & Hilfsspalten
    df = ensure_dates(df)
    df = add_computed_columns(df)

    # optional filtern
    if args.only:
        needles = [s.lower() for s in args.only]
        mask = df["Objekt"].fillna("").str.lower().apply(lambda x: any(n in x for n in needles))
        df = df[mask]

    if df.empty:
        print("Keine passenden Zeilen gefunden.")
        return

    # pro Objekt
    for obj, g in df.groupby("Objekt"):
        safe = "".join(ch if ch.isalnum() else "_" for ch in (obj or "Objekt")).strip("_")
        out_pdf = outdir / f"{safe}_report.pdf"
        make_report_for_object(g, out_pdf, obj_label=obj)
        print(f"✔ Report geschrieben: {out_pdf}")


if __name__ == "__main__":
    main()
