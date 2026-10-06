"""Entrypoint for the public Streamlit deployment; no credentials in source."""

import os
import runpy
from pathlib import Path

import streamlit as st


os.environ["CAREER_QUEST_PUBLIC"] = "true"
# Set these before faster-whisper/huggingface_hub is first imported.
# Plain HTTP downloads avoid the optional Xet native downloader on small hosts.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "30")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
os.environ.setdefault("CAREER_QUEST_DATA_DIR", str(Path(__file__).with_name("data")))
try:
    options = st.secrets.get("hosting", {})
except FileNotFoundError:
    options = {}
except Exception:
    st.error("网站部署配置无法读取，请管理员检查 Secrets 的 TOML 格式。")
    st.stop()

try:
    limit = int(options.get("daily_api_limit", os.environ.get("CAREER_QUEST_DAILY_API_LIMIT", "200")))
    if not 1 <= limit <= 10000:
        raise ValueError
    os.environ["CAREER_QUEST_DAILY_API_LIMIT"] = str(limit)
    model_size = str(options.get("whisper_model", os.environ.get("CAREER_QUEST_WHISPER_MODEL", "base")))
    if model_size not in ("base", "small"):
        raise ValueError
    os.environ["CAREER_QUEST_WHISPER_MODEL"] = model_size
except (ValueError, TypeError):
    st.error("网站部署参数有误：每日调用上限须为 1–10000 的整数，语音模型须为 base 或 small。")
    st.stop()

runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
