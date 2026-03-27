import asyncio
import uuid
import re
import structlog
from typing import List, Dict, Any, Optional, Tuple
from app.messaging.orchestrator import Orchestrator, HandoffResult
from app.core.exceptions import (
    HandoffAuthorizationError, 
    TranslationError,
    TransientError,
    PermanentError,
    RateLimitError,
    NetworkError,
    ExpiredTokenError,
    InvalidCredentialsError
)
from app.core.security import verify_engram_token
from app.messaging.connectors.registry import get_default_registry
from bridge.memory import memory_backend
from app.core.tui_bridge import tui_event_queue
from sqlmodel import Session, select
from app.db.models import PermissionProfile

logger = structlog.get_logger(__name__)

class MultiAgentOrchestrator:
    """
    Advanced Orchestration Layer for multi-agent coordination.
    Handles task parsing, agent selection, permission verification (EAT),
    sequential execution with dependency management, and result normalization.
    """
    def __init__(self, orchestrator: Optional[Orchestrator] = None):
        self.orchestrator = orchestrator or Orchestrator()
        self.connector_registry = get_default_registry()

    async def execute_task(self, user_task: str, eat: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Coordinates a complex task across multiple agents.
        
        1. Verifies the user's permissions via the EAT and DB profiles.
        2. Parses the task into subtasks and determines required agents.
        3. Routes each subtask to the relevant connector.
        4. Collects and merges responses into a normalized output.
        5. Handles retries and failures.
        """
        # 1. Verify EAT and extract user info
        try:
            auth_payload = verify_engram_token(eat)
            user_id = str(auth_payload.get("sub"))
            logger.info("Multi-agent task initiated", user_id=user_id, task=user_task)
        except Exception as e:
            logger.error("Authorization failed", error=str(e))
            raise HandoffAuthorizationError(f"Invalid or missing Engram Access Token (EAT): {str(e)}")

        # 2. Parse Task into a Plan (Intent Detection & Planner)
        plan = self._generate_plan(user_task)
        
        if not plan:
            tui_event_queue.put_nowait(f"⚠️ [bold yellow]Planner:[/] Could not determine subtasks for '{user_task[:30]}...'")
            return {
                "status": "error", 
                "message": "Task parser could not determine a multi-agent plan. Please name the agents (e.g., Claude, Perplexity, Slack) in your request."
            }

        # 3. Inform TUI of the plan
        tui_event_queue.put_nowait(f"📋 [bold cyan]Orchestration Plan:[/] Split into {len(plan)} agent steps.")

        results = {}
        context = {"original_task": user_task}
        correlation_id = str(uuid.uuid4())

        # 4. Execution Loop (Sequential with basic dependency mapping)
        max_retries = 3
        for i, step in enumerate(plan):
            agent_name = step["agent"].upper()
            sub_command = step["command"]
            
            # Simple context injection: replace {AgentName} with previous result if referenced
            for prev_agent, prev_res in results.items():
                pattern = f"\\{{{prev_agent}\\}}"
                if re.search(pattern, sub_command, re.IGNORECASE):
                    # Extract a summary or content for injection
                    injection_content = prev_res.get("content") or prev_res.get("summary") or prev_res.get("result") or str(prev_res)
                    sub_command = re.sub(pattern, str(injection_content), sub_command, flags=re.IGNORECASE)

            # Execution with Retries
            last_err = None
            for attempt in range(max_retries):
                tui_event_queue.put_nowait(f"🔄 [yellow]Step {i+1} (Att {attempt+1}):[/] Handing off to [bold]{agent_name}[/]")
                try:
                    # Permission check against Database Profile + EAT Scopes
                    if db:
                        await self._verify_db_permissions(db, user_id, agent_name, auth_payload)
                    else:
                        self._verify_eat_scopes(auth_payload, agent_name)

                    # Prepare payload for the agent
                    source_message = {
                        "command": sub_command,
                        "metadata": {
                            "correlation_id": correlation_id,
                            "step": i + 1,
                            "total_steps": len(plan),
                            "orchestrator": "MultiAgentOrchestrator/v1",
                            "attempt": attempt + 1
                        }
                    }
                    
                    # Execute via multi-hop Orchestrator (NL -> Agent Protocol)
                    handoff_res = await self.orchestrator.handoff_async(
                        source_message=source_message,
                        source_protocol="NL",
                        target_protocol=agent_name,
                        eat=eat,
                        db=db
                    )
                    
                    # Capture result
                    step_result = handoff_res.translated_message
                    
                    # Check if result is an error status (normalized connector response)
                    if isinstance(step_result, dict) and step_result.get("status") == "error":
                        err_type = step_result.get("error_type", "")
                        is_transient = step_result.get("is_transient", False)
                        
                        if "ExpiredToken" in err_type:
                            raise ExpiredTokenError(step_result.get("detail", "Token expired"))
                        if "InvalidCredentials" in err_type:
                            raise InvalidCredentialsError(step_result.get("detail", "Invalid credentials"))
                        
                        if is_transient or "RateLimit" in err_type or "Network" in err_type:
                            raise NetworkError(step_result.get("detail", "Transient tool error"))
                            
                        raise TranslationError(step_result.get("detail", "Permanent agent execution error"))

                    results[agent_name] = step_result
                    context[f"step_{i}_result"] = step_result
                    
                    # Record to Swarm Memory
                    memory_backend.write(
                        agent_id="Orchestrator",
                        protocol="A2A",
                        payload={
                            "correlation_id": correlation_id,
                            "step": i,
                            "agent": agent_name,
                            "status": "completed"
                        }
                    )
                    
                    tui_event_queue.put_nowait(f"✅ [green]Step {i+1} OK:[/] [bold]{agent_name}[/] finished.")
                    last_err = None
                    break # Success!

                except ExpiredTokenError as e:
                    tui_event_queue.put_nowait(f"🔑 [bold red]Auth Error:[/] Token for {agent_name} expired. Please refresh credentials.")
                    logger.warning("MultiAgent: token expired", agent=agent_name, error=str(e))
                    return {"status": "error", "error": "token_expired", "action_required": "REFRESH_CREDENTIALS", "detail": str(e)}
                
                except InvalidCredentialsError as e:
                    tui_event_queue.put_nowait(f"🚫 [bold red]Auth Error:[/] Invalid credentials for {agent_name}.")
                    logger.warning("MultiAgent: invalid credentials", agent=agent_name, error=str(e))
                    return {"status": "error", "error": "invalid_credentials", "detail": str(e)}

                except (TransientError, NetworkError, RateLimitError) as e:
                    last_err = e
                    logger.warning("Step transient failure", agent=agent_name, attempt=attempt+1, error=str(e))
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 * (attempt + 1)) # Backoff
                    else:
                        tui_event_queue.put_nowait(f"⏳ [red]Step {i+1} failed after retries:[/] {agent_name} is currently unavailable.")
                        # After 3 attempts, we can't do more
                
                except Exception as e:
                    logger.error("Step permanent failure", agent=agent_name, error=str(e), exc_info=True)
                    tui_event_queue.put_nowait(f"❌ [red]Orchestration aborted at {agent_name}:[/] Permanent error: {str(e)}")
                    return {
                        "status": "error",
                        "failed_step": i + 1,
                        "failed_agent": agent_name,
                        "error": str(e),
                        "partial_results": results
                    }
            
            if last_err:
                tui_event_queue.put_nowait(f"❌ [red]Orchestration aborted at {agent_name}:[/] Failed after {max_retries} attempts.")
                return {
                    "status": "error",
                    "failed_step": i + 1,
                    "failed_agent": agent_name,
                    "error": str(last_err),
                    "partial_results": results
                }

        # 5. Merge and Normalize Output
        final_summary = self._normalize_final_output(results, user_task)
        
        tui_event_queue.put_nowait(f"🏁 [bold green]Complex task synchronized successfully.[/]")
        
        return {
            "status": "success",
            "correlation_id": correlation_id,
            "results": results,
            "normalized_output": final_summary
        }

    def _generate_plan(self, task: str) -> List[Dict[str, Any]]:
        """
        Parses the natural language task into a plan of agent calls.
        Detects connector names and splits by sequence keywords.
        """
        plan = []
        # Support for: PERPLEXITY, CLAUDE, SLACK, OPENCLAW, MIROFISH
        known_agents = self.connector_registry.list_connectors()
        
        # Split into logical steps: "Step A, then Step B; finally Step C"
        steps = re.split(r"[,;] then | then | and then |; |finally ", task, flags=re.IGNORECASE)
        
        for step_text in steps:
            step_text = step_text.strip()
            if not step_text: continue
            
            # Find which agent is mentioned or implied
            target_agent = None
            for agent in known_agents:
                if agent.lower() in step_text.lower():
                    target_agent = agent
                    break
            
            # Heuristic: If 'post' or 'send' without agent name, imply SLACK if available
            if not target_agent and ("post" in step_text.lower() or "send" in step_text.lower()):
                if "SLACK" in known_agents:
                    target_agent = "SLACK"
            
            # Heuristic: If 'search' or 'research' or 'find' imply PERPLEXITY
            if not target_agent and ("search" in step_text.lower() or "research" in step_text.lower()):
                if "PERPLEXITY" in known_agents:
                    target_agent = "PERPLEXITY"

            if target_agent:
                plan.append({
                    "agent": target_agent,
                    "command": step_text
                })
        
        # If no explicit steps detected, try to find all agents mentioned anywhere
        if not plan:
            for agent in known_agents:
                if agent.lower() in task.lower():
                    plan.append({"agent": agent, "command": task})
                    
        return plan

    async def _verify_db_permissions(self, db: Session, user_id: str, agent_name: str, payload: Dict[str, Any]):
        """Checks both EAT scopes and database PermissionProfile."""
        # 1. Check EAT first (Fast)
        try:
            self._verify_eat_scopes(payload, agent_name)
            return # EAT is authoritative if it has the scope
        except HandoffAuthorizationError:
            pass # Fallback to DB check
            
        # 2. Check DB Profile (Precise)
        try:
            stmt = select(PermissionProfile).where(PermissionProfile.user_id == uuid.UUID(user_id))
            res = await db.execute(stmt)
            profile = res.scalars().first()
            
            if not profile:
                raise HandoffAuthorizationError(f"No permission profile found for user {user_id}")
                
            perms = profile.permissions or {}
            # Allow if agent_name is in keys or '*' is in keys
            if "*" in perms or agent_name.upper() in [k.upper() for k in perms.keys()]:
                return
                
            raise HandoffAuthorizationError(f"User profile does not permit access to agent '{agent_name}'")
        except ValueError:
             raise HandoffAuthorizationError(f"Invalid user_id in EAT: {user_id}")

    def _verify_eat_scopes(self, payload: Dict[str, Any], agent_name: str):
        allowed_tools = payload.get("allowed_tools", [])
        scopes = payload.get("scopes", {}) # tool -> [scopes]
        
        agent_key = agent_name.upper()
        
        if "*" in allowed_tools:
            return
            
        if "translator" in allowed_tools:
            t_scopes = scopes.get("translator", [])
            if "*" in t_scopes or agent_key in t_scopes:
                return

        if agent_key in [t.upper() for t in allowed_tools]:
            return
            
        raise HandoffAuthorizationError(f"EAT does not authorize access to tool '{agent_name}'")

    def _normalize_final_output(self, results: Dict[str, Any], original_task: str) -> Dict[str, Any]:
        """Merges results into a single cohesive response."""
        full_text = ""
        for agent, res in results.items():
            content = res.get("content") or res.get("summary") or res.get("result") or str(res)
            full_text += f"### {agent} Response\n{content}\n\n"
            
        return {
            "task_summary": f"Executed multi-agent orchestration for: {original_task}",
            "full_report": full_text.strip(),
            "completion_status": "Success",
            "agents_involved": list(results.keys()),
            "timestamp": asyncio.get_event_loop().time()
        }
