# Pendências — Automação de Atendimento via WhatsApp (AtendimentoZap)

Este documento centraliza o status de engenharia do projeto, dividindo o que foi concluído, as melhorias opcionais e o que depende de infraestrutura externa e credenciais reais.

---

## 1. Módulos Concluídos e Testados (100% Offline / Cobertos)

### Núcleo de Mensageria e Webhooks
- [x] **Webhook Meta Oficial:** Endpoints `GET /webhook` (verificação de desafio com token) e `POST /webhook` (verificação de assinatura criptográfica HMAC-SHA256 via header `X-Hub-Signature-256`).
- [x] **Rate Limiting & Anti-Replay:** Proteção com Redis contra rajadas e ataques de repetição utilizando chave primária e deduplicação estrita de `wamid`.
- [x] **Processamento Assíncrono Idempotente:** Enfileiramento durável para worker Celery com persistência antes do ACK HTTP e backoff exponencial em falhas.

### Conformidade, Janela e Consentimento
- [x] **Regra de 24 Horas da Meta:** Controle temporal de sessão de atendimento livre (`src/flows/message_policy.py`); bloqueio estrito de mensagens ativas fora da janela sem template aprovado.
- [x] **Gestão de Consentimento (LGPD / Meta Policy):** Registro transacional de opt-in e revogação imediata via palavras-chave (*PARAR*, *SAIR*, *CANCELAR*, *DESCADAS TRAR*).
- [x] **Controle de Custos e Categorias:** Contadores mensais de mensagens agrupados por categoria oficial (SERVICE, UTILITY, MARKETING, AUTHENTICATION).

### Atendimento Humano & Handoff
- [x] **Máquina de Estados de Transição:** Controle explícito de propriedade da conversa (`BOT`, `HUMAN`, `CLOSED`). O bot silencia automaticamente durante a atuação do operador humano.
- [x] **API Interna de Conversas (`src/api/conversations.py`):** Rotas REST para listagem de tickets em aberto, resposta por operador humano e devolução do controle ao bot.
- [x] **Integração Chatwoot (`src/handoff/chatwoot.py`):** Cliente de sincronização de contatos, abertura de conversas, envio de mensagens e resolução de tickets via API do Chatwoot.

### Inteligência, NLU e RAG Seguro
- [x] **NLU & Classificador de Intenção (`src/nlu/`):** Identificação de intenções (saudação, opt-out, atendente humano, rastreio de pedido, agendamento, FAQ) com extração de entidades e pontuação de confiança.
- [x] **RAG com Guardrails de Segurança (`src/knowledge/`):** FAQ fundamentada em artigos oficiais com citação de título, imunidade a tentativas de *prompt injection* (jailbreaks, markers hostis) e recusa elegante fora do escopo.

### Operação, Privacidade e Métricas
- [x] **Métricas Prometheus (`/metrics`):** Exposição de contadores de conversas por status, tickets de handoff e fluxo de mensagens por direção.
- [x] **Proteção de Privacidade & Mascaramento PII (`src/privacy/`):** Mascaramento de telefones e CPFs para conformidade com a LGPD em logs e relatórios.
- [x] **Pesquisa de Satisfação pós-atendimento (CSAT):** Módulo de coleta e validação de notas de 1 a 5 após a finalização do atendimento.

### Canais
- [x] **Simulador Local (`SimulatorAdapter`):** Testes reproduzíveis sem rede ou custo com a Meta.
- [x] **Adapter Oficial Meta Cloud API (`MetaCloudAdapter`):** Implementação completa do protocolo de envio de texto, botões interativos, templates e marcação de mensagens como lidas.

---

## 2. Melhorias Futuras Opcionais (Backlog de Engenharia)
- [ ] **Integração com LLM via OmniRoute Local:** Conectar o classificador de intenções NLU ao endpoint OpenAI-compatível local (`http://localhost:20128/v1`) como backend neural quando a flag de NLU avançado estiver ativada.
- [ ] **Dashboard Web de Operadores:** Interface gráfica própria para visualização de conversas além do painel Chatwoot.

---

## 3. Dependências Externas (Infraestrutura & Credenciais de Produção)
- [x] **Modo Offline e Simulador:** O projeto opera 100% de ponta a ponta sem qualquer dependência externa nos testes automatizados (`167/167` testes passando).
- [ ] **Meta Cloud API Oficial (`META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID`, `META_APP_SECRET`, `META_VERIFY_TOKEN`):** Necessários para deploy em produção apontando para a infraestrutura real do WhatsApp.
- [ ] **Instância Chatwoot em Produção (`CHATWOOT_API_URL`, `CHATWOOT_API_TOKEN`, `CHATWOOT_ACCOUNT_ID`):** Necessária apenas se a empresa utilizar o Chatwoot externo como painel para os atendentes humanos.
- [ ] **PostgreSQL 16 e Redis em Produção:** Utilizados nos testes de integração via SQLite/mocks em memória; em produção, os serviços são providos pelo `docker-compose.yml`.
