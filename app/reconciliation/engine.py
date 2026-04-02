import os
import uuid
import structlog
from typing import Dict, Any, List, Optional, Tuple
import torch
from sentence_transformers import SentenceTransformer, util
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.db.session import engine as db_engine
from app.db.models import ProtocolMapping, MappingFailureLog
from app.reconciliation.ontology import OntologyResolver

logger = structlog.get_logger(__name__)

class ReconciliationEngine:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.ontology = OntologyResolver()
        self.model = SentenceTransformer(model_name)
        self.ontology_concepts = self.ontology.get_concept_names()
        # Precompute ontology embeddings
        self.ontology_embeddings = self.model.encode(self.ontology_concepts, convert_to_tensor=True)
        self.similarity_threshold = 0.75
        self.auto_apply_threshold = 0.85

    def compute_similarity(self, term: str) -> List[Tuple[str, float]]:
        """Computes similarity between a term and ontology concepts."""
        term_embedding = self.model.encode(term, convert_to_tensor=True)
        cosine_scores = util.cos_sim(term_embedding, self.ontology_embeddings)[0]
        
        # Get scores and concepts
        scores = []
        for i, score in enumerate(cosine_scores):
            scores.append((self.ontology_concepts[i], float(score)))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    async def resolve_field(self, source_protocol: str, target_protocol: str, source_field: str) -> Optional[str]:
        """Attempts to resolve a field using semantic similarity and ontology reasoning."""
        # 1. First, check existing mappings in DB
        async with AsyncSession(db_engine) as session:
            query = select(ProtocolMapping).where(
                ProtocolMapping.source_protocol == source_protocol,
                ProtocolMapping.target_protocol == target_protocol,
                ProtocolMapping.is_active == True
            )
            result = await session.execute(query)
            mapping = result.scalars().first()
            
            if mapping and source_field in mapping.semantic_equivalents:
                return mapping.semantic_equivalents[source_field]

        # 2. Try ontology reasoning (synonyms, sameAs)
        concept = self.ontology.search_concept(source_field)
        if concept:
            logger.info("Ontology direct match found", concept=concept.name)
            await self._update_mapping(source_protocol, target_protocol, source_field, concept.name)
            return concept.name

        # 3. Use embedding similarity
        similarities = self.compute_similarity(source_field)
        best_match, score = similarities[0]
        
        logger.info("Semantic match attempt", source_field=source_field, best_match=best_match, score=score)
        
        # 4. Hybrid Scoring
        if score >= self.auto_apply_threshold:
            suggested_concept = self.ontology.search_concept(best_match)
            if suggested_concept:
                logger.info("Auto-applying mapping via ML/Ontology Hybrid", 
                    source_field=source_field, 
                    target_field=best_match
                )
                await self._update_mapping(source_protocol, target_protocol, source_field, best_match)
                return best_match
        
        # 5. Fallback
        suggestion = best_match if score >= self.similarity_threshold else None
        await self._log_failure(source_protocol, target_protocol, source_field, suggestion, score)
        return recommendation if (recommendation := suggestion) else None

    async def _update_mapping(self, source_protocol: str, target_protocol: str, source_field: str, target_field: str):
        async with AsyncSession(db_engine) as session:
            query = select(ProtocolMapping).where(
                ProtocolMapping.source_protocol == source_protocol,
                ProtocolMapping.target_protocol == target_protocol,
                ProtocolMapping.is_active == True
            )
            result = await session.execute(query)
            mapping = result.scalars().first()
            
            if not mapping:
                mapping = ProtocolMapping(
                    source_protocol=source_protocol,
                    target_protocol=target_protocol,
                    semantic_equivalents={source_field: target_field},
                    version=1,
                    is_active=True
                )
                session.add(mapping)
            else:
                mapping.version += 1
                mapping.semantic_equivalents[source_field] = target_field
                mapping.semantic_equivalents = dict(mapping.semantic_equivalents)
                session.add(mapping)
            
            await session.commit()
            logger.info("Persisted mapping adaptation", 
                source=source_protocol, 
                target=target_protocol, 
                field=source_field,
                version=mapping.version
            )

    async def _log_failure(self, source_protocol: str, target_protocol: str, source_field: str, suggestion: Optional[str], score: float):
        async with AsyncSession(db_engine) as session:
            failure = MappingFailureLog(
                source_protocol=str(source_protocol),
                target_protocol=str(target_protocol),
                source_field=str(source_field),
                model_suggestion=suggestion,
                model_confidence=score,
                error_type="SEMANTIC_MISMATCH",
                applied=False
            )
            session.add(failure)
            await session.commit()
            logger.warning("Logged mapping failure", source_field=source_field, suggestion=suggestion, confidence=score)

    async def repair_loop(self):
        """Processes unapplied failure logs and attempts to heal them."""
        async with AsyncSession(db_engine) as session:
            query = select(MappingFailureLog).where(MappingFailureLog.applied == False)
            result = await session.execute(query)
            failures = result.scalars().all()
            
            for failure in failures:
                if (failure.model_confidence or 0.0) >= self.auto_apply_threshold:
                    if failure.model_suggestion:
                        await self._update_mapping(
                            failure.source_protocol, 
                            failure.target_protocol, 
                            failure.source_field, 
                            failure.model_suggestion
                        )
                        failure.applied = True
                        session.add(failure)
            
            await session.commit()

reconciliation_engine = ReconciliationEngine()
