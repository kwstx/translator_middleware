import asyncio
import aiohttp
import structlog
from datetime import datetime, timezone
from typing import List, Dict, Any, Set, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from app.db.models import AgentRegistry, ProtocolMapping
from app.db.session import engine

logger = structlog.get_logger(__name__)


class DiscoveryService:
    """
    Service responsible for agent discovery, health monitoring, and collaboration matching.

    Periodically pings registered agents via their endpoint_urls using aiohttp
    to update availability status in the AgentRegistry. Also provides a method
    to find compatible collaborators using a compatibility score formula:

        score = (shared_protocols + mappable_protocols) / total_protocols

    where:
        - shared_protocols: protocols supported by both agents directly.
        - mappable_protocols: protocols the collaborator supports that we can
          reach via ProtocolMapping translations.
        - total_protocols: total protocols the candidate collaborator supports.
    """

    DEFAULT_PING_TIMEOUT_SECONDS = 5
    DEFAULT_HEALTH_PATH = "/health"

    def __init__(self, ping_interval: int = 60, ping_timeout: int = 5):
        """
        Args:
            ping_interval: Seconds between each discovery cycle.
            ping_timeout: Seconds before an individual agent ping times out.
        """
        self.ping_interval = ping_interval
        self.ping_timeout = aiohttp.ClientTimeout(total=ping_timeout)
        self._ping_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start_periodic_discovery(self):
        """Starts the background task for periodic agent pinging."""
        if self._ping_task is not None:
            logger.warning("DiscoveryService: Periodic discovery already running.")
            return

        logger.info(
            "DiscoveryService: Starting periodic discovery.",
            interval_seconds=self.ping_interval,
        )
        self._ping_task = asyncio.create_task(self._ping_agents_loop())

    async def stop_periodic_discovery(self):
        """Stops the periodic discovery background task gracefully."""
        if self._ping_task:
            logger.info("DiscoveryService: Stopping periodic discovery.")
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None
            logger.info("DiscoveryService: Periodic discovery stopped.")

    # ------------------------------------------------------------------
    # Periodic Ping Loop
    # ------------------------------------------------------------------

    async def _ping_agents_loop(self):
        """Main loop that periodically pings every registered agent."""
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        while True:
            try:
                async with async_session() as session:
                    query = select(AgentRegistry)
                    result = await session.execute(query)
                    agents = result.scalars().all()

                    if agents:
                        logger.info(
                            "DiscoveryService: Pinging registered agents.",
                            agent_count=len(agents),
                        )
                        async with aiohttp.ClientSession(
                            timeout=self.ping_timeout
                        ) as client_session:
                            tasks = [
                                self._ping_agent(client_session, agent, session)
                                for agent in agents
                            ]
                            await asyncio.gather(*tasks, return_exceptions=True)

                        await session.commit()
                        logger.info(
                            "DiscoveryService: Agent health statuses committed to registry."
                        )

                        # Recalculate and update reliability metrics for any active agents.
                        # This enables real-time weighted Dijkstra routing in the Orchestrator.
                        try:
                            await self.update_agent_metrics(session)
                            logger.info(
                                "DiscoveryService: Reliability metrics updated for agents."
                            )
                        except Exception as e:
                            logger.error(
                                f"DiscoveryService: Failed to update agent metrics: {str(e)}"
                            )
                    else:
                        logger.debug(
                            "DiscoveryService: No agents registered for discovery."
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "DiscoveryService: Error in ping loop",
                    error=str(e),
                    exc_info=True,
                )

            await asyncio.sleep(self.ping_interval)

    async def _ping_agent(
        self,
        client_session: aiohttp.ClientSession,
        agent: AgentRegistry,
        db_session: AsyncSession,
    ):
        """
        Pings a single agent's health endpoint and updates its registry entry.

        The agent is marked active if the health endpoint returns HTTP 200,
        otherwise it is marked inactive.
        """
        url = (
            agent.endpoint_url
            if agent.endpoint_url.startswith("http")
            else f"http://{agent.endpoint_url}"
        )
        health_url = url.rstrip("/") + self.DEFAULT_HEALTH_PATH
        is_active = False

        try:
            async with client_session.get(health_url) as response:
                is_active = response.status == 200
        except asyncio.TimeoutError:
            logger.debug(
                "DiscoveryService: Ping timed out for agent",
                agent_id=str(agent.agent_id),
                health_url=health_url,
            )
        except aiohttp.ClientError as e:
            logger.debug(
                "DiscoveryService: Ping failed for agent",
                agent_id=str(agent.agent_id),
                error=str(e),
            )
        except Exception as e:
            logger.warning(
                "DiscoveryService: Unexpected error pinging agent",
                agent_id=str(agent.agent_id),
                error=str(e),
            )

        # Integration with DynamicRuleSynthesizer for self-healing mapping
        if is_active and agent.documentation_url:
            from app.semantic.dynamic_rule_synthesizer import DynamicRuleSynthesizer
            synthesizer = DynamicRuleSynthesizer(db_session)
            await synthesizer.sync_agent(agent)

        # Update agent status in registry
        previous_status = agent.is_active
        agent.is_active = is_active
        agent.last_seen = datetime.now(timezone.utc)
        db_session.add(agent)

        if previous_status != is_active:
            status_label = "ONLINE" if is_active else "OFFLINE"
            logger.info(
                "DiscoveryService: Agent status changed",
                agent_id=str(agent.agent_id),
                status=status_label,
            )

    # ------------------------------------------------------------------
    # Performance Monitoring
    # ------------------------------------------------------------------

    async def update_agent_metrics(self, session: AsyncSession):
        """
        Recalculates avg_latency and success_rate for all active agents
        based on historical AgentMessage logs.
        """
        from app.db.models import AgentMessage, AgentMessageStatus
        from sqlalchemy import func
        
        logger.info("DiscoveryService: Updating agent performance metrics from logs.")
        
        # 1. Fetch all agents
        query = select(AgentRegistry)
        result = await session.execute(query)
        agents = result.scalars().all()
        
        for agent in agents:
            # Calculate Success Rate
            # We look at messages in the last 24h or similar? 
            # For now, let's just take all historical data or a reasonable window.
            msg_query = select(AgentMessage).where(AgentMessage.agent_id == agent.agent_id)
            msg_result = await session.execute(msg_query)
            messages = msg_result.scalars().all()
            
            if not messages:
                continue
                
            total = len(messages)
            acked = len([m for m in messages if m.status == AgentMessageStatus.ACKED])
            agent.success_rate = acked / total
            
            # Calculate Latency (only for ACKED messages)
            latencies = []
            for m in messages:
                if m.status == AgentMessageStatus.ACKED and m.acked_at and m.created_at:
                    diff = (m.acked_at - m.created_at).total_seconds()
                    latencies.append(max(0, diff))
            
            if latencies:
                agent.avg_latency = sum(latencies) / len(latencies)
            
            session.add(agent)
            logger.debug(
                "Agent metrics updated", 
                agent_id=str(agent.agent_id), 
                success_rate=round(agent.success_rate, 2),
                avg_latency=round(agent.avg_latency, 3)
            )
            
        await session.commit()

    # ------------------------------------------------------------------
    # Collaboration Matching
    # ------------------------------------------------------------------

    @staticmethod
    async def find_collaborators(
        session: AsyncSession,
        source_protocols: List[str],
        min_score: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Finds rival/collaborator agents with a compatibility score >= min_score.

        Formula:
            score = (shared_protocols + mappable_protocols) / total_protocols

        Args:
            session: Active async database session.
            source_protocols: Protocols the requesting agent supports.
            min_score: Minimum compatibility score threshold (default 0.7).

        Returns:
            List of dicts containing the agent record and its compatibility score,
            sorted by score descending.
        """
        # 1. Fetch all available protocol mappings to determine translation capabilities
        mapping_query = select(ProtocolMapping)
        mapping_result = await session.execute(mapping_query)
        mappings = mapping_result.scalars().all()

        source_set = {p.upper() for p in source_protocols}

        # Protocols we can reach from what the source supports via translation
        mappable_targets: Set[str] = {
            m.target_protocol.upper()
            for m in mappings
            if m.source_protocol.upper() in source_set
        }

        # 2. Fetch all currently active candidate agents
        agent_query = select(AgentRegistry).where(AgentRegistry.is_active == True)  # noqa: E712
        agent_result = await session.execute(agent_query)
        candidates = agent_result.scalars().all()

        collaborators: List[Dict[str, Any]] = []

        for agent in candidates:
            target_protocols = {p.upper() for p in agent.supported_protocols}
            if not target_protocols:
                continue

            # Directly shared protocols
            shared = source_set.intersection(target_protocols)
            # Protocols the candidate has that we can translate to (but don't share natively)
            mappable = target_protocols.intersection(mappable_targets) - source_set

            score = (len(shared) + len(mappable)) / len(target_protocols)

            if score >= min_score:
                logger.info(
                    "DiscoveryService: Collaborator candidate",
                    agent_id=str(agent.agent_id),
                    score=round(score, 2),
                    shared=len(shared),
                    mappable=len(mappable),
                    total=len(target_protocols),
                )
                collaborators.append(
                    {
                        "agent": agent,
                        "compatibility_score": round(score, 4),
                        "shared_protocols": sorted(shared),
                        "mappable_protocols": sorted(mappable),
                    }
                )

        # Sort by score descending so the best matches come first
        collaborators.sort(key=lambda c: c["compatibility_score"], reverse=True)
        return collaborators

    @staticmethod
    async def find_collaborators_simple(
        session: AsyncSession,
        source_protocols: List[str],
        min_score: float = 0.7,
    ) -> List[AgentRegistry]:
        """
        Simplified version that returns only AgentRegistry objects (for the API
        response_model compatibility).
        """
        results = await DiscoveryService.find_collaborators(
            session=session,
            source_protocols=source_protocols,
            min_score=min_score,
        )
        return [r["agent"] for r in results]
