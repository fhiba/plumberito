"""
create_project tool — full project setup in one call:
  1. Create GitHub repo from template
  2. Push starter files (template-specific)
  3. Push CI pipeline
  4. Initiate ownership transfer to target user

Exposes:
  CREATE_PROJECT_SCHEMA  — OpenAI-compatible tool definition
  create_project()       — async implementation
"""
import os
from tools import github
from tools.templates import blank as blank_template

_GITHUB_ORG = os.getenv("GITHUB_ORG", "")
_GITHUB_TEMPLATE_REPO = os.getenv("GITHUB_TEMPLATE_REPO", "")  # "owner/repo"

TEMPLATES = {
    "blank": blank_template,
}

CREATE_PROJECT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_project",
        "description": (
            "Creates a complete project repository from a template. "
            "Generates starter code, sets up a CI pipeline, and initiates "
            "an ownership transfer to the target GitHub user."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "repo_name": {
                    "type": "string",
                    "description": "Repository name in lowercase kebab-case (e.g. 'my-todo-app').",
                },
                "target_owner": {
                    "type": "string",
                    "description": "GitHub username of the person who will own the repository.",
                },
                "template": {
                    "type": "string",
                    "enum": ["blank"],
                    "description": "Template to use. 'blank' creates a minimal HTML/CSS/JS scaffold.",
                },
                "description": {
                    "type": "string",
                    "description": "Short one-line description of the project.",
                },
            },
            "required": ["repo_name", "target_owner", "template"],
        },
    },
}


async def create_project(
    repo_name: str,
    target_owner: str,
    template: str = "blank",
    description: str = "",
) -> dict:
    """
    Full project setup flow.

    Returns:
        {
            "repo_name": str,
            "full_name": str,           # org/repo-name
            "html_url": str,
            "files_pushed": int,
            "transfer_initiated": bool,
        }

    Raises:
        ValueError: unknown template or bad GITHUB_TEMPLATE_REPO config.
        httpx.HTTPStatusError: on any GitHub API failure.
    """
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template '{template}'. Available: {list(TEMPLATES)}")

    if "/" not in _GITHUB_TEMPLATE_REPO:
        raise ValueError(
            f"GITHUB_TEMPLATE_REPO must be 'owner/repo', got: '{_GITHUB_TEMPLATE_REPO}'"
        )

    template_owner, template_repo = _GITHUB_TEMPLATE_REPO.split("/", 1)

    # 1. Create repo from template under the org
    repo_data = await github.create_from_template(
        template_owner=template_owner,
        template_repo=template_repo,
        new_owner=_GITHUB_ORG,
        repo_name=repo_name,
    )
    full_name = repo_data["full_name"]

    # 2. Push template-specific files + CI
    files = TEMPLATES[template].get_files(repo_name, description)
    for f in files:
        await github.push_file(full_name, f["path"], f["content"])

    # 3. Initiate ownership transfer
    await github.transfer_repo(full_name, target_owner)

    return {
        "repo_name": repo_name,
        "full_name": full_name,
        "html_url": repo_data["html_url"],
        "files_pushed": len(files),
        "transfer_initiated": True,
    }
