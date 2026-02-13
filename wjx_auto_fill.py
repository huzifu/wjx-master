import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, scrolledtext, messagebox, filedialog
import ttkbootstrap as tb # 引入现代UI库
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame
import threading
import logging
import random
import webbrowser
import re
import sys
import os

# 尝试导入AIChatTab，如果失败则定义占位类，以防模块缺失导致崩溃
try:
    from ui.components.ai_chat_tab import AIChatTab
except ImportError:
    class AIChatTab(ttk.Frame):
        def __init__(self, master, **kwargs):
            if 'api_key_getter' in kwargs: del kwargs['api_key_getter']
            if 'api_service_getter' in kwargs: del kwargs['api_service_getter']
            if 'app_ref' in kwargs: del kwargs['app_ref']
            super().__init__(master, **kwargs)
            ttk.Label(self, text="AI 模块未找到 (ui.components.ai_chat_tab)").pack(pady=20)

# 添加配置目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
sys.path.append(os.path.join(current_dir, 'config', 'settings'))

try:
    # 优先使用绝对导入，避免linter无法解析
    from config.settings.logger_config import (
        setup_logging,
        get_logger,
        get_operation_logger,
        log_operation,
    )
except ImportError:
    # 使用动态导入避免静态分析器误报相对导入告警
    import importlib
    try:
        logger_config = importlib.import_module("logger_config")
        setup_logging = getattr(logger_config, "setup_logging")
        get_logger = getattr(logger_config, "get_logger")
        get_operation_logger = getattr(logger_config, "get_operation_logger")
        log_operation = getattr(logger_config, "log_operation")
    except Exception:
        # 最终兜底：使用基础日志实现，保证不因导入失败而中断
        def setup_logging(*args, **kwargs):
            logging.basicConfig(level=logging.INFO)
            return None

        def get_logger(name=None):
            return logging.getLogger(name)

        def get_operation_logger():
            return logging.getLogger("operation")

        def log_operation(name):
            def decorator(func):
                return func
            return decorator
from core.ai.ai_chat_tab import AIChatTab

# 导入新模块
try:
    from core.parser.questionnaire_parser import EnhancedQuestionnaireParser, MatrixScaleParser, ConfigParser
    from core.filler.questionnaire_filler import EnhancedQuestionnaireFiller
    from ui.components.ui_enhancer import ModernUI, ModernMessageBox
    from config.settings.config_manager import EnhancedConfigManager, ConfigUI
    # from system_monitor import SystemMonitor, PerformanceOptimizer  # 已删除
    from core.ai.ai_questionnaire_parser import ai_parse_questionnaire, AdvancedQuestionParser, MatrixQuestionParser
    NEW_MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"部分新模块导入失败: {e}")
    NEW_MODULES_AVAILABLE = False
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
import traceback
import time
import numpy as np
import requests
import openai
import json
from core.ai.ai_questionnaire_parser import ai_parse_questionnaire
import os
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, \
    ElementNotInteractableException
# from ttkthemes import ThemedTk  # 暂时注释掉，使用标准tkinter
from PIL import Image, ImageTk
# import sv_ttk  # 用于现代主题，暂时注释掉
import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
# ================== 配置参数 ==================
# 默认参数值
DEFAULT_CONFIG = {
    "url": "https://www.wjx.cn/vm/OaRP2BF.aspx",
    "target_num": 100,
    "min_duration":1,
    "max_duration":20,
    "weixin_ratio": 0.5,
    "min_delay": 1,
    "max_delay": 2,
    "submit_delay": 1,
    "page_load_delay": 2,
    "per_question_delay": (0.5, 1),
    "min_submit_gap": 5,  # 单份提交最小间隔（分钟）
    "max_submit_gap": 15,  # 单份提交最大间隔（分钟）
    "batch_size": 5,  # 每N份后暂停
    "batch_pause": 15,  # 批量暂停M分钟
    "per_page_delay": (2.0, 6.0),
    "enable_smart_gap": True,  # 智能提交间隔开关

    "headless": False,
    "parse_headless": True,  # 解析问卷时是否强制无头运行，避免弹出浏览器
    "parse_fast_mode": True,  # 优先尝试快速解析（requests+bs4），失败再用Selenium
    "parse_fast_timeout": 8,  # 快速解析超时（秒）
    "parse_cache_enabled": True,  # 同URL解析结果缓存
    "num_threads": 4,
    "use_ip": False,
    "ip_api": "https://service.ipzan.com/core-extract?num=1&minute=1&pool=quality&secret=YOUR_SECRET",
    "ip_change_mode": "per_submit",  # 新增, 可选: per_submit, per_batch
    "ip_change_batch": 5,  # 每N份切换, 仅per_batch有效


    # 单选题概率配置
    "single_prob": {
        "1": -1,  # -1表示随机选择
        "2": [0.3, 0.7],  # 数组表示每个选项的选择概率
        "3": [0.2, 0.2, 0.6]
    },
    "other_texts": {
        # 题号: [可选的其他文本1, 2, 3...]
        "4": ["自定义内容A", "自定义内容B", "自定义内容C"],
        "5": ["随便写点", "哈哈哈", "其他情况"]
    },
    # 多选题概率配置 - 增强版
    "multiple_prob": {
        "4": {
            "prob": [0.4, 0.3, 0.3],  # 每个选项被选中的概率
            "min_selection": 1,  # 最小选择项数
            "max_selection": 2  # 最大选择项数
        },
        "5": {
            "prob": [0.5, 0.5, 0.5, 0.5],
            "min_selection": 2,
            "max_selection": 3
        }
    },
    "ai_service": "质谱清言",
    "ai_fill_enabled": False,
    "openai_api_key": "",
    "qingyan_api_key": "",
    "ai_prompt_template": "请用简洁、自然的中文回答：{question}",
    # 矩阵题概率配置
    "matrix_prob": {
        "6": [0.2, 0.3, 0.5],  # 每行选项的选择概率
        "7": -1  # -1表示随机选择
    },

    # 量表题概率配置
    "scale_prob": {
        "8": [0.1, 0.2, 0.4, 0.2, 0.1],  # 每个刻度的选择概率
        "9": [0.2, 0.2, 0.2, 0.2, 0.2]
    },

    # 填空题答案配置
    "texts": {
        "10": ["示例答案1", "示例答案2", "示例答案3"],
        "11": ["回答A", "回答B", "回答C"]
    },

    # 多项填空配置
    "multiple_texts": {
        "12": [
            ["选项1", "选项2", "选项3"],
            ["选项A", "选项B", "选项C"]
        ]
    },

    # 排序题概率配置
    "reorder_prob": {
        "13": [0.4, 0.3, 0.2, 0.1],  # 每个位置的选择概率
        "14": [0.25, 0.25, 0.25, 0.25]
    },

    # 下拉框概率配置
    "droplist_prob": {
        "15": [0.3, 0.4, 0.3],  # 每个选项的选择概率
        "16": [0.5, 0.5]
    },

    # 题目文本存储
    "question_texts": {
        "1": "您的性别",
        "2": "您的年级",
        "3": "您每月的消费项目",
        "4": "您喜欢的运动",
        "5": "您的兴趣爱好",
        "6": "您对学校的满意度",
        "7": "您的专业课程评价",
        "8": "您的生活满意度",
        "9": "您的学习压力程度",
        "10": "您的姓名",
        "11": "您的联系方式",
        "12": "您的家庭信息",
        "13": "您喜欢的食物排序",
        "14": "您喜欢的电影类型排序",
        "15": "您的出生地",
        "16": "您的职业"
    },
    # 逻辑/约束规则（按题号配置）
    # 示例：
    # "logic_rules": {
    #   "3": {"must": ["是"], "avoid": ["否"], "min": 1, "max": 1, "prefer": ["是"]}
    # }
    "logic_rules": {},
    "page_load_timeout": 20,  # 页面加载超时时间(秒)
    "element_timeout": 10,# 元素查找超时时间(秒)
    # 选项文本存储
    "option_texts": {
        "1": ["男", "女"],
        "2": ["大一", "大二", "大三", "大四"],
        "3": ["伙食", "购置衣物", "交通通讯", "生活用品", "日常交际", "学习用品", "娱乐旅游", "其他"],
        "4": ["篮球", "足球", "游泳", "跑步", "羽毛球"],
        "5": ["阅读", "音乐", "游戏", "旅行", "摄影"],
        "6": ["非常满意", "满意", "一般", "不满意", "非常不满意"],
        "7": ["非常满意", "满意", "一般", "不满意", "非常不满意"],
        "8": ["非常满意", "满意", "一般", "不满意", "非常不满意"],
        "9": ["非常大", "较大", "一般", "较小", "没有压力"],
        "13": ["中餐", "西餐", "日料", "快餐"],
        "14": ["科幻", "动作", "喜剧", "爱情"],
        "15": ["北京", "上海", "广州", "深圳"],
        "16": ["学生", "上班族", "自由职业", "退休"]
    }
}


# ToolTip类用于显示题目提示
class ToolTip:
    def __init__(self, widget, text='', delay=300, wraplength=500):  # 减少延迟，增加宽度
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wraplength = wraplength
        self.tip_window = None
        self.id = None
        self.x = self.y = 0

        # 绑定事件
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<Motion>", self.motion)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def motion(self, event=None):
        self.x, self.y = event.x, event.y
        self.x += self.widget.winfo_rootx() + 25
        self.y += self.widget.winfo_rooty() + 20
        if self.tip_window:
            self.tip_window.geometry(f"+{self.x}+{self.y}")

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self):
        if self.tip_window:
            return
        # 创建提示窗口
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{self.x}+{self.y}")
        # 使用更明显的样式
        label = tk.Label(self.tip_window, text=self.text, justify=tk.LEFT,
                         background="#ffffff", relief=tk.SOLID, borderwidth=1,
                         wraplength=self.wraplength, padx=10, pady=5,
                         font=("Arial", 10))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


