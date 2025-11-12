#!/usr/bin/env bash
set -euo pipefail

SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="artifacts/models/xtts_v2"
ALLOW_DOWNLOAD=0
EXPECTED_SHA=""

usage() {
  cat <<USAGE
Usage: ./scripts/fetch_model.sh [--allow-download] [--dest PATH] [--expected-sha256 HASH]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --allow-download)
      ALLOW_DOWNLOAD=1
      shift
      ;;
    --dest)
      DEST="$2"
      shift 2
      ;;
    --expected-sha256)
      EXPECTED_SHA="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

LOG_DIR="$SCRIPT_ROOT/../artifacts/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/fetch-model-$(date +%Y%m%d%H%M%S).jsonl"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.10+ before running this script." >&2
  exit 1
fi

log() {
  local stage="$1" status="$2" message="$3"
  shift 3 || true
  python3 - <<'PY' "$stage" "$status" "$message" "$LOG_FILE" "$@"
import json, sys, datetime
stage, status, message, log_file, *rest = sys.argv[1:]
extra = {}
for item in rest:
    if '=' in item:
        key, value = item.split('=', 1)
        extra[key] = value
entry = {"timestamp": datetime.datetime.utcnow().isoformat(), "stage": stage, "status": status, "message": message}
entry.update(extra)
with open(log_file, 'a', encoding='utf-8') as fh:
    json.dump(entry, fh, ensure_ascii=False, separators=(',',':'))
    fh.write('\n')
print(f"[{stage}][{status}] {message}")
PY
}

DEST_DIR="$SCRIPT_ROOT/../$DEST"
mkdir -p "$DEST_DIR"
MODEL_FILE="$DEST_DIR/xtts_v2.pth"

if [[ -f "$MODEL_FILE" ]]; then
  SHA="$(python3 - <<'PY' "$MODEL_FILE"
import hashlib, sys
path = sys.argv[1]
hash = hashlib.sha256()
with open(path, 'rb') as fh:
    for chunk in iter(lambda: fh.read(1024 * 1024), b''):
        hash.update(chunk)
print(hash.hexdigest())
PY
)"
  log verify success "Existing model located" path="$MODEL_FILE" sha256="$SHA"
  if [[ -n "$EXPECTED_SHA" && "$SHA" != "$EXPECTED_SHA" ]]; then
    echo "SHA256 mismatch for $MODEL_FILE" >&2
    exit 1
  fi
  exit 0
fi

if [[ "$ALLOW_DOWNLOAD" -ne 1 ]]; then
  log download error "Model file missing" path="$MODEL_FILE" hint="Rerun with --allow-download"
  echo "Model weights not present. Supply them manually or use --allow-download." >&2
  exit 1
fi

log download start "Fetching XTTS v2 weights" path="$MODEL_FILE"
python3 "$SCRIPT_ROOT/fetch_model.py" --dest "$DEST_DIR"

if [[ ! -f "$MODEL_FILE" ]]; then
  echo "Model download failed" >&2
  exit 1
fi

SHA="$(python3 - <<'PY' "$MODEL_FILE"
import hashlib, sys
path = sys.argv[1]
hash = hashlib.sha256()
with open(path, 'rb') as fh:
    for chunk in iter(lambda: fh.read(1024 * 1024), b''):
        hash.update(chunk)
print(hash.hexdigest())
PY
)"
log download success "Model downloaded" path="$MODEL_FILE" sha256="$SHA"

if [[ -n "$EXPECTED_SHA" && "$SHA" != "$EXPECTED_SHA" ]]; then
  echo "SHA256 mismatch for $MODEL_FILE" >&2
  exit 1
fi
