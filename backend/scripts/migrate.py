import os
import sqlite3
from datetime import datetime

from app import DB_PATH, init_db


def ensure_default_conversations(conn):
    users = conn.execute("SELECT id, username FROM users").fetchall()
    created = 0
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for user in users:
        has_conv = conn.execute(
            "SELECT 1 FROM conversations WHERE user_id = ? LIMIT 1",
            (user["id"],),
        ).fetchone()
        if not has_conv:
            conn.execute(
                """
                INSERT INTO conversations (user_id, title, status, created_at, updated_at)
                VALUES (?, ?, 'active', ?, ?)
                """,
                (user["id"], "默认会话", now, now),
            )
            created += 1
    conn.commit()
    return created


def migrate():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    init_db()
    conn = sqlite3.connect(DB_PATH)
    created = ensure_default_conversations(conn)
    conn.close()
    if created:
        print(f"迁移完成，新增默认会话 {created} 个。")
    else:
        print("迁移完成，无需新增默认会话。")


if __name__ == "__main__":
    migrate()
