import os
import subprocess
from datetime import datetime

def run_git_command(command):
    """运行git命令并返回结果"""
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',
            errors='ignore'
        )
        stdout, stderr = process.communicate()
        return (True, stdout) if process.returncode == 0 else (False, stderr)
    except Exception as e:
        return False, str(e)

def init_repository():
    """初始化新的git仓库"""
    print("\n开始初始化新的git仓库...")
    
    # 1. 确保 .git 文件夹不存在
    if os.path.exists('.git'):
        print("检测到已存在的git仓库。")
        choice = input("是否删除现有仓库重新初始化？(y/N): ").strip().lower()
        if choice != 'y':
            print("操作取消")
            return False
        print("请手动删除 .git 文件夹后重试")
        return False
    
    # 2. 初始化新仓库
    success, output = run_git_command('git init')
    if not success:
        print(f"初始化失败：\n{output}")
        return False
    
    # 3. 添加远程仓库
    remote_url = "https://github.com/wrl1214/Moon_SD_Models_Viewer2.git"
    success, output = run_git_command(f'git remote add origin {remote_url}')
    if not success:
        print(f"添加远程仓库失败：\n{output}")
        return False
    
    print("git仓库初始化完成！")
    return True

def commit_changes():
    """提交更改"""
    print("\n准备提交更改...")
    
    # 获取标签输入
    tag_version = input("请输入版本标签(例如 v1.0.0，直接回车跳过)：").strip()
    
    # 获取提交信息
    commit_message = input("请输入提交信息(默认: Update)：").strip() or "Update"
    
    files_to_update = [
        'ui',
        '运行查看器.bat',
        'build.py',
        'requirements.txt',
        'safetensors_viewer.py',
        'README.md',
        'update_git.py',
        '.gitignore'
        
    ]
    
    # 添加文件
    for file in files_to_update:
        success, output = run_git_command(f'git add "{file}"')
        if not success:
            print(f"添加文件 {file} 失败：\n{output}")
            return False
        print(f"已添加文件：{file}")
    
    # 创建提交
    success, output = run_git_command(f'git commit -m "{commit_message}"')
    if not success:
        print(f"提交更改失败：\n{output}")
        return False
    
    print(f"已创建提交：{commit_message}")
    
    # 如果提供了标签，创建并推送标签
    if tag_version:
        success, output = run_git_command(f'git tag {tag_version}')
        if not success:
            print(f"创建标签失败：\n{output}")
            return False
        print(f"已创建标签：{tag_version}")
    
    return True

def pull_changes():
    """拉取远程更新"""
    print("\n开始拉取远程更新...")
    
    # 获取当前分支
    success, current_branch = run_git_command("git rev-parse --abbrev-ref HEAD")
    if not success:
        print("获取当前分支失败")
        return False
    current_branch = current_branch.strip()
    
    # 先获取远程更新
    success, output = run_git_command(f'git fetch origin {current_branch}')
    if not success:
        print(f"获取远程更新失败：\n{output}")
        return False
    
    # 尝试合并远程更改
    success, output = run_git_command(f'git merge origin/{current_branch} --allow-unrelated-histories')
    if not success:
        print(f"合并远程更改失败：\n{output}")
        # 如果有冲突，中止合并
        run_git_command('git merge --abort')
        return False
    
    print("成功拉取并合并远程更新！")
    return True

