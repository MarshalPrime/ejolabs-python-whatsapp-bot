import os
import requests
import logging

def generate_ejochat_response(message_body):
    api_key = os.getenv("EJOCHAT_API_KEY") or os.getenv("EjoChat_API_KEY")
    api_url = os.getenv("EJOCHAT_API_URL") or os.getenv("EjoChat_API_URL") or "https://ejolabs.com/api/v1/subiza"
    
    if not api_key:
        logging.error("EJOCHAT_API_KEY / EjoChat_API_KEY is not set in environment.")
        return "Nta gishya (EjoChat API Key is missing)."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful WhatsApp assistant. Respond naturally and concisely in Kinyarwanda or English depending on what the user speaks."
            },
            {
                "role": "user",
                "content": message_body
            }
        ]
    }
    
    try:
        logging.info(f"Sending request to EjoChat API: {api_url}")
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        return answer.strip()
    except Exception as e:
        logging.error(f"EjoChat API call failed: {e}")
        return "Habaye ikibazo mu gusubiza (Error connecting to EjoChat)."
