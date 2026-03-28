# Plumberito

Agente de infraestructura conversacional que transforma un prompt en un proyecto deployado end-to-end — repositorio en GitHub, infra provisionada en AWS via Pulumi, y deploy automático — todo desde un chat en tiempo real.

Construido para HackITBA 2026.

## Qué hace

El usuario describe lo que quiere construir. Plumberito lo convierte en un plan de acciones y lo ejecuta secuencialmente: genera el código, crea el repositorio, provisiona la infraestructura y hace el deploy. Cada paso se muestra en tiempo real en el frontend vía WebSocket.

## Arquitectura

```
[Frontend - React/Vite en Firebase Hosting]
    │
    │ WebSocket
    ▼
[Backend - Python/FastAPI en GCP Cloud Run]
    │
    ├── HTTPS ──► [OpenRouter] ──► [LLM (Claude/GPT-4)]
    │
    ├── invoke ──► [GitHub API]        crear repo, push código
    ├── invoke ──► [Pulumi SDK]        provisionar infra AWS
    └── invoke ──► [Deploy target]     deploy del proyecto generado
```

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React + Vite + Tailwind CSS |
| Hosting frontend | Firebase Hosting (GCP) |
| Backend / orquestador | Python + FastAPI |
| Hosting backend | GCP Cloud Run |
| LLM gateway | OpenRouter |
| IaC | Pulumi (Python SDK) |
| Repositorios | GitHub REST API v3 |
| Comunicación real-time | WebSocket |

## Estructura del repo

```
plumberito/
├── frontend/          # SPA React + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx       # Navbar con token counter de OpenRouter
│   │   │   ├── ChatMessage.jsx  # Renders user/agent/system messages
│   │   │   ├── CommandInput.jsx # Input con animaciones de entrada/salida
│   │   │   └── SidePanel.jsx    # Paneles laterales con info de sesión
│   │   ├── hooks/
│   │   │   └── useWebSocket.js  # Conexión WS con reconexión automática
│   │   └── App.jsx              # Estado central y layout
│   └── firebase.json            # Config Firebase Hosting
├── docs/                        # Arquitectura y rúbrica del hackathon
└── skills-lock.json             # Skills de Claude Code
```

## Setup frontend

```bash
cd frontend
cp .env.example .env.local       # configurar VITE_WS_URL
npm install
npm run dev
```

Para deploy en Firebase:

```bash
npm run build
firebase deploy --only hosting
```

## Protocolo WebSocket

El backend debe emitir los siguientes tipos de mensaje:

```json
{ "type": "agent_start" }
{ "type": "agent_step",     "step": 1, "action": "REPO_CREATE", "title": "...", "content": "..." }
{ "type": "agent_stream",   "delta": "texto parcial..." }
{ "type": "agent_step_done" }
{ "type": "agent_done" }
{ "type": "agent_error",    "message": "..." }
{ "type": "token_usage",    "payload": { "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0 } }
```

## Alcance del MVP

**Incluido:** flujo prompt → código → repo → infra → deploy, interfaz de chat con streaming en tiempo real, un usuario a la vez (demo).

**Excluido:** autenticación, multi-tenancy, persistencia de sesiones, rollback de acciones, tests del código generado.
