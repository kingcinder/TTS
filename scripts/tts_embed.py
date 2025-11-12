import argparse
import json
import os
from datetime import datetime, timezone

import torch
from TTS.api import TTS


def load_xtts_for_env():
    """Prefer local model+config if TTS_MODEL_DIR is set; otherwise use model_name."""
    mdir = os.environ.get("TTS_MODEL_DIR")
    if mdir:
        mp = os.path.join(mdir, "xtts_v2.pth")
        cp = os.path.join(mdir, "config.json")
        if os.path.exists(mp) and os.path.exists(cp):
            return TTS(model_path=mp, config_path=cp, gpu=False)
    return TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", nargs="+", required=True, help="List of reference WAV files")
    ap.add_argument("--out", default="artifacts/models/voice.pt")
    ap.add_argument("--log-file")
    args = ap.parse_args()

    out_dir = os.path.dirname(args.out) or "."
    os.makedirs(out_dir, exist_ok=True)
    write_log(args.log_file, "embed", "start", "Embedding extraction started", refs=args.refs)

    model = load_xtts_for_env()
    embed = model.get_speaker_embeddings(args.refs)
    torch.save(embed, args.out)

    write_log(args.log_file, "embed", "success", "Embedding saved", output=args.out)
    print("Saved", args.out)


if __name__ == "__main__":
    main()
