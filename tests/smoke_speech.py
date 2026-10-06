"""Real model download and CPU inference on generated, non-personal audio."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "30")

from speech import quality_issues, transcribe_recording
from speech_model import load_cpu_model

with tempfile.TemporaryDirectory(prefix="quest-speech-smoke-") as directory:
    directory = Path(directory)
    audio = directory / "sample.wav"
    subprocess.run(["espeak-ng", "-v", "cmn", "-s", "150", "-w", str(audio),
                    "你好，我是设计专业的学生。我在课程中设计了一张海报，负责版式和颜色。"], check=True)
    for size in ("base", "small"):
        model = load_cpu_model(size, directory / "models")
        # Exercise default transcription without vocabulary/prompt contamination.
        result = transcribe_recording(audio.read_bytes(), model, use_vad=True)
        assert result["text"].strip(), "Synthetic speech should produce a nonempty transcript"
        assert not quality_issues(result["text"]), "Synthetic result must not contain an obvious decoding loop"
        print(f"Real multilingual {size} model, CPU int8 and VAD smoke check passed.")
        print("Synthetic sample transcript:", result["text"])
        del model
