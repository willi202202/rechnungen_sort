"""
Zentrale Konfiguration für alle Rechnungsskripte.
Lädt config.json und stellt alle relevanten Pfade bereit.

Benutzung in jedem Skript:
    from settings import *
"""

import json
from pathlib import Path
import sys


# ---------------------------------------------------------
# 1. Pfad zum Ordner, in dem settings.py liegt
# ---------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------
# 2. config.json laden
# ---------------------------------------------------------
CONFIG_PATH = SCRIPT_DIR / "config.json"

if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"Konfigurationsdatei fehlt: {CONFIG_PATH}")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)


# ---------------------------------------------------------
# 3. Basis-Ordner für alle Rechnungen
# ---------------------------------------------------------
BASE_DIR = Path(cfg["BASE_DIR"]).expanduser().resolve()


# ---------------------------------------------------------
# 4. Python-Interpreter aus config.json
# ---------------------------------------------------------
PYTHON_EXE = Path(cfg.get("PYTHON_EXE", sys.executable)).resolve()


# ---------------------------------------------------------
# 5. Subfolder der einzelnen Provider
# ---------------------------------------------------------
FOLDERS = cfg["FOLDERS"]

SWISSCOM_DIR = BASE_DIR / FOLDERS["swisscom"]
SWISSCARD_DIR = BASE_DIR / FOLDERS["swisscard"]
SZKB_DIR = BASE_DIR / FOLDERS["szkb_privatkonto"]
STROM_DIR = BASE_DIR / FOLDERS["strom"]

# CSV-Dateien pro Kategorie
SWISSCOM_CSV      = SWISSCOM_DIR / "swisscom.csv"
SWISSCARD_CSV     = SWISSCARD_DIR / "swisscard.csv"
SZKB_CSV          = SZKB_DIR / "szkb_privatkonto.csv"
STROM_CSV         = STROM_DIR / "strom.csv"
STROM_VERIFIED_CSV = STROM_DIR / "strom_verified.csv"


# Ordner automatisch erstellen, wenn sie fehlen
for p in [BASE_DIR, SWISSCOM_DIR, SWISSCARD_DIR, SZKB_DIR, STROM_DIR]:
    p.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# 6. Debug-Info (optional)
# ---------------------------------------------------------
if __name__ == "__main__":
    print("SCRIPT_DIR      =", SCRIPT_DIR)
    print("BASE_DIR        =", BASE_DIR)
    print("PYTHON_EXE      =", PYTHON_EXE)
    print("SWISSCOM_DIR    =", SWISSCOM_DIR)
    print("SWISSCARD_DIR   =", SWISSCARD_DIR)
    print("SZKB_DIR        =", SZKB_DIR)
    print("STROM_DIR       =", STROM_DIR)
    print("SWISSCOM_CSV    =", SWISSCOM_CSV)
    print("SWISSCARD_CSV   =", SWISSCARD_CSV)
    print("SZKB_CSV        =", SZKB_CSV)    
    print("STROM_CSV       =", STROM_CSV)
    print("STROM_VERIFIED_CSV =", STROM_VERIFIED_CSV)
    