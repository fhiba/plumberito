import asyncio
import json
import os
from base64 import b64decode

from github import Github

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_ORG = os.environ.get("GITHUB_ORG", "")


NOISE_DIRS = {"node_modules", ".venv", "__pycache__", "dist", "build", ".next", ".git", ".tox", "venv", "env"}

STACK_FILES = {
    "package.json", "requirements.txt", "pyproject.toml", "Cargo.toml",
    "go.mod", "Gemfile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "tsconfig.json", "pom.xml", "build.gradle",
}

MAX_FILE_SIZE = 10_000
MAX_TOTAL_SIZE = 30_000

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_repos",
            "description": "Search the authenticated GitHub user's repositories. All filters are optional — omit everything to list all repos. Supports pagination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Filter by repository name (substring match, case-insensitive)",
                    },
                    "owner": {
                        "type": "string",
                        "description": "Filter by owner/creator username (substring match, case-insensitive)",
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by primary language (e.g. 'Python', 'TypeScript')",
                    },
                    "sort": {
                        "type": "string",
                        "enum": ["updated", "created", "name"],
                        "description": "Sort order. Default: updated",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-based). Default: 1",
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "Results per page (max 50). Default: 20",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_repo",
            "description": "Read a GitHub repository's file tree and optionally specific file contents. Without paths, returns the tree plus contents of common stack-indicator files (package.json, requirements.txt, Dockerfile, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_full_name": {
                        "type": "string",
                        "description": "Full repository name in owner/repo format",
                    },
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific file paths to read. If omitted, reads common config/stack files automatically.",
                    },
                },
                "required": ["repo_full_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_repo",
            "description": "Create a repository from a GitHub template repo. Copies all files from the template, then initiates ownership transfer to the target user. Use search_repos to find available templates in the org first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Repository name in lowercase kebab-case (e.g. 'my-todo-app')",
                    },
                    "target_owner": {
                        "type": "string",
                        "description": "GitHub username who will own the repository",
                    },
                    "template_repo": {
                        "type": "string",
                        "description": "Full name of the template repo in owner/repo format (e.g. 'my-org/blank-template')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Short one-line description of the project",
                    },
                },
                "required": ["repo_name", "target_owner", "template_repo"],
            },
        },
    },
]


def _get_github():
    return Github(GITHUB_TOKEN)


def _search_repos(
    name: str = "",
    owner: str = "",
    language: str = "",
    sort: str = "updated",
    page: int = 1,
    per_page: int = 20,
) -> str:
    g = _get_github()
    per_page = min(per_page, 50)
    name_lower = name.lower()
    owner_lower = owner.lower()
    language_lower = language.lower()

    matched = []
    for repo in g.get_user().get_repos(sort=sort if sort != "name" else "full_name"):
        if name_lower and name_lower not in repo.name.lower():
            continue
        if owner_lower and owner_lower not in (repo.owner.login or "").lower():
            continue
        if language_lower and language_lower != (repo.language or "").lower():
            continue
        matched.append({
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description or "",
            "language": repo.language or "",
            "default_branch": repo.default_branch,
            "updated_at": repo.updated_at.isoformat() if repo.updated_at else "",
            "private": repo.private,
        })

    # Sort by name locally if requested (GitHub API doesn't support name sort)
    if sort == "name":
        matched.sort(key=lambda r: r["name"].lower())

    # Paginate
    start = (page - 1) * per_page
    page_results = matched[start:start + per_page]

    return json.dumps({
        "results": page_results,
        "total": len(matched),
        "page": page,
        "per_page": per_page,
        "has_more": start + per_page < len(matched),
    })


def _is_noise(path: str) -> bool:
    parts = path.split("/")
    return any(p in NOISE_DIRS for p in parts)


def _read_file_content(repo, path: str) -> str | None:
    try:
        content = repo.get_contents(path)
        if content.encoding == "base64" and content.content:
            text = b64decode(content.content).decode("utf-8", errors="replace")
            if len(text) > MAX_FILE_SIZE:
                return text[:MAX_FILE_SIZE] + "\n[truncated]"
            return text
        return None
    except Exception:
        return None


def _read_repo(repo_full_name: str, paths: list[str] | None = None) -> str:
    g = _get_github()
    repo = g.get_repo(repo_full_name)

    tree = repo.get_git_tree(sha=repo.default_branch, recursive=True)
    tree_paths = [item.path for item in tree.tree if item.type == "blob" and not _is_noise(item.path)]

    if len(tree_paths) > 500:
        tree_paths = tree_paths[:500]
        tree_truncated = True
    else:
        tree_truncated = False

    files_to_read = []
    if paths:
        files_to_read = paths
    else:
        for p in tree_paths:
            filename = p.split("/")[-1]
            if filename in STACK_FILES:
                files_to_read.append(p)
            if filename == "README.md" and p.count("/") == 0:
                files_to_read.append(p)

    file_contents = {}
    total_size = 0
    for p in files_to_read:
        if total_size >= MAX_TOTAL_SIZE:
            break
        content = _read_file_content(repo, p)
        if content is not None:
            file_contents[p] = content
            total_size += len(content)

    result = {
        "repo": repo_full_name,
        "default_branch": repo.default_branch,
        "description": repo.description or "",
        "language": repo.language or "",
        "tree": tree_paths,
        "tree_truncated": tree_truncated,
        "files": file_contents,
    }
    return json.dumps(result)


def _create_repo(
    repo_name: str,
    target_owner: str,
    template_repo: str,
    description: str = "",
) -> str:
    if "/" not in template_repo:
        return json.dumps({"error": f"template_repo must be 'owner/repo', got: '{template_repo}'"})

    template_owner, template_repo_name = template_repo.split("/", 1)

    import httpx

    # 1. Create repo from template (copies all files automatically)
    resp = httpx.post(
        f"https://api.github.com/repos/{template_owner}/{template_repo_name}/generate",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "owner": GITHUB_ORG,
            "name": repo_name,
            "description": description,
            "private": True,
            "include_all_branches": False,
        },
    )
    resp.raise_for_status()
    repo_data = resp.json()
    full_name = repo_data["full_name"]

    # 2. Initiate ownership transfer
    transfer_resp = httpx.post(
        f"https://api.github.com/repos/{full_name}/transfer",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        json={"new_owner": target_owner},
    )
    transfer_initiated = transfer_resp.status_code < 300

    return json.dumps({
        "repo_name": repo_name,
        "full_name": full_name,
        "html_url": repo_data["html_url"],
        "transfer_initiated": transfer_initiated,
    })


TOOL_DISPATCH = {
    "search_repos": _search_repos,
    "read_repo": _read_repo,
    "create_repo": _create_repo,
}


async def execute_tool(name: str, arguments: dict) -> str:
    fn = TOOL_DISPATCH.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    return await asyncio.to_thread(fn, **arguments)
