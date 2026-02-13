# Strike Mission – Snow & Flight Monitor

This repo contains a scheduled job that:

1. Checks the 7‑day snowfall forecast (starting the Monday run time) for:
   - Snowbird
   - Jackson Hole
   - Taos
   - Big Sky (Montana)
   - Steamboat Springs
   - Mammoth Mountain
2. If any mountain has **>= 24 inches** forecast, it searches for **non‑stop flights** from any NYC airport (JFK/LGA/EWR) or Westchester County (HPN) to the **two closest airports** (by distance) to that mountain.
3. Searches outbound flights **Thursday 3:00pm–12:00am local time** and return flights **Sunday (configurable)**.
4. Emails the results Monday night.

## How it runs

GitHub Actions runs the workflow on Mondays during the 5pm ET hour (it checks local time before sending):

```
0 20-23 * * 1
```

The script verifies that it is **Monday 5pm ET** before sending.

## Configuration

Create repository secrets in GitHub:

### OpenSnow API
- `OPENSNOW_API_KEY`

### Amadeus API
- `AMADEUS_CLIENT_ID`
- `AMADEUS_CLIENT_SECRET`

### Email (SMTP)
Example for Gmail SMTP (requires an App Password):
- `SMTP_HOST` (e.g. smtp.gmail.com)
- `SMTP_PORT` (e.g. 587)
- `SMTP_USER` (your Gmail address)
- `SMTP_PASSWORD` (app password)
- `SMTP_FROM` (same as sender)
- `SMTP_TO` (recipient email)

### Optional overrides
- `SNOWFALL_THRESHOLD_IN` (default: 24)
- `RETURN_DAY_OFFSET` (default: 3; Thursday + 3 = Sunday)
- `NYC_AIRPORTS` (default: JFK,LGA,EWR,HPN)

## Local run

```
pip install -r requirements.txt
python scripts/snow_flight_report.py
```

## Publishing to GitHub

This repo can be pushed from your local machine or from a container workspace. If you are
working in a container and want the files on your Mac first, create a zip and download it
from your editor’s file explorer:

```
cd /workspace
zip -r Strike-Mission.zip Strike-Mission
```

Then unzip locally and publish with GitHub Desktop, or add a remote and push with git.

## Notes
- Google Flights is not easily automated; this uses the Amadeus API for real‑time flight offers.
- Airport lists and coordinates are in `scripts/snow_flight_report.py`.
