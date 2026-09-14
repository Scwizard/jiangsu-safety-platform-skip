@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

rem ==========================================================
rem  "2026江苏省大学新生安全知识教育" 一键脚本 - 运行环境安装器
rem  项目: https://github.com/Scwizard/jiangsu-safety-platform-skip
rem  用法: 双击本文件即可，全程自动，按提示操作
rem ==========================================================

title 安全知识教育脚本 - 一键运行环境

set "ROOT=%~dp0"
set "DIRNAME=jiangsu-safety-platform-skip"
set "APPDIR=%ROOT%%DIRNAME%"
set "PY_VER=3.12.10"
set "REPO=Scwizard/jiangsu-safety-platform-skip
set "BRANCH=main"
set "PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple"
set "PIP_TRUST=pypi.tuna.tsinghua.edu.cn"
set "TMPZIP=%TEMP%\%DIRNAME%.zip"
set "TMPX=%TEMP%\%DIRNAME%_extract"
set "PYSETUP=%TEMP%\python-%PY_VER%-amd64.exe"
set "VERFILE=%ROOT%_project_version.txt"
set "VER_TMP=%TEMP%\%DIRNAME%_ver.txt"
set "VER_JSON=%TEMP%\%DIRNAME%_ver.json"

rem 强制重新下载: 把下一行改成 1，或者运行时加参数 -u
set "FORCE_UPDATE=0"
if /I "%~1"=="-u" set "FORCE_UPDATE=1"
if /I "%~1"=="--update" set "FORCE_UPDATE=1"

if /I "%~dp0"=="%APPDIR%\" (
    (echo  [错误] 请不要把本脚本放在 %DIRNAME% 文件夹里面运行。)
    (echo  请把 一键安装并运行.bat 复制到其它任意文件夹，再双击运行。)
    echo.
    pause
    endlocal
    exit /b 1
)

echo.
(echo  ============================================================)
(echo     江苏省大学新生安全知识教育 - 一键运行环境)
(echo  ============================================================)
echo.
(echo   脚本所在位置: %ROOT%)
(echo   项目安装位置: %APPDIR%)
echo.

rem ======================= 第 1 步: Python3 =======================
(echo ------------------------------------------------------------)
(echo  [1/4] 检查 Python 3 运行环境)
(echo ------------------------------------------------------------)
call :detect_python
if defined PYEXE (
    (echo   已检测到 Python: %PYEXE%)
    for /f "delims=" %%V in ('"%PYEXE%" -c "import sys;print(sys.version.split()[0])" 2^>nul') do (echo   版本: %%V)
) else (
    (echo   没有检测到 Python 3，准备自动下载并安装 ...)
    call :install_python
    if not defined PYEXE goto :fail_python
    (echo   Python 安装完成: %PYEXE%)
)

rem ======================= 第 2 步: 检查更新并下载 =======================
echo.
(echo ------------------------------------------------------------)
(echo  [2/4] 检查项目更新)
(echo ------------------------------------------------------------)

rem 本地现有版本是否完整
set "LOCAL_OK=0"
if exist "%APPDIR%\main.py" if exist "%APPDIR%\utils.py" if exist "%APPDIR%\database.db" set "LOCAL_OK=1"

rem 读取上次下载时记录的版本
set "LOCAL_SHA="
set "LOCAL_DATE="
if exist "%VERFILE%" (
    for /f "usebackq tokens=1,2 delims=," %%A in ("%VERFILE%") do (
        if not defined LOCAL_SHA (
            set "LOCAL_SHA=%%A"
            set "LOCAL_DATE=%%B"
        )
    )
)

rem 查询远端最新版本
call :get_remote_sha
if defined REMOTE_SHA (
    (echo   最新版本: !REMOTE_SHA:~0,7!  更新时间: %REMOTE_DATE%)
) else (
    (echo   无法连接 GitHub 查询最新版本)
)

if "%LOCAL_OK%"=="1" (
    (echo   本地版本: %LOCAL_SHA%)
) else (
    (echo   本地还没有可用的项目文件)
)

rem 判断是否需要下载
set "NEED_DL=1"
if "%FORCE_UPDATE%"=="1" (
    (echo   已开启强制更新，将重新下载)
) else (
    if "%LOCAL_OK%"=="1" (
        if defined REMOTE_SHA (
            if /I "!LOCAL_SHA!"=="!REMOTE_SHA!" (
                set "NEED_DL=0"
                (echo   本地已是最新版，无需重新下载)
            ) else (
                (echo   检测到新版本，准备更新)
            )
        ) else (
            set "NEED_DL=0"
            (echo   无法检查更新，保留当前已有的版本)
        )
    )
)

