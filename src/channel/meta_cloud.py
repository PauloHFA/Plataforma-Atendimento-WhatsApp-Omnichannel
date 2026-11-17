from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from src.channel.adapter import (
    ChannelAdapter,
    InboundMessage,
    OutboundMessage,
    _items,
    _mapping,
    _parse_message,
    _required_string,
)


class MetaCloudError(Exception):
    """Erro em chamadas à Cloud API do WhatsApp."""


class MetaCloudAdapter(ChannelAdapter):
    """Adaptador de canal oficial para a WhatsApp Cloud API da Meta."""

    def __init__(
        self,
        *,
        phone_number_id: str,
        access_token: str,
        graph_api_version: str = "v21.0",
        client: httpx.Client | None = None,
    ) -> None:
        self.phone_number_id = phone_number_id.strip()
        self.access_token = access_token.strip()
        self.graph_api_version = graph_api_version.strip()
        self.base_url = (
            f"https://graph.facebook.com/{self.graph_api_version}/{self.phone_number_id}/messages"
        )
        self._client = client or httpx.Client(timeout=10.0)

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def parse_inbound(self, payload: Mapping[str, object]) -> list[InboundMessage]:
        entries = _items(payload.get("entry", []), "entry")
        messages: list[InboundMessage] = []
        for entry_index, entry_value in enumerate(entries):
            entry = _mapping(entry_value, f"entry[{entry_index}]")
            changes = _items(entry.get("changes", []), f"entry[{entry_index}].changes")
            for change_index, change_value in enumerate(changes):
                change = _mapping(change_value, f"changes[{change_index}]")
                if change.get("field") != "messages":
                    continue
                value = _mapping(change.get("value"), "change.value")
                raw_messages = value.get("messages", [])
                if not isinstance(raw_messages, list):
                    raise ValueError("change.value.messages must be an array")
                for message_index, message_value in enumerate(raw_messages):
                    message = _mapping(message_value, f"messages[{message_index}]")
                    messages.append(_parse_message(message))
        return messages

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(self.base_url, headers=self._headers, json=payload)
        if not response.is_success:
            raise MetaCloudError(
                f"Meta API error {response.status_code}: {response.text}"
            )
        return response.json()  # type: ignore[no-any-return]

    def send_text(self, recipient: str, text: str) -> OutboundMessage:
        recipient = _required_string(recipient, "recipient")
        text = _required_string(text, "text")
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        res = self._post(body)
        return OutboundMessage(recipient=recipient, message_type="text", payload=res)

    def send_interactive(
        self, recipient: str, interactive: Mapping[str, object]
    ) -> OutboundMessage:
        recipient = _required_string(recipient, "recipient")
        payload = dict(_mapping(interactive, "interactive"))
        body = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "interactive",
            "interactive": payload,
        }
        res = self._post(body)
        return OutboundMessage(recipient=recipient, message_type="interactive", payload=res)

    def send_template(
        self,
        recipient: str,
        name: str,
        language: str = "pt_BR",
        components: list[Mapping[str, object]] | None = None,
    ) -> OutboundMessage:
        recipient = _required_string(recipient, "recipient")
        name = _required_string(name, "name")
        body: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "template",
            "template": {
                "name": name,
                "language": {"code": language},
            },
        }
        if components:
            body["template"]["components"] = [dict(c) for c in components]
        res = self._post(body)
        return OutboundMessage(recipient=recipient, message_type="template", payload=res)

    def mark_read(self, message_id: str) -> None:
        message_id = _required_string(message_id, "message_id")
        body = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        self._post(body)
