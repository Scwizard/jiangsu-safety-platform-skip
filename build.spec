# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置：生成单文件 GUI exe。

用法：pyinstaller --clean --noconfirm build.spec
输出：dist/江苏省安全教育一键完成.exe
"""

a = Analysis(
    ["gui.py"],
    pathex=[],
    binaries=[],
    datas=[("database.db", ".")],  # 题库数据库，解压到运行目录根
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="江苏省安全教育一键完成",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 程序，无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
