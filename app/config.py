import sys
import os
from dotenv import load_dotenv
import logging


REQUIRED_SETTINGS = (
    "ACCESS_TOKEN",
    "APP_SECRET",
    "VERSION",
    "PHONE_NUMBER_ID",
    "VERIFY_TOKEN",
)


def load_configurations(app):
    load_dotenv()
    app.config["ACCESS_TOKEN"] = os.getenv("ACCESS_TOKEN")
    app.config["YOUR_PHONE_NUMBER"] = os.getenv("YOUR_PHONE_NUMBER")
    app.config["APP_ID"] = os.getenv("APP_ID")
    app.config["APP_SECRET"] = os.getenv("APP_SECRET")
    app.config["RECIPIENT_WAID"] = os.getenv("RECIPIENT_WAID")
    app.config["VERSION"] = os.getenv("VERSION")
    app.config["PHONE_NUMBER_ID"] = os.getenv("PHONE_NUMBER_ID")
    app.config["VERIFY_TOKEN"] = os.getenv("VERIFY_TOKEN")
    app.config["EJOCHAT_API_KEY"] = os.getenv("EJOCHAT_API_KEY") or os.getenv("EjoChat_API_KEY")
    app.config["EJOCHAT_API_URL"] = (
        os.getenv("EJOCHAT_API_URL")
        or os.getenv("EjoChat_API_URL")
        or "https://api.ejolabs.com/api/v1/subiza"
    )
    app.config["LLM_PROVIDER"] = os.getenv("LLM_PROVIDER", "ejochat")
    app.config["KABISA_RESPONSE_LANGUAGE"] = os.getenv("KABISA_RESPONSE_LANGUAGE", "auto")
    app.config["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
    app.config["GEMINI_MODEL"] = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    app.config["QDRANT_URL"] = os.getenv("QDRANT_URL", "http://localhost:6333")
    app.config["QDRANT_COLLECTION"] = os.getenv("QDRANT_COLLECTION", "kabisa_rw")
    app.config["KABISA_COUNTRY"] = os.getenv("KABISA_COUNTRY", "RW")
    app.config["KABISA_SITE_BASE_URL"] = os.getenv(
        "KABISA_SITE_BASE_URL", "https://www.gokabisa.com/rw"
    )
    app.config["KABISA_API_BASE_URL"] = os.getenv(
        "KABISA_API_BASE_URL", "https://api.gokabisa.com"
    )
    app.config["WEBHOOK_ASYNC"] = os.getenv("WEBHOOK_ASYNC", "true").lower() == "true"

    missing = [name for name in REQUIRED_SETTINGS if not app.config.get(name)]
    if missing:
        logging.warning("Missing required settings: %s", ", ".join(missing))


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
