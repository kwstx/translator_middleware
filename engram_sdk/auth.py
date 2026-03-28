from typing import Any, Dict, Optional

from .communication import EngramTransport
from .exceptions import EngramAuthError


class AuthClient:
    def __init__(
        self,
        transport: EngramTransport,
        *,
        email: Optional[str] = None,
        password: Optional[str] = None,
        eat_expires_days: int = 30,
    ) -> None:
        self._transport = transport
        self._email = email
        self._password = password
        self._eat_expires_days = eat_expires_days

    def set_credentials(self, email: Optional[str], password: Optional[str]) -> None:
        if email:
            self._email = email
        if password:
            self._password = password

    def set_eat_expires_days(self, days: int) -> None:
        self._eat_expires_days = days

    def get_session_token(self) -> Optional[str]:
        return self._transport.token

    def get_eat(self) -> Optional[str]:
        return self._transport.eat

    def login(self, email: Optional[str] = None, password: Optional[str] = None) -> str:
        login_email = email or self._email
        login_password = password or self._password
        if not login_email or not login_password:
            raise EngramAuthError("Email and password are required to login.")

        self._email = login_email
        self._password = login_password
        payload = {"username": login_email, "password": login_password}
        response = self._transport.request_json(
            "POST",
            "/auth/login",
            data=payload,
            auth=None,
        )
        access_token = response.get("access_token")
        if not access_token:
            raise EngramAuthError("Login response missing access_token.")
        self._transport.set_token(access_token)
        return access_token

    def signup(
        self,
        email: str,
        password: str,
        *,
        user_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._transport.request_json(
            "POST",
            "/auth/signup",
            json_body={
                "email": email,
                "password": password,
                "user_metadata": user_metadata or {"source": "sdk"},
            },
            auth=None,
        )

    def generate_eat(self, *, expires_days: Optional[int] = None) -> str:
        if not self._transport.token:
            self.ensure_session_token()
        response = self._transport.request_json(
            "POST",
            "/auth/tokens/generate-eat",
            params={"expires_days": expires_days or self._eat_expires_days},
            auth="token",
        )
        eat = response.get("eat")
        if not eat:
            raise EngramAuthError("EAT generation failed; missing eat token.")
        self._transport.set_eat(eat)
        return eat

    def set_session_token(self, token: Optional[str]) -> None:
        self._transport.set_token(token)

    def set_eat(self, eat: Optional[str]) -> None:
        self._transport.set_eat(eat)

    def ensure_session_token(self) -> Optional[str]:
        if self._transport.token:
            return self._transport.token
        return self.login()

    def ensure_eat(self) -> Optional[str]:
        if self._transport.eat:
            return self._transport.eat
        return self.generate_eat()

    def refresh_session_token(self) -> Optional[str]:
        return self.login()

    def refresh_eat(self) -> Optional[str]:
        self.ensure_session_token()
        return self.generate_eat()
