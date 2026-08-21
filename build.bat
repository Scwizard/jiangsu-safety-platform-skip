@echo off
chcp 65001 >nul
echo ========================================
echo  江苏省安全教育一键完成 - 打包脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查 PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller 未安装，正在安装...
    python -m pip install "pyinstaller>=6.3"
    if %errorlevel% neq 0 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
) else (
    echo PyInstaller 已安装
)

echo.
echo [2/3] 清理旧文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo [3/3] 开始打包...
pyinstaller --clean --noconfirm build.spec
if %errorlevel% neq 0 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo  打包完成！
echo  输出文件: dist\江苏省安全教育一键完成.exe
echo ========================================
echo.
pause