import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI

from app.tools import GITHUB_ORG, TOOLS, execute_tool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("plumberito")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = os.environ.get("LLM_MODEL", "qwen/qwen3.5-flash-02-23")
MAX_CONTEXT_TOKENS = None
MAX_AGENT_ITERATIONS = 10

SYSTEM_PROMPT = (
    "You are Plumberito, a DevOps and infrastructure assistant with access to the user's GitHub repositories "
    "and the ability to provision GCP infrastructure.\n\n"
    "Always base your answers on actual repo data — use search_repos to find repos, then read_repo to inspect contents before answering.\n\n"
    "When the user wants to create a new project:\n"
    f"1. Search for available templates in the '{GITHUB_ORG}' org using search_repos\n"
    "2. Read the README of candidate templates with read_repo to understand what each one provides\n"
    "3. Recommend the best match and confirm with the user\n"
    "4. Call create_repo with the chosen template_repo — this creates the repo and sends a collaboration invite\n"
    "5. Ask the user to accept the collaboration invite on GitHub (email or notifications)\n"
    "6. Once the user confirms they accepted, call transfer_repo to transfer ownership to them\n\n"
    "When the user wants to deploy or provision infrastructure:\n"
    "1. Understand what the user wants to deploy (a web app, an API, a static site, storage, etc.)\n"
    "2. Determine the appropriate GCP resources: cloud_run_service for containerized apps, cloud_storage_bucket for storage/static files\n"
    "3. Call provision_infrastructure with a descriptive project_name and the list of resources\n"
    "4. Report the outputs (URLs, resource names) back to the user\n"
    "5. If the user wants to tear down resources, use destroy_infrastructure\n\n"
    "For Cloud Run deployments, you need a container image. Ask the user for the image URL "
    "(e.g. from Artifact Registry or Docker Hub). If none is provided, use the default hello-world image for demo purposes.\n"
    "For simple storage needs, use cloud_storage_bucket.\n"
)


@app.on_event("startup")
def fetch_model_context_length():
    global MAX_CONTEXT_TOKENS
    logger.info("Starting up — model=%s", MODEL)
    import httpx
    resp = httpx.get("https://openrouter.ai/api/v1/models")
    resp.raise_for_status()
    models = resp.json().get("data", [])
    match = next((m for m in models if m["id"] == MODEL), None)
    if not match:
        raise RuntimeError(f"Model '{MODEL}' not found on OpenRouter")
    MAX_CONTEXT_TOKENS = match.get("context_length")
    logger.info("Context length fetched: %s", MAX_CONTEXT_TOKENS)


def sse(data: str) -> str:
    return f"data: {data}\n\n"


def sse_json(obj: dict) -> str:
    return sse(json.dumps(obj))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    if not messages and body.get("prompt"):
        messages = [{"role": "user", "content": body["prompt"]}]

    llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    async def generate():
        nonlocal llm_messages

        logger.info("POST /chat — user message: %s", messages[-1].get("content", "")[:100] if messages else "(empty)")

        yield sse_json({"type": "agent_start"})

        step = 1
        last_usage = None

        try:
            for iteration in range(MAX_AGENT_ITERATIONS):
                logger.info("Agent iteration %d/%d", iteration + 1, MAX_AGENT_ITERATIONS)

                # Call LLM with tools and streaming
                stream = client.chat.completions.create(
                    model=MODEL,
                    messages=llm_messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    stream=True,
                    stream_options={"include_usage": True},
                )

                # Accumulate the streamed response
                content_buffer = ""
                tool_calls = {}  # index -> {id, name, arguments}
                finish_reason = None
                content_step_started = False

                for chunk in stream:
                    # Track usage from the last chunk
                    if hasattr(chunk, "usage") and chunk.usage:
                        last_usage = chunk.usage

                    if not chunk.choices:
                        continue

                    choice = chunk.choices[0]
                    finish_reason = choice.finish_reason or finish_reason
                    delta = choice.delta

                    # Accumulate tool calls
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls:
                                tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
                            if tc.id:
                                tool_calls[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls[idx]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls[idx]["arguments"] += tc.function.arguments

                    # Stream text content
                    if delta.content:
                        if not content_step_started:
                            yield sse_json({
                                "type": "agent_step",
                                "step": step,
                                "action": "LLM_RESPONSE",
                                "title": "Generating response\u2026",
                                "content": "",
                            })
                            content_step_started = True
                        content_buffer += delta.content
                        yield sse_json({"type": "agent_stream", "delta": delta.content})

                logger.info("LLM finished — finish_reason=%s, tool_calls=%d, content_len=%d",
                            finish_reason, len(tool_calls), len(content_buffer))

                if content_step_started:
                    yield sse_json({"type": "agent_step_done"})
                    step += 1

                # If the LLM made tool calls, execute them and loop
                if tool_calls:
                    # Build the assistant message with tool calls
                    assistant_tool_calls = []
                    for idx in sorted(tool_calls.keys()):
                        tc = tool_calls[idx]
                        assistant_tool_calls.append({
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"],
                            },
                        })

                    llm_messages.append({
                        "role": "assistant",
                        "tool_calls": assistant_tool_calls,
                    })

                    # Execute each tool call
                    for tc_msg in assistant_tool_calls:
                        name = tc_msg["function"]["name"]
                        try:
                            args = json.loads(tc_msg["function"]["arguments"])
                        except json.JSONDecodeError:
                            args = {}

                        logger.info("Executing tool: %s with args: %s", name, tc_msg["function"]["arguments"][:200])

                        yield sse_json({
                            "type": "agent_step",
                            "step": step,
                            "action": "TOOL_CALL",
                            "title": f"Calling {name}\u2026",
                            "content": "",
                        })
                        yield sse_json({"type": "agent_stream", "delta": json.dumps(args, indent=2)})
                        yield sse_json({"type": "agent_step_done"})
                        step += 1

                        result = await execute_tool(name, args)
                        logger.info("Tool %s result length: %d", name, len(result))

                        # Show a preview of the result
                        preview = result[:500] + "\u2026" if len(result) > 500 else result
                        yield sse_json({
                            "type": "agent_step",
                            "step": step,
                            "action": "TOOL_RESULT",
                            "title": f"{name} result",
                            "content": "",
                        })
                        yield sse_json({"type": "agent_stream", "delta": preview})
                        yield sse_json({"type": "agent_step_done"})
                        step += 1

                        llm_messages.append({
                            "role": "tool",
                            "tool_call_id": tc_msg["id"],
                            "content": result,
                        })

                    continue  # Loop back to LLM with tool results

                # No tool calls — we're done
                break

        except Exception:
            logger.exception("Error in chat generate()")
            yield sse_json({"type": "error", "message": "Internal server error — check logs"})

        # Emit token usage
        usage_payload = {}
        if MAX_CONTEXT_TOKENS:
            usage_payload["max_context_tokens"] = MAX_CONTEXT_TOKENS
        if last_usage:
            usage_payload.update({
                "total_tokens": last_usage.total_tokens,
                "prompt_tokens": last_usage.prompt_tokens,
                "completion_tokens": last_usage.completion_tokens,
            })
        yield sse_json({"type": "token_usage", "payload": usage_payload})

        logger.info("Chat completed — tokens: %s", usage_payload)
        yield sse_json({"type": "agent_done"})

    return StreamingResponse(generate(), media_type="text/event-stream")
