import sqlite3, os, logging
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
                last_sent   TEXT,
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)
        # Agregar columna last_sent si no existe (para DBs viejas)
        try:
            conn.execute("ALTER TABLE reminders ADD COLUMN last_sent TEXT")
        except:
            pass
        conn.commit()
    logging.info("DB lista")

def save_reminder(phone, task, remind_at, repeat=None):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO reminders (phone, task, remind_at, repeat) VALUES (?,?,?,?)",
            (phone, task, remind_at, repeat)
        )
        conn.commit()
        return cur.lastrowid

def get_pending_reminders():
    """Recordatorios que deben dispararse: vencidos Y (nunca enviados O enviados hace 30+ min)"""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:00")
    ago = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:00")
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM reminders
            WHERE status IN ('pending','reminded')
            AND remind_at <= ?
            AND (last_sent IS NULL OR last_sent <= ?)
        """, (now, ago)).fetchall()
    return [dict(r) for r in rows]

def mark_reminded(reminder_id):
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:00")
    with get_conn() as conn:
        conn.execute(
            "UPDATE reminders SET status='reminded', last_sent=? WHERE id=?",
            (now, reminder_id)
        )
        conn.commit()

def mark_done(reminder_id):
    with get_conn() as conn:
        conn.execute("UPDATE reminders SET status='done' WHERE id=?", (reminder_id,))
        conn.commit()

def mark_done_by_phone(phone):
    """Marca TODOS los recordatorios activos del usuario como finalizados"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE reminders SET status='done' WHERE phone=? AND status IN ('pending','reminded')",
            (phone,)
        )
        conn.commit()

def get_last_reminded(phone):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM reminders WHERE phone=? AND status='reminded' ORDER BY remind_at DESC LIMIT 1",
            (phone,)
        ).fetchone()
    return dict(row) if row else None

def get_reminded_by_id(reminder_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM reminders WHERE id=? AND status='reminded'", (reminder_id,)
        ).fetchone()
    return dict(row) if row else None

def get_pending_for_user(phone):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE phone=? AND status IN ('pending','reminded') ORDER BY remind_at ASC",
            (phone,)
        ).fetchall()
    return [dict(r) for r in rows]

def schedule_next(reminder):
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
