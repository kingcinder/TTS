import os, json, time, datetime, pathlib, threading

class JsonlLogger:
    def __init__(self, run_dir: str | None = None):
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        base = pathlib.Path("runs")
        self.run_dir = pathlib.Path(run_dir) if run_dir else base / ts
        self.logs_dir = self.run_dir / "logs"
        os.makedirs(self.logs_dir, exist_ok=True)
        self._path = self.logs_dir / "render.jsonl"
        self._lock = threading.Lock()

    @property
    def path(self): return str(self._path)

    def _stamp(self): return datetime.datetime.utcnow().isoformat() + "Z"

    def log(self, kind: str, **fields):
        rec = {"ts": self._stamp(), "kind": kind}
        rec.update(fields)
        line = json.dumps(rec, ensure_ascii=False)
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
