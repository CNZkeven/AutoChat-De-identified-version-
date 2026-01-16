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


def get_agent_credentials(agent: str) -> tuple[str, str]:
    prefix = AGENT_ENV_PREFIXES.get(agent)
    if not prefix:
        return "", ""
    return (
        os.environ.get(f"{prefix}_API_KEY", ""),
        os.environ.get(f"{prefix}_BASE_URL", ""),
    )

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
