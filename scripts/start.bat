@echo off
title LeetMentor 本地服务(关闭本窗口即停止)
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo 首次运行,先执行安装...
  call scripts\setup.bat
  if not exist ".venv\Scripts\python.exe" exit /b 1
)

".venv\Scripts\python.exe" -m server.main --open
pause
