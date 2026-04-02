from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import Any, Dict, Optional, List
from uuid import UUID

from app.db.session import get_session
from app.db.models import User, PermissionProfile
from app.core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_principal,
    revoke_token
)
from app.services.eat_identity import EATIdentityService
from datetime import timedelta
from app.services.session import SessionService
from pydantic import BaseModel, EmailStr
from fastapi import Request
import structlog
from app.core.logging import bind_context

router = APIRouter()
logger = structlog.get_logger(__name__)

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    user_metadata: Dict[str, Any] = {}

class UserPublic(BaseModel):
    id: UUID
    email: str
    user_metadata: Dict[str, Any]
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str

class SignupResult(BaseModel):
    user: UserPublic
    access_token: str
    token_type: str = "bearer"
    eat: Optional[str] = None
    eat_refresh_token: Optional[str] = None
    eat_expires_at: Optional[str] = None

class EATTokenRequest(BaseModel):
    semantic_scopes: Optional[List[str]] = None
    expires_minutes: Optional[int] = None
    refresh_expires_minutes: Optional[int] = None

class EATTokenResponse(BaseModel):
    eat: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: str

class EATRefreshRequest(BaseModel):
    refresh_token: str

@router.post("/signup", response_model=SignupResult, status_code=status.HTTP_201_CREATED)
async def signup(request: Request, user_in: UserCreate, db: Session = Depends(get_session)):
    # Check if user already exists
    statement = select(User).where(User.email == user_in.email)
    result = await db.execute(statement)
    user = result.scalars().first()
    if user:
        logger.warning("Signup failed: user already exists", email=user_in.email)
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # Create new user
    db_obj = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        user_metadata=user_in.user_metadata,
    )
    db.add(db_obj)
    await db.flush()  # To get db_obj.id

    # Create default permission profile
    default_permissions = {
        "core_translator": ["read", "execute"],
        "discovery": ["read"]
    }
    perm_profile = PermissionProfile(
        user_id=db_obj.id,
        profile_name="Standard",
        permissions=default_permissions
    )
    db.add(perm_profile)

    await db.commit()
    await db.refresh(db_obj)
    
    # Auto-login after signup to provide immediate credentials
    session_id = SessionService.create_session(
        user_id=str(db_obj.id),
        metadata={
            "user_agent": request.headers.get("user-agent", "unknown"),
            "ip_address": request.client.host if request.client else "unknown",
            "event": "auto_signup_login"
        }
    )
    
    access_token = create_access_token(
        data={
            "sub": str(db_obj.id), 
            "email": db_obj.email, 
            "sid": session_id,
            "scope": "translate:a2a"
        }
    )
    
    eat_result = EATIdentityService.issue_token(
        db=db,
        user_id=str(db_obj.id),
        permissions=default_permissions,
        semantic_scopes=["execute:tool-invocation"],
        metadata={
            "event": "auto_signup_login",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "ip_address": request.client.host if request.client else "unknown"
        }
    )
    await db.commit()
    
    bind_context(user_id=str(db_obj.id), session_id=session_id)
    logger.info("Signup and auto-authentication successful", user_id=str(db_obj.id), session_id=session_id)
    
    return {
        "user": db_obj,
        "access_token": access_token,
        "token_type": "bearer",
        "eat": eat_result.token,
        "eat_refresh_token": eat_result.refresh_token,
        "eat_expires_at": eat_result.expires_at.isoformat()
    }

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    db: Session = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    # Authenticate user
    statement = select(User).where(User.email == form_data.username)
    result = await db.execute(statement)
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Login failed: invalid credentials", email=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        logger.warning("Login failed: inactive user", user_id=str(user.id), email=user.email)
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Create persistent session metadata
    session_id = SessionService.create_session(
        user_id=str(user.id),
        metadata={
            "user_agent": request.headers.get("user-agent", "unknown"),
            "ip_address": request.client.host if request.client else "unknown"
        }
    )
    bind_context(user_id=str(user.id), session_id=session_id)
    logger.info("Login successful", user_id=str(user.id), session_id=session_id)
    
    # Create access token including session ID
    access_token = create_access_token(
        data={
            "sub": str(user.id), 
            "email": user.email, 
            "sid": session_id,
            "scope": "translate:a2a"
        }
    )
    logger.info("Access token issued", user_id=str(user.id), scope="translate:a2a")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(principal: Dict[str, Any] = Depends(get_current_principal)):
    session_id = principal.get("sid")
    if session_id:
        SessionService.revoke_session(session_id)
        
    jti = principal.get("jti")
    exp = principal.get("exp")
    if jti and exp:
        # Revoke the token until it would have expired
        now = int(timedelta(seconds=0).total_seconds()) # placeholder for current time
        import time
        expires_in = max(1, exp - int(time.time()))
        revoke_token(jti, expires_in)
    bind_context(user_id=str(principal.get("sub")), session_id=session_id)
    logger.info("Logout successful", user_id=str(principal.get("sub")), session_id=session_id, token_revoked=bool(jti and exp))
    return {"detail": "Successfully logged out"}

