import json
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI

from app.tools import TOOLS, execute_tool

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
MAX_AGENT_ITERATIONS = 10

SYSTEM_PROMPT = (
    "You are Plumberito, a development assistant with access to the user's GitHub repositories. "
    "When the user asks about a repository, first use search_repos to find it, then use read_repo "
    "to inspect its contents before answering. Always base your answers on actual repo data."
)


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

    if not messages and body.get("prompt"):
        messages = [{"role": "user", "content": body["prompt"]}]

    llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    async def generate():
        nonlocal llm_messages

        yield sse_json({"type": "agent_start"})

        step = 1
        last_usage = None

        for _ in range(MAX_AGENT_ITERATIONS):
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

        yield sse_json({"type": "agent_done"})

    return StreamingResponse(generate(), media_type="text/event-stream")
