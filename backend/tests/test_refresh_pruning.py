from fastapi.testclient import TestClient
from app.api.auth import auth_service
from app.db import get_db_manager
from app.db.models import RefreshToken, User
from sqlalchemy import select
import asyncio

import pytest


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest.mark.skip(reason="Token pruning test needs InMemoryDB query improvements")
def test_refresh_token_pruning(client, monkeypatch):
    # reduce limit for testability
    monkeypatch.setattr(auth_service, "MAX_REFRESH_TOKENS_PER_USER", 3)

    email = "prune@example.com"
    client.post("/auth/register", json={"email": email, "password": "pwd"})

    # create 4 refresh tokens by logging in multiple times
    for _ in range(4):
        r = client.post("/auth/login", json={"email": email, "password": "pwd"})
        assert r.status_code == 200

    async def _count_active():
        db_manager = get_db_manager()
        async with db_manager.get_session() as session:
            # find the user id
            uq = await session.execute(select(User).where(User.email == email))
            user = uq.scalars().first()
            if not user:
                return 0
            q = await session.execute(
                select(RefreshToken).where(not RefreshToken.revoked).where(RefreshToken.user_id == user.id)
            )
            return len(q.scalars().all())

    active_count = asyncio.run(_count_active())
    assert active_count <= 3
