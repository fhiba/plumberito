# Plumberito

Agente de infraestructura conversacional que transforma un prompt en un proyecto deployado end-to-end — repositorio en GitHub, infra provisionada en GCP via Pulumi, y deploy automatico — todo desde un chat en tiempo real.

Construido para HackITBA 2026.

## Que hace

El usuario describe lo que quiere construir. Plumberito lo convierte en un plan de acciones y lo ejecuta secuencialmente: genera el codigo, crea el repositorio, provisiona la infraestructura y hace el deploy. Cada paso se muestra en tiempo real en el frontend via SSE.

## Arquitectura

```
[Frontend - React/Vite en Firebase Hosting]
    |
    | HTTP + SSE
    v
[Backend - Python/FastAPI en GCP Cloud Run]
    |
    |-- HTTPS --> [OpenRouter] --> [LLM (Claude/GPT-4/Qwen/Deepseek)]
    |
    |-- invoke --> [GitHub API]        crear repo, push codigo
    |-- invoke --> [Pulumi SDK]        provisionar infra GCP
    └-- invoke --> [Deploy target]     deploy del proyecto generado
```

## Stack

| Capa | Tecnologia |
|------|-----------|
| Frontend | React 19 + Vite 8 + Tailwind CSS |
| Hosting frontend | Firebase Hosting (GCP) |
| Backend / orquestador | Python 3.11 + FastAPI |
| Hosting backend | GCP Cloud Run |
| LLM gateway | OpenRouter |
| IaC | Pulumi (Python SDK) + GCP provider |
| Repositorios | GitHub REST API v3 + OAuth |
| Error tracking | Sentry (para proyectos deployados) |
| Comunicacion real-time | SSE (Server-Sent Events) |

---

## Requisitos previos

### Herramientas locales

