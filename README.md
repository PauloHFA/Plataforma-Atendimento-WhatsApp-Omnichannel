# Plataforma de Atendimento WhatsApp Omnichannel

Plataforma escalável e orientada a eventos para automação de atendimento corporativo via **WhatsApp Cloud API** oficial da Meta, com filas assíncronas duráveis (Redis + Celery), gestão estrita de conformidade (janela de 24 horas e consentimento LGPD), FAQ com RAG seguro contra *prompt injection*, handoff humano integrado ao **Chatwoot** e exportação de métricas operacionais para o Prometheus.

---

## 1. Visão Geral e Arquitetura

A arquitetura separa categoricamente as regras de negócio das particularidades do protocolo de mensageria da Meta, garantindo processamento idempotente, proteção contra ataques de repetição e transições de estado transacionais.

```text
                                  ┌────────────────────────┐
                                  │   WhatsApp Cloud API   │
                                  │   (Meta Graph v21.0)   │
                                  └───────────┬────────────┘
                                              │ Webhook Event (POST)
                                              ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ FastAPI Application                                                                    │
│                                                                                        │
│   ┌───────────────────────────┐         ┌────────────────────────┐                     │
│   │   HMAC-SHA256 Signature   │ ──────▶ │  Redis Rate Limiter    │                     │
│   │   Verification (X-Hub)    │         │  & Deduplication       │                     │
│   └─────────────┬─────────────┘         └───────────┬────────────┘                     │
│                 │                                   │                                  │
│                 ▼                                   ▼                                  │
│   ┌──────────────────────────────────────────────────────────────┐                     │
│   │      Persistência do WebhookEvent no Banco Relacional        │                     │
│   └─────────────────────────────┬────────────────────────────────┘                     │
└─────────────────────────────────┼──────────────────────────────────────────────────────┘
                                  │ Enfileiramento Durável (Task)
                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Celery Worker Engine                                                                   │
│                                                                                        │
│   ┌───────────────────────────┐         ┌────────────────────────┐                     │
│   │ NLU & Intent Classifier   │         │ RAG Assistant          │                     │
│   │ (Saudação, Pedido, FAQ,   │ ──────▶ │ (Citação de Fontes,    │                     │
│   │  Agendamento, Opt-out)    │         │  Defesa Prompt Inject) │                     │
│   └─────────────┬─────────────┘         └────────────────────────┘                     │
│                 │                                                                      │
│                 ▼                                                                      │
│   ┌───────────────────────────┐         ┌────────────────────────┐                     │
│   │ Policy Guard (Janela 24h) │ ──────▶ │ Transições de Handoff  │                     │
│   │ & Consentimento LGPD      │         │ (Silenciamento do Bot) │                     │
│   └─────────────┬─────────────┘         └───────────┬────────────┘                     │
└─────────────────┼───────────────────────────────────┼──────────────────────────────────┘
                  │                                   │
                  ▼                                   ▼
   ┌─────────────────────────────┐     ┌─────────────────────────────┐
   │ MetaCloudAdapter /          │     │ Chatwoot API Integration    │
   │ SimulatorAdapter (Outbound) │     │ (Painel Atendente Humano)   │
   └─────────────────────────────┘     └─────────────────────────────┘
```

---

## 2. Componentes Principais

### 2.1 Ingestão & Webhooks (`src/api/webhook.py`)
- **GET `/webhook`**: Verificação do handshake oficial da Meta com `hub.verify_token` e retorno do `hub.challenge`.
- **POST `/webhook`**: Validação criptográfica rigorosa via cabeçalho `X-Hub-Signature-256` utilizando o `META_APP_SECRET`.
- **Deduplicação e Rate Limiting (`src/api/rate_limit.py`)**: Limitador deslizante no Redis e descarte idempotente de `wamid` duplicados.

### 2.2 Fila Assíncrona & Celery Tasks (`src/tasks.py`)
- Separação entre o recebimento rápido do webhook (ACK em milissegundos) e o processamento de regras de negócio no Celery com backoff exponencial.

