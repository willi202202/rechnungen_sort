#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import re

import pdfplumber

from .base_provider import InvoiceProvider
from settings import SZKB_DIR, SZKB_CSV



# Begriffe rund um Schlusssaldo
SALDO_KEYWORDS = [
    "Schlusssaldo",
]


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    PDF -> reiner Text (alle Seiten).
    """
    chunks: List[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def find_all_dates(text: str) -> List[str]:
    """
    Findet alle Datumsangaben im Format TT.MM.JJJJ.
    """
    return re.findall(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)


def find_period_from_dates(dates: List[str]) -> tuple[str | None, str | None]:
    """
    Bestimme Zeitraum (von, bis) aus allen gefundenen Datumsangaben.
    """
    if not dates:
        return None, None
    dates_sorted = sorted(dates)
    return dates_sorted[0], dates_sorted[-1]


def find_saldo(text: str) -> str | None:
    """
    Sucht nach einer Zeile mit 'Schlusssaldo' (oder allgemein 'Saldo'),
    und extrahiert den Betrag.
    """
    lines: List[str] = []

    for line in text.splitlines():
        if any(k.upper() in line.upper() for k in SALDO_KEYWORDS):
            lines.append(line)

    if not lines:
        # Fallback: irgendwo im Text nach 'Saldo' suchen
        fallback = re.findall(r"(Saldo.*)", text, flags=re.IGNORECASE)
        lines.extend(fallback)

    if not lines:
        return None

    last_line = lines[-1]

    # Betrag herausparsen (CHF optional, Vorzeichen optional)
    m = re.search(r"([+-]?\s*CHF\s*)?([+-]?[0-9' ]+\.\d{2})", last_line)
    if not m:
        return None

    amount_str = m.group(2)
    return amount_str.strip()


def normalize_amount(amount_str: str) -> float | None:
    """
    Betragstring in float umwandeln.
    z.B. "1'234.50" oder "- 1'234,50" -> 1234.5 / -1234.5
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


class SZKBProvider(InvoiceProvider):

    # Keywords zur Erkennung von Kontoauszügen
    REQUIRED_KEYWORDS = ["Schwyzer Kantonalbank", "Privatkonto", "812186-0560"]
    # ---------------- Basis-Metadaten ----------------

    @property
    def name(self) -> str:
        return "SZKB_Privatkonto"

    @property
    def target_dir(self) -> Path:
        return SZKB_DIR

    @property
    def csv_path(self) -> Path:
        return SZKB_CSV

    @property
    def csv_header(self) -> List[str]:
        return ["Von_Datum", "Bis_Datum", "Schlusssaldo", "Datei"]

    # ---------------- Parsing ----------------

    def parse_invoice(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Liefert:
            - von_datum / bis_datum (Zeitraum)
            - saldo_num (= Schlusssaldo_num)
            - file
            - date: für generische Verwendung = bis_datum
            - amount: für generische Verwendung = saldo_num
        """

        dates = find_all_dates(text)
        von, bis = find_period_from_dates(dates)

        saldo_str = find_saldo(text)
        if saldo_str:
            saldo_num = normalize_amount(saldo_str) or 0.0
        else:
            saldo_num = 0.0

        # 'date' und 'amount' für generische Verarbeitung (z.B. YearlyReport)
        # nehmen wir als Bis_Datum / Schlusssaldo_num
        return {
            "from_date": von or "",
            "to_date": bis or "",
            "saldo": saldo_num,
            "file": filename,
        }