if "%NEED_DL%"=="0" goto :skip_download

if exist "%APPDIR%" (
    (echo   正在清理旧版本目录 ...)
    rmdir /s /q "%APPDIR%" >nul 2>&1
)
if exist "%TMPX%" rmdir /s /q "%TMPX%" >nul 2>&1
if exist "%TMPZIP%" del /f /q "%TMPZIP%" >nul 2>&1

set "DL_OK=0"
for %%U in (
    "https://github.com/%REPO%/archive/refs/heads/%BRANCH%.zip"
    "https://ghfast.top/https://github.com/%REPO%/archive/refs/heads/%BRANCH%.zip"
    "https://gh-proxy.com/https://github.com/%REPO%/archive/refs/heads/%BRANCH%.zip"
    "https://gh-proxy.net/https://github.com/%REPO%/archive/refs/heads/%BRANCH%.zip"
) do (
    if "!DL_OK!"=="0" (
        (echo   正在尝试下载: %%~U)
        call :dl "%%~U" "%TMPZIP%"
        if not errorlevel 1 (
            set "DL_OK=1"
            (echo   下载成功)
        )
    )
)

if "!DL_OK!"=="1" (
    mkdir "%TMPX%" >nul 2>&1
    (echo   正在解压 ...)
    tar -xf "%TMPZIP%" -C "%TMPX%" >nul 2>&1
    if errorlevel 1 (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue';Expand-Archive -LiteralPath '%TMPZIP%' -DestinationPath '%TMPX%' -Force" >nul 2>&1
    )
    set "SRC="
    for /d %%D in ("%TMPX%\*") do set "SRC=%%D"
    if defined SRC (
        move /y "!SRC!" "%APPDIR%" >nul 2>&1
    )
    if not exist "%APPDIR%" (
        for /d %%D in ("%TMPX%\*") do (
            if not exist "%APPDIR%" xcopy /e /y /i /q "%%D" "%APPDIR%\" >nul 2>&1
        )
    )
    rmdir /s /q "%TMPX%" >nul 2>&1
    del /f /q "%TMPZIP%" >nul 2>&1
)

if not exist "%APPDIR%\main.py" (
    (echo   ZIP 方式失败，尝试用 git 下载 ...)
    where git >nul 2>&1
    if not errorlevel 1 (
        git clone --depth 1 -b %BRANCH% "https://github.com/%REPO%.git" "%APPDIR%" >nul 2>&1
        if errorlevel 1 (
            if exist "%APPDIR%" rmdir /s /q "%APPDIR%" >nul 2>&1
            git clone --depth 1 -b %BRANCH% "https://ghfast.top/https://github.com/%REPO%.git" "%APPDIR%" >nul 2>&1
        )
    )
)

rem 记录本次下载对应的版本（只有真正下载成功才记录）
if exist "%APPDIR%\main.py" (
    if defined REMOTE_SHA (
        (echo %REMOTE_SHA%,%REMOTE_DATE%)>"%VERFILE%"
    ) else (
        if exist "%VERFILE%" del /f /q "%VERFILE%" >nul 2>&1
    )
)

:skip_download
if not exist "%APPDIR%\main.py" goto :fail_download

for %%F in ("%APPDIR%\utils.py" "%APPDIR%\database.db") do (
    if not exist "%%~F" (echo   警告: 缺少 %%~nxF)
)
(echo   项目已就绪: %APPDIR%)

rem ======================= 第 3 步: 安装依赖 =======================
echo.
(echo ------------------------------------------------------------)
(echo  [3/4] 安装依赖库 requests)
(echo ------------------------------------------------------------)
"%PYEXE%" -m pip --version >nul 2>&1
if errorlevel 1 (
    (echo   pip 不可用，正在尝试修复 ...)
    "%PYEXE%" -m ensurepip --default-pip >nul 2>&1
    "%PYEXE%" -m pip --version >nul 2>&1
    if errorlevel 1 "%PYEXE%" -m ensurepip --upgrade >nul 2>&1
)

