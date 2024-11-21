"""
Safetensors Viewer
Version: 1.5.2
"""

# 全局常量
VERSION = "1.5.2"
APP_NAME = "月光AI宝盒-模型管理器"
APP_TITLE = f"{APP_NAME} v{VERSION}"


import os  # 操作系统相关
import sys  # 系统相关
import tkinter as tk  # GUI库
from tkinter import ttk, messagebox, StringVar, filedialog, PhotoImage  # GUI相关
from PIL import Image, ImageTk, ImageGrab  # 图像处理
import json  # JSON处理
import webbrowser  # 网页浏览
import logging  # 日志记录
from functools import lru_cache  # 缓存
import tkinter.font as tkfont  # 字体
import tempfile  # 临时文件
import urllib.request  # URL请求
import subprocess  # 子进程
import platform  # 平台相关
from tkinterdnd2 import DND_FILES, TkinterDnD  # 拖放
import ttkbootstrap as ttk  # GUI主题
from ttkbootstrap.constants import *  # GUI主题相关
from ttkbootstrap.style import Style  # GUI主题相关
import threading  # 多线程
import time  # 时间相关
import hashlib  # 哈希
import urllib.parse  # URL解析
import requests  # HTTP请求
from bs4 import BeautifulSoup  # HTML解析
import shutil  # 文件操作
import ctypes  # Windows相关
from playwright.sync_api import sync_playwright  # 浏览器自动化
from bs4 import NavigableString, Tag  # HTML解析
from PIL import Image, ImageTk  # 确保导入PIL库
import queue  # 队列
import math

def get_base_path():
    return os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))

BASE_PATH = get_base_path()

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = BASE_PATH
    return os.path.join(base_path, relative_path)

class FileSystemCache:
    def __init__(self):
        self.cache = {}

    def get_file_info(self, file_path):
        if file_path not in self.cache:
            self.cache[file_path] = self._get_file_info(file_path)
        return self.cache[file_path]

    def _get_file_info(self, file_path):
        try:
            file_stat = os.stat(file_path)
            return {
                'size': file_stat.st_size,
                'mtime': file_stat.st_mtime,
                'exists': True
            }
        except FileNotFoundError:
            return {
                'size': 0,
                'mtime': 0,
                'exists': False
            }

    def clear_cache(self):
        self.cache.clear()

