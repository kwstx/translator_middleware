from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

import httpx

from .exceptions import EngramRequestError, EngramResponseError


class _AuthHandler(Protocol):
    def ensure_session_token(self) -> Optional[str]:
        ...

    def ensure_eat(self) -> Optional[str]:
        ...

    def refresh_session_token(self) -> Optional[str]:
        ...

    def refresh_eat(self) -> Optional[str]:
        ...


class EngramTransport:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 60.0,
        token: Optional[str] = None,
        eat: Optional[str] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._token = token
        self._eat = eat
        self._client = httpx.Client(timeout=timeout)
        self._auth_handler: Optional[_AuthHandler] = None

    @property
    def base_url(self) -> str:
        return self._base_url

    def set_base_url(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def set_token(self, token: Optional[str]) -> None:
        self._token = token

    def set_eat(self, eat: Optional[str]) -> None:
        self._eat = eat

    def set_auth_handler(self, handler: Optional[_AuthHandler]) -> None:
        self._auth_handler = handler

    @property
    def token(self) -> Optional[str]:
        return self._token

    @property
    def eat(self) -> Optional[str]:
        return self._eat

    def _auth_header(self, token: Optional[str]) -> Dict[str, str]:
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def _merge_headers(
        self, base: Optional[Dict[str, str]], extra: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        merged: Dict[str, str] = {}
        if base:
            merged.update(base)
        if extra:
            merged.update(extra)
        return merged

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self._base_url}{path}"

    def _response_indicates_token_issue(self, response: httpx.Response) -> bool:
        if response.status_code not in (401, 403):
            return False
        detail = response.text.lower()
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = str(payload.get("detail") or payload.get("error") or detail).lower()
        except Exception:
            pass
        markers = ("expired", "revoked", "invalid", "unauthorized", "missing", "session")
        return any(marker in detail for marker in markers)

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[str] = "eat",
        allow_retry: bool = True,
    ) -> httpx.Response:
        token = None
        if auth == "token":
            token = self._token
            if token is None and self._auth_handler:
                token = self._auth_handler.ensure_session_token()
        elif auth == "eat":
            token = self._eat
            if token is None and self._auth_handler:
                token = self._auth_handler.ensure_eat()
        elif auth is None:
            token = None

        if auth in ("token", "eat") and token is None:
            from .exceptions import EngramAuthError

            raise EngramAuthError(
                "Authentication required but no valid token is available."
            )

        request_headers = self._merge_headers(headers, self._auth_header(token))
        url = self._build_url(path)
        response = self._client.request(
            method,
            url,
            json=json_body,
            data=data,
            params=params,
            headers=request_headers,
        )

        if (
            allow_retry
            and auth in ("token", "eat")
            and self._auth_handler
            and self._response_indicates_token_issue(response)
        ):
            refreshed = None
            if auth == "eat":
                refreshed = self._auth_handler.refresh_eat()
            elif auth == "token":
                refreshed = self._auth_handler.refresh_session_token()

            if refreshed:
                retry_headers = self._merge_headers(
                    headers, self._auth_header(refreshed)
                )
                return self._client.request(
                    method,
                    url,
                    json=json_body,
                    data=data,
                    params=params,
                    headers=retry_headers,
                )

        return response

    def request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[str] = "eat",
        allow_retry: bool = True,
    ) -> Dict[str, Any]:
        response = self.request(
            method,
            path,
            json_body=json_body,
            data=data,
            params=params,
            headers=headers,
            auth=auth,
            allow_retry=allow_retry,
        )

        if response.status_code >= 400:
            detail = response.text
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    detail = str(payload.get("detail") or payload.get("error") or detail)
            except Exception:
                pass
            raise EngramRequestError(
                f"Engram request failed ({response.status_code}): {detail}"
            )

        try:
            return response.json()
        except Exception as exc:
            raise EngramResponseError(
                f"Engram response was not valid JSON: {exc}"
            ) from exc

    def ping(self) -> bool:
        root_url = self._base_url.replace("/api/v1", "")
        response = self._client.get(root_url, headers=self._auth_header(self._eat or self._token))
        return response.status_code == 200

    def close(self) -> None:
        self._client.close()