set "INSTALLED=0"
if exist "%APPDIR%\requirements.txt" (
    (echo   按项目 requirements.txt 安装，使用清华镜像 ...)
    "%PYEXE%" -m pip install --disable-pip-version-check -r "%APPDIR%\requirements.txt" -i "%PIP_INDEX%" --trusted-host %PIP_TRUST%
    if not errorlevel 1 (
        set "INSTALLED=1"
    ) else (
        (echo   镜像失败，改用官方源重试 ...)
        "%PYEXE%" -m pip install --disable-pip-version-check -r "%APPDIR%\requirements.txt"
        if not errorlevel 1 set "INSTALLED=1"
    )
) else (
    (echo   未找到 requirements.txt，直接安装 requests，使用清华镜像 ...)
    "%PYEXE%" -m pip install --disable-pip-version-check requests -i "%PIP_INDEX%" --trusted-host %PIP_TRUST%
    if not errorlevel 1 (
        set "INSTALLED=1"
    ) else (
        (echo   镜像失败，改用官方源重试 ...)
        "%PYEXE%" -m pip install --disable-pip-version-check requests
        if not errorlevel 1 set "INSTALLED=1"
    )
)

"%PYEXE%" -c "import requests" >nul 2>&1
if errorlevel 1 goto :fail_pip
(echo   依赖安装完成)

rem ======================= 第 4 步: 运行 =======================
echo.
(echo ------------------------------------------------------------)
(echo  [4/4] 启动 main.py)
(echo ------------------------------------------------------------)
cd /d "%APPDIR%"
start "main.py 运行窗口" /d "%APPDIR%" "%COMSPEC%" /k ""%PYEXE%" main.py"
start "" explorer "%APPDIR%"
echo.
(echo  ============================================================)
(echo   全部完成！)
(echo   已在新窗口中运行 main.py，请在该窗口中按提示输入)
(echo   学校名称、账号和密码。)
echo.
(echo   项目目录: %APPDIR%)
(echo   以后想再次运行，重新双击本脚本即可。)
(echo  ============================================================)
echo.
pause
endlocal
exit /b 0

rem ==========================================================
rem                      子过程
rem ==========================================================

rem ---------- 查找本机 Python 3 ----------
:detect_python
set "PYEXE="
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PYEXE (
        set "CAND=%%P"
        if /I "!CAND:WindowsApps=!"=="!CAND!" (
            "%%P" -c "import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)" >nul 2>&1
            if not errorlevel 1 set "PYEXE=%%P"
        )
    )
)
if not defined PYEXE (
    where py >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%Q in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do (
            if not defined PYEXE if exist "%%Q" set "PYEXE=%%Q"
        )
    )
)
if not defined PYEXE (
    for %%D in ("%LOCALAPPDATA%\Programs\Python" "%ProgramFiles%\Python") do (
        if not defined PYEXE (
            for /d %%E in ("%%~D\Python3*") do (
                if not defined PYEXE if exist "%%E\python.exe" set "PYEXE=%%E\python.exe"
            )
        )
    )
)
if not defined PYEXE (
    for %%K in (HKCU HKLM) do (
        if not defined PYEXE (
            for /f "tokens=2,*" %%A in ('reg query "%%K\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /I "REG_SZ"') do (
                if not defined PYEXE if exist "%%B" set "PYEXE=%%B"
            )
        )
    )
)
if defined PYEXE (
    "%PYEXE%" -c "import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)" >nul 2>&1
    if errorlevel 1 set "PYEXE="
)
exit /b 0

rem ---------- 下载安装 Python ----------
:install_python
echo.
(echo   正在下载 Python %PY_VER% 安装包，约 25MB，请耐心等待 ...)
call :dl "https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-amd64.exe" "%PYSETUP%" 5000000
if errorlevel 1 (
    (echo   官方源太慢或失败，改用华为云镜像 ...)
    call :dl "https://mirrors.huaweicloud.com/python/%PY_VER%/python-%PY_VER%-amd64.exe" "%PYSETUP%" 5000000
)
if errorlevel 1 (
    if exist "%PYSETUP%" del /f /q "%PYSETUP%" >nul 2>&1
    (echo   Python 安装包下载失败。)
    exit /b 1
)
(echo   正在静默安装，约 1 到 3 分钟，请稍候 ...)
start /wait "" "%PYSETUP%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0 Include_doc=0 Include_dev=0
del /f /q "%PYSETUP%" >nul 2>&1
call :detect_python
if defined PYEXE exit /b 0
exit /b 1

