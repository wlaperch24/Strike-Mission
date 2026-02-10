print("Snow & Flight Monitor: agent started")

import os

required_vars = [
    "OPENSNOW_API_KEY",
    "AMADEUS_CLIENT_ID",
    "AMADEUS_CLIENT_SECRET",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "SMTP_TO",
]

missing = [v for v in required_vars if not os.getenv(v)]

if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

print("All required environment variables are present.")
print("Agent finished successfully.")

