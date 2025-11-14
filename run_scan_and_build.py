#!/usr/bin/env python3
from __future__ import annotations

"""
Orchestrator:
1. Neue PDFs im BASE_DIR einsortieren (scan_sort_all)
2. CSVs für Swisscom, Swisscard, SZKB neu aufbauen
"""

from build import (
    build_swisscom_csv,
    build_swisscard_csv,
    build_szkb_csv,
)
import sort_all


def main():
    print("=====================================")
    print("   Schritt 1: PDFs scannen & sortieren")
    print("=====================================\n")

    sort_all.main()

    print("\n=====================================")
    print("   Schritt 2: CSVs neu erzeugen")
    print("=====================================\n")

    build_swisscom_csv.main()
    build_swisscard_csv.main()
    build_szkb_csv.main()

    print("\n=====================================")
    print("   Fertig: Sortierung + CSV-Build")
    print("=====================================\n")


if __name__ == "__main__":
    main()

