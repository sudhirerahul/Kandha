# agent.py — Repatriation Agent router: session management + SSE streaming turns
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models.agent import AgentSession, AgentTurn
from services.gmi import GMIClient, get_gmi_client
from services.hydra import MemoryClient, get_memory_client
from services.photon_guard import PhotonGuardClient, get_photon_guard

log = structlog.get_logger()
router = APIRouter(prefix="/agent", tags=["agent"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    """Request body for creating a new agent session."""
    analysis_session_id: str | None = None


class CreateSessionResponse(BaseModel):
    """Response after successfully creating a session."""
    session_id: str
    hydra_session_id: str


class SendMessageRequest(BaseModel):
    """A single user message to the agent."""
    content: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    memory: MemoryClient = Depends(get_memory_client),
    user_id: str = Depends(get_current_user),
) -> CreateSessionResponse:
    """Create a new repatriation agent session with persistent memory."""
    session_id = str(uuid.uuid4())

    # Initialise memory (HydraDB or Redis)
    hydra_session_id = await memory.create_session(
        session_id,
        metadata={"user_id": user_id, "analysis_session_id": body.analysis_session_id},
    )

    # Persist in DB
    db_session = AgentSession(
        id=uuid.UUID(session_id),
        user_id=user_id,
        hydra_session_id=hydra_session_id,
        status="active",
    )
    db.add(db_session)
    await db.flush()

    log.info("agent.session.created", session_id=session_id, user_id=user_id)
    return CreateSessionResponse(session_id=session_id, hydra_session_id=hydra_session_id)


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    memory: MemoryClient = Depends(get_memory_client),
    gmi: GMIClient = Depends(get_gmi_client),
    guard: PhotonGuardClient = Depends(get_photon_guard),
    user_id: str = Depends(get_current_user),
) -> StreamingResponse:
    """Send a user message and stream the agent's response via SSE.

    SSE event format:
      data: {"type": "chunk", "content": "..."} — incremental text
      data: {"type": "done", "session_id": "..."}  — stream complete
      data: {"type": "error", "message": "..."}    — on failure
    """
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="Message content cannot be empty.")

    async def event_stream() -> AsyncGenerator[str, None]:
        full_response_parts: list[str] = []

        try:
            # 0. Screen user input for prompt injection
            screening = await guard.screen_input(body.content)
            if not screening["safe"]:
                log.warning("agent.input.blocked", session_id=session_id, reason=screening["reason"])
                yield f"data: {json.dumps({'type': 'error', 'message': screening['reason']})}\n\n"
                return

            # 1. Load conversation history from memory
            history = await memory.get_history(session_id)

            # 2. Append user turn to memory
            await memory.append_turn(session_id, "user", body.content)

            # 3. Build messages list for GMI
            messages = [*history, {"role": "user", "content": body.content}]

            # 4. Stream GMI response
            async for chunk in gmi.stream_chat(messages):
                full_response_parts.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            full_response = "".join(full_response_parts)

            # 5. Screen output — filter PII and score quality
            output_check = await guard.screen_output(full_response)
            full_response = output_check["filtered"]

            score = await guard.score_quality(body.content, full_response)
            log.info("agent.quality_score", session_id=session_id, score=score)

            # 6. Persist assistant response to memory
            await memory.append_turn(session_id, "assistant", full_response)

            # 7. Persist both turns to DB (best-effort — don't fail the stream)
            try:
                user_turn = AgentTurn(
                    session_id=uuid.UUID(session_id),
                    role="user",
                    content=body.content,
                )
                assistant_turn = AgentTurn(
                    session_id=uuid.UUID(session_id),
                    role="assistant",
                    content=full_response,
                )
                db.add_all([user_turn, assistant_turn])
                await db.flush()
            except Exception as db_exc:
                log.warning("agent.db.persist_failed", error=str(db_exc))

            log.info(
                "agent.turn.complete",
                session_id=session_id,
                response_chars=len(full_response),
            )
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

        except Exception as exc:
            log.error("agent.stream.error", error=str(exc), session_id=session_id)
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/sessions/{session_id}/history")
async def get_history(
    session_id: str,
    memory: MemoryClient = Depends(get_memory_client),
) -> dict:
    """Return full conversation history for a session."""
    history = await memory.get_history(session_id)
    return {"session_id": session_id, "turns": history, "count": len(history)}


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    memory: MemoryClient = Depends(get_memory_client),
) -> None:
    """Clear memory and mark session as closed."""
    await memory.clear_session(session_id)
    log.info("agent.session.deleted", session_id=session_id)
