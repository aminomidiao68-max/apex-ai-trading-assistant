from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings
from app.models import (
    ProviderConnectionTestResponse,
    ProviderSecretStatus,
    ProviderSecretStatusResponse,
    ProviderSecretUpsertRequest,
)
from app.services.database_service import DatabaseManager


PROVIDERS = ("groq", "openai", "twelvedata", "finnhub", "newsapi", "oanda")
_DEFAULT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4.1-mini",
}


class ProviderVaultError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ProviderSecretMaterial:
    provider: str
    api_key: str
    account_id: str | None
    model: str | None
    enabled: bool


class ProviderSecretService:
    def __init__(
        self,
        database: DatabaseManager,
        master_key: str | None = None,
        key_version: int | None = None,
    ) -> None:
        self.database = database
        self.key_version = key_version or settings.user_secret_key_version
        self._key = self._decode_master_key(
            settings.user_secret_master_key if master_key is None else master_key
        )

    @property
    def configured(self) -> bool:
        return self._key is not None

    def _decode_master_key(self, value: str) -> bytes | None:
        raw = (value or "").strip()
        if not raw:
            return None
        try:
            if len(raw) == 64:
                decoded = bytes.fromhex(raw)
            else:
                padding = "=" * (-len(raw) % 4)
                decoded = base64.urlsafe_b64decode(raw + padding)
        except Exception as exc:
            raise ProviderVaultError("invalid_user_secret_master_key_encoding") from exc
        if len(decoded) != 32:
            raise ProviderVaultError("user_secret_master_key_must_be_32_bytes")
        return decoded

    def _aad(self, user_id: int, provider: str, key_version: int) -> bytes:
        return f"apex:user:{user_id}:provider:{provider}:v{key_version}".encode("utf-8")

    def _validate_provider(self, provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized not in PROVIDERS:
            raise ProviderVaultError("unsupported_provider")
        return normalized

    def upsert(
        self,
        user_id: int,
        provider: str,
        request: ProviderSecretUpsertRequest,
    ) -> ProviderSecretStatus:
        provider = self._validate_provider(provider)
        if not self.configured or self._key is None:
            raise ProviderVaultError("provider_vault_not_configured")
        account_id = request.account_id.get_secret_value().strip() if request.account_id else None
        if provider == "oanda" and not account_id:
            raise ProviderVaultError("oanda_account_id_required")
        model = (request.model or _DEFAULT_MODELS.get(provider) or "").strip() or None
        payload = json.dumps(
            {
                "api_key": request.api_key.get_secret_value().strip(),
                "account_id": account_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._key).encrypt(
            nonce,
            payload,
            self._aad(user_id, provider, self.key_version),
        )
        now = datetime.now(timezone.utc).isoformat()
        metadata = json.dumps(
            {"model": model, "has_account_id": bool(account_id)},
            separators=(",", ":"),
        )
        with self.database.connection() as conn:
            conn.execute(
                """
                INSERT INTO user_provider_secrets (
                    user_id, provider, ciphertext, nonce, key_version, enabled,
                    metadata_json, last_test_status, last_tested_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, provider) DO UPDATE SET
                    ciphertext = excluded.ciphertext,
                    nonce = excluded.nonce,
                    key_version = excluded.key_version,
                    enabled = excluded.enabled,
                    metadata_json = excluded.metadata_json,
                    last_test_status = NULL,
                    last_tested_at = NULL,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    provider,
                    ciphertext,
                    nonce,
                    self.key_version,
                    1 if request.enabled else 0,
                    metadata,
                    None,
                    None,
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.status_for(user_id, provider)

    def get_material(
        self,
        user_id: int,
        provider: str,
        require_enabled: bool = True,
    ) -> ProviderSecretMaterial | None:
        provider = self._validate_provider(provider)
        if not self.configured or self._key is None:
            return None
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_provider_secrets WHERE user_id = ? AND provider = ?",
                (user_id, provider),
            ).fetchone()
        if row is None:
            return None
        enabled = bool(row["enabled"])
        if require_enabled and not enabled:
            return None
        key_version = int(row["key_version"])
        try:
            plaintext = AESGCM(self._key).decrypt(
                bytes(row["nonce"]),
                bytes(row["ciphertext"]),
                self._aad(user_id, provider, key_version),
            )
            payload = json.loads(plaintext.decode("utf-8"))
            metadata = json.loads(row["metadata_json"] or "{}")
        except Exception as exc:
            raise ProviderVaultError("provider_secret_decryption_failed") from exc
        return ProviderSecretMaterial(
            provider=provider,
            api_key=str(payload.get("api_key") or ""),
            account_id=(str(payload["account_id"]) if payload.get("account_id") else None),
            model=(str(metadata["model"]) if metadata.get("model") else None),
            enabled=enabled,
        )

    def list_status(self, user_id: int) -> ProviderSecretStatusResponse:
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT provider, enabled, metadata_json, last_test_status, last_tested_at, updated_at "
                "FROM user_provider_secrets WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        row_map = {row["provider"]: row for row in rows}
        statuses = []
        for provider in PROVIDERS:
            row = row_map.get(provider)
            metadata = json.loads(row["metadata_json"] or "{}") if row else {}
            statuses.append(
                ProviderSecretStatus(
                    provider=provider,
                    configured=row is not None,
                    enabled=bool(row["enabled"]) if row else False,
                    has_account_id=bool(metadata.get("has_account_id")),
                    model=metadata.get("model"),
                    last_test_status=row["last_test_status"] if row else None,
                    last_tested_at=row["last_tested_at"] if row else None,
                    updated_at=row["updated_at"] if row else None,
                )
            )
        return ProviderSecretStatusResponse(
            vault_configured=self.configured,
            providers=statuses,
            raw_secrets_returned=False,
        )

    def status_for(self, user_id: int, provider: str) -> ProviderSecretStatus:
        provider = self._validate_provider(provider)
        return next(item for item in self.list_status(user_id).providers if item.provider == provider)

    def delete(self, user_id: int, provider: str) -> None:
        provider = self._validate_provider(provider)
        with self.database.connection() as conn:
            conn.execute(
                "DELETE FROM user_provider_secrets WHERE user_id = ? AND provider = ?",
                (user_id, provider),
            )
            conn.commit()

    def _update_test_status(self, user_id: int, provider: str, status: str, tested_at: str) -> None:
        with self.database.connection() as conn:
            conn.execute(
                """
                UPDATE user_provider_secrets
                SET last_test_status = ?, last_tested_at = ?, updated_at = ?
                WHERE user_id = ? AND provider = ?
                """,
                (status, tested_at, tested_at, user_id, provider),
            )
            conn.commit()

    async def test_connection(
        self,
        user_id: int,
        provider: str,
    ) -> ProviderConnectionTestResponse:
        provider = self._validate_provider(provider)
        tested_at = datetime.now(timezone.utc).isoformat()
        if not self.configured:
            return ProviderConnectionTestResponse(
                provider=provider,
                status="vault_unavailable",
                tested_at=tested_at,
                live_execution_enabled=settings.enable_live_execution,
            )
        material = self.get_material(user_id, provider)
        if material is None:
            return ProviderConnectionTestResponse(
                provider=provider,
                status="not_configured",
                tested_at=tested_at,
                live_execution_enabled=settings.enable_live_execution,
            )
        try:
            status = await self._probe(material)
        except Exception:
            status = "unavailable"
        self._update_test_status(user_id, provider, status, tested_at)
        return ProviderConnectionTestResponse(
            provider=provider,
            status=status,
            tested_at=tested_at,
            live_execution_enabled=settings.enable_live_execution,
            details_exposed=False,
        )

    async def _probe(
        self,
        material: ProviderSecretMaterial,
    ) -> Literal["connected", "auth_failed", "unavailable"]:
        timeout = httpx.Timeout(12.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            if material.provider == "groq":
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {material.api_key}"},
                )
            elif material.provider == "openai":
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {material.api_key}"},
                )
            elif material.provider == "twelvedata":
                response = await client.get(
                    "https://api.twelvedata.com/price",
                    params={"symbol": "EUR/USD", "apikey": material.api_key},
                )
            elif material.provider == "finnhub":
                response = await client.get(
                    "https://finnhub.io/api/v1/quote",
                    params={"symbol": "AAPL", "token": material.api_key},
                )
            elif material.provider == "newsapi":
                response = await client.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={"country": "us", "pageSize": 1, "apiKey": material.api_key},
                )
            else:
                if not material.account_id:
                    return "auth_failed"
                response = await client.get(
                    f"{settings.oanda_base_url}/v3/accounts/{material.account_id}/summary",
                    headers={"Authorization": f"Bearer {material.api_key}"},
                )
        if response.status_code in {401, 403}:
            return "auth_failed"
        return "connected" if response.is_success else "unavailable"
