#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
江苏省安全教育一键完成 - Python 打包脚本
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """执行命令并显示结果"""
    print(f"\n[{description}]")
    print(f"执行: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"错误: {e}")
        print(f"输出: {e.stdout}")
        print(f"错误信息: {e.stderr}")
        return False

def main():
    print("=" * 50)
    print("江苏省安全教育一键完成 - 打包脚本")
    print("=" * 50)
    
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"工作目录: {os.getcwd()}")
    
    # 检查 PyInstaller
    print("\n[1/3] 检查 PyInstaller...")
    if not run_command("python -m pip show pyinstaller", "检查 PyInstaller"):
        print("PyInstaller 未安装，正在安装...")
        if not run_command('python -m pip install "pyinstaller>=6.3"', "安装 PyInstaller"):
            print("[错误] PyInstaller 安装失败")
            input("按回车键退出...")
            sys.exit(1)
    
    # 清理旧文件
    print("\n[2/3] 清理旧文件...")
    import shutil
    if os.path.exists("build"):
        shutil.rmtree("build")
        print("已删除 build 目录")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
        print("已删除 dist 目录")
    
    # 执行打包
    print("\n[3/3] 开始打包...")
    if not run_command("pyinstaller --clean --noconfirm build.spec", "打包"):
        print("[错误] 打包失败")
        input("按回车键退出...")
        sys.exit(1)
    
    # 检查输出
    print("\n" + "=" * 50)
    print("打包完成！")
    exe_path = os.path.join("dist", "江苏省安全教育一键完成.exe")
    if os.path.exists(exe_path):
        file_size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"输出文件: {exe_path}")
        print(f"文件大小: {file_size:.2f} MB")
    else:
        print("警告: 未找到输出文件")
    print("=" * 50)
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()