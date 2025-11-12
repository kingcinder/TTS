import argparse, os, sys, wave, math, struct, shutil
from pathlib import Path

def gen_beep(path: Path, sec=3.0, sr=16000, freq=440.0):
    n = int(sec * sr)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        for i in range(n):
            val = int(32767 * math.sin(2 * math.pi * freq * (i / sr)))
            w.writeframes(struct.pack("<h", val))

def gen_tts(path: Path, text="This is a demo voice sample for XTTS embedding."):
    try:
        import pyttsx3  # offline: SAPI5 on Windows, NSSpeech on macOS, eSpeak on Linux
        engine = pyttsx3.init()
        engine.save_to_file(text, str(path))
        engine.runAndWait()
        return True
    except Exception:
        return False

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="app/refs/demo.wav")
    ap.add_argument("--text", default="This is a demo voice sample for XTTS embedding.")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    ok = gen_tts(out, args.text)
    if not ok:
        # Fallback: generate a beep so downstream steps still run (quality will be poor — replace with real speech later).
        gen_beep(out, sec=3.0)
    print(f"Demo reference ready: {out}")
