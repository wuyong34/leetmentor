"""论文获取与解析。

- 解析 arXiv 链接/编号,拉取元数据(标题/作者/摘要)
- 下载 arXiv 全文 PDF 并提取文本
- 提取本地上传 PDF 的文本
"""
from __future__ import annotations

import hashlib
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from .config import DATA_DIR

UPLOAD_DIR = DATA_DIR / "uploads"

ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_PDF = "https://arxiv.org/pdf/{id}"

MAX_PDF_BYTES = 40 * 1024 * 1024      # 单个 PDF 上限 40MB
MAX_PDF_PAGES = 200                    # 只解析前 200 页
PROMPT_TEXT_LIMIT = 60000              # 送入提示词的正文上限(字符)

_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}


class PaperError(Exception):
    """带用户可读中文提示的论文处理错误。"""


# ---------------------------------------------------------------- arXiv 编号
def parse_arxiv_id(text: str) -> str | None:
    """从链接或编号中提取 arXiv ID,失败返回 None。

    支持:
      https://arxiv.org/abs/1706.03762
      https://arxiv.org/pdf/1706.03762v7
      1706.03762 / 1706.03762v2
      hep-th/9901001(老式编号)
    """
    text = (text or "").strip()
    if not text:
        return None

    m = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#\s]+)", text, re.I)
    if m:
        ident = m.group(1).rstrip("/")
        if ident.lower().endswith(".pdf"):
            ident = ident[:-4]
        if re.fullmatch(r"[a-z-]+/\d{7}(v\d+)?", ident, re.I):
            return ident
        first = ident.split("/")[0]
        return first if re.fullmatch(r"\d{4}\.\d{4,5}(v\d+)?", first) else None

    if re.fullmatch(r"\d{4}\.\d{4,5}(v\d+)?", text):
        return text
    if re.fullmatch(r"[a-z-]+/\d{7}(v\d+)?", text, re.I):
        return text
    return None


# ---------------------------------------------------------------- arXiv 元数据
async def fetch_arxiv_meta(arxiv_id: str, timeout: float = 25.0) -> dict:
    """通过 arXiv 官方 API 获取标题/作者/摘要。"""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(ARXIV_API, params={"id_list": arxiv_id}, headers=_UA)
            resp.raise_for_status()
            xml_text = resp.text
    except httpx.HTTPError as exc:
        raise PaperError(f"无法访问 arXiv,请检查网络(可能需要代理)。({exc.__class__.__name__})") from exc

    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise PaperError("arXiv 返回了无法解析的内容,请稍后再试。") from exc

    entry = root.find("a:entry", ns)
    if entry is None:
        raise PaperError("arXiv 没有返回结果。")
    entry_id = entry.findtext("a:id", "", ns)
    if "api/errors" in entry_id:
        raise PaperError(f"arXiv 上找不到这篇论文({arxiv_id}),请检查编号或链接。")

    title = " ".join((entry.findtext("a:title", "", ns) or "").split())
    if not title or title.lower() == "error":
        raise PaperError(f"arXiv 上找不到这篇论文({arxiv_id}),请检查编号或链接。")

    authors = [
        (a.findtext("a:name", "", ns) or "").strip()
        for a in entry.findall("a:author", ns)
    ]
    primary = entry.find("arxiv:primary_category", ns)
    return {
        "id": arxiv_id,
        "title": title,
        "abstract": (entry.findtext("a:summary", "", ns) or "").strip(),
        "authors": [a for a in authors if a],
        "published": (entry.findtext("a:published", "", ns) or "")[:10],
        "comment": (entry.findtext("arxiv:comment", "", ns) or "").strip(),
        "category": primary.get("term", "") if primary is not None else "",
        "url": f"https://arxiv.org/abs/{arxiv_id}",
    }


async def download_arxiv_pdf(arxiv_id: str, timeout: float = 120.0) -> bytes:
    """下载 arXiv 全文 PDF(限制大小)。"""
    url = ARXIV_PDF.format(id=arxiv_id)
    chunks: list[bytes] = []
    total = 0
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", url, headers=_UA) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_PDF_BYTES:
                        raise PaperError("这篇论文的 PDF 太大,无法在线总结;可以下载后截取重点段落粘贴到“粘贴文字”。")
                    chunks.append(chunk)
    except PaperError:
        raise
    except httpx.HTTPError as exc:
        raise PaperError(f"下载论文全文失败,请检查网络后重试。({exc.__class__.__name__})") from exc
    return b"".join(chunks)


def arxiv_cache_path(arxiv_id: str) -> Path:
    """arXiv PDF 的本地缓存路径(避免重复下载同一篇论文)。"""
    safe = re.sub(r"[^0-9A-Za-z._-]", "_", arxiv_id)
    return UPLOAD_DIR / f"arxiv-{safe}.pdf"


async def get_arxiv_pdf(arxiv_id: str) -> bytes:
    """优先使用本地已下载的 PDF,没有则下载并保存。"""
    path = arxiv_cache_path(arxiv_id)
    if path.exists():
        try:
            data = path.read_bytes()
            if data[:5].startswith(b"%PDF"):
                return data
        except OSError:
            pass
    data = await download_arxiv_pdf(arxiv_id)
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    except OSError:
        pass
    return data


# ---------------------------------------------------------------- PDF 文本提取
def extract_pdf_text(data: bytes) -> tuple[str, int]:
    """提取 PDF 文本,返回 (文本, 页数)。"""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PaperError("缺少 pypdf 依赖,请重新运行 scripts\\setup.bat 安装。") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:  # noqa: BLE001
                raise PaperError("这个 PDF 有密码保护,无法读取。") from exc
        if len(reader.pages) == 0:
            raise PaperError("这个 PDF 没有可读取的页面。")
        pages: list[str] = []
        for page in reader.pages[:MAX_PDF_PAGES]:
            try:
                pages.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001 - 单页失败不影响整体
                pages.append("")
        text = clean_text("\n".join(pages))
        if len(text.strip()) < 100:
            raise PaperError("这个 PDF 几乎提取不到文字(可能是扫描版图片),暂时无法总结。")
        return text, len(reader.pages)
    except PaperError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PaperError(f"PDF 解析失败:{exc}") from exc


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------- 上传文件
def save_upload(data: bytes, filename: str = "paper.pdf") -> tuple[Path, str]:
    """保存上传的 PDF,按内容去重,返回 (路径, 内容 sha1)。"""
    if not data:
        raise PaperError("上传的文件是空的。")
    if len(data) > MAX_PDF_BYTES:
        raise PaperError("文件太大(超过 40MB),请换一个小一点的 PDF。")
    if not data[:5].startswith(b"%PDF"):
        raise PaperError("这不是一个有效的 PDF 文件;目前只支持 PDF,请检查后重试。")

    digest = hashlib.sha1(data).hexdigest()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{digest[:16]}.pdf"
    if not path.exists():
        path.write_bytes(data)
    return path, digest


def trim_for_prompt(text: str, limit: int = PROMPT_TEXT_LIMIT) -> str:
    """超长正文掐头去尾(保留开头和结尾,中间标注省略)。"""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    head = int(limit * 0.6)
    tail = limit - head - 40
    return text[:head] + "\n\n……(中间内容省略)……\n\n" + text[-tail:]


def short_authors(authors: list[str], max_count: int = 6) -> str:
    if not authors:
        return "(未提供)"
    if len(authors) <= max_count:
        return "、".join(authors)
    return "、".join(authors[:max_count]) + f" 等 {len(authors)} 人"
