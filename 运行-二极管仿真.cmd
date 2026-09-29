@echo off
chcp 936 >nul
title 01 - PN结二极管 I-V 仿真 (DEVSIM)
echo ============================================================
echo   DEVSIM 仿真：1D PN 结二极管 I-V 特性
echo ============================================================
echo.
echo   [运行中] 大约需要 1-2 分钟，请耐心等待...
echo.
"D:\devsim\.venv\Scripts\python.exe" "D:\devsim\sim\01_diode_iv.py"
echo.
echo ============================================================
echo   运行结束！结果文件在这里：
echo     图片： D:\devsim\results\diode_iv.png
echo     数据： D:\devsim\results\diode_iv.csv
echo ============================================================
echo.
pause
