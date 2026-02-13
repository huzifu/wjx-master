"""
UI增强模块
提供现代化的界面组件和主题
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
from typing import Dict, Any, Optional, Callable
import logging


class ModernUI:
    """现代化UI组件"""
    
    def __init__(self):
        self.colors = {
            'primary': '#2196F3',
            'secondary': '#FF9800',
            'success': '#4CAF50',
            'danger': '#F44336',
            'warning': '#FFC107',
            'info': '#00BCD4',
            'light': '#F5F5F5',
            'dark': '#212121',
            'white': '#FFFFFF',
            'gray': '#9E9E9E',
            'border': '#E0E0E0'
        }
        
        self.fonts = {
            'title': ('微软雅黑', 16, 'bold'),
            'subtitle': ('微软雅黑', 14, 'bold'),
            'heading': ('微软雅黑', 12, 'bold'),
            'body': ('微软雅黑', 10),
            'small': ('微软雅黑', 9)
        }

    def create_modern_button(self, parent, text: str, command: Callable = None, 
                           style: str = 'primary', width: int = None) -> ttk.Button:
        """创建现代化按钮"""
        btn = ttk.Button(parent, text=text, command=command, width=width)
        
        # 设置样式
        style_name = f'Modern.TButton.{style}'
        style_obj = ttk.Style()
        
        if style == 'primary':
            style_obj.configure(style_name, 
                              background=self.colors['primary'],
                              foreground=self.colors['white'],
                              borderwidth=0,
                              focuscolor='none')
        elif style == 'secondary':
            style_obj.configure(style_name,
                              background=self.colors['secondary'],
                              foreground=self.colors['white'],
                              borderwidth=0,
                              focuscolor='none')
        elif style == 'success':
            style_obj.configure(style_name,
                              background=self.colors['success'],
                              foreground=self.colors['white'],
                              borderwidth=0,
                              focuscolor='none')
        elif style == 'danger':
            style_obj.configure(style_name,
                              background=self.colors['danger'],
                              foreground=self.colors['white'],
                              borderwidth=0,
                              focuscolor='none')
        
        btn.configure(style=style_name)
        return btn

    def create_modern_frame(self, parent, title: str = None, 
                          padding: int = 10) -> ttk.LabelFrame:
        """创建现代化框架"""
        if title:
            frame = ttk.LabelFrame(parent, text=title, padding=padding)
        else:
            frame = ttk.Frame(parent, padding=padding)
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.TLabelframe',
                          background=self.colors['light'],
                          borderwidth=1,
                          relief='solid')
        style_obj.configure('Modern.TLabelframe.Label',
                          background=self.colors['light'],
                          foreground=self.colors['dark'],
                          font=self.fonts['heading'])
        
        if title:
            frame.configure(style='Modern.TLabelframe')
        
        return frame

    def create_modern_entry(self, parent, placeholder: str = None, 
                          width: int = 30) -> ttk.Entry:
        """创建现代化输入框"""
        entry = ttk.Entry(parent, width=width)
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.TEntry',
                          fieldbackground=self.colors['white'],
                          borderwidth=1,
                          relief='solid',
                          focuscolor=self.colors['primary'])
        
        entry.configure(style='Modern.TEntry')
        
        # 添加占位符功能
        if placeholder:
            entry.insert(0, placeholder)
            entry.bind('<FocusIn>', lambda e: self._on_entry_focus_in(entry, placeholder))
            entry.bind('<FocusOut>', lambda e: self._on_entry_focus_out(entry, placeholder))
        
        return entry

    def create_modern_combobox(self, parent, values: list, 
                             placeholder: str = None, width: int = 20) -> ttk.Combobox:
        """创建现代化下拉框"""
        combo = ttk.Combobox(parent, values=values, width=width)
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.TCombobox',
                          fieldbackground=self.colors['white'],
                          borderwidth=1,
                          relief='solid',
                          focuscolor=self.colors['primary'])
        
        combo.configure(style='Modern.TCombobox')
        
        # 设置占位符
        if placeholder:
            combo.set(placeholder)
        
        return combo

    def create_modern_progress_bar(self, parent, mode: str = 'determinate') -> ttk.Progressbar:
        """创建现代化进度条"""
        progress = ttk.Progressbar(parent, mode=mode)
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.Horizontal.TProgressbar',
                          background=self.colors['primary'],
                          troughcolor=self.colors['light'],
                          borderwidth=0,
                          lightcolor=self.colors['primary'],
                          darkcolor=self.colors['primary'])
        
        progress.configure(style='Modern.Horizontal.TProgressbar')
        return progress

    def create_modern_label(self, parent, text: str, 
                          font: str = 'body', color: str = 'dark') -> ttk.Label:
        """创建现代化标签"""
        label = ttk.Label(parent, text=text, font=self.fonts[font])
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.TLabel',
                          background=self.colors['light'],
                          foreground=self.colors[color])
        
        label.configure(style='Modern.TLabel')
        return label

    def create_modern_checkbutton(self, parent, text: str, 
                                variable: tk.BooleanVar = None) -> ttk.Checkbutton:
        """创建现代化复选框"""
        check = ttk.Checkbutton(parent, text=text, variable=variable)
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.TCheckbutton',
                          background=self.colors['light'],
                          foreground=self.colors['dark'],
                          indicatorcolor=self.colors['primary'])
        
        check.configure(style='Modern.TCheckbutton')
        return check

    def create_modern_radiobutton(self, parent, text: str, 
                                variable: tk.StringVar = None, value: str = None) -> ttk.Radiobutton:
        """创建现代化单选按钮"""
        radio = ttk.Radiobutton(parent, text=text, variable=variable, value=value)
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.TRadiobutton',
                          background=self.colors['light'],
                          foreground=self.colors['dark'],
                          indicatorcolor=self.colors['primary'])
        
        radio.configure(style='Modern.TRadiobutton')
        return radio

    def create_modern_notebook(self, parent) -> ttk.Notebook:
        """创建现代化标签页"""
        notebook = ttk.Notebook(parent)
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.TNotebook',
                          background=self.colors['light'],
                          borderwidth=1,
                          relief='solid')
        style_obj.configure('Modern.TNotebook.Tab',
                          background=self.colors['white'],
                          foreground=self.colors['dark'],
                          borderwidth=1,
                          relief='solid',
                          padding=[10, 5])
        style_obj.map('Modern.TNotebook.Tab',
                     background=[('selected', self.colors['primary']),
                                ('active', self.colors['secondary'])],
                     foreground=[('selected', self.colors['white']),
                                ('active', self.colors['white'])])
        
        notebook.configure(style='Modern.TNotebook')
        return notebook

    def create_modern_treeview(self, parent, columns: list) -> ttk.Treeview:
        """创建现代化树形视图"""
        tree = ttk.Treeview(parent, columns=columns, show='headings')
        
        # 设置列标题
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor='center')
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.Treeview',
                          background=self.colors['white'],
                          foreground=self.colors['dark'],
                          fieldbackground=self.colors['white'],
                          borderwidth=1,
                          relief='solid')
        style_obj.configure('Modern.Treeview.Heading',
                          background=self.colors['primary'],
                          foreground=self.colors['white'],
                          borderwidth=0,
                          relief='flat')
        
        tree.configure(style='Modern.Treeview')
        return tree

    def create_modern_scrollbar(self, parent, orient: str = 'vertical') -> ttk.Scrollbar:
        """创建现代化滚动条"""
        scrollbar = ttk.Scrollbar(parent, orient=orient)
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.Vertical.TScrollbar',
                          background=self.colors['gray'],
                          borderwidth=0,
                          relief='flat',
                          troughcolor=self.colors['light'],
                          width=12)
        
        scrollbar.configure(style='Modern.Vertical.TScrollbar')
        return scrollbar

    def create_modern_spinbox(self, parent, from_: int, to: int, 
                            width: int = 10) -> ttk.Spinbox:
        """创建现代化数字输入框"""
        spinbox = ttk.Spinbox(parent, from_=from_, to=to, width=width)
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.TSpinbox',
                          fieldbackground=self.colors['white'],
                          borderwidth=1,
                          relief='solid',
                          focuscolor=self.colors['primary'])
        
        spinbox.configure(style='Modern.TSpinbox')
        return spinbox

    def create_modern_scale(self, parent, from_: int, to: int, 
                          orient: str = 'horizontal') -> ttk.Scale:
        """创建现代化滑动条"""
        scale = ttk.Scale(parent, from_=from_, to=to, orient=orient)
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Modern.Horizontal.TScale',
                          background=self.colors['light'],
                          troughcolor=self.colors['light'],
                          slidercolor=self.colors['primary'],
                          borderwidth=0,
                          relief='flat')
        
        scale.configure(style='Modern.Horizontal.TScale')
        return scale

    def create_status_indicator(self, parent, text: str = "就绪") -> ttk.Label:
        """创建状态指示器"""
        indicator = ttk.Label(parent, text="●", font=('微软雅黑', 12))
        
        # 设置样式
        style_obj = ttk.Style()
        style_obj.configure('Status.TLabel',
                          background=self.colors['light'],
                          foreground=self.colors['success'])
        
        indicator.configure(style='Status.TLabel')
        return indicator

    def update_status_indicator(self, indicator: ttk.Label, status: str):
        """更新状态指示器"""
        style_obj = ttk.Style()
        
        if status == 'success':
            indicator.configure(foreground=self.colors['success'])
        elif status == 'warning':
            indicator.configure(foreground=self.colors['warning'])
        elif status == 'error':
            indicator.configure(foreground=self.colors['danger'])
        elif status == 'info':
            indicator.configure(foreground=self.colors['info'])
        else:
            indicator.configure(foreground=self.colors['gray'])

    def create_tooltip(self, widget, text: str, delay: int = 500):
        """创建工具提示"""
        tooltip = ToolTip(widget, text, delay)
        return tooltip

    def _on_entry_focus_in(self, entry: ttk.Entry, placeholder: str):
        """输入框获得焦点时的处理"""
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.configure(foreground=self.colors['dark'])

    def _on_entry_focus_out(self, entry: ttk.Entry, placeholder: str):
        """输入框失去焦点时的处理"""
        if not entry.get():
            entry.insert(0, placeholder)
            entry.configure(foreground=self.colors['gray'])


class ToolTip:
    """工具提示类"""
    
    def __init__(self, widget, text: str, delay: int = 500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip = None
        self.scheduled = False
        
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<Motion>', self.motion)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hide()

    def motion(self, event=None):
        if self.scheduled:
            self.unschedule()
        self.schedule()

    def schedule(self):
        self.scheduled = True
        self.widget.after(self.delay, self.show)

    def unschedule(self):
        self.scheduled = False
        self.widget.after_cancel(self.scheduled)

    def show(self):
        if not self.scheduled:
            return
        
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, 
                        justify=tk.LEFT,
                        background="#ffffe0", 
                        relief=tk.SOLID, 
                        borderwidth=1,
                        font=("微软雅黑", 9))
        label.pack()

    def hide(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class ModernDialog:
    """现代化对话框"""
    
    def __init__(self, parent, title: str, message: str, 
                 buttons: list = None, icon: str = 'info'):
        self.parent = parent
        self.title = title
        self.message = message
        self.buttons = buttons or ['确定']
        self.icon = icon
        self.result = None
        
        self.create_dialog()

    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (200 // 2)
        self.dialog.geometry(f"400x200+{x}+{y}")
        
        # 创建内容
        self.create_content()
        
        # 等待用户响应
        self.dialog.wait_window()

    def create_content(self):
        """创建对话框内容"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 图标
        icon_label = ttk.Label(main_frame, text=self.get_icon_text(), 
                              font=('微软雅黑', 24))
        icon_label.pack(pady=(0, 10))
        
        # 消息
        message_label = ttk.Label(main_frame, text=self.message, 
                                 font=('微软雅黑', 11), wraplength=350)
        message_label.pack(pady=(0, 20))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack()
        
        # 按钮
        for i, button_text in enumerate(self.buttons):
            btn = ttk.Button(button_frame, text=button_text,
                           command=lambda text=button_text: self.button_click(text))
            btn.pack(side=tk.LEFT, padx=5)

    def get_icon_text(self) -> str:
        """获取图标文本"""
        icons = {
            'info': 'ℹ',
            'warning': '⚠',
            'error': '✗',
            'success': '✓',
            'question': '?'
        }
        return icons.get(self.icon, 'ℹ')

    def button_click(self, button_text: str):
        """按钮点击处理"""
        self.result = button_text
        self.dialog.destroy()

    def get_result(self) -> str:
        """获取对话框结果"""
        return self.result


