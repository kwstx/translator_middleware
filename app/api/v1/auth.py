from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import Any, Dict, Optional
from uuid import UUID

from app.db.session import get_session
from app.db.models import User, PermissionProfile
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_principal
from app.services.session import SessionService
from pydantic import BaseModel, EmailStr
from fastapi import Request

router = APIRouter()

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

@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, db: Session = Depends(get_session)):
    # Check if user already exists
    statement = select(User).where(User.email == user_in.email)
    result = await db.execute(statement)
    user = result.scalars().first()
    if user:
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
    return db_obj

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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Create persistent session metadata
    session_id = SessionService.create_session(
        user_id=str(user.id),
        metadata={
            "user_agent": request.headers.get("user-agent", "unknown"),
            "ip_address": request.client.host if request.client else "unknown"
        }
    )
    
    # Create access token including session ID
    access_token = create_access_token(
        data={
            "sub": str(user.id), 
            "email": user.email, 
            "sid": session_id,
            "scope": "translate:a2a"
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(principal: Dict[str, Any] = Depends(get_current_principal)):
    session_id = principal.get("sid")
    if session_id:
        SessionService.revoke_session(session_id)
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
