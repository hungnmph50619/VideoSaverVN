@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Desktop-Shortcut.ps1"
if errorlevel 1 (
  echo Could not create Desktop shortcut.
  pause
)
