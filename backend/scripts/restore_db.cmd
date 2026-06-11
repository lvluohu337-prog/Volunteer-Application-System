@echo off
setlocal
if "%~1"=="" (
  echo Usage: restore_db.cmd path\to\backup.sql
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0restore_db.ps1" -BackupFile "%~1"
