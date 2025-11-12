# Enhanced CLI that logs JSONL and uses the logged workers + FFmpeg-checked joiner
import argparse, os, subprocess, sys, time
# Allow absolute `scripts.*` imports even when executed directly
if __package__ in (None, ""):
    import pathlib as _pathlib
    _root = str(_pathlib.Path(__file__).resolve().parents[1])
    if _root not in sys.path:
        sys.path.insert(0, _root)
from scripts.backend import pick_backend
from scripts.log_util import JsonlLogger

def sh(*args): print('>', ' '.join(args)); return subprocess.check_call(list(args))

if __name__=='__main__':
  import os as _os

  ap = argparse.ArgumentParser()
  ap.add_argument('--text', required=True)
  ap.add_argument('--voice', required=True)
  ap.add_argument('--device-order', default=_os.environ.get('TTS_DEVICE_ORDER','rocm,dml,cpu'))
  ap.add_argument('--gpu-workers', type=int, default=1)
  ap.add_argument('--cpu-workers', type=int, default=6)
  ap.add_argument('--chunk-sec', type=int, default=int(_os.environ.get('TTS_CHUNK_SECONDS','20')))
  ap.add_argument('--crossfade-ms', type=int, default=int(_os.environ.get('TTS_CROSSFADE_MS','8')))
  ap.add_argument('--sr', type=int, default=int(_os.environ.get('TTS_SAMPLE_RATE','48000')))
  ap.add_argument('--out', required=True)
  ap.add_argument('--cpu-only', action='store_true')
  ap.add_argument('--run-dir', default=None, help='Optional runs/<timestamp> root for logs/artifacts')
  args = ap.parse_args()

  logs = JsonlLogger(args.run_dir)
  logs.log("pipeline_start", text=args.text, out=args.out, device_order=args.device_order)

  os.makedirs(os.path.dirname(args.out), exist_ok=True)

  # Backend selection
  backend = pick_backend(args.device_order)
  print('Backend selected:', backend)
  logs.log("backend_selected", backend=backend)
  # Propagate to worker so it can pick DML/ROCm/CUDA deterministically
  os.environ["TTS_BACKEND"] = backend

  # Chunk text
  chunks_jsonl = os.path.join(os.path.dirname(args.out), 'chunks.jsonl')
  t0 = time.time()
  sh(sys.executable, 'scripts/tts_chunk.py', '--text', args.text, '--out', chunks_jsonl, '--chunk-sec', str(args.chunk_sec))
  logs.log("chunking_done", elapsed=round(time.time()-t0,3), chunks_jsonl=chunks_jsonl)

  # Worker (logged variants)
  workdir = os.path.join(os.path.dirname(args.out), 'chunks')
  os.makedirs(workdir, exist_ok=True)
  if backend != 'cpu' and not args.cpu_only:
      sh(sys.executable, 'scripts/tts_worker_gpu_logged.py', chunks_jsonl, workdir, args.voice, logs.run_dir.as_posix())
  else:
      sh(sys.executable, 'scripts/tts_worker_cpu_logged.py', chunks_jsonl, workdir, args.voice, logs.run_dir.as_posix())

  # Join + normalize with ffmpeg check
  sh(sys.executable, 'scripts/tts_join_checked.py', '--chunks', os.path.join(workdir, '*.wav'),
     '--out', args.out, '--sr', str(args.sr), '--crossfade-ms', str(args.crossfade_ms),
     '--run-dir', logs.run_dir.as_posix())

  logs.log("pipeline_end", out=args.out)
  print('All done:', args.out)

# USAGE (OPTIONAL “PLUS” PATH)
# Windows:
#   python scripts\\tts_cli_plus.py --text texts\\book.txt --voice .cache\\voice.pt --device-order dml,cpu --out runs\\win\\render.wav
#
# Ubuntu:
#   python scripts/tts_cli_plus.py --text texts/book.txt --voice .cache/voice.pt --device-order rocm,dml,cpu --out runs/linux/render.wav
#
# OUTPUTS
# - JSONL logs: runs/<timestamp>/logs/render.jsonl
#   Contains: backend selection, chunk timings, per-chunk RTF, join timings, final artifact path.
# - Normalized WAV: <out path>, with the same audio behavior as the original pipeline.
