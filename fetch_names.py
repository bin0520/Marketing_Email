#!/usr/bin/env python3
"""
Fetch Instagram display names for all influencers in influencers.csv.
Saves results back to the CSV as a new 'name' column.
Run this before send_campaign.py.
"""

import csv
import os
import re
import time
import unicodedata
from playwright.sync_api import sync_playwright


def clean_name(raw_name, fallback=""):
    """Extract just the first name from a messy IG display name."""
    if not raw_name or not raw_name.strip():
        return fallback

    name = raw_name.strip()

    emoji_re = re.compile(
        "[\U0001F1E0-\U0001F1FF"
        "\U0001F300-\U0001F9FF"
        "\u2600-\u27BF"
        "\u25A0-\u25FF"
        "\uFE0F\u200D]",
        flags=re.UNICODE
    )
    name = emoji_re.sub("", name).strip()
    name = re.split(r"\s*[|•·▫◽/]\s*|\s+[-—]\s+", name)[0].strip()
    name = name.rstrip(".,!?♡✨✺ ")

    words = [w for w in name.split() if w]
    if not words:
        return fallback

    first_name = unicodedata.normalize("NFKC", words[0])
    return first_name.capitalize()

CSV_FILE = "influencers.csv"
SESSION_FILE = "ig_session.json"


def load_influencers():
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_influencers(rows):
    fieldnames = ["ig_handle", "email", "name"]
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def ensure_ig_session(playwright):
    browser = playwright.chromium.launch(headless=False)

    if os.path.exists(SESSION_FILE):
        context = browser.new_context(storage_state=SESSION_FILE)
        page = context.new_page()
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
        if "/accounts/login/" not in page.url:
            print("Instagram session loaded from saved file.\n")
            page.close()
            return browser, context
        print("Saved session expired — need to log in again.")
        page.close()
        context.close()

    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.instagram.com/accounts/login/")
    print("\nA browser window has opened. Please log in to Instagram.")
    print("The script will continue automatically once you are logged in...\n")
    page.wait_for_url(
        re.compile(r"instagram\.com(?!/accounts/login)"),
        timeout=180000
    )
    context.storage_state(path=SESSION_FILE)
    print(f"Login successful! Session saved to {SESSION_FILE}\n")
    page.close()
    return browser, context


def get_ig_name(context, ig_handle):
    page = context.new_page()
    try:
        page.goto(
            f"https://www.instagram.com/{ig_handle}/",
            wait_until="domcontentloaded",
            timeout=20000
        )
        og_title = page.get_attribute('meta[property="og:title"]', "content")
        if og_title:
            match = re.match(r"^(.+?)\s*\(@", og_title)
            if match:
                return match.group(1).strip()
        title = page.title()
        match = re.match(r"^(.+?)\s*\(@", title)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"  WARNING: Could not fetch name for @{ig_handle}: {e}")
    finally:
        page.close()
    return ""


def main():
    rows = load_influencers()
    print(f"Found {len(rows)} influencer(s) in CSV.\n")

    with sync_playwright() as p:
        browser, context = ensure_ig_session(p)

        for i, row in enumerate(rows):
            handle = row["ig_handle"].strip().lstrip("@")
            existing_name = row.get("name", "").strip()

            if existing_name:
                print(f"[{i+1}/{len(rows)}] @{handle} — already has name: {existing_name}, skipping.")
                continue

            print(f"[{i+1}/{len(rows)}] Fetching name for @{handle}...")
            name = get_ig_name(context, handle)

            if name:
                print(f"  Found: {name}")
            else:
                print(f"  Not found. Will use handle as fallback when sending.")

            row["name"] = clean_name(name, fallback=handle)

            # Save after each fetch so progress isn't lost if script is interrupted
            save_influencers(rows)

            if i < len(rows) - 1:
                time.sleep(2)

        context.close()
        browser.close()

    print("\nAll done! Names saved to influencers.csv.")
    print("Review the CSV, then run send_campaign.py to send emails.")


if __name__ == "__main__":
    main()
