#!/bin/bash
# ==========================================================
#  "2026江苏省大学新生安全知识教育" 一键脚本 - macOS 运行环境
#  项目: https://github.com/Scwizard/jiangsu-safety-platform-skip
#
#  用法: 双击本文件即可，全程自动，按提示操作。
#        （这是 Windows 版「一键安装并运行.bat」的 macOS 对应版本）
#
#  可选参数:
#        -u / --update   强制重新下载一份最新的项目文件
#        --check         只做环境自检，不运行 main.py
# ==========================================================

# ---- 中文 + UTF-8 输出 ----
export LANG="${LANG:-en_US.UTF-8}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"
export PYTHONIOENCODING=utf-8

set -u

# ---- 颜色 ----
if [ -t 1 ]; then
  C_RESET=$'\033[0m'; C_TITLE=$'\033[1;36m'; C_OK=$'\033[1;32m'
  C_WARN=$'\033[1;33m'; C_ERR=$'\033[1;31m'; C_DIM=$'\033[2m'
else
  C_RESET=""; C_TITLE=""; C_OK=""; C_WARN=""; C_ERR=""; C_DIM=""
fi

printf '\033]0;江苏省安全知识教育脚本 - 一键运行环境\007' 2>/dev/null || true

hr()  { printf '%s\n' "------------------------------------------------------------"; }
say() { printf '%s\n' "$*"; }
ok()  { printf '%s\n' "${C_OK}$*${C_RESET}"; }
warn(){ printf '%s\n' "${C_WARN}$*${C_RESET}"; }
err() { printf '%s\n' "${C_ERR}$*${C_RESET}"; }

pause_exit() {
  echo
  printf '%s' "按回车键关闭本窗口 ..."
  read -r _ 2>/dev/null || true
  exit "${1:-0}"
}

# ==========================================================
#  基础路径
# ==========================================================

# 脚本自身所在目录（解析软链接，兼容 Finder 双击启动）
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  _dir="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$_dir/$SOURCE"
done
ROOT="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"

REPO="Scwizard/jiangsu-safety-platform-skip"
BRANCH="main"
DIRNAME="jiangsu-safety-platform-skip"
APPDIR="$ROOT/$DIRNAME"
VERFILE="$ROOT/_project_version.txt"
VENV="$ROOT/.venv"

PY_VER="3.12.10"
PIP_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple"
PIP_HOST="pypi.tuna.tsinghua.edu.cn"

FORCE_UPDATE=0
CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    -u|--update) FORCE_UPDATE=1 ;;
    --check)     CHECK_ONLY=1 ;;
  esac
done

PYEXE=""        # 最终使用的 python 解释器
PROJECT=""      # 最终使用的项目目录
RUNPY=""        # 运行时解释器（可能是 venv 里的 python）

# ==========================================================
#  子过程
# ==========================================================

# 判断某个解释器是否 >= 3.8
py_ok() {
  [ -n "$1" ] && [ -x "$1" ] && \
  "$1" -c 'import sys; sys.exit(0 if sys.version_info>=(3,8) else 1)' >/dev/null 2>&1
}

