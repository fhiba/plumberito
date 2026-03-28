#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/frontend"

VITE_BACKEND_URL="${VITE_BACKEND_URL:?Set VITE_BACKEND_URL to your Cloud Run URL}" npm run build
firebase deploy --only hosting
