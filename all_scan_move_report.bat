@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==============================
REM  Jahresreport-Generator
REM  Erzeugt Swisscom, Swisscard, SZKB & Strom Reports
REM ==============================
goto :main

REM ========= Helper zum Ausfuehren mit Fehlercheck =========
REM Aufruf: call :run "Titel" <command> [args...]
REM Bricht bei Fehler ab.
:run
set "TITLE=%~1"
shift
echo --- %TITLE% ---
%*
if errorlevel 1 (
  echo [FEHLER] %TITLE% fehlgeschlagen. Abbruch.
  exit /b 1
)
echo.
goto :eof
REM ==============================

:main
REM ---- Python finden / setzen ----
REM set "PYTHON_EXE=python"
set "PYTHON_EXE=C:\Users\Roman\AppData\Local\Programs\Python\Python312\python.exe"
where %PYTHON_EXE% >nul 2>&1
if errorlevel 1 (
  echo [FEHLER] Python nicht gefunden. Bitte PATH anpassen oder PYTHON_EXE setzen.
  exit /b 1
)

REM ---- Skript-Ordner (Repo) ----
REM Passe das an, falls noetig:
set "SCRIPT_DIR=D:\Projekte_GITHub\rechnungen_sort"

REM ---- Datenbasis ----
set "BASE=D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage"
set "SCOM=%BASE%\swisscom\swisscom.csv"
set "SCARD=%BASE%\swisscard\swisscard.csv"
set "SZKB=%BASE%\szkb_privatkonto\szkb_privatkonto.csv"
set "STROM=%BASE%\strom\strom.csv"
set "STROM_VER=%BASE%\strom\strom_verified.csv"
set "STROM_OUTDIR=%BASE%\strom"

REM ---- Jahr (optional als 1. Argument) ----
if "%~1"=="" (
  set "YEAR=2025"
) else (
  set "YEAR=%~1"
)

echo ===============================================
echo  Jahresreport-Generator  --  Jahr: %YEAR%
echo  Skripte: "%SCRIPT_DIR%"
echo  Datenbasis: "%BASE%"
echo ===============================================
echo.

echo Starte Verarbeitung...
REM ================= Swisscom =================
if not exist "%PYTHON_EXE%" echo [HINWEIS] Python fehlt: "%PYTHON_EXE%"
if not exist "%SCRIPT_DIR%\scan_move_swisscom.py" echo [HINWEIS] Datei fehlt: "%SCRIPT_DIR%\scan_move_swisscom.py"
call :run "Swisscom: Scan and Move" "%PYTHON_EXE%" "%SCRIPT_DIR%\scan_move_swisscom.py"
call :run "Swisscom: Jahresreport %YEAR%" "%PYTHON_EXE%" "%SCRIPT_DIR%\yearly_report.py" --csv "%SCOM" --label Swisscom --year %YEAR%

REM ================= Swisscard =================
call :run "Swisscard: Scan and Move" "%PYTHON_EXE%" "%SCRIPT_DIR%\scan_move_swisscard.py"
call :run "Swisscard: Jahresreport %YEAR%" "%PYTHON_EXE%" "%SCRIPT_DIR%\yearly_report.py" --csv "%SCARD" --label Swisscard --year %YEAR%

REM ================= SZKB Privatkonto =================
call :run "SZKB Privatkonto: Scan and Move" "%PYTHON_EXE%" "%SCRIPT_DIR%\scan_move_szkb_privatkonto.py"
call :run "SZKB Privatkonto: Jahresreport %YEAR%" "%PYTHON_EXE%" "%SCRIPT_DIR%\yearly_report.py" --csv "%SZKB" --label SZKB_Privatkonto --year %YEAR%

REM ================= Strom =================
call :run "Strom: Scan and Move" "%PYTHON_EXE%" "%SCRIPT_DIR%\scan_move_strom.py"
call :run "Strom: Verify Tabelle" "%PYTHON_EXE%" "%SCRIPT_DIR%\strom_table_verify.py" --csv "%STROM" --out "%STROM_VER%"
call :run "Strom: Report je Objekt" "%PYTHON_EXE%" "%SCRIPT_DIR%\strom_report_per_object.py" --csv "%STROM_VER%" --outdir "%STROM_OUTDIR%"

echo -----------------------------------------------
echo Fertig! PDF/CSV liegen in den jeweiligen Ordnern.
echo Jahr: %YEAR%
echo -----------------------------------------------
endlocal