import os, json, logging, requests, tempfile
from datetime import datetime
from groq import Groq

def get_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

# ──────────────────────────────────────────────────────────────────────────────
#  PASO 1: Descargar audio de Meta y transcribir con Whisper (gratis)
# ──────────────────────────────────────────────────────────────────────────────

def transcribe_audio(media_id: str) -> str | None:
    """Descarga el audio de WhatsApp y lo transcribe con Groq Whisper. Gratis."""
    token = os.getenv("WHATSAPP_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(
        f"https://graph.facebook.com/v20.0/{media_id}",
        headers=headers, timeout=10
    )
    r.raise_for_status()
    media_url = r.json().get("url")
    if not media_url:
        logging.error("No se obtuvo URL del audio")
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
        text = transcription.strip()
        logging.info(f"Transcripcion: {text}")
        return text
    except Exception as e:
        logging.error(f"Error transcribiendo audio: {e}")
        return None
    finally:
        os.unlink(tmp_path)


# ──────────────────────────────────────────────────────────────────────────────
#  PASO 2: Parsear texto con LLaMA 3.3 y extraer recordatorios (gratis)
# ──────────────────────────────────────────────────────────────────────────────

def parse_reminders(text: str) -> list | None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    system = (
        "Eres un parser de recordatorios para WhatsApp. "
        "Recibes mensajes en espanol y extraes TODAS las tareas con su fecha y hora. "
        "Un mensaje puede tener varias tareas. "
        "Responde UNICAMENTE con un array JSON valido. Sin markdown. Sin texto extra."
    )

    prompt = f"""Fecha y hora actual: {now} (Colombia, UTC-5)

Mensaje: "{text}"

Extrae TODOS los recordatorios del mensaje. Para cada uno responde un objeto asi:
{{"task":"descripcion de la tarea","datetime":"YYYY-MM-DDTHH:MM:00","datetime_display":"ej: manana a las 3:00 PM","repeat":null}}

Valores validos de repeat: null | "daily" | "weekly" | "monthly"
Cuando digan "en la manana" usa 08:00, "en la tarde" usa 15:00, "en la noche" usa 20:00.
Si NO hay ningun recordatorio responde: []
Responde SOLO el array JSON."""

    try:
        client = get_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt}
            ],
            max_tokens=500,
            temperature=0.1
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result if result else None

    except json.JSONDecodeError:
        logging.error(f"LLaMA retorno JSON invalido: {raw}")
        return None
    except Exception as e:
        logging.error(f"Error en groq_parser: {e}")
        return None
