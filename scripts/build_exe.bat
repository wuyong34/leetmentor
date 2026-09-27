@echo off
title LeetMentor 打包
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo 请先运行 scripts\setup.bat 安装环境。
  pause
  exit /b 1
)

echo [1/4] 安装 PyInstaller...
".venv\Scripts\python.exe" -m pip install pyinstaller --quiet
if errorlevel 1 (
  echo [错误] PyInstaller 安装失败,请检查网络。
  pause
  exit /b 1
)

echo [2/4] 打包 LeetMentorServer.exe(需要一两分钟)...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile ^
  --name LeetMentorServer ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan.on ^
  --hidden-import python_multipart ^
  --hidden-import pypdf ^
  --hidden-import openpyxl ^
  --paths . ^
  scripts\launcher.py
if errorlevel 1 (
  echo [错误] 打包失败,请查看上方日志。
  pause
  exit /b 1
)

echo [3/4] 组装便携包...
set PKG=dist\LeetMentor-portable
if exist "%PKG%" rmdir /s /q "%PKG%"
mkdir "%PKG%"
copy /y "dist\LeetMentorServer.exe" "%PKG%\LeetMentorServer.exe" >nul
copy /y "userscript\leetcode-mentor.user.js" "%PKG%\leetcode-mentor.user.js" >nul
copy /y "docs\使用说明.txt" "%PKG%\使用说明.txt" >nul

echo [4/4] 压缩为 zip...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\LeetMentor-portable\*' -DestinationPath 'dist\LeetMentor-v0.3.1-win64.zip' -Force"

echo.
echo 打包完成!
echo   便携包文件夹: dist\LeetMentor-portable\
echo   压缩包:       dist\LeetMentor-v0.3.1-win64.zip
echo   拷贝到其他电脑后:解压 - 双击 LeetMentorServer.exe - 按提示安装油猴脚本
pause
