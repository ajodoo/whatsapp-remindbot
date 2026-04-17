import sqlite3
import os
import logging
from datetime import datetime, timedelta

DB_PATH = os.getenv("DB_PATH", "reminders.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                phone       TEXT    NOT NULL,
                task        TEXT    NOT NULL,
                remind_at   TEXT    NOT NULL,
                repeat      TEXT,
                status      TEXT    DEFAULT 'pending',
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.commit()
    logging.info("DB lista")

# ── Guardar un nuevo recordatorio ──────────────────────────────────────────────
def save_reminder(phone: str, task: str, remind_at: str, repeat: str = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO reminders (phone, task, remind_at, repeat) VALUES (?,?,?,?)",
            (phone, task, remind_at, repeat)
        )
        conn.commit()
        return cur.lastrowid

# ── Recordatorios que ya vencieron y están pendientes ─────────────────────────
def get_pending_reminders() -> list[dict]:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:00")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE status='pending' AND remind_at <= ?", (now,)
        ).fetchall()
    return [dict(r) for r in rows]

# ── Estado: pendiente → avisado ───────────────────────────────────────────────
def mark_reminded(reminder_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE reminders SET status='reminded' WHERE id=?", (reminder_id,))
        conn.commit()

# ── Estado: avisado/pendiente → finalizado ────────────────────────────────────
def mark_done(reminder_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE reminders SET status='done' WHERE id=?", (reminder_id,))
        conn.commit()

# ── Último recordatorio que se avisó (para el "finalizado") ───────────────────
def get_last_reminded(phone: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM reminders WHERE phone=? AND status='reminded' ORDER BY remind_at DESC LIMIT 1",
            (phone,)
        ).fetchone()
    return dict(row) if row else None

# ── Lista de pendientes del usuario ───────────────────────────────────────────
def get_pending_for_user(phone: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE phone=? AND status='pending' ORDER BY remind_at ASC",
            (phone,)
        ).fetchall()
    return [dict(r) for r in rows]

# ── Programar la siguiente ocurrencia (para recordatorios repetitivos) ─────────
def schedule_next(reminder: dict):
    dt = datetime.fromisoformat(reminder["remind_at"])
    repeat = reminder.get("repeat")

    if repeat == "daily":
        next_dt = dt + timedelta(days=1)
    elif repeat == "weekly":
        next_dt = dt + timedelta(weeks=1)
    elif repeat == "monthly":
        m = dt.month % 12 + 1
        y = dt.year + (1 if dt.month == 12 else 0)
        try:
            next_dt = dt.replace(year=y, month=m)
        except ValueError:
            next_dt = dt.replace(year=y, month=m, day=28)
    else:
        return

    save_reminder(reminder["phone"], reminder["task"],
                  next_dt.strftime("%Y-%m-%dT%H:%M:00"), repeat)
    logging.info(f"Próximo recordatorio programado: {next_dt}")
