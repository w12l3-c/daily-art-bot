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

# Function to restore our specific stash
restore_our_stash() {
    if [ "$STASHED" = true ]; then
        echo "$(date): Restoring our stashed changes..."
        # Find and pop only our specific stash
        STASH_ID=$(git stash list | grep "$STASH_NAME" | head -n1 | cut -d: -f1)
        if [ -n "$STASH_ID" ]; then
            if ! git stash pop "$STASH_ID"; then
                echo "$(date): Warning: Could not restore our stashed changes, continuing anyway..."
            fi
        else
            echo "$(date): Warning: Could not find our stash '$STASH_NAME', continuing anyway..."
        fi
    fi
}

# Stash any existing changes temporarily
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "$(date): Stashing existing changes..."
    STASH_NAME="auto_backup_$(date +%s)"
    git stash push -m "$STASH_NAME"
    STASHED=true
else
    STASHED=false
fi

# Pull latest changes first to avoid conflicts
echo "$(date): Pulling latest changes..."
if ! git pull origin main; then
    echo "$(date): Failed to pull latest changes"
    restore_our_stash
    exit 1
fi

# Restore our specific stash if we created one
restore_our_stash

# Add backup.json to git
git add backup.json wcw.json

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
    echo "$(date): Successfully pushed backup.json and wcw.json"
else
    echo "$(date): Failed to push backup.json and wcw.json"
    exit 1
fi