def push_changes():
    """推送更改到远程"""
    print("\n开始推送到远程仓库...")
    
    # 获取当前分支
    success, current_branch = run_git_command("git rev-parse --abbrev-ref HEAD")
    if not success:
        print("获取当前分支失败")
        return False
    current_branch = current_branch.strip()
    
    # 先尝试拉取并合并更新
    print("正在拉取远程更新...")
    if pull_changes():
        print("正在推送更改...")
        success, output = run_git_command(f'git push -u origin {current_branch}')
        if success:
            print(f"成功推送到远程仓库的 {current_branch} 分支！")
            # 推送成功后，检查是否有标签需要推送
            success, tags = run_git_command('git tag --points-at HEAD')
            if success and tags.strip():
                print("\n检测到新标签，准备推送标签...")
                success, output = run_git_command('git push origin --tags')
                if not success:
                    print(f"推送标签失败：\n{output}")
                else:
                    print("标签推送成功！")
            return True
        else:
            print(f"推送失败：\n{output}")
    
    # 询问是否强制推送
    choice = input("\n是否要强制推送？这将覆盖远程的所有更改！(y/N): ").strip().lower()
    if choice == 'y':
        success, output = run_git_command(f'git push -f origin {current_branch}')
        if not success:
            print(f"强制推送失败：\n{output}")
            return False
        print("强制推送成功！")
        # 推送成功后，检查是否有标签需要推送
        success, tags = run_git_command('git tag --points-at HEAD')
        if success and tags.strip():
            print("\n检测到新标签，准备推送标签...")
            success, output = run_git_command('git push origin --tags')
            if not success:
                print(f"推送标签失败：\n{output}")
            else:
                print("标签推送成功！")
        return True
    
    return False

def switch_branch():
    """切换或创建分支"""
    print("\n切换分支...")
    
    # 获取当前分支
    success, current = run_git_command("git rev-parse --abbrev-ref HEAD")
    if success:
        print(f"当前分支：{current.strip()}")
    
    # 获取所有本地分支
    success, branches = run_git_command("git branch")
    if success:
        print("\n本地分支列表：")
        print(branches.strip())
    
    # 获取用户输入
    branch_name = input("\n请输入要切换的分支名称（输入新名称将创建新分支）：").strip()
    if not branch_name:
        print("分支名称不能为空")
        return False
    
    # 检查分支是否存在
    success, exists = run_git_command(f"git show-ref --verify --quiet refs/heads/{branch_name}")
    if success:
        # 分支存在，直接切换
        success, output = run_git_command(f"git checkout {branch_name}")
    else:
        # 分支不存在，创建并切换
        print(f"\n分支 {branch_name} 不存在，将创建新分支")
        success, output = run_git_command(f"git checkout -b {branch_name}")
    
    if not success:
        print(f"切换分支失败：\n{output}")
        return False
    
    print(f"\n已切换到分支：{branch_name}")
    return True

def reset_changes():
    """取消当前更改，恢复到远程最新版本"""
    print("\n准备恢复到远程仓库最新版本...")
    
    # 获取当前分支
    success, current_branch = run_git_command("git rev-parse --abbrev-ref HEAD")
    if not success:
        print("获取当前分支失败")
        return False
    current_branch = current_branch.strip()
    
    # 确认操作
    print("\n警告：此操作将丢失所有未提交的更改！")
    choice = input("是否继续？(y/N): ").strip().lower()
    if choice != 'y':
        print("操作已取消")
        return False
    
    # 获取远程最新状态
    success, output = run_git_command(f'git fetch origin {current_branch}')
    if not success:
        print(f"获取远程更新失败：\n{output}")
        return False
    
    # 强制重置到远程版本
    success, output = run_git_command(f'git reset --hard origin/{current_branch}')
    if not success:
        print(f"重置失败：\n{output}")
        return False
    
    # 清理未跟踪的文件
    success, output = run_git_command('git clean -fd')
    if not success:
        print(f"清理未跟踪文件失败：\n{output}")
        return False
    
    print("已成功恢复到远程仓库最新版本！")
    return True

def show_menu():
    """显示菜单"""
    print("\n=== Git操作菜单 ===")
    print("1. 初始化git仓库")
    print("2. 拉取远程更新")
    print("3. 提交更改")
    print("4. 推送到远程")
    print("5. 切换分支")
    print("6. 恢复到远程版本")
    print("0. 退出")
    return input("请选择操作 (0-6): ").strip()

def main():
    while True:
        choice = show_menu()
        if choice == "1":
            init_repository()
        elif choice == "2":
            pull_changes()
        elif choice == "3":
            commit_changes()
        elif choice == "4":
            push_changes()
        elif choice == "5":
            switch_branch()
        elif choice == "6":
            reset_changes()
        elif choice == "0":
            print("\n感谢使用！")
            break
        else:
            print("\n无效的选择，请重试。")
        
        input("\n按回车键继续...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n发生错误：{str(e)}")
        input("\n按回车键退出...")