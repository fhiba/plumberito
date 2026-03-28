# Arquitectura End-to-End del MVP (GCP Edition)

## Desde el prompt del usuario hasta la ejecución sobre infraestructura, repositorios y deploy.

---

## 1. Flujo paso a paso

1. El usuario ingresa un prompt en el frontend (React SPA) describiendo lo que quiere construir o deployar.
2. El frontend envía el prompt al backend (Python en Cloud Run) vía WebSocket o SSE, lo que permite streaming de la conversación en tiempo real.
3. El backend recibe el prompt y lo envía al Agent Provider (OpenRouter) que rutea hacia el modelo LLM adecuado.
4. El LLM analiza el prompt y devuelve un plan de acciones estructurado (por ejemplo: crear repo, generar archivos, configurar infra, hacer deploy).
5. El backend ejecuta el agent loop: interpreta cada acción del plan y la ejecuta secuencialmente invocando las integraciones correspondientes (GitHub API, Pulumi, etc.).
6. Cada acción se ejecuta vía Cloud Functions especializadas que manejan operaciones atómicas (crear repo, push de código, provisión de infra).
7. El resultado de cada paso se streamea al frontend vía WebSocket/SSE para que el usuario vea el progreso en tiempo real.
8. Al completar todas las acciones, el usuario recibe la URL del recurso deployado o el estado final de la operación.

---

## 2. Componentes Principales del MVP

### 2.1 Frontend — React SPA

**Stack:** React + shadcn/ui + TanStack (Query + Router) deployado como SPA estática.

**Justificación del stack:**

- shadcn/ui provee componentes accesibles y personalizables sin overhead de runtime (copy-paste, no library). Ideal para una UI de chat pulida en poco tiempo.
- TanStack Query maneja el estado del servidor (cache, refetch, optimistic updates) sin boilerplate. TanStack Router provee routing type-safe si se necesitan múltiples vistas.
- Al ser una SPA pura (sin SSR), el build genera archivos estáticos (HTML/JS/CSS) que se pueden hostear en cualquier CDN.

**Opciones de hosting (en orden de pragmatismo para hackathon):**

| Opción | Pros | Contras | Recomendación |
|--------|------|---------|---------------|
| **Vercel/Netlify** | Zero config, push y listo, CDN global, free tier generoso | Frontend fuera de GCP | **Recomendado para hackathon.** La SPA es estática, no importa dónde viva. |
| **Firebase Hosting** | Dentro de GCP, CDN global, free tier (10 GB storage, 360 MB/día transfer) | Requiere instalar firebase-tools, crear proyecto Firebase, configurar | Viable si quieren todo en GCP. |
| **Cloud Storage + Load Balancer** | 100% GCP nativo | Configuración manual del bucket público, CDN requiere Cloud CDN ($), más pasos | Overkill para MVP. |

**Decisión: Vercel o Netlify.** Hostear una SPA estática en Vercel/Netlify es trivial y no depende de GCP. El backend sí vive en GCP. Mezclar clouds para una hackathon es perfectamente válido — lo que importa es minimizar fricción.

**Responsabilidades clave:**

- Interfaz de chat donde el usuario ingresa el prompt.
- Visualización del progreso en tiempo real (pasos del agente, logs, resultados).
- Manejo de estado de la sesión de conversación vía TanStack Query.
- Conexión al backend vía WebSocket o SSE (ver sección de comunicación).

**Info útil:** Para WebSocket desde React, considerar usar una library liviana como `use-websocket` o implementar un hook custom. Si se usa SSE, TanStack Query puede manejar el streaming con `EventSource` nativo del browser. shadcn/ui tiene un componente de `ScrollArea` que sirve perfecto para el chat scroll.

---

### 2.2 Backend / Orquestador — Cloud Run

**Stack:** Python + FastAPI corriendo en un container Docker deployado en Google Cloud Run.

**Justificación de Cloud Run:**

