import logging
import os

from app.services.constants import FALLBACK_RESPONSE, looks_like_default_persona
from app.services.llm_service import generate_kabisa_response
from app.services.qdrant_service import (
    list_available_vehicles,
    list_charging_stations,
    search_knowledge,
)
from app.services.whatsapp_service import send_image_message, send_text_message
import re


MIN_RETRIEVAL_SCORE = 0.55
LAST_IMAGE_BY_USER = {}


GREETING_RESPONSE = (
    "Muraho! Ndi umufasha wa Kabisa kuri WhatsApp. "
    "Nakugufasha kumenya imodoka z'amashanyarazi, charging, maintenance, "
    "test drive, cyangwa amakuru ya Kabisa mu Rwanda."
)

IDENTITY_RESPONSE = (
    "Ndi umufasha wa Kabisa kuri WhatsApp. Nkoresha amakuru ya Kabisa kugira ngo "
    "ngufashe kumenya imodoka z'amashanyarazi, charging, maintenance, na test drive mu Rwanda."
)

HELP_RESPONSE = (
    "Ndi hano kugufasha ku makuru ya Kabisa. Ushobora kumbaza ku modoka, charging, "
    "maintenance, test drive, ibiciro, range, cyangwa aho Kabisa iherereye."
)

SIMPLE_RESPONSES = {
    "rw": {
        "greeting": GREETING_RESPONSE,
        "identity": IDENTITY_RESPONSE,
        "help": HELP_RESPONSE,
    },
    "en": {
        "greeting": (
            "Hello! I am Kabisa's WhatsApp assistant. I can help with electric vehicles, "
            "charging, maintenance, test drives, and Kabisa information in Rwanda."
        ),
        "identity": (
            "I am Kabisa's WhatsApp assistant. I use Kabisa information to help with "
            "electric vehicles, charging, maintenance, and test drives in Rwanda."
        ),
        "help": (
            "I can help with Kabisa information about vehicles, charging, maintenance, "
            "test drives, prices, range, and locations."
        ),
    },
    "fr": {
        "greeting": (
            "Bonjour! Je suis l'assistant WhatsApp de Kabisa. Je peux vous aider avec "
            "les vehicules electriques, la recharge, la maintenance, les essais, et les "
            "informations de Kabisa au Rwanda."
        ),
        "identity": (
            "Je suis l'assistant WhatsApp de Kabisa. J'utilise les informations de Kabisa "
            "pour vous aider avec les vehicules electriques, la recharge, la maintenance, "
            "et les essais au Rwanda."
        ),
        "help": (
            "Je peux vous aider avec les informations de Kabisa sur les vehicules, la "
            "recharge, la maintenance, les essais, les prix, l'autonomie, et les lieux."
        ),
    },
}


def _preferred_simple_language(compact):
    configured = os.getenv("KABISA_RESPONSE_LANGUAGE", "auto").strip().lower()
    if configured in ("kinyarwanda", "rw"):
        return "rw"
    if configured in ("english", "en"):
        return "en"
    if configured in ("french", "fr"):
        return "fr"

    english_markers = (
        "hello",
        "hi",
        "hey",
        "good evening",
        "who are you",
        "what are you",
        "help",
    )
    french_markers = ("bonjour", "bonsoir", "salut", "qui es tu", "tu es qui", "aide")
    if any(marker in compact for marker in english_markers):
        return "en"
    if any(marker in compact for marker in french_markers):
        return "fr"
    return "rw"


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def get_simple_assistant_response(message_body):
    normalized = message_body.lower().strip()
    compact = re.sub(r"[^\w\s]", "", normalized)
    words = set(compact.split())
    language = _preferred_simple_language(compact)

    greeting_words = {
        "hi",
        "hello",
        "hey",
        "muraho",
        "bite",
        "bonjour",
        "bonsoir",
        "salut",
        "good evening",
        "mwaramutse",
        "mwiriwe",
    }
    greeting_phrases = ("good evening",)
    if (words & greeting_words or compact in greeting_phrases) and len(words) <= 4:
        return SIMPLE_RESPONSES[language]["greeting"]

    identity_phrases = (
        "who are you",
        "what are you",
        "uri nde",
        "witwa nde",
        "who is this",
        "what is your name",
        "qui es tu",
        "tu es qui",
    )
    if any(phrase in compact for phrase in identity_phrases):
        return SIMPLE_RESPONSES[language]["identity"]

    help_phrases = (
        "help",
        "what can you do",
        "what can you help",
        "wamfasha",
        "wafasha iki",
        "ushobora gukora iki",
        "aide",
        "aidez moi",
    )
    if any(phrase in compact for phrase in help_phrases):
        return SIMPLE_RESPONSES[language]["help"]

    return None


