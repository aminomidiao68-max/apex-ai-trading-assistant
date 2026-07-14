from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from app.config import settings
from app.models import AuthLoginRequest, AuthRegisterRequest, AuthResponse, AuthUser
from app.services.database_service import DatabaseManager


_PASSWORD_SCHEME = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 310_000


class AuthService:
    def __init__(self, db_path: str | None = None, seed_demo_user: bool | None = None) -> None:
        self.database = DatabaseManager(db_path=db_path)
        self.db_path = self.database.sqlite_path or ""
        self.db_backend = self.database.backend
        should_seed = settings.seed_demo_user if seed_demo_user is None else seed_demo_user
        if should_seed:
            self._seed_demo_user()

    def _connect(self):
        return self.database.connection()

    def _seed_demo_user(self) -> None:
        demo_email = "demo@apexai.app"
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM users WHERE email = ?", (demo_email,)).fetchone()
            if row is None:
                password_hash = self._hash_password("Demo12345!")
                conn.execute(
                    "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    ("APEX Demo", demo_email, password_hash, self._now()),
                )
                conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _hash_password(
        self,
        password: str,
        salt: bytes | None = None,
        iterations: int = _PASSWORD_ITERATIONS,
    ) -> str:
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return "$".join(
            [
                _PASSWORD_SCHEME,
                str(iterations),
                base64.b64encode(salt).decode(),
                base64.b64encode(digest).decode(),
            ]
        )

    def _verify_password(self, password: str, stored: str) -> bool:
        try:
            if stored.startswith(f"{_PASSWORD_SCHEME}$"):
                _, iterations_raw, salt_b64, _ = stored.split("$", 3)
                candidate = self._hash_password(
                    password,
                    base64.b64decode(salt_b64.encode()),
                    int(iterations_raw),
                )
                return hmac.compare_digest(candidate, stored)

            # Legacy Alpha sessions used salt$digest with 100k iterations.
            salt_b64, _ = stored.split("$", 1)
            salt = base64.b64decode(salt_b64.encode())
            digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
            legacy = f"{salt_b64}${base64.b64encode(digest).decode()}"
            return hmac.compare_digest(legacy, stored)
        except (ValueError, TypeError):
            return False

    def _needs_password_rehash(self, stored: str) -> bool:
        if not stored.startswith(f"{_PASSWORD_SCHEME}$"):
            return True
        try:
            return int(stored.split("$", 2)[1]) < _PASSWORD_ITERATIONS
        except (ValueError, IndexError):
            return True

    def _serialize_user(self, row: Any) -> AuthUser:
        return AuthUser(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            created_at=row["created_at"],
        )

    def _token_digest(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _create_session(self, user_id: int) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_digest = self._token_digest(raw_token)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=settings.session_ttl_hours)).isoformat()
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE created_at < ?", (cutoff,))
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token_digest, user_id, self._now()),
            )
            conn.commit()
        return raw_token

    def register(self, request: AuthRegisterRequest) -> AuthResponse:
        email = request.email.strip().lower()
        with self._connect() as conn:
            exists = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if exists is not None:
                raise HTTPException(status_code=409, detail="Email already registered")

            password_hash = self._hash_password(request.password)
            try:
                cursor = conn.execute(
                    "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (request.name.strip(), email, password_hash, self._now()),
                )
                conn.commit()
            except Exception as exc:
                conn.rollback()
                # Never return raw database messages or constraints.
                if "unique" in type(exc).__name__.lower():
                    raise HTTPException(status_code=409, detail="Email already registered") from exc
                raise
            user_id = int(cursor.lastrowid)
            user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

        token = self._create_session(user_id)
        return AuthResponse(access_token=token, user=self._serialize_user(user_row))

    def login(self, request: AuthLoginRequest) -> AuthResponse:
        email = request.email.strip().lower()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row is None or not self._verify_password(request.password, row["password_hash"]):
                raise HTTPException(status_code=401, detail="Invalid email or password")
            if self._needs_password_rehash(row["password_hash"]):
                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (self._hash_password(request.password), row["id"]),
                )
                conn.commit()

        token = self._create_session(int(row["id"]))
        return AuthResponse(access_token=token, user=self._serialize_user(row))

    def get_user_by_token(self, token: str) -> AuthUser:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=settings.session_ttl_hours)).isoformat()
        token_digest = self._token_digest(token)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.name, u.email, u.created_at
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ? AND s.created_at >= ?
                """,
                (token_digest, cutoff),
            ).fetchone()
            if row is None:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token_digest,))
                conn.commit()
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            return self._serialize_user(row)

    def logout(self, token: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (self._token_digest(token),))
            conn.commit()
