#!/usr/bin/env bash
set -euo pipefail

TASK_FILE="${1:-}"
CREDENTIAL_FILE="${HOME}/.openclaw/credentials/instagram_credentials.json"

if [[ -z "${TASK_FILE}" ]]; then
  python3 - <<'PY'
import json
print(json.dumps({
    "success": False,
    "status": "failed",
    "message": "Usage: upload_instagram.sh <task-file>"
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
    "message": f"Missing Instagram credentials. Place them at {credential_file} and implement the Instagram Graph API upload call in pipeline/upload_instagram.sh.",
    "task_file": task_file,
    "credential_file": credential_file,
    "platform": "instagram_reels"
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
    "message": f"Credential file exists at {credential_file}. Replace the scaffold in pipeline/upload_instagram.sh with an Instagram Graph API Reels upload implementation.",
    "task_file": task_file,
    "credential_file": credential_file,
    "platform": "instagram_reels"
}))
PY
