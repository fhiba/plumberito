#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/backend"

gcloud run deploy orchestrator \
  --source . \
  --region us-central1 \
  --timeout 3600 \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 2 \
  --allow-unauthenticated \
  --set-env-vars "LLM_MODEL=${LLM_MODEL:-google/gemini-2.0-flash-001}" \
  --set-secrets "OPENROUTER_API_KEY=OPENROUTER_API_KEY:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest"
