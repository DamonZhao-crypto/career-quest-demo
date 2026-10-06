"""Offline transcription with short vocabulary hints and explicit review."""

import os
import re
import tempfile

SPEECH_MODELS = {"small · 清晰优先（推荐）": "small", "base · 速度优先": "base"}


class SpeechInputError(ValueError):
    """Safe user-facing recording errors."""


def vocabulary_hints(custom=""):
    # Only explicitly requested terms; job/profile terms can leak into the answer.
    terms = []
    for term in re.split(r"[,，、;；\n\t]+", custom):
        term = term.strip()[:24]
        if term and term not in terms:
            terms.append(term)
    return "，".join(terms[:8])[:120]


def repetition_detected(text):
    # Ignore punctuation to catch e.g. Figma:岗位 repeated with stray symbols.
    # Ordinary stutters and repeated technical terms are not enough to trigger it.
    compact = re.sub(r"[\W_]+", "", text, flags=re.UNICODE)[:10000]
    return bool(re.search(r"(.{8,80}?)\1{2,}|(.{4,40}?)\2{4,}", compact))


def quality_issues(text):
    issues = []
    if repetition_detected(text):
        issues.append("repetition")
    if "\ufffd" in text:
        issues.append("invalid_character")
    return issues


def _decode(model, audio_path, vocabulary, use_vad, retry=False):
    segments, _ = model.transcribe(
        audio_path, language="zh", task="transcribe", beam_size=5,
        # A fixed 0 disables the built-in fallback on poor/repetitive decoding.
        temperature=(0.0, 0.2, 0.4), condition_on_previous_text=False,
        compression_ratio_threshold=2.4, log_prob_threshold=-1.0,
        vad_filter=use_vad,
        vad_parameters={"min_silence_duration_ms": 1000, "speech_pad_ms": 400},
        initial_prompt=None, hotwords=vocabulary or None,
        # Apply additional constraints only to an already suspicious recording.
        repetition_penalty=1.08 if retry else 1.0,
        no_repeat_ngram_size=12 if retry else 0,
    )
    # Consume while the temporary recording is still present.
    return list(segments)


def transcribe_recording(raw, model, vocabulary="", use_vad=True):
    if not raw:
        raise SpeechInputError("请先录制一段回答。")
    if len(raw) > 10 * 1024 * 1024:
        raise SpeechInputError("录音请控制在 10 MB 以内。")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temporary:
        temporary.write(raw)
        audio_path = temporary.name
    try:
        pieces = _decode(model, audio_path, vocabulary_hints(vocabulary), use_vad)
        text = "".join(piece.text for piece in pieces).strip()
        original_text = text
        warnings = []
        retried = False
        if quality_issues(text):
            retried = True
            # Re-run audio, never guess or delete chunks from the user's answer.
            retry_pieces = _decode(model, audio_path, "", use_vad, retry=True)
            retry_text = "".join(piece.text for piece in retry_pieces).strip()
            # Keep the first result if retry is empty or has more problem types.
            if retry_text and len(quality_issues(retry_text)) <= len(quality_issues(text)):
                pieces, text = retry_pieces, retry_text
            warnings.append("首次转写出现异常重复或字符，已自动重识别一次。请回听录音，重点核对原异常位置；重识别不保证内容准确。")
        if quality_issues(text):
            warnings.append("转写仍存在异常重复或字符。请修改后再确认提交；也可清空专业词汇并重录，避免识别错误影响评分。")
        if not text:
            raise SpeechInputError("没有识别到清晰的人声。请靠近麦克风重录；轻声回答也可尝试关闭静音过滤。")
        review = [{"start": round(piece.start, 1), "end": round(piece.end, 1), "text": piece.text.strip()}
                  for piece in pieces
                  if piece.avg_logprob < -0.8 or piece.no_speech_prob > 0.5 or quality_issues(piece.text)][:8]
        return {"text": text, "review": review, "warnings": warnings,
                "retried": retried, "original_text": original_text}
    finally:
        os.unlink(audio_path)
