from __future__ import annotations

import json
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple

import networkx as nx
from sentence_transformers import SentenceTransformer
from sqlalchemy import Integer, case, func
from sqlmodel import select
import structlog
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

from app.core.config import settings
from app.db.models import (
    ExecutionType,
    ToolExecutionMetadata,
    ToolRegistry,
    ToolRoutingDecision,
)

logger = structlog.get_logger(__name__)

_GRAPH_CACHE: Dict[str, Tuple[float, nx.DiGraph]] = {}

def context_aware_prune_tools(
    tools: List[ToolRegistry],
    task_intent: str,
    conversation_history: List[Dict[str, str]] = None
) -> List[ToolRegistry]:
    """
    Pre-routing step: Embeds task intent + conversation history to dynamically 
    filter tools or compress schemas based on semantic relevance.
    """
    if not task_intent:
        return tools
        
    # Combine intent and recent history for context
    history_text = " ".join([m.get("content", "") for m in (conversation_history or [])[-3:]])
    context_text = f"{task_intent} {history_text}".strip()
    context_vec = _embed_text(context_text)
    
    pruned: List[ToolRegistry] = []
    logger.info("Starting context-aware pruning", context_length=len(context_text), original_tool_count=len(tools))
    
    for tool in tools:
        tool_text = _tool_base_text(tool)
        tool_vec = _embed_text(tool_text)
        similarity = _cosine_similarity(context_vec, tool_vec)
        
        # Semantic threshold to filter out irrelevant tools entirely
        if similarity < 0.2:
            logger.debug("Pruning tool based on semantic mismatch", tool=tool.name, similarity=similarity)
            continue
            
        # Compress schema based on history (e.g. drop irrelevant fields)
        # We apply heuristic compression preserving semantic meaning
        # In a real setup, a local LLM would restructure the schema.
        if hasattr(tool, 'input_schema') and isinstance(tool.input_schema, dict):
            props = tool.input_schema.get("properties", {})
            # Mock compression: if property mentions "metadata" but task doesn't, drop it
            if "metadata" in props and "metadata" not in context_text.lower():
                props.pop("metadata")
                tool.input_schema["properties"] = props
                
        pruned.append(tool)
        
    logger.info("Completed context-aware pruning", pruned_tool_count=len(pruned))
    return pruned



CLI_BACKEND = "CLI"
MCP_BACKEND = "MCP"
HTTP_BACKEND = "HTTP"


@dataclass(frozen=True)
class BackendStats:
    latency_ms: float
    success_rate: float
    token_cost: float
    context_overhead: float
    samples: int


@dataclass(frozen=True)
class BackendScore:
    backend: str
    similarity: float
    performance_score: float
    composite_score: float
    token_cost_est: float
    context_overhead_est: float
    latency_ms: float
    success_rate: float
    preference_score: float


@dataclass(frozen=True)
class RoutingDecision:
    backend: str
    candidates: List[BackendScore]
    task_description: str
    parallel_suggested: bool = False


@dataclass(frozen=True)
class RoutingWeights:
    similarity: float
    success: float
    latency: float
    token_cost: float
    context_overhead: float
    preference: float
    predictive: float

@dataclass(frozen=True)
class RoutingGuardrails:
    max_token_budget: int
    fallback_backend: str = CLI_BACKEND

