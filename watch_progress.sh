#!/bin/bash
# Live progress monitor - run this to watch scraping progress

while true; do
    clear
    echo "========================================="
    echo "IBDB SCRAPING PROGRESS - Live Monitor"
    echo "========================================="
    echo ""
    python3 check_progress.py
    echo ""
    echo "Press Ctrl+C to stop monitoring"
    echo "Refreshing in 10 seconds..."
    sleep 10
done
