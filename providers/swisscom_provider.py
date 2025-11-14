#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import re

import pdfplumber

from .base_provider import InvoiceProvider
from settings import SWISSCOM_DIR, SWISSCOM_CSV





MONTHS = {
    "JANUAR": 1,
    "FEBRUAR": 2,
    "MAERZ": 3,
    "MÄRZ": 3,
    "APRIL": 4,
    "MAI": 5,
    "JUNI": 6,
    "JULI": 7,
    "AUGUST": 8,
    "SEPTEMBER": 9,
    "OKTOBER": 10,
    "NOVEMBER": 11,
    "DEZEMBER": 12,
}


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    PDF -> reiner Text (alle Seiten).
    Diesen Helper können später auch Sorter / CSV-Builder benutzen.
    """
    chunks: List[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            chunks.append(t)
    return "\n".join(chunks)


def parse_german_date(date_str: str) -> str | None:
    """
    Wandelt '6. November 2025' -> '06.11.2025' um.
    """
    m = re.match(r"\s*(\d{1,2})\.\s+([A-Za-zÄÖÜäöü]+)\s+(\d{4})\s*$", date_str)
    if not m:
        return None

    day = int(m.group(1))
    month_name = (
        m.group(2)
        .upper()
        .replace("Ä", "AE")
        .replace("Ö", "OE")
        .replace("Ü", "UE")
    )
    year = int(m.group(3))

    month = MONTHS.get(month_name)
    if not month:
        return None

    return f"{day:02d}.{month:02d}.{year}"


def find_datum(text: str) -> str | None:
    """
    Sucht nach 'Datum 6. November 2025' oder 'Datum: 6. November 2025'.
    Gibt Datum als 'TT.MM.JJJJ' zurück.
    """
    m = re.search(r"Datum[: ]+(\d{1,2}\.\s+[A-Za-zÄÖÜäöü]+\s+\d{4})", text)
    if not m:
        return None
    raw = m.group(1)
    return parse_german_date(raw)


def find_amount(text: str) -> str | None:
    """
    Sucht zuerst nach 'Rechnungstotal in CHF inkl. MWST 11.70'
    und, falls nicht gefunden, nach 'Rechnungsbetrag inkl. MWST CHF 11.70'.
    Gibt den Betrag als String, z.B. '11.70', zurück.
    """
    # Variante 1: Zusammenfassung
    m = re.search(
        r"Rechnungstotal in CHF inkl\. MWST\s+([0-9' ]+\.\d{2})",
        text
    )
    if m:
        return m.group(1).strip()

    # Variante 2: eBill-Block
    m = re.search(
        r"Rechnungsbetrag\s+inkl\. MWST\s+CHF\s+([0-9' ]+\.\d{2})",
        text,
        re.S,
    )
    if m:
        return m.group(1).strip()

    # Fallback: letzter Betrag vor 'Betrag' im Zahlteil (sehr grob)
    m = re.search(r"Währung\s+CHF\s+Betrag\s+([0-9' ]+\.\d{2})", text, re.S)
    if m:
        return m.group(1).strip()

    return None


def normalize_amount_for_number(amount_str: str) -> float | None:
    """
    Betrag in float umwandeln.
    z.B. "1'234.50" oder "1'234,50" -> 1234.5
    """
    try:
        s = amount_str.replace("'", "").replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return None


class SwisscomProvider(InvoiceProvider):
    
    REQUIRED_KEYWORDS = ["Swisscom (Schweiz) AG", "Rechnungstotal in CHF inkl. MWST"]
    # ---------------- Basis-Metadaten ----------------

    @property
    def name(self) -> str:
        return "Swisscom"

    @property
    def target_dir(self) -> Path:
        return SWISSCOM_DIR

    @property
    def csv_path(self) -> Path:
        return SWISSCOM_CSV

    @property
    def csv_header(self) -> List[str]:
        return ["Rechnungsdatum", "Betrag", "Datei"]

    # ---------------- Parsing ----------------

    def parse_invoice(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Nutzt deine bestehende Logik:
        - Datum über 'Datum ...'
        - Betrag über 'Rechnungstotal in CHF inkl. MWST' etc.
        """
        date_str = find_datum(text)
        amount_str = find_amount(text)

        if amount_str is None:
            # Zur Sicherheit – wir wollen kein None nach außen geben
            amount_str = "0.00"
            amount_num = 0.0
        else:
            amount_num = normalize_amount_for_number(amount_str) or 0.0

        # Das generische Format für die weitere Verarbeitung:
        return {
            "date": date_str or "",
            "amount": amount_num,
            "file": filename,
        }