def _format_context(results):
    if not results:
        return ""

    chunks = []
    seen = set()
    for index, result in enumerate(results, start=1):
        metadata = result.get("metadata", {})
        source_url = metadata.get("source_url", "")
        key = (metadata.get("content_type"), source_url, metadata.get("vehicle_id"))
        if key in seen:
            continue
        seen.add(key)
        text = result.get("text", "")[:1200]
        chunks.append(
            f"[{index}] {text}\nSource: {source_url}".strip()
        )
        if len(chunks) >= 5:
            break
    return "\n\n".join(chunks)


def _vehicle_field(text, label):
    match = re.search(rf"{re.escape(label)}:\s*([^:]+?)(?=\s+[A-Z][A-Za-z ]+:|$)", text)
    return match.group(1).strip() if match else ""


def _format_available_vehicles(vehicles):
    if not vehicles:
        return FALLBACK_RESPONSE

    lines = ["Based on Kabisa's available information, you can buy:"]
    for vehicle in vehicles:
        metadata = vehicle.get("metadata", {})
        text = vehicle.get("text", "")
        name = (text.split(" Trim:", 1)[0] or "Vehicle").strip()
        classification = metadata.get("classification") or _vehicle_field(text, "Classification")
        vehicle_type = _format_vehicle_type(classification) if classification else "Vehicle"
        range_km = _vehicle_field(text, "Range")
        battery = _vehicle_field(text, "Battery capacity")
        source_url = metadata.get("source_url")

        lines.append(f"\n* {name} ({vehicle_type})")
        if range_km:
            lines.append(f"  * Range: {range_km}")
        if battery:
            lines.append(f"  * Battery: {battery}")
        if source_url:
            lines.append(f"  * More details: {source_url}")

    return "\n".join(lines)


def _format_charging_stations(chargers):
    if not chargers:
        return FALLBACK_RESPONSE

    lines = ["Based on Kabisa's charging information, you can go to:"]
    for charger in chargers:
        metadata = charger.get("metadata", {})
        name = metadata.get("name") or "Charging station"
        address = metadata.get("address")
        status = metadata.get("operational_status") or metadata.get("status")
        connector = metadata.get("connector")
        power = metadata.get("power")
        source_url = metadata.get("source_url")

        lines.append(f"\n* {name}")
        if address:
            lines.append(f"  * Address: {address}")
        if status:
            lines.append(f"  * Status: {status}")
        if connector:
            lines.append(f"  * Connector: {connector}")
        if power:
            lines.append(f"  * Power: {power} kW")
        if source_url:
            lines.append(f"  * Map: {source_url}")
    return "\n".join(lines)


def _format_vehicle_type(classification):
    words = classification.replace("_", " ").split()
    return " ".join(word.upper() if word.lower() == "suv" else word.title() for word in words)


def _best_image_url(results):
    for result in results:
        metadata = result.get("metadata", {})
        if metadata.get("image_url"):
            return metadata["image_url"]
        image_urls = metadata.get("image_urls") or []
        if image_urls:
            return image_urls[0]
    return None


def _wants_image(message_body):
    compact = message_body.lower()
    image_terms = (
        "show",
        "image",
        "photo",
        "picture",
        "see it",
        "nyereka",
        "ifoto",
        "ishusho",
        "montre",
        "voir",
    )
    return any(term in compact for term in image_terms)