| Herramienta | Version | Instalacion |
|-------------|---------|-------------|
| **Node.js** | >= 18 | [nodejs.org](https://nodejs.org) o `nvm install 18` |
| **npm** | >= 9 | Viene con Node.js |
| **Python** | 3.11 | [python.org](https://python.org) o `pyenv install 3.11` |
| **pip** | cualquiera | Viene con Python |
| **Google Cloud CLI** (`gcloud`) | latest | [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) |
| **Firebase CLI** | latest | `npm install -g firebase-tools` |
| **Pulumi CLI** | >= 3.x | `curl -fsSL https://get.pulumi.com \| sh` |
| **Docker** | cualquiera | Solo necesario si queres buildear el container localmente |

### Cuentas y servicios externos

| Servicio | Para que | Donde conseguirlo |
|----------|----------|-------------------|
| **GCP Project** | Cloud Run, Secret Manager, IAM | [console.cloud.google.com](https://console.cloud.google.com) |
| **Firebase** | Hosting del frontend | `firebase login` + `firebase init hosting` |
| **OpenRouter** | Gateway a LLMs (Claude, GPT-4, etc.) | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **GitHub** | Repos + OAuth app | [github.com/settings/tokens](https://github.com/settings/tokens) |
| **GitHub OAuth App** | Login de usuarios | [github.com/settings/developers](https://github.com/settings/developers) |
| **Pulumi Cloud** | Estado de stacks IaC | [app.pulumi.com](https://app.pulumi.com) (free tier) |
| **Sentry** | Error tracking en proyectos generados | [sentry.io](https://sentry.io) |

---

## Configuracion de GCP

### APIs que hay que habilitar

```bash
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  firebase.googleapis.com
```

### Secret Manager

El backend en Cloud Run lee secretos desde GCP Secret Manager. Hay que crear cada uno:

```bash
# Repetir para cada secreto
echo -n "valor" | gcloud secrets create NOMBRE_DEL_SECRETO --data-file=-

# Secretos necesarios:
# OPENROUTER_API_KEY, GITHUB_TOKEN, PULUMI_ACCESS_TOKEN,
# GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, OAUTH_CALLBACK_URL,
# SENTRY_AUTH_TOKEN, SENTRY_WEBHOOK_SECRET
```

### Workload Identity Federation (WIF)

WIF permite que GitHub Actions asuma un Service Account de GCP sin keys. Esto se usa para que los proyectos generados puedan hacer deploy a Firebase desde CI.

```bash
# 1. Crear pool de identidad
gcloud iam workload-identity-pools create github \
  --location=global \
  --display-name="GitHub Actions"

# 2. Crear provider OIDC
gcloud iam workload-identity-pools providers create-oidc github-actions \
  --location=global \
  --workload-identity-pool=github \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository"

# 3. Dar permisos al SA
gcloud iam service-accounts add-iam-policy-binding \
  firebase-deployer@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/ORG_NAME/*"
```

### Service Account para Firebase deploy

```bash
# Crear el SA
gcloud iam service-accounts create firebase-deployer \
  --display-name="Firebase Deployer (usado por GitHub Actions)"

# Roles necesarios
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:firebase-deployer@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/firebasehosting.admin"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:firebase-deployer@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

### IAM del Service Account de Cloud Run

El SA default de Cloud Run necesita acceso a Secret Manager:

```bash
# El SA default es: PROJECT_NUMBER-compute@developer.gserviceaccount.com
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Configuracion de GitHub OAuth App

1. Ir a [github.com/settings/developers](https://github.com/settings/developers) > **OAuth Apps** > **New OAuth App**
2. Configurar:
   - **Application name:** Plumberito
   - **Homepage URL:** URL del frontend (Firebase Hosting o `http://localhost:5173`)
   - **Authorization callback URL:** `http://localhost:5173/auth/callback` (dev) o tu URL de produccion
3. Anotar el **Client ID** y generar un **Client Secret**

---

## Variables de entorno

### Backend (`backend/.env`)

```bash
cd backend
cp .env.example .env
```

| Variable | Descripcion |
|----------|-------------|
| `OPENROUTER_API_KEY` | API key de OpenRouter |
| `LLM_MODEL` | Modelo a usar para el agente (default: `google/gemini-2.0-flash-001`) |
| `WEBHOOK_LLM_MODEL` | Modelo para webhooks de Sentry (default: `deepseek/deepseek-chat`) |
| `GITHUB_TOKEN` | Personal Access Token con scopes `repo`, `workflow`, `admin:org` |
| `GITHUB_ORG` | Org o usuario donde se crean los repos |
| `GITHUB_CLIENT_ID` | Client ID de la OAuth App |
| `GITHUB_CLIENT_SECRET` | Client Secret de la OAuth App |
| `OAUTH_CALLBACK_URL` | URL de callback del OAuth (`http://localhost:5173/auth/callback`) |
| `GCP_PROJECT` | ID del proyecto GCP |
| `GCP_PROJECT_NUMBER` | Numero del proyecto GCP (numerico) |
| `GCP_REGION` | Region GCP (default: `us-central1`) |
| `WIF_PROVIDER` | Full resource name del WIF provider |
| `FIREBASE_SA_EMAIL` | Email del SA de Firebase deploy |
| `PULUMI_ACCESS_TOKEN` | Token de Pulumi Cloud |
| `SENTRY_AUTH_TOKEN` | Token de Sentry para crear proyectos |
| `SENTRY_ORG` | Organizacion de Sentry |
| `SENTRY_TEAM` | Team de Sentry |
| `SENTRY_WEBHOOK_SECRET` | Secreto para validar webhooks de Sentry |

### Frontend (`frontend/.env.local`)

```bash
cd frontend
cp .env.example .env.local
```

| Variable | Descripcion |
|----------|-------------|
| `VITE_BACKEND_URL` | URL del backend (`http://localhost:8000` en dev, URL de Cloud Run en prod) |

---

## Setup local

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # editar con tus valores
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # editar VITE_BACKEND_URL
npm run dev                   # http://localhost:5173
```

Para correr con datos mock (sin backend):

```bash
npm run mock
```

---

## Deploy a produccion

### Backend (Cloud Run)

Prerequisitos:
- `gcloud auth login` y proyecto configurado (`gcloud config set project PROJECT_ID`)
- Secretos cargados en Secret Manager (ver seccion anterior)
- El archivo `backend/.env` con las variables no-secretas

```bash
./deploy-backend.sh
```

Esto ejecuta `gcloud run deploy` con:
- Timeout de 1 hora (para operaciones largas del agente)
- 1 vCPU, 1 GiB RAM, max 2 instancias
- Variables de entorno inyectadas desde `.env`
- Secretos inyectados desde Secret Manager

### Frontend (Firebase Hosting)

Prerequisitos:
- `firebase login`
- Proyecto de Firebase inicializado (`firebase init hosting`)

```bash
VITE_BACKEND_URL=https://orchestrator-XXXXX.us-central1.run.app ./deploy-frontend.sh
```

---

## Protocolo SSE

El backend streamea eventos en formato `text/event-stream`:

```json
{ "type": "agent_start" }
{ "type": "agent_step",     "step": 1, "action": "REPO_CREATE", "title": "...", "content": "..." }
{ "type": "agent_stream",   "delta": "texto parcial..." }
{ "type": "agent_step_done" }
{ "type": "agent_done" }
{ "type": "agent_error",    "message": "..." }
{ "type": "token_usage",    "payload": { "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0 } }
{ "type": "artifact",       "kind": "github|deploy", "label": "...", "url": "..." }
```

## Tools del agente

El backend expone 6 herramientas que el LLM puede invocar:

| Tool | Que hace |
|------|----------|
| `search_repos` | Buscar repos del usuario en GitHub (filtros: nombre, lenguaje, template, etc.) |
| `read_repo` | Leer arbol de archivos y contenido de un repo |
| `create_repo` | Crear repo desde un template en la cuenta del usuario |
| `setup_deploy` | Configurar Firebase Hosting + workflow de GitHub Actions con WIF |
| `provision_infrastructure` | Provisionar recursos GCP via Pulumi (Cloud Run, Cloud Storage) |
| `destroy_infrastructure` | Destruir un stack de Pulumi |

## Estructura del repo

```
plumberito/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, /chat endpoint, SSE streaming
│   │   ├── auth.py           # GitHub OAuth routes
│   │   ├── tools.py          # Implementacion de las 6 tools
│   │   ├── infra.py          # Integracion con Pulumi Automation API
│   │   └── webhooks.py       # Sentry webhook → auto-fix con LLM
│   ├── Dockerfile            # python:3.11-slim + Pulumi CLI
│   ├── requirements.txt
│   ├── requirements-dev.txt  # pytest, respx
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Estado central, OAuth flow, layout
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── ChatMessage.jsx
│   │   │   ├── CommandInput.jsx
│   │   │   ├── SidePanel.jsx
│   │   │   └── PaywallModal.jsx
│   │   ├── hooks/
│   │   │   └── useSSEChat.js # Conexion SSE con reconexion
│   │   └── mocks/
│   │       └── mockSSEStream.js
│   ├── firebase.json         # Config Firebase Hosting
│   ├── .env.example
│   └── package.json
├── docs/                     # Arquitectura y rubrica del hackathon
├── scripts/                  # Utilidades (Sentry templates, test deploy)
├── deploy-backend.sh         # Deploy a Cloud Run
├── deploy-frontend.sh        # Build + deploy a Firebase
└── README.md
```

## Alcance del MVP

**Incluido:** flujo prompt -> codigo -> repo -> infra -> deploy, interfaz de chat con streaming en tiempo real, GitHub OAuth, auto-fix de errores via Sentry webhooks.
