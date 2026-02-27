#!/usr/bin/env python3
"""
Send personalized marketing emails to all influencers in influencers.csv.
Run fetch_names.py first to populate the 'name' column.
"""

import csv
import smtplib
import imaplib
import ssl
import time
import os
import sys
import re
import unicodedata
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtpout.secureserver.net")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

CSV_FILE = "influencers.csv"
EMAIL_BODY_FILE = "email_body.txt"


def clean_name(raw_name, fallback=""):
    """Extract just the first name from a messy IG display name."""
    if not raw_name or not raw_name.strip():
        return fallback

    name = raw_name.strip()

    # Remove emojis and flag characters
    emoji_re = re.compile(
        "[\U0001F1E0-\U0001F1FF"   # country flags
        "\U0001F300-\U0001F9FF"    # misc symbols, emoticons
        "\u2600-\u27BF"            # misc symbols & dingbats
        "\u25A0-\u25FF"            # geometric shapes (▫◽)
        "\uFE0F\u200D]",           # variation selectors, zero-width joiner
        flags=re.UNICODE
    )
    name = emoji_re.sub("", name).strip()

    # Split on title separators and take the first part
    name = re.split(r"\s*[|•·▫◽/]\s*|\s+[-]\s+", name)[0].strip()

    # Remove leftover trailing symbols
    name = name.rstrip(".,!?♡✨✺ ")

    # Take just the first word (first name)
    words = [w for w in name.split() if w]
    if not words:
        return fallback

    first_name = unicodedata.normalize("NFKC", words[0])
    return first_name.capitalize()


def load_email_body():
    with open(EMAIL_BODY_FILE, "r", encoding="utf-8") as f:
        return f.read()


def load_influencers():
    influencers = []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            handle = row["ig_handle"].strip().lstrip("@")
            email = row["email"].strip()
            name = clean_name(row.get("name", ""), fallback="there")
            sent_date = row.get("sent_date", "").strip()
            if handle and email:
                influencers.append({"ig_handle": handle, "email": email, "name": name, "sent_date": sent_date})
    return influencers


def mark_sent(ig_handle, date_str):
    """Write the sent date back to the CSV for a given handle."""
    rows = []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["ig_handle"].strip().lstrip("@") == ig_handle and not row.get("sent_date", "").strip():
                row["sent_date"] = date_str
            rows.append(row)
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def to_html(text):
    import html as html_module

    PARA_STYLE  = 'style="margin:0 0 14px 0;font-size:15px;line-height:1.6;color:#222;"'
    LI_STYLE    = 'style="margin-bottom:7px;font-size:15px;line-height:1.6;color:#222;"'
    UL_STYLE    = 'style="margin:0 0 28px 20px;padding-left:0;"'
    HDG_STYLE   = ('style="margin:20px 0 8px 0;font-size:15px;font-weight:700;'
                   'color:#111;"')

    def fmt(line):
        escaped = html_module.escape(line)
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)

    def is_solo_heading(stripped):
        """True when the entire line is wrapped in **...**"""
        return bool(re.match(r"^\*\*[^*]+\*\*$", stripped))

    blocks = []
    current_para = []
    current_bullets = []

    def flush_para():
        if current_para:
            blocks.append(f'<p {PARA_STYLE}>' + "<br>".join(current_para) + "</p>")
            current_para.clear()

    def flush_bullets():
        if current_bullets:
            items = "".join(f"<li {LI_STYLE}>{item}</li>" for item in current_bullets)
            blocks.append(f"<ul {UL_STYLE}>{items}</ul>")
            current_bullets.clear()

    for line in text.split("\n"):
        stripped = line.strip()
        if line.startswith("- "):
            flush_para()
            current_bullets.append(fmt(line[2:]))
        elif stripped and is_solo_heading(stripped):
            flush_para()
            flush_bullets()
            heading_text = html_module.escape(stripped[2:-2])
            blocks.append(f"<p {HDG_STYLE}>{heading_text}</p>")
        elif stripped:
            flush_bullets()
            current_para.append(fmt(line))
        else:
            flush_para()
            flush_bullets()

    flush_para()
    flush_bullets()

    body_html = "\n".join(blocks)

    signature = """\
<br>
<table cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td>
      <img src="https://viralt.ai/assets/viralt-horizontal-logo-Disq2McJ.png"
           alt="Viralt" width="150" style="display:block;margin-bottom:8px;border:0;">
      <p style="margin:0;font-size:13px;color:#555;">
        <a href="https://viralt.ai/home"
           style="color:#555;text-decoration:none;">Website</a>&nbsp;&nbsp;&nbsp;&nbsp;<a href="https://www.instagram.com/viralt.ai/"
           style="color:#555;text-decoration:none;">Instagram</a>&nbsp;&nbsp;&nbsp;&nbsp;<a href="https://www.linkedin.com/company/viraltai/"
           style="color:#555;text-decoration:none;">LinkedIn</a>&nbsp;&nbsp;&nbsp;&nbsp;<a href="https://x.com/Viralt_AI"
           style="color:#555;text-decoration:none;">X</a>
      </p>
    </td>
  </tr>
</table>"""

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#ffffff;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#ffffff;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;padding:30px 24px;
                      font-family:Arial,sans-serif;font-size:15px;
                      line-height:1.6;color:#222;">
          <tr>
            <td>
{body_html}
<br>
{signature}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_message(sender, recipient_email, subject, plain_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Libin @ Viralt.ai <{sender}>"
    msg["To"] = recipient_email
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(to_html(plain_body), "html", "utf-8"))
    return msg


