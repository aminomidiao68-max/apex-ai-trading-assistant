import os
import sys
from uuid import uuid4

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import AuthLoginRequest, AuthRegisterRequest
from app.services.auth_service import AuthService


db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "auth_smoke.db"))
service = AuthService(db_path=db_path)

email = f"tester_{uuid4().hex[:8]}@example.com"
register_response = service.register(
    AuthRegisterRequest(name="Test User", email=email, password="Secret123")
)
print("REGISTERED:", register_response.user.email)

login_response = service.login(AuthLoginRequest(email=email, password="Secret123"))
print("LOGGED IN:", bool(login_response.access_token))

me = service.get_user_by_token(login_response.access_token)
print("ME:", me.name, me.email)

service.logout(login_response.access_token)
print("LOGOUT: ok")
