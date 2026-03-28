import hashlib
import hmac
import json
import logging
import os

import httpx
from fastapi import APIRouter, Request, Response
from openai import OpenAI

router = APIRouter(prefix="/webhooks")

logger = logging.getLogger("plumberito")

SENTRY_WEBHOOK_SECRET = os.environ.get("SENTRY_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen/qwen3.5-flash-02-23")

DEPLOY_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "deploy_registry.json")


def _load_deploy_registry() -> dict:
    try:
        with open(DEPLOY_REGISTRY_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _verify_sentry_signature(body: bytes, signature: str) -> bool:
    if not SENTRY_WEBHOOK_SECRET:
        return True
    expected = hmac.new(
        SENTRY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _analyze_error_with_llm(error_title: str, error_detail: str, repo_context: str) -> str:
    """Use LLM to analyze the error and suggest a fix."""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior developer diagnosing a production error. "
                    "Analyze the error and provide: "
                    "1. A brief root cause analysis "
                    "2. The likely file(s) and line(s) involved "
                    "3. A suggested fix "
                    "Be concise and actionable. Write in markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## Error\n{error_title}\n\n"
                    f"## Details\n{error_detail}\n\n"
                    f"## Repository Context\n{repo_context}"
                ),
            },
        ],
        max_tokens=1000,
    )

    return response.choices[0].message.content or "Could not analyze error."


def _create_github_issue(repo_full_name: str, title: str, body: str):
    """Create a GitHub issue in the repo."""
    resp = httpx.post(
        f"https://api.github.com/repos/{repo_full_name}/issues",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "title": title,
            "body": body,
            "labels": ["bug", "sentry"],
        },
    )
    if resp.status_code >= 400:
        logger.error("Failed to create GitHub issue (%d): %s", resp.status_code, resp.text)
    else:
        logger.info("Created GitHub issue: %s", resp.json().get("html_url"))


@router.post("/sentry")
async def sentry_webhook(request: Request):
    body = await request.body()

    # Verify signature
    signature = request.headers.get("sentry-hook-signature", "")
    if not _verify_sentry_signature(body, signature):
        return Response(status_code=401)

    resource = request.headers.get("sentry-hook-resource", "")
    if resource not in ("issue", "event_alert"):
        return {"status": "ignored", "reason": f"resource type '{resource}' not handled"}

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return Response(status_code=400)

    # Extract error info from the payload
    if resource == "event_alert":
        event = payload.get("data", {}).get("event", {})
        error_title = event.get("title", "Unknown error")
        error_detail = event.get("message", "") or json.dumps(event.get("exception", {}), indent=2)[:2000]
        project_slug = payload.get("data", {}).get("triggered_rule", {}).get("project_slug", "")
    else:
        issue_data = payload.get("data", {}).get("issue", payload.get("data", {}))
        error_title = issue_data.get("title", "Unknown error")
        error_detail = issue_data.get("culprit", "") or issue_data.get("message", "")
        project_slug = issue_data.get("project", {}).get("slug", "")

    if not project_slug:
        logger.warning("Sentry webhook missing project slug")
        return {"status": "ignored", "reason": "no project slug"}

    # Look up repo from deploy registry
    registry = _load_deploy_registry()
    deploy_info = registry.get(project_slug)

    if not deploy_info:
        logger.warning("No deploy registry entry for project: %s", project_slug)
        return {"status": "ignored", "reason": f"project '{project_slug}' not in registry"}

    repo_full_name = deploy_info["repo"]

    # Get repo context for LLM analysis
    from app.tools import _read_repo
    repo_context = _read_repo(repo_full_name)

    # Analyze with LLM
    logger.info("Analyzing Sentry error for %s: %s", repo_full_name, error_title)
    analysis = _analyze_error_with_llm(error_title, error_detail, repo_context[:5000])

    # Create GitHub issue
    issue_body = (
        f"## Production Error (Sentry)\n\n"
        f"**Error:** {error_title}\n\n"
        f"**Details:**\n```\n{error_detail[:1000]}\n```\n\n"
        f"## Analysis\n\n{analysis}\n\n"
        f"---\n"
        f"*Automatically created by Plumberito from Sentry alert*"
    )

    _create_github_issue(
        repo_full_name,
        f"[Sentry] {error_title[:100]}",
        issue_body,
    )

    return {"status": "ok", "repo": repo_full_name, "issue_created": True}