- Soporta WebSocket y SSE con timeout configurable hasta **60 minutos** por request. Esto cubre de sobra cualquier sesión de demo.
- Escala a cero automáticamente (no pagás cuando no hay tráfico), a diferencia de una VM permanente.
- Free tier: 2 millones de requests, 360,000 vCPU-seconds, 180,000 GiB-seconds por mes. Más que suficiente para hackathon.
- Deploy con un solo comando: `gcloud run deploy`.
- No requiere manejar VMs, SSH, security groups ni networking manual.

**Justificación de Cloud Run sobre Compute Engine (ex EC2):**

| Aspecto | Cloud Run | Compute Engine |
|---------|-----------|----------------|
| Costo en idle | $0 (escala a cero) | Corre 24/7 aunque no haya tráfico |
| Setup | Dockerfile + 1 comando | Crear VM, instalar deps, configurar firewall, etc. |
| WebSocket | Sí, hasta 60 min | Sí, sin límite |
| Cold start | ~2-5 seg primera request | No hay (siempre encendido) |
| Free tier | Generoso (por uso) | 1 VM e2-micro siempre encendida |

Para la hackathon, Cloud Run gana por menor fricción operativa. El cold start se mitiga con `--min-instances=1` si es necesario (consume free tier más rápido pero elimina el delay).

**Configuración recomendada:**

```
gcloud run deploy orchestrator \
  --source . \
  --region us-central1 \
  --timeout 3600 \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 3 \
  --allow-unauthenticated
```

**Responsabilidades clave:**

- Recibir el prompt del frontend vía WebSocket/SSE.
- Manejar el agent loop: enviar prompts a OpenRouter, recibir planes de acción, orquestar la ejecución.
- Invocar las Cloud Functions para ejecutar acciones atómicas.
- Streamear resultados parciales al frontend.

**Info útil:** FastAPI tiene soporte nativo de WebSocket (`@app.websocket("/ws")`). Para SSE, usar `StreamingResponse` de Starlette. El Dockerfile puede ser minimal: `python:3.11-slim` + `pip install fastapi uvicorn`. Cloud Run asigna automáticamente un dominio HTTPS (*.run.app) con TLS, no hay que configurar certificados.

---

### 2.3 Agent Provider — OpenRouter

**Rol:** Gateway unificado hacia múltiples modelos LLM. Sin cambios respecto a la arquitectura original — OpenRouter es cloud-agnostic.

**Modelo de costos:** Créditos con compra previa. Para el MVP se compra un paquete de créditos (~$20-50 USD) antes de la hackathon y se monitorea el consumo.

**Responsabilidades clave:**

- Recibir el prompt procesado desde el backend.
- Rutear hacia el modelo LLM configurado (Claude, GPT-4, Llama, etc.).
- Devolver la respuesta estructurada con el plan de acciones.

**Info útil:** La API de OpenRouter es compatible con el formato de OpenAI, así que se puede usar el SDK de OpenAI apuntando al endpoint de OpenRouter. Soporta streaming vía SSE. Para la hackathon, Claude Sonnet ofrece buen balance costo/calidad para generación de código y planes de acción.

---

### 2.4 Ejecutores de Acciones — Cloud Functions (2nd gen)

**Stack:** Google Cloud Functions 2nd gen (Python runtime).

**Justificación:**

- Cloud Functions 2nd gen corre sobre Cloud Run internamente, lo que les da mejor performance y hasta 60 min de timeout.
- Free tier: 2 millones de invocaciones, 400,000 GB-seconds, 200,000 GHz-seconds por mes.
- Deploy simple: `gcloud functions deploy`.
- Python como runtime mantiene un solo lenguaje en todo el backend.

**Acciones que puede realizar el agente (MVP):**

- Crear un repositorio en GitHub vía GitHub API.
- Hacer push de archivos generados al repo.
- Provisionar infraestructura básica vía Pulumi (ej: bucket de Cloud Storage, instancia de Compute Engine, Cloud Run service).
- Ejecutar un deploy del proyecto generado.

**Consideración sobre Pulumi en Cloud Functions:**

