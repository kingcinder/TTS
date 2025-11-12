import argparse
import glob
import json
import os
import subprocess
from datetime import datetime, timezone

from pydub import AudioSegment


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
    log_dir = os.path.dirname(log_file) or '.'
    os.makedirs(log_dir, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

def crossfade_concat(files, out, sr=48000, crossfade_ms=8):
    seg = AudioSegment.silent(duration=0, frame_rate=sr)
    for f in files:
        seg = seg.append(AudioSegment.from_file(f), crossfade=crossfade_ms)
    tmp = out.replace('.wav','_pre.wav')
    seg.export(tmp, format='wav')
    # Two-pass EBU R128 loudness normalization
    # Pass 1
    meter = subprocess.check_output([
        'ffmpeg','-y','-i',tmp,'-af',
        'loudnorm=I=-16:TP=-1.0:LRA=11:print_format=json',
        '-f','null','-'
    ], stderr=subprocess.STDOUT).decode('utf-8', errors='ignore')
    # Very light-weight parse
    import re
    get = lambda k: (re.search(rf'"{k}":\s*([-0-9.]+)', meter) or [None, None])[1]
    measured_I = get('input_i') or "-23"
    measured_TP = get('input_tp') or "-2"
    measured_LRA = get('input_lra') or "7"
    measured_thresh = get('input_thresh') or "-23"
    offset = get('target_offset') or "0"
    # Pass 2
    subprocess.check_call([
        'ffmpeg','-y','-i',tmp,'-af',
        f'loudnorm=I=-16:TP=-1.0:LRA=11:measured_I={measured_I}:'
        f'measured_LRA={measured_LRA}:measured_TP={measured_TP}:'
        f'measured_thresh={measured_thresh}:offset={offset}',
        out
    ])

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', default='runs/latest/chunks/*.wav')
    ap.add_argument('--out', default='runs/latest/render.wav')
    ap.add_argument('--sr', type=int, default=48000)
    ap.add_argument('--crossfade-ms', type=int, default=8)
    ap.add_argument('--log-file')
    a = ap.parse_args()
    files = sorted(glob.glob(a.chunks))
    out_dir = os.path.dirname(a.out) or '.'
    os.makedirs(out_dir, exist_ok=True)
    crossfade_concat(files, a.out, a.sr, a.crossfade_ms)
    write_log(
        a.log_file,
        'join',
        'success',
        'Chunks concatenated',
        output=a.out,
        chunk_count=len(files),
    )
    print('Wrote', a.out)
