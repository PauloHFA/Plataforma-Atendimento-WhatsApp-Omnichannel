from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.db.models import Base, Contact, Conversation, Message, Ticket
from src.db.session import get_db
from src.main import app


@pytest.fixture
def session() -> Iterator[Session]:
    mem_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(mem_engine)

    def override_get_db() -> Iterator[Session]:
        with Session(mem_engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with Session(mem_engine) as db:
        yield db
    app.dependency_overrides.pop(get_db, None)
    mem_engine.dispose()


def test_metrics_endpoint(session: Session) -> None:
    contact = Contact(wa_id="5511988887777")
    session.add(contact)
    session.flush()

    conv = Conversation(contact_id=contact.id, status="BOT", state="menu")
    session.add(conv)
    session.flush()

    ticket = Ticket(conversation_id=conv.id, reason="Suporte", status="OPEN")
    session.add(ticket)

    msg = Message(
        conversation_id=conv.id,
        direction="INBOUND",
        message_type="text",
        content={"text": "Oi"},
        delivery_status="RECEIVED",
    )
    session.add(msg)
    session.commit()

    test_client = TestClient(app)
    resp = test_client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    text = resp.text
    assert 'whatsapp_conversations_total{status="BOT"} 1' in text
    assert 'whatsapp_tickets_total{status="OPEN"} 1' in text
    assert 'whatsapp_messages_total{direction="INBOUND"} 1' in text
    assert "whatsapp_service_up 1" in text
