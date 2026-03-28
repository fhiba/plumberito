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
  --allow-unauthenticated
