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
if errorlevel 1 echo.      警告：拉取失败（网络问题或需要授权）
echo.
echo ------------------------------------------------------------
set "msg="
set /p "msg=[3/5] 请输入这次改了什么（直接回车=自动生成说明）: "
echo.
echo [4/5] 检查需要提交的改动...
git add -A
git diff --cached --quiet
if not errorlevel 1 goto :skipcommit
if "%msg%"=="" set "msg=自动提交"
git commit -m "%msg%"
if errorlevel 1 goto :commitfail
goto :dopush

:skipcommit
echo       没有新的改动需要提交（可能上次已经提交过了）
echo       继续检查是否有提交需要推送...
echo.

:dopush
echo ------------------------------------------------------------
echo [5/5] 推送到 GitHub...
echo.
echo       如果提示输入账号密码，请这样填：
echo         Username  -^>  min609
echo         Password  -^>  粘贴 token（屏幕不显示任何字符，是正常的）
echo.
git push
if errorlevel 1 goto :pushfail
echo.
echo ============================================================
echo   全部完成！改动已经在 GitHub 上：
echo   https://github.com/min609/devsim-diode-study
echo ============================================================
goto :end

:commitfail
echo.
echo   提交失败，请看上面的错误信息。
goto :end

:pushfail
echo.
echo ============================================================
echo   推送失败！常见原因：
echo     1. token 无效或输错了
echo        确认用的是【最新】创建的那个 token
echo        若需重来，先删除已存凭据:
echo            cmdkey /delete:git:https://github.com
echo     2. 网络问题（检查 Nano 是否开着，它会劫持代理）
echo     3. 本地落后远程（先运行 git pull）
echo ============================================================
goto :end

:end
echo.
pause
