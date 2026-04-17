from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import os, logging
from datetime import datetime

from database     import (init_db, save_reminder, get_pending_reminders,
                           mark_reminded, mark_done, get_last_reminded,
                           get_pending_for_user, schedule_next)
from whatsapp_api import send_message
from groq_parser  import transcribe_audio, parse_reminders

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")

app = Flask(__name__)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "remindbot_secret")
CHECK_KEY    = os.getenv("CHECK_KEY",    "check_secret")

DONE_WORDS = {
    "finalizado", "listo", "hecho", "done", "ok",
    "completado", "terminé", "termine", "ya", "listo gracias"
}
LIST_WORDS = {
    "mis recordatorios", "lista", "pendientes",
    "qué tengo", "que tengo", "ver recordatorios"
}

# ──────────────────────────────────────────────────────────────────────────────
#  WEBHOOK
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/webhook", methods=["GET"])
def verify():
    if (request.args.get("hub.mode") == "subscribe" and
            request.args.get("hub.verify_token") == VERIFY_TOKEN):
        logging.info("Webhook verificado ✓")
        return request.args.get("hub.challenge"), 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    try:
        value = (data.get("entry", [{}])[0]
                     .get("changes", [{}])[0]
                     .get("value", {}))

        if "messages" not in value:
            return "ok", 200

        msg   = value["messages"][0]
        phone = msg["from"]
        mtype = msg.get("type", "")

        # ── AUDIO: Whisper transcribe → LLaMA parsea ──────────────────────────
        if mtype == "audio":
            send_message(phone, "🎙️ Escuchando tu audio...")
            media_id = msg["audio"]["id"]
            text = transcribe_audio(media_id)

            if not text:
                send_message(phone, "❌ No pude escuchar el audio. Intenta de nuevo o escríbelo.")
                return "ok", 200

            _procesar_recordatorios(phone, text)
            return "ok", 200

        # ── TEXTO ─────────────────────────────────────────────────────────────
        if mtype != "text":
            return "ok", 200

        text  = msg["text"]["body"].strip()
        lower = text.lower()

        if any(w in lower for w in LIST_WORDS):
            _cmd_lista(phone)
            return "ok", 200

        if any(lower == w or lower.startswith(w) for w in DONE_WORDS):
            _cmd_finalizado(phone)
            return "ok", 200

        _procesar_recordatorios(phone, text)

    except Exception as e:
        logging.error(f"Error en webhook: {e}", exc_info=True)

    return "ok", 200


# ──────────────────────────────────────────────────────────────────────────────
#  LÓGICA COMPARTIDA
# ──────────────────────────────────────────────────────────────────────────────

def _procesar_recordatorios(phone: str, text: str):
    reminders = parse_reminders(text)

    if not reminders:
        send_message(phone,
            "No encontré recordatorios 🤔\n\n"
            "*Ejemplos:*\n"
            "• _Mañana a las 3pm llamar al proveedor_\n"
            "• _El viernes 9am reunión con el equipo_\n"
            "• _Mañana llevar documentos, en la tarde revisar campañas_")
        return

    for r in reminders:
        save_reminder(phone, r["task"], r["datetime"], r.get("repeat"))

    if len(reminders) == 1:
        r = reminders[0]
        resp = f"✅ ¡Recordatorio guardado!\n\n📌 *{r['task']}*\n🕐 {r['datetime_display']}"
        if r.get("repeat"):
            labels = {"daily":"cada día","weekly":"cada semana","monthly":"cada mes"}
            resp += f"\n🔁 Se repite {labels.get(r['repeat'], r['repeat'])}"
        send_message(phone, resp)
    else:
        lines = [f"✅ ¡{len(reminders)} recordatorios guardados!\n"]
        for i, r in enumerate(reminders, 1):
            lines.append(f"{i}. 📌 *{r['task']}*\n    🕐 {r['datetime_display']}")
        send_message(phone, "\n".join(lines))


def _cmd_lista(phone: str):
    pending = get_pending_for_user(phone)
    if not pending:
        send_message(phone, "📭 No tienes recordatorios pendientes.")
        return
    lines = ["📋 *Tus recordatorios pendientes:*\n"]
    for i, r in enumerate(pending, 1):
        dt  = datetime.fromisoformat(r["remind_at"])
        rep = " 🔁" if r.get("repeat") else ""
        lines.append(f"{i}. {r['task']}{rep}\n   🕐 {dt.strftime('%d/%m/%Y %H:%M')}")
    send_message(phone, "\n".join(lines))


def _cmd_finalizado(phone: str):
    reminder = get_last_reminded(phone)
    if reminder:
        mark_done(reminder["id"])
        send_message(phone, f"✅ *{reminder['task']}* marcado como finalizado.")
    else:
        send_message(phone,
            "No encontré ningún recordatorio activo.\n"
            "¿Quieres crear uno? Escríbeme o mándame un audio.")


# ──────────────────────────────────────────────────────────────────────────────
#  SCHEDULER — 100% gratis, sin IA
# ──────────────────────────────────────────────────────────────────────────────

def check_and_send():
    reminders = get_pending_reminders()
    for r in reminders:
        logging.info(f"Enviando recordatorio {r['id']} → {r['phone']}")
        ok = send_message(r["phone"],
            f"🔔 *Recordatorio:*\n\n{r['task']}\n\n"
            "Responde *finalizado* cuando lo hayas completado.")
        if ok:
            mark_reminded(r["id"])
            if r.get("repeat"):
                schedule_next(r)


@app.route("/check", methods=["GET", "POST"])
def check_endpoint():
    key = request.args.get("key") or (request.json or {}).get("key", "")
    if key != CHECK_KEY:
        return "Forbidden", 403
    check_and_send()
    return "ok", 200


# ──────────────────────────────────────────────────────────────────────────────
#  INICIO
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    scheduler = BackgroundScheduler(timezone="America/Bogota")
    scheduler.add_job(check_and_send, "interval", minutes=1, id="check_reminders")
    scheduler.start()
    logging.info("🤖 RemindBot activo (100% gratis)")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
