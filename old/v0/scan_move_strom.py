#!/usr/bin/env python3
import os
import re
import csv
import shutil
from pathlib import Path

import pdfplumber

# ==========================
# KONFIGURATION
# ==========================

BASE_DIR = r"D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage"
STROM_SUBFOLDER = "strom"           # Zielordner fuer Stromrechnungen
CSV_NAME = "strom.csv"              # CSV mit allen Objekten

PROVIDER_KEYWORD = "Elektroversorgung"


# ==========================
# Hilfsfunktionen
# ==========================

def normalize_number(s: str) -> float | None:
    """
    '1'182' -> 1182.0
    '0.1370' -> 0.137
    '30.00' -> 30.0
    """
    if s is None:
        return None
    s = s.replace("'", "").replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return None


def normalize_date_ddmmyy(date_str: str) -> str:
    """
    01.07.25 -> 01.07.2025
    01.07.2025 -> 01.07.2025
    """
    date_str = date_str.strip()
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{2}|\d{4})$", date_str)
    if not m:
        return date_str
    d, mth, y = m.groups()
    if len(y) == 2:
        yy = int(y)
        year = 2000 + yy if yy <= 79 else 1900 + yy
    else:
        year = int(y)
    return f"{d}.{mth}.{year}"


def extract_first(text: str, pattern: str, flags=0) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None

def parse_mwst_rate_from_table(energy_net_section: str) -> float | None:
    """
    Liest den MWST-Satz aus Tabellenzeilen der Betragsermittlung.
    Am Zeilenende stehen i.d.R. drei Zahlen: exkl  %satz  inkl.
    """
    if not energy_net_section:
        return None

    # Regex: ... <exkl> <prozentsatz> <inkl> am Zeilenende
    pat = re.compile(
        r"([0-9']+[.,]\d{2})\s+([0-9]{1,2}[.,]\d{1,2})\s+([0-9']+[.,]\d{2})\s*$"
    )

    for raw in energy_net_section.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = pat.search(line)
        if not m:
            continue

        # gruppe2 = % Satz MWST
        satz = m.group(2).replace(",", ".")
        try:
            val = float(satz)
        except ValueError:
            continue

        # Plausibilitätsfenster (CH): ~5–15 %
        if 5.0 <= val <= 15.0:
            return round(val, 2)

    return None

# ==========================
# Parsing pro Objekt-Seite
# ==========================

