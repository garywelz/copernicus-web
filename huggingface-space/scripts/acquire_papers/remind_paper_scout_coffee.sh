#!/bin/bash
# 5-minute reminder before Daily Paper Scout (e.g. cron at 10:10 when run is 10:15 America/New_York)
# Shows a Windows message box from WSL; falls back to notify-send or a log line.

set -e
BASE_DIR="${BASE_DIR:-/home/gdubs/copernicus-web-public/huggingface-space}"
LOG="${BASE_DIR}/paper_acquisition_logs/daily_scout/reminder_coffee.log"
mkdir -p "$(dirname "$LOG")"
TS="$(date -Iseconds)"
MSG="Copernicus Daily Paper Scout runs in about 5 minutes. Good time for a short break (coffee)."

if command -v powershell.exe >/dev/null 2>&1; then
  if powershell.exe -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('${MSG}','Daily Paper Scout','OK','Info')" 2>/dev/null; then
    echo "[$TS] Reminder: Windows message box" >> "$LOG"
    exit 0
  fi
fi
if command -v notify-send >/dev/null 2>&1; then
  notify-send "Daily Paper Scout" "$MSG" -u normal -t 60000
  echo "[$TS] Reminder: notify-send" >> "$LOG"
  exit 0
fi
echo "[$TS] $MSG" | tee -a "$LOG"
exit 0