Pulumi Automation API descarga plugins en cold start, lo que puede tardar 10-30 segundos la primera vez. Opciones:

1. **Correr Pulumi desde Cloud Run (orquestador):** Elimina el overhead de cold start de una function separada. El orquestador ya tiene conexión larga, así que el tiempo de Pulumi no es problema. **Recomendado para MVP.**
2. **Cloud Function dedicada con imagen custom:** Prebakear los plugins de Pulumi en la imagen del container. Requiere más setup pero aísla mejor la responsabilidad.

**Para el MVP: Pulumi corre en el orquestador (Cloud Run), las Cloud Functions solo manejan operaciones livianas (GitHub API, deploy triggers).**

**Invocación desde el orquestador:**

```python
# Opción 1: HTTP directo (Cloud Functions 2nd gen expone HTTP endpoint)
import httpx
response = await httpx.post(
    "https://REGION-PROJECT.cloudfunctions.net/create-repo",
    json={"name": "my-project", "template": "landing-page"},
    headers={"Authorization": f"Bearer {id_token}"}
)

# Opción 2: Usando google-cloud-functions client (más GCP-nativo)
# Para MVP, HTTP directo es más simple y testeable.
```

---

### 2.5 Integraciones Externas

**GitHub API:** Sin cambios. Se necesita un GitHub App o Personal Access Token (PAT) con permisos de repo. API REST v3 para el MVP. Rate limit: 5,000 requests/hora con autenticación.

**Pulumi (IaC):**

- Cambia el target de AWS a GCP: en vez de crear S3 buckets y EC2 instances, se crean Cloud Storage buckets, Cloud Run services, Compute Engine instances.
- Pulumi soporta GCP nativamente con el provider `pulumi-gcp`.
- Para el MVP: usar Pulumi Automation API desde el orquestador.
- State management: Pulumi Cloud (free tier) o state local en el filesystem del container (más simple para demo pero no persiste entre deploys del orquestador).

**Secrets y configuración:**

- Para el MVP/demo: variables de entorno en Cloud Run (`--set-env-vars` o `--set-secrets` con Secret Manager).
- GCP Secret Manager tiene 6 versiones activas gratis y 10,000 operaciones de acceso/mes gratis.

---

## 3. Comunicación Frontend ↔ Backend

### Opción A: WebSocket (recomendado si ya tienen experiencia)

- FastAPI soporta WebSocket nativo.
- Cloud Run soporta WebSocket con timeout de hasta 60 min.
- El frontend abre una conexión persistente y recibe updates en tiempo real.
- Requiere manejar reconexión si la conexión se corta.

### Opción B: SSE — Server-Sent Events (recomendado para simplicidad)

- Más simple de implementar: es un HTTP GET normal con `Content-Type: text/event-stream`.
- Cloud Run lo soporta nativamente sin configuración extra.
- El browser tiene `EventSource` nativo, no necesita library.
- Unidireccional (server → client). Para enviar el prompt, se usa un POST normal y luego se abre el SSE stream para recibir updates.
- Más fácil de debuggear (es HTTP estándar, se ve en DevTools).

**Recomendación para hackathon: SSE.** Es más simple de implementar y debuggear. El flujo sería:

1. POST `/api/prompt` → envía el prompt, recibe un `session_id`.
2. GET `/api/stream/{session_id}` → abre SSE stream, recibe eventos de progreso.

---

## 4. Autenticación entre servicios (GCP)

Para la comunicación **orquestador → Cloud Functions**, GCP ofrece autenticación nativa vía IAM:

- El Cloud Run service tiene un **service account** asociado.
- Las Cloud Functions se configuran para aceptar invocaciones solo desde ese service account.
- El orquestador obtiene un ID token automáticamente vía metadata server de GCP (no hay que manejar API keys).

**Para el MVP/demo:** Se pueden dejar las Cloud Functions como `--allow-unauthenticated` para simplificar. No hay auth de usuarios de todas formas.

---

## 5. Límites y Exclusiones del MVP

### Lo que SÍ entra en el MVP (v1):