# ---- 查找本机 Python 3 ----
detect_python() {
  local cand
  # 1) 本项目自带的独立环境（如果之前已经建好）
  if py_ok "$VENV/bin/python"; then PYEXE="$VENV/bin/python"; return 0; fi
  # 2) PATH 里的 python3
  cand="$(command -v python3 2>/dev/null || true)"
  if py_ok "$cand"; then PYEXE="$cand"; return 0; fi
  # 3) 常见安装位置（Homebrew / python.org / 系统自带）
  local p
  for p in \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/*/bin/python3 \
    /usr/bin/python3 ; do
    if py_ok "$p"; then PYEXE="$p"; return 0; fi
  done
  PYEXE=""
  return 1
}

# ---- 通用下载: dl "url" "outfile" [最小字节数] ----
dl() {
  local url="$1" out="$2" min="${3:-1024}"
  rm -f "$out" 2>/dev/null || true
  curl -fL --retry 2 --connect-timeout 15 -m 900 \
       -A "jsp-installer" -o "$out" "$url" >/dev/null 2>&1 || true
  [ -s "$out" ] || return 1
  local size
  size="$(wc -c < "$out" | tr -d ' ')"
  [ "$size" -ge "$min" ] || { rm -f "$out"; return 1; }
  return 0
}

# ---- 下载安装 Python（macOS 官方 pkg，走图形安装向导）----
install_python() {
  local tmp pkg
  tmp="$(mktemp -d 2>/dev/null || echo /tmp/jsp_py.$$)"
  mkdir -p "$tmp"
  pkg="$tmp/python-$PY_VER-macos11.pkg"

  say "  正在下载 Python $PY_VER 安装包（约 45MB），请耐心等待 ..."
  if ! dl "https://www.python.org/ftp/python/$PY_VER/python-$PY_VER-macos11.pkg" "$pkg" 5000000; then
    say "  官方源较慢或失败，改用华为云镜像 ..."
    dl "https://mirrors.huaweicloud.com/python/$PY_VER/python-$PY_VER-macos11.pkg" "$pkg" 5000000 || true
  fi
  if [ ! -s "$pkg" ]; then
    err "  Python 安装包下载失败（可能网络不通）。"
    return 1
  fi

  say "  即将打开安装向导，请在弹出的窗口里一路「继续 / 安装」，"
  say "  安装过程中会要求输入你的 Mac 开机密码，装完后回到本窗口按回车。"
  open "$pkg" >/dev/null 2>&1 || true
  echo
  printf '%s' "  装好后按回车键继续 ..."
  read -r _ 2>/dev/null || true
  rm -rf "$tmp" 2>/dev/null || true
  detect_python
}

# ---- 取远端最新 commit 号 ----
fetch_remote_sha() {
  local json url sha
  json="$(mktemp 2>/dev/null || echo /tmp/jsp_sha.$$)"
  for url in \
    "https://api.github.com/repos/$REPO/commits/$BRANCH" \
    "https://ghfast.top/https://api.github.com/repos/$REPO/commits/$BRANCH" ; do
    sha="$(curl -fsL -m 20 -A "jsp-installer" "$url" 2>/dev/null \
           | sed -n 's/.*"sha"[[:space:]]*:[[:space:]]*"\([0-9a-f]\{40\}\)".*/\1/p' | head -1)"
    [ -n "$sha" ] && { printf '%s' "$sha"; rm -f "$json" 2>/dev/null; return 0; }
  done
  rm -f "$json" 2>/dev/null || true
  return 1
}

# ---- 下载项目（zip 优先，git 兜底）----
download_project() {
  local tmp zip extract src url
  tmp="$(mktemp -d 2>/dev/null || echo /tmp/jsp_dl.$$)"
  mkdir -p "$tmp"
  zip="$tmp/project.zip"
  extract="$tmp/extract"

  if [ -e "$APPDIR" ]; then
    say "  正在清理旧版本目录 ..."
    rm -rf "$APPDIR" 2>/dev/null || true
  fi

  local dl_ok=0
  for url in \
    "https://github.com/$REPO/archive/refs/heads/$BRANCH.zip" \
    "https://ghfast.top/https://github.com/$REPO/archive/refs/heads/$BRANCH.zip" \
    "https://gh-proxy.com/https://github.com/$REPO/archive/refs/heads/$BRANCH.zip" \
    "https://gh-proxy.net/https://github.com/$REPO/archive/refs/heads/$BRANCH.zip" ; do
    if [ "$dl_ok" = "0" ]; then
      say "  正在尝试下载: $url"
      if dl "$url" "$zip" 10000; then
        dl_ok=1
        ok "  下载成功"
      else
        say "  该地址下载失败"
      fi
    fi
  done

  if [ "$dl_ok" = "1" ]; then
    mkdir -p "$extract"
    say "  正在解压 ..."
    if tar -xf "$zip" -C "$extract" >/dev/null 2>&1; then
      src="$(find "$extract" -maxdepth 1 -mindepth 1 -type d | head -1)"
      [ -n "$src" ] && mv "$src" "$APPDIR" 2>/dev/null || true
    fi
    rm -rf "$tmp" 2>/dev/null || true
  fi

  # zip 方式失败则尝试 git
  if [ ! -f "$APPDIR/main.py" ] && command -v git >/dev/null 2>&1; then
    say "  ZIP 方式失败，尝试用 git 下载 ..."
    rm -rf "$APPDIR" 2>/dev/null || true
    git clone --depth 1 -b "$BRANCH" "https://github.com/$REPO.git" "$APPDIR" >/dev/null 2>&1 || \
    git clone --depth 1 -b "$BRANCH" "https://ghfast.top/https://github.com/$REPO.git" "$APPDIR" >/dev/null 2>&1 || true
  fi
  [ -f "$APPDIR/main.py" ]
}

