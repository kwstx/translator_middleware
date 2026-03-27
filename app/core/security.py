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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iss": settings.AUTH_ISSUER,
        "aud": settings.AUTH_AUDIENCE,
        "iat": int(datetime.now(timezone.utc).timestamp())
    })
    return jwt.encode(to_encode, _get_verification_key(), algorithm=settings.AUTH_JWT_ALGORITHM)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    scopes={
        "translate:a2a": "Translate messages using A2A protocol scope.",
        "translate:beta": "Access beta translation endpoints for enterprise users.",
    },
)


def _get_verification_key() -> str:
    if settings.AUTH_JWT_ALGORITHM.startswith("HS"):
        if not settings.AUTH_JWT_SECRET:
            raise RuntimeError("AUTH_JWT_SECRET is required for HS* algorithms.")
        return settings.AUTH_JWT_SECRET
    if not settings.AUTH_JWT_PUBLIC_KEY:
        raise RuntimeError("AUTH_JWT_PUBLIC_KEY is required for RS*/ES* algorithms.")
    return settings.AUTH_JWT_PUBLIC_KEY


def _extract_scopes(payload: Dict[str, Any]) -> List[str]:
    scope_val = payload.get("scope")
    if isinstance(scope_val, str):
        return [s for s in scope_val.split(" ") if s]
    scopes_val = payload.get("scopes")
    if isinstance(scopes_val, list):
        return [str(s) for s in scopes_val]
    return []


async def get_current_principal(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
) -> Dict[str, Any]:
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
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication token.") from exc

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
        SessionService.extend_session(session_id)

    return payload


def require_scopes(scopes: List[str]):
    return Security(get_current_principal, scopes=scopes)


async def check_permissions(
    tool_id: str,
    scope: str,
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    user_id = principal.get("sub")
    statement = select(PermissionProfile).where(PermissionProfile.user_id == user_id)
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
