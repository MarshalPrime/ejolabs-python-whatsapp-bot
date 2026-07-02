import os
import requests
import logging

from app.services.constants import FALLBACK_RESPONSE, looks_like_default_persona
from app.services.prompt_service import (
    build_kabisa_system_instruction,
    build_kabisa_user_prompt,
)


def generate_ejochat_response(message_body, context=None):
    api_key = os.getenv("EJOCHAT_API_KEY") or os.getenv("EjoChat_API_KEY")
    api_url = os.getenv("EJOCHAT_API_URL") or os.getenv("EjoChat_API_URL") or "https://ejolabs.com/api/v1/subiza"
    
    if not api_key:
        logging.error("EJOCHAT_API_KEY / EjoChat_API_KEY is not set in environment.")
        return FALLBACK_RESPONSE

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    if not context:
        return FALLBACK_RESPONSE

    system_message = build_kabisa_system_instruction()
    user_message = build_kabisa_user_prompt(message_body, context)

    payload = {
        "messages": [
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": user_message,
            }
        ]
    }
    
    try:
        logging.info(f"Sending request to EjoChat API: {api_url}")
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        if looks_like_default_persona(answer):
            logging.error("EjoChat returned default persona instead of Kabisa answer: %s", answer)
            return FALLBACK_RESPONSE
        return answer.strip()
    except Exception as e:
        logging.error(f"EjoChat API call failed: {e}")
        return FALLBACK_RESPONSE
