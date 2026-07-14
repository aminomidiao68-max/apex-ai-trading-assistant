from __future__ import annotations

import os
from uuid import uuid4

import pytest

from app.models import (
    AuthLoginRequest,
    AuthRegisterRequest,
    MarketType,
    SignalDirection,
    TradeJournalCloseRequest,
    TradeJournalCreateRequest,
)
from app.services.auth_service import AuthService
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.storage_service import StorageService


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
pytestmark = pytest.mark.skipif(
    not DATABASE_URL.startswith(("postgresql://", "postgres://")),
    reason="PostgreSQL integration DATABASE_URL is not configured",
)


def test_postgresql_migration_auth_and_user_scoped_journal_roundtrip():
    database = DatabaseManager(database_url=DATABASE_URL)
    assert database.backend == "postgresql"
    health = database.health()
    assert health["connected"] is True
    assert health["persistent"] is True
    assert health["schema_version"] == LATEST_SCHEMA_VERSION
    assert health["migration_current"] is True

    auth = AuthService(seed_demo_user=False)
    storage = StorageService()
    email = f"postgres-rc-{uuid4().hex}@example.com"
    registered = auth.register(
        AuthRegisterRequest(name="Postgres RC", email=email, password="StrongPass123!")
    )
    user_id = registered.user.id
    assert auth.get_user_by_token(registered.access_token).id == user_id
    logged_in = auth.login(AuthLoginRequest(email=email, password="StrongPass123!"))
    assert logged_in.user.id == user_id

    trade = storage.create_trade(
        TradeJournalCreateRequest(
            symbol="BTCUSDT",
            market=MarketType.crypto,
            direction=SignalDirection.buy,
            entry_price=100,
            stop_loss=98,
            take_profit=104,
            size=1,
            notes="postgres integration",
        ),
        user_id=user_id,
    )
    assert trade.id > 0
    assert [item.id for item in storage.list_trades(user_id=user_id)] == [trade.id]
    closed = storage.close_trade(
        trade.id,
        TradeJournalCloseRequest(exit_price=104, pnl_amount=4, notes="closed"),
        user_id=user_id,
    )
    assert closed.status == "closed"
    assert storage.get_trade_stats(user_id=user_id).net_pnl == 4
    storage.delete_trade(trade.id, user_id=user_id)
    auth.logout(registered.access_token)
    auth.logout(logged_in.access_token)

    with database.connection() as conn:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
