from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json
import uuid

from sqlmodel import Session
import structlog

from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.core.security import create_engram_access_token, revoke_token
from app.db.models import TokenAuditLog, TokenAuditEvent

logger = structlog.get_logger(__name__)

REFRESH_TOKEN_PREFIX = "refresh_token:"


@dataclass
class EATIssueResult:
    token: str
    refresh_token: str
    expires_at: datetime
    jti: str


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _refresh_key(refresh_token: str) -> str:
    return f"{REFRESH_TOKEN_PREFIX}{_hash_value(refresh_token)}"


def _store_refresh_token(refresh_token: str, payload: Dict[str, Any], ttl_seconds: int) -> None:
    redis = get_redis_client()
    if not redis:
        return
    key = _refresh_key(refresh_token)
    try:
        redis.setex(key, ttl_seconds, json.dumps(payload))
    except Exception as exc:
        logger.error("Failed to store refresh token", error=str(exc))


def _consume_refresh_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    redis = get_redis_client()
    if not redis:
        return None
    key = _refresh_key(refresh_token)
    try:
        payload_raw = redis.get(key)
        if payload_raw:
            redis.delete(key)
            return json.loads(payload_raw)
    except Exception as exc:
        logger.error("Failed to consume refresh token", error=str(exc))
    return None


def _revoke_refresh_token(refresh_token: str) -> None:
    redis = get_redis_client()
    if not redis:
        return
    key = _refresh_key(refresh_token)
    try:
        redis.delete(key)
    except Exception:
        return


def _audit_token_event(
    db: Session,
    user_id: str,
    token: str,
    jti: str,
    token_type: str,
    event_type: TokenAuditEvent,
    expires_at: Optional[datetime],
    scopes: Dict[str, Any],
    semantic_scopes: List[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    token_hash = _hash_value(token)
    record = TokenAuditLog(
        user_id=uuid.UUID(user_id),
        token_type=token_type,
        event_type=event_type,
        jti=jti,
        token_hash=token_hash,
        issued_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        scopes=scopes or {},
        semantic_scopes=semantic_scopes or [],
        metadata=metadata or {},
    )
    db.add(record)


class EATIdentityService:
    @staticmethod
    def issue_token(
        db: Session,
        user_id: str,
        permissions: Dict[str, List[str]],
        semantic_scopes: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None,
        refresh_expires_delta: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None,
        event_type: TokenAuditEvent = TokenAuditEvent.ISSUED,
    ) -> EATIssueResult:
        expires_delta = expires_delta or timedelta(minutes=settings.EAT_ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expires_delta = refresh_expires_delta or timedelta(minutes=settings.EAT_REFRESH_TOKEN_EXPIRE_MINUTES)

        token = create_engram_access_token(
            user_id=user_id,
            permissions=permissions,
            semantic_scopes=semantic_scopes or ["execute:tool-invocation"],
            expires_delta=expires_delta,
        )
        now = datetime.now(timezone.utc)
        expires_at = now + expires_delta
        refresh_token = str(uuid.uuid4())
        refresh_payload = {
            "sub": user_id,
            "jti": None,
            "exp": int((now + refresh_expires_delta).timestamp()),
        }

        # Extract JTI from token for audit/revocation
        try:
            import jwt
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
            )
            jti = payload.get("jti") or ""
        except Exception:
            jti = ""

        refresh_payload["jti"] = jti
        _store_refresh_token(refresh_token, refresh_payload, int(refresh_expires_delta.total_seconds()))

        _audit_token_event(
            db,
            user_id=user_id,
            token=token,
            jti=jti,
            token_type="EAT",
            event_type=event_type,
            expires_at=expires_at,
            scopes=permissions,
            semantic_scopes=semantic_scopes or ["execute:tool-invocation"],
            metadata=metadata,
        )

        return EATIssueResult(
            token=token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            jti=jti,
        )

    @staticmethod
    def refresh_token(
        db: Session,
        refresh_token: str,
        permissions: Dict[str, List[str]],
        semantic_scopes: Optional[List[str]] = None,
    ) -> EATIssueResult:
        payload = _consume_refresh_token(refresh_token)
        if not payload:
            raise ValueError("Invalid or expired refresh token.")
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Refresh token subject missing.")
        return EATIdentityService.issue_token(
            db=db,
            user_id=user_id,
            permissions=permissions,
            semantic_scopes=semantic_scopes,
            metadata={"refresh": True},
            event_type=TokenAuditEvent.REFRESHED,
        )

    @staticmethod
    def revoke_eat(
        db: Session,
        user_id: str,
        token: str,
        jti: Optional[str],
        expires_in: int,
        refresh_token: Optional[str] = None,
    ) -> None:
        if jti:
            revoke_token(jti, expires_in)
        if refresh_token:
            _revoke_refresh_token(refresh_token)
        _audit_token_event(
            db=db,
            user_id=user_id,
            token=token,
            jti=jti or "",
            token_type="EAT",
            event_type=TokenAuditEvent.REVOKED,
            expires_at=None,
            scopes={},
            semantic_scopes=[],
            metadata={"refresh_revoked": bool(refresh_token)},
        )
