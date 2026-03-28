#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/backend"

gcloud run deploy orchestrator \
  --source . \
  --region us-central1 \
  --timeout 3600 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 2 \
  --allow-unauthenticated \
  --set-env-vars "LLM_MODEL=${LLM_MODEL:-google/gemini-2.0-flash-001},GITHUB_ORG=${GITHUB_ORG:-plumberito},GCP_PROJECT=${GCP_PROJECT},GCP_REGION=${GCP_REGION:-us-central1}" \
  --set-secrets "OPENROUTER_API_KEY=OPENROUTER_API_KEY:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest,PULUMI_ACCESS_TOKEN=PULUMI_ACCESS_TOKEN:latest,GITHUB_CLIENT_ID=GITHUB_CLIENT_ID:latest,GITHUB_CLIENT_SECRET=GITHUB_CLIENT_SECRET:latest,OAUTH_CALLBACK_URL=OAUTH_CALLBACK_URL:latest"
