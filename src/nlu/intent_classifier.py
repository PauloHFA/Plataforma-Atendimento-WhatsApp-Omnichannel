from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

IntentName = Literal[
    "greeting",
    "opt_out",
    "human_agent",
    "order_status",
    "appointment",
    "faq",
    "out_of_scope",
    "unrecognized",
]


@dataclass(frozen=True)
class IntentResult:
    intent: IntentName
    confidence: float
    entities: dict[str, str] = field(default_factory=dict)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    cleaned = re.sub(r"[^\w\s]", " ", without_marks)
    return " ".join(cleaned.lower().split())


_GREETINGS = frozenset({"oi", "ola", "bom dia", "boa tarde", "boa noite", "e ai", "opa"})
_OPT_OUT_WORDS = frozenset({"parar", "sair", "cancelar", "descadastrar", "stop", "unsubscribe"})
_HUMAN_WORDS = frozenset(
    {
        "atendente",
        "humano",
        "pessoa",
        "suporte",
        "falar com atendente",
        "falar com humano",
        "atendimento humano",
    }
)
_ORDER_PATTERNS = [
    re.compile(r"\bpedido\b"),
    re.compile(r"\brastrear\b"),
    re.compile(r"\brastreio\b"),
    re.compile(r"\bstatus do pedido\b"),
    re.compile(r"\bonde esta meu pedido\b"),
]
_APPOINTMENT_PATTERNS = [
    re.compile(r"\bagendar\b"),
    re.compile(r"\bagendamento\b"),
    re.compile(r"\bconsulta\b"),
    re.compile(r"\bmarcar horario\b"),
    re.compile(r"\bremarcar\b"),
    re.compile(r"\bhorarios disponiveis\b"),
]
_ORDER_CODE_PATTERN = re.compile(r"#([A-Za-z0-9]+)|\b(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{4,12}\b")


class IntentClassifier:
    """Classificador de intenções híbrido para mensagens do WhatsApp."""

    def __init__(self, confidence_threshold: float = 0.6) -> None:
        self.confidence_threshold = confidence_threshold

    def classify(self, text: str) -> IntentResult:
        normalized = _normalize(text)
        if not normalized:
            return IntentResult(intent="unrecognized", confidence=0.0)

        # 1. Opt-out (prioridade regulatória máxima)
        tokens = set(normalized.split())
        if tokens & _OPT_OUT_WORDS or normalized in _OPT_OUT_WORDS:
            return IntentResult(intent="opt_out", confidence=1.0)

        # 2. Solicitação de Atendente Humano
        for phrase in _HUMAN_WORDS:
            if phrase in normalized:
                return IntentResult(intent="human_agent", confidence=0.98)

        # 3. Pedidos & Rastreamento
        for pattern in _ORDER_PATTERNS:
            if pattern.search(normalized):
                entities: dict[str, str] = {}
                code_match = _ORDER_CODE_PATTERN.search(text)
                if code_match:
                    entities["order_number"] = code_match.group(0).lstrip("#")
                return IntentResult(intent="order_status", confidence=0.95, entities=entities)

        # 4. Agendamentos e Consultas
        for pattern in _APPOINTMENT_PATTERNS:
            if pattern.search(normalized):
                return IntentResult(intent="appointment", confidence=0.95)

        # 5. Saudações
        if normalized in _GREETINGS:
            return IntentResult(intent="greeting", confidence=0.99)

        # 6. Perguntas frequentes (indícios de FAQ)
        faq_cues = [
            "como funciona",
            "qual valor",
            "quanto custa",
            "preco",
            "horario",
            "onde fica",
            "endereco",
        ]
        if any(cue in normalized for cue in faq_cues) or normalized.endswith("?"):
            return IntentResult(intent="faq", confidence=0.85)

        return IntentResult(intent="unrecognized", confidence=0.4)
