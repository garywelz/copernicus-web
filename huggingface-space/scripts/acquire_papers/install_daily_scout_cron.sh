#!/bin/bash
# Install Daily Paper Scout Cron Job
# This script adds a cron job to run the daily scout at 2:00 AM EST (7:00 AM UTC)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR/../.."
CRON_LOG="$BASE_DIR/paper_acquisition_logs/daily_scout/cron.log"
RUN_SCRIPT="$SCRIPT_DIR/run_daily_scout.sh"

# Ensure log directory exists
mkdir -p "$(dirname "$CRON_LOG")"

# Create cron entry
# Time: 7:00 AM UTC = 2:00 AM EST (during standard time)
# For EDT (daylight saving), use 6:00 AM UTC - adjust manually if needed
CRON_ENTRY="0 7 * * * cd $BASE_DIR && $RUN_SCRIPT >> $CRON_LOG 2>&1"

echo "📅 Setting up Daily Paper Scout cron job..."
echo ""
echo "Schedule: Daily at 2:00 AM EST (7:00 AM UTC)"
echo "Script: $RUN_SCRIPT"
echo "Log: $CRON_LOG"
echo ""
echo "Cron entry:"
echo "$CRON_ENTRY"
echo ""

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "run_daily_scout.sh"; then
    echo "⚠️  Cron job for daily_scout already exists!"
    echo ""
    echo "Current crontab:"
    crontab -l | grep "run_daily_scout"
    echo ""
    read -p "Replace existing entry? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove existing entry
        crontab -l 2>/dev/null | grep -v "run_daily_scout.sh" | crontab -
        # Add new entry
        (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
        echo "✅ Cron job updated!"
    else
        echo "❌ Keeping existing cron job. Exiting."
        exit 1
    fi
else
    # Add new entry
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "✅ Cron job installed!"
fi

echo ""
echo "📋 Current crontab:"
crontab -l
echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Notes:"
echo "  - The script runs daily at 2:00 AM EST (7:00 AM UTC)"
echo "  - Logs are saved to: $CRON_LOG"
echo "  - To edit: crontab -e"
echo "  - To remove: crontab -e (then delete the line)"
echo "  - To view: crontab -l"
echo ""
echo "🧪 Test the script manually:"
echo "  $RUN_SCRIPT"
echo ""
