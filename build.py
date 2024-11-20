import os
import shutil
import subprocess
import site
import glob
import re

def get_version():
    """从 safetensors_viewer.py 中读取版本号"""
    try:
        with open('safetensors_viewer.py', 'r', encoding='utf-8') as f:
            content = f.read()
            # 查找 VERSION = "x.x.x" 格式的行
            version_match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
            if version_match:
                return version_match.group(1)
    except Exception as e:
        print(f"读取版本号时发生错误: {e}")
    return "unknown"

def clean_build():
    """清理旧的构建文件"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

def install_requirements():
    """安装 requirements.txt 中的所有依赖"""
    subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)

def find_tkdnd():
    """查找 tkdnd 文件"""
    site_packages = site.getsitepackages()
    for site_package in site_packages:
        tkdnd_path = os.path.join(site_package, 'tkinterdnd2', 'tkdnd')
        if os.path.exists(tkdnd_path):
            return tkdnd_path
    return None

def build():
    # 获取版本号
    version = get_version()
    app_name = f"月光AI宝盒_v{version}"
    
    # 清理旧文件
    clean_build()
    
    # 安装 requirements.txt 中的所有依赖
    install_requirements()
    
    # 获取 Firefox 浏览器路径
    firefox_base = os.path.join(os.path.dirname(__file__), 'playwright-browsers')
    firefox_path = glob.glob(os.path.join(firefox_base, 'firefox-*', 'firefox'))[0]  # 获取具体路径
    
    # 获取 tkdnd 路径
    tkdnd_path = find_tkdnd()
    if not tkdnd_path:
        raise RuntimeError("Could not find tkdnd directory")
    
    # PyInstaller 命令
    cmd = [
        'pyinstaller',
        '--noconfirm',
        '--clean',
        f'--name={app_name}',
        '--icon=ui/icon.ico',
        '--add-data=ui;ui',
        f'--add-data={firefox_path};playwright-browsers/firefox',  # 使用具体路径
        f'--add-data={tkdnd_path};tkdnd',
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=PIL',
        '--hidden-import=ttkbootstrap',
        '--hidden-import=tkinterdnd2',
        '--collect-data=tkinterdnd2',
        '--hidden-import=playwright',
        '--hidden-import=playwright.sync_api',
        '--hidden-import=playwright._impl._api_types',
        '--hidden-import=playwright._impl.sync_api',
        '--collect-data=playwright',
        '--collect-all=playwright',
        '--noconsole',
        '--onefile',
        'safetensors_viewer.py'
    ]
    
    # 执行打包命令
    subprocess.run(cmd)
    
    print(f"\n打包完成: {app_name}")

if __name__ == "__main__":
    build() 