### 2.3 Políticas de Mensageria e Consentimento (`src/flows/`, `src/consent/`)
- **Janela de 24h (`src/flows/message_policy.py`)**: Bloqueio ativo de mensagens livres fora do período de 24 horas da última interação do cliente.
- **Consentimento & Opt-out (`src/consent/service.py`)**: Reconhecimento automático e prioritário de palavras-chave regulatórias (*PARAR*, *SAIR*, *CANCELAR*, *DESCADAS TRAR*).
- **Contabilidade de Mensagens (`src/usage/service.py`)**: Agregação de mensagens por categoria Meta (`SERVICE`, `UTILITY`, `AUTHENTICATION`, `MARKETING`).

### 2.4 Atendimento Humano & Chatwoot (`src/handoff/`, `src/api/conversations.py`)
- **Máquina de Estados de Posse**: Quando o cliente solicita um humano ou ocorrem falhas consecutivas, a conversa transita para `status="HUMAN"`. O bot é silenciado instantaneamente até a devolução formal.
- **Chatwoot Client (`src/handoff/chatwoot.py`)**: Criação de contatos, abertura de tickets/conversas, envio de mensagens e sincronização de encerramento via API REST do Chatwoot.
- **Rotas de Atendimento Interno**:
  - `GET /api/v1/conversations/tickets`: Listagem paginada de tickets abertos.
  - `POST /api/v1/conversations/{id}/reply`: Envio de resposta por atendente humano.
  - `POST /api/v1/conversations/{id}/return`: Devolução da posse da conversa para o bot.

### 2.5 NLU & RAG com Guardrails de Segurança (`src/nlu/`, `src/knowledge/`)
- **Classificador de Intenções (`src/nlu/intent_classifier.py`)**: Identificação determinística de intenções e extração de códigos de pedido com cálculo de score de confiança.
- **RAG Seguro (`src/knowledge/rag.py`)**: Base de conhecimento auditável com citação explícita do título do artigo e blindagem contra *prompt injection* (`ADVERSARIAL_MARKERS`), além de recusa elegante de temas fora do escopo.

### 2.6 Métricas Operacionais & Privacidade (`src/api/metrics.py`, `src/privacy/`)
- **Métricas Prometheus (`GET /metrics`)**: Contadores e gauges de conversas ativas, tickets de suporte e mensagens recebidas/enviadas.
- **Mascaramento PII (`src/privacy/masking.py`)**: Higienização de telefones e CPFs em logs para conformidade com a LGPD.
- **Pesquisa de Satisfação (CSAT) (`src/flows/csat.py`)**: Validação de notas de 1 a 5 no pós-atendimento.

---

## 3. Guia de Execução

### Opção A: Executar com Docker Compose (Recomendado)

1. Crie o arquivo `.env` a partir do template:
   ```bash
   cp .env.example .env
   ```
2. Inicialize todos os serviços (PostgreSQL, Redis, API FastAPI e Celery Worker):
   ```bash
   docker compose up --build -d
   ```
3. Verifique o status dos contêineres e a rota de saúde:
   ```bash
   docker compose ps
   curl http://localhost:8000/health
   ```
   A documentação interativa OpenAPI está disponível em `http://localhost:8000/docs`.

### Opção B: Executar Localmente sem Docker

1. Instale as dependências com Python 3.12:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # No Windows: .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```
2. Execute as migrações do banco com Alembic:
   ```bash
   alembic upgrade head
   ```
3. Suba o servidor web FastAPI:
   ```bash
   uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
   ```
4. Em outro terminal, inicie o worker do Celery (com Redis rodando na porta 6379):
   ```bash
   celery -A src.celery_app:celery_app worker --loglevel=INFO --pool=solo
   ```

---

## 4. Esteira de Testes e Qualidade

O projeto conta com suíte de testes unitários, contratuais, de integração e cenários de diálogo ponta a ponta:

```bash
# Executar todos os testes automatizados
pytest -v

# Checagem rigorosa de linter e formatação
ruff check .

# Checagem estrita de tipos estáticos
mypy src
```

Status atual: **167 testes passando com 100% de conformidade**.

Para detalhes sobre o roadmap de engenharia, consulte o arquivo [PENDENCIAS.md](PENDENCIAS.md).
