import os
import sys
import logging
from contextlib import contextmanager
from pathlib import Path

logging.disable(logging.CRITICAL)

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.constants import FALLBACK_RESPONSE, looks_like_default_persona
from app.services.llm_service import generate_kabisa_response
from app.utils.whatsapp_utils import (
    _asks_available_vehicles,
    _asks_charging_stations,
    _format_charging_stations,
    _format_available_vehicles,
    _is_image_followup,
    _requested_location,
    _wants_image,
    get_simple_assistant_response,
)


@contextmanager
def patched_env(**updates):
    original = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(value, label):
    if not value:
        raise AssertionError(f"{label}: expected truthy value")


def assert_false(value, label):
    if value:
        raise AssertionError(f"{label}: expected falsey value")


def check_simple_replies():
    assert_true(
        get_simple_assistant_response("bonsoir").startswith("Bonjour!"),
        "French greeting",
    )
    assert_true(
        get_simple_assistant_response("good evening").startswith("Hello!"),
        "English greeting",
    )
    assert_true(
        get_simple_assistant_response("muraho").startswith("Muraho!"),
        "Kinyarwanda greeting",
    )
    assert_true(
        "Kabisa" in get_simple_assistant_response("who are you?"),
        "identity reply mentions Kabisa",
    )


def check_image_intent():
    assert_false(_wants_image("bonsoir"), "greeting does not want image")
    assert_false(
        _wants_image("tell me the models I can buy"),
        "availability query is not direct image intent",
    )
    assert_true(
        _asks_available_vehicles("tell me the models I can buy"),
        "English availability query",
    )
    assert_true(
        _asks_available_vehicles("Show me all the models you have"),
        "English all-models query",
    )
    assert_true(
        _asks_available_vehicles("tell me types of cars I can buy"),
        "English vehicle type query",
    )
    assert_true(
        _asks_available_vehicles("mbwira imodoka zihari nagura"),
        "Kinyarwanda availability query",
    )
    assert_true(
        _asks_available_vehicles("mbwira imodoga zihari nagura"),
        "Kinyarwanda availability query with common typo",
    )
    assert_true(_wants_image("show me the 2025 Geely Ex2 Pro"), "explicit image request")
    assert_true(_is_image_followup("show it here"), "image follow-up")
    assert_false(_is_image_followup("show me the 2025 Geely Ex2 Pro"), "specific image request")


def check_available_vehicle_formatting():
    vehicles = [
        {
            "text": "2025 Geely Ex2 Pro Trim: Pro Classification: COMPACT_SUV Range: 345 km Battery capacity: 39 kWh",
            "metadata": {"classification": "COMPACT_SUV", "source_url": "https://example.com/v11"},
        },
        {
            "text": "2025 Geely Galaxy EX5 Trim: Max Classification: SUV Range: 530 km Battery capacity: 57 kWh",
            "metadata": {"classification": "SUV", "source_url": "https://example.com/v21"},
        },
    ]
    output = _format_available_vehicles(vehicles)
    assert_true("2025 Geely Ex2 Pro" in output, "formats first vehicle")
    assert_true("2025 Geely Galaxy EX5" in output, "formats second vehicle")
    assert_true("Compact SUV" in output, "formats compact SUV label")
    assert_true("SUV" in output, "formats SUV label")


def check_charging_station_intent_and_formatting():
    message = "Tell me the charging stations in kigali I can go to"
    assert_true(_asks_charging_stations(message), "charging station query")
    assert_equal(_requested_location(message), "kigali", "detects Kigali location")

    chargers = [
        {
            "text": "Charging station: People Kacyiru",
            "metadata": {
                "name": "People Kacyiru",
                "status": "available",
                "operational_status": "operational",
                "connector": "GBT,CSS2",
                "power": 240,
                "source_url": "https://www.google.com/maps?q=-1.948032516796903,30.09290996249001",
            },
        }
    ]
    output = _format_charging_stations(chargers)
    assert_true("People Kacyiru" in output, "formats charger name")
    assert_true("GBT,CSS2" in output, "formats connector")


def check_provider_fallbacks():
    with patched_env(
        LLM_PROVIDER="unknown",
        EJOCHAT_API_KEY=None,
        EjoChat_API_KEY=None,
        GEMINI_API_KEY=None,
    ):
        assert_equal(
            generate_kabisa_response("hello", "Kabisa context"),
            FALLBACK_RESPONSE,
            "unsupported provider fallback",
        )

    with patched_env(
        LLM_PROVIDER="gemini",
        EJOCHAT_API_KEY=None,
        EjoChat_API_KEY=None,
        GEMINI_API_KEY=None,
    ):
        assert_equal(
            generate_kabisa_response("hello", "Kabisa context"),
            FALLBACK_RESPONSE,
            "gemini missing key fallback",
        )

    with patched_env(
        LLM_PROVIDER="ejochat",
        EJOCHAT_API_KEY=None,
        EjoChat_API_KEY=None,
        GEMINI_API_KEY=None,
    ):
        assert_equal(
            generate_kabisa_response("hello", "Kabisa context"),
            FALLBACK_RESPONSE,
            "ejochat missing key fallback",
        )


def check_persona_guard():
    assert_true(
        looks_like_default_persona("Ndi Uri Subiza, umufasha wa AI wakozwe na Ejo Labs."),
        "blocks old Subiza persona",
    )
    assert_false(
        looks_like_default_persona("I am Kabisa's WhatsApp assistant."),
        "allows Kabisa persona",
    )


def main():
    check_simple_replies()
    check_image_intent()
    check_available_vehicle_formatting()
    check_charging_station_intent_and_formatting()
    check_provider_fallbacks()
    check_persona_guard()
    print("Smoke checks passed.")


if __name__ == "__main__":
    main()
