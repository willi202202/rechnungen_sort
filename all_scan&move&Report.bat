@echo off
REM ==============================
REM  Jahresreport-Generator
REM  Erzeugt Swisscom und Swisscard PDFs
REM ==============================

set PYTHON_EXE=python
set SCRIPT_PATH=D:\Projekte_GITHub\rechnungen_sort
set YEAR=2025

echo === Swisscom Report %YEAR% ===
%PYTHON_EXE% "%SCRIPT_PATH:"=%\scan&move_swisscom.py"
%PYTHON_EXE% "%SCRIPT_PATH:"=%\yearly_report.py" --csv "D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage\swisscom\swisscom.csv" --label Swisscom --year %YEAR%
pause

echo.
echo === Swisscard Report %YEAR% ===
%PYTHON_EXE% "%SCRIPT_PATH:"=%\scan&move_swisscard.py"
%PYTHON_EXE% "%SCRIPT_PATH:"=%\yearly_report.py" --csv "D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage\swisscard\swisscard.csv" --label Swisscard --year %YEAR%

echo.
echo === SZKB Privatkonto Report %YEAR% ===
%PYTHON_EXE% "%SCRIPT_PATH:"=%\scan&move_szkb_privatkonto.py"
%PYTHON_EXE% "%SCRIPT_PATH:"=%\yearly_report.py" --csv "D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage\szkb_privatkonto\szkb_privatkonto.csv" --label SZKB_Privatkonto --year %YEAR%

echo.
echo Fertig! PDF-Dateien sollten nun in den jeweiligen Ordnern liegen.
