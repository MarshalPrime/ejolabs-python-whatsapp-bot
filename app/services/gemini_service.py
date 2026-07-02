import logging
import os

from app.services.constants import FALLBACK_RESPONSE, looks_like_default_persona
from app.services.prompt_service import (
    build_kabisa_system_instruction,
    build_kabisa_user_prompt,
)


def generate_gemini_response(message_body, context=None):
    if not context:
        return FALLBACK_RESPONSE

    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    if not api_key:
        logging.error("GEMINI_API_KEY is not set in environment.")
        return FALLBACK_RESPONSE

    try:
        from google import genai
    except ImportError:
        logging.error("google-genai is not installed.")
        return FALLBACK_RESPONSE

    try:
        client = genai.Client(api_key=api_key)
        interaction = client.interactions.create(
            model=model,
            system_instruction=build_kabisa_system_instruction(),
            input=build_kabisa_user_prompt(message_body, context),
            generation_config={
                "temperature": 0.2,
                "thinking_level": "low",
            },
        )
        answer = (interaction.output_text or "").strip()
        if looks_like_default_persona(answer):
            logging.error("Gemini returned non-Kabisa persona response: %s", answer)
            return FALLBACK_RESPONSE
        return answer or FALLBACK_RESPONSE
    except Exception as exc:
        logging.error("Gemini API call failed: %s", exc)
        return FALLBACK_RESPONSE
