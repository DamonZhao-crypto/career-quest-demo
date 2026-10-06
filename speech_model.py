"""CPU Whisper loading with separate download and startup diagnostics."""

import json
import logging
import traceback
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


LOGGER = logging.getLogger("career_quest.speech")


class SpeechServiceError(RuntimeError):
    """Only static diagnostic messages are shown to visitors."""

    def __init__(self, code, message):
        self.code = code
        super().__init__(f"{message}（诊断编号：{code}）")


def report_speech_failure(stage, error):
    """Log types and stack locations, without audio, prompts, tokens or URLs."""
    errors = []
    current, seen = error, set()
    while current is not None and id(current) not in seen and len(errors) < 6:
        seen.add(id(current))
        response = getattr(current, "response", None)
        errors.append({
            "type": type(current).__name__,
            "errno": getattr(current, "errno", None),
            "status": getattr(response, "status_code", None),
            "frames": [f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
                       for frame in traceback.extract_tb(current.__traceback__)[-8:]],
        })
        current = current.__cause__ or current.__context__
    versions = {}
    for name in ("faster-whisper", "ctranslate2", "huggingface-hub", "av", "onnxruntime"):
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = "missing"
    LOGGER.error("CAREER_QUEST_SPEECH %s", json.dumps({"stage": stage, "errors": errors, "versions": versions}))


def _complete_snapshot(path):
    for name in ("model.bin", "config.json", "tokenizer.json"):
        candidate = path / name
        if not candidate.is_file() or candidate.stat().st_size == 0:
            return False
    try:
        json.loads((path / "config.json").read_text(encoding="utf-8"))
        json.loads((path / "tokenizer.json").read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False
    return True


def load_cpu_model(model_size, model_dir):
    if model_size not in ("base", "small"):
        raise ValueError("不支持的语音模型。")
    try:
        from faster_whisper import WhisperModel
        from faster_whisper.utils import download_model
    except Exception as error:
        report_speech_failure("backend-import", error)
        raise SpeechServiceError("S01", "语音依赖未能启动，请管理员检查部署日志") from error

    model_dir = Path(model_dir)
    try:
        model_dir.mkdir(parents=True, exist_ok=True)
        snapshots = sorted(model_dir.glob(f"models--Systran--faster-whisper-{model_size}/snapshots/*"))
        model_path = next((str(path) for path in reversed(snapshots) if _complete_snapshot(path)), None)
    except OSError as error:
        report_speech_failure("model-storage", error)
        raise SpeechServiceError("S02", "服务器无法读写语音模型缓存，请管理员检查磁盘和权限") from error

    if model_path is None:
        try:
            # This is a public multilingual model; no Hugging Face token is needed.
            model_path = download_model(model_size, cache_dir=str(model_dir), use_auth_token=False)
        except Exception as error:
            report_speech_failure("model-download", error)
            raise SpeechServiceError("S03", "服务器未能下载语音模型，请稍后重试；持续失败请管理员查看下载日志") from error
    try:
        return WhisperModel(model_path, device="cpu", compute_type="int8", cpu_threads=2, num_workers=1,
                            local_files_only=True)
    except Exception as error:
        report_speech_failure("model-load", error)
        raise SpeechServiceError("S04", "语音模型未能加载，请管理员检查服务器内存及运行环境") from error
