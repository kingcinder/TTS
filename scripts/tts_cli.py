import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# Allow absolute `scripts.*` imports even when executed as "python scripts/tts_cli.py"
if __package__ in (None, ""):
    import pathlib as _pathlib
    _root = str(_pathlib.Path(__file__).resolve().parents[1])
    if _root not in sys.path:
        sys.path.insert(0, _root)

from scripts.backend import pick_backend


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_log(log_file, stage, status, message, **extra):
    if not log_file:
        return
    entry = {
        "timestamp": timestamp(),
        "stage": stage,
        "status": status,
        "message": message,
        **extra,
    }
    log_dir = os.path.dirname(log_file) or "."
    os.makedirs(log_dir, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def sh(args, log_file=None, env=None):
    print(">", " ".join(args))
    write_log(log_file, "process", "start", "Executing command", command=args)
    subprocess.check_call(args, env=env)
    write_log(log_file, "process", "success", "Command completed", command=args)


if __name__ == "__main__":
    import os as _os

    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--voice", help="Path to voice embedding (.pt). Optional when using built-in speaker.")
    ap.add_argument("--device-order", default=_os.environ.get("TTS_DEVICE_ORDER", "rocm,dml,cpu"))
    ap.add_argument("--gpu-workers", type=int, default=1)
    ap.add_argument("--cpu-workers", type=int, default=6)
    ap.add_argument("--chunk-sec", type=int, default=int(_os.environ.get("TTS_CHUNK_SECONDS", "20")))
    ap.add_argument("--crossfade-ms", type=int, default=int(_os.environ.get("TTS_CROSSFADE_MS", "8")))
    ap.add_argument("--sr", type=int, default=int(_os.environ.get("TTS_SAMPLE_RATE", "48000")))
    ap.add_argument("--out", required=True)
    ap.add_argument("--cpu-only", action="store_true")
    ap.add_argument("--log-file", default=os.environ.get("TTS_LOG_FILE"))
    ap.add_argument(
        "--language",
        default="en",
        help="Language token for synthesis (default: en).",
    )
    args = ap.parse_args()

    if not args.voice:
        print("No voice embedding supplied; the base XTTS speaker will be used.")

    if args.log_file:
        write_log(args.log_file, "cli", "start", "XTTS CLI invoked", parameters=vars(args))

    out_dir = os.path.dirname(args.out) or "."
    os.makedirs(out_dir, exist_ok=True)

    backend = pick_backend(args.device_order)
    print("Backend selected:", backend)
    write_log(args.log_file, "backend", "success", "Backend resolved", backend=backend)

    chunks_jsonl = os.path.join(out_dir, "chunks.jsonl")
    chunk_cmd = [
        sys.executable,
        "scripts/tts_chunk.py",
        "--text",
        args.text,
        "--out",
        chunks_jsonl,
        "--chunk-sec", str(args.chunk_sec),
    ]
    if args.log_file:
        chunk_cmd.extend(["--log-file", args.log_file])
    sh(chunk_cmd, log_file=args.log_file)

    workdir = os.path.join(out_dir, "chunks")
    os.makedirs(workdir, exist_ok=True)

    worker_env = os.environ.copy()
    if args.log_file:
        worker_env["TTS_LOG_FILE"] = args.log_file

    worker_script = "scripts/tts_worker_gpu.py" if (backend != "cpu" and not args.cpu_only) else "scripts/tts_worker_cpu.py"
    worker_args = [
        sys.executable,
        worker_script,
        "--chunks",
        chunks_jsonl,
        "--out-dir",
        workdir,
        "--language",
        args.language,
    ]
    if args.voice:
        worker_args.extend(["--voice", args.voice])
    if args.log_file:
        worker_args.extend(["--log-file", args.log_file])
    if backend != "cpu" and not args.cpu_only:
        worker_args.extend(["--device", backend])
    sh(worker_args, log_file=args.log_file, env=worker_env)

    join_cmd = [
        sys.executable,
        "scripts/tts_join.py",
        "--chunks",
        os.path.join(workdir, "*.wav"),
        "--out",
        args.out,
        "--sr",
        str(args.sr),
        "--crossfade-ms",
        str(args.crossfade_ms),
    ]
    if args.log_file:
        join_cmd.extend(["--log-file", args.log_file])
    sh(join_cmd, log_file=args.log_file)

    write_log(args.log_file, "cli", "success", "Render complete", output=args.out)
    print("All done:", args.out)
