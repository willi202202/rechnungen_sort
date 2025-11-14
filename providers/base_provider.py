#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List


class InvoiceProvider(ABC):
    """
    Abstrakte Basis für alle Rechnungstypen (Swisscom, Swisscard, SZKB, Strom, ...).
    """

    #: Alle diese Keywords MUESSEN im Text vorkommen (case-insensitive).
    REQUIRED_KEYWORDS: List[str] = []

    @property
    @abstractmethod
    def name(self) -> str:
        """Lesbarer Name, z.B. 'Swisscom'."""
        ...

    def matches(self, text: str) -> bool:
        """
        Standard-Implementierung:
        - Alle REQUIRED_KEYWORDS müssen vorkommen
        """
        if not self.REQUIRED_KEYWORDS:
            return False

        upper = text.upper().replace("\xa0", " ")

        # alle required Keywords müssen drin sein
        for kw in self.REQUIRED_KEYWORDS:
            if kw.upper() not in upper:
                return False
        return True

    @abstractmethod
    def parse_invoice(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Extrahiert die relevanten Daten aus der Rechnung.

        Muss mindestens zurückgeben:
            {
                "date": "24.10.2025",   # als String TT.MM.JJJJ
                "amount": 39.90,        # float
                "raw_amount": "39.90",  # originaler String
                "file": "foo.pdf"       # Dateiname
            }

        Weitere Felder (z.B. 'art' bei Swisscard) sind erlaubt.
        """
        ...

    @property
    @abstractmethod
    def target_dir(self) -> Path:
        """Zielordner für die PDFs dieses Providers."""
        ...

    @property
    @abstractmethod
    def csv_path(self) -> Path:
        """Pfad zur CSV-Datei dieses Providers."""
        ...

    @property
    @abstractmethod
    def csv_header(self) -> List[str]:
        """
        Kopfzeile der CSV-Datei, z.B.
        ['Rechnungsdatum', 'Betrag_roh', 'Betrag_num', 'Datei']
        """
        ...
