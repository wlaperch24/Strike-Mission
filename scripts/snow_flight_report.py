#!/usr/bin/env python3
import datetime as dt
import math
import os
import smtplib
import sys
import time
from dataclasses import dataclass
from email.message import EmailMessage
from http import HTTPStatus
from typing import Dict, Iterable, List, Optional, Tuple

import pytz
import requests
from dateutil import parser as date_parser

NY_TZ = pytz.timezone("America/New_York")
REQUEST_TIMEOUT_SECONDS = 45
AMADEUS_RATE_LIMIT_RETRIES = 4
AMADEUS_TOKEN_RETRIES = 3
AMADEUS_BETWEEN_REQUEST_DELAY_SECONDS = 0.25

@dataclass(frozen=True)
class Airport:
    code: str
    name: str
    latitude: float
    longitude: float

@dataclass(frozen=True)
class Mountain:
    name: str
    latitude: float
    longitude: float

@dataclass(frozen=True)
class FlightOption:
    origin: str
    destination: str
    departure_local: str
    price: str
    carrier: str

MOUNTAINS: List[Mountain] = [
    Mountain("Snowbird", 40.5803, -111.6547),
    Mountain("Jackson Hole", 43.5875, -110.8270),
    Mountain("Taos", 36.5970, -105.4542),
    Mountain("Big Sky, Montana", 45.2840, -111.4010),
    Mountain("Steamboat Springs", 40.4572, -106.8087),
    Mountain("Mammoth Mountain", 37.6308, -119.0322),
]

AIRPORTS: List[Airport] = [
    Airport("JFK", "John F. Kennedy International", 40.6413, -73.7781),
    Airport("LGA", "LaGuardia", 40.7769, -73.8740),
    Airport("EWR", "Newark Liberty International", 40.6895, -74.1745),
    Airport("HPN", "Westchester County", 41.0670, -73.7076),
    Airport("SLC", "Salt Lake City International", 40.7899, -111.9791),
    Airport("JAC", "Jackson Hole", 43.6073, -110.7378),
    Airport("SMF", "Sacramento International", 38.6951, -121.5908),
    Airport("RNO", "Reno-Tahoe International", 39.4986, -119.7681),
    Airport("MMH", "Mammoth Yosemite", 37.6240, -118.8378),
    Airport("HDN", "Yampa Valley Regional", 40.4812, -107.2183),
    Airport("DEN", "Denver International", 39.8561, -104.6737),
    Airport("BZN", "Bozeman Yellowstone", 45.7775, -111.1523),
    Airport("BIL", "Billings Logan International", 45.8077, -108.5429),
    Airport("ABQ", "Albuquerque International Sunport", 35.0425, -106.6090),
    Airport("TSM", "Taos Regional", 36.4582, -105.6719),
]


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_miles * c


def closest_airports(mountain: Mountain, count: int = 2) -> List[Airport]:
    sorted_airports = sorted(
        AIRPORTS,
        key=lambda airport: haversine_miles(mountain.latitude, mountain.longitude, airport.latitude, airport.longitude),
    )
    return sorted_airports[:count]


