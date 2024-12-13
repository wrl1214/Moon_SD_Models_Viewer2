import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
import json
import os
import shutil
from datetime import datetime
from PIL import Image, ImageTk
from io import BytesIO
import struct
import zlib

class WorkflowManager(ttk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.main_app = main_app
        self.workflows = {}
        self.current_workflow = None
        
        # 添加当前筛选器集合
        self.current_filters = set()  # 使用集合存储当前选中的筛选器
        
        # 使用主应用的样式和字体
        self.style = main_app.style
        self.base_font = main_app.base_font
        self.base_title_font = main_app.base_title_font
        
        # 获取DPI缩放系数
        self.dpi_scale = main_app.dpi_scale
        
        # 设置预览图尺寸
        self.base_preview_size = int(450 / (self.dpi_scale ** (7/24)))
        self.base_thumbnail_size = int(60 / (self.dpi_scale ** (1/4)))
        self.thumbnail_size = (self.base_thumbnail_size, self.base_thumbnail_size)
        
        # 设置工作流目录和信息文件路径
        self.workflow_dir = os.path.join(os.getcwd(), 'my_workflows')
        self.workflow_info_file = 'workflow_info.json'
        os.makedirs(self.workflow_dir, exist_ok=True)
        
        self.default_preview = None
        self.list_preview = None
        self.load_default_preview()
        
        # 设置支持的文件类型
        self.supported_image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
        
        # 添加自动保存定时器
        self.save_timer = None
        
        # 加载收藏图标
        self.favorite_icon = None
        try:
            favorite_image = Image.open(os.path.join('ui', 'favorite.png'))
            if favorite_image.mode != 'RGBA':
                favorite_image = favorite_image.convert('RGBA')
            # 调整收藏图标大小为缩略图的1/3
            favorite_icon_size = (self.thumbnail_size[0] // 3, self.thumbnail_size[1] // 3)
            favorite_image = favorite_image.resize(favorite_icon_size, Image.LANCZOS)
            self.favorite_icon = ImageTk.PhotoImage(favorite_image)
        except Exception as e:
            print(f"加载收藏图标失败: {str(e)}")
            self.favorite_icon = None
        
        # 添加搜索定时器
        self.search_timer = None
        
        self.setup_ui()
        self.load_workflows()
        
        # 绑定上下键
        self.bind_all("<Up>", self.select_previous_workflow)
        self.bind_all("<Down>", self.select_next_workflow)

    def setup_ui(self):
        """设置界面"""
        # 使用 PanedWindow 分割左右区域
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 设置左右框架
        self.setup_left_frame()
        self.setup_right_frame()
        
        # 添加框架到 PanedWindow
        self.paned_window.add(self.left_frame)
        self.paned_window.add(self.right_frame)
        
        # 绑定窗口大小变化事件
        self.bind('<Configure>', self.on_window_configure)

    def on_window_configure(self, event):
        """处理窗口大小变化"""
        if event.widget == self:
            # 获取当前分隔线位置
            current_sash = self.paned_window.sashpos(0)
            # 如果分隔线位置小于最小宽度，重置为最小宽度
            if current_sash < 350:
                self.paned_window.sashpos(0, 350)

    def setup_left_frame(self):
        """设置左侧框架"""
        self.left_frame = ttk.Frame(self.paned_window)
        self.left_frame.configure(width=350)  # 设置最小宽度
        
        # 创建工作流选择标签框
        workflow_selection_frame = ttk.LabelFrame(
            self.left_frame, 
            text="工作流选择", 
            style='primary.TLabelframe'
        )
        workflow_selection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 搜索和筛选区域
        control_frame = ttk.Frame(workflow_selection_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 显示当前根目录
        self.root_dir_label = ttk.Label(
            control_frame,
            text="",  # 初始为空，稍后更新
            font=self.base_font,
            wraplength=0,  # 禁用自动换行
            anchor='w'  # 左对齐
        )
        self.root_dir_label.pack(fill=tk.X, pady=(0, 5))
        
        # 第一行：根目录和刷新按钮
        first_row = ttk.Frame(control_frame)
        first_row.pack(fill=tk.X, pady=(0, 5))
        first_row.columnconfigure(0, weight=1)  # 让第一列（根目录按钮）占据剩余空间
        
        # 更改根目录按钮
        ttk.Button(
            first_row,
            text="更改根目录",
            style='info.TButton',
            command=self.change_workflow_dir
        ).grid(row=0, column=0, sticky='ew', padx=(0, 5))
        
        # 刷新按钮
        ttk.Button(
            first_row,
            text="刷新",
            width=6,  # 固定宽度
            style='info.TButton',
            command=self.refresh_workflows
        ).grid(row=0, column=1)
        
        # 第二行：搜索区域
        search_frame = ttk.Frame(control_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(
            search_frame, 
            text="搜索:",
            font=self.base_font
        ).pack(side=tk.LEFT)
        
        # 搜索框
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.search_workflows)
        self.search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=self.base_font,
            width=10
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 清除按钮
        ttk.Button(
            search_frame,
            text="×",
            width=2,
            style='info.TButton',
            command=self.clear_search
        ).pack(side=tk.LEFT, padx=(0, 0))
        
        # 排序按钮
        ttk.Button(
            search_frame,
            text="排序",
            width=6,  # 与刷新按钮相同的宽度
            style='info.TButton',
            command=lambda: None  # 暂时不实现功能
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # 排序按钮区域
        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(fill=tk.X)
        
        # 创建排序按钮容器
        self.button_container = ttk.Frame(filter_frame)
        self.button_container.pack(fill=tk.X)
        
        # 初始化筛选按钮字典
        self.filter_buttons = {}
        
        # 创建初始筛选按钮
        self.update_filter_buttons()
        
        # 工作流列表区域
        workflow_list_frame = ttk.LabelFrame(
            self.left_frame,
            text="工作流列表",
            style='primary.TLabelframe'
        )
        workflow_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 统计信息
        self.stats_label = ttk.Label(
            workflow_list_frame,
            text="",
            font=self.base_font
        )
        self.stats_label.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建列表滚动区域
        list_container = ttk.Frame(workflow_list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建画布和滚动条
        self.canvas = tk.Canvas(
            list_container,
            bg=self.style.colors.bg,
            highlightthickness=0,
            width=300,
            height=400
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定鼠标滚轮事件到画布
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        
        scrollbar = ttk.Scrollbar(
            list_container,
            orient="vertical",
            command=self.canvas.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建可滚动框架
        self.scrollable_frame = ttk.Frame(self.canvas, style='List.TFrame')
        
        # 创建画布窗口，添加内边距
        self.canvas_window = self.canvas.create_window(
            (0, 5),  # 添加顶部内边距
            window=self.scrollable_frame,
            anchor="nw",
            width=280,
            tags="frame"
        )
        
        # 配置画布滚动
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # 更新滚动区域
        def update_scroll_region(event=None):
            # 确保滚动区域至少有一个屏幕高度
            min_height = self.canvas.winfo_height()
            actual_height = self.scrollable_frame.winfo_height() + 10
            scroll_height = max(min_height, actual_height)
            self.canvas.configure(scrollregion=(0, 0, 0, scroll_height))
        
        self.scrollable_frame.bind("<Configure>", update_scroll_region)
        
        # 绑定画布大小变化事件
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # 设置最小宽度
        self.left_frame.update()
        min_width = 350
        if self.left_frame.winfo_width() < min_width:
            self.left_frame.configure(width=min_width)

    def setup_right_frame(self):
        """设置右侧框架"""
        self.right_frame = ttk.Frame(self.paned_window, width=540)
        
        # 创建主要内容区域
        title_frame = ttk.LabelFrame(self.right_frame, text="工作流详情", style='primary.TLabelframe')
        title_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        content_frame = ttk.Frame(title_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # 预览图区域
        preview_frame = ttk.Frame(content_frame, style='Border.TFrame')
        preview_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)
        
        # 预览图容器
        preview_container = tk.Frame(
            preview_frame,
            width=self.base_preview_size,  # 使基于DPI的尺寸
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
        self.preview_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # 添加点击事件绑定
        self.preview_label.bind("<Button-1>", self.show_full_preview)
        self.preview_label.bind("<Enter>", lambda e: self.preview_label.configure(cursor="hand2"))
        self.preview_label.bind("<Leave>", lambda e: self.preview_label.configure(cursor=""))
        
        # 添加右键菜单绑定
        self.preview_label.bind("<Button-3>", self.show_preview_menu)
        
        # 工作流信息区域
        info_frame = ttk.Frame(content_frame, style='Border.TFrame')
        info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建一个固定高度的容器框架
        info_container = ttk.Frame(info_frame)
        info_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 设置固定高度
        info_container.configure(height=150)
        info_container.pack_propagate(False)
        
        # 信息框架
        self.info_frame = ttk.Frame(info_container)
        self.info_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建工作流信息输入框
        self.workflow_name = self.create_info_entry("工作流名称", with_button=True, button_text="保存", button_command=self.save_workflow_name)
        self.workflow_info = self.create_info_entry("基础信息", is_readonly=True, with_button=True, button_text="路径", button_command=self.open_workflow_path)
        self.workflow_hash = self.create_info_entry("哈希值", is_readonly=True, with_button=True, button_text="复制", button_command=self.copy_workflow_hash)
        self.workflow_type = self.create_info_entry("工作流类型", is_context_menu=True, with_button=True)
        self.workflow_url = self.create_info_entry("工作流网址", is_context_menu=True, with_button=True, button_text="前往", button_command=self.open_url)
        self.workflow_desc = self.create_info_entry("工作流描述", is_context_menu=True, with_button=True, button_text="详情", button_command=self.show_full_description)
        
        # 操作按钮区域
        operation_frame = ttk.Frame(content_frame, style='Border.TFrame')
        operation_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)

        button_frame = ttk.Frame(operation_frame)
        button_frame.pack(fill=tk.X, expand=False, padx=5)
        
        for i in range(6):
            button_frame.columnconfigure(i, weight=1)
        
        # 添加收藏按钮
        self.favorite_btn = ttk.Button(
            button_frame,
            text="收藏工作流",  # 默认文本
            style='warning.TButton',  # 使用 warning 样式
            command=self.toggle_current_favorite
        )
        self.favorite_btn.grid(row=0, column=0, padx=5, pady=(0, 5), sticky='nsew')
        
        # 修改第二个按钮为"复制json"
        copy_json_btn = ttk.Button(
            button_frame,
            text="复制json",
            style='warning.TButton',
            command=self.copy_workflow_json
        )
        copy_json_btn.grid(row=0, column=1, padx=5, pady=(0, 5), sticky='nsew')
        
        # 修改第三个按钮为"在网页打开"
        open_in_comfyui_btn = ttk.Button(
            button_frame,
            text="在网页打开",
            style='warning.TButton',
            command=self.open_in_comfyui
        )
        open_in_comfyui_btn.grid(row=0, column=2, padx=5, pady=(0, 5), sticky='nsew')
        
        # 添加其他占位按钮
        for i in range(3, 6):  # 从第4个按钮开始
            button = ttk.Button(
                button_frame,
                text=f"按钮{i+1}",
                state='disabled',
                style='warning.TButton'
            )
            button.grid(row=0, column=i, padx=5, pady=(0, 5), sticky='nsew')

    def create_info_entry(self, label_text, is_context_menu=False, is_readonly=False, with_button=False, button_text="", button_command=None):
        """创建信息输入框"""
        frame = ttk.Frame(self.info_frame)
        frame.pack(fill=tk.X, padx=5, pady=5)
        
        label = ttk.Label(
            frame, 
            text=label_text + ":", 
            font=self.base_font,
            width=10,
            anchor='w'
        )
        label.pack(side=tk.LEFT, padx=(0, 5))
        
        input_container = ttk.Frame(frame)
        input_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        if label_text == "基础信息" or label_text == "哈希值":  # 只读字段
            entry = ttk.Entry(input_container, font=self.base_font)
            entry.pack(fill=tk.X)
            entry.configure(state='readonly')
        else:
            if label_text == "工作流描述":
                entry = tk.Text(
                    input_container,
                    font=self.base_font,
                    width=20,
                    wrap='word'
                )
                entry.pack(fill=tk.BOTH, expand=True)
                
                # 修改 Text 组件的绑定方式
                def on_text_modified(event):
                    entry.edit_modified(False)  # 重置修改标志
                    self.schedule_save(label_text)
                
                entry.bind("<<Modified>>", on_text_modified)
            else:
                entry = ttk.Entry(input_container, font=self.base_font)
                entry.pack(fill=tk.X)
                # 只为非工作流名称的字段绑定自动保存
                if label_text != "工作流名称":
                    entry.bind('<KeyRelease>', lambda e: self.schedule_save(label_text))
        
            # 为非只读字段添加右键菜单
            menu = self.create_context_menu(entry)
            entry.bind('<Button-3>', lambda e: self.show_context_menu(e, menu))
        
        if with_button:
            if label_text == "工作流类型":
                # 为工作流类型添加"同类"按钮
                button = ttk.Button(
                    frame,
                    text="同类",
                    command=lambda: self.search_var.set(entry.get("1.0", tk.END).strip() if isinstance(entry, tk.Text) else entry.get().strip()),
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
        
        return entry

    # 以下是必要的辅助方法
    def create_context_menu(self, widget):
        """创建右键菜单"""
        menu = tk.Menu(self.master, tearoff=0, font=self.base_font)
        menu.add_command(label="粘贴并替换", command=lambda: self.paste_and_replace_text(widget))
        menu.add_command(label="粘贴", command=lambda: self.paste_text(widget))
        menu.add_command(label="复制", command=lambda: self.copy_text(widget))
        menu.add_separator()
        menu.add_command(label="清空", command=lambda: self.clear_text(widget))
        return menu

    def show_context_menu(self, event, menu):
        """显示右键菜单"""
        menu.post(event.x_root, event.y_root)

    def copy_text(self, widget):
        """复制文本"""
        if isinstance(widget, tk.Text):
            text = widget.get("1.0", tk.END).strip()
        else:
            text = widget.get()
        if text:
            self.master.clipboard_clear()
            self.master.clipboard_append(text)

    def paste_text(self, widget):
        """粘贴文本"""
        try:
            text = self.master.clipboard_get()
            if isinstance(widget, tk.Text):
                widget.insert(tk.INSERT, text)
                # 触发自动保存
                if widget == self.workflow_desc:
                    self.schedule_save("工作流描述")
                elif widget == self.workflow_type:
                    self.schedule_save("工作流类型")
                elif widget == self.workflow_url:
                    self.schedule_save("工作流网址")
            elif isinstance(widget, ttk.Entry):
                widget.configure(state='normal')
                widget.insert(tk.INSERT, text)
                if widget == self.workflow_name:
                    self.save_workflow_name()
                elif widget == self.workflow_type:
                    self.schedule_save("工作流类型")
                elif widget == self.workflow_url:
                    self.schedule_save("工作流网址")
        except:
            pass

    def clear_text(self, widget):
        """清空文本"""
        if isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
            # 触发自动保存
            if widget == self.workflow_desc:
                self.schedule_save("工作流描述")
            elif widget == self.workflow_type:
                self.schedule_save("工作流类型")
            elif widget == self.workflow_url:
                self.schedule_save("工作流网址")
        elif isinstance(widget, ttk.Entry):
            widget.configure(state='normal')
            widget.delete(0, tk.END)
            if widget == self.workflow_name:
                # 工作流名称不需要自动保存，也不需要检查是否为空
                pass
            else:
                if widget == self.workflow_type:
                    self.schedule_save("工作流类型")
                elif widget == self.workflow_url:
                    self.schedule_save("工作流网址")

    def on_frame_configure(self, event=None):
        """配置画布滚动区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """处理画布大小变化"""
        # 更新内容框架的宽度以匹配画布
        self.canvas.itemconfig(
            self.canvas.find_withtag("all")[0],
            width=event.width - 4
        )

    def load_workflows(self):
        """加载工作流数据"""
        self.workflows = {}
        
        # 先加载保存的工作流信息
        saved_info = {}
        if os.path.exists(self.workflow_info_file):
            try:
                with open(self.workflow_info_file, 'r', encoding='utf-8') as f:
                    saved_info = json.load(f)
                    # 如果有保存的根目录，更新当前根目录
                    if '_root_dir' in saved_info:
                        self.workflow_dir = saved_info['_root_dir']
            except Exception as e:
                print(f"加载工作流信息文件失败: {str(e)}")
        
        # 更新根目录显示
        self.root_dir_label.configure(text=self.workflow_dir)
        
        # 递归扫描目录
        for root, dirs, files in os.walk(self.workflow_dir):
            # 处理当前目录下的json、png和svg文件
            for file_name in files:
                if file_name.endswith(('.json', '.png', '.svg')):
                    workflow_path = os.path.join(root, file_name)
                    
                    try:
                        # 读取工作流文件内容
                        if file_name.endswith('.json'):
                            with open(workflow_path, 'r', encoding='utf-8') as f:
                                workflow_data = json.load(f)
                            preview_image = None
                        else:  # PNG或SVG文件
                            # 尝试从文件中提取JSON数据
                            with open(workflow_path, 'rb') as f:
                                data = f.read()
                            
                            # 查找JSON数据
                            workflow_data = {'nodes': [], 'links': []}  # 默认空工作流数据
                            start_marker = b'{"last_node_id":'
                            start_pos = data.find(start_marker)
                            
                            if start_pos == -1 and file_name.endswith('.svg'):
                                # 对于SVG文件，尝试查找转义后的JSON开始标记
                                start_marker = b'%7B%22last_node_id%22%3A'
                                start_pos = data.find(start_marker)
                                if start_pos != -1:
                                    # 将URL编码的数据解码为普通JSON
                                    from urllib.parse import unquote
                                    encoded_data = data[start_pos:].split(b'"')[0]
                                    json_str = unquote(encoded_data.decode('ascii'))
                                    workflow_data = json.loads(json_str)
                                else:
                                    # 再尝试查找HTML转义的JSON开始标记
                                    start_marker = b'{"amp;last_node_id":'
                                    start_pos = data.find(start_marker)
                                    if start_pos != -1:
                                        json_bytes = data[start_pos:]
                                        # 找到JSON的结束位置
                                        brace_count = 0
                                        end_pos = 0
                                        i = 0
                                        while i < len(json_bytes):
                                            byte = json_bytes[i:i+1]
                                            if byte == b'{':
                                                brace_count += 1
                                            elif byte == b'}':
                                                brace_count -= 1
                                                if brace_count == 0:
                                                    end_pos = i + 1
                                                    break
                                            i += 1
                                        
                                        if end_pos > 0:
                                            json_data = json_bytes[:end_pos]
                                            try:
                                                json_str = json_data.decode('utf-8')
                                                # 处理HTML转义字符
                                                json_str = json_str.replace('&amp;', '&')
                                                json_str = json_str.replace('&quot;', '"')
                                                json_str = json_str.replace('&lt;', '<')
                                                json_str = json_str.replace('&gt;', '>')
                                                workflow_data = json.loads(json_str)
                                            except UnicodeDecodeError:
                                                json_str = json_data.decode('latin1')
                                                workflow_data = json.loads(json_str)
                            
                            elif start_pos != -1:  # PNG文件或未编码的SVG文件
                                json_bytes = data[start_pos:]
                                brace_count = 0
                                end_pos = 0
                                i = 0
                                while i < len(json_bytes):
                                    byte = json_bytes[i:i+1]
                                    if byte == b'{':
                                        brace_count += 1
                                    elif byte == b'}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            end_pos = i + 1
                                            break
                                    i += 1
                                
                                if end_pos > 0:
                                    json_data = json_bytes[:end_pos]
                                    try:
                                        json_str = json_data.decode('utf-8')
                                    except UnicodeDecodeError:
                                        json_str = json_data.decode('latin1')
                                    workflow_data = json.loads(json_str)
                            
                            # 加载预览图（仅PNG文件）
                            preview_image = Image.open(workflow_path) if file_name.endswith('.png') else None
                        
                        # 计算哈希值作为唯一ID
                        workflow_hash = self.calculate_workflow_hash(workflow_path)
                        
                        # 提取工作流的基本信息
                        workflow_info = {
                            'name': os.path.splitext(file_name)[0],  # 默认使用文件名作为显示名称
                            'description': '',  # 描述默认为空，由用户手动录入
                            'type': '',
                            'url': '',
                            'created_date': datetime.fromtimestamp(
                                os.path.getctime(workflow_path)
                            ).strftime("%y-%m-%d %H:%M"),
                            'file_path': workflow_path,  # 保存完整路径
                            'folder': os.path.relpath(root, self.workflow_dir) if root != self.workflow_dir else "",
                            'nodes': workflow_data.get('nodes', []),
                            'connections': workflow_data.get('links', []),
                            'hash': workflow_hash,
                            'is_favorite': False  # 默认非收藏
                        }
                        
                        # 如果是PNG文件，创建预览图
                        if preview_image:
                            # 创建列表预览图
                            workflow_info['list_preview'] = self.resize_preview_image(
                                preview_image, 
                                self.thumbnail_size[0], 
                                self.thumbnail_size[1]
                            )
                            # 创建详情预览图
                            workflow_info['detail_preview'] = self.resize_preview_image(
                                preview_image,
                                self.base_preview_size,
                                self.base_preview_size
                            )
                        
                        # 如果有保存的信息，更新相关字段
                        if workflow_hash in saved_info:
                            saved_data = saved_info[workflow_hash]
                            workflow_info.update({
                                'name': saved_data.get('name', workflow_info['name']),
                                'description': saved_data.get('description', ''),
                                'type': saved_data.get('type', ''),
                                'url': saved_data.get('url', ''),
                                'is_favorite': saved_data.get('is_favorite', False)
                            })
                        
                        # 添加到工作流字典
                        self.workflows[workflow_hash] = workflow_info
                        
                    except Exception as e:
                        print(f"处理文件 {file_name} 时出错: {str(e)}")
                        continue
        
        # 保存更新后的信息
        self.save_workflow_info()
        
        # 刷新列表显示
        self.refresh_workflow_list()

    def save_workflow_info(self):
        """保存工作流信息到文件"""
        try:
            # 只保存需要持久化的信息
            save_data = {
                '_root_dir': self.workflow_dir  # 保存根目录
            }
            for workflow_hash, workflow in self.workflows.items():
                save_data[workflow_hash] = {
                    'name': workflow['name'],
                    'description': workflow['description'],
                    'type': workflow.get('type', ''),
                    'url': workflow.get('url', ''),
                    'is_favorite': workflow.get('is_favorite', False)
                }
            
            with open(self.workflow_info_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存工作流信息失败: {str(e)}")

    def refresh_workflow_list(self):
        """刷新工作流列表"""
        # 清空现有列表
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # 获取搜索词
        search_term = self.search_var.get().lower()
        
        # 用于存储符合条件的工作流
        filtered_workflows = []
        
        # 筛选工作流
        for workflow_hash, workflow in self.workflows.items():
            show_workflow = True
            
            # 检查搜索词 - 支持多字段搜索
            if search_term:
                searchable_fields = [
                    workflow['name'].lower(),
                    workflow.get('folder', '').lower(),
                    workflow.get('type', '').lower()
                ]
                if not any(search_term in field for field in searchable_fields):
                    show_workflow = False
            
            # 检查筛选条件
            if show_workflow and self.current_filters:
                filter_type = next(iter(self.current_filters))
                if filter_type == "收藏":
                    show_workflow = workflow.get('is_favorite', False)
                elif filter_type == "其他":
                    show_workflow = workflow.get('folder', '') == ""
                else:  # 文件夹筛选
                    show_workflow = workflow.get('folder', '') == filter_type
            
            # 如果通过所有检查，添加到筛选结果
            if show_workflow:
                filtered_workflows.append((workflow_hash, workflow))
        
        # 更新统计信息
        if search_term:
            self.stats_label.configure(text=f"搜索结果：{len(filtered_workflows)} 个工作流")
        elif self.current_filters:
            filter_type = next(iter(self.current_filters))
            if filter_type == "收藏":
                self.stats_label.configure(text=f"收藏：{len(filtered_workflows)} 个工作流")
            elif filter_type == "其他":
                self.stats_label.configure(text=f"根目录：{len(filtered_workflows)} 个工作流")
            else:
                self.stats_label.configure(text=f"文件夹 {filter_type}：{len(filtered_workflows)} 个工作流")
        else:
            # 没有筛选时显示全部工作流数量
            self.stats_label.configure(text=f"共 {len(filtered_workflows)} 个工作流")
        
        # 显示筛选后的工作流
        for workflow_hash, workflow in filtered_workflows:
            self.create_workflow_entry(workflow_hash, workflow)
        
        def update_selection():
            # 如果有工作流，选中第一个
            if filtered_workflows:
                first_workflow_hash = filtered_workflows[0][0]
                self.select_workflow(first_workflow_hash)
                # 滚动到顶部
                self.canvas.yview_moveto(0)
            else:
                # 如果没有工作流，清除当前选中状态
                self.current_workflow = None
                self.update_workflow_detail()
        
        # 使用延时确保界面元素已完全创建
        self.after(100, update_selection)

    def create_workflow_entry(self, workflow_hash, workflow):
        """创建工作流列表项"""
        # 创建主框架
        frame = ttk.Frame(self.scrollable_frame)
        frame.pack(fill=tk.X, padx=5, pady=2)
        
        # 创建内容框架
        content_frame = ttk.Frame(frame)
        content_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建预览图和文本的容器
        preview_text_frame = ttk.Frame(content_frame)
        preview_text_frame.pack(fill=tk.X, expand=True)
        
        # 添加小预览图
        thumbnail_label = None
        if workflow.get('list_preview'):  # 优先使用工作流自带的预览图
            preview_image = workflow['list_preview']
        elif self.list_preview:  # 否则使用默认预览图
            preview_image = self.list_preview
        else:
            preview_image = None

        if preview_image:
            preview_container = ttk.Frame(
                preview_text_frame, 
                width=self.thumbnail_size[0],
                height=self.thumbnail_size[1]
            )
            preview_container.pack(side=tk.LEFT, padx=(0, 10))
            preview_container.pack_propagate(False)
            
            # 创建预览图标签
            thumbnail_label = ttk.Label(
                preview_container,
                image=preview_image,
                style='List.TLabel'
            )
            thumbnail_label.place(relx=0.5, rely=0.5, anchor="center")
            
            # 如果是收藏的工作流，添加收藏图标
            if workflow.get('is_favorite', False) and self.favorite_icon:
                favorite_label = tk.Label(
                    thumbnail_label,
                    image=self.favorite_icon,
                    bg=self.style.colors.bg,
                    bd=0,
                    highlightthickness=0
                )
                favorite_label.place(x=2, y=2)
        
        # 创建文本容器
        text_container = ttk.Frame(preview_text_frame)
        text_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建路径容器
        path_container = ttk.Frame(text_container)
        path_container.pack(fill=tk.X)
        
        # 构建路径显示文本
        path_text = workflow.get('folder', '')
        if not path_text:  # 如果路径为空，显示"根目录"
            path_text = "根目录"
        
        # 添加"路径:"前缀
        path_label = ttk.Label(
            path_container,
            text=f"路径: {path_text}",  # 添加前缀
            font=self.base_font,
            style='List.TLabel',
            anchor='w'
        )
        path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 创建名称容器
        name_container = ttk.Frame(text_container)
        name_container.pack(fill=tk.X)
        
        # 添加"名称:"前缀
        name_label = ttk.Label(
            name_container,
            text=f"名称: {workflow['name']}",  # 添加前缀
            font=self.base_font,
            style='List.TLabel',
            anchor='w'
        )
        name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 直接添加分隔线，不使用延时
        separator = ttk.Separator(frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(5, 0))
        
        # 保存所有需要更新样式的组件
        frame.style_widgets = [
            frame, content_frame, preview_text_frame, text_container, 
            path_container, path_label, name_container, name_label,
            thumbnail_label, separator
        ]
        frame.workflow_hash = workflow_hash
        
        # 绑定点击事件
        for widget in frame.style_widgets:
            if widget:
                widget.bind("<Button-1>", lambda e, wid=workflow_hash: self.select_workflow(wid))
                widget.bind("<Button-3>", lambda e, wid=workflow_hash: self.show_workflow_menu(e, wid))
                widget.bind("<Enter>", lambda e: e.widget.configure(cursor="hand2"))
                widget.bind("<Leave>", lambda e: e.widget.configure(cursor=""))
        
        # 如果是当前选中的工作流，应用选中样式
        if self.current_workflow and workflow_hash == self.current_workflow.get('hash'):
            self.apply_selected_style(frame)
        else:
            self.apply_normal_style(frame)

    def select_workflow(self, workflow_hash):
        """选择工作流"""
        # 取消之前选中项的样式
        for widget in self.scrollable_frame.winfo_children():
            if hasattr(widget, 'workflow_hash'):
                self.apply_normal_style(widget)
        
        # 设置新的选中项
        self.current_workflow = self.workflows.get(workflow_hash)
        if self.current_workflow:
            # 找到并应用选中样式
            for widget in self.scrollable_frame.winfo_children():
                if hasattr(widget, 'workflow_hash') and widget.workflow_hash == workflow_hash:
                    self.apply_selected_style(widget)
                    break
            
            # 更新详情显示
            self.update_workflow_detail()

    def apply_selected_style(self, frame):
        """应用选中样式"""
        for widget in frame.style_widgets:
            if widget:
                if isinstance(widget, ttk.Label):
                    widget.configure(style='Selected.TLabel')
                elif isinstance(widget, ttk.Frame):
                    widget.configure(style='Selected.TFrame')
        
        # 恢复收藏图标
        if hasattr(frame, 'favorite_label') and frame.favorite_label:
            frame.favorite_label.lift()

    def apply_normal_style(self, frame):
        """应用普通样式"""
        for widget in frame.style_widgets:
            if widget:
                if isinstance(widget, ttk.Label):
                    widget.configure(style='List.TLabel')
                elif isinstance(widget, ttk.Frame):
                    widget.configure(style='List.TFrame')
        
        # 恢复收藏图标
        if hasattr(frame, 'favorite_label') and frame.favorite_label:
            frame.favorite_label.lift()

    def update_workflow_detail(self):
        """更新工作流详情显示"""
        if not self.current_workflow:
            return
        
        # 更新基本信息
        self.workflow_name.delete(0, tk.END)
        self.workflow_name.insert(0, self.current_workflow['name'])
        
        # 获取文件的最后修改时间
        file_path = self.current_workflow['file_path']
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%y-%m-%d %H:%M")
        
        # 获取详情的最后修改时间
        detail_mtime = self.current_workflow.get('last_modified', self.current_workflow['created_date'])
        
        # 更新基础信息显示
        self.workflow_info.configure(state='normal')
        self.workflow_info.delete(0, tk.END)
        self.workflow_info.insert(0, f"详情修改: {detail_mtime} | 文件修改: {file_mtime}")
        self.workflow_info.configure(state='readonly')
        
        # 更新哈希值
        self.workflow_hash.configure(state='normal')
        self.workflow_hash.delete(0, tk.END)
        self.workflow_hash.insert(0, self.current_workflow.get('hash', ''))
        self.workflow_hash.configure(state='readonly')
        
        # 更新其他信息 (Text 组件)
        if isinstance(self.workflow_type, tk.Text):
            self.workflow_type.delete("1.0", tk.END)
            self.workflow_type.insert("1.0", self.current_workflow.get('type', ''))
        else:
            self.workflow_type.delete(0, tk.END)
            self.workflow_type.insert(0, self.current_workflow.get('type', ''))
        
        if isinstance(self.workflow_url, tk.Text):
            self.workflow_url.delete("1.0", tk.END)
            self.workflow_url.insert("1.0", self.current_workflow.get('url', ''))
        else:
            self.workflow_url.delete(0, tk.END)
            self.workflow_url.insert(0, self.current_workflow.get('url', ''))
        
        if isinstance(self.workflow_desc, tk.Text):
            self.workflow_desc.delete("1.0", tk.END)
            self.workflow_desc.insert("1.0", self.current_workflow.get('description', ''))
        else:
            self.workflow_desc.delete(0, tk.END)
            self.workflow_desc.insert(0, self.current_workflow.get('description', ''))
        
        # 更新预览图
        if self.current_workflow.get('detail_preview'):  # 优先使用工作流自带的预览图
            preview_image = self.current_workflow['detail_preview']
        elif self.default_preview:  # 否则使用默认预览图
            preview_image = self.default_preview
        else:
            preview_image = None

        if preview_image:
            self.preview_label.configure(image=preview_image)
        
        # 更新收藏按钮状态和文本
        if self.current_workflow.get('is_favorite', False):
            self.favorite_btn.configure(text="取消收藏")
        else:
            self.favorite_btn.configure(text="收藏工作流")

    def update_stats_label(self):
        """更新统计信息"""
        if not self.current_filters:
            # 没有筛选器时显示总数
            total_count = len(self.workflows)
            self.stats_label.configure(text=f"共 {total_count} 个工作流")
        else:
            # 根据筛选条件统计数量
            filter_type = next(iter(self.current_filters))
            filtered_count = 0
            
            for workflow in self.workflows.values():
                if filter_type == "收藏" and workflow.get('is_favorite', False):
                    filtered_count += 1
                elif filter_type == "其他" and workflow.get('folder', '') == "":
                    # "其他"表示根录下的工作流
                    filtered_count += 1
                elif filter_type == workflow.get('folder', ''):  # 文件夹筛选
                    filtered_count += 1
            
            # 显示筛选后的数量
            if filter_type == "收藏":
                self.stats_label.configure(text=f"收藏：{filtered_count} 个工作流")
            elif filter_type == "其他":
                self.stats_label.configure(text=f"根目录：{filtered_count} 个工作流")
            else:
                self.stats_label.configure(text=f"文件夹 {filter_type}：{filtered_count} 个工作流")

    def search_workflows(self, *args):
        """处理搜索事件"""
        # 取消之前的定时器
        if self.search_timer:
            self.master.after_cancel(self.search_timer)
        
        # 设置新的定时器，300ms 后执行搜索
        self.search_timer = self.master.after(300, self.do_search)

    def do_search(self):
        """执行实际的搜索"""
        # 清除定时器引用
        self.search_timer = None
        
        # 刷新列表
        self.refresh_workflow_list()

    def clear_search(self):
        """清除搜索"""
        self.search_var.set("")
        self.search_entry.focus_set()

    def refresh_workflows(self):
        """刷新工作流列表"""
        self.load_workflows()
        self.main_app.show_popup_message("工作流列表已刷新")

    def copy_workflow_name(self):
        """复制工作流名称"""
        name = self.workflow_name.get()
        if name:
            self.master.clipboard_clear()
            self.master.clipboard_append(name)
            self.main_app.show_popup_message("工作流名称已复制")

    def open_workflow_path(self):
        """打开工作流文件路径并选中文件"""
        if not self.current_workflow:
            return
        
        # 使用与右键菜单相同的方法打开并选中文件
        self.open_and_select_file(self.current_workflow['file_path'])

    def open_url(self):
        """打开工作流网址"""
        if isinstance(self.workflow_url, tk.Text):
            url = self.workflow_url.get("1.0", tk.END).strip()
        else:
            url = self.workflow_url.get().strip()
        
        if url:
            import webbrowser
            webbrowser.open(url)

    def show_full_description(self):
        """显示完整描述"""
        if not self.current_workflow:
            return
        
        desc_window = tk.Toplevel(self.master)
        desc_window.title("工作流描述")
        desc_window.geometry("800x600")  # 设置初始大小
        
        # 设置窗口最小尺寸
        desc_window.minsize(600, 400)
        
        # 获取描述输入框的位置和大小
        desc_x = self.workflow_desc.winfo_rootx()
        desc_y = self.workflow_desc.winfo_rooty()
        desc_height = self.workflow_desc.winfo_height()
        
        # 计算弹出窗口的位置（在描述输入框的附近）
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
        current_desc = self.workflow_desc.get("1.0", tk.END).strip()
        text_widget.insert("1.0", current_desc)
        
        def on_closing():
            """窗口关闭时的处理"""
            # 获取编辑后的内容
            new_desc = text_widget.get("1.0", tk.END).strip()
            
            # 更新主窗口的描述内容
            self.workflow_desc.delete("1.0", tk.END)
            self.workflow_desc.insert("1.0", new_desc)
            
            # 更新工作流信息并保存
            self.current_workflow['description'] = new_desc
            self.save_workflow_info()
            
            # 关闭窗口
            desc_window.destroy()
        
        # 绑定窗口关闭事件
        desc_window.protocol("WM_DELETE_WINDOW", on_closing)
        
        # 设置窗口状态
        desc_window.state('normal')
        
        # 添加最大化/还原按钮
        desc_window.resizable(True, True)

    def load_default_preview(self):
        """加载默认预览图"""
        try:
            # 使用 ui/null.png 作为默认预览图
            image_path = os.path.join('ui', 'null.png')
            if os.path.exists(image_path):
                image = Image.open(image_path)
                # 列表预览图尺寸
                self.list_preview = self.resize_preview_image(image, self.thumbnail_size[0], self.thumbnail_size[1])
                # 详情预览图尺寸
                self.default_preview = self.resize_preview_image(image, self.base_preview_size, self.base_preview_size)
        except Exception as e:
            print(f"加载默认预览图失败: {str(e)}")
            self.list_preview = None
            self.default_preview = None

    def resize_preview_image(self, image, width, height):
        """调整预览图大小"""
        # 计算缩放比例
        ratio = min(width / image.width, height / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        
        # 调整图片大小
        resized = image.resize(new_size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(resized) 

    def filter_workflows(self, filter_type):
        """筛选工作流"""
        # 如果点击当前选中的筛选器，取消选中
        if filter_type in self.current_filters:
            self.current_filters.clear()
            self.filter_buttons[filter_type].configure(style='primary.TButton')
        else:
            # 清除其他筛选器的选中状态
            for btn_text, btn in self.filter_buttons.items():
                btn.configure(style='primary.TButton')
            self.current_filters.clear()
            
            # 选中当前筛选器
            self.current_filters.add(filter_type)
            self.filter_buttons[filter_type].configure(style='secondary.TButton')
        
        self.refresh_workflow_list()

    def toggle_favorite(self, workflow_hash):
        """切换收藏状态"""
        if workflow_hash in self.workflows:
            self.workflows[workflow_hash]['is_favorite'] = not self.workflows[workflow_hash].get('is_favorite', False)
            self.save_workflow_info()
            self.refresh_workflow_list()

    def copy_workflow_hash(self):
        """复制工作流哈希值"""
        hash_value = self.workflow_hash.get()
        if hash_value:
            self.master.clipboard_clear()
            self.master.clipboard_append(hash_value)
            self.main_app.show_popup_message("希值已复制")

    def calculate_workflow_hash(self, workflow_path):
        """计算工作流文件的哈希值"""
        try:
            import hashlib
            with open(workflow_path, 'rb') as f:
                file_hash = hashlib.sha256()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
            return file_hash.hexdigest()
        except Exception as e:
            print(f"计算哈希值失败: {str(e)}")
            return ""

    def schedule_save(self, field_type):
        """计划保存更改"""
        if self.save_timer:
            self.master.after_cancel(self.save_timer)
        self.save_timer = self.master.after(500, lambda: self.save_field_change(field_type))

    def save_field_change(self, field_type):
        """保存字段更改"""
        if not self.current_workflow:
            return
        
        workflow_hash = self.current_workflow['hash']
        if workflow_hash not in self.workflows:
            return
        
        # 获取字段值
        if field_type == "工作流名称":
            new_value = self.workflow_name.get()
            field = 'name'
        elif field_type == "工作流类型":
            if isinstance(self.workflow_type, tk.Text):
                new_value = self.workflow_type.get("1.0", tk.END).strip()
            else:
                new_value = self.workflow_type.get().strip()
            field = 'type'
        elif field_type == "工作流网址":
            if isinstance(self.workflow_url, tk.Text):
                new_value = self.workflow_url.get("1.0", tk.END).strip()
            else:
                new_value = self.workflow_url.get().strip()
            field = 'url'
        elif field_type == "工作流描述":
            if isinstance(self.workflow_desc, tk.Text):
                new_value = self.workflow_desc.get("1.0", tk.END).strip()
            else:
                new_value = self.workflow_desc.get().strip()
            field = 'description'
        else:
            return
            
        
        # 更新工作流信息
        if self.workflows[workflow_hash].get(field) != new_value:
            self.workflows[workflow_hash][field] = new_value
            # 更新最后修改时间
            self.workflows[workflow_hash]['last_modified'] = datetime.now().strftime("%y-%m-%d %H:%M")
            self.save_workflow_info()
            
            # 更新基础信息显示
            self.update_workflow_detail()
            
            # 如果是名称变更，刷新列表显示
            if field == 'name':
                self.refresh_workflow_list()

    def save_workflow_name(self):
        """保存工作流名称并更新文件"""
        if not self.current_workflow:
            return
        
        workflow_hash = self.current_workflow['hash']
        if workflow_hash not in self.workflows:
            return
        
        new_name = self.workflow_name.get().strip()
        if not new_name:
            self.main_app.show_popup_message("工作流名称不能为空")
            return
        
        old_path = self.workflows[workflow_hash]['file_path']
        old_folder = os.path.dirname(old_path)
        # 保留原文件后缀名
        old_ext = os.path.splitext(old_path)[1]
        new_path = os.path.join(old_folder, f"{new_name}{old_ext}")
        
        try:
            # 检查新文件名是否已存在
            if os.path.exists(new_path) and old_path != new_path:
                self.main_app.show_popup_message("该名称已存在，请使用其他名称")
                return
            
            # 重命名文件
            os.rename(old_path, new_path)
            
            # 更新工作流信息
            self.workflows[workflow_hash]['name'] = new_name
            self.workflows[workflow_hash]['file_path'] = new_path
            
            # 重新计算哈希值
            new_hash = self.calculate_workflow_hash(new_path)
            
            # 更新哈希值
            if new_hash != workflow_hash:
                self.workflows[new_hash] = self.workflows[workflow_hash]
                self.workflows[new_hash]['hash'] = new_hash
                del self.workflows[workflow_hash]
                self.current_workflow = self.workflows[new_hash]
            
            # 保存更新后的信息
            self.save_workflow_info()
            
            # 刷新列表和详情显示
            self.refresh_workflow_list()
            self.update_workflow_detail()
            
            self.main_app.show_popup_message("工作流名称已保存")
            
        except Exception as e:
            self.main_app.show_popup_message(f"保存失败: {str(e)}")

    def toggle_current_favorite(self):
        """切换当前工作流的收藏状态"""
        if not self.current_workflow:
            return
        
        workflow_hash = self.current_workflow['hash']
        if workflow_hash not in self.workflows:
            return
        
        # 切换收藏状态
        self.workflows[workflow_hash]['is_favorite'] = not self.workflows[workflow_hash].get('is_favorite', False)
        is_favorite = self.workflows[workflow_hash]['is_favorite']
        
        # 更新按钮文本
        if is_favorite:
            self.favorite_btn.configure(text="取消收藏")
            self.main_app.show_popup_message("已添加到收藏")
        else:
            self.favorite_btn.configure(text="收藏工作流")
            self.main_app.show_popup_message("已取消收藏")
        
        # 保存更改
        self.save_workflow_info()
        
        # 更新列表中的收藏图标
        for frame in self.scrollable_frame.winfo_children():
            if hasattr(frame, 'workflow_hash') and frame.workflow_hash == workflow_hash:
                # 找到预览图容器
                for widget in frame.winfo_children():
                    if isinstance(widget, ttk.Frame):  # content_frame
                        for child in widget.winfo_children():
                            if isinstance(child, ttk.Frame):  # preview_text_frame
                                for preview in child.winfo_children():
                                    if isinstance(preview, ttk.Frame) and preview.winfo_width() == self.thumbnail_size[0]:  # preview_container
                                        thumbnail_label = preview.winfo_children()[0]  # thumbnail_label
                                        # 移除旧的收藏图标
                                        for old_icon in thumbnail_label.winfo_children():
                                            old_icon.destroy()
                                        # 如果是收藏状态，添加新的收藏图标
                                        if is_favorite and self.favorite_icon:
                                            favorite_label = tk.Label(
                                                thumbnail_label,
                                                image=self.favorite_icon,
                                                bg=self.style.colors.bg,
                                                bd=0,
                                                highlightthickness=0
                                            )
                                            favorite_label.place(x=2, y=2)
                                            favorite_label.bind("<Button-1>", lambda e, wid=workflow_hash: self.select_workflow(wid))
                                        return

    def on_thumbnail_enter(self, thumbnail_label):
        """鼠标进入缩略图"""
        thumbnail_label.configure(cursor="hand2")
        # 确保藏图标在最上层
        for child in thumbnail_label.winfo_children():
            child.lift()

    def on_thumbnail_leave(self, thumbnail_label):
        """鼠标离开缩略图"""
        thumbnail_label.configure(cursor="")

    def filter_by_type(self, type_value):
        """按类型筛选工作流"""
        if not type_value:
            self.main_app.show_popup_message("工作流类型为空")
            return
        
        # 清除所有筛选器的选中状态
        for btn in self.filter_buttons.values():
            btn.configure(style='primary.TButton')
        self.current_filters.clear()
        
        # 创建临时筛选函数
        def type_filter(workflow):
            return workflow.get('type', '').strip() == type_value
        
        # 统计符合条件的工作流数量
        filtered_count = sum(1 for workflow in self.workflows.values() if type_filter(workflow))
        
        # 更新统计信息
        self.stats_label.configure(text=f"类型 {type_value}：{filtered_count} 个工作流")
        
        # 刷新列表显示
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # 显示符合条件的工作流
        for workflow_hash, workflow in self.workflows.items():
            if type_filter(workflow):
                self.create_workflow_entry(workflow_hash, workflow)
        
        self.main_app.show_popup_message(f"已筛选出 {filtered_count} 个同工作流")

    def show_workflow_menu(self, event, workflow_hash):
        """显示工作流右键菜单"""
        # 先选中该工作流
        self.select_workflow(workflow_hash)
        
        menu = tk.Menu(self, tearoff=0, font=self.base_font)
        
        # 获取工作流信息
        workflow = self.workflows.get(workflow_hash)
        if not workflow:
            return
        
        # 收藏/取消收藏
        is_favorite = workflow.get('is_favorite', False)
        menu.add_command(
            label="取消收藏" if is_favorite else "收藏工作流",
            command=lambda: self.toggle_current_favorite()
        )
        
        # 打开路径并选中文件
        menu.add_command(
            label="打开路径",
            command=lambda: self.open_and_select_file(workflow['file_path'])
        )
        
        # 更新哈希
        menu.add_command(
            label="更新哈希",
            command=lambda: self.update_workflow_hash(workflow_hash)
        )
        
        menu.add_separator()
        
        # 移动工作流
        menu.add_command(
            label="移动工作流",
            command=lambda: self.move_workflow(workflow_hash)
        )
        
        # 复制工作流
        menu.add_command(
            label="复制工作流",
            command=lambda: self.copy_workflow(workflow_hash)
        )
        
        # 删除工作流
        menu.add_command(
            label="删除工作流",
            command=lambda: self.delete_workflow(workflow_hash)
        )
        
        # 显示菜单
        menu.post(event.x_root, event.y_root)

    def open_and_select_file(self, file_path):
        """打开路径并选中文件"""
        import subprocess
        # 确保使用完整路径
        abs_path = os.path.abspath(file_path)
        subprocess.run(['explorer', '/select,', abs_path])

    def update_workflow_hash(self, workflow_hash):
        """更新工作流哈希值"""
        workflow = self.workflows.get(workflow_hash)
        if not workflow:
            return
        
        # 计算新的哈希值
        new_hash = self.calculate_workflow_hash(workflow['file_path'])
        if new_hash == workflow_hash:
            self.main_app.show_popup_message("哈希值未发生变化")
            return
        
        # 更新哈希值
        self.workflows[new_hash] = workflow
        self.workflows[new_hash]['hash'] = new_hash
        del self.workflows[workflow_hash]
        
        # 如果是当前选中的工作流，更新引用
        if self.current_workflow and self.current_workflow.get('hash') == workflow_hash:
            self.current_workflow = self.workflows[new_hash]
        
        # 保存更改并刷新显示
        self.save_workflow_info()
        self.refresh_workflow_list()
        self.main_app.show_popup_message("哈希值已更新")

    def move_workflow(self, workflow_hash):
        """移动工作流"""
        workflow = self.workflows.get(workflow_hash)
        if not workflow:
            return
        
        # 创建文件夹选择对话框
        from tkinter import filedialog
        new_path = filedialog.askdirectory(
            title="选择目标文件夹",
            initialdir=self.workflow_dir
        )
        
        if not new_path:
            return
        
        try:
            # 构建新的文件路径
            file_name = os.path.basename(workflow['file_path'])
            new_file_path = os.path.join(new_path, file_name)
            
            # 检查目标路径是否存在同名文件
            if os.path.exists(new_file_path):
                self.main_app.show_popup_message("目标位置已存在同名文件")
                return
            
            # 移动文件
            shutil.move(workflow['file_path'], new_file_path)
            
            # 更新工作流信息
            workflow['file_path'] = new_file_path
            workflow['folder'] = os.path.relpath(new_path, self.workflow_dir) if new_path != self.workflow_dir else ""
            
            # 保存更改并刷新显示
            self.save_workflow_info()
            self.refresh_workflow_list()
            self.main_app.show_popup_message("工作流已移动")
            
        except Exception as e:
            self.main_app.show_popup_message(f"移动失败: {str(e)}")

    def copy_workflow(self, workflow_hash):
        """复制工作流"""
        workflow = self.workflows.get(workflow_hash)
        if not workflow:
            return
        
        try:
            # 构建新的文件名
            file_name = os.path.basename(workflow['file_path'])
            name, ext = os.path.splitext(file_name)
            new_name = f"{name}_copy{ext}"
            new_path = os.path.join(os.path.dirname(workflow['file_path']), new_name)
            
            # 读取原文件内容
            ext = ext.lower()
            if ext == '.png':
                # 如果是PNG文件，提取JSON数据
                with open(workflow['file_path'], 'rb') as f:
                    data = f.read()
                json_data = self.extract_json_from_png(data)
                if not json_data:
                    raise ValueError("无法从PNG文件提取工作流数据")
                
                # 修改JSON数据
                json_obj = json.loads(json_data)
                # 添加复制时间戳，确保生成不同的哈希值
                json_obj['_copy_timestamp'] = datetime.now().strftime("%Y%m%d%H%M%S%f")
                
                # 如果是PNG文件，需要保留预览图
                image = Image.open(workflow['file_path'])
                # 保存新文件（包含修改后的JSON数据）
                self.save_image_with_json(image, json.dumps(json_obj), new_path)
            
            elif ext == '.svg':
                # 读取SVG文件内容
                with open(workflow['file_path'], 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                # 查找JSON数据
                start_marker = '{"last_node_id":'
                start_pos = svg_content.find(start_marker)
                
                if start_pos == -1:
                    # 尝试查找URL编码的JSON
                    start_marker = '%7B%22last_node_id%22%3A'
                    start_pos = svg_content.find(start_marker)
                    if start_pos != -1:
                        # 找到URL编码的JSON结束位置
                        end_pos = svg_content.find('"', start_pos)
                        if end_pos != -1:
                            from urllib.parse import unquote
                            encoded_data = svg_content[start_pos:end_pos]
                            json_str = unquote(encoded_data)
                            json_obj = json.loads(json_str)
                    else:
                        # 尝试查找HTML转义的JSON
                        start_marker = '{"amp;last_node_id":'
                        start_pos = svg_content.find(start_marker)
                        if start_pos == -1:
                            raise ValueError("无法从SVG文件提取工作流数据")
                        
                        # 解析HTML转义的JSON
                        json_str = ''
                        brace_count = 0
                        i = start_pos
                        while i < len(svg_content):
                            char = svg_content[i]
                            json_str += char
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    break
                            i += 1
                        
                        # 处理HTML转义字符
                        json_str = json_str.replace('&amp;', '&')
                        json_str = json_str.replace('&quot;', '"')
                        json_str = json_str.replace('&lt;', '<')
                        json_str = json_str.replace('&gt;', '>')
                        json_obj = json.loads(json_str)
                else:
                    # 解析普通JSON
                    json_str = ''
                    brace_count = 0
                    i = start_pos
                    while i < len(svg_content):
                        char = svg_content[i]
                        json_str += char
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                break
                        i += 1
                    json_obj = json.loads(json_str)
                
                # 添加复制时间戳
                json_obj['_copy_timestamp'] = datetime.now().strftime("%Y%m%d%H%M%S%f")
                
                # 替换原JSON数据
                new_json_str = json.dumps(json_obj)
                if '%7B%22last_node_id%22%3A' in svg_content:
                    # URL编码的情况
                    from urllib.parse import quote
                    new_encoded_json = quote(new_json_str)
                    new_svg_content = svg_content.replace(encoded_data, new_encoded_json)
                else:
                    # 普通JSON或HTML转义的情况
                    new_svg_content = svg_content.replace(json_str, new_json_str)
                
                # 保存新SVG文件
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write(new_svg_content)
            
            else:
                # JSON文件直接读取和修改
                with open(workflow['file_path'], 'r', encoding='utf-8') as f:
                    json_obj = json.load(f)
                
                # 添加复制时间戳，确保生成不同的哈希值
                json_obj['_copy_timestamp'] = datetime.now().strftime("%Y%m%d%H%M%S%f")
                
                # 保存新文件
                with open(new_path, 'w', encoding='utf-8') as f:
                    json.dump(json_obj, f, ensure_ascii=False, indent=2)
            
            # 重新加载工作流列表
            self.load_workflows()
            self.main_app.show_popup_message("工作流已复制")
            
        except Exception as e:
            self.main_app.show_popup_message(f"复制失败: {str(e)}")

    def delete_workflow(self, workflow_hash):
        """删除工作流"""
        workflow = self.workflows.get(workflow_hash)
        if not workflow:
            return
        
        # 确认删除
        if not messagebox.askyesno("确认删除", "确定要删除这个工作流吗？"):
            return
        
        try:
            # 删除文件
            os.remove(workflow['file_path'])
            
            # 从工作流字典中移除
            del self.workflows[workflow_hash]
            
            # 如果是当前选中的工作流，清除选中状态
            if self.current_workflow and self.current_workflow.get('hash') == workflow_hash:
                self.current_workflow = None
            
            # 保存更改并刷新显示
            self.save_workflow_info()
            self.refresh_workflow_list()
            self.main_app.show_popup_message("工作流已删除")
            
        except Exception as e:
            self.main_app.show_popup_message(f"删除失败: {str(e)}")

    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def select_previous_workflow(self, event=None):
        """选择上一个工作流"""
        # 如果焦点在搜索框上，不处理上下键
        if self.master.focus_get() == self.search_entry:
            return
        
        if not self.workflows:
            return
        
        # 获取所有工作流哈希值的列表
        workflow_hashes = []
        for frame in self.scrollable_frame.winfo_children():
            if hasattr(frame, 'workflow_hash'):
                workflow_hashes.append(frame.workflow_hash)
        
        if not workflow_hashes:
            return
        
        if not self.current_workflow:
            # 如果当前没有选中的工作流，选择最后一个
            last_hash = workflow_hashes[-1]
            self.select_workflow(last_hash)
            return
        
        # 获取当前工作流的索引
        try:
            current_index = workflow_hashes.index(self.current_workflow['hash'])
            # 获取上一个工作流的索引（如果是第一个则循环到最后一个）
            previous_index = (current_index - 1) if current_index > 0 else len(workflow_hashes) - 1
            previous_hash = workflow_hashes[previous_index]
            
            # 选择上一个工作流
            self.select_workflow(previous_hash)
            
            # 确保选中的项目可见
            self.ensure_workflow_visible(previous_hash)
        except ValueError:
            pass

    def select_next_workflow(self, event=None):
        """选择下一个工作流"""
        # 如果焦点在搜索框上，不处理上下键
        if self.master.focus_get() == self.search_entry:
            return
        
        if not self.workflows:
            return
        
        # 获取所有工作流哈希值的列表
        workflow_hashes = []
        for frame in self.scrollable_frame.winfo_children():
            if hasattr(frame, 'workflow_hash'):
                workflow_hashes.append(frame.workflow_hash)
        
        if not workflow_hashes:
            return
        
        if not self.current_workflow:
            # 如果当前没有选中的工作流，选择第一个
            first_hash = workflow_hashes[0]
            self.select_workflow(first_hash)
            return
        
        # 获取当前工作流的索引
        try:
            current_index = workflow_hashes.index(self.current_workflow['hash'])
            # 获取下一个工作流的索引（如果是最后一个则循环到第一个）
            next_index = (current_index + 1) % len(workflow_hashes)
            next_hash = workflow_hashes[next_index]
            
            # 选择下一个工作流
            self.select_workflow(next_hash)
            
            # 确保选中的项目可见
            self.ensure_workflow_visible(next_hash)
        except ValueError:
            pass

    def ensure_workflow_visible(self, workflow_hash):
        """确保工作流在可视区域内"""
        for frame in self.scrollable_frame.winfo_children():
            if hasattr(frame, 'workflow_hash') and frame.workflow_hash == workflow_hash:
                frame_top = frame.winfo_y()
                frame_bottom = frame_top + frame.winfo_height()
                
                canvas_height = self.canvas.winfo_height()
                scroll_top = self.canvas.yview()[0] * self.scrollable_frame.winfo_height()
                scroll_bottom = self.canvas.yview()[1] * self.scrollable_frame.winfo_height()
                
                # 如果选中的项目在可视区域外，调整滚动位置
                if frame_top < scroll_top:
                    # 如果项目在可视区域上方，向上滚动
                    self.canvas.yview_moveto(frame_top / self.scrollable_frame.winfo_height())
                elif frame_bottom > scroll_bottom:
                    # 如果项目在可视区域下方，向下滚动
                    self.canvas.yview_moveto((frame_bottom - canvas_height) / self.scrollable_frame.winfo_height())
                break

    def paste_and_replace_text(self, widget):
        """粘贴并替换文本"""
        try:
            text = self.master.clipboard_get()
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
                widget.insert("1.0", text)
                # 触发自动保存
                if widget == self.workflow_desc:
                    self.schedule_save("工作流描述")
                elif widget == self.workflow_type:
                    self.schedule_save("工作流类型")
                elif widget == self.workflow_url:
                    self.schedule_save("工作流网址")
            elif isinstance(widget, ttk.Entry):
                if widget == self.workflow_name:
                    # 工作流名称不需要自动保存，保持可编辑状态
                    widget.configure(state='normal')
                    widget.delete(0, tk.END)
                    widget.insert(0, text)
                else:
                    widget.configure(state='normal')
                    widget.delete(0, tk.END)
                    widget.insert(0, text)
                    if widget == self.workflow_type:
                        self.schedule_save("工作流类型")
                    elif widget == self.workflow_url:
                        self.schedule_save("工作流网址")
        except:
            pass

    def paste_text(self, widget):
        """粘贴文本"""
        try:
            text = self.master.clipboard_get()
            if isinstance(widget, tk.Text):
                widget.insert(tk.INSERT, text)
                # 触发自动保存
                if widget == self.workflow_desc:
                    self.schedule_save("工作流描述")
                elif widget == self.workflow_type:
                    self.schedule_save("工作流类型")
                elif widget == self.workflow_url:
                    self.schedule_save("工作流网址")
            elif isinstance(widget, ttk.Entry):
                if widget == self.workflow_name:
                    # 工作流名称不需要自动保存，保持可编辑状态
                    widget.configure(state='normal')
                    widget.delete(0, tk.END)
                    widget.insert(0, text)
                else:
                    widget.configure(state='normal')
                    widget.delete(0, tk.END)
                    widget.insert(0, text)
                    if widget == self.workflow_type:
                        self.schedule_save("工作流类型")
                    elif widget == self.workflow_url:
                        self.schedule_save("工作流网址")
        except:
            pass

    def change_workflow_dir(self):
        """更改工作流根目录"""
        from tkinter import filedialog
        
        # 打开文件夹选择对话框，默认定位到当前根目录
        new_dir = filedialog.askdirectory(
            title="选择工作流根目录",
            initialdir=self.workflow_dir
        )
        
        if new_dir:  # 如果用户选择了目录
            try:
                backup_file = 'workflow_info(backup).json'
                
                # 检查备份文件中的根目录
                backup_root_dir = None
                if os.path.exists(backup_file):
                    try:
                        with open(backup_file, 'r', encoding='utf-8') as f:
                            backup_info = json.load(f)
                            backup_root_dir = backup_info.get('_root_dir')
                    except:
                        pass
                
                # 如果选择的目录与备份文件中的根目录一致
                if backup_root_dir and os.path.normpath(new_dir) == os.path.normpath(backup_root_dir):
                    # 交换两个文件的名称
                    temp_file = 'workflow_info.temp'
                    os.rename(self.workflow_info_file, temp_file)
                    os.rename(backup_file, self.workflow_info_file)
                    os.rename(temp_file, backup_file)
                    
                    # 更新工作流目录
                    self.workflow_dir = new_dir
                    
                    # 更新根目录显示
                    self.root_dir_label.configure(text=new_dir)  # 直接显示路径
                    
                    # 重新加载工作流
                    self.workflows = {}
                    self.current_workflow = None
                    self.load_workflows()
                    
                    # 更新界面
                    self.refresh_workflow_list()
                    
                    # 显示成功消息
                    self.main_app.show_popup_message(f"已更改根目录为: {new_dir}\n已恢复使用原配置文件")
                else:
                    # 备份当前的 workflow_info.json
                    if os.path.exists(self.workflow_info_file):
                        # 如果备份文件已存在，先删除
                        if os.path.exists(backup_file):
                            os.remove(backup_file)
                        # 重命名当前文件为备份文件
                        os.rename(self.workflow_info_file, backup_file)
                    
                    # 更新工作流目录
                    self.workflow_dir = new_dir
                    
                    # 更新根目录显示
                    self.root_dir_label.configure(text=new_dir)  # 直接显示路径
                    
                    # 清空当前工作流信息
                    self.workflows = {}
                    self.current_workflow = None
                    
                    # 重新加载工作流（这会生成新的 workflow_info.json）
                    self.load_workflows()
                    
                    # 更新界面
                    self.refresh_workflow_list()
                    
                    # 显示成功消息
                    self.main_app.show_popup_message(f"已更改根目录为: {new_dir}\n原配置文件已备份为: workflow_info(backup).json")
                
            except Exception as e:
                self.main_app.show_popup_message(f"更改根目录失败: {str(e)}")

    def update_filter_buttons(self):
        """更新筛选按钮"""
        # 清除现有按钮
        for widget in self.button_container.winfo_children():
            widget.destroy()
        self.filter_buttons.clear()
        
        # 获取当前根目录下的文件夹
        folders = [folder for folder in sorted(os.listdir(self.workflow_dir)) 
                  if os.path.isdir(os.path.join(self.workflow_dir, folder))]
        
        # 合并所有按钮文本，将收藏和其他放在最后
        all_buttons = folders + ["其他", "收藏"]
        
        # 计算每行按钮数量
        buttons_per_row = 4
        
        # 创建按钮
        for i, text in enumerate(all_buttons):
            row = i // buttons_per_row
            col = i % buttons_per_row
            
            # 配置列权重
            if col == 0:
                for j in range(buttons_per_row):
                    self.button_container.columnconfigure(j, weight=1)
            
            btn = ttk.Button(
                self.button_container,
                text=text,
                style='primary.TButton',
                command=lambda t=text: self.filter_workflows(t)
            )
            btn.grid(row=row, column=col, padx=2, pady=2, sticky='ew')
            self.filter_buttons[text] = btn

    def show_full_preview(self, event=None):
        """显示全尺寸预览图"""
        if not self.current_workflow:
            return
        
        # 如果是 PNG 格式工作流，直接使用原文件
        if self.current_workflow['file_path'].lower().endswith('.png'):
            image_path = self.current_workflow['file_path']
        else:
            # 否则使用默认预览图
            image_path = os.path.join('ui', 'null.png')
            if not os.path.exists(image_path):
                return
        
        try:
            # 创建预览窗口
            preview_window = tk.Toplevel(self.master)
            preview_window.title("预览图")
            preview_window.transient(self.master)
            
            # 获取屏幕尺寸
            screen_width = self.master.winfo_screenwidth()
            screen_height = self.master.winfo_screenheight()
            
            # 加载原始图片
            original_image = Image.open(image_path)
            
            # 计算缩放比例，确保预览窗口不超过屏幕大小的80%
            max_width = int(screen_width * 0.8)
            max_height = int(screen_height * 0.8)
            width_ratio = max_width / original_image.width
            height_ratio = max_height / original_image.height
            scale_ratio = min(width_ratio, height_ratio)
            
            # 如果图片小于最大尺寸，则使用原始尺寸
            if scale_ratio >= 1:
                new_width = original_image.width
                new_height = original_image.height
            else:
                new_width = int(original_image.width * scale_ratio)
                new_height = int(original_image.height * scale_ratio)
            
            # 调整图片大小
            current_scale = scale_ratio
            resized_image = original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(resized_image)
            
            # 创建标签显示图片
            label = ttk.Label(preview_window, image=photo)
            label.photo = photo  # 保持引用
            label.pack(padx=10, pady=10)
            
            # 设置窗口大小和位置
            window_width = new_width + 20  # 添加内边距
            window_height = new_height + 20
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            preview_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            # 添加拖拽相关变量
            drag_data = {"x": 0, "y": 0, "dragging": False}
            
            def update_image(scale):
                """更新图片大小"""
                new_w = int(original_image.width * scale)
                new_h = int(original_image.height * scale)
                resized = original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                new_photo = ImageTk.PhotoImage(resized)
                label.configure(image=new_photo)
                label.photo = new_photo  # 保持引用
                
                # 更新窗口大小
                win_width = new_w + 20
                win_height = new_h + 20
                win_x = preview_window.winfo_x()
                win_y = preview_window.winfo_y()
                
                # 确保窗口不会超出屏幕
                if win_width > screen_width:
                    win_width = screen_width
                    win_x = 0
                if win_height > screen_height:
                    win_height = screen_height
                    win_y = 0
                
                preview_window.geometry(f"{win_width}x{win_height}+{win_x}+{win_y}")
            
            def on_mousewheel(event):
                """处理鼠标滚轮事件"""
                nonlocal current_scale
                
                # 调整缩放速度和平滑度
                # 1. 降低 delta 值使缩放更平滑 (从 1200.0 改为 2400.0)
                # 2. 根据当前缩放比例动态调整缩放速度
                base_delta = event.delta / 2400.0
                
                # 当放大时降低缩放速度，缩小时提高缩放速度
                if event.delta > 0:  # 放大
                    adjusted_delta = base_delta * (1.0 / (current_scale ** 0.5))
                else:  # 缩小
                    adjusted_delta = base_delta * (current_scale ** 0.3)
                
                # 计算新的缩放比例
                new_scale = current_scale * (1.0 + adjusted_delta)
                
                # 限制缩放范围并添加缓动效果
                min_scale = 0.1
                max_scale = 5.0
                
                if min_scale <= new_scale <= max_scale:
                    # 添加缓动效果，使缩放更平滑
                    current_scale = current_scale + (new_scale - current_scale) * 0.8
                    update_image(current_scale)
            
            def start_drag(event):
                """开始拖拽"""
                drag_data["x"] = event.x
                drag_data["y"] = event.y
                drag_data["dragging"] = True
                label.configure(cursor="fleur")  # 更改鼠标指针样式为移动状态
            
            def stop_drag(event):
                """停止拖拽"""
                drag_data["dragging"] = False
                label.configure(cursor="")  # 恢复默认鼠标指针样式
            
            def do_drag(event):
                """执行拖拽"""
                if drag_data["dragging"]:
                    # 计算位移
                    dx = event.x - drag_data["x"]
                    dy = event.y - drag_data["y"]
                    
                    # 获取当前窗口位置
                    x = preview_window.winfo_x()
                    y = preview_window.winfo_y()
                    
                    # 更新窗口位置
                    preview_window.geometry(f"+{x + dx}+{y + dy}")
            
            # 绑定鼠标事件
            label.bind("<Button-1>", start_drag)
            label.bind("<ButtonRelease-1>", stop_drag)
            label.bind("<B1-Motion>", do_drag)
            
            # 绑定鼠标滚轮事件
            preview_window.bind("<MouseWheel>", on_mousewheel)
            
            # 绑定 Escape 键关闭窗口
            preview_window.bind("<Escape>", lambda e: preview_window.destroy())
            
            # 设置窗口图标
            if hasattr(self.main_app, 'icon'):
                preview_window.iconphoto(True, self.main_app.icon)
            
        except Exception as e:
            self.main_app.show_popup_message(f"显示预览图失败: {str(e)}")

    def copy_workflow_json(self):
        """复制工作流的json内容到剪贴板"""
        if not self.current_workflow:
            self.main_app.show_popup_message("请先选择一个工作流")
            return
        
        try:
            file_path = self.current_workflow['file_path']
            file_ext = file_path.lower()
            
            # 如果是PNG或SVG文件，从文件中提取json片段
            if file_ext.endswith(('.png', '.svg')):
                try:
                    # 读取文件的二进制数据
                    with open(file_path, 'rb') as f:
                        data = f.read()
                    
                    # 查找JSON数据的开始和结束位置
                    start_marker = b'{"last_node_id":'
                    start_pos = data.find(start_marker)
                    
                    if start_pos == -1 and file_ext.endswith('.svg'):
                        # 对于SVG文件，尝试查找转义后的JSON开始标记
                        start_marker = b'%7B%22last_node_id%22%3A'
                        start_pos = data.find(start_marker)
                        if start_pos != -1:
                            # 将URL编码的数据解码为普通JSON
                            from urllib.parse import unquote
                            encoded_data = data[start_pos:].split(b'"')[0]
                            json_str = unquote(encoded_data.decode('ascii'))
                            workflow_data = json.loads(json_str)
                        else:
                            # 再尝试查找HTML转义的JSON开始标记
                            start_marker = b'{"amp;last_node_id":'
                            start_pos = data.find(start_marker)
                            if start_pos != -1:
                                # 处理HTML转义的JSON
                                json_bytes = data[start_pos:]
                                # 找到JSON的结束位置
                                brace_count = 0
                                end_pos = 0
                                i = 0
                                while i < len(json_bytes):
                                    byte = json_bytes[i:i+1]
                                    if byte == b'{':
                                        brace_count += 1
                                    elif byte == b'}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            end_pos = i + 1
                                            break
                                    i += 1
                                
                                if end_pos > 0:
                                    json_data = json_bytes[:end_pos]
                                    try:
                                        json_str = json_data.decode('utf-8')
                                        # 处理HTML转义字符
                                        json_str = json_str.replace('&amp;', '&')
                                        json_str = json_str.replace('&quot;', '"')
                                        json_str = json_str.replace('&lt;', '<')
                                        json_str = json_str.replace('&gt;', '>')
                                    except UnicodeDecodeError:
                                        json_str = json_data.decode('latin1')
                                    # 验证JSON是否有效
                                    json.loads(json_str)
                                else:
                                    raise ValueError("无法找到完整的JSON数据")
                            else:
                                raise ValueError("未找到JSON数据")
                    
                    elif start_pos != -1:  # PNG文件或未编码的SVG文件
                        # 从找到的位置开始截取数据
                        json_bytes = data[start_pos:]
                        
                        # 找到JSON的结束位置
                        brace_count = 0
                        end_pos = 0
                        
                        # 逐字节处理
                        i = 0
                        while i < len(json_bytes):
                            byte = json_bytes[i:i+1]
                            if byte == b'{':
                                brace_count += 1
                            elif byte == b'}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_pos = i + 1
                                    break
                            i += 1
                        
                        if end_pos > 0:
                            # 截取完整的JSON数据
                            json_data = json_bytes[:end_pos]
                            # 尝试解码
                            try:
                                json_str = json_data.decode('utf-8')
                            except UnicodeDecodeError:
                                json_str = json_data.decode('latin1')
                            
                            # 验证JSON是否有效
                            json.loads(json_str)  # 这会抛出异常如果JSON无效
                        else:
                            raise ValueError("无法找到完整的JSON数据")
                    else:
                        raise ValueError("未找到JSON数据")
                
                except Exception as e:
                    self.main_app.show_popup_message(f"从{file_ext[1:].upper()}提取JSON失败: {str(e)}")
                    return
            else:
                # 如果是JSON文件，直接读取内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_str = json.dumps(json.load(f), ensure_ascii=False, indent=2)
            
            # 复制到剪贴板
            self.master.clipboard_clear()
            self.master.clipboard_append(json_str)
            
            self.main_app.show_popup_message("工作流JSON已复制到剪贴板")
        except Exception as e:
            self.main_app.show_popup_message(f"复制JSON失败: {str(e)}")

    def open_in_comfyui(self):
        """在ComfyUI中打开工作流"""
        if not self.current_workflow:
            self.main_app.show_popup_message("请先选择一个工作流")
            return
        
        try:
            # 先复制JSON到剪贴板
            self.copy_workflow_json()
            
            # 打开ComfyUI网页
            import webbrowser
            webbrowser.open('http://127.0.0.1:8188/')
            
            # 等待一小段时间后模拟按下Ctrl+V
            self.after(5000, self.simulate_paste)
            
        except Exception as e:
            self.main_app.show_popup_message(f"打开ComfyUI失败: {str(e)}")

    def simulate_paste(self):
        """模拟按下Ctrl+V"""
        try:
            import pyautogui
            # 模拟按下Ctrl+V
            pyautogui.hotkey('ctrl', 'v')
            
        except ImportError:
            self.main_app.show_popup_message("请安装pyautogui库以支持自动粘贴功能")
        except Exception as e:
            self.main_app.show_popup_message(f"自动粘贴失败: {str(e)}")

    def change_preview_image(self, workflow_hash):
        """更换工作流预览图"""
        workflow = self.workflows.get(workflow_hash)
        if not workflow:
            return
        
        from tkinter import filedialog
        
        # 选择新的图片文件
        new_image_path = filedialog.askopenfilename(
            title="选择新的预览图",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.webp"),
                ("所有文件", "*.*")
            ]
        )
        
        if not new_image_path:
            return
        
        try:
            # 读取新图片
            new_image = Image.open(new_image_path)
            
            # 如果不是PNG格式，转换为PNG
            if new_image.format != 'PNG':
                new_image = new_image.convert('RGBA')
            
            # 获取原工作流文件路径和类型
            original_path = workflow['file_path']
            is_json = original_path.lower().endswith('.json')
            
            if is_json:
                # 如果是JSON文件，创建新的PNG文件
                new_file_path = os.path.splitext(original_path)[0] + '.png'
                
                # 读取原JSON内容并确保格式正确
                with open(original_path, 'r', encoding='utf-8') as f:
                    json_data = f.read()
                    # 验证并格式化JSON
                    json_obj = json.loads(json_data)
                    json_data = json.dumps(json_obj, ensure_ascii=False)
                
                # 将JSON数据添加到PNG文件
                self.save_image_with_json(new_image, json_data, new_file_path)
                
                # 删除原JSON文件
                os.remove(original_path)
                
            else:
                # 如果是PNG文件，保留原JSON数据
                new_file_path = original_path
                
                # 读取原PNG文件中的JSON数据
                with open(original_path, 'rb') as f:
                    data = f.read()
                
                # 提取JSON数据
                json_data = self.extract_json_from_png(data)
                if json_data:
                    # 保存新图片并添加原JSON数据
                    self.save_image_with_json(new_image, json_data, new_file_path)
                else:
                    self.main_app.show_popup_message("无法从原文件提取工作流数据")
                    return
            
            # 更新工作流信息
            workflow['file_path'] = new_file_path
            
            # 重新加载预览图
            preview_image = new_image.copy()
            workflow['list_preview'] = self.resize_preview_image(
                preview_image,
                self.thumbnail_size[0],
                self.thumbnail_size[1]
            )
            workflow['detail_preview'] = self.resize_preview_image(
                preview_image,
                self.base_preview_size,
                self.base_preview_size
            )
            
            # 保存更改并刷新显示
            self.save_workflow_info()
            self.refresh_workflow_list()
            self.update_workflow_detail()
            
            self.main_app.show_popup_message("预览图已更新")
            
        except Exception as e:
            self.main_app.show_popup_message(f"更换预览图失败: {str(e)}")

    def save_image_with_json(self, image, json_data, output_path):
        """将JSON数据保存到PNG文件中，确保与ComfyUI格式兼容"""
        try:
            # 确保JSON数据格式正确
            if isinstance(json_data, str):
                try:
                    json_obj = json.loads(json_data)
                    json_data = json.dumps(json_obj, ensure_ascii=False, separators=(',', ':'))
                except json.JSONDecodeError:
                    raise ValueError("Invalid JSON data")

            # 创建新的PNG文件
            with open(output_path, 'wb') as f:
                # 1. PNG标准文件头
                f.write(b'\x89PNG\r\n\x1a\n')

                # 2. IHDR块
                width = image.width
                height = image.height
                ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
                f.write(struct.pack('>I', 13))  # IHDR长度（固定为13）
                f.write(b'IHDR')
                f.write(ihdr_data)
                f.write(struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data)))

                # 3. tEXt块（工作流数据）
                workflow_data = b'workflow' + b'\x00' + json_data.encode('utf-8')
                f.write(struct.pack('>I', len(workflow_data)))
                f.write(b'tEXt')
                f.write(workflow_data)
                f.write(struct.pack('>I', zlib.crc32(b'tEXt' + workflow_data)))

                # 4. sRGB块
                f.write(struct.pack('>I', 1))  # 长度为1
                f.write(b'sRGB')
                f.write(b'\x00')  # 渲染意图：知觉
                f.write(struct.pack('>I', zlib.crc32(b'sRGB\x00')))

                # 5. gAMA块
                gama_data = struct.pack('>I', 45455)  # 标准伽马值
                f.write(struct.pack('>I', 4))
                f.write(b'gAMA')
                f.write(gama_data)
                f.write(struct.pack('>I', zlib.crc32(b'gAMA' + gama_data)))

                # 6. 图像数据
                img_byte_arr = BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_data = img_byte_arr.getvalue()
                
                # 提取并写入IDAT块
                idat_start = img_data.find(b'IDAT')
                while idat_start != -1:
                    length_bytes = img_data[idat_start-4:idat_start]
                    length = struct.unpack('>I', length_bytes)[0]
                    chunk_end = idat_start + 4 + length + 4
                    f.write(img_data[idat_start-4:chunk_end])
                    idat_start = img_data.find(b'IDAT', chunk_end)

                # 7. IEND块
                f.write(struct.pack('>I', 0))
                f.write(b'IEND')
                f.write(struct.pack('>I', zlib.crc32(b'IEND')))

        except Exception as e:
            raise Exception(f"保存工作流失败: {str(e)}")

    def extract_json_from_png(self, data):
        """从PNG文件中提取JSON数据"""
        try:
            # 查找tEXt块中的workflow数据
            text_pos = data.find(b'tEXtworkflow\x00')
            if text_pos != -1:
                # 找到workflow数据的开始位置
                json_start = text_pos + len(b'tEXtworkflow\x00')
                # 找到下一个PNG块的开始
                next_chunk = data.find(b'sRGB', json_start)
                if next_chunk != -1:
                    json_data = data[json_start:next_chunk-8].strip()
                    try:
                        json_str = json_data.decode('utf-8')
                        json.loads(json_str)  # 验证JSON
                        return json_str
                    except:
                        return None
            return None
        except Exception:
            return None

    def show_preview_menu(self, event):
        """显示预览图右键菜单"""
        if not self.current_workflow:
            return
        
        menu = tk.Menu(self, tearoff=0, font=self.base_font)
        
        # 添加菜单项
        menu.add_command(
            label="更换预览图",
            command=lambda: self.change_preview_image(self.current_workflow['hash'])
        )
        menu.add_command(
            label="删除预览图",
            command=self.remove_preview_image
        )
        
        # 显示菜单
        menu.post(event.x_root, event.y_root)

    def remove_preview_image(self):
        """删除预览图，将PNG工作流转换为JSON工作流"""
        if not self.current_workflow:
            return
        
        workflow_path = self.current_workflow['file_path']
        if not workflow_path.lower().endswith('.png'):
            self.main_app.show_popup_message("当前工作流不是PNG格式")
            return
        
        try:
            # 读取PNG文件中的JSON数据
            with open(workflow_path, 'rb') as f:
                data = f.read()
            
            # 提取JSON数据
            json_data = self.extract_json_from_png(data)
            if not json_data:
                self.main_app.show_popup_message("无法从文件中提取工作流数据")
                return
            
            # 创建新的JSON文件路径
            new_file_path = os.path.splitext(workflow_path)[0] + '.json'
            
            # 保存JSON文件
            with open(new_file_path, 'w', encoding='utf-8') as f:
                # 格式化JSON数据
                json_obj = json.loads(json_data)
                json.dump(json_obj, f, ensure_ascii=False, indent=2)
            
            # 删除原PNG文件
            os.remove(workflow_path)
            
            # 更新工作流信息
            workflow_hash = self.current_workflow['hash']
            self.workflows[workflow_hash]['file_path'] = new_file_path
            
            # 使用默认预览图
            if self.list_preview:
                self.workflows[workflow_hash]['list_preview'] = self.list_preview
            if self.default_preview:
                self.workflows[workflow_hash]['detail_preview'] = self.default_preview
            
            # 保存更改并刷新显示
            self.save_workflow_info()
            self.refresh_workflow_list()
            self.update_workflow_detail()
            
            self.main_app.show_popup_message("预览图已删除，工作流已转换为JSON格式")
            
        except Exception as e:
            self.main_app.show_popup_message(f"删除预览图失败: {str(e)}")