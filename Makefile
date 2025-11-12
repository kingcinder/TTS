# Simple helpers for the XTTS repo
# Usage:
#   make setup
#   make run
#   make test
#   make fetch-model
#   make docker-build && make docker-run

SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

# --- Config (override via env or CLI: make run OUT=artifacts/outputs/foo.wav) ---
export PYTHONPATH := $(CURDIR)
TEXT          ?= app/texts/demo.txt
VOICE         ?= artifacts/models/voice.pt
OUT           ?= artifacts/outputs/demo/render.wav
DEVICE_ORDER  ?= rocm,dml,cpu
SR            ?= 48000
CROSSFADE_MS  ?= 8
LOG_DIR       ?= artifacts/logs
MODEL_DIR     ?= artifacts/models/xtts_v2

export TTS_TEXT_PATH     := $(TEXT)
export TTS_VOICE_REFS    ?= app/refs/demo.wav
export TTS_OUTPUT_DIR    := $(dir $(OUT))
export TTS_LOG_DIR       := $(LOG_DIR)
export TTS_SAMPLE_RATE   := $(SR)
export TTS_CROSSFADE_MS  := $(CROSSFADE_MS)
export TTS_DEVICE_ORDER  := $(DEVICE_ORDER)
export TTS_MODEL_DIR     := $(MODEL_DIR)

# --- Python/venv ---
PY_SYS := $(shell command -v python3 || command -v python)
VENV   := env
PY     := $(CURDIR)/$(VENV)/bin/python3

ifeq ($(OS),Windows_NT)
	PY    := $(CURDIR)/env/Scripts/python.exe
endif

.PHONY: help venv setup demo-ref embed run run-cli test fetch-model docker-build docker-run clean

help:
	@echo "Targets:"
	@echo "  make setup        - create venv and install deps"
	@echo "  make embed        - build speaker embedding"
	@echo "  make run          - render with plus CLI -> $(OUT)"
	@echo "  make run-cli      - render with base CLI"
	@echo "  make test         - compile+pytest"
	@echo "  make fetch-model  - download XTTS model into $(MODEL_DIR)"
	@echo "  make docker-build - build container"
	@echo "  make docker-run   - run container"
	@echo "  make clean        - remove venv and renders"

venv:
	@mkdir -p artifacts/logs artifacts/models artifacts/outputs app/refs
	@echo "[build] creating venv at $(VENV)"
	"$(PY_SYS)" -m venv "$(VENV)"

setup: venv
	@echo "[build] installing pinned deps"
	"$(PY)" -m pip install --upgrade pip wheel setuptools >/dev/null
	"$(PY)" scripts/tts_setup.py --backend auto

demo-ref:
	@echo "[embed] ensuring demo reference at $(TTS_VOICE_REFS)"
	@if [ ! -f "$(TTS_VOICE_REFS)" ]; then \
		"$(PY)" scripts/make_demo_ref.py --out "$(TTS_VOICE_REFS)"; \
	fi
embed: setup demo-ref
	@echo "[embed] building speaker embedding -> $(VOICE)"
	@mkdir -p "$(dir $(VOICE))"
	"$(PY)" scripts/tts_embed.py --refs "$(TTS_VOICE_REFS)" --out "$(VOICE)" --log-file "$(LOG_DIR)/embed.jsonl"

run: setup embed
	@echo "[run] rendering -> $(OUT)"
	@mkdir -p "$(TTS_OUTPUT_DIR)" "$(LOG_DIR)"
	"$(PY)" scripts/tts_cli_plus.py \
		--text "$(TEXT)" \
		--voice "$(VOICE)" \
		--device-order "$(DEVICE_ORDER)" \
		--out "$(OUT)" \
		--sr "$(SR)" \
		--crossfade-ms "$(CROSSFADE_MS)" \
		--run-dir artifacts
# Plain CLI path (uses non-PLUS CLI)
run-cli: setup embed
	@mkdir -p "$(TTS_OUTPUT_DIR)" "$(LOG_DIR)"
	"$(PY)" scripts/tts_cli.py \
		--text "$(TEXT)" \
		--voice "$(VOICE)" \
		--device-order "$(DEVICE_ORDER)" \
		--out "$(OUT)" \
		--sr "$(SR)" \
		--crossfade-ms "$(CROSSFADE_MS)" \
		--log-file "$(LOG_DIR)/run.jsonl"

test: setup
	@echo "[test] compiling + pytest (if available)"
	"$(PY)" -m compileall scripts tests >/dev/null
	@if "$(PY)" -c "import sys; import importlib.util as u; sys.exit(0 if u.find_spec('pytest') else 1)"; then \
		"$(PY)" -m pytest -q; \
	else \
		echo "pytest not installed (ok)"; \
	fi
# Fetch the XTTS model locally (requires network)
fetch-model: setup
	@echo "[model] fetching weights into $(MODEL_DIR)"
	chmod +x scripts/fetch_model.sh
	./scripts/fetch_model.sh --allow-download --dest "$(MODEL_DIR)"

docker-build:
	@echo "[docker] building image 'xtts:local'"
	docker build -f containers/Dockerfile -t xtts:local .

docker-run:
	@echo "[docker] running xtts:local (bind-mount artifacts/ and app/)"
	docker run --rm -it \
		-e PYTHONPATH=/app \
		-e TTS_OUTPUT_DIR=/app/$(TTS_OUTPUT_DIR) \
		-e TTS_LOG_FILE=/app/$(LOG_DIR)/container.jsonl \
		-v "$(CURDIR)/artifacts:/app/artifacts" \
		-v "$(CURDIR)/app:/app/app" \
		txtts:local

clean:
	@echo "[clean] removing venv and generated outputs"
	@rm -rf "$(VENV)" runs
	@find artifacts/outputs -type f -name '*.wav' -delete || true
