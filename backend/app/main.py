import json
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI

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

MODEL = os.environ.get("LLM_MODEL", "meta-llama/llama-3.1-8b-instruct")
MAX_CONTEXT_TOKENS = None


@app.on_event("startup")
def fetch_model_context_length():
    global MAX_CONTEXT_TOKENS
    try:
        import httpx
        resp = httpx.get(f"https://openrouter.ai/api/v1/models/{MODEL}")
        data = resp.json()
        MAX_CONTEXT_TOKENS = data.get("data", {}).get("context_length")
    except Exception:
        MAX_CONTEXT_TOKENS = None


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

    # Fallback: si mandan solo "prompt", convertir a messages
    if not messages and body.get("prompt"):
        messages = [{"role": "user", "content": body["prompt"]}]

    async def generate():
        yield sse_json({"type": "agent_start"})
        yield sse_json({
            "type": "agent_step",
            "step": 1,
            "action": "LLM_RESPONSE",
            "title": "Generating response\u2026",
            "content": "",
        })

        stream = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield sse_json({"type": "agent_stream", "delta": delta})

        yield sse_json({"type": "agent_step_done"})

        usage_payload = {}
        if MAX_CONTEXT_TOKENS:
            usage_payload["max_context_tokens"] = MAX_CONTEXT_TOKENS
        if hasattr(chunk, "usage") and chunk.usage:
            usage_payload.update({
                "total_tokens": chunk.usage.total_tokens,
                "prompt_tokens": chunk.usage.prompt_tokens,
                "completion_tokens": chunk.usage.completion_tokens,
            })
        yield sse_json({"type": "token_usage", "payload": usage_payload})

        yield sse_json({"type": "agent_done"})

    return StreamingResponse(generate(), media_type="text/event-stream")
