"""图片处理工具:识图前的压缩、尺寸控制(工具箱也会用到)。"""
from __future__ import annotations

import io

MAX_DIMENSION = 1600
JPEG_QUALITY = 90
MAX_INPUT_BYTES = 20 * 1024 * 1024


class ImageError(Exception):
    """带用户可读中文提示的图片处理错误。"""


def _require_pillow():
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise ImageError("缺少 Pillow 依赖,请重新运行 scripts\\setup.bat 安装。") from exc
    return Image


def prepare_image(data: bytes) -> tuple[bytes, str]:
    """把图片压缩到适合识别的尺寸,返回 (字节, mime)。

    - 长边限制到 1600px(控制视觉模型的 token 成本)
    - 大图统一转 JPEG(带透明通道的先垫白底)
    - 小尺寸 PNG 截图保留 PNG 原样,保证文字清晰
    """
    Image = _require_pillow()
    if not data:
        raise ImageError("图片是空的。")
    if len(data) > MAX_INPUT_BYTES:
        raise ImageError("图片太大(超过 20MB),请压缩后再试。")
    try:
        img = Image.open(io.BytesIO(data))
        if getattr(img, "is_animated", False):
            img.seek(0)
        img.load()
    except Exception as exc:  # noqa: BLE001
        raise ImageError(f"无法识别这张图片:{exc}") from exc

    width, height = img.size
    longest = max(width, height)
    needs_resize = longest > MAX_DIMENSION
    original_format = (img.format or "").upper()
    if original_format == "PNG" and not needs_resize and len(data) <= 2 * 1024 * 1024:
        return data, "image/png"

    if needs_resize:
        scale = MAX_DIMENSION / longest
        img = img.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))), Image.LANCZOS
        )
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue(), "image/jpeg"


def to_base64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")
