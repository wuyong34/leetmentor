"""配置加载与保存。

配置优先级:环境变量 > data/config.json > 默认值。
配置文件位置:
  - 开发环境: 项目根目录/data/config.json
  - 打包后:   exe 所在目录/data/config.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "LeetMentor"
APP_VERSION = "0.3.1"

DEFAULTS = {
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "default_language": "python3",
    "port": 8765,
    # 识图(视觉模型):默认 deepseek-flash,复用上面的 Key;也可单独配置
    "vision_model": "deepseek-flash",
    "vision_base_url": "",
    "vision_api_key": "",
}


def base_dir() -> Path:
    """项目根目录(开发时为仓库根目录,打包后为 exe 所在目录)。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


DATA_DIR = base_dir() / "data"
CONFIG_PATH = DATA_DIR / "config.json"


def _load_file() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def load_config(use_env: bool = True) -> dict:
    """读取配置。use_env=True 时允许环境变量覆盖 API Key。"""
    cfg = _load_file()
    if use_env:
        env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if env_key:
            cfg["api_key"] = env_key
    return cfg


def save_config(updates: dict) -> dict:
    """保存部分字段到配置文件(只接受已知字段,空值不覆盖)。"""
    cfg = _load_file()
    for key, value in updates.items():
        if key in DEFAULTS and value is not None and value != "":
            cfg[key] = value
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return load_config()
