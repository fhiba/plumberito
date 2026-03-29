import hashlib
import hmac
import json
import logging
import os
import time

import httpx
from fastapi import APIRouter, Request, Response
from openai import OpenAI

router = APIRouter(prefix="/webhooks")

logger = logging.getLogger("plumberito")

SENTRY_WEBHOOK_SECRET = os.environ.get("SENTRY_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
WEBHOOK_LLM_MODEL = os.environ.get("WEBHOOK_LLM_MODEL", "deepseek/deepseek-chat")

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


def _analyze_error_with_llm(error_title: str, error_detail: str, repo_context: str) -> dict:
    """Use LLM to analyze the error and generate a fix.

    Returns dict with:
      - analysis: markdown string with root cause analysis
      - files: dict {path: content} with fixed files (empty if no fix possible)
    """
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    response = client.chat.completions.create(
        model=WEBHOOK_LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior developer diagnosing a production error. "
                    "You must respond with a JSON object containing:\n"
                    '- "analysis": a brief markdown root cause analysis\n'
                    '- "files": an object mapping file paths to their full corrected content. '
                    "Only include files you are confident need changes. "
                    "If you cannot produce a concrete fix, set files to an empty object {}.\n\n"
                    "Respond ONLY with valid JSON, no markdown fences."
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
        max_tokens=4000,
    )

    raw = response.choices[0].message.content or "{}"
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON response, treating as analysis only")
        result = {"analysis": raw, "files": {}}

    return {
        "analysis": result.get("analysis", "Could not analyze error."),
        "files": result.get("files", {}),
    }


def _create_fix_pr(
    repo_full_name: str,
    title: str,
    body: str,
    files: dict[str, str],
    default_branch: str,
) -> str | None:
    """Create a branch, commit the fix, and open a PR. Returns PR URL or None."""
    from app.tools import _commit_files

    api = f"https://api.github.com/repos/{repo_full_name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    # Get head SHA of default branch
    ref_resp = httpx.get(f"{api}/git/ref/heads/{default_branch}", headers=headers)
    if ref_resp.status_code >= 400:
        logger.error("Failed to get default branch ref: %s", ref_resp.text)
        return None
    head_sha = ref_resp.json()["object"]["sha"]

    # Create fix branch
    branch_name = f"fix/sentry-{int(time.time())}"
    create_ref_resp = httpx.post(
        f"{api}/git/refs",
        headers=headers,
        json={"ref": f"refs/heads/{branch_name}", "sha": head_sha},
    )
    if create_ref_resp.status_code >= 400:
        logger.error("Failed to create branch: %s", create_ref_resp.text)
        return None

    # Commit files to the new branch
    success, err = _commit_files(repo_full_name, files, f"fix: {title}", branch_name, headers)
    if not success:
        logger.error("Failed to commit fix: %s", err)
        return None

    # Create PR
    pr_resp = httpx.post(
        f"{api}/pulls",
        headers=headers,
        json={
            "title": title,
            "body": body,
            "head": branch_name,
            "base": default_branch,
        },
    )
    if pr_resp.status_code >= 400:
        logger.error("Failed to create PR (%d): %s", pr_resp.status_code, pr_resp.text)
        return None

    pr_url = pr_resp.json().get("html_url")
    logger.info("Created fix PR: %s", pr_url)
    return pr_url


def _create_github_issue(repo_full_name: str, title: str, body: str):
    """Fallback: create a GitHub issue when no code fix is possible."""
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

    # Get repo context — first read tree, then read source files (not just config)
    from app.tools import _read_repo
    repo_context_raw = _read_repo(repo_full_name)
    repo_context = json.loads(repo_context_raw)

    # Read actual source code files so the LLM can generate fixes
    SOURCE_EXTS = {".js", ".jsx", ".ts", ".tsx", ".py", ".vue", ".svelte", ".go", ".rs"}
    source_paths = [
        p for p in repo_context.get("tree", [])
        if any(p.endswith(ext) for ext in SOURCE_EXTS)
        and "/node_modules/" not in p
        and "/dist/" not in p
        and "/.next/" not in p
        and "/build/" not in p
    ]
    if source_paths:
        repo_with_source = _read_repo(repo_full_name, paths=source_paths)
    else:
        repo_with_source = repo_context_raw

    # Analyze with LLM and generate fix
    logger.info("Analyzing Sentry error for %s: %s", repo_full_name, error_title)
    llm_result = _analyze_error_with_llm(error_title, error_detail, repo_with_source[:8000])

    analysis = llm_result["analysis"]
    fix_files = llm_result["files"]

    pr_body = (
        f"## Production Error (Sentry)\n\n"
        f"**Error:** {error_title}\n\n"
        f"**Details:**\n```\n{error_detail[:1000]}\n```\n\n"
        f"## Analysis\n\n{analysis}\n\n"
        f"---\n"
        f"*Automatically created by Plumberito from Sentry alert*"
    )

    if fix_files:
        pr_url = _create_fix_pr(
            repo_full_name,
            f"[Sentry Fix] {error_title[:100]}",
            pr_body,
            fix_files,
            repo_context["default_branch"],
        )
        if pr_url:
            return {"status": "ok", "repo": repo_full_name, "pr_created": True, "pr_url": pr_url}
        logger.warning("PR creation failed, falling back to issue")

    # Fallback: create issue if no fix or PR creation failed
    _create_github_issue(
        repo_full_name,
        f"[Sentry] {error_title[:100]}",
        pr_body,
    )

    return {"status": "ok", "repo": repo_full_name, "issue_created": True}
