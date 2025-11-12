# GPU/DML worker with JSONL logging (keeps original worker untouched)
import os, json, time, torch, sys, platform
from TTS.api import TTS
# Allow absolute `scripts.*` imports even when executed directly
if __package__ in (None, ""):
    import pathlib as _pathlib
    _root = str(_pathlib.Path(__file__).resolve().parents[1])
    if _root not in sys.path:
        sys.path.insert(0, _root)
from scripts.log_util import JsonlLogger

def device_string():
    # 1) honor explicit choice from CLI via env
    forced = os.environ.get('TTS_BACKEND','').lower()
    if forced in {'rocm','cuda','dml','cpu'}:
        return forced
    # 2) best-effort auto-detect
    if platform.system()=='Windows':
        try:
            import torch_directml as _dml  # noqa: F401
            return 'dml'
        except Exception:
            pass
    if torch.cuda.is_available():
        # Distinguish ROCm vs CUDA for accurate logging
        try:
            if getattr(torch.version, 'hip', None):
                return 'rocm'
        except Exception:
            pass
        return 'cuda'
    return 'cpu'

def load_xtts():
    dev = device_string()
    if dev == 'rocm':
        os.environ.setdefault('HIP_VISIBLE_DEVICES','0')
        mdir = os.environ.get("TTS_MODEL_DIR")
        if mdir and os.path.exists(os.path.join(mdir,"xtts_v2.pth")) and os.path.exists(os.path.join(mdir,"config.json")):
            return TTS(model_path=os.path.join(mdir,"xtts_v2.pth"), config_path=os.path.join(mdir,"config.json"), gpu=True)
        return TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
    if dev == 'dml':
        import torch_directml as _dml  # noqa: F401
        # keep gpu=False on DirectML, model still runs accelerated
        mdir = os.environ.get("TTS_MODEL_DIR")
        if mdir and os.path.exists(os.path.join(mdir,"xtts_v2.pth")) and os.path.exists(os.path.join(mdir,"config.json")):
            return TTS(model_path=os.path.join(mdir,"xtts_v2.pth"), config_path=os.path.join(mdir,"config.json"), gpu=False)
        return TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    mdir = os.environ.get("TTS_MODEL_DIR")
    if mdir and os.path.exists(os.path.join(mdir,"xtts_v2.pth")) and os.path.exists(os.path.join(mdir,"config.json")):
        return TTS(model_path=os.path.join(mdir,"xtts_v2.pth"), config_path=os.path.join(mdir,"config.json"), gpu=(dev!='cpu'))
    return TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=(dev!='cpu'))

def run_worker(in_path, out_dir, voice_pt, logs: JsonlLogger):
    os.makedirs(out_dir, exist_ok=True)
    model = load_xtts()
    spk_embed = torch.load(voice_pt, map_location='cpu')
    sr = getattr(getattr(model, "synthesizer", None), "output_sample_rate", 24000)
    with open(in_path,'r',encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            t0 = time.time()
            wav = model.tts(text=item["text"], speaker=spk_embed, language="en")
            dur = len(wav)/sr if sr else 0.0
            elapsed = time.time()-t0
            rtf = elapsed/max(1e-6, dur)
            out_wav = os.path.join(out_dir, f'{item["id"]:06d}.wav')
            model.save_wav(wav, out_wav)
            dev = device_string().upper()
            print(f'{dev} chunk {item["id"]} -> {out_wav} RTF={rtf:.2f}')
            logs.log("chunk_done", engine="gpu", device=device_string(), chunk_id=item["id"],
                     rtf=round(rtf,3), elapsed=round(elapsed,3), seconds=round(dur,3), out=out_wav)

if __name__=='__main__':
    in_path, out_dir, voice_pt = sys.argv[1], sys.argv[2], sys.argv[3]
    run_dir = sys.argv[4] if len(sys.argv) > 4 else None
    logger = JsonlLogger(run_dir)
    logger.log("worker_start", engine="gpu", device=device_string(), in_path=in_path, out_dir=out_dir)
    run_worker(in_path, out_dir, voice_pt, logger)
    logger.log("worker_end", engine="gpu", device=device_string())
