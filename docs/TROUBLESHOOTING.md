# Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `python3` missing when running scripts | Python not installed or not on PATH | Install Python 3.10+, then rerun `./run.sh` or `./run.ps1`. |
| `torch-directml` import fails on Windows | GPU drivers out of date or DirectML not available | Update Windows 11 and DirectX drivers; rerun `run.ps1` which falls back to CPU automatically. |
| `HIP_VISIBLE_DEVICES` warning | ROCm stack not detected | Ensure AMD ROCm drivers are installed; otherwise the pipeline falls back to CPU. |
| `ffmpeg` missing during normalization | System FFmpeg not installed | Install FFmpeg (`winget install Gyan.FFmpeg` on Windows or `sudo apt install ffmpeg` on Ubuntu) and rerun. |
| SHA256 mismatch after model download | Mirror updated weights | Delete `artifacts/models/xtts_v2/xtts_v2.pth`, rerun fetch script with the new SHA printed after download. |
| `compileall` smoke step fails | Syntax error in scripts/tests | Inspect console output, fix Python errors, rerun orchestrator. |
| Audio renders but is silent | Input reference audio is synthetic tone (demo) | Replace `app/refs/demo.wav` with 30–60 seconds of real speech and regenerate embeddings. |
| `pip` install times out | Network restrictions | Pre-download wheels and use `pip install --no-index --find-links <dir>` by editing `scripts/tts_setup.py` to point at the cache. |
