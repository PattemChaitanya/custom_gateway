#!/usr/bin/env python3
"""Generate a backend/.env file with strong random secrets for local dev.

Usage: python backend/scripts/generate_env.py
"""
import secrets
from pathlib import Path

env_path = Path(__file__).resolve().parents[1] / ".env"

values = {
    "DATABASE_URL": "sqlite+aiosqlite:///./dev.db",
    "JWT_SECRET": secrets.token_urlsafe(48),
    "REFRESH_TOKEN_SALT": secrets.token_urlsafe(48),
    "SQL_ECHO": "False",
}

lines = [f"{k}={v}" for k, v in values.items()]

env_path.write_text("\n".join(lines) + "\n")
print(f"Wrote {env_path}")
