"""从力扣获取题目信息(服务端兜底 + 命令行测试用)。

正常情况下题目内容由油猴脚本从页面提取;当脚本提取失败时,
本地服务可以用这个模块按 slug 再抓一次。
"""
from __future__ import annotations

import httpx

GRAPHQL_URL = "https://leetcode.cn/graphql/"

_QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    title
    translatedTitle
    difficulty
    content
    topicTags { name slug }
    hints
  }
}
"""

_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Referer": "https://leetcode.cn/",
}


_DIFFICULTY_CN = {"Easy": "简单", "Medium": "中等", "Hard": "困难"}


def normalize_question(raw: dict, slug: str) -> dict:
    """把力扣返回的字段整理成内部统一结构。"""
    title = raw.get("translatedTitle") or raw.get("title") or slug
    tags = [t.get("name", "") for t in (raw.get("topicTags") or []) if t.get("name")]
    difficulty = raw.get("difficulty", "")
    return {
        "slug": slug,
        "title": title,
        "difficulty": _DIFFICULTY_CN.get(difficulty, difficulty),
        "tags": tags,
        "content": raw.get("content") or "",
        "question_id": raw.get("questionId", ""),
        "hints": raw.get("hints") or [],
    }


async def fetch_question(slug: str, timeout: float = 15.0) -> dict | None:
    """按题目 slug 拉取题目,失败返回 None。"""
    payload = {
        "operationName": "questionData",
        "variables": {"titleSlug": slug},
        "query": _QUERY,
    }
    headers = dict(_HEADERS)
    headers["Referer"] = f"https://leetcode.cn/problems/{slug}/"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(GRAPHQL_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    question = (data.get("data") or {}).get("question")
    if not question:
        return None
    return normalize_question(question, slug)
