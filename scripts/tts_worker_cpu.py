import argparse
import json
import os
import time
from datetime import datetime, timezone

import torch
from TTS.api import TTS


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


def load_xtts():
    mdir = os.environ.get("TTS_MODEL_DIR")
    if mdir:
        mp, cp = os.path.join(mdir, "xtts_v2.pth"), os.path.join(mdir, "config.json")
        if os.path.exists(mp) and os.path.exists(cp):
            return TTS(model_path=mp, config_path=cp, gpu=False)
    return TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--voice")
    parser.add_argument("--language", default="en")
    parser.add_argument("--log-file")
    args = parser.parse_args()

    log_file = args.log_file or os.environ.get("TTS_LOG_FILE")

    os.makedirs(args.out_dir, exist_ok=True)
    write_log(log_file, "worker", "start", "CPU worker boot", mode="cpu")

    model = load_xtts()
    spk_embed = None
    if args.voice:
        spk_embed = torch.load(args.voice, map_location="cpu")
        write_log(log_file, "worker", "info", "Loaded speaker embedding", path=args.voice)

    with open(args.chunks, "r", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            start = time.time()
            if spk_embed is not None:
                wav = model.tts(text=item["text"], speaker=spk_embed, language=args.language)
            else:
                wav = model.tts(text=item["text"], language=args.language)
            duration = len(wav) / model.synthesizer.output_sample_rate
            rtf = (time.time() - start) / max(1e-6, duration)
            out_wav = os.path.join(args.out_dir, f"{item['id']:06d}.wav")
            model.save_wav(wav, out_wav)
            msg = f"CPU chunk {item['id']} -> {out_wav} RTF={rtf:.2f}"
            write_log(
                log_file,
                "worker",
                "success",
                "Chunk rendered",
                chunk_id=item["id"],
                path=out_wav,
                rtf=rtf,
                device="cpu",
            )
            print(msg)

    write_log(log_file, "worker", "success", "CPU worker finished", mode="cpu")


if __name__ == "__main__":
    main()
