"""Conversation manager for multi-turn intelligent dialogues."""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from apps.database.repositories import SessionRepository
from apps.orchestrator.llm_router import LLMRouter, LLMRequest

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages multi-turn conversations with context and memory."""

    def __init__(
        self,
        llm_router: LLMRouter,
        db_session: AsyncSession,
    ):
        self.llm_router = llm_router
        self.db_session = db_session
        self.session_repo = SessionRepository(db_session)

        # In-memory context for active sessions
        self.active_contexts: Dict[str, Dict[str, Any]] = {}

    async def start_session(
        self,
        user_id: Optional[int] = None,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start a new conversation session."""
        session_id = str(uuid.uuid4())

        # Create session in database
        session = await self.session_repo.create_session(
            session_id=session_id,
            user_id=user_id,
            context=initial_context or {},
        )

        # Initialize in-memory context
        self.active_contexts[session_id] = {
            "history": [],
            "facts": {},
            "last_topic": None,
            "user_preferences": {},
            "pending_questions": [],
        }

        logger.info(f"Started conversation session {session_id}")
        return session_id

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a user message in conversation."""
        # Get or create context
        if session_id not in self.active_contexts:
            await self._load_session_context(session_id)

        context = self.active_contexts[session_id]

        # Add user message to history
        await self.session_repo.add_message(
            session_id=session_id,
            role="user",
            content=user_message,
            metadata=metadata,
        )

        context["history"].append({"role": "user", "content": user_message})

        # Analyze message intent
        intent = await self._analyze_intent(user_message, context)

        # Check if clarification needed
        if intent.get("needs_clarification"):
            clarification = await self._generate_clarification(user_message, context)

            # Save assistant message
            await self.session_repo.add_message(
                session_id=session_id,
                role="assistant",
                content=clarification,
                metadata={"type": "clarification"},
            )

            context["history"].append({"role": "assistant", "content": clarification})
            context["pending_questions"].append(clarification)

            return {
                "response": clarification,
                "type": "clarification",
                "intent": intent,
                "requires_input": True,
            }

        # Generate contextual response
        response = await self._generate_response(user_message, context, intent)

        # Save assistant message
        await self.session_repo.add_message(
            session_id=session_id,
            role="assistant",
            content=response["content"],
            metadata={"type": "response", "intent": intent},
        )

        context["history"].append({"role": "assistant", "content": response["content"]})

        # Update context
        await self._update_context(session_id, context, intent)

        return {
            "response": response["content"],
            "type": "response",
            "intent": intent,
            "requires_input": False,
            "suggested_actions": response.get("suggested_actions", []),
        }

    async def _analyze_intent(
        self,
        message: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze user message intent."""
        # Build context-aware prompt
        history_summary = self._summarize_history(context["history"][-5:])

        prompt = f"""Analyze the following user message in the context of our conversation.

Recent conversation:
{history_summary}

Current message: "{message}"

Determine:
1. Intent type (question, command, clarification, feedback)
2. Whether clarification is needed
3. Key entities mentioned
4. Urgency level

Respond in JSON format."""

        llm_request = LLMRequest(
            prompt=prompt,
            system_message="You are an intent analyzer for a DevOps AI agent.",
            temperature=0.2,
            max_tokens=500,
        )

        try:
            response = await self.llm_router.complete(llm_request)

            # Parse JSON response
            import json

            intent = json.loads(response.content)
            return intent

        except Exception as e:
            logger.warning(f"Intent analysis failed: {e}")
            return {
                "intent_type": "command",
                "needs_clarification": False,
                "entities": [],
                "urgency": "normal",
            }

    async def _generate_clarification(
        self,
        message: str,
        context: Dict[str, Any],
    ) -> str:
        """Generate clarification question."""
        prompt = f"""The user said: "{message}"

Based on our conversation history, what clarification questions should I ask to better understand their request?

Generate a helpful, specific clarification question."""

        llm_request = LLMRequest(
            prompt=prompt,
            system_message="You are a DevOps AI agent that asks clarifying questions.",
            temperature=0.3,
            max_tokens=200,
        )

        try:
            response = await self.llm_router.complete(llm_request)
            return response.content.strip()

        except Exception as e:
            logger.error(f"Clarification generation failed: {e}")
            return "Could you please provide more details about your request?"

    async def _generate_response(
        self,
        message: str,
        context: Dict[str, Any],
        intent: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate contextual response."""
        history_summary = self._summarize_history(context["history"][-10:])

        system_message = """You are an intelligent DevOps AI agent that helps manage Linux servers via SSH.

You have access to:
- SSH commands execution
- System information collection
- Log analysis
- Service management
- File operations

Provide helpful, actionable responses. If you need to execute commands, clearly state what you plan to do."""

        prompt = f"""Conversation history:
{history_summary}

User message: "{message}"

Intent: {intent.get('intent_type', 'command')}

Provide a helpful response. If this is a command request, explain what you'll do before doing it."""

        llm_request = LLMRequest(
            prompt=prompt,
            system_message=system_message,
            temperature=0.4,
            max_tokens=1000,
        )

        try:
            response = await self.llm_router.complete(llm_request)

            # Extract suggested actions if any
            suggested_actions = self._extract_suggested_actions(response.content)

            return {
                "content": response.content,
                "suggested_actions": suggested_actions,
            }

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return {
                "content": "I'm having trouble processing your request. Could you try rephrasing it?",
                "suggested_actions": [],
            }

    def _summarize_history(self, messages: List[Dict[str, str]]) -> str:
        """Summarize conversation history."""
        summary = []
        for msg in messages:
            role = msg["role"].capitalize()
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            summary.append(f"{role}: {content}")

        return "\n".join(summary)

    def _extract_suggested_actions(self, response: str) -> List[str]:
        """Extract suggested actions from response."""
        # Look for action indicators
        actions = []

        # Simple pattern matching for now
        if "check" in response.lower():
            actions.append("check_system_status")
        if "restart" in response.lower():
            actions.append("restart_service")
        if "analyze" in response.lower():
            actions.append("analyze_logs")

        return actions

    async def _update_context(
        self,
        session_id: str,
        context: Dict[str, Any],
        intent: Dict[str, Any],
    ):
        """Update session context."""
        # Extract facts from conversation
        # (Simplified - in production, use NER or other techniques)

        # Update last topic
        if intent.get("entities"):
            context["last_topic"] = intent["entities"][0] if intent["entities"] else None

        # Save to database
        await self.session_repo.update_context(session_id, context)

    async def _load_session_context(self, session_id: str):
        """Load session context from database."""
        session = await self.session_repo.get_session(session_id, include_messages=True)

        if not session:
            # Create new session
            await self.start_session()
            return

        # Rebuild context from messages
        history = []
        for msg in session.messages:
            history.append({"role": msg.role, "content": msg.content})

        self.active_contexts[session_id] = {
            "history": history,
            "facts": session.context.get("facts", {}),
            "last_topic": session.context.get("last_topic"),
            "user_preferences": session.context.get("user_preferences", {}),
            "pending_questions": session.context.get("pending_questions", []),
        }

    async def summarize_session(self, session_id: str) -> str:
        """Generate a summary of the conversation session."""
        context = self.active_contexts.get(session_id)

        if not context:
            return "No active session found."

        prompt = f"""Summarize the following conversation:

{self._summarize_history(context['history'])}

Provide a concise summary highlighting:
1. Main topics discussed
2. Actions taken or planned
3. Any open questions or pending items"""

        llm_request = LLMRequest(
            prompt=prompt,
            system_message="You are a conversation summarizer.",
            temperature=0.3,
            max_tokens=500,
        )

        try:
            response = await self.llm_router.complete(llm_request)
            return response.content

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return "Could not generate summary."

    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get conversation history."""
        messages = await self.session_repo.get_messages(session_id, limit=limit)

        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
                "metadata": msg.metadata,
            }
            for msg in messages
        ]
