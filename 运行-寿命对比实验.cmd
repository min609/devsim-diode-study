@echo off
chcp 936 >nul
title 03 - 少子寿命对比实验 (DEVSIM)
echo ============================================================
echo   少子寿命对比实验：tau = 10ns  vs  1us
echo   会跑两次仿真，并自动分解出"扩散电流"与"复合电流"
echo ============================================================
echo.
echo   [运行中] 大约需要 2-4 分钟，请耐心等待...
echo.
"D:\devsim\.venv\Scripts\python.exe" "D:\devsim\sim\03_compare_lifetime.py"
echo.
echo ============================================================
echo   运行结束！结果文件：
echo     对比图： D:\devsim\results\diode_lifetime_compare.png
echo     分解表： D:\devsim\results\diode_current_decomposition.csv
echo ============================================================
echo.
pause
