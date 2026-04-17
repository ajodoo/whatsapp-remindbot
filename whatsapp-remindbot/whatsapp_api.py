import requests
import os
import logging

WHATSAPP_TOKEN   = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID  = os.getenv("PHONE_NUMBER_ID")

def send_message(phone: str, text: str) -> bool:
    """Envía un mensaje WhatsApp. NO gasta tokens de Claude."""
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "text",
        "text": {"body": text, "preview_url": False}
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        logging.info(f"Mensaje enviado a {phone}")
        return True
    except requests.RequestException as e:
        logging.error(f"Error WhatsApp → {phone}: {e}")
        return False