@router.get("/sessions")
async def list_sessions(principal: Dict[str, Any] = Depends(get_current_principal)):
    user_id = principal.get("sub")
    active_sids = SessionService.get_user_sessions(user_id)
    
    sessions = []
    for sid in active_sids:
        data = SessionService.get_session(sid)
        if data:
            data["sid"] = sid
            sessions.append(data)
            
    return sessions


@router.post("/tokens/generate-eat", response_model=EATTokenResponse)
async def generate_eat(
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal),
    request: EATTokenRequest = None
):
    """
    Generates a long-lived Engram Access Token (EAT) for external agent access.
    The token encodes permissions from the user's current profile.
    """
    user_id = principal.get("sub")
    statement = select(PermissionProfile).where(PermissionProfile.user_id == UUID(user_id))
    result = await db.execute(statement)
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Permission profile not found")
        
    request = request or EATTokenRequest()
    expires_delta = timedelta(minutes=request.expires_minutes) if request.expires_minutes else None
    refresh_delta = timedelta(minutes=request.refresh_expires_minutes) if request.refresh_expires_minutes else None
    eat_result = EATIdentityService.issue_token(
        db=db,
        user_id=user_id,
        permissions=profile.permissions,
        semantic_scopes=request.semantic_scopes or ["execute:tool-invocation"],
        expires_delta=expires_delta,
        refresh_expires_delta=refresh_delta,
        metadata={"event": "manual_generate"}
    )
    await db.commit()
    bind_context(user_id=str(user_id))
    logger.info("EAT generated", user_id=str(user_id))
    return {
        "eat": eat_result.token,
        "refresh_token": eat_result.refresh_token,
        "token_type": "bearer",
        "expires_at": eat_result.expires_at.isoformat()
    }

@router.post("/tokens/refresh-eat", response_model=EATTokenResponse)
async def refresh_eat(
    request: EATRefreshRequest,
    db: Session = Depends(get_session),
    principal: Dict[str, Any] = Depends(get_current_principal),
):
    user_id = principal.get("sub")
    statement = select(PermissionProfile).where(PermissionProfile.user_id == UUID(user_id))
    result = await db.execute(statement)
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Permission profile not found")
    try:
        eat_result = EATIdentityService.refresh_token(
            db=db,
            refresh_token=request.refresh_token,
            permissions=profile.permissions,
            semantic_scopes=["execute:tool-invocation"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    bind_context(user_id=str(user_id))
    logger.info("EAT refreshed", user_id=str(user_id))
    return {
        "eat": eat_result.token,
        "refresh_token": eat_result.refresh_token,
        "token_type": "bearer",
        "expires_at": eat_result.expires_at.isoformat()
    }
@router.post("/tokens/revoke-eat")
async def revoke_eat(
    token_to_revoke: str,
    refresh_token: Optional[str] = None,
    principal: Dict[str, Any] = Depends(get_current_principal),
    db: Session = Depends(get_session)
):
    """
    Revokes a specific Engram Access Token.
    Users can only revoke their own tokens.
    """
    import jwt
    from app.core.config import settings
    from app.core.security import _get_verification_key
    
    try:
        # We decode without verification of expiration to allow revoking already expired tokens if needed,
        # but we verify signature.
        payload = jwt.decode(
            token_to_revoke,
            _get_verification_key(),
            algorithms=[settings.AUTH_JWT_ALGORITHM],
            options={"verify_exp": False, "require": ["jti", "sub"]}
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid token format")

    # Access control
    if payload.get("sub") != principal.get("sub"):
        raise HTTPException(status_code=403, detail="You can only revoke your own tokens.")

    jti = payload.get("jti")
    exp = payload.get("exp")
    
    if jti and exp:
        import time
        expires_in = max(1, exp - int(time.time()))
        EATIdentityService.revoke_eat(
            db=db,
            user_id=str(principal.get("sub")),
            token=token_to_revoke,
            jti=jti,
            expires_in=expires_in,
            refresh_token=refresh_token,
        )
        await db.commit()
    bind_context(user_id=str(principal.get("sub")))
    logger.info("EAT revoked", user_id=str(principal.get("sub")), jti=jti)
    return {"detail": "Token successfully revoked"}