class LoadPredictor(nn.Module):
    """Tiny neural net for load predictions."""
    def __init__(self, input_size=5, hidden_size=10):
        super(LoadPredictor, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        # Output represents a 'load factor' or predicted latency/success shift
        return self.sigmoid(x)

_PREDICTORS: Dict[str, LoadPredictor] = {}

def _get_predictor(backend: str) -> LoadPredictor:
    if backend not in _PREDICTORS:
        _PREDICTORS[backend] = LoadPredictor()
    return _PREDICTORS[backend]

def predict_future_metrics(
    backend: str, 
    history: List[ToolRoutingDecision],
    current_task_tokens: int
) -> Dict[str, float]:
    """
    Uses the predictor to estimate future performance based on recent history.
    """
    if not history:
        return {}
        
    model = _get_predictor(backend)
    # Feature engineering from history (take last 5 samples)
    recent = history[-5:]
    if len(recent) < 5:
        return {}
        
    # Features: [avg_latency, success_rate, avg_tokens, time_delta_index, current_load_est]
    latencies = [r.latency_ms or 0.0 for r in recent]
    successes = [1.0 if r.success else 0.0 for r in recent]
    tokens = [r.token_cost_actual or 0.0 for r in recent]
    
    # Normalize features roughly
    features = torch.tensor([
        np.mean(latencies) / 2000.0,
        np.mean(successes),
        np.mean(tokens) / 1000.0,
        current_task_tokens / 500.0,
        len(history) / 100.0  # Simple load proxy
    ], dtype=torch.float32)
    
    model.eval()
    with torch.no_grad():
        load_factor = model(features).item()
        
    # Shift baseline stats by load factor
    return {
        "latency_adjustment": 1.0 + (load_factor * 0.5), # up to 50% increase
        "success_adjustment": 1.0 - (load_factor * 0.1), # up to 10% decrease
        "token_adjustment": 1.0 + (load_factor * 0.05)   # minimal impact on tokens
    }


_DEFAULT_BACKEND_STATS = BackendStats(
    latency_ms=400.0,
    success_rate=0.98,
    token_cost=200.0,
    context_overhead=60.0,
    samples=0,
)


@lru_cache(maxsize=1)
def _embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.ROUTING_EMBEDDING_MODEL)


@lru_cache(maxsize=2048)
def _embed_text(text: str) -> Tuple[float, ...]:
    if not text:
        return tuple()
    model = _embedding_model()
    vector = model.encode(text, normalize_embeddings=True)
    return tuple(float(x) for x in vector)


def _cosine_similarity(vec_a: Tuple[float, ...], vec_b: Tuple[float, ...]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    length = min(len(vec_a), len(vec_b))
    return sum(vec_a[i] * vec_b[i] for i in range(length))


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / 4))


def _normalize_latency(latency_ms: float) -> float:
    if latency_ms <= 0:
        return 1.0
    return 1.0 / (1.0 + (latency_ms / 1000.0))


def _normalize_cost(cost_tokens: float, scale: float) -> float:
    if cost_tokens <= 0:
        return 1.0
    return 1.0 / (1.0 + (cost_tokens / scale))


def _weights_from_settings() -> RoutingWeights:
    return RoutingWeights(
        similarity=settings.ROUTING_WEIGHT_SIMILARITY,
        success=settings.ROUTING_WEIGHT_SUCCESS,
        latency=settings.ROUTING_WEIGHT_LATENCY,
        token_cost=settings.ROUTING_WEIGHT_TOKEN_COST,
        context_overhead=settings.ROUTING_WEIGHT_CONTEXT_OVERHEAD,
        preference=settings.ROUTING_WEIGHT_PREFERENCE,
        predictive=getattr(settings, "ROUTING_WEIGHT_PREDICTIVE", 0.15),
    )


def _exec_params(metadata: Optional[ToolExecutionMetadata]) -> Dict[str, Any]:
    if not metadata:
        return {}
    if getattr(metadata, "exec_params", None):
        return metadata.exec_params or {}
    if getattr(metadata, "metadata", None):
        return metadata.metadata or {}
    return {}