class SafetensorsViewer:
    def __init__(self, master):
        # 基础属性初始化
        self.master = master
        self.version = VERSION

        # 设置窗口图标
        self.master.iconphoto(False, PhotoImage(file=get_resource_path('ui\\icon.png')))

        # 添加异步加载控制 - 移到前面
        self.loading_lock = threading.Lock()
        self.loading_thread = None
        self.loading_cancelled = False
        self.is_loading = False
        self.load_queue = queue.Queue()

        # 添加文件系统缓存 - 移到前面
        self.fs_cache = FileSystemCache()

        # DPI 缩放相关属性初始化
        try:
            if os.name == 'nt':
                awareness = ctypes.c_int()
                ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
                self.dpi_scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
            else:
                self.dpi_scale = 1.0
        except:
            self.dpi_scale = 1.0

        # 窗口尺寸设置
        self.window_width = 1240
        self.window_height = 950
        
        # 预览图和缩略图尺寸设置
        self.base_preview_size = int(450 / (self.dpi_scale ** (7/24)))
        self.base_thumbnail_size = int(60 / (self.dpi_scale ** (1/4)))
        self.thumbnail_size = (self.base_thumbnail_size, self.base_thumbnail_size)

        # 字体大小设置
        self.large_base_font_size_base = 14 
        self.large_base_title_font_size_base = 16
        self.small_base_font_size_base = 11
        self.small_base_title_font_size_base = 13

        # 默认字体大小设置
        self.base_font_size = int(self.small_base_font_size_base / (self.dpi_scale ** (1/3)))
        self.base_title_font_size = int(self.small_base_title_font_size_base / (self.dpi_scale ** (1/3)))

        # 从配置中读取字体大小设置
        try:
            info_file = 'model_info.json'
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
                    if "_app_settings" in all_info:
                        size_mode = all_info["_app_settings"].get("font_size_mode", "small")
                        if size_mode == "large":
                            self.base_font_size = int(self.large_base_font_size_base / (self.dpi_scale ** (1/3)))
                            self.base_title_font_size = int(self.large_base_title_font_size_base / (self.dpi_scale ** (1/3)))
                        else:  # 默认使用小字体
                            self.base_font_size = int(self.small_base_font_size_base / (self.dpi_scale ** (1/3)))
                            self.base_title_font_size = int(self.small_base_title_font_size_base / (self.dpi_scale ** (1/3)))
        except Exception as e:
            logging.error(f"读取字体大小设置时发生错误：{str(e)}")
            # 默认使用小字体
            self.base_font_size = int(self.small_base_font_size_base / (self.dpi_scale ** (1/3)))
            self.base_title_font_size = int(self.small_base_title_font_size_base / (self.dpi_scale ** (1/3)))

        # 添加字体定义
        self.current_font_family = self.get_saved_font() or 'Microsoft YaHei'
        self.base_font = (self.current_font_family, self.base_font_size)
        self.base_title_font = (self.current_font_family, self.base_title_font_size, 'bold')

        print(f"字体大小: {self.base_font_size}, 标题字体大小: {self.base_title_font_size}, 当前字体：{self.current_font_family}")

        
        # 其他属性初始化
        self.current_file = None
        self.current_subfolder = None
        self.current_sort = 'name_asc'  # 设置默认排序方式
        self.current_batch = 0
        self.batch_size = 20
        self.search_after_id = None
        
        # 支持的文件类型
        self.supported_model_extensions = ('.safetensors', '.ckpt', '.bin', '.pth', '.gguf','.pt')
        self.supported_image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
        
        # 数据存储
        self.categories = []
        self.all_files = []
        self.file_frames = {}
        self.subfolder_buttons = {}
        self.favorite_icon = None
        
        # 缓存
        self._file_paths_cache = {}
        self._preview_exists_cache = {}
        
        # UI 变量
        self.search_var = StringVar()
        
        # 设置主题
        saved_theme = self.get_saved_theme()
        self.style = Style(theme=saved_theme or 'darkly')
        
        # 初始化顺序调整
        self.add_favorite_field_to_model_info()
        self.favorites = self.load_favorites()
        self.setup_ui()  # 确保在设置完字体后再创建UI
        self.load_categories()
        
        # 设置事件绑定
        self.setup_drag_and_drop()
        self.master.bind_all('<Control-v>', self.paste_image)
        self.master.bind('<Up>', self.select_previous_model)
        self.master.bind('<Down>', self.select_next_model)
        self.master.bind('<Control-s>', self.handle_save_shortcut)
        self.master.bind('<Control-f>', self.focus_search)  # 添加 Ctrl+F 快捷键
        
        # 最后进行初加载
        self.initial_load()
        
        # 添加输入状态跟踪
        self.is_editing = False
        self.save_timer = None
        
        # 添加字体设置
        self.update_fonts()
        
    def get_saved_theme(self):
        """从 model_info.json 获取保存的主题设置"""
        try:
            info_file = 'model_info.json'
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
                    # 使用特殊键 "_app_settings" 存储应用设置
                    if "_app_settings" in all_info:
                        return all_info["_app_settings"].get("theme")
        except Exception as e:
            logging.error(f"读取主题设置时发生错误：{str(e)}")
        return None

    def save_theme(self, theme_name):
        """保存主题设置到 model_info.json"""
        try:
            info_file = 'model_info.json'
            all_info = {}
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
            
            # 确保 _app_settings 存在
            if "_app_settings" not in all_info:
                all_info["_app_settings"] = {}
            
            # 保存主题设置
            all_info["_app_settings"]["theme"] = theme_name
            
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(all_info, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logging.error(f"保存主题设置时发生错误：{str(e)}")

    def get_file_path(self, file_tuple):
        """获取文件完整路径（带缓存）"""
        cache_key = f"{file_tuple[1]}_{file_tuple[0]}"
        if cache_key not in self._file_paths_cache:
            self._file_paths_cache[cache_key] = os.path.join(BASE_PATH, file_tuple[1], file_tuple[0])
        return self._file_paths_cache[cache_key]

    def has_preview(self, file_tuple):
        """检查是否有预览图（带缓存）"""
        cache_key = f"{file_tuple[1]}_{file_tuple[0]}"
        if cache_key not in self._preview_exists_cache:
            file_name = file_tuple[0]
            relative_path = file_tuple[1]
            base_name = os.path.splitext(file_name)[0]
            
            self._preview_exists_cache[cache_key] = any(
                os.path.exists(os.path.join(BASE_PATH, relative_path, f"{base_name}{ext}"))
                for ext in self.supported_image_extensions
            )
        return self._preview_exists_cache[cache_key]

    def clear_caches(self):
        """清除所有缓存"""
        self._file_paths_cache.clear()
        self._preview_exists_cache.clear()
        self.load_thumbnail.cache_clear()

    def sort_filtered_files(self, files, sort_method):
        """优化的文件排序"""
        if not files:
            return []

        # 确保使用正确的排序方法
        sort_method = sort_method or self.current_sort
        
        # 创建文件列表的副本进行排序
        files = list(files)
        
        # 基础排序键
        name_key = lambda x: x[0].lower()
        
        if sort_method == 'name_asc':
            files.sort(key=name_key)
        elif sort_method == 'name_desc':
            files.sort(key=name_key, reverse=True)
        elif sort_method == 'date_desc':
            files.sort(key=lambda x: os.path.getmtime(self.get_file_path(x)), reverse=True)
        elif sort_method == 'date_asc':
            files.sort(key=lambda x: os.path.getmtime(self.get_file_path(x)))
        elif sort_method == 'info_modified_desc':
            # 从 model_info.json 获取最后修改时间
            info_file = 'model_info.json'
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
                files.sort(key=lambda x: all_info.get(os.path.join(x[1], x[0]), {}).get('last_modified', 
                    os.path.getmtime(self.get_file_path(x))), reverse=True)
            else:
                files.sort(key=lambda x: os.path.getmtime(self.get_file_path(x)), reverse=True)
        elif sort_method == 'no_preview_first':
            # 无预览图优先
            files.sort(key=lambda x: (self.has_preview(x), name_key(x)))
        elif sort_method == 'no_url_first':
            # 无模型网址优先
            info_file = 'model_info.json'
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
                files.sort(key=lambda x: (bool(all_info.get(os.path.join(x[1], x[0]), {}).get('url')), name_key(x)))
            else:
                files.sort(key=name_key)
        
        return files

    def filter_files(self, category, search_term=''):
        """优化的文件筛选，支持搜索模型类型"""
        search_term = search_term.lower()
        
        def matches_filter(file_tuple):
            file, path = file_tuple
            full_path = os.path.join(path, file)
            
            # 基本路径检查 - 修改为精确匹配类别路径
            path_parts = path.split(os.sep)
            if path_parts[0] != category:  # 确保第一级目录完全匹配
                return False
            
            # 子文件夹筛选 - 移到最前面，优先处理
            if self.current_subfolder:
                if self.current_subfolder == "其他":
                    if path != category:  # 如果不是根目录，直接返回False
                        return False
                elif self.current_subfolder == "收藏":
                    if full_path not in self.favorites:
                        return False
                else:
                    # 确保完全匹配子文件夹路径
                    if self.current_subfolder not in path_parts or path_parts.index(self.current_subfolder) != len(category.split(os.sep)):
                        return False
            
            # 搜索词检查
            if search_term:
                # 检查文件名和路径
                if search_term in file.lower() or search_term in path.lower():
                    return True
                    
                # 检查模型类型
                model_info = self.get_model_info(full_path)
                if model_info and 'type' in model_info:
                    if search_term in model_info['type'].lower():
                        return True
                    
                # 如果都不匹配，返回 False
                return False
            
            return True
        
        # 保持原有排序顺序进行筛选
        filtered_files = list(filter(matches_filter, self.all_files))
        
        # 如果是无模型网址优先排序，确保在筛选后再次应用排序
        if self.current_sort == 'no_url_first':
            info_file = 'model_info.json'
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
                filtered_files.sort(key=lambda x: (bool(all_info.get(os.path.join(x[1], x[0]), {}).get('url')), x[0].lower()))
        
        return filtered_files

    def load_files(self, category, search_term='', sort_method=None):
        """优化的文件加载方法"""
        self.clear_file_list()
        
        # 获取并筛选文件
        filtered_files = self.filter_files(category, search_term)
        if sort_method:
            filtered_files = self.sort_filtered_files(filtered_files, sort_method)
        
        # 开始分批创建文件条目
        self.create_file_entries_batch(filtered_files, 0)
        
        # 更新统计信息
        self.update_stats_label()

    def create_file_entries_batch(self, files, start_idx, batch_size=20):
        """分批创建文件条目"""
        end_idx = min(start_idx + batch_size, len(files))
        current_batch = files[start_idx:end_idx]
        
        # 确保没有重复的文件条目
        for file, path in current_batch:
            full_path = os.path.join(path, file)
            if full_path not in self.file_frames:
                self.create_file_entry(file, path)
        
        # 如果还有更多文件，安排下一批
        if end_idx < len(files):
            self.master.after(10, lambda: self.create_file_entries_batch(files, end_idx))
        else:
            # 所有批次处理完成
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # 选择第一个文件（如果有）
            if files and not self.current_file:
                first_file = files[0]
                self.select_file(first_file[0], first_file[1])

    def setup_ui(self):
        self.master.title(f"月光AI宝盒-模型管理器 v{self.version}")
      
        # 设置样式
        self.setup_styles()
        
        # 创建主框架，使用普通Frame而不是PanedWindow
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=1)
        
        # 创建菜单区域，固定宽度为250
        self.menu_frame = ttk.Frame(self.main_frame, style='Left.TFrame', width=250)
        self.menu_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.menu_frame.pack_propagate(False)  # 防止子组件影响框架大小
        
        # 创建内容区域
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建按钮
        self.setup_menu()
        
        # 创建模型管理界面
        self.model_management_frame = ttk.Frame(self.content_frame)
        self.setup_model_management()
        
        # 创建模型映射界面
        self.model_mapping_frame = ttk.Frame(self.content_frame)
        self.setup_model_mapping()
        
        # 创建帮助界面
        self.help_frame = ttk.Frame(self.content_frame)
        self.setup_help_frame()
        
        # 默认显示模型管理界面
        self.show_model_management()
    
    def setup_menu(self):
        """设置菜单按钮"""
        # 创建标题标签框
        title_frame = ttk.LabelFrame(self.menu_frame, text="功能区", style='primary.TLabelframe')
        title_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 设置按钮样式，使其填充整个宽度（移除 style 参数）
        button_style = {
            'padding': 5,
            'width': 28  # 增加按钮宽度以填充250像素宽的区域
        }
        
        # 在标题框内创建按钮
        self.model_management_btn = ttk.Button(
            title_frame, 
            text="模型管理", 
            command=self.show_model_management,
            style='secondary.TButton',
            **button_style
        )
        self.model_management_btn.pack(pady=5, padx=5, fill=tk.X)
        
        self.model_mapping_btn = ttk.Button(
            title_frame, 
            text="模型映射", 
            command=self.show_model_mapping,
            style='primary.TButton',  # 直接指定 style
            **button_style
        )
        self.model_mapping_btn.pack(pady=5, padx=5, fill=tk.X)
        
        # 修改计算哈希按钮为一键脚本按钮
        self.batch_btn = ttk.Button(
            title_frame,
            text="一键脚本",
            command=self.show_batch_menu,
            style='primary.TButton',
            **button_style
        )
        self.batch_btn.pack(pady=5, padx=5, fill=tk.X)
        
        # 添加主题切换按钮
        self.theme_btn = ttk.Button(
            title_frame,
            text="更换主题",
            command=self.show_theme_menu,
            style='primary.TButton',  # 直接指定 style
            **button_style
        )
        self.theme_btn.pack(pady=5, padx=5, fill=tk.X)

        # 修改字体切换按钮的命令
        self.font_btn = ttk.Button(
            title_frame,
            text="更换字体",
            command=self.show_font_size_menu,  # 改为显示字体大小菜单
            style='primary.TButton',
            **button_style
        )
        self.font_btn.pack(pady=5, padx=5, fill=tk.X)
        
        self.help_btn = ttk.Button(
            title_frame, 
            text="使用帮助", 
            command=self.show_help,
            style='primary.TButton',  # 直接指定 style
            **button_style
        )
        self.help_btn.pack(pady=5, padx=5, fill=tk.X)
        
        # 创建公告栏标签框
        announcement_frame = ttk.LabelFrame(self.menu_frame, text="公告栏", style='primary.TLabelframe')
        announcement_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建公告文本框
        self.announcement_text = tk.Text(
            announcement_frame,
            #wrap=tk.WORD,  # 自动换行
            height=5,
            font=self.base_font,
            bg=self.style.colors.bg,  # 使用主题背景色
            fg=self.style.colors.fg,  # 使用主题前景色
            relief='flat',  # 扁平化外观
            padx=5,        # 水平内边距
            pady=5         # 垂直内边距
        )
        self.announcement_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 设置公告内容
        announcement_content = f"""月光AI宝盒-模型管理器 v{VERSION}

※本软件完全免费，仅供学习交流使用，请勿用于商业用途。
※新版本发布请关注B站UP：黑米饭吃了么
※qq群：565977956
※长期下载更新地址：https://pan.quark.cn/s/75450b122a53

v{VERSION} 更新内容：
1.增加了列表缓存机制，有效提升列表加载速度
2.更换了体积更小浏览器内核，提升首次打开软件的速度
3.收藏功能取消了自动刷新机制，操作更流畅
4.增加了列表的快捷键操作
5.将更换预览图功能转移到详情图右键快捷菜单
6.增加了详情输入框的键入撤销功能（Ctrl+Z）
7.其他细节优化及问题修复

v1.5.0 更新内容：
【重点优化】
1.抓取功能全面升级
   - 内置了浏览器内核，实现更全面更稳定的抓取
   - Liblib抓取实现一键全信息抓取（需要手动填写网址）
   - Civitai抓取更稳定，抓取的描述格式进一步优化

2. 全面优化交互界面
   - 增加了自定义字体切换及大小调整
   - 预览图点击可以放大查看全尺寸图片
   - 列表区右键可以显示选单，支持更多操作
   - 详情区输入框右键可以显示选单，支持复制、粘贴、清空等操作
   - 增加了列表区当前类别下的模型总数和总大小统计
   - 排序中增加了多种排序方式，方便手动筛选无信息模型
   - 详情中增加了基础信息的显示

3. 全新的一键脚本功能
   - 新增"一键从Liblib抓取"功能
   - 新增"一键从Civitai抓取"功能
   - 新增"一键生成Custom Scripts配置文件"功能
   - 新增"一键生成SD WebUI可识别配置文件"功能


【问题修复】
1. 全面优化了高DPI下UI的显示效果（建议不要超过175%）
2. 修复了gguf模型无法识别的问题
3.重新设计了UI自适应逻辑，使得界面不容易出现按钮被遮挡的情况
4.其他功能及显示bug修复

※Bug提交网址：https://odopqev8le.feishu.cn/share/base/form/shrcnXRZoJWjH3Ab8jV4CExIPze

感谢您的使用！"""
        
        # 插入公告内容并禁用编辑
        self.announcement_text.insert('1.0', announcement_content)
        self.announcement_text.configure(state='disabled')
        
        # 绑定主题变更事件
        self.master.bind('<<ThemeChanged>>', self.update_announcement_colors)
        
        # 创建快捷入口标签框
        shortcut_frame = ttk.LabelFrame(self.menu_frame, text="快捷入口", style='primary.TLabelframe')
        shortcut_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)
        
        # 创建 Civitai 入口按钮
        civitai_btn = ttk.Button(
            shortcut_frame,
            text="Civitai入口",
            command=lambda: webbrowser.open("https://civitai.com/"),
            style='success.TButton',
            **button_style
        )
        civitai_btn.pack(pady=5, padx=5, fill=tk.X)
        
        # 创建 Liblib 入口按钮
        liblib_btn = ttk.Button(
            shortcut_frame,
            text="Liblib入口",
            command=lambda: webbrowser.open("https://www.liblib.art/"),
            style='success.TButton',
            **button_style
        )
        liblib_btn.pack(pady=5, padx=5, fill=tk.X)
        
        # 创建 Openart 入口按钮
        openart_btn = ttk.Button(
            shortcut_frame,
            text="Openart入口",
            command=lambda: webbrowser.open("https://openart.ai/home"),
            style='success.TButton',
            **button_style
        )
        openart_btn.pack(pady=5, padx=5, fill=tk.X)

        # 创建Huggingface入口按钮
        huggingface_btn = ttk.Button(
            shortcut_frame,
            text="HuggingFace入口",
            command=lambda: webbrowser.open("https://huggingface.co/"),
            style='success.TButton',
            **button_style
        )
        huggingface_btn.pack(pady=5, padx=5, fill=tk.X)

    def show_theme_menu(self, event=None):
        """显示主题选择菜单"""
        # 创建主题菜单
        menu = tk.Menu(self.master, tearoff=0, font=self.base_font)
        
        # 获取当前主题
        current_theme = self.style.theme.name
        
        # 所有支持的主题
        themes = [
            # 浅色主题
            ('Cosmo', 'cosmo'),
            ('Flatly', 'flatly'), 
            ('Journal', 'journal'),
            ('Lumen', 'lumen'),
            ('Minty', 'minty'),
            ('Pulse', 'pulse'),
            ('Sandstone', 'sandstone'),
            ('United', 'united'),
            ('Yeti', 'yeti'),
            ('Morph', 'morph'),
            # 深色主题
            ('Superhero', 'superhero'),
            ('Darkly', 'darkly'),
            ('Cyborg', 'cyborg'),
            ('Solar', 'solar'),
            ('Vapor', 'vapor')
        ]
        
        # 添加浅色主题
        menu.add_command(
            label="=== 浅色主题 ===",
            state='disabled',
            font=self.base_font
        )
        for theme_name, theme_id in themes[:10]:  # 前10个是浅色主题
            menu.add_command(
                label=f"✓ {theme_name}" if current_theme == theme_id else theme_name,
                command=lambda t=theme_id: self.change_theme(t),
                font=self.base_font
            )
        # 添加分隔线
        menu.add_separator()
        
        # 添加深色主题
        menu.add_command(
            label="=== 深色主题 ===",
            state='disabled',
            font=self.base_font
        )
        for theme_name, theme_id in themes[10:]:  # 后5个是深色主题
            menu.add_command(
                label=f"✓ {theme_name}" if current_theme == theme_id else theme_name,
                command=lambda t=theme_id: self.change_theme(t),
                font=self.base_font
            )
        # 在按钮下方显示菜单
        x = self.theme_btn.winfo_rootx()
        y = self.theme_btn.winfo_rooty() + self.theme_btn.winfo_height()
        menu.post(x, y)

    def change_theme(self, theme_name):
        """切换主题"""
        try:
            # 保存当前选中的文件
            current_file = self.current_file
            
            # 切换主题
            self.style = Style(theme=theme_name)
            
            # 保存主题设置
            self.save_theme(theme_name)
            
            # 重新应用样式
            self.setup_styles()
            
            # 更新预览图容器边框颜色
            if hasattr(self, 'preview_container'):
                self.preview_container.configure(
                    bg=self.style.colors.bg,
                    highlightbackground=self.style.colors.primary  # 更新外描边颜色
                )
                self.inner_frame.configure(bg=self.style.colors.bg)
            
            # 刷新界面显示
            if current_file:
                # 重新加载当前文件以更新样式
                file_name = os.path.basename(current_file)
                relative_path = os.path.dirname(current_file)
                self.select_file(file_name, relative_path)
            
            # 显示成功消息
            self.show_popup_message(f"主题已切换为 {theme_name}")
            
        except Exception as e:
            self.show_popup_message(f"切换主题时发生错误：{str(e)}")

    def setup_model_management(self):
        # 使用 ttk.PanedWindow
        self.paned_window = ttk.PanedWindow(
            self.model_management_frame, 
            orient=tk.HORIZONTAL
        )
        self.paned_window.pack(fill=tk.BOTH, expand=1)
        
        # 设置左右框架
        self.setup_left_frame()
        self.setup_right_frame()
        
        # 添加框架到 PanedWindow 并设置权重
        self.paned_window.add(self.left_frame)
        self.paned_window.add(self.right_frame)
        
         # 确保布局已完成
        self.master.update_idletasks() 
        # 延迟1毫秒后设置分隔线位置
        self.master.after(10, lambda: self.paned_window.sashpos(0, 350))

        
    def setup_model_mapping(self):
        """创建模型映射界面的内容"""
        # 创建主框架
        mapping_frame = ttk.Frame(self.model_mapping_frame)
        mapping_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建画布和滚动条
        canvas = tk.Canvas(mapping_frame, bg=self.style.colors.bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(mapping_frame, orient="vertical", command=canvas.yview)
        
        # 创建内容框架
        content_frame = ttk.Frame(canvas)
        
        # 配置画布滚动
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 创建映射说明的 LabelFrame
        mapping_info_frame = ttk.LabelFrame(content_frame, text="映射说明", style='primary.TLabelframe')
        mapping_info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建按钮框架
        button_frame = ttk.Frame(mapping_info_frame)
        button_frame.pack(pady=10, padx=20, fill=tk.X)

        # 显示主要信息
        main_info = ttk.Label(button_frame, text="映射功能允许将模型文件放在电脑中的任何位置，通过映射让ComfyUI或SD能够正确读取到模型文件，\n"
                                             "方便统一管理所有模型文件，推荐将ComfyUI中models文件整体复制到外部，例如H:/models，并且将\n"
                                             "本软件放到该文件夹下\n\n"
                                             "※重要说明：适用于所有映射\n"
                                             "1、外部模型文件夹目录需要使用ComfyUI中models文件夹下的目录结构。\n"
                                             "2、外部模型文件夹全路径不可包含中文字符，推荐使用models命名。\n"
                                             "3、外部模型文件尽可能放在固态硬盘下使用。", 
                             justify='left', style='danger.TLabel')
        main_info.pack(pady=(0, 10), fill=tk.X)  # 拉伸占满整个 LabelFrame

        # ComfyUI 按钮
        comfyui_button = ttk.Button(
            button_frame, 
            text="ComfyUI", 
            width=50,
            style='primary.TButton',
            command=self.setup_comfyui_mapping,
        )
        comfyui_button.pack(pady=5, anchor='w')  # 左对齐

        # ComfyUI 使用说明
        comfyui_info = ttk.Label(button_frame, text="※此功能适配原版ComfyUI以及各类改版\n1、点击此按钮以配置 ComfyUI 的模型映射。\n2、输入ComfyUI根目录文件夹地址。\n3、点击确认按钮。", 
                                 justify='left')
        comfyui_info.pack(pady=(0, 10), fill=tk.X)  # 拉伸占满整个 LabelFrame

        # Stable Diffusion A1111 WebUI 按钮
        sd_button = ttk.Button(button_frame, text="Stable Diffusion A1111 WebUI",width=50, style='primary.TButton',
                               command=self.setup_sd_mapping)
        sd_button.pack(pady=5, anchor='w')  # 左对齐

        # Stable Diffusion A1111 WebUI 使用说明
        sd_info = ttk.Label(button_frame, text="※此功能适配原版SD WebUI以及Forge等改版（只要是通过读取webui-user.bat启动即可）\n1、点击此按钮以配置 Stable Diffusion A1111 WebUI 的模型映射。\n2、输入Stable Diffusion A1111 WebUI根目录文件夹地址。\n3、点击确认按钮。", 
                            justify='left')
        sd_info.pack(pady=(0, 10), fill=tk.X)  # 拉伸占满整个 LabelFrame

        # 获取当前程序所在文件夹的路径
        current_directory = os.getcwd().replace("\\", "/")  # 替换反斜杠为正斜杠

        # 显示参数的输入框
        params_info = f"--ckpt-dir {current_directory}/checkpoints\n" \
                      f"--lora-dir {current_directory}/loras\n" \
                      f"--vae-dir {current_directory}/vae\n" \
                      f"--embeddings-dir {current_directory}/embeddings\n" \
                      f"--gfpgan-models-path {current_directory}/upscale_models\n" \
                      f"--esrgan-models-path {current_directory}/upscale_models\n" \
                      f"--controlnet-dir {current_directory}/controlnet"

        # 秋叶WebUI启动器按钮
        autumn_leaves_button = ttk.Button(button_frame, text="复制秋叶WebUI启动器参数",width=50, style='primary.TButton',
                                       command=lambda: self.setup_autumn_leaves_mapping(params_info))  # 需要实现该方法
        autumn_leaves_button.pack(pady=5, anchor='w')  # 左对齐

        # 修改为使用 Text 组件以支持自动换行
        params_entry = tk.Text(button_frame, height=10, wrap=tk.WORD, font=self.base_font, state='disabled')  # 使用 Text 组件并设置为不可编辑
        params_entry.configure(state='normal')  # 临时启用编辑以插入文本
        params_entry.insert('1.0', params_info)  # 插入参数信息
        params_entry.configure(state='disabled')  # 恢复为不可编辑状态
        params_entry.pack(pady=(0, 10), fill=tk.X)  # 拉伸占满整个 LabelFrame
        params_entry.configure(width=100)  # 设置合适的宽度以确保文本显示

        # 秋叶WebUI启动器使用说明
        autumn_leaves_info = ttk.Label(button_frame, text="1、打开秋叶WebUI启动器\n2、打开设置 > 一般设置\n3、配置模式改为高级\n4、打开高级选项\n5、找到其他设置 > 自定义参数\n6、点击按钮复制参数\n7、正常通过启动器打开WebUI", 
                                        justify='left')
        autumn_leaves_info.pack(pady=(0, 10), fill=tk.X)  # 拉伸占满整个 LabelFrame

        # 配置画布和滚动条
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 在画布上创建窗口
        canvas.create_window((0, 0), window=content_frame, anchor="nw", width=canvas.winfo_width())

        # 更新滚动区域
        def update_scrollregion(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())

        # 存储画布窗口的引用
        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")

        # 绑定事件
        content_frame.bind("<Configure>", update_scrollregion)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=canvas.winfo_width()))

        # 添加鼠标滚轮支持，带有顶部限制
        def _on_mousewheel(event):
            # 获取当前滚动位置
            current_pos = canvas.yview()[0]
            
            # 计算滚动方向和距离
            if platform.system() == "Windows":
                delta = int(-1 * (event.delta / 120))
            elif platform.system() == "Darwin":  # macOS
                delta = int(-1 * event.delta)
            else:  # Linux
                if event.num == 4:
                    delta = -1
                elif event.num == 5:
                    delta = 1
                else:
                    return

            # 如果已经在顶部且试图向上滚动，则不执行滚动
            if current_pos <= 0 and delta < 0:
                return
                
            # 执行滚动
            canvas.yview_scroll(delta, "units")

        # 绑定鼠标滚轮事件
        if platform.system() == "Windows" or platform.system() == "Darwin":
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        else:  # Linux
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        # 解绑鼠标滚轮事件（当离开区域时）
        def _unbind_mousewheel(event):
            if platform.system() == "Windows" or platform.system() == "Darwin":
                canvas.unbind_all("<MouseWheel>")
            else:  # Linux
                canvas.unbind_all("<Button-4>")
                canvas.unbind_all("<Button-5>")

        # 重新绑定鼠标滚轮事件（当进入区域时）
        def _bind_mousewheel(event):
            if platform.system() == "Windows" or platform.system() == "Darwin":
                canvas.bind_all("<MouseWheel>", _on_mousewheel)
            else:  # Linux
                canvas.bind_all("<Button-4>", _on_mousewheel)
                canvas.bind_all("<Button-5>", _on_mousewheel)

        # 绑定鼠标进入/离开事件
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        # 自定义滚动条命令，添加顶部限制
        def custom_scroll(*args):
            if args[0] == 'scroll':
                # 获取当前位置
                current_pos = canvas.yview()[0]
                
                # 如果在顶部且试图向上滚动，则不执行
                if current_pos <= 0 and int(args[1]) < 0:
                    return
                    
            # 执行正常的滚动
            canvas.yview(*args)

        # 更新滚动条配置，使用自定义滚动命令
        scrollbar.configure(command=custom_scroll)     

    def setup_sd_mapping(self):
        """创建 SD WebUI 配置对话框"""
        # 创建输入对话框
        dialog = tk.Toplevel(self.master)
        dialog.title("Stable Diffusion WebUI 配置")
        dialog.geometry("600x200")
        dialog.transient(self.master)
        dialog.grab_set()
        
        # 居中显示对话框
        dialog.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 300}+"
                       f"{self.master.winfo_y() + self.master.winfo_height()//2 - 75}")
        
        # 创建主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建标签和输入框
        ttk.Label(main_frame, text="请输入 Stable Diffusion WebUI 根目录文件夹地址:\n※请提前确认该根目录下是否有webui-user.bat文件").pack(anchor='w', pady=(0, 5))
        
        # 创建输入框框架
        entry_frame = ttk.Frame(main_frame)
        entry_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 创建输入框
        entry = ttk.Entry(entry_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        def browse_directory():
            directory = filedialog.askdirectory()
            if directory:
                entry.delete(0, tk.END)
                entry.insert(0, directory)
        
        # 添加浏览按钮
        browse_button = ttk.Button(entry_frame, text="浏览",width=10, style='primary.TButton', command=browse_directory)
        browse_button.pack(side=tk.LEFT)
        
        # 创建按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        def create_config():
            webui_path = entry.get().strip()
            if not webui_path:
                messagebox.showwarning("警告", "请输入 Webui 根目录文件夹地址")
                return
                
            bat_file = os.path.join(webui_path, 'webui-user.bat')
            
            if not os.path.isdir(webui_path):
                messagebox.showwarning("警告", "根目录设置错误")
                return
                
            # 获取当前程序所在目录的完整路径
            current_directory = os.getcwd().replace("\\", "/")  # 替换反斜杠为正斜杠
            
            # 构建命令行参数（单行格式）
            args = "set COMMANDLINE_ARGS=--ckpt-dir " + current_directory + "/checkpoints --lora-dir " + current_directory + "/loras --vae-dir " + current_directory + "/vae --embeddings-dir " + current_directory + "/embeddings --gfpgan-models-path " + current_directory + "/upscale_models --esrgan-models-path " + current_directory + "/upscale_models --controlnet-dir " + current_directory + "/controlnet"
            
            if os.path.exists(bat_file):
                # 读取现有文件内容
                with open(bat_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # 找到 COMMANDLINE_ARGS 行并替换
                found = False
                for i, line in enumerate(lines):
                    if line.startswith('set COMMANDLINE_ARGS='):
                        if not messagebox.askyesno("确认", "webui-user.bat 已存在，是否替换？"):
                            return
                        lines[i] = args + '\n'
                        found = True
                        break
                
                # 如果没找到，添加到文件开头
                if not found:
                    lines.insert(1, args + '\n')
                
                # 写回文件
                with open(bat_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
            else:
                # 创建新文件
                with open(bat_file, 'w', encoding='utf-8') as f:
                    f.write('@echo off\n')
                    f.write(args + '\n')
                    f.write('call webui.bat\n')
            
            messagebox.showinfo("成功", "配置文件已成功更新")
            dialog.destroy()
        
        # 添加确认和取消按钮
        ttk.Button(
            button_frame, 
            text="取消", 
            command=dialog.destroy,
            style='primary.TButton',
            width=10
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            button_frame, 
            text="确认", 
            command=create_config,
            style='primary.TButton',
            width=10
        ).pack(side=tk.RIGHT)

    def setup_autumn_leaves_mapping(self,text):
        """将文本复制到剪贴板"""
        self.master.clipboard_clear()  # 清空剪贴板
        self.master.clipboard_append(text)  # 添加文本到剪贴板
        self.show_popup_message("参数已复制")

    def setup_comfyui_mapping(self):
        """创建 ComfyUI 配置对话框"""
        # 创建输入对话框
        dialog = tk.Toplevel(self.master)
        dialog.title("ComfyUI 配置")
        dialog.geometry("600x200")
        dialog.transient(self.master)
        dialog.grab_set()
        
        # 居中显示对话框
        dialog.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 300}+"
                       f"{self.master.winfo_y() + self.master.winfo_height()//2 - 75}")
        
        # 创建主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建标签和输入框
        ttk.Label(main_frame, text="请输入ComfyUI根目录文件夹址:\n※请提前确认该根目录下是否有extra_model_paths.yaml文件").pack(anchor='w', pady=(0, 5))
        
        # 创建输入框框架
        entry_frame = ttk.Frame(main_frame)
        entry_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 创建输入框
        entry = ttk.Entry(entry_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        def browse_directory():
            directory = filedialog.askdirectory()
            if directory:
                entry.delete(0, tk.END)
                entry.insert(0, directory)
        
        # 按输入框架
        browse_button = ttk.Button(entry_frame, text="浏览",width=10, style='primary.TButton', command=browse_directory)
        browse_button.pack(side=tk.LEFT)
        
        # 创建按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        def create_config():
            path = entry.get().strip()
            if not path:
                messagebox.showwarning("警告", "请输入ComfyUI根目录文件夹地址")
                return
            if not os.path.isdir(path):
                messagebox.showwarning("警告", "输入的路径是有效的文件夹")
                return
            
            yaml_path = os.path.join(path, 'extra_model_paths.yaml')
            if os.path.exists(yaml_path):
                if not messagebox.askyesno("确认", "extra_model_paths.yaml 文件已存在，是否替换？"):
                    return
            
            try:
                self.create_comfyui_config(yaml_path)
                messagebox.showinfo("成功", "配置文件已成功创建")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"创建配置文件时发生错误：{str(e)}")
        
        # 添加确认和取消按钮
        ttk.Button(
            button_frame, 
            text="取消", 
            style='primary.TButton',
            command=dialog.destroy,
            width=10
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            button_frame, 
            text="确认", 
            style='primary.TButton',
            command=create_config,
            width=10
        ).pack(side=tk.RIGHT)
        
        # 确保对话框大小合适
        dialog.update_idletasks()
        dialog.minsize(dialog.winfo_width(), dialog.winfo_height())
        
        # 设置焦点到输入框
        entry.focus_set()

    def create_comfyui_config(self, yaml_path):
        """建 ComfyUI 配置文件"""

        # 获取当程序所在位置的上层文件夹地址
        base_path = os.path.dirname(BASE_PATH)
        # 获取当前程序所在文件夹的路径
        current_directory = os.getcwd()
        # 获取当前程序所在文件夹的文件名
        program_folder_name = os.path.basename(current_directory)
        # 创建配置文件内容
        config_content = f'''comfyui:
        base_path: {base_path}
        # You can use is_default to mark that these folders should be listed first, and used as the default dirs for eg downloads
        #is_default: true
        checkpoints: {program_folder_name}/checkpoints/
        clip: {program_folder_name}/clip/
        clip_vision: {program_folder_name}/clip_vision/
        configs: {program_folder_name}/configs/
        controlnet: {program_folder_name}/controlnet/
        diffusion_models: |
                     {program_folder_name}/diffusion_models
                     {program_folder_name}/unet
        embeddings: {program_folder_name}/embeddings/
        loras: {program_folder_name}/loras/
        upscale_models: {program_folder_name}/upscale_models/
        vae: {program_folder_name}/vae/
        animatediff_models: {program_folder_name}/animatediff_models/
        animatediff_motion_lora: {program_folder_name}/animatediff_motion_lora/
        ipadapter: {program_folder_name}/ipadapter/'''
        
        # 写入配置文件
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(config_content)

    def show_model_management(self):
        """显示模型管理界面"""
        self.model_mapping_frame.pack_forget()
        self.help_frame.pack_forget()
        self.model_management_frame.pack(fill=tk.BOTH, expand=True)
        
        self.model_management_btn.configure(style='secondary.TButton')
        self.model_mapping_btn.configure(style='primary.TButton')
        self.help_btn.configure(style='primary.TButton')

    def show_model_mapping(self):
        """显示型映射界面"""
        self.model_management_frame.pack_forget()
        self.help_frame.pack_forget()
        self.model_mapping_frame.pack(fill=tk.BOTH, expand=True)
        
        self.model_mapping_btn.configure(style='secondary.TButton')
        self.model_management_btn.configure(style='primary.TButton')
        self.help_btn.configure(style='primary.TButton')

    def setup_styles(self):
        """设置自定义样式"""
        
        # 设置基础样式
        self.style.configure('TFrame', background=self.style.colors.bg)
        self.style.configure('TLabel', 
            background=self.style.colors.bg,
            font=self.base_font
        )
        
        # 列表项样式
        self.style.configure('List.TFrame', 
            background=self.style.colors.bg,
            relief='flat',
            borderwidth=0
        )
        
        # 选中项样式
        self.style.configure('Selected.TFrame',
            background=self.style.colors.secondary,
            relief='flat',
            borderwidth=0
        )
        
        # 选中项标签样式
        self.style.configure('Selected.TLabel',
            background=self.style.colors.secondary,
            foreground=self.style.colors.fg,
            font=self.base_font
        )
        
        # 功能区按钮基础样式
        menu_button_config = {
            'font': self.base_font,
            'width': 15,
            'padding': 5    
        }
        
        # 功能区按钮样式 - 未选中
        self.style.configure('primary.TButton', **menu_button_config)
        
        # 功能区按钮样式 - 选中
        self.style.configure('secondary.TButton', **menu_button_config)

        # 操作按钮样式
        self.style.configure('warning.TButton',
            font=self.base_font,
            height=3,
            width=15,
            padding=5,
            background=self.style.colors.warning,
        )
        
        # 信息按钮样式
        self.style.configure('info.TButton',
            font=self.base_font,
            width=6,
            padding=3
        )
        
        # 搜索样式
        self.style.configure('primary.TEntry',
            font=self.base_font,
            padding=5
        )
        
        # 下拉框样式
        self.style.configure('primary.TCombobox',
            font=self.base_font,
            padding=5
        )
        
        # 标签框样式
        self.style.configure('primary.TLabelframe', 
            background=self.style.colors.bg,
            foreground=self.style.colors.primary,
            font=self.base_title_font
        )
        
        self.style.configure('primary.TLabelframe.Label',
            background=self.style.colors.bg,
            foreground=self.style.colors.primary,
            font=self.base_title_font
        )
        
        # 粗体标签样式
        self.style.configure('Bold.TLabel',
            font=self.base_title_font,
            background=self.style.colors.bg,
            foreground=self.style.colors.fg
        )
        
        # 在现有的样式设置中添加 TPanedwindow 的样式
        self.style.configure('TPanedwindow', 
            background=self.style.colors.bg,
            sashwidth=4,  # 设置分隔线宽度
            sashrelief='flat'  # 设置分隔线样式
        )
        
        # 添加图标样式
        self.style.configure('Icon.TLabel',
            font=self.base_title_font,  # 使用更大的字体显示图标
            foreground=self.style.colors.primary,  # 使用主题主色
            background=self.style.colors.bg,
            padding=(0, 0, 0, 2)  # 稍微下移以对齐文本
        )
        
        # 设置成功按钮样式（用于快捷入口）
        self.style.configure(
            'success.TButton',
            font=self.base_font,
            background=self.style.colors.success,
        )
        
        # 添加带边框的 Frame 样式
        self.style.configure('Border.TFrame',
            background=self.style.colors.bg,
            borderwidth=0,  # 将边框宽度改为最细
            relief='solid',
            bordercolor=self.style.colors.primary  # 使用主题主色作为边框颜色
        )

        # 添加 Combobox 样式
        self.style.configure(
            'TCombobox',
            font=self.base_font,
            padding=5
        )
        
        # 设置 Combobox 下拉列表样式
        self.master.option_add('*TCombobox*Listbox.font', self.base_font)

    def setup_left_frame(self):
        """设置左侧框架"""
        self.left_frame = ttk.Frame(self.paned_window)  # 移除固定宽度设置
        
        # 创建模型选择标签框
        model_selection_frame = ttk.LabelFrame(self.left_frame, text="模型选择", style='primary.TLabelframe')
        model_selection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 将控件放入模型选择框内
        control_frame = ttk.Frame(model_selection_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        control_frame.columnconfigure(1, weight=1)

        # 类别选择框
        ttk.Label(control_frame, text="类别:", 
            style='Left.TLabel',
            font=self.base_font
        ).grid(row=0, column=0, sticky='w', padx=(0, 5), pady=2)
        
        self.category_combobox = ttk.Combobox(
            control_frame, 
            state="readonly",
            font=self.base_font  # 设置类别下拉框字体
        )
        self.category_combobox.grid(row=0, column=1, sticky='ew', pady=2)
        self.category_combobox.bind("<<ComboboxSelected>>", self.on_category_selected)
        
        self.refresh_button = ttk.Button(
            control_frame, 
            text="刷新", 
            command=self.refresh_files, 
            width=6, 
            style='info.TButton'
        )
        self.refresh_button.grid(row=0, column=2, padx=(5, 0), pady=2)

        # 搜索框
        ttk.Label(control_frame, text="搜索:", 
            style='Left.TLabel',
            font=self.base_font
        ).grid(row=1, column=0, sticky='w', padx=(0, 5), pady=2)
        
        # 创建搜索框容器
        search_container = ttk.Frame(control_frame)
        search_container.grid(row=1, column=1, sticky='ew', pady=2)
        search_container.columnconfigure(0, weight=1)  # 让搜索框占据大部分空间
        
        # 创建搜索框
        self.search_var = StringVar()
        self.search_var.trace("w", self.schedule_search)
        self.search_entry = ttk.Entry(
            search_container, 
            textvariable=self.search_var,
            font=self.base_font  # 设置搜索框字体
        )
        self.search_entry.grid(row=0, column=0, sticky='ew')
        self.search_entry.bind("<Control-v>", self.paste_image)
        
        # 创建清除按钮
        clear_button = ttk.Button(
            search_container, 
            text="×",  # 使用 × 符号作为清除图标
            width=2,   # 设置按钮宽度
            style='info.TButton',
            command=self.clear_search
        )
        clear_button.grid(row=0, column=1, padx=(2, 0))  # 在搜索框右侧添加按钮
        
        # 排序按钮
        self.sort_button = ttk.Button(control_frame, text="排序", command=self.show_sort_menu, width=6, style='info.TButton')
        self.sort_button.grid(row=1, column=2, padx=(5, 0), pady=2)

        # 快速筛选区域
        self.quick_filter_frame = ttk.Frame(model_selection_frame, style='Left.TFrame')
        self.quick_filter_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # 用于存储子文件夹按钮的引用
        self.subfolder_buttons = {}
        self.current_subfolder = None

        # 创建型列表标签框
        model_list_frame = ttk.LabelFrame(self.left_frame, text="模型列表", style='primary.TLabelframe')
        model_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建统计信息容器
        stats_container = ttk.Frame(model_list_frame)
        stats_container.pack(fill=tk.X, padx=5, pady=5)

        # 添加统计信息标签
        self.stats_label = ttk.Label(
            stats_container,
            text="",
            font=self.base_font,
            wraplength=280  # 减小文本自动换行宽度以适应按钮
        )
        self.stats_label.pack(side=tk.LEFT)

        # 添加快速滚动按钮
        scroll_buttons_frame = ttk.Frame(stats_container)
        scroll_buttons_frame.pack(side=tk.RIGHT)

        # 滚动到顶部按钮
        scroll_top_btn = ttk.Button(
            scroll_buttons_frame,
            text="顶",
            width=3,
            style='info.TButton',
            command=self.scroll_to_top
        )
        scroll_top_btn.pack(side=tk.LEFT, padx=2)

        # 滚动到底部按钮
        scroll_bottom_btn = ttk.Button(
            scroll_buttons_frame,
            text="底",
            width=3,
            style='info.TButton',
            command=self.scroll_to_bottom
        )
        scroll_bottom_btn.pack(side=tk.LEFT)

        # 创建容器框架
        self.canvas_container = ttk.Frame(model_list_frame)
        self.canvas_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 配置容器的网格布局
        self.canvas_container.grid_rowconfigure(0, weight=1)
        self.canvas_container.grid_columnconfigure(0, weight=1)

        # 创建画布和滚动条
        self.canvas = tk.Canvas(
            self.canvas_container, 
            bg=self.style.colors.bg, 
            highlightthickness=0,
            width=350  # 设置初始最小宽度
        )
        self.scrollbar = ttk.Scrollbar(self.canvas_container, orient="vertical", command=self.canvas.yview)
        
        # 创建可滚动框架
        self.scrollable_frame = ttk.Frame(self.canvas, style='Left.TFrame')
        
        # 使用grid布局
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.scrollbar.grid(row=0, column=1, sticky='ns')

        # 配置画布的滚动
        self.canvas.configure(yscrollcommand=self.scrollbar.set)  # 添加这行
        
        # 绑定滚动区域更新
        def update_scrollregion(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # 确保滚动条状态正确更新
            if self.scrollable_frame.winfo_height() > self.canvas.winfo_height():
                self.scrollbar.grid()
            else:
                self.scrollbar.grid_remove()
        
        self.scrollable_frame.bind(
            "<Configure>",
            update_scrollregion
        )

        # 创建画布窗口，设置anchor为nw确保从左上角开始显示
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw",
            width=self.canvas.winfo_width()  # 设置初始宽度
        )

        # 绑定画布大小变化事件
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        # 绑定鼠标滚轮事件
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        # 绑定Home和End快捷键
        self.master.bind('<Home>', lambda e: self.scroll_to_top())
        self.master.bind('<End>', lambda e: self.scroll_to_bottom())
        # 绑定PageUp和PageDown快捷键
        self.master.bind('<Prior>', lambda e: self.scroll_page_up())  # PageUp
        self.master.bind('<Next>', lambda e: self.scroll_page_down())  # PageDown

    def scroll_page_up(self):
        """向上滚动一页"""
        # 获取当前可见区域的高度
        visible_height = self.canvas.winfo_height()
        # 获取当前滚动位置
        current_pos = self.canvas.yview()[0]
        # 计算新的滚动位置(向上滚动一个可见区域的高度)
        new_pos = max(0, current_pos - (visible_height / self.scrollable_frame.winfo_height()))
        # 移动到新位置
        self.canvas.yview_moveto(new_pos)

    def scroll_page_down(self):
        """向下滚动一页"""
        # 获取当前可见区域的高度
        visible_height = self.canvas.winfo_height()
        # 获取当前滚动位置
        current_pos = self.canvas.yview()[0]
        # 计算新的滚动位置(向下滚动一个可见区域的高度)
        new_pos = min(1, current_pos + (visible_height / self.scrollable_frame.winfo_height()))
        # 移动到新位置
        self.canvas.yview_moveto(new_pos)

    def scroll_to_top(self):
        """滚动到顶部"""
        self.canvas.yview_moveto(0)

    def scroll_to_bottom(self):
        """滚动到底部"""
        self.canvas.yview_moveto(1)

    def setup_right_frame(self):
        """设置右侧框架"""
        # 1. 创建主框架
        self.right_frame = ttk.Frame(self.paned_window, width=540)
        
        # 2. 创建主要内容区域
        title_frame = ttk.LabelFrame(self.right_frame, text="模型详情", style='primary.TLabelframe')
        title_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        content_frame = ttk.Frame(title_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        common_padding = (5, 5)
        
        # 3. 预览图区域 - 使用普通 Frame 并添加描边
        preview_frame = ttk.Frame(
            content_frame,
            style='Border.TFrame'  # 使用自定义样式
        )
        preview_frame.pack(fill=tk.X, expand=False, padx=common_padding)
        
        # 预览图容器 - 使用计算后的尺寸
        preview_container = tk.Frame(
            preview_frame,
            width=self.base_preview_size,
            height=self.base_preview_size,
            bg=self.style.colors.bg,
            highlightthickness=3,
            highlightbackground=self.style.colors.primary
        )
        preview_container.pack(pady=15, fill=tk.NONE)
        preview_container.pack_propagate(False)
        
        # 预览图标签
        self.inner_frame = tk.Frame(preview_container, bg=self.style.colors.bg)
        self.inner_frame.pack(fill='both', expand=True)
        
        self.preview_label = ttk.Label(self.inner_frame, style='Right.TLabel')
        self.preview_label.place(relx=0.5, rely=0.5, anchor="center")  # 使用相对定位确保居中
        self.preview_label.drop_target_register(DND_FILES)
        self.preview_label.dnd_bind('<<Drop>>', self.handle_drop)
        
        # 添加右键菜单绑定
        self.preview_label.bind('<Button-3>', self.show_preview_context_menu)
        
        # 4. 模型信息区域 - 使用普通 Frame 并添加描边
        info_frame = ttk.Frame(
            content_frame,
            style='Border.TFrame'  # 使用自定义样式
        )
        info_frame.pack(fill=tk.BOTH, expand=True, padx=common_padding, pady=5)
        
        # 创建一个固定高度的容器框架
        info_container = ttk.Frame(info_frame)
        info_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 设置固定高度
        info_container.configure(height=150)
        info_container.pack_propagate(False)  # 防止子控件影响容器大小
        
        # 直接使用 Frame 替代滚动区域
        self.info_frame = ttk.Frame(info_container)
        self.info_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建模型信息输入框
        self.model_name = self.create_info_entry("模型名称", with_button=True, button_text="复制", button_command=self.copy_model_name)
        self.model_info = self.create_info_entry("基础信息", is_readonly=True, with_button=True, button_text="路径", button_command=self.open_model_path)
        self.model_hash = self.create_info_entry("哈希值", is_readonly=True, with_button=True, button_text="复制", button_command=self.copy_model_hash)
        self.model_type = self.create_info_entry("模型类型", is_context_menu=True, with_button=True, button_text="同类", button_command=lambda: self.search_similar_type(self.model_type.get()))
        self.model_url = self.create_info_entry("模型网址", is_context_menu=True, with_button=True, button_text="前往", button_command=self.open_url)
        self.trigger_words = self.create_info_entry("触发词", is_context_menu=True, with_button=True, button_text="复制", button_command=self.copy_trigger_words)
        self.model_desc = self.create_info_entry("模型描述", is_context_menu=True, with_button=True, button_text="详情", button_command=self.show_full_description)
        
        # 5. 操作按钮区域 - 使用普通 Frame 并添加描边
        operation_frame = ttk.Frame(
            content_frame,
            style='Border.TFrame'  # 使用自定义样式
        )
        operation_frame.pack(fill=tk.X, expand=False, padx=common_padding, pady=5)

        button_frame = ttk.Frame(operation_frame)
        button_frame.pack(fill=tk.X, expand=False, padx=5)
        
        for i in range(6):
            button_frame.columnconfigure(i, weight=1)
        
        # 第一行按钮
        buttons = [
            ("收藏模型", self.toggle_favorite),
            ("Liblib搜索", self.search_on_liblib),
            ("Liblib抓取", self.fetch_from_liblib),
            ("Civitai抓取", self.fetch_from_civitai),
            ("适配CS", self.setup_custom_scripts),
            ("适配SD", self.setup_sd_json)  # 添加新按钮
            # ("换预览图", self.change_preview_image),
            # ("删除模型", self.delete_model),
            # ("移动模型", self.move_model),
            # ("打开路径", self.open_model_path),
            # ("更新哈希", self.update_current_hash)
        ]
        
        for i, (text, command) in enumerate(buttons):
            button = ttk.Button(button_frame, text=text, command=command, style='warning.TButton')
            button.grid(row=0, column=i, padx=5, pady=(0, 5), sticky='nsew')
            if text == "收藏模型":
                self.favorite_button = button
        
        # # 第二行按钮
        # second_row_buttons = [
        #     ("Liblib搜索", self.search_on_liblib),
        #     ("Liblib抓取", self.fetch_from_liblib),
        #     ("Civitai抓取", self.fetch_from_civitai),
        #     ("适配CS", self.setup_custom_scripts),
        #     ("去CF粘贴节点", self.show_cf_node_menu)
        # ]
        
        # for i, (text, command) in enumerate(second_row_buttons):
        #     button = ttk.Button(button_frame, text=text, command=command, style='warning.TButton')
        #     button.grid(row=1, column=i, padx=5, pady=(0, 5), sticky='nsew')
        
        # 6. 事件绑定
        self.right_frame.bind("<Configure>", self.update_canvas_width)
        self.master.bind("<Configure>", self.on_window_resize)
        self.info_frame.bind("<Configure>", self.on_canvas_resize)
        self.rebind_paste_event()

    def setup_custom_scripts(self):
        """设置custom scripts相关文件"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
        
        if not messagebox.askyesno("确认", "是否要为当前模型创建custom scripts相关文件？"):
            return
        
        try:
            # 获取模型文件路径和名称
            model_path = os.path.join(BASE_PATH, self.current_file)
            model_dir = os.path.dirname(model_path)
            model_name = os.path.splitext(os.path.basename(model_path))[0]
            
            # 创建同名文件夹
            custom_dir = os.path.join(model_dir, model_name)
            os.makedirs(custom_dir, exist_ok=True)
            
            # 获取描述和触发词内容
            description = self.model_desc.get("1.0", tk.END).strip()
            trigger_words = self.trigger_words.get("1.0", tk.END).strip()
            
            files_created = []
            
            # 只有在描述非空时创建Describe.txt
            if description:
                describe_path = os.path.join(custom_dir, "Describe.txt")
                with open(describe_path, 'w', encoding='utf-8') as f:
                    f.write(description)
                files_created.append("Describe.txt")
            
            # 只有在触发词非空时创建Trigger_Words.txt
            if trigger_words:
                trigger_path = os.path.join(custom_dir, "Trigger_Words.txt")
                with open(trigger_path, 'w', encoding='utf-8') as f:
                    f.write(trigger_words)
                files_created.append("Trigger_Words.txt")
            
            # 根据创建的文件给出相应提示
            if files_created:
                message = f"已创建以下文件：\n{', '.join(files_created)}"
                if len(files_created) < 2:
                    message += "\n\n注意：部分内容为空，未创建对应文件"
            else:
                message = "模型描述和触发词都为空，未创建任何文件"
            
            self.show_popup_message(message)
            
            # 询问是否打开文件夹
            if files_created and messagebox.askyesno("提示", "文件已创建，是否打开所在文件夹？"):
                system = platform.system()
                try:
                    if system == "Windows":
                        subprocess.run(['explorer', custom_dir])
                    elif system == "Darwin":  # macOS
                        subprocess.run(['open', custom_dir])
                    elif system == "Linux":
                        subprocess.run(['xdg-open', custom_dir])
                except Exception as e:
                    self.show_popup_message(f"打开文件夹失败：{str(e)}")
        
        except Exception as e:
            self.show_popup_message(f"创建custom scripts文件失败：{str(e)}")

    def setup_sd_json(self):
        """设置SD WebUI的json配置文件"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
        
        try:
            # 获取模型文件路径和名称
            model_path = os.path.join(BASE_PATH, self.current_file)
            model_dir = os.path.dirname(model_path)
            model_name = os.path.splitext(os.path.basename(model_path))[0]
            json_path = os.path.join(model_dir, f"{model_name}.json")
            
            # 获取描述和触发词内容
            description = self.model_desc.get("1.0", tk.END).strip()
            trigger_words = self.trigger_words.get("1.0", tk.END).strip()
            
            # 准备json数据
            json_data = {
                "description": description,
                "sd version": "",
                "activation text": trigger_words,
                "preferred weight": 0,
                "negative text": "",
                "notes": ""
            }
            
            # 如果json文件已存在，读取现有内容并更新
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        # 只更新描述和触发词字段
                        existing_data["description"] = description
                        existing_data["activation text"] = trigger_words
                        json_data = existing_data
                except json.JSONDecodeError:
                    # 如果现有文件无法解析，使用新数据
                    pass
            
            # 保存json文件
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            
            self.show_popup_message("SD配置文件已创建/更新")
            
            # 询问是否打开文件夹
            if messagebox.askyesno("提示", "配置文件已创建，是否打开所在文件夹？"):
                system = platform.system()
                try:
                    if system == "Windows":
                        subprocess.run(['explorer', '/select,', json_path])
                    elif system == "Darwin":  # macOS
                        subprocess.run(['open', '-R', json_path])
                    elif system == "Linux":
                        subprocess.run(['xdg-open', os.path.dirname(json_path)])
                except Exception as e:
                    self.show_popup_message(f"打开文件夹失败：{str(e)}")
        
        except Exception as e:
            self.show_popup_message(f"创建SD配置文件失败：{str(e)}")

    def update_current_hash(self):
        """更新当前选中模型的哈希值"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
        
        # 创建进度对话框
        dialog = tk.Toplevel(self.master)
        dialog.title("计算哈希值")
        dialog.geometry("400x120")
        dialog.transient(self.master)
        dialog.grab_set()
        
        # 居中显示
        dialog.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 200}+"
                       f"{self.master.winfo_y() + self.master.winfo_height()//2 - 60}")
        
        # 创建主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            main_frame,
            variable=progress_var,
            maximum=100,
            mode='determinate',
            style='primary.Horizontal.TProgressbar'
        )
        progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # 创建状态标签
        status_label = ttk.Label(main_frame, text="正在计算哈希值...")
        status_label.pack(fill=tk.X, pady=(0, 10))
        
        def calculate():
            try:
                # 获取文件大小用于计算进度
                full_path = os.path.join(BASE_PATH, self.current_file)
                file_size = os.path.getsize(full_path)
                
                # 使用 SHA-256 算法
                sha256_hash = hashlib.sha256()
                
                # 已读取的字节数
                bytes_read = 0
                last_update_time = time.time()
                update_interval = 0.1  # 每0.1秒更新一次界面
                
                # 以二进制模式读取文件
                with open(full_path, "rb") as f:
                    # 分块读取文件以处理大文件，使用1MB的块大小
                    for byte_block in iter(lambda: f.read(1024 * 1024), b""):  # 增加到1MB
                        sha256_hash.update(byte_block)
                        # 更新进度
                        bytes_read += len(byte_block)
                        current_time = time.time()
                        
                        # 每隔一定时间更新一次界面
                        if current_time - last_update_time >= update_interval:
                            progress = (bytes_read / file_size) * 100
                            progress_var.set(progress)
                            # 更新状态文本
                            status_label.config(text=f"已处理: {bytes_read/1024/1024:.1f} MB / {file_size/1024/1024:.1f} MB")
                            # 更新界面
                            dialog.update()
                            last_update_time = current_time
                
                # 最后更新一次进度到100%
                progress_var.set(100)
                status_label.config(text=f"已处理: {file_size/1024/1024:.1f} MB / {file_size/1024/1024:.1f} MB")
                dialog.update()
                
                # 获取哈希值
                hash_value = sha256_hash.hexdigest()
                
                # 更新显示
                self.model_hash.configure(state='normal')
                self.model_hash.delete(0, tk.END)
                self.model_hash.insert(0, hash_value)
                self.model_hash.configure(state='readonly')
                
                # 更新 model_info.json
                info = self.get_model_info(self.current_file)
                info['hash'] = hash_value
                self.save_model_info(self.current_file, info)
                
                dialog.destroy()
                self.show_popup_message("哈希值已更新")
                
            except Exception as e:
                dialog.destroy()
                self.show_popup_message(f"计算哈希值时发生错误：{str(e)}")
        
        # 在新线程中执行计算
        threading.Thread(target=calculate, daemon=True).start()

    def auto_save_changes(self):
        """自动保存更改（无提示）"""
        if not self.current_file:
            return
        
        try:
            # 获取当前所有需要保存的输入框的值
            info = {
                "type": self.model_type.get("1.0", tk.END).strip() if isinstance(self.model_type, tk.Text) else self.model_type.get(),
                "url": self.model_url.get("1.0", tk.END).strip() if isinstance(self.model_url, tk.Text) else self.model_url.get(),
                "description": self.model_desc.get("1.0", tk.END).strip() if isinstance(self.model_desc, tk.Text) else self.model_desc.get(),
                "trigger_words": self.trigger_words.get("1.0", tk.END).strip() if isinstance(self.trigger_words, tk.Text) else self.trigger_words.get(),
                "hash": self.model_hash.get() if self.model_hash else ""
            }
            
            # 获取现有信息
            existing_info = self.get_model_info(self.current_file)
            
            # 保留其他字段（如收藏状态、最后修改时间等）
            for key in existing_info:
                if key not in info and key != 'last_modified':  # 排除我们要更新的字段和last_modified
                    info[key] = existing_info[key]
            
            # 更新最后修改时间
            info['last_modified'] = time.time()
            
            # 保存到 model_info.json
            self.save_model_info(self.current_file, info)
            
        except Exception as e:
            logging.error(f"自动保存时发生错误：{str(e)}")

    def save_changes(self):
        """手动保存当前模型的所有更改"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
        
        try:
            # 获取当前所有需要保存的输入框的值
            info = {
                "type": self.model_type.get("1.0", tk.END).strip() if isinstance(self.model_type, tk.Text) else self.model_type.get(),
                "url": self.model_url.get("1.0", tk.END).strip() if isinstance(self.model_url, tk.Text) else self.model_url.get(),
                "description": self.model_desc.get("1.0", tk.END).strip() if isinstance(self.model_desc, tk.Text) else self.model_desc.get(),
                "trigger_words": self.trigger_words.get("1.0", tk.END).strip() if isinstance(self.trigger_words, tk.Text) else self.trigger_words.get(),
                "hash": self.model_hash.get() if self.model_hash else ""
            }
            
            # 获取现有信息
            existing_info = self.get_model_info(self.current_file)
            
            # 保留其他字段（如收藏状态、最后修改时间等）
            for key in existing_info:
                if key not in info and key != 'last_modified':  # 排除我们要更新的字段和last_modified
                    info[key] = existing_info[key]
            
            # 更新最后修改时间
            info['last_modified'] = time.time()
            
            # 保存到 model_info.json
            self.save_model_info(self.current_file, info)
            
            # 显示成功消息
            self.show_popup_message("更改已保存")
            
        except Exception as e:
            self.show_popup_message(f"保存更改时发生错误：{str(e)}")

    def on_window_resize(self, event):
        """窗口大小改变时的处理"""
        if event.widget == self.master:
            self.update_canvas_width(event)
            # 删除对不存在方法的调用
            # self.update_scrollbar_visibility()

    def on_canvas_resize(self, event):
        self.center_preview_image()
        self.check_load_more()

    def check_load_more(self):
        if self.canvas.yview()[1] == 1.0:
            self.load_more()

    def load_more(self):
        category = self.category_combobox.get()
        search_term = self.search_var.get().lower()
        self.load_files(category, search_term)

    def update_canvas_width(self, event):
        canvas_width = self.right_frame.winfo_width() - 20
        self.info_frame.config(width=canvas_width)
        self.center_preview_image()
        logging.debug(f"Canvas width updated to {canvas_width}")

    def center_preview_image(self):
        """居中显示预览图"""
        if hasattr(self, 'preview_image') and self.preview_image:
            # 获取预览图和容器的尺寸
            image_width = self.preview_image.width()
            image_height = self.preview_image.height()
            container_width = self.inner_frame.winfo_width()
            container_height = self.inner_frame.winfo_height()
            
            # 计算居中位置
            x = max(0, (container_width - image_width) // 2)
            y = max(0, (container_height - image_height) // 2)
            
            # 更新预览图位置
            self.preview_label.place(
                x=x, 
                y=y, 
                width=image_width, 
                height=image_height
            )
            logging.debug(f"Centered preview image at x={x}, y={y}, width={image_width}, height={image_height}")
        else:
            logging.debug("No preview image to center")

    def initial_load(self):
        """初始加载"""
        if not self.categories:
            return
        
        # 清除现有内容
        self.clear_file_list()
        
        # 设置初始类别
        initial_category = "checkpoints" if "checkpoints" in self.categories else self.categories[0]
        self.category_combobox.set(initial_category)
        
        # 更新文件夹按钮
        self.update_subfolder_buttons(initial_category)
        
        # 确保所有文件已加载并排序
        if not self.all_files:
            self.load_all_files()
        
        # 筛选前类别的文件（保持排序顺序）
        filtered_files = [
            (file, path) for file, path in self.all_files
            if path.startswith(initial_category)
        ]
        
        # 重置批次计数器
        self.current_batch = 0
        
        # 创建文件条目
        for file, path in filtered_files:
            self.create_file_entry(file, path)
        
        # 更新滚动区域
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(0)
        
        # 选择第一个文件
        if filtered_files:
            first_file = filtered_files[0]
            self.select_file(first_file[0], first_file[1])

    def clear_file_list(self):
        """清除文件列表中的所有内容"""
        # 销毁所有文件框架
        for frame_tuple in self.file_frames.values():
            frame = frame_tuple[0]
            frame.destroy()
        
        # 清空文件框架字典
        self.file_frames.clear()
        
        # 重置当前文件和批次
        self.current_file = None
        self.current_batch = 0
        
        # 清空滚动框架中的所有内容
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # 重置滚动区域
        self.canvas.configure(scrollregion=(0, 0, 0, 0))
        self.canvas.yview_moveto(0)

    def load_files_direct(self, category, search_term='', sort_method=None):
        """直接加载所有文件，不使用批量加载"""
        self.clear_file_list()
        
        # 使用当前的排序方式（如果没有指定）
        sort_method = sort_method or self.current_sort
        
        # 筛选和排序文件
        filtered_files = self.filter_files(category, search_term)
        sorted_files = self.sort_filtered_files(filtered_files, sort_method)
        
        # 接创建所有件条目
        for file, path in sorted_files:
            self.create_file_entry(file, path)

        # 更新滚动区域
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(0)

    def load_batch(self, filtered_files):
        """批量加载文件"""
        start = self.current_batch * self.batch_size
        end = start + self.batch_size
        batch = filtered_files[start:end]

        # 加载一批的文件
        for file, path in batch:
            self.create_file_entry(file, path)

        self.current_batch += 1

        # 如果还有更多文件，安加载下一批
        if end < len(filtered_files):
            self.master.after(10, lambda: self.load_batch(filtered_files))

    def on_category_selected(self, event):
        """类别选择改变时的处理"""
        # 保存当前状态
        current_sort = self.current_sort
        
        # 清空搜索框和子文件夹选择
        self.search_var.set('')
        self.current_subfolder = None
        
        # 清空文件列表和UI
        self.clear_file_list()
        
        # 重置所有子文件夹按钮状态
        for button in self.subfolder_buttons.values():
            button.configure(style='primary.TButton')
        
        # 获取新选择的类别
        new_category = self.category_combobox.get()
        
        # 更新子文件夹按钮
        self.update_subfolder_buttons(new_category)
        
        # 重新筛选当前类别的文件
        filtered_files = [
            (file, path) for file, path in self.all_files
            if path.startswith(new_category)
        ]
        
        # 应用排序
        sorted_files = self.sort_filtered_files(filtered_files, current_sort)
        
        # 重置批次计数器
        self.current_batch = 0
        
        # 创建文件条目
        self.create_file_entries_batch(sorted_files, 0)
        
        # 更新统计信息
        self.update_stats_label()
        
        # 重新绑定事件
        self.rebind_paste_event()
        self.search_entry.focus_set()

    def load_preview(self, file_name, relative_path):
        """加载预览图"""
        logging.debug(f"Loading preview for {file_name} in {relative_path}")
        image_path = self.get_image_path(file_name, relative_path)
        if not image_path:
            logging.warning("No specific preview image found, using default null image")
            image_path = get_resource_path('ui/null.png')

        try:
            with Image.open(image_path) as img:
                # 计算基础尺寸和实际显示尺寸
                base_size = self.base_preview_size  # 基础尺寸反向调整

                # 先裁剪成正方形
                width, height = img.size
                if width > height:
                    left = (width - height) // 2
                    img = img.crop((left, 0, left + height, height))
                else:
                    top = (height - width) // 2
                    img = img.crop((0, top, width, top + width))
                
                # 调整到基础尺寸
                img = img.resize((base_size, base_size), Image.LANCZOS)
                logging.debug(f"Processed size: {img.size}")
                photo = ImageTk.PhotoImage(img)
                self.preview_label.config(image=photo)
                self.preview_label.image = photo
                self.preview_image = photo  # 保存引用以防止垃圾回收
                
                # 绑定点击事件以显示全尺寸图
                self.preview_label.bind("<Button-1>", lambda e: self.show_full_size_image(image_path))
                self.preview_label.bind("<Enter>", lambda e: e.widget.configure(cursor="hand2"))
                self.preview_label.bind("<Leave>", lambda e: e.widget.configure(cursor=""))
                
                # 居中显示预览图
                self.master.update_idletasks()  # 确保容器尺寸已更新
                self.center_preview_image()
                
                logging.debug(f"Preview image loaded: {photo.width()}x{photo.height()}")
        except Exception as e:
            logging.error(f"Error loading preview image: {str(e)}")
            self.preview_label.config(image='')
            self.preview_label.image = None

    def show_full_size_image(self, image_path):
        """显示全尺寸预览图"""
        # 创建加载窗口
        loading_window = tk.Toplevel(self.master)
        loading_window.title("加载中")
        loading_window.geometry("300x100")
        
        # 使窗口居中
        loading_window.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 150}+"
                              f"{self.master.winfo_y() + self.master.winfo_height()//2 - 50}")
        
        # 添加加载提示
        loading_label = ttk.Label(loading_window, text="正在加载图片...", font=self.base_font)
        loading_label.pack(pady=10)
        
        # 添加进度条
        progress = ttk.Progressbar(loading_window, mode='indeterminate')
        progress.pack(fill=tk.X, padx=20)
        progress.start(10)
        
        def load_image():
            try:
                # 在新线程中加载和处理图片
                with Image.open(image_path) as img:
                    # 获取图片大小
                    img_size = os.path.getsize(image_path) / (1024 * 1024)  # 转换为MB
                    
                    # 如果图片大于50MB，进行预压缩
                    if img_size > 50:
                        # 计算压缩比例
                        scale_factor = min(1.0, math.sqrt(50 / img_size))
                        new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
                        img = img.resize(new_size, Image.LANCZOS)
                    
                    self._current_preview_img = img.copy()
                
                # 在主线程中创建和显示窗口
                self.master.after(0, create_preview_window)
                
            except Exception as e:
                # 在主线程中显示错误
                self.master.after(0, lambda: self.show_error_and_cleanup(str(e), loading_window))
        
        def create_preview_window():
            try:
                # 关闭加载窗口
                loading_window.destroy()
                
                # 创建预览窗口
                full_size_window = tk.Toplevel(self.master)
                full_size_window.title("全尺寸预览图")
                
                # 获取屏幕尺寸
                screen_width = full_size_window.winfo_screenwidth()
                screen_height = full_size_window.winfo_screenheight()
                
                # 设置最小窗口大小
                full_size_window.minsize(400, 300)
                
                # 计算适应屏幕的窗口大小（预留一些边距）
                margin = 100
                max_width = screen_width - margin
                max_height = screen_height - margin
                
                # 计算缩放比例
                width_ratio = max_width / self._current_preview_img.width
                height_ratio = max_height / self._current_preview_img.height
                scale_ratio = min(width_ratio, height_ratio, 1.0)
                
                # 计算初始窗口大小
                window_width = int(self._current_preview_img.width * scale_ratio)
                window_height = int(self._current_preview_img.height * scale_ratio)
                
                # 保存初始宽高比
                self._aspect_ratio = window_width / window_height
                
                # 创建图片标签
                label = tk.Label(full_size_window)
                label.pack(fill='both', expand=True)
                
                # 添加缩放状态变量
                self._current_scale = scale_ratio
                self._min_scale = 0.1  # 最小缩放比例
                self._max_scale = 3.0  # 最大缩放比例
                self._scale_speed = 0.1  # 缩放速度
                self._last_resize_time = 0  # 上次调整大小的时间
                self._resize_delay = 50  # 调整大小的延迟（毫秒）
                
                def resize_image(event=None, scale_override=None):
                    """调整图片大小以适应窗口"""
                    current_time = time.time() * 1000  # 转换为毫秒
                    
                    # 如果距离上次调整时间太短，则跳过
                    if current_time - self._last_resize_time < self._resize_delay:
                        return
                    
                    self._last_resize_time = current_time
                    
                    if event and event.widget == full_size_window:
                        # 窗口大小改变时的处理
                        win_width = event.width
                        win_height = event.height
                        
                        # 根据宽高比调整窗口大小
                        desired_height = int(win_width / self._aspect_ratio)
                        if desired_height != win_height:
                            full_size_window.geometry(f"{win_width}x{desired_height}")
                            win_height = desired_height  # 更新高度值
                        
                        # 计算缩放比例
                        width_ratio = win_width / self._current_preview_img.width
                        height_ratio = win_height / self._current_preview_img.height
                        self._current_scale = min(width_ratio, height_ratio)
                        
                        # 计算新的图片大小
                        new_width = int(self._current_preview_img.width * self._current_scale)
                        new_height = int(self._current_preview_img.height * self._current_scale)
                        
                    elif scale_override is not None:
                        # 使用指定的缩放比例
                        self._current_scale = scale_override
                        
                        # 计算新的窗口大小，保持宽高比
                        new_width = int(self._current_preview_img.width * self._current_scale)
                        new_height = int(new_width / self._aspect_ratio)
                        
                        # 确保窗口大小不超出屏幕
                        if new_width > screen_width - margin or new_height > screen_height - margin:
                            # 重新计算以适应屏幕
                            if new_width / (screen_width - margin) > new_height / (screen_height - margin):
                                new_width = screen_width - margin
                                new_height = int(new_width / self._aspect_ratio)
                            else:
                                new_height = screen_height - margin
                                new_width = int(new_height * self._aspect_ratio)
                        
                        # 更新窗口大小
                        full_size_window.geometry(f"{new_width}x{new_height}")
                    else:
                        # 使用当前窗口大小
                        new_width = full_size_window.winfo_width()
                        new_height = full_size_window.winfo_height()
                    
                    try:
                        # 调整图片大小
                        resized_img = self._current_preview_img.resize((new_width, new_height), Image.LANCZOS)
                        photo = ImageTk.PhotoImage(resized_img)
                        
                        # 更新标签
                        label.configure(image=photo)
                        label.image = photo  # 保持引用以防止垃圾回收
                    except Exception as e:
                        logging.error(f"调整图片大小时发生错误：{str(e)}")
                
                def on_mousewheel(event):
                    """处理鼠标滚轮事件"""
                    # 获取当前缩放比例
                    current_scale = self._current_scale
                    
                    # 根据滚轮方向调整缩放比例
                    if event.delta > 0:  # 向上滚动，放大
                        new_scale = min(current_scale * (1 + self._scale_speed), self._max_scale)
                    else:  # 向下滚动，缩小
                        new_scale = max(current_scale * (1 - self._scale_speed), self._min_scale)
                    
                    # 如果缩放比例有变化，则调整图片大小
                    if new_scale != current_scale:
                        resize_image(scale_override=new_scale)
                
                # 绑定事件
                full_size_window.bind('<Configure>', resize_image)
                full_size_window.bind('<MouseWheel>', on_mousewheel)  # Windows
                full_size_window.bind('<Button-4>', lambda e: on_mousewheel(type('Event', (), {'delta': 120})))  # Linux 向上滚动
                full_size_window.bind('<Button-5>', lambda e: on_mousewheel(type('Event', (), {'delta': -120})))  # Linux 向下滚动
                
                # 绑定点击事件以关闭窗口
                label.bind("<Button-1>", lambda e: full_size_window.destroy())
                label.bind("<Enter>", lambda e: e.widget.configure(cursor="hand2"))
                label.bind("<Leave>", lambda e: e.widget.configure(cursor=""))
                
                # 设置窗口初始大小和位置
                full_size_window.geometry(f"{window_width}x{window_height}")
                
                # 计算窗口位置使其居中
                x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (window_width // 2)
                y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (window_height // 2)
                
                # 确保窗口位置在屏幕内
                x = max(0, min(x, screen_width - window_width))
                y = max(0, min(y, screen_height - window_height))
                
                full_size_window.geometry(f"+{x}+{y}")
                
                # 创建并显示初始图片
                initial_img = self._current_preview_img.resize((window_width, window_height), Image.LANCZOS)
                initial_photo = ImageTk.PhotoImage(initial_img)
                label.configure(image=initial_photo)
                label.image = initial_photo
                
                def on_closing():
                    if hasattr(self, '_current_preview_img'):
                        del self._current_preview_img
                    full_size_window.destroy()
                
                full_size_window.protocol("WM_DELETE_WINDOW", on_closing)
                
                full_size_window.transient(self.master)
                full_size_window.grab_set()
                full_size_window.focus_set()
                
            except Exception as e:
                self.show_popup_message(f"创建预览窗口时发生错误：{str(e)}")
                if hasattr(self, '_current_preview_img'):
                    del self._current_preview_img
        
        def show_error_and_cleanup(self, error_message, loading_win):
            """显示错误并清理资源"""
            loading_win.destroy()
            self.show_popup_message(f"加载图片时发生错误：{error_message}")
            if hasattr(self, '_current_preview_img'):
                del self._current_preview_img
        
        # 在新线程中加载图片
        threading.Thread(target=load_image, daemon=True).start()
        

    def get_image_path(self, file_name, relative_path):
        """获取图片路径"""
        folder_path = os.path.join(BASE_PATH, relative_path)
        for ext in self.supported_image_extensions:
            image_path = os.path.join(folder_path, os.path.splitext(file_name)[0] + ext)
            if os.path.exists(image_path):
                logging.debug(f"Found image: {image_path}")
                return image_path
        logging.warning(f"No image found for {file_name} in {relative_path}")
        return None

    def load_model_info(self):
        """加载模型信息"""
        if not self.current_file:
            return
        
        info = self.get_model_info(self.current_file)
        file_name = os.path.basename(self.current_file)  # 获取完整文件名（包含后缀）
        
        # 设置模型名称为完整文件名
        if isinstance(self.model_name, ttk.Entry):
            self.model_name.configure(state='normal')
            self.model_name.delete(0, tk.END)
            self.model_name.insert(0, file_name)
            self.model_name.configure(state='readonly')
        
        # 获取文件信息
        full_path = os.path.join(BASE_PATH, self.current_file)
        file_size = os.path.getsize(full_path)
        file_mtime = os.path.getmtime(full_path)
        info_mtime = info.get('last_modified', file_mtime)
        
        # 格式化文件大小
        def format_size(size):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        
        # 格式化时间
        def format_time(timestamp):
            return time.strftime("%y-%m-%d %H:%M", time.localtime(timestamp))
        
        # 构建基础信息字符串
        basic_info = (
            f"大小: {format_size(file_size)} | "
            f"详情修改: {format_time(info_mtime)} | "
            f"文件修改: {format_time(file_mtime)}"
        )
        
        # 设置基础信息
        if isinstance(self.model_info, ttk.Entry):
            self.model_info.configure(state='normal')
            self.model_info.delete(0, tk.END)
            self.model_info.insert(0, basic_info)
            self.model_info.configure(state='readonly')
        
        # 哈希值使用 Entry
        if self.model_hash:
            self.model_hash.configure(state='normal')
            self.model_hash.delete(0, tk.END)
            self.model_hash.insert(0, info.get('hash', ''))
            self.model_hash.configure(state='readonly')
        
        # 其他字段都使用 Text
        if isinstance(self.model_type, tk.Text):
            self.model_type.delete("1.0", tk.END)
            self.model_type.insert("1.0", info.get('type', ''))
        
        if isinstance(self.model_url, tk.Text):
            self.model_url.delete("1.0", tk.END)
            self.model_url.insert("1.0", info.get('url', ''))
        
        if isinstance(self.model_desc, tk.Text):
            self.model_desc.delete("1.0", tk.END)
            self.model_desc.insert("1.0", info.get('description', ''))
        
        if isinstance(self.trigger_words, tk.Text):
            self.trigger_words.delete("1.0", tk.END)
            self.trigger_words.insert("1.0", info.get('trigger_words', ''))


    def get_model_info(self, file_path):
        """获取模型信息"""
        info_file = 'model_info.json'
        try:
            # 如果文件不存在，创建一个空的 JSON 文件
            if not os.path.exists(info_file):
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                logging.info("Created new model_info.json file")
                return {}
            
            # 读取并解析 JSON 文件
            with open(info_file, 'r', encoding='utf-8') as f:
                all_info = json.load(f)
                return all_info.get(file_path, {})
                
        except json.JSONDecodeError as e:
            logging.error(f"JSON 解析错误：{str(e)}")
            # 尝试修复并重新加载 JSON 文件
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 移除尾随逗号
                content = content.replace(',}', '}').replace(',\n}', '\n}')
                # 尝试解析修复后的内容
                all_info = json.loads(content)
                # 保存修复后文件
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(all_info, f, ensure_ascii=False, indent=2)
                return all_info.get(file_path, {})
            except Exception as e2:
                logging.error(f"修复 JSON 文件失败：{str(e2)}")
                return {}
        except Exception as e:
            logging.error(f"读取模型信息时发生误：{str(e)}")
            # 如果发生其他错误，创建新的 JSON 文件
            try:
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                logging.info("Created new model_info.json file after error")
            except Exception as e2:
                logging.error(f"创建新 JSON 文件失败：{str(e2)}")
            return {}

    def save_model_info(self, file_path, info):
        """保存模型信息"""
        info_file = 'model_info.json'
        all_info = {}
        if os.path.exists(info_file):
            with open(info_file, 'r', encoding='utf-8') as f:
                all_info = json.load(f)
        
        # 保持收藏状态
        current_info = all_info.get(file_path, {})
        info['is_favorite'] = current_info.get('is_favorite', False)
        
        # 添加最后修改时间戳
        info['last_modified'] = time.time()
        
        all_info[file_path] = info
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(all_info, f, ensure_ascii=False, indent=2)

    def create_info_entry(self, label_text, is_context_menu=False, is_text=True, is_readonly=False, with_button=False, button_text="", button_command=None):
        """创建信息输入框"""
        # 创建主框架，设置合适的边距
        frame = ttk.Frame(self.info_frame)
        
        # 设置框架填充方式
        if label_text == "模型描述":
            frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)  # 让描述框架可以在垂直方向扩展
        else:
            frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建标签，使用粗体，调整字间距以保持宽度一致
        label = ttk.Label(
            frame, 
            text=label_text + ":", 
            font=self.base_font,
            width=8,
            anchor='w',
            justify='right'
        )
        label.pack(side=tk.LEFT, padx=(0, 5))
        
        # 创建输入区域容器
        input_container = ttk.Frame(frame)
        if label_text == "模型描述":
            input_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))  # 让描述容器可以在垂直方向扩展
        else:
            input_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # 创建输入框
        if is_readonly or label_text == "模型名称":  # 修改条件，模型名称也使用只读的Entry
            # 只读字段使用 Entry
            entry = ttk.Entry(input_container, width=20, font=self.base_font)
            entry.pack(fill=tk.X)
            entry.configure(state='readonly')
            
            # 创建并绑定右键菜单
            if is_context_menu:
                context_menu = self.create_context_menu(entry)
                entry.bind('<Button-3>', lambda e: self.show_context_menu(e, context_menu))
            
        else:
            # 其他字段使用 Text
            entry = tk.Text(
                input_container, 
                font=self.base_font,
                width=20, 
                height=4 if label_text == "模型描述" else 1,
                undo=True,  # 启用撤销功能
                wrap='word' if label_text == "模型描述" else 'none'  # 只有描述框启用自动换行
            )
            if label_text == "模型描述":
                entry.pack(fill=tk.BOTH, expand=True)  # 让描述文本框在两个方向上都可以扩展
            else:
                entry.pack(fill=tk.X)
            
            # 创建并绑定右键菜单
            if is_context_menu: 
                context_menu = self.create_context_menu(entry)
                entry.bind('<Button-3>', lambda e: self.show_context_menu(e, context_menu))
            
            # 为可输入的文本框添加 Tab 键序列
            entry.bind('<Tab>', self.focus_next_widget)
            entry.bind('<Shift-Tab>', self.focus_prev_widget)
        
        # 创建按钮（如果需要）
        if with_button:
            if button_text == "前往":
                button = ttk.Button(
                    frame, 
                    text=button_text, 
                    command=lambda: self.open_url(entry.get("1.0", tk.END).strip() if isinstance(entry, tk.Text) else entry.get()) if (entry.get("1.0", tk.END).strip() if isinstance(entry, tk.Text) else entry.get()) else self.show_popup_message("网址为空"),
                    style='info.TButton',
                    width=6
                )
            elif button_text == "同类":
                button = ttk.Button(
                    frame,
                    text=button_text,
                    command=lambda: self.search_similar_type(entry.get("1.0", tk.END).strip()),
                    style='info.TButton',
                    width=6
                )
            else:
                button = ttk.Button(
                    frame, 
                    text=button_text, 
                    command=button_command,
                    style='info.TButton',
                    width=6
                )
            button.pack(side=tk.RIGHT)
        
        # 为输入控件添加事件绑定
        if not is_readonly:
            entry.bind('<Key>', self.on_text_change)
            entry.bind('<FocusIn>', lambda e: self.set_editing_state(True))
            entry.bind('<FocusOut>', lambda e: self.set_editing_state(False))
        
        return entry

    def set_editing_state(self, state):
        """设置编辑状态"""
        self.is_editing = state
        if not state and self.save_timer:
            # 当用户完成编辑时，执行保存
            self.master.after_cancel(self.save_timer)
            self.save_timer = None
            self.auto_save_changes()

    def on_entry_change(self, event):
        """处理输入框内容变化"""
        if not self.is_editing:
            return
        
        # 取消之前的定时器
        if self.save_timer:
            self.master.after_cancel(self.save_timer)
        
        # 设置新的定时器
        self.save_timer = self.master.after(500, self.auto_save_changes)

    def on_text_change(self, event):
        """处理文本框内容变化"""
        if not self.is_editing:
            return
        
        # 取消之前的定时器
        if self.save_timer:
            self.master.after_cancel(self.save_timer)
        
        # 设置新的定时器
        self.save_timer = self.master.after(500, self.auto_save_changes)

    def search_similar_type(self, model_type):
        """搜索相同类型的模型"""
        if isinstance(self.model_type, tk.Text):
            model_type = self.model_type.get("1.0", tk.END).strip()
        if model_type:
            # 设置搜索框的值
            self.search_var.set(model_type)
            # 触发搜索
            self.search_files()
            # 显示提示消息
            self.show_popup_message(f"正在搜索类型：{model_type}")

    def open_url(self, url):
        if url:
            webbrowser.open(url)
        else:
            messagebox.showinfo("提示", "网址为空")

    def copy_trigger_words(self):
        text = self.trigger_words.get("1.0", tk.END).strip()
        self.master.clipboard_clear()
        self.master.clipboard_append(text)
        self.show_popup_message("触发词已复制")

    def refresh_files(self):
        """优化的刷新方法"""
        # 保存当前状态
        current_category = self.category_combobox.get()
        current_subfolder = self.current_subfolder
        current_file = self.current_file
        
        # 清除所有缓存
        self.fs_cache.clear()
        try:
            self.load_thumbnail.cache_clear()
        except AttributeError:
            original_load_thumbnail = self.load_thumbnail
            self.load_thumbnail = lru_cache(maxsize=100)(original_load_thumbnail)
        
        self._file_paths_cache.clear()
        self._preview_exists_cache.clear()
        
        # 清空文件列表和UI
        self.clear_file_list()
        self.all_files = []  # 确保清空文件列表
        
        # 重新加载类别
        self.categories = []
        self.load_categories()
        
        # 异步加载文件
        def on_refresh_complete():
            try:
                # 恢复之前的选择
                if current_category in self.categories:
                    self.category_combobox.set(current_category)
                    self.update_subfolder_buttons(current_category)
                    
                    if current_subfolder:
                        self.current_subfolder = current_subfolder
                        if current_subfolder in self.subfolder_buttons:
                            self.subfolder_buttons[current_subfolder].configure(style='secondary.TButton')
                    
                    # 使用新的文件列表加载文件
                    self.load_files(current_category, self.search_var.get(), self.current_sort)
                    
                    # 如果之前有选中的文件，尝试重新选中
                    if current_file:
                        file_name = os.path.basename(current_file)
                        relative_path = os.path.dirname(current_file)
                        self.select_file(file_name, relative_path)
                
                self.show_popup_message("文件列表已刷新")
            except Exception as e:
                logging.error(f"Error in on_refresh_complete: {str(e)}")
        
        # 开始异步加载
        self.load_all_files()
        self.master.after(100, lambda: self.check_loading_complete(on_refresh_complete))

    def check_loading_complete(self, callback):
        """检查加载是否完成"""
        if not self.loading_thread or not self.loading_thread.is_alive():
            callback()
        else:
            self.master.after(100, lambda: self.check_loading_complete(callback))

    def show_full_description(self):
        """显示完整的模型描述（可编辑）"""
        if not self.current_file:
            return
        
        desc_window = tk.Toplevel(self.master)
        desc_window.title("模型描述")
        desc_window.geometry("800x600")  # 设置初始大小
        
        # 设置窗口最小尺寸
        desc_window.minsize(600, 400)
        
        # 获取模型描述输入框的位置和大小
        desc_x = self.model_desc.winfo_rootx()
        desc_y = self.model_desc.winfo_rooty()
        desc_height = self.model_desc.winfo_height()
        
        # 计算弹出窗口的位置（在模型描述输入框的附近）
        window_x = desc_x
        window_y = desc_y + desc_height + 5  # 在输入框下方留5像素的间距
        
        # 确保窗口不会超出主窗口的范围
        main_width = self.master.winfo_width()
        main_height = self.master.winfo_height()
        main_x = self.master.winfo_rootx()
        main_y = self.master.winfo_rooty()
        
        # 如果窗口会超出右边界，向左调整
        if window_x + 800 > main_x + main_width:
            window_x = main_x + main_width - 800
        
        # 如果窗口会超出下边界，向上弹出
        if window_y + 600 > main_y + main_height:
            window_y = desc_y - 600 - 5  # 在输入框上方
        
        # 设置窗口位置
        desc_window.geometry(f"800x600+{window_x}+{window_y}")
        
        # 创建主框架
        main_frame = ttk.Frame(desc_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建文本编辑器和滚动条的容器框架
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建文本编辑器
        text_widget = tk.Text(
            text_frame,
            wrap="word",
            font=self.base_font,
            undo=True  # 启用撤销功能
        )
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 放置文本编辑器并配置滚动条
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_widget.yview)
        
        # 插入当前描述内容
        current_desc = self.model_desc.get("1.0", tk.END).strip()
        text_widget.insert("1.0", current_desc)
        
        def on_closing():
            """窗口关闭时的处理"""
            # 获取编辑后的内容
            new_desc = text_widget.get("1.0", tk.END).strip()
            
            # 更新主窗口的描述内容
            self.model_desc.delete("1.0", tk.END)
            self.model_desc.insert("1.0", new_desc)
            
            # 自动保存更改
            self.auto_save_changes()
            
            # 关闭窗口
            desc_window.destroy()
        
        # 绑定窗口关闭事件
        desc_window.protocol("WM_DELETE_WINDOW", on_closing)
        
        # 设置窗口状态
        desc_window.state('normal')
        
        # 添加最大化/还原按钮
        desc_window.resizable(True, True)

    def copy_model_name(self):
        """复制模型名称（不包含后缀名）"""
        if self.current_file:
            # 获取文件名（不包含路径）
            file_name = os.path.basename(self.current_file)
            # 获取不带后缀的文件名
            model_name = os.path.splitext(file_name)[0]
            # 复制到剪贴板
            self.master.clipboard_clear()
            self.master.clipboard_append(model_name)
            self.show_popup_message("模型名称已复制")
        else:
            self.show_popup_message("没有选择模型文件")

    def on_search_change(self, *args):
        self.search_files()

    def show_popup_message(self, message):
        popup = tk.Toplevel(self.master)
        popup.title("")
        # 增加窗口大小以适应外描边
        popup.geometry("326x106")  # 220+6 x 60+6 来适应3像素的边框
        popup.resizable(False, False)
        
        # 使用当前主题的颜色
        bg_color = self.style.colors.bg
        fg_color = self.style.colors.fg
        border_color = self.style.colors.primary
        
        popup.configure(bg=border_color)  # 设置窗口背景色为边框色
        
        popup.overrideredirect(True)
        
        # 调整弹窗位置
        popup.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 113}+{self.master.winfo_y() + self.master.winfo_height()//2 - 33}")
        
        # 创建内部框架
        inner_frame = tk.Frame(
            popup,
            bg=border_color,  # 边框色
            bd=0
        )
        inner_frame.pack(fill='both', expand=True, padx=3, pady=3)  # 使用padding创建边框效果
        
        # 创建消息容器
        message_frame = tk.Frame(
            inner_frame,
            bg=bg_color,  # 内容背景色
            bd=0
        )
        message_frame.pack(fill='both', expand=True)
        
        # 创建消息标签
        label = tk.Label(
            message_frame,
            text=message,
            bg=bg_color,
            fg=fg_color,
            font=self.base_title_font  # 直接使用字体大小
        )
        label.pack(expand=True)
        
        # 将弹窗置于顶层
        popup.lift()
        popup.focus_force()
        
        def fade_away(alpha):
            alpha = alpha - 0.1
            popup.attributes("-alpha", alpha)
            if alpha > 0:
                popup.after(50, lambda: fade_away(alpha))
            else:
                popup.destroy()
        
        popup.after(2000, lambda: fade_away(1.0))

    def create_file_entry(self, file_name, relative_path):
        """创建文件列表项"""
        # 创建主框架
        frame = ttk.Frame(self.scrollable_frame, style='List.TFrame')
        frame.pack(fill=tk.X, expand=True, pady=5)  # 添加 expand=True
        
        # 创建内容框架
        content_frame = ttk.Frame(frame, style='List.TFrame')
        content_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # 创建左侧缩略图容器
        thumbnail_container = ttk.Frame(content_frame, style='List.TFrame')
        thumbnail_container.pack(side=tk.LEFT, padx=(0, 10))
        
        # 加载缩略图
        thumbnail = self.load_thumbnail(file_name, relative_path)
        
        # 创建缩略图标签
        thumbnail_label = ttk.Label(
            thumbnail_container,
            image=thumbnail if thumbnail else None,
            style='List.TLabel'
        )
        thumbnail_label.image = thumbnail  # 保持引用
        thumbnail_label.pack()
        
        # 绑定点击事件
        full_path = os.path.join(relative_path, file_name)
        thumbnail_label.bind("<Button-1>", lambda e, fn=file_name, rp=relative_path: self.select_file(fn, rp))
        
        # 如果是收藏的模型，添加收藏图标
        if self.is_favorite(full_path):
            if self.favorite_icon is None:
                try:
                    favorite_image = Image.open(get_resource_path('ui/favorite.png'))
                    if favorite_image.mode != 'RGBA':
                        favorite_image = favorite_image.convert('RGBA')
                    # 调整收藏图标大小为缩略图的1/3
                    favorite_icon_size = (self.thumbnail_size[0] // 3, self.thumbnail_size[1] // 3)
                    favorite_image = favorite_image.resize(favorite_icon_size, Image.LANCZOS)
                    background = Image.new('RGBA', favorite_image.size, (0, 0, 0, 0))
                    background.paste(favorite_image, (0, 0), favorite_image)
                    self.favorite_icon = ImageTk.PhotoImage(background)
                except Exception as e:
                    logging.error(f"Error loading favorite icon: {str(e)}")
                    self.favorite_icon = None
                    pass
                    
            if self.favorite_icon:
                favorite_label = tk.Label(
                    thumbnail_label,
                    image=self.favorite_icon,
                    bg=self.style.colors.bg,
                    bd=0,
                    highlightthickness=0
                )
                favorite_label.place(x=2, y=2)
                favorite_label.bind("<Button-1>", lambda e, fn=file_name, rp=relative_path: self.select_file(fn, rp))

                pass
        
        # 创建右侧文本容器
        text_container = ttk.Frame(content_frame, style='List.TFrame')
        text_container.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 创建路径标签
        path_label = ttk.Label(
            text_container, 
            text=f"路径: {relative_path}", 
            style='List.TLabel',
            anchor='w'
        )
        path_label.pack(fill=tk.X, expand=True)
        
        # 创建名称标签
        name_label = ttk.Label(
            text_container, 
            text=f"模型: {os.path.splitext(file_name)[0]}", 
            style='List.TLabel',
            anchor='w'
        )
        name_label.pack(fill=tk.X, expand=True)
        
        # 添加分隔线
        separator = ttk.Separator(frame, orient='horizontal')
        separator.pack(fill=tk.X, expand=True, padx=0, pady=0)
        
        # 保存框架引用
        self.file_frames[full_path] = (frame, path_label, name_label)
        
        # 为所有组件绑定左键点击事件
        for widget in [frame, content_frame, thumbnail_container, thumbnail_label, text_container, path_label, name_label]:
            widget.bind("<Button-1>", lambda e, fn=file_name, rp=relative_path: self.select_file(fn, rp))
            widget.bind('<Button-3>', lambda e, fp=full_path: self.show_model_context_menu(e, fp))
        
        # 设置鼠标样式为手型
        for widget in [frame, content_frame, thumbnail_container, thumbnail_label, text_container, path_label, name_label]:
            widget.bind("<Enter>", lambda e: e.widget.configure(cursor="hand2"))
            widget.bind("<Leave>", lambda e: e.widget.configure(cursor=""))

    @lru_cache(maxsize=100)  # 添加缓存装饰器
    def load_thumbnail(self, file_name, relative_path, size=None, crop=True):
        """优化的缩略图加载"""
        if size is None:
            size = self.thumbnail_size
        
        # 使用缓存的文件系统操作
        folder_path = os.path.join(BASE_PATH, relative_path)
        image_path = None
        
        # 检查预览图
        for ext in self.supported_image_extensions:
            test_path = os.path.join(folder_path, os.path.splitext(file_name)[0] + ext)
            if self.fs_cache.get_file_info(test_path):
                image_path = test_path
                break
        
        if not image_path:
            # 使用默认图片
            null_image_path = get_resource_path('ui/null.png')
            if os.path.exists(null_image_path):
                return self.process_image(null_image_path, size, crop)
            return None
        
        return self.process_image(image_path, size, crop)

    def process_image(self, image_path, size, crop=True):
        try:
            with Image.open(image_path) as img:
                if crop:
                    width, height = img.size
                    if width / height > size[0] / size[1]:
                        new_width = int(height * size[0] / size[1])
                        left = (width - new_width) // 2
                        img = img.crop((left, 0, left + new_width, height))
                    else:
                        new_height = int(width * size[1] / size[0])
                        top = (height - new_height) // 2
                        img = img.crop((0, top, width, top + new_height))
                img = img.resize(size, Image.LANCZOS)
                return ImageTk.PhotoImage(img)
        except Exception as e:
            logging.error(f"Error processing image {image_path}: {str(e)}")
        return None

    def select_file(self, file_name, relative_path):
        logging.debug(f"Selecting file: {file_name} in {relative_path}")
        new_current_file = os.path.join(relative_path, file_name)
        
        # 取消之前选中项的样式
        if self.current_file and self.current_file in self.file_frames:
            frame, path_label, name_label = self.file_frames[self.current_file]
            frame.configure(style='List.TFrame')
            path_label.configure(style='Left.TLabel')
            name_label.configure(style='Left.TLabel')
            # 重置所有子部件的样式
            for widget in frame.winfo_children():
                if isinstance(widget, ttk.Frame):
                    widget.configure(style='List.TFrame')
                elif isinstance(widget, ttk.Label):
                    widget.configure(style='Left.TLabel')
        
        # 设置新选中项的样式
        if new_current_file in self.file_frames:
            self.current_file = new_current_file
            frame, path_label, name_label = self.file_frames[new_current_file]
            frame.configure(style='Selected.TFrame')  # 使用 secondary 颜色
            path_label.configure(style='Selected.TLabel')  # 使用 secondary 颜色
            name_label.configure(style='Selected.TLabel')  # 使用 secondary 颜色
            # 设置所有子部件的样式
            for widget in frame.winfo_children():
                if isinstance(widget, ttk.Frame):
                    widget.configure(style='Selected.TFrame')  # 使用 secondary 颜色
                elif isinstance(widget, ttk.Label):
                    widget.configure(style='Selected.TLabel')  # 使用 secondary 颜色
            
            self.load_preview(file_name, relative_path)
            self.load_model_info()

        else:
            logging.error(f"File not found in file_frames: {new_current_file}")

        # 更新收藏按钮文本
        self.update_favorite_button_text()

    def setup_drag_and_drop(self):
        self.master.drop_target_register(DND_FILES)
        self.master.dnd_bind('<<Drop>>', self.handle_drop)

    def handle_drop(self, event):
        data = event.data
        logging.debug(f"Received drop event with data: {data}")
        
        if self.current_file:
            if messagebox.askyesno("确认", "是否需要替换换预览图？"):
                if data.startswith('http://') or data.startswith('https://'):
                    # 直接处理 URL
                    self.replace_preview_image_from_url(data)
                elif data.startswith('{'):
                    # 尝试解析 JSON
                    try:
                        drop_data = json.loads(data)
                        if isinstance(drop_data, list) and len(drop_data) > 0:
                            # Edge 浏览器可能会传递一个列表
                            url = drop_data[0].get('url', '')
                        elif isinstance(drop_data, dict):
                            # 他浏览器可能传递一个字典
                            url = drop_data.get('url', '') or drop_data.get('text/uri-list', '') or drop_data.get('text/plain', '')
                        else:
                            url = ''

                        if url:
                            self.replace_preview_image_from_url(url)
                        else:
                            self.show_popup_message("无识别拖入的图片")
                    except json.JSONDecodeError:
                        # 如果不是 JSON，可能是本地文径
                        self.replace_preview_image(data)
                else:
                    # 假设本地文件路径
                    self.replace_preview_image(data)
        else:
            self.show_popup_message("请先选择个模型文件")

    def replace_preview_image_from_url(self, url):
        logging.debug(f"Attempting to replace preview image from URL: {url}")
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                logging.debug(f"Created temporary file: {temp_file.name}")
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    temp_file.write(response.read())
                logging.debug(f"Downloaded image to temporary file")
                self.replace_preview_image(temp_file.name)
        except Exception as e:
            logging.error(f"Error downloading image from URL: {str(e)}")
            self.show_popup_message(f"从URL下图片时发生误：{str(e)}")

    def replace_preview_image(self, new_image_path):
        """替换预览图"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return

        model_dir = os.path.dirname(os.path.join(BASE_PATH, self.current_file))
        model_name = os.path.splitext(os.path.basename(self.current_file))[0]
        new_image_name = f"{model_name}.png"
        new_image_path_full = os.path.join(model_dir, new_image_name)

        try:
            # 转换图片格式为PNG并保存
            with Image.open(new_image_path) as img:
                img.save(new_image_path_full, "PNG")
            
            # 清除缓存
            self.load_thumbnail.cache_clear()
            self._preview_exists_cache.clear()  # 清除预览图存在状态的缓存
            
            # 重新加载预览图
            self.load_preview(os.path.basename(self.current_file), os.path.dirname(self.current_file))
            
            # 获取当前文件的frame
            if self.current_file in self.file_frames:
                frame, _, _ = self.file_frames[self.current_file]
                
                # 查找并更新缩略图
                for child in frame.winfo_children():
                    if isinstance(child, ttk.Frame):  # 找到内容框架
                        for content_child in child.winfo_children():
                            if isinstance(content_child, ttk.Frame):  # 找到左侧容器
                                # 重新加载缩略图
                                new_image = self.load_thumbnail(
                                    os.path.basename(self.current_file),
                                    os.path.dirname(self.current_file),
                                    size=self.thumbnail_size,
                                    crop=True
                                )
                                
                                if new_image:
                                    # 更新缩略图
                                    for label in content_child.winfo_children():
                                        if isinstance(label, ttk.Label) and hasattr(label, 'image'):
                                            label.configure(image=new_image)
                                            label.image = new_image
                                            
                                            # 如果是收藏的模型，重新添加收藏图标
                                            if self.is_favorite(self.current_file):
                                                if self.favorite_icon:
                                                    favorite_label = tk.Label(
                                                        label,
                                                        image=self.favorite_icon,
                                                        bg=self.style.colors.bg,
                                                        bd=0,
                                                        highlightthickness=0
                                                    )
                                                    favorite_label.place(x=2, y=2)
                                                    favorite_label.bind(
                                                        "<Button-1>",
                                                        lambda e, fn=os.path.basename(self.current_file),
                                                        rp=os.path.dirname(self.current_file): self.select_file(fn, rp)
                                                    )
            
            self.show_popup_message("预览图已成功替换")
            
        except Exception as e:
            self.show_popup_message(f"替换预览图时发生错误：{str(e)}")
        finally:
            # 如果是临时文件，删除它
            if new_image_path.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(new_image_path)
                except:
                    pass

    def refresh_thumbnail(self, file_name, relative_path):
        """刷新缩略图"""
        full_path = os.path.join(relative_path, file_name)
        if full_path in self.file_frames:
            frame, _, _ = self.file_frames[full_path]
            
            # 查找缩略图容器
            thumbnail_container = None
            for child in frame.winfo_children():
                if isinstance(child, ttk.Frame):
                    thumbnail_container = child
                    break
            
            if thumbnail_container:
                # 重新加载缩略图，使用全局参数
                new_image = self.load_thumbnail(file_name, relative_path, size=self.thumbnail_size, crop=True)
                
                if new_image:
                    # 查找并更新图片标签
                    for child in thumbnail_container.winfo_children():
                        if isinstance(child, ttk.Label) and hasattr(child, 'image'):
                            child.configure(image=new_image)
                            child.image = new_image
                            break
                    
                    # 如果是收藏的模型，保持收藏图标显示
                    if self.is_favorite(full_path):
                        has_favorite_icon = False
                        for child in thumbnail_container.winfo_children():
                            if isinstance(child, (tk.Label, ttk.Label)) and hasattr(child, 'image') and child.image == self.favorite_icon:
                                has_favorite_icon = True
                                break
                        
                        if not has_favorite_icon and self.favorite_icon:
                            favorite_label = tk.Label(
                                thumbnail_container,
                                image=self.favorite_icon,
                                bg=self.style.lookup('Left.TFrame', 'background'),
                                bd=0,
                                highlightthickness=0
                            )
                            favorite_label.image = self.favorite_icon
                            favorite_label.place(x=2, y=2)

    def open_model_path(self):
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
        
        model_path = os.path.join(BASE_PATH, self.current_file)
        if os.path.exists(model_path):
            try:
                system = platform.system()
                if system == "Windows":
                    subprocess.run(['explorer', '/select,', model_path])
                elif system == "Darwin":  # macOS
                    subprocess.run(['open', '-R', model_path])
                elif system == "Linux":
                    subprocess.run(['xdg-open', os.path.dirname(model_path)])
                else:
                    self.show_popup_message("不支持操作系统")
            except Exception as e:
                self.show_popup_message(f"开文件路径时发生错误：{str(e)}")
        else:
            self.show_popup_message("模型文件不存在")

    def paste_image(self, event=None):
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return "break"

        try:
            # 尝试获取剪贴板中的图片
            image = ImageGrab.grabclipboard()
            
            if image:
                # 如果是 PIL Image 对象或文件径列表
                is_image = isinstance(image, Image.Image)
                is_image_list = isinstance(image, list) and len(image) > 0 and isinstance(image[0], str) and image[0].lower().endswith(self.supported_image_extensions)
                
                if is_image or is_image_list:
                    if messagebox.askyesno("确认", "是否需要替换预览图？"):
                        if is_image:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                                image.save(temp_file.name, "PNG")
                                self.replace_preview_image(temp_file.name)
                        else:
                            self.replace_preview_image(image[0])
                    return "break"

            # 检查剪贴板中的文本内容
            clipboard_content = ""
            try:
                clipboard_content = self.master.clipboard_get()
            except tk.TclError:
                pass

            if clipboard_content:
                if os.path.isfile(clipboard_content) and clipboard_content.lower().endswith(self.supported_image_extensions):
                    # 如果是本地图片文件路径
                    if messagebox.askyesno("确认", "检测到本地图文件，是否要替换预览图？"):
                        self.replace_preview_image(clipboard_content)
                    return "break"
                elif clipboard_content.lower().startswith(('http://', 'https://')) and clipboard_content.lower().endswith(self.supported_image_extensions):
                    # 如果是图片URL
                    if messagebox.askyesno("确认", "检测到图片URL，是否需要替换览图？"):
                        self.replace_preview_image_from_url(clipboard_content)
                    return "break"

            # 如果不是图片相关内容，允许默认粘贴行为
            return None

        except Exception as e:
            self.show_popup_message(f"粘贴图片时发错误：{str(e)}")
            return "break"

    def delete_model(self):
        """删除模型及其相关文件"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return

        if messagebox.askyesno("确认删除", "您确定要删除这个模型和相关文件？此操作不可撤销。"):
            try:
                # 获取文件路径信息
                model_path = os.path.join(BASE_PATH, self.current_file)
                model_dir = os.path.dirname(model_path)
                model_basename = os.path.splitext(os.path.basename(model_path))[0]
                
                # 删除模型文件
                os.remove(model_path)
                
                # 删除同名json文件（如果存在）
                json_path = os.path.join(model_dir, f"{model_basename}.json")
                if os.path.exists(json_path):
                    os.remove(json_path)

                # 删除预览图（如果存在）
                preview_path = self.get_image_path(os.path.basename(self.current_file), os.path.dirname(self.current_file))
                if preview_path:
                    os.remove(preview_path)
                
                # 删除适配CS生成的配置文件夹（如果存在）
                cs_folder = os.path.join(model_dir, model_basename)
                if os.path.exists(cs_folder) and os.path.isdir(cs_folder):
                    shutil.rmtree(cs_folder)

                # 从 all_files 列表中移除
                self.all_files = [(f, p) for f, p in self.all_files if os.path.join(p, f) != self.current_file]

                # 从 file_frames 字典中移除
                if self.current_file in self.file_frames:
                    frame, _, _ = self.file_frames[self.current_file]
                    frame.destroy()  # 销毁框架
                    del self.file_frames[self.current_file]

                # 从 model_info.json 中移除
                info_file = 'model_info.json'
                if os.path.exists(info_file):
                    with open(info_file, 'r', encoding='utf-8') as f:
                        all_info = json.load(f)
                    if self.current_file in all_info:
                        del all_info[self.current_file]
                    with open(info_file, 'w', encoding='utf-8') as f:
                        json.dump(all_info, f, ensure_ascii=False, indent=2)

                # 从收藏集合中移除
                if self.current_file in self.favorites:
                    self.favorites.remove(self.current_file)

                # 重置当前文件
                self.current_file = None

                # 重新加载当前类别的文件列表
                category = self.category_combobox.get()
                self.load_files(category, sort_method=self.current_sort)

                self.show_popup_message("模型和相关文件已成功删除")

            except Exception as e:
                self.show_popup_message(f"删除模型时发生错误：{str(e)}")

    def rebind_paste_event(self):
        # 为索框重新绑定 Ctrl+V 事件
        self.search_entry.bind("<Control-v>", self.paste_image)
        
        # 为所有信输入重新绑定 Ctrl+V 事件
        for widget in [self.model_name, self.model_type, self.model_url, self.model_desc, self.trigger_words]:
            if isinstance(widget, tk.Text):
                widget.bind("<Control-v>", self.paste_image)
            elif isinstance(widget, ttk.Entry):
                widget.bind("<Control-v>", self.paste_image)

    def select_previous_model(self, event=None):
        """选择上一个模型"""
        # 如果焦点在类别选择框上，不处理上下键
        if self.master.focus_get() == self.category_combobox:
            return
        
        if not self.file_frames:
            return
        
        # 获取所有文件路径的列表
        file_paths = list(self.file_frames.keys())
        
        if not self.current_file:
            # 如果当前没有选中的文件，选择最后一个
            last_file = file_paths[-1]
            file_name = os.path.basename(last_file)
            relative_path = os.path.dirname(last_file)
            self.select_file(file_name, relative_path)
            return
        
        # 获取当前文件的索引
        try:
            current_index = file_paths.index(self.current_file)
            # 获取上一个文件的索引（如果是第一个则循环到最后一个）
            previous_index = (current_index - 1) if current_index > 0 else len(file_paths) - 1
            previous_file = file_paths[previous_index]
            
            # 择上一个文件
            file_name = os.path.basename(previous_file)
            relative_path = os.path.dirname(previous_file)
            self.select_file(file_name, relative_path)
            
            # 确保中项目可见
            self.ensure_file_visible(previous_file)
        except ValueError:
            pass

    def select_next_model(self, event=None):
        """选择下一个模型"""
        # 如果焦点在类别选择框上，不理上下键
        if self.master.focus_get() == self.category_combobox:
            return
        
        if not self.file_frames:
            return
        
        # 获取所有文件路径的列表
        file_paths = list(self.file_frames.keys())
        
        if not self.current_file:
            # 如果当前没有中的文件，选择第一个
            first_file = file_paths[0]
            file_name = os.path.basename(first_file)
            relative_path = os.path.dirname(first_file)
            self.select_file(file_name, relative_path)
            return
        
        # 获取当前文件的索引
        try:
            current_index = file_paths.index(self.current_file)
            # 获取一个文件的索引（如果是最后一个则循环到第一个）
            next_index = (current_index + 1) % len(file_paths)
            next_file = file_paths[next_index]
            
            # 选择下一个文件
            file_name = os.path.basename(next_file)
            relative_path = os.path.dirname(next_file)
            self.select_file(file_name, relative_path)
            
            # 确保选中的项目可见
            self.ensure_file_visible(next_file)
        except ValueError:
            pass

    def ensure_file_visible(self, file_path):
        """确保文件在可视区域内"""
        if file_path not in self.file_frames:
            return
        
        frame = self.file_frames[file_path][0]
        frame_top = frame.winfo_y()
        frame_bottom = frame_top + frame.winfo_height()
        
        canvas_height = self.canvas.winfo_height()
        scroll_top = self.canvas.yview()[0] * self.scrollable_frame.winfo_height()
        scroll_bottom = self.canvas.yview()[1] * self.scrollable_frame.winfo_height()
        
        # 如果选中的项目在可视区域外，调整滚动位置
        if frame_top < scroll_top:
            # 如果项目在可视区域上，向上滚动
            self.canvas.yview_moveto(frame_top / self.scrollable_frame.winfo_height())
        elif frame_bottom > scroll_bottom:
            # 如果项目在可视区域下方，向下滚动
            self.canvas.yview_moveto((frame_bottom - canvas_height) / self.scrollable_frame.winfo_height())

    def update_subfolder_buttons(self, category):
        """更新子文件夹按钮"""
        # 清除现有的按钮和框架
        for widget in self.quick_filter_frame.winfo_children():
            widget.destroy()
        self.subfolder_buttons.clear()
        self.current_subfolder = None

        # 获取类别路径
        category_path = os.path.join(BASE_PATH, category)
        if not os.path.exists(category_path):
            return

        # 获取所有子文件夹并检查其中的模型文件
        subfolders = []
        has_root_files = False
        
        # 检查根目录下是否有模型文件
        for item in os.listdir(category_path):
            item_path = os.path.join(category_path, item)
            if os.path.isdir(item_path):
                # 检查子文件夹中是否包含支持的模型文件
                if self.check_directory_for_models(item_path):
                    subfolders.append(item)
            elif item.endswith(self.supported_model_extensions):
                has_root_files = True

        # 如果没有任何子文件夹也没有根目录文件，返回
        if not subfolders and not has_root_files:
            ttk.Frame(self.quick_filter_frame, style='Left.TFrame', height=1).pack(fill=tk.X)
            return

        # 设置固定的按钮参数
        buttons_per_row = 3
        button_width = 10

        # 子文件夹排序，如果有根目录文件，将"其他"添加到末尾
        sorted_subfolders = sorted(subfolders)
        if has_root_files:
            sorted_subfolders.append("其他")
        
        # 添加"收藏"按钮
        sorted_subfolders.append("收藏")

        # 计算需要的行数，始终使用完整的3列布局
        total_buttons = len(sorted_subfolders)
        padding_needed = (buttons_per_row - (total_buttons % buttons_per_row)) % buttons_per_row
        sorted_subfolders.extend([''] * padding_needed)
        rows_needed = len(sorted_subfolders) // buttons_per_row

        # 创建一个主容器来控制整体布局
        main_container = ttk.Frame(self.quick_filter_frame, style='Left.TFrame')
        main_container.pack(fill=tk.X, pady=(0, 2))
        
        # 配置主容器的列权重
        for i in range(buttons_per_row):
            main_container.columnconfigure(i, weight=1)

        # 创建按钮网格
        for row in range(rows_needed):
            for col in range(buttons_per_row):
                idx = row * buttons_per_row + col
                subfolder = sorted_subfolders[idx]
                
                if subfolder:  # 只为非空的占位符创建按钮
                    button = ttk.Button(
                        main_container,
                        text=subfolder,
                        command=lambda sf=subfolder: self.filter_by_subfolder(sf),
                        style='primary.TButton',  # 默认使用 primary 样式
                        width=10  # 固定宽度
                    )
                    button.grid(row=row, column=col, padx=2, pady=1, sticky='nswe')
                    self.subfolder_buttons[subfolder] = button
                else:
                    # 创建空白占位框架，保持布局一致
                    placeholder = ttk.Frame(main_container)
                    placeholder.grid(row=row, column=col, padx=2, pady=1, sticky='nswe')

    def filter_by_subfolder(self, subfolder):
        # 先保存当前模型信息
        if self.current_file:
            self.auto_save_changes()
        
        if self.current_subfolder == subfolder:
            # 如果点击当前选中的子文件夹，取消筛选
            self.current_subfolder = None
            self.subfolder_buttons[subfolder].configure(style='primary.TButton')
            # 使用当前排序方式重新加载文件
            self.load_files(self.category_combobox.get(), self.search_var.get(), sort_method=self.current_sort)
        else:
            # 取消之前选中的按钮样式
            if self.current_subfolder and self.current_subfolder in self.subfolder_buttons:
                self.subfolder_buttons[self.current_subfolder].configure(style='primary.TButton')
            
            # 设置新的选中状态
            self.current_subfolder = subfolder
            self.subfolder_buttons[subfolder].configure(style='secondary.TButton')
            
            # 获取当前类别和搜索词
            category = self.category_combobox.get()
            search_term = self.search_var.get()
            
            # 筛选文件
            filtered_files = self.filter_files(category, search_term)
            sorted_files = self.sort_filtered_files(filtered_files, self.current_sort)
            
            # 清除当前显示
            self.clear_file_list()
            
            # 加载文件
            self.load_batch(sorted_files)
            
            # 更新滚动区域
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self.canvas.yview_moveto(0)
            
            # 如果有文件，选择第一个
            if sorted_files:
                first_file = sorted_files[0]
                self.select_file(first_file[0], first_file[1])

        # 更新统计信息
        self.update_stats_label()

    def show_sort_menu(self, event=None):
        # 创建排序菜单
        menu = tk.Menu(self.master, tearoff=0)
        
        # 获取当前排序方式
        current_sort = getattr(self, 'current_sort', 'name_asc')
        
        # 添加排序选项
        menu.add_command(
            label="✓ 按名称升序" if current_sort == 'name_asc' else "按名称升序",
            command=lambda: self.sort_files('name_asc'),
            font=self.base_font
        )
        menu.add_command(
            label="✓ 按名称降序" if current_sort == 'name_desc' else "按名称降序",
            command=lambda: self.sort_files('name_desc'),
            font=self.base_font
        )
        menu.add_separator()
        menu.add_command(
            label="✓ 按文件修改最晚" if current_sort == 'date_desc' else "按文件修改最晚",
            command=lambda: self.sort_files('date_desc'),
            font=self.base_font
        )
        menu.add_command(
            label="✓ 按文件修改最早" if current_sort == 'date_asc' else "按文件修改最早",
            command=lambda: self.sort_files('date_asc'),
            font=self.base_font
        )
        menu.add_command(
            label="✓ 按详情修改最晚" if current_sort == 'info_modified_desc' else "按详情修改最晚",
            command=lambda: self.sort_files('info_modified_desc'),
            font=self.base_font
        )
        menu.add_separator()
        menu.add_command(
            label="✓ 无预览图优先" if current_sort == 'no_preview_first' else "无预览图优先",
            command=lambda: self.sort_files('no_preview_first'),
            font=self.base_font
        )
        menu.add_command(
            label="✓ 无模型网址优先" if current_sort == 'no_url_first' else "无模型网址优先",
            command=lambda: self.sort_files('no_url_first'),
            font=self.base_font
        )
        
        # 在按钮下方显示菜单
        x = self.sort_button.winfo_rootx()
        y = self.sort_button.winfo_rooty() + self.sort_button.winfo_height()
        menu.post(x, y)

    def sort_files(self, sort_method):
        """切换排序方式"""
        try:
            # 设置标记，表示正在进行排序操作
            self._sorting = True
            
            # 先保存当前模型信息
            if self.current_file:
                self.auto_save_changes()
            
            self.current_sort = sort_method
            category = self.category_combobox.get()
            search_term = self.search_var.get()
            
            # 获取并筛选文件
            filtered_files = self.filter_files(category, search_term)
            sorted_files = self.sort_filtered_files(filtered_files, sort_method)
            
            # 清除当前显示
            self.clear_file_list()
            
            # 加载所有文件（不使用批量加载）
            for file, path in sorted_files:
                self.create_file_entry(file, path)
            
            # 更新滚动区域并等待更新完成
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self.canvas.yview_moveto(0)  # 滚动到顶部
            
            # 选择第一个文件
            if sorted_files:
                first_file = sorted_files[0]
                self.select_file(first_file[0], first_file[1])
        
        finally:
            # 移除排序标记
            if hasattr(self, '_sorting'):
                delattr(self, '_sorting')

    def toggle_favorite(self):
        """切换收藏状态"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return

        # 确保收藏图标已加载
        if self.favorite_icon is None:
            try:
                favorite_image = Image.open(get_resource_path('ui/favorite.png'))
                if favorite_image.mode != 'RGBA':
                    favorite_image = favorite_image.convert('RGBA')
                # 调整收藏图标大小为缩略图的1/3
                favorite_icon_size = (self.thumbnail_size[0] // 3, self.thumbnail_size[1] // 3)
                favorite_image = favorite_image.resize(favorite_icon_size, Image.LANCZOS)
                background = Image.new('RGBA', favorite_image.size, (0, 0, 0, 0))
                background.paste(favorite_image, (0, 0), favorite_image)
                self.favorite_icon = ImageTk.PhotoImage(background)
            except Exception as e:
                logging.error(f"Error loading favorite icon: {str(e)}")
                self.favorite_icon = None

        # 读取现有的模型信息
        info_file = 'model_info.json'
        all_info = {}
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
            except Exception as e:
                logging.error(f"Error reading model info: {str(e)}")

        # 获取当前模型的信息
        current_info = all_info.get(self.current_file, {})
        
        # 切换收藏状态
        is_favorite = not current_info.get('is_favorite', False)
        current_info['is_favorite'] = is_favorite
        
        # 更新模型信息
        all_info[self.current_file] = current_info
        
        # 保存到文件
        try:
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(all_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving model info: {str(e)}")
            self.show_popup_message(f"保存收藏状态时发生错误：{str(e)}")
            return

        # 更新内存中的收藏集合
        if is_favorite:
            self.favorites.add(self.current_file)
            self.show_popup_message("已添加收藏")
        else:
            self.favorites.discard(self.current_file)
            self.show_popup_message("已取消收藏")
        
        # 更新按钮文本
        self.update_favorite_button_text()
        
        # 更新当前文件的收藏图标
        if self.current_file in self.file_frames and self.favorite_icon:
            frame, _, _ = self.file_frames[self.current_file]
            # 查找缩略图标签
            for child in frame.winfo_children():
                if isinstance(child, ttk.Frame):  # 找到内容框架
                    for content_child in child.winfo_children():
                        if isinstance(content_child, ttk.Frame):  # 找到左侧容器
                            for label in content_child.winfo_children():
                                if isinstance(label, ttk.Label) and hasattr(label, 'image'):
                                    # 移除现有的收藏图标（如果有）
                                    for widget in label.winfo_children():
                                        if isinstance(widget, tk.Label):
                                            widget.destroy()
                                    
                                    # 如果是收藏状态，添加收藏图标
                                    if is_favorite:
                                        favorite_label = tk.Label(
                                            label,
                                            image=self.favorite_icon,
                                            bg=self.style.colors.bg,
                                            bd=0,
                                            highlightthickness=0
                                        )
                                        favorite_label.place(x=2, y=2)
                                        favorite_label.bind(
                                            "<Button-1>",
                                            lambda e, fn=os.path.basename(self.current_file),
                                            rp=os.path.dirname(self.current_file): self.select_file(fn, rp)
                                        )

    def load_favorites(self):
        """从 model_info.json 中加载收藏信息"""
        favorites = set()
        info_file = 'model_info.json'
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
                    # 遍历所有模型信息，检查是否有藏标记
                    for file_path, info in all_info.items():
                        if info.get('is_favorite', False):
                            favorites.add(file_path)
            except Exception as e:
                logging.error(f"Error loading favorites: {str(e)}")
        return favorites

    def save_favorites(self, favorites):
        with open('favorites.json', 'w', encoding='utf-8') as f:
            json.dump(list(favorites), f, ensure_ascii=False, indent=2)

    def is_favorite(self, file_path):
        return file_path in self.favorites

    def update_favorite_button_text(self):
        if not self.current_file:
            self.favorite_button.configure(text="收藏模型")
            return

        if self.is_favorite(self.current_file):
            self.favorite_button.configure(text="取消收藏")
        else:
            self.favorite_button.configure(text="收藏模型")

    def refresh_current_file_display(self, keep_selection=False, selected_file=None):
        """刷新当前件的显示"""
        # 先保存当前模型信息
        if self.current_file:
            self.auto_save_changes()
        
        if not keep_selection:
            # 重新加载当前类别的文件，保持当前排序和筛
            self.load_files(self.category_combobox.get(), self.search_var.get(), self.current_sort)
        else:
            # 保存当前的滚动位置
            current_scroll = self.canvas.yview()
            
            # 重新加载文件
            self.load_files_without_selection(self.category_combobox.get(), self.search_var.get(), self.current_sort)
            
            # 如果提供了要选中的文件，选中它
            if selected_file and selected_file in self.file_frames:
                file_name = os.path.basename(selected_file)
                relative_path = os.path.dirname(selected_file)
                self.select_file(file_name, relative_path)
                
                # 确保选中的文件可见
                self.ensure_file_visible(selected_file)
            
            # 恢复滚动位置
            self.canvas.yview_moveto(current_scroll[0])

    def load_files_without_selection(self, category, search_term='', sort_method=None):
        """加载文件但不自选择第一个"""
        # 清除现有内容
        self.clear_file_list()

        # 获取并筛选文件
        filtered_files = [
            (file, path) for file, path in self.all_files
            if path.startswith(category) and 
               (search_term.lower() in file.lower() or search_term.lower() in path.lower()) and
               (not self.current_subfolder or 
                (self.current_subfolder == "其他" and path == category) or
                (self.current_subfolder == "收藏" and os.path.join(path, file) in self.favorites) or
                (self.current_subfolder != "其他" and self.current_subfolder != "收藏" and 
                 self.current_subfolder in path.split(os.sep)))
        ]

        # 根据排序方对文件列表行排序
        if sort_method:
            filtered_files = self.sort_filtered_files(filtered_files, sort_method)

        # 加载第一批文件
        self.load_batch(filtered_files)

        # 更新滚动区域
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def schedule_search(self, *args):
        """延迟执行搜索，避免频繁更新"""
        if self.search_after_id:
            self.master.after_cancel(self.search_after_id)
        self.search_after_id = self.master.after(300, self.search_files)

    def search_files(self):
        """执行搜索"""
        search_term = self.search_var.get().lower()
        category = self.category_combobox.get()
        self.current_batch = 0
        self.load_files(category, search_term, self.current_sort)
        
        # 更新统计信息
        self.update_stats_label()

    def _bind_mousewheel(self, event):
        """绑定鼠标滚轮事件"""
        self.canvas.bind_all("<MouseWheel>", self._on_list_mousewheel)

    def _unbind_mousewheel(self, event):
        """解绑鼠标滚轮事"""
        self.canvas.unbind_all("<MouseWheel>")
        self.info_frame.unbind_all("<MouseWheel>")

    def _on_list_mousewheel(self, event):
        """处理列表区域的鼠标滚事件"""
        if self.canvas.yview() != (0.0, 1.0):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif self.canvas.yview()[0] != 0.0 and event.delta > 0:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def load_categories(self):
        """加载所有类别并设置默认选项"""
        # 获取所有文件夹
        all_dirs = [d for d in os.listdir(BASE_PATH) 
                    if os.path.isdir(os.path.join(BASE_PATH, d)) and d not in ['ui']]
        
        # 检查每个文件夹是否包含支持的模型文件
        valid_categories = []
        for directory in all_dirs:
            dir_path = os.path.join(BASE_PATH, directory)
            has_models = self.check_directory_for_models(dir_path)
            if has_models:
                valid_categories.append(directory)
        
        # 设置类别列表
        self.categories = []
        
        # 按照指定顺序添加 checkpoints 和 loras（如果它们包含有效模型）
        if "checkpoints" in valid_categories:
            self.categories.append("checkpoints")
            valid_categories.remove("checkpoints")
        if "loras" in valid_categories:
            self.categories.append("loras")
            valid_categories.remove("loras")
        
        # 添加其他有效类别
        self.categories.extend(sorted(valid_categories))
        
        # 设置下拉框的选项
        self.category_combobox['values'] = self.categories
        
        # 预加载所有文件信息
        self.load_all_files()

    def check_directory_for_models(self, directory_path):
        """
        检查目录及其子目录是否包含支持的模型文件
        Args:
            directory_path: 要检查的目录路径
        Returns:
            bool: 如果找到支持的模型文件返回True，否则返回False
        """
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith(self.supported_model_extensions):
                    return True
        return False

    def load_all_files(self):
        """异步加载所有文件"""
        if self.loading_thread and self.loading_thread.is_alive():
            self.loading_cancelled = True
            self.loading_thread.join()
        
        self.loading_cancelled = False
        # 确保清空文件列表
        self.all_files = []
        
        def load_files_thread():
            with self.loading_lock:
                try:
                    temp_files = []  # 使用临时列表存储文件
                    for category in self.categories:
                        if self.loading_cancelled:
                            return
                            
                        category_path = os.path.join(BASE_PATH, category)
                        self.recursive_load_all_files_to_list(category_path, category, temp_files)
                    
                    # 加载完成后，一次性更新 all_files，并应用默认排序
                    if not self.loading_cancelled:
                        self.all_files = list(set(temp_files))  # 使用 set 去重
                        # 应用默认排序
                        self.all_files = self.sort_filtered_files(self.all_files, self.current_sort)
                        # 加载完成后在主线程中更新UI
                        self.master.after(0, self.on_files_loaded)
                except Exception as e:
                    logging.error(f"Error in load_files_thread: {str(e)}")
        
        self.loading_thread = threading.Thread(target=load_files_thread)
        self.loading_thread.daemon = True
        self.loading_thread.start()

    def recursive_load_all_files_to_list(self, path, relative_path, file_list):
        """递归加载文件到指定列表（使用缓存）"""
        try:
            items = self.fs_cache.get_dir_content(path)
            for item in items:
                if self.loading_cancelled:
                    return
                        
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    self.recursive_load_all_files_to_list(
                        item_path, 
                        os.path.join(relative_path, item),
                        file_list
                    )
                elif item.endswith(self.supported_model_extensions):
                    file_list.append((item, relative_path))
        except Exception as e:
            logging.error(f"Error loading files from {path}: {str(e)}")

    def on_files_loaded(self):
        """文件加载完成后的处理"""
        # 刷新当前显示，使用当前排序方式
        if hasattr(self, 'category_combobox'):
            category = self.category_combobox.get()
            self.load_files(category, self.search_var.get(), self.current_sort)

    def add_favorite_field_to_model_info(self):
        """为所有模型信息添加收藏字段"""
        info_file = 'model_info.json'
        if os.path.exists(info_file):
            try:
                # 读取现有的模型信息
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
                
                # 为每个模型添加 is_favorite 字段（如果不存在）
                modified = False
                for model_path in all_info:
                    if 'is_favorite' not in all_info[model_path]:
                        all_info[model_path]['is_favorite'] = False
                        modified = True
                
                # 如果有修改，保存更新后的信息
                if modified:
                    with open(info_file, 'w', encoding='utf-8') as f:
                        json.dump(all_info, f, ensure_ascii=False, indent=2)
                    logging.info("Added is_favorite field to model info")
            except Exception as e:
                logging.error(f"Error adding favorite field to model info: {str(e)}")

    def setup_help_frame(self):
        """创建帮助界面"""
        help_text = tk.Text(
            self.help_frame, 
            wrap=tk.WORD, 
            padx=20, 
            pady=20,
            font=self.base_font  # 设置帮助文本的字体
        )
        scrollbar = ttk.Scrollbar(self.help_frame, command=help_text.yview)
        help_text.configure(yscrollcommand=scrollbar.set)
        
        help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        help_content = f"""月光AI宝盒-模型管理器 v{VERSION} 使用说明

【界面布局】
1. 左侧：功能区、公告栏、快捷入口
2. 中间：模型列表区域（显示总数和大小统计）
3. 右侧：预览图和模型信息区域

【基本功能】
1. 模型浏览
   - 选择类别：选择要查看的模型类别（如 checkpoints、loras）
   - 快速筛选：点击文件夹名可以筛选该文件夹下的模型（没有模型文件的文件夹不会显示）
   - 搜索功能：支持搜索文件名、路径、模型类型
   - 排序方式：支持多种排序方式，如名称、修改时间等
   - 快捷键：上下方向键快速切换模型，Ctrl+F 聚焦到搜索框
   - 快捷键：Home回到顶部，End回到底部
   - 快捷键：PageUp向上翻页，PageDown向下翻页
   - 右键选单：右键点击模型支持多种操作模型的选单

2. 模型信息管理
   - 自动保存：编辑模型信息后会自动保存
   - 快捷键：Ctrl+Z 撤销所选输入框的修改
   - 快捷键：Ctrl+S 手动保存模型信息
   - 描述编辑：点击"详情"按钮可在大窗口中编辑描述
   - 收藏功能：点击"收藏模型"可收藏/取消收藏
   - 移动功能：可以移动模型及相关所有配置文件到其他文件夹，并保留详情信息和收藏状态
   - 复制功能：可以复制模型及相关所有配置文件到其他文件夹，并保留详情信息
   - 删除功能：可以删除模型及相关所有配置

3. 预览图管理
   - 更换方式：
     * 拖拽图片到预览区
     * 复制图片后按 Ctrl+V
     * 右键选单"换预览图"选择本地图片
   - 自动获取：通过 Civitai/Liblib 抓取功能自动获取预览图
   - 点击预览图可以放大查看全尺寸图片

4. 信息抓取
   - Civitai 抓取：
     * 自动获取预览图和模型信息
     * 需要先计算模型哈希值
     * 支持单个抓取和批量抓取
   - Liblib 抓取：
     * 自动获取模型描述和预览图
     * 需要先填写模型网址
     * 支持单个抓取和批量抓取

5. 批量处理（一键脚本）
   - 一键计算哈希值：为所有模型计算哈希值
   - 一键适配CS：批量创建CS配置文件，生成后可在ComfyUI，pysss节点直接查看模型信息（预览图、描述、触发词）
   - 一键适配SD：批量创建SD配置文件，生成后可在SD WebUI模型管理界面同步显示模型信息（预览图、描述、触发词）
   - 一键从Liblib抓取：批量抓取Liblib信息
   - 一键从Civitai抓取：批量抓取Civitai信息

6. 模型映射（支持三种方式）
   - ComfyUI：配置 extra_model_paths.yaml，实现外部模型文件在ComfyUI中读取
   - SD WebUI：配置 webui-user.bat，实现外部模型文件在SD WebUI中读取

【使用建议】
1. 软件可以直接放在ComfyUI的models文件夹下使用（无需映射），也可以在外部按照ComfyUI的models文件目录结构新建文件夹，将软件放入其中使用（需要映射）
2. 定期点击"刷新"按钮更新文件列表
3. 定期备份 model_info.json 文件
4. 避免使用中文路径
5. 建议将模型放在固态硬盘上

【联系方式】
- 问题反馈：https://odopqev8le.feishu.cn/share/base/form/shrcnXRZoJWjH3Ab8jV4CExIPze
- QQ群：565977956
- 邮箱：wrl1214@126.com
- B站：黑米饭吃了么

【长期下载更新地址】
https://pan.quark.cn/s/75450b122a53"""


        help_text.insert('1.0', help_content)
        help_text.configure(state='disabled')  # 设为只读

    def show_help(self):
        """显示帮助界面"""
        self.model_management_frame.pack_forget()
        self.model_mapping_frame.pack_forget()
        self.help_frame.pack(fill=tk.BOTH, expand=True)
        
        self.help_btn.configure(style='secondary.TButton')
        self.model_management_btn.configure(style='primary.TButton')
        self.model_mapping_btn.configure(style='primary.TButton')

    def on_sash_drag(self, event):
        """分隔栏拖拽过程中的处理"""
        # 暂时隐藏预览图和动内容
        if hasattr(self, 'preview_container'):
            self.preview_container.pack_forget()
        if hasattr(self, 'scrollable_frame'):
            self.scrollable_frame.pack_forget()
        if hasattr(self, 'info_frame'):
            self.info_frame.pack_forget()

    def on_sash_release(self, event):
        """分隔拖结束后处理"""
        # 恢复预览图和滚动内容的显示
        if hasattr(self, 'preview_container'):
            self.preview_container.pack(pady=0, padx=0)
        if hasattr(self, 'canvas'):
            self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        if hasattr(self, 'info_frame'):
            self.canvas_frame = self.info_frame.create_window((0, 0), window=self.info_frame, anchor="nw")
        
        # 更新布局
        self.update_content_layout()

    def on_window_configure(self, event):
        """窗口大小改变时延迟更内容"""
        if event.widget == self.master:
            # 取之前的定时器
            if self.resize_timer:
                self.master.after_cancel(self.resize_timer)
            # 设置新的定时器
            self.resize_timer = self.master.after(100, self.update_content_layout)

    def update_content_layout(self):
        """更新内容布局"""
        # 更新预览图大小
        if hasattr(self, 'preview_container'):
            self.center_preview_image()
        
        # 更新滚动区域
        if hasattr(self, 'canvas'):
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 更新信息区域
        if hasattr(self, 'info_frame'):
            self.update_scrollregion()

    def change_preview_image(self):
        """更换预览图"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
    
        # 直接打开文件选择对话框
        file_types = [
            ('图片文件', '*' + ';*'.join(self.supported_image_extensions)),  # 使用全局支持的图片格式
            ('所有文件', '*.*')
        ]
    
        file_path = filedialog.askopenfilename(
            title="选择预览图",
            filetypes=file_types
        )
    
        if file_path:
            self.replace_preview_image(file_path)

    def on_info_canvas_configure(self, event):
        """当信息区域画布大小改变时调整内容"""
        # 调整内容框架宽度以适应画布
        self.info_frame.itemconfig(
            self.canvas_frame,
            width=event.width
        )

    def calculate_file_hash(self, file_path):
        """计算文件的哈希值"""
        try:
            import hashlib
            # 使用 SHA-256 算法
            sha256_hash = hashlib.sha256()
            
            # 以二进制模式读取文件
            with open(file_path, "rb") as f:
                # 分块读取文件以处理大文件
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            # 返回十六进制格式的哈希值
            return sha256_hash.hexdigest()
        except Exception as e:
            logging.error(f"计算哈希值时发生错误：{str(e)}")
            return "无法计算哈希值"

    def copy_model_hash(self):
        """复制模型哈希值"""
        hash_value = self.model_hash.get()
        if hash_value:
            self.master.clipboard_clear()
            self.master.clipboard_append(hash_value)
            self.show_popup_message("哈希值已复制")
        else:
            self.show_popup_message("哈希值为空")

    def show_hash_dialog(self):
        """显示哈希值计算对话框"""
        dialog = tk.Toplevel(self.master)
        dialog.title("计算模型哈希值")
        dialog.geometry("400x150")
        dialog.transient(self.master)
        dialog.grab_set()
        
        # 居中显示
        dialog.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 200}+"
                       f"{self.master.winfo_y() + self.master.winfo_height()//2 - 75}")
        
        # 创建主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            main_frame,
            variable=progress_var,
            maximum=100,
            mode='determinate',
            style='primary.Horizontal.TProgressbar'
        )
        progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # 创建状态标签
        status_label = ttk.Label(main_frame, text="可能需要较长的时间，和模型数量以及磁盘性能有关")
        status_label.pack(fill=tk.X, pady=(0, 10))
        
        # 创建按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 取消标志
        cancel_flag = {'value': False}
        
        def calculate_hashes():
            try:
                # 获取所有模型文件
                all_files = [(f, p) for f, p in self.all_files]
                total = len(all_files)
                
                # 读取现有的模型信息
                info_file = 'model_info.json'
                if os.path.exists(info_file):
                    with open(info_file, 'r', encoding='utf-8') as f:
                        all_info = json.load(f)
                else:
                    all_info = {}
                
                # 计算每个文件的进度比例
                progress_step = 100.0 / total if total > 0 else 0
                
                # 遍历所有文件计算哈希值
                for i, (file, path) in enumerate(all_files):
                    if cancel_flag['value']:
                        break
                    
                    full_path = os.path.join(BASE_PATH, path, file)
                    model_path = os.path.join(path, file)
                    
                    # 检查是否已有有效的哈希值
                    if model_path in all_info and 'hash' in all_info[model_path]:
                        existing_hash = all_info[model_path]['hash']
                        if existing_hash and len(existing_hash) == 64:  # SHA-256 哈希值长度为64
                            logging.info(f"跳过已有哈希值的模型: {model_path}")
                            status_label.config(text=f"跳过: {file} (已有哈希值)")
                            progress_var.set((i + 1) * progress_step)
                            dialog.update()
                            continue
                    
                    status_label.config(text=f"正在计算: {file}")
                    
                    # 计算哈希值
                    hash_value = self.calculate_file_hash(full_path)
                    
                    # 更新模型信息
                    if model_path not in all_info:
                        all_info[model_path] = {}
                    all_info[model_path]['hash'] = hash_value
                    
                    # 更新进度
                    progress_var.set((i + 1) * progress_step)
                    dialog.update()
                
                # 保存更新后的信息
                if not cancel_flag['value']:
                    with open(info_file, 'w', encoding='utf-8') as f:
                        json.dump(all_info, f, ensure_ascii=False, indent=2)
                    
                    # 如果当前有选中的文件，刷新显示
                    if self.current_file:
                        self.load_model_info()
                    
                    status_label.config(text="计算完成！")
                    self.show_popup_message("哈希值计算完成")
                else:
                    status_label.config(text="已取消计算")
                
            except Exception as e:
                status_label.config(text=f"发生错误：{str(e)}")
                messagebox.showerror("错误", f"计算哈希值时发生错误：{str(e)}")
            finally:
                start_btn.configure(state='normal')
        
        def start_calculation():
            cancel_flag['value'] = False
            start_btn.configure(state='disabled')
            progress_var.set(0)
            threading.Thread(target=calculate_hashes, daemon=True).start()
        
        
        # 建开始和取消按钮
        start_btn = ttk.Button(
            button_frame,
            text="开始计算",
            command=start_calculation,
            width=10,
            style='primary.TButton'  # 使用统一的按钮样式
        )
        start_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = ttk.Button(
            button_frame,
            text="关闭",
            command=dialog.destroy,
            width=10,
            style='primary.TButton'  # 使用统一的按钮样式
        )
        close_btn.pack(side=tk.RIGHT, padx=5)

    def handle_save_shortcut(self, event=None):
        """处理 Ctrl+S 快捷键"""
        # 检查窗口是否处于激活状态
        if self.master.focus_displayof() is not None:
            # 执行保存操作
            self.save_changes()
        return "break"  # 阻止事件继续传播

    def update_announcement_colors(self, event=None):
        """更新公告栏颜色以匹配当前主题"""
        self.announcement_text.configure(
            bg=self.style.colors.bg,
            fg=self.style.colors.fg,
            insertbackground=self.style.colors.fg  # 光标颜色
        )

    def search_on_liblib(self):
        """在 Liblib 搜索当前模型"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
        
        try:
            # 获取模型名称
            model_name = os.path.splitext(os.path.basename(self.current_file))[0]
            # 使用正则表达式去掉"_v数字"、"_v数字.数字"或"_数字.数字"部分
            import re
            model_name = re.sub(r'(_v\d+(\.\d+)?|_\d+(\.\d+)?)', '', model_name, flags=re.IGNORECASE)
            # 构建搜索URL（使用正确的搜索参数格式）
            search_url = f"https://www.liblib.art/search?keyword={urllib.parse.quote(model_name)}"
            # 在默认浏览器中打开
            webbrowser.open(search_url)
        except Exception as e:
            self.show_popup_message(f"打开搜索页面失败：{str(e)}")


    def fetch_from_liblib(self):
        """从Liblib抓取模型信息"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
        
        # 获取当前模型的网址
        url = self.model_url.get("1.0", tk.END).strip()
        if not url:
            self.show_popup_message("模型网址为空，请先填写模型网址")
            return
        
        if not url.startswith("https://www.liblib.art/"):
            self.show_popup_message("请输入正确的Liblib模型页面网址")
            return
        
        # 创建进度提示框
        progress_window = tk.Toplevel(self.master)
        progress_window.title("Liblib抓取")
        progress_window.geometry("400x150")
        progress_window.transient(self.master)
        progress_window.grab_set()
        
        # 居中显示
        progress_window.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 200}+"
                           f"{self.master.winfo_y() + self.master.winfo_height()//2 - 75}")
        
        # 创建主框架
        main_frame = ttk.Frame(progress_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建状态标签
        status_label = ttk.Label(main_frame, text="正在准备抓取...", wraplength=380)
        status_label.pack(pady=(0, 10))
        
        # 创建进度条
        progress_bar = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            style='primary.Horizontal.TProgressbar'
        )
        progress_bar.pack(fill=tk.X, pady=(0, 10))
        progress_bar.start(10)
        
        def update_status(text):
            status_label.config(text=text)
            progress_window.update()

        def get_browser_path():
            """获取 Firefox 浏览器路径"""
            try:
                if getattr(sys, 'frozen', False):
                    # 打包环境
                    base_dir = sys._MEIPASS
                    firefox_path = os.path.join(base_dir, 'firefox', 'firefox', 'firefox.exe')  # 注意这里添加了两次 firefox
                    if os.path.exists(firefox_path):
                        print(f"使用打包的Firefox: {firefox_path}")
                        return firefox_path
                
                # 开发环境
                return None
            except Exception as e:
                logging.error(f"获取浏览器路径失败：{str(e)}")
            return None     
        
        try:
            update_status("正在从Liblib获取模型信息...")
            
            with sync_playwright() as p:
                browser = None
                browser_path = get_browser_path()
                print(f"浏览器路径: {browser_path}")
                try:
                    # 启动浏览器时显式指定可执行文件路径
                    browser = p.firefox.launch(
                        headless=True,
                        executable_path = browser_path # 指定浏览器路径
                    )
                    page = browser.new_page()
                    
                    # 访问页面
                    page.goto(url)
                    
                    # 标记是否有任何内容被抓取
                    content_found = False
                    
                    # 尝试获取预览图
                    try:
                        update_status("正在获取预览图...")
                        if page.wait_for_selector(".ModelVersion_modelVersion__4cm1k .relative.cursor-pointer img", timeout=3000):
                            img_element = page.query_selector(".ModelVersion_modelVersion__4cm1k .relative.cursor-pointer img")
                            if img_element:
                                img_url = img_element.get_attribute("src")
                                if img_url:
                                    # 检查是否已有预览图
                                    file_name = os.path.basename(self.current_file)
                                    relative_path = os.path.dirname(self.current_file)
                                    has_preview = self.get_image_path(file_name, relative_path) is not None
                                    
                                    # 如果已有预览图，询问是否替换
                                    replace_preview = True
                                    if has_preview:
                                        progress_window.withdraw()  # 暂时隐藏进度窗口
                                        replace_preview = messagebox.askyesno("确认", "当前模型已有预览图，是否需要替换？")
                                        progress_window.deiconify()  # 重新显示进度窗口
                                    
                                    if replace_preview:
                                        headers = {
                                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                                        }
                                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                                            img_response = requests.get(img_url, headers=headers)
                                            if img_response.status_code == 200:
                                                temp_file.write(img_response.content)
                                                self.replace_preview_image(temp_file.name)
                                                content_found = True
                    except Exception as e:
                        print(f"获取预览图失败：{str(e)}")
                    
                    # 尝试获取触发词
                    try:
                        update_status("正在获取触发词...")
                        self.trigger_words.delete("1.0", tk.END)  # 先清空触发词
                        if page.wait_for_selector(".ModelDetailCard_triggerTxt__cKZOL", timeout=1000):
                            trigger_elements = page.query_selector_all(".ModelDetailCard_triggerTxt__cKZOL")
                            if trigger_elements:
                                trigger_words = [element.inner_text() for element in trigger_elements]
                                if trigger_words:
                                    self.trigger_words.insert("1.0", ", ".join(trigger_words))
                                    content_found = True
                    except Exception as e:
                        print(f"获取触发词失败：{str(e)}")
                    
                    # 尝试获取描述
                    try:
                        update_status("正在获取模型描述...")
                        if page.wait_for_selector('.ModelDescription_desc__EoTMz', timeout=1000):
                            description_container = page.query_selector('.ModelDescription_desc__EoTMz')
                            if description_container:
                                # 获取所有文本节点，包括嵌套的
                                description_lines = []
                                
                                # 使用 evaluate 在浏览器中执行 JavaScript 来获取所有文本内容
                                script = """
                                (element) => {
                                    const texts = [];
                                    const walk = (node) => {
                                        if (node.nodeType === 3 && node.textContent.trim()) {  // 文本节点
                                            texts.push(node.textContent.trim());
                                        } else if (node.nodeType === 1) {  // 元素节点
                                            if (node.tagName === 'BR') {
                                                texts.push('');
                                            }
                                            for (const child of node.childNodes) {
                                                walk(child);
                                            }
                                            if (['P', 'DIV', 'LI'].includes(node.tagName)) {
                                                texts.push('');
                                            }
                                        }
                                    };
                                    walk(element);
                                    return texts.filter(text => text !== '');
                                }
                                """
                                description_lines = description_container.evaluate(script)
                                
                                if description_lines:
                                    # 将抓取的内容添加到模型描述中
                                    current_desc = self.model_desc.get("1.0", tk.END).strip()
                                    liblib_marker = "=== 从Liblib抓取的描述 ==="
                                    civitai_marker = "=== 从Civitai抓取的描述 ==="
                                    
                                    if current_desc=="":
                                        new_desc = liblib_marker + "\n" + "\n\n".join(description_lines)
                                    else:
                                        # 分割现有描述
                                        parts = current_desc.split(liblib_marker)
                                        if len(parts) > 1:
                                            # 已存在Liblib描述，更新它
                                            user_desc = parts[0].strip()
                                            if user_desc=="":
                                                new_desc = liblib_marker + "\n" + "\n\n".join(description_lines)
                                            else:
                                                new_desc = user_desc + "\n\n" + liblib_marker + "\n" + "\n\n".join(description_lines)
                                        else:
                                            # 检查是否存在Civitai描述
                                            parts = current_desc.split(civitai_marker)
                                            if len(parts) > 1:
                                                # 存在Civitai描述，在其后添加Liblib描述
                                                user_desc = parts[0].strip()
                                                new_desc = user_desc + "\n\n" + civitai_marker + parts[1] + "\n\n" + liblib_marker  +"\n" +  "\n\n".join(description_lines)
                                            else:
                                                # 没有任何抓取的描述，直接添加
                                                if current_desc=="":
                                                    new_desc = liblib_marker +"\n" +  "\n\n".join(description_lines)
                                                else:   
                                                    new_desc = current_desc + "\n\n" + liblib_marker +"\n" +  "\n\n".join(description_lines)
                                        
                                    self.model_desc.delete("1.0", tk.END)
                                    self.model_desc.insert("1.0", new_desc)
                                    content_found = True
                    except Exception as e:
                        print(f"获取描述失败：{str(e)}")
                    
                    # 检查是否有任何内容被抓取
                    if not content_found:
                        update_status("未找到任何模型信息...")
                        progress_window.after(1000, progress_window.destroy)
                        self.show_popup_message("在Liblib上未找到此模型的任何信息")
                        return
                    
                    # 自动保存更改
                    self.auto_save_changes()
                    
                    # 显示成功消息
                    progress_window.destroy()
                    self.show_popup_message("信息抓取成功")
                    
                except Exception as e:                    
                    if "TimeoutError" in str(e):
                        update_status("等待页面加载超时...")
                        progress_window.after(1000, progress_window.destroy)
                        self.show_popup_message("页面加载超时，请检查网络连接或稍后重试")
                    else:
                        raise e
                finally:
                    browser.close()
                    
        except Exception as e:
            progress_window.destroy()
            self.show_popup_message(f"抓取信息时发生错误：{str(e)}")
            print(f"抓取信息时发生错误：{str(e)}")
        finally:
            progress_window.destroy()

    def fetch_from_civitai(self):
        """从Civitai抓取模型信息"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
        
        # 创建进度提示框
        progress_window = tk.Toplevel(self.master)
        progress_window.title("从Civitai抓取")
        progress_window.geometry("400x150")
        progress_window.transient(self.master)
        progress_window.grab_set()
        
        # 居中显示
        progress_window.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 200}+"
                           f"{self.master.winfo_y() + self.master.winfo_height()//2 - 75}")
        
        # 创建主框架
        main_frame = ttk.Frame(progress_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建状态标签
        status_label = ttk.Label(main_frame, text="正在准备抓取...", wraplength=380)
        status_label.pack(pady=(0, 10))
        
        # 创建进度条
        progress_bar = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            style='primary.Horizontal.TProgressbar'
        )
        progress_bar.pack(fill=tk.X, pady=(0, 10))
        progress_bar.start(10)
        
        def update_status(text):
            status_label.config(text=text)
            progress_window.update()
        
        try:
            # 检查预览图
            file_name = os.path.basename(self.current_file)
            relative_path = os.path.dirname(self.current_file)
            has_preview = self.get_image_path(file_name, relative_path) is not None
            
            # 如果已有预览图，询问是否替换
            replace_preview = True
            if has_preview:
                progress_window.withdraw()  # 暂时隐藏进度窗口
                replace_preview = messagebox.askyesno("确认", "当前模型已有预览图，是否需要替换？")
                progress_window.deiconify()  # 重新显示进度窗口
            
            # 获取哈希值
            update_status("正在获取模型哈希值...")
            hash_value = self.model_hash.get()
            if not hash_value:
                full_path = os.path.join(BASE_PATH, self.current_file)
                file_size = os.path.getsize(full_path)
                
                # 使用 SHA-256 算法
                sha256_hash = hashlib.sha256()
                
                # 已读取的字节数
                bytes_read = 0
                last_update_time = time.time()
                update_interval = 0.1  # 每0.1秒更新一次界面
                
                # 以二进制模式读取文件
                with open(full_path, "rb") as f:
                    while True:
                        # 读取数据块
                        chunk = f.read(8192)
                        if not chunk:
                            break
                            
                        sha256_hash.update(chunk)
                        bytes_read += len(chunk)
                        
                        # 更新进度
                        current_time = time.time()
                        if current_time - last_update_time >= update_interval:
                            progress = (bytes_read / file_size) * 100
                            update_status(f"正在计算哈希值... {progress:.1f}%")
                            last_update_time = current_time
                
                hash_value = sha256_hash.hexdigest()
                if not hash_value:
                    raise Exception("无法计算模型哈希值")
                
                self.model_hash.configure(state='normal')
                self.model_hash.delete(0, tk.END)
                self.model_hash.insert(0, hash_value)
                self.model_hash.configure(state='readonly')
            
            # 使用API获取信息
            update_status("正在从Civitai获取模型信息...")
            api_url = f"https://civitai.com/api/v1/model-versions/by-hash/{hash_value}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            try:
                response = requests.get(api_url, headers=headers, timeout=30)  # 添加超时设置
                
                if response.status_code == 404:
                    update_status("未找到模型信息...")
                    progress_window.after(1000, progress_window.destroy)  # 延迟关闭窗口
                    self.show_popup_message("在Civitai上未找到此模型")
                    return
                    
                elif response.status_code == 200:
                    data = response.json()
                    if not data or not isinstance(data, dict):
                        update_status("未找到模型信息...")
                        progress_window.after(1000, progress_window.destroy)  # 延迟关闭窗口
                        self.show_popup_message("在Civitai上未找到此模型")
                        return
                    
                    # 获取模型URL
                    model_id = data.get('modelId')
                    version_id = data.get('id')
                    if not model_id or not version_id:
                        update_status("未找到模型信息...")
                        progress_window.after(1000, progress_window.destroy)  # 延迟关闭窗口
                        self.show_popup_message("在Civitai上未找到此模型")
                        return
                    
                    model_url = f"https://civitai.com/models/{model_id}?modelVersionId={version_id}"
                    self.model_url.delete("1.0", tk.END)
                    self.model_url.insert("1.0", model_url)
                    
                    update_status("正在获取预览图和模型信息...")
                    # 如果用户同意替换预览图，且有可用的预览图
                    if replace_preview and 'images' in data and len(data['images']) > 0:
                        image_url = data['images'][0].get('url')
                        if image_url:
                            # 下载并设置预览图
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                                img_response = requests.get(image_url, headers=headers)
                                temp_file.write(img_response.content)
                                self.replace_preview_image(temp_file.name)
                
                    # 获取触发词
                    if 'trainedWords' in data:
                        trigger_words = ", ".join(data['trainedWords'])
                        self.trigger_words.delete("1.0", tk.END)
                        self.trigger_words.insert("1.0", trigger_words)
                    
                    update_status("正在获取模型描述...")
                    # 使用 json-ld 获取描述
                    try:
                        # 发送请求获取页面内容
                        page_response = requests.get(model_url, headers=headers, timeout=30)
                        if page_response.status_code == 200:
                            soup = BeautifulSoup(page_response.text, 'html.parser')
                            
                            # 查找 json-ld 脚本
                            json_script = soup.find('script', type='application/ld+json')
                            if json_script:
                                json_data = json.loads(json_script.string)
                                description = json_data.get('description', '')
                                if description:
                                    # 解析HTML并保持原始格式
                                    desc_soup = BeautifulSoup(description, 'html.parser')
                                    
                                    # 获取所有文本，保持段落结构
                                    description_lines = []
                                    for element in desc_soup.descendants:
                                        if isinstance(element, NavigableString):
                                            text = element.strip()
                                            if text:
                                                description_lines.append(text)
                                        elif element.name in ['p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                            description_lines.append('')  # 添加空行作为段落分隔
                                    
                                    # 清理连续的空行
                                    clean_description = []
                                    prev_empty = False
                                    for line in description_lines:
                                        if line:
                                            clean_description.append(line)
                                            prev_empty = False
                                        elif not prev_empty:
                                            clean_description.append(line)
                                            prev_empty = True
                                    
                                    # 合并文本
                                    formatted_description = '\n'.join(clean_description).strip()
                                    
                                    if formatted_description:
                                        # 将抓取的内容添加到模型描述中
                                        current_desc = self.model_desc.get("1.0", tk.END).strip()
                                        civitai_marker = "=== 从Civitai抓取的描述 ==="
                                        liblib_marker = "=== 从Liblib抓取的描述 ==="
                                        
                                        if current_desc=="":
                                            new_desc = civitai_marker + "\n" + formatted_description
                                        else:
                                            # 分割现有描述
                                            parts = current_desc.split(civitai_marker)
                                            if len(parts) > 1:
                                                # 已存在Civitai描述，更新它
                                                user_desc = parts[0].strip()
                                                if user_desc=="":
                                                    new_desc = civitai_marker + "\n" + formatted_description
                                                else:   
                                                    new_desc = user_desc + "\n\n" + civitai_marker + "\n" + formatted_description
                                            else:
                                                # 检查是否存在Liblib描述
                                                parts = current_desc.split(liblib_marker)
                                                if len(parts) > 1:
                                                    # 存在Liblib描述，在其后添加Civitai描述
                                                    user_desc = parts[0].strip()
                                                    new_desc = user_desc + "\n\n" + liblib_marker + parts[1] + "\n\n" + civitai_marker + "\n" + formatted_description
                                                else:
                                                    # 没有任何抓取的描述，直接添加
                                                    if current_desc=="":
                                                        new_desc = civitai_marker + "\n" + formatted_description
                                                    else:
                                                        new_desc = current_desc + "\n\n" + civitai_marker + "\n" + formatted_description
                                        
                                        self.model_desc.delete("1.0", tk.END)
                                        self.model_desc.insert("1.0", new_desc)
                    except Exception as e:
                        print(f"获取描述失败：{str(e)}")
                    
                    # 自动保存更改
                    self.auto_save_changes()
                    
                    progress_window.destroy()
                    self.show_popup_message("信息抓取成功")
                else:
                    update_status(f"请求失败: {response.status_code}")
                    progress_window.after(1000, progress_window.destroy)  # 延迟关闭窗口
                    self.show_popup_message(f"API请求失败：{response.status_code}")
                    return
                
            except requests.exceptions.Timeout:
                update_status("请求超时...")
                progress_window.after(1000, progress_window.destroy)  # 延迟关闭窗口
                self.show_popup_message("请求超时，请检查网络连接")
                return
            except requests.exceptions.RequestException as e:
                update_status("网络请求失败...")
                progress_window.after(1000, progress_window.destroy)  # 延迟关闭窗口
                self.show_popup_message(f"网络请求失败：{str(e)}")
                return
            
        except Exception as e:
            update_status("发生错误...")
            progress_window.after(1000, progress_window.destroy)  # 延迟关闭窗口
            self.show_popup_message(f"抓取信息时发生错误：{str(e)}")
            return

    def move_model(self):
        """移动模型及其相关文件"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
        
        # 获取当前模型所在目录作为初始目录
        current_path = os.path.join(BASE_PATH, self.current_file)
        current_dir = os.path.dirname(current_path)
        
        # 获取目标路径,并使用当前目录作为初始目录
        target_dir = filedialog.askdirectory(title="选择要移动到的文件夹", initialdir=current_dir)
        if not target_dir:
            return
        
        try:
            # 检查目标路径是否在程序路径内的子目录
            try:
                relative_path = os.path.relpath(target_dir, BASE_PATH)
                # 检查是否为程序路径下的子目录
                is_sub_directory = not (relative_path == '.' or relative_path.startswith('..'))
            except ValueError:  # 在不同驱动器的情况
                is_sub_directory = False
            
            # 获取当前模型文件的路径信息
            model_dir = os.path.dirname(current_path)
            model_name = os.path.basename(current_path)
            model_basename = os.path.splitext(model_name)[0]
            
            # 确认是否要移动，并提示是否会更新JSON
            confirm_message = f"是否要将模型 {model_name} 及相关文件移动到:\n{target_dir}"
            if not is_sub_directory:
                confirm_message += "\n\n注意：移动到此位置将不会更新模型信息"
            
            if not messagebox.askyesno("确认", confirm_message):
                return
            # 检查并移动同名json文件
            json_path = os.path.join(model_dir, f"{model_basename}.json")
            new_json_path = os.path.join(target_dir, f"{model_basename}.json")
            
            # 移动模型文件
            new_model_path = os.path.join(target_dir, model_name)
            shutil.move(current_path, new_model_path)
            
            # 如果存在json文件，也移动它
            if os.path.exists(json_path):
                shutil.move(json_path, new_json_path)
            
            # 移动预览图（如果存在）
            for ext in self.supported_image_extensions:
                preview_name = model_basename + ext
                preview_path = os.path.join(model_dir, preview_name)
                if os.path.exists(preview_path):
                    new_preview_path = os.path.join(target_dir, preview_name)
                    shutil.move(preview_path, new_preview_path)
                    break
            
            # 移动适配CS生成的配置文件夹（如果存在）
            cs_folder = os.path.join(model_dir, model_basename)
            if os.path.exists(cs_folder) and os.path.isdir(cs_folder):
                new_cs_folder = os.path.join(target_dir, model_basename)
                shutil.move(cs_folder, new_cs_folder)
            
            # 只有当移动到程序路径下的子目录时才更新 json
            if is_sub_directory:
                info_file = 'model_info.json'
                if os.path.exists(info_file):
                    with open(info_file, 'r', encoding='utf-8') as f:
                        all_info = json.load(f)
                    
                    # 获取当前模型的相对路径
                    old_relative_path = self.current_file
                    
                    # 计算新的相对路径
                    new_relative_path = os.path.relpath(new_model_path, BASE_PATH)
                    
                    # 如果有模型信息，更新路径
                    if old_relative_path in all_info:
                        # 保存模型信息，包括收藏状态
                        model_info = all_info.pop(old_relative_path)
                        all_info[new_relative_path] = model_info
                        
                        # 更新收藏集合
                        if model_info.get('is_favorite', False):
                            self.favorites.remove(old_relative_path)
                            self.favorites.add(new_relative_path)
                        
                        # 保存更新后的信息
                        with open(info_file, 'w', encoding='utf-8') as f:
                            json.dump(all_info, f, ensure_ascii=False, indent=2)
            
            # 刷新文件列表
            self.refresh_files()
            
            # 根据是否更新了json给出不同的提示
            if is_sub_directory:
                self.show_popup_message("模型移动成功，并已更新信息")
            else:
                self.show_popup_message("模型移动成功，但未更新信息（目标路径不在程序目录下）")
            
        except Exception as e:
            self.show_popup_message(f"移动模型时发生错误：{str(e)}")

    def on_canvas_configure(self, event):
        """处理画布大小变化"""
        # 更新画布窗口的宽度以匹配画布宽度
        width = event.width - 4  # 减去一些边距
        self.canvas.itemconfig(
            self.canvas_window,
            width=width
        )
        
        # 设置scrollable_frame的最小宽度
        self.scrollable_frame.configure(width=width)
        
        # 强制更新所有子组件
        self.scrollable_frame.update_idletasks()
        
        # 更新滚动区域
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 更新滚动条显示状态
        if self.scrollable_frame.winfo_height() > self.canvas.winfo_height():
            self.scrollbar.grid()
        else:
            self.scrollbar.grid_remove()

    def clear_search(self):
        """清除搜索框内容"""
        self.search_var.set("")  # 清空搜索框
        self.search_entry.focus_set()  # 将焦点设置回搜索框

    def focus_search(self, event=None):
        """Ctrl+F 快捷键处理函数"""
        self.search_entry.focus_set()
        return "break"  # 阻止事件继续传播

    def focus_next_widget(self, event):
        """处理 Tab 键事件"""
        current = event.widget
        widgets = self.get_input_widgets()
        try:
            next_idx = (widgets.index(current) + 1) % len(widgets)
            widgets[next_idx].focus_set()
        except ValueError:
            pass
        return "break"  # 阻止默认的 Tab 键行为

    def focus_prev_widget(self, event):
        """处理 Shift+Tab 键事件"""
        current = event.widget
        widgets = self.get_input_widgets()
        try:
            prev_idx = (widgets.index(current) - 1) % len(widgets)
            widgets[prev_idx].focus_set()
        except ValueError:
            pass
        return "break"  # 阻止默认的 Shift+Tab 键行为

    def get_input_widgets(self):
        """获取所有可输入的文本框"""
        widgets = []
        if isinstance(self.model_type, tk.Text):
            widgets.append(self.model_type)
        if isinstance(self.model_url, tk.Text):
            widgets.append(self.model_url)
        if isinstance(self.trigger_words, tk.Text):
            widgets.append(self.trigger_words)
        if isinstance(self.model_desc, tk.Text):
            widgets.append(self.model_desc)
        return widgets

    def create_context_menu(self, widget):
        """创建右键菜单"""
        menu = tk.Menu(self.master, tearoff=0, font=self.base_font)
        
        # 添加菜单项
        menu.add_command(
            label="粘贴并替换", 
            command=lambda: self.paste_and_replace(widget)
        )
        menu.add_command(
            label="粘贴", 
            command=lambda: self.paste_text(widget)
        )
        menu.add_command(
            label="复制", 
            command=lambda: self.copy_text(widget)
        )
        menu.add_separator()
        menu.add_command(
            label="清空", 
            command=lambda: self.clear_text(widget)
        )
        
        return menu

    def show_context_menu(self, event, menu):
        """显示右键菜单"""
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def paste_and_replace(self, widget):
        """粘贴并替换文本"""
        try:
            text = self.master.clipboard_get()
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
                widget.insert("1.0", text)
            elif isinstance(widget, ttk.Entry):
                widget.configure(state='normal')
                widget.delete(0, tk.END)
                widget.insert(0, text)
                if widget == self.model_name:  # 如果是模型名称输入框，恢复只读状态
                    widget.configure(state='readonly')
            self.auto_save_changes()
        except tk.TclError:
            pass  # 剪贴板为空时不做操作

    def paste_text(self, widget):
        """粘贴文本"""
        try:
            text = self.master.clipboard_get()
            if isinstance(widget, tk.Text):
                widget.insert(tk.INSERT, text)
            elif isinstance(widget, ttk.Entry):
                widget.configure(state='normal')
                widget.insert(tk.INSERT, text)
                if widget == self.model_name:  # 如果是模型名称输入框，恢复只读状态
                    widget.configure(state='readonly')
            self.auto_save_changes()
        except tk.TclError:
            pass  # 剪贴板为空时不做操作

    def copy_text(self, widget):
        """复制文本"""
        if isinstance(widget, tk.Text):
            if widget.tag_ranges(tk.SEL):  # 如果有选中的文本
                text = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            else:
                text = widget.get("1.0", tk.END).strip()
        elif isinstance(widget, ttk.Entry):
            if widget.selection_present():  # 如果有选中的文本
                text = widget.selection_get()
            else:
                text = widget.get()
        
        if text:
            self.master.clipboard_clear()
            self.master.clipboard_append(text)

    def clear_text(self, widget):
        """清空文本"""
        if isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
        elif isinstance(widget, ttk.Entry):
            widget.configure(state='normal')
            widget.delete(0, tk.END)
            if widget == self.model_name:  # 如果是模型名称输入框，恢复只读状态
                widget.configure(state='readonly')
        self.auto_save_changes()

    def get_subfolders(self, category):
        """获取指定类别下的所有子文件夹"""
        subfolders = set()
        category_path = os.path.join(BASE_PATH, category)
        
        if os.path.exists(category_path):
            # 遍历目录
            for root, dirs, files in os.walk(category_path):
                # 获取相对于类别目录的路径
                relative_path = os.path.relpath(root, category_path)
                if relative_path != '.':  # 排除当前目录
                    # 将路径分割成各级目录名
                    path_parts = relative_path.split(os.sep)
                    # 只添加第一级子文件夹
                    if len(path_parts) == 1:
                        subfolders.add(path_parts[0])
        
        # 添加"其他"和"收藏"选项
        subfolders.add("其他")
        subfolders.add("收藏")
        
        # 转换为排序的列表
        return sorted(list(subfolders))

    def create_model_context_menu(self):
        """创建模型列表右键菜单"""
        menu = tk.Menu(self.master, tearoff=0, font=self.base_font)
        
        # 添加第一行按钮的功能
        if self.current_file and self.is_favorite(self.current_file):
            menu.add_command(label="取消收藏", command=self.toggle_favorite)
        else:
            menu.add_command(label="收藏模型", command=self.toggle_favorite)
        menu.add_command(label="打开路径", command=self.open_model_path)
        #menu.add_command(label="换预览图", command=self.change_preview_image)
        menu.add_command(label="更新哈希", command=self.update_current_hash)
        
        menu.add_separator()
        
        # 添加新功能
        menu.add_command(label="移动模型", command=self.move_model)
        menu.add_command(label="复制模型", command=self.copy_model)
        menu.add_command(label="删除模型", command=self.delete_model)
        
        return menu

    def show_model_context_menu(self, event, file_path):
        """显示模型右键菜单"""
        # 先选中点击的模型
        file_name = os.path.basename(file_path)
        relative_path = os.path.dirname(file_path)
        self.select_file(file_name, relative_path)  # 使用 select_file 而不是 select_model
        
        # 显示菜单
        try:
            menu = self.create_model_context_menu()
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def copy_model(self):
        """复制模型及相关文件"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
        
        # 创建进度提示框
        progress_window = tk.Toplevel(self.master)
        progress_window.title("复制模型")
        progress_window.geometry("400x150")
        progress_window.transient(self.master)
        progress_window.grab_set()
        
        # 居中显示
        progress_window.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 200}+"
                       f"{self.master.winfo_y() + self.master.winfo_height()//2 - 75}")
        
        # 创建主框架
        main_frame = ttk.Frame(progress_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建状态标签
        status_label = ttk.Label(main_frame, text="准备复制...", wraplength=380)
        status_label.pack(pady=(0, 10))
        
        # 创建进度条
        progress_bar = ttk.Progressbar(
            main_frame,
            mode='determinate',
            style='primary.Horizontal.TProgressbar'
        )
        progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        def update_status(text, progress=None):
            status_label.config(text=text)
            if progress is not None:
                progress_bar['value'] = progress
            progress_window.update()
        
        try:
            # 获取源文件路径信息
            source_path = os.path.join(BASE_PATH, self.current_file)
            source_dir = os.path.dirname(source_path)
            model_name = os.path.basename(source_path)
            model_basename, model_ext = os.path.splitext(model_name)
            
            # 获取目标路径,并使用当前目录作为初始目录
            target_dir = filedialog.askdirectory(title="选择要复制到的文件夹", initialdir=source_dir)
            if not target_dir:
                progress_window.destroy()
                return
            
            # 检查目标文件是否存在，如果存在则重命名
            target_path = os.path.join(target_dir, model_name)
            counter = 1
            while os.path.exists(target_path):
                new_basename = f"{model_basename}(���本){counter if counter > 1 else ''}"
                target_path = os.path.join(target_dir, new_basename + model_ext)
                counter += 1
            
            new_model_basename = os.path.splitext(os.path.basename(target_path))[0]
            
            # 复制模型文件
            update_status("正在复制模型文件...", 0)
            total_size = os.path.getsize(source_path)
            copied_size = 0
            shutil.copy2(source_path, target_path)
            
            with open(source_path, 'rb') as fsrc, open(target_path, 'wb') as fdst:
                while True:
                    buf = fsrc.read(10 * 1024 * 1024)  # 每次读取10MB
                    if not buf:
                        break
                    fdst.write(buf)
                    copied_size += len(buf)
                    progress = (copied_size / total_size) * 80  # 模型文件占总进度的80%
                    update_status(f"正在复制模型文件... {copied_size/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB", progress)
            
            # 复制同名json文件（如果存在）
            json_path = os.path.join(source_dir, f"{model_basename}.json")
            if os.path.exists(json_path):
                new_json_path = os.path.join(target_dir, f"{new_model_basename}.json")
                shutil.copy2(json_path, new_json_path)
            
            # 复制预览图（如果存在）
            update_status("正在复制预览图...", 80)
            for ext in self.supported_image_extensions:
                preview_name = model_basename + ext
                preview_path = os.path.join(source_dir, preview_name)
                if os.path.exists(preview_path):
                    target_preview = os.path.join(target_dir, new_model_basename + ext)
                    shutil.copy2(preview_path, target_preview)
                    break
            
            # 复制适配CS生成的配置文件夹（如果存在）
            update_status("正在复制配置文件...", 90)
            cs_folder = os.path.join(source_dir, model_basename)
            if os.path.exists(cs_folder) and os.path.isdir(cs_folder):
                target_cs_folder = os.path.join(target_dir, new_model_basename)
                shutil.copytree(cs_folder, target_cs_folder)
            
            # 复制模型信息（如果目标路径在程序目录下）
            update_status("正在复制模型信息...", 95)
            try:
                relative_target = os.path.relpath(target_path, BASE_PATH)
                info_file = 'model_info.json'
                if os.path.exists(info_file):
                    with open(info_file, 'r', encoding='utf-8') as f:
                        all_info = json.load(f)
                    if self.current_file in all_info:
                        # 复制模型信息，但重置收藏状态
                        model_info = all_info[self.current_file].copy()
                        model_info['is_favorite'] = False
                        all_info[relative_target] = model_info
                        with open(info_file, 'w', encoding='utf-8') as f:
                            json.dump(all_info, f, ensure_ascii=False, indent=2)
            except ValueError:
                # 目标路径不在程序目录下，忽略信息复制
                pass
            
            update_status("复制完成！", 100)
            
            # 刷新文件列表
            self.refresh_files()
            
            # 延迟关闭窗口
            progress_window.after(1000, progress_window.destroy)
            self.show_popup_message("模型及相关文件复制成功")
            
        except Exception as e:
            progress_window.destroy()
            self.show_popup_message(f"复制模型时发生错误：{str(e)}")


    def show_cf_node_menu(self):
        """显示CF节点选择菜单"""
        if not self.current_file:
            self.show_popup_message("请先选择一个模型文件")
            return
        
        menu = tk.Menu(self.master, tearoff=0, font=self.base_font)
        menu.add_command(label="普通节点", command=lambda: self.copy_cf_node("normal"))
        menu.add_command(label="pysss节点", command=lambda: self.copy_cf_node("pysss"))
        
        def find_button(widget):
            """递归查找按钮"""
            if isinstance(widget, ttk.Button) and widget['text'] == "去CF粘贴节点":
                return widget
                
            for child in widget.winfo_children():
                result = find_button(child)
                if result:
                    return result
            return None
        
        button = find_button(self.right_frame)
        
        if button:
            # 获取按钮位置和尺寸
            x = button.winfo_rootx()
            # 在按钮上方显示，减去菜单高度（估计值）和一些间距
            y = button.winfo_rooty() - 50  
            menu.post(x, y)
        else:
            # 后备方案：使用鼠标当前位置
            x = self.master.winfo_pointerx()
            y = self.master.winfo_pointery() - 50
            menu.post(x, y)

    def copy_cf_node(self, node_type):
        """生成并复制CF节点"""
        if not self.current_file:
            return
        
        # 获取模型文件名
        model_name = os.path.basename(self.current_file)
        print(f"模型文件名: {model_name}")
        
        # 获取当前类别
        category = os.path.dirname(self.current_file).split(os.sep)[0].lower()
        print(f"模型类别: {category}")
        # 根据类别和节点类型生成不同的节点数据
        node_data = {}
        
        if node_type == "normal":
            if category == "checkpoints":
                node_data = {
                    "3": {
                        "inputs": {
                            "ckpt_name": model_name
                        },
                        "class_type": "CheckpointLoaderSimple"
                    }
                }
            elif category == "loras":
                node_data = {
                    "3": {
                        "inputs": {
                            "lora_name": model_name,
                            "strength_model": 1.0,
                            "strength_clip": 1.0
                        },
                        "class_type": "LoraLoader"
                    }
                }
            elif category == "embeddings":
                node_data = {
                    "3": {
                        "inputs": {
                            "embedding_name": model_name
                        },
                        "class_type": "CLIPTextEncode"
                    }
                }
            elif category == "controlnet":
                node_data = {
                    "3": {
                        "inputs": {
                            "control_net_name": model_name
                        },
                        "class_type": "ControlNetLoader"
                    }
                }
            elif category == "upscaler":
                node_data = {
                    "3": {
                        "inputs": {
                            "model_name": model_name
                        },
                        "class_type": "UpscaleModelLoader"
                    }
                }
        elif node_type == "pysss":
            # 根据不同模型类型生成pysss节点
            # TODO: 待添加pysss节点的具体格式
            pass
        
        if node_data:
            # 将节点数据转换为JSON字符串并复制到剪贴板
            json_str = json.dumps(node_data, indent=2, ensure_ascii=False)
            print(f"节点数据: {json_str}")
            self.master.clipboard_clear()
            self.master.clipboard_append(json_str)
            self.show_popup_message("节点数据已复制到剪贴板")
        else:
            self.show_popup_message("不支持的模型类别")

    def get_saved_font(self):
        """从 model_info.json 获取保存的字体设置"""
        try:
            info_file = 'model_info.json'
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
                    if "_app_settings" in all_info:
                        return all_info["_app_settings"].get("font_family")
        except Exception as e:
            logging.error(f"读取字体设置时发生错误：{str(e)}")
        return None

    def save_font(self, font_family):
        """保存字体设置到 model_info.json"""
        try:
            info_file = 'model_info.json'
            all_info = {}
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
            
            if "_app_settings" not in all_info:
                all_info["_app_settings"] = {}
            
            all_info["_app_settings"]["font_family"] = font_family
            
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(all_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存字体设置时发生错误：{str(e)}")

    def update_fonts(self):
        """更新所有字体设置"""
        self.base_font = (self.current_font_family, self.base_font_size)
        self.base_title_font = (self.current_font_family, self.base_title_font_size, 'bold')
        
        # 更新已创建的控件字体
        self.update_widget_fonts(self.master)
        
        # 重新应用样式
        self.setup_styles()
        
        # 刷新界面显示
        if hasattr(self, 'announcement_text'):
            self.announcement_text.configure(font=self.base_font)
        
        # 更新所有文本输入框的字体
        for widget in [self.model_name, self.model_info, self.model_type, 
                      self.model_url, self.model_desc, self.trigger_words]:
            if isinstance(widget, (tk.Text, ttk.Entry)):
                widget.configure(font=self.base_font)

    def update_widget_fonts(self, widget):
        """递归更新所有控件的字体"""
        try:
            # 更新当前控件的字体
            if isinstance(widget, (ttk.Label, ttk.Button, ttk.Entry)):
                widget.configure(font=self.base_font)
            elif isinstance(widget, tk.Text):
                widget.configure(font=self.base_font)
            
            # 递归更新子控件
            for child in widget.winfo_children():
                self.update_widget_fonts(child)
        except:
            pass


    def show_font_size_menu(self):
        """显示字体大小菜单"""
        menu = tk.Menu(self.master, tearoff=0, font=self.base_font)
        
        # 添加选项
        menu.add_command(
            label="选择字体",
            command=self.show_font_menu,
            font=self.base_font
        )
        menu.add_separator()
        
        # 获取当前字体大小状态
        current_size = '大字体显示' if self.base_font_size > self.small_base_font_size_base else '小字体显示'
        
        # 添加字体大小选项，确保首次打开时显示正确
        menu.add_command(
            label="✓ 大字体显示" if self.base_font_size > self.small_base_font_size_base else "大字体显示",
            command=lambda: self.change_font_size('large'),
            font=self.base_font
        )
        print(self.base_font_size, self.small_base_font_size_base)  
        menu.add_command(
            label="✓ 小字体显示" if self.base_font_size <= self.small_base_font_size_base else "小字体显示",
            command=lambda: self.change_font_size('small'),
            font=self.base_font
        )
        
        # 在按钮下方显示菜单
        x = self.font_btn.winfo_rootx()
        y = self.font_btn.winfo_rooty() + self.font_btn.winfo_height()
        menu.post(x, y)

    def show_font_menu(self):
        """显示字体选择对话框"""
        dialog = tk.Toplevel(self.master)
        dialog.title("选择字体")
        dialog.geometry("400x500")
        dialog.transient(self.master)
        dialog.grab_set()
        
        # 居中显示
        dialog.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 200}+"
                       f"{self.master.winfo_y() + self.master.winfo_height()//2 - 250}")
        
        # 创建主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 获取系统字体列表
        font_list = sorted(list(set(tkfont.families())))  # 使用set去重
        
        # 创建列表框
        font_listbox = tk.Listbox(
            main_frame,
            font=self.base_font,
            selectmode=tk.SINGLE
        )
        font_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(font_listbox)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        font_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=font_listbox.yview)
        
        # 添加字体到列表框
        for font in font_list:
            font_listbox.insert(tk.END, font)
        
        # 选中当前字体
        try:
            current_index = font_list.index(self.current_font_family)
            font_listbox.select_set(current_index)
            font_listbox.see(current_index)
        except ValueError:
            pass
        
        # 预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="预览")
        preview_frame.pack(fill=tk.X, pady=(0, 10))
        
        preview_text = tk.Text(
            preview_frame,
            height=3,
            wrap=tk.WORD,
            font=self.base_font
        )
        preview_text.pack(fill=tk.X, padx=5, pady=5)
        preview_text.insert("1.0", "月光AI宝盒-模型管理器\nABCDEFGHIJKLMNOPQRSTUVWXYZ\n0123456789")
        preview_text.configure(state='disabled')
        
        def update_preview(*args):
            selection = font_listbox.curselection()
            if selection:
                font_family = font_listbox.get(selection[0])
                preview_text.configure(state='normal')
                preview_text.configure(font=(font_family, self.base_font_size))
                preview_text.configure(state='disabled')
        
        font_listbox.bind('<<ListboxSelect>>', update_preview)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        def apply_font():
            selection = font_listbox.curselection()
            if selection:
                font_family = font_listbox.get(selection[0])
                self.current_font_family = font_family
                self.save_font(font_family)
                self.update_fonts()
                dialog.destroy()
                self.show_popup_message("字体已更新")
        
        ttk.Button(
            button_frame,
            text="确定",
            command=apply_font,
            style='primary.TButton',
            width=10
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame,
            text="取消",
            command=dialog.destroy,
            style='primary.TButton',
            width=10
        ).pack(side=tk.RIGHT)

    def change_font_size(self, size_mode):
        """更改字体大小"""
        if size_mode == 'large':
            self.base_font_size = int(self.large_base_font_size_base / (self.dpi_scale ** (1/3)))
            self.base_title_font_size = int(self.large_base_title_font_size_base / (self.dpi_scale ** (1/3)))
        elif size_mode == 'small':
            self.base_font_size = int(self.small_base_font_size_base / (self.dpi_scale ** (1/3)))
            self.base_title_font_size = int(self.small_base_title_font_size_base / (self.dpi_scale ** (1/3)))
        
        # 保存字体大小设置
        try:
            info_file = 'model_info.json'
            all_info = {}
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    all_info = json.load(f)
            
            if "_app_settings" not in all_info:
                all_info["_app_settings"] = {}
            
            all_info["_app_settings"]["font_size_mode"] = size_mode
            
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(all_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存字体大小设置时发生错误：{str(e)}")
        
        # 更新字体
        self.update_fonts()
        self.show_popup_message("字体大小已更新")

    def show_batch_menu(self):
        """显示一键脚本菜单"""
        menu = tk.Menu(self.master, tearoff=0, font=self.base_font)
        
        menu.add_command(
            label="一键计算哈希值",
            command=lambda: self.batch_process('hash'),
            font=self.base_font
        )
        menu.add_command(
            label="一键适配CS",
            command=lambda: self.batch_process('cs'),
            font=self.base_font
        )
        menu.add_command(
            label="一键适配SD",
            command=lambda: self.batch_process('sd'),
            font=self.base_font
        )
        menu.add_separator()
        menu.add_command(
            label="一键从Liblib抓取",
            command=self.batch_fetch_from_liblib,
            font=self.base_font
        )
        menu.add_command(
            label="一键从Civitai抓取",
            command=self.batch_fetch_from_civitai,
            font=self.base_font
        )
        
        # 在按钮右侧显示菜单
        button = self.batch_btn
        x = button.winfo_rootx() + button.winfo_width()
        y = button.winfo_rooty()
        menu.post(x, y)

    def batch_process(self, process_type):
        """批量处理功能"""
        # 确认对话框的消息
        messages = {
            'hash': "是否要为所有模型计算哈希值？\n如果大文件较多，可能需要较长时间，请耐心等待",
            'cs': "是否要为所有模型创建CS配置文件？\n将会在模型文件夹中创建或替换Describe.txt和Trigger_Words.txt文件",
            'sd': "是否要为所有模型创建SD配置文件？\n将会在模型文件夹中创建或替换.json文件"
        }
        
        if not messagebox.askyesno("确认", messages[process_type]):
            return
        
        # 创建进度窗口
        progress_window = tk.Toplevel(self.master)
        progress_window.title("批量处理")
        progress_window.geometry("400x150")
        progress_window.transient(self.master)
        progress_window.grab_set()
        
        # 居中显示
        progress_window.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 200}+"
                           f"{self.master.winfo_y() + self.master.winfo_height()//2 - 75}")
        
        # 创建主框架
        main_frame = ttk.Frame(progress_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建状态标签
        status_label = ttk.Label(main_frame, text="准备处理...", wraplength=380)
        status_label.pack(pady=(0, 10))
        
        # 创建进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            main_frame,
            variable=progress_var,
            maximum=100,
            mode='determinate',
            style='primary.Horizontal.TProgressbar'
        )
        progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # 创建取消按钮 - 修改这部分
        cancel_flag = [False]  # 使用列表而不是字典
        cancel_btn = ttk.Button(
            main_frame,
            text="取消",
            command=lambda: cancel_flag.__setitem__(0, True),  # 修改取消按钮的命令
            style='primary.TButton'
        )
        cancel_btn.pack(pady=(0, 10))
        
        def update_progress(current, total, message):
            if not progress_window.winfo_exists():
                return
            progress = (current / total) * 100
            progress_var.set(progress)
            status_label.config(text=message)
            progress_window.update()
        
        def process():
            try:
                total_files = len(self.all_files)
                processed = 0
                skipped = 0
                
                for file, path in self.all_files:
                    # 先检查取消标志
                    if cancel_flag[0]:
                        update_progress(processed + skipped, total_files, "正在取消...")
                        break
                    
                    full_path = os.path.join(BASE_PATH, path, file)
                    update_progress(processed, total_files, f"正在处理: \n{file[:18] + '...' if len(file) > 18 else file}")
                    
                    try:
                        # 每个操作前都检查取消标志
                        if cancel_flag[0]:
                            break
                            
                        if process_type == 'hash':
                            # 计算哈希值
                            hash_value = self.calculate_file_hash(full_path)
                            if hash_value and not cancel_flag[0]:  # 再次检查取消标志
                                info = self.get_model_info(os.path.join(path, file))
                                info['hash'] = hash_value
                                self.save_model_info(os.path.join(path, file), info)
                        
                        elif process_type == 'cs':
                            if cancel_flag[0]:
                                break
                            # 创建CS配置文件
                            model_dir = os.path.dirname(full_path)
                            model_name = os.path.splitext(os.path.basename(full_path))[0]
                            custom_dir = os.path.join(model_dir, model_name)
                            os.makedirs(custom_dir, exist_ok=True)
                            
                            info = self.get_model_info(os.path.join(path, file))
                            description = info.get('description', '')
                            trigger_words = info.get('trigger_words', '')
                            
                            if description and not cancel_flag[0]:
                                with open(os.path.join(custom_dir, "Describe.txt"), 'w', encoding='utf-8') as f:
                                    f.write(description)
                            if trigger_words and not cancel_flag[0]:
                                with open(os.path.join(custom_dir, "Trigger_Words.txt"), 'w', encoding='utf-8') as f:
                                    f.write(trigger_words)
                        
                        elif process_type == 'sd':
                            if cancel_flag[0]:
                                break
                            # 创建SD配置文件
                            model_dir = os.path.dirname(full_path)
                            model_name = os.path.splitext(os.path.basename(full_path))[0]
                            json_path = os.path.join(model_dir, f"{model_name}.json")
                            
                            info = self.get_model_info(os.path.join(path, file))
                            json_data = {
                                "description": info.get('description', ''),
                                "sd version": "",
                                "activation text": info.get('trigger_words', ''),
                                "preferred weight": 0,
                                "negative text": "",
                                "notes": ""
                            }
                            
                            if not cancel_flag[0]:
                                with open(json_path, 'w', encoding='utf-8') as f:
                                    json.dump(json_data, f, ensure_ascii=False, indent=4)
                        
                        processed += 1
                    except Exception as e:
                        logging.error(f"处理文件 {file} 时发生错误: {str(e)}")
                        skipped += 1
                    
                if cancel_flag[0]:
                    update_progress(processed + skipped, total_files, "操作已取消")
                else:
                    update_progress(processed + skipped, total_files, 
                                  f"已处理: {processed} 个文件 跳过: {skipped} 个文件")
                
                # 修改取消按钮为关闭按钮
                cancel_btn.configure(
                    text="关闭",
                    command=lambda: finish_process()
                )

            except Exception as e:
                self.show_popup_message(f"批量处理时发生错误：{str(e)}")

        def finish_process():
            """完成处理后的清理工作"""
            progress_window.destroy()
            # 刷新文件列表
            self.refresh_files()

        
        # 在新线程中执行处理
        threading.Thread(target=process, daemon=True).start()

    def batch_fetch_from_liblib(self):
        """批量从Liblib抓取模型信息"""
        if not messagebox.askyesno("确认", "是否要从Liblib批量抓取模型信息？\n此操作会对所有包含Liblib网址的模型信息进行覆盖，请谨慎操作\n由于网络波动原因，并不保证一定抓取成功，请手动查漏补缺"):
            return
        
        # 询问预览图处理方式
        replace_all = messagebox.askyesno("预览图处理", "是否替换所有模型的预览图？\n选择\"是\"将替换所有预览图\n选择\"否\"将只为没有预览图的模型添加预览图")
        
        # 保存当前选中的文件
        current_selected_file = self.current_file
        
        # 取消当前选中状态
        self.current_file = None
        if current_selected_file in self.file_frames:
            frame, path_label, name_label = self.file_frames[current_selected_file]
            frame.configure(style='List.TFrame')
            path_label.configure(style='Left.TLabel')
            name_label.configure(style='Left.TLabel')
            # 重置所有子部件的样式
            for widget in frame.winfo_children():
                if isinstance(widget, ttk.Frame):
                    widget.configure(style='List.TFrame')
                elif isinstance(widget, ttk.Label):
                    widget.configure(style='Left.TLabel')
        
        # 创建进度窗口
        progress_window = tk.Toplevel(self.master)
        progress_window.title("批量抓取")
        progress_window.geometry("400x150")
        progress_window.transient(self.master)
        progress_window.grab_set()
        
        # 居中显示
        progress_window.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 200}+"
                       f"{self.master.winfo_y() + self.master.winfo_height()//2 - 75}")
        
        # 创建主框架
        main_frame = ttk.Frame(progress_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建状态标签
        status_label = ttk.Label(main_frame, text="准备抓取...", wraplength=380)
        status_label.pack(pady=(0, 10))
        
        # 创建进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            main_frame,
            variable=progress_var,
            maximum=100,
            mode='determinate',
            style='primary.Horizontal.TProgressbar'
        )
        progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # 创建取消按钮
        cancel_flag = [False]  # 使用列表而不是字典
        cancel_btn = ttk.Button(
            main_frame,
            text="取消",
            command=lambda: cancel_flag.__setitem__(0, True),  # 修改取消按钮的命令
            style='primary.TButton'
        )
        cancel_btn.pack(pady=(0, 10))
        
        def update_progress(current, total, message):
            if not progress_window.winfo_exists():
                return
            progress = (current / total) * 100
            #print(f"进度: {progress},当前: {current},总数: {total}")
            progress_var.set(progress)
            status_label.config(text=message)
            progress_window.update()
        
        def process():
            try:
                # 保存当前选中的文件
                current_selected_file = self.current_file
                
                total_files = len(self.all_files)
                processed = 0
                skipped = 0
                success = 0
                
                for file, path in self.all_files:
                    if cancel_flag[0]:  # 检查取消标志
                        break
                    
                    full_path = os.path.join(BASE_PATH, path, file)
                    update_progress(processed, total_files, f"正在处理: \n{file[:18] + '...' if len(file) > 18 else file}")
                    
                    try:
                        # 获取模型信息
                        info = self.get_model_info(os.path.join(path, file))
                        url = info.get('url', '').strip()
                        
                        # 检查是否有Liblib网址
                        if url and 'liblib.art' in url:
                            # 检查预览图
                            has_preview = self.get_image_path(file, path) is not None
                            if has_preview and not replace_all:
                                # 如果有预览图且不替换，跳过预览图处理
                                need_preview = False
                            else:
                                need_preview = True
                            
                            def get_browser_path():
                                """获取 Firefox 浏览器路径"""
                                try:
                                    if getattr(sys, 'frozen', False):
                                        # 打包环境
                                        base_dir = sys._MEIPASS
                                        firefox_path = os.path.join(base_dir, 'firefox', 'firefox', 'firefox.exe')  # 注意这里添加了两次 firefox
                                        if os.path.exists(firefox_path):
                                            print(f"使用打包的Firefox: {firefox_path}")
                                            return firefox_path
                                    
                                    # 开发环境
                                    return None
                                except Exception as e:
                                    logging.error(f"获取浏览器路径失败：{str(e)}")
                                return None     

                            # 使用 playwright 抓取信息
                            with sync_playwright() as p:
                                browser = None
                                try:
                                    browser = None
                                    browser_path = get_browser_path()
                                    print(f"浏览器路径: {browser_path}")
                                    # 启动浏览器时显式指定可执行文件路径
                                    browser = p.firefox.launch(
                                        headless=True,
                                        executable_path = browser_path # 指定浏览器路径
                                    )
                                    page = browser.new_page()
                                    
                                    # 访问页面
                                    page.goto(url)
                                    
                                    # 标记是否有任何内容被抓取
                                    content_found = False
                                    
                                    # 尝试获取预览图
                                    if need_preview:
                                        try:
                                            if page.wait_for_selector(".ModelVersion_modelVersion__4cm1k .relative.cursor-pointer img", timeout=3000):
                                                img_element = page.query_selector(".ModelVersion_modelVersion__4cm1k .relative.cursor-pointer img")
                                                if img_element:
                                                    img_url = img_element.get_attribute("src")
                                                    if img_url:
                                                        headers = {
                                                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                                                        }
                                                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                                                            img_response = requests.get(img_url, headers=headers)
                                                            if img_response.status_code == 200:
                                                                temp_file.write(img_response.content)
                                                                # 直接保存预览图，而不是使用replace_preview_image方法
                                                                preview_path = os.path.join(BASE_PATH, path, f"{os.path.splitext(file)[0]}.png")
                                                                with Image.open(temp_file.name) as img:
                                                                    img.save(preview_path, "PNG")
                                        except Exception as e:
                                            logging.error(f"当前文件: {file} 获取预览图失败：{str(e)}")
                                except Exception as e:
                                    logging.error(f"启动浏览器失败：{str(e)}")

                                # 获取触发词
                                try:
                                    if page.wait_for_selector(".ModelDetailCard_triggerTxt__cKZOL", timeout=1000):
                                        trigger_elements = page.query_selector_all(".ModelDetailCard_triggerTxt__cKZOL")
                                        if trigger_elements:
                                            trigger_words = [element.inner_text() for element in trigger_elements]
                                            if trigger_words:
                                                info['trigger_words'] = ", ".join(trigger_words)
                                except Exception as e:
                                    logging.error(f"当前文件: {file} 获取触发词失败：{str(e)}")
                                
                                # 获取描述
                                try:
                                    if page.wait_for_selector('.ModelDescription_desc__EoTMz', timeout=1000):
                                        description_container = page.query_selector('.ModelDescription_desc__EoTMz')
                                        if description_container:
                                            script = """
                                            (element) => {
                                                const texts = [];
                                                const walk = (node) => {
                                                    if (node.nodeType === 3 && node.textContent.trim()) {
                                                        texts.push(node.textContent.trim());
                                                    } else if (node.nodeType === 1) {
                                                        if (node.tagName === 'BR') {
                                                            texts.push('');
                                                        }
                                                        for (const child of node.childNodes) {
                                                            walk(child);
                                                        }
                                                        if (['P', 'DIV', 'LI'].includes(node.tagName)) {
                                                            texts.push('');
                                                        }
                                                    }
                                                };
                                                walk(element);
                                                return texts.filter(text => text !== '');
                                            }
                                            """
                                            description_lines = description_container.evaluate(script)
                                            if description_lines:
                                                liblib_marker = "=== 从Liblib抓取的描述 ==="
                                                new_desc = liblib_marker + "\n" + "\n\n".join(description_lines)
                                                info['description'] = new_desc
                                except Exception as e:
                                    logging.error(f"当前文件: {file} 获取描述失败：{str(e)}")
                                
                                browser.close()
                            
                            # 保存更新后的信息
                            self.save_model_info(os.path.join(path, file), info)
                            success += 1
                        else:
                            skipped += 1
                        
                        processed += 1
                        
                    except Exception as e:
                        logging.error(f"处理文件 {file} 时发生错误: {str(e)}")
                        skipped += 1
                    
                
                if cancel_flag[0]:
                    update_progress(processed + skipped, total_files, "操作已取消")
                else:
                    update_progress(processed + skipped, total_files, 
                                  f"已处理: {processed} 个文件 成功: {success} 个 跳过: {skipped} 个")
                    progress_var.set(100)
                    
                # 修改取消按钮为关闭按钮
                cancel_btn.configure(
                    text="关闭",
                    command=lambda: finish_process(current_selected_file)
                )
            
            except Exception as e:
                self.show_popup_message(f"批量抓取时发生错误：{str(e)}")
                progress_window.destroy()
        
        def finish_process(selected_file):
            """完成处理后的清理工作"""
            # 关闭进度窗口
            progress_window.destroy()
            
            # 刷新文件列表
            self.refresh_files()
            
            # 如果之前有选中的文件，重新选中并刷新其信息
            if selected_file:
                file_name = os.path.basename(selected_file)
                relative_path = os.path.dirname(selected_file)
                
                # 清空当前输入框的内容
                if isinstance(self.model_type, tk.Text):
                    self.model_type.delete("1.0", tk.END)
                if isinstance(self.model_url, tk.Text):
                    self.model_url.delete("1.0", tk.END)
                if isinstance(self.model_desc, tk.Text):
                    self.model_desc.delete("1.0", tk.END)
                if isinstance(self.trigger_words, tk.Text):
                    self.trigger_words.delete("1.0", tk.END)
                
                # 重新选中文件
                self.select_file(file_name, relative_path)
                
                # 强制重新加载模型信息
                self.load_model_info()
                
                # 重新加载预览图
                self.load_preview(file_name, relative_path)
                
                # 确保界面更新
                self.master.update_idletasks()
        
        # 在新线程中执行处理
        threading.Thread(target=process, daemon=True).start()

    def batch_fetch_from_civitai(self):
        """批量从Civitai抓取模型信息"""
        if not messagebox.askyesno("确认", "是否要从Civitai批量抓取模型信息？\n此操作需要先计算模型哈希值，可能需要较长时间\n本过程将自动跳过已存在Liblib网址的模型\n由于网络（科学网络必须）波动原因，并不保证一定抓取成功，请手动查漏补缺"):
            return
        
        # 询问预览图处理方式
        replace_all = messagebox.askyesno("预览图处理", "是否替换所有模型的预览图？\n选择\"是\"将替换所有预览图\n选择\"否\"将只为没有预览图的模型添加预览图")
        
        # 保存当前选中的文件
        current_selected_file = self.current_file
        
        # 取消当前选中状态
        self.current_file = None
        if current_selected_file in self.file_frames:
            frame, path_label, name_label = self.file_frames[current_selected_file]
            frame.configure(style='List.TFrame')
            path_label.configure(style='Left.TLabel')
            name_label.configure(style='Left.TLabel')
            # 重置所有子部件的样式
            for widget in frame.winfo_children():
                if isinstance(widget, ttk.Frame):
                    widget.configure(style='List.TFrame')
                elif isinstance(widget, ttk.Label):
                    widget.configure(style='Left.TLabel')
    
        # 创建进度窗口
        progress_window = tk.Toplevel(self.master)
        progress_window.title("批量抓取")
        progress_window.geometry("400x150")
        progress_window.transient(self.master)
        progress_window.grab_set()
    
        # 居中显示
        progress_window.geometry(f"+{self.master.winfo_x() + self.master.winfo_width()//2 - 200}+"
                       f"{self.master.winfo_y() + self.master.winfo_height()//2 - 75}")
    
        # 创建主框架
        main_frame = ttk.Frame(progress_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        # 创建状态标签
        status_label = ttk.Label(main_frame, text="准备抓取...", wraplength=380)
        status_label.pack(pady=(0, 10))
    
        # 创建进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            main_frame,
            variable=progress_var,
            maximum=100,
            mode='determinate',
            style='primary.Horizontal.TProgressbar'
        )
        progress_bar.pack(fill=tk.X, pady=(0, 10))
    
        # 创建取消按钮
        cancel_flag = [False]
        cancel_btn = ttk.Button(
            main_frame,
            text="取消",
            command=lambda: cancel_flag.__setitem__(0, True),
            style='primary.TButton'
        )
        cancel_btn.pack(pady=(0, 10))
    
        def update_progress(current, total, message):
            if not progress_window.winfo_exists():
                return
            progress = (current / total) * 100
            progress_var.set(progress)
            status_label.config(text=message)
            progress_window.update()
    
        def process():
            try:
                total_files = len(self.all_files)
                processed = 0
                skipped = 0
                success = 0
                
                for file, path in self.all_files:
                    if cancel_flag[0]:
                        break
                    
                    full_path = os.path.join(BASE_PATH, path, file)
                    update_progress(processed, total_files, f"正在处理: \n{file[:18] + '...' if len(file) > 18 else file}")
                    
                    try:
                        # 获取模型信息
                        info = self.get_model_info(os.path.join(path, file))
                        
                        # 检查是否已有Liblib网址
                        url = info.get('url', '').strip()
                        if url and 'liblib.art' in url:
                            skipped += 1
                            processed += 1
                            continue
                        
                        # 获取或计算哈希值
                        hash_value = info.get('hash', '')
                        if not hash_value:
                            hash_value = self.calculate_file_hash(full_path)
                            info['hash'] = hash_value
                        
                        if hash_value:
                            # 检查预览图
                            has_preview = self.get_image_path(file, path) is not None
                            if has_preview and not replace_all:
                                need_preview = False
                            else:
                                need_preview = True
                            
                            # 使用API获取信息
                            api_url = f"https://civitai.com/api/v1/model-versions/by-hash/{hash_value}"
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                            }
                            
                            response = requests.get(api_url, headers=headers, timeout=30)
                            
                            if response.status_code == 200:
                                data = response.json()
                                
                                # 获取模型URL
                                model_id = data.get('modelId')
                                version_id = data.get('id')
                                if model_id and version_id:
                                    info['url'] = f"https://civitai.com/models/{model_id}?modelVersionId={version_id}"
                                
                                # 获取预览图
                                if need_preview and 'images' in data and len(data['images']) > 0:
                                    image_url = data['images'][0].get('url')
                                    if image_url:
                                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                                            img_response = requests.get(image_url, headers=headers)
                                            if img_response.status_code == 200:
                                                temp_file.write(img_response.content)
                                                preview_path = os.path.join(BASE_PATH, path, f"{os.path.splitext(file)[0]}.png")
                                                with Image.open(temp_file.name) as img:
                                                    img.save(preview_path, "PNG")
                                
                                # 获取触发词
                                if 'trainedWords' in data:
                                    info['trigger_words'] = ", ".join(data['trainedWords'])
                                
                                # 获取描述
                                if info['url']:
                                    try:
                                        page_response = requests.get(info['url'], headers=headers, timeout=30)
                                        if page_response.status_code == 200:
                                            soup = BeautifulSoup(page_response.text, 'html.parser')
                                            json_script = soup.find('script', type='application/ld+json')
                                            if json_script:
                                                json_data = json.loads(json_script.string)
                                                description = json_data.get('description', '')
                                                if description:
                                                    desc_soup = BeautifulSoup(description, 'html.parser')
                                                    description_lines = []
                                                    for element in desc_soup.descendants:
                                                        if isinstance(element, NavigableString):
                                                            text = element.strip()
                                                            if text:
                                                                description_lines.append(text)
                                                        elif element.name in ['p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                                            description_lines.append('')
                                                
                                                formatted_description = '\n'.join(description_lines).strip()
                                                if formatted_description:
                                                    info['description'] = "=== 从Civitai抓取的描述 ===\n" + formatted_description
                                    except Exception as e:
                                        logging.error(f"获取描述失败：{str(e)}")
                                
                                # 保存更新后的信息
                                self.save_model_info(os.path.join(path, file), info)
                                success += 1
                            else:
                                skipped += 1
                        else:
                            skipped += 1
                        
                        processed += 1
                        
                    except Exception as e:
                        logging.error(f"处理文件 {file} 时发生错误: {str(e)}")
                        skipped += 1
                                    
                if cancel_flag[0]:
                    update_progress(processed + skipped, total_files, "操作已取消")
                else:
                    update_progress(processed + skipped, total_files, 
                                  f"已处理: {processed} 个文件 成功: {success} 个 跳过: {skipped} 个")
                    progress_var.set(100)
                
                # 修改取消按钮为关闭按钮
                cancel_btn.configure(
                    text="关闭",
                    command=lambda: finish_process(current_selected_file)
                )
                
            except Exception as e:
                self.show_popup_message(f"批量抓取时发生错误：{str(e)}")
                progress_window.destroy()
        
        def finish_process(selected_file):
            """完成处理后的清理工作"""
            # 关闭进度窗口
            progress_window.destroy()
            
            # 刷新文件列表
            self.refresh_files()
            
            # 如果之前有选中的文件，重新选中并刷新其信息
            if selected_file:
                file_name = os.path.basename(selected_file)
                relative_path = os.path.dirname(selected_file)
                
                # 清空当前输入框的内容
                if isinstance(self.model_type, tk.Text):
                    self.model_type.delete("1.0", tk.END)
                if isinstance(self.model_url, tk.Text):
                    self.model_url.delete("1.0", tk.END)
                if isinstance(self.model_desc, tk.Text):
                    self.model_desc.delete("1.0", tk.END)
                if isinstance(self.trigger_words, tk.Text):
                    self.trigger_words.delete("1.0", tk.END)
                
                # 重新选中文件
                self.select_file(file_name, relative_path)
                
                # 强制重新加载模型信息
                self.load_model_info()
                
                # 重新加载预览图
                self.load_preview(file_name, relative_path)
                
                # 确保界面更新
                self.master.update_idletasks()
        
        # 在新线程中执行处理
        threading.Thread(target=process, daemon=True).start()

    def update_stats_label(self):
        """更新统计信息标签"""
        if not hasattr(self, 'stats_label'):
            return
        
        try:
            category = self.category_combobox.get()
            subfolder = self.current_subfolder
            filtered_files = self.filter_files(category, self.search_var.get())
            
            # 计算文件总数
            total_count = len(filtered_files)
            
            # 计算总大小
            total_size = 0
            for file, path in filtered_files:
                try:
                    full_path = os.path.join(BASE_PATH, path, file)
                    total_size += os.path.getsize(full_path)
                except:
                    continue
            
            # 格式化大小
            def format_size(size):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024:
                        return f"{size:.1f} {unit}"
                    size /= 1024
                return f"{size:.1f} TB"
            
            # 构建显示文本
            location_text = f"当前位置: {category}"
            if subfolder:
                location_text += f" > {subfolder}"
            
            stats_text = f"共 {total_count} 个模型，总计 {format_size(total_size)}"
            
            # 更新标签文本
            self.stats_label.configure(text=stats_text)
            
        except Exception as e:
            logging.error(f"更新统计信息时发生错误：{str(e)}")

    def show_preview_context_menu(self, event):
        """显示预览图右键菜单"""
        if not self.current_file:
            return
        
        # 获取当前预览图路径
        file_name = os.path.basename(self.current_file)
        relative_path = os.path.dirname(self.current_file)
        preview_path = self.get_image_path(file_name, relative_path)
        
        if not preview_path:
            self.show_popup_message("当前模型没有预览图")
            return
        
        menu = tk.Menu(self.master, tearoff=0, font=self.base_font)
        menu.add_command(
            label="换预览图",
            command=self.change_preview_image,
            font=self.base_font
        )
        menu.add_separator()
        menu.add_command(
            label="复制图片文件",
            command=lambda: self.copy_preview_image(preview_path),
            font=self.base_font
        )
        menu.add_command(
            label="另存为图片文件",
            command=lambda: self.save_preview_image_as(preview_path),
            font=self.base_font
        )
        menu.add_separator()
        menu.add_command(
            label="删除图片文件",
            command=lambda: self.delete_preview_image(preview_path),
            font=self.base_font
        )
        
        menu.post(event.x_root, event.y_root)

    def copy_preview_image(self, preview_path):
        """复制预览图文件到剪贴板"""
        try:
            # 复制文件到剪贴板
            if platform.system() == 'Windows':
                cmd = f'powershell.exe Set-Clipboard -Path "{preview_path}"'
                subprocess.run(cmd, shell=True)
                self.show_popup_message("预览图文件已复制到剪贴板")
            else:
                self.show_popup_message("当前系统不支持复制文件到剪贴板")
        except Exception as e:
            self.show_popup_message(f"复制预览图文件失败：{str(e)}")

    def save_preview_image_as(self, preview_path):
        """另存为预览图文件"""
        try:
            # 获取原始文件扩展名
            ext = os.path.splitext(preview_path)[1]
            
            # 打开文件保存对话框
            file_path = filedialog.asksaveasfilename(
                defaultextension=ext,
                filetypes=[
                    ("PNG图片", "*.png"),
                    ("JPEG图片", "*.jpg;*.jpeg"),
                    ("所有文件", "*.*")
                ],
                initialfile=os.path.basename(preview_path)
            )
            
            if file_path:
                shutil.copy2(preview_path, file_path)
                self.show_popup_message("预览图已保存")
        except Exception as e:
            self.show_popup_message(f"保存预览图失败：{str(e)}")

    def delete_preview_image(self, preview_path):
        """删除预览图文件"""
        if not messagebox.askyesno("确认", "是否要删除当前预览图？此操作不可撤销。"):
            return
        
        try:
            os.remove(preview_path)
            
            # 清除预览图缓存
            self.load_thumbnail.cache_clear()
            self._preview_exists_cache.clear()
            
            # 刷新预览图显示
            self.preview_label.configure(image='')
            self.preview_label.image = None
            self.preview_image = None
            
            # 刷新缩略图显示
            if self.current_file in self.file_frames:
                self.refresh_thumbnail(
                    os.path.basename(self.current_file),
                    os.path.dirname(self.current_file)
                )
            
            self.show_popup_message("预览图已删除")

            self.refresh_files()
        except Exception as e:
            self.show_popup_message(f"删除预览图失败：{str(e)}")

class FileSystemCache:
    def __init__(self):
        self.file_info_cache = {}
        self.dir_content_cache = {}
        self.cache_time = {}
        self.cache_lifetime = 300  # 缓存有效期(秒)

    def get_file_info(self, file_path):
        current_time = time.time()
        if file_path in self.file_info_cache:
            cache_time = self.cache_time.get(file_path, 0)
            if current_time - cache_time < self.cache_lifetime:
                return self.file_info_cache[file_path]

        try:
            stat = os.stat(file_path)
            info = {
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'exists': True
            }
            self.file_info_cache[file_path] = info
            self.cache_time[file_path] = current_time
            return info
        except:
            return None

    def get_dir_content(self, dir_path):
        current_time = time.time()
        if dir_path in self.dir_content_cache:
            cache_time = self.cache_time.get(dir_path, 0)
            if current_time - cache_time < self.cache_lifetime:
                return self.dir_content_cache[dir_path]

        try:
            content = os.listdir(dir_path)
            self.dir_content_cache[dir_path] = content
            self.cache_time[dir_path] = current_time
            return content
        except:
            return []

    def clear(self):
        self.file_info_cache.clear()
        self.dir_content_cache.clear()
        self.cache_time.clear()

if __name__ == "__main__":
    import os
    import sys

    # 设置 Windows DPI 感知
    try:
        if os.name == 'nt':  # Windows 系统
            # 尝试使用 Per Monitor V2 - 最新的 DPI 感知模式
            awareness = ctypes.c_int()
            errorCode = ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
            
            if errorCode == 0:  # 成功获取当前 DPI 感知状态
                # 如果不是 Per Monitor V2，则设置为 Per Monitor V2
                if awareness.value != 2:  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)
            else:
                # 如果 GetProcessDpiAwareness 失败，直接尝试设置
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
                
            # 设置 DPI 缩放
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception as e:
        logging.warning(f"设置 DPI 感知时发生错误: {str(e)}")

    def _discover_tkdnd_path():
        """发现 tkdnd 路径"""
        if getattr(sys, 'frozen', False):
            # 如果是打包后的可执行文件
            base_dir = sys._MEIPASS
            tkdnd_path = os.path.join(base_dir, 'tkdnd')
            if os.path.exists(tkdnd_path):
                return tkdnd_path
        return None

    # 在创建主窗口之前设置 tkdnd 路径
    tkdnd_path = _discover_tkdnd_path()
    if tkdnd_path:
        os.environ['TKDND_LIBRARY'] = tkdnd_path
    
    # 创建主窗口
    root = TkinterDnD.Tk()
    
    # 设置主窗口宽度和高度
    window_width = 1300  # 设置窗口宽度
    window_height = 950  # 设置窗口高度
    print(f"窗口宽度: {window_width}")
    print(f"窗口高度: {window_height}")

    # 获取屏幕宽度和高度
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    print(f"屏幕宽度: {screen_width}")
    print(f"屏幕高度: {screen_height}")

    # 计算窗口的初始位置
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)

    # 设置窗口属性
    root.title("月光AI宝盒-模型管理器")
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # 创建应用例
    app = SafetensorsViewer(root)
    
    # 启动主循环
    root.mainloop()