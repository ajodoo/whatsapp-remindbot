import os, json, logging, requests, tempfile
from datetime import datetime
import pytz
from groq import Groq

BOG = pytz.timezone("America/Bogota")

def get_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

def transcribe_audio(media_id: str) -> str | None:
    token = os.getenv("WHATSAPP_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"https://graph.facebook.com/v20.0/{media_id}", headers=headers, timeout=10)
    r.raise_for_status()
    media_url = r.json().get("url")
    if not media_url:
        return None
    r = requests.get(media_url, headers=headers, timeout=30)
    r.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(r.content)
        tmp_path = tmp.name
    try:
        client = get_client()
        with open(tmp_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(tmp_path), f.read()),
                model="whisper-large-v3-turbo",
                language="es",
                response_format="text"
            )
        return transcription.strip()
    except Exception as e:
        logging.error(f"Error transcribiendo: {e}")
        return None
    finally:
        os.unlink(tmp_path)

def parse_reminders(text: str) -> list | None:
    # Hora actual en Colombia
    now_bog = datetime.now(BOG).strftime("%Y-%m-%d %H:%M")

    system = (
        "Eres un parser de recordatorios para WhatsApp. "
        "Recibes mensajes en espanol colombiano y extraes TODAS las tareas con fecha y hora. "
        "La zona horaria es America/Bogota (UTC-5). "
        "IMPORTANTE: El campo datetime SIEMPRE debe estar en hora de Colombia (UTC-5), NO en UTC. "
        "Responde UNICAMENTE con un array JSON valido. Sin markdown. Sin texto extra."
    )

    prompt = f"""Fecha y hora actual en Colombia: {now_bog} (UTC-5, America/Bogota)

Mensaje: "{text}"

Extrae TODOS los recordatorios. Para cada uno:
{{"task":"descripcion","datetime":"YYYY-MM-DDTHH:MM:00","datetime_display":"ej: hoy a las 11:45 PM","repeat":null}}

IMPORTANTE: El datetime debe ser en hora Colombia (UTC-5).
Cuando digan "en la manana" usa 08:00, "en la tarde" usa 15:00, "en la noche" usa 20:00.
Si NO hay recordatorios responde: []
Responde SOLO el array JSON."""

    try:
        client = get_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.1
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result if result else None
    except json.JSONDecodeError:
        logging.error(f"JSON invalido: {raw}")
        return None
    except Exception as e:
        logging.error(f"Error parser: {e}")
        return None