class ModernMessageBox:
    """现代化消息框"""
    
    @staticmethod
    def show_info(parent, title: str, message: str):
        """显示信息对话框"""
        dialog = ModernDialog(parent, title, message, ['确定'], 'info')
        return dialog.get_result()

    @staticmethod
    def show_warning(parent, title: str, message: str):
        """显示警告对话框"""
        dialog = ModernDialog(parent, title, message, ['确定'], 'warning')
        return dialog.get_result()

    @staticmethod
    def show_error(parent, title: str, message: str):
        """显示错误对话框"""
        dialog = ModernDialog(parent, title, message, ['确定'], 'error')
        return dialog.get_result()

    @staticmethod
    def show_success(parent, title: str, message: str):
        """显示成功对话框"""
        dialog = ModernDialog(parent, title, message, ['确定'], 'success')
        return dialog.get_result()

    @staticmethod
    def ask_question(parent, title: str, message: str):
        """显示问题对话框"""
        dialog = ModernDialog(parent, title, message, ['是', '否'], 'question')
        return dialog.get_result()

    @staticmethod
    def ask_yes_no(parent, title: str, message: str):
        """显示是/否对话框"""
        dialog = ModernDialog(parent, title, message, ['是', '否'], 'question')
        result = dialog.get_result()
        return result == '是'

    @staticmethod
    def ask_ok_cancel(parent, title: str, message: str):
        """显示确定/取消对话框"""
        dialog = ModernDialog(parent, title, message, ['确定', '取消'], 'question')
        result = dialog.get_result()
        return result == '确定'
