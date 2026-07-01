import os
import sys
from tempfile import NamedTemporaryFile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import DeviceTokenRegisterRequest
from app.services.notification_service import NotificationService
from app.services.storage_service import StorageService


tmp = NamedTemporaryFile(suffix=".db", delete=False)
storage = StorageService(db_path=tmp.name)
service = NotificationService(storage)

storage.register_device_token(
    user_id=1,
    request=DeviceTokenRegisterRequest(token="fcm_test_token_value_12345678901234567890", platform="android", device_name="Pixel")
)
result = service.send_test_notification(user_id=1, title="Ping", body="Hello")
print(result.model_dump())
