import argparse
import json
import os
import re
from datetime import datetime, timezone


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


def chunk_text(txt, max_sec=20):
    sents = re.split(r"(?<=[.!?])\s+", txt.strip())
    chunks, cur, cur_len = [], [], 0
    for s in sents:
        l = max(1, len(s) // 15)
        if cur_len + l > max_sec and cur:
            chunks.append(" ".join(cur))
            cur, cur_len = [], 0
        cur.append(s)
        cur_len += l
    if cur:
        chunks.append(" ".join(cur))
    return chunks


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chunk-sec", type=int, default=20)
    ap.add_argument("--log-file")
    args = ap.parse_args()
    txt = open(args.text, "r", encoding="utf-8").read()
    out_dir = os.path.dirname(args.out) or "."
    os.makedirs(out_dir, exist_ok=True)
    chunks = chunk_text(txt, args.chunk_sec)
    with open(args.out, "w", encoding="utf-8") as f:
        for i, c in enumerate(chunks):
            f.write(json.dumps({"id": i, "text": c}, ensure_ascii=False) + "\n")
    write_log(
        args.log_file,
        "chunk",
        "success",
        "Chunked input text",
        output=args.out,
        chunks=len(chunks),
    )
    print("Wrote", args.out, len(chunks), "chunks")
