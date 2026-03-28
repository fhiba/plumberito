import asyncio
import json
import logging
import os
from base64 import b64decode, b64encode

from github import Github
import httpx
from nacl import encoding, public

from app.infra import _provision_infrastructure, _destroy_infrastructure

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_ORG = os.environ.get("GITHUB_ORG", "")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "")
GCP_PROJECT_NUMBER = os.environ.get("GCP_PROJECT_NUMBER", "")
WIF_PROVIDER = os.environ.get("WIF_PROVIDER", "")  # projects/NUM/locations/global/workloadIdentityPools/github/providers/github-actions
FIREBASE_SA_EMAIL = os.environ.get("FIREBASE_SA_EMAIL", "")  # firebase-deployer@PROJECT.iam.gserviceaccount.com
SENTRY_AUTH_TOKEN = os.environ.get("SENTRY_AUTH_TOKEN", "")
SENTRY_ORG = os.environ.get("SENTRY_ORG", "plumberito")
SENTRY_TEAM = os.environ.get("SENTRY_TEAM", "projects")

logger = logging.getLogger("plumberito")


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
                    "is_template": {
                        "type": "boolean",
                        "description": "If true, only return repos marked as GitHub template repositories. Default: false",
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
            "description": "Create a repository in the user's GitHub account from a template repo. The repo is created directly under the user's account — no transfer needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Repository name in lowercase kebab-case (e.g. 'my-todo-app')",
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
                "required": ["repo_name", "template_repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_deploy",
            "description": "Configure automatic deployment for a frontend repository. Creates a Firebase Hosting site, updates the deploy workflow in the repo, and sets up GitHub secrets. Call this after create_repo when the user wants their frontend deployed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_full_name": {
                        "type": "string",
                        "description": "Full repository name in owner/repo format",
                    },
                    "site_id": {
                        "type": "string",
                        "description": "Firebase Hosting site ID (lowercase, hyphens). Use the repo name.",
                    },
                },
                "required": ["repo_full_name", "site_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "provision_infrastructure",
            "description": "Provision GCP infrastructure using Pulumi. Creates or updates a stack of resources. Returns outputs (URLs, resource names) when complete. This operation may take 30-120 seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Short kebab-case name for the project (e.g. 'my-landing-page'). Used as Pulumi project and stack identifier.",
                    },
                    "resources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["cloud_run_service", "cloud_storage_bucket"],
                                    "description": "The type of GCP resource to create.",
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Resource name (lowercase, hyphens allowed).",
                                },
                                "config": {
                                    "type": "object",
                                    "description": "Resource-specific configuration. For cloud_run_service: {image, port, env_vars, memory, cpu, allow_unauthenticated}. For cloud_storage_bucket: {location}.",
                                },
                            },
                            "required": ["type", "name"],
                        },
                        "description": "List of GCP resources to provision.",
                    },
                },
                "required": ["project_name", "resources"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "destroy_infrastructure",
            "description": "Destroy all infrastructure in a previously provisioned Pulumi stack. Use this to clean up resources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "The project name used when provisioning (same as the Pulumi stack identifier).",
                    },
                },
                "required": ["project_name"],
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
    is_template: bool = False,
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
        if is_template and not repo.is_template:
            continue
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
    template_repo: str,
    description: str = "",
    user_token: str | None = None,
) -> str:
    if "/" not in template_repo:
        return json.dumps({"error": f"template_repo must be 'owner/repo', got: '{template_repo}'"})

    template_owner, template_repo_name = template_repo.split("/", 1)
    token = user_token or GITHUB_TOKEN

    import httpx

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    # Resolve the owner for the new repo (user's account if using their token)
    if user_token:
        user_resp = httpx.get("https://api.github.com/user", headers=headers)
        if user_resp.status_code >= 400:
            return json.dumps({"error": f"Failed to get GitHub user info: {user_resp.text}"})
        owner = user_resp.json()["login"]
    else:
        owner = GITHUB_ORG

    resp = httpx.post(
        f"https://api.github.com/repos/{template_owner}/{template_repo_name}/generate",
        headers=headers,
        json={
            "owner": owner,
            "name": repo_name,
            "description": description,
            "private": True,
            "include_all_branches": False,
        },
    )
    if resp.status_code >= 400:
        import logging
        logging.getLogger("plumberito").error("create_repo failed (%d): %s", resp.status_code, resp.text)
        return json.dumps({"error": f"GitHub API error {resp.status_code}: {resp.text}"})

    repo_data = resp.json()

    return json.dumps({
        "repo_name": repo_name,
        "full_name": repo_data["full_name"],
        "html_url": repo_data["html_url"],
        "owner": owner,
    })


