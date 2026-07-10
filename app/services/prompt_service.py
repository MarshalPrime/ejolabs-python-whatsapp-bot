import os

from app.services.constants import FALLBACK_RESPONSE


def _language_instruction():
    language = os.getenv("KABISA_RESPONSE_LANGUAGE", "auto").strip().lower()

    if language in ("kinyarwanda", "rw"):
        return "Answer in Kinyarwanda. "
    if language in ("english", "en"):
        return "Answer in English. "
    if language in ("french", "fr"):
        return "Answer in French. "

    return (
        "Answer in the same language the user used. "
        "If the user's language is unclear, answer in Kinyarwanda. "
    )


def build_kabisa_system_instruction():
    return (
        "You are Kabisa's WhatsApp assistant. "
        "EjoChat, Gemini, and other model providers are only infrastructure; never introduce yourself as them. "
        "Never introduce yourself as Subiza or Ejo Labs. "
        f"{_language_instruction()}"
        "Use only the provided Kabisa knowledge base context. "
        "Format contact details as plain text; do not wrap email addresses, phone numbers, names, or locations in square brackets or Markdown links. "
        f"If the answer is not in the context, don't imagine or hallucinate, reply exactly: {FALLBACK_RESPONSE}"
    )


def build_kabisa_user_prompt(message_body, context):
    return (
        "Act as Kabisa's WhatsApp assistant. "
        "Do not greet as Uri Subiza. Do not mention being created by Ejo Labs. "
        "Answer only from the Kabisa knowledge base context below. "
        "When listing contact details, keep email addresses and phone numbers as plain text without square brackets. "
        f"If the context does not answer the question, don't imagine or hallucinate, reply exactly: {FALLBACK_RESPONSE}\n\n"
        f"KABISA KNOWLEDGE BASE CONTEXT:\n{context}\n\n"
        f"USER QUESTION:\n{message_body}"
    )