def available_backends(tool: ToolRegistry, metadata: Optional[ToolExecutionMetadata]) -> List[str]:
    if not metadata:
        return []
    params = _exec_params(metadata)
    backends: List[str] = []

    has_cli = (
        metadata.execution_type == ExecutionType.CLI
        or metadata.cli_wrapper is not None
        or bool(params.get("cli_command"))
        or bool(params.get("cli_wrapper"))
        or bool(metadata.docker_image)
    )
    has_mcp = (
        metadata.execution_type == ExecutionType.MCP
        or "mcp" in params
        or bool(params.get("mcp_endpoint"))
        or bool(params.get("mcp_server"))
    )
    has_http = (
        metadata.execution_type == ExecutionType.HTTP
        or bool(params.get("openapi_spec"))
        or bool(params.get("endpoint_url"))
        or bool(params.get("graphql_url"))
    )

    if has_cli:
        backends.append(CLI_BACKEND)
    if has_mcp:
        backends.append(MCP_BACKEND)
    if has_http:
        backends.append(HTTP_BACKEND)

    if not backends:
        backends.append(metadata.execution_type.value)

    return backends


def _tool_base_text(tool: ToolRegistry) -> str:
    action_names = ", ".join([a.get("name", "") for a in tool.actions or []])
    tags = ", ".join(tool.tags or [])
    return f"{tool.name}\n{tool.description}\nActions: {action_names}\nTags: {tags}"


def _backend_text(tool: ToolRegistry, metadata: ToolExecutionMetadata, backend: str) -> str:
    params = _exec_params(metadata)
    base = _tool_base_text(tool)
    if backend == CLI_BACKEND:
        cli_cmd = params.get("cli_command", tool.name)
        cli_help = params.get("help_output", "") or ""
        return f"{base}\nBackend: CLI\nCommand: {cli_cmd}\nHelp: {cli_help[:400]}"
    if backend == MCP_BACKEND:
        mcp_meta = params.get("mcp", params)
        return f"{base}\nBackend: MCP\nMetadata: {json.dumps(mcp_meta)[:500]}"
    if backend == HTTP_BACKEND:
        http_meta = {k: params.get(k) for k in ("endpoint_url", "graphql_url", "openapi_spec")}
        return f"{base}\nBackend: HTTP\nMetadata: {json.dumps(http_meta)[:500]}"
    return f"{base}\nBackend: {backend}"


def _estimate_context_overhead(tool: ToolRegistry, metadata: ToolExecutionMetadata, backend: str, task_text: str) -> float:
    params = _exec_params(metadata)
    task_tokens = estimate_tokens(task_text)
    if backend == CLI_BACKEND:
        cli_help = params.get("help_output", "") or ""
        cli_context = estimate_tokens(cli_help) * 0.15
        return max(10.0, cli_context)
    if backend in {MCP_BACKEND, HTTP_BACKEND}:
        schema_blob = json.dumps(tool.input_schema or {})
        actions_blob = json.dumps(tool.actions or [])
        exec_blob = json.dumps(params or {})
        context_tokens = estimate_tokens(schema_blob + actions_blob + exec_blob)
        return max(80.0, context_tokens - task_tokens)
    return 50.0


def _estimate_token_cost(
    tool: ToolRegistry,
    metadata: ToolExecutionMetadata,
    backend: str,
    task_text: str,
) -> float:
    params = _exec_params(metadata)
    task_tokens = estimate_tokens(task_text)
    if backend == CLI_BACKEND:
        expected = float(params.get("expected_output_tokens", 120))
        return task_tokens + expected
    expected = float(params.get("expected_response_tokens", 400))
    if backend == HTTP_BACKEND:
        expected = float(params.get("expected_response_tokens", 350))
    context_overhead = _estimate_context_overhead(tool, metadata, backend, task_text)
    return task_tokens + expected + context_overhead


