from __future__ import annotations

import re

_PHONE_PATTERN = re.compile(r"(\+?\d{2}\s?\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4})")
_CPF_PATTERN = re.compile(r"(\b\d{3}\.?\d{3}\.?\d{3}[-\.]?\d{2}\b)")


def mask_phone(phone: str) -> str:
    cleaned = "".join(ch for ch in phone if ch.isdigit())
    if len(cleaned) <= 4:
        return "****"
    return f"{cleaned[:2]}****{cleaned[-4:]}"


def mask_cpf(cpf: str) -> str:
    digits = "".join(ch for ch in cpf if ch.isdigit())
    if len(digits) != 11:
        return "***.***.***-**"
    return f"***.***.{digits[6:9]}-**"


def mask_text(text: str) -> str:
    masked = _CPF_PATTERN.sub("***.***.***-**", text)

    def _replace_phone(m: re.Match[str]) -> str:
        return mask_phone(m.group(0))

    return _PHONE_PATTERN.sub(_replace_phone, masked)
