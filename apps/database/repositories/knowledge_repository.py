"""Knowledge base repository for learning mechanism."""

import logging
from typing import List, Optional
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import KnowledgeBase

logger = logging.getLogger(__name__)


class KnowledgeRepository:
    """Repository for Knowledge Base operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pattern(
        self,
        category: str,
        pattern: str,
        solution: str,
        task_id: Optional[str] = None,
        confidence_score: float = 0.5,
    ) -> KnowledgeBase:
        """Create a new knowledge pattern."""
        knowledge = KnowledgeBase(
            task_id=task_id,
            category=category,
            pattern=pattern,
            solution=solution,
            confidence_score=confidence_score,
            success_count=0,
            failure_count=0,
        )

        self.session.add(knowledge)
        await self.session.commit()
        await self.session.refresh(knowledge)

        logger.info(f"Created knowledge pattern in category {category}")
        return knowledge

    async def record_success(self, knowledge_id: int) -> None:
        """Record a successful use of this pattern."""
        stmt = (
            update(KnowledgeBase)
            .where(KnowledgeBase.id == knowledge_id)
            .values(
                success_count=KnowledgeBase.success_count + 1,
                confidence_score=KnowledgeBase.confidence_score * 1.1,  # Increase confidence
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def record_failure(self, knowledge_id: int) -> None:
        """Record a failed use of this pattern."""
        stmt = (
            update(KnowledgeBase)
            .where(KnowledgeBase.id == knowledge_id)
            .values(
                failure_count=KnowledgeBase.failure_count + 1,
                confidence_score=KnowledgeBase.confidence_score * 0.9,  # Decrease confidence
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_best_patterns(
        self,
        category: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 10,
    ) -> List[KnowledgeBase]:
        """Get best patterns by confidence score."""
        query = select(KnowledgeBase).where(KnowledgeBase.confidence_score >= min_confidence)

        if category:
            query = query.where(KnowledgeBase.category == category)

        query = query.order_by(desc(KnowledgeBase.confidence_score)).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_patterns(self, search_text: str, limit: int = 5) -> List[KnowledgeBase]:
        """Search patterns by text."""
        query = (
            select(KnowledgeBase)
            .where(KnowledgeBase.pattern.ilike(f"%{search_text}%"))
            .order_by(desc(KnowledgeBase.confidence_score))
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())