def _get_gcp_access_token() -> str:
    """Get a GCP access token using Application Default Credentials."""
    import google.auth
    import google.auth.transport.requests

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/firebase"],
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


def _encrypt_secret(public_key: str, secret_value: str) -> str:
    """Encrypt a secret value using the repo's public key (for GitHub Actions secrets)."""
    pk = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(pk)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


def _set_github_secret(repo_full_name: str, secret_name: str, secret_value: str, token: str):
    """Create or update a GitHub Actions secret in a repo."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    # Get the repo's public key for secret encryption
    pk_resp = httpx.get(
        f"https://api.github.com/repos/{repo_full_name}/actions/secrets/public-key",
        headers=headers,
    )
    if pk_resp.status_code >= 400:
        raise RuntimeError(f"Failed to get public key: {pk_resp.text}")

    pk_data = pk_resp.json()
    encrypted_value = _encrypt_secret(pk_data["key"], secret_value)

    # Set the secret
    resp = httpx.put(
        f"https://api.github.com/repos/{repo_full_name}/actions/secrets/{secret_name}",
        headers=headers,
        json={
            "encrypted_value": encrypted_value,
            "key_id": pk_data["key_id"],
        },
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Failed to set secret {secret_name}: {resp.text}")


DEPLOY_WORKFLOW = """\
name: Deploy

on:
  push:
    branches: [{default_branch}]
  workflow_dispatch:

permissions:
  contents: read
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: latest

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm

      - run: pnpm install --frozen-lockfile
      - run: pnpm build
        env:
          VITE_SENTRY_DSN: ${{{{ secrets.SENTRY_DSN }}}}

      - uses: google-github-actions/auth@v3
        id: auth
        with:
          project_id: {project_id}
          workload_identity_provider: {wif_provider}
          service_account: {service_account}

      - run: npx firebase-tools@latest deploy --only hosting:{site_id} --project {project_id} --non-interactive --json
        env:
          GOOGLE_APPLICATION_CREDENTIALS: ${{{{ steps.auth.outputs.credentials_file_path }}}}
