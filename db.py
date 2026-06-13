import sqlite3
from datetime import datetime, timezone
from typing import Optional
from config import DB_PATH


def _connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS photos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id  INTEGER NOT NULL,
                group_id    INTEGER NOT NULL,
                group_name  TEXT,
                sender_id   INTEGER,
                sender_name TEXT,
                date        TEXT NOT NULL,
                file_hash   TEXT,
                phash       TEXT,
                thumb_path  TEXT,
                full_path   TEXT,
                UNIQUE(message_id, group_id)
            );
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_file_hash ON photos(file_hash);
            CREATE INDEX IF NOT EXISTS idx_phash     ON photos(phash);
        """)


def save_photo(message_id, group_id, group_name, sender_id, sender_name,
               date, file_hash, phash, thumb_path, full_path):
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO photos
                (message_id, group_id, group_name, sender_id, sender_name,
                 date, file_hash, phash, thumb_path, full_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (message_id, group_id, group_name, sender_id, sender_name,
              date, file_hash, phash, thumb_path, full_path))


def get_last_run(group_id: int) -> Optional[datetime]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = ?",
            (f"last_run_{group_id}",)
        ).fetchone()
    if row:
        return datetime.fromisoformat(row[0])
    return None


def set_last_run(group_id: int, dt: datetime):
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (f"last_run_{group_id}", dt.isoformat())
        )


def clear_group(group_id: int):
    with _connect() as conn:
        conn.execute("DELETE FROM photos WHERE group_id = ?", (group_id,))


def clear_group_by_name(group_name: str):
    with _connect() as conn:
        conn.execute("DELETE FROM photos WHERE group_name = ?", (group_name,))


def update_group_name(group_id: int, group_name: str):
    with _connect() as conn:
        conn.execute(
            "UPDATE photos SET group_name = ? WHERE group_id = ?",
            (group_name, group_id)
        )


def clear_all():
    with _connect() as conn:
        conn.executescript("DELETE FROM photos; DELETE FROM meta;")


def get_all_photos() -> "list[dict]":
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM photos ORDER BY date").fetchall()
    return [dict(r) for r in rows]


def get_photos_by_groups(group_ids: "list[int]") -> "list[dict]":
    placeholders = ",".join("?" * len(group_ids))
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT * FROM photos WHERE group_id IN ({placeholders}) ORDER BY date",
            group_ids
        ).fetchall()
    return [dict(r) for r in rows]
