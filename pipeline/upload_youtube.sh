#!/usr/bin/env bash
set -euo pipefail

TASK_FILE="${1:-}"
CREDENTIAL_FILE="${HOME}/.openclaw/credentials/youtube_client_secret.json"

if [[ -z "${TASK_FILE}" ]]; then
  python3 - <<'PY'
import json
print(json.dumps({
    "success": False,
    "status": "failed",
    "message": "Usage: upload_youtube.sh <task-file>"
}))
PY
  exit 2
fi

if [[ ! -f "${CREDENTIAL_FILE}" ]]; then
  python3 - "${TASK_FILE}" "${CREDENTIAL_FILE}" <<'PY'
import json
import sys
task_file, credential_file = sys.argv[1], sys.argv[2]
print(json.dumps({
    "success": False,
    "status": "manual_credentials_required",
    "message": f"Missing YouTube OAuth client secret. Place it at {credential_file} and implement the YouTube Data API v3 upload call in pipeline/upload_youtube.sh.",
    "task_file": task_file,
    "credential_file": credential_file,
    "platform": "youtube_shorts"
}))
PY
  exit 0
fi

python3 - "${TASK_FILE}" "${CREDENTIAL_FILE}" <<'PY'
import json
import sys
task_file, credential_file = sys.argv[1], sys.argv[2]
print(json.dumps({
    "success": False,
    "status": "scaffold_only",
    "message": f"Credential file exists at {credential_file}. Replace the scaffold in pipeline/upload_youtube.sh with a YouTube Data API v3 upload implementation.",
    "task_file": task_file,
    "credential_file": credential_file,
    "platform": "youtube_shorts"
}))
PY
