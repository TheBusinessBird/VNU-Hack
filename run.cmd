@echo off
REM Dublu-click pentru a porni proiectul (ocoleste restrictia de executie a scripturilor PowerShell).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
if errorlevel 1 pause
