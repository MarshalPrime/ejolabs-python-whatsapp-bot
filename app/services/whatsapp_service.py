import json
import logging

import requests
from flask import current_app, jsonify


def _graph_url():
    return (
        f"https://graph.facebook.com/{current_app.config['VERSION']}/"
        f"{current_app.config['PHONE_NUMBER_ID']}/messages"
    )


def _headers():
    return {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }


def _send_payload(payload, timeout=10):
    try:
        response = requests.post(
            _graph_url(), data=json.dumps(payload), headers=_headers(), timeout=timeout
        )
        response.raise_for_status()
    except requests.Timeout:
        logging.error("Timeout occurred while sending WhatsApp message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except requests.RequestException as exc:
        logging.error("WhatsApp send failed: %s", exc)
        return jsonify({"status": "error", "message": "Failed to send message"}), 500

    logging.info("WhatsApp send status=%s body=%s", response.status_code, response.text)
    return response


def send_text_message(recipient, text):
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    return _send_payload(payload)


def send_image_message(recipient, image_url, caption=None):
    image = {"link": image_url}
    if caption:
        image["caption"] = caption[:1024]

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "image",
        "image": image,
    }
    return _send_payload(payload)