# ---- 确保 requests 已安装 ----
ensure_requests() {
  # 优先使用项目内的独立环境（避开 macOS 的 externally-managed 限制）
  if [ ! -x "$VENV/bin/python" ]; then
    say "  正在创建独立运行环境 (.venv) ..."
    "$PYEXE" -m venv "$VENV" >/dev/null 2>&1 || warn "  创建独立环境失败，将回退到系统环境。"
  fi

  if [ -x "$VENV/bin/python" ]; then
    RUNPY="$VENV/bin/python"
  else
    RUNPY="$PYEXE"
  fi

  if "$RUNPY" -c "import requests" >/dev/null 2>&1; then
    ok "  requests 已安装，无需重复安装"
    return 0
  fi

  # pip 可用性修复
  if ! "$RUNPY" -m pip --version >/dev/null 2>&1; then
    say "  pip 不可用，正在尝试修复 ..."
    "$RUNPY" -m ensurepip --default-pip >/dev/null 2>&1 || true
  fi

  local req="$PROJECT/requirements.txt"
  local args
  if [ -f "$req" ]; then
    args=(-r "$req")
    say "  按项目 requirements.txt 安装，使用清华镜像 ..."
  else
    args=(requests)
    say "  未找到 requirements.txt，直接安装 requests，使用清华镜像 ..."
  fi

  if [ "$RUNPY" = "$PYEXE" ]; then
    # 系统解释器：加 --user，避免写系统目录 / 权限问题
    "$RUNPY" -m pip install --disable-pip-version-check --user "${args[@]}" \
      -i "$PIP_INDEX" --trusted-host "$PIP_HOST" || true
    "$RUNPY" -c "import requests" >/dev/null 2>&1 && return 0
    "$RUNPY" -m pip install --disable-pip-version-check --user "${args[@]}" || true
  else
    "$RUNPY" -m pip install --disable-pip-version-check "${args[@]}" \
      -i "$PIP_INDEX" --trusted-host "$PIP_HOST" || true
    "$RUNPY" -c "import requests" >/dev/null 2>&1 && return 0
    say "  镜像失败，改用官方源重试 ..."
    "$RUNPY" -m pip install --disable-pip-version-check "${args[@]}" || true
  fi

  "$RUNPY" -c "import requests" >/dev/null 2>&1 && return 0
  return 1
}

# ==========================================================
#  主流程
# ==========================================================

echo
say "${C_TITLE}============================================================${C_RESET}"
say "${C_TITLE}   江苏省大学新生安全知识教育 - 一键运行环境 (macOS)${C_RESET}"
say "${C_TITLE}============================================================${C_RESET}"
echo
say "  脚本所在位置: $ROOT"
echo