def _backend_preference(task_text: str, tool: ToolRegistry, backend: str) -> float:
    task_lower = task_text.lower()
    cli_terms = {
        "file", "filesystem", "git", "diff", "grep", "rg", "ls", "cat", "mkdir",
        "rm", "mv", "cp", "chmod", "shell", "terminal", "command", "pytest", "pip",
    }
    mcp_terms = {
        "saas", "oauth", "token", "auth", "api", "webhook", "slack", "notion",
        "jira", "salesforce", "stripe", "zendesk", "gmail", "calendar", "hubspot",
    }
    cli_hits = sum(1 for term in cli_terms if term in task_lower)
    mcp_hits = sum(1 for term in mcp_terms if term in task_lower)

    tag_text = " ".join(tool.tags or []).lower()
    if "cli" in tag_text or "local" in tag_text:
        cli_hits += 1
    if "saas" in tag_text or "api" in tag_text:
        mcp_hits += 1

    score = 0.0
    if backend == CLI_BACKEND:
        score = (cli_hits * 0.2) - (mcp_hits * 0.1)
    elif backend in {MCP_BACKEND, HTTP_BACKEND}:
        score = (mcp_hits * 0.2) - (cli_hits * 0.1)
    return max(-1.0, min(1.0, score))


def build_tool_graph(
    tool: ToolRegistry,
    metadata: ToolExecutionMetadata,
    stats_by_backend: Dict[str, BackendStats],
) -> nx.DiGraph:
    graph = nx.DiGraph()
    tool_node = str(tool.id)
    graph.add_node(
        tool_node,
        name=tool.name,
        description=tool.description,
        tags=tool.tags or [],
        execution_type=metadata.execution_type.value if metadata else None,
    )
    for backend, stats in stats_by_backend.items():
        graph.add_node(backend, type="backend")
        graph.add_edge(
            tool_node,
            backend,
            latency_ms=stats.latency_ms,
            success_rate=stats.success_rate,
            token_cost=stats.token_cost,
            context_overhead=stats.context_overhead,
            samples=stats.samples,
        )
    return graph


def _cached_tool_graph(
    tool: ToolRegistry,
    metadata: ToolExecutionMetadata,
    stats_by_backend: Dict[str, BackendStats],
) -> nx.DiGraph:
    cache_key = f"{tool.id}:{tool.updated_at}:{metadata.updated_at}:{hash(json.dumps(stats_by_backend, default=str, sort_keys=True))}"
    now = time.time()
    cached = _GRAPH_CACHE.get(cache_key)
    if cached and (now - cached[0]) < settings.ROUTING_CACHE_TTL_SECONDS:
        return cached[1]
    graph = build_tool_graph(tool, metadata, stats_by_backend)
    _GRAPH_CACHE[cache_key] = (now, graph)
    return graph


