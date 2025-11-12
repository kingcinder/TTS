# Quickstart (Local XTTS Voice Cloning)

The repository ships with a fully automated XTTS v2 stack. Pick your OS and follow the matching single-command workflow.

## Windows 11 / 10 (PowerShell)
```powershell
# 1. Clone repo, then from the repo root:
./run.ps1
```

`run.ps1` will:
1. Check for `py`/PowerShell, create `.\env`, and install pinned Python dependencies.
2. Optionally download XTTS weights (use `scripts\fetch-model.ps1 -AllowDownload` if needed).
3. Synthesize a demo reference at `app\refs\demo.wav` (pyttsx3 when available, tone fallback) and build the speaker embedding.
4. Render `app\texts\demo.txt` to `artifacts\outputs\demo\render.wav` with DirectML → CPU fallback.
5. Write structured logs to `artifacts\logs\run-*.jsonl` and run smoke tests.

To customise inputs:
```powershell
python scripts\make_demo_ref.py --out app\refs\demo.wav
python scripts\tts_embed.py --refs app\refs\*.wav --out artifacts\models\voice.pt --log-file artifacts\logs\custom.jsonl
python scripts\tts_cli.py --text app\texts\demo.txt --voice artifacts\models\voice.pt --device-order rocm,dml,cpu --out artifacts\outputs\demo\render.wav --log-file artifacts\logs\demo.jsonl
```

Need to fetch weights offline? Place them at `artifacts\models\xtts_v2\xtts_v2.pth` or run:
```powershell
scripts\fetch-model.ps1 -AllowDownload -ExpectedSha256 <sha256>
```
(The script prints the SHA256 so you can pin it in CI.)

## Ubuntu 22.04 (bash)
```bash
# 1. Clone repo, then:
./run.sh
```

`run.sh` mirrors the PowerShell flow: creates `env/`, installs pinned wheels, runs the demo render, and logs to `artifacts/logs/`.

Manual commands (if you prefer):
```bash
python3 -m venv env && source env/bin/activate
python scripts/tts_setup.py --backend auto
python scripts/make_demo_ref.py --out app/refs/demo.wav
python scripts/tts_embed.py --refs app/refs/demo.wav --out artifacts/models/voice.pt --log-file artifacts/logs/manual.jsonl
python scripts/tts_cli.py --text app/texts/demo.txt --voice artifacts/models/voice.pt --device-order rocm,dml,cpu --out artifacts/outputs/manual/render.wav --log-file artifacts/logs/manual.jsonl
```

Download weights with verification:
```bash
./scripts/fetch_model.sh --allow-download --expected-sha256 <sha256>
```

## Notes
- Structured JSONL logs live in `artifacts/logs/`; review them with `jq` or any log shipper.
- `config/default.yaml` and `.env.example` illustrate overridable defaults.
- Tests live under `tests/smoke/` and are executed automatically as part of `run.ps1` / `run.sh`.
- `scripts/make_demo_ref.py` generates a demo clip with offline `pyttsx3`; if unavailable it falls back to a short tone so downstream smoke tests still succeed.
- On Windows, the setup prefers DirectML automatically. To force CPU-only for maximum compatibility, set `TTS_FORCE_CPU=1` before running (`$env:TTS_FORCE_CPU=1; ./run.ps1`).

## Configure via `.env`
Create a `.env` (or `.env.local`) at repo root:
```
TTS_DEVICE_ORDER=rocm,dml,cpu
TTS_OUTPUT_DIR=artifacts/outputs/demo
TTS_LOG_DIR=artifacts/logs
TTS_TEXT_PATH=app/texts/demo.txt
TTS_VOICE_REFS=app/refs/demo.wav
TTS_SAMPLE_RATE=48000
TTS_CROSSFADE_MS=8
TTS_CHUNK_SECONDS=20
```
Runners will auto-load it and apply sensible fallbacks if unset.
