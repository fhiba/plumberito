# Arquitectura End-to-End del MVP

## Desde el prompt del usuario hasta la ejecucion sobre infraestructura, repositorios y deploy.

## Paso a paso del flujo

1. El usuario ingresa un prompt en el frontend ([Next.js](http://Next.js) en Vercel) describiendo lo que quiere construir o deployar.  
2. El frontend envia el prompt al backend (Python en EC2) via WebSocket, lo que permite streaming de la conversacion en tiempo real.  
3. El backend recibe el prompt y lo envia al Agent Provider (OpenRouter) que rutea hacia el modelo LLM adecuado.  
4. El LLM analiza el prompt y devuelve un plan de acciones estructurado (por ejemplo: crear repo, generar archivos, configurar infra, hacer deploy).  
5. El backend ejecuta el agent loop: interpreta cada accion del plan y la ejecuta secuencialmente invocando las integraciones correspondientes (GitHub API, Pulumi, etc.).  
6. Cada accion se ejecuta via Lambdas especializadas que manejan operaciones atomicas (crear repo, push de codigo, provision de infra).  
7. El resultado de cada paso se stremea al frontend via WebSocket para que el usuario vea el progreso en tiempo real.  
8. Al completar todas las acciones, el usuario recibe la URL del recurso deployado o el estado final de la operacion.

# 2\. Componentes Principales del MVP

## 2.1 Frontend

Stack: [Next.js](http://Next.js) deployado en Vercel.

Justificacion:

- Deploy gratuito en el tier free de Vercel (suficiente para el MVP y la hackaton).  
- CD (Continuous Deployment) automatico con cada push a main via integracion nativa Vercel \+ GitHub.  
- Soporte nativo de SSR y API Routes por si se necesitan endpoints ligeros en el frontend.  
- Conexion al backend via WebSocket para mantener la conversacion en tiempo real con el agente, permitiendo streaming de cada paso de ejecucion.

Responsabilidades clave:

- Interfaz de chat donde el usuario ingresa el prompt.  
- Visualizacion del progreso en tiempo real (pasos del agente, logs, resultados).  
- Manejo de estado de la sesion de conversacion.

Info util: Vercel tiene un limite de 100 GB de bandwidth y 100 horas de serverless function execution en el free tier, lo cual es suficiente para un MVP/demo. Para WebSockets, considerar usar Vercel Edge Functions o un approach de Server-Sent Events (SSE) si WebSocket nativo no es soportado en Vercel serverless.

## 2.2 Backend / Orquestador (EC2)

Stack: Python corriendo en una instancia AWS EC2.

Justificacion de Python:

- Ecosistema maduro para manejar LLMs e integraciones con APIs de IA (langchain, openai SDK, etc.).  
- Facilidad para prototipar rapido durante la hackaton.  
- Trade-off aceptado: mayor flexibilidad para IA vs. menor type-safety que TypeScript. El codigo del backend se puede revisar y migrar en PRs posteriores si escala.

Justificacion de EC2 sobre Lambdas para el orquestador:

- El agent loop requiere conexiones de larga duracion (WebSocket) que no son ideales para Lambdas (timeout de 15 min max, cold starts).  
- EC2 permite mantener un proceso persistente que maneja el socket abierto con el frontend.  
- Para la hackaton, AWS EC2 entra en el free tier (t2.micro/t3.micro, 750 horas/mes por 12 meses).

Responsabilidades clave:

- Recibir el prompt del frontend via WebSocket.  
- Manejar el agent loop: enviar prompts a OpenRouter, recibir planes de accion, orquestar la ejecucion.  
- Invocar las Lambdas para ejecutar acciones atomicas.  
- Stremear resultados parciales al frontend.

Info util: Considerar usar FastAPI con soporte de WebSocket nativo, o alternativamente usar websockets library de Python. FastAPI tambien permite exponer endpoints REST para health checks y configuracion.

## 2.3 Agent Provider: OpenRouter

Rol: Actua como gateway unificado hacia multiples modelos LLM. En lugar de integrarse directamente con un proveedor (OpenAI, Anthropic, etc.), OpenRouter permite cambiar de modelo sin cambiar codigo.

Modelo de costos: Creditos con compra previa. Para el MVP se compra un paquete de creditos antes de la hackaton y se monitorea el consumo.

Responsabilidades clave:

- Recibir el prompt procesado desde el backend.  
- Rutear hacia el modelo LLM configurado (ej: Claude, GPT-4, Llama, etc.).  
- Devolver la respuesta estructurada con el plan de acciones.

Info util: OpenRouter soporta streaming de respuestas via SSE, lo que permite que el backend comience a procesar la respuesta del LLM antes de que termine de generarse. Esto reduce la latencia percibida. La API es compatible con el formato de OpenAI, por lo que se puede usar el SDK de OpenAI apuntando al endpoint de OpenRouter. Evaluar cual modelo ofrece mejor relacion costo/calidad para generacion de codigo y planes de accion (Claude Sonnet suele ser buen balance).

## 2.4 Lambdas: Ejecutores de Acciones

Stack: AWS Lambda (free tier incluye 1 millon de requests y 400,000 GB-segundos/mes).

Rol: Ejecutar las acciones atomicas que el agente decide. Cada Lambda es una funcion especializada que realiza una operacion especifica.

Acciones que puede realizar el agente (MVP):

- Crear un repositorio en GitHub via GitHub API.  
- Hacer push de archivos generados al repo.  
- Provisionar infraestructura basica via Pulumi (ej: crear un bucket S3, un dominio, una instancia).  
- Ejecutar un deploy del proyecto generado.

Justificacion de Lambdas para acciones:

- Las acciones son operaciones cortas y atomicas (no requieren conexion persistente).  
- Escalan automaticamente si hay multiples usuarios.  
- Entran en el free tier de AWS.  
- Se pueden testear y deployar de forma independiente.

Info util: Cada Lambda deberia recibir un payload JSON estandarizado con el tipo de accion y los parametros. Definir un contrato claro de entrada/salida para cada tipo de accion. Considerar usar Python tambien en las Lambdas para mantener un solo lenguaje en el backend.

## 2.5 Integraciones Externas

GitHub API:

- Crear repositorios, hacer commits, push de archivos generados por el agente.  
- Se necesita un GitHub App o Personal Access Token (PAT) con permisos de repo.  
- API REST v3 o GraphQL v4. Para el MVP, REST es mas simple.  
- Rate limit: 5,000 requests/hora con autenticacion (suficiente para MVP).

Pulumi (IaC \- Infrastructure as Code):

- Provisionar recursos de infraestructura de forma programatica.  
- Pulumi soporta Python como lenguaje de definicion (consistente con el backend).  
- Permite crear stacks de infra (S3, EC2, etc.) desde codigo que el agente genera.  
- Para el MVP: usar Pulumi Automation API que permite ejecutar operaciones de IaC programaticamente sin CLI.  
- Pulumi tiene un free tier para proyectos individuales.

Repositorio del proyecto:

- Monorepo o multi-repo segun preferencia del equipo.  
- Secrets del usuario: para el MVP/demo se pueden hardcodear o usar variables de entorno. Para produccion seria necesario Supabase, AWS Secrets Manager o similar.

Opciones de hosting gratuito alternativas evaluadas:

- Railway: tiene free tier pero con limites mas estrictos (500 horas/mes). Viable como alternativa si EC2 presenta problemas.  
- Render: free tier con auto-sleep despues de 15 min de inactividad (no ideal para WebSockets).  
- [Fly.io](http://Fly.io): free tier generoso, buena opcion si se necesita algo mas cercano a un PaaS.

# 3\. Limites y Exclusiones del MVP

Lo que SI entra en el MVP (v1):

- Un unico flujo de prompt-to-deploy funcional de punta a punta.  
- Generacion de codigo basico a partir del prompt (proyecto simple, ej: una landing page o API basica).  
- Creacion automatica de repositorio en GitHub con el codigo generado.  
- Provision basica de infraestructura via Pulumi (un recurso simple: S3, EC2, o similar).  
- Deploy automatico del proyecto generado.  
- Interfaz de chat con streaming de progreso en tiempo real.  
- Un solo usuario a la vez (sin multi-tenancy).  
- CI/CD del proyecto generado (el agente hace deploy directo, no configura pipelines).  
- UI pulida con UX simple, funciona como funciona.

Lo que NO entra en el MVP (exclusiones explicitas):

- Autenticacion de usuarios (login/registro). El MVP es una demo sin auth.  
- Multi-tenancy o manejo de sesiones concurrentes.  
- Persistencia de conversaciones o historial (las sesiones son efimeras).  
- Soporte para multiples lenguajes/frameworks (solo un template base).  
- Rollback de acciones o undo si algo falla a mitad del flujo.  
- Manejo sofisticado de errores del LLM (retry basico, sin fallback a otro modelo).  
- Monitoring, logging avanzado o alertas en produccion.  
- Manejo seguro de secrets del usuario (se hardcodean o usan env vars para el demo).  
- Tests automatizados del codigo generado por el agente.

# 4\. Dependencias Externas y Supuestos Criticos

## 4.1 Dependencias externas

OpenRouter (critica): Si OpenRouter esta caido o los creditos se agotan, el agente no puede funcionar. Mitigacion: monitorear creditos, tener un budget alert configurado.

GitHub API (critica): Necesaria para la creacion de repos y push de codigo. Si GitHub tiene downtime, el flujo se interrumpe. Mitigacion: manejar errores gracefully y mostrar al usuario que reintente.

AWS (EC2 \+ Lambda) (critica): Toda la infraestructura de backend corre aca. Mitigacion: usar una sola region (us-east-1 por costo y disponibilidad).

Pulumi Cloud (media): Necesario para el state management de la infra provisionada. Si Pulumi Cloud no esta disponible, no se puede provisionar. Mitigacion: considerar usar state local como fallback.

Vercel (media): Si Vercel tiene problemas, el frontend no esta disponible pero el backend sigue operativo. Mitigacion: para la demo, tener el frontend listo para correr localmente si es necesario.

## 4.2 Supuestos criticos

- Se asume un solo usuario usando el sistema a la vez (demo/hackaton).  
- Los creditos de OpenRouter seran suficientes para las demos y pruebas de la hackaton (estimar \~$20-50 USD de consumo).  
- El free tier de AWS (EC2 \+ Lambda) sera suficiente para el periodo de la hackaton.  
- El modelo LLM elegido via OpenRouter sera capaz de generar planes de accion estructurados y codigo funcional con prompts bien disenados.  
- El usuario del demo tiene una cuenta de GitHub donde el agente puede crear repos (se usa un token pre-configurado).  
- La latencia de OpenRouter \+ LLM es aceptable para una experiencia de demo (\< 30 segundos para generar un plan).  
- No se requiere persistencia de datos entre sesiones.  
- El equipo tiene acceso a una cuenta AWS con free tier activo.

# 5\. Arquitectura de Referencia para Implementacion

## 5.1 Diagrama de arquitectura (texto)

\[Usuario\]  
    |  
    | (HTTPS)  
    v  
\[Frontend \- [Next.js](http://Next.js) en Vercel\]  
    |  
    | (WebSocket / SSE)  
    v  
\[Backend \- Python en EC2\]  
    |  
    |--- (HTTPS) —\> \[OpenRouter\] —\> \[LLM (Claude/GPT-4/etc)\]  
    |  
    |--- (invoke) —\> \[Lambda: GitHub Actions\] —\> \[GitHub API\]  
    |  
    |--- (invoke) —\> \[Lambda: Pulumi Actions\] —\> \[AWS Resources\]  
    |  
    |--- (invoke) —\> \[Lambda: Deploy Actions\] —\> \[Target Infra\]

## 5.2 Stack tecnologico resumen

Frontend: [Next.js](http://Next.js) \+ Vercel (free tier)  
Backend/Orquestador: Python \+ FastAPI \+ AWS EC2 (free tier, t2.micro)  
Agent Provider: OpenRouter (creditos pre-comprados)  
Ejecutores: AWS Lambda (free tier)  
IaC: Pulumi con Python SDK (free tier individual)  
Repositorio: GitHub (API REST v3)  
Comunicacion frontend-backend: WebSocket o SSE  
Comunicacion backend-lambdas: AWS SDK (boto3 invoke)

## 5.3 Decisiones tecnicas clave

EC2 para orquestacion (conexiones largas) \+ Lambdas para acciones (operaciones cortas): Esta separacion permite que el orquestador mantenga el WebSocket abierto mientras delega trabajo pesado a funciones serverless que escalan independientemente.

Python como lenguaje unico del backend: Mantener un solo lenguaje reduce la complejidad operativa durante la hackaton. Python tiene el mejor ecosistema para IA/LLM.

OpenRouter como abstraccion del LLM: Permite cambiar de modelo (Claude, GPT-4, Llama) sin cambiar codigo. Util para optimizar costo/calidad durante el desarrollo.

WebSocket/SSE para comunicacion real-time: El usuario necesita ver el progreso del agente paso a paso. Una API REST con polling no daria la misma experiencia.

Pulumi sobre Terraform: Pulumi permite definir infra en Python (mismo lenguaje del backend) y tiene Automation API para ejecucion programatica. Terraform requeriria un lenguaje separado (HCL) y una ejecucion basada en CLI.

## 5.4 Proximos pasos para implementacion

1. Crear los repositorios del proyecto (frontend \+ backend, o monorepo).  
2. Configurar la instancia EC2 y deployar un “hello world” del backend con FastAPI \+ Socket.  
3. Configurar el proyecto [Next.js](http://Next.js) en Vercel y conectar al repo.  
4. Crear una primera Lambda de prueba (ej: crear repo en GitHub) y validar la ocacion desde EC2.  
5. Integrar OpenRouter y validar que se puede enviar un prompt y recibir una puesta estructurada.  
6. Implementar el agent loop basico: prompt \-\> plan \-\> ejecucion secuencial de iones.  
7. Conectar el frontend al backend via WebSocket y mostrar streaming del progreso.  
8. 8\. Implementar el flujo completo end-to-end con un caso de uso simple (ej: “creame una landing page y deployala”).