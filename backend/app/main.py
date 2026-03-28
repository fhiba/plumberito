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


def sse(data: str) -> str:
    return f"data: {data}\n\n"


def sse_json(obj: dict) -> str:
    import json
    return sse(json.dumps(obj))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")

    async def generate():
        yield sse_json({"type": "agent_start"})
        yield sse_json({
            "type": "agent_step",
            "step": 1,
            "action": "LLM_RESPONSE",
            "title": "Generating response…",
            "content": "",
        })

        stream = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
            if delta:
                yield sse_json({"type": "agent_stream", "delta": delta})

        yield sse_json({"type": "agent_step_done"})

        if hasattr(chunk, "usage") and chunk.usage:
            yield sse_json({
                "type": "token_usage",
                "payload": {
                    "total_tokens": chunk.usage.total_tokens,
                    "prompt_tokens": chunk.usage.prompt_tokens,
                    "completion_tokens": chunk.usage.completion_tokens,
                },
            })

        yield sse_json({"type": "agent_done"})

    return StreamingResponse(generate(), media_type="text/event-stream")
