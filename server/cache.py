"""SQLite 缓存:同一道题的同一层讲解只向 AI 请求一次。"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from .config import DATA_DIR

DB_PATH = DATA_DIR / "cache.db"
_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS hints (
    cache_key      TEXT PRIMARY KEY,
    slug           TEXT NOT NULL,
    level          INTEGER NOT NULL,
    language       TEXT NOT NULL,
    model          TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    content        TEXT NOT NULL,
    created_at     REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hints_slug ON hints(slug);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.executescript(_SCHEMA)
    return conn


def make_key(slug: str, level: int, language: str, model: str, prompt_version: str) -> str:
    """缓存键。

    L1/L2 与编程语言无关(讲解不含代码),language 传 "-" 以便复用;
    L3 与语言有关,language 传具体值。
    """
    return f"{prompt_version}|{model}|{slug}|{level}|{language}"


def get(cache_key: str) -> str | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT content FROM hints WHERE cache_key = ?", (cache_key,)
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()


def put(
    cache_key: str,
    slug: str,
    level: int,
    language: str,
    model: str,
    prompt_version: str,
    content: str,
) -> None:
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO hints
                   (cache_key, slug, level, language, model, prompt_version, content, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(cache_key) DO UPDATE SET
                     content = excluded.content,
                     created_at = excluded.created_at""",
                (cache_key, slug, level, language, model, prompt_version, content, time.time()),
            )
            conn.commit()
        finally:
            conn.close()


def stats() -> dict:
    with _lock:
        conn = _connect()
        try:
            total = conn.execute("SELECT COUNT(*) FROM hints").fetchone()[0]
            problems = conn.execute("SELECT COUNT(DISTINCT slug) FROM hints").fetchone()[0]
            return {"entries": total, "problems": problems}
        finally:
            conn.close()


def clear() -> int:
    """清空全部缓存,返回删除条数。"""
    with _lock:
        conn = _connect()
        try:
            count = conn.execute("SELECT COUNT(*) FROM hints").fetchone()[0]
            conn.execute("DELETE FROM hints")
            conn.commit()
            return count
        finally:
            conn.close()