def get_open_meteo_snowfall(mountain: Mountain) -> float:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": mountain.latitude,
        "longitude": mountain.longitude,
        "daily": "snowfall_sum",
        "timezone": "America/Denver",
    }
    payload = get_json_with_retries(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    daily = payload.get("daily", {})
    snowfall_values = daily.get("snowfall_sum", [])
    return float(sum(snowfall_values[:7]))


OPENSNOW_STATIONS = {
    "Snowbird": "OPENSNOW_STATION_SNOWBIRD",
    "Jackson Hole": "OPENSNOW_STATION_JACKSON_HOLE",
    "Taos": "OPENSNOW_STATION_TAOS",
    "Big Sky, Montana": "OPENSNOW_STATION_BIG_SKY_MONTANA",
    "Steamboat Springs": "OPENSNOW_STATION_STEAMBOAT_SPRINGS",
    "Mammoth Mountain": "OPENSNOW_STATION_MAMMOTH_MOUNTAIN",
}

AIRLINE_NAMES = {
    "AA": "American Airlines",
    "AS": "Alaska Airlines",
    "B6": "JetBlue",
    "DL": "Delta Air Lines",
    "F9": "Frontier Airlines",
    "NK": "Spirit Airlines",
    "UA": "United Airlines",
    "WN": "Southwest Airlines",
}


def get_snowfall_forecast(mountain: Mountain) -> float:
    api_key = os.getenv("OPENSNOW_API_KEY")
    station_env = OPENSNOW_STATIONS.get(mountain.name)
    station_id = os.getenv(station_env) if station_env else None
    if api_key and station_id:
        url = "https://api.opensnow.com/forecast"
        try:
            payload = get_json_with_retries(
                url,
                params={"station_id": station_id},
                headers={"X-Api-Key": api_key},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            daily = payload.get("daily", [])
            snowfall_values = [day.get("snowfall_inches", 0) for day in daily[:7]]
            return float(sum(snowfall_values))
        except requests.RequestException as exc:
            print(f"OpenSnow lookup failed for {mountain.name}, falling back to Open-Meteo: {exc}")
    return get_open_meteo_snowfall(mountain)


def get_json_with_retries(
    url: str,
    *,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
    retries: int = 3,
) -> dict:
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(2 ** (attempt - 1))


def amadeus_token() -> str:
    client_id = os.environ["AMADEUS_CLIENT_ID"]
    client_secret = os.environ["AMADEUS_CLIENT_SECRET"]
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    for attempt in range(AMADEUS_TOKEN_RETRIES):
        response = requests.post(url, data=data, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS and attempt < AMADEUS_TOKEN_RETRIES - 1:
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                delay_seconds = max(1, int(retry_after))
            else:
                delay_seconds = min(8, 2 ** attempt)
            time.sleep(delay_seconds)
            continue
        response.raise_for_status()
        return response.json()["access_token"]

    raise RuntimeError("Unable to retrieve Amadeus token after retries.")


def parse_departure_hour(iso_time: str) -> int:
    parsed = date_parser.isoparse(iso_time)
    return parsed.hour


def find_best_flight(
    token: str,
    origin: str,
    destination: str,
    date: str,
    time_min: int = 15,
    time_max: int = 24,
) -> Optional[FlightOption]:
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": date,
        "adults": 1,
        "nonStop": "true",
        "currencyCode": "USD",
        "max": 20,
    }
    response = request_amadeus_flight_offers_with_retries(url, headers=headers, params=params)
    if response is None:
        return None
    offers = response.json().get("data", [])
    best: Optional[FlightOption] = None
    for offer in offers:
        segments = offer["itineraries"][0]["segments"]
        if len(segments) != 1:
            continue
        departure_time = segments[0]["departure"]["at"]
        hour = parse_departure_hour(departure_time)
        if hour < time_min or hour >= time_max:
            continue
        price = offer["price"]["total"]
        carrier = segments[0]["carrierCode"]
        option = FlightOption(
            origin=origin,
            destination=destination,
            departure_local=departure_time,
            price=price,
            carrier=carrier,
        )
        if best is None or float(option.price) < float(best.price):
            best = option
    return best


def request_amadeus_flight_offers_with_retries(
    url: str,
    *,
    headers: dict,
    params: dict,
) -> Optional[requests.Response]:
    for attempt in range(AMADEUS_RATE_LIMIT_RETRIES + 1):
        response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS and attempt < AMADEUS_RATE_LIMIT_RETRIES:
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                delay_seconds = max(1, int(retry_after))
            else:
                delay_seconds = min(16, 2 ** attempt)
            time.sleep(delay_seconds)
            continue
        if response.ok:
            return response
        print(f"AMADEUS flight-offers request failed ({response.status_code}): {response.text}")
        return None
    return None


def get_best_fares(
    token: str,
    origin_airports: Iterable[str],
    destination_airports: Iterable[str],
    outbound_date: str,
    return_date: str,
) -> Tuple[Optional[FlightOption], Optional[FlightOption]]:
    outbound_best: Optional[FlightOption] = None
    return_best: Optional[FlightOption] = None
    for destination in destination_airports:
        for origin in origin_airports:
            outbound = find_best_flight(token, origin, destination, outbound_date)
            if outbound and (outbound_best is None or float(outbound.price) < float(outbound_best.price)):
                outbound_best = outbound
            time.sleep(AMADEUS_BETWEEN_REQUEST_DELAY_SECONDS)
        for origin in origin_airports:
            inbound = find_best_flight(token, destination, origin, return_date)
            if inbound and (return_best is None or float(inbound.price) < float(return_best.price)):
                return_best = inbound
            time.sleep(AMADEUS_BETWEEN_REQUEST_DELAY_SECONDS)
    return outbound_best, return_best


def format_flight(option: Optional[FlightOption]) -> str:
    if not option:
        return "No non-stop flights found in time window."
    carrier_name = AIRLINE_NAMES.get(option.carrier, "Unknown Airline")
    return (
        f"{option.origin} → {option.destination} | {option.departure_local} | "
        f"{carrier_name} ({option.carrier}) | ${option.price}"
    )


def send_email(subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = os.environ["SMTP_TO"]
    msg.set_content(body)

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


def should_run_now() -> bool:
    now = dt.datetime.now(NY_TZ)
    return now.weekday() == 0 and now.hour == 17


def next_thursday_date(start: dt.datetime) -> dt.date:
    days_ahead = (3 - start.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (start + dt.timedelta(days=days_ahead)).date()


def main() -> None:
    if not should_run_now() and os.getenv("FORCE_RUN") != "true":
        print("Not within Monday 5pm ET window. Exiting.")
        return

    threshold = float(os.getenv("SNOWFALL_THRESHOLD_IN", "16"))
    return_offset = int(os.getenv("RETURN_DAY_OFFSET", "3"))
    origin_airports = [code.strip().upper() for code in os.getenv("NYC_AIRPORTS", "JFK,LGA,EWR,HPN").split(",") if code.strip()]

    now = dt.datetime.now(NY_TZ)
    outbound_date = next_thursday_date(now)
    return_date = outbound_date + dt.timedelta(days=return_offset)

    report_lines = [
        f"Snow & Flight Report for {now.strftime('%Y-%m-%d')} (Monday 5pm ET)",
        "",
    ]

    qualifying_mountains: Dict[str, float] = {}
    for mountain in MOUNTAINS:
        try:
            snowfall = get_snowfall_forecast(mountain)
        except requests.RequestException as exc:
            report_lines.append(f"{mountain.name}: forecast unavailable ({exc})")
            continue
        report_lines.append(f"{mountain.name}: {snowfall:.1f} in (7-day forecast)")
        if snowfall >= threshold:
            qualifying_mountains[mountain.name] = snowfall

    report_lines.append("")

    if not qualifying_mountains:
        report_lines.append("No mountains exceeded the snowfall threshold.")
    else:
        token = amadeus_token()
        for mountain in MOUNTAINS:
            if mountain.name not in qualifying_mountains:
                continue
            nearby = closest_airports(mountain)
            destination_airports = [airport.code for airport in nearby]
            report_lines.append(f"--- {mountain.name} ---")
            report_lines.append(
                f"Closest airports: {', '.join([f'{a.code} ({a.name})' for a in nearby])}"
            )

            outbound_best, return_best = get_best_fares(
                token,
                origin_airports,
                destination_airports,
                outbound_date.isoformat(),
                return_date.isoformat(),
            )

            report_lines.append(
                f"Outbound ({outbound_date} 3pm-12am): {format_flight(outbound_best)}"
            )
            report_lines.append(f"Return ({return_date}): {format_flight(return_best)}")
            report_lines.append("")

    report_body = "\n".join(report_lines)
    subject = "Snowfall & Flight Monitor"

    print("=== REPORT START ===")
    print(report_body)
    print("=== REPORT END ===")

    send_email(subject, report_body)
    print(f"Email sent to {os.environ['SMTP_TO']} with subject: {subject}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
