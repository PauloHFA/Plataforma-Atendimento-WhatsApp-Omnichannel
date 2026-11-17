from typing import Any

import pytest

from src.channel.meta_cloud import MetaCloudAdapter, MetaCloudError


@pytest.fixture
def adapter() -> MetaCloudAdapter:
    return MetaCloudAdapter(
        phone_number_id="123456789",
        access_token="fake_access_token",
        graph_api_version="v21.0",
    )


def test_meta_cloud_send_text(adapter: MetaCloudAdapter, respx_mock: Any) -> None:
    respx_mock.post("https://graph.facebook.com/v21.0/123456789/messages").respond(
        status_code=200,
        json={"messaging_product": "whatsapp", "messages": [{"id": "wamid.HBgL..."}]},
    )
    msg = adapter.send_text("5511999998888", "Olá, como podemos ajudar?")
    assert msg.recipient == "5511999998888"
    assert msg.message_type == "text"
    assert "messages" in msg.payload


def test_meta_cloud_send_interactive(adapter: MetaCloudAdapter, respx_mock: Any) -> None:
    respx_mock.post("https://graph.facebook.com/v21.0/123456789/messages").respond(
        status_code=200,
        json={"messaging_product": "whatsapp", "messages": [{"id": "wamid.HBgL2..."}]},
    )
    interactive_payload = {
        "type": "button",
        "body": {"text": "Escolha uma opção:"},
        "action": {"buttons": [{"type": "reply", "reply": {"id": "opt1", "title": "FAQ"}}]},
    }
    msg = adapter.send_interactive("5511999998888", interactive_payload)
    assert msg.message_type == "interactive"
    assert msg.recipient == "5511999998888"


def test_meta_cloud_send_template(adapter: MetaCloudAdapter, respx_mock: Any) -> None:
    respx_mock.post("https://graph.facebook.com/v21.0/123456789/messages").respond(
        status_code=200,
        json={"messaging_product": "whatsapp", "messages": [{"id": "wamid.HBgL3..."}]},
    )
    msg = adapter.send_template("5511999998888", name="order_update", language="pt_BR")
    assert msg.message_type == "template"
    assert msg.recipient == "5511999998888"


def test_meta_cloud_mark_read(adapter: MetaCloudAdapter, respx_mock: Any) -> None:
    route = respx_mock.post("https://graph.facebook.com/v21.0/123456789/messages").respond(
        status_code=200,
        json={"success": True},
    )
    adapter.mark_read("wamid.HBgL_target")
    assert route.called


def test_meta_cloud_error_handling(adapter: MetaCloudAdapter, respx_mock: Any) -> None:
    respx_mock.post("https://graph.facebook.com/v21.0/123456789/messages").respond(
        status_code=401,
        text="Invalid OAuth access token.",
    )
    with pytest.raises(MetaCloudError) as exc_info:
        adapter.send_text("5511999998888", "Mensagem que vai falhar")
    assert "401" in str(exc_info.value)
