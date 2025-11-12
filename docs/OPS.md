# Operational Runbook

## Service Overview
- **Application**: Offline XTTS v2 voice cloning pipeline.
- **Entry points**: `run.ps1` (Windows) and `run.sh` (Linux) orchestrate full lifecycle.
- **Artifacts**: Models, embeddings, renders, and logs under `artifacts/`.

## Routine Operations
1. Execute `./run.ps1` or `./run.sh` to rebuild, render, and smoke test.
2. Inspect `artifacts/logs/run-*.jsonl` for structured telemetry (RTF, device, file paths).
3. Generated audio lives in `artifacts/outputs/<scenario>/render.wav`.

## Configuration
- `.env.example` documents overridable environment variables.
- `config/default.yaml` sets default paths, device order, and audio settings.
- CLI overrides available via `scripts/tts_cli.py --help`.

## Maintenance
- Regenerate embeddings when swapping reference WAVs using `scripts/tts_embed.py`.
- Run `scripts/fetch-model.ps1 -AllowDownload` or `scripts/fetch_model.sh --allow-download` to refresh XTTS weights.
- Update Python dependencies via `scripts/tts_setup.py` (the script is idempotent).

## Monitoring & Logs
- JSONL logs: `artifacts/logs/run-*.jsonl`, `fetch-model-*.jsonl` (structured, UTC timestamps).
- Console mirrors log stages for quick visibility.

## Incident Response
- If renders fail, check latest log file for `status=error` entries.
- Re-run orchestrator with `--device-order cpu` to force CPU fallback when GPU backends misbehave.
- Validate model checksum with the fetch scripts to rule out corrupt weights.

## Backup & Retention
- Copy `artifacts/models/` and `artifacts/outputs/` to persistent storage post-run.
- Logs can be ingested into ELK/Splunk via JSONL import.
