import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

PINS = {
  'numpy': '1.26.4',
  'librosa': '0.10.2.post1',
  'soundfile': '0.12.1',
  'phonemizer': '3.3.0',
  'pydub': '0.25.1',
  'ffmpeg-normalize': '1.27.7',
  'TTS': '0.22.0'
}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_log(message, status="info", stage="setup"):
    log_file = os.environ.get("TTS_LOG_FILE")
    if not log_file:
        return
    entry = {
        "timestamp": timestamp(),
        "stage": stage,
        "status": status,
        "message": message,
    }
    log_dir = os.path.dirname(log_file) or "."
    os.makedirs(log_dir, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def sh(*args):
    print('>', ' '.join(args))
    write_log(f"Running {' '.join(args)}", stage="setup", status="start")
    subprocess.check_call(list(args))
    write_log(f"Finished {' '.join(args)}", stage="setup", status="success")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--backend', default='auto')
    a = ap.parse_args()

    os.makedirs('artifacts', exist_ok=True)
    os.makedirs('artifacts/models', exist_ok=True)
    os.makedirs('artifacts/logs', exist_ok=True)

    sh(sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', 'wheel', 'setuptools')
    pkgs = [f"{k}=={v}" for k, v in PINS.items()]
    sh(sys.executable, '-m', 'pip', 'install', *pkgs)

    def install_cpu_torch():
        sh(
            sys.executable, '-m', 'pip', 'install',
            '--index-url', 'https://download.pytorch.org/whl/cpu',
            'torch==2.3.1', 'torchaudio==2.3.1', 'torchvision==0.18.1'
        )

    # On Windows prefer DirectML unless user forces CPU.
    if platform.system() == 'Windows' and os.environ.get('TTS_FORCE_CPU', '0').lower() not in ('1','true','yes'):
        try:
            sh(sys.executable, '-m', 'pip', 'install', 'torch-directml')
            # Verify DirectML import (and that it provides a torch)
            sh(sys.executable, '-c', 'import torch_directml, torch; print(torch.__version__)')
            write_log('DirectML installed; skipping CPU torch wheels.', status='success', stage='setup')
        except Exception:
            write_log('DirectML install failed; falling back to CPU-only PyTorch wheels.', status='warn', stage='setup')
            install_cpu_torch()
    else:
        install_cpu_torch()

    write_log('Setup complete.', status='success', stage='setup')
    print('Setup complete.')