def parse_object_page(text: str, rechnungsnummer: str, filename: str) -> dict | None:
    """
    Parsed eine Seite mit:
      - 'Objekt: ...'
      - Bezugsermittlung
      - Betragsermittlung (Energie / Netznutzung / Grundpreis)
      - Abgaben
      - Total Objekt
    und gibt ein Dict mit allen benoetigten Feldern zurueck.
    """

    # Objekt-Name
    objekt = extract_first(text, r"Objekt:\s*(.+)")
    if not objekt:
        return None

    # ----- Bezugsermittlung: HT/NT Stand + Zeitraum -----
    bezug_idx = text.find("Bezugsermittlung")
    if bezug_idx == -1:
        return None
    # bis zur naechsten Ueberschrift
    next_idx = text.find("Bezug Ansatz", bezug_idx)
    if next_idx == -1:
        next_idx = text.find("Betragsermittlung", bezug_idx)
    bezug_section = text[bezug_idx:next_idx]

    # Hochtarif Energie (Zeile mit Datum/Zaehler/Staenden)
    m_ht = re.search(
        r"Hochtarif Energie\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*kWh",
        bezug_section
    )
    m_nt = re.search(
        r"Niedertarif Energie\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*kWh",
        bezug_section
    )
    zeitraum_von = zeitraum_bis = None
    ht_stand_alt = ht_stand_neu = ht_bezug = None
    nt_stand_alt = nt_stand_neu = nt_bezug = None

    if m_ht:
        z_von_raw, z_bis_raw = m_ht.group(1), m_ht.group(2)
        zeitraum_von = normalize_date_ddmmyy(z_von_raw)
        zeitraum_bis = normalize_date_ddmmyy(z_bis_raw)
        ht_stand_alt = normalize_number(m_ht.group(4))
        ht_stand_neu = normalize_number(m_ht.group(5))
        ht_bezug = normalize_number(m_ht.group(6))

    if m_nt:
        # m_nt.group(1) = Zeitraum von  -> 01.07.25
        # m_nt.group(2) = Zeitraum bis  -> 01.10.25
        # m_nt.group(3) = Stand alt     -> 28'363
        # m_nt.group(4) = Stand neu     -> 29'297
        # m_nt.group(5) = Bezug         -> 934
        nt_stand_alt = normalize_number(m_nt.group(3))
        nt_stand_neu = normalize_number(m_nt.group(4))
        nt_bezug     = normalize_number(m_nt.group(5))

    # ----- Betragsermittlung: Energie / Netznutzung / Grundpreis -----
    betrag_idx = text.find("Betragsermittlung")
    if betrag_idx != -1:
        abgaben_idx = text.find("Abgaben", betrag_idx)
        energy_net_section = text[betrag_idx:abgaben_idx if abgaben_idx != -1 else None]
    else:
        energy_net_section = ""

    # --- MWST-Satz [%] ---
    mwst_satz_prozent = parse_mwst_rate_from_table(energy_net_section)

    # Energie: Hochtarif / Niedertarif
    ht_energie_ansatz = None
    nt_energie_ansatz = None
    m_ht_e = re.search(r"Hochtarif Energie\s+[\d']+\s*kWh\s+([0-9]+\.\d+)", energy_net_section)
    m_nt_e = re.search(r"Niedertarif Energie\s+[\d']+\s*kWh\s+([0-9]+\.\d+)", energy_net_section)
    if m_ht_e:
        ht_energie_ansatz = normalize_number(m_ht_e.group(1))
    if m_nt_e:
        nt_energie_ansatz = normalize_number(m_nt_e.group(1))

    # Netznutzung: Hochtarif / Niedertarif
    ht_net_ansatz = None
    nt_net_ansatz = None
    m_ht_n = re.search(r"Hochtarif Netznutzung\s+[\d']+\s*kWh\s+([0-9]+\.\d+)", energy_net_section)
    m_nt_n = re.search(r"Niedertarif Netznutzung\s+[\d']+\s*kWh\s+([0-9]+\.\d+)", energy_net_section)
    if m_ht_n:
        ht_net_ansatz = normalize_number(m_ht_n.group(1))
    if m_nt_n:
        nt_net_ansatz = normalize_number(m_nt_n.group(1))

    # Grundpreis pro Messstelle (Ansatz + Flag, ob verrechnet)
    grundpreis_ansatz = None
    grundpreis_verrechnet = False

    m_gp_line = re.search(r"Grundpreis pro Messstelle.*", energy_net_section)
    if m_gp_line:
        line = m_gp_line.group(0)
        # alle Dezimalzahlen in der Zeile holen, z.B.:
        # "Grundpreis pro Messstelle 1 10.0000 3 Mt. 30.00 8.10 32.43"
        nums = re.findall(r"[0-9']+\.\d+", line)
        if nums:
            # erste Zahl: Ansatz (10.0000)
            grundpreis_ansatz = normalize_number(nums[0])
            # zweite Zahl: Betrag exkl. MwSt (30.00), falls vorhanden
            if len(nums) >= 2:
                grundpreis_betrag_exkl = normalize_number(nums[1])
                if grundpreis_betrag_exkl is not None and grundpreis_betrag_exkl > 0:
                    grundpreis_verrechnet = True
            else:
                # wenn nur der Ansatz vorhanden ist, aber kein Betrag, behandeln wir als nicht verrechnet
                grundpreis_verrechnet = False

    # ----- Abgaben: Systemdienstl. / KEV / Gemeinde / Stromreserve -----
    abgaben_idx = text.find("Abgaben")
    systemdienstl_ansatz = kev_ansatz = abgabe_gem_ansatz = stromreserve_ansatz = None
    if abgaben_idx != -1:
        total_obj_idx = text.find("Total Objekt", abgaben_idx)
        abgaben_section = text[abgaben_idx:total_obj_idx if total_obj_idx != -1 else None]

        def parse_abgabe(label: str) -> float | None:
            m = re.search(
                rf"{label}\s+[\d']+\s*kWh\s+([0-9]+\.\d+)",
                abgaben_section
            )
            return normalize_number(m.group(1)) if m else None

        systemdienstl_ansatz = parse_abgabe("Systemdienstleistungen")
        kev_ansatz = parse_abgabe("Kostendeckende Einspeisevergütung")
        abgabe_gem_ansatz = parse_abgabe("Abgabe an die Gemeinde")
        stromreserve_ansatz = parse_abgabe("Stromreserve")

    # ----- Total Objekt -----
    total_obj = None
    m_tot = re.search(r"Total Objekt\s+([0-9']+\.\d{2})", text)
    if m_tot:
        total_obj = normalize_number(m_tot.group(1))

    row = {
        "Rechnungsnummer": rechnungsnummer,
        "Objekt": objekt,
        "Zeitraum_von": zeitraum_von or "",
        "Zeitraum_bis": zeitraum_bis or "",
        "MWST_Satz_prozent": mwst_satz_prozent,
        "Grundpreis_Messstelle_Ansatz_CHF": grundpreis_ansatz,
        "Grundpreis_verrechnet": grundpreis_verrechnet,
        "Systemdienstleistungen_Ansatz_CHF": systemdienstl_ansatz,
        "KEV_Ansatz_CHF": kev_ansatz,
        "Abgabe_Gemeinde_Ansatz_CHF": abgabe_gem_ansatz,
        "Stromreserve_Ansatz_CHF": stromreserve_ansatz,
        "HT_Stand_alt_kWh": ht_stand_alt,
        "HT_Stand_neu_kWh": ht_stand_neu,
        "HT_Bezug_kWh": ht_bezug,
        "HT_Energie_Ansatz_CHF_kWh": ht_energie_ansatz,
        "HT_Netznutzung_Ansatz_CHF_kWh": ht_net_ansatz,
        "NT_Stand_alt_kWh": nt_stand_alt,
        "NT_Stand_neu_kWh": nt_stand_neu,
        "NT_Bezug_kWh": nt_bezug,
        "NT_Energie_Ansatz_CHF_kWh": nt_energie_ansatz,
        "NT_Netznutzung_Ansatz_CHF_kWh": nt_net_ansatz,
        "Total_Objekt_CHF": total_obj,
        "Datei": filename,
    }
    return row


