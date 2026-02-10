
# Strike Mission — Snow & Flight Monitor

Strike Mission is an automated monitor that checks upcoming snowfall at major ski destinations and alerts you when conditions align with affordable, non-stop flights from the NYC area.

The goal: identify high-confidence ski weekends without manual searching.

---

## What it does

A scheduled job runs each Monday evening and:

1. Checks the **7-day snowfall forecast** (starting from that Monday) for:
   - Snowbird
   - Jackson Hole
   - Taos
   - Big Sky (Montana)
   - Steamboat Springs
   - Mammoth Mountain

2. If any mountain has **≥ 24 inches** of projected snowfall:
   - Searches for **non-stop outbound flights** from:
     - JFK, LGA, EWR, or HPN
   - To the **two closest airports (by distance)** for that mountain

3. Flight search constraints:
   - **Outbound:** Thursday between **3:00pm–12:00am (local time)**
   - **Return:** Sunday (configurable via environment variable)

4. Emails a summarized report with:
   - qualifying mountains
   - best available fares
   - outbound + return pricing

---

## How it runs

- The workflow is executed via **GitHub Actions**
- It runs on Mondays during the **5:00pm ET hour**
- A time check inside the script ensures the email only sends at the correct local time

Cron schedule:

---

## Configuration

All configuration is handled via environment variables.

Use `.env.example` as a reference and create the corresponding repository secrets in GitHub Actions.

### OpenSnow
- `OPENSNOW_API_KEY`
- Optional per-mountain station overrides:
  - `OPENSNOW_STATION_SNOWBIRD`
  - `OPENSNOW_STATION_JACKSON_HOLE`
  - `OPENSNOW_STATION_TAOS`
  - `OPENSNOW_STATION_BIG_SKY_MONTANA`
  - `OPENSNOW_STATION_STEAMBOAT_SPRINGS`
  - `OPENSNOW_STATION_MAMMOTH_MOUNTAIN`

### Amadeus (Flights API)
- `AMADEUS_CLIENT_ID`
- `AMADEUS_CLIENT_SECRET`

### Email (SMTP)
Typical Gmail setup (requires App Password):
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_TO`

### Optional overrides
- `SNOWFALL_THRESHOLD_IN` (default: 24)
- `RETURN_DAY_OFFSET` (default: 3 → Thursday + 3 = Sunday)
- `NYC_AIRPORTS` (default: JFK,LGA,EWR,HPN)

---

## Local execution

```bash
pip install -r requirements.txt
python scripts/snow_flight_report.py


'''bash
