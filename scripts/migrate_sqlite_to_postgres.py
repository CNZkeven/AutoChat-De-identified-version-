import json
import os
import sqlite3

import psycopg

SQLITE_PATH = os.environ.get(
    "SQLITE_PATH", os.path.join(os.path.dirname(__file__), "..", "database", "agent_db.sqlite")
)
POSTGRES_URL = os.environ.get("DATABASE_URL", "")
DEFAULT_AGENT = os.environ.get("DEFAULT_AGENT", "task")

TABLES = [
    "users",
    "chat_sessions",
    "chat_messages",
    "knowledge",
    "knowledge_embeddings",
    "tools",
    "courses",
    "course_relationships",
    "course_prerequisite_association",
    "course_related_association",
    "sessions",
    "course_logs",
]

BOOLEAN_COLUMNS = {
    "users": {"is_active"},
    "knowledge": {"is_active"},
    "courses": {"is_active", "is_exam_course", "is_investigation_course"},
    "course_relationships": {"is_confirmed"},
}


def fetch_rows(connection, table_name):
    cursor = connection.execute(f"SELECT * FROM {table_name}")
    columns = [desc[0] for desc in cursor.description]
    return columns, cursor.fetchall()


def ensure_sequence(conn, table_name):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT setval(pg_get_serial_sequence(%s, 'id'), COALESCE(MAX(id), 1)) FROM "
            + table_name,
            (table_name,),
        )


def parse_json(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def coerce_bool(value):
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str) and value in {"0", "1"}:
        return value == "1"
    return value


def apply_boolean_casts(payload: dict, table_name: str) -> None:
    for key in BOOLEAN_COLUMNS.get(table_name, set()):
        if key in payload:
            payload[key] = coerce_bool(payload[key])


def normalize_postgres_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def resolve_postgres_url() -> str:
    if POSTGRES_URL:
        return normalize_postgres_url(POSTGRES_URL)
    env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip().startswith("DATABASE_URL="):
                    _, value = line.split("=", 1)
                    return normalize_postgres_url(value.strip())
    raise SystemExit("DATABASE_URL is required")


def main():
    postgres_url = resolve_postgres_url()

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    with psycopg.connect(postgres_url) as pg_conn:
        pg_conn.execute("SET session_replication_role = replica")
        for table in TABLES:
            columns, rows = fetch_rows(sqlite_conn, table)
            if not rows:
                continue

            if table == "chat_sessions":
                dest_table = "conversations"
                dest_columns = [
                    "id",
                    "user_id",
                    "title",
                    "agent",
                    "status",
                    "created_at",
                    "updated_at",
                ]
                insert_sql = (
                    "INSERT INTO conversations (id, user_id, title, agent, status, created_at, updated_at) "
                    "VALUES (%(id)s, %(user_id)s, %(title)s, %(agent)s, %(status)s, %(created_at)s, %(updated_at)s) "
                    "ON CONFLICT DO NOTHING"
                )
                payloads = []
                for row in rows:
                    payload = {
                        "id": row["id"],
                        "user_id": row["user_id"],
                        "title": row["title"],
                        "agent": DEFAULT_AGENT,
                        "status": "active",
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                    apply_boolean_casts(payload, dest_table)
                    payloads.append(payload)
            elif table == "chat_messages":
                dest_table = "messages"
                dest_columns = [
                    "id",
                    "conversation_id",
                    "user_id",
                    "role",
                    "content",
                    "created_at",
                ]
                insert_sql = (
                    "INSERT INTO messages (id, conversation_id, user_id, role, content, created_at) "
                    "VALUES (%(id)s, %(conversation_id)s, %(user_id)s, %(role)s, %(content)s, %(created_at)s) "
                    "ON CONFLICT DO NOTHING"
                )
                payloads = []
                for row in rows:
                    payload = {
                        "id": row["id"],
                        "conversation_id": row["session_id"],
                        "user_id": row["user_id"],
                        "role": row["role"],
                        "content": row["content"],
                        "created_at": row["created_at"],
                    }
                    apply_boolean_casts(payload, dest_table)
                    payloads.append(payload)
            elif table == "users":
                dest_table = "users"
                dest_columns = [
                    "id",
                    "username",
                    "email",
                    "hashed_password",
                    "is_active",
                    "created_at",
                    "updated_at",
                ]
                insert_sql = (
                    "INSERT INTO users (id, username, email, hashed_password, is_active, created_at, updated_at) "
                    "VALUES (%(id)s, %(username)s, %(email)s, %(hashed_password)s, %(is_active)s, %(created_at)s, %(updated_at)s) "
                    "ON CONFLICT DO NOTHING"
                )
                payloads = []
                for row in rows:
                    payload = {
                        "id": row["id"],
                        "username": row["username"],
                        "email": row["email"],
                        "hashed_password": row["hashed_password"],
                        "is_active": row["is_active"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                    apply_boolean_casts(payload, dest_table)
                    payloads.append(payload)
            elif table == "knowledge_embeddings":
                dest_table = "knowledge_embeddings"
                dest_columns = [
                    "id",
                    "knowledge_id",
                    "chunk_index",
                    "chunk_text",
                    "embedding",
                    "created_at",
                ]
                insert_sql = (
                    "INSERT INTO knowledge_embeddings (id, knowledge_id, chunk_index, chunk_text, embedding, created_at) "
                    "VALUES (%(id)s, %(knowledge_id)s, %(chunk_index)s, %(chunk_text)s, %(embedding)s, %(created_at)s) "
                    "ON CONFLICT DO NOTHING"
                )
                payloads = []
                for row in rows:
                    payload = {
                        "id": row["id"],
                        "knowledge_id": row["knowledge_id"],
                        "chunk_index": row["chunk_index"],
                        "chunk_text": row["chunk_text"],
                        "embedding": json.dumps(parse_json(row["embedding"]))
                        if row["embedding"] is not None
                        else None,
                        "created_at": row["created_at"],
                    }
                    apply_boolean_casts(payload, dest_table)
                    payloads.append(payload)
            elif table == "tools":
                dest_table = "tools"
                dest_columns = ["id", "name", "description", "parameters_schema", "created_at"]
                insert_sql = (
                    "INSERT INTO tools (id, name, description, parameters_schema, created_at) "
                    "VALUES (%(id)s, %(name)s, %(description)s, %(parameters_schema)s, %(created_at)s) "
                    "ON CONFLICT DO NOTHING"
                )
                payloads = []
                for row in rows:
                    payload = {
                        "id": row["id"],
                        "name": row["name"],
                        "description": row["description"],
                        "parameters_schema": json.dumps(parse_json(row["parameters_schema"])),
                        "created_at": row["created_at"],
                    }
                    apply_boolean_casts(payload, dest_table)
                    payloads.append(payload)
            else:
                dest_table = table
                dest_columns = columns
                column_list = ", ".join(columns)
                placeholders = ", ".join([f"%({col})s" for col in columns])
                insert_sql = (
                    f"INSERT INTO {table} ({column_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                )
                payloads = []
                for row in rows:
                    payload = dict(row)
                    apply_boolean_casts(payload, dest_table)
                    payloads.append(payload)

            if not payloads:
                continue

            with pg_conn.cursor() as cur:
                cur.executemany(insert_sql, payloads)

            if "id" in dest_columns:
                ensure_sequence(pg_conn, dest_table)

        pg_conn.execute("SET session_replication_role = DEFAULT")
        pg_conn.commit()

    sqlite_conn.close()


if __name__ == "__main__":
    main()