def route_tool_backend_sync(
    tool: ToolRegistry,
    metadata: ToolExecutionMetadata,
    task_description: str,
    stats_by_backend: Dict[str, BackendStats],
    history_by_backend: Optional[Dict[str, List[ToolRoutingDecision]]] = None,
) -> RoutingDecision:
    weights = _weights_from_settings()
    task_text = (task_description or "").strip()
    task_vec = _embed_text(task_text)
    graph = _cached_tool_graph(tool, metadata, stats_by_backend)
    tool_node = str(tool.id)

    candidates: List[BackendScore] = []
    for backend in stats_by_backend.keys():
        edge = graph.edges[tool_node, backend]
        stats = BackendStats(
            latency_ms=edge.get("latency_ms", _DEFAULT_BACKEND_STATS.latency_ms),
            success_rate=edge.get("success_rate", _DEFAULT_BACKEND_STATS.success_rate),
            token_cost=edge.get("token_cost", _DEFAULT_BACKEND_STATS.token_cost),
            context_overhead=edge.get("context_overhead", _DEFAULT_BACKEND_STATS.context_overhead),
            samples=edge.get("samples", _DEFAULT_BACKEND_STATS.samples),
        )
        backend_text = _backend_text(tool, metadata, backend)
        backend_vec = _embed_text(backend_text)
        similarity = _cosine_similarity(task_vec, backend_vec)

        # Predictive adjustment
        task_tokens = estimate_tokens(task_text)
        history = (history_by_backend or {}).get(backend, [])
        adjustments = predict_future_metrics(backend, history, task_tokens)
        lat_adj = adjustments.get("latency_adjustment", 1.0)
        suc_adj = adjustments.get("success_adjustment", 1.0)

        latency_score = _normalize_latency(stats.latency_ms * lat_adj)
        success_score = stats.success_rate * suc_adj
        token_score = _normalize_cost(stats.token_cost, scale=600.0)
        context_score = _normalize_cost(stats.context_overhead, scale=500.0)
        preference_score = _backend_preference(task_text, tool, backend)

        performance_score = (
            (weights.success * success_score)
            + (weights.latency * latency_score)
            + (weights.token_cost * token_score)
            + (weights.context_overhead * context_score)
            + (weights.preference * preference_score)
        )
        composite_score = (weights.similarity * similarity) + performance_score

        candidates.append(
            BackendScore(
                backend=backend,
                similarity=similarity,
                performance_score=performance_score,
                composite_score=composite_score,
                token_cost_est=stats.token_cost,
                context_overhead_est=stats.context_overhead,
                latency_ms=stats.latency_ms,
                success_rate=stats.success_rate,
                preference_score=preference_score,
            )
        )

    if not candidates:
        return RoutingDecision(backend=metadata.execution_type.value, candidates=[], task_description=task_text)

    candidates.sort(key=lambda c: c.composite_score, reverse=True)
    
    # Apply rules for optimal choice and budget guardrails
    best = candidates[0]
    
    # FALLBACK: Budget Guardrails
    max_tokens = getattr(settings, "ROUTING_BUDGET_TOKEN_LIMIT", 8000)
    if best.backend == MCP_BACKEND and best.token_cost_est > max_tokens:
        cli_candidate = next((c for c in candidates if c.backend == CLI_BACKEND), None)
        if cli_candidate and cli_candidate.token_cost_est < max_tokens:
            logger.info("Budget guardrail triggered: Falling back to CLI from MCP", 
                        mcp_cost=best.token_cost_est, cli_cost=cli_candidate.token_cost_est)
            best = cli_candidate
            
    # PARALLEL EXECUTION: If competitive scores and low reliability
    parallel_suggested = False
    if len(candidates) > 1:
        second = candidates[1]
        score_diff = best.composite_score - second.composite_score
        confidence_threshold = getattr(settings, "ROUTING_PARALLEL_CONFIDENCE_THRESHOLD", 0.05)
        if score_diff < confidence_threshold and best.success_rate < 0.9:
            logger.info("Suggesting parallel execution due to low confidence and reliability",
                        best_backend=best.backend, second_backend=second.backend, diff=score_diff)
            parallel_suggested = True

    return RoutingDecision(
        backend=best.backend, 
        candidates=candidates, 
        task_description=task_text,
        parallel_suggested=parallel_suggested # Need to update dataclass
    )


