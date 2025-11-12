import shutil, sys

def assert_ffmpeg_available():
    if shutil.which("ffmpeg") is None:
        msg = (
            "FFmpeg not found on PATH. Install it first.\n"
            "Windows (PowerShell): winget install Gyan.FFmpeg  (or: choco install ffmpeg)  and ensure ffmpeg.exe is on PATH\n"
            "Ubuntu: sudo apt-get install -y ffmpeg\n"
        )
        print(msg, file=sys.stderr)
        raise SystemExit(2)