def send_email(smtp, msg):
    """Sends the email using the modern send_message method."""
    smtp.send_message(msg)


def save_draft(imap, msg):
    """Append message to the Drafts folder via IMAP."""
    for folder in ["Drafts", "Draft", "INBOX.Drafts"]:
        result = imap.append(folder, "\\Draft", None, msg.as_bytes())
        if result[0] == "OK":
            return folder
    raise Exception("Could not find Drafts folder. Tried: Drafts, Draft, INBOX.Drafts")


def main(dry_run=False, draft_mode=False):
    missing = [k for k, v in {
        "SENDER_EMAIL": SENDER_EMAIL,
        "SENDER_PASSWORD": SENDER_PASSWORD,
    }.items() if not v]
    if missing:
        print(f"ERROR: Missing config in .env: {', '.join(missing)}")
        sys.exit(1)

    email_body_template = load_email_body()
    influencers = load_influencers()

    if not influencers:
        print("No influencers found in influencers.csv. Exiting.")
        sys.exit(0)

    print(f"Found {len(influencers)} influencer(s).\n")

    if dry_run:
        print("=== DRY RUN MODE - no emails will be sent ===\n")
    elif draft_mode:
        print("=== DRAFT MODE - emails will be saved to Drafts folder ===\n")

    smtp = None
    imap = None

    try:
        if not dry_run:
            ctx = ssl.create_default_context()
            if draft_mode:
                print("Connecting to IMAP imap.secureserver.net:993...")
                imap = imaplib.IMAP4_SSL("imap.secureserver.net", 993)
                imap.login(SENDER_EMAIL, SENDER_PASSWORD)
                print("IMAP connected.\n")
            else:
                print(f"Connecting to SMTP {SMTP_HOST}:{SMTP_PORT}...")
                smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
                smtp.starttls(context=ctx)
                smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
                print("SMTP connected.\n")

        results = {"done": [], "failed": []}

        for i, inf in enumerate(influencers):
            handle = inf["ig_handle"]
            email = inf["email"]
            name = inf["name"]

            subject = f"Collab Invite: Viralt x @{handle}"
            body = email_body_template.replace("{name}", name)
            sent_date = inf["sent_date"]

            if sent_date:
                print(f"[{i+1}/{len(influencers)}] @{handle} - already sent on {sent_date}, skipping.\n")
                results["done"].append(handle)
                continue

            print(f"[{i+1}/{len(influencers)}] @{handle} -> {email} (name: {name})")

            if dry_run:
                print(f"  Subject: {subject}")
                print(f"  Body preview: {body[:120].strip()}...\n")
                results["done"].append(handle)
            else:
                msg = build_message(SENDER_EMAIL, email, subject, body)
                try:
                    if draft_mode:
                        folder = save_draft(imap, msg)
                        print(f"  Saved to {folder}.\n")
                    else:
                        send_email(smtp, msg)
                        today = date.today().strftime("%Y-%m-%d")
                        mark_sent(handle, today)
                        print(f"  Sent. Date recorded: {today}\n")
                    results["done"].append(handle)
                except Exception as e:
                    print(f"  ERROR: {e}\n")
                    results["failed"].append(handle)

                # Sleep outside the try block to respect rate limits even on failures
                if i < len(influencers) - 1:
                    print("  Waiting 3 minutes before next email...")
                    time.sleep(180)

        action = "Drafted" if draft_mode else "Sent"
        print("=== Campaign Summary ===")
        print(f"{action}: {len(results['done'])}")
        if results["failed"]:
            print(f"Failed: {len(results['failed'])} - {results['failed']}")
        print("Done.")

    finally:
        # Ensures connections are closed even if you keyboard interrupt (Ctrl+C)
        if smtp:
            smtp.quit()
        if imap:
            try:
                imap.logout()
            except Exception:
                pass

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    draft_mode = "--draft" in sys.argv
    main(dry_run=dry_run, draft_mode=draft_mode)