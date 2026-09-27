"""PyInstaller 打包入口:生成 LeetMentorServer.exe。

这个文件不参与开发运行(开发时用 scripts\\start.bat),
只作为打包时 PyInstaller 的入口。
"""
from __future__ import annotations

import multiprocessing
import sys


def _main() -> None:
    # 打包后运行时,确保能找到 server 包(onefile 模式已内置)
    from server.main import main

    main()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    _main()
