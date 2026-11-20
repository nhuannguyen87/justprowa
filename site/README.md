# Just Professional Services – website

FastAPI website for JPS (Perth handyman, carpentry, renos and maintenance plans), with a staff admin area.

## Run it on your Mac

You need **Python 3.10 or newer** (`python3 --version`). If it's missing: `brew install python` or download it from python.org.

```bash
cd ~/Documents/Benoit/business/JPS_website/site
./run.sh
```

The first run:
1. creates a virtual environment (`.venv`) and installs the packages,
2. creates `.env` with a random `SECRET_KEY`,
3. asks you for a staff username and password (e.g. `ben`).

Then open:

| | |
|---|---|
| Website | http://localhost:8000 |
| Staff admin | http://localhost:8000/admin |

Stop with **Ctrl + C**. Run `./run.sh` again any time to start it.

If you get "permission denied": `chmod +x run.sh`.

### Manual steps (if you prefer)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.cli create-admin ben       # add a staff login (run again for ash)
python -m app.cli seed-demo              # optional: example requests to click through
uvicorn app.main:app --reload
```

Run the tests: `pytest -q`

## What it does

**Public site**: Home, Services, Maintenance Plans, Our Work, About, Contact, Terms & Policies.

- **Request a Quote** (`/quote`): project/reno quote, call-out or subscriber request. The customer describes the job, uploads up to 8 photos/videos/PDFs (15 MB each), picks preferred days, and leaves their contact details. The request is saved, JPS gets an email, and the customer gets a confirmation with a **private tracking link**.
- **Tracking page** (`/track/<code>`): the customer sees the status, your replies and your quoted price, and can **Accept** or **Decline** the quote online.
- **Plan sign-up** (`/subscribe/bronze|silver|gold`): choose the plan's 2/3/4 services and leave details. Saved for you to call and confirm.
- **Contact form**: saved as a message.

**Admin** (`/admin`, login required):

- **Requests**: list, filter by status/type, search. Open a request to see the photos, the customer details, a Google Maps link for the address, and internal notes.
- **Reply**: write a message plus an optional quote amount, and choose whether to email it. A quote amount moves the request to *Quote sent*.
- **Status**: New → Reviewing → Quote sent → Accepted → Scheduled → Completed (or Declined/Cancelled).
- **Plan sign-ups**: mark each one Pending / Active / Cancelled.
- **Messages**: mark each one handled.

## Where things are

```
app/
  content.py     ← prices, plans, services, terms wording (edit here)
  main.py        ← all pages and form handling
  models.py      ← database tables
  templates/     ← HTML pages (admin/ for the staff area)
  static/        ← style.css, admin.css, logo, fonts, site.js
data/            ← created on first run: jps.db (database) + uploads/ (customer photos)
```

**Back up the `data/` folder.** It holds all requests and photos.

## Email

Locally, emails are **printed in the terminal** instead of being sent. To send real emails from a Gmail account:

1. In the Google account, turn on 2-Step Verification, then create an **App Password**.
2. In `.env`, set:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=<the business Gmail address>
   NOTIFY_EMAIL=<the address that should receive new requests>
   SMTP_PASSWORD=<16-character app password>
   ```
3. Restart.

## Online payments (later)

`app/payments.py` and the `Payment` table are ready for Stripe but switched off. When JPS has a Stripe account, add the keys to `.env` and wire up the Checkout calls. The *Accept quote* and *Subscribe* buttons are where payment plugs in.

## Online version

- `build_static.py` saves the public pages as plain HTML (`STATIC_SITE=1`: forms are shown but switched off, no admin). GitHub Actions (`.github/workflows/pages.yml`) runs the tests, builds and publishes to GitHub Pages.

## Security

Passwords hashed (PBKDF2), CSRF tokens on every form, uploads stored privately with random names and served with the type of their (whitelisted) extension, security headers (nosniff, no iframes), and a staff login locks for 15 minutes after 5 wrong passwords.

## Before going live

- Set `SITE_URL` to the real domain and keep a long random `SECRET_KEY` in `.env`.
- Replace the placeholder project photos (`Our Work`), the team photo, and the presentation video.
- Use a high-resolution logo in `app/static/logo.png`.
- Host on a server with a persistent disk for `data/`. Postgres can be used via `DATABASE_URL`.
