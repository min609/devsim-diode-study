@echo off
chcp 936 >nul
title DEVSIM Python 交互终端
echo 已进入 DEVSIM 虚拟环境（可以直接 import devsim）。
echo 试一句： import devsim; print("devsim ok")
echo 退出：   exit()
echo.
"D:\devsim\.venv\Scripts\python.exe"
pause