"""

FIREBASE_JSON_TEMPLATE = """\
{{
  "hosting": {{
    "site": "{site_id}",
    "public": "dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {{
        "source": "**",
        "destination": "/index.html"
      }}
    ]
  }}
}}
"""

FIREBASERC_TEMPLATE = """\
{{
  "projects": {{
    "default": "{project_id}"
  }}
}}
"""


def _commit_files(
    repo_full_name: str,
    files: dict[str, str],
    message: str,
    branch: str,
    headers: dict,
) -> tuple[bool, str]:
    """Create a single commit with multiple files using the Git Trees API.
    files: {path: content} mapping.
    Returns (success, error_msg).
    """
    api = f"https://api.github.com/repos/{repo_full_name}"

    # Get the SHA of the branch head
    ref_resp = httpx.get(f"{api}/git/ref/heads/{branch}", headers=headers)
    if ref_resp.status_code >= 400:
        return False, f"Failed to get branch ref: {ref_resp.text}"
    head_sha = ref_resp.json()["object"]["sha"]

    # Create blobs for each file
    tree_items = []
    for path, content in files.items():
        blob_resp = httpx.post(
            f"{api}/git/blobs",
            headers=headers,
            json={"content": content, "encoding": "utf-8"},
        )
        if blob_resp.status_code >= 400:
            return False, f"Failed to create blob for {path}: {blob_resp.text}"
        tree_items.append({
            "path": path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_resp.json()["sha"],
        })

    # Create tree
    tree_resp = httpx.post(
        f"{api}/git/trees",
        headers=headers,
        json={"base_tree": head_sha, "tree": tree_items},
    )
    if tree_resp.status_code >= 400:
        return False, f"Failed to create tree: {tree_resp.text}"

    # Create commit
    commit_resp = httpx.post(
        f"{api}/git/commits",
        headers=headers,
        json={
            "message": message,
            "tree": tree_resp.json()["sha"],
            "parents": [head_sha],
        },
    )
    if commit_resp.status_code >= 400:
        return False, f"Failed to create commit: {commit_resp.text}"

    # Update branch ref
    update_resp = httpx.patch(
        f"{api}/git/refs/heads/{branch}",
        headers=headers,
        json={"sha": commit_resp.json()["sha"]},
    )
    if update_resp.status_code >= 400:
        return False, f"Failed to update ref: {update_resp.text}"

    return True, ""


DEPLOY_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "deploy_registry.json")


def _load_deploy_registry() -> dict:
    try:
        with open(DEPLOY_REGISTRY_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_deploy_registry(registry: dict):
    os.makedirs(os.path.dirname(DEPLOY_REGISTRY_PATH), exist_ok=True)
    with open(DEPLOY_REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)


def _create_sentry_project(site_id: str) -> str | None:
    """Create a Sentry project and return the public DSN."""
    sentry_headers = {
        "Authorization": f"Bearer {SENTRY_AUTH_TOKEN}",
        "Content-Type": "application/json",
    }

    # Create project
    resp = httpx.post(
        f"https://sentry.io/api/0/teams/{SENTRY_ORG}/{SENTRY_TEAM}/projects/",
        headers=sentry_headers,
        json={"name": site_id, "platform": "javascript"},
    )
    if resp.status_code >= 400 and "already exists" not in resp.text.lower():
        logger.error("Sentry project creation failed (%d): %s", resp.status_code, resp.text)
        return None

    # Get DSN
    keys_resp = httpx.get(
        f"https://sentry.io/api/0/projects/{SENTRY_ORG}/{site_id}/keys/",
        headers=sentry_headers,
    )
    if keys_resp.status_code >= 400:
        logger.error("Sentry keys fetch failed (%d): %s", keys_resp.status_code, keys_resp.text)
        return None

    keys = keys_resp.json()
    if keys:
        return keys[0].get("dsn", {}).get("public")
    return None


def _create_sentry_alert_rule(site_id: str):
    """Create an alert rule that triggers on new issues."""
    sentry_headers = {
        "Authorization": f"Bearer {SENTRY_AUTH_TOKEN}",
        "Content-Type": "application/json",
    }
    httpx.post(
        f"https://sentry.io/api/0/projects/{SENTRY_ORG}/{site_id}/rules/",
        headers=sentry_headers,
        json={
            "name": "Notify on new issue",
            "actionMatch": "any",
            "filterMatch": "all",
            "frequency": 30,
            "conditions": [
                {"id": "sentry.rules.conditions.first_seen_event.FirstSeenEventCondition"}
            ],
            "actions": [
                {
                    "id": "sentry.rules.actions.notify_event.NotifyEventAction",
                }
            ],
        },
    )


def _grant_wif_access(repo_full_name: str):
    """Add a repo to the WIF IAM binding on the Firebase SA (read-modify-write)."""
    import google.auth
    import google.auth.transport.requests

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    credentials.refresh(google.auth.transport.requests.Request())
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }
    sa_resource = f"projects/{GCP_PROJECT}/serviceAccounts/{FIREBASE_SA_EMAIL}"
    role = "roles/iam.workloadIdentityUser"
    member = (
        f"principalSet://iam.googleapis.com/"
        f"projects/{GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/"
        f"attribute.repository/{repo_full_name}"
    )

    # Get current policy
    get_resp = httpx.post(
        f"https://iam.googleapis.com/v1/{sa_resource}:getIamPolicy",
        headers=headers,
        json={"options": {"requestedPolicyVersion": 3}},
    )
    get_resp.raise_for_status()
    policy = get_resp.json()

    # Find or create the WIF binding
    bindings = policy.get("bindings", [])
    wif_binding = next((b for b in bindings if b["role"] == role), None)
    if wif_binding:
        if member in wif_binding["members"]:
            logger.info("WIF binding already exists for %s", repo_full_name)
            return
        wif_binding["members"].append(member)
    else:
        bindings.append({"role": role, "members": [member]})
        policy["bindings"] = bindings

    # Set updated policy
    set_resp = httpx.post(
        f"https://iam.googleapis.com/v1/{sa_resource}:setIamPolicy",
        headers=headers,
        json={"policy": policy},
    )
    set_resp.raise_for_status()
    logger.info("Granted WIF access for %s", repo_full_name)


def _setup_deploy(
    repo_full_name: str,
    site_id: str,
    user_token: str | None = None,
) -> str:
    token = user_token or GITHUB_TOKEN
    steps = []

    # 0. Get repo's default branch
    gh_headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    repo_resp = httpx.get(f"https://api.github.com/repos/{repo_full_name}", headers=gh_headers)
    default_branch = "main"
    if repo_resp.status_code == 200:
        default_branch = repo_resp.json().get("default_branch", "main")

    # 1. Create Firebase Hosting site
    try:
        gcp_token = _get_gcp_access_token()
        site_resp = httpx.post(
            f"https://firebasehosting.googleapis.com/v1beta1/projects/{GCP_PROJECT}/sites",
            headers={
                "Authorization": f"Bearer {gcp_token}",
                "Content-Type": "application/json",
            },
            params={"siteId": site_id},
            json={},
        )
        if site_resp.status_code < 300:
            site_url = f"https://{site_id}.web.app"
            steps.append({"step": "create_site", "status": "success", "url": site_url})
        elif "already exists" in site_resp.text.lower():
            site_url = f"https://{site_id}.web.app"
            steps.append({"step": "create_site", "status": "already_exists", "url": site_url})
        else:
            logger.error("Firebase site creation failed (%d): %s", site_resp.status_code, site_resp.text)
            return json.dumps({"error": f"Failed to create Firebase site: {site_resp.text}"})
    except Exception as e:
        logger.error("Firebase site creation error: %s", e)
        return json.dumps({"error": f"Failed to create Firebase site: {e}"})

    # 2. Update deploy.yml in the repo
    import time
    try:
        # Wait for repo to have content (template population is async)
        for attempt in range(10):
            check = httpx.get(
                f"https://api.github.com/repos/{repo_full_name}/contents/",
                headers=gh_headers,
            )
            if check.status_code == 200:
                break
            logger.info("Repo not populated yet, waiting 3s... (attempt %d/10)", attempt + 1)
            time.sleep(3)
        else:
            return json.dumps({"error": "Repo template population timed out after 30s"})

        # Create/update firebase.json, .firebaserc, and deploy workflow in a single commit
        firebase_json = FIREBASE_JSON_TEMPLATE.format(site_id=site_id)
        firebaserc = FIREBASERC_TEMPLATE.format(project_id=GCP_PROJECT)
        workflow_content = DEPLOY_WORKFLOW.format(
            project_id=GCP_PROJECT,
            site_id=site_id,
            wif_provider=WIF_PROVIDER,
            service_account=FIREBASE_SA_EMAIL,
            default_branch=default_branch,
        )

        ok, err = _commit_files(
            repo_full_name,
            {
                "firebase.json": firebase_json,
                ".firebaserc": firebaserc,
                ".github/workflows/deploy.yml": workflow_content,
            },
            "ci: configure Firebase Hosting deploy",
            default_branch,
            gh_headers,
        )
        if ok:
            steps.append({"step": "configure_firebase_deploy", "status": "success"})
        else:
            logger.error("Firebase deploy config failed: %s", err)
            return json.dumps({"error": f"Failed to configure Firebase deploy: {err}"})
    except Exception as e:
        logger.error("Workflow update error: %s", e)
        return json.dumps({"error": f"Failed to update deploy workflow: {e}"})

    # 3. Grant WIF access for this repo to the Firebase SA
    try:
        _grant_wif_access(repo_full_name)
        steps.append({"step": "grant_wif_access", "status": "success"})
    except Exception as e:
        logger.error("WIF IAM binding error: %s", e)
        return json.dumps({"error": f"Failed to grant WIF access: {e}"})

    # 4. Create Sentry project and set DSN
    sentry_dsn = None
    if SENTRY_AUTH_TOKEN:
        try:
            sentry_dsn = _create_sentry_project(site_id)
            if sentry_dsn:
                _set_github_secret(repo_full_name, "SENTRY_DSN", sentry_dsn, token)
                _create_sentry_alert_rule(site_id)
                steps.append({"step": "setup_sentry", "status": "success", "dsn": sentry_dsn})
            else:
                steps.append({"step": "setup_sentry", "status": "skipped", "reason": "Could not get DSN"})
        except Exception as e:
            logger.error("Sentry setup error: %s", e)
            steps.append({"step": "setup_sentry", "status": "error", "reason": str(e)})

    # 5. Save deploy registry
    try:
        registry = _load_deploy_registry()
        registry[site_id] = {
            "repo": repo_full_name,
            "site_url": site_url,
            "sentry_dsn": sentry_dsn,
        }
        _save_deploy_registry(registry)
        steps.append({"step": "save_registry", "status": "success"})
    except Exception as e:
        logger.error("Deploy registry save error: %s", e)

    # 6. Trigger first deploy
    try:
        dispatch_resp = httpx.post(
            f"https://api.github.com/repos/{repo_full_name}/actions/workflows/deploy.yml/dispatches",
            headers=gh_headers,
            json={"ref": default_branch},
        )
        if dispatch_resp.status_code < 300:
            steps.append({"step": "trigger_first_deploy", "status": "success"})
        else:
            logger.error("Workflow dispatch failed (%d): %s", dispatch_resp.status_code, dispatch_resp.text)
            steps.append({"step": "trigger_first_deploy", "status": "error", "reason": dispatch_resp.text})
    except Exception as e:
        logger.error("Workflow dispatch error: %s", e)
        steps.append({"step": "trigger_first_deploy", "status": "error", "reason": str(e)})

    return json.dumps({
        "status": "success",
        "site_url": site_url,
        "steps": steps,
        "message": f"Deploy configured and first deploy triggered. Every push to main will deploy to {site_url}. Errors are tracked via Sentry.",
    })


TOOL_DISPATCH = {
    "search_repos": _search_repos,
    "read_repo": _read_repo,
    "create_repo": _create_repo,
    "setup_deploy": _setup_deploy,
    "provision_infrastructure": _provision_infrastructure,
    "destroy_infrastructure": _destroy_infrastructure,
}

# Tools that receive the user's GitHub token
_USER_TOKEN_TOOLS = {"create_repo", "setup_deploy"}


async def execute_tool(name: str, arguments: dict, github_token: str | None = None) -> str:
    fn = TOOL_DISPATCH.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    if github_token and name in _USER_TOKEN_TOOLS:
        arguments["user_token"] = github_token
    return await asyncio.to_thread(fn, **arguments)