rem ---------- 查询远端最新 commit 版本 ----------
:get_remote_sha
set "REMOTE_SHA="
set "REMOTE_DATE="
if exist "%VER_TMP%" del /f /q "%VER_TMP%" >nul 2>&1
for %%A in (
    "https://api.github.com/repos/%REPO%/commits/%BRANCH%"
    "https://ghfast.top/https://api.github.com/repos/%REPO%/commits/%BRANCH%"
) do (
    if not defined REMOTE_SHA (
        call :fetch_commit "%%~A"
        if exist "%VER_TMP%" (
            for /f "usebackq tokens=1,2 delims=," %%X in ("%VER_TMP%") do (
                if not defined REMOTE_SHA (
                    set "REMOTE_SHA=%%X"
                    set "REMOTE_DATE=%%Y"
                )
            )
            del /f /q "%VER_TMP%" >nul 2>&1
        )
    )
)
if not defined REMOTE_SHA call :fetch_commit_git
exit /b 0

rem ---------- 从 GitHub API 取一条 commit 信息: call :fetch_commit "url" ----------
:fetch_commit
if exist "%VER_JSON%" del /f /q "%VER_JSON%" >nul 2>&1
rem 优先用 curl（有些网络下 api.github.com 只认 curl，不认 .NET）
where curl >nul 2>&1
if not errorlevel 1 (
    curl.exe -s -L -m 12 -H "User-Agent: jsp-installer" -o "%VER_JSON%" "%~1" >nul 2>&1
)
if not exist "%VER_JSON%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try{[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;$j=(Invoke-WebRequest -Uri '%~1' -Headers @{'User-Agent'='jsp-installer'} -TimeoutSec 10 -UseBasicParsing).Content;[IO.File]::WriteAllText('%VER_JSON%',$j)}catch{exit 1}" >nul 2>&1
)
if not exist "%VER_JSON%" exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$j=[IO.File]::ReadAllText('%VER_JSON%');$c=$j|ConvertFrom-Json;if($c.sha.Length -ne 40){exit 1};($c.sha+','+$c.commit.author.date)|Out-File -FilePath '%VER_TMP%' -Encoding ascii}catch{exit 1}" >nul 2>&1
del /f /q "%VER_JSON%" >nul 2>&1
exit /b 0

rem ---------- 兜底: 用 git ls-remote 查版本 ----------
:fetch_commit_git
where git >nul 2>&1
if errorlevel 1 exit /b 1
for /f "tokens=1" %%S in ('git ls-remote "https://github.com/%REPO%.git" "%BRANCH%" 2^>nul') do (
    if not defined REMOTE_SHA set "REMOTE_SHA=%%S"
)
if defined REMOTE_SHA set "REMOTE_DATE=通过 git 查询"
exit /b 0

rem ---------- 通用下载: call :dl "url" "outfile" [最小字节数] ----------
:dl
set "DL_URL=%~1"
set "DL_OUT=%~2"
set "DL_MIN=%~3"
if "%DL_MIN%"=="" set "DL_MIN=1024"
if exist "%DL_OUT%" del /f /q "%DL_OUT%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue';[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;try{$w=New-Object System.Net.WebClient;$w.DownloadFile('%DL_URL%','%DL_OUT%');$s=(Get-Item -LiteralPath '%DL_OUT%').Length;if($s -lt %DL_MIN%){exit 2}}catch{exit 1}"
if errorlevel 1 (
    (echo   该地址下载失败)
    if exist "%DL_OUT%" del /f /q "%DL_OUT%" >nul 2>&1
    exit /b 1
)
exit /b 0

rem ---------- 错误出口 ----------
:fail_python
echo.
(echo  [失败] 无法安装 Python 3。)
(echo  请手动到 https://www.python.org/downloads/ 下载安装 Python 3)
(echo  安装时务必勾选 "Add python.exe to PATH"，然后重新双击本脚本。)
echo.
pause
endlocal
exit /b 1

:fail_download
echo.
(echo  [失败] 项目下载失败，可能是网络问题或 GitHub 访问不通。)
(echo  请换个网络（比如手机热点）后重新双击本脚本再试一次。)
echo.
pause
endlocal
exit /b 1

:fail_pip
echo.
(echo  [失败] requests 库安装失败。)
(echo  可以手动执行下面的命令试试：)
(echo    "%PYEXE%" -m pip install requests)
echo.
pause
endlocal
exit /b 1