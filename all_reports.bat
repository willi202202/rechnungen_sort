@echo off
REM =====================================================
REM  Konto-Filter Starter
REM  Extrahiert Buchungen für eine bestimmte Gegenpartei
REM =====================================================

set PYTHON_EXE=python
set SCRIPT_PATH=%~dp0konto_filter_by_keyword.py

REM ---- Parameter ----
set PAYEE="Agrisano Krankenkasse AG"
set OUTDIR="D:\Projekte_OneDrive\OneDrive\Privat\Zur_Ablage\reports"

echo ============================================
echo   Starte Konto-Filter für %PAYEE%
echo   Ausgabeordner: %OUTDIR%
echo ============================================
echo.

REM %PYTHON_EXE% "%SCRIPT_PATH%" --payee "Agrisano Krankenkasse AG" --outdir %OUTDIR%
REM %PYTHON_EXE% "%SCRIPT_PATH%" --payee "Goutoulli Tyler Santiago M." --outdir %OUTDIR%
REM %PYTHON_EXE% "%SCRIPT_PATH%" --payee "Ost - Ostschweizer Fachhochschule" --outdir %OUTDIR%
REM %PYTHON_EXE% "%SCRIPT_PATH%" --payee "DEP Datamanagement GmbH" --outdir %OUTDIR%
%PYTHON_EXE% "%SCRIPT_PATH%" --payee "BVK Personalvorsorge des Kantons" --outdir %OUTDIR%

echo.
echo Fertig! CSV und PDF sollten im Ausgabeordner liegen.
