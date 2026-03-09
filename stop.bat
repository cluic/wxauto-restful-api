@echo off
REM wxauto API 停止脚本
REM 查找并停止运行在8000端口的服务

echo ========================================
echo wxautox4 RESTful API 服务停止脚本
echo ========================================
echo.

REM 查找占用8000端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    set PID=%%a
    goto :found
)

echo ❌ 未找到监听8000端口的服务
goto :end

:found
echo 🔍 找到进程 ID: %PID%

REM 尝试正常终止进程
echo 📤 正在停止服务...
taskkill /PID %PID% /T

REM 检查是否成功
timeout /t 2 /nobreak >nul
netstat -ano | findstr :8000 | findstr LISTENING >nul
if %errorlevel% equ 0 (
    echo.
    echo ⚠️  正常终止失败，尝试强制终止...
    taskkill /F /PID %PID% /T
    timeout /t 1 /nobreak >nul
)

REM 最终检查
netstat -ano | findstr :8000 | findstr LISTENING >nul
if %errorlevel% equ 0 (
    echo.
    echo ❌ 端口8000仍被占用，可能需要手动处理
    echo 💡 提示：可以重启电脑或使用其他端口
) else (
    echo.
    echo ✅ 服务已成功停止
)

:end
echo.
echo ========================================
pause
