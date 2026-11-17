from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from src.db.models import Conversation, Message, Ticket
from src.db.session import get_db
from src.handoff.service import HandoffError, list_open_tickets, return_to_bot

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    reason: str
    summary: str | None = None
    status: str


class ReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)


class ReplyResponse(BaseModel):
    status: str
    conversation_id: UUID
    text: str


class ReturnResponse(BaseModel):
    status: str
    conversation_id: UUID


@router.get("/tickets", response_model=list[TicketOut])
def get_open_tickets(
    session: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Ticket]:
    try:
        return list_open_tickets(session, limit=limit, offset=offset)
    except HandoffError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{conversation_id}/reply", response_model=ReplyResponse)
def reply_to_conversation(
    conversation_id: UUID,
    body: ReplyRequest,
    session: Annotated[Session, Depends(get_db)],
) -> ReplyResponse:
    conv = session.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conv.status != "HUMAN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reply to conversation that is not assigned to a human agent",
        )

    msg = Message(
        conversation_id=conversation_id,
        direction="OUTBOUND",
        message_type="text",
        content={"text": body.text},
        delivery_status="SENT",
    )
    session.add(msg)
    session.commit()
    return ReplyResponse(status="sent", conversation_id=conversation_id, text=body.text)


@router.post("/{conversation_id}/return", response_model=ReturnResponse)
def return_conversation_to_bot(
    conversation_id: UUID,
    session: Annotated[Session, Depends(get_db)],
) -> ReturnResponse:
    try:
        return_to_bot(session, conversation_id)
        session.commit()
        return ReturnResponse(status="returned_to_bot", conversation_id=conversation_id)
    except HandoffError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
