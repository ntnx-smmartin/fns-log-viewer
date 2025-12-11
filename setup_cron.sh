#!/bin/bash
# Setup script for automated log pruning via cron
# This script helps set up a cron job to run the log pruning script daily

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRUNE_SCRIPT="$SCRIPT_DIR/prune_logs.py"
CRON_LOG="/var/log/fns-log-pruner-cron.log"

# Check if prune_logs.py exists
if [ ! -f "$PRUNE_SCRIPT" ]; then
    echo "Error: prune_logs.py not found at $PRUNE_SCRIPT"
    exit 1
fi

# Make the script executable
chmod +x "$PRUNE_SCRIPT"

# Determine Python path (use the virtual environment if it exists)
if [ -f "$SCRIPT_DIR/bin/python3" ]; then
    PYTHON_PATH="$SCRIPT_DIR/bin/python3"
    echo "Using virtual environment Python: $PYTHON_PATH"
else
    PYTHON_PATH=$(which python3)
    echo "Using system Python: $PYTHON_PATH"
fi

# Create cron entry (runs daily at 2:00 AM)
CRON_ENTRY="0 2 * * * $PYTHON_PATH $PRUNE_SCRIPT >> $CRON_LOG 2>&1"

echo ""
echo "Cron job configuration:"
echo "======================"
echo "Schedule: Daily at 2:00 AM"
echo "Command: $PYTHON_PATH $PRUNE_SCRIPT"
echo "Log file: $CRON_LOG"
echo ""
echo "To add this cron job, run:"
echo "  crontab -e"
echo ""
echo "Then add this line:"
echo "  $CRON_ENTRY"
echo ""
echo "Or run this command to add it automatically:"
echo "  (crontab -l 2>/dev/null; echo \"$CRON_ENTRY\") | crontab -"
echo ""
read -p "Do you want to add this cron job now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "Cron job added successfully!"
    echo "View current crontab with: crontab -l"
else
    echo "Cron job not added. You can add it manually later."
fi

