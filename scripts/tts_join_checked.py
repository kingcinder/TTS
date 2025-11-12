# Wrapper around the existing join (+ loudnorm) with FFmpeg check and logging
import argparse, glob, os, time, sys
# Allow absolute `scripts.*` imports even when executed directly
if __package__ in (None, ""):
    import pathlib as _pathlib
    _root = str(_pathlib.Path(__file__).resolve().parents[1])
    if _root not in sys.path:
        sys.path.insert(0, _root)
from scripts.log_util import JsonlLogger
from scripts.ffmpeg_check import assert_ffmpeg_available

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', default='runs/latest/chunks/*.wav')
    ap.add_argument('--out', default='runs/latest/render.wav')
    ap.add_argument('--sr', type=int, default=48000)
    ap.add_argument('--crossfade-ms', type=int, default=8)
    ap.add_argument('--run-dir', default=None)
    a = ap.parse_args()

    logs = JsonlLogger(a.run_dir)
    logs.log("join_start", chunks=a.chunks, out=a.out, sr=a.sr, crossfade_ms=a.crossfade_ms)

    assert_ffmpeg_available()

    # Dynamically import and call the existing joiner to avoid modifying it
    import importlib, importlib.util, sys, pathlib

    tts_join = None
    try:
        # Prefer package import first
        from scripts import tts_join as tts_join  # type: ignore
    except Exception:
        try:
            import importlib
            # Next, try top-level module (if scripts/ is on PYTHONPATH)
            tts_join = importlib.import_module("tts_join")
        except Exception:
            try:
                # Finally, load directly from scripts/tts_join.py
                join_path = (pathlib.Path(__file__).parent / "tts_join.py").resolve()
                spec = importlib.util.spec_from_file_location("tts_join", join_path)
                mod = importlib.util.module_from_spec(spec)
                assert spec and spec.loader
                spec.loader.exec_module(mod)
                tts_join = mod
            except Exception:
                tts_join = None
    t0 = time.time()
    # Re-implement tiny call using its function to respect your existing behavior
    files = sorted(glob.glob(a.chunks))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    # The original exposes crossfade_concat in top-level file; call via module attribute if present
    if tts_join is not None and hasattr(tts_join, "crossfade_concat"):
        tts_join.crossfade_concat(files, a.out, a.sr, a.crossfade_ms)
    else:
        # Fallback: shell out to python scripts/tts_join.py if implementation changes
        import subprocess, sys
        subprocess.check_call([
            sys.executable, 'scripts/tts_join.py',
            '--chunks', a.chunks, '--out', a.out,
            '--sr', str(a.sr), '--crossfade-ms', str(a.crossfade_ms)
        ])
    elapsed = time.time() - t0
    logs.log("join_end", out=a.out, elapsed=round(elapsed,3))

if __name__ == '__main__':
    main()