- Un único flujo de prompt-to-deploy funcional de punta a punta.
- Generación de código básico a partir del prompt (proyecto simple, ej: una landing page o API básica).
- Creación automática de repositorio en GitHub con el código generado.
- Provisión básica de infraestructura vía Pulumi sobre GCP (Cloud Storage, Cloud Run, o similar).
- Deploy automático del proyecto generado.
- Interfaz de chat con streaming de progreso en tiempo real.
- Un solo usuario a la vez (sin multi-tenancy).
- UI pulida con shadcn/ui, UX simple y funcional.

### Lo que NO entra en el MVP:

- Autenticación de usuarios (login/registro). El MVP es una demo sin auth.
- Multi-tenancy o manejo de sesiones concurrentes.
- Persistencia de conversaciones o historial (sesiones efímeras).
- Soporte para múltiples lenguajes/frameworks (solo un template base).
- Rollback de acciones o undo si algo falla a mitad del flujo.
- Manejo sofisticado de errores del LLM (retry básico, sin fallback a otro modelo).
- Monitoring, logging avanzado o alertas en producción.
- Tests automatizados del código generado por el agente.

---

## 6. Dependencias Externas y Supuestos Críticos

### 6.1 Dependencias externas

| Dependencia | Criticidad | Mitigación |
|-------------|-----------|------------|
| **OpenRouter** | Crítica | Monitorear créditos, tener budget alert. Si cae, el agente no funciona. |
| **GitHub API** | Crítica | Manejar errores gracefully. Rate limit de 5,000 req/hora es suficiente. |
| **GCP (Cloud Run + Cloud Functions)** | Crítica | Usar una sola región (us-central1). $300 créditos gratis en cuentas nuevas + free tier permanente. |
| **Pulumi Cloud** | Media | Para MVP se puede usar state local como fallback. |
| **Vercel/Netlify** | Baja | SPA estática se puede servir desde cualquier lado. Tener build local listo como backup. |

### 6.2 Supuestos críticos

- Se asume un solo usuario usando el sistema a la vez (demo/hackathon).
- Los créditos de OpenRouter serán suficientes (~$20-50 USD de consumo estimado).
- El free tier de GCP (o los $300 de créditos nuevos) será suficiente para el período de la hackathon.
- El modelo LLM elegido será capaz de generar planes de acción estructurados y código funcional.
- El usuario del demo tiene una cuenta de GitHub donde el agente puede crear repos (token pre-configurado).
- La latencia de OpenRouter + LLM es aceptable para demo (< 30 segundos para generar un plan).
- No se requiere persistencia de datos entre sesiones.
- El equipo tiene acceso a una cuenta GCP con billing habilitado (necesario para activar Cloud Run/Functions, aunque no se cobre nada con free tier).

---

## 7. Arquitectura de Referencia

### 7.1 Diagrama de arquitectura (texto)

```
[Usuario]
    |
    | (HTTPS)
    v
[Frontend — React SPA en Vercel/Netlify]
    |
    | (SSE o WebSocket sobre HTTPS)
    v
[Backend — Python/FastAPI en Cloud Run]
    |
    |--- (HTTPS) ——→ [OpenRouter] ——→ [LLM (Claude/GPT-4/etc)]
    |
    |--- (HTTP) ——→ [Cloud Function: GitHub Actions] ——→ [GitHub API]
    |
    |--- (directo) → [Pulumi Automation API] ——→ [GCP Resources]
    |
    |--- (HTTP) ——→ [Cloud Function: Deploy Actions] ——→ [Target Infra]
```

### 7.2 Stack tecnológico resumen

| Componente | Tecnología | Hosting |
|-----------|-----------|---------|
| Frontend | React + shadcn/ui + TanStack | Vercel o Netlify (free tier) |
| Backend/Orquestador | Python + FastAPI | Cloud Run (free tier) |
| Agent Provider | OpenRouter | SaaS (créditos pre-comprados) |
| Ejecutores livianos | Python | Cloud Functions 2nd gen (free tier) |
| IaC | Pulumi + Python SDK + GCP provider | Corre en Cloud Run (orquestador) |
| Repositorio | GitHub | API REST v3 |
| Comunicación FE↔BE | SSE (recomendado) o WebSocket | Sobre HTTPS nativo de Cloud Run |
| Comunicación BE→Functions | HTTP directo | Endpoints nativos de Cloud Functions |
| Secrets | Variables de entorno en Cloud Run | (Secret Manager para producción) |

