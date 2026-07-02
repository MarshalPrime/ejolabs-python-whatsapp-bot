import logging
import os

from app.services.constants import FALLBACK_RESPONSE
from app.services.ejochat_service import generate_ejochat_response
from app.services.gemini_service import generate_gemini_response


def generate_kabisa_response(message_body, context):
    provider = os.getenv("LLM_PROVIDER", "ejochat").strip().lower()
    logging.info("Generating Kabisa response with provider: %s", provider)

    if provider == "ejochat":
        if not (os.getenv("EJOCHAT_API_KEY") or os.getenv("EjoChat_API_KEY")):
            logging.error("LLM_PROVIDER=ejochat but EJOCHAT_API_KEY is not set.")
            return FALLBACK_RESPONSE
        return generate_ejochat_response(message_body, context=context)
    if provider == "gemini":
        if not os.getenv("GEMINI_API_KEY"):
            logging.error("LLM_PROVIDER=gemini but GEMINI_API_KEY is not set.")
            return FALLBACK_RESPONSE
        return generate_gemini_response(message_body, context=context)

    logging.error("Unsupported LLM_PROVIDER: %s", provider)
    return FALLBACK_RESPONSE
