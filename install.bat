@echo off
title Discord Bot Installation

:: --- Schritt 1: Prüfen ob Python installiert ist ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python ist nicht installiert. Bitte lade es von https://www.python.org/downloads/ herunter.
    pause
    exit /b
)

:: --- Schritt 2: Pakete installieren ---
echo Installiere benötigte Pakete...
pip install --upgrade pip
pip install discord.py pytz

:: --- Schritt 3: JSON-Datei erstellen, falls sie fehlt ---
if not exist credits.json (
    echo {} > credits.json
    echo credits.json erstellt
)

:: --- Schritt 4: Bot starten ---
echo Starte Bot...
python bot.py

pause