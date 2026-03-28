"""Unit tests for the blank template — pure logic, no HTTP."""
from tools.templates.blank import get_files


def test_get_files_returns_required_paths():
    files = get_files("my-app")
    paths = {f["path"] for f in files}
    assert "index.html" in paths
    assert "style.css" in paths
    assert "main.js" in paths
    assert "README.md" in paths
    assert ".github/workflows/ci.yml" in paths


def test_get_files_uses_repo_name_in_title():
    files = get_files("cool-project")
    html = next(f for f in files if f["path"] == "index.html")
    assert "Cool Project" in html["content"]


def test_get_files_uses_custom_description():
    files = get_files("my-app", description="A task manager app.")
    readme = next(f for f in files if f["path"] == "README.md")
    assert "A task manager app." in readme["content"]


def test_get_files_default_description_fallback():
    files = get_files("my-app")
    readme = next(f for f in files if f["path"] == "README.md")
    assert len(readme["content"]) > 0


def test_ci_workflow_targets_main_branch():
    files = get_files("my-app")
    ci = next(f for f in files if f["path"] == ".github/workflows/ci.yml")
    assert "branches: [main]" in ci["content"]


def test_ci_workflow_checks_required_files():
    files = get_files("my-app")
    ci = next(f for f in files if f["path"] == ".github/workflows/ci.yml")
    assert "index.html" in ci["content"]
    assert "style.css" in ci["content"]
    assert "main.js" in ci["content"]
