from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from passlib.context import CryptContext

from app.core.config import settings
from app.db.session import get_session
from app.db.models import PermissionProfile
from app.services.session import SessionService
from sqlmodel import Session, select
import uuid
from uuid import UUID
from app.core.redis_client import get_redis_client

import bcrypt
import structlog

logger = structlog.get_logger(__name__)

REVOKED_TOKEN_PREFIX = "revoked_token:"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    # bcrypt.hashpw expects bytes
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Ensure JTI exists for revocation tracking
    if "jti" not in to_encode:
        to_encode["jti"] = str(uuid.uuid4())
        
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iss": settings.AUTH_ISSUER,
        "aud": settings.AUTH_AUDIENCE,
        "iat": int(datetime.now(timezone.utc).timestamp())
    })
    return jwt.encode(to_encode, _get_signing_key(), algorithm=settings.AUTH_JWT_ALGORITHM)


def create_engram_access_token(
    user_id: str,
    permissions: Dict[str, List[str]],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generates an Engram Access Token (EAT).
    EATs are used by agents to authenticate on behalf of users.
    """
    allowed_tools = list(permissions.keys())
    # The 'scope' claim is usually a space-separated string of permissions
    # We include both the flattened scopes and the structured permissions map
    all_scopes = set()
    for s in permissions.values():
        all_scopes.update(s)

    data = {
        "sub": user_id,
        "type": "EAT",
        "allowed_tools": allowed_tools,
        "scopes": permissions,
        "scope": " ".join(sorted(list(all_scopes)))
    }
    return create_access_token(data, expires_delta)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    scopes={
        "translate:a2a": "Translate messages using A2A protocol scope.",
        "translate:beta": "Access beta translation endpoints for enterprise users.",
    },
)


def _get_signing_key() -> str:
    if not settings.AUTH_JWT_SECRET:
        raise RuntimeError("AUTH_JWT_SECRET is required for signing tokens.")
    return settings.AUTH_JWT_SECRET


def _get_verification_key() -> str:
    if settings.AUTH_JWT_ALGORITHM.startswith("HS"):
        return _get_signing_key()
    if not settings.AUTH_JWT_PUBLIC_KEY:
        raise RuntimeError("AUTH_JWT_PUBLIC_KEY is required for verification with RS*/ES* algorithms.")
    return settings.AUTH_JWT_PUBLIC_KEY


def _extract_scopes(payload: Dict[str, Any]) -> List[str]:
    scope_val = payload.get("scope")
    if isinstance(scope_val, str):
        return [s for s in scope_val.split(" ") if s]
    scopes_val = payload.get("scopes")
    if isinstance(scopes_val, list):
        return [str(s) for s in scopes_val]
    return []

def is_token_revoked(jti: str) -> bool:
    """
    Checks if a token has been explicitly revoked.
    Implements a hybrid fail-mode based on environment and AUTH_FAIL_CLOSED setting.
    """
    if not jti:
        return False
        
    redis = get_redis_client()
    if not redis:
        # middle ground: loud warning, but only block if configured or in production
        logger.warning("Security Check: Redis unavailable for revocation lookup", jti=jti)
        if settings.AUTH_FAIL_CLOSED and settings.ENVIRONMENT != "development":
            return True # Fail-closed (secure)
        return False # Fail-open (dev-friendly)

    try:
        return redis.exists(f"{REVOKED_TOKEN_PREFIX}{jti}") > 0
    except Exception as exc:
        logger.error("Redis error during revocation check", error=str(exc), jti=jti)
        if settings.AUTH_FAIL_CLOSED and settings.ENVIRONMENT != "development":
            return True # Fail-closed
        return False # Fail-open


def revoke_token(jti: str, expires_in: int):
    """Adds a token to the revocation list until it would have expired."""
    redis = get_redis_client()
    if not redis or not jti:
        return
    try:
        redis.setex(f"{REVOKED_TOKEN_PREFIX}{jti}", expires_in, "1")
    except Exception:
        # Swallow Redis errors for environments without Redis.
        return


def verify_engram_token(token: str) -> Dict[str, Any]:
    """
    Synchronously verifies an Engram Access Token (EAT).
    Checks signature, expiration, issuer, audience, type, and revocation status.
    """
    key = _get_verification_key()
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[settings.AUTH_JWT_ALGORITHM],
            audience=settings.AUTH_AUDIENCE,
            issuer=settings.AUTH_ISSUER,
            options={"require": ["exp", "iss", "aud", "jti"]},
        )
        if payload.get("type") != "EAT":
            raise HTTPException(status_code=401, detail="Token is not a valid Engram Access Token (EAT).")
        
        if is_token_revoked(payload.get("jti")):
            raise HTTPException(status_code=401, detail="Token has been revoked.")
            
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Engram Access Token has expired.")
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Engram Access Token: {str(exc)}")


async def get_current_principal(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    # We use the generic verification here but we also allow non-EAT tokens (standard access tokens)
    # for the main API endpoints.
    key = _get_verification_key()
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[settings.AUTH_JWT_ALGORITHM],
            audience=settings.AUTH_AUDIENCE,
            issuer=settings.AUTH_ISSUER,
            options={"require": ["exp", "iss", "aud"]},
        )
        
        # We don't always require JTI for standard tokens if they were issued before this change,
        # but if it exists, we check revocation.
        jti = payload.get("jti")
        if jti and is_token_revoked(jti):
             raise HTTPException(status_code=401, detail="Token has been revoked.")
             
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {str(exc)}")

    token_scopes = _extract_scopes(payload)
    required_scopes = list(security_scopes.scopes)
    if required_scopes and not set(required_scopes).issubset(set(token_scopes)):
        raise HTTPException(status_code=403, detail="Insufficient scope for this resource.")

    # Validate session for stateful check if session ID is present
    session_id = payload.get("sid")
    if session_id:
        session_data = SessionService.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=401, detail="Session expired or revoked.")
    # Slide session expiration
    if session_id:
        SessionService.extend_session(session_id)

    payload["_raw_token"] = token
    return payload


def require_scopes(scopes: List[str]):
    return Security(get_current_principal, scopes=scopes)


async def check_permissions(
    tool_id: str,
    scope: str,
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    # For EAT tokens, we prioritize the embedded scopes for performance and single-key semantics
    if principal.get("type") == "EAT":
        eat_permissions = principal.get("scopes", {})
        if scope in eat_permissions.get(tool_id, []):
            return True

    user_id = principal.get("sub")
    if not user_id:
         raise HTTPException(status_code=401, detail="Subject missing in token.")

    statement = select(PermissionProfile).where(PermissionProfile.user_id == UUID(user_id))
    result = await db.execute(statement)
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(status_code=403, detail="Permission profile not found.")

    tool_perms = profile.permissions.get(tool_id, [])
    if scope not in tool_perms:
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient permissions. Scope '{scope}' for tool '{tool_id}' required."
        )
    return True
