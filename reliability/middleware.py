import asyncio
import hashlib
import json
import structlog
from typing import Any, Dict, Optional, Callable, Awaitable
from pydantic import create_model, BaseModel, ValidationError
from datetime import datetime, timezone
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from app.core.tui_bridge import get_tui_event_queue
from bridge.memory import memory_backend
from app.core.exceptions import (
    TransientError, 
    PermanentError, 
    RateLimitError, 
    NetworkError, 
    ExpiredTokenError,
    InvalidCredentialsError
)

logger = structlog.get_logger(__name__)

# CIRCUIT BREAKER STATE
# destination -> failure_count
_circuit_breaker: Dict[str, int] = {}
BREAKER_THRESHOLD = 5
COOLDOWN_SECONDS = 30
_last_failure_time: Dict[str, datetime] = {}

def get_idempotency_key(payload: Any, correlation_id: str, retry_count: int) -> str:
    """
    Generates a unique idempotency key based on message hash, correlation_id and retry count.
    """
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
    return f"{payload_hash}:{correlation_id}:{retry_count}"

def log_to_tui(message: str):
    """Logs a message directly to the TUI trace panel."""
    try:
        get_tui_event_queue().put_nowait(message)
    except Exception:
        pass

class ReliabilityMiddleware:
    """
    Wraps routing calls with reliability primitives:
    - Retries for transient errors (Exponential Backoff)
    - Idempotency / Exactly-once semantics via memory layer
    - Circuit Breaker pattern per destination
    - Auto schema inference & Pydantic validation
    - TUI trace logging with structured error reporting
    """
    
    def __init__(self, func: Callable[..., Awaitable[Dict[str, Any]]]):
        self.func = func

    async def __call__(
        self, 
        target: str, 
        payload: Any, 
        correlation_id: str = "default", 
        retry_count: int = 0, 
        **kwargs: Any
    ) -> Dict[str, Any]:
        
        # 1. CIRCUIT BREAKER CHECK
        if _circuit_breaker.get(target, 0) >= BREAKER_THRESHOLD:
            last_fail = _last_failure_time.get(target)
            if last_fail and (datetime.now(timezone.utc) - last_fail).total_seconds() < COOLDOWN_SECONDS:
                log_to_tui(f"🚫 [bold red]Circuit breaker tripped for {target}.[/] Pausing routing.")
                return {
                    "status": "error",
                    "error": "circuit_breaker_open",
                    "destination": target,
                    "retry_after": COOLDOWN_SECONDS
                }
            else:
                # Reset if cooldown passed
                _circuit_breaker[target] = 0
                log_to_tui(f"🔄 [bold yellow]Circuit breaker for {target} cooling down...[/] Retrying.")

        # 2. SCHEMA INFERENCE & VALIDATION
        if isinstance(payload, dict):
            try:
                fields = {k: (type(v), ...) for k, v in payload.items()}
                DynamicModel = create_model("InferredPayloadModel", **fields)
                DynamicModel(**payload) # Validate
                if any("unknown" in str(k).lower() or "temp" in str(k).lower() for k in payload.keys()):
                    log_to_tui(f"⚠️ [bold yellow]Low-confidence payload:[/] {target} schema contains ambiguous fields.")
            except Exception:
                log_to_tui(f"👀 [bold cyan]Schema inference alert:[/] Detected novel payload structure for {target}.")

        # 3. IDEMPOTENCY / EXACTLY-ONCE
        idemp_key = get_idempotency_key(payload, correlation_id, retry_count)
        if memory_backend.check_exists('idempotency_key', idemp_key, 'middle_ware'):
            log_to_tui(f"🛡️ [bold green]Exactly-once enforced:[/] Skipping duplicate message {idemp_key}")
            return {
                "status": "cached",
                "message": "Message already processed",
                "idempotency_key": idemp_key
            }

        # 4. RETRYABLE EXECUTION
        @retry(
            retry=retry_if_exception_type((TransientError, NetworkError, RateLimitError)),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=5),
            before_sleep=before_sleep_log(logger, "DEBUG"),
            reraise=True
        )
        async def _execute_with_retry():
            log_to_tui(f"🛰️ [bold blue]Routing message:[/] {target} (ID: {idemp_key[:8]})")
            try:
                result = await self.func(target, payload, correlation_id, retry_count, **kwargs)
                
                # Check for success status in result if it returns a dict
                if isinstance(result, dict) and result.get("status") == "error":
                    # Some connectors return error status instead of raising
                    err_type = result.get("error_type", "")
                    engram_code = result.get("engram_code", "")
                    
                    if "RateLimit" in err_type or "Timeout" in err_type or engram_code == "TRANSIENT_TOOL_ERROR":
                        raise NetworkError(result.get("detail", "Transient tool error"))
                    
                    if "ExpiredToken" in err_type:
                        raise ExpiredTokenError(result.get("detail", "Token expired"))
                        
                    if "InvalidCredentials" in err_type:
                        raise InvalidCredentialsError(result.get("detail", "Invalid credentials"))
                
                return result

            except (RateLimitError, NetworkError) as transient:
                log_to_tui(f"🔄 [bold yellow]Transient error ({type(transient).__name__}):[/] Retrying...")
                raise

        try:
            result = await _execute_with_retry()
            
            # Record success in memory
            memory_backend.write('middle_ware', 'INTERNAL', {"idempotency_key": idemp_key})
            
            # Reset circuit breaker on success
            _circuit_breaker[target] = 0
            
            return result
            
        except ExpiredTokenError as e:
            log_to_tui(f"🔑 [bold red]Auth Error:[/] Token for {target} expired. Please refresh credentials.")
            logger.warning("ReliabilityMiddleware: auth token expired", target=target, error=str(e), action_required="REFRESH_CREDENTIALS")
            return {
                "status": "error",
                "error": "token_expired",
                "detail": str(e),
                "action_required": "REFRESH_CREDENTIALS"
            }
        except InvalidCredentialsError as e:
            log_to_tui(f"🚫 [bold red]Auth Error:[/] Invalid credentials for {target}. Check provider settings.")
            logger.warning("ReliabilityMiddleware: invalid credentials", target=target, error=str(e))
            return {
                "status": "error",
                "error": "invalid_credentials",
                "detail": str(e)
            }
        except PermanentError as e:
            log_to_tui(f"💥 [bold red]Permanent Failure:[/] {target} failed: {str(e)}")
            logger.error("ReliabilityMiddleware: permanent failure", target=target, error=str(e))
            # FAILURE TRACKING
            _circuit_breaker[target] = _circuit_breaker.get(target, 0) + 1
            _last_failure_time[target] = datetime.now(timezone.utc)
            return {
                "status": "error",
                "error": "permanent_failure",
                "detail": str(e)
            }
        except Exception as e:
            # UNEXPECTED ERRORS
            _circuit_breaker[target] = _circuit_breaker.get(target, 0) + 1
            _last_failure_time[target] = datetime.now(timezone.utc)
            
            log_to_tui(f"🚨 [bold red]Routing failed for {target}:[/] {str(e)}")
            logger.error("ReliabilityMiddleware: unexpected system failure", target=target, error=str(e), exc_info=True)

            
            return {
                "status": "error",
                "error": "unexpected_failure",
                "detail": str(e)
            }

def wrap_route_to(func):
    middleware = ReliabilityMiddleware(func)
    async def wrapper(*args, **kwargs):
        return await middleware(*args, **kwargs)
    return wrapper
