"""命令行测试工具:不用打开浏览器,直接体验某道题的三层讲解。

用法(在项目根目录执行):
    .venv\\Scripts\\python scripts\\test_cli.py                    # 默认 two-sum,生成三层
    .venv\\Scripts\\python scripts\\test_cli.py two-sum --level 1  # 只看第 1 层
    .venv\\Scripts\\python scripts\\test_cli.py two-sum --lang java
    .venv\\Scripts\\python scripts\\test_cli.py two-sum --force    # 忽略缓存重新生成
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server import cache, languages, leetcode, llm, prompts  # noqa: E402
from server.config import load_config  # noqa: E402
from server.html_text import html_to_text  # noqa: E402

LEVEL_NAMES = {1: "第 1 层 · 思路引导", 2: "第 2 层 · 详细步骤", 3: "第 3 层 · 参考代码"}


async def generate_level(cfg: dict, problem: dict, level: int, lang: str,
                         prior: dict[int, str], force: bool) -> str:
    content = html_to_text(problem["content"])
    problem = dict(problem, content=content)

    cache_lang = lang if level == 3 else "-"
    key = cache.make_key(problem["slug"], level, cache_lang, cfg["model"], prompts.PROMPT_VERSION)

    if not force:
        cached = cache.get(key)
        if cached:
            print("(来自缓存)")
            return cached

    messages = prompts.build_messages(problem, level, lang, prior)
    parts: list[str] = []
    async for text in llm.stream_chat(cfg, messages):
        print(text, end="", flush=True)
        parts.append(text)
    print()
    full = "".join(parts).strip()
    if full:
        cache.put(key, problem["slug"], level, cache_lang, cfg["model"],
                  prompts.PROMPT_VERSION, full)
    return full


async def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="LeetMentor 命令行测试")
    parser.add_argument("slug", nargs="?", default="two-sum", help="题目 slug(默认 two-sum)")
    parser.add_argument("--level", type=int, choices=[1, 2, 3], help="只生成某一层(默认全部)")
    parser.add_argument("--lang", default=None, help="代码语言(第 3 层用,默认取配置)")
    parser.add_argument("--force", action="store_true", help="忽略缓存,强制重新生成")
    args = parser.parse_args()

    cfg = load_config()
    lang = languages.normalize(args.lang or cfg["default_language"])

    print(f"正在获取题目: {args.slug} …")
    problem = await leetcode.fetch_question(args.slug)
    if not problem:
        print("[失败] 未能获取题目。检查 slug 是否正确、网络是否可用。")
        return 1
    print(f"《{problem['title']}》 难度: {problem['difficulty']}  标签: {'、'.join(problem['tags']) or '无'}")
    print(f"模型: {cfg['model']}   语言: {languages.display_name(lang)}\n")

    levels = [args.level] if args.level else [1, 2, 3]
    prior: dict[int, str] = {}
    for level in levels:
        print("=" * 60)
        print(f"{LEVEL_NAMES[level]}")
        print("=" * 60)
        try:
            prior[level] = await generate_level(cfg, problem, level, lang, prior, args.force)
        except llm.LLMError as exc:
            print(f"\n[失败] {exc}")
            return 2
        print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(130)
