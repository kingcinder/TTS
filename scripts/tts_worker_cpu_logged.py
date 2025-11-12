# CPU worker with JSONL logging (keeps original worker untouched)
import torch, json, sys, os, time
from TTS.api import TTS
# Allow absolute `scripts.*` imports even when executed directly
if __package__ in (None, ""):
    import pathlib as _pathlib
    _root = str(_pathlib.Path(__file__).resolve().parents[1])
    if _root not in sys.path:
        sys.path.insert(0, _root)
from scripts.log_util import JsonlLogger

def load_xtts():
    mdir = os.environ.get("TTS_MODEL_DIR")
    if mdir and os.path.exists(os.path.join(mdir,"xtts_v2.pth")) and os.path.exists(os.path.join(mdir,"config.json")):
        return TTS(model_path=os.path.join(mdir,"xtts_v2.pth"), config_path=os.path.join(mdir,"config.json"), gpu=False)
    return TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)

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
            print(f'CPU chunk {item["id"]} -> {out_wav} RTF={rtf:.2f}')
            logs.log("chunk_done", engine="cpu", chunk_id=item["id"], rtf=round(rtf,3),
                     elapsed=round(elapsed,3), seconds=round(dur,3), out=out_wav)

if __name__=='__main__':
    # args: jsonl input, out_dir, voice.pt, run_dir(optional)
    in_path, out_dir, voice_pt = sys.argv[1], sys.argv[2], sys.argv[3]
    run_dir = sys.argv[4] if len(sys.argv) > 4 else None
    logger = JsonlLogger(run_dir)
    logger.log("worker_start", engine="cpu", in_path=in_path, out_dir=out_dir)
    run_worker(in_path, out_dir, voice_pt, logger)
    logger.log("worker_end", engine="cpu")
