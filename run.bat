@echo off
:: This automatically finds the current directory of the bat file
cd /d "%~dp0"

:: Use pythonw.exe to run without a visible console window
start "" pythonw.exe launchpad.py