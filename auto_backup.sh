#!/bin/bash

# auto_backup.sh
# Automatically commits and pushes backup.json to git
# Run this script with cron on your Raspberry Pi (e.g., daily at 12:45 AM)

# Change to the bot directory
cd "$(dirname "$0")"

# Check if backup.json exists
if [ ! -f "backup.json" ]; then
    echo "$(date): backup.json not found, skipping backup"
    exit 0
fi

# Pull latest changes first to avoid conflicts
echo "$(date): Pulling latest changes..."
if ! git pull --rebase origin ; then
    echo "$(date): Failed to pull latest changes"
    exit 1
fi

# Add backup.json to git
git add backup.json

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "$(date): No changes to backup.json, skipping commit"
    exit 0
fi

# Commit with timestamp
COMMIT_MSG="Auto-backup: $(date '+%Y-%m-%d %H:%M:%S')"
git commit -m "$COMMIT_MSG"

# Push to remote
if git push origin main; then
    echo "$(date): Successfully pushed backup.json"
else
    echo "$(date): Failed to push backup.json"
    exit 1
fi
