from __future__ import annotations

import asyncio
import base64
import json
import sqlite3

import pytest

from app.models import ProviderSecretUpsertRequest
from app.services.database_service import DatabaseManager, LATEST_SCHEMA_VERSION
from app.services.provider_secret_service import ProviderSecretService, ProviderVaultError


def _master_key() -> str:
    return base64.urlsafe_b64encode(b"k" * 32).decode()


def test_provider_secret_is_encrypted_user_scoped_and_never_read_back(tmp_path):
    database = DatabaseManager(db_path=str(tmp_path / "vault.db"))
    service = ProviderSecretService(database, master_key=_master_key())
    raw_secret = "test-provider-secret-value-123456"
    status = service.upsert(
        1,
        "groq",
        ProviderSecretUpsertRequest(
            api_key=raw_secret,
            model="test-model",
            enabled=True,
        ),
    )
    assert status.configured is True
    assert status.enabled is True
    assert status.model == "test-model"
    assert service.list_status(1).raw_secrets_returned is False
    assert service.list_status(2).providers[0].configured is False

    material = service.get_material(1, "groq")
    assert material is not None
    assert material.api_key == raw_secret
    assert service.get_material(2, "groq") is None

    with sqlite3.connect(database.sqlite_path) as conn:
        row = conn.execute(
            "SELECT ciphertext, nonce, metadata_json FROM user_provider_secrets WHERE user_id=1"
        ).fetchone()
    assert raw_secret.encode() not in bytes(row[0])
    assert len(bytes(row[1])) == 12
    assert raw_secret not in row[2]
    serialized = service.list_status(1).model_dump_json()
    assert raw_secret not in serialized
    assert database.schema_version() == LATEST_SCHEMA_VERSION == 5

    service.delete(1, "groq")
    assert service.get_material(1, "groq") is None


def test_oanda_requires_account_id_and_disabled_secret_is_not_resolved(tmp_path):
    service = ProviderSecretService(
        DatabaseManager(db_path=str(tmp_path / "oanda.db")),
        master_key=_master_key(),
    )
    with pytest.raises(ProviderVaultError, match="oanda_account_id_required"):
        service.upsert(
            1,
            "oanda",
            ProviderSecretUpsertRequest(api_key="practice-token-value"),
        )
    service.upsert(
        1,
        "oanda",
        ProviderSecretUpsertRequest(
            api_key="practice-token-value",
            account_id="practice-account-id",
            enabled=False,
        ),
    )
    assert service.get_material(1, "oanda") is None
    material = service.get_material(1, "oanda", require_enabled=False)
    assert material is not None and material.account_id == "practice-account-id"
    assert service.status_for(1, "oanda").has_account_id is True


def test_vault_fails_closed_without_or_with_wrong_master_key(tmp_path):
    database = DatabaseManager(db_path=str(tmp_path / "keys.db"))
    unavailable = ProviderSecretService(database, master_key="")
    assert unavailable.configured is False
    with pytest.raises(ProviderVaultError, match="provider_vault_not_configured"):
        unavailable.upsert(
            1,
            "openai",
            ProviderSecretUpsertRequest(api_key="some-openai-key"),
        )

    writer = ProviderSecretService(database, master_key=_master_key())
    writer.upsert(
        1,
        "openai",
        ProviderSecretUpsertRequest(api_key="encrypted-openai-key"),
    )
    wrong_key = base64.urlsafe_b64encode(b"z" * 32).decode()
    reader = ProviderSecretService(database, master_key=wrong_key)
    with pytest.raises(ProviderVaultError, match="provider_secret_decryption_failed"):
        reader.get_material(1, "openai")


def test_connection_result_is_sanitized_and_persisted(monkeypatch, tmp_path):
    service = ProviderSecretService(
        DatabaseManager(db_path=str(tmp_path / "probe.db")),
        master_key=_master_key(),
    )
    service.upsert(
        1,
        "finnhub",
        ProviderSecretUpsertRequest(api_key="finnhub-test-key-value"),
    )

    async def fake_probe(material):
        assert material.api_key == "finnhub-test-key-value"
        return "connected"

    monkeypatch.setattr(service, "_probe", fake_probe)
    result = asyncio.run(service.test_connection(1, "finnhub"))
    assert result.status == "connected"
    assert result.details_exposed is False
    assert result.live_execution_enabled is False
    status = service.status_for(1, "finnhub")
    assert status.last_test_status == "connected"
    assert "finnhub-test-key-value" not in result.model_dump_json()
