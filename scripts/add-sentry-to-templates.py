#!/usr/bin/env python3
"""Add @sentry/browser (or framework-specific SDK) to all template repos in the org."""

import base64
import json
import os
import sys

import httpx

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
ORG = os.environ.get("GITHUB_ORG", "plumberito")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}
API = "https://api.github.com"
COMMIT_MSG = "feat: add Sentry error tracking (auto-initialized when VITE_SENTRY_DSN is set)"


def get_file(repo: str, path: str) -> tuple[str, str]:
    """Return (content_decoded, sha) for a file in a repo."""
    resp = httpx.get(f"{API}/repos/{ORG}/{repo}/contents/{path}", headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    content = base64.b64decode(data["content"]).decode()
    return content, data["sha"]


def put_file(repo: str, path: str, content: str, sha: str | None, message: str = COMMIT_MSG):
    """Create or update a file in a repo."""
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode()).rstrip(b"=").decode() + "==",
    }
    # base64 encode properly
    payload["content"] = base64.b64encode(content.encode()).decode()
    if sha:
        payload["sha"] = sha
    resp = httpx.put(f"{API}/repos/{ORG}/{repo}/contents/{path}", headers=HEADERS, json=payload)
    if resp.status_code >= 400:
        print(f"  ERROR {resp.status_code}: {resp.text[:300]}")
        return False
    print(f"  ✓ {path} updated")
    return True


def add_dep_to_package_json(repo: str, dep_name: str, dep_version: str = "^9"):
    """Add a dependency to package.json."""
    content, sha = get_file(repo, "package.json")
    pkg = json.loads(content)
    deps = pkg.get("dependencies", {})
    if dep_name in deps:
        print(f"  {dep_name} already in package.json, skipping")
        return True
    deps[dep_name] = dep_version
    pkg["dependencies"] = dict(sorted(deps.items()))
    new_content = json.dumps(pkg, indent=2) + "\n"
    return put_file(repo, "package.json", new_content, sha)


def prepend_to_file(repo: str, path: str, code: str):
    """Prepend code to an existing file."""
    content, sha = get_file(repo, path)
    if "Sentry" in content:
        print(f"  Sentry already in {path}, skipping")
        return True
    new_content = code + "\n" + content
    return put_file(repo, path, new_content, sha)


def create_file(repo: str, path: str, code: str):
    """Create a new file (fails if exists)."""
    # Check if file exists
    resp = httpx.get(f"{API}/repos/{ORG}/{repo}/contents/{path}", headers=HEADERS)
    if resp.status_code == 200:
        existing = base64.b64decode(resp.json()["content"]).decode()
        if "Sentry" in existing:
            print(f"  Sentry already in {path}, skipping")
            return True
        # Update existing file
        return put_file(repo, path, code, resp.json()["sha"])
    return put_file(repo, path, code, None)


# --- Sentry init snippets ---

VITE_SENTRY_INIT = """\
import * as Sentry from "@sentry/browser";

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE,
  });
}
"""

SVELTEKIT_HOOKS_CLIENT = """\
import * as Sentry from "@sentry/browser";

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE,
  });
}

/** @type {import('@sveltejs/kit').HandleClientError} */
export function handleError({ error, event }) {
  Sentry.captureException(error);
  console.error(error);
}
"""

NEXTJS_SENTRY_CLIENT = """\
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 1.0,
});
"""

NEXTJS_SENTRY_CONFIG = """\
import { withSentryConfig } from "@sentry/nextjs";

/** @type {import('next').NextConfig} */
const nextConfig = {};

export default withSentryConfig(nextConfig, {
  silent: true,
  hideSourceMaps: true,
});
"""

ASTRO_SENTRY_CLIENT = """\
<script>
  import * as Sentry from "@sentry/browser";

  const dsn = import.meta.env.PUBLIC_SENTRY_DSN;
  if (dsn) {
    Sentry.init({
      dsn,
      environment: import.meta.env.MODE,
    });
  }
</script>
"""


# --- Per-repo update functions ---

def update_react(repo: str):
    print(f"\n📦 {repo} (React)")
    add_dep_to_package_json(repo, "@sentry/browser")
    prepend_to_file(repo, "src/main.tsx", VITE_SENTRY_INIT)


def update_vue(repo: str):
    print(f"\n📦 {repo} (Vue)")
    add_dep_to_package_json(repo, "@sentry/browser")
    prepend_to_file(repo, "src/main.ts", VITE_SENTRY_INIT)


def update_svelte(repo: str):
    print(f"\n📦 {repo} (SvelteKit)")
    add_dep_to_package_json(repo, "@sentry/browser")
    create_file(repo, "src/hooks.client.ts", SVELTEKIT_HOOKS_CLIENT)


def update_solid(repo: str):
    print(f"\n📦 {repo} (Solid)")
    add_dep_to_package_json(repo, "@sentry/browser")
    prepend_to_file(repo, "src/index.tsx", VITE_SENTRY_INIT)


def update_astro(repo: str):
    print(f"\n📦 {repo} (Astro)")
    add_dep_to_package_json(repo, "@sentry/browser")
    # For Astro, inject a client-side script into the base layout
    content, sha = get_file(repo, "src/layouts/Layout.astro")
    if "Sentry" in content:
        print("  Sentry already in Layout.astro, skipping")
        return
    # Insert the script block right after the opening <head> or before </head>
    if "</head>" in content:
        new_content = content.replace("</head>", ASTRO_SENTRY_CLIENT + "\n</head>")
    elif "<head>" in content:
        new_content = content.replace("<head>", "<head>\n" + ASTRO_SENTRY_CLIENT)
    else:
        print("  WARNING: Could not find <head> in Layout.astro, injecting at top")
        new_content = ASTRO_SENTRY_CLIENT + "\n" + content
    put_file(repo, "src/layouts/Layout.astro", new_content, sha)


def update_nextjs(repo: str):
    print(f"\n📦 {repo} (Next.js)")
    add_dep_to_package_json(repo, "@sentry/nextjs")
    # Create sentry.client.config.ts
    create_file(repo, "sentry.client.config.ts", NEXTJS_SENTRY_CLIENT)
    # Add instrumentation hook to layout.tsx
    content, sha = get_file(repo, "src/app/layout.tsx")
    if "Sentry" in content:
        print("  Sentry already in layout.tsx, skipping")
    else:
        sentry_import = 'import "../../../sentry.client.config";\n'
        new_content = sentry_import + content
        put_file(repo, "src/app/layout.tsx", new_content, sha)


REPOS = {
    "spa-react-shadcn-tanstack": update_react,
    "spa-vue-tailwind-vrouter": update_vue,
    "spa-svelte-tailwind-sveltekit": update_svelte,
    "spa-solid-tailwind-solidrouter": update_solid,
    "mpa-astro-tailwind-shadcn": update_astro,
    "ssr-next-shadcn-approuter": update_nextjs,
}


def main():
    # Optional: only update specific repos
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(REPOS.keys())

    for repo in targets:
        if repo not in REPOS:
            print(f"Unknown repo: {repo}")
            continue
        try:
            REPOS[repo](repo)
        except Exception as e:
            print(f"  ERROR: {e}")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