### 7.3 Decisiones técnicas clave

**Cloud Run para orquestación + Cloud Functions para acciones livianas:** Cloud Run mantiene la conexión larga (SSE/WebSocket) y ejecuta Pulumi directamente. Cloud Functions maneja operaciones atómicas y livianas (GitHub API calls, deploy triggers) que no necesitan conexión persistente.

**Pulumi en el orquestador, no en Cloud Function separada:** Evita el cold start pesado de Pulumi. El orquestador ya tiene una sesión larga, así que el tiempo de Pulumi (10-30 seg) no es problema. Simplifica el número de servicios a mantener.

**SSE sobre WebSocket para la hackathon:** Más simple de implementar, debuggear y mantener. HTTP estándar, sin necesidad de manejar reconexión de sockets. Si en el futuro necesitan bidireccionalidad (ej: el usuario cancela una acción mid-stream), migrar a WebSocket es un cambio menor.

**React SPA en Vercel, backend en GCP:** Mezclar clouds está bien para una hackathon. La SPA es estática y se sirve desde CDN — no tiene acoplamiento con el cloud del backend. Esto minimiza la fricción de setup (Vercel = push y listo) sin comprometer la arquitectura.

**Python como lenguaje único del backend:** Cloud Run, Cloud Functions y Pulumi usan Python. Un solo lenguaje reduce complejidad operativa durante la hackathon.

**OpenRouter como abstracción del LLM:** Sin cambios. Permite cambiar de modelo sin cambiar código. Cloud-agnostic.

---

## 8. Próximos pasos para implementación

1. **Crear proyecto GCP** y habilitar billing (necesario aunque todo sea free tier). Habilitar APIs: Cloud Run, Cloud Functions, Artifact Registry, Cloud Build.
2. **Instalar `gcloud` CLI** y autenticarse (`gcloud auth login`, `gcloud config set project PROJECT_ID`).
3. **Crear el repo del proyecto** (monorepo o multi-repo según preferencia).
4. **Scaffoldear el backend:** FastAPI + Dockerfile minimal. Deployar un "hello world" a Cloud Run y validar que responde.
5. **Scaffoldear el frontend:** React + Vite + shadcn/ui + TanStack. Deployar a Vercel y validar que carga.
6. **Crear una Cloud Function de prueba** (ej: crear repo en GitHub) y validar la invocación desde Cloud Run.
7. **Integrar OpenRouter** y validar que se puede enviar un prompt y recibir una respuesta estructurada.
8. **Conectar frontend al backend** vía SSE y mostrar streaming de un mensaje de prueba.
9. **Implementar el agent loop básico:** prompt → plan → ejecución secuencial de acciones.
10. **Flujo end-to-end** con un caso de uso simple: "creame una landing page y deployala".

---

## 9. Free Tier Cheat Sheet (GCP)

| Servicio | Free Tier | Suficiente para hackathon? |
|----------|-----------|---------------------------|
| Cloud Run | 2M requests, 360K vCPU-sec, 180K GiB-sec/mes | Sí, de sobra |
| Cloud Functions | 2M invocaciones, 400K GB-sec/mes | Sí |
| Cloud Storage | 5 GB, 5K operaciones Class A, 50K Class B/mes | Sí |
| Artifact Registry | 500 MB storage | Sí (para imágenes Docker) |
| Secret Manager | 6 versiones activas, 10K accesos/mes | Sí |
| Cloud Build | 120 min/día de build | Sí |
| **Créditos nuevos** | **$300 USD por 90 días (cuentas nuevas)** | **Cubre todo sin preocuparse** |
