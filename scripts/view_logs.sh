#!/bin/bash
# Log viewer script

LOG_FILE=${1:-"logs/django.log"}

if [ ! -f "$LOG_FILE" ]; then
    echo "Log file not found: $LOG_FILE"
    exit 1
fi

# View logs with colors
tail -f $LOG_FILE | grep --color=always -E "ERROR|WARNING|INFO|DEBUG|$"