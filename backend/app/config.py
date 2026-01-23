import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
LOG_DIR = Path(os.environ.get("LOG_DIR", PROJECT_ROOT / ".logs"))

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://localhost:5432/autochat")

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-this-secret")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

AGENT_ENV_PREFIXES = {
    "ideological": "IDEOLOGICAL",
    "evaluation": "EVALUATION",
    "task": "TASK",
    "exploration": "EXPLORATION",
    "competition": "COMPETITION",
    "course": "COURSE",
}

SUMMARY_API_KEY = os.environ.get("SUMMARY_API_KEY", "")
SUMMARY_BASE_URL = os.environ.get("SUMMARY_BASE_URL", "")
SUMMARY_MODEL = os.environ.get("SUMMARY_MODEL", "")

EXTERNAL_API_BASE_URL = os.environ.get("EXTERNAL_API_BASE_URL", "http://localhost:3000")
EXTERNAL_JWT_SECRET = os.environ.get("EXTERNAL_JWT_SECRET", "external-jwt-dev-secret")
EXTERNAL_JWT_ISSUER = os.environ.get("EXTERNAL_JWT_ISSUER", "external-system")
EXTERNAL_JWT_AUDIENCE = os.environ.get("EXTERNAL_JWT_AUDIENCE", "course-analysis-external")
EXTERNAL_JWT_EXPIRE_MINUTES = int(os.environ.get("EXTERNAL_JWT_EXPIRE_MINUTES", "60"))
EXTERNAL_API_TIMEOUT = float(os.environ.get("EXTERNAL_API_TIMEOUT", "6"))

ACHIEVE_DB_DSN = os.environ.get("ACHIEVE_DB_DSN", "")
SYNC_TERM_WINDOW = os.environ.get("SYNC_TERM_WINDOW", "")
SYNC_BATCH_SIZE = int(os.environ.get("SYNC_BATCH_SIZE", "2000"))
SYNC_SCHEDULE_CRON = os.environ.get("SYNC_SCHEDULE_CRON", "0 3 * * *")


def get_agent_credentials(agent: str) -> tuple[str, str]:
    prefix = AGENT_ENV_PREFIXES.get(agent)
    if not prefix:
        return "", ""
    return (
        os.environ.get(f"{prefix}_API_KEY", ""),
        os.environ.get(f"{prefix}_BASE_URL", ""),
    )


def get_agent_model(agent: str) -> str:
    prefix = AGENT_ENV_PREFIXES.get(agent)
    if not prefix:
        return ""
    return os.environ.get(f"{prefix}_MODEL", "")

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://localhost:5174,http://127.0.0.1:5174"
    ).split(",")
    if origin.strip()
]
