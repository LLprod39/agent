"""Conversation router for chat functionality."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ..models import ConversationRequest, ConversationResponse
from ..dependencies import get_orchestrator, get_current_user, get_request_context
from ...orchestrator import Orchestrator, OrchestrationRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ConversationResponse)
async def chat(
    request: ConversationRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user_id: str = Depends(get_current_user),
    context: Dict[str, Any] = Depends(get_request_context),
):
    """Chat with the DevOps agent."""
    try:
        # Prepare orchestration request
        orchestration_request = OrchestrationRequest(
            task=request.message,
            context=request.context or {},
            environment_profile=request.environment_profile,
            session_id=request.session_id,
            user_id=user_id,
            auto_approve=False,
            metadata=context,
        )

        # Process the request
        response = await orchestrator.process_request(orchestration_request)

        # Create conversation response
        return ConversationResponse(
            session_id=response.task_id,
            message=response.message,
            task_id=response.task_id,
            requires_approval=response.requires_approval,
            risk_level=response.risk_level,
            metadata=response.metadata,
        )

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}",
        )


@router.post("/chat/stream")
async def chat_stream(
    request: ConversationRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user_id: str = Depends(get_current_user),
    context: Dict[str, Any] = Depends(get_request_context),
):
    """Stream chat response from the DevOps agent."""
    try:
        # Prepare orchestration request
        orchestration_request = OrchestrationRequest(
            task=request.message,
            context=request.context or {},
            environment_profile=request.environment_profile,
            session_id=request.session_id,
            user_id=user_id,
            auto_approve=False,
            metadata=context,
        )

        # Process the request (this would need to be modified to support streaming)
        response = await orchestrator.process_request(orchestration_request)

        # For now, return a simple stream
        # TODO: Implement actual streaming from LLM
        async def generate_stream():
            yield f"data: {response.message}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache"},
        )

    except Exception as e:
        logger.error(f"Stream chat error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stream chat failed: {str(e)}",
        )


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str, orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Get session information."""
    try:
        # Get task status from orchestrator
        task_status = await orchestrator.get_task_status(session_id)

        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        return {
            "session_id": session_id,
            "status": task_status["status"],
            "current_step": task_status.get("current_step", "unknown"),
            "results": task_status.get("results", []),
            "error": task_status.get("error"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}",
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str, orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Delete a session."""
    try:
        # Remove from orchestrator's active tasks
        if session_id in orchestrator.active_tasks:
            del orchestrator.active_tasks[session_id]
            return {"message": f"Session {session_id} deleted"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )
