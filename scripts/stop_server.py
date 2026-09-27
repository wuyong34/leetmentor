"""关闭静默运行的 LeetMentor 服务(pythonw.exe 进程)。"""
from __future__ import annotations

import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT = (
    "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | "
    "Where-Object { $_.CommandLine -match 'server.main' } | "
    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Output $_.ProcessId }"
)


def main() -> int:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", SCRIPT],
        capture_output=True, text=True,
    )
    output = (result.stdout or "").strip()
    if output:
        pids = ", ".join(p for p in output.splitlines() if p.strip())
        print(f"已停止服务进程:{pids}")
        return 0
    print("没有发现正在运行的服务(可能已经停止)。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
