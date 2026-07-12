from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException

from app.config import settings
from app.models import AuthLoginRequest, AuthRegisterRequest, AuthResponse, AuthUser


class AuthService:
    def __init__(self, db_path: str | None = None, seed_demo_user: bool | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        data_dir = root / "app_data"
        data_dir.mkdir(parents=True, exist_ok=True)
        configured_path = settings.database_path.strip()
        self.db_path = db_path or configured_path or str(data_dir / "smartmoney.db")
        self._init_db()
        should_seed = settings.seed_demo_user if seed_demo_user is None else seed_demo_user
        if should_seed:
            self._seed_demo_user()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.commit()

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

    def _hash_password(self, password: str, salt: bytes | None = None) -> str:
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"

    def _verify_password(self, password: str, stored: str) -> bool:
        salt_b64, digest_b64 = stored.split("$", 1)
        salt = base64.b64decode(salt_b64.encode())
        new_hash = self._hash_password(password, salt)
        return hmac.compare_digest(new_hash, stored)

    def _serialize_user(self, row: sqlite3.Row) -> AuthUser:
        return AuthUser(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            created_at=row["created_at"],
        )

    def _create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=settings.session_ttl_hours)).isoformat()
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE created_at < ?", (cutoff,))
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, self._now()),
            )
            conn.commit()
        return token

    def register(self, request: AuthRegisterRequest) -> AuthResponse:
        email = request.email.strip().lower()
        with self._connect() as conn:
            exists = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if exists is not None:
                raise HTTPException(status_code=409, detail="Email already registered")

            password_hash = self._hash_password(request.password)
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (request.name.strip(), email, password_hash, self._now()),
            )
            conn.commit()
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

        token = self._create_session(int(row["id"]))
        return AuthResponse(access_token=token, user=self._serialize_user(row))

    def get_user_by_token(self, token: str) -> AuthUser:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=settings.session_ttl_hours)).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.name, u.email, u.created_at
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ? AND s.created_at >= ?
                """,
                (token, cutoff),
            ).fetchone()
            if row is None:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            return self._serialize_user(row)

    def logout(self, token: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
