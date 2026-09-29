@echo off
chcp 936 >nul
title DEVSIM 环境自检
echo === Python 与依赖版本 ===
"D:\devsim\.venv\Scripts\python.exe" -c "import sys,devsim,numpy,matplotlib;print(\"Python:\",sys.version.split()[0]);print(\"devsim: OK (MKL/PARDISO loaded)\");print(\"numpy :\",numpy.__version__);print(\"mpl   :\",matplotlib.__version__)"
echo.
echo === 项目文件 ===
echo [sim] & dir /b "D:\devsim\sim"
echo [results] & dir /b "D:\devsim\results"
echo.
pause
