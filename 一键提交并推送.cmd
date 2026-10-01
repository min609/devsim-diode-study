@echo off
chcp 936 >nul
setlocal
cd /d D:\devsim
title 一键提交并推送 - devsim

echo ============================================================
echo   一键提交并推送     项目: D:\devsim
echo ============================================================
echo.
echo [1/5] 当前改动：
echo.
git status --short
echo.
echo ------------------------------------------------------------
echo [2/5] 先从 GitHub 拉取最新内容（防止本地落后）
git pull
if errorlevel 1 echo.      警告：拉取失败（可能是网络问题或需要授权）
echo.
echo ------------------------------------------------------------
set "msg="
set /p "msg=[3/5] 请输入这次改了什么（直接回车取消）: "
if "%msg%"=="" goto :cancelled
echo.
echo [4/5] 提交中...
git add -A
git diff --cached --quiet
if not errorlevel 1 goto :nothing
git commit -m "%msg%"
if errorlevel 1 goto :commitfail
echo.
echo ------------------------------------------------------------
echo [5/5] 推送到 GitHub...
git push
if errorlevel 1 goto :pushfail
echo.
echo ============================================================
echo   全部完成！改动已经在 GitHub 上：
echo   https://github.com/min609/devsim-diode-study
echo ============================================================
goto :end

:cancelled
echo.
echo   你按了回车，已取消，什么都没做。
goto :end

:nothing
echo.
echo   没有检测到任何改动，不需要提交。
goto :end

:commitfail
echo.
echo   提交失败，请看上面的错误信息。
goto :end

:pushfail
echo.
echo ============================================================
echo   推送失败！常见原因：
echo     1. 需要重新授权（之前那个 token 已删除）
echo        解决：新建 token 后运行 git push，按提示输入
echo     2. 网络问题（检查 Nano 是否开着，它会劫持代理）
echo     3. 本地落后远程（先运行 git pull）
echo ============================================================
goto :end

:end
echo.
pause
