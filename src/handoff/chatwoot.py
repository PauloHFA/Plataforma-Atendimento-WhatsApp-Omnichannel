from __future__ import annotations

from typing import Any

import httpx


class ChatwootError(Exception):
    """Base error for Chatwoot integration."""


class ChatwootClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_token: str,
        account_id: int,
        inbox_id: int,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token.strip()
        self.account_id = account_id
        self.inbox_id = inbox_id
        self._client = client or httpx.Client(timeout=10.0)

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "api_access_token": self.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def find_or_create_contact(self, phone_number: str, name: str | None = None) -> int:
        clean_phone = phone_number.strip().lstrip("+")
        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/search"
        response = self._client.get(url, headers=self._headers, params={"q": clean_phone})
        if response.is_success:
            payload = response.json()
            payload_data = payload.get("payload", [])
            if payload_data and isinstance(payload_data, list):
                first = payload_data[0]
                if isinstance(first, dict) and "id" in first:
                    return int(first["id"])

        create_url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts"
        contact_body: dict[str, Any] = {
            "inbox_id": self.inbox_id,
            "phone_number": f"+{clean_phone}",
            "name": name or f"WhatsApp {clean_phone[-4:]}",
        }
        res = self._client.post(create_url, headers=self._headers, json=contact_body)
        if not res.is_success:
            raise ChatwootError(f"Failed to create Chatwoot contact: {res.status_code} {res.text}")
        contact_id = res.json().get("payload", {}).get("contact", {}).get("id")
        if not contact_id:
            raise ChatwootError(f"Chatwoot did not return contact id: {res.text}")
        return int(contact_id)

    def create_conversation(self, contact_id: int, summary: str | None = None) -> int:
        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations"
        body: dict[str, Any] = {
            "source_id": f"contact-{contact_id}",
            "inbox_id": self.inbox_id,
            "contact_id": contact_id,
            "status": "open",
        }
        if summary:
            body["additional_attributes"] = {"summary": summary}
        res = self._client.post(url, headers=self._headers, json=body)
        if not res.is_success:
            raise ChatwootError(
                f"Failed to create Chatwoot conversation: {res.status_code} {res.text}"
            )
        conv_id = res.json().get("id")
        if not conv_id:
            raise ChatwootError(f"Chatwoot did not return conversation id: {res.text}")
        return int(conv_id)

    def send_message(self, conversation_id: int, content: str) -> dict[str, Any]:
        url = (
            f"{self.base_url}/api/v1/accounts/{self.account_id}"
            f"/conversations/{conversation_id}/messages"
        )
        body = {
            "content": content,
            "message_type": "outgoing",
            "private": False,
        }
        res = self._client.post(url, headers=self._headers, json=body)
        if not res.is_success:
            raise ChatwootError(f"Failed to send Chatwoot message: {res.status_code} {res.text}")
        return res.json()  # type: ignore[no-any-return]

    def resolve_conversation(self, conversation_id: int) -> bool:
        url = (
            f"{self.base_url}/api/v1/accounts/{self.account_id}"
            f"/conversations/{conversation_id}/toggle_status"
        )
        res = self._client.post(url, headers=self._headers, json={"status": "resolved"})
        return res.is_success
