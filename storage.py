"""Local demo progress storage. Resumes and API keys are never saved here."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = (Path(os.environ["CAREER_QUEST_DATA_DIR"]) / "career_quest.db"
           if os.environ.get("CAREER_QUEST_DATA_DIR") else Path(__file__).with_name("career_quest.db"))
QUEST_VERSION = 2


@contextmanager
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db():
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                job TEXT NOT NULL,
                stage TEXT NOT NULL,
                score INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                feedback TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(results)")}
        if "result_key" not in columns:
            connection.execute("ALTER TABLE results ADD COLUMN result_key TEXT")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS results_result_key ON results(result_key)")


def save_result(player_id, job, stage, score, passed, feedback, result_key=None):
    with _connect() as connection:
        cursor = connection.execute(
            """INSERT OR IGNORE INTO results
               (player_id, job, stage, score, passed, feedback, created_at, result_key)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                player_id,
                job,
                stage,
                score,
                int(passed),
                json.dumps(feedback, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                result_key,
            ),
        )
        return cursor.rowcount == 1


def get_history(player_id):
    with _connect() as connection:
        rows = connection.execute(
            """SELECT job, stage, score, passed, feedback, created_at
               FROM results WHERE player_id = ? ORDER BY id""",
            (player_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_history(player_id):
    with _connect() as connection:
        connection.execute("DELETE FROM results WHERE player_id = ?", (player_id,))