# ---------------- 第 1 步: Python3 ----------------
hr
say "  [1/4] 检查 Python 3 运行环境"
hr
if detect_python; then
  ok "  已检测到 Python: $PYEXE"
  say "  版本: $("$PYEXE" --version 2>&1)"
else
  say "  没有检测到 Python 3，准备自动下载并安装 ..."
  if install_python; then
    ok "  Python 安装完成: $PYEXE"
  else
    echo
    err "  [失败] 无法安装 Python 3。"
    say "  请手动到 https://www.python.org/downloads/ 下载安装 Python 3，"
    say "  安装完成后重新双击本脚本即可。"
    pause_exit 1
  fi
fi

# ---------------- 第 2 步: 准备项目 ----------------
echo
hr
say "  [2/4] 准备项目文件"
hr

# 优先使用脚本同目录下的项目（本项目自带一套）；否则下载一份
if [ "$FORCE_UPDATE" = "0" ] && [ -f "$ROOT/main.py" ]; then
  PROJECT="$ROOT"
  ok "  使用当前目录下的项目文件: $PROJECT"
elif [ "$FORCE_UPDATE" = "0" ] && [ -f "$APPDIR/main.py" ]; then
  PROJECT="$APPDIR"
  ok "  使用已下载的项目文件: $PROJECT"
else
  say "  本地没有可用的项目文件，开始下载 ..."
  if [ "$FORCE_UPDATE" = "1" ]; then say "  （已开启强制更新）"; fi
  REMOTE_SHA="$(fetch_remote_sha || true)"
  if [ -n "${REMOTE_SHA:-}" ]; then
    say "  最新版本: ${REMOTE_SHA:0:7}"
  else
    say "  无法连接 GitHub 查询最新版本"
  fi
  if download_project; then
    PROJECT="$APPDIR"
    ok "  项目已就绪: $PROJECT"
    [ -n "${REMOTE_SHA:-}" ] && printf '%s\n' "$REMOTE_SHA" > "$VERFILE" 2>/dev/null || true
  else
    echo
    err "  [失败] 项目下载失败，可能是网络问题或 GitHub 访问不通。"
    say "  请换个网络（比如手机热点）后重新双击本脚本再试一次。"
    say "  也可以手动下载项目并解压到本目录后再运行。"
    pause_exit 1
  fi
fi

for f in main.py utils.py 题库答案.json; do
  [ -f "$PROJECT/$f" ] || warn "  警告: 缺少 $f"
done
say "  项目目录: $PROJECT"

# ---------------- 第 3 步: 安装依赖 ----------------
echo
hr
say "  [3/4] 安装依赖库 requests"
hr
if ! ensure_requests; then
  echo
  err "  [失败] requests 库安装失败。"
  say "  可以手动执行下面的命令试试："
  say "    \"$RUNPY\" -m pip install requests"
  pause_exit 1
fi

# ---------------- 自检模式 ----------------
if [ "$CHECK_ONLY" = "1" ]; then
  echo
  ok "  [自检完成] 运行环境一切正常，可以双击运行了。"
  say "  Python : $PYEXE"
  say "  运行器 : $RUNPY"
  say "  项目   : $PROJECT"
  pause_exit 0
fi

# ---------------- 第 4 步: 运行 ----------------
echo
hr
say "  [4/4] 启动 main.py"
hr
say "  接下来请按提示输入：学校名称、账号、密码。"
say "  （输入密码时屏幕不会显示字符，输完直接回车即可）"
echo

cd "$PROJECT" || pause_exit 1
"$RUNPY" main.py
rc=$?

echo
say "${C_TITLE}============================================================${C_RESET}"
if [ "$rc" = "0" ]; then
  ok "   运行结束。"
else
  warn "   运行结束（退出码 ${rc}），如有报错请截图反馈。"
fi
say "   以后想再次运行，重新双击本脚本即可。"
say "   项目目录: $PROJECT"
say "${C_TITLE}============================================================${C_RESET}"
pause_exit "$rc"
