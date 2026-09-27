"""实验数据分析:pandas 统计 + matplotlib 自动绘图 + 供 AI 解读的结构化摘要。

依赖(pandas / matplotlib)均为延迟导入,保证服务启动不被拖慢或阻断。
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from .config import DATA_DIR

CHARTS_DIR = DATA_DIR / "charts"

MAX_ROWS = 20000
MAX_COLS = 30
MAX_BYTES = 10 * 1024 * 1024


class DataError(Exception):
    """带用户可读中文提示的数据处理错误。"""


def _require_pandas():
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover
        raise DataError("缺少 pandas 依赖,请重新运行 scripts\\setup.bat 安装。") from exc
    return pd


def load_table(data: bytes, filename: str = "data.csv"):
    """读取 CSV / Excel 为 DataFrame。"""
    pd = _require_pandas()
    if not data:
        raise DataError("上传的内容是空的。")
    if len(data) > MAX_BYTES:
        raise DataError("数据太大(超过 10MB),请先裁剪后再上传。")

    name = (filename or "").lower()
    try:
        if name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(data))
        else:
            last_error = None
            df = None
            for encoding in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
                try:
                    df = pd.read_csv(io.BytesIO(data), encoding=encoding, sep=None, engine="python")
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
            if df is None:
                raise DataError(f"CSV 读取失败:{last_error}")
    except DataError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DataError(f"文件解析失败:{exc}") from exc

    if df.empty or len(df.columns) == 0:
        raise DataError("没有读到任何数据,请检查文件格式(第一行应为列名)。")
    if len(df) > MAX_ROWS:
        df = df.head(MAX_ROWS)
    if len(df.columns) > MAX_COLS:
        df = df.iloc[:, :MAX_COLS]
    df.columns = [str(c).strip() or f"列{i + 1}" for i, c in enumerate(df.columns)]
    return df


def summarize(df) -> dict:
    """计算描述统计,返回结构化字典。"""
    pd = _require_pandas()
    info: dict = {"rows": int(len(df)), "cols": int(len(df.columns)), "columns": []}
    for col in df.columns:
        series = df[col]
        entry: dict = {
            "name": str(col),
            "type": "数值" if pd.api.types.is_numeric_dtype(series) else "文本",
            "missing": int(series.isna().sum()),
            "unique": int(series.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(series):
            desc = series.describe()
            entry["stats"] = {
                "mean": _round(desc.get("mean")),
                "std": _round(desc.get("std")),
                "min": _round(desc.get("min")),
                "max": _round(desc.get("max")),
                "median": _round(series.median()),
            }
        else:
            top = series.astype(str).value_counts().head(3)
            entry["top_values"] = [f"{k}({v} 次)" for k, v in top.items()]
        info["columns"].append(entry)

    numeric = df.select_dtypes("number")
    if len(numeric.columns) >= 2:
        corr = numeric.corr(numeric_only=True)
        pairs = []
        cols = list(corr.columns)
        for i, a in enumerate(cols):
            for b in cols[i + 1:]:
                value = corr.loc[a, b]
                if value is not None and value == value:  # 排除 NaN
                    pairs.append((abs(float(value)), float(value), str(a), str(b)))
        pairs.sort(reverse=True)
        info["correlations"] = [
            {"pair": f"{a} × {b}", "r": round(r, 3)}
            for _, r, a, b in pairs[:5]
        ]
    return info


def stats_markdown(df, info: dict) -> str:
    """把统计结果整理成给 AI 看的文本(也用于展示的摘要)。"""
    lines = [f"数据规模:{info['rows']} 行 × {info['cols']} 列"]
    numeric_rows = []
    text_rows = []
    for col in info["columns"]:
        if "stats" in col:
            s = col["stats"]
            numeric_rows.append(
                f"| {col['name']} | {col['missing']} | {s['mean']} | {s['std']} | "
                f"{s['min']} | {s['max']} | {s['median']} |"
            )
        else:
            text_rows.append(
                f"- {col['name']}({col['type']}):常见取值 {'; '.join(col.get('top_values', []))}"
            )
    if numeric_rows:
        lines.append("")
        lines.append("数值列统计(缺失值 / 均值 / 标准差 / 最小 / 最大 / 中位数):")
        lines.append("| 列名 | 缺失 | 均值 | 标准差 | 最小 | 最大 | 中位数 |")
        lines.append("|---|---|---|---|---|---|---|")
        lines.extend(numeric_rows)
    if text_rows:
        lines.append("")
        lines.append("文本列:")
        lines.extend(text_rows)
    correlations = info.get("correlations") or []
    if correlations:
        lines.append("")
        lines.append("强相关列对(相关系数 r,|r| 从高到低):")
        for item in correlations:
            lines.append(f"- {item['pair']}: r = {item['r']}")
    return "\n".join(lines)


def make_charts(df, tag: str) -> list[dict]:
    """自动生成图表,返回 [{name, url, path}]。单个图失败不影响整体。"""
    charts: list[dict] = []
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["font.sans-serif"] = [
            "Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans",
        ]
        plt.rcParams["axes.unicode_minus"] = False
    except ImportError as exc:  # pragma: no cover
        raise DataError("缺少 matplotlib 依赖,请重新运行 scripts\\setup.bat 安装。") from exc

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    def save(fig, name: str) -> None:
        try:
            filename = f"{tag}_{len(charts)}_{_safe_name(name)}.png"
            path = CHARTS_DIR / filename
            fig.tight_layout()
            fig.savefig(path, dpi=110, bbox_inches="tight")
            charts.append({"name": name, "url": f"/charts/{filename}", "path": str(path)})
        except Exception:  # noqa: BLE001
            pass
        finally:
            plt.close(fig)

    numeric = list(df.select_dtypes("number").columns)

    # 1) 数值列分布直方图(最多 4 列)
    hist_cols = numeric[:4]
    if hist_cols:
        try:
            fig, axes = plt.subplots(1, len(hist_cols), figsize=(3.4 * len(hist_cols), 2.8), squeeze=False)
            for ax, col in zip(axes[0], hist_cols):
                df[col].dropna().plot(kind="hist", bins=12, ax=ax, color="#4f7cff", edgecolor="white")
                ax.set_title(str(col), fontsize=10)
                ax.set_ylabel("")
            save(fig, "数值分布直方图")
        except Exception:  # noqa: BLE001
            pass

    # 2) 趋势图:第一个数值列作为 x,其余数值列(最多 3 个)作为 y
    if numeric:
        x_col = numeric[0]
        y_cols = [c for c in numeric if c != x_col][:3]
        try:
            fig, ax = plt.subplots(figsize=(6.2, 3.2))
            if y_cols:
                for col in y_cols:
                    ax.plot(df[x_col], df[col], marker="o", markersize=2.6, linewidth=1.2, label=str(col))
                ax.set_xlabel(str(x_col))
                ax.legend(fontsize=8)
                save(fig, f"趋势图({x_col} 为横轴)")
            else:
                ax.plot(df.index, df[x_col], marker="o", markersize=2.6, linewidth=1.2, color="#4f7cff")
                ax.set_xlabel("行号")
                ax.set_ylabel(str(x_col))
                save(fig, f"趋势图({x_col})")
        except Exception:  # noqa: BLE001
            pass

    # 3) 相关散点图(取 |r| 最大的一对数值列)
    if len(numeric) >= 2:
        try:
            corr = df[numeric].corr().abs()
            best = None
            best_r = -1.0
            cols = list(numeric)
            for i, a in enumerate(cols):
                for b in cols[i + 1:]:
                    value = corr.loc[a, b]
                    if value == value and float(value) >= best_r:
                        best_r = float(value)
                        best = (a, b)
            if best:
                fig, ax = plt.subplots(figsize=(4.6, 3.4))
                ax.scatter(df[best[0]], df[best[1]], s=15, color="#e2574c", alpha=0.8)
                ax.set_xlabel(str(best[0]))
                ax.set_ylabel(str(best[1]))
                ax.set_title(f"相关性 r={best_r:.2f}", fontsize=10)
                save(fig, f"散点图({best[0]} 与 {best[1]})")
        except Exception:  # noqa: BLE001
            pass

    # 4) 分类列计数柱状图(最多 2 列,类别数 2~12 才有意义)
    text_cols = [c for c in df.columns if not _is_numeric(df[c])][:3]
    made = 0
    for col in text_cols:
        if made >= 2:
            break
        try:
            counts = df[col].astype(str).value_counts()
            if not (2 <= len(counts) <= 12):
                continue
            fig, ax = plt.subplots(figsize=(4.8, 2.9))
            counts.plot(kind="bar", ax=ax, color="#37a67d")
            ax.set_title(str(col), fontsize=10)
            save(fig, f"{col} 分类计数")
            made += 1
        except Exception:  # noqa: BLE001
            continue
    return charts


def digest(data: bytes) -> str:
    import hashlib

    return hashlib.sha1(data).hexdigest()[:16]


def _is_numeric(series) -> bool:
    pd = _require_pandas()
    return bool(pd.api.types.is_numeric_dtype(series))


def _round(value) -> float | None:
    try:
        if value is None:
            return None
        value = float(value)
        if value != value:  # NaN
            return None
        return round(value, 4)
    except (TypeError, ValueError):
        return None


def _safe_name(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|\s]+", "_", str(name))
    return name.strip("_")[:40] or "chart"
