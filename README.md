# Viralt.ai — Influencer Email Campaign

Automated outreach tool that fetches Instagram display names and sends personalized HTML emails to a list of influencers via GoDaddy SMTP.

---

## Project Structure

```
.
├── fetch_names.py      # Step 1: scrape Instagram display names into the CSV
├── send_email.py       # Step 2: send (or draft) personalized emails
├── email_body.txt      # Email body template — uses {name} placeholder
├── influencers.csv     # Input data: ig_handle, email, name, sent_date
├── .env                # Credentials (SMTP + sender info) — never commit this
├── .env.example        # Template for .env
├── requirements.txt    # Python dependencies
└── ig_session.json     # Saved Playwright Instagram session (auto-generated)
```

---

## Prerequisites

- Python 3.10 or later
- A GoDaddy email account (or any SMTP provider)
- An Instagram account for name fetching

Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Setup

**1. Configure credentials**

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```
SMTP_HOST=smtpout.secureserver.net
SMTP_PORT=465
SENDER_EMAIL=you@yourdomain.com
SENDER_PASSWORD=your_password
```

**2. Prepare the influencer list**

Create or edit `influencers.csv` with at minimum these columns:

```csv
ig_handle,email,name,sent_date
janedoe,jane@example.com,,
```

- `name` and `sent_date` can be left blank — they are filled in automatically.
- Any row with a `sent_date` already set will be skipped when sending.

**3. Write the email body**

Edit `email_body.txt`. Use `{name}` where you want the recipient's first name inserted. Formatting supported in the template:

- `**bold text**` — rendered as bold in the HTML email
- `- bullet item` — rendered as an indented list
- A line that is entirely `**bold**` (nothing else on the line) becomes a section heading

---

## Workflow

### Step 1 — Fetch Instagram names

```bash
python fetch_names.py
```

A browser window will open. Log in to Instagram once; the session is saved to `ig_session.json` for future runs. The script visits each influencer's profile, extracts the display name, cleans it to a first name, and writes it back to `influencers.csv`.

Already-named rows are skipped automatically.

### Step 2 — Send emails

**Dry run** (preview subjects and body snippets, no emails sent):

```bash
python send_email.py --dry-run
```

**Draft mode** (save to your Drafts folder via IMAP so you can review before sending):

```bash
python send_email.py --draft
```

**Live send**:

```bash
python send_email.py
```

Each successfully sent email is stamped with today's date in the `sent_date` column of `influencers.csv`, preventing accidental re-sends. The script waits 3 minutes between emails to stay within typical sending rate limits.

---

## Email Personalization

| Field | Value |
|---|---|
| From | `Libin @ Viralt.ai <libin@viralt.ai>` |
| Subject | `Collab Invite: Viralt x @{ig_handle}` |
| Greeting name | First name from Instagram display name, or the handle as fallback |

The email is sent as both `text/plain` and `text/html` (multipart/alternative) so it renders correctly across all mail clients.

---

## Notes

- Never commit `.env` or `ig_session.json` to version control.
- If Instagram requires 2FA during `fetch_names.py`, complete it manually in the opened browser window — the script waits up to 3 minutes.
- To re-send to someone already marked as sent, clear their `sent_date` cell in the CSV.