class WJXAutoFillApp:
    def __init__(self, root):
        self.after_ids = []
        self.root = root
        # 设置标题和图标
        self.root.title("智能表单自动填充系统 - Pro")
        try:
            self.root.iconbitmap("wjx_icon.ico")
        except:
            pass
            
        self.root.geometry("1400x900")
        
        # 使用 ttkbootstrap 样式
        # 如果 root 是 tb.Window, style 已经自动初始化。这里再次获取引用。
        self.style = tb.Style()
        
        # 全局字体配置 - 强制使用微软雅黑
        self.default_font = ("Microsoft YaHei UI", 10)
        self.style.configure('.', font=self.default_font)
        self.style.configure('TButton', font=self.default_font)
        self.style.configure('TLabel', font=self.default_font)
        self.style.configure('TEntry', font=self.default_font)
        self.style.configure('TLabelframe.Label', font=("Microsoft YaHei UI", 11, "bold"))
        self.style.configure('Treeview', font=self.default_font, rowheight=30)
        self.style.configure('Treeview.Heading', font=("Microsoft YaHei UI", 11, "bold"))
        
        # 初始化核心变量
        self.config = DEFAULT_CONFIG.copy()
        self.running = False
        self.paused = False
        self.cur_num = 0
        self.cur_fail = 0
        self.lock = threading.Lock()
        self.pause_event = threading.Event()
        self.tooltips = []
        self.parsing = False
        self.previous_url = None
        self.dynamic_prompt_list = None
        
        # 初始化新模块
        if NEW_MODULES_AVAILABLE:
            self.config_manager = EnhancedConfigManager()
            self.config = self.config_manager.config
            self.questionnaire_parser = EnhancedQuestionnaireParser()
            self.questionnaire_filler = EnhancedQuestionnaireFiller(self.config)
            self.modern_ui = ModernUI()
            logging.info("新模块已成功集成")
        else:
            logging.warning("新模块不可用，使用原有功能")
            self.config_manager = None
            self.questionnaire_parser = None
            self.questionnaire_filler = None
            self.modern_ui = None

        # 字体变量 (保留用于部分逻辑兼容)
        self.font_family = tk.StringVar(value="Microsoft YaHei UI")
        self.font_size = tk.IntVar(value=10)

        # 构建现代化UI
        self.setup_modern_ui()
        
        # 绑定字体更新
        self.font_family.trace_add("write", self.update_font)
        self.font_size.trace_add("write", self.update_font)
        
        # 初始化日志
        self.setup_logging()
        
        # 初始调整
        self.update_font()
    def setup_modern_ui(self):
        """构建现代化的三段式布局"""
        # 主容器
        main_container = tb.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 1. 顶部任务区
        self.create_top_task_area(main_container)
        
        # 2. 中部配置区
        self.create_middle_config_area(main_container)
        
        # 3. 底部控制区
        self.create_bottom_control_area(main_container)

    def create_top_task_area(self, parent):
        """顶部：问卷链接与解析"""
        task_frame = tb.Frame(parent)
        task_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 标题栏/Logo (可选)
        header = tb.Frame(task_frame)
        header.pack(fill=tk.X, pady=(0, 10))
        tb.Label(header, text="智能表单自动填充系统 Pro", font=("Microsoft YaHei UI", 16, "bold"), bootstyle="primary").pack(side=tk.LEFT)
        
        # 输入容器 (居中布局)
        input_container_outer = tb.Frame(task_frame)
        input_container_outer.pack(fill=tk.X, padx=20)
        
        input_container = tb.Labelframe(input_container_outer, text=" 第一步：解析问卷 ", padding=15, bootstyle="primary")
        input_container.pack(fill=tk.X, expand=True) # 保持宽但增加内部margins
        
        # 内部布局优化
        inner_frame = tb.Frame(input_container)
        inner_frame.pack(fill=tk.X, expand=True)
        
        tb.Label(inner_frame, text="🔗 问卷链接:", font=("Microsoft YaHei UI", 12)).pack(side=tk.LEFT, padx=(0, 10))
        
        self.url_var = tk.StringVar(value=self.config.get("url", ""))
        self.url_entry = tb.Entry(inner_frame, textvariable=self.url_var, font=("Microsoft YaHei UI", 12))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))
        
        # 解析按钮
        self.parse_btn = tb.Button(inner_frame, text="🔍 解析问卷", 
                                  bootstyle="primary", 
                                  command=self.parse_survey,
                                  width=15)
        self.parse_btn.pack(side=tk.LEFT, padx=5)

    def create_middle_config_area(self, parent):
        """中部：配置选项卡"""
        self.notebook = tb.Notebook(parent, bootstyle="primary")
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Tab 1: 题型设置
        self.question_frame = tb.Frame(self.notebook, padding=10)
        self.notebook.add(self.question_frame, text="📝 题型设置")
        
        # 加载题型设置UI
        try:
            from ui.components.wjx_question_settings_ui import WJXQuestionSettingsUI
            self.wjx_question_ui = WJXQuestionSettingsUI(self.question_frame, self.config)
            # show_header=False to avoid double title
            self.wjx_settings_frame = self.wjx_question_ui.create_question_settings_frame(self.question_frame, show_header=False)
            self._connect_ui_functions()
        except ImportError:
            tb.Label(self.question_frame, text="模块加载失败").pack()
            
        # Tab 2: 运行参数
        self.params_frame = tb.Frame(self.notebook, padding=10)
        self.notebook.add(self.params_frame, text="⚙️ 运行参数")
        # 滚动区域
        try:
            from ttkbootstrap.scrolled import ScrolledFrame
            self.params_scroll = ScrolledFrame(self.params_frame)
        except Exception:
             # Fallback if ScrolledFrame fails for some reason
            self.params_scroll = tb.Frame(self.params_frame)
            
        self.params_scroll.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.create_global_settings_content(self.params_scroll) 
        
        # Tab 3: AI 助手
        self.ai_frame = tb.Frame(self.notebook, padding=10)
        # self.notebook.add(self.ai_frame, text="🤖 AI 助手") 
        # Note: AIChatTab handles adding itself or works as a frame.
        # Checking old code: self.ai_chat_tab = AIChatTab(self.notebook, ...) -> self.notebook.add(self.ai_chat_tab, ...)
        
        self.ai_chat_tab = AIChatTab(
            self.notebook,
            api_key_getter=lambda: (
                self.openai_api_key_entry.get().strip() if self.ai_service.get() == "OpenAI"
                else self.qingyan_api_key_entry.get().strip()
            ),
            api_service_getter=lambda: self.ai_service.get(),
            app_ref=self
        )
        self.notebook.add(self.ai_chat_tab, text="💬 AI问卷助手")

        # Tab 4: 运行日志
        self.log_frame = tb.Frame(self.notebook, padding=10)
        self.notebook.add(self.log_frame, text="📋 运行日志")

    def create_global_settings_content(self, parent):
        """运行参数设置内容"""
        # 1. 基础设置
        base_lf = tb.Labelframe(parent, text="基础设置", padding=10, bootstyle="info")
        base_lf.pack(fill=tk.X, pady=(0, 10))
        
        grid_opts = {'padx': 5, 'pady': 5, 'sticky': tk.W}
        
        tb.Label(base_lf, text="目标份数:").grid(row=0, column=0, **grid_opts)
        self.target_entry = tb.Spinbox(base_lf, from_=1, to=10000, width=10)
        self.target_entry.grid(row=0, column=1, **grid_opts)
        self.target_entry.set(self.config["target_num"])
        
        tb.Label(base_lf, text="提交延迟(秒):").grid(row=0, column=2, **grid_opts)
        self.submit_delay = tb.Spinbox(base_lf, from_=1, to=10, width=10)
        self.submit_delay.grid(row=0, column=3, **grid_opts)
        self.submit_delay.set(self.config["submit_delay"])

        # 2. 延迟策略
        delay_lf = tb.Labelframe(parent, text="拟人化延迟策略 (秒)", padding=10, bootstyle="warning")
        delay_lf.pack(fill=tk.X, pady=(0, 10))
        
        # 基础延迟
        tb.Label(delay_lf, text="基础延迟:").grid(row=0, column=0, **grid_opts)
        self.min_delay = tb.Spinbox(delay_lf, from_=0.1, to=10, increment=0.1, width=5); self.min_delay.grid(row=0, column=1, **grid_opts); self.min_delay.set(self.config["min_delay"])
        tb.Label(delay_lf, text=" - ").grid(row=0, column=2); 
        self.max_delay = tb.Spinbox(delay_lf, from_=0.1, to=10, increment=0.1, width=5); self.max_delay.grid(row=0, column=3, **grid_opts); self.max_delay.set(self.config["max_delay"])

        # 每题延迟
        tb.Label(delay_lf, text="每题延迟:").grid(row=1, column=0, **grid_opts)
        self.min_q_delay = tb.Spinbox(delay_lf, from_=0.1, to=5, increment=0.1, width=5); self.min_q_delay.grid(row=1, column=1, **grid_opts); self.min_q_delay.set(self.config["per_question_delay"][0])
        tb.Label(delay_lf, text=" - ").grid(row=1, column=2); 
        self.max_q_delay = tb.Spinbox(delay_lf, from_=0.1, to=5, increment=0.1, width=5); self.max_q_delay.grid(row=1, column=3, **grid_opts); self.max_q_delay.set(self.config["per_question_delay"][1])
        
        # 页面延迟
        tb.Label(delay_lf, text="翻页延迟:").grid(row=2, column=0, **grid_opts)
        self.min_p_delay = tb.Spinbox(delay_lf, from_=0.1, to=10, increment=0.1, width=5); self.min_p_delay.grid(row=2, column=1, **grid_opts); self.min_p_delay.set(self.config["per_page_delay"][0])
        tb.Label(delay_lf, text=" - ").grid(row=2, column=2); 
        self.max_p_delay = tb.Spinbox(delay_lf, from_=0.1, to=10, increment=0.1, width=5); self.max_p_delay.grid(row=2, column=3, **grid_opts); self.max_p_delay.set(self.config["per_page_delay"][1])

        # 3. 智能间隔
        smart_lf = tb.Labelframe(parent, text="智能间隔与自动休息", padding=10, bootstyle="success")
        smart_lf.pack(fill=tk.X, pady=(0, 10))
        
        self.enable_smart_gap_var = tk.BooleanVar(value=self.config.get("enable_smart_gap", True))
        tb.Checkbutton(smart_lf, text="启用智能防封控策略", variable=self.enable_smart_gap_var, bootstyle="round-toggle").pack(anchor=tk.W, pady=5, padx=5)
        
        gap_frame = tb.Frame(smart_lf)
        gap_frame.pack(fill=tk.X, pady=5, padx=5)
        tb.Label(gap_frame, text="每提交 1 份，暂停").pack(side=tk.LEFT)
        self.min_submit_gap = tb.Spinbox(gap_frame, from_=1, to=120, width=5); self.min_submit_gap.pack(side=tk.LEFT, padx=5); self.min_submit_gap.set(self.config.get("min_submit_gap", 10))
        tb.Label(gap_frame, text="-").pack(side=tk.LEFT)
        self.max_submit_gap = tb.Spinbox(gap_frame, from_=1, to=180, width=5); self.max_submit_gap.pack(side=tk.LEFT, padx=5); self.max_submit_gap.set(self.config.get("max_submit_gap", 20))
        tb.Label(gap_frame, text="分钟").pack(side=tk.LEFT)
        
        # 4. 高级设置
        adv_lf = tb.Labelframe(parent, text="高级设置", padding=10, bootstyle="secondary")
        adv_lf.pack(fill=tk.X, pady=(0, 10))
        
        # 浏览器窗口数
        tb.Label(adv_lf, text="并发窗口:").grid(row=0, column=0, **grid_opts)
        self.num_threads = tb.Spinbox(adv_lf, from_=1, to=10, width=5)
        self.num_threads.grid(row=0, column=1, **grid_opts)
        self.num_threads.set(self.config["num_threads"])
        
        # 无头模式
        self.headless_var = tk.BooleanVar(value=self.config["headless"])
        tb.Checkbutton(adv_lf, text="无头模式(后台运行)", variable=self.headless_var, bootstyle="round-toggle").grid(row=0, column=2, columnspan=2, **grid_opts)
        
        # 代理IP
        self.use_ip_var = tk.BooleanVar(value=self.config["use_ip"])
        tb.Checkbutton(adv_lf, text="启用代理IP", variable=self.use_ip_var, bootstyle="round-toggle").grid(row=1, column=0, **grid_opts)
        
        self.ip_entry = tb.Entry(adv_lf, width=40)
        self.ip_entry.grid(row=1, column=1, columnspan=3, **grid_opts)
        self.ip_entry.insert(0, self.config["ip_api"])
        
        # 初始化 AI 变量 (隐藏但必要)
        self.ai_service = tb.Combobox(adv_lf, values=["质谱清言", "OpenAI"], width=10) # Hidden
        self.ai_service.set(self.config.get("ai_service", "质谱清言"))
        
        self.qingyan_api_key_entry = tb.Entry(adv_lf) 
        self.qingyan_api_key_entry.insert(0, self.config.get("api_key", "")) 
        
        self.openai_api_key_entry = tb.Entry(adv_lf)
        self.openai_api_key_entry.insert(0, self.config.get("openai_api_key", ""))
        
        # 保存按钮
        tb.Button(parent, text="💾 保存配置", command=self.on_save_config, bootstyle="success-outline").pack(pady=20)


    def create_bottom_control_area(self, parent):
        """底部状态与控制"""
        control_panel = tb.Frame(parent, bootstyle="light")
        control_panel.pack(fill=tk.X, pady=(0, 0))
        
        # 状态指示
        status_frame = tb.Frame(control_panel)
        status_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        self.main_status_var = tk.StringVar(value="就绪")
        tb.Label(status_frame, text="状态:", font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        self.main_status_label = tb.Label(status_frame, textvariable=self.main_status_var, 
                font=("Microsoft YaHei UI", 12, "bold"), bootstyle="success")
        self.main_status_label.pack(side=tk.LEFT, padx=5)

         # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = tb.Progressbar(status_frame, variable=self.progress_var, 
                                          maximum=100, length=200, bootstyle="success-striped")
        self.progress_bar.pack(side=tk.LEFT, padx=15)
        
        self.percent_var = tk.StringVar(value="0.0%")
        tb.Label(status_frame, textvariable=self.percent_var).pack(side=tk.LEFT, padx=5)

        # 统计数据
        stat_frame = tb.Frame(control_panel)
        stat_frame.pack(side=tk.LEFT, padx=20)
        tb.Label(stat_frame, text="✅ 成功:", bootstyle="success").pack(side=tk.LEFT)
        self.success_count_var = tk.StringVar(value="0")
        tb.Label(stat_frame, textvariable=self.success_count_var, font=("Impact", 14), bootstyle="success").pack(side=tk.LEFT, padx=2)
        
        tb.Label(stat_frame, text="❌ 失败:", bootstyle="danger").pack(side=tk.LEFT, padx=(10, 0))
        self.fail_count_var = tk.StringVar(value="0")
        tb.Label(stat_frame, textvariable=self.fail_count_var, font=("Impact", 14), bootstyle="danger").pack(side=tk.LEFT, padx=2)

        # 控制按钮 (右停靠)
        btn_frame = tb.Frame(control_panel)
        btn_frame.pack(side=tk.RIGHT, padx=10, pady=10)
        
        self.start_btn = tb.Button(btn_frame, text="▶ 开始运行", bootstyle="success", width=12,
                                  command=self.start_filling)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_btn = tb.Button(btn_frame, text="⏸ 暂停", bootstyle="warning", width=8,
                                  command=self.toggle_pause, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tb.Button(btn_frame, text="⏹ 停止", bootstyle="danger", width=8,
                                 command=self.stop_filling, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

    def create_log_area(self):
        """创建现代化的日志显示区域"""
        # 日志控制面板
        log_control_frame = ttk.Frame(self.log_frame)
        log_control_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        # 左侧标题
        title_frame = ttk.Frame(log_control_frame)
        title_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        title_label = ttk.Label(title_frame, text="📋 运行日志", 
                                font=("微软雅黑", 12, "bold"), foreground="#2c3e50")
        title_label.pack(side=tk.LEFT)
        
        # 日志统计信息
        stats_frame = ttk.Frame(title_frame)
        stats_frame.pack(side=tk.LEFT, padx=(15, 0))
        
        self.log_stats_var = tk.StringVar(value="日志条数: 0")
        stats_label = ttk.Label(stats_frame, textvariable=self.log_stats_var,
                               font=("微软雅黑", 9), foreground="#7f8c8d")
        stats_label.pack(side=tk.LEFT)
        
        # 右侧控制按钮
        btn_frame = ttk.Frame(log_control_frame)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 日志级别过滤
        filter_frame = ttk.Frame(btn_frame)
        filter_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(filter_frame, text="级别:", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.log_level_var = tk.StringVar(value="ALL")
        level_combo = ttk.Combobox(filter_frame, textvariable=self.log_level_var,
                                   values=["ALL", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                   width=8, state="readonly", font=("微软雅黑", 9))
        level_combo.pack(side=tk.LEFT, padx=(5, 0))
        level_combo.bind("<<ComboboxSelected>>", self.filter_logs)
        
        # 控制按钮
        self.clear_log_btn = ttk.Button(btn_frame, text="🗑️ 清空", 
                                       command=self.clear_log, width=8)
        self.clear_log_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.export_log_btn = ttk.Button(btn_frame, text="📤 导出", 
                                        command=self.export_log, width=8)
        self.export_log_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_cb = ttk.Checkbutton(btn_frame, text="自动滚动", 
                                        variable=self.auto_scroll_var)
        auto_scroll_cb.pack(side=tk.LEFT, padx=(0, 5))
        
        # 分隔线
        ttk.Separator(self.log_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=5)
        
        # 日志文本区域 - 现代化设计
        log_container = ttk.Frame(self.log_frame)
        log_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 创建带行号的日志区域
        self.create_log_text_with_line_numbers(log_container)
        
        # 底部状态栏
        status_frame = ttk.Frame(self.log_frame)
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.log_status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(status_frame, textvariable=self.log_status_var,
                                font=("微软雅黑", 9), foreground="#7f8c8d")
        status_label.pack(side=tk.LEFT)
        
        # 日志文件路径显示
        self.log_file_var = tk.StringVar(value="日志文件: 未保存")
        file_label = ttk.Label(status_frame, textvariable=self.log_file_var,
                              font=("微软雅黑", 9), foreground="#7f8c8d")
        file_label.pack(side=tk.RIGHT)
    def create_log_text_with_line_numbers(self, parent):
        """创建带行号的日志文本区域"""
        # 创建水平框架
        h_frame = ttk.Frame(parent)
        h_frame.pack(fill=tk.BOTH, expand=True)
        
        # 行号区域
        self.line_numbers = tk.Text(h_frame, width=4, padx=3, pady=5, takefocus=0,
                                   border=0, background='#f0f0f0', state='disabled',
                                   font=("Consolas", 9))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # 分隔线
        separator = ttk.Separator(h_frame, orient=tk.VERTICAL)
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        # 日志文本区域
        self.log_area = scrolledtext.ScrolledText(h_frame, height=12, 
                                                 font=("Consolas", 9),
                                                 background='#ffffff',
                                                 selectbackground='#0078d4',
                                                 insertbackground='#000000')
        self.log_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 绑定滚动事件
        self.log_area.bind('<Key>', self.on_log_key)
        self.log_area.bind('<Button-1>', self.on_log_click)
        self.log_area.bind('<MouseWheel>', self.on_log_scroll)
        
        # 配置标签样式
        self.log_area.tag_configure("INFO", foreground="#000000")
        self.log_area.tag_configure("WARNING", foreground="#ff8c00")
        self.log_area.tag_configure("ERROR", foreground="#d13438")
        self.log_area.tag_configure("CRITICAL", foreground="#d13438", background="#ffebee")
        
        # 初始化行号
        self.update_line_numbers()
        
        # 设置只读
        self.log_area.config(state=tk.DISABLED)
        
        # 初始化日志计数器
        self.log_count = 0
        self.filtered_logs = []

    def update_line_numbers(self):
        """更新行号显示"""
        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete(1.0, tk.END)
        
        # 获取日志区域的行数
        line_count = self.log_area.index('end-1c').split('.')[0]
        if line_count == '0':
            return
            
        # 添加行号
        for i in range(1, int(line_count) + 1):
            self.line_numbers.insert(tk.END, f"{i}\n")
        
        self.line_numbers.config(state=tk.DISABLED)

    def on_log_key(self, event):
        """处理日志区域的键盘事件"""
        # 禁用编辑
        return "break"

    def on_log_click(self, event):
        """处理日志区域的点击事件"""
        # 保持光标在末尾
        self.log_area.see(tk.END)

    def on_log_scroll(self, event):
        """处理日志区域的滚动事件"""
        # 同步行号滚动
        self.line_numbers.yview_moveto(self.log_area.yview()[0])

    def filter_logs(self, event=None):
        """根据级别过滤日志"""
        level = self.log_level_var.get()
        if level == "ALL":
            # 显示所有日志
            self.log_area.config(state=tk.NORMAL)
            self.log_area.delete(1.0, tk.END)
            for log_entry in self.filtered_logs:
                self.log_area.insert(tk.END, log_entry['text'] + '\n', log_entry['level'])
            self.log_area.config(state=tk.DISABLED)
        else:
            # 过滤指定级别
            self.log_area.config(state=tk.NORMAL)
            self.log_area.delete(1.0, tk.END)
            for log_entry in self.filtered_logs:
                if log_entry['level'] == level:
                    self.log_area.insert(tk.END, log_entry['text'] + '\n', log_entry['level'])
            self.log_area.config(state=tk.DISABLED)
        
        self.update_line_numbers()
        if self.auto_scroll_var.get():
            self.log_area.see(tk.END)


    def setup_logging(self):
        """配置现代化的日志系统"""
        # 确保日志目录
        try:
            os.makedirs('logs', exist_ok=True)
        except Exception:
            pass

        # 清理已有处理器，避免重复输出
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        for h in list(root_logger.handlers):
            root_logger.removeHandler(h)

        # 控制台与文件处理器
        console_handler = logging.StreamHandler(sys.stdout)
        file_handler = None
        try:
            file_handler = logging.FileHandler('logs/system.log', encoding='utf-8')
        except Exception:
            file_handler = None
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        if file_handler:
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # 文本区域处理器（写入到界面）
        class TextHandler(logging.Handler):
            def __init__(self, app):
                super().__init__()
                self.app = app
                self.setFormatter(formatter)

            def emit(self, record):
                try:
                    msg = self.format(record)
                    level = record.levelname

                    def append():
                        try:
                            # 写入内部缓存，便于过滤
                            self.app.filtered_logs.append({'level': level, 'text': msg})
                            self.app.log_count += 1
                            if hasattr(self.app, 'log_stats_var'):
                                self.app.log_stats_var.set(f"日志条数: {self.app.log_count}")

                            # 写入文本区域
                            self.app.log_area.config(state=tk.NORMAL)
                            tag = level if level in ["INFO", "WARNING", "ERROR", "CRITICAL"] else "INFO"
                            self.app.log_area.insert(tk.END, msg + '\n', tag)
                            self.app.log_area.config(state=tk.DISABLED)

                            # 自动滚动与行号
                            if getattr(self.app, 'auto_scroll_var', None) and self.app.auto_scroll_var.get():
                                self.app.log_area.see(tk.END)
                            self.app.update_line_numbers()
                        except Exception:
                            pass

                    # 切回主线程安全更新
                    try:
                        self.app.root.after(0, append)
                    except Exception:
                        append()
                except Exception:
                    pass

        ui_handler = TextHandler(self)
        root_logger.addHandler(ui_handler)

    def create_global_settings(self):
        """创建全局设置界面，包括智能提交间隔和批量休息设置，并支持鼠标滚轮滚动（支持字体字号手输且自动校验）"""
        frame = self.global_frame
        padx, pady = 8, 5

        # 创建滚动条
        canvas = tk.Canvas(frame, background='#f0f0f0')
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='TFrame')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 鼠标滚轮支持（跨平台）
        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        # ======== 界面显示设置 ========
        font_frame = ttk.LabelFrame(scrollable_frame, text="🎨 界面显示设置")
        font_frame.grid(row=0, column=0, columnspan=2, padx=padx, pady=pady, sticky=tk.EW)

        # 第一行：字体选择
        font_row1 = ttk.Frame(font_frame)
        font_row1.pack(fill=tk.X, padx=15, pady=(15, 10))

        ttk.Label(font_row1, text="字体选择:",
                  font=("微软雅黑", 10, "bold"), foreground="#2c6fbb").pack(side=tk.LEFT, padx=(0, 10))

        # 常用字体列表（优化排序，楷体优先）
        common_fonts = ["楷体", "微软雅黑", "宋体", "黑体", "Arial", "Times New Roman"]
        font_options = common_fonts + [f for f in sorted(tkfont.families()) if f not in common_fonts]

        self.font_menu = ttk.Combobox(font_row1, textvariable=self.font_family,
                                      values=font_options, width=20, state="normal", font=("微软雅黑", 9))
        self.font_menu.pack(side=tk.LEFT, padx=(0, 20))
        self.font_menu.set("楷体")
        self.font_menu.bind("<FocusOut>", self._validate_font_family)
        self.font_menu.bind("<<ComboboxSelected>>", self._validate_font_family)

        # 第二行：字体大小控制
        font_row2 = ttk.Frame(font_frame)
        font_row2.pack(fill=tk.X, padx=15, pady=(0, 10))

        ttk.Label(font_row2, text="字体大小:",
                  font=("微软雅黑", 10, "bold"), foreground="#2c6fbb").pack(side=tk.LEFT, padx=(0, 10))

        # 字体大小滑块
        self.font_size_scale = ttk.Scale(font_row2, from_=8, to=20, orient=tk.HORIZONTAL,
                                         length=200, value=12)
        self.font_size_scale.pack(side=tk.LEFT, padx=(0, 10))
        self.font_size_scale.set(12)

        # 字体大小数值显示
        self.font_size_var = tk.StringVar(value="12")
        size_label = ttk.Label(font_row2, textvariable=self.font_size_var,
                               font=("微软雅黑", 10, "bold"), foreground="#2980b9", width=4)
        size_label.pack(side=tk.LEFT, padx=(0, 20))

        # 绑定字体大小变化事件
        def update_font_size_display(*args):
            size = int(self.font_size_scale.get())
            self.font_size_var.set(str(size))
            self.font_size.set(size)
            self.update_font()

        self.font_size_scale.bind("<Motion>", update_font_size_display)
        self.font_size_scale.bind("<ButtonRelease-1>", update_font_size_display)

        # 第三行：快速设置按钮
        font_row3 = ttk.Frame(font_frame)
        font_row3.pack(fill=tk.X, padx=15, pady=(0, 10))

        ttk.Label(font_row3, text="快速设置:",
                  font=("微软雅黑", 10, "bold"), foreground="#2c6fbb").pack(side=tk.LEFT, padx=(0, 10))

        # 创建快速设置按钮框架
        quick_btn_frame = ttk.Frame(font_row3)
        quick_btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 简化的快速设置按钮
        for size, text in [(10, "小"), (12, "中"), (14, "大")]:
            btn = ttk.Button(quick_btn_frame, text=text, width=8,
                             command=lambda s=size: self.quick_set_font_size(s))
            btn.pack(side=tk.LEFT, padx=(0, 8))

        # 保持原有的Spinbox用于兼容性
        self.font_size_spinbox = ttk.Spinbox(
            font_frame, from_=8, to=20, increment=1,
            textvariable=self.font_size, width=5,
            validate='focusout',
            validatecommand=(font_frame.register(self._validate_font_size), '%P')
        )
        self.font_size_spinbox.pack_forget()  # 隐藏但保留

        # ======== 问卷设置 ========
        survey_frame = ttk.LabelFrame(scrollable_frame, text="问卷设置")
        survey_frame.grid(row=1, column=0, columnspan=2, padx=padx, pady=pady, sticky=tk.EW)

        ttk.Label(survey_frame, text="问卷链接:").grid(row=0, column=0, padx=padx, pady=pady, sticky=tk.W)
        self.url_entry = ttk.Entry(survey_frame, width=50)
        self.url_entry.grid(row=0, column=1, columnspan=3, padx=padx, pady=pady, sticky=tk.EW)
        self.url_entry.insert(0, self.config["url"])

        ttk.Label(survey_frame, text="目标份数:").grid(row=1, column=0, padx=padx, pady=pady, sticky=tk.W)
        self.target_entry = ttk.Spinbox(survey_frame, from_=1, to=10000, width=8)
        self.target_entry.grid(row=1, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.target_entry.set(self.config["target_num"])

        ttk.Label(survey_frame, text="微信作答比率:").grid(row=1, column=2, padx=padx, pady=pady, sticky=tk.W)
        self.ratio_scale = ttk.Scale(survey_frame, from_=0, to=1, orient=tk.HORIZONTAL, length=100)
        self.ratio_scale.grid(row=1, column=3, padx=padx, pady=pady, sticky=tk.EW)
        self.ratio_scale.set(self.config["weixin_ratio"])
        self.ratio_var = tk.StringVar()
        self.ratio_var.set(f"{self.config['weixin_ratio'] * 100:.0f}%")
        ratio_label = ttk.Label(survey_frame, textvariable=self.ratio_var, width=4)
        ratio_label.grid(row=1, column=4, padx=(0, padx), pady=pady, sticky=tk.W)
        self.ratio_scale.bind("<Motion>", self.update_ratio_display)
        self.ratio_scale.bind("<ButtonRelease-1>", self.update_ratio_display)

        ttk.Label(survey_frame, text="作答时长(秒):").grid(row=2, column=0, padx=padx, pady=pady, sticky=tk.W)
        ttk.Label(survey_frame, text="最短:").grid(row=2, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.min_duration = ttk.Spinbox(survey_frame, from_=5, to=300, width=5)
        self.min_duration.grid(row=2, column=2, padx=padx, pady=pady, sticky=tk.W)
        self.min_duration.set(self.config["min_duration"])
        ttk.Label(survey_frame, text="最长:").grid(row=2, column=3, padx=padx, pady=pady, sticky=tk.W)
        self.max_duration = ttk.Spinbox(survey_frame, from_=5, to=300, width=5)
        self.max_duration.grid(row=2, column=4, padx=padx, pady=pady, sticky=tk.W)
        self.max_duration.set(self.config["max_duration"])

        # ======== 延迟设置 ========
        delay_frame = ttk.LabelFrame(scrollable_frame, text="延迟设置")
        delay_frame.grid(row=2, column=0, columnspan=2, padx=padx, pady=pady, sticky=tk.EW)
        ttk.Label(delay_frame, text="基础延迟(秒):").grid(row=0, column=0, padx=padx, pady=pady, sticky=tk.W)
        ttk.Label(delay_frame, text="最小:").grid(row=0, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.min_delay = ttk.Spinbox(delay_frame, from_=0.1, to=10, increment=0.1, width=5)
        self.min_delay.grid(row=0, column=2, padx=padx, pady=pady, sticky=tk.W)
        self.min_delay.set(self.config["min_delay"])
        ttk.Label(delay_frame, text="最大:").grid(row=0, column=3, padx=padx, pady=pady, sticky=tk.W)
        self.max_delay = ttk.Spinbox(delay_frame, from_=0.1, to=10, increment=0.1, width=5)
        self.max_delay.grid(row=0, column=4, padx=padx, pady=pady, sticky=tk.W)
        self.max_delay.set(self.config["max_delay"])

        ttk.Label(delay_frame, text="每题延迟(秒):").grid(row=1, column=0, padx=padx, pady=pady, sticky=tk.W)
        ttk.Label(delay_frame, text="最小:").grid(row=1, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.min_q_delay = ttk.Spinbox(delay_frame, from_=0.1, to=5, increment=0.1, width=5)
        self.min_q_delay.grid(row=1, column=2, padx=padx, pady=pady, sticky=tk.W)
        self.min_q_delay.set(self.config["per_question_delay"][0])
        ttk.Label(delay_frame, text="最大:").grid(row=1, column=3, padx=padx, pady=pady, sticky=tk.W)
        self.max_q_delay = ttk.Spinbox(delay_frame, from_=0.1, to=5, increment=0.1, width=5)
        self.max_q_delay.grid(row=1, column=4, padx=padx, pady=pady, sticky=tk.W)
        self.max_q_delay.set(self.config["per_question_delay"][1])

        ttk.Label(delay_frame, text="页面延迟(秒):").grid(row=2, column=0, padx=padx, pady=pady, sticky=tk.W)
        ttk.Label(delay_frame, text="最小:").grid(row=2, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.min_p_delay = ttk.Spinbox(delay_frame, from_=0.1, to=10, increment=0.1, width=5)
        self.min_p_delay.grid(row=2, column=2, padx=padx, pady=pady, sticky=tk.W)
        self.min_p_delay.set(self.config["per_page_delay"][0])
        ttk.Label(delay_frame, text="最大:").grid(row=2, column=3, padx=padx, pady=pady, sticky=tk.W)
        self.max_p_delay = ttk.Spinbox(delay_frame, from_=0.1, to=10, increment=0.1, width=5)
        self.max_p_delay.grid(row=2, column=4, padx=padx, pady=pady, sticky=tk.W)
        self.max_p_delay.set(self.config["per_page_delay"][1])

        ttk.Label(delay_frame, text="提交延迟:").grid(row=3, column=0, padx=padx, pady=pady, sticky=tk.W)
        self.submit_delay = ttk.Spinbox(delay_frame, from_=1, to=10, width=5)
        self.submit_delay.grid(row=3, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.submit_delay.set(self.config["submit_delay"])

        # ======== 智能提交间隔设置 ========
        smart_gap_frame = ttk.LabelFrame(scrollable_frame, text="智能提交间隔")
        smart_gap_frame.grid(row=3, column=0, columnspan=2, padx=padx, pady=pady, sticky=tk.EW)
        self.enable_smart_gap_var = tk.BooleanVar(value=self.config.get("enable_smart_gap", True))
        smart_gap_switch = ttk.Checkbutton(
            smart_gap_frame, text="开启智能提交间隔与批量休息", variable=self.enable_smart_gap_var)
        smart_gap_switch.grid(row=0, column=0, padx=padx, pady=pady, sticky=tk.W, columnspan=5)
        ttk.Label(smart_gap_frame, text="单份提交间隔(分钟):").grid(row=1, column=0, padx=padx, pady=pady, sticky=tk.W)
        self.min_submit_gap = ttk.Spinbox(smart_gap_frame, from_=1, to=120, width=5)
        self.min_submit_gap.grid(row=1, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.min_submit_gap.set(self.config.get("min_submit_gap", 10))
        ttk.Label(smart_gap_frame, text="~").grid(row=1, column=2, padx=2, pady=pady, sticky=tk.W)
        self.max_submit_gap = ttk.Spinbox(smart_gap_frame, from_=1, to=180, width=5)
        self.max_submit_gap.grid(row=1, column=3, padx=padx, pady=pady, sticky=tk.W)
        self.max_submit_gap.set(self.config.get("max_submit_gap", 20))
        ttk.Label(smart_gap_frame, text="每").grid(row=2, column=0, padx=padx, pady=pady, sticky=tk.W)
        self.batch_size = ttk.Spinbox(smart_gap_frame, from_=1, to=100, width=5)
        self.batch_size.grid(row=2, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.batch_size.set(self.config.get("batch_size", 5))
        ttk.Label(smart_gap_frame, text="份后暂停").grid(row=2, column=2, padx=2, pady=pady, sticky=tk.W)
        self.batch_pause = ttk.Spinbox(smart_gap_frame, from_=1, to=120, width=5)
        self.batch_pause.grid(row=2, column=3, padx=padx, pady=pady, sticky=tk.W)
        self.batch_pause.set(self.config.get("batch_pause", 15))
        ttk.Label(smart_gap_frame, text="分钟").grid(row=2, column=4, padx=2, pady=pady, sticky=tk.W)

        # ======== 高级设置 ========
        self.advanced_frame = ttk.LabelFrame(scrollable_frame, text="高级设置")
        self.advanced_frame.grid(row=4, column=0, columnspan=2, padx=padx, pady=pady, sticky=tk.EW)

        # 第0行：浏览器窗口数量
        ttk.Label(self.advanced_frame, text="浏览器窗口数量:").grid(row=0, column=0, padx=padx, pady=pady, sticky=tk.W)
        self.num_threads = ttk.Spinbox(self.advanced_frame, from_=1, to=10, width=5)
        self.num_threads.grid(row=0, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.num_threads.set(self.config["num_threads"])

        # 第1行：代理IP设置
        self.use_ip_var = tk.BooleanVar(value=self.config["use_ip"])
        ttk.Checkbutton(self.advanced_frame, text="使用代理IP", variable=self.use_ip_var).grid(
            row=1, column=0, padx=padx, pady=pady, sticky=tk.W)
        ttk.Label(self.advanced_frame, text="IP API:").grid(row=1, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.ip_entry = ttk.Entry(self.advanced_frame, width=40)
        self.ip_entry.grid(row=1, column=2, columnspan=3, padx=padx, pady=pady, sticky=tk.EW)
        self.ip_entry.insert(0, self.config["ip_api"])

        # 第2行：代理切换设置
        ttk.Label(self.advanced_frame, text="代理切换:").grid(row=2, column=0, padx=padx, pady=pady, sticky=tk.W)
        self.ip_change_mode = ttk.Combobox(self.advanced_frame, values=["per_submit", "per_batch"], width=12)
        self.ip_change_mode.grid(row=2, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.ip_change_mode.set(self.config.get("ip_change_mode", "per_submit"))
        ttk.Label(self.advanced_frame, text="每N份切换:").grid(row=2, column=2, padx=padx, pady=pady, sticky=tk.W)
        self.ip_change_batch = ttk.Spinbox(self.advanced_frame, from_=1, to=100, width=5)
        self.ip_change_batch.grid(row=2, column=3, padx=padx, pady=pady, sticky=tk.W)
        self.ip_change_batch.set(self.config.get("ip_change_batch", 5))

        # 第3行：无头模式设置
        self.headless_var = tk.BooleanVar(value=self.config["headless"])
        ttk.Checkbutton(self.advanced_frame, text="无头模式(不显示浏览器)", variable=self.headless_var).grid(
            row=3, column=0, padx=padx, pady=pady, sticky=tk.W)

        # 第4行：启用AI答题
        self.ai_fill_var = tk.BooleanVar(value=self.config.get("ai_fill_enabled", False))
        ttk.Checkbutton(self.advanced_frame, text="启用AI自动答题（填空题）", variable=self.ai_fill_var).grid(
            row=4, column=0, padx=padx, pady=pady, sticky=tk.W, columnspan=2)

        # ======== AI服务设置 ========
        # 第5行：AI服务选择
        ttk.Label(self.advanced_frame, text="AI服务:").grid(row=5, column=0, padx=padx, pady=pady, sticky=tk.W)
        self.ai_service = ttk.Combobox(self.advanced_frame, values=["质谱清言", "OpenAI"], width=10)
        self.ai_service.grid(row=5, column=1, padx=padx, pady=pady, sticky=tk.W)
        self.ai_service.set(self.config.get("ai_service", "质谱清言"))

        # 第6行：质谱清言API Key
        # 使用正确的变量名 - 删除_label后缀
        self.qingyan_api_key_label = ttk.Label(self.advanced_frame, text="质谱清言 API Key:")  # 添加此行
        self.qingyan_api_key_label.grid(row=6, column=0, padx=padx, pady=pady, sticky=tk.W)
        self.qingyan_api_key_entry = ttk.Entry(self.advanced_frame, width=40)
        self.qingyan_api_key_entry.grid(row=6, column=1, columnspan=2, padx=padx, pady=pady, sticky=tk.EW)

        # 获取API Key链接（放在质谱清言行）
        self.api_link = ttk.Label(self.advanced_frame, text="获取API Key", foreground="blue", cursor="hand2")  # 添加此行
        self.api_link.grid(row=6, column=3, padx=5, pady=pady)
        self.api_link.bind("<Button-1>", lambda e: webbrowser.open("https://open.bigmodel.cn/usercenter/apikeys"))

        # 第7行：OpenAI API Key
        # 使用正确的变量名 - 删除_label后缀
        self.openai_api_key_label = ttk.Label(self.advanced_frame, text="OpenAI API Key:")  # 添加此行
        self.openai_api_key_label.grid(row=7, column=0, padx=padx, pady=pady, sticky=tk.W)
        self.openai_api_key_entry = ttk.Entry(self.advanced_frame, width=40)
        self.openai_api_key_entry.grid(row=7, column=1, columnspan=2, padx=padx, pady=pady, sticky=tk.EW)

        # 第8行：AI答题Prompt模板
        self.ai_prompt_label = ttk.Label(self.advanced_frame, text="AI答题Prompt模板:")  # 添加此行
        self.ai_prompt_label.grid(row=8, column=0, padx=padx, pady=pady, sticky=tk.W)
        self.ai_prompt_var = tk.StringVar()
        self.ai_prompt_combobox = ttk.Combobox(
            self.advanced_frame, textvariable=self.ai_prompt_var, width=60, state="normal"
        )
        self.ai_prompt_combobox.grid(row=8, column=1, columnspan=2, padx=padx, pady=pady, sticky=tk.EW)
        self.ai_prompt_combobox['values'] = [
            self.config.get("ai_prompt_template", "请用简洁、自然的中文回答：{question}")]
        self.ai_prompt_combobox.set(self.config.get("ai_prompt_template", "请用简洁、自然的中文回答：{question}"))

        # 重新生成Prompt按钮
        self.refresh_prompt_btn = ttk.Button(  # 添加此行
            self.advanced_frame, text="重新生成Prompt(质谱清言)",
            command=self.on_refresh_qingyan_prompts
        )
        self.refresh_prompt_btn.grid(row=8, column=3, padx=5, pady=pady)

        # ======== 操作按钮 ========
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky=tk.W)
        self.save_btn = ttk.Button(button_frame, text="保存配置", command=self.on_save_config, width=15)
        self.save_btn.grid(row=0, column=2, padx=5)
        self.parse_btn = ttk.Button(button_frame, text="解析问卷", command=self.parse_survey, width=15)
        self.parse_btn.grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="重置默认", command=self.reset_defaults, width=15).grid(row=0, column=1, padx=5)
        scrollable_frame.columnconfigure(0, weight=1)
        tip_label = ttk.Label(scrollable_frame, text="提示: 填写前请先解析问卷以获取题目结构", style='Warning.TLabel')
        tip_label.grid(row=6, column=0, columnspan=2, pady=(10, 0))

        # 添加AI服务切换事件绑定
        self.ai_service.bind("<<ComboboxSelected>>", self.on_ai_service_change)
        # 初始化UI状态
        self.on_ai_service_change()

    def on_ai_service_change(self, event=None):
        """动态显示/隐藏API Key输入框 - 修复版"""
        service = self.ai_service.get()

        # 使用grid_forget()完全移除旧布局
        self.qingyan_api_key_label.grid_forget()
        self.qingyan_api_key_entry.grid_forget()
        self.api_link.grid_forget()
        self.openai_api_key_label.grid_forget()
        self.openai_api_key_entry.grid_forget()

        if service == "OpenAI":
            # 重新布局OpenAI相关控件
            self.openai_api_key_label.grid(row=7, column=0, padx=5, pady=5, sticky=tk.W)
            self.openai_api_key_entry.grid(row=7, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

            # 修改提示文本
            self.refresh_prompt_btn.config(text="重新生成Prompt(OpenAI)")
        else:
            # 重新布局质谱清言相关控件
            self.qingyan_api_key_label.grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)
            self.qingyan_api_key_entry.grid(row=6, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
            self.api_link.grid(row=6, column=3, padx=5, pady=5)

            # 恢复按钮文本
            self.refresh_prompt_btn.config(text="重新生成Prompt(质谱清言)")

        # 确保布局更新
        self.advanced_frame.update_idletasks()
    def _validate_font_family(self, event=None):
        family = self.font_family.get()
        valid_families = set(tkfont.families())
        # 限长防止撑界面
        if len(family) > 32:
            family = family[:32]
            self.font_family.set(family)
        if family not in valid_families:
            self.font_family.set("楷体")

    def _validate_font_size(self, value):
        """验证字体大小输入"""
        try:
            if value == '':
                return True  # 允许空值（编辑过程中）
            size = int(value)
            return 8 <= size <= 20  # 限制字体大小范围
        except ValueError:
            return False

    def run_ai_structured_analysis(self):
        api_key = self.qingyan_api_key_entry.get().strip()
        # 采集问卷结构
        qlist = []
        for qid, qtext in self.config["question_texts"].items():
            opts = self.config["option_texts"].get(qid, [])
            qlist.append({"text": qtext, "options": opts})
        ai_result = ai_parse_questionnaire(qlist, api_key)
        # ai_result["questions"]、ai_result["dimensions"] 可直接用于自动填充题型设置和维度分组
        # 你可以自动刷新界面，用AI推荐的题型/分组/配置覆盖现有设置，或者让用户确认
        # 也支持将json结构显示在AI分析tab
        self.ai_analysis_text.delete(1.0, "end")
        self.ai_analysis_text.insert("end", json.dumps(ai_result, ensure_ascii=False, indent=2))

    def on_refresh_qingyan_prompts(self):
        """生成Prompt - 优化版（带状态提示和错误处理）"""
        api_key = self.qingyan_api_key_entry.get().strip()
        if not api_key:
            messagebox.showerror("错误", "请先填写质谱清言API Key")
            return

        # 获取题目文本（最多15题）
        q_texts = list(self.config.get("question_texts", {}).values())[:15]
        if not q_texts:
            messagebox.showerror("错误", "请先解析问卷获取题目")
            return

        # 更新UI状态
        self.main_status_var.set("AI正在生成Prompt...")
        self.main_status_label.config(foreground="orange")
        self.root.update()

        # 禁用按钮防止重复点击
        self.parse_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)

        # 显示加载动画
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start()

        def worker():
            try:
                prompt_list = self.generate_prompt_templates_by_qingyan(q_texts, api_key)

                self.root.after(0, lambda: self._update_prompt_list(prompt_list))
                self.root.after(0, lambda: self.main_status_var.set("Prompt生成成功"))
                self.root.after(0, lambda: self.main_status_label.config(foreground="green"))
                self.root.after(0, lambda: messagebox.showinfo("成功", f"已生成{len(prompt_list)}条Prompt模板"))

            except Exception as e:
                error_msg = f"生成Prompt失败: {str(e)}"
                self.root.after(0, lambda: self.main_status_var.set("生成失败"))
                self.root.after(0, lambda: self.main_status_label.config(foreground="red"))
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                logging.error(error_msg)

            finally:
                # 恢复UI状态
                self.root.after(0, lambda: self.progress_bar.stop())
                self.root.after(0, lambda: self.progress_bar.config(mode="determinate"))
                self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.save_btn.config(state=tk.NORMAL))

        # 启动工作线程
        threading.Thread(target=worker, daemon=True).start()

    def _update_prompt_list(self, prompt_list):
        """更新Prompt下拉框 - 优化版"""
        if not prompt_list:
            messagebox.showwarning("提示", "未生成有效的Prompt")
            return

        # 更新下拉框
        current_values = list(self.ai_prompt_combobox["values"])
        new_values = current_values + prompt_list
        self.ai_prompt_combobox["values"] = new_values
        self.ai_prompt_combobox.set(prompt_list[0])
        self.dynamic_prompt_list = prompt_list
        logging.info(f"已生成{len(prompt_list)}条Prompt模板")

    def on_save_config(self):
        if self.save_config():
            messagebox.showinfo("提示", "配置已保存（仅存于内存，如需导出请用导出功能）")

    def ai_generate_answer(self, question: str, api_key: str, prompt_template: str) -> str:
        """使用OpenAI API生成答案（适配1.0+版本）"""
        try:
            # 确保导入在函数内部以避免兼容性问题
            from openai import OpenAI

            if not api_key:
                return "自动填写内容"

            client = OpenAI(api_key=api_key)
            prompt = prompt_template.format(question=question)

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7,
                n=1
            )

            return response.choices[0].message.content.strip()
        except ImportError:
            logging.error("OpenAI库未安装，请运行: pip install openai")
            return "自动填写内容"
        except Exception as e:
            logging.error(f"AI答题失败: {str(e)}")
            return "自动填写内容"

    def zhipu_generate_answer(self, question: str, api_key: str, prompt_template: str) -> str:
        """
        优化版AI答题 - 支持题型识别和格式控制
        """
        import re
        import logging

        # 1. 提取人设
        identity = self.extract_identity_from_prompt(prompt_template)

        # 2. 题型识别与格式控制
        format_rules = ""
        if re.search(r'年龄|岁数|多大', question):
            format_rules = "请只回答数字（如'25'），不要任何文字说明。"
        elif re.search(r'金额|价格|费用|收入|支出|消费', question):
            format_rules = "请只回答数字（如'5000'或'1.2万'），可带简单单位。"
        elif re.search(r'日期|时间|何时|时候', question):
            format_rules = "请按'YYYY-MM-DD'或'X年前'格式回答。"
        elif re.search(r'评分|打分|评价|满意度', question):
            format_rules = "请用1-10的数字回答。"
        elif re.search(r'姓名|称呼', question):
            format_rules = "请生成常见中文姓名。"
        elif re.search(r'电话|手机|联系方式', question):
            format_rules = "请生成13开头的手机号。"

        # 3. 构建Prompt
        full_prompt = (
            f"你现在的身份是：{identity}。请严格按以下要求回答：\n"
            f"1. 只输出最终答案，不要任何解释\n"
            f"2. 答案长度不超过10个字\n"
            f"3. {format_rules}\n"
            f"问题：{question}"
        )

        # 4. API请求（增加超时和重试）
        try:
            url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": "glm-4",
                "messages": [{"role": "user", "content": full_prompt}],
                "max_tokens": 50,  # 限制长度
                "temperature": 0.3,  # 降低随机性
                "top_p": 0.8
            }

            # 增加重试机制
            for attempt in range(3):
                try:
                    response = requests.post(url, headers=headers, json=data, timeout=15)
                    response.raise_for_status()
                    result = response.json()
                    content = (
                        result.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    )

                    # 5. 答案后处理
                    return self.simplify_answer(content, question)
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                    if attempt < 2:
                        time.sleep(1.5)
                        continue
                    else:
                        raise
        except Exception as e:
            logging.error(f"AI答题失败: {str(e)}")

        return self.get_identity_answer(identity, question)

    def extract_identity_from_prompt(self, prompt_template: str) -> str:
        """从Prompt模板提取身份（只保留"xx岁xx职业/地区/性别"这种）"""
        import re
        # 匹配"你是..."或"身份：..."等格式
        match = re.search(r"你是([^\u4e00-\u9fa5a-zA-Z0-9]*[\u4e00-\u9fa5a-zA-Z0-9，、 ]+)", prompt_template)
        if match:
            return match.group(1).split("，请")[0].strip()
        return "用户"

    def simplify_answer(self, answer: str, question: str) -> str:
        """答案后处理 - 增强版（按题型优化）"""
        import re

        # 移除所有标点符号和多余空格
        answer = re.sub(r'[^\w\u4e00-\u9fa5]', ' ', answer).strip()

        # 题型特定处理
        if re.search(r'年龄|岁数|多大', question):
            # 提取数字
            match = re.search(r'\d{1,2}', answer)
            return match.group(0) if match else "30"

        elif re.search(r'金额|价格|费用|收入|支出|消费', question):
            # 提取数字和单位
            match = re.search(r'(\d+\.?\d*)(万?元?)', answer)
            if match:
                num, unit = match.groups()
                return f"{num}{unit}" if unit else num
            return "5000"

        elif re.search(r'日期|时间|何时|时候', question):
            # 标准化日期格式
            if re.match(r'\d{4}-\d{1,2}-\d{1,2}', answer):
                return answer
            return "2023-01-01"

        elif re.search(r'评分|打分|评价|满意度', question):
            # 确保1-10分
            match = re.search(r'\d+', answer)
            if match:
                score = min(10, max(1, int(match.group(0))))
                return str(score)
            return "7"

        elif re.search(r'姓名|称呼', question):
            # 保留中文姓名
            match = re.search(r'[\u4e00-\u9fa5]{2,3}', answer)
            return match.group(0) if match else "张三"

        elif re.search(r'电话|手机|联系方式', question):
            # 生成有效手机号
            match = re.search(r'1[3-9]\d{9}', answer)
            return match.group(0) if match else "13800138000"

        # 通用处理：取第一个有效片段
        parts = answer.split()
        return parts[0][:15] if parts else "无"

    def get_identity_answer(self, identity: str, question: str) -> str:
        """备选答案池 - 按题目类型优化"""
        import random

        # 按题型分类的答案池
        answer_pools = {
            "age": [str(i) for i in range(18, 65)],
            "income": ["5000", "8000", "10000", "15000", "20000", "30000"],
            "rating": [str(i) for i in range(1, 11)],
            "date": ["2020-01-01", "2021-05-15", "2022-07-20", "2023-03-10"],
            "name": ["李明", "张伟", "王芳", "刘洋", "陈静", "赵强"],
            "phone": ["13800138000", "13912345678", "13787654321", "13511223344"],
            "bool": ["是", "否", "有", "无", "满意", "不满意", "同意", "不同意"],
            "default": ["无", "不知道", "一般", "还行", "3年", "5次", "1000元"]
        }

        # 题目类型识别
        if re.search(r'年龄|岁数|多大', question):
            return random.choice(answer_pools["age"])
        elif re.search(r'金额|价格|收入|支出|消费', question):
            return random.choice(answer_pools["income"])
        elif re.search(r'评分|打分|评价|满意度', question):
            return random.choice(answer_pools["rating"])
        elif re.search(r'日期|时间|何时|时候', question):
            return random.choice(answer_pools["date"])
        elif re.search(r'姓名|称呼', question):
            return random.choice(answer_pools["name"])
        elif re.search(r'电话|手机|联系方式', question):
            return random.choice(answer_pools["phone"])
        elif re.search(r'是否|有没有|同意吗', question):
            return random.choice(answer_pools["bool"])

        return random.choice(answer_pools["default"])

    def fill_associated_textbox(
            self, driver, question, option_element,
            default_text="自动填写内容", max_retry=8,
            ai_enabled=False, ai_api_key="", ai_prompt_template="", question_text=""
    ):
        """
        多选题/单选题选中某选项后，在整个题目区域下查找所有空白且可见的文本框，自动填入内容（支持AI）。
        """
        import time, random
        from selenium.webdriver.common.by import By

        # content内容：AI优先，否则默认
        if ai_enabled and ai_api_key and question_text and ai_prompt_template:
            try:
                content = self.zhipu_generate_answer(question_text, ai_api_key, ai_prompt_template)
            except Exception as e:
                print(f"AI生成失败: {e}")
                content = default_text + str(random.randint(1000, 9999))
        else:
            content = default_text + str(random.randint(1000, 9999))

        for _ in range(max_retry):
            candidates = []
            try:
                candidates += [el for el in question.find_elements(By.CSS_SELECTOR, "input[type='text']") if
                               el.is_displayed() and not el.get_attribute("value")]
                candidates += [el for el in question.find_elements(By.CSS_SELECTOR, "textarea") if
                               el.is_displayed() and not el.get_attribute("value")]
                candidates += [el for el in question.find_elements(By.CSS_SELECTOR, "input.OtherText") if
                               el.is_displayed() and not el.get_attribute("value")]
                candidates += [el for el in question.find_elements(By.CSS_SELECTOR, "input[placeholder*='其他']") if
                               el.is_displayed() and not el.get_attribute("value")]
                candidates += [el for el in question.find_elements(By.CSS_SELECTOR, "input[placeholder*='补充']") if
                               el.is_displayed() and not el.get_attribute("value")]
            except Exception:
                pass
            try:
                candidates += [el for el in question.find_elements(By.CSS_SELECTOR, "[contenteditable='true']") if
                               el.is_displayed() and not el.text.strip()]
            except Exception:
                pass
            uniq = []
            seen = set()
            for c in candidates:
                h = id(c)
                if h not in seen:
                    seen.add(h)
                    uniq.append(c)

            for tb in uniq:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", tb)
                except Exception:
                    pass
                try:
                    if tb.tag_name == "span" and tb.get_attribute("contenteditable") == "true":
                        driver.execute_script("arguments[0].innerText = '';", tb)
                        for ch in content:
                            tb.send_keys(ch)
                            time.sleep(random.uniform(0.01, 0.03))
                    else:
                        tb.clear()
                        for ch in content:
                            tb.send_keys(ch)
                            time.sleep(random.uniform(0.01, 0.03))
                except Exception:
                    if tb.tag_name == "span":
                        driver.execute_script("arguments[0].innerText = arguments[1];", tb, content)
                    else:
                        driver.execute_script("arguments[0].value = arguments[1];", tb, content)
                try:
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", tb)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", tb)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));", tb)
                except Exception:
                    pass
                val = tb.get_attribute("value") if tb.tag_name != "span" else tb.text.strip()
                if val and content[:4] in val:
                    return True
            time.sleep(0.5)

        return False



    def create_question_settings(self):
        """创建题型设置界面 - 已被新UI替代，保留空实现以兼容旧调用"""
        pass

    def _connect_ui_functions(self):
        """连接新UI需要的主应用方法"""
        if not self.wjx_question_ui:
            return

        # 确保新UI能访问主应用的保存方法
        if not hasattr(self.wjx_question_ui, 'save_settings'):
            # 如果新UI没有save_settings方法，创建一个委托
            def save_settings_delegate():
                if hasattr(self.wjx_question_ui, 'save_from_table'):
                    return self.wjx_question_ui.save_from_table()
                return True
            self.wjx_question_ui.save_settings = save_settings_delegate

        # 确保新UI能访问解析相关功能
        if not hasattr(self.wjx_question_ui, 'parse_survey'):
            self.wjx_question_ui.parse_survey = self.parse_survey

        # 确保新UI能访问配置保存功能
        if not hasattr(self.wjx_question_ui, 'save_config'):
            self.wjx_question_ui.save_config = self.save_config

        logging.info("UI功能连接完成")
                
    def correct_question_types(self):
        """手动修正题型对话框 - 增强版（带滚动条，按钮底部居中，支持鼠标滚轮，确保所有题目都能显示，弹窗居中显示）"""
        dialog = tk.Toplevel(self.root)
        dialog.title("手动修正题型")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中弹窗到屏幕中间
        dialog.update_idletasks()
        w = 800
        h = 600
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        x = int((screen_w - w) / 2)
        y = int((screen_h - h) / 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        # 主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 滚动区域
        canvas = tk.Canvas(main_frame, background='#f0f0f0')
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 鼠标滚轮绑定
        self.bind_mousewheel_to_scrollbar(canvas)

        # 提示标签
        tip_label = ttk.Label(scrollable_frame,
                              text="提示：下拉框题目通常包含'请选择'文本或小三角形图标，"
                                   "如果自动识别错误请手动修正为'下拉框'",
                              style='Warning.TLabel',
                              font=("Arial", 9, "italic"),
                              wraplength=700)
        tip_label.grid(row=0, column=0, columnspan=4, pady=(0, 10), sticky=tk.W)

        # 表头
        headers = ["题号", "题目预览", "当前题型", "修正为"]
        for col, header in enumerate(headers):
            header_label = ttk.Label(scrollable_frame, text=header, font=("Arial", 9, "bold"))
            header_label.grid(row=1, column=col, padx=5, pady=5, sticky=tk.W)

        # 题型映射
        type_names = {
            "1": "填空题",
            "2": "多项填空",
            "3": "单选题",
            "4": "多选题",
            "5": "量表题",
            "6": "矩阵题",
            "7": "下拉框",
            "11": "排序题"
        }
        type_codes = {v: k for k, v in type_names.items()}
        all_types = list(type_names.values())

        # 填充数据
        self.correction_vars = {}
        row_idx = 2  # 从第2行开始（标题在第1行）
        for q_num in sorted(self.config["question_texts"].keys(), key=int):
            q_text = self.config["question_texts"][q_num]
            preview = (q_text[:25] + '...') if len(q_text) > 25 else q_text

            # 当前题型判断
            current_type_code = "unknown"
            current_type_name = "未知"

            # 检查所有题型配置
            for config_key, data in [
                ("single_prob", "单选题"),
                ("multiple_prob", "多选题"),
                ("matrix_prob", "矩阵题"),
                ("texts", "填空题"),
                ("multiple_texts", "多项填空"),
                ("reorder_prob", "排序题"),
                ("droplist_prob", "下拉框"),
                ("scale_prob", "量表题")
            ]:
                if q_num in self.config[config_key]:
                    current_type_name = data
                    current_type_code = [k for k, v in type_names.items() if v == data][0]
                    break

            # 题号
            ttk.Label(scrollable_frame, text=f"第{q_num}题").grid(
                row=row_idx, column=0, padx=5, pady=2, sticky=tk.W)

            # 题目预览
            preview_label = ttk.Label(scrollable_frame, text=preview, width=25)
            preview_label.grid(row=row_idx, column=1, padx=5, pady=2, sticky=tk.W)
            tooltip_text = f"题目类型: {current_type_name}\n\n完整题目: {q_text}"
            ToolTip(preview_label, tooltip_text, wraplength=400)

            # 当前题型
            ttk.Label(scrollable_frame, text=current_type_name).grid(
                row=row_idx, column=2, padx=5, pady=2, sticky=tk.W)

            # 修正下拉框
            var = tk.StringVar(value=current_type_name)
            self.correction_vars[q_num] = var
            combo = ttk.Combobox(scrollable_frame, textvariable=var, width=12,
                                 values=all_types, state="readonly")
            combo.grid(row=row_idx, column=3, padx=5, pady=2, sticky=tk.W)

            # 特别提示下拉框题目
            if "选择" in q_text or "下拉" in q_text or "select" in q_text.lower():
                ttk.Label(scrollable_frame, text="← 可能是下拉框",
                          style='Warning.TLabel', font=("Arial", 8)).grid(
                    row=row_idx, column=4, padx=5, pady=2, sticky=tk.W)

            row_idx += 1

        # 按钮框架 - 放在主框架底部中间
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, pady=10, side=tk.BOTTOM)

        # 居中按钮
        apply_btn = ttk.Button(btn_frame, text="应用修正", width=15,
                               command=lambda: self.apply_corrections(dialog))
        apply_btn.pack(side=tk.LEFT, padx=10, expand=True)

        cancel_btn = ttk.Button(btn_frame, text="取消", width=15,
                                command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=10, expand=True)

    def apply_corrections(self, dialog):
        """应用手动修正"""
        type_codes = {
            "填空题": "1", "多项填空": "2", "单选题": "3",
            "多选题": "4", "量表题": "5", "矩阵题": "6",
            "下拉框": "7", "排序题": "11"
        }

        for q_num, var in self.correction_vars.items():
            new_type = type_codes.get(var.get(), "")
            if not new_type:
                continue

            # 从所有题型配置中移除该题
            for config_key in [
                "single_prob", "multiple_prob", "matrix_prob",
                "texts", "multiple_texts", "reorder_prob",
                "droplist_prob", "scale_prob"
            ]:
                if q_num in self.config[config_key]:
                    del self.config[config_key][q_num]

            # 添加到正确的题型配置
            if new_type == "1":
                self.config["texts"][q_num] = ["示例答案"]
            elif new_type == "2":
                option_count = len(self.config["option_texts"].get(q_num, []))
                self.config["multiple_texts"][q_num] = [["示例答案"]] * (option_count or 1)
            elif new_type == "3":
                self.config["single_prob"][q_num] = -1
            elif new_type == "4":
                option_count = len(self.config["option_texts"].get(q_num, []))
                self.config["multiple_prob"][q_num] = {
                    "prob": [50] * (option_count or 1),
                    "min_selection": 1,
                    "max_selection": option_count or 1
                }
            elif new_type == "5":
                option_count = len(self.config["option_texts"].get(q_num, []))
                self.config["scale_prob"][q_num] = [0.2] * (option_count or 1)
            elif new_type == "6":
                self.config["matrix_prob"][q_num] = -1
            elif new_type == "7":
                option_count = len(self.config["option_texts"].get(q_num, []))
                self.config["droplist_prob"][q_num] = [0.3] * (option_count or 1)
            elif new_type == "11":
                option_count = len(self.config["option_texts"].get(q_num, []))
                self.config["reorder_prob"][q_num] = [0.25] * (option_count or 1)

        dialog.destroy()
        self.reload_question_settings()
        logging.info("已应用手动修正")
    def update_ratio_display(self, event=None):
        """更新微信作答比率显示"""
        ratio = self.ratio_scale.get()
        self.ratio_var.set(f"{ratio * 100:.0f}%")
        self.config["weixin_ratio"] = ratio

    def ai_generate_structure(self):
        """AI一键生成题型配置"""
        try:
            # 检查是否有解析的题目数据
            if not self.config.get("question_texts"):
                messagebox.showwarning("提示", "请先解析问卷，获取题目信息后再使用AI生成配置")
                return

            # 检查AI配置
            ai_config = self.config.get("ai_config", {})
            if not ai_config.get("enabled", False):
                # 显示AI配置对话框
                result = messagebox.askyesno("AI配置",
                                             "AI功能未启用，是否使用内置智能配置模板？\n"
                                             "点击「是」使用内置模板\n"
                                             "点击「否」手动配置AI")
                if not result:
                    self.show_ai_config_dialog()
                    return

            # 显示进度提示
            self.main_status_var.set("AI正在生成题型配置...")
            self.main_status_label.config(foreground="blue")

            # 生成配置
            success_count = self._generate_intelligent_config()

            if success_count > 0:
                messagebox.showinfo("成功",
                                    f"AI已成功为 {success_count} 个题目生成智能配置！\n"
                                    "配置基于题目类型和内容自动优化，您可以在题型设置中查看和调整。")

                # 刷新界面显示新配置
                self.reload_question_settings()
                if hasattr(self, 'wjx_question_ui') and self.wjx_question_ui:
                    self.wjx_question_ui.refresh_interface()

                self.main_status_var.set("AI配置生成完成")
                self.main_status_label.config(foreground="green")
            else:
                messagebox.showwarning("提示", "未能生成有效配置，请检查题目数据")
                self.main_status_var.set("AI配置生成失败")
                self.main_status_label.config(foreground="red")

        except Exception as e:
            logging.error(f"AI生成配置失败: {e}")
            messagebox.showerror("错误", f"AI生成配置失败: {str(e)}")
            self.main_status_var.set("AI配置生成失败")
            self.main_status_label.config(foreground="red")

    def _generate_intelligent_config(self):
        """生成智能配置"""
        try:
            success_count = 0
            q_texts = self.config.get("question_texts", {})
            q_types = self.config.get("question_types", {})
            opt_texts = self.config.get("option_texts", {})

            for qid, qtype in q_types.items():
                question_text = q_texts.get(qid, "")
                options = opt_texts.get(qid, [])
                option_count = len(options)

                if qtype == "3":  # 单选题
                    # 根据题目内容生成智能概率
                    if any(keyword in question_text for keyword in ["年龄", "性别", "学历"]):
                        # 基本信息题：使用现实分布
                        if "性别" in question_text:
                            self.config.setdefault("single_prob", {})[qid] = [0.4, 0.6]  # 假设女性比例稍高
                        elif "年龄" in question_text and option_count >= 4:
                            self.config.setdefault("single_prob", {})[qid] = [0.1, 0.3, 0.4, 0.2]  # 中年为主
                        else:
                            self.config.setdefault("single_prob", {})[qid] = -1  # 随机
                    else:
                        self.config.setdefault("single_prob", {})[qid] = -1  # 默认随机
                    success_count += 1

                elif qtype == "4":  # 多选题
                    # 多选题智能配置
                    if option_count > 0:
                        avg_prob = min(0.6, max(0.3, 1.5 / option_count))  # 平均选择概率
                        probs = [avg_prob] * option_count
                        min_sel = max(1, option_count // 3)
                        max_sel = min(option_count, option_count // 2 + 1)

                        self.config.setdefault("multiple_prob", {})[qid] = {
                            "prob": probs,
                            "min_selection": min_sel,
                            "max_selection": max_sel
                        }
                        success_count += 1

                elif qtype == "5":  # 量表题
                    # 量表题：中间值权重高
                    if option_count == 5:  # 5点量表
                        self.config.setdefault("scale_prob", {})[qid] = [0.1, 0.2, 0.4, 0.2, 0.1]
                    elif option_count == 4:  # 4点量表
                        self.config.setdefault("scale_prob", {})[qid] = [0.2, 0.3, 0.3, 0.2]
                    else:
                        # 其他量表：均匀分布
                        prob = 1.0 / option_count if option_count > 0 else 0.5
                        self.config.setdefault("scale_prob", {})[qid] = [prob] * option_count
                    success_count += 1

                elif qtype == "6":  # 矩阵题
                    self.config.setdefault("matrix_prob", {})[qid] = -1  # 随机选择
                    success_count += 1

                elif qtype == "8":  # 矩阵量表题
                    # 矩阵量表：按列概率，偏向中间值
                    if option_count == 5:
                        self.config.setdefault("matrix_prob", {})[qid] = [0.1, 0.2, 0.4, 0.2, 0.1]
                    elif option_count == 4:
                        self.config.setdefault("matrix_prob", {})[qid] = [0.2, 0.3, 0.3, 0.2]
                    else:
                        prob = 1.0 / option_count if option_count > 0 else 0.25
                        self.config.setdefault("matrix_prob", {})[qid] = [prob] * option_count
                    success_count += 1

                elif qtype == "7":  # 下拉题
                    self.config.setdefault("droplist_prob", {})[qid] = -1  # 随机选择
                    success_count += 1

                elif qtype == "11":  # 排序题
                    # 排序题：随机权重
                    if option_count > 0:
                        self.config.setdefault("reorder_prob", {})[qid] = [1.0 / option_count] * option_count
                    success_count += 1

                elif qtype == "1":  # 填空题
                    # 生成智能文本内容
                    if "姓名" in question_text or "名字" in question_text:
                        self.config.setdefault("texts", {})[qid] = ["张三", "李四", "王五", "赵六", "孙七"]
                    elif "电话" in question_text or "手机" in question_text:
                        self.config.setdefault("texts", {})[qid] = ["13800138000", "13900139000", "15800158000"]
                    elif "邮箱" in question_text or "email" in question_text.lower():
                        self.config.setdefault("texts", {})[qid] = ["user@example.com", "test@mail.com",
                                                                    "sample@qq.com"]
                    elif "地址" in question_text:
                        self.config.setdefault("texts", {})[qid] = ["北京市朝阳区", "上海市浦东新区", "广州市天河区"]
                    else:
                        self.config.setdefault("texts", {})[qid] = ["自动填写内容", "智能生成回答", "AI配置答案"]
                    success_count += 1

            logging.info(f"AI智能配置生成完成，成功配置 {success_count} 个题目")
            return success_count

        except Exception as e:
            logging.error(f"生成智能配置时出错: {e}")
            return 0

    def show_ai_config_dialog(self):
        """显示AI配置对话框"""
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title("AI配置")
            dialog.geometry("500x400")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 居中显示
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
            y = (dialog.winfo_screenheight() // 2) - (400 // 2)
            dialog.geometry(f"500x400+{x}+{y}")
            
            main_frame = ttk.Frame(dialog)
            main_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # 标题
            title_label = ttk.Label(main_frame, text="AI配置", font=('微软雅黑', 14, 'bold'))
            title_label.pack(pady=(0, 10))
            
            # 启用AI开关
            ai_frame = ttk.LabelFrame(main_frame, text="AI功能")
            ai_frame.pack(fill='x', pady=(0, 10))
            
            ai_enabled_var = tk.BooleanVar(value=self.config.get("ai_config", {}).get("enabled", False))
            ai_check = ttk.Checkbutton(ai_frame, text="启用AI智能配置", variable=ai_enabled_var)
            ai_check.pack(anchor='w', padx=5, pady=5)
            
            # 说明文本
            info_text = tk.Text(main_frame, height=10, wrap='word')
            info_text.pack(fill='both', expand=True, pady=(0, 10))
            
            info_content = """AI智能配置功能说明：

1. 内置智能模板：
   • 根据题目类型自动选择最优配置
   • 单选题：智能识别基本信息题，采用真实分布
   • 多选题：根据选项数量自动调整选择概率
   • 量表题：偏向中间值，符合填写习惯
   • 矩阵量表题：按列统一概率，提高一致性

2. 文本题智能填写：
   • 自动识别姓名、电话、邮箱等字段
   • 生成相应的示例内容
   • 支持自定义文本模板

3. 使用建议：
   • 先解析问卷获取题目结构
   • 使用AI生成基础配置
   • 根据需要手动微调特定题目

注意：AI配置会覆盖现有设置，建议备份重要配置。"""
            
            info_text.insert('1.0', info_content)
            info_text.config(state='disabled')
            
            # 按钮区域
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill='x')
            
            def save_config():
                # 保存AI配置
                if "ai_config" not in self.config:
                    self.config["ai_config"] = {}
                self.config["ai_config"]["enabled"] = ai_enabled_var.get()
                
                dialog.destroy()
                messagebox.showinfo("保存成功", "AI配置已保存")
            
            ttk.Button(btn_frame, text="保存", command=save_config).pack(side='right', padx=(5, 0))
            ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side='right')
            
        except Exception as e:
            logging.error(f"显示AI配置对话框失败: {e}")
            messagebox.showerror("错误", f"显示AI配置对话框失败: {str(e)}")

    def _try_fast_parse(self, url):
        """快速解析：优先用requests+bs4，失败返回None"""
        if not self.config.get("parse_fast_mode", True):
            return None
        try:
            from bs4 import BeautifulSoup
        except Exception:
            logging.info("快速解析跳过：未安装bs4")
            return None

        timeout = self.config.get("parse_fast_timeout", 8)
        headers = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            ])
        }

        for attempt in range(1, 3):
            try:
                resp = requests.get(url, headers=headers, timeout=timeout)
                if resp.status_code != 200 or not resp.text:
                    logging.warning(f"快速解析HTTP状态异常: {resp.status_code}")
                    continue
                html = resp.text
                soup = BeautifulSoup(html, "html.parser")

                question_selectors = [
                    ".div_question", ".field", ".question", ".question-wrapper", ".survey-question"
                ]
                questions = []
                for sel in question_selectors:
                    questions = soup.select(sel)
                    if questions:
                        break
                if not questions:
                    potential = soup.select("div[id^='div'], div[id^='field']")
                    questions = [q for q in potential if q.select_one(".question-title, .field-label, .question-text")]

                if not questions:
                    return None

                results = []
                for idx, q in enumerate(questions, start=1):
                    qid_raw = q.get("id", "")
                    qid = re.sub(r"^(div|field|question)", "", qid_raw) or str(idx)
                    title_el = q.select_one(".div_title_question, .field-label, .question-title, .question-text, h2, h3, .title")
                    title = title_el.get_text(strip=True) if title_el else f"题目{qid}"

                    has_radio = q.select_one("input[type='radio']") is not None
                    has_checkbox = q.select_one("input[type='checkbox']") is not None
                    has_select = q.select_one("select") is not None
                    has_text = q.select_one("input[type='text'], textarea") is not None
                    has_table = q.select_one("table") is not None
                    has_scale = q.select_one(".scale-ul, .scale-item, .rating-scale, .likert-scale") is not None
                    has_sort = q.select_one(".sort-ul, .sortable, .ui-sortable") is not None

                    qtype = "1"
                    if has_table:
                        qtype = "6"
                    elif has_radio and not has_table:
                        qtype = "3"
                    elif has_checkbox:
                        qtype = "4"
                    elif has_select:
                        qtype = "7"
                    elif has_sort:
                        qtype = "11"
                    elif has_scale:
                        qtype = "5"
                    elif has_text:
                        qtype = "1"

                    options = [opt.get_text(strip=True) for opt in q.select(".ulradiocheck label, .wjx-option-label, .option-label, label")]
                    options = [o for i, o in enumerate(options) if o and o not in options[:i]]

                    results.append({
                        "id": qid,
                        "text": title,
                        "type": qtype,
                        "options": options
                    })

                if results:
                    logging.info(f"快速解析成功：{len(results)} 题")
                    return results
            except Exception as e:
                logging.warning(f"快速解析失败(第{attempt}次): {e}")
                time.sleep(1 * attempt)
        return None

    def _extract_option_texts(self, question, inputs):
        """提取选项文本（label/父节点兜底）"""
        from selenium.webdriver.common.by import By
        texts = []
        for inp in inputs:
            text = ""
            try:
                input_id = inp.get_attribute("id")
                if input_id:
                    try:
                        label = question.find_element(By.CSS_SELECTOR, f"label[for='{input_id}']")
                        text = label.text.strip()
                    except Exception:
                        text = ""
                if not text:
                    try:
                        parent = inp.find_element(By.XPATH, "./..")
                        text = parent.text.strip()
                    except Exception:
                        text = ""
            except Exception:
                text = ""
            texts.append(text)
        return texts

    def _apply_logic_rules(self, q_key, option_texts):
        """应用逻辑/约束规则，返回 must/avoid/prefer 索引集合以及min/max覆盖"""
        rules = self.config.get("logic_rules", {}).get(q_key, {}) or {}
        must_kw = rules.get("must", []) or rules.get("must_select", []) or []
        avoid_kw = rules.get("avoid", []) or rules.get("avoid_select", []) or []
        prefer_kw = rules.get("prefer", []) or rules.get("prefer_select", []) or []
        min_override = rules.get("min")
        max_override = rules.get("max")

        def match_keywords(keywords):
            idxs = set()
            for i, text in enumerate(option_texts):
                if not text:
                    continue
                for kw in keywords:
                    if kw and kw in text:
                        idxs.add(i)
                        break
            return idxs

        must_idx = match_keywords(must_kw)
        avoid_idx = match_keywords(avoid_kw)
        prefer_idx = match_keywords(prefer_kw)
        return must_idx, avoid_idx, prefer_idx, min_override, max_override

    def _weighted_sample_indices(self, weights, candidates, k):
        """按权重无放回抽样索引"""
        if k <= 0:
            return []
        if not candidates:
            return []
        if k >= len(candidates):
            return list(candidates)

        selected = []
        cand = list(candidates)
        for _ in range(k):
            local_weights = [max(0.0, float(weights[i])) for i in cand]
            total = sum(local_weights)
            if total <= 0:
                choice = random.choice(cand)
            else:
                probs = [w / total for w in local_weights]
                choice = int(np.random.choice(cand, p=probs))
            selected.append(choice)
            cand.remove(choice)
        return selected

    def parse_survey(self):
        """增强版问卷解析 - 识别页面结构和跳转规则"""
        try:
            logging.info("开始解析问卷...")

            if self.parsing:
                messagebox.showwarning("警告", "正在解析问卷，请稍候...")
                return

            # 检查URL是否为空
            url = self.url_entry.get().strip()
            if not url:
                messagebox.showerror("错误", "请输入问卷链接")
                logging.error("问卷链接为空")
                return

            # 同URL且已有解析结果时，优先使用缓存
            if self.config.get("parse_cache_enabled", True) and url == self.previous_url and self.config.get("question_texts"):
                logging.info("检测到相同URL，使用缓存解析结果")
                self.main_status_var.set("已使用缓存")
                if hasattr(self, "action_status_var"):
                    self.action_status_var.set("已使用缓存")
                self._delayed_ui_refresh()
                return

            # 在解析新问卷前，清空旧的解析数据
            self._clear_old_survey_data()

            logging.info(f"问卷链接: {url}")
            self.previous_url = url

            self.parsing = True
            self.parse_btn.config(state=tk.DISABLED, text="解析中...")
            self.main_status_var.set("正在解析问卷...")
            self.main_status_label.config(foreground="orange")
            if hasattr(self, "action_status_var"):
                self.action_status_var.set("解析中...")

            # 启动解析线程
            logging.info("启动解析线程...")
            threading.Thread(target=self._parse_survey_thread, daemon=True).start()

        except Exception as e:
            logging.error(f"解析问卷启动失败: {str(e)}")
            messagebox.showerror("错误", f"解析问卷启动失败: {str(e)}")
            self.parsing = False
            self.parse_btn.config(state=tk.NORMAL, text="解析问卷")
            self.main_status_var.set("解析失败")
            self.main_status_label.config(foreground="red")

    def _parse_survey_thread(self):
        """问卷解析线程 - 识别页面结构和跳转规则（修复版）"""
        driver = None
        try:
            logging.info("解析线程开始执行...")

            url = self.url_entry.get().strip()
            if not url:
                self.root.after(0, lambda: messagebox.showerror("错误", "请输入问卷链接"))
                logging.error("问卷链接为空")
                return

            # 快速解析优先（requests+bs4）
            fast_questions = self._try_fast_parse(url)
            if fast_questions:
                self._process_cankao_style_questions(fast_questions)
                self.root.after(0, lambda: self.question_progress_var.set(100))
                self.root.after(0, lambda: self.question_status_var.set("解析完成(快速)"))
                self.root.after(0, lambda: self.main_status_var.set("解析完成(快速)"))
                self.root.after(0, lambda: self.main_status_label.config(foreground="green"))
                if hasattr(self, "action_status_var"):
                    self.root.after(0, lambda: self.action_status_var.set("快速解析完成"))
                self.root.after(0, lambda: messagebox.showinfo("成功", f"问卷解析成功！发现 {len(fast_questions)} 个题目"))
                return

            logging.info(f"开始创建Chrome浏览器实例...")

            # 尝试定位本地ChromeDriver（若不存在则退回Selenium Manager）
            try:
                import os
                chromedriver_path = os.path.join(os.getcwd(), 'chromedriver.exe')
                if not os.path.exists(chromedriver_path):
                    logging.warning(f"未找到本地ChromeDriver: {chromedriver_path}，将尝试使用webdriver-manager自动管理")
                    chromedriver_path = None
                else:
                    logging.info(f"ChromeDriver路径: {chromedriver_path}")
            except Exception as e:
                logging.warning(f"检查ChromeDriver时发生异常，将继续尝试使用webdriver-manager: {e}")
                chromedriver_path = None

            # 创建浏览器实例
            try:
                logging.info("配置Chrome选项...")
                options = webdriver.ChromeOptions()
                # 基于cankao.py的稳定配置
                if self.config.get("parse_headless", True):
                    options.add_argument('--headless')  # 使用稳定的headless模式
                options.add_argument('--disable-gpu')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--blink-settings=imagesEnabled=false')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-logging')
                options.add_argument('--log-level=3')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--disable-web-security')
                options.add_argument('--allow-running-insecure-content')
                options.add_argument('--disable-notifications')
                options.add_argument('--disable-popup-blocking')
                options.add_argument('--disable-infobars')
                options.add_argument('--disable-save-password-bubble')
                options.add_argument('--disable-translate')
                options.add_argument('--ignore-certificate-errors')

                # 添加随机User-Agent (从cankao.py)
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1"
                ]
                options.add_argument(f'--user-agent={random.choice(user_agents)}')

                # 优化性能的偏好设置 (从cankao.py)
                prefs = {
                    'profile.default_content_setting_values': {
                        'images': 2,
                        'javascript': 1,
                        'css': 2
                    }
                }
                options.add_experimental_option('prefs', prefs)

                # 基于cankao.py的稳定驱动创建方式，添加兼容性处理和超时管理
                logging.info("创建Chrome浏览器实例...")
                driver = None

                # 设置Chrome启动超时
                import threading
                chrome_created = threading.Event()

                def create_chrome_with_timeout():
                    nonlocal driver
                    try:
                        # 1. 优先尝试使用本地 chromedriver (如果存在)
                        if chromedriver_path and os.path.exists(chromedriver_path):
                            try:
                                logging.info(f"发现本地ChromeDriver: {chromedriver_path}，尝试启动...")
                                service = Service(executable_path=chromedriver_path)
                                driver = webdriver.Chrome(service=service, options=options)
                                logging.info("使用本地ChromeDriver创建浏览器成功")
                            except Exception as e1:
                                logging.warning(f"本地ChromeDriver启动失败: {e1}，将尝试自动下载...")

                        # 2. 如果本地driver失败或不存在，尝试使用 webdriver-manager
                        if not driver:
                            try:
                                from webdriver_manager.chrome import ChromeDriverManager
                                logging.info("尝试使用webdriver-manager自动管理ChromeDriver...")
                                service = Service(ChromeDriverManager().install())
                                driver = webdriver.Chrome(service=service, options=options)
                                logging.info("使用webdriver-manager创建浏览器成功")
                            except Exception as e2:
                                logging.warning(f"webdriver-manager创建失败: {e2}")

                        # 3. 最后尝试 Selenium Manager (直接调用)
                        if not driver:
                            try:
                                driver = webdriver.Chrome(options=options)
                                logging.info("使用Selenium Manager创建浏览器成功")
                            except Exception as e3:
                                logging.error(f"Selenium Manager创建失败: {e3}")
                                raise Exception(
                                    f"所有ChromeDriver创建方式都失败: 本地driver({e1 if 'e1' in locals() else '未尝试'}), webdriver-manager({e2 if 'e2' in locals() else '未尝试'}), selenium-manager({e3})")
                    finally:
                        chrome_created.set()

                # 在后台线程中创建Chrome，设置60秒超时（首次下载ChromeDriver可能需要较长时间）
                chrome_thread = threading.Thread(target=create_chrome_with_timeout, daemon=True)
                chrome_thread.start()

                # 等待Chrome创建完成或超时
                if chrome_created.wait(timeout=60):
                    if not driver:
                        raise Exception("Chrome浏览器实例创建失败（driver为None），请检查ChromeDriver与Chrome版本匹配")
                else:
                    raise Exception("Chrome浏览器启动超时，请检查ChromeDriver和Chrome浏览器")

                if not driver:
                    raise Exception("无法创建Chrome浏览器实例，请检查Chrome浏览器是否正确安装")

                driver.set_page_load_timeout(20)  # 设置较短超时
                driver.implicitly_wait(8)  # 简化等待时间
                logging.info("Chrome浏览器实例配置完成")

            except Exception as e:
                error_msg = f"创建Chrome浏览器实例失败: {str(e)}"
                logging.error(error_msg)
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                return

            logging.info(f"正在访问问卷: {url}")
            # 增强的访问与重试逻辑：若driver为None，直接中断并提示
            if driver is None:
                error_msg = "浏览器驱动创建失败，请检查Chrome与ChromeDriver版本是否匹配（建议使用Selenium自动管理或更新本地driver）。"
                logging.error(error_msg)
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                return
            from selenium.common.exceptions import WebDriverException
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    logging.info(f"尝试访问问卷链接(第{attempt}次)...")
                    driver.get(url)

                    # 检查页面是否成功加载（检查标题或URL变化）
                    current_url = driver.current_url
                    if current_url != url:
                        logging.warning(f"URL跳转: {url} -> {current_url}")

                    # 检查是否有错误页面
                    page_title = driver.title.lower()
                    if any(error in page_title for error in ['error', '404', 'connection', 'timeout']):
                        raise WebDriverException(f"页面加载错误，标题: {driver.title}")

                    logging.info("问卷页面访问成功")
                    break

                except WebDriverException as e:
                    error_msg = str(e)
                    logging.error(f"打开链接失败(第{attempt}次): {error_msg}")

                    # 特殊处理网络连接错误
                    if "net::ERR_CONNECTION_CLOSED" in error_msg or "connection" in error_msg.lower():
                        logging.info(f"检测到网络连接问题，等待更长时间后重试...")
                        time.sleep(5 * attempt)  # 网络问题等待更长时间
                    else:
                        time.sleep(3 * attempt)

                    if attempt == max_retries:
                        raise Exception(f"无法访问问卷链接，已重试{max_retries}次。最后一次错误: {error_msg}")

            # 基于cankao.py的简化等待逻辑
            logging.info(f"正在访问问卷: {url}")
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".div_question, .field, .question"))
                )
            except TimeoutException:
                logging.error("问卷加载超时，请检查链接是否正确")
                raise Exception("问卷加载超时，请检查链接是否正确")

            # 修复后的JavaScript解析代码 - 简化版，避免语法错误
            questions_data = driver.execute_script(r"""
            const getText = (element) => element ? element.textContent.trim() : '';
            const questionSelectors = [
                '.div_question',
                '.field',
                '.question',
                '.question-wrapper',
                '.survey-question'
            ];

            let questions = [];
            for (const selector of questionSelectors) {
                const elements = document.querySelectorAll(selector);
                if (elements.length > 0) {
                    questions = Array.from(elements);
                    break;
                }
            }

            if (questions.length === 0) {
                const potentialQuestions = document.querySelectorAll('div[id^="div"], div[id^="field"]');
                questions = Array.from(potentialQuestions).filter(q => {
                    return q.querySelector('.question-title, .field-label, .question-text');
                });
            }

            const result = [];
            questions.forEach((q, index) => {
                let id = q.id.replace('div', '').replace('field', '').replace('question', '') || `${index+1}`;
                let titleElement = q.querySelector('.div_title_question, .field-label, .question-title');
                if (!titleElement) {
                    titleElement = q.querySelector('h2, h3, .title, .question-text');
                }
                const title = titleElement ? getText(titleElement) : `题目${id}`;

                // 简化的题型识别逻辑
                let type = '1'; // 默认填空题

                // 1. 检查单选按钮
                const hasRadio = q.querySelector('.ui-radio, input[type="radio"]');
                // 2. 检查多选按钮
                const hasCheckbox = q.querySelector('.ui-checkbox, input[type="checkbox"]');
                // 3. 检查表格结构
                const hasTable = q.querySelector('table');
                // 4. 检查下拉框
                const hasSelect = q.querySelector('select');
                // 5. 检查文本输入框
                const hasTextInput = q.querySelector('input[type="text"], textarea');
                // 6. 检查多个文本输入框
                const hasMultipleText = q.querySelectorAll('input[type="text"], textarea').length > 1;
                // 7. 检查量表结构
                const hasScale = q.querySelector('.scale-ul, .scale-item, .rating-scale');

                // 题型判断逻辑
                if (hasTable) {
                    type = '6'; // 矩阵题
                } else if (hasRadio && !hasTable) {
                    type = '3'; // 单选题
                } else if (hasCheckbox) {
                    type = '4'; // 多选题
                } else if (hasSelect) {
                    type = '7'; // 下拉题
                } else if (hasMultipleText) {
                    type = '2'; // 多项填空
                } else if (hasTextInput) {
                    type = '1'; // 填空题
                } else if (hasScale) {
                    type = '5'; // 量表题
                }

                // 获取选项文本
                const options = [];
                const optionElements = q.querySelectorAll('.ulradiocheck label, .wjx-option-label, .option-label');
                optionElements.forEach(opt => {
                    const text = getText(opt);
                    if (text && text.length > 0 && !text.includes('input') && !text.includes('radio')) {
                        options.push(text);
                    }
                });

                // 如果选项为空，尝试其他选择器
                if (options.length === 0) {
                    const altOptions = q.querySelectorAll('li, label');
                    altOptions.forEach(opt => {
                        const text = getText(opt);
                        if (text && text.length > 0 && !text.includes('input') && !text.includes('radio')) {
                            options.push(text);
                        }
                    });
                }

                // 检查是否有排序相关元素
                const hasSortable = q.querySelector('.sort-ul, .sortable, .ui-sortable');
                if (hasSortable) {
                    type = '11'; // 排序题
                }

                result.push({
                    id: id,
                    text: title,
                    type: type,
                    options: options,
                    hasTable: !!hasTable,
                    hasRadio: !!hasRadio,
                    hasCheckbox: !!hasCheckbox,
                    hasSelect: !!hasSelect,
                    hasTextInput: !!hasTextInput,
                    hasMultipleText: hasMultipleText,
                    hasScale: !!hasScale
                });
            });

            return result;
            """)

            # 基于cankao.py的简化解析结果处理
            self._process_cankao_style_questions(questions_data)

            # 基于cankao.py的简化日志输出
            logging.info("=== 解析结果详情 ===")
            logging.info(f"解析到 {len(questions_data)} 个题目")

            # 统计各题型数量
            type_counts = {}
            matrix_scale_details = []

            for i, question in enumerate(questions_data):
                qtype = question['type']
                type_counts[qtype] = type_counts.get(qtype, 0) + 1

                logging.info(f"  题目 {i + 1}: ID={question['id']}, 类型={qtype}, 文本='{question['text'][:50]}...'")

                # 特别记录矩阵量表题的详细信息
                if qtype == '8':
                    matrix_info = {
                        'id': question['id'],
                        'text': question['text'],
                        'has_matrix_data': bool(question.get('matrixData')),
                        'rows_count': len(question.get('matrixData', {}).get('rows', [])),
                        'cols_count': len(question.get('matrixData', {}).get('cols', []))
                    }
                    matrix_scale_details.append(matrix_info)

            # 输出题型统计
            logging.info("=== 题型统计 ===")
            type_names = {
                '1': '填空题', '2': '多项填空', '3': '单选题', '4': '多选题',
                '5': '量表题', '6': '矩阵题', '8': '矩阵量表题', '7': '下拉题', '11': '排序题', '0': '指导语'
            }
            for qtype, count in type_counts.items():
                type_name = type_names.get(qtype, f'未知类型({qtype})')
                logging.info(f"  {type_name}: {count} 题")

            # 矩阵量表题详细信息
            if matrix_scale_details:
                logging.info("=== 矩阵量表题详情 ===")
                for detail in matrix_scale_details:
                    logging.info(f"  题目 {detail['id']}: {detail['text'][:30]}...")
                    logging.info(f"    - 矩阵数据: {'有' if detail['has_matrix_data'] else '无'}")
                    logging.info(f"    - 行数: {detail['rows_count']}, 列数: {detail['cols_count']}")
            else:
                logging.warning("⚠️ 未发现矩阵量表题，可能需要检查解析逻辑")

            # 检查是否有疑似矩阵量表的题目（包括类型5和有调试信息的题目）
            suspected_matrix = [q for q in questions_data if q['type'] == '5' or ('debugInfo' in q and q['debugInfo'])]
            if suspected_matrix:
                logging.warning("=== 疑似矩阵量表题DOM结构分析 ===")
                for q in suspected_matrix:
                    logging.warning(f"  题目 {q['id']}: {q['text'][:50]}...")
                    if 'debugInfo' in q and q['debugInfo']:
                        debug = q['debugInfo']
                        logging.warning(f"    - 包含表格: {debug.get('hasTable', 'N/A')}")
                        logging.warning(f"    - 包含matrix类: {debug.get('hasMatrix', 'N/A')}")
                        logging.warning(f"    - 单选按钮组数: {debug.get('hasRadioGroups', 'N/A')}")
                        logging.warning(f"    - 每组按钮数: {debug.get('radioGroupSizes', 'N/A')}")
                        logging.warning(f"    - CSS类名: {debug.get('className', 'N/A')}")
                        logging.warning(
                            f"    - 检测结果: 量表={debug.get('hasLikertScale', 'N/A')}, 矩阵量表={debug.get('hasLikertMatrix', 'N/A')}")

                        # 表格结构详情
                        if 'tableInfo' in debug and debug['tableInfo']:
                            table_info = debug['tableInfo']
                            logging.warning(f"    - 表格行数: {table_info.get('rowCount', 'N/A')}")
                            logging.warning(f"    - 第一行单选按钮数: {table_info.get('radiosInFirstRow', 'N/A')}")
                            logging.warning(f"    - 最多单选按钮的行: {table_info.get('maxRadiosInRow', 'N/A')}")
                            logging.warning(f"    - 表格中单选按钮总数: {table_info.get('totalRadios', 'N/A')}")
                            logging.warning(f"    - 有表头: {table_info.get('hasHeaderRow', 'N/A')}")

                        logging.warning(f"    - DOM结构（前100字符）: {debug.get('innerHTML', 'N/A')[:100]}...")

            # 更新状态
            self.root.after(0, lambda: self.question_progress_var.set(100))
            self.root.after(0, lambda: self.question_status_var.set("解析完成"))
            self.root.after(0, lambda: self.main_status_var.set("解析完成"))
            self.root.after(0, lambda: self.main_status_label.config(foreground="green"))
            if hasattr(self, "action_status_var"):
                self.root.after(0, lambda: self.action_status_var.set("解析完成"))
            self.root.after(0, lambda: messagebox.showinfo("成功", f"问卷解析成功！发现 {len(questions_data)} 个题目"))

        except Exception as e:
            logging.error(f"解析问卷时出错: {str(e)}")
            import traceback
            traceback.print_exc()

            # 增强错误提示
            error_msg = f"解析问卷时出错: {str(e)}\n\n"
            error_msg += "可能的原因：\n"
            error_msg += "1. 问卷链接无效或已过期\n"
            error_msg += "2. 网络连接问题\n"
            error_msg += "3. 问卷使用了特殊的题目结构\n"
            error_msg += "4. 浏览器版本不兼容\n\n"
            error_msg += "建议：\n"
            error_msg += "1. 检查问卷链接是否正确\n"
            error_msg += "2. 尝试手动打开问卷确认可访问\n"
            error_msg += "3. 检查网络连接\n"
            error_msg += "4. 查看日志获取详细错误信息"

            self.root.after(0, lambda: messagebox.showerror("解析失败", error_msg))
            self.root.after(0, lambda: self.main_status_var.set("解析失败"))
            self.root.after(0, lambda: self.main_status_label.config(foreground="red"))
            if hasattr(self, "action_status_var"):
                self.root.after(0, lambda: self.action_status_var.set("解析失败"))
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            self.parsing = False
            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL, text="解析问卷"))

    def _process_cankao_style_questions(self, questions_data):
        """处理cankao.py风格的解析结果 - 简化处理"""
        # 清空原有配置
        self.config["question_texts"] = {}
        self.config["option_texts"] = {}
        self.config["jump_rules"] = {}
        self.config["question_types"] = {}
        # 初始化所有题型配置字典，保证后续界面有数据源
        self.config.setdefault("single_prob", {})
        self.config.setdefault("multiple_prob", {})
        self.config.setdefault("matrix_prob", {})
        self.config.setdefault("texts", {})
        self.config.setdefault("multiple_texts", {})
        self.config.setdefault("reorder_prob", {})
        self.config.setdefault("droplist_prob", {})
        self.config.setdefault("scale_prob", {})
        
        # 处理每个题目
        for question in questions_data:
            qid = str(question["id"])
            question_text = question["text"]
            
            # 过滤无效题目：跳过"子题目 X"格式的无效题目
            if (question_text.startswith('子题目') or 
                question_text.strip() == '...' or 
                len(question_text.strip()) < 3 or
                question_text.strip().isdigit()):
                logging.warning(f"跳过无效题目: ID={qid}, 文本='{question_text}'")
                continue
            
            # 存储题目文本
            self.config["question_texts"][qid] = question_text
            
            # 存储选项文本
            options = question.get("options", [])
            self.config["option_texts"][qid] = options
            
            # 存储题目类型
            qtype = question.get("type", "1")
            self.config["question_types"][qid] = qtype
            
            # 初始化题型配置
            # 保存矩阵数据（矩阵量表或普通矩阵）
            if question.get("matrixData"):
                self.config.setdefault("matrix_data", {})[qid] = question["matrixData"]

            self._init_question_type_config(qid, qtype, len(options), question.get("空数", 0))
            
        logging.info(f"处理完成：{len(questions_data)} 个题目")
        
        # 延迟刷新UI，避免与解析过程冲突，增加超时保护
        self.root.after(200, self._delayed_ui_refresh)

    def _delayed_ui_refresh(self):
        """延迟UI刷新，确保解析完成后再更新界面 - 增强版"""
        try:
            logging.info("开始延迟UI刷新...")
            
            # 增加重试计数器，避免无限循环
            if not hasattr(self, '_refresh_retry_count'):
                self._refresh_retry_count = 0
            
            # 检查是否还在解析状态，但不阻止用户操作
            if getattr(self, 'parsing', False):
                self._refresh_retry_count += 1
                if self._refresh_retry_count > 5:  # 减少重试次数到5次（5秒），避免过长等待
                    logging.warning("解析进行中，但强制执行UI刷新以响应用户操作")
           # 强制禁用代理 (Security Policy)
        self.config["use_ip"] = False
        
        # 初始化变量
        self.is_running = False  # 允许界面刷新
                else:
                    logging.info(f"解析进行中，等待解析完成 (等待 {self._refresh_retry_count}/5)")
                    self.root.after(1000, self._delayed_ui_refresh)  # 增加到1秒间隔，减少频繁重试
                    return
            
            # 重置重试计数器
            self._refresh_retry_count = 0
            
            # 优先刷新新的题型设置界面
            if hasattr(self, 'wjx_question_ui') and self.wjx_question_ui:
                # 先切换到题型设置标签页
                try:
                    self.notebook.select(self.question_frame)
                    # 添加防卡死保护：分步刷新，增加超时保护
                    self.root.after(200, self._safe_refresh_wjx_ui)  # 增加延迟到200ms，给解析更多时间
                    logging.info("已安排新版题型设置界面刷新")
                except Exception as switch_error:
                    logging.error(f"切换标签页失败: {switch_error}")
                    # 切换失败时尝试直接刷新
                    self._safe_refresh_wjx_ui()
            else:
                # 回退到原有界面刷新
                try:
                    self.reload_question_settings()
                    # 切换到题型设置标签页
                    self.notebook.select(self.question_frame)
                    logging.info("已刷新旧版题型设置界面")
                except Exception as reload_error:
                    logging.error(f"旧版界面刷新失败: {reload_error}")
                
        except Exception as e:
            logging.error(f"延迟UI刷新失败: {e}")
            # 发生严重错误时，至少要释放解析状态
            if hasattr(self, 'parsing'):
                self.parsing = False

    def force_switch_to_settings(self):
        """强制切换到题型设置页面，无论解析状态如何"""
        try:
            # 直接切换到题型设置标签页
            self.notebook.select(self.question_frame)
            logging.info("用户强制切换到题型设置页面")
            
            # 如果有数据但界面未刷新，尝试刷新
            if hasattr(self, 'config') and self.config.get("question_texts"):
                if hasattr(self, 'wjx_question_ui') and self.wjx_question_ui:
                    self.root.after(100, self._safe_refresh_wjx_ui)
                    
        except Exception as e:
            logging.error(f"强制切换到题型设置页面失败: {e}")

    def _safe_refresh_wjx_ui(self):
        """安全刷新WJX界面，使用after轮询避免阻塞主线程"""
        try:
            if not (hasattr(self, 'wjx_question_ui') and self.wjx_question_ui):
                logging.warning("WJX界面组件不存在")
                return
            if not (self.root and self.root.winfo_exists()):
                logging.warning("主窗口已销毁，跳过UI刷新")
                return

            refresh_state = {
                'start_ts': None,
                'timeout_ms': 5000,
                'error': None,
            }

            def start_refresh():
                try:
                    import time
                    refresh_state['start_ts'] = int(time.time() * 1000)
                    self._do_refresh_ui_nonblocking(check_completion)
                except Exception as e:
                    refresh_state['error'] = e
                    finish(False)

            def check_completion():
                # 当 _do_refresh_ui_nonblocking 调用完成后进入
                finish(True)

            def finish(success: bool):
                if success:
                    logging.info("WJX界面刷新完成")
                else:
                    logging.error("WJX界面刷新失败或超时，可能发生卡顿")
                    try:
                        if hasattr(self, 'wjx_question_ui') and hasattr(self.wjx_question_ui, '_refreshing'):
                            self.wjx_question_ui._refreshing = False
                    except Exception:
                        pass

            # 启动异步刷新
            self.root.after_idle(start_refresh)
        except Exception as e:
            logging.error(f"安全刷新WJX界面失败: {e}")
            try:
                if hasattr(self, 'wjx_question_ui') and hasattr(self.wjx_question_ui, '_refreshing'):
                    self.wjx_question_ui._refreshing = False
            except Exception:
                pass
            try:
                messagebox.showerror("界面错误", f"界面刷新失败，请重新解析问卷: {str(e)}")
            except Exception:
                pass

    def _do_refresh_ui_nonblocking(self, on_done):
        """在UI线程中执行刷新，并在完成时回调on_done，不阻塞主线程"""
        try:
            if hasattr(self, 'wjx_question_ui') and self.wjx_question_ui:
                # refresh_interface 内部已采用分阶段/after异步渲染
                self.wjx_question_ui.refresh_interface()
            # 计划稍后回调完成，确保有机会进入事件循环
            if self.root and self.root.winfo_exists():
                self.root.after(0, on_done)
            else:
                on_done()
        except Exception as e:
            logging.error(f"UI刷新执行失败: {e}")
            if self.root and self.root.winfo_exists():
                self.root.after(0, on_done)
            else:
                on_done()

    def _clear_old_survey_data(self):
        """清空旧的问卷解析数据"""
        try:
            logging.info("清空旧的问卷解析数据...")
            
            # 清空解析相关的配置项
            keys_to_clear = [
                'question_texts', 'question_types', 'option_texts', 'page_paths',
                'single_prob', 'multiple_prob', 'matrix_prob', 'matrix_data',
                'texts', 'multiple_texts', 'reorder_prob', 'scale_prob', 'droplist_prob'
            ]
            
            for key in keys_to_clear:
                if key in self.config:
                    self.config[key] = {}
                    
            logging.info("旧数据清空完成")
            
        except Exception as e:
            logging.error(f"清空旧数据失败: {e}")

    def _init_question_type_config(self, qid, qtype, option_count, blank_count=0):
        """初始化题型配置"""
        # 首先更新题型映射
        if "question_types" not in self.config:
            self.config["question_types"] = {}
        self.config["question_types"][qid] = qtype
        
        if qtype == "0":  # 指导语/说明文字
            # 指导语不需要特殊配置，仅记录类型
            pass
        elif qtype == "3":  # 单选题
            if "single_prob" not in self.config:
                self.config["single_prob"] = {}
            self.config["single_prob"][qid] = -1  # 默认随机
        elif qtype == "4":  # 多选题
            if "multiple_prob" not in self.config:
                self.config["multiple_prob"] = {}
            self.config["multiple_prob"][qid] = {
                "prob": [50] * max(1, option_count),
                "min_selection": 1,
                "max_selection": max(1, min(3, option_count))
            }
        elif qtype == "5":  # 量表题（单题量表）
            if "scale_prob" not in self.config:
                self.config["scale_prob"] = {}
            self.config["scale_prob"][qid] = -1  # 默认随机
        elif qtype == "6":  # 矩阵题
            if "matrix_prob" not in self.config:
                self.config["matrix_prob"] = {}
            # 矩阵题初始化为每列的默认概率
            col_count = max(1, option_count)
            probs = [round(1.0 / col_count, 2) for _ in range(col_count)]
            s = sum(probs)
            if probs:
                probs[-1] = round(probs[-1] + (1.0 - s), 2)
            self.config["matrix_prob"][qid] = probs
        elif qtype == "8":  # 矩阵量表题（整表共享量表列，按列概率）
            if "matrix_prob" not in self.config:
                self.config["matrix_prob"] = {}
            col_count = max(1, option_count)
            probs = [round(1.0 / col_count, 2) for _ in range(col_count)]
            s = sum(probs)
            if probs:
                probs[-1] = round(probs[-1] + (1.0 - s), 2)
            self.config["matrix_prob"][qid] = probs
        elif qtype == "1":  # 填空题
            self.config.setdefault("texts", {})[qid] = [""]
        elif qtype == "2":  # 多项填空
            self.config.setdefault("multiple_texts", {})[qid] = [[""] for _ in range(max(1, blank_count))]
        elif qtype == "7":  # 下拉框
            self.config.setdefault("droplist_prob", {})[qid] = [-1] * max(1, option_count)
        elif qtype == "11":  # 排序题
            self.config.setdefault("reorder_prob", {})[qid] = [round(1.0 / max(1, option_count), 2)] * max(1, option_count)
    def _process_parsed_questions(self, pages):
        """处理解析结果，构建路径树 - 确保题目完整"""
        # 清空原有配置
        self.config["question_texts"] = {}
        self.config["option_texts"] = {}
        self.config["jump_rules"] = {}
        # 新的page_paths只保存题目ID列表
        self.config["page_paths"] = []
        for page in pages:
            # 提取题目ID列表
            question_ids = [str(q['id']) for q in page["questions"]]
            self.config["page_paths"].append({
                "page": page["page"],
                "path": page["path"],
                "questions": question_ids  # 存储ID列表
            })
            # 存储题目信息
            for question in page["questions"]:
                qid = str(question["id"])
                # 存储题目文本 - 确保完整
                self.config["question_texts"][qid] = question["text"]
                
                # 存储选项文本 - 标准化为纯文本列表
                def _normalize_option_texts(options):
                    texts = []
                    try:
                        for opt in options or []:
                            if isinstance(opt, dict):
                                text = opt.get('text') or opt.get('label') or opt.get('value')
                            else:
                                text = str(opt)
                            if text:
                                texts.append(text.strip())
                    except Exception:
                        pass
                    return texts

                option_list = _normalize_option_texts(question.get("options"))
                self.config["option_texts"][qid] = option_list
                
                # 存储矩阵数据（如果有）
                if question.get("matrixData") and question["matrixData"].get("rows"):
                    self.config.setdefault("matrix_data", {})[qid] = question["matrixData"]
                
                # 存储跳转规则
                if question.get("jumpRules"):
                    self.config["jump_rules"][qid] = question["jumpRules"]
                
                # 根据题型初始化配置 - 确保完整
                q_type = question.get("type")
                if q_type == '3':  # 单选题
                    if qid not in self.config.get("single_prob", {}):
                        self.config.setdefault("single_prob", {})[qid] = -1  # 默认随机
                elif q_type == '4':  # 多选题
                    if qid not in self.config.get("multiple_prob", {}):
                        option_count = len(self.config["option_texts"][qid])
                        self.config.setdefault("multiple_prob", {})[qid] = {
                            "prob": [50] * option_count,
                            "min_selection": 1,
                            "max_selection": min(3, option_count)
                        }
                elif q_type == '6':  # 矩阵题
                    if qid not in self.config.get("matrix_prob", {}):
                        # 为矩阵题设置更合理的默认配置
                        matrix_data = question.get("matrixData", {})
                        if matrix_data and matrix_data.get("rows"):
                            # 为每行设置概率配置
                            row_count = len(matrix_data["rows"])
                            self.config.setdefault("matrix_prob", {})[qid] = {
                                "rows": row_count,
                                "cols": len(matrix_data.get("cols", [])),
                                "row_probs": [[0.2] * len(matrix_data.get("cols", [])) for _ in range(row_count)]
                            }
                        else:
                            self.config.setdefault("matrix_prob", {})[qid] = -1  # 默认随机
                elif q_type == '1':  # 填空题
                    if qid not in self.config.get("texts", {}):
                        self.config.setdefault("texts", {})[qid] = ["示例答案"]
                elif q_type == '5':  # 量表题
                    if qid not in self.config.get("scale_prob", {}):
                        option_count = len(self.config["option_texts"][qid])
                        self.config.setdefault("scale_prob", {})[qid] = [0.2] * option_count
                elif q_type == '7':  # 下拉框
                    if qid not in self.config.get("droplist_prob", {}):
                        option_count = len(self.config["option_texts"][qid])
                        self.config.setdefault("droplist_prob", {})[qid] = [0.3] * option_count
                elif q_type == '11':  # 排序题
                    if qid not in self.config.get("reorder_prob", {}):
                        option_count = len(self.config["option_texts"][qid])
                        self.config.setdefault("reorder_prob", {})[qid] = [0.25] * option_count
                elif q_type == '2':  # 多项填空
                    if qid not in self.config.get("multiple_texts", {}):
                        option_count = len(self.config["option_texts"][qid])
                        self.config.setdefault("multiple_texts", {})[qid] = [["示例答案"]] * option_count
        # 更新题型设置界面
        self.root.after(0, self.reload_question_settings)
        import logging
        # 详细统计解析结果
        total_questions = len(self.config['question_texts'])
        total_paths = len(pages)
        
        # 统计各题型数量
        type_counts = {}
        for qid, q_text in self.config['question_texts'].items():
            q_type = self.get_question_type(qid)
            type_name = self.get_question_type_name(q_type)
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        # 输出详细统计信息
        logging.info("=" * 50)
        logging.info("📊 解析结果统计")
        logging.info("=" * 50)
        logging.info(f"📄 页面路径数量: {total_paths}")
        logging.info(f"📝 题目总数量: {total_questions}")
        logging.info("📋 题型分布:")
        for type_name, count in type_counts.items():
            logging.info(f"   • {type_name}: {count} 题")
        logging.info("=" * 50)
        
        # 输出题目详情
        logging.info("📋 题目详情:")
        for qid, q_text in self.config['question_texts'].items():
            q_type = self.get_question_type(qid)
            type_name = self.get_question_type_name(q_type)
            options = self.config.get('option_texts', {}).get(qid, [])
            option_count = len(options)
            logging.info(f"   Q{qid}: {q_text[:50]}{'...' if len(q_text) > 50 else ''} ({type_name}, {option_count}个选项)")
        
        logging.info("=" * 50)
        logging.info(f"解析完成，共发现{len(pages)}个页面路径")
        logging.info(f"配置中存储的题目: {list(self.config['question_texts'].keys())}")
        logging.info(f"配置中存储的路径: {self.config['page_paths']}")

    def set_matrix_random(self, q_num):
        """设置矩阵题为随机选择"""
        q_key = str(q_num)
        self.config["matrix_prob"][q_key] = -1
        logging.info(f"矩阵题 {q_num} 已设置为随机选择")
        
    def set_matrix_average(self, q_num):
        """设置矩阵题为平均概率"""
        q_key = str(q_num)
        matrix_data = self.config.get("matrix_data", {}).get(q_key, {})
        if matrix_data and matrix_data.get("cols"):
            col_count = len(matrix_data["cols"])
            self.config["matrix_prob"][q_key] = {
                "rows": len(matrix_data.get("rows", [])),
                "cols": col_count,
                "row_probs": [[1.0/col_count] * col_count for _ in range(len(matrix_data.get("rows", [])))]
            }
        else:
            self.config["matrix_prob"][q_key] = -1
        logging.info(f"矩阵题 {q_num} 已设置为平均概率")
        
    def set_matrix_bias(self, q_num, direction):
        """设置矩阵题偏置"""
        q_key = str(q_num)
        matrix_data = self.config.get("matrix_data", {}).get(q_key, {})
        if matrix_data and matrix_data.get("cols"):
            col_count = len(matrix_data["cols"])
            row_count = len(matrix_data.get("rows", []))
            
            if direction == "left":
                # 偏左：前面的选项概率更高
                bias_factors = [0.4, 0.3, 0.2, 0.1, 0.05]
            else:  # right
                # 偏右：后面的选项概率更高
                bias_factors = [0.05, 0.1, 0.2, 0.3, 0.4]
            
            row_probs = []
            for _ in range(row_count):
                row_prob = []
                for i in range(col_count):
                    if i < len(bias_factors):
                        prob = bias_factors[i]
                    else:
                        prob = bias_factors[-1] * (0.8 ** (i - len(bias_factors) + 1))
                    row_prob.append(prob)
                # 归一化
                total = sum(row_prob)
                if total > 0:
                    row_prob = [p / total for p in row_prob]
                row_probs.append(row_prob)
            
            self.config["matrix_prob"][q_key] = {
                "rows": row_count,
                "cols": col_count,
                "row_probs": row_probs
            }
        else:
            self.config["matrix_prob"][q_key] = -1
        logging.info(f"矩阵题 {q_num} 已设置为{direction}偏置")

    def create_single_settings(self, frame, qid=None):
        """创建单选题设置界面 - Excel表格风格横向布局：题目文本 | 参数设置 | 快捷按钮"""
        if qid is not None:
            # 如果指定了qid，处理单个题目（保留原有功能）
            self._create_single_question_setting(frame, qid)
            return
        
        # 否则创建所有单选题的表格视图
        padx, pady = 4, 2
        
        # 说明框架
        desc_frame = ttk.LabelFrame(frame, text="单选题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 输入-1表示随机选择，正数为选项权重", 
                  font=("Arial", 9)).pack(anchor=tk.W)
        
        # 表格框架
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 表头 - Excel风格三列
        headers = ["题目文本", "参数设置", "快捷操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=padx, pady=pady, sticky=tk.W)
        
        # 题目行 - 每题一行，横向分布
        for row_idx, (q_num, probs) in enumerate(self.config.get("single_prob", {}).items(), start=1):
            q_text = self.config.get("question_texts", {}).get(q_num, f"单选题 {q_num}")
            option_count = len(self.config.get("option_texts", {}).get(q_num, [])) or 1
            
            # 第一列：题目文本（完整显示）
            text_container = ttk.Frame(table_frame)
            text_container.grid(row=row_idx, column=0, padx=padx, pady=pady, sticky=tk.W)
            
            # 题号 + 题目文本，横向排列
            ttk.Label(text_container, text=f"第{q_num}题:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            text_label = ttk.Label(text_container, text=q_text, width=35, anchor="w", 
                                  wraplength=250, font=("Arial", 9))
            text_label.pack(side=tk.LEFT, padx=(5, 0))
            ToolTip(text_label, text=q_text)
            
            # 第二列：参数设置输入框（紧跟在题目后面）
            param_container = ttk.Frame(table_frame)
            param_container.grid(row=row_idx, column=1, padx=padx, pady=pady, sticky=tk.W)
            
            entry_row = []
            for opt_idx in range(option_count):
                # 选项标签和输入框横向排列
                ttk.Label(param_container, text=f"选项{opt_idx + 1}:", width=6).pack(side=tk.LEFT, padx=(0, 2))
                entry = ttk.Entry(param_container, width=5)
                
                if isinstance(probs, list) and opt_idx < len(probs):
                    entry.insert(0, str(probs[opt_idx]))
                elif probs == -1:
                    entry.insert(0, "-1")
                else:
                    entry.insert(0, "1")
                
                entry.pack(side=tk.LEFT, padx=(0, 4))
                entry_row.append(entry)
            
            self.single_entries.append(entry_row)
            
            # 第三列：四个快捷按钮（最后一部分）
            btn_container = ttk.Frame(table_frame)
            btn_container.grid(row=row_idx, column=2, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Button(btn_container, text="偏左", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("single", "left", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_container, text="偏右", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("single", "right", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_container, text="随机", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_random("single", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_container, text="平均", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_average("single", q, e)).pack(
                side=tk.LEFT, padx=1)
    
    def _create_single_question_setting(self, frame, qid):
        """创建单个单选题的配置界面（保留原有功能）"""
        # 配置说明卡片
        desc_frame = ttk.LabelFrame(frame, text="📋 单选题配置说明")
        desc_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        
        desc_content = ttk.Frame(desc_frame)
        desc_content.pack(fill=tk.X, padx=12, pady=8)
        
        ttk.Label(desc_content, text="• 输入 -1 表示随机选择，正数表示选项权重", 
                  font=("微软雅黑", 9), foreground="#2c3e50").pack(anchor=tk.W)
        ttk.Label(desc_content, text="• 权重越高，该选项被选中的概率越大", 
                  font=("微软雅黑", 9), foreground="#2c3e50").pack(anchor=tk.W)
        
        # 题目配置区域
        config_frame = ttk.Frame(frame)
        config_frame.pack(fill=tk.BOTH, expand=True)
        
        # 获取题目信息
        q_text = self.config.get("question_texts", {}).get(qid, f"单选题 {qid}")
        option_texts = self.config.get("option_texts", {}).get(qid, [])
        option_count = len(option_texts)
        
        # 题目信息卡片
        info_frame = ttk.LabelFrame(config_frame, text="📝 题目信息")
        info_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        
        info_content = ttk.Frame(info_frame)
        info_content.pack(fill=tk.X, padx=12, pady=8)
        
        # 题目文本
        ttk.Label(info_content, text="题目内容:", 
                  font=("微软雅黑", 10, "bold"), foreground="#34495e").pack(anchor=tk.W)
        ttk.Label(info_content, text=q_text,
                  font=("微软雅黑", 9), foreground="#2c3e50", 
                  wraplength=500, justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 8))
        
        # 选项信息
        ttk.Label(info_content, text="选项列表:", 
                  font=("微软雅黑", 10, "bold"), foreground="#34495e").pack(anchor=tk.W)
        
        options_frame = ttk.Frame(info_content)
        options_frame.pack(fill=tk.X, pady=(2, 0))
        
        for i, option in enumerate(option_texts):
            option_label = ttk.Label(options_frame, text=f"选项{i+1}: {option}",
                                    font=("微软雅黑", 9), foreground="#7f8c8d")
            option_label.pack(anchor=tk.W, pady=1)
        
        # 配置设置卡片
        settings_frame = ttk.LabelFrame(config_frame, text="⚙️ 概率配置")
        settings_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        
        settings_content = ttk.Frame(settings_frame)
        settings_content.pack(fill=tk.X, padx=12, pady=8)
        
        # 快捷设置按钮
        quick_frame = ttk.Frame(settings_content)
        quick_frame.pack(fill=tk.X, pady=(0, 12))
        
        ttk.Label(quick_frame, text="快捷设置:", 
                  font=("微软雅黑", 10, "bold"), foreground="#34495e").pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(quick_frame)
        btn_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        # 创建按钮样式
        btn_style = {"width": 8, "style": "Accent.TButton"}
        
        random_btn = ttk.Button(btn_frame, text="🎲 随机", 
                               command=lambda: self.set_question_random("single", qid, []), **btn_style)
        random_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        avg_btn = ttk.Button(btn_frame, text="⚖️ 平均", 
                            command=lambda: self.set_question_average("single", qid, []), **btn_style)
        avg_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        left_btn = ttk.Button(btn_frame, text="⬅️ 偏左", 
                             command=lambda: self.set_question_bias("single", "left", qid, []), **btn_style)
        left_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        right_btn = ttk.Button(btn_frame, text="➡️ 偏右", 
                              command=lambda: self.set_question_bias("single", "right", qid, []), **btn_style)
        right_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 手动配置区域
        manual_frame = ttk.Frame(settings_content)
        manual_frame.pack(fill=tk.X)
        
        ttk.Label(manual_frame, text="手动配置:", 
                  font=("微软雅黑", 10, "bold"), foreground="#34495e").pack(anchor=tk.W, pady=(0, 8))
        
        # 创建选项输入框
        entry_frame = ttk.Frame(manual_frame)
        entry_frame.pack(fill=tk.X)
        
        entry_row = []
        for i in range(option_count):
            option_frame = ttk.Frame(entry_frame)
            option_frame.pack(side=tk.LEFT, padx=(0, 15))
            
            ttk.Label(option_frame, text=f"选项{i+1}:", 
                      font=("微软雅黑", 9), foreground="#7f8c8d").pack(anchor=tk.W)
            
            entry = ttk.Entry(option_frame, width=8, font=("微软雅黑", 9))
            entry.pack(anchor=tk.W, pady=(2, 0))
            
            # 设置默认值
            probs = self.config.get("single_prob", {}).get(qid, -1)
            if isinstance(probs, list) and i < len(probs):
                entry.insert(0, str(probs[i]))
            elif probs == -1:
                entry.insert(0, "-1")
            else:
                entry.insert(0, "1")
            
            entry_row.append(entry)
        
        self.single_entries.append(entry_row)
        
        # 应用按钮
        apply_frame = ttk.Frame(settings_content)
        apply_frame.pack(fill=tk.X, pady=(12, 0))
        
        apply_btn = ttk.Button(apply_frame, text="✅ 应用配置", 
                              command=lambda: self.apply_single_config(qid, entry_row),
                              style="Accent.TButton", width=12)
        apply_btn.pack(side=tk.RIGHT)
        
        # 添加工具提示
        ToolTip(random_btn, "设置所有选项为随机选择")
        ToolTip(avg_btn, "设置所有选项为平均概率")
        ToolTip(left_btn, "设置前面选项的概率更高")
        ToolTip(right_btn, "设置后面选项的概率更高")
        ToolTip(apply_btn, "应用当前配置到题目")

    def apply_single_config(self, qid, entries):
        """应用单选题配置"""
        try:
            values = []
            for entry in entries:
                value = entry.get().strip()
                try:
                    values.append(float(value))
                except ValueError:
                    messagebox.showerror("错误", f"选项值 '{value}' 不是有效的数字")
                    return
            
            # 更新配置
            self.config["single_prob"][qid] = values
            logging.info(f"单选题 {qid} 配置已更新: {values}")
            
            # 显示成功消息
            messagebox.showinfo("成功", f"单选题 {qid} 配置已应用")
            
        except Exception as e:
            logging.error(f"应用单选题配置失败: {e}")
            messagebox.showerror("错误", f"应用配置失败: {str(e)}")

    def create_multi_settings(self, frame, qid=None):
        padx, pady = 4, 2
        desc_frame = ttk.LabelFrame(frame, text="多选题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 每个选项概率为0-100，表示被选的独立概率", font=("Arial", 9)).pack(anchor=tk.W)
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        headers = ["题号", "题目预览", "最小", "最大", "选项及操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(row=0, column=col, padx=padx, pady=pady,
                                                                                sticky=tk.W)
        self.other_entries = {}
        for row_idx, (q_num, config) in enumerate(self.config.get("multiple_prob", {}).items(), start=1):
            base_row = row_idx * 2
            q_text = self.config.get("question_texts", {}).get(q_num, f"多选题 {q_num}")
            option_count = len(self.config.get("option_texts", {}).get(q_num, [])) or 1
            ttk.Label(table_frame, text=f"第{q_num}题", font=("Arial", 10)).grid(row=base_row, column=0, padx=padx,
                                                                                 pady=pady, sticky=tk.NW)
            preview_text = q_text
            ttk.Label(table_frame, text=preview_text, width=20, anchor="w", wraplength=300).grid(row=base_row, column=1,
                                                                                                 padx=padx, pady=pady,
                                                                                                 sticky=tk.NW)
            min_entry = ttk.Spinbox(table_frame, from_=1, to=option_count, width=3)
            min_entry.set(config.get("min_selection", 1))
            min_entry.grid(row=base_row, column=2, padx=padx, pady=pady)
            self.min_selection_entries.append(min_entry)
            max_entry = ttk.Spinbox(table_frame, from_=1, to=option_count, width=3)
            max_entry.set(config.get("max_selection", option_count))
            max_entry.grid(row=base_row, column=3, padx=padx, pady=pady)
            self.max_selection_entries.append(max_entry)
            option_line = ttk.Frame(table_frame)
            option_line.grid(row=base_row, column=4, padx=padx, pady=pady, sticky=tk.W)
            entry_row = []
            option_texts = self.config.get("option_texts", {}).get(q_num, [])
            for opt_idx in range(option_count):
                ttk.Label(option_line, text=f"选项{opt_idx + 1}:", width=5).pack(side=tk.LEFT, padx=(0, 2))
                entry = ttk.Entry(option_line, width=6)
                if isinstance(config["prob"], list) and opt_idx < len(config["prob"]):
                    entry.insert(0, config["prob"][opt_idx])
                else:
                    entry.insert(0, 50)
                entry.pack(side=tk.LEFT, padx=(0, 2))
                entry_row.append(entry)
                if opt_idx < len(option_texts):
                    if "其他" in option_texts[opt_idx] or "other" in option_texts[opt_idx].lower():
                        other_edit = ttk.Entry(option_line, width=14)
                        other_values = self.config.get("other_texts", {}).get(q_num, ["自定义"])
                        other_edit.insert(0, ", ".join(other_values))
                        other_edit.pack(side=tk.LEFT, padx=(6, 0))
                        self.other_entries[q_num] = other_edit
            self.multi_entries.append(entry_row)
            btn_group = ttk.Frame(option_line)
            btn_group.pack(side=tk.LEFT, padx=(8, 0))
            ttk.Button(btn_group, text="偏左", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("multiple", "left", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_group, text="偏右", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("multiple", "right", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_group, text="随机", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_random("multiple", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_group, text="50%", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_value("multiple", q, e, 50)).pack(
                side=tk.LEFT, padx=1)
            ttk.Separator(table_frame, orient='horizontal').grid(
                row=base_row + 1, column=0, columnspan=5, sticky='ew', pady=10
            )

    def create_matrix_settings(self, frame, qid=None):
        """矩阵题配置界面 - 增强版，支持矩阵数据结构显示"""
        padx, pady = 4, 2
        desc_frame = ttk.LabelFrame(frame, text="矩阵题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 矩阵题包含多行问题，每行对应不同选项", font=("Arial", 9)).pack(anchor=tk.W)
        ttk.Label(desc_frame, text="• 输入-1为随机，正数为权重", font=("Arial", 9)).pack(anchor=tk.W)
        
        # 创建滚动区域
        canvas = tk.Canvas(frame, borderwidth=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 鼠标滚轮支持
        canvas.bind("<Enter>", lambda e: self.bind_mousewheel(canvas))
        canvas.bind("<Leave>", lambda e: self.unbind_mousewheel())
        
        table_frame = ttk.Frame(scrollable_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        headers = ["题号", "题目预览", "矩阵结构", "配置操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(row=0, column=col, padx=padx, pady=pady,
                                                                                sticky=tk.W)
        
        for row_idx, (q_num, probs) in enumerate(self.config.get("matrix_prob", {}).items(), start=1):
            base_row = row_idx * 3  # 增加行高以容纳矩阵信息
            
            q_text = self.config.get("question_texts", {}).get(q_num, f"矩阵题 {q_num}")
            option_count = len(self.config.get("option_texts", {}).get(q_num, [])) or 1
            
            # 题号
            ttk.Label(table_frame, text=f"第{q_num}题", font=("Arial", 10)).grid(row=base_row, column=0, padx=padx,
                                                                                 pady=pady, sticky=tk.NW)
            
            # 题目预览
            preview_text = q_text[:50] + "..." if len(q_text) > 50 else q_text
            ttk.Label(table_frame, text=preview_text, width=25, anchor="w", wraplength=300).grid(row=base_row, column=1,
                                                                                                 padx=padx, pady=pady,
                                                                                                 sticky=tk.NW)
            
            # 矩阵结构信息
            matrix_info_frame = ttk.Frame(table_frame)
            matrix_info_frame.grid(row=base_row, column=2, padx=padx, pady=pady, sticky=tk.W)
            
            # 显示矩阵数据（如果有）
            matrix_data = self.config.get("matrix_data", {}).get(q_num, {})
            if matrix_data and matrix_data.get("rows"):
                rows = matrix_data["rows"]
                cols = matrix_data.get("cols", [])
                
                ttk.Label(matrix_info_frame, text=f"行数: {len(rows)}", font=("Arial", 8)).pack(anchor=tk.W)
                ttk.Label(matrix_info_frame, text=f"列数: {len(cols)}", font=("Arial", 8)).pack(anchor=tk.W)
                
                # 显示前几行标题
                if rows:
                    preview_rows = rows[:3]
                    row_text = "行标题: " + ", ".join(preview_rows)
                    if len(rows) > 3:
                        row_text += f"... (共{len(rows)}行)"
                    ttk.Label(matrix_info_frame, text=row_text, font=("Arial", 8), wraplength=200).pack(anchor=tk.W)
                
                # 显示列标题
                if cols:
                    col_text = "列标题: " + ", ".join(cols[:3])
                    if len(cols) > 3:
                        col_text += f"... (共{len(cols)}列)"
                    ttk.Label(matrix_info_frame, text=col_text, font=("Arial", 8), wraplength=200).pack(anchor=tk.W)
            else:
                ttk.Label(matrix_info_frame, text="标准矩阵题", font=("Arial", 8)).pack(anchor=tk.W)
                ttk.Label(matrix_info_frame, text=f"选项数: {option_count}", font=("Arial", 8)).pack(anchor=tk.W)
            
            # 配置操作区域
            config_frame = ttk.Frame(table_frame)
            config_frame.grid(row=base_row, column=3, padx=padx, pady=pady, sticky=tk.W)
            
            # 如果是复杂矩阵，显示简化配置
            if isinstance(probs, dict) and probs.get("rows"):
                ttk.Label(config_frame, text="复杂矩阵配置", font=("Arial", 8, "bold")).pack(anchor=tk.W)
                ttk.Label(config_frame, text=f"行数: {probs['rows']}, 列数: {probs['cols']}", font=("Arial", 8)).pack(anchor=tk.W)
                
                # 快捷配置按钮
                btn_frame = ttk.Frame(config_frame)
                btn_frame.pack(anchor=tk.W, pady=2)
                
                ttk.Button(btn_frame, text="随机", width=6,
                           command=lambda q=q_num: self.set_matrix_random(q)).pack(side=tk.LEFT, padx=1)
                ttk.Button(btn_frame, text="平均", width=6,
                           command=lambda q=q_num: self.set_matrix_average(q)).pack(side=tk.LEFT, padx=1)
                ttk.Button(btn_frame, text="偏左", width=6,
                           command=lambda q=q_num: self.set_matrix_bias(q, "left")).pack(side=tk.LEFT, padx=1)
                ttk.Button(btn_frame, text="偏右", width=6,
                           command=lambda q=q_num: self.set_matrix_bias(q, "right")).pack(side=tk.LEFT, padx=1)
            else:
                # 标准配置
                option_line = ttk.Frame(config_frame)
                option_line.pack(anchor=tk.W)
                entry_row = []
                for opt_idx in range(option_count):
                    ttk.Label(option_line, text=f"选项{opt_idx + 1}:", width=5).pack(side=tk.LEFT, padx=(0, 2))
                    entry = ttk.Entry(option_line, width=6)
                    if isinstance(probs, list) and opt_idx < len(probs):
                        entry.insert(0, str(probs[opt_idx]))
                    elif probs == -1:
                        entry.insert(0, "-1")
                    else:
                        entry.insert(0, "1")
                    entry.pack(side=tk.LEFT, padx=(0, 2))
                    entry_row.append(entry)
                self.matrix_entries.append(entry_row)
                
                btn_group = ttk.Frame(option_line)
                btn_group.pack(side=tk.LEFT, padx=(8, 0))
                ttk.Button(btn_group, text="偏左", width=4,
                           command=lambda q=q_num, e=entry_row: self.set_question_bias("matrix", "left", q, e)).pack(
                    side=tk.LEFT, padx=1)
                ttk.Button(btn_group, text="偏右", width=4,
                           command=lambda q=q_num, e=entry_row: self.set_question_bias("matrix", "right", q, e)).pack(
                    side=tk.LEFT, padx=1)
                ttk.Button(btn_group, text="随机", width=4,
                           command=lambda q=q_num, e=entry_row: self.set_question_random("matrix", q, e)).pack(side=tk.LEFT,
                                                                                                               padx=1)
                ttk.Button(btn_group, text="平均", width=4,
                           command=lambda q=q_num, e=entry_row: self.set_question_average("matrix", q, e)).pack(
                    side=tk.LEFT, padx=1)
            
            # 分隔线
            ttk.Separator(table_frame, orient='horizontal').grid(
                row=base_row + 1, column=0, columnspan=4, sticky='ew', pady=10
            )
    def create_reorder_settings(self, frame, qid=None):
        padx, pady = 4, 2
        desc_frame = ttk.LabelFrame(frame, text="排序题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 每个位置的概率为相对权重", font=("Arial", 9)).pack(anchor=tk.W)
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        headers = ["题号", "题目预览", "位置概率配置及操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(row=0, column=col, padx=padx, pady=pady,
                                                                                sticky=tk.W)
        for row_idx, (q_num, probs) in enumerate(self.config.get("reorder_prob", {}).items(), start=1):
            base_row = row_idx * 2
            q_text = self.config.get("question_texts", {}).get(q_num, f"排序题 {q_num}")
            option_count = len(self.config.get("option_texts", {}).get(q_num, [])) or 1
            ttk.Label(table_frame, text=f"第{q_num}题", font=("Arial", 10)).grid(row=base_row, column=0, padx=padx,
                                                                                 pady=pady, sticky=tk.NW)
            preview_text = q_text
            ttk.Label(table_frame, text=preview_text, width=20, anchor="w", wraplength=300).grid(row=base_row, column=1,
                                                                                                 padx=padx, pady=pady,
                                                                                                 sticky=tk.NW)
            option_line = ttk.Frame(table_frame)
            option_line.grid(row=base_row, column=2, padx=padx, pady=pady, sticky=tk.W)
            entry_row = []
            for pos_idx in range(option_count):
                ttk.Label(option_line, text=f"位置{pos_idx + 1}:", width=5).pack(side=tk.LEFT, padx=(0, 2))
                entry = ttk.Entry(option_line, width=6)
                if isinstance(probs, list) and pos_idx < len(probs):
                    entry.insert(0, str(probs[pos_idx]))
                else:
                    entry.insert(0, f"{1 / option_count:.2f}")
                entry.pack(side=tk.LEFT, padx=(0, 2))
                entry_row.append(entry)
            self.reorder_entries.append(entry_row)
            btn_group = ttk.Frame(option_line)
            btn_group.pack(side=tk.LEFT, padx=(8, 0))
            ttk.Button(btn_group, text="偏前", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("reorder", "left", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_group, text="偏后", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("reorder", "right", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_group, text="随机", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_random("reorder", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_group, text="平均", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_average("reorder", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Separator(table_frame, orient='horizontal').grid(
                row=base_row + 1, column=0, columnspan=3, sticky='ew', pady=10
            )

    def create_droplist_settings(self, frame, qid=None):
        """下拉框题配置界面 - 支持概率配置和快捷按钮"""
        padx, pady = 4, 2
        desc_frame = ttk.LabelFrame(frame, text="下拉框题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame,
                  text="• 概率英文逗号分隔，数量等于下拉选项数，支持快捷按钮\n• 示例: 0.3, 0.4, 0.3 表示三个选项的选择概率",
                  font=("Arial", 9)).pack(anchor=tk.W)

        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        headers = ["题号", "题目预览", "选项概率配置及操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=padx, pady=pady, sticky=tk.W)

        self.droplist_entries = []  # 清空现有条目

        # 遍历配置中的所有下拉框题
        for row_idx, (q_num, probs) in enumerate(self.config.get("droplist_prob", {}).items(), start=1):
            base_row = row_idx * 2
            q_text = self.config.get("question_texts", {}).get(q_num, f"下拉题 {q_num}")

            # 直接获取选项列表
            option_texts = self.config.get("option_texts", {}).get(q_num, [])
            option_count = len(option_texts)

            ttk.Label(table_frame, text=f"第{q_num}题", font=("Arial", 10)).grid(
                row=base_row, column=0, padx=padx, pady=pady, sticky=tk.NW)
            ttk.Label(table_frame, text=q_text, width=20, anchor="w", wraplength=300).grid(
                row=base_row, column=1, padx=padx, pady=pady, sticky=tk.NW)

            # 选项配置行
            option_line = ttk.Frame(table_frame)
            option_line.grid(row=base_row, column=2, padx=padx, pady=pady, sticky=tk.W)

            # 创建输入框
            entry = ttk.Entry(option_line, width=40)

            # 处理概率配置格式
            if not isinstance(probs, list):
                # 尝试转换为列表
                if isinstance(probs, (int, float)):
                    probs = [probs]
                elif isinstance(probs, str):
                    try:
                        probs = [float(p.strip()) for p in probs.split(",")]
                    except:
                        probs = [0.3] * option_count
                else:
                    probs = [0.3] * option_count

            # 确保概率数量匹配选项数量
            if len(probs) > option_count:
                probs = probs[:option_count]
                logging.info(f"题目 {q_num} 概率配置截断为 {option_count} 项")
            elif len(probs) < option_count:
                probs = probs + [0.3] * (option_count - len(probs))
                logging.info(f"题目 {q_num} 概率配置扩展为 {option_count} 项")

            # 格式化显示
            entry_str = ", ".join(str(round(p, 2)) for p in probs)
            entry.insert(0, entry_str)
            entry.pack(side=tk.LEFT, padx=(0, 2))
            self.droplist_entries.append(entry)

            # 按钮组
            btn_group = ttk.Frame(option_line)
            btn_group.pack(side=tk.LEFT, padx=(8, 0))

            # 快捷按钮
            ttk.Button(btn_group, text="偏前", width=4,
                       command=lambda e=entry, c=option_count: self.set_question_bias("droplist", "left", None, [e],
                                                                                      c)).pack(side=tk.LEFT, padx=1)
            ttk.Button(btn_group, text="偏后", width=4,
                       command=lambda e=entry, c=option_count: self.set_question_bias("droplist", "right", None, [e],
                                                                                      c)).pack(side=tk.LEFT, padx=1)
            ttk.Button(btn_group, text="随机", width=4,
                       command=lambda e=entry, c=option_count: self.set_question_random("droplist", None, [e], c)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_group, text="平均", width=4,
                       command=lambda e=entry, c=option_count: self.set_question_average("droplist", None, [e],
                                                                                         c)).pack(side=tk.LEFT, padx=1)

            # 分隔线
            ttk.Separator(table_frame, orient='horizontal').grid(
                row=base_row + 1, column=0, columnspan=3, sticky='ew', pady=10
            )

    def create_scale_settings(self, frame, qid=None):
        padx, pady = 4, 2
        desc_frame = ttk.LabelFrame(frame, text="量表题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 概率越高，被选中的几率越大", font=("Arial", 9)).pack(anchor=tk.W)
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        headers = ["题号", "题目预览", "刻度概率配置及操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(row=0, column=col, padx=padx, pady=pady,
                                                                                sticky=tk.W)
        for row_idx, (q_num, probs) in enumerate(self.config.get("scale_prob", {}).items(), start=1):
            base_row = row_idx * 2
            q_text = self.config.get("question_texts", {}).get(q_num, f"量表题 {q_num}")
            option_count = len(self.config.get("option_texts", {}).get(q_num, [])) or 1
            ttk.Label(table_frame, text=f"第{q_num}题", font=("Arial", 10)).grid(row=base_row, column=0, padx=padx,
                                                                                 pady=pady, sticky=tk.NW)
            preview_text = q_text
            ttk.Label(table_frame, text=preview_text, width=20, anchor="w", wraplength=300).grid(row=base_row, column=1,
                                                                                                 padx=padx, pady=pady,
                                                                                                 sticky=tk.NW)
            option_line = ttk.Frame(table_frame)
            option_line.grid(row=base_row, column=2, padx=padx, pady=pady, sticky=tk.W)
            entry_row = []
            for opt_idx in range(option_count):
                ttk.Label(option_line, text=f"刻度{opt_idx + 1}:", width=5).pack(side=tk.LEFT, padx=(0, 2))
                entry = ttk.Entry(option_line, width=6)
                if isinstance(probs, list) and opt_idx < len(probs):
                    entry.insert(0, str(probs[opt_idx]))
                else:
                    entry.insert(0, "0.2")
                entry.pack(side=tk.LEFT, padx=(0, 2))
                entry_row.append(entry)
            self.scale_entries.append(entry_row)
            btn_group = ttk.Frame(option_line)
            btn_group.pack(side=tk.LEFT, padx=(8, 0))
            ttk.Button(btn_group, text="偏左", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("scale", "left", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_group, text="偏右", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("scale", "right", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_group, text="随机", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_random("scale", q, e)).pack(side=tk.LEFT,
                                                                                                          padx=1)
            ttk.Button(btn_group, text="平均", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_average("scale", q, e)).pack(side=tk.LEFT,
                                                                                                           padx=1)
            ttk.Separator(table_frame, orient='horizontal').grid(
                row=base_row + 1, column=0, columnspan=3, sticky='ew', pady=10
            )

    def create_text_settings(self, frame, qid=None):
        padx, pady = 4, 2
        desc_frame = ttk.LabelFrame(frame, text="填空题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 填空题答案用逗号分隔，自动随机选", font=("Arial", 9)).pack(anchor=tk.W)
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        headers = ["题号", "题目预览", "答案配置"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(row=0, column=col, padx=padx, pady=pady,
                                                                                sticky=tk.W)
        for row_idx, (q_num, answers) in enumerate(self.config.get("texts", {}).items(), start=1):
            base_row = row_idx * 2
            q_text = self.config.get("question_texts", {}).get(q_num, f"填空题 {q_num}")
            option_count = len(self.config.get("option_texts", {}).get(q_num, [])) or 1
            ttk.Label(table_frame, text=f"第{q_num}题", font=("Arial", 10)).grid(row=base_row, column=0, padx=padx,
                                                                                 pady=pady, sticky=tk.NW)
            preview_text = q_text
            ttk.Label(table_frame, text=preview_text, width=20, anchor="w", wraplength=300).grid(row=base_row, column=1,
                                                                                                 padx=padx, pady=pady,
                                                                                                 sticky=tk.NW)
            answer_line = ttk.Frame(table_frame)
            answer_line.grid(row=base_row, column=2, padx=padx, pady=pady, sticky=tk.W)
            entry_row = []
            for i in range(option_count):
                entry = ttk.Entry(answer_line, width=14)
                answer_str = ", ".join(answers) if i == 0 else ""
                entry.insert(0, answer_str)
                entry.pack(side=tk.LEFT, padx=(0, 2))
                entry_row.append(entry)
            self.text_entries.append(entry_row)
            reset_btn = ttk.Button(answer_line, text="重置", width=6,
                                   command=lambda e=entry_row: [ent.delete(0, tk.END) or ent.insert(0, "示例答案") for
                                                                ent in e])
            reset_btn.pack(side=tk.LEFT, padx=(6, 0))
            ttk.Separator(table_frame, orient='horizontal').grid(
                row=base_row + 1, column=0, columnspan=3, sticky='ew', pady=10
            )

    def create_multiple_text_settings(self, frame, qid=None):
        padx, pady = 4, 2
        desc_frame = ttk.LabelFrame(frame, text="多项填空配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 每空答案用逗号分隔，自动随机选", font=("Arial", 9)).pack(anchor=tk.W)
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        headers = ["题号", "题目预览", "答案配置"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(row=0, column=col, padx=padx, pady=pady,
                                                                                sticky=tk.W)
        for row_idx, (q_num, answers_list) in enumerate(self.config.get("multiple_texts", {}).items(), start=1):
            base_row = row_idx * 2
            q_text = self.config.get("question_texts", {}).get(q_num, f"多项填空 {q_num}")
            option_count = len(self.config.get("option_texts", {}).get(q_num, [])) or len(answers_list) or 1
            ttk.Label(table_frame, text=f"第{q_num}题", font=("Arial", 10)).grid(row=base_row, column=0, padx=padx,
                                                                                 pady=pady, sticky=tk.NW)
            preview_text = q_text
            ttk.Label(table_frame, text=preview_text, width=20, anchor="w", wraplength=300).grid(row=base_row, column=1,
                                                                                                 padx=padx, pady=pady,
                                                                                                 sticky=tk.NW)
            answer_line = ttk.Frame(table_frame)
            answer_line.grid(row=base_row, column=2, padx=padx, pady=pady, sticky=tk.W)
            entry_row = []
            for i in range(option_count):
                entry = ttk.Entry(answer_line, width=14)
                answer_str = ", ".join(answers_list[i]) if i < len(answers_list) else ""
                entry.insert(0, answer_str)
                entry.pack(side=tk.LEFT, padx=(0, 2))
                entry_row.append(entry)
            self.multiple_text_entries.append(entry_row)
            reset_btn = ttk.Button(answer_line, text="重置", width=6,
                                   command=lambda e=entry_row: [ent.delete(0, tk.END) or ent.insert(0, "示例答案") for
                                                                ent in e])
            reset_btn.pack(side=tk.LEFT, padx=(6, 0))
            ttk.Separator(table_frame, orient='horizontal').grid(
                row=base_row + 1, column=0, columnspan=3, sticky='ew', pady=10
            )

    def auto_click_next_page(self, driver):
        """
        更鲁棒的问卷星翻页函数：多重检测，保证翻页成功才返回True，否则False。
        优化点：
        - 只统计可见题目，防止隐藏题目影响判断
        - 检查URL、题目内容、页码文本、下一页按钮消失
        - 日志详细，便于排查
        """
        import time
        from selenium.webdriver.common.by import By
        import logging

        prev_url = driver.current_url
        try:
            main_questions = driver.find_elements(By.CSS_SELECTOR, ".div_question, .field, .question")
            prev_q_texts = [q.text[:30] for q in main_questions if q.is_displayed()] if main_questions else []
        except Exception:
            prev_q_texts = []

        # 多种方式查找"下一页"按钮
        selectors = [
            "#divNext a", "a[id*='NextPage']", "a[onclick*='next']", "button.next"
        ]
        next_btn = None
        for sel in selectors:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                for b in btns:
                    if b.is_displayed() and b.is_enabled():
                        next_btn = b
                        break
                if next_btn:
                    break
            except Exception:
                continue
        # 兜底：文本查找
        if not next_btn:
            try:
                btns = driver.find_elements(By.XPATH, "//*[contains(text(),'下一页') or contains(text(),'Next')]")
                for b in btns:
                    if b.is_displayed() and b.is_enabled():
                        next_btn = b
                        break
            except Exception:
                pass

        if not next_btn:
            logging.warning("未找到下一页按钮")
            return False

        # 尝试点击
        try:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_btn)
            time.sleep(0.1)
            next_btn.click()
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", next_btn)
            except Exception as e:
                logging.error(f"下一页按钮点击失败: {e}")
                return False

        # 动态检测页面变化（最多5秒，每0.2s检测一次）
        start = time.time()
        while time.time() - start < 5:
            # 1. URL变化
            if driver.current_url != prev_url:
                logging.info("翻页成功：URL已变化")
                return True
            # 2. 题目内容变化
            try:
                new_questions = driver.find_elements(By.CSS_SELECTOR, ".div_question, .field, .question")
                new_q_texts = [q.text[:30] for q in new_questions if q.is_displayed()] if new_questions else []
                if new_q_texts != prev_q_texts and new_q_texts:
                    logging.info("翻页成功：题目内容已变化")
                    return True
            except Exception:
                pass
            # 3. 页码文本变化
            page_source = driver.page_source
            if any(word in page_source for word in ["第2页", "第3页", "Page 2", "Page 3", "下一页", "Next"]):
                logging.info("翻页成功：检测到页码变化")
                return True
            # 4. 下一页按钮消失（有些模板最后一页"下一页"按钮直接消失）
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, "#divNext a, a[id*='NextPage']")
                if not any(b.is_displayed() for b in btns):
                    logging.info("翻页成功：下一页按钮消失")
                    return True
            except Exception:
                pass
            # 5. 验证码出现
            if any(word in page_source for word in ["验证码", "geetest_panel", "nc_iconfont"]):
                logging.warning("出现验证码，翻页流程暂停")
                return False
            time.sleep(0.2)
        logging.warning("翻页超时，页面未变化")
        return False

    def safe_click(self, driver, element):
        """
        安全点击元素，处理各种点击异常情况
        """
        import time
        from selenium.common.exceptions import ElementClickInterceptedException

        try:
            # 滚动元素到视图中央
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});",
                element
            )
            time.sleep(0.5)

            # 尝试直接点击
            try:
                element.click()
                time.sleep(1)  # 等待页面响应
                return True
            except ElementClickInterceptedException:
                # 处理被遮挡的情况
                try:
                    # 尝试点击元素的中心点
                    location = element.location
                    size = element.size
                    x = location['x'] + size['width'] // 2
                    y = location['y'] + size['height'] // 2

                    actions = ActionChains(driver)
                    actions.move_to_element_with_offset(element, 0, 0)
                    actions.move_by_offset(size['width'] // 2, size['height'] // 2)
                    actions.click()
                    actions.perform()
                    time.sleep(1)
                    return True
                except Exception:
                    # 最后尝试JavaScript点击
                    try:
                        driver.execute_script("arguments[0].click();", element)
                        time.sleep(1)
                        return True
                    except Exception as e:
                        logging.error(f"JavaScript点击失败: {str(e)}")
                        return False
            except Exception as e:
                logging.error(f"直接点击失败: {str(e)}")
                return False
        except Exception as e:
            logging.error(f"安全点击异常: {str(e)}")
            return False

    def is_next_page_loaded(self, driver, prev_url=None, prev_q_texts=None):
        """
        更鲁棒的一次性检测，判断页面是否已翻页。
        - prev_url: 翻页前的URL
        - prev_q_texts: 翻页前题目文本列表
        """
        import logging
        from selenium.webdriver.common.by import By

        try:
            if prev_url and driver.current_url != prev_url:
                logging.info("检测到URL已变化，已翻页")
                return True
            # 题目内容变化
            new_questions = driver.find_elements(By.CSS_SELECTOR, ".div_question, .field, .question")
            new_q_texts = [q.text[:30] for q in new_questions] if new_questions else []
            if prev_q_texts is not None and new_q_texts != prev_q_texts and new_q_texts:
                logging.info("检测到题目内容变化，已翻页")
                return True
            # 页码文本
            page_source = driver.page_source
            if any(word in page_source for word in ["第2页", "第3页", "Page 2", "Page 3", "下一页", "Next"]):
                logging.info("检测到页码变化，已翻页")
                return True
            # 下一页按钮消失
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, "#divNext a, a[id*='NextPage']")
                if not any(b.is_displayed() for b in btns):
                    logging.info("下一页按钮消失，疑似已翻页")
                    return True
            except Exception:
                pass
        except Exception as e:
            logging.error(f"is_next_page_loaded检测异常: {e}")
        return False

    def set_question_bias(self, q_type, direction, q_num, entries):
        """为单个题目设置偏左或偏右分布"""
        bias_factors = {
            "left": [0.4, 0.3, 0.2, 0.1, 0.05],
            "right": [0.05, 0.1, 0.2, 0.3, 0.4]
        }

        factors = bias_factors.get(direction, [0.2, 0.2, 0.2, 0.2, 0.2])

        for i, entry in enumerate(entries):
            if i < len(factors):
                prob = factors[i]
            else:
                prob = factors[-1] * (0.8 ** (i - len(factors) + 1))  # 指数衰减

            # 根据题目类型格式化概率值
            if q_type == "multiple":
                prob_value = int(prob * 100)
            else:
                prob_value = f"{prob:.2f}"

            entry.delete(0, tk.END)
            entry.insert(0, str(prob_value))

        logging.info(f"第{q_num}题已设置为{direction}偏置")

    def set_question_random(self, q_type, q_num, entries):
        """为单个题目设置随机选择"""
        for entry in entries:
            entry.delete(0, tk.END)
            entry.insert(0, "-1")

        logging.info(f"第{q_num}题已设置为随机选择")

    def set_question_average(self, q_type, q_num, entries):
        """为单个题目设置平均概率"""
        option_count = len(entries)
        if option_count == 0:
            return

        avg_prob = 1.0 / option_count

        for entry in entries:
            entry.delete(0, tk.END)
            if q_type == "multiple":
                entry.insert(0, str(int(avg_prob * 100)))
            else:
                entry.insert(0, f"{avg_prob:.2f}")

        logging.info(f"第{q_num}题已设置为平均概率")

    def set_question_value(self, q_type, q_num, entries, value):
        """为单个题目设置指定值（多用于多选题）"""
        for entry in entries:
            entry.delete(0, tk.END)
            entry.insert(0, str(value))

        logging.info(f"第{q_num}题已设置为{value}%概率")

    def clear_log(self):
        """清空日志"""
        try:
            self.log_area.config(state=tk.NORMAL)
            self.log_area.delete(1.0, tk.END)
            self.log_area.config(state=tk.DISABLED)
            
            # 清空过滤列表和计数器
            self.filtered_logs.clear()
            self.log_count = 0
            self.log_stats_var.set("日志条数: 0")
            
            # 更新行号
            self.update_line_numbers()
            
            # 更新状态
            self.log_status_var.set("日志已清空")
            logging.info("日志已清空")
        except Exception as e:
            logging.error(f"清空日志失败: {e}")

    def export_log(self):
        """导出日志到文件"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"), 
                ("Log files", "*.log"), 
                ("All files", "*.*")
            ],
            title="导出日志",
            initialfile=f"wjx_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    # 写入日志头部信息
                    f.write("=" * 60 + "\n")
                    f.write("智能表单自动填充系统 - 运行日志\n")
                    f.write(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"日志条数: {self.log_count}\n")
                    f.write("=" * 60 + "\n\n")
                    
                    # 写入日志内容
                    log_content = self.log_area.get(1.0, tk.END)
                    f.write(log_content)
                    
                    # 写入统计信息
                    f.write("\n" + "=" * 60 + "\n")
                    f.write("日志统计信息:\n")
                    level_counts = {}
                    for entry in self.filtered_logs:
                        level = entry['level']
                        level_counts[level] = level_counts.get(level, 0) + 1
                    
                    for level, count in level_counts.items():
                        f.write(f"{level}: {count} 条\n")
                    f.write("=" * 60 + "\n")
                
                # 更新状态
                self.log_file_var.set(f"日志文件: {filename}")
                self.log_status_var.set("日志导出成功")
                
                messagebox.showinfo("成功", f"日志已导出到:\n{filename}")
                logging.info(f"日志已导出到: {filename}")
                
            except Exception as e:
                error_msg = f"导出失败: {str(e)}"
                messagebox.showerror("错误", error_msg)
                logging.error(error_msg)

    def update_font(self, *args):
        """更新UI字体 - 增强版，避免频繁触发刷新"""
        try:
            font_family = self.font_family.get()
            try:
                font_size = int(self.font_size.get())
                # 限制字体大小范围
                if font_size < 8:
                    font_size = 8
                    self.font_size.set(8)
                elif font_size > 20:
                    font_size = 20
                    self.font_size.set(20)
            except (ValueError, TypeError):
                font_size = 10
                self.font_size.set(10)

            # 确保字体族名称有效
            if not font_family or font_family not in tkfont.families():
                font_family = "微软雅黑"
                self.font_family.set(font_family)

            new_font = (font_family, font_size)

            # 检查字体是否真的改变了
            current_font = getattr(self, '_current_font', None)
            if current_font == new_font:
                return  # 字体没有变化，直接返回

            self._current_font = new_font

            # 更新全局样式
            style = ttk.Style()
            style.configure('.', font=new_font)

            # 更新特定控件样式
            style.configure('TLabel', font=new_font)
            style.configure('TButton', font=new_font)
            style.configure('TEntry', font=new_font)
            style.configure('TCombobox', font=new_font)
            style.configure('TNotebook.Tab', font=new_font)
            style.configure('TLabelframe.Label', font=new_font)

            # 更新主要控件字体
            if hasattr(self, 'log_area'):
                self.log_area.configure(font=new_font)

            # 更新AI聊天界面字体
            if hasattr(self, 'ai_chat_tab') and self.ai_chat_tab:
                try:
                    if hasattr(self.ai_chat_tab, 'chat_history'):
                        self.ai_chat_tab.chat_history.configure(font=new_font)
                except:
                    pass

            # 递归更新所有控件字体
            try:
                self._update_widget_font_recursive(self.root, new_font)
            except Exception as e:
                logging.debug(f"递归更新字体时出错: {str(e)}")

            logging.debug(f"字体已更新为: {font_family} {font_size}")

        except Exception as e:
            logging.error(f"更新字体时出错: {str(e)}")
            try:
                self.font_family.set("微软雅黑")
                self.font_size.set(10)
            except:
                pass

    def _update_widget_font_recursive(self, widget, font):
        """递归更新控件的字体"""
        try:
            # 检查控件是否有效
            if not widget or not widget.winfo_exists():
                return

            # 更新当前控件
            if hasattr(widget, 'configure') and 'font' in widget.configure():
                try:
                    widget.configure(font=font)
                except Exception:
                    pass

            # 递归更新子控件
            for child in widget.winfo_children():
                try:
                    self._update_widget_font_recursive(child, font)
                except Exception:
                    continue
        except Exception as e:
            pass  # 静默处理递归错误

    def reload_question_settings(self):
        """重新加载题型设置界面 - 使用优化后的版本（增强防抖）"""
        try:
            # 检查主窗口是否还存在
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                logging.debug("主窗口已销毁，跳过刷新")
                return

            # 检查是否有解析数据
            if not self.config.get('question_texts'):
                logging.debug("没有解析数据，跳过题型设置界面刷新")
                return

            # 增强防抖：1秒内最多触发一次
            now = time.time()
            last = getattr(self, '_last_reload_ts', 0)
            if now - last < 1.0:  # 增加到1秒
                logging.debug("刷新题型设置界面... (已防抖，忽略重复调用)")
                return
            self._last_reload_ts = now

            logging.info("刷新题型设置界面...")

            # 使用专用UI的刷新方法
            if hasattr(self, 'wjx_question_ui') and self.wjx_question_ui:
                # 使用异步刷新，但增加更长的延迟，避免阻塞主线程
                self.root.after(100, self._safe_async_refresh_ui)  # 增加到100ms
            else:
                logging.warning("题型设置UI实例不存在，跳过刷新")

        except Exception as e:
            logging.error(f"刷新题型设置界面失败: {e}")

    def _safe_async_refresh_ui(self):
        """安全异步刷新UI，避免阻塞（增强版）"""
        try:
            # 再次检查防抖
            if not hasattr(self, '_last_async_refresh_ts'):
                self._last_async_refresh_ts = 0

            now = time.time()
            if now - self._last_async_refresh_ts < 0.5:  # 0.5秒内不重复刷新
                logging.debug("异步刷新已防抖")
                return

            self._last_async_refresh_ts = now

            # 检查UI实例是否仍然存在
            if not (hasattr(self, 'wjx_question_ui') and self.wjx_question_ui):
                logging.warning("UI实例不存在，跳过异步刷新")
                return

            # 检查主窗口是否存在
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                logging.warning("主窗口已销毁，跳过异步刷新")
                return

            # 检查是否正在解析中
            if getattr(self, 'parsing', False):
                logging.debug("解析进行中，稍后重试刷新")
                self.root.after(500, self._safe_async_refresh_ui)  # 500ms后重试
                return

            # 执行刷新
            if hasattr(self.wjx_question_ui, 'refresh_interface'):
                self.wjx_question_ui.refresh_interface()
                logging.debug("题型设置界面异步刷新完成")
            else:
                logging.warning("UI刷新方法不可用")

        except Exception as e:
            logging.error(f"异步UI刷新失败: {e}")


    def _auto_run_reliability_analysis(self):
        """自动运行信效度分析并应用推荐权重"""
        try:
            if hasattr(self, 'wjx_question_ui') and self.wjx_question_ui:
                logging.info("开始自动信效度分析...")
                
                # 运行信效度分析
                question_data = {
                    'question_texts': self.config.get('question_texts', {}),
                    'question_types': self.config.get('question_types', {}),
                    'option_texts': self.config.get('option_texts', {})
                }
                
                if question_data['question_texts']:
                    self.wjx_question_ui.reliability_result = self.wjx_question_ui.reliability_analyzer.analyze_questionnaire_reliability(question_data)
                    
                    if self.wjx_question_ui.reliability_result:
                        alpha = self.wjx_question_ui.reliability_result.cronbach_alpha
                        logging.info(f"信效度分析完成，Cronbach's Alpha: {alpha:.3f}")
                        
                        # 如果信效度较低，自动应用推荐权重
                        if alpha < 0.75:
                            logging.info("信效度偏低，自动应用推荐权重...")
                            self.wjx_question_ui.apply_recommended_weights()
                            # 显示信效度分析结果
                            self.root.after(100, lambda: messagebox.showinfo(
                                "信效度分析",
                                f"问卷信效度: {alpha:.3f}\n"
                                f"等级: {self.wjx_question_ui.reliability_result.reliability_level}\n"
                                f"已自动应用推荐权重以提升信效度"
                            ))
                        else:
                            # 显示良好的信效度结果
                            self.root.after(100, lambda: messagebox.showinfo(
                                "信效度分析",
                                f"问卷信效度: {alpha:.3f}\n"
                                f"等级: {self.wjx_question_ui.reliability_result.reliability_level}\n"
                                f"信效度良好，可直接使用当前设置"
                            ))
                    else:
                        logging.warning("信效度分析失败")
                
        except Exception as e:
            logging.error(f"自动信效度分析失败: {e}")

    def _force_rebuild_question_ui(self):
        """强制重建题型设置UI（兜底）"""
        try:
            if hasattr(self, 'wjx_question_ui') and self.wjx_question_ui:
                container = getattr(self.wjx_question_ui, 'container', self.question_frame)
                # 清空旧容器
                for widget in container.winfo_children():
                    try:
                        widget.destroy()
                    except Exception:
                        pass
                # 重新创建
                self.wjx_question_ui.create_question_settings_frame(container)
                # 强制刷新
                self.root.update_idletasks()
                logging.info("题型设置界面已强制重建")
        except Exception as e:
            logging.error(f"强制重建题型设置界面失败: {e}")

    def configure_path_priority(self):
        """配置路径优先级对话框 - 基本实现"""
        dialog = tk.Toplevel(self.root)
        dialog.title("路径优先级配置")
        dialog.geometry("600x400")

        # 主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标题
        ttk.Label(main_frame, text="问卷路径优先级顺序", font=("Arial", 12, "bold")).pack(pady=10)

        # 提示信息
        ttk.Label(main_frame,
                  text="拖动路径调整执行顺序，排在前面的路径将被优先尝试",
                  wraplength=500).pack(pady=5)

        # 创建可排序的列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建列表框
        self.path_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            height=10
        )
        self.path_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.path_listbox.yview)

        # 填充路径
        for path in self.config.get("page_paths", []):
            path_str = "→".join(str(p) for p in path["path"])
            self.path_listbox.insert(tk.END, f"路径 {path_str} (页{path['page']})")

        # 控制按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="上移", command=self.move_path_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="下移", command=self.move_path_down).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="确定", command=lambda: self.save_path_priority(dialog)).pack(side=tk.LEFT,
                                                                                                 padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def move_path_up(self):
        """将选中的路径上移"""
        selected = self.path_listbox.curselection()
        if not selected or selected[0] == 0:
            return
        index = selected[0]
        item = self.path_listbox.get(index)
        self.path_listbox.delete(index)
        self.path_listbox.insert(index - 1, item)
        self.path_listbox.select_set(index - 1)

    def move_path_down(self):
        """将选中的路径下移"""
        selected = self.path_listbox.curselection()
        if not selected or selected[0] == self.path_listbox.size() - 1:
            return
        index = selected[0]
        item = self.path_listbox.get(index)
        self.path_listbox.delete(index)
        self.path_listbox.insert(index + 1, item)
        self.path_listbox.select_set(index + 1)

    def save_path_priority(self, dialog):
        """保存路径优先级顺序"""
        # 获取新的路径顺序
        new_paths = []
        for i in range(self.path_listbox.size()):
            # 从列表项中提取路径信息
            # 这里需要根据实际格式解析路径数据
            # 简单实现：保持原样
            if i < len(self.config["page_paths"]):
                new_paths.append(self.config["page_paths"][i])

        # 更新配置
        self.config["page_paths"] = new_paths
        logging.info("路径优先级已更新")

        # 关闭对话框
        dialog.destroy()

    def start_filling(self):
        """开始填写问卷（优化版）"""
        try:
            # 保存当前配置
            if not self.save_config():
                return

            # 验证基本参数
            if not self.config["url"]:
                messagebox.showerror("错误", "请输入问卷链接")
                return

            try:
                self.config["target_num"] = int(self.target_entry.get())
                if self.config["target_num"] <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("错误", "目标份数必须是正整数")
                return

            # 验证URL格式
            if not re.match(r'^https?://(www\.)?wjx\.cn/vm/[\w\d]+\.aspx(#)?$', self.config["url"]):
                messagebox.showerror("错误", "问卷链接格式不正确")
                return

            # 更新运行状态
            self.running = True
            self.paused = False
            self.cur_num = 0
            self.cur_fail = 0
            self.pause_event.clear()

            # UI状态初始化
            self.main_status_var.set("🚀 启动中...")
            self.action_status_var.set("正在初始化浏览器线程...")
            self.success_count_var.set("0")
            self.fail_count_var.set("0")
            self.progress_var.set(0)
            self.percent_var.set("0.0%")

            # 更新按钮状态
            self.start_btn.config(state=tk.DISABLED)  # 文本由状态栏显示，按钮保持简单
            self.pause_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)

            # 设置进度条初始值
            self.progress_var.set(0)
            self.question_progress_var.set(0)
            self.main_status_var.set("运行中...")  # 修复这里，使用main_status_var

            # 创建并启动线程
            self.threads = []
            for i in range(self.config["num_threads"]):
                x = (i % 2) * 600
                y = (i // 2) * 400
                t = threading.Thread(target=self.run_filling, args=(x, y), daemon=True)
                t.start()
                self.threads.append(t)

            # 启动进度更新线程（不再传参）
            progress_thread = threading.Thread(target=self.update_progress, daemon=True)
            progress_thread.start()

            logging.info(f"启动填写任务，目标份数: {self.config['target_num']}，线程数: {self.config['num_threads']}")

        except Exception as e:
            logging.error(f"启动失败: {str(e)}")
            messagebox.showerror("错误", f"启动失败: {str(e)}")
            # 恢复UI状态
            self.start_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.main_status_var.set("启动失败")
            self.main_status_label.config(foreground="red")

    def quick_set_font_size(self, size):
        """快速设置字体大小"""
        try:
            self.font_size_scale.set(size)
            self.font_size_var.set(str(size))
            self.font_size.set(size)
            self.update_font()
            logging.debug(f"快速设置字体大小为: {size}")
        except Exception as e:
            logging.error(f"快速设置字体大小失败: {e}")
    def run_filling(self, x=0, y=0):
        """
        运行填写任务 - 增强版：自动处理浏览器崩溃和会话断开
        """
        import random
        import time
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException
        import logging
        from selenium.webdriver.chrome.service import Service
        import os

        driver = None
        submit_count = 0
        proxy_ip = None

        WECHAT_UA = (
            "Mozilla/5.0 (Linux; Android 10; MI 8 Build/QKQ1.190828.002; wv) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 "
            "XWEB/4317 MMWEBSDK/20220105 Mobile Safari/537.36 "
            "MicroMessenger/8.0.18.2040(0x28001235) "
            "Process/toolsmp WeChat/arm64 NetType/WIFI Language/zh_CN ABI/arm64"
        )
        PC_UA = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )

        def create_driver(options):
            try:
                # 首先尝试本地ChromeDriver
                chromedriver_path = os.path.join(os.getcwd(), 'chromedriver.exe')
                if os.path.exists(chromedriver_path):
                    service = Service(executable_path=chromedriver_path)
                    return webdriver.Chrome(service=service, options=options)
                else:
                    # 使用webdriver-manager自动管理
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
                    return webdriver.Chrome(service=service, options=options)
            except Exception as e:
                logging.error(f"常规驱动创建失败，尝试备用方案: {e}")
                try:
                    # 最后尝试webdriver-manager
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
                    return webdriver.Chrome(service=service, options=options)
                except Exception as e2:
                    logging.error(f"创建浏览器驱动彻底失败: {e2}")
                    return None

        while self.running and self.cur_num < self.config["target_num"]:
            if self.paused:
                time.sleep(1)
                continue

            # === 1. 配置浏览器选项 ===
            use_weixin = random.random() < float(self.config.get("weixin_ratio", 0.5))
            options = webdriver.ChromeOptions()
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument('--disable-blink-features=AutomationControlled')
            ua = WECHAT_UA if use_weixin else PC_UA
            options.add_argument(f'--user-agent={ua}')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--ignore-certificate-errors')

            # 页面加载策略：eager (加速加载)
            try:
                options.page_load_strategy = 'eager'
            except:
                pass

            if self.config.get("headless", False):
                options.add_argument('--headless=new')
            else:
                options.add_argument(f'--window-position={x},{y}')
                if use_weixin:
                    options.add_argument(f'--window-size=375,812')
                else:
                    options.add_argument(f'--window-size=1024,768')

            # === 2. 代理设置 ===
            use_ip = self.config.get("use_ip", False)
            # 简化代理逻辑：每次都尝试获取新IP，或者沿用有效IP
            if use_ip:
                new_ip = self.get_new_proxy()
                if new_ip:
                    proxy_ip = new_ip
                    logging.info(f"获取新代理IP: {proxy_ip}")

                if proxy_ip:
                    options.add_argument(f'--proxy-server={proxy_ip}')

            # === 3. 创建与维护 Driver ===
            try:
                # 每次都重建 driver 以应用新的 options（UA、代理等）
                if driver is not None:
                    try:
                        driver.quit()
                    except:
                        pass
                driver = create_driver(options)

                if not driver:
                    logging.error("无法启动浏览器，等待5秒重试...")
                    time.sleep(5)
                    continue

                # 访问问卷
                try:
                    driver.get(self.config["url"])
                    time.sleep(self.config["page_load_delay"])
                except Exception as e:
                    logging.warning(f"打开问卷链接失败(可能是网络或驱动问题): {e}")
                    # 如果打开链接就崩了，大概率是驱动坏了，重置
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
                    continue

                # === 4. 执行填写 ===
                success = False
                try:
                    success = self.fill_survey(driver)
                except Exception as e:
                    err_msg = str(e).lower()
                    # 关键修复：捕捉会话失效错误
                    if "invalid session" in err_msg or "closed" in err_msg or "not connected" in err_msg:
                        logging.error("检测到浏览器会话失效，正在重启浏览器...")
                        driver = None
                        continue
                    else:
                        logging.error(f"填写过程发生未知错误: {e}")

                # === 5. 结果处理 ===
                if success:
                    with self.lock:
                        self.cur_num += 1
                    logging.info(f"✅ 第 {self.cur_num} 份问卷提交成功")
                    submit_count += 1
                else:
                    with self.lock:
                        self.cur_fail += 1
                    logging.warning(f"❌ 第 {self.cur_num + 1} 份填写失败")

                # === 6. 提交间隔与维护 ===
                # 每填写N份强制重启一次浏览器，防止内存泄漏或缓存积累
                if submit_count % 5 == 0:
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None

                # 智能等待
                if self.config.get("enable_smart_gap", True):
                    # 如果开启了批量休息
                    batch_size = self.config.get("batch_size", 5)
                    if batch_size > 0 and submit_count % batch_size == 0:
                        pause_min = self.config.get("batch_pause", 15)
                        logging.info(f"已完成 {batch_size} 份，触发批量休息 {pause_min} 分钟...")
                        # 分段休息，保持响应停止信号
                        for _ in range(pause_min * 60):
                            if not self.running: break
                            time.sleep(1)
                    else:
                        # 普通间隔
                        gap = random.uniform(self.config.get("min_submit_gap", 1), self.config.get("max_submit_gap", 3))
                        # 转换为秒（这里假设配置是分钟，如果配置是秒则直接用）
                        # 注意：原配置注释说是分钟，但通常测试时用秒。这里为了安全，若数值小视为秒
                        wait_seconds = gap
                        if wait_seconds > 0:
                            logging.info(f"等待 {wait_seconds:.1f} 秒后继续...")
                            time.sleep(wait_seconds)

            except Exception as e:
                logging.error(f"主循环异常: {str(e)}")
                try:
                    if driver:
                        driver.quit()
                except:
                    pass
                driver = None
                time.sleep(3)

        # 结束清理
        if driver:
            try:
                driver.quit()
            except:
                pass

    def fill_survey(self, driver):
        """
        填写问卷 - 稳健版：防止元素失效(StaleElement)导致的崩溃
        """
        import random
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

        current_page = 1
        max_pages = 20

        # 辅助：尝试查找提交按钮
        def try_find_submit_button():
            selectors = ["#submit_button", "#ctlNext", "#btnSubmit", ".submit-btn", "a.submitbutton",
                         "input[type='submit']"]
            for sel in selectors:
                try:
                    btns = driver.find_elements(By.CSS_SELECTOR, sel)
                    for b in btns:
                        if b.is_displayed(): return b
                except:
                    continue
            return None

        while current_page <= max_pages and self.running:
            logging.info(f"正在处理第 {current_page} 页")

            # 1. 等待页面元素加载
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".div_question, .field, .question, #div1"))
                )
            except TimeoutException:
                logging.warning("页面加载超时，尝试刷新页面...")
                try:
                    driver.refresh()
                    time.sleep(3)
                except:
                    return False  # 刷新失败，可能是浏览器断了
                continue

            # 2. 获取题目数量
            # 注意：这里只获取数量，具体的元素我们在循环中实时获取
            questions = driver.find_elements(By.CSS_SELECTOR, ".div_question, .field, .question")

            # 如果没有题目，可能是因为已经在提交页，或者是纯文本页
            if not questions:
                submit_btn = try_find_submit_button()
                if submit_btn:
                    logging.info("未发现题目但发现提交按钮，尝试提交")
                    return self.submit_survey(driver)

                # 尝试直接翻页
                if self.auto_click_next_page(driver):
                    current_page += 1
                    continue
                else:
                    logging.warning("当前页无题目且无法翻页，流程结束")
                    break

            # 3. 遍历填写每一道题
            # 使用索引遍历，每次循环重新查找元素，完美解决 StaleElementReferenceException
            page_needs_refresh = False

            for i in range(len(questions)):
                if not self.running: return False

                try:
                    # [关键步骤] 重新查找当前页的所有题目，取第 i 个
                    # 这样即使上一题触发了页面刷新，这一行也能获取到最新的DOM元素
                    current_qs = driver.find_elements(By.CSS_SELECTOR, ".div_question, .field, .question")
                    if i >= len(current_qs):
                        break  # 题目数量变少了？跳出

                    q = current_qs[i]

                    # 如果不可见，跳过
                    if not q.is_displayed():
                        continue

                    # 如果已经填写过，跳过
                    if self.is_filled(q):
                        continue

                    # 获取题号
                    q_id = q.get_attribute("id") or str(i)
                    q_num = q_id.replace("div", "").replace("question", "")

                    # 识别并填写
                    q_type = self.detect_question_type_by_dom(q) or self.get_question_type(q_num)

                    # 执行对应的填写函数
                    if q_type == "3":
                        self.fill_single(driver, q, q_num)
                    elif q_type == "4":
                        self.fill_multiple(driver, q, q_num)
                    elif q_type == "5":
                        self.fill_scale(driver, q, q_num)
                    elif q_type == "6" or q_type == "8":
                        self.fill_matrix(driver, q, q_num)
                    elif q_type == "1" or q_type == "2":
                        self.fill_text(driver, q, q_num)
                    elif q_type == "7":
                        self.fill_droplist(driver, q, q_num)
                    elif q_type == "11":
                        self.fill_reorder(driver, q, q_num)
                    else:
                        self.auto_detect_question_type(driver, q, q_num)

                    # 模拟人类操作间隔
                    time.sleep(random.uniform(0.3, 0.8))

                except StaleElementReferenceException:
                    logging.warning(f"第 {i + 1} 题元素已失效，页面可能发生了变动，重新扫描本页...")
                    page_needs_refresh = True
                    break  # 跳出题目循环，重新开始 while 循环
                except Exception as e:
                    logging.debug(f"填写第 {i + 1} 题时出错(非致命): {e}")
                    continue

            # 如果页面结构变动了，重新开始本页循环
            if page_needs_refresh:
                time.sleep(1)
                continue

                # 4. 本页填写完毕，尝试翻页
            if self.auto_click_next_page(driver):
                current_page += 1
                continue

            # 5. 无法翻页，尝试提交
            return self.submit_survey(driver)

        return False

    def detect_question_type_by_dom(self, question):
        """基于DOM结构快速识别题型，返回 '1','2','3','4','5','6','7','11' 或 None"""
        try:
            from selenium.webdriver.common.by import By
            # 矩阵量表题（优先于普通矩阵检测）
            # 识别要点：表格/矩阵结构，每行含多个单选，首行像量表标题，或常见类名
            matrix_scale_hits = []
            for sel in [
                ".matrix-scale", ".scale-matrix", "table.matrix-scale", ".wjx-matrix.scale", ".matrix.likert"
            ]:
                nodes = question.find_elements(By.CSS_SELECTOR, sel)
                if nodes:
                    matrix_scale_hits = nodes
                    break
            if not matrix_scale_hits:
                # 结构启发式：表格行数>2，且每行含多个radio，首行含表头/量表词汇
                rows = question.find_elements(By.CSS_SELECTOR, "tr")
                if len(rows) >= 3:
                    first_row_headers = rows[0].find_elements(By.CSS_SELECTOR, "th, td")
                    header_text = " ".join([h.text for h in first_row_headers])
                    keywords = ["非常", "满意", "一般", "不同意", "赞同", "程度"]
                    radios_in_next = rows[1].find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    if radios_in_next and any(kw in header_text for kw in keywords):
                        return "8"
            if matrix_scale_hits:
                return "8"
            # 排序题
            sort_lis = question.find_elements(By.CSS_SELECTOR,
                                              ".sort-ul li, .sortable li, .wjx-sortable li, .ui-sortable li, .sort-container li, ul.sort-ul > li, ul.sortable > li")
            if sort_lis and len(sort_lis) >= 2:
                return "11"
            # 单选
            radio_btns = question.find_elements(By.CSS_SELECTOR, ".ui-radio, input[type='radio']")
            if radio_btns:
                return "3"
            # 多选
            checkboxes = question.find_elements(By.CSS_SELECTOR, ".ui-checkbox, input[type='checkbox']")
            if checkboxes:
                return "4"
            # 量表（Likert/评分）
            scale_items = []
            for sel in [
                ".scale-ul li", ".scale-item", ".wjx-scale", ".rating-scale",
                ".star-rating", ".likert-scale", ".rating-item", ".rating li", ".scale li", ".likert li", ".star li"
            ]:
                items = question.find_elements(By.CSS_SELECTOR, sel)
                if items:
                    scale_items = items
                    break
            if scale_items and len(scale_items) >= 3:
                return "5"
            # 矩阵
            matrix_rows = []
            for sel in [
                ".matrix tr", ".matrix-row", ".wjx-matrix", ".table-question",
                ".matrix-table", ".grid-question", ".matrix-item", ".table-row",
                ".matrix .matrix-row", ".grid .grid-row", ".table-question tr", ".matrix-table tr", ".grid-table tr"
            ]:
                rows = question.find_elements(By.CSS_SELECTOR, sel)
                if rows:
                    matrix_rows = rows
                    break
            if matrix_rows and len(matrix_rows) >= 2:
                return "6"
            # 下拉
            dropdowns = question.find_elements(By.CSS_SELECTOR, "select, .dropdown, .wjx-select, .select-box, .dropdown-menu, .select-option, [data-type='select']")
            if dropdowns:
                return "7"
            # 填空/多项填空
            spans = question.find_elements(By.CSS_SELECTOR, "span.textCont[contenteditable='true']")
            text_inputs = question.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea")
            if spans or text_inputs:
                # 无法区分1/2，默认填空题
                return "1"
        except Exception:
            return None
        return None

    def find_path_config(self, path):
        """查找匹配的路径配置 - 确保功能完整"""
        # 首先尝试完全匹配
        for config in self.config.get("page_paths", []):
            if config["path"] == path:
                return config

        # 如果没有完全匹配，找最长前缀匹配
        best_match = None
        best_length = 0
        for config in self.config.get("page_paths", []):
            config_path = config["path"]
            if len(config_path) <= len(path) and config_path == path[:len(config_path)]:
                if len(config_path) > best_length:
                    best_match = config
                    best_length = len(config_path)

        return best_match

    def get_selected_options(self, driver, question):
        """获取已选择的选项 - 确保功能完整"""
        selected = []
        try:
            # 单选按钮
            radios = question.find_elements(By.CSS_SELECTOR, "input[type='radio']:checked")
            for radio in radios:
                # 尝试获取选项索引
                try:
                    labels = question.find_elements(By.CSS_SELECTOR, "label")
                    for idx, label in enumerate(labels):
                        if label.get_attribute("for") == radio.get_attribute("id"):
                            selected.append(idx)
                            break
                except:
                    # 备选方案：通过位置关系判断
                    try:
                        all_radios = question.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                        selected.append(all_radios.index(radio))
                    except:
                        pass

            # 多选按钮
            checks = question.find_elements(By.CSS_SELECTOR, "input[type='checkbox']:checked")
            for check in checks:
                try:
                    labels = question.find_elements(By.CSS_SELECTOR, "label")
                    for idx, label in enumerate(labels):
                        if label.get_attribute("for") == check.get_attribute("id"):
                            selected.append(idx)
                            break
                except:
                    # 备选方案：通过位置关系判断
                    try:
                        all_checks = question.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                        selected.append(all_checks.index(check))
                    except:
                        pass

        except Exception as e:
            logging.error(f"获取已选选项时出错: {str(e)}")

        return selected

    def check_jump_rules(self, selected_options):
        """检查跳转规则 - 确保功能完整"""
        for qid, options in selected_options.items():
            if qid in self.config.get("jump_rules", {}):
                jump_rules = self.config["jump_rules"][qid]
                for opt_idx in options:
                    if str(opt_idx) in jump_rules:
                        return jump_rules[str(opt_idx)]
                    # 尝试整型键
                    elif opt_idx in jump_rules:
                        return jump_rules[opt_idx]
        return None

    def try_submit(self, driver):
        """尝试提交问卷 - 增强版，确保功能完整"""
        submit_selectors = [
            "#submit_button", "#ctlNext", "input[value*='提交']",
            "a.submitbutton", "#btnSubmit", ".submit-btn",
            ".submitbutton", ".btn-submit", ".btn-success",
            "button[type='submit']", "input[type='submit']"
        ]

        # 尝试多种选择器
        for selector in submit_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed() and elem.is_enabled():
                        text = elem.text or elem.get_attribute("value") or ""
                        if any(word in text for word in ["提交", "完成", "交卷", "确定", "submit"]):
                            try:
                                # 滚动到元素可见
                                driver.execute_script(
                                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
                                time.sleep(0.5)

                                # 尝试点击
                                elem.click()
                                time.sleep(self.config["submit_delay"])

                                # 检查是否提交成功
                                if "感谢" in driver.page_source or "提交成功" in driver.page_source:
                                    return True
                            except Exception as e:
                                logging.error(f"点击提交按钮失败: {str(e)}")
                                # 尝试JavaScript点击
                                try:
                                    driver.execute_script("arguments[0].click();", elem)
                                    time.sleep(self.config["submit_delay"])
                                    if "感谢" in driver.page_source or "提交成功" in driver.page_source:
                                        return True
                                except:
                                    continue
            except Exception:
                continue

        return False

    def auto_detect_question_type(self, driver, question, q_num):
        """
        自动检测题型并填写 - 增强版，支持量表矩阵等复杂题型
        """
        import random
        import time
        from selenium.webdriver.common.by import By

        try:
            # 1. 排序题检测 - 增强版
            sort_selectors = [
                ".sort-ul li", ".sortable li", ".wjx-sortable li", ".ui-sortable li", 
                ".sort-container li", "ul.sort-ul > li", "ul.sortable > li",
                ".drag-sort li", ".order-list li", "[data-sortable]"
            ]
            sort_lis = []
            for selector in sort_selectors:
                sort_lis = question.find_elements(By.CSS_SELECTOR, selector)
                if sort_lis and len(sort_lis) >= 2:
                    break
            if sort_lis and len(sort_lis) >= 2:
                self.fill_reorder(driver, question, q_num)
                return

            # 2. 通过题目文本检测排序题
            try:
                title_selectors = [
                    ".div_title_question", ".question-title", ".field-label",
                    ".wjx-question-title", ".title", "h3", "h4", ".question-text"
                ]
                title_text = ""
                for selector in title_selectors:
                    try:
                        title_elem = question.find_element(By.CSS_SELECTOR, selector)
                        title_text = title_elem.text.strip()
                        if title_text:
                            break
                    except:
                        continue
                
                if title_text and any(keyword in title_text for keyword in ["排序", "顺序", "拖动", "拖拽", "重新排列"]):
                    self.fill_reorder(driver, question, q_num)
                    return
            except Exception:
                pass

            # 3. 单选题检测 - 增强版
            radio_selectors = [
                ".ui-radio", "input[type='radio']", ".radio-item", ".wjx-radio",
                ".radio-option", ".single-choice", "[data-type='radio']"
            ]
            radio_btns = []
            for selector in radio_selectors:
                radio_btns = question.find_elements(By.CSS_SELECTOR, selector)
                if radio_btns:
                    break
            if radio_btns:
                self.fill_single(driver, question, q_num)
                return

            # 4. 多选题检测 - 增强版
            checkbox_selectors = [
                ".ui-checkbox", "input[type='checkbox']", ".checkbox-item", ".wjx-checkbox",
                ".checkbox-option", ".multi-choice", "[data-type='checkbox']"
            ]
            checkboxes = []
            for selector in checkbox_selectors:
                checkboxes = question.find_elements(By.CSS_SELECTOR, selector)
                if checkboxes:
                    break
            if checkboxes:
                self.fill_multiple(driver, question, q_num)
                return

            # 5. 量表题检测 - 增强版
            scale_selectors = [
                ".scale-ul li", ".scale-item", ".wjx-scale", ".rating-scale", 
                ".star-rating", ".likert-scale", ".scale-option", ".rating-item",
                ".scale-ul .scale-item", ".rating-ul li", ".star-item"
            ]
            for selector in scale_selectors:
                scale_items = question.find_elements(By.CSS_SELECTOR, selector)
                if scale_items and len(scale_items) >= 3:  # 量表至少3个选项
                    self.fill_scale(driver, question, q_num)
                    return

            # 6. 矩阵题检测 - 增强版
            matrix_selectors = [
                ".matrix tr", ".matrix-row", ".wjx-matrix", ".table-question", 
                ".matrix-table", ".grid-question", ".matrix-item", ".table-row",
                ".matrix .matrix-row", ".grid .grid-row", ".table-question tr"
            ]
            for selector in matrix_selectors:
                matrix_rows = question.find_elements(By.CSS_SELECTOR, selector)
                if matrix_rows and len(matrix_rows) >= 2:  # 矩阵至少2行
                    self.fill_matrix(driver, question, q_num)
                    return

            # 7. 下拉框检测 - 增强版
            dropdown_selectors = [
                "select", ".dropdown", ".wjx-select", ".select-box", 
                ".dropdown-menu", ".select-option", "[data-type='select']"
            ]
            dropdowns = []
            for selector in dropdown_selectors:
                dropdowns = question.find_elements(By.CSS_SELECTOR, selector)
                if dropdowns:
                    break
            if dropdowns:
                self.fill_droplist(driver, question, q_num)
                return

            # 8. 填空题/多项填空检测 - 增强版
            text_selectors = [
                "span.textCont[contenteditable='true']", "input[type='text']", "textarea",
                ".text-input", ".input-field", ".text-area", "[contenteditable='true']"
            ]
            text_inputs = []
            for selector in text_selectors:
                text_inputs.extend(question.find_elements(By.CSS_SELECTOR, selector))
            
            if text_inputs and len(text_inputs) >= 1:
                self.fill_text(driver, question, q_num)
                return

            # 9. 通用点击处理 - 增强版
            clickable_selectors = [
                "li", "label", "button", ".clickable", ".option", ".choice",
                ".selectable", "[onclick]", "[data-click]"
            ]
            for selector in clickable_selectors:
                clickable = question.find_elements(By.CSS_SELECTOR, selector)
                for elem in clickable:
                    if elem.is_displayed() and elem.is_enabled():
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
                            elem.click()
                            self.random_delay(*self.config.get("per_question_delay", (1.0, 3.0)))
                            return
                        except Exception:
                            continue

            # 10. 兜底处理
            text_inputs = question.find_elements(By.CSS_SELECTOR, "input, textarea")
            for inp in text_inputs:
                if inp.is_displayed() and not inp.get_attribute("value"):
                    try:
                        inp.send_keys("自动填写内容")
                        self.random_delay(*self.config.get("per_question_delay", (1.0, 3.0)))
                        return
                    except Exception:
                        continue

            import logging
            logging.warning(f"无法自动检测题目 {q_num} 的类型，尝试通用方法")
        except Exception as e:
            import logging
            logging.error(f"自动检测题目类型时出错: {str(e)}")
    def fill_text(self, driver, question, q_num, path_config=None):
        """填空题/多项填空题自动填写 - 优化日志版"""
        import random
        import time
        import logging
        from selenium.webdriver.common.by import By

        q_key = str(q_num)
        # 获取所有可填写的控件
        editable_spans = question.find_elements(By.CSS_SELECTOR, "span.textCont[contenteditable='true']")
        visible_inputs = [el for el in question.find_elements(By.CSS_SELECTOR, "input[type='text']") if
                          el.is_displayed()]
        visible_textareas = [el for el in question.find_elements(By.CSS_SELECTOR, "textarea") if el.is_displayed()]
        all_fields = editable_spans + visible_inputs + visible_textareas
        if not all_fields:
            all_fields = [el for el in question.find_elements(By.CSS_SELECTOR, "input") if el.is_displayed()]

        if not all_fields:
            logging.debug(f"题目 {q_num} 未找到可填写的输入框")
            return

        # ==== AI自动答题优先 ====
        answers = []
        ai_enabled = self.config.get("ai_fill_enabled", False)
        api_key = self.config.get("openai_api_key", "")
        prompt_template = self.config.get("ai_prompt_template", "请用简洁、自然的中文回答：{question}")
        question_text = self.config.get("question_texts", {}).get(q_key, "")

        if ai_enabled and api_key and question_text:
            try:
                service = self.config.get("ai_service", "质谱清言")
                if service == "OpenAI":
                    # 使用OpenAI接口
                    ai_answer = self.ai_generate_answer(question_text, api_key, prompt_template)
                else:
                    # 使用质谱清言接口
                    ai_answer = self.zhipu_generate_answer(question_text, api_key, prompt_template)
                answers = [ai_answer] * len(all_fields)
                logging.info(f"使用{service}生成答案: {ai_answer[:20]}...")
            except Exception as e:
                logging.warning(f"AI答题失败: {str(e)}")
                answers = [self.get_identity_answer("", question_text)] * len(all_fields)

        elif q_key in self.config.get("multiple_texts", {}):
            ans_lists = self.config["multiple_texts"][q_key]
            for i in range(len(all_fields)):
                if i < len(ans_lists) and ans_lists[i]:
                    chosen = random.choice(ans_lists[i])
                    answers.append(chosen)
                else:
                    answers.append("自动填写内容")
        elif q_key in self.config.get("texts", {}):
            ans_list = self.config["texts"][q_key]
            for i in range(len(all_fields)):
                chosen = random.choice(ans_list) if ans_list else "自动填写内容"
                answers.append(chosen)
        else:
            answers = ["自动填写内容"] * len(all_fields)

        # ==== 填写答案 ====
        for idx, field in enumerate(all_fields):
            val = (field.tag_name == "span" and field.text.strip()) or (field.get_attribute("value"))
            if val:
                continue  # 已有内容不覆盖

            answer = answers[idx] if idx < len(answers) else "自动填写内容"

            if field.tag_name == "span" and field.get_attribute("contenteditable") == "true":
                try:
                    driver.execute_script("arguments[0].innerText = '';", field)
                    for ch in answer:
                        field.send_keys(ch)
                        time.sleep(random.uniform(0.01, 0.03))
                except Exception:
                    driver.execute_script("arguments[0].innerText = arguments[1];", field, answer)
                try:
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", field)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", field)
                except Exception:
                    pass
            else:
                try:
                    field.clear()
                except Exception:
                    pass
                try:
                    for ch in answer:
                        field.send_keys(ch)
                        time.sleep(random.uniform(0.01, 0.03))
                except Exception:
                    driver.execute_script("arguments[0].value = arguments[1];", field, answer)
                try:
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", field)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", field)
                except Exception:
                    pass

        self.random_delay(*self.config.get("per_question_delay", (1.0, 3.0)))
        logging.info(f"已填写题目 {q_num}")

    def repair_required_questions(self, driver):
        """
        检查所有必答项，自动补全未填写项，包括"其他"多选题下的必答填空。
        """
        try:
            questions = driver.find_elements(By.CSS_SELECTOR, ".div_question, .field, .question")
            for q in questions:
                is_required = False
                # 判断必答标记
                try:
                    if q.find_element(By.CSS_SELECTOR, ".required, .star, .necessary, .wjxnecessary"):
                        is_required = True
                except:
                    if "必答" in q.text or q.get_attribute("data-required") == "1":
                        is_required = True
                if not is_required:
                    continue

                all_inputs = q.find_elements(By.CSS_SELECTOR, "input, textarea, select")
                any_filled = False
                for inp in all_inputs:
                    typ = inp.get_attribute("type")
                    if typ in ("checkbox", "radio"):
                        if inp.is_selected():
                            any_filled = True
                            # 检查"其他"选项的填空
                            if "其他" in inp.get_attribute("value") or "other" in (inp.get_attribute("id") or ""):
                                try:
                                    other_text = q.find_element(By.CSS_SELECTOR, "input[type='text'], textarea")
                                    if not other_text.get_attribute("value"):
                                        other_text.send_keys("自动补全内容")
                                except:
                                    pass
                    elif typ in ("text", None):
                        if inp.get_attribute("value"):
                            any_filled = True
                    elif typ == "select-one":
                        if inp.get_attribute("value"):
                            any_filled = True
                # 未填写自动补全
                if not any_filled:
                    self.auto_fill_question(driver, q)
        except Exception as e:
            logging.warning(f"自动修复必答题时出错: {e}")

    def auto_fill_question(self, driver, question):
        """
        自动补全问题 - 修复版，确保多选题中的'其他'文本必填
        """
        import random
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import StaleElementReferenceException

        try:
            # 1. 单选题
            try:
                radios = question.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                if radios:
                    random.choice(radios).click()
                    return
            except StaleElementReferenceException:
                pass

            # 2. 多选题
            try:
                checks = question.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                if checks:
                    # 随机勾选一个
                    chosen = random.choice(checks)
                    try:
                        chosen.click()
                    except:
                        driver.execute_script("arguments[0].click();", chosen)

                    # 获取选项文本
                    option_labels = []
                    label_elems = question.find_elements(By.CSS_SELECTOR, "label")
                    for el in label_elems:
                        try:
                            txt = el.text.strip()
                            if not txt:
                                spans = el.find_elements(By.CSS_SELECTOR, "span")
                                if spans:
                                    txt = spans[0].text.strip()
                            option_labels.append(txt)
                        except StaleElementReferenceException:
                            option_labels.append("")

                    # 检查是否有"其他"选项被选中
                    chose_other = False
                    for idx, chk in enumerate(checks):
                        try:
                            if chk.is_selected() and idx < len(option_labels):
                                label_text = option_labels[idx]
                                if "其他" in label_text or "other" in label_text.lower():
                                    chose_other = True
                                    break
                        except:
                            continue

                    # 如果选中了"其他"选项，填写文本框
                    if chose_other:
                        # 增强定位策略
                        locator_strategies = [
                            (By.XPATH, f".//input[preceding-sibling::label[contains(., '其他')]]"),
                            (By.CSS_SELECTOR, "input[placeholder*='其他'], input[placeholder*='请填写']"),
                            (By.CLASS_NAME, "OtherText"),
                            (By.XPATH, ".//div[contains(@class, 'other')]//input"),
                            (By.CSS_SELECTOR, "input[type='text'], textarea")
                        ]

                        other_inputs = []
                        for strategy in locator_strategies:
                            try:
                                found_inputs = question.find_elements(strategy[0], strategy[1])
                                if found_inputs:
                                    other_inputs = found_inputs
                                    break
                            except:
                                continue

                        # 全局查找
                        if not other_inputs:
                            for strategy in locator_strategies:
                                try:
                                    found_inputs = driver.find_elements(strategy[0], strategy[1])
                                    if found_inputs:
                                        other_inputs = found_inputs
                                        break
                                except:
                                    continue

                        # 填写找到的第一个可见文本框
                        for inp in other_inputs:
                            try:
                                if inp.is_displayed() and not inp.get_attribute("value"):
                                    try:
                                        inp.send_keys("自动补全内容")
                                        logging.info("成功补全'其他'文本框")
                                        break
                                    except:
                                        try:
                                            driver.execute_script("arguments[0].value = '自动补全内容';", inp)
                                            logging.info("通过JS补全'其他'文本框")
                                            break
                                        except:
                                            pass
                            except:
                                continue
                    return
            except StaleElementReferenceException:
                pass

            # 3. 填空题
            try:
                texts = question.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea")
                if texts:
                    for t in texts:
                        if not t.get_attribute("value") and t.is_displayed():
                            try:
                                t.send_keys("自动补全内容")
                            except:
                                try:
                                    driver.execute_script("arguments[0].value = '自动补全内容';", t)
                                except:
                                    pass
                    return
            except StaleElementReferenceException:
                pass

            # 4. 下拉框
            try:
                selects = question.find_elements(By.CSS_SELECTOR, "select")
                if selects:
                    for sel in selects:
                        options = sel.find_elements(By.TAG_NAME, "option")
                        for op in options:
                            try:
                                if op.get_attribute("value") and not op.get_attribute("disabled"):
                                    sel.send_keys(op.get_attribute("value"))
                                    break
                            except:
                                continue
                    return
            except StaleElementReferenceException:
                pass

            # 5. 最后尝试：点击任何可点击元素
            try:
                clickable_elements = question.find_elements(By.CSS_SELECTOR,
                                                            "li, label, div[onclick], span[onclick], .option")
                if clickable_elements:
                    element = random.choice(clickable_elements)
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                          element)
                    time.sleep(0.2)
                    element.click()
                    return
            except StaleElementReferenceException:
                pass

            logging.warning("无法自动补全问题")
        except Exception as e:
            logging.error(f"自动补全题目时出错: {str(e)}")

    def submit_survey(self, driver):

        import time
        import random
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException

        # 内部工具函数
        def is_submit_success():
            """判断问卷是否已提交成功"""
            try:
                if hasattr(self, '_original_url') and driver.current_url != self._original_url:
                    return True
                page = driver.page_source.lower()
                success_texts = [
                    "感谢", "提交成功", "问卷已完成", "谢谢您的参与", "再次填写",
                    "thank", "success", "complete", "finished"
                ]
                if any(t in page for t in success_texts):
                    return True
                selectors = [
                    "div.complete", ".survey-success", ".end-page",
                    ".finish-container", ".thank-you-page"
                ]
                for sel in selectors:
                    if driver.find_elements(By.CSS_SELECTOR, sel):
                        return True
                return False
            except Exception:
                return False

        def smart_click(element):
            """多方式尝试点击元素"""
            try:
                if not element.is_displayed() or not element.is_enabled():
                    return False
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", element
                )
                time.sleep(0.2)
                try:
                    element.click()
                    return True
                except Exception:
                    driver.execute_script("arguments[0].click();", element)
                    return True
            except Exception:
                return False

        def find_and_click_submit():
            """智能查找并点击提交按钮"""
            selectors = [
                "#ctlNext", "#submit_button", ".submit-btn", ".submitbutton",
                "a[id*='submit']", "button[type='submit']", "input[type='submit']",
                "div.submit", ".btn-submit", ".btn-success", "#submit_btn",
                "#next_button", ".next-button"
            ]
            for sel in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, sel)
                    for elem in elements:
                        if smart_click(elem):
                            return True
                except Exception:
                    continue
            # 尝试文本查找
            texts = ["提交", "submit", "完成", "交卷", "提交问卷", "确定"]
            for txt in texts:
                try:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(),'{txt}')]")
                    for elem in elements:
                        if smart_click(elem):
                            return True
                except Exception:
                    continue
            return False

        def solve_slider():
            """全自动滑块验证码处理"""
            try:
                # 多种滑块兼容
                slider = None
                selectors = [
                    "#nc_1_n1z",
                    "//div[contains(@class,'nc_slider_btn')]",
                    ".yidun_slider",
                    ".slider-btn"
                ]
                for sel in selectors:
                    try:
                        if sel.startswith("//"):
                            slider = driver.find_element(By.XPATH, sel)
                        else:
                            slider = driver.find_element(By.CSS_SELECTOR, sel)
                        if slider:
                            break
                    except NoSuchElementException:
                        continue
                if not slider:
                    return False

                bar = slider.find_element(By.XPATH, "../..")
                bar_width = bar.size['width']
                slider_width = slider.size['width']
                distance = bar_width - slider_width - random.randint(6, 12)

                def get_tracks(total, duration=1.7):
                    """生成拟人化轨迹"""
                    tracks = []
                    v = 0
                    t = 0.18
                    current = 0
                    mid = total * 0.8
                    while current < total:
                        if current < mid:
                            a = random.uniform(2, 4)
                        else:
                            a = -random.uniform(3, 5)
                        v0 = v
                        v = v0 + a * t
                        move = v0 * t + 0.5 * a * t * t
                        move = int(max(1, round(move)))
                        if current + move > total:
                            move = total - current
                        tracks.append(move)
                        current += move
                    for _ in range(3):
                        tracks.append(-random.randint(1, 2))
                        tracks.append(random.randint(1, 2))
                    return tracks

                tracks = get_tracks(distance)
                action = ActionChains(driver)
                action.click_and_hold(slider).perform()
                for x in tracks:
                    y = random.randint(-2, 2)
                    action.move_by_offset(xoffset=x, yoffset=y).perform()
                    time.sleep(random.uniform(0.012, 0.034))
                for _ in range(2):
                    action.move_by_offset(1, 0).perform()
                    time.sleep(0.09)
                    action.move_by_offset(-1, 0).perform()
                    time.sleep(0.09)
                action.release().perform()
                time.sleep(1.2)
                return True
            except Exception as e:
                print(f"[滑块拖动失败] {e}")
                return False

        def handle_dialogs():
            """自动关闭常见弹窗"""
            dialog_selectors = [
                '//*[@id="layui-layer1"]/div[3]/a',
                '//*[@id="SM_BTN_1"]',
                "//a[contains(text(),'确定')]",
                "//button[contains(text(),'好的')]"
            ]
            for sel in dialog_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, sel)
                    for elem in elements:
                        if elem.is_displayed():
                            smart_click(elem)
                            time.sleep(0.3)
                except Exception:
                    continue

        def repair_and_submit():
            """自动修复必填和验证码相关问题"""
            try:
                hints = driver.find_elements(
                    By.XPATH, "//*[contains(text(),'必答题') or contains(text(),'请填写')]"
                )
                if hints:
                    self.repair_required_questions(driver)
                    return True
                if "验证码" in driver.page_source or "请完成验证" in driver.page_source:
                    for _ in range(3):
                        if solve_slider():
                            break
                        time.sleep(1)
                    return True
                return False
            except Exception:
                return False

        # 主流程
        try:
            self._original_url = driver.current_url
        except Exception:
            self._original_url = None

        max_attempts = 8
        for attempt in range(max_attempts):
            try:
                if not find_and_click_submit():
                    print(f"第{attempt + 1}次尝试：未找到可用的提交按钮")
                    continue
                time.sleep(1.1)
                handle_dialogs()
                time.sleep(0.8)
                for _ in range(3):  # 验证码最多尝试3次
                    if solve_slider():
                        break
                    time.sleep(1)
                for _ in range(10):
                    if is_submit_success():
                        print("问卷提交成功！")
                        return True
                    time.sleep(1)
                if repair_and_submit():
                    continue
                print(f"第{attempt + 1}次提交未成功，刷新重试...")
                driver.refresh()
                time.sleep(2)
            except Exception as e:
                print(f"提交过程异常: {e}")
                driver.refresh()
                time.sleep(2)
        print("达到最大重试次数，提交失败")
        return False
    def fill_droplist(self, driver, question, q_num, path_config=None):
        """
        增强版下拉框题目填写方法 - 支持原生select和自定义下拉框
        """
        import random
        import time
        import numpy as np
        import logging
        import datetime
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.common.exceptions import (NoSuchElementException,
                                                ElementNotInteractableException,
                                                StaleElementReferenceException)

        logging.info(f"开始处理下拉框题目 {q_num}")
        try:
            q_key = str(q_num)
            # 获取配置的概率
            probs = self.config.get("droplist_prob", {}).get(q_key, None)

            # 尝试定位原生select元素
            try:
                select_elem = question.find_element(By.CSS_SELECTOR, "select")
                logging.info(f"找到原生select元素")

                # 创建Select对象
                select = Select(select_elem)
                options = select.options

                # 过滤无效选项
                valid_options = []
                for idx, op in enumerate(options):
                    try:
                        # 跳过禁用项和"请选择"选项
                        if op.get_attribute("disabled") or op.text.strip() in ["请选择", "Select", "--请选择--"]:
                            continue
                        # 如果value为空但文本有效，也算有效选项
                        if not op.get_attribute("value") and op.text.strip():
                            valid_options.append((idx, op))
                        elif op.get_attribute("value") and op.get_attribute("value").strip():
                            valid_options.append((idx, op))
                    except StaleElementReferenceException:
                        continue

                if not valid_options:
                    logging.warning(f"题目 {q_num} 未找到有效下拉选项")
                    return

                logging.info(f"题目 {q_num} 有 {len(valid_options)} 个有效选项")

                # 处理概率配置（支持-1随机，或相对权重归一化）
                if probs and isinstance(probs, list) and len(probs) == len(valid_options):
                    try:
                        if any(str(p) in ('-1', '-1.0') for p in probs):
                            raise ValueError('contains -1 -> random')
                        weights = [float(p) for p in probs]
                        total = sum(weights)
                        if total > 0:
                            weights = [w / total for w in weights]
                            selected_idx = np.random.choice(range(len(valid_options)), p=weights)
                            logging.info(f"使用概率选择: 索引 {selected_idx}")
                        else:
                            selected_idx = random.randint(0, len(valid_options) - 1)
                            logging.info(f"概率总和为零，随机选择: 索引 {selected_idx}")
                    except Exception as e:
                        logging.warning(f"概率处理失败或存在-1，使用随机选择: {str(e)}")
                        selected_idx = random.randint(0, len(valid_options) - 1)
                else:
                    selected_idx = random.randint(0, len(valid_options) - 1)
                    logging.info(f"无有效概率配置，随机选择: 索引 {selected_idx}")

                # 获取选中的选项
                idx, op = valid_options[selected_idx]
                option_text = op.text.strip()
                option_value = op.get_attribute("value") or option_text

                # 使用Select类进行选择
                try:
                    logging.info(f"尝试通过索引选择: {idx}")
                    select.select_by_index(idx)
                    logging.info(f"选择选项: {option_text}")
                except Exception as e:
                    try:
                        logging.info(f"索引选择失败，尝试按值选择: {option_value}")
                        select.select_by_value(option_value)
                    except:
                        try:
                            logging.info(f"值选择失败，尝试按文本选择: {option_text}")
                            select.select_by_visible_text(option_text)
                        except Exception as e2:
                            logging.error(f"所有选择方式失败: {str(e2)}")
                            # 使用JS直接设置值
                            js = f"""
                            var select = arguments[0];
                            select.selectedIndex = {idx};
                            var event = new Event('change', {{ bubbles: true }});
                            select.dispatchEvent(event);
                            """
                            driver.execute_script(js, select_elem)
                            logging.info("使用JS设置下拉框值")

                self.random_delay(*self.config.get("per_question_delay", (1.0, 3.0)))
                return
            except NoSuchElementException:
                logging.info("未找到原生select元素，尝试自定义下拉框")
            except Exception as e:
                logging.warning(f"原生select处理失败: {str(e)}")

            # 处理自定义下拉框
            try:
                # 查找自定义下拉框触发器
                triggers = question.find_elements(By.CSS_SELECTOR,
                                                  ".custom-select, .dropdown-toggle, .select-box, .ant-select-selection")
                if not triggers:
                    logging.info("未找到自定义下拉框触发器")
                    return

                trigger = triggers[0]
                logging.info(f"找到自定义下拉框触发器: {trigger.get_attribute('outerHTML')[:100]}")

                # 滚动到元素并点击展开
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", trigger)
                time.sleep(0.3)

                # 确保元素可见
                if not trigger.is_displayed():
                    logging.info("触发器不可见，尝试滚动页面")
                    actions = ActionChains(driver)
                    actions.move_to_element(trigger).perform()
                    time.sleep(0.5)

                try:
                    trigger.click()
                    logging.info("点击展开下拉框")
                except ElementNotInteractableException:
                    logging.info("点击失败，使用JS点击")
                    driver.execute_script("arguments[0].click();", trigger)

                time.sleep(0.8)  # 等待下拉框展开

                # 获取所有选项 - 使用更广泛的CSS选择器
                option_selectors = [
                    ".option",
                    ".dropdown-item",
                    ".select-item",
                    ".ant-select-dropdown-menu-item",
                    ".menu-item",
                    ".item",
                    "li"
                ]

                option_elems = []
                for selector in option_selectors:
                    try:
                        found = driver.find_elements(By.CSS_SELECTOR, selector)
                        if found:
                            option_elems = found
                            logging.info(f"使用选择器 '{selector}' 找到 {len(option_elems)} 个选项")
                            break
                    except:
                        continue

                if not option_elems:
                    logging.warning("未找到下拉选项")
                    return

                # 过滤无效选项
                valid_options = []
                for op in option_elems:
                    try:
                        if not op.is_displayed():
                            continue
                        text = op.text.strip()
                        if not text or "请选择" in text:
                            continue
                        if op.get_attribute("disabled") or op.get_attribute("aria-disabled") == "true":
                            continue
                        valid_options.append(op)
                    except StaleElementReferenceException:
                        continue

                if not valid_options:
                    logging.warning("未找到有效选项")
                    return

                logging.info(f"找到 {len(valid_options)} 个有效选项")

                # 处理概率配置（支持-1随机，或相对权重归一化）
                if probs and isinstance(probs, list) and len(probs) == len(valid_options):
                    try:
                        if any(str(p) in ('-1', '-1.0') for p in probs):
                            raise ValueError('contains -1 -> random')
                        weights = [float(p) for p in probs]
                        total = sum(weights)
                        if total > 0:
                            weights = [w / total for w in weights]
                            selected = np.random.choice(valid_options, p=weights)
                        else:
                            selected = random.choice(valid_options)
                    except Exception as e:
                        logging.warning(f"概率处理失败或存在-1，使用随机选择: {str(e)}")
                        selected = random.choice(valid_options)
                else:
                    selected = random.choice(valid_options)

                # 点击选中
                try:
                    logging.info(f"尝试点击选项: {selected.text[:20]}...")
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                          selected)
                    time.sleep(0.2)
                    selected.click()
                    time.sleep(0.5)
                except Exception as e:
                    logging.warning(f"点击选项失败: {str(e)}，使用JS点击")
                    driver.execute_script("arguments[0].click();", selected)

                self.random_delay(*self.config.get("per_question_delay", (1.0, 3.0)))
                return
            except Exception as e:
                logging.error(f"自定义下拉框处理失败: {str(e)}")

            # 最终尝试：直接使用JavaScript设置值
            try:
                logging.info("尝试最终方案：JS设置值")
                # 获取选项文本列表
                option_texts = self.config.get("option_texts", {}).get(q_key, [])
                if not option_texts:
                    logging.warning("无选项文本配置")
                    return

                # 随机选择一个选项
                selected_text = random.choice(option_texts)
                logging.info(f"随机选择文本: {selected_text}")

                # 查找所有select元素
                selects = driver.find_elements(By.CSS_SELECTOR, "select")
                if not selects:
                    logging.info("无select元素")
                    return

                for sel in selects:
                    # 使用JS设置值
                    js = f"""
                    var select = arguments[0];
                    var found = false;
                    for (var i = 0; i < select.options.length; i++) {{
                        if (select.options[i].text === '{selected_text}') {{
                            select.selectedIndex = i;
                            found = true;
                            break;
                        }}
                    }}
                    if (!found) {{
                        for (var i = 0; i < select.options.length; i++) {{
                            if (select.options[i].text.includes('{selected_text}')) {{
                                select.selectedIndex = i;
                                found = true;
                                break;
                            }}
                        }}
                    }}
                    if (found) {{
                        var event = new Event('change', {{ bubbles: true }});
                        select.dispatchEvent(event);
                    }}
                    """
                    driver.execute_script(js, sel)
                    logging.info("执行JS设置下拉框值")

                self.random_delay(*self.config.get("per_question_delay", (1.0, 3.0)))
            except Exception as e:
                logging.error(f"最终JS设置下拉框值失败: {str(e)}")

        except Exception as e:
            logging.error(f"填写下拉框题 {q_num} 时出错: {str(e)}")
            # 截图保存当前页面状态
            try:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"error_droplist_q{q_num}_{timestamp}.png"
                driver.save_screenshot(screenshot_path)
                logging.info(f"已保存错误截图: {screenshot_path}")
            except:
                logging.error("无法保存截图")

    def verify_submission(self, driver):
        """多维度验证提交是否成功"""
        # 1. 检查URL特征
        current_url = driver.current_url
        if any(keyword in current_url for keyword in ["complete", "success", "finish", "end", "thank"]):
            return True

        # 2. 检查页面关键元素
        success_selectors = [
            "div.complete",
            "div.survey-complete",
            "div.text-success",
            "img[src*='success']",
            ".survey-success",
            ".end-page",
            ".endtext",
            ".finish-container",
            ".thank-you-page"
        ]

        for selector in success_selectors:
            try:
                if driver.find_element(By.CSS_SELECTOR, selector):
                    return True
            except:
                continue

        # 3. 检查关键文本
        success_phrases = [
            "提交成功", "问卷已完成", "感谢参与",
            "success", "completed", "thank you",
            "问卷提交成功", "提交成功", "已完成",
            "感谢您的参与", "提交完毕", "finish",
            "问卷结束", "谢谢您的参与"
        ]

        page_text = driver.page_source.lower()
        if any(phrase.lower() in page_text for phrase in success_phrases):
            return True

        # 4. 检查错误消息缺失
        error_phrases = [
            "验证码", "错误", "失败", "未提交",
            "error", "fail", "captcha", "未完成",
            "请检查", "不正确", "需要验证"
        ]

        if not any(phrase in page_text for phrase in error_phrases):
            return True

        return False

    # ================== 增强验证码处理 ==================
    def handle_captcha(self, driver):
        """增强的验证码处理"""
        try:
            # 检查多种验证码形式
            captcha_selectors = [
                "div.captcha-container",
                "div.geetest_panel",
                "iframe[src*='captcha']",
                "div#captcha",
                ".geetest_holder",
                ".nc-container",
                ".captcha-modal"
            ]

            # 检查验证码是否存在
            for selector in captcha_selectors:
                try:
                    captcha = driver.find_element(By.CSS_SELECTOR, selector)
                    if captcha.is_displayed():
                        logging.warning("检测到验证码，尝试自动处理")
                        self.pause_for_captcha()
                        return True
                except:
                    continue

            # 检查页面是否有验证码文本提示
            captcha_phrases = ["验证码", "captcha", "验证", "请完成验证"]
            page_text = driver.page_source.lower()
            if any(phrase in page_text for phrase in captcha_phrases):
                logging.warning("页面检测到验证码提示，暂停程序")
                self.pause_for_captcha()
                return True

        except Exception as e:
            logging.error(f"验证码处理出错: {str(e)}")

        return False

    def pause_for_captcha(self):
        """暂停程序并提醒用户处理验证码"""
        self.paused = True
        self.pause_btn.config(text="继续")

        # 创建提醒窗口
        alert = tk.Toplevel(self.root)
        alert.title("需要验证码")
        alert.geometry("400x200")
        alert.resizable(False, False)

        msg = ttk.Label(alert, text="检测到验证码，请手动处理并点击继续", font=("Arial", 12))
        msg.pack(pady=20)

        # 添加倒计时
        countdown_var = tk.StringVar(value="窗口将在 60 秒后自动继续")
        countdown_label = ttk.Label(alert, textvariable=countdown_var, font=("Arial", 10))
        countdown_label.pack(pady=10)

        def resume_after_timeout(seconds=60):
            if seconds > 0:
                countdown_var.set(f"窗口将在 {seconds} 秒后自动继续")
                alert.after(1000, lambda: resume_after_timeout(seconds - 1))
            else:
                self.paused = False
                self.pause_btn.config(text="暂停")
                alert.destroy()

        # 手动继续按钮
        continue_btn = ttk.Button(alert, text="我已处理验证码",
                                  command=lambda: [alert.destroy(), self.toggle_pause()])
        continue_btn.pack(pady=10)

        # 开始倒计时
        resume_after_timeout()

        # 置顶窗口
        alert.attributes('-topmost', True)
        alert.update()
        alert.attributes('-topmost', False)



    def fill_single(self, driver, question, q_num, path_config=None):
        """
        单选题自动填写，兼容新版问卷星自定义UI，优先点击label或外层div，保证前端能识别选中。
        并自动填写被选中选项关联的弹出文本框（AI优先）。
        """
        import random, time
        from selenium.webdriver.common.by import By
        import logging

        # 1. 先找所有可见input[type=radio]
        radios = question.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        if not radios:
            return

        q_key = str(q_num)
        probs = self.config.get("single_prob", {}).get(q_key, -1)

        # 2. 结合逻辑规则/权重选择
        option_texts = self._extract_option_texts(question, radios)
        must_idx, avoid_idx, prefer_idx, _, _ = self._apply_logic_rules(q_key, option_texts)

        # 构建候选集合
        if must_idx:
            candidates = list(must_idx)
        else:
            candidates = [i for i in range(len(radios)) if i not in avoid_idx]
            if not candidates:
                candidates = list(range(len(radios)))

        # 权重处理
        if isinstance(probs, list) and not any(str(v) in ('-1', '-1.0') for v in probs):
            weights = probs[:len(radios)] if len(probs) > len(radios) else probs + [1.0] * (len(radios) - len(probs))
            try:
                weights = [float(w) for w in weights]
            except Exception:
                weights = [1.0] * len(radios)
        else:
            weights = [1.0] * len(radios)

        # 逻辑规则加权/排除
        for i in range(len(weights)):
            if i in avoid_idx and i not in must_idx:
                weights[i] = 0.0
            if i in prefer_idx:
                weights[i] = weights[i] * 1.5

        # 选取
        if candidates:
            picked = self._weighted_sample_indices(weights, candidates, 1)
            selected_idx = picked[0] if picked else random.choice(candidates)
        else:
            selected_idx = random.randint(0, len(radios) - 1)

        selected_radio = radios[selected_idx]

        # 3. 优先找label[for=id]，否则点父节点，最后才点input本身
        input_id = selected_radio.get_attribute("id")
        label = None
        if input_id:
            try:
                label = question.find_element(By.CSS_SELECTOR, f"label[for='{input_id}']")
            except:
                label = None
        if not label:
            try:
                label = selected_radio.find_element(By.XPATH, "./..")
            except:
                label = None
        if not label:
            try:
                label = selected_radio.find_element(By.XPATH, "../..")
            except:
                label = None

        clicked = False
        for elem in [label, selected_radio]:
            if elem is not None:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
                    if elem.is_displayed() and elem.is_enabled():
                        elem.click()
                        clicked = True
                        break
                except Exception:
                    continue

        # 强制触发change/input事件
        try:
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", selected_radio)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", selected_radio)
        except Exception:
            pass

        # 检查input是否变为选中，否则再强制用JS选中并触发事件
        try:
            is_checked = selected_radio.is_selected() or selected_radio.get_attribute("checked")
            if not is_checked:
                driver.execute_script("arguments[0].checked = true;", selected_radio)
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                                      selected_radio)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                                      selected_radio)
        except Exception:
            pass

        # ==== 新增：点选后自动填写该题下所有空白文本框（AI优先） ====
        time.sleep(0.5)  # 等待弹框动画
        self.fill_associated_textbox(
            driver, question, selected_radio,
            ai_enabled=self.config.get("ai_fill_enabled", False),
            ai_api_key=self.config.get("openai_api_key", ""),
            ai_prompt_template=self.config.get("ai_prompt_template", "请用简洁、自然的中文回答：{question}"),
            question_text=self.config.get("question_texts", {}).get(str(q_num), "")
        )

        self.random_delay(*self.config.get("per_question_delay", (1.0, 3.0)))

    def fill_multiple(self, driver, question, q_num, path_config=None):
        """
        多选题填写 - 稳健版：防止循环点击时元素失效
        """
        import random
        import time
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException

        try:
            # 1. 初次查找所有checkbox
            checkboxes = question.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            if not checkboxes:
                return

            # 2. 决定选几个，选哪些（支持权重/逻辑/约束）
            count = len(checkboxes)
            q_key = str(q_num)
            conf = self.config.get("multiple_prob", {}).get(q_key, {})
            min_sel = conf.get("min_selection", 1)
            max_sel = conf.get("max_selection", min(3, count))

            # 逻辑规则
            option_texts = self._extract_option_texts(question, checkboxes)
            must_idx, avoid_idx, prefer_idx, min_override, max_override = self._apply_logic_rules(q_key, option_texts)
            if isinstance(min_override, int):
                min_sel = max(min_sel, min_override)
            if isinstance(max_override, int):
                max_sel = min(max_sel, max_override)

            # 确保范围有效
            if max_sel > count:
                max_sel = count
            if min_sel > max_sel:
                min_sel = max_sel

            must_count = len(must_idx)
            if min_sel < must_count:
                min_sel = must_count
            if max_sel < must_count:
                max_sel = must_count

            # 计算权重
            prob_list = conf.get("prob", [])
            if isinstance(prob_list, list) and prob_list:
                weights = prob_list[:count] if len(prob_list) > count else prob_list + [1.0] * (count - len(prob_list))
                try:
                    weights = [float(w) for w in weights]
                except Exception:
                    weights = [1.0] * count
            else:
                weights = [1.0] * count

            for i in range(count):
                if i in avoid_idx and i not in must_idx:
                    weights[i] = 0.0
                if i in prefer_idx:
                    weights[i] = weights[i] * 1.5

            # 随机决定本次选几个
            to_select_count = random.randint(min_sel, max_sel) if max_sel >= min_sel else min_sel
            to_select_count = max(to_select_count, must_count)

            # 选择索引（先必选，再按权重抽样）
            candidates = [i for i in range(count) if i not in must_idx and i not in avoid_idx]
            extra_needed = max(0, to_select_count - must_count)
            extra_selected = self._weighted_sample_indices(weights, candidates, extra_needed)
            indices = list(must_idx) + extra_selected
            # 去重并补足
            indices = list(dict.fromkeys(indices))
            if len(indices) < to_select_count:
                remaining = [i for i in range(count) if i not in indices and i not in avoid_idx]
                extra = self._weighted_sample_indices(weights, remaining, to_select_count - len(indices))
                indices.extend(extra)

            # 3. 稳健的循环点击逻辑
            for idx in indices:
                retry_count = 0
                while retry_count < 3:
                    try:
                        # [关键] 重新在 question 容器中查找 checkbox 列表
                        # 确保即使上一次点击导致DOM微变，这里也能拿到最新的元素
                        current_boxes = question.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                        if idx >= len(current_boxes): break  # 索引越界保护

                        target = current_boxes[idx]

                        # 如果还没被选中，则点击
                        if not target.is_selected():
                            # 优先尝试点击 label（通常 label 比 input 更容易接受点击）
                            clicked = False
                            try:
                                label_id = target.get_attribute('id')
                                if label_id:
                                    label = question.find_element(By.CSS_SELECTOR, f"label[for='{label_id}']")
                                    driver.execute_script(
                                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", label)
                                    label.click()
                                    clicked = True
                            except:
                                pass

                            # 如果 label 点击失败，尝试直接点击 input
                            if not clicked:
                                driver.execute_script(
                                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target)
                                try:
                                    target.click()
                                except (ElementClickInterceptedException, StaleElementReferenceException):
                                    # 最后的手段：JS点击
                                    driver.execute_script("arguments[0].click();", target)

                            # 稍微等待，防止操作过快
                            time.sleep(0.2)

                        # 成功则跳出重试循环
                        break

                    except StaleElementReferenceException:
                        # 元素失效，重试
                        retry_count += 1
                        time.sleep(0.5)
                    except Exception as e:
                        # 其他错误，跳过该选项
                        break

            # 4. 自动处理关联填空 (如“其他”后面的输入框)
            # 这里调用你原有的关联填空逻辑
            self.fill_associated_textbox(
                driver, question, None,  # 这里的None是因为多选通常不需要指定特定radio
                ai_enabled=self.config.get("ai_fill_enabled", False),
                ai_api_key=self.config.get("openai_api_key", ""),
                ai_prompt_template=self.config.get("ai_prompt_template", ""),
                question_text=self.config.get("question_texts", {}).get(str(q_num), "")
            )

        except Exception as e:
            import logging
            logging.error(f"多选题 {q_num} 填写失败: {e}")

    def fill_matrix(self, driver, question, q_num, path_config=None):
        """填写矩阵题 - WJX2风格处理，支持普通矩阵(6)与矩阵量表(8)"""
        import random
        import time
        import numpy as np
        from selenium.webdriver.common.by import By

        try:
            q_key = str(q_num)
            # 识别是否矩阵量表题（8）
            qt = self.config.get("question_types", {}).get(q_key)
            is_scale_matrix = (qt == '8')
            probs = self.config.get("matrix_prob", {}).get(q_key, -1)
            matrix_data = self.config.get("matrix_data", {}).get(q_key, {})
            
            # 扩展矩阵选择器
            matrix_selectors = [
                f"#divRefTab{q_num} tbody tr",
                ".matrix tr", ".matrix-row", ".wjx-matrix", ".table-question", 
                ".matrix-table", ".grid-question", ".matrix-item", ".table-row",
                ".matrix .matrix-row", ".grid .grid-row", ".table-question tr",
                ".matrix-table tr", ".grid-table tr", ".question-table tr"
            ]
            
            rows = []
            for selector in matrix_selectors:
                rows = question.find_elements(By.CSS_SELECTOR, selector)
                if rows:
                    break
            
            if not rows:
                import logging
                logging.warning(f"矩阵题 {q_num} 未找到矩阵行")
                return

            # 矩阵量表：整张表共享一套量表选项；按列概率选择
            if is_scale_matrix:
                # 列概率来自 matrix_prob[q_num]（列表）或 -1 随机
                header_cells = rows[0].find_elements(By.CSS_SELECTOR, "th, td") if rows else []
                scale_len = len(header_cells) - 1 if len(header_cells) > 1 else 5
                if probs == -1 or not isinstance(probs, list):
                    col_probs = [1.0/scale_len] * scale_len
                else:
                    col_probs = probs[:scale_len] if len(probs) > scale_len else probs + [0.2] * (scale_len - len(probs))
                    s = sum(col_probs)
                    col_probs = [p/s for p in col_probs] if s > 0 else [1.0/scale_len] * scale_len

                for i, row in enumerate(rows[1:], 1):  # 跳过表头
                    # 取本行可点击的列（从第2列起）
                    col_selectors = ["td", ".matrix-cell", ".table-cell", ".grid-cell"]
                    cols = []
                    for sel in col_selectors:
                        cols = row.find_elements(By.CSS_SELECTOR, sel)
                        if cols:
                            break
                    if not cols or len(cols) <= 1:
                        continue
                    # 根据概率选择列
                    selected_col = int(np.random.choice(range(1, len(cols)), p=col_probs[:len(cols)-1]))
                    self._click_matrix_cell(driver, cols[selected_col], q_num, i)
                    self.random_delay(0.1, 0.3)
                self.random_delay(*self.config.get("per_question_delay", (1.0, 3.0)))
                import logging
                logging.info(f"已填写矩阵量表题 {q_num}")
                return

            # 普通矩阵处理
            if isinstance(probs, dict) and probs.get("row_probs"):
                # 复杂矩阵：每行有不同的概率配置
                row_probs = probs["row_probs"]
                for i, row in enumerate(rows[1:], 1):  # 跳过表头行
                    if i-1 < len(row_probs):
                        current_row_probs = row_probs[i-1]
                    else:
                        current_row_probs = [1.0] * 5  # 默认概率
                    
                    # 扩展列选择器
                    col_selectors = ["td", ".matrix-cell", ".table-cell", ".grid-cell"]
                    cols = []
                    for selector in col_selectors:
                        cols = row.find_elements(By.CSS_SELECTOR, selector)
                        if cols:
                            break
                    
                    if not cols or len(cols) <= 1:
                        continue

                    # 根据行概率选择列
                    if len(current_row_probs) >= len(cols) - 1:
                        col_probs = current_row_probs[:len(cols) - 1]
                    else:
                        col_probs = current_row_probs + [0.2] * (len(cols) - 1 - len(current_row_probs))
                    
                    # 归一化概率
                    total = sum(col_probs)
                    if total > 0:
                        col_probs = [p / total for p in col_probs]
                        selected_col = np.random.choice(range(1, len(cols)), p=col_probs)
                    else:
                        selected_col = random.randint(1, len(cols) - 1)
                    
                    self._click_matrix_cell(driver, cols[selected_col], q_num, i)
                    self.random_delay(0.1, 0.3)
                    
            else:
                # WJX2风格矩阵处理：每个小题独立处理
                # 参考wjx2.py的matrix函数逻辑
                valid_rows = [row for row in rows if row.get_attribute("rowindex") is not None]
                if not valid_rows:
                    valid_rows = rows[1:]  # 跳过表头
                
                for matrix_sub_idx, row in enumerate(valid_rows):
                    # 扩展列选择器
                    col_selectors = ["td", ".matrix-cell", ".table-cell", ".grid-cell"]
                    cols = []
                    for selector in col_selectors:
                        cols = row.find_elements(By.CSS_SELECTOR, selector)
                        if cols:
                            break
                    
                    if not cols or len(cols) <= 1:
                        continue

                    # WJX2风格：支持每个小题的独立概率配置
                    if isinstance(probs, dict) and "sub_questions" in probs:
                        # 多小题独立配置
                        sub_probs = probs["sub_questions"].get(matrix_sub_idx, -1)
                    elif isinstance(probs, list) and len(probs) > matrix_sub_idx:
                        # 列表形式：每个元素对应一个小题
                        sub_probs = probs[matrix_sub_idx]
                    else:
                        # 统一配置：所有小题使用相同概率
                        sub_probs = probs

                    # 选择列（wjx2.py风格：从第2列开始，因为第1列是题目文本）
                    selectable_cols = cols[1:] if len(cols) > 1 else cols
                    
                    if sub_probs == -1:  # 随机选择（wjx2.py标准）
                        selected_col_idx = random.randint(0, len(selectable_cols) - 1)
                    elif isinstance(sub_probs, list):  # 按概率选择
                        # WJX2风格归一化处理
                        if len(sub_probs) != len(selectable_cols):
                            # 调整概率数组长度以匹配选项数量
                            if len(sub_probs) > len(selectable_cols):
                                sub_probs = sub_probs[:len(selectable_cols)]
                            else:
                                sub_probs = sub_probs + [1.0] * (len(selectable_cols) - len(sub_probs))
                        
                        # 归一化（wjx2.py风格）
                        total = sum(sub_probs)
                        if total > 0:
                            normalized_probs = [p / total for p in sub_probs]
                            selected_col_idx = np.random.choice(range(len(selectable_cols)), p=normalized_probs)
                        else:
                            selected_col_idx = random.randint(0, len(selectable_cols) - 1)
                    else:  # 默认随机
                        selected_col_idx = random.randint(0, len(selectable_cols) - 1)

                    # 点击选中的列（使用1-based索引，因为第0列是题目文本）
                    actual_col_idx = selected_col_idx + 1
                    self._click_matrix_cell(driver, cols[actual_col_idx], q_num, matrix_sub_idx + 1)
                    self.random_delay(0.1, 0.3)

            self.random_delay(*self.config.get("per_question_delay", (1.0, 3.0)))
            import logging
            logging.info(f"已填写矩阵题 {q_num}")
            
        except Exception as e:
            import logging
            logging.error(f"填写矩阵题 {q_num} 时出错: {str(e)}")
            
    def _click_matrix_cell(self, driver, cell, q_num, row_idx):
        """点击矩阵单元格的辅助函数"""
        import time
        try:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", cell)
            time.sleep(0.2)
            
            # 尝试多种点击方式
            try:
                cell.click()
            except:
                try:
                    driver.execute_script("arguments[0].click();", cell)
                except:
                    # 查找内部的单选按钮
                    radio_btns = cell.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    if radio_btns:
                        radio_btns[0].click()
                    else:
                        # 查找其他可点击元素
                        clickable = cell.find_elements(By.CSS_SELECTOR, "button, .clickable, [onclick]")
                        if clickable:
                            clickable[0].click()
                        else:
                            # 最后尝试点击父元素
                            try:
                                parent = cell.find_element(By.XPATH, "..")
                                parent.click()
                            except:
                                pass
                                
        except Exception as e:
            import logging
            logging.debug(f"矩阵题 {q_num} 第{row_idx}行点击失败: {str(e)}")

    def fill_scale(self, driver, question, q_num, path_config=None):
        """填写量表题 - 增强版，支持多种量表类型"""
        import random
        import numpy as np
        import time
        from selenium.webdriver.common.by import By

        try:
            # 扩展量表选择器
            scale_selectors = [
                f"#div{q_num} .scale-ul li",
                ".scale-ul li", ".scale-item", ".wjx-scale", ".rating-scale", 
                ".star-rating", ".likert-scale", ".scale-option", ".rating-item",
                ".scale-ul .scale-item", ".rating-ul li", ".star-item",
                ".rating li", ".scale li", ".likert li", ".star li"
            ]
            
            options = []
            for selector in scale_selectors:
                options = question.find_elements(By.CSS_SELECTOR, selector)
                if options:
                    break
            
            # 兜底：查找所有可能的量表元素
            if not options:
                options = question.find_elements(By.CSS_SELECTOR, "li, .option, .choice")
            
            if not options:
                import logging
                logging.warning(f"量表题 {q_num} 未找到选项")
                return

            q_key = str(q_num)
            probs = self.config["scale_prob"].get(q_key, [1] * len(options))

            # 确保概率列表长度匹配
            probs = probs[:len(options)] if len(probs) > len(options) else probs + [1] * (len(options) - len(probs))

            # 归一化概率
            total = sum(probs)
            if total > 0:
                probs = [p / total for p in probs]
                selected = np.random.choice(options, p=probs)
            else:
                selected = random.choice(options)

            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", selected)
                time.sleep(0.2)
                
                # 尝试多种点击方式
                try:
                    selected.click()
                except:
                    try:
                        driver.execute_script("arguments[0].click();", selected)
                    except:
                        # 查找内部的点击元素
                        clickable = selected.find_elements(By.CSS_SELECTOR, "input, button, .clickable, [onclick]")
                        if clickable:
                            clickable[0].click()
                        else:
                            # 最后尝试点击父元素
                            parent = selected.find_element(By.XPATH, "..")
                            parent.click()

            except Exception as e:
                import logging
                logging.error(f"量表题 {q_num} 点击失败: {str(e)}")

            self.random_delay(*self.config.get("per_question_delay", (1.0, 3.0)))
            import logging
            logging.info(f"已填写量表题 {q_num}")
            
        except Exception as e:
            import logging
            logging.error(f"填写量表题 {q_num} 时出错: {str(e)}")

    def fill_reorder(self, driver, question, q_num, path_config=None):
        """
        问卷星排序题专用：只点击一轮，每个li只点一次，顺序随机，绝不补点。
        选项查找范围更广，未找到时输出结构，提升成功率。
        """
        from selenium.webdriver.common.by import By
        import random
        import time
        try:
            lis = question.find_elements(
                By.CSS_SELECTOR,
                '.sort-ul li, .sortable li, .wjx-sortable li, .ui-sortable li, .sort-container li, ul li'
            )
            lis = [li for li in lis if li.is_displayed() and li.is_enabled()]
            if not lis:
                import logging
                logging.warning(f"排序题 {q_num} 未找到选项，结构为: {question.get_attribute('outerHTML')}")
                return
            idxs = list(range(len(lis)))
            random.shuffle(idxs)
            for idx in idxs:
                try:
                    lis[idx].click()
                    time.sleep(0.3)
                except Exception as e:
                    try:
                        driver.execute_script("arguments[0].click();", lis[idx])
                    except Exception:
                        import logging
                        logging.warning(f"排序题 {q_num} 第{idx + 1}项点击失败: {e}")
            # 只做一轮，绝不补点
            self.random_delay(*self.config.get("per_question_delay", (1.0, 3.0)))
        except Exception as e:
            import logging
            logging.error(f"填写排序题 {q_num} 时出错: {str(e)}")



    # 调用方法示例（比如在auto_detect_question_type或fill_text内）：
    # 假设你判断到是多项填空题型(q_type == "2")，这样调用：
    # self.fill_multiple_text(driver, question, q_num)
    
    def fill_multiple_text(self, driver, question, q_num, path_config=None):
        """填写多项填空题"""
        from selenium.webdriver.common.by import By
        try:
            # 查找所有文本输入框
            text_inputs = question.find_elements(By.CSS_SELECTOR, 
                "input[type='text'], textarea, span[contenteditable='true']")
            
            if not text_inputs:
                logging.warning(f"第{q_num}题：未找到文本输入框")
                return
                
            # 为每个输入框填写内容
            for i, text_input in enumerate(text_inputs):
                try:
                    # 获取配置的答案
                    qid = str(q_num)
                    if qid in self.config.get("other_texts", {}):
                        answers = self.config["other_texts"][qid]
                        if i < len(answers):
                            answer = answers[i]
                        else:
                            answer = "自动填写内容"
                    else:
                        answer = "自动填写内容"
                    
                    # 填写内容
                    if text_input.tag_name == "span":
                        driver.execute_script("arguments[0].innerText = arguments[1];", text_input, answer)
                    else:
                        text_input.clear()
                        text_input.send_keys(answer)
                        
                    logging.info(f"第{q_num}题第{i+1}个输入框：{answer}")
                    
                except Exception as e:
                    logging.error(f"第{q_num}题第{i+1}个输入框填写失败：{str(e)}")
                    
        except Exception as e:
            logging.error(f"第{q_num}题多项填空填写失败：{str(e)}")

    def bind_mousewheel_to_scrollbar(self, canvas):
        """将鼠标滚轮事件绑定到指定的画布上"""

        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

    def update_progress(self):
        """持续刷新整体进度条和状态栏 - 适配新版仪表盘（线程安全版）"""
        import time
        while self.running:
            try:
                # 1. 计算总体进度
                target = self.config.get("target_num", 100)
                cur_num = self.cur_num
                cur_fail = self.cur_fail
                paused = self.paused

                if target > 0:
                    progress = (cur_num / target) * 100
                else:
                    progress = 0

                # 2. 使用 root.after 将所有 UI 操作调度到主线程
                def _update_ui(progress=progress, cur_num=cur_num, cur_fail=cur_fail, paused=paused, target=target):
                    try:
                        if not self.root.winfo_exists():
                            return
                        self.progress_var.set(progress)
                        self.percent_var.set(f"{progress:.1f}%")

                        if paused:
                            self.main_status_var.set("⏸ 已暂停")
                            self.main_status_label.configure(style='StatusStopped.TLabel')
                            self.action_status_var.set("等待用户继续...")
                        else:
                            self.main_status_var.set("▶ 运行中")
                            self.main_status_label.configure(style='StatusRunning.TLabel')
                            self.action_status_var.set(f"正在处理第 {cur_num + 1} 份问卷...")

                        self.success_count_var.set(str(cur_num))
                        self.fail_count_var.set(str(cur_fail))
                        self.target_display_var.set(f"目标份数: {target}")
                    except Exception:
                        pass

                self.root.after(0, _update_ui)

                # 3. 自动停止判断
                if cur_num >= target:
                    def _finish_ui():
                        try:
                            if not self.root.winfo_exists():
                                return
                            self.progress_var.set(100)
                            self.percent_var.set("100%")
                            self.success_count_var.set(str(self.cur_num))
                            self.main_status_var.set("✅ 已完成")
                            self.action_status_var.set("所有任务已完成")
                            self.stop_filling()
                            messagebox.showinfo("完成", "恭喜！所有问卷填写任务已完成！")
                        except Exception:
                            pass
                    self.root.after(0, _finish_ui)
                    break

            except Exception as e:
                import logging
                logging.error(f"更新进度时出错: {str(e)}")
            time.sleep(0.5)

    def is_filled(self, question):
        """检查问题是否已填写"""
        try:
            # 检查排序题
            if question.find_elements(By.CSS_SELECTOR,
                                      ".sort-ul, .sortable, .wjx-sortable, .ui-sortable, .sort-container"):
                return True
            # 检查 input/textarea/select
            inputs = question.find_elements(By.CSS_SELECTOR, "input, textarea, select")
            for inp in inputs:
                typ = inp.get_attribute("type")
                if typ in ("checkbox", "radio"):
                    if inp.is_selected():
                        return True
                elif typ in ("text", None):
                    if inp.get_attribute("value"):
                        return True
                elif typ == "select-one":
                    v = inp.get_attribute("value")
                    if v and v != "" and v != "请选择":
                        return True
            # 检查 contenteditable span
            spans = question.find_elements(By.CSS_SELECTOR, "span[contenteditable='true']")
            for span in spans:
                if span.text.strip():
                    return True
                try:
                    # 确保driver已定义
                    if hasattr(self, 'driver') and self.driver:
                        inner = self.driver.execute_script("return arguments[0].innerText;", span)
                    else:
                        inner = span.get_attribute('innerText')
                    if inner and inner.strip():
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def toggle_pause(self):
        """切换暂停/继续状态"""
        self.paused = not self.paused
        if self.paused:
            self.pause_event.clear()
            self.pause_btn.config(text="继续")
            logging.info("已暂停")
            self.main_status_label.config(foreground="orange")
        else:
            self.pause_event.set()
            self.pause_btn.config(text="暂停")
            logging.info("已继续")
            self.main_status_label.config(foreground="green")

    def stop_filling(self):
        """停止填写"""
        self.running = False
        self.pause_event.set()  # 确保所有线程都能退出
        self.start_btn.config(state=tk.NORMAL, text="▶ 开始填写")
        self.pause_btn.config(state=tk.DISABLED, text="⏸ 暂停")
        self.stop_btn.config(state=tk.DISABLED)

        self.main_status_var.set("⏹ 已停止")
        self.main_status_label.configure(style='StatusStopped.TLabel')
        self.action_status_var.set("任务已手动终止")
        logging.info("已停止")
    def reset_defaults(self):
        """重置为默认配置"""
        result = messagebox.askyesno("确认", "确定要重置所有设置为默认值吗？")
        if result:
            self.config = DEFAULT_CONFIG.copy()
            # 全局设置
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, self.config["url"])
            self.target_entry.set(self.config["target_num"])
            self.ratio_scale.set(self.config["weixin_ratio"])
            self.ratio_var.set(f"{self.config['weixin_ratio'] * 100:.0f}%")
            self.min_duration.set(self.config["min_duration"])
            self.max_duration.set(self.config["max_duration"])
            self.min_delay.set(self.config["min_delay"])
            self.max_delay.set(self.config["max_delay"])
            self.min_q_delay.set(self.config["per_question_delay"][0])
            self.max_q_delay.set(self.config["per_question_delay"][1])
            self.min_p_delay.set(self.config["per_page_delay"][0])
            self.max_p_delay.set(self.config["per_page_delay"][1])
            self.submit_delay.set(self.config["submit_delay"])
            self.num_threads.set(self.config["num_threads"])
            self.use_ip_var.set(self.config["use_ip"])
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, self.config["ip_api"])
            self.ip_change_mode.set(self.config.get("ip_change_mode", "per_submit"))
            self.ip_change_batch.set(self.config.get("ip_change_batch", 5))
            self.headless_var.set(self.config["headless"])
            # 智能提交间隔/批量休息
            self.enable_smart_gap_var.set(self.config.get("enable_smart_gap", True))
            self.min_submit_gap.set(self.config.get("min_submit_gap", 10))
            self.max_submit_gap.set(self.config.get("max_submit_gap", 20))
            self.batch_size.set(self.config.get("batch_size", 5))
            self.batch_pause.set(self.config.get("batch_pause", 15))
            # 重新加载题型设置
            self.ai_service.set(DEFAULT_CONFIG["ai_service"])
            self.ai_fill_var.set(DEFAULT_CONFIG["ai_fill_enabled"])
            self.openai_api_key_entry.delete(0, tk.END)
            self.openai_api_key_entry.insert(0, DEFAULT_CONFIG.get("openai_api_key", ""))
            self.qingyan_api_key_entry.delete(0, tk.END)
            self.qingyan_api_key_entry.insert(0, DEFAULT_CONFIG.get("qingyan_api_key", ""))
            self.ai_prompt_combobox.set(DEFAULT_CONFIG["ai_prompt_template"])
            self.reload_question_settings()
            logging.info("已重置为默认配置")

    @staticmethod
    def safe_get(widget, cast_type=int, default=None):
        """
        通用安全型取值，适用于Spinbox、Entry、Scale等，统一异常处理。
        支持直接数值和get方法。
        """
        try:
            val = widget.get() if hasattr(widget, "get") else widget
            return cast_type(val)
        except Exception:
            return default

    def save_config(self):
        import logging
        from tkinter import messagebox

        # === 全局保险：所有题型相关配置的key统一转为字符串，包括question_texts/option_texts ===
        for key in [
            "single_prob", "multiple_prob", "matrix_prob", "texts", "multiple_texts",
            "reorder_prob", "droplist_prob", "scale_prob", "other_texts",
            "question_texts", "option_texts"
        ]:
            if key in self.config:
                self.config[key] = {str(k): v for k, v in self.config[key].items()}

        try:
            # 优先让新题型设置界面将其内部改动同步到 self.config，避免读取已销毁的控件
            if hasattr(self, "wjx_question_ui") and self.wjx_question_ui:
                try:
                    self.wjx_question_ui.save_settings()
                except Exception as ui_e:
                    logging.warning(f"题型设置保存同步失败（已忽略）：{ui_e}")

            # ====== 1. 全局基础配置 ======
            self.config["url"] = self.url_entry.get().strip()

            # 安全的整数转换函数
            def safe_int_convert(value_str, default=1, min_val=1):
                try:
                    # 先转换为float，再转换为int，确保处理'0.8'这样的输入
                    val = float(str(value_str).strip())
                    return max(min_val, int(val))
                except (ValueError, TypeError):
                    return default

            # 安全的浮点数转换函数
            def safe_float_convert(value_str, default=1.0, min_val=0.0):
                try:
                    val = float(str(value_str).strip())
                    return max(min_val, val)
                except (ValueError, TypeError):
                    return default

            self.config["target_num"] = safe_int_convert(self.target_entry.get(), 100, 1)
            self.config["weixin_ratio"] = self.ratio_scale.get()
            self.config["min_duration"] = safe_int_convert(self.min_duration.get(), 1, 1)
            self.config["max_duration"] = safe_int_convert(self.max_duration.get(), 20, 1)
            self.config["min_delay"] = safe_float_convert(self.min_delay.get(), 1.0, 0.1)
            self.config["max_delay"] = safe_float_convert(self.max_delay.get(), 2.0, 0.1)
            self.config["per_question_delay"] = [safe_float_convert(self.min_q_delay.get(), 0.5, 0.1), safe_float_convert(self.max_q_delay.get(), 1.0, 0.1)]
            self.config["per_page_delay"] = [safe_float_convert(self.min_p_delay.get(), 2.0, 0.5), safe_float_convert(self.max_p_delay.get(), 6.0, 0.5)]
            self.config["submit_delay"] = safe_int_convert(self.submit_delay.get(), 1, 1)
            self.config["num_threads"] = safe_int_convert(self.num_threads.get(), 4, 1)
            self.config["use_ip"] = self.use_ip_var.get()
            self.config["ip_api"] = self.ip_entry.get().strip()
            self.config["ip_change_mode"] = self.ip_change_mode.get()
            self.config["ip_change_batch"] = safe_int_convert(self.ip_change_batch.get(), 5, 1)
            self.config["headless"] = self.headless_var.get()
            self.config["enable_smart_gap"] = self.enable_smart_gap_var.get()
            self.config["min_submit_gap"] = safe_int_convert(self.min_submit_gap.get(), 5, 1)
            self.config["max_submit_gap"] = safe_int_convert(self.max_submit_gap.get(), 15, 1)
            self.config["batch_size"] = safe_int_convert(self.batch_size.get(), 5, 1)
            self.config["batch_pause"] = safe_int_convert(self.batch_pause.get(), 15, 1)
            self.config["ai_service"] = self.ai_service.get()
            self.config["ai_fill_enabled"] = self.ai_fill_var.get()
            self.config["openai_api_key"] = self.openai_api_key_entry.get().strip()
            self.config["qingyan_api_key"] = self.qingyan_api_key_entry.get().strip()
            self.config["ai_prompt_template"] = self.ai_prompt_combobox.get()
            # ====== 2. 题型配置 ======
            # 单选题配置（容错：控件不存在或已销毁时跳过，不覆盖既有配置）
            if hasattr(self, "single_entries") and isinstance(self.single_entries, list):
                for i, entry_row in enumerate(self.single_entries):
                    try:
                        q_num = list(self.config.get("single_prob", {}).keys())[i]
                    except Exception:
                        continue
                    probs = []
                    all_random = False
                    got_any = False
                    for entry in entry_row:
                        try:
                            val = entry.get().strip()
                        except Exception:
                            continue
                        got_any = True
                        if val == "-1":
                            all_random = True
                        else:
                            try:
                                probs.append(float(val))
                            except Exception:
                                probs.append(1.0)
                    if not got_any:
                        continue
                    if all_random:
                        self.config.setdefault("single_prob", {})[q_num] = -1
                    else:
                        self.config.setdefault("single_prob", {})[q_num] = probs

            # 多选题配置（同样容错处理）
            if hasattr(self, "multi_entries") and isinstance(self.multi_entries, list):
                for i, entry_row in enumerate(self.multi_entries):
                    try:
                        q_num = list(self.config.get("multiple_prob", {}).keys())[i]
                    except Exception:
                        continue
                    # 默认从既有配置读取上下限，若控件可用则覆盖
                    existing_conf = self.config.get("multiple_prob", {}).get(q_num, {})
                    min_selection = existing_conf.get("min_selection", 1)
                    max_selection = existing_conf.get("max_selection", max(1, len(self.config.get("option_texts", {}).get(q_num, []))))
                    try:
                        min_selection = safe_int_convert(self.min_selection_entries[i].get(), 1, 1)
                        max_selection = safe_int_convert(self.max_selection_entries[i].get(), max(1, len(self.config.get("option_texts", {}).get(q_num, []))), 1)
                    except Exception:
                        pass
                    option_count = len(self.config.get("option_texts", {}).get(q_num, []))
                    min_selection = max(1, min(min_selection, option_count))
                    max_selection = max(min_selection, min(max_selection, option_count))

                    probs = []
                    got_any = False
                    for entry in entry_row:
                        try:
                            raw = entry.get().strip()
                        except Exception:
                            continue
                        got_any = True
                        raw = raw.replace('%', '')
                        try:
                            fval = float(raw)
                            perc = int(round(fval * 100)) if fval <= 1.0 else int(round(fval))
                            perc = max(0, min(100, perc))
                        except Exception:
                            perc = 50
                        probs.append(perc)

                    # 其他选项文本
                    if q_num in getattr(self, "other_entries", {}):
                        try:
                            other_entry = self.other_entries[q_num]
                            other_val = other_entry.get().strip()
                            if other_val:
                                self.config.setdefault("other_texts", {})[q_num] = [x.strip() for x in other_val.split(",")]
                        except Exception:
                            pass

                    if got_any:
                        self.config.setdefault("multiple_prob", {})[q_num] = {
                            "prob": probs,
                            "min_selection": min_selection,
                            "max_selection": max_selection
                        }

            # 矩阵题配置
            if hasattr(self, "matrix_entries") and isinstance(self.matrix_entries, list):
                for i, entry_row in enumerate(self.matrix_entries):
                    try:
                        q_num = list(self.config.get("matrix_prob", {}).keys())[i]
                    except Exception:
                        continue
                    probs = []
                    all_random = False
                    got_any = False
                    for entry in entry_row:
                        try:
                            val = entry.get().strip()
                        except Exception:
                            continue
                        got_any = True
                        if val == "-1":
                            all_random = True
                        else:
                            try:
                                probs.append(float(val))
                            except Exception:
                                probs.append(1.0)
                    if not got_any:
                        continue
                    if all_random:
                        self.config.setdefault("matrix_prob", {})[q_num] = -1
                    else:
                        self.config.setdefault("matrix_prob", {})[q_num] = probs

            # 排序题配置
            if hasattr(self, "reorder_entries") and isinstance(self.reorder_entries, list):
                for i, entry_row in enumerate(self.reorder_entries):
                    try:
                        q_num = list(self.config.get("reorder_prob", {}).keys())[i]
                    except Exception:
                        continue
                    probs = []
                    got_any = False
                    for entry in entry_row:
                        try:
                            probs.append(float(entry.get().strip()))
                            got_any = True
                        except Exception:
                            probs.append(0.25)
                    if got_any:
                        self.config.setdefault("reorder_prob", {})[q_num] = probs

            # 下拉框题配置
            if hasattr(self, "droplist_entries") and isinstance(self.droplist_entries, list):
                for i, entry in enumerate(self.droplist_entries):
                    try:
                        q_num = list(self.config.get("droplist_prob", {}).keys())[i]
                    except Exception:
                        continue
                    try:
                        val = entry.get().strip()
                    except Exception:
                        # 无法读取控件，跳过
                        continue
                    if val:
                        try:
                            prob_list = [float(x.strip()) for x in val.split(",")]
                        except Exception:
                            option_count = len(self.config.get("option_texts", {}).get(q_num, []))
                            prob_list = [0.3] * option_count
                    else:
                        option_count = len(self.config.get("option_texts", {}).get(q_num, []))
                        prob_list = [0.3] * option_count

                    option_texts = self.config.get("option_texts", {}).get(q_num, [])
                    if len(prob_list) > len(option_texts):
                        prob_list = prob_list[:len(option_texts)]
                    elif len(prob_list) < len(option_texts):
                        prob_list += [0.3] * (len(option_texts) - len(prob_list))

                    self.config.setdefault("droplist_prob", {})[q_num] = prob_list

            # 量表题配置
            if hasattr(self, "scale_entries") and isinstance(self.scale_entries, list):
                for i, entry_row in enumerate(self.scale_entries):
                    try:
                        q_num = list(self.config.get("scale_prob", {}).keys())[i]
                    except Exception:
                        continue
                    probs = []
                    got_any = False
                    for entry in entry_row:
                        try:
                            probs.append(float(entry.get().strip()))
                            got_any = True
                        except Exception:
                            probs.append(0.2)
                    if got_any:
                        self.config.setdefault("scale_prob", {})[q_num] = probs

            # 填空题配置
            if hasattr(self, "text_entries") and isinstance(self.text_entries, list):
                for i, entry_row in enumerate(self.text_entries):
                    try:
                        q_num = list(self.config.get("texts", {}).keys())[i]
                    except Exception:
                        continue
                    answers = []
                    for entry in entry_row:
                        try:
                            val = entry.get().strip()
                        except Exception:
                            continue
                        if val:
                            answers = [x.strip() for x in val.split(",")]
                            break
                    if answers:
                        self.config.setdefault("texts", {})[q_num] = answers

            # 多项填空配置
            if hasattr(self, "multiple_text_entries") and isinstance(self.multiple_text_entries, list):
                for i, entry_row in enumerate(self.multiple_text_entries):
                    try:
                        q_num = list(self.config.get("multiple_texts", {}).keys())[i]
                    except Exception:
                        continue
                    answers_list = []
                    got_any = False
                    for j, entry in enumerate(entry_row):
                        try:
                            val = entry.get().strip()
                        except Exception:
                            val = ""
                        if val:
                            got_any = True
                            answers_list.append([x.strip() for x in val.split(",")])
                        else:
                            answers_list.append(["示例答案"])
                    if got_any:
                        self.config.setdefault("multiple_texts", {})[q_num] = answers_list

            # 保存成功
            logging.info("配置保存成功")
            return True
        except Exception as e:
            logging.error(f"保存配置时出错: {str(e)}")
            messagebox.showerror("错误", f"保存配置时出错: {str(e)}")
            return False


    def get_new_proxy(self):
        """拉取代理IP"""
        # Security: User requested to stop proxy usage.
        logging.warning("Proxy usage is disabled by security policy.")
        return None


    def random_delay(self, min_time=None, max_time=None):
        """生成随机延迟时间"""
        if min_time is None:
            min_time = self.config["min_delay"]
        if max_time is None:
            max_time = self.config["max_delay"]
        delay = random.uniform(min_time, max_time)
        time.sleep(delay)

    def set_blank_texts(self, qid, answers):
        """
        设置指定填空题的答案池，并同步更新对应UI控件（如存在）。
        :param qid: 题目编号（int或str）
        :param answers: 答案列表（list of str）
        """
        qid_str = str(qid)
        # 更新数据
        if "texts" not in self.config:
            self.config["texts"] = {}
        self.config["texts"][qid_str] = answers

        # 如果有UI控件，自动同步显示
        if hasattr(self, 'blank_text_widget') and qid_str in self.blank_text_widget:
            widget = self.blank_text_widget[qid_str]
            widget.delete("1.0", "end")
            for ans in answers:
                widget.insert("end", ans + "\n")
        # 可选：通知其它模块或刷新
        self.refresh_some_ui_if_needed()
        
    def refresh_some_ui_if_needed(self):
        """刷新相关UI组件"""
        try:
            # 只有在有解析数据时才刷新题型设置界面
            if hasattr(self, 'question_frame') and self.config.get('question_texts'):
                self.reload_question_settings()
            # 更新状态
            self.root.after(0, lambda: self.main_status_var.set("配置已更新"))
        except Exception as e:
            logging.debug(f"UI刷新失败: {str(e)}")
            
    def generate_sample_answers(self, num):
        """
        批量生成num份问卷模拟答案，返回文本或保存到文件。
        支持AI生成和本地随机生成，自动推断题型和配置。
        """
        import random
        import json

        answers_list = []
        for _ in range(num):
            answer = {}
            for qid, qtext in self.config.get("question_texts", {}).items():
                # 优先选题型
                qid_str = str(qid)
                # 单选题
                if qid_str in self.config.get("single_prob", {}):
                    options = self.config.get("option_texts", {}).get(qid_str, [])
                    probs = self.config["single_prob"][qid_str]
                    if probs == -1 or not isinstance(probs, list):
                        idx = random.randint(0, len(options) - 1)
                    else:
                        total = sum(probs)
                        weights = [p / total for p in probs] if total > 0 else [1 / len(options)] * len(options)
                        idx = random.choices(range(len(options)), weights=weights)[0]
                    answer[qtext] = options[idx] if idx < len(options) else ""
                # 多选题
                elif qid_str in self.config.get("multiple_prob", {}):
                    options = self.config.get("option_texts", {}).get(qid_str, [])
                    conf = self.config["multiple_prob"][qid_str]
                    probs = conf.get("prob", [50] * len(options))
                    min_sel = conf.get("min_selection", 1)
                    max_sel = conf.get("max_selection", max(1, len(options)))
                    sel = []
                    for i, p in enumerate(probs):
                        if random.random() < p / 100:
                            sel.append(options[i] if i < len(options) else "")
                    if len(sel) < min_sel:
                        left = [o for i, o in enumerate(options) if o not in sel]
                        sel += random.sample(left, min(min_sel - len(sel), len(left)))
                    if len(sel) > max_sel:
                        sel = random.sample(sel, max_sel)
                    answer[qtext] = ",".join(sel)
                # 下拉框
                elif qid_str in self.config.get("droplist_prob", {}):
                    options = self.config.get("option_texts", {}).get(qid_str, [])
                    probs = self.config["droplist_prob"][qid_str]
                    total = sum(probs)
                    weights = [p / total for p in probs] if total > 0 else [1 / len(options)] * len(options)
                    idx = random.choices(range(len(options)), weights=weights)[0]
                    answer[qtext] = options[idx] if idx < len(options) else ""
                # 填空题
                elif qid_str in self.config.get("texts", {}):
                    texts = self.config["texts"][qid_str]
                    answer[qtext] = random.choice(texts) if texts else ""
                # 多项填空
                elif qid_str in self.config.get("multiple_texts", {}):
                    ans_lists = self.config["multiple_texts"][qid_str]
                    ans = [random.choice(a) if a else "" for a in ans_lists]
                    answer[qtext] = ";".join(ans)
                # 排序题
                elif qid_str in self.config.get("reorder_prob", {}):
                    options = self.config.get("option_texts", {}).get(qid_str, [])
                    order = options[:]
                    random.shuffle(order)
                    answer[qtext] = "->".join(order)
                # 量表题、矩阵题等
                elif qid_str in self.config.get("scale_prob", {}):
                    options = self.config.get("option_texts", {}).get(qid_str, [])
                    probs = self.config["scale_prob"][qid_str]
                    total = sum(probs)
                    weights = [p / total for p in probs] if total > 0 else [1 / len(options)] * len(options)
                    idx = random.choices(range(len(options)), weights=weights)[0]
                    answer[qtext] = options[idx] if idx < len(options) else ""
                elif qid_str in self.config.get("matrix_prob", {}):
                    options = self.config.get("option_texts", {}).get(qid_str, [])
                    answer[qtext] = random.choice(options) if options else ""
                else:
                    answer[qtext] = ""
            answers_list.append(answer)
        # 可选：保存到文件/返回
        try:
            with open("sample_answers.json", "w", encoding="utf-8") as f:
                json.dump(answers_list, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return answers_list

    def check_params(self):
        """
        检查当前参数设置的合理性，返回建议和自动修复提示。
        """
        tips = []
        # 目标份数
        try:
            target = int(self.config.get("target_num", 0))
            if target <= 0:
                tips.append("目标份数应大于0。")
        except Exception:
            tips.append("目标份数设置异常。")
        # 微信比例
        ratio = self.config.get("weixin_ratio", 0.5)
        if not (0 <= ratio <= 1):
            tips.append("微信比例应为0~1之间。")
        # 时间区间
        min_d, max_d = self.config.get("min_duration", 1), self.config.get("max_duration", 20)
        if min_d > max_d:
            tips.append("最短时长不能大于最长时长。")
        # 线程数
        threads = self.config.get("num_threads", 4)
        if threads < 1 or threads > 20:
            tips.append("线程数应在1~20之间，建议4~8。")
        # 延迟
        min_delay, max_delay = self.config.get("min_delay", 1), self.config.get("max_delay", 2)
        if min_delay > max_delay:
            tips.append("最小延迟应小于最大延迟。")
        # 批量/休息
        batch_size = self.config.get("batch_size", 5)
        batch_pause = self.config.get("batch_pause", 15)
        if batch_size < 1:
            tips.append("批量份数应≥1。")
        if batch_pause < 0:
            tips.append("批量休息时间应≥0分钟。")
        # 题型/概率检查
        for qid, qtext in self.config.get("question_texts", {}).items():
            qid_str = str(qid)
            if qid_str in self.config.get("single_prob", {}):
                probs = self.config["single_prob"][qid_str]
                if isinstance(probs, list) and abs(sum(probs) - 1) > 0.01 and all(p >= 0 for p in probs):
                    tips.append(f"第{qid}题单选概率和不为1，建议调整。")
            if qid_str in self.config.get("multiple_prob", {}):
                conf = self.config["multiple_prob"][qid_str]
                min_sel = conf.get("min_selection", 1)
                max_sel = conf.get("max_selection", 1)
                if min_sel > max_sel:
                    tips.append(f"第{qid}题多选最小选择数大于最大选择数，请检查。")
        if not tips:
            return "参数设置正常，无需优化。"
        return "\n".join(tips)
    def _safe_refresh_wjx_ui(self):
        """安全刷新WJX界面，使用after轮询避免阻塞主线程"""
        try:
            if not (hasattr(self, 'wjx_question_ui') and self.wjx_question_ui):
                logging.warning("WJX界面组件不存在")
                return
            if not (self.root and self.root.winfo_exists()):
                logging.warning("主窗口已销毁，跳过UI刷新")
                return

            refresh_state = {
                'start_ts': None,
                'timeout_ms': 5000,
                'error': None,
            }

            def start_refresh():
                try:
                    import time
                    refresh_state['start_ts'] = int(time.time() * 1000)
                    self._do_refresh_ui_nonblocking(check_completion)
                except Exception as e:
                    refresh_state['error'] = e
                    finish(False)

            def check_completion():
                # 当 _do_refresh_ui_nonblocking 调用完成后进入
                finish(True)

            def finish(success: bool):
                if success:
                    logging.info("WJX界面刷新完成")
                else:
                    logging.error("WJX界面刷新失败或超时，可能发生卡顿")
                    try:
                        if hasattr(self, 'wjx_question_ui') and hasattr(self.wjx_question_ui, '_refreshing'):
                            self.wjx_question_ui._refreshing = False
                    except Exception:
                        pass

            # 启动异步刷新
            self.root.after_idle(start_refresh)
        except Exception as e:
            logging.error(f"安全刷新WJX界面失败: {e}")
            try:
                if hasattr(self, 'wjx_question_ui') and hasattr(self.wjx_question_ui, '_refreshing'):
                    self.wjx_question_ui._refreshing = False
            except Exception:
                pass
            try:
                messagebox.showerror("界面错误", f"界面刷新失败，请重新解析问卷: {str(e)}")
            except Exception:
                pass

    def _do_refresh_ui_nonblocking(self, on_done):
        """在UI线程中执行刷新，并在完成时回调on_done，不阻塞主线程"""
        try:
            if hasattr(self, 'wjx_question_ui') and self.wjx_question_ui:
                # refresh_interface 内部已采用分阶段/after异步渲染
                self.wjx_question_ui.refresh_interface()
            # 计划稍后回调完成，确保有机会进入事件循环
            if self.root and self.root.winfo_exists():
                self.root.after(0, on_done)
            else:
                on_done()
        except Exception as e:
            logging.error(f"UI刷新执行失败: {e}")
            if self.root and self.root.winfo_exists():
                self.root.after(0, on_done)
            else:
                on_done()

    def cleanup_ui(self):
        """清理UI资源"""
        try:
            # 取消所有定时器
            if hasattr(self, 'after_ids'):
                for after_id in self.after_ids:
                    try:
                        self.root.after_cancel(after_id)
                    except:
                        pass
                self.after_ids.clear()
            
            # 清理日志处理器
            if hasattr(self, 'log_handler'):
                try:
                    self.log_handler.close()
                except:
                    pass
        except Exception:
            pass

if __name__ == "__main__":
    # 设置 DPI 感知，避免 Windows 自动缩放导致界面模糊
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    # 使用 ttkbootstrap 创建主窗口，应用Cosmo主题 (现代扁平化风格)
    root = tb.Window(themename="cosmo")
    
    # 居中显示
    w, h = 1400, 900
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - w) // 2
    y = (screen_h - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    
    app = WJXAutoFillApp(root)
    root.mainloop()
