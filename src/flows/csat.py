from __future__ import annotations

import re

_CSAT_PATTERN = re.compile(r"\b([1-5])\b")


class CSATService:
    """Serviço de pesquisa de satisfação pós-atendimento (CSAT)."""

    SURVEY_PROMPT = (
        "Seu atendimento foi concluído! Como você avalia a sua experiência hoje?\n"
        "Envie uma nota de 1 a 5 (onde 1 é péssimo e 5 é excelente)."
    )

    THANK_YOU_MESSAGE = (
        "Agradecemos pelo seu feedback! Sua avaliação é essencial para melhorarmos continuamente."
    )

    RETRY_MESSAGE = (
        "Opção inválida. Por favor, responda com um número de 1 a 5 para registrar sua avaliação."
    )

    def extract_score(self, text: str) -> int | None:
        match = _CSAT_PATTERN.search(text.strip())
        if match:
            return int(match.group(1))
        return None
