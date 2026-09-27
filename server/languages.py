"""力扣语言标识 ↔ 展示名 ↔ 提示词用名 的映射。

以后要支持新语言,只需要在这里加一行。
"""
from __future__ import annotations

# 力扣语言标识 -> (菜单展示名, 提示词中使用的语言名)
LANGUAGES: dict[str, tuple[str, str]] = {
    "python3": ("Python3(默认)", "Python 3"),
    "python": ("Python", "Python"),
    "java": ("Java", "Java"),
    "cpp": ("C++", "C++"),
    "c": ("C", "C"),
    "csharp": ("C#", "C#"),
    "javascript": ("JavaScript", "JavaScript (Node.js)"),
    "typescript": ("TypeScript", "TypeScript"),
    "golang": ("Go", "Go"),
    "rust": ("Rust", "Rust"),
    "kotlin": ("Kotlin", "Kotlin"),
    "swift": ("Swift", "Swift"),
    "php": ("PHP", "PHP"),
    "ruby": ("Ruby", "Ruby"),
    "scala": ("Scala", "Scala"),
    "dart": ("Dart", "Dart"),
    "elixir": ("Elixir", "Elixir"),
    "erlang": ("Erlang", "Erlang"),
    "racket": ("Racket", "Racket"),
}

DEFAULT_LANGUAGE = "python3"

# 页面上(编辑器语言下拉框)可能出现的文本 -> 力扣语言标识
TEXT_TO_LANG: dict[str, str] = {
    "python3": "python3",
    "python": "python3",
    "python 3": "python3",
    "java": "java",
    "c++": "cpp",
    "cpp": "cpp",
    "c": "c",
    "c#": "csharp",
    "csharp": "csharp",
    ".net": "csharp",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "go": "golang",
    "golang": "golang",
    "rust": "rust",
    "kotlin": "kotlin",
    "swift": "swift",
    "php": "php",
    "ruby": "ruby",
    "scala": "scala",
    "dart": "dart",
    "elixir": "elixir",
    "erlang": "erlang",
    "racket": "racket",
}


def normalize(lang: str | None) -> str:
    """把任意输入归一化为合法的力扣语言标识,非法时回落到默认语言。"""
    if not lang:
        return DEFAULT_LANGUAGE
    key = str(lang).strip().lower()
    if key in LANGUAGES:
        return key
    if key in TEXT_TO_LANG:
        return TEXT_TO_LANG[key]
    return DEFAULT_LANGUAGE


def display_name(lang: str) -> str:
    """菜单展示名(去掉"(默认)"后缀)。"""
    name = LANGUAGES.get(normalize(lang), LANGUAGES[DEFAULT_LANGUAGE])[0]
    return name.replace("(默认)", "")


def prompt_name(lang: str) -> str:
    """提示词中使用的语言名,如 "Python 3"、"C++"。"""
    return LANGUAGES.get(normalize(lang), LANGUAGES[DEFAULT_LANGUAGE])[1]


def choices() -> list[dict[str, str]]:
    """给前端(设置页/油猴面板)用的语言列表。"""
    return [
        {"id": key, "label": name.replace("(默认)", "")}
        for key, (name, _) in LANGUAGES.items()
    ]


# Markdown 代码块围栏标签(让前端高亮正确识别)
_FENCE_LABELS = {
    "python3": "python",
    "golang": "go",
    "csharp": "csharp",
    "cpp": "cpp",
    "javascript": "javascript",
    "typescript": "typescript",
}

def fence_label(lang: str) -> str:
    key = normalize(lang)
    return _FENCE_LABELS.get(key, key)

