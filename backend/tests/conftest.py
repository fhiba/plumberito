import os

# Set env vars before any app modules are imported
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_ORG", "plumberito-org")
os.environ.setdefault("GITHUB_TEMPLATE_REPO", "plumberito-org/blank-web")

FAKE_REPO = {
    "full_name": "plumberito-org/my-app",
    "html_url": "https://github.com/plumberito-org/my-app",
    "name": "my-app",
}

FAKE_TRANSFER = {
    "full_name": "plumberito-org/my-app",
    "html_url": "https://github.com/plumberito-org/my-app",
}