def _asks_available_vehicles(message_body):
    compact = message_body.lower()
    inventory_words = ("model", "models", "car", "cars", "vehicle", "vehicles")
    inventory_qualifiers = (
        "all",
        "available",
        "you have",
        "i can buy",
        "do you have",
        "which",
        "what",
    )
    if any(word in compact for word in inventory_words) and any(
        qualifier in compact for qualifier in inventory_qualifiers
    ):
        return True

    availability_terms = (
        "models i can buy",
        "cars i can buy",
        "vehicles i can buy",
        "types of cars",
        "available models",
        "available cars",
        "available vehicles",
        "what cars do you have",
        "which cars do you have",
        "all the models",
        "models you have",
        "all models you have",
        "show me all the models",
        "show me all the cars",
        "imodoka zihari",
        "imodoka mufite",
        "imodoga zihari",
        "imodoga mufite",
        "nagura",
        "vehicules disponibles",
        "modeles disponibles",
    )
    return any(term in compact for term in availability_terms)


def _is_image_followup(message_body):
    compact = message_body.lower().strip()
    followup_terms = (
        "show it",
        "show it here",
        "send it",
        "send it here",
        "see it",
        "nyereka",
        "montre le",
        "montre la",
    )
    return any(term in compact for term in followup_terms)


def _asks_charging_stations(message_body):
    compact = message_body.lower()
    charging_terms = ("charging station", "charging stations", "charger", "chargers")
    location_terms = ("where", "location", "locations", "kigali", "go to", "near")
    return any(term in compact for term in charging_terms) and any(
        term in compact for term in location_terms
    )


def _requested_location(message_body):
    compact = message_body.lower()
    if "kigali" in compact:
        return "kigali"
    return None


def _has_relevant_context(results):
    if not results:
        logging.warning("No Kabisa RAG results found")
        return False

    top_score = results[0].get("score") or 0
    if top_score < MIN_RETRIEVAL_SCORE:
        logging.warning("Kabisa RAG score too low: %s", top_score)
        return False

    return True


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    if message.get("type") != "text" or not message.get("text", {}).get("body"):
        send_text_message(wa_id, FALLBACK_RESPONSE)
        return

    message_body = message["text"]["body"]
    
    logging.info(f"Received message: '{message_body}' from '{name}' ({wa_id})")

    simple_response = get_simple_assistant_response(message_body)
    if simple_response:
        send_text_message(wa_id, simple_response)
        return

    if _asks_available_vehicles(message_body):
        vehicles = list_available_vehicles()
        if not vehicles:
            send_text_message(wa_id, FALLBACK_RESPONSE)
            return

        image_url = _best_image_url(vehicles)
        if image_url:
            LAST_IMAGE_BY_USER[wa_id] = image_url

        send_text_message(wa_id, process_text_for_whatsapp(_format_available_vehicles(vehicles)))
        if image_url:
            send_image_message(wa_id, image_url)
        return

    if _asks_charging_stations(message_body):
        chargers = list_charging_stations(location=_requested_location(message_body))
        if not chargers:
            send_text_message(wa_id, FALLBACK_RESPONSE)
            return
        send_text_message(wa_id, process_text_for_whatsapp(_format_charging_stations(chargers)))
        return

    if _wants_image(message_body) and _is_image_followup(message_body):
        image_url = LAST_IMAGE_BY_USER.get(wa_id)
        if image_url:
            send_image_message(wa_id, image_url)
            return

    results = search_knowledge(message_body, limit=10)
    logging.info(
        "Kabisa RAG results: %s",
        [
            {
                "score": round(result.get("score") or 0, 3),
                "type": result.get("metadata", {}).get("content_type"),
                "source": result.get("metadata", {}).get("source_url"),
            }
            for result in results[:3]
        ],
    )

    if not _has_relevant_context(results):
        send_text_message(wa_id, FALLBACK_RESPONSE)
        return

    image_url = _best_image_url(results)
    if image_url:
        LAST_IMAGE_BY_USER[wa_id] = image_url

    context = _format_context(results)
    if not context:
        logging.warning("Kabisa RAG returned results but context formatting was empty")
        send_text_message(wa_id, FALLBACK_RESPONSE)
        return

    response = generate_kabisa_response(message_body, context=context)
    response = process_text_for_whatsapp(response)
    if looks_like_default_persona(response):
        logging.error("Blocked non-Kabisa persona response at WhatsApp boundary: %s", response)
        response = FALLBACK_RESPONSE

    send_text_message(wa_id, response)
    if (_wants_image(message_body) or _asks_available_vehicles(message_body)) and image_url:
        send_image_message(wa_id, image_url)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
