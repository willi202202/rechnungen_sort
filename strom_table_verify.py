#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strom_verify.py
Prüft strom.csv und zeigt Teilresultate pro Objekt in der Konsole inkl. ASCII-Balken.
Schreibt zusätzlich eine *_verified.csv mit allen Rechenschritten.

Benötigt: pandas
"""

import argparse
import math
from datetime import datetime
import pandas as pd

# ---------- Helpers ----------

def num(x):
    """Robust nach float wandeln: erlaubt '1'234.56, 1'234.56, 1 234,56 etc."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0.0
    s = str(x).strip()
    if s == "" or s.lower() == "none":
        return 0.0
    s = s.replace("'", "").replace(" ", "").replace("\u00A0", "")  # geschütztes Leerzeichen
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def round2(x):
    return float(f"{x:.2f}")

def parse_dmy(s: str):
    if not s or str(s).strip() == "":
        return None
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(str(s).strip(), fmt)
        except ValueError:
            continue
    return None

def months_between(d1, d2) -> float:
    """
    Ganze Monate zwischen d1 und d2.
    Beispiel: 01.07.2025 -> 01.10.2025 = 3.
    Falls Tag(d2) < Tag(d1), 1 Monat abziehen.
    """
    if not d1 or not d2:
        return 0.0
    m = (d2.year - d1.year) * 12 + (d2.month - d1.month)
    if d2.day < d1.day:
        m -= 1
    return float(max(m, 0))

