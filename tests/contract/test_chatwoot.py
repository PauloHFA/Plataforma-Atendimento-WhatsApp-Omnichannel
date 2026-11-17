from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.db.models import Base, Contact, Conversation, Ticket
from src.db.session import get_db
from src.handoff.chatwoot import ChatwootClient
from src.main import app


def test_chatwoot_find_or_create_existing(respx_mock: Any) -> None:
    respx_mock.get("https://app.chatwoot.com/api/v1/accounts/1/contacts/search").respond(
        status_code=200, json={"payload": [{"id": 42, "phone_number": "+5511999999999"}]}
    )
    client = ChatwootClient(
        base_url="https://app.chatwoot.com",
        api_token="dummy_token",
        account_id=1,
        inbox_id=10,
    )
    contact_id = client.find_or_create_contact("5511999999999")
    assert contact_id == 42


def test_chatwoot_create_new_contact(respx_mock: Any) -> None:
    respx_mock.get("https://app.chatwoot.com/api/v1/accounts/1/contacts/search").respond(
        status_code=200, json={"payload": []}
    )
    respx_mock.post("https://app.chatwoot.com/api/v1/accounts/1/contacts").respond(
        status_code=200, json={"payload": {"contact": {"id": 99}}}
    )
    client = ChatwootClient(
        base_url="https://app.chatwoot.com",
        api_token="dummy_token",
        account_id=1,
        inbox_id=10,
    )
    contact_id = client.find_or_create_contact("+5511988888888")
    assert contact_id == 99


def test_chatwoot_create_conversation_and_send_message(respx_mock: Any) -> None:
    respx_mock.post("https://app.chatwoot.com/api/v1/accounts/1/conversations").respond(
        status_code=200, json={"id": 123}
    )
    respx_mock.post(
        "https://app.chatwoot.com/api/v1/accounts/1/conversations/123/messages"
    ).respond(status_code=200, json={"id": 555, "content": "Olá, atendente aqui."})
    respx_mock.post(
        "https://app.chatwoot.com/api/v1/accounts/1/conversations/123/toggle_status"
    ).respond(status_code=200, json={"status": "resolved"})

    client = ChatwootClient(
        base_url="https://app.chatwoot.com",
        api_token="dummy_token",
        account_id=1,
        inbox_id=10,
    )
    conv_id = client.create_conversation(contact_id=99, summary="Cliente com dúvida")
    assert conv_id == 123

    msg = client.send_message(123, "Olá, atendente aqui.")
    assert msg["id"] == 555

    resolved = client.resolve_conversation(123)
    assert resolved is True


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


def test_conversations_api_tickets_and_replies(session: Session) -> None:
    contact = Contact(wa_id="5511977777777")
    session.add(contact)
    session.flush()

    conv = Conversation(contact_id=contact.id, status="HUMAN", state="handoff")
    session.add(conv)
    session.flush()

    ticket = Ticket(conversation_id=conv.id, reason="Dúvida complexa", status="OPEN")
    session.add(ticket)
    session.commit()

    test_client = TestClient(app)

    # 1. List open tickets
    resp = test_client.get("/api/v1/conversations/tickets")
    assert resp.status_code == 200
    data = resp.json()
    assert any(t["id"] == str(ticket.id) for t in data)

    # 2. Reply to human conversation
    reply_resp = test_client.post(
        f"/api/v1/conversations/{conv.id}/reply",
        json={"text": "Olá, sou o suporte humano."},
    )
    assert reply_resp.status_code == 200
    assert reply_resp.json()["text"] == "Olá, sou o suporte humano."

    # 3. Return to bot
    return_resp = test_client.post(f"/api/v1/conversations/{conv.id}/return")
    assert return_resp.status_code == 200
    assert return_resp.json()["status"] == "returned_to_bot"

    # Verify conversation is now BOT
    session.refresh(conv)
    assert conv.status == "BOT"
    assert conv.state == "menu"
