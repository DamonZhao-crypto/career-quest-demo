"""Offline transcription with short vocabulary hints and explicit review."""

import os
import re
import tempfile

SPEECH_MODELS = {"small · 清晰优先（推荐）": "small", "base · 速度优先": "base"}


class SpeechInputError(ValueError):
    """Safe user-facing recording errors."""


def vocabulary_hints(job, skills, custom=""):
    # Vocabulary only: never inject the expected answer or full resume.
    terms = []
    for source in (custom, job, "、".join(skills or [])):
        for term in re.split(r"[,，、;；\n\t]+", source):
            term = term.strip()[:36]
            if term and term not in terms:
                terms.append(term)
    return "，".join(terms[:24])[:240]


def transcribe_recording(raw, model, vocabulary="", use_vad=True):
    if not raw:
        raise SpeechInputError("请先录制一段回答。")
    if len(raw) > 10 * 1024 * 1024:
        raise SpeechInputError("录音请控制在 10 MB 以内。")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temporary:
        temporary.write(raw)
        audio_path = temporary.name
    try:
        segments, _ = model.transcribe(
            audio_path, language="zh", task="transcribe", beam_size=5,
            temperature=0.0, condition_on_previous_text=False,
            vad_filter=use_vad,
            vad_parameters={"min_silence_duration_ms": 1000, "speech_pad_ms": 400},
            initial_prompt="以下为简体中文职业面试录音。" + (f"可能出现的词汇：{vocabulary}。" if vocabulary else ""),
            hotwords=vocabulary or None,
        )
        pieces = list(segments)
        text = "".join(piece.text for piece in pieces).strip()
        if not text:
            raise SpeechInputError("没有识别到清晰的人声。请靠近麦克风重录；轻声回答也可尝试关闭静音过滤。")
        review = [{"start": round(piece.start, 1), "end": round(piece.end, 1), "text": piece.text.strip()}
                  for piece in pieces
                  if piece.avg_logprob < -0.8 or piece.no_speech_prob > 0.5][:8]
        return {"text": text, "review": review}
    finally:
        os.unlink(audio_path)
