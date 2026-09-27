"""大模型客户端(默认 DeepSeek,OpenAI 兼容接口,流式输出)。"""
from __future__ import annotations

import asyncio
import os
from typing import AsyncIterator

import openai
from openai import AsyncOpenAI


class LLMError(Exception):
    """带用户可读中文提示的模型调用错误。"""


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, openai.AuthenticationError):
        return "API Key 无效或已过期。请打开设置页检查 Key(首次使用请先在 DeepSeek 开放平台创建)。"
    if isinstance(exc, openai.RateLimitError):
        return "请求过于频繁或余额不足,请稍后再试,或检查 DeepSeek 账户余额。"
    if isinstance(exc, openai.APIConnectionError):
        return "无法连接 DeepSeek 服务,请检查网络(可能需要代理)后重试。"
    if isinstance(exc, openai.APIStatusError):
        return f"DeepSeek 服务返回错误(HTTP {exc.status_code}),请稍后重试。"
    return f"调用 AI 时出错:{exc}"


_FAKE_SNIPPET = """### 这题在考什么
(模拟输出,未调用真实 AI)主要考查数组的基本遍历和查找。

### 用自己的话复述题意
给定一个整数数组和一个目标值,找出两个数的下标,使它们的和为目标值。

### 动手前先想这几个问题
1. 如果允许两重循环,你会怎么写?要比较多少次?
2. 有没有办法记住"见过的数",避免重复扫描?

### 可以留意的工具和边界
想一想:什么结构可以快速判断"某个数出现过没有"?注意数组里可能有重复元素。
"""


async def _stream(
    cfg: dict,
    messages: list[dict],
    *,
    model: str,
    base_url: str | None,
    api_key: str | None,
    temperature: float,
) -> AsyncIterator[str]:
    """共享的流式调用实现(文本 / 视觉共用)。"""
    # 开发调试用:设置 LEETMENTOR_FAKE_LLM=1 时不真实调用 API,零成本测试流程
    if os.environ.get("LEETMENTOR_FAKE_LLM"):
        for i in range(0, len(_FAKE_SNIPPET), 16):
            await asyncio.sleep(0.01)
            yield _FAKE_SNIPPET[i : i + 16]
        return

    api_key = (api_key or "").strip()
    if not api_key:
        raise LLMError(
            "还没有配置 API Key。请打开 http://127.0.0.1:8765/setup 填写 DeepSeek API Key。"
        )

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url or "https://api.deepseek.com",
        timeout=180.0,
        max_retries=1,
    )
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=temperature,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            # deepseek-reasoner 的思维链字段是 reasoning_content,这里只输出正文
            text = getattr(delta, "content", None)
            if text:
                yield text
    except openai.OpenAIError as exc:
        raise LLMError(_friendly_error(exc)) from exc
    finally:
        await client.close()


def stream_chat(
    cfg: dict,
    messages: list[dict],
    temperature: float = 0.45,
) -> AsyncIterator[str]:
    """流式调用文本模型(默认 deepseek-chat),逐段产出文本。出错时抛出 LLMError。"""
    return _stream(
        cfg,
        messages,
        model=cfg.get("model") or "deepseek-chat",
        base_url=cfg.get("base_url"),
        api_key=cfg.get("api_key"),
        temperature=temperature,
    )


def stream_vision(
    cfg: dict,
    messages: list[dict],
    temperature: float = 0.4,
) -> AsyncIterator[str]:
    """流式调用视觉模型(默认 deepseek-flash,复用 DeepSeek Key)。"""
    return _stream(
        cfg,
        messages,
        model=cfg.get("vision_model") or "deepseek-flash",
        base_url=cfg.get("vision_base_url") or cfg.get("base_url"),
        api_key=cfg.get("vision_api_key") or cfg.get("api_key"),
        temperature=temperature,
    )


async def test_connection(cfg: dict) -> tuple[bool, str]:
    """设置页的"测试连接":发一个极小的请求验证 Key 是否可用。"""
    if os.environ.get("LEETMENTOR_FAKE_LLM"):
        return True, "模拟模式:跳过真实连接测试。"
    if not (cfg.get("api_key") or "").strip():
        return False, "尚未填写 API Key。"
    try:
        client = AsyncOpenAI(
            api_key=cfg["api_key"],
            base_url=cfg.get("base_url") or "https://api.deepseek.com",
            timeout=30.0,
            max_retries=0,
        )
        try:
            resp = await client.chat.completions.create(
                model=cfg.get("model") or "deepseek-chat",
                messages=[{"role": "user", "content": "回复:ok"}],
                max_tokens=8,
                temperature=0,
            )
        finally:
            await client.close()
        model = resp.model if hasattr(resp, "model") else cfg.get("model")
        return True, f"连接成功,模型 {model} 可用。"
    except openai.OpenAIError as exc:
        return False, _friendly_error(exc)
