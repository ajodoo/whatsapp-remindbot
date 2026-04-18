import requests, os, logging

WHATSAPP_TOKEN  = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

def send_message(phone: str, text: str) -> bool:
    """Envía mensaje de texto simple."""
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}",
               "Content-Type": "application/json"}
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
        return True
    except requests.RequestException as e:
        logging.error(f"Error WhatsApp texto → {phone}: {e}")
        return False

def send_reminder_with_button(phone: str, task: str, reminder_id: int) -> bool:
    """Envía recordatorio con botón interactivo 'Finalizado'."""
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}",
               "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": f"🔔 *Recordatorio:*\n\n{task}"},
            "action": {
                "buttons": [{
                    "type": "reply",
                    "reply": {
                        "id": f"done_{reminder_id}",
                        "title": "✅ Finalizado"
                    }
                }]
            }
        }
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        logging.info(f"Recordatorio con botón enviado a {phone}")
        return True
    except requests.RequestException as e:
        logging.error(f"Error botón → {phone}: {e} | {r.text if 'r' in dir() else ''}")
        # Fallback a mensaje simple si falla el botón
        return send_message(phone,
            f"🔔 *Recordatorio:*\n\n{task}\n\nResponde *finalizado* cuando lo completes.")
