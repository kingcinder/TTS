import argparse, shutil
from pathlib import Path
from TTS.utils.manage import ModelManager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", required=True)
    args = parser.parse_args()

    destination = Path(args.dest)
    destination.mkdir(parents=True, exist_ok=True)
    manager = ModelManager()
    model_path, config_path = manager.download_model("tts_models/multilingual/multi-dataset/xtts_v2")
    # Preserve both files locally in a predictable place
    pth_target = destination / "xtts_v2.pth"
    cfg_target = destination / "config.json"
    shutil.copyfile(model_path, pth_target)
    shutil.copyfile(config_path, cfg_target)
    print(pth_target)


if __name__ == "__main__":
    main()
