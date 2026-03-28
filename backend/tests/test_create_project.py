"""
Integration tests for create_project() — all HTTP mocked via respx.
Tests cover the full flow: create repo → push files → transfer ownership.
"""
import json
import pytest
import respx
import httpx

from tools.create_project import create_project
from tests.conftest import FAKE_REPO, FAKE_TRANSFER

_BASE = "https://api.github.com"
_TEMPLATE_URL = f"{_BASE}/repos/plumberito-org/blank-web/generate"
_TRANSFER_URL = f"{_BASE}/repos/plumberito-org/my-app/transfers"


def _contents_get_url(path: str) -> str:
    return f"{_BASE}/repos/plumberito-org/my-app/contents/{path}"


def _contents_put_url(path: str) -> str:
    return f"{_BASE}/repos/plumberito-org/my-app/contents/{path}"


def _mock_file_push(path: str, exists: bool = False):
    """Helper: mock GET (404 or 200) + PUT (201) for a single file."""
    sha_response = {"sha": "abc123"} if exists else None
    respx.get(_contents_get_url(path)).mock(
        return_value=httpx.Response(200, json=sha_response) if exists
        else httpx.Response(404)
    )
    respx.put(_contents_put_url(path)).mock(
        return_value=httpx.Response(201, json={})
    )


# ── happy path ────────────────────────────────────────────────────────────────

@respx.mock
async def test_create_project_returns_expected_keys():
    respx.post(_TEMPLATE_URL).mock(return_value=httpx.Response(201, json=FAKE_REPO))
    for path in ["README.md", "index.html", "style.css", "main.js", ".github/workflows/ci.yml"]:
        _mock_file_push(path)
    respx.post(_TRANSFER_URL).mock(return_value=httpx.Response(202, json=FAKE_TRANSFER))

    result = await create_project("my-app", "john-doe", "blank", "A test app.")

    assert result["repo_name"] == "my-app"
    assert result["full_name"] == "plumberito-org/my-app"
    assert result["html_url"] == "https://github.com/plumberito-org/my-app"
    assert result["transfer_initiated"] is True


@respx.mock
async def test_create_project_pushes_all_template_files():
    respx.post(_TEMPLATE_URL).mock(return_value=httpx.Response(201, json=FAKE_REPO))
    for path in ["README.md", "index.html", "style.css", "main.js", ".github/workflows/ci.yml"]:
        _mock_file_push(path)
    respx.post(_TRANSFER_URL).mock(return_value=httpx.Response(202, json=FAKE_TRANSFER))

    result = await create_project("my-app", "john-doe", "blank")

    assert result["files_pushed"] == 5


@respx.mock
async def test_create_project_calls_template_generate_endpoint():
    captured = {}

    async def capture(request, route):
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json=FAKE_REPO)

    respx.post(_TEMPLATE_URL).mock(side_effect=capture)
    for path in ["README.md", "index.html", "style.css", "main.js", ".github/workflows/ci.yml"]:
        _mock_file_push(path)
    respx.post(_TRANSFER_URL).mock(return_value=httpx.Response(202, json=FAKE_TRANSFER))

    await create_project("my-app", "john-doe", "blank")

    assert captured["body"]["name"] == "my-app"
    assert captured["body"]["owner"] == "plumberito-org"
    assert captured["body"]["private"] is True


@respx.mock
async def test_create_project_initiates_transfer_to_target_owner():
    respx.post(_TEMPLATE_URL).mock(return_value=httpx.Response(201, json=FAKE_REPO))
    for path in ["README.md", "index.html", "style.css", "main.js", ".github/workflows/ci.yml"]:
        _mock_file_push(path)

    captured = {}

    async def capture_transfer(request, route):
        captured["body"] = json.loads(request.content)
        return httpx.Response(202, json=FAKE_TRANSFER)

    respx.post(_TRANSFER_URL).mock(side_effect=capture_transfer)

    await create_project("my-app", "john-doe", "blank")

    assert captured["body"]["new_owner"] == "john-doe"


@respx.mock
async def test_create_project_file_push_sends_sha_when_file_exists():
    respx.post(_TEMPLATE_URL).mock(return_value=httpx.Response(201, json=FAKE_REPO))

    # README.md already exists in the repo
    _mock_file_push("README.md", exists=True)
    for path in ["index.html", "style.css", "main.js", ".github/workflows/ci.yml"]:
        _mock_file_push(path)

    put_requests = []

    async def capture_put(request, route):
        put_requests.append(json.loads(request.content))
        return httpx.Response(201, json={})

    # Override the README.md PUT mock to capture
    respx.put(_contents_put_url("README.md")).mock(side_effect=capture_put)
    respx.post(_TRANSFER_URL).mock(return_value=httpx.Response(202, json=FAKE_TRANSFER))

    await create_project("my-app", "john-doe", "blank")

    assert put_requests[0]["sha"] == "abc123"


# ── error cases ───────────────────────────────────────────────────────────────

async def test_create_project_raises_on_unknown_template():
    with pytest.raises(ValueError, match="Unknown template"):
        await create_project("my-app", "john-doe", "nonexistent")


async def test_create_project_raises_on_bad_template_repo_config(monkeypatch):
    monkeypatch.setenv("GITHUB_TEMPLATE_REPO", "invalid-no-slash")
    # Reload env-dependent values
    import importlib, tools.create_project as cp
    monkeypatch.setattr(cp, "_GITHUB_TEMPLATE_REPO", "invalid-no-slash")

    with pytest.raises(ValueError, match="GITHUB_TEMPLATE_REPO"):
        await create_project("my-app", "john-doe", "blank")


@respx.mock
async def test_create_project_raises_on_github_api_error():
    respx.post(_TEMPLATE_URL).mock(
        return_value=httpx.Response(422, json={"message": "Repository already exists"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await create_project("my-app", "john-doe", "blank")


@respx.mock
async def test_create_project_raises_on_transfer_failure():
    respx.post(_TEMPLATE_URL).mock(return_value=httpx.Response(201, json=FAKE_REPO))
    for path in ["README.md", "index.html", "style.css", "main.js", ".github/workflows/ci.yml"]:
        _mock_file_push(path)
    respx.post(_TRANSFER_URL).mock(return_value=httpx.Response(404, json={"message": "User not found"}))

    with pytest.raises(httpx.HTTPStatusError):
        await create_project("my-app", "nonexistent-user", "blank")
