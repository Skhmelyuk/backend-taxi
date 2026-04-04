#!/bin/bash
# Log rotation script

LOG_DIR="logs"
ARCHIVE_DIR="logs/archive"
DAYS_TO_KEEP=30

# Create archive directory
mkdir -p $ARCHIVE_DIR

# Find and compress old logs
find $LOG_DIR -name "*.log" -type f -mtime +7 -exec gzip {} \;

# Move compressed logs to archive
find $LOG_DIR -name "*.log.gz" -type f -exec mv {} $ARCHIVE_DIR/ \;

# Delete old archives
find $ARCHIVE_DIR -name "*.log.gz" -type f -mtime +$DAYS_TO_KEEP -delete

echo "Log rotation completed"