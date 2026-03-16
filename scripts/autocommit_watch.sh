#!/bin/zsh

set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
LOCK_DIR="$REPO_DIR/.git/autocommit.lock"
INTERVAL_SECONDS="${AUTO_COMMIT_INTERVAL_SECONDS:-5}"
QUIET_SECONDS="${AUTO_COMMIT_QUIET_SECONDS:-12}"
AUTHOR_NAME="${AUTO_COMMIT_AUTHOR_NAME:-sns-auto-bot}"
AUTHOR_EMAIL="${AUTO_COMMIT_AUTHOR_EMAIL:-bigmac@local}"

cleanup() {
  rmdir "$LOCK_DIR" >/dev/null 2>&1 || true
}

if ! mkdir "$LOCK_DIR" >/dev/null 2>&1; then
  exit 0
fi

trap cleanup EXIT INT TERM

cd "$REPO_DIR" || exit 1

has_untracked_files() {
  [[ -n "$(git ls-files --others --exclude-standard)" ]]
}

repo_is_dirty() {
  ! git diff --quiet --ignore-submodules HEAD -- ||
    ! git diff --cached --quiet --ignore-submodules -- ||
    has_untracked_files
}

last_dirty_at=0

while true; do
  if repo_is_dirty; then
    now=$(date +%s)
    if [[ "$last_dirty_at" -eq 0 ]]; then
      last_dirty_at="$now"
      sleep "$INTERVAL_SECONDS"
      continue
    fi

    if (( now - last_dirty_at < QUIET_SECONDS )); then
      sleep "$INTERVAL_SECONDS"
      continue
    fi

    if git add -A >/dev/null 2>&1; then
      if ! git diff --cached --quiet --ignore-submodules --; then
        stamp=$(date '+%Y-%m-%d %H:%M:%S %Z')
        GIT_AUTHOR_NAME="$AUTHOR_NAME" \
          GIT_AUTHOR_EMAIL="$AUTHOR_EMAIL" \
          GIT_COMMITTER_NAME="$AUTHOR_NAME" \
          GIT_COMMITTER_EMAIL="$AUTHOR_EMAIL" \
          git commit --no-verify -m "auto: $stamp" >/dev/null 2>&1 || true
      fi
    fi

    last_dirty_at=0
  else
    last_dirty_at=0
  fi

  sleep "$INTERVAL_SECONDS"
done
