"""LeetMentor 本地服务入口。

只监听 127.0.0.1,提供:
  GET  /health       健康检查(油猴脚本据此发现服务)
  GET  /setup        设置页(填写 API Key / 模型 / 默认语言)
  GET  /api/config   读取配置(不含 API Key 明文)
  POST /api/config   保存配置
  POST /api/test     测试 DeepSeek 连接
  POST /api/hint     生成讲解(SSE 流式)
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import socket
import sys
import threading
import urllib.request
import webbrowser

import uvicorn
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import cache, data_analysis, image_utils, languages, leetcode, llm, papers, prompts, toolbox
from .config import APP_VERSION, DATA_DIR, load_config, save_config
from .html_text import html_to_text
from .setup_page import SETUP_PAGE
from .study_page import STUDY_PAGE

logger = logging.getLogger("leetmentor")

app = FastAPI(title="LeetMentor", version=APP_VERSION)

# --- 安全:只允许力扣页面(以及本机页面/扩展)调用本地服务 ----
_SAFE_ORIGINS = {
    "https://leetcode.cn",
    "https://www.leetcode.cn",
    "https://leetcode.com",
    "https://www.leetcode.com",
}
_SAFE_ORIGIN_PREFIXES = (
    "http://127.0.0.1",
    "http://localhost",
    "chrome-extension://",
    "moz-extension://",
    "safari-web-extension://",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_SAFE_ORIGINS),
    allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    # 允许从 leetcode.cn 这类公网页面访问本机服务(Chrome/Edge 的 Private Network Access 预检)
    allow_private_network=True,
)


@app.middleware("http")
async def origin_guard(request: Request, call_next):
    """浏览器页面发起的跨域请求,Origin 不在白名单内直接拒绝,防止别的网站白嫖你的 API Key。"""
    origin = request.headers.get("origin")
    if origin and origin not in _SAFE_ORIGINS and not origin.startswith(_SAFE_ORIGIN_PREFIXES):
        return JSONResponse({"error": "origin not allowed"}, status_code=403)
    return await call_next(request)


# 实验数据的图表静态目录(数据模式生成 PNG,页面直接引用)
_CHARTS_DIR = DATA_DIR / "charts"
_CHARTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/charts", StaticFiles(directory=_CHARTS_DIR), name="charts")

# 工具箱转换后的文件目录(页面直接下载)
toolbox.CONVERT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=toolbox.CONVERT_DIR), name="files")


# ---------------------------------------------------------------- 数据模型
class HintRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=200)
    title: str = ""
    difficulty: str = ""
    tags: list[str] = []
    content: str = ""
    level: int = 1
    language: str = "python3"
    prior: dict[str, str] = {}
    force: bool = False


class ConfigRequest(BaseModel):
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None
    default_language: str | None = None
    vision_model: str | None = None


class SubjectRequest(BaseModel):
    text: str = Field(min_length=2, max_length=8000)
    context: str = ""
    question: str = ""
    history: list[dict] = []
    force: bool = False


class VisionRequest(BaseModel):
    image_base64: str = Field(min_length=16)
    mime: str = "image/png"
    question: str = ""
    context: str = ""
    history: list[dict] = []
    force: bool = False


# ---------------------------------------------------------------- 基础接口
@app.get("/health")
async def health() -> dict:
    cfg = load_config()
    return {
        "status": "ok",
        "app": "leetmentor",
        "version": APP_VERSION,
        "model": cfg["model"],
        "vision_model": cfg.get("vision_model", ""),
        "base_url": cfg["base_url"],
        "has_api_key": bool((cfg.get("api_key") or "").strip()),
        "default_language": cfg["default_language"],
        "languages": languages.choices(),
    }


@app.get("/api/config")
async def get_config() -> dict:
    cfg = load_config()
    return {
        "model": cfg["model"],
        "vision_model": cfg.get("vision_model", ""),
        "base_url": cfg["base_url"],
        "default_language": cfg["default_language"],
        "port": cfg["port"],
        "has_api_key": bool((cfg.get("api_key") or "").strip()),
    }


@app.post("/api/config")
async def post_config(req: ConfigRequest) -> dict:
    updates = {k: v for k, v in req.model_dump().items() if v}
    if "default_language" in updates:
        updates["default_language"] = languages.normalize(updates["default_language"])
    save_config(updates)
    return {"ok": True}


@app.post("/api/test")
async def test_llm() -> dict:
    ok, message = await llm.test_connection(load_config())
    return {"ok": ok, "message": message}


# ---------------------------------------------------------------- 讲解接口
def _sse(payload: dict) -> str:
    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


async def _hint_stream(req: HintRequest):
    try:
        if req.level not in (1, 2, 3):
            yield _sse({"type": "error", "message": f"层级必须是 1/2/3,收到 {req.level}"})
            return

        cfg = load_config()
        lang = languages.normalize(req.language)

        problem = {
            "slug": req.slug,
            "title": req.title or req.slug,
            "difficulty": req.difficulty,
            "tags": req.tags,
            "content": req.content,
        }
        # 页面提取失败时,服务端按 slug 兜底抓取
        if not problem["content"].strip():
            fetched = await leetcode.fetch_question(req.slug)
            if fetched:
                problem["title"] = problem["title"] if req.title else fetched["title"]
                problem["difficulty"] = problem["difficulty"] or fetched["difficulty"]
                problem["tags"] = problem["tags"] or fetched["tags"]
                problem["content"] = fetched["content"]
        if not problem["content"].strip():
            yield _sse({
                "type": "error",
                "message": "没能获取到题目内容。请刷新力扣页面后重试;如果题目是会员专享,可能无法读取。",
            })
            return
        problem["content"] = html_to_text(problem["content"])

        # L1/L2 与语言无关,缓存共用;L3 按语言分开缓存
        cache_lang = lang if req.level == 3 else "-"
        key = cache.make_key(
            req.slug, req.level, cache_lang, cfg["model"], prompts.PROMPT_VERSION
        )

        if not req.force:
            cached = cache.get(key)
            if cached:
                yield _sse({"type": "meta", "cached": True, "level": req.level})
                yield _sse({"type": "delta", "text": cached})
                yield _sse({"type": "done", "cached": True})
                return

        prior = {}
        for k, v in (req.prior or {}).items():
            try:
                prior[int(k)] = v
            except (TypeError, ValueError):
                continue

        messages = prompts.build_messages(problem, req.level, lang, prior)
        yield _sse({"type": "meta", "cached": False, "level": req.level, "model": cfg["model"]})

        parts: list[str] = []
        async for text in llm.stream_chat(cfg, messages):
            parts.append(text)
            yield _sse({"type": "delta", "text": text})

        full = "".join(parts).strip()
        if full:
            cache.put(
                key, req.slug, req.level, cache_lang, cfg["model"],
                prompts.PROMPT_VERSION, full,
            )
        yield _sse({"type": "done", "cached": False})
    except llm.LLMError as exc:
        yield _sse({"type": "error", "message": str(exc)})
    except Exception as exc:  # noqa: BLE001 - 兜底,避免流中断无提示
        logger.exception("生成讲解失败")
        yield _sse({"type": "error", "message": f"服务器内部错误:{exc}"})


@app.post("/api/hint")
async def hint(req: HintRequest) -> StreamingResponse:
    return StreamingResponse(
        _hint_stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------- 论文总结
async def _paper_stream(
    url: str,
    text: str,
    title: str,
    full_text: bool,
    force: bool,
    file: UploadFile | None,
    detail: bool = False,
):
    try:
        cfg = load_config()
        # 详细分析需要全文:arXiv 场景下自动切换为全文模式
        auto_full = False
        if detail and not full_text:
            full_text = True
            auto_full = True
        meta: dict = {"title": "", "authors": [], "abstract": "", "url": ""}
        body = ""
        body_kind = "abstract"  # abstract / fulltext / pasted
        source_label = ""
        source_id = ""

        if file is not None and (file.filename or ""):
            yield _sse({"type": "status", "text": "正在接收文件…"})
            data = await file.read()
            _, digest = await asyncio.to_thread(papers.save_upload, data, file.filename or "paper.pdf")
            source_id = f"file-{digest[:16]}"
            source_label = f"上传文件:{file.filename}"
            meta["title"] = (title or "").strip() or (file.filename or "上传的论文").rsplit(".", 1)[0]
            yield _sse({"type": "status", "text": "正在解析 PDF 文本…"})
            body, pages = await asyncio.to_thread(papers.extract_pdf_text, data)
            body_kind = "fulltext"
            source_label += f"({pages} 页)"
        elif url.strip():
            arxiv_id = papers.parse_arxiv_id(url)
            if not arxiv_id:
                yield _sse({
                    "type": "error",
                    "message": "这不是有效的 arXiv 链接或编号。示例:https://arxiv.org/abs/1706.03762 或 1706.03762",
                })
                return
            yield _sse({"type": "status", "text": f"正在获取论文信息(arXiv {arxiv_id})…"})
            meta = await papers.fetch_arxiv_meta(arxiv_id)
            source_id = f"arxiv-{arxiv_id}"
            source_label = f"arXiv {arxiv_id}"
            if full_text:
                download_msg = (
                    "详细分析需要全文,正在下载并解析全文(较大的论文可能需要一会儿)…"
                    if auto_full
                    else "正在下载并解析全文(较大的论文可能需要一会儿)…"
                )
                yield _sse({"type": "status", "text": download_msg})
                try:
                    pdf = await papers.get_arxiv_pdf(arxiv_id)
                    body, pages = await asyncio.to_thread(papers.extract_pdf_text, pdf)
                    body_kind = "fulltext"
                    source_label += f" · 全文 {pages} 页"
                except papers.PaperError as exc:
                    yield _sse({"type": "status", "text": f"全文获取失败({exc})改用摘要生成。"})
        elif text.strip():
            body = papers.clean_text(text)
            body_kind = "pasted"
            digest = hashlib.sha1(body.encode("utf-8")).hexdigest()
            source_id = f"text-{digest[:16]}"
            source_label = "粘贴的文字"
            meta["title"] = (title or "").strip() or "粘贴的论文内容"
        else:
            yield _sse({"type": "error", "message": "请提供 arXiv 链接、上传 PDF,或粘贴一段文字。"})
            return

        yield _sse({
            "type": "paper",
            "title": meta.get("title") or "",
            "authors": meta.get("authors") or [],
            "source": source_label,
            "kind": {"abstract": "基于摘要", "fulltext": "基于全文", "pasted": "基于粘贴文字"}.get(body_kind, ""),
            "url": meta.get("url") or "",
            "detail": detail,
        })

        # 简单分析(level 0)与详细分析(level 1)分开缓存
        depth_level = 1 if detail else 0
        prompt_version = prompts.paper_version(detail)
        key = cache.make_key(f"paper:{source_id}", depth_level, "-", cfg["model"], prompt_version)
        if not force:
            cached = cache.get(key)
            if cached:
                yield _sse({"type": "meta", "cached": True})
                yield _sse({"type": "delta", "text": cached})
                yield _sse({"type": "done", "cached": True})
                return

        messages = prompts.build_paper_messages(meta, body, body_kind, detail=detail)
        yield _sse({"type": "meta", "cached": False, "model": cfg["model"]})

        parts: list[str] = []
        async for piece in llm.stream_chat(cfg, messages):
            parts.append(piece)
            yield _sse({"type": "delta", "text": piece})

        full = "".join(parts).strip()
        if full:
            cache.put(key, f"paper:{source_id}", depth_level, "-", cfg["model"], prompt_version, full)
        yield _sse({"type": "done", "cached": False})
    except papers.PaperError as exc:
        yield _sse({"type": "error", "message": str(exc)})
    except llm.LLMError as exc:
        yield _sse({"type": "error", "message": str(exc)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("论文总结失败")
        yield _sse({"type": "error", "message": f"服务器内部错误:{exc}"})


@app.post("/api/paper")
async def paper_summary(
    url: str = Form(""),
    text: str = Form(""),
    title: str = Form(""),
    full_text: bool = Form(False),
    force: bool = Form(False),
    detail: bool = Form(False),
    file: UploadFile | None = File(None),
) -> StreamingResponse:
    return StreamingResponse(
        _paper_stream(url, text, title, full_text, force, file, detail),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------- 学科题
async def _subject_stream(req: SubjectRequest):
    try:
        cfg = load_config()
        material = req.text.strip()
        question = req.question.strip()
        is_followup = bool(question)

        history_pairs: list[dict] = []
        for item in (req.history or [])[-6:]:
            if isinstance(item, dict):
                history_pairs.append({
                    "q": str(item.get("q") or ""),
                    "a": str(item.get("a") or ""),
                })

        cache_key = None
        digest = None
        if not is_followup:
            digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]
            cache_key = cache.make_key(
                f"subject:{digest}", 0, "-", cfg["model"], prompts.SUBJECT_PROMPT_VERSION
            )
            if not req.force:
                cached = cache.get(cache_key)
                if cached:
                    yield _sse({"type": "meta", "cached": True, "mode": "explain"})
                    yield _sse({"type": "delta", "text": cached})
                    yield _sse({"type": "done", "cached": True})
                    return

        messages = prompts.build_subject_messages(
            material, req.context, question, history_pairs
        )
        yield _sse({
            "type": "meta",
            "cached": False,
            "mode": "followup" if is_followup else "explain",
            "model": cfg["model"],
        })

        parts: list[str] = []
        async for piece in llm.stream_chat(cfg, messages):
            parts.append(piece)
            yield _sse({"type": "delta", "text": piece})

        full = "".join(parts).strip()
        if full and cache_key and digest:
            cache.put(
                cache_key, f"subject:{digest}", 0, "-", cfg["model"],
                prompts.SUBJECT_PROMPT_VERSION, full,
            )
        yield _sse({"type": "done", "cached": False})
    except llm.LLMError as exc:
        yield _sse({"type": "error", "message": str(exc)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("学科题讲解失败")
        yield _sse({"type": "error", "message": f"服务器内部错误:{exc}"})


@app.post("/api/subject")
async def subject(req: SubjectRequest) -> StreamingResponse:
    return StreamingResponse(
        _subject_stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------- 实验数据分析
async def _data_stream(text: str, context: str, force: bool, file: UploadFile | None):
    try:
        cfg = load_config()
        if file is not None and (file.filename or ""):
            data = await file.read()
            filename = file.filename or "data.csv"
        elif text.strip():
            data = text.strip().encode("utf-8")
            filename = "粘贴的数据.csv"
        else:
            yield _sse({"type": "error", "message": "请上传 CSV / Excel 文件,或粘贴数据。"})
            return

        yield _sse({"type": "status", "text": "正在读取数据…"})
        df = await asyncio.to_thread(data_analysis.load_table, data, filename)
        digest = data_analysis.digest(data)

        yield _sse({"type": "status", "text": "正在计算统计并生成图表…"})
        info = await asyncio.to_thread(data_analysis.summarize, df)
        charts = await asyncio.to_thread(data_analysis.make_charts, df, digest)

        yield _sse({
            "type": "data",
            "rows": info["rows"],
            "cols": info["cols"],
            "charts": [{"name": c["name"], "url": c["url"]} for c in charts],
        })

        key = cache.make_key(f"data:{digest}", 0, "-", cfg["model"], prompts.DATA_PROMPT_VERSION)
        if not force:
            cached = cache.get(key)
            if cached:
                yield _sse({"type": "meta", "cached": True})
                yield _sse({"type": "delta", "text": cached})
                yield _sse({"type": "done", "cached": True})
                return

        stats_text = data_analysis.stats_markdown(df, info)
        messages = prompts.build_data_messages(context, stats_text, [c["name"] for c in charts])
        yield _sse({"type": "meta", "cached": False, "model": cfg["model"]})

        parts: list[str] = []
        async for piece in llm.stream_chat(cfg, messages):
            parts.append(piece)
            yield _sse({"type": "delta", "text": piece})

        full = "".join(parts).strip()
        if full:
            cache.put(key, f"data:{digest}", 0, "-", cfg["model"], prompts.DATA_PROMPT_VERSION, full)
        yield _sse({"type": "done", "cached": False})
    except data_analysis.DataError as exc:
        yield _sse({"type": "error", "message": str(exc)})
    except llm.LLMError as exc:
        yield _sse({"type": "error", "message": str(exc)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("数据分析失败")
        yield _sse({"type": "error", "message": f"服务器内部错误:{exc}"})


@app.post("/api/data")
async def data_endpoint(
    text: str = Form(""),
    context: str = Form(""),
    force: bool = Form(False),
    file: UploadFile | None = File(None),
) -> StreamingResponse:
    return StreamingResponse(
        _data_stream(text, context, force, file),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------- 识图解题
def _parse_history(raw) -> list[dict]:
    """解析前端传来的历史问答(JSON 字符串或列表,容错处理)。"""
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str) and raw:
        try:
            items = json.loads(raw)
        except (ValueError, TypeError):
            return []
    else:
        return []
    if not isinstance(items, list):
        return []
    pairs: list[dict] = []
    for item in items[-6:]:
        if isinstance(item, dict):
            pairs.append({"q": str(item.get("q") or ""), "a": str(item.get("a") or "")})
    return pairs


async def _vision_stream(
    image_bytes: bytes,
    question: str,
    context: str,
    history_pairs: list[dict],
    force: bool,
):
    try:
        cfg = load_config()
        prepared, mime = await asyncio.to_thread(image_utils.prepare_image, image_bytes)
        digest = hashlib.sha1(prepared).hexdigest()[:16]

        is_followup = bool(question.strip())
        vision_model = cfg.get("vision_model") or "deepseek-flash"

        key = None
        if not is_followup:
            key = cache.make_key(
                f"vision:{digest}", 0, "-", vision_model, prompts.VISION_PROMPT_VERSION
            )
            if not force:
                cached = cache.get(key)
                if cached:
                    yield _sse({"type": "meta", "cached": True, "mode": "explain"})
                    yield _sse({"type": "delta", "text": cached})
                    yield _sse({"type": "done", "cached": True})
                    return

        yield _sse({"type": "status", "text": "正在识别题目图片…"})
        image_b64 = image_utils.to_base64(prepared)
        messages = prompts.build_vision_messages(context, question, history_pairs, image_b64, mime)
        yield _sse({
            "type": "meta",
            "cached": False,
            "mode": "followup" if is_followup else "explain",
            "model": vision_model,
        })

        parts: list[str] = []
        async for piece in llm.stream_vision(cfg, messages):
            parts.append(piece)
            yield _sse({"type": "delta", "text": piece})

        full = "".join(parts).strip()
        if full and key:
            cache.put(key, f"vision:{digest}", 0, "-", vision_model, prompts.VISION_PROMPT_VERSION, full)
        yield _sse({"type": "done", "cached": False})
    except image_utils.ImageError as exc:
        yield _sse({"type": "error", "message": str(exc)})
    except llm.LLMError as exc:
        yield _sse({"type": "error", "message": str(exc)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("识图解题失败")
        yield _sse({"type": "error", "message": f"服务器内部错误:{exc}"})


@app.post("/api/vision")
async def vision(
    file: UploadFile = File(...),
    question: str = Form(""),
    context: str = Form(""),
    history: str = Form(""),
    force: bool = Form(False),
) -> StreamingResponse:
    """识图解题(multipart 上传,工作台使用)。"""
    read_error = ""
    try:
        raw = await file.read()
    except Exception as exc:  # noqa: BLE001
        raw = b""
        read_error = str(exc)

    if not raw:
        async def _error_stream():
            message = f"读取图片失败:{read_error}" if read_error else "图片是空的,请重新上传。"
            yield _sse({"type": "error", "message": message})

        return StreamingResponse(
            _error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )
    return StreamingResponse(
        _vision_stream(raw, question, context, _parse_history(history), force),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/vision-json")
async def vision_json(req: VisionRequest) -> StreamingResponse:
    """识图解题(JSON + base64,油猴脚本使用;两条传输通道都支持)。"""
    try:
        raw = base64.b64decode(req.image_base64, validate=False)
    except Exception:  # noqa: BLE001
        raw = b""

    if not raw:
        async def _error_stream():
            yield _sse({"type": "error", "message": "图片数据损坏,请重新粘贴或选择图片。"})

        return StreamingResponse(
            _error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )
    return StreamingResponse(
        _vision_stream(raw, req.question, req.context, _parse_history(req.history), req.force),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------- 文件转换工具箱
@app.post("/api/convert")
async def convert(
    kind: str = Form(...),
    options: str = Form("{}"),
    files: list[UploadFile] = File(...),
) -> JSONResponse:
    try:
        opts = json.loads(options or "{}")
        if not isinstance(opts, dict):
            opts = {}
    except (ValueError, TypeError):
        opts = {}

    payload: list[tuple[str, bytes]] = []
    for item in files:
        try:
            payload.append((item.filename or "file", await item.read()))
        except Exception as exc:  # noqa: BLE001
            return JSONResponse({"ok": False, "error": f"读取上传文件失败:{exc}"})

    try:
        outputs = await asyncio.to_thread(toolbox.run_conversion, kind, payload, opts)
    except toolbox.ToolError as exc:
        return JSONResponse({"ok": False, "error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("文件转换失败")
        return JSONResponse({"ok": False, "error": f"转换失败:{exc}"})

    return JSONResponse({
        "ok": True,
        "outputs": [
            {"name": name, "url": f"/files/{path.name}", "size": path.stat().st_size}
            for name, path in outputs
        ],
    })


# ---------------------------------------------------------------- 缓存管理(备用)
@app.get("/api/cache/stats")
async def cache_stats() -> dict:
    return cache.stats()


@app.post("/api/cache/clear")
async def cache_clear() -> dict:
    return {"ok": True, "removed": cache.clear()}


# ---------------------------------------------------------------- 页面
def _status_page() -> str:
    stats = cache.stats()
    cfg = load_config()
    key_state = "已配置 ✓" if (cfg.get("api_key") or "").strip() else "未配置 ✗"
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>LeetMentor 状态</title>
<style>
 body {{ font-family: "Segoe UI","Microsoft YaHei",system-ui,sans-serif; background:#f6f8fa;
        display:flex; justify-content:center; padding:60px 16px; color:#0f172a; }}
 .card {{ background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:32px 36px;
          box-shadow:0 4px 18px rgba(15,23,42,.06); max-width:560px; width:100%; }}
 h1 {{ margin:0 0 6px; font-size:22px; }} .sub {{ color:#64748b; font-size:13px; margin-bottom:24px; }}
 .row {{ display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px dashed #e2e8f0; font-size:14px; }}
 .row b {{ font-weight:600; }} a {{ color:#2563eb; text-decoration:none; }}
 .tip {{ margin-top:22px; font-size:13px; color:#64748b; line-height:1.8; }}
</style></head><body><div class="card">
 <h1>LeetMentor 本地服务</h1>
 <div class="sub">版本 {APP_VERSION} · 只在本机运行</div>
 <div class="row"><span>API Key</span><b>{key_state}</b></div>
 <div class="row"><span>当前模型</span><b>{cfg['model']}</b></div>
 <div class="row"><span>缓存讲解</span><b>{stats['entries']} 条 / {stats['problems']} 道题</b></div>
 <div class="tip">
   ← <a href="/study">学习工作台</a>:论文总结 / 学科题 / 实验数据<br>
   ← <a href="/setup">打开设置页</a> 填写 API Key<br>
   ← 回到浏览器,打开任意力扣题目页,点击右下角「✨ AI 讲解」
 </div>
</div></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    return _status_page()


@app.get("/setup", response_class=HTMLResponse)
async def setup() -> str:
    return SETUP_PAGE


@app.get("/study", response_class=HTMLResponse)
async def study() -> str:
    return STUDY_PAGE


# ---------------------------------------------------------------- 启动
def find_free_port(start: int, attempts: int = 5) -> int | None:
    """从 start 开始找一个可用端口(被占用时自动递增)。"""
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return None


_MUTEX_HANDLE = None


def _single_instance_ok() -> bool:
    """Windows 命名互斥体:保证同一时间只有一个服务实例(含启动竞态)。"""
    global _MUTEX_HANDLE
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(None, 0, "LeetMentorServer_SingleInstance")
        if not handle:
            return True
        _MUTEX_HANDLE = handle
        ERROR_ALREADY_EXISTS = 183
        return ctypes.get_last_error() != ERROR_ALREADY_EXISTS
    except Exception:  # noqa: BLE001
        return True


def _already_running(port: int) -> bool:
    """检查该端口上是否已经有一个 LeetMentor 服务(避免重复启动;绕过系统代理)。"""
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{port}/health", timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
            return data.get("app") == "leetmentor"
    except Exception:  # noqa: BLE001
        return False


def main() -> None:
    # pythonw(无控制台静默运行)时 stdout/stderr 是 None,uvicorn 会因 isatty() 崩溃,
    # 这里先兜底成安全流,再做 UTF-8 输出配置
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    # Windows 下输出被重定向(或 chcp 非 65001)时,避免中文/表情打印崩溃
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    cfg = load_config()
    default_port = int(cfg.get("port", 8765))
    if not _single_instance_ok():
        print("LeetMentor 服务已经在运行,无需重复启动。")
        return
    if _already_running(default_port):
        print(f"LeetMentor 服务已经在运行(端口 {default_port}),无需重复启动。")
        return
    port = find_free_port(default_port)
    if port is None:
        print("[错误] 8765~8769 端口都被占用,请关闭占用程序后重试。")
        sys.exit(1)

    url = f"http://127.0.0.1:{port}"
    print("=" * 56)
    print("  LeetMentor 本地服务已启动")
    print(f"  设置页:  {url}/setup")
    print(f"  状态页:  {url}/")
    print("  使用方式:浏览器打开力扣题目页,点击右下角「✨ AI 讲解」")
    print("  按 Ctrl+C 停止服务")
    print("=" * 56)

    should_open = ("--open" in sys.argv) or (
        getattr(sys, "frozen", False) and "--no-open" not in sys.argv
    )
    if should_open:
        threading.Timer(1.2, lambda: webbrowser.open(url + "/setup")).start()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
