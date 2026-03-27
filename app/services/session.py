import uuid
import json
from datetime import timedelta, datetime, timezone
from typing import Optional, Dict, Any, List
from app.core.redis_client import get_redis_client
from app.core.config import settings

SESSION_PREFIX = "session:"

class SessionService:
    @staticmethod
    def create_session(user_id: str, metadata: Dict[str, Any] = None) -> str:
        redis = get_redis_client()
        if redis is None:
            # Fallback if Redis is disabled, though requested to track active sessions
            return str(uuid.uuid4())
        
        session_id = str(uuid.uuid4())
        key = f"{SESSION_PREFIX}{session_id}"
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_agent": metadata.get("user_agent") if metadata else "unknown",
            "ip_address": metadata.get("ip_address") if metadata else "unknown",
        }
        
        # Store as JSON string
        redis.setex(
            key,
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            json.dumps(session_data)
        )
        
        # Add to user sessions set
        redis.sadd(f"user:{user_id}:sessions", session_id)
        redis.expire(f"user:{user_id}:sessions", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        
        return session_id

    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        redis = get_redis_client()
        if redis is None:
            return None
        
        data = redis.get(f"{SESSION_PREFIX}{session_id}")
        if data:
            return json.loads(data)
        return None

    @staticmethod
    def revoke_session(session_id: str) -> bool:
        redis = get_redis_client()
        if redis is None:
            return False
        
        data = SessionService.get_session(session_id)
        if data:
            user_id = data.get("user_id")
            redis.srem(f"user:{user_id}:sessions", session_id)
            
        return redis.delete(f"{SESSION_PREFIX}{session_id}") > 0

    @staticmethod
    def get_user_sessions(user_id: str) -> List[str]:
        redis = get_redis_client()
        if redis is None:
            return []
        
        # Cleanup expired sessions from the set first if needed
        # (Though we rely on SREM during revocation and TTL for individual session keys)
        session_ids = redis.smembers(f"user:{user_id}:sessions")
        # Validate they still exist
        active_sessions = []
        for sid in session_ids:
            if redis.exists(f"{SESSION_PREFIX}{sid}"):
                active_sessions.append(sid)
            else:
                redis.srem(f"user:{user_id}:sessions", sid)
        return active_sessions

    @staticmethod
    def extend_session(session_id: str):
        redis = get_redis_client()
        if redis is None:
            return
        
        redis.expire(f"{SESSION_PREFIX}{session_id}", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
