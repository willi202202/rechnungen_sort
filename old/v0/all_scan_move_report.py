#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

# Zentrale Settings
from settings import (
    SCRIPT_DIR,
    BASE_DIR,
    PYTHON_EXE,
    SWISSCOM_CSV,
    SWISSCARD_CSV,
    SZKB_CSV,
    STROM_CSV,
    STROM_VERIFIED_CSV,
    STROM_DIR,
)


def main():
    parser = argparse.ArgumentParser(description="Einfacher Rechnungsreport-Runner")
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()
    year = args.year

    print("\n===============================================")
    print(f"Jahresreport-Generator – Jahr {year}")
    print("SCRIPT_DIR:", SCRIPT_DIR)
    print("BASE_DIR:  ", BASE_DIR)
    print("PYTHON_EXE:", PYTHON_EXE)
    print("===============================================\n")

    # Python-Exe als String
    py = str(PYTHON_EXE)

    # ---------------------------------------------------------
    # Swisscom
    # ---------------------------------------------------------
    subprocess.check_call([py, str(SCRIPT_DIR / "scan_move_swisscom.py")])
    subprocess.check_call([
        py, str(SCRIPT_DIR / "yearly_report.py"),
        "--csv", str(SWISSCOM_CSV),
        "--label", "Swisscom",
        "--year", str(year),
    ])

    # ---------------------------------------------------------
    # Swisscard
    # ---------------------------------------------------------
    subprocess.check_call([py, str(SCRIPT_DIR / "scan_move_swisscard.py")])
    subprocess.check_call([
        py, str(SCRIPT_DIR / "yearly_report.py"),
        "--csv", str(SWISSCARD_CSV),
        "--label", "Swisscard",
        "--year", str(year),
    ])

    # ---------------------------------------------------------
    # SZKB Privatkonto
    # ---------------------------------------------------------
    subprocess.check_call([py, str(SCRIPT_DIR / "scan_move_szkb_privatkonto.py")])
    subprocess.check_call([
        py, str(SCRIPT_DIR / "yearly_report.py"),
        "--csv", str(SZKB_CSV),
        "--label", "SZKB_Privatkonto",
        "--year", str(year),
    ])

    """

    # ---------------------------------------------------------
    # Strom
    # ---------------------------------------------------------
    subprocess.check_call([py, str(SCRIPT_DIR / "scan_move_strom.py")])
    subprocess.check_call([
        py, str(SCRIPT_DIR / "strom_table_verify.py"),
        "--csv", str(STROM_CSV),
        "--out", str(STROM_VERIFIED_CSV),
    ])
    subprocess.check_call([
        py, str(SCRIPT_DIR / "strom_report_per_object.py"),
        "--csv", str(STROM_VERIFIED_CSV),
        "--outdir", str(STROM_DIR),
    ])
    """

if __name__ == "__main__":
    main()
