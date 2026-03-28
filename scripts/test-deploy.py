#!/usr/bin/env python3
"""Test the setup_deploy flow with a svelte template repo."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from app.tools import _create_repo, _setup_deploy

REPO_NAME = "test-sentry-svelte"

# Step 1: Create repo from svelte template
print(f"1. Creating repo '{REPO_NAME}' from svelte template...")
result = _create_repo(
    repo_name=REPO_NAME,
    template_repo="plumberito/spa-svelte-tailwind-sveltekit",
    user_token=os.environ["GITHUB_TOKEN"],
)
print(f"   {result}\n")

data = json.loads(result)
if "error" in data:
    print("   Failed to create repo, trying setup_deploy anyway (maybe it already exists)...")
    repo_full_name = f"pescudeiro/{REPO_NAME}"
else:
    repo_full_name = data["full_name"]

# Step 2: Setup deploy
print(f"2. Setting up deploy for {repo_full_name}...")
result = _setup_deploy(
    repo_full_name=repo_full_name,
    site_id=REPO_NAME,
    user_token=os.environ["GITHUB_TOKEN"],
)
print(f"   {json.dumps(json.loads(result), indent=2)}")
