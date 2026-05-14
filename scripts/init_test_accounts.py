#!/usr/bin/env python3
"""Initialize test accounts from docs/TestAccount.md."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "backend"))

from app.db import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


def load_accounts(path: Path) -> list[tuple[str, str | None]]:
    accounts: list[tuple[str, str | None]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(">") or line.startswith("```") or line.startswith("<"):
            continue
        parts = line.split()
        if not parts:
            continue
        student_no = parts[0]
        if student_no.startswith("<"):
            continue
        name = "".join(parts[1:]) if len(parts) > 1 else None
        accounts.append((student_no, name))
    return accounts


def init_accounts() -> None:
    source = ROOT_DIR / "docs" / "TestAccount.md"
    if not source.exists():
        raise FileNotFoundError(f"TestAccount file not found: {source}")

    accounts = load_accounts(source)
    if not accounts:
        print("No test accounts found.")
        return

    session = SessionLocal()
    created = 0
    skipped = 0
    try:
        for student_no, _name in accounts:
            existing = session.query(User).filter(User.username == student_no).first()
            if existing:
                skipped += 1
                continue
            user = User(
                username=student_no,
                email=None,
                hashed_password=hash_password(student_no),
            )
            session.add(user)
            created += 1
        session.commit()
    finally:
        session.close()

    print(f"Created {created} accounts, skipped {skipped} existing.")


if __name__ == "__main__":
    init_accounts()
