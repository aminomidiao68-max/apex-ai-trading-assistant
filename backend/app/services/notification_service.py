from __future__ import annotations

from pathlib import Path
import json

import httpx

from app.config import settings
from app.models import NotificationDispatchResult, SignalHistoryItem
from app.services.storage_service import StorageService


class NotificationService:
    def __init__(self, storage: StorageService) -> None:
        self.storage = storage

    def send_test_notification(self, user_id: int, title: str, body: str) -> NotificationDispatchResult:
        devices = self.storage.list_device_tokens(user_id)
        registered_devices = len(devices)
        if registered_devices == 0:
            self.storage.log_notification_event(user_id=user_id, title=title, body=body, mode="dry-run", sent_count=0)
            return NotificationDispatchResult(
                success=False,
                mode="dry-run",
                registered_devices=0,
                sent_count=0,
                message="No registered devices",
            )

        if self._is_firebase_configured():
            sent_count = self._send_fcm_notifications([device.token for device in devices], title, body)
            success = sent_count > 0
            mode = "firebase-live"
            message = "FCM push attempted with configured service account"
        else:
            sent_count = registered_devices
            success = True
            mode = "dry-run"
            message = "Notification event logged; add Firebase credentials for real remote delivery"

        self.storage.log_notification_event(
            user_id=user_id,
            title=title,
            body=body,
            mode=mode,
            sent_count=sent_count,
        )
        return NotificationDispatchResult(
            success=success,
            mode=mode,
            registered_devices=registered_devices,
            sent_count=sent_count,
            message=message,
        )

    def _is_firebase_configured(self) -> bool:
        return bool(settings.firebase_project_id and settings.firebase_service_account_json)

    def _send_fcm_notifications(self, tokens: list[str], title: str, body: str) -> int:
        try:
            access_token = self._build_google_access_token()
        except Exception:
            return 0

        url = f"https://fcm.googleapis.com/v1/projects/{settings.firebase_project_id}/messages:send"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; UTF-8",
        }
        sent_count = 0
        for token in tokens:
            payload = {
                "message": {
                    "token": token,
                    "notification": {"title": title, "body": body},
                    "data": {"title": title, "body": body},
                }
            }
            try:
                response = httpx.post(url, headers=headers, json=payload, timeout=15.0)
                if response.is_success:
                    sent_count += 1
            except Exception:
                continue
        return sent_count

    def _build_google_access_token(self) -> str:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        raw_value = settings.firebase_service_account_json.strip()
        if raw_value.startswith("{"):
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(raw_value),
                scopes=["https://www.googleapis.com/auth/firebase.messaging"],
            )
        else:
            service_account_path = Path(raw_value)
            credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=["https://www.googleapis.com/auth/firebase.messaging"],
            )
        credentials.refresh(Request())
        if not credentials.token:
            raise RuntimeError("Failed to acquire Firebase access token")
        return credentials.token


    def try_send_fresh_signal_alert(self, signal: SignalHistoryItem, user_id: int) -> None:
        """Notify only the owner of a newly saved actionable signal."""
        if signal.direction.value == "neutral" or signal.score < 70:
            return

        devices = self.storage.list_device_tokens(user_id)
        if not devices:
            return

        title = f"{signal.symbol} {signal.direction.value.upper()} • {signal.timeframe}"
        body = f"Score {signal.score} • Grade {signal.setup_grade} • {signal.execution_label}"

        if self._is_firebase_configured():
            sent_count = self._send_fcm_notifications(
                [device.token for device in devices], title, body
            )
            mode = "firebase-live"
        else:
            sent_count = len(devices)
            mode = "dry-run"

        self.storage.log_notification_event(
            user_id=user_id,
            title=title,
            body=body,
            mode=mode,
            sent_count=sent_count,
        )
