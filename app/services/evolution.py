from __future__ import annotations
import uuid
import json
import structlog
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlmodel import select, text
from sqlalchemy.ext.asyncio import AsyncSession
import semver

from app.db.models import (
    ToolRegistry,
    ToolExecutionMetadata,
    ToolEvolution,
    ToolRoutingDecision,
    EvolutionFeedbackType,
)
from app.core.config import settings

logger = structlog.get_logger(__name__)

class ToolEvolutionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_tool_signals(self, tool_id: uuid.UUID):
        """
        Fetches signals for a specific tool from the Feature Store view.
        """
        stmt = text("SELECT * FROM tool_evolution_signals_v1 WHERE tool_id = :tool_id")
        result = await self.session.execute(stmt, {"tool_id": str(tool_id)})
        return result.mappings().first()

    async def propose_evolution(self, tool_id: uuid.UUID) -> Optional[ToolEvolution]:
        """
        Analyzes tool performance and user feedback to propose an evolution.
        Uses Reinforcement Learning signals (success/failure) as rewards.
        """
        tool = await self.session.get(ToolRegistry, tool_id)
        if not tool:
            return None

        signals = await self.get_tool_signals(tool_id)
        if not signals or signals["total_executions"] < 10:
            logger.info("Not enough data to evolve tool", tool_id=tool_id)
            return None

        # Logic for 'Small Model fine-tuning' placeholder 
        # In a real scenario, this would call a transformers pipeline.
        # Here we simulate with architectural logic based on signals.
        
        evolution_type = None
        diff_payload = {}
        
        # Example RL Rule: If success rate < 0.7, refine description or parameters
        if signals["success_rate"] < 0.7:
            evolution_type = "description_refinement"
            # Simulate SFT/LLM refinement:
            diff_payload["description"] = f"{tool.description} (Self-corrected: Optimized for higher success rate based on {signals['total_executions']} samples)"
            
        # Example RL Rule: If high negative feedback, adjust default parameters
        if signals["avg_user_rating"] and signals["avg_user_rating"] < 0.4:
            evolution_type = "params_optimization"
            # Simulate refinement:
            diff_payload["actions"] = self._refine_actions(tool.actions)

        if not evolution_type:
            return None

        # Automatic Versioning (Semantic Versioning)
        current_version = tool.version or "0.1.0"
        try:
            ver = semver.VersionInfo.parse(current_version)
            new_version = str(ver.bump_patch())
        except:
            new_version = "0.1.1"

        evolution = ToolEvolution(
            tool_id=tool_id,
            previous_version=current_version,
            new_version=new_version,
            change_type=evolution_type,
            diff_payload=diff_payload,
            evolution_signals=dict(signals),
            confidence_score=0.85, # Mock confidence
            applied=False
        )
        
        self.session.add(evolution)
        await self.session.commit()
        logger.info("Evolution proposed", tool_id=tool_id, version=new_version)
        return evolution

    async def apply_evolution(self, evolution_id: uuid.UUID) -> Optional[ToolEvolution]:
        """
        Actually applies the proposed evolution to the tool registry.
        """
        evolution = await self.session.get(ToolEvolution, evolution_id)
        if not evolution or evolution.applied:
            return None

        tool = await self.session.get(ToolRegistry, evolution.tool_id)
        if not tool:
            return None

        # Apply version and updates to tool registry (Hot-redeploy)
        tool.version = evolution.new_version
        if "description" in evolution.diff_payload:
            tool.description = evolution.diff_payload["description"]
        if "actions" in evolution.diff_payload:
            tool.actions = evolution.diff_payload["actions"]
            
        evolution.applied = True
        evolution.applied_at = datetime.now(timezone.utc)
        
        self.session.add(tool)
        self.session.add(evolution)
        await self.session.commit()
        logger.info("Tool evolved and hot-redeployed", tool_id=tool.id, version=tool.version)
        return evolution

    async def get_evolution_status(self) -> Dict[str, Any]:
        """
        Aggregates summary of evolution progress across all tools.
        """
        pending_stmt = select(ToolEvolution, ToolRegistry.name).join(ToolRegistry, ToolEvolution.tool_id == ToolRegistry.id).where(ToolEvolution.applied == False)
        pending_result = await self.session.execute(pending_stmt)
        pending_data = []
        for row in pending_result:
            evo, name = row
            evo_dict = evo.model_dump()
            evo_dict["tool_name"] = name
            pending_data.append(evo_dict)

        total_stmt = select(ToolEvolution)
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalars().all()

        return {
            "pending_count": len(pending_data),
            "total_evolutions": len(total),
            "pending_proposals": pending_data,
            "last_updated": datetime.now(timezone.utc)
        }

    def _refine_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Mock logic to 'optimize' action parameters or types
        # In practice: DistilBERT could be used to classify parameter usage errors
        refined = []
        for action in actions:
            # Add 'recovery_hint' to schemas for failing actions
            if "input_schema" in action:
                action["input_schema"]["_evolution_hint"] = "Strict type checking applied via self-evolution"
            refined.append(action)
        return refined

    async def run_evolution_loop(self):
        """
        Executes evolution for all tools that have significant execution history.
        """
        stmt = select(ToolRegistry.id)
        result = await self.session.execute(stmt)
        tool_ids = result.scalars().all()
        
        for tool_id in tool_ids:
            try:
                await self.propose_evolution(tool_id)
            except Exception as e:
                logger.error("Failed to evolve tool", tool_id=tool_id, error=str(e))