def yn_flag(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes", "ja")

def make_bar(values, width=44):
    """
    Erzeugt kurze ASCII-Balken. Skaliert auf max-Betrag der übergebenen Werte.
    """
    vmax = max([abs(v) for v in values] + [1.0])
    scale = width / vmax
    def bar(v):
        n = int(round(abs(v) * scale))
        return "█" * n
    return bar

# ---------- Kernberechnung pro Zeile ----------

def recompute_row(row):
    # Bezug in kWh
    ht_kwh = num(row.get("HT_Bezug_kWh"))
    nt_kwh = num(row.get("NT_Bezug_KWh") or row.get("NT_Bezug_kWh"))  # toleranter Key
    tot_kwh = ht_kwh + nt_kwh

    # Ansätze Energie/Netznutzung (CHF/kWh)
    ht_e = num(row.get("HT_Energie_Ansatz_CHF_kWh"))
    nt_e = num(row.get("NT_Energie_Ansatz_CHF_kWh"))
    ht_n = num(row.get("HT_Netznutzung_Ansatz_CHF_kWh"))
    nt_n = num(row.get("NT_Netznutzung_Ansatz_CHF_kWh"))

    # Abgaben-Ansätze (CHF/kWh)
    sysd = num(row.get("Systemdienstleistungen_Ansatz_CHF"))
    kev  = num(row.get("KEV_Ansatz_CHF"))
    gem  = num(row.get("Abgabe_Gemeinde_Ansatz_CHF"))
    res  = num(row.get("Stromreserve_Ansatz_CHF"))

    # Grundpreis
    gp_ans   = num(row.get("Grundpreis_Messstelle_Ansatz_CHF"))
    gp_verr  = yn_flag(row.get("Grundpreis_verrechnet", ""))
    d_von = parse_dmy(row.get("Zeitraum_von"))
    d_bis = parse_dmy(row.get("Zeitraum_bis"))
    monate = months_between(d_von, d_bis)
    exkl_grundpreis = gp_ans * monate * (1.0 if gp_verr else 0.0)

    # MWST
    mwst_rate = num(row.get("MWST_Satz_prozent")) / 100.0

    # Teilbeträge exkl. MWST
    exkl_energie     = ht_kwh*ht_e + nt_kwh*nt_e
    exkl_netznutzung = ht_kwh*ht_n + nt_kwh*nt_n
    exkl_abgaben     = tot_kwh * (sysd + kev + gem + res)

    exkl_summe = exkl_energie + exkl_netznutzung + exkl_abgaben + exkl_grundpreis
    mwst_betrag = exkl_summe * mwst_rate
    inkl_summe = exkl_summe + mwst_betrag

    total_rechnung = num(row.get("Total_Objekt_CHF"))
    delta = round2(inkl_summe) - round2(total_rechnung)
    ok = abs(delta) <= 0.05  # 5 Rp. Toleranz

    return {
        "Monate_Grundpreis": monate,
        "Exkl_Energie_CHF": round2(exkl_energie),
        "Exkl_Netznutzung_CHF": round2(exkl_netznutzung),
        "Exkl_Abgaben_CHF": round2(exkl_abgaben),
        "Exkl_Grundpreis_CHF": round2(exkl_grundpreis),
        "Exkl_Summe_CHF": round2(exkl_summe),
        "MWST_Satz_prozent": round2(mwst_rate*100.0),
        "MWST_Betrag_CHF": round2(mwst_betrag),
        "Recalc_Total_Inkl_CHF": round2(inkl_summe),
        "Total_Objekt_CHF": round2(total_rechnung),
        "Delta_CHF": round2(delta),
        "OK": ok,
    }

def print_console_block(row_dict, src_row, idx, ascii_width=44):
    """Hübscher Konsolen-Block mit Teilresultaten und ASCII-Balken."""
    titel = f"{src_row.get('Objekt','(ohne Objekt)')} | {src_row.get('Zeitraum_von','?')} – {src_row.get('Zeitraum_bis','?')}"
    rnr = src_row.get("Rechnungsnummer", "")
    label = f"[{idx+1}] {titel}"
    if rnr:
        label += f" | Rg-Nr: {rnr}"

    ex_ene = row_dict["Exkl_Energie_CHF"]
    ex_net = row_dict["Exkl_Netznutzung_CHF"]
    ex_abg = row_dict["Exkl_Abgaben_CHF"]
    ex_gp  = row_dict["Exkl_Grundpreis_CHF"]
    ex_sum = row_dict["Exkl_Summe_CHF"]
    mwst_p = row_dict["MWST_Satz_prozent"]
    mwst_b = row_dict["MWST_Betrag_CHF"]
    tot    = row_dict["Recalc_Total_Inkl_CHF"]
    inv    = row_dict["Total_Objekt_CHF"]
    delt   = row_dict["Delta_CHF"]
    ok     = row_dict["OK"]

    bar = make_bar([ex_ene, ex_net, ex_abg, ex_gp, mwst_b, tot, inv], width=ascii_width)

    print("=" * (len(label)))
    print(label)
    print("-" * (len(label)))
    print(f"  Monate Grundpreis: {row_dict['Monate_Grundpreis']:.0f}   |  GP verrechnet: {yn_flag(src_row.get('Grundpreis_verrechnet',''))}")
    print()
    print(f"  Exkl. Energie      {ex_ene:10.2f} CHF  {bar(ex_ene)}")
    print(f"  Exkl. Netznutzung  {ex_net:10.2f} CHF  {bar(ex_net)}")
    print(f"  Exkl. Abgaben      {ex_abg:10.2f} CHF  {bar(ex_abg)}")
    print(f"  Exkl. Grundpreis   {ex_gp:10.2f} CHF  {bar(ex_gp)}")
    print(f"  -----------------  {'-'*10}      {'-'*min(10,ascii_width)}")
    print(f"  Summe exkl. MWST   {ex_sum:10.2f} CHF")
    print(f"  MWST  ({mwst_p:>5.2f}%)    {mwst_b:10.2f} CHF  {bar(mwst_b)}")
    print(f"  -----------------  {'-'*10}      {'-'*min(10,ascii_width)}")
    print(f"  Total (recalc)     {tot:10.2f} CHF  {bar(tot)}")
    print(f"  Total (Rechnung)   {inv:10.2f} CHF  {bar(inv)}")
    status = "OK ✅" if ok else "NICHT OK ❌"
    print(f"  Delta              {delt:10.2f} CHF   --> {status}")
    print()

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Verifiziert strom.csv und zeigt Teilresultate pro Objekt auf der Konsole.")
    ap.add_argument("--csv", required=True, help="Pfad zur strom.csv")
    ap.add_argument("--sep", default=";", help="CSV-Separator (Default: ';')")
    ap.add_argument("--out", help="Optionaler Pfad für verifizierte CSV (Default: *_verified.csv)")
    ap.add_argument("--filter", help="Nur Zeilen, deren 'Objekt' diesen Text enthält (case-insensitive).")
    ap.add_argument("--limit", type=int, help="Nur die ersten N passenden Zeilen anzeigen.")
    args = ap.parse_args()

    df = pd.read_csv(args.csv, sep=args.sep, encoding="utf-8")

    if args.filter:
        f = args.filter.lower()
        if "Objekt" in df.columns:
            df = df[df["Objekt"].fillna("").str.lower().str.contains(f)]
        else:
            print("Warnung: 'Objekt'-Spalte nicht gefunden; Filter wird ignoriert.")

    results = []
    shown = 0
    for idx, (_, src_row) in enumerate(df.iterrows()):
        res = recompute_row(src_row)
        results.append(res)
        # Konsole: Teilresultate anzeigen
        print_console_block(res, src_row, idx)
        shown += 1
        if args.limit and shown >= args.limit:
            break

    # verifizierte CSV schreiben (alle Zeilen, nicht nur gefilterte Anzeige)
    df_out = pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)
    out_path = args.out if args.out else args.csv.replace(".csv", "_verified.csv")
    df_out.to_csv(out_path, sep=args.sep, index=False, encoding="utf-8")
    print(f"geschrieben: {out_path}")

    # kurze Zusammenfassung
    n = len(df_out)
    n_ok = int(df_out["OK"].sum()) if "OK" in df_out.columns else 0
    print(f"OK: {n_ok}/{n} Zeilen innerhalb ±0.05 CHF.")

if __name__ == "__main__":
    main()
