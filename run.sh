#!/usr/bin/env bash
set -euo pipefail

SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_ROOT"

# Load .env / .env.local if present
set +u
if [[ -f ".env" ]]; then set -a; source ".env"; set +a; fi
if [[ -f ".env.local" ]]; then set -a; source ".env.local"; set +a; fi
set -u

LOG_DIR="${TTS_LOG_DIR:-$SCRIPT_ROOT/artifacts/logs}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run-$(date +%Y%m%d%H%M%S).jsonl"

log() {
  local stage="$1" status="$2" message="$3"
  shift 3 || true
  local timestamp
  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$timestamp" "$stage" "$status" "$message" "$@" <<'PY' >> "$LOG_FILE"
import json, sys
stamp, stage, status, message, *pairs = sys.argv[1:]
extra = {}
for item in pairs:
    if '=' in item:
        key, value = item.split('=', 1)
        extra[key] = value
entry = {"timestamp": stamp, "stage": stage, "status": status, "message": message}
entry.update(extra)
print(json.dumps(entry, ensure_ascii=False, separators=(',',':')))
PY
  else
    printf '{"timestamp":"%s","stage":"%s","status":"%s","message":"%s"}\n' "$timestamp" "$stage" "$status" "$message" >> "$LOG_FILE"
  fi
  echo "[$stage][$status] $message"
}

log doctor start "Checking required tools" log="$LOG_FILE"
if ! command -v python3 >/dev/null 2>&1; then
  log doctor error "python3 not found" remediation="Install Python 3.10+"
  exit 1
fi
log doctor success "All prerequisite commands available"

VENV_PATH="$SCRIPT_ROOT/env"
PYTHON_BIN="$VENV_PATH/bin/python3"
if [[ ! -x "$PYTHON_BIN" ]]; then
  log build start "Creating Python virtual environment" path="$VENV_PATH"
  python3 -m venv "$VENV_PATH"
  log build success "Virtual environment created" path="$VENV_PATH"
fi

export VIRTUAL_ENV="$VENV_PATH"
export PATH="$VENV_PATH/bin:$PATH"
# Ensure absolute imports like `from scripts.*` work even when running files from the scripts/ folder
export PYTHONPATH="$SCRIPT_ROOT${PYTHONPATH:+:$PYTHONPATH}"

log build start "Installing Python dependencies"
"$PYTHON_BIN" -m pip install --upgrade pip wheel setuptools >/dev/null
"$PYTHON_BIN" scripts/tts_setup.py --backend auto >/dev/null
log build success "Dependencies installed"

export TTS_LOG_FILE="$LOG_FILE"
VOICE_PATH="$SCRIPT_ROOT/artifacts/models/voice.pt"
VOICE_REFS="${TTS_VOICE_REFS:-$SCRIPT_ROOT/app/refs/demo.wav}"
[[ -f "$VOICE_REFS" ]] || "$PYTHON_BIN" scripts/make_demo_ref.py --out "$VOICE_REFS"
if [[ ! -f "$VOICE_PATH" ]]; then
  log embed start "Generating speaker embedding" output="$VOICE_PATH"
  "$PYTHON_BIN" scripts/tts_embed.py --refs "$VOICE_REFS" --out "$VOICE_PATH" --log-file "$LOG_FILE"
  log embed success "Speaker embedding ready" output="$VOICE_PATH"
fi

OUTPUT_DIR="${TTS_OUTPUT_DIR:-$SCRIPT_ROOT/artifacts/outputs/demo}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_FILE="$OUTPUT_DIR/render.wav"
log run start "Rendering demo sample" voice="$VOICE_PATH"
"$PYTHON_BIN" - <<'PY' >/dev/null 2>&1 || true
import os, pathlib
out_dir = os.environ.get("TTS_OUTPUT_DIR", "")
if out_dir:
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
PY
DEVICE_ORDER="${TTS_DEVICE_ORDER:-rocm,dml,cpu}"
TEXT_PATH="${TTS_TEXT_PATH:-$SCRIPT_ROOT/app/texts/demo.txt}"
SR="${TTS_SAMPLE_RATE:-48000}"
CROSSFADE_MS="${TTS_CROSSFADE_MS:-8}"
"$PYTHON_BIN" scripts/tts_cli_plus.py \
  --text "$TEXT_PATH" \
  --voice "$VOICE_PATH" \
  --device-order "$DEVICE_ORDER" \
  --out "$OUTPUT_FILE" \
  --sr "$SR" --crossfade-ms "$CROSSFADE_MS" \
  --run-dir "$SCRIPT_ROOT/artifacts"
log run success "Render completed" output="$OUTPUT_FILE"

log health start "Verifying render artifact" path="$OUTPUT_FILE"
if [[ ! -f "$OUTPUT_FILE" ]]; then
  log health error "Render artifact missing" path="$OUTPUT_FILE"
  exit 1
fi
log health success "Render artifact verified" bytes="$(stat -c%s "$OUTPUT_FILE")"

log smoke start "Running smoke tests"
"$PYTHON_BIN" -m compileall scripts tests >/dev/null
log smoke success "Smoke tests completed"

log complete success "Pipeline finished" log="$LOG_FILE"
