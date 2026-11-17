from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from src.knowledge.faq import FAQService

ADVERSARIAL_MARKERS = frozenset(
    {
        "ignore previous instructions",
        "ignore as instrucoes",
        "esqueça as instrucoes",
        "esqueca as instrucoes",
        "voce agora e",
        "voce agora e um",
        "system prompt",
        "jailbreak",
        "developer mode",
        "modo desenvolvedor",
        "revele suas instrucoes",
        "quais sao suas regras",
        "instrucoes do sistema",
    }
)

OUT_OF_SCOPE_MARKERS = frozenset(
    {
        "receita de bolo",
        "politica",
        "eleicoes",
        "futebol",
        "previsao do tempo",
        "quem ganhou a copa",
        "criptomoeda",
        "bitcoin",
    }
)


@dataclass(frozen=True)
class RAGResponse:
    answer: str
    source_title: str | None
    is_hostile: bool
    confidence: float
    abstained: bool
    disclaimer: str = "Informação fundamentada na base de conhecimento oficial."


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return without_marks.lower().strip()


class RAGAssistant:
    """Assistente RAG com guardrails contra prompt injection e respostas infundadas."""

    def __init__(
        self,
        articles: Sequence[Any],
        faq_service: FAQService | None = None,
    ) -> None:
        self.articles = articles
        self.faq_service = faq_service or FAQService()

    def ask(self, question: str) -> RAGResponse:
        normalized = _normalize(question)

        # 1. Guardrail contra Prompt Injection
        for marker in ADVERSARIAL_MARKERS:
            if marker in normalized:
                return RAGResponse(
                    answer=(
                        "Não posso processar essa solicitação "
                        "pois viola nossas diretrizes de segurança."
                    ),
                    source_title=None,
                    is_hostile=True,
                    confidence=0.0,
                    abstained=True,
                )

        # 2. Guardrail contra perguntas fora de escopo do negócio
        for marker in OUT_OF_SCOPE_MARKERS:
            if marker in normalized:
                return RAGResponse(
                    answer=(
                        "Desculpe, sou um assistente especializado "
                        "e não posso responder sobre este assunto."
                    ),
                    source_title=None,
                    is_hostile=False,
                    confidence=0.0,
                    abstained=True,
                )

        # 3. Busca fundamentada na base de conhecimento
        match = self.faq_service.answer(question, self.articles)
        if match is None:
            return RAGResponse(
                answer=(
                    "Desculpe, não encontrei essa informação em nossa base oficial. "
                    "Gostaria de falar com um atendente?"
                ),
                source_title=None,
                is_hostile=False,
                confidence=0.3,
                abstained=True,
            )

        grounded_answer = f"{match.content}\n\n(Fonte: {match.source_title})"
        return RAGResponse(
            answer=grounded_answer,
            source_title=match.source_title,
            is_hostile=False,
            confidence=0.95,
            abstained=False,
        )