# ==========================
# Hauptlogik: scan & move
# ==========================

def process_stromrechnungen():
    base = Path(BASE_DIR)
    strom_dir = base / STROM_SUBFOLDER
    strom_dir.mkdir(exist_ok=True)

    csv_path = strom_dir / CSV_NAME
    csv_exists = csv_path.exists()

    fieldnames = [
        "Rechnungsnummer",
        "Objekt",
        "Zeitraum_von",
        "Zeitraum_bis",
        "MWST_Satz_prozent",
        "Grundpreis_Messstelle_Ansatz_CHF",
        "Grundpreis_verrechnet",
        "Systemdienstleistungen_Ansatz_CHF",
        "KEV_Ansatz_CHF",
        "Abgabe_Gemeinde_Ansatz_CHF",
        "Stromreserve_Ansatz_CHF",
        "HT_Stand_alt_kWh",
        "HT_Stand_neu_kWh",
        "HT_Bezug_kWh",
        "HT_Energie_Ansatz_CHF_kWh",
        "HT_Netznutzung_Ansatz_CHF_kWh",
        "NT_Stand_alt_kWh",
        "NT_Stand_neu_kWh",
        "NT_Bezug_kWh",
        "NT_Energie_Ansatz_CHF_kWh",
        "NT_Netznutzung_Ansatz_CHF_kWh",
        "Total_Objekt_CHF",
        "Datei",
    ]

    with csv_path.open("a", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=fieldnames, delimiter=";")
        if not csv_exists:
            writer.writeheader()

        # alle PDFs im Basisordner durchgehen
        for entry in base.iterdir():
            if not entry.is_file():
                continue
            if not entry.name.lower().endswith(".pdf"):
                continue

            pdf_path = entry
            print(f"Pruefe Datei: {pdf_path.name}")  # Debug-Ausgabe

            try:
                with pdfplumber.open(pdf_path) as pdf:
                    first_text = (pdf.pages[0].extract_text() or "")
                    # Grober Provider-Check, case-insensitive
                    if PROVIDER_KEYWORD.lower() not in first_text.lower():
                        print("  -> Kein Gemeindewerke-PDF, ueberspringe.")
                        continue

                    # Rechnungsnummer extrahieren (falls vorhanden)
                    rechnungsnummer = extract_first(first_text, r"Rechnungsnummer\s+([\d']+)")
                    if not rechnungsnummer:
                        rechnungsnummer = ""

                    # alle Seiten mit "Objekt:" durchgehen
                    for page in pdf.pages:
                        txt = page.extract_text() or ""
                        if "Objekt:" not in txt:
                            continue

                        row = parse_object_page(txt, rechnungsnummer, pdf_path.name)
                        if row:
                            writer.writerow(row)
                            print(f"  -> Objekt erfasst: {row['Objekt']}")

            except Exception as e:
                print(f"Fehler beim Verarbeiten von {pdf_path.name}: {e}")
                continue

            # PDF in den Strom-Unterordner verschieben
            target = strom_dir / pdf_path.name
            if not target.exists():
                shutil.move(str(pdf_path), str(target))
                print(f"  -> Verschoben nach {target}")

    print(f"Fertig. CSV: {csv_path}")


if __name__ == "__main__":
    process_stromrechnungen()
