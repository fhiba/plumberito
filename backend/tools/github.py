"""
Thin async wrapper over the GitHub REST API.
Each function maps 1:1 to a single API call — no orchestration here.
"""
import base64
import os
import httpx

_BASE = "https://api.github.com"


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def create_from_template(
    template_owner: str,
    template_repo: str,
    new_owner: str,
    repo_name: str,
    private: bool = True,
) -> dict:
    """POST /repos/{template_owner}/{template_repo}/generate
    Returns the full GitHub repo object."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{_BASE}/repos/{template_owner}/{template_repo}/generate",
            headers=_headers(),
            json={"owner": new_owner, "name": repo_name, "private": private, "include_all_branches": False},
        )
        r.raise_for_status()
        return r.json()


async def push_file(
    repo_full_name: str,
    path: str,
    content: str,
    message: str = "chore: initial scaffold",
) -> None:
    """PUT /repos/{repo}/contents/{path} — creates or updates a file."""
    encoded = base64.b64encode(content.encode()).decode()

    async with httpx.AsyncClient(timeout=20) as client:
        # Fetch existing sha if the file already exists (required for updates)
        sha = None
        check = await client.get(
            f"{_BASE}/repos/{repo_full_name}/contents/{path}",
            headers=_headers(),
        )
        if check.status_code == 200:
            sha = check.json().get("sha")

        payload = {"message": message, "content": encoded}
        if sha:
            payload["sha"] = sha

        r = await client.put(
            f"{_BASE}/repos/{repo_full_name}/contents/{path}",
            headers=_headers(),
            json=payload,
        )
        r.raise_for_status()


async def transfer_repo(repo_full_name: str, new_owner: str) -> dict:
    """POST /repos/{owner}/{repo}/transfers — initiates an ownership transfer.
    The new owner receives an email invitation to accept.
    Returns the repo object with transfer status."""
    owner, repo = repo_full_name.split("/", 1)
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{_BASE}/repos/{owner}/{repo}/transfers",
            headers=_headers(),
            json={"new_owner": new_owner},
        )
        r.raise_for_status()
        return r.json()
