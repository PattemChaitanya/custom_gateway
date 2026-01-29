# Backend

Quick start (local):

1. Create and activate a Python virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and set values.

3. Run migrations:

```bash
python -m alembic -c alembic.ini upgrade head
```

4. Start the app:

```bash
uvicorn app.main:app --reload --port 8000
```

5. Run tests:

```bash
pytest -q
```

Notes:
- Use a real secret and salt in production, and store them in a secrets manager or CI secrets.
- The project uses async SQLAlchemy with `aiosqlite` for local development. For production use Postgres and set `DATABASE_URL` accordingly.

## CI / Secrets

This project requires two secrets to be set in CI for running migrations and tests:

- `JWT_SECRET` - secret used to sign JWT access/refresh tokens.
- `REFRESH_TOKEN_SALT` - server-side secret used to HMAC refresh token jti values before storing.

Set these in GitHub repository settings under **Settings → Secrets → Actions**.

The included GitHub Actions workflow will fail early if these secrets are not present.
