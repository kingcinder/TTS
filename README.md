# TTS – XTTS v2 Offline Pipeline

End-to-end XTTS v2 voice cloning that runs fully offline on Windows (PowerShell) and Linux (bash). The stack is reproducible, idempotent, and fully scripted.

- `run.ps1` / `run.sh`: single-command build → render → healthcheck → smoke test orchestrators.
- `scripts/`: Python helpers (chunking, embedding, workers, backend detection, model fetchers).
- `app/`: demo assets (reference audio + text) used by smoke tests.
- `artifacts/`: outputs, models, and structured logs (see `.gitkeep` for directory layout).
- `containers/`: Docker build assets for isolated execution.
- `docs/`: quickstart, troubleshooting, and automation prompts.
- `tests/`: minimal smoke coverage for utility code.

New to the repo? Start with [`README-QUICKSTART.md`](README-QUICKSTART.md) for platform-specific instructions, or just run `./run.sh` (Linux) or `./run.ps1` (Windows PowerShell) for the automated pipeline.
