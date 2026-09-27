"""轻量 HTML → 文本转换(只用标准库)。

力扣题目的描述是 HTML,LLM 看不懂视觉样式,但保留段落/列表/代码块结构
能让它更准确地理解题意,同时比直接发 HTML 更省 token。
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

_BLOCK_TAGS = {
    "p", "div", "section", "article", "header", "footer", "main",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "table", "tr", "blockquote", "pre",
}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class _Converter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._pre_depth = 0
        self._skip_depth = 0  # 跳过 script/style 等

    # -- 输出小工具 -------------------------------------------------
    def _newline(self, count: int = 1) -> None:
        if not self._parts:
            return
        text = "".join(self._parts[-3:])
        trailing = len(text) - len(text.rstrip("\n"))
        need = count - trailing
        if need > 0:
            self._parts.append("\n" * need)

    # -- HTMLParser 回调 ---------------------------------------------
    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in ("script", "style"):
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "pre":
            self._pre_depth += 1
            self._newline(1)
            self._parts.append("```\n")
        elif tag == "br":
            self._parts.append("\n")
        elif tag == "li":
            self._newline(1)
            self._parts.append("- ")
        elif tag in ("p", "div", "section", "blockquote", "table", "tr"):
            self._newline(2 if tag in ("p", "div", "section", "blockquote") else 1)
        elif tag in _HEADING_TAGS:
            self._newline(2)
            self._parts.append("### ")
        elif tag == "code" and not self._pre_depth:
            self._parts.append("`")
        elif tag == "sup":
            self._parts.append("^")
        elif tag == "sub":
            self._parts.append("_")
        elif tag in ("td", "th"):
            self._parts.append(" ")
        elif tag == "img":
            alt = dict(attrs).get("alt", "")
            if alt:
                self._parts.append(f"[图片: {alt}]")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ("script", "style"):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "pre":
            self._pre_depth = max(0, self._pre_depth - 1)
            self._newline(1)
            self._parts.append("```\n")
        elif tag == "code" and not self._pre_depth:
            self._parts.append("`")
        elif tag in _BLOCK_TAGS and tag not in ("br",):
            self._newline(2 if tag in ("p", "div", "section", "blockquote") else 1)
        elif tag == "li":
            self._newline(1)

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._pre_depth:
            self._parts.append(data)
        else:
            # 普通文本里连续空白折叠成一个空格
            self._parts.append(re.sub(r"\s+", " ", data))

    # -- 结果 ---------------------------------------------------------
    def result(self) -> str:
        text = "".join(self._parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        return text.strip()


def html_to_text(html: str) -> str:
    """把 HTML 转为保留结构的纯文本。已经是纯文本时原样返回。"""
    if not html:
        return ""
    if "<" not in html:
        return html.strip()
    parser = _Converter()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # 解析异常时退回正则粗洗
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    return parser.result()
