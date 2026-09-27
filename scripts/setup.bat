@echo off
title LeetMentor 安装
cd /d "%~dp0.."

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没有找到 Python。
  echo        请先到 https://www.python.org/downloads/ 安装 Python 3.10 或更高版本,
  echo        安装时务必勾选 "Add python.exe to PATH",然后重新运行本脚本。
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo 正在创建虚拟环境 .venv ...
  python -m venv .venv
)

echo 正在安装依赖(第一次需要一两分钟,请耐心等待)...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r server\requirements.txt
if errorlevel 1 (
  echo [错误] 依赖安装失败,请检查网络后重试。
  pause
  exit /b 1
)

echo.
echo 安装完成!下一步:
echo   1. 双击 scripts\start.bat 启动服务
echo   2. 按提示打开设置页填写 DeepSeek API Key
echo   3. 到浏览器安装油猴脚本(见 README.md)
pause
