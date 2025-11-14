#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import re

import pdfplumber

from .base_provider import InvoiceProvider
from settings import SWISSCARD_DIR, SWISSCARD_CSV

def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    PDF -> reiner Text (alle Seiten).
    """
    chunks: List[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def find_rechnungsdatum(text: str) -> str | None:
    """
    Sucht explizit nach 'Rechnungsdatum 24.10.2025'.
    Fallback: erstes Datum im Format TT.MM.JJJJ.
    """
    m = re.search(r"Rechnungsdatum\s+(\d{2}\.\d{2}\.\d{4})", text)
    if m:
        return m.group(1)

    # Fallback: erstes Datum irgendwo
    m = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
    if m:
        return m.group(1)

    return None


def find_betraege_block(text: str) -> list[str] | None:
    """
    Sucht den Block mit den 5 CHF-Beträgen nach 'Mindestzahlung'
    und gibt eine Liste mit 5 Strings zurück:
    [Saldo letzte Rechnung, Ihre Zahlungen, Total neue Transaktionen,
     Neuer Saldo, Mindestzahlung]
    """
    m = re.search(
        r"Mindestzahlung.*?(CHF\s*[0-9' .]+\d{2}(?:\s+CHF\s*[0-9' .]+\d{2}){4})",
        text,
        re.S,
    )
    if not m:
        return None

    line = m.group(1)
    amounts = re.findall(r"CHF\s*([0-9' .]+\d{2})", line)
    if len(amounts) != 5:
        return None
    return amounts


def normalize_amount(amount_str: str) -> float | None:
    """
    Betrag in float umwandeln.
    z.B. "1'234.50" oder "1 234,50" -> 1234.5
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


class SwisscardProvider(InvoiceProvider):

    # ---------------- Basis-Metadaten ----------------
    REQUIRED_KEYWORDS = ["Swisscard AECS GmbH", "Cashback Cards", "1001 0765 294"]

    @property
    def name(self) -> str:
        return "Swisscard"

    @property
    def target_dir(self) -> Path:
        return SWISSCARD_DIR

    @property
    def csv_path(self) -> Path:
        return SWISSCARD_CSV

    @property
    def csv_header(self) -> List[str]:
        # Schlanke Struktur: kein Betrag_roh
        # Rechnungsdatum;Betrag_num;Art;Datei
        return ["Rechnungsdatum", "Betrag", "Datei"]

    # ---------------- Parsing ----------------

    def parse_invoice(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Nutzt deine bisherige Swisscard-Parsinglogik:
        - Rechnungsdatum
        - Betragsblock (Neuer Saldo & Mindestzahlung)
        - Flag USE_MINDESTZAHLUNG entscheidet, welcher Betrag genommen wird.
        """

        rechnungsdatum = find_rechnungsdatum(text) or ""

        betraege = find_betraege_block(text)
        if not betraege:
            # Wenn wir hier landen, ist was mit dem PDF komisch,
            # wir liefern dann eine "leere" Rechnung zurück.
            return {
                "date": rechnungsdatum,
                "amount": 0.0,
                "file": filename
            }

        saldo_letzte, zahlungen, total_trans, neuer_saldo, mindest = betraege

        amt = normalize_amount(neuer_saldo) or 0.0

        return {
            "date": rechnungsdatum,
            "amount": amt,
            "file": filename
        }
