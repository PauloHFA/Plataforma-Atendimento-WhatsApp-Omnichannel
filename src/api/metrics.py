from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import Conversation, Message, Ticket
from src.db.session import get_db

router = APIRouter(tags=["operational"])


@router.get("/metrics")
def get_metrics(session: Annotated[Session, Depends(get_db)]) -> Response:
    conv_counts = dict(
        session.execute(
            select(Conversation.status, func.count(Conversation.id)).group_by(Conversation.status)
        ).all()
    )
    ticket_counts = dict(
        session.execute(
            select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
        ).all()
    )
    msg_counts = dict(
        session.execute(
            select(Message.direction, func.count(Message.id)).group_by(Message.direction)
        ).all()
    )

    lines = [
        "# HELP whatsapp_service_up Status do servico de atendimento",
        "# TYPE whatsapp_service_up gauge",
        "whatsapp_service_up 1",
        "# HELP whatsapp_conversations_total Total de conversas agrupadas por status",
        "# TYPE whatsapp_conversations_total gauge",
        f'whatsapp_conversations_total{{status="BOT"}} {conv_counts.get("BOT", 0)}',
        f'whatsapp_conversations_total{{status="HUMAN"}} {conv_counts.get("HUMAN", 0)}',
        f'whatsapp_conversations_total{{status="CLOSED"}} {conv_counts.get("CLOSED", 0)}',
        "# HELP whatsapp_tickets_total Total de tickets de handoff por status",
        "# TYPE whatsapp_tickets_total gauge",
        f'whatsapp_tickets_total{{status="OPEN"}} {ticket_counts.get("OPEN", 0)}',
        f'whatsapp_tickets_total{{status="CLOSED"}} {ticket_counts.get("CLOSED", 0)}',
        "# HELP whatsapp_messages_total Total de mensagens por direcao",
        "# TYPE whatsapp_messages_total counter",
        f'whatsapp_messages_total{{direction="INBOUND"}} {msg_counts.get("INBOUND", 0)}',
        f'whatsapp_messages_total{{direction="OUTBOUND"}} {msg_counts.get("OUTBOUND", 0)}',
    ]

    content = "\n".join(lines) + "\n"
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")
