#!/usr/bin/env python3
"""
Test script — sends to test_influencers.csv only.
Uses the same logic as send_email.py.
"""

import sys
sys.path.insert(0, ".")

# Override CSV file before importing main module
import send_email
send_email.CSV_FILE = "test_influencers.csv"

from send_email import main

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
