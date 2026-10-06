"""Small public-demo guards: private session IDs and bounded shared resources."""

import os
import secrets
import sqlite3
import threading
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path


class HostingError(ValueError):
    """Static messages that may be shown directly to visitors."""


def public_mode():
    return os.environ.get("CAREER_QUEST_PUBLIC", "").lower() in ("1", "true", "yes")


def data_dir():
    return Path(os.environ.get("CAREER_QUEST_DATA_DIR") or Path(__file__).with_name("data"))


def visitor_id(state):
    # Visitors never choose or look up another visitor's identifier.
    if "public_visitor_id" not in state:
        state["public_visitor_id"] = secrets.token_hex(32)
    return state["public_visitor_id"]


_api_slots = threading.BoundedSemaphore(2)
_speech_slot = threading.BoundedSemaphore(1)


@contextmanager
def speech_slot():
    if not _speech_slot.acquire(blocking=False):
        raise HostingError("其他访客正在识别录音，请稍后重试。你也可以先输入文字继续练习。")
    try:
        yield
    finally:
        _speech_slot.release()


def _reserve_daily_request():
    limit = int(os.environ.get("CAREER_QUEST_DAILY_API_LIMIT", "200"))
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).date().isoformat()
    with closing(sqlite3.connect(directory / "usage.db", timeout=15)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("CREATE TABLE IF NOT EXISTS usage (day TEXT PRIMARY KEY, calls INTEGER NOT NULL)")
            connection.execute("DELETE FROM usage WHERE day < ?", (day,))
            row = connection.execute("SELECT calls FROM usage WHERE day = ?", (day,)).fetchone()
            if row and row[0] >= limit:
                raise HostingError("今天的演示服务已达到使用上限，请明天再来练习。")
            connection.execute(
                "INSERT INTO usage(day, calls) VALUES (?, 1) "
                "ON CONFLICT(day) DO UPDATE SET calls = calls + 1", (day,)
            )


@contextmanager
def api_request():
    if not public_mode():
        yield
        return
    if not _api_slots.acquire(blocking=False):
        raise HostingError("当前练习人数较多，请稍后再试。你的当前回答会保留在本次会话中。")
    try:
        import streamlit as st
        if st.session_state.get("public_api_calls", 0) >= 60:
            raise HostingError("本次会话已达到演示次数上限，请先导出成长记录。")
        _reserve_daily_request()
        st.session_state.public_api_calls = st.session_state.get("public_api_calls", 0) + 1
        yield
    finally:
        _api_slots.release()