async def fetch_backend_stats(
    session,
    tool_id: Any,
    backends: Iterable[str],
    window_hours: Optional[int] = None,
    include_history: bool = False,
) -> Tuple[Dict[str, BackendStats], Dict[str, List[ToolRoutingDecision]]]:
    backend_list = list(backends)
    if not backend_list:
        return {}, {}
    window = window_hours if window_hours is not None else settings.ROUTING_STATS_WINDOW_HOURS
    cutoff = None
    if window and window > 0:
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(hours=window)

    success_case = case(
        (ToolRoutingDecision.success == True, 1),  # noqa: E712
        else_=0,
    )

    query = select(
        ToolRoutingDecision.backend_selected,
        func.count(ToolRoutingDecision.id),
        func.avg(ToolRoutingDecision.latency_ms),
        func.avg(success_case.cast(Integer)),
        func.avg(ToolRoutingDecision.token_cost_actual),
        func.avg(ToolRoutingDecision.context_overhead_est),
    ).where(
        ToolRoutingDecision.tool_id == tool_id,
        ToolRoutingDecision.backend_selected.in_(backend_list),
    )
    if cutoff:
        query = query.where(ToolRoutingDecision.created_at >= cutoff)
    query = query.group_by(ToolRoutingDecision.backend_selected)

    result = await session.execute(query)
    rows = result.all()

    stats: Dict[str, BackendStats] = {b: _DEFAULT_BACKEND_STATS for b in backend_list}
    for row in rows:
        backend, count, avg_latency, avg_success, avg_token, avg_context = row
        stats[backend] = BackendStats(
            latency_ms=float(avg_latency or _DEFAULT_BACKEND_STATS.latency_ms),
            success_rate=float(avg_success or _DEFAULT_BACKEND_STATS.success_rate),
            token_cost=float(avg_token or _DEFAULT_BACKEND_STATS.token_cost),
            context_overhead=float(avg_context or _DEFAULT_BACKEND_STATS.context_overhead),
            samples=int(count or 0),
        )

    history: Dict[str, List[ToolRoutingDecision]] = {}
    if include_history:
        # Fetch last 10 samples for each backend
        for backend in backend_list:
            h_query = select(ToolRoutingDecision).where(
                ToolRoutingDecision.tool_id == tool_id,
                ToolRoutingDecision.backend_selected == backend
            ).order_by(ToolRoutingDecision.created_at.desc()).limit(10)
            h_res = await session.execute(h_query)
            history[backend] = list(h_res.scalars().all())

    return stats, history


def estimate_backend_stats(
    tool: ToolRegistry,
    metadata: ToolExecutionMetadata,
    backend: str,
    task_description: str,
    existing: Optional[BackendStats],
) -> BackendStats:
    base = existing or _DEFAULT_BACKEND_STATS
    context_overhead = _estimate_context_overhead(tool, metadata, backend, task_description)
    token_cost = _estimate_token_cost(tool, metadata, backend, task_description)
    return BackendStats(
        latency_ms=base.latency_ms,
        success_rate=base.success_rate,
        token_cost=token_cost,
        context_overhead=context_overhead,
        samples=base.samples,
    )


async def log_routing_decision(
    session,
    tool_id: Any,
    action: Optional[str],
    decision: RoutingDecision,
) -> ToolRoutingDecision:
    candidates_payload = [
        {
            "backend": c.backend,
            "similarity": c.similarity,
            "performance_score": c.performance_score,
            "composite_score": c.composite_score,
            "token_cost_est": c.token_cost_est,
            "context_overhead_est": c.context_overhead_est,
            "latency_ms": c.latency_ms,
            "success_rate": c.success_rate,
            "preference_score": c.preference_score,
        }
        for c in decision.candidates
    ]
    best = decision.candidates[0] if decision.candidates else None
    record = ToolRoutingDecision(
        tool_id=tool_id,
        action=action,
        backend_selected=decision.backend,
        backend_candidates=candidates_payload,
        task_description=decision.task_description,
        similarity_score=best.similarity if best else 0.0,
        performance_score=best.performance_score if best else 0.0,
        composite_score=best.composite_score if best else 0.0,
        token_cost_est=best.token_cost_est if best else 0.0,
        context_overhead_est=best.context_overhead_est if best else 0.0,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    logger.info(
        "Tool routing decision logged",
        tool_id=str(tool_id),
        backend=decision.backend,
        candidates=len(decision.candidates),
    )
    return record


async def finalize_routing_decision(
    session,
    decision_id: Any,
    success: bool,
    latency_ms: float,
    token_cost_actual: float,
    error: Optional[str] = None,
) -> None:
    record = await session.get(ToolRoutingDecision, decision_id)
    if not record:
        return
    record.success = success
    record.latency_ms = latency_ms
    record.token_cost_actual = token_cost_actual
    record.error = error
    from datetime import datetime, timezone

    record.completed_at = datetime.now(timezone.utc)
    session.add(record)
    await session.commit()
    logger.info(
        "Tool routing decision finalized",
        decision_id=str(decision_id),
        success=success,
        latency_ms=latency_ms,
    )
