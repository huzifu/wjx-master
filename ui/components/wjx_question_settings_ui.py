#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问卷星专用题型设置界面 - 重构优化版
完全重新设计的现代化界面，充分利用横屏优势，丰富策略支持
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import json
import os
import sys
import random
import math
from typing import Dict, List, Optional, Any

# 添加核心分析模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core', 'analysis'))

try:
    from core.analysis.reliability_analyzer import ReliabilityAnalyzer
except Exception:
    class ReliabilityAnalyzer:
        def analyze_questionnaire_reliability(self, question_data):
            return None


class ModernTheme:
    """现代化配色主题"""

    # 主色调 - 深蓝科技风
    PRIMARY = "#2563EB"      # 主蓝色
    PRIMARY_LIGHT = "#3B82F6" # 浅蓝色
    PRIMARY_DARK = "#1D4ED8"  # 深蓝色

    # 辅助色
    SECONDARY = "#64748B"     # 灰蓝色
    SUCCESS = "#10B981"       # 成功绿
    WARNING = "#F59E0B"       # 警告黄
    ERROR = "#EF4444"         # 错误红
    INFO = "#06B6D4"          # 信息青

    # 背景色
    BG_PRIMARY = "#F8FAFC"    # 主背景
    BG_SECONDARY = "#F1F5F9"  # 次背景
    BG_ACCENT = "#E2E8F0"     # 强调背景

    # 文字色
    TEXT_PRIMARY = "#0F172A"   # 主文字
    TEXT_SECONDARY = "#475569" # 次文字
    TEXT_MUTED = "#94A3B8"     # 弱化文字

    # 边框色
    BORDER_LIGHT = "#E2E8F0"
    BORDER_MEDIUM = "#CBD5E1"
    BORDER_DARK = "#94A3B8"

    # 题型专用色彩 - 更现代的配色
    QUESTION_COLORS = {
        '0': '#6366F1',  # 指导语 - 靛蓝
        '1': '#10B981',  # 填空题 - 翠绿
        '2': '#06B6D4',  # 多项填空 - 青色
        '3': '#F59E0B',  # 单选题 - 琥珀
        '4': '#8B5CF6',  # 多选题 - 紫色
        '5': '#EF4444',  # 量表题 - 红色
        '6': '#84CC16',  # 矩阵题 - 青柠
        '7': '#14B8A6',  # 下拉题 - 蓝绿
        '8': '#F97316',  # 矩阵量表 - 橙色
        '11': '#EC4899', # 排序题 - 粉色
    }


class AdvancedStrategies:
    """高级分布策略"""

    @staticmethod
    def normal_distribution(size: int, center: float = 0.5, std: float = 0.15) -> List[float]:
        """正态分布"""
        values = []
        for i in range(size):
            x = (i + 0.5) / size
            # 正态分布密度函数
            y = math.exp(-0.5 * ((x - center) / std) ** 2)
            values.append(y)

        # 归一化
        total = sum(values)
        return [v / total for v in values] if total > 0 else [1/size] * size

    @staticmethod
    def beta_distribution(size: int, alpha: float = 2, beta: float = 2) -> List[float]:
        """Beta分布"""
        values = []
        for i in range(size):
            x = (i + 0.5) / size
            # Beta分布密度函数近似
            y = (x ** (alpha - 1)) * ((1 - x) ** (beta - 1))
            values.append(y)

        total = sum(values)
        return [v / total for v in values] if total > 0 else [1/size] * size

    @staticmethod
    def exponential_distribution(size: int, rate: float = 2.0, reverse: bool = False) -> List[float]:
        """指数分布"""
        values = []
        for i in range(size):
            x = (i + 0.5) / size
            if reverse:
                x = 1 - x
            y = rate * math.exp(-rate * x)
            values.append(y)

        total = sum(values)
        return [v / total for v in values] if total > 0 else [1/size] * size

    @staticmethod
    def likert_5_optimal(size: int) -> List[float]:
        """5点量表最优分布"""
        if size != 5:
            return AdvancedStrategies.normal_distribution(size)
        # 基于心理学研究的最优分布
        return [0.1, 0.2, 0.4, 0.25, 0.05]

    @staticmethod
    def likert_7_optimal(size: int) -> List[float]:
        """7点量表最优分布"""
        if size != 7:
            return AdvancedStrategies.normal_distribution(size)
        return [0.05, 0.1, 0.2, 0.3, 0.2, 0.1, 0.05]

    @staticmethod
    def u_shaped_distribution(size: int) -> List[float]:
        """U型分布（两端概率高）"""
        values = []
        for i in range(size):
            x = (i + 0.5) / size
            # U型函数
            y = (x - 0.5) ** 2 + 0.1
            values.append(1 / y)  # 反比

        total = sum(values)
        return [v / total for v in values] if total > 0 else [1/size] * size

class WJXQuestionSettingsUI:
    """问卷星题型设置界面 - 重构优化版"""

    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        self.root = parent if isinstance(parent, tk.Tk) else parent.winfo_toplevel()

        # 主题和样式
        self.theme = ModernTheme()
        self.strategies = AdvancedStrategies()

        # 界面变量
        self.container = None
        self.main_paned = None
        self.left_panel = None
        self.right_panel = None
        self.question_tree = None
        self.config_frame = None

        # 数据变量
        self.option_entries = {}
        self.strategy_vars = {}
        self.current_question = None

        # 题型定义 - 扩展版
        self.question_types = {
            '0': {'name': '指导语', 'icon': '📖', 'color': self.theme.QUESTION_COLORS['0']},
            '1': {'name': '填空题', 'icon': '✏️', 'color': self.theme.QUESTION_COLORS['1']},
            '2': {'name': '多项填空', 'icon': '📝', 'color': self.theme.QUESTION_COLORS['2']},
            '3': {'name': '单选题', 'icon': '🔘', 'color': self.theme.QUESTION_COLORS['3']},
            '4': {'name': '多选题', 'icon': '☑️', 'color': self.theme.QUESTION_COLORS['4']},
            '5': {'name': '量表题', 'icon': '📊', 'color': self.theme.QUESTION_COLORS['5']},
            '6': {'name': '矩阵题', 'icon': '📋', 'color': self.theme.QUESTION_COLORS['6']},
            '7': {'name': '下拉题', 'icon': '🔽', 'color': self.theme.QUESTION_COLORS['7']},
            '8': {'name': '矩阵量表', 'icon': '📈', 'color': self.theme.QUESTION_COLORS['8']},
            '11': {'name': '排序题', 'icon': '🔀', 'color': self.theme.QUESTION_COLORS['11']}
        }

        # 策略定义 - 大幅扩展
        self.distribution_strategies = {
            'random': {'name': '完全随机', 'desc': '所有选项等概率随机选择'},
            'uniform': {'name': '均匀分布', 'desc': '所有选项概率相等'},
            'normal': {'name': '正态分布', 'desc': '中间选项概率较高'},
            'normal_left': {'name': '左偏正态', 'desc': '左侧选项概率较高'},
            'normal_right': {'name': '右偏正态', 'desc': '右侧选项概率较高'},
            'beta_22': {'name': 'Beta(2,2)', 'desc': '中心集中的Beta分布'},
            'beta_15': {'name': 'Beta(1,5)', 'desc': '左偏的Beta分布'},
            'beta_51': {'name': 'Beta(5,1)', 'desc': '右偏的Beta分布'},
            'exponential': {'name': '指数递减', 'desc': '从左到右递减'},
            'exponential_reverse': {'name': '指数递增', 'desc': '从左到右递增'},
            'u_shaped': {'name': 'U型分布', 'desc': '两端概率高，中间概率低'},
            'likert_5_optimal': {'name': '5点量表最优', 'desc': '适合5点量表的心理学最优分布'},
            'likert_7_optimal': {'name': '7点量表最优', 'desc': '适合7点量表的心理学最优分布'},
            'extreme_avoidance': {'name': '避免极端', 'desc': '减少极端选项的选择概率'},
            'social_desirability': {'name': '社会期望', 'desc': '倾向于社会期望的回答'},
            'custom': {'name': '自定义配置', 'desc': '手动设置每个选项的权重'}
        }

        # 状态变量
        self.total_questions_var = tk.StringVar(value="题目总数: 0")
        self.configured_questions_var = tk.StringVar(value="已配置: 0")
        self.current_question_var = tk.StringVar(value="当前题目: 无")

        # 初始化界面
        self._setup_styles()

        logging.info("[UI] 重构版问卷星题型设置界面初始化完成")

    def _setup_styles(self):
        """设置现代化样式"""
        style = ttk.Style()

        # 不覆盖全局主题，保持与主应用一致
        # style.theme_use('clam')  # 已移除，避免与主程序主题冲突

        # 使用 11pt 字体确保清晰可读
        self._ui_font = ('Microsoft YaHei UI', 11)
        self._ui_font_bold = ('Microsoft YaHei UI', 11, 'bold')
        self._ui_font_small = ('Microsoft YaHei UI', 10)

        # 自定义样式
        style.configure('Modern.TLabel',
                       foreground=self.theme.TEXT_PRIMARY,
                       font=self._ui_font)

        style.configure('Title.TLabel',
                       foreground=self.theme.PRIMARY,
                       font=('Microsoft YaHei UI', 18, 'bold'))

        style.configure('Subtitle.TLabel',
                       foreground=self.theme.TEXT_SECONDARY,
                       font=('Microsoft YaHei UI', 13, 'bold'))

        style.configure('Modern.TButton',
                       font=self._ui_font)

        style.configure('Primary.TButton',
                       font=self._ui_font_bold)

        # 配置Treeview样式 - 增大行高和字体
        style.configure('Modern.Treeview',
                       background=self.theme.BG_PRIMARY,
                       foreground=self.theme.TEXT_PRIMARY,
                       font=self._ui_font,
                       rowheight=32)

        style.configure('Modern.Treeview.Heading',
                       background=self.theme.BG_SECONDARY,
                       foreground=self.theme.TEXT_PRIMARY,
                       font=self._ui_font_bold)

        # 配置Frame样式
        style.configure('Card.TFrame',
                       background=self.theme.BG_PRIMARY,
                       relief='raised',
                       borderwidth=1)

    def create_question_settings_frame(self, parent, show_header=True):
        """创建主界面框架"""
        self.container = parent

        # 主容器 - 减少默认padding，由外部父容器控制
        main_frame = ttk.Frame(parent)
        pad_x = 10 if show_header else 0
        pad_y = 10 if show_header else 0
        main_frame.pack(fill=tk.BOTH, expand=True, padx=pad_x, pady=pad_y)

        # 创建头部
        if show_header:
            self._create_modern_header(main_frame)

        # 创建工具栏
        self._create_advanced_toolbar(main_frame)

        # 创建状态栏
        self._create_status_bar(main_frame)

        # 创建主内容区域 - 双面板设计
        self._create_dual_panel_layout(main_frame)

        # 初始化数据
        self.refresh_interface()

    def _create_modern_header(self, parent):
        """创建现代化头部"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        # 左侧标题区域
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 主标题
        title_label = ttk.Label(title_frame, text="智能表单自动填充系统",style='Title.TLabel')
        title_label.pack(anchor=tk.W)

        # 副标题
        subtitle_label = ttk.Label(title_frame,
                                 text="Professional Questionnaire Configuration Platform",
                                 foreground=self.theme.TEXT_MUTED,
                                 font=self._ui_font)
        subtitle_label.pack(anchor=tk.W, pady=(2, 0))

        # 右侧版本信息
        version_frame = ttk.Frame(header_frame)
        version_frame.pack(side=tk.RIGHT)



    def _create_advanced_toolbar(self, parent):
        """创建高级工具栏"""
        toolbar_frame = ttk.Frame(parent, style='Card.TFrame')
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))

        # 内部padding
        inner_frame = ttk.Frame(toolbar_frame)
        inner_frame.pack(fill=tk.X, padx=15, pady=10)

        # 左侧工具组
        left_tools = ttk.Frame(inner_frame)
        left_tools.pack(side=tk.LEFT)

        # 数据操作
        data_group = ttk.LabelFrame(left_tools, text="数据操作", padding=5)
        data_group.pack(side=tk.LEFT, padx=(0, 10))

        data_buttons = [
            ("刷新数据", self.refresh_interface, self.theme.INFO),
            ("导入配置", self.import_config, self.theme.SUCCESS),
            ("导出配置", self.export_config, self.theme.WARNING)
        ]

        for text, command, color in data_buttons:
            btn = tk.Button(data_group, text=text, command=command,
                          bg=color, fg='white', relief='flat',
                          font=self._ui_font, cursor='hand2')
            btn.pack(side=tk.LEFT, padx=2, ipadx=8, ipady=2)

        # 批量操作
        batch_group = ttk.LabelFrame(left_tools, text="批量操作", padding=5)
        batch_group.pack(side=tk.LEFT, padx=(0, 10))

        batch_buttons = [
            ("智能配置", self.smart_configuration, self.theme.PRIMARY),
            ("批量设置", self.advanced_batch_settings, self.theme.SECONDARY),
            ("策略推荐", self.recommend_strategies, self.theme.SUCCESS)
        ]

        for text, command, color in batch_buttons:
            btn = tk.Button(batch_group, text=text, command=command,
                          bg=color, fg='white', relief='flat',
                          font=self._ui_font, cursor='hand2')
            btn.pack(side=tk.LEFT, padx=2, ipadx=8, ipady=2)

        # 右侧快捷操作
        right_tools = ttk.Frame(inner_frame)
        right_tools.pack(side=tk.RIGHT)

        # 视图控制
        view_group = ttk.LabelFrame(right_tools, text="视图控制", padding=5)
        view_group.pack(side=tk.RIGHT)

        # 显示模式选择
        ttk.Label(view_group, text="显示模式:", font=self._ui_font).pack(side=tk.LEFT, padx=(0, 5))

        self.view_mode_var = tk.StringVar(value="详细")
        view_combo = ttk.Combobox(view_group, textvariable=self.view_mode_var,
                                values=["简洁", "详细", "专家"], state='readonly', width=8)
        view_combo.pack(side=tk.LEFT, padx=(0, 10))
        view_combo.bind('<<ComboboxSelected>>', self._on_view_mode_change)

        # 保存按钮
        save_btn = tk.Button(view_group, text="保存所有配置",
                           command=self.save_all_configurations,
                           bg=self.theme.SUCCESS, fg='white', relief='flat',
                           font=self._ui_font_bold, cursor='hand2')
        save_btn.pack(side=tk.LEFT, ipadx=14, ipady=5)

    def _create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent, style='Card.TFrame')
        status_frame.pack(fill=tk.X, pady=(0, 10))

        inner_frame = ttk.Frame(status_frame)
        inner_frame.pack(fill=tk.X, padx=15, pady=8)

        # 左侧统计信息
        stats_frame = ttk.Frame(inner_frame)
        stats_frame.pack(side=tk.LEFT)

        # 状态指示器
        indicators = [
            (self.total_questions_var, self.theme.PRIMARY),
            (self.configured_questions_var, self.theme.SUCCESS),
            (self.current_question_var, self.theme.INFO)
        ]

        for var, color in indicators:
            indicator = tk.Label(stats_frame, textvariable=var,
                               bg=color, fg='white', font=self._ui_font,
                               padx=12, pady=4)
            indicator.pack(side=tk.LEFT, padx=(0, 10))

        # 右侧进度信息
        progress_frame = ttk.Frame(inner_frame)
        progress_frame.pack(side=tk.RIGHT)

        # 配置进度条
        ttk.Label(progress_frame, text="配置进度:").pack(side=tk.LEFT, padx=(0, 5))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                          length=150, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 10))

        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side=tk.LEFT)

    def _create_dual_panel_layout(self, parent):
        """创建双面板布局 - 充分利用横屏"""
        # 主分割面板
        self.main_paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)

        # 左侧面板 - 题目列表和概览
        self._create_left_panel()

        # 右侧面板 - 详细配置
        self._create_right_panel()

        # 设置初始分割比例 - 充分利用横屏空间
        self.root.after(100, lambda: self.main_paned.sashpos(0, 450))

    def _create_left_panel(self):
        """创建左侧面板"""
        left_container = ttk.Frame(self.main_paned, style='Card.TFrame')
        self.main_paned.add(left_container, weight=1)

        self.left_panel = ttk.Frame(left_container)
        self.left_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧标题
        title_frame = ttk.Frame(self.left_panel)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(title_frame, text="题目概览", style='Subtitle.TLabel').pack(side=tk.LEFT)

        # 快捷筛选
        filter_frame = ttk.Frame(title_frame)
        filter_frame.pack(side=tk.RIGHT)

        ttk.Label(filter_frame, text="筛选:").pack(side=tk.LEFT, padx=(0, 5))

        self.filter_var = tk.StringVar(value="全部")
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                  width=10, state='readonly')
        filter_combo.pack(side=tk.LEFT)
        filter_combo.bind('<<ComboboxSelected>>', self._on_filter_change)

        # 题目树形视图
        self._create_question_tree()

        # 题型统计图表
        self._create_type_statistics()

    def _create_question_tree(self):
        """创建题目树形视图"""
        # 树形视图容器
        tree_container = ttk.Frame(self.left_panel)
        tree_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建Treeview - 增加高度以显示更多题目
        columns = ('type', 'status', 'strategy')
        self.question_tree = ttk.Treeview(tree_container, columns=columns,
                                        show='tree headings', style='Modern.Treeview',
                                        height=20)

        # 配置列 - 优化列宽以充分利用左侧面板空间
        self.question_tree.heading('#0', text='题目', anchor=tk.W)
        self.question_tree.heading('type', text='类型', anchor=tk.CENTER)
        self.question_tree.heading('status', text='状态', anchor=tk.CENTER)
        self.question_tree.heading('strategy', text='策略', anchor=tk.CENTER)

        self.question_tree.column('#0', width=300, minwidth=220)
        self.question_tree.column('type', width=110, minwidth=80)
        self.question_tree.column('status', width=80, minwidth=70)
        self.question_tree.column('strategy', width=130, minwidth=100)

        # 滚动条
        tree_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL,
                                  command=self.question_tree.yview)
        self.question_tree.configure(yscrollcommand=tree_scroll.set)

        # 布局
        self.question_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定事件
        self.question_tree.bind('<<TreeviewSelect>>', self._on_question_select)
        self.question_tree.bind('<Double-1>', self._on_question_double_click)

    def _create_type_statistics(self):
        """创建题型统计"""
        stats_frame = ttk.LabelFrame(self.left_panel, text="题型统计", padding=10)
        stats_frame.pack(fill=tk.X)

        # 统计图表区域（简化版）
        self.stats_canvas = tk.Canvas(stats_frame, height=120, bg=self.theme.BG_PRIMARY)
        self.stats_canvas.pack(fill=tk.X, pady=5)

    def _create_right_panel(self):
        """创建右侧面板"""
        right_container = ttk.Frame(self.main_paned, style='Card.TFrame')
        self.main_paned.add(right_container, weight=2)

        self.right_panel = ttk.Frame(right_container)
        self.right_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 右侧标题
        title_frame = ttk.Frame(self.right_panel)
        title_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(title_frame, text="题目配置", style='Subtitle.TLabel').pack(side=tk.LEFT)

        # 配置选项卡
        self.config_notebook = ttk.Notebook(self.right_panel)
        self.config_notebook.pack(fill=tk.BOTH, expand=True)

        # 基础配置标签页
        self._create_basic_config_tab()

        # 高级配置标签页
        self._create_advanced_config_tab()

        # 预览标签页
        self._create_preview_tab()

    def _create_basic_config_tab(self):
        """创建基础配置标签页"""
        basic_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(basic_frame, text="基础配置")

        # 滚动容器
        canvas = tk.Canvas(basic_frame)
        scrollbar = ttk.Scrollbar(basic_frame, orient="vertical", command=canvas.yview)
        self.basic_scrollable_frame = ttk.Frame(canvas)

        self.basic_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.basic_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 鼠标滚轮绑定
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)

    def _create_advanced_config_tab(self):
        """创建高级配置标签页"""
        advanced_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(advanced_frame, text="高级配置")

        # 策略推荐系统
        strategy_frame = ttk.LabelFrame(advanced_frame, text="智能策略推荐", padding=10)
        strategy_frame.pack(fill=tk.X, padx=10, pady=5)

        # 推荐引擎
        ttk.Label(strategy_frame, text="基于题目类型和选项数量的智能推荐:").pack(anchor=tk.W)

        self.recommendation_text = tk.Text(strategy_frame, height=4, wrap=tk.WORD,
                                         font=self._ui_font)
        self.recommendation_text.pack(fill=tk.X, pady=(5, 0))

        # 批量操作区域
        batch_frame = ttk.LabelFrame(advanced_frame, text="批量操作", padding=10)
        batch_frame.pack(fill=tk.X, padx=10, pady=5)

        # 批量策略应用
        batch_strategy_frame = ttk.Frame(batch_frame)
        batch_strategy_frame.pack(fill=tk.X, pady=5)

        ttk.Label(batch_strategy_frame, text="批量应用策略:").pack(side=tk.LEFT)

        self.batch_strategy_var = tk.StringVar()
        batch_strategy_combo = ttk.Combobox(batch_strategy_frame,
                                           textvariable=self.batch_strategy_var,
                                           values=list(self.distribution_strategies.keys()),
                                           state='readonly', width=20)
        batch_strategy_combo.pack(side=tk.LEFT, padx=(5, 10))

        tk.Button(batch_strategy_frame, text="应用到选中题目",
                command=self.apply_batch_strategy,
                bg=self.theme.PRIMARY, fg='white', relief='flat',
                font=self._ui_font).pack(side=tk.LEFT, ipadx=8, ipady=3)

    def _create_preview_tab(self):
        """创建预览标签页"""
        preview_frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(preview_frame, text="效果预览")

        # 预览图表
        chart_frame = ttk.LabelFrame(preview_frame, text="分布预览图", padding=10)
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.preview_canvas = tk.Canvas(chart_frame, bg='white', height=300)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, pady=5)

        # 配置摘要
        summary_frame = ttk.LabelFrame(preview_frame, text="配置摘要", padding=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=5)

        self.summary_text = tk.Text(summary_frame, height=8, wrap=tk.WORD,
                                  font=self._ui_font)
        self.summary_text.pack(fill=tk.X)

    def _create_tooltip(self, widget, text):
        """创建工具提示"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(tooltip, text=text, background="#ffffe0", font=('微软雅黑', 8))
            label.pack()
            widget.tooltip = tooltip
            
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
                
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def refresh_interface(self):
        """刷新界面数据"""
        try:
            # 清理旧数据
            self.option_entries.clear()
            self.strategy_vars.clear()

            # 确保基础数据
            self._ensure_data_integrity()

            # 更新题目树
            self._update_question_tree()

            # 更新统计信息
            self._update_statistics()

            # 更新筛选选项
            self._update_filter_options()

            # 清空配置面板
            self._clear_config_panels()

        except Exception as e:
            logging.error(f"刷新界面失败: {e}")
            messagebox.showerror("错误", f"刷新失败: {str(e)}")

    def _ensure_data_integrity(self):
        """确保数据完整性"""
        # 确保基础数据结构
        required_keys = ['question_texts', 'question_types', 'option_texts']
        for key in required_keys:
            if key not in self.config:
                self.config[key] = {}

        # 推断题目类型
        q_types = self.config.get('question_types', {})
        q_texts = self.config.get('question_texts', {})

        type_mapping = {
            'single_prob': '3', 'multiple_prob': '4', 'matrix_prob': '6',
            'scale_prob': '5', 'droplist_prob': '7', 'texts': '1',
            'multiple_texts': '2', 'reorder_prob': '11', 'matrix_scale_prob': '8'
        }

        for config_key, type_code in type_mapping.items():
            for qid in self.config.get(config_key, {}).keys():
                if qid not in q_types:
                    q_types[qid] = type_code

        # 默认为单选题
        for qid in q_texts.keys():
            if qid not in q_types:
                q_types[qid] = '3'

    def _update_question_tree(self):
        """更新题目树"""
        # 清空树
        for item in self.question_tree.get_children():
            self.question_tree.delete(item)

        q_texts = self.config.get('question_texts', {})
        q_types = self.config.get('question_types', {})

        if not q_texts:
            return

        # 按题型分组
        type_groups = {}
        for qid, qtype in q_types.items():
            if qtype not in type_groups:
                type_groups[qtype] = []
            type_groups[qtype].append(qid)

        # 添加到树中
        for qtype, qids in type_groups.items():
            type_info = self.question_types.get(qtype, {'name': f'类型{qtype}', 'icon': '❓'})
            type_name = f"{type_info['icon']} {type_info['name']} ({len(qids)}题)"

            # 创建类型节点
            type_node = self.question_tree.insert('', 'end', text=type_name,
                                                 values=('', '', ''), open=True)

            # 添加题目
            for qid in sorted(qids, key=lambda x: int(str(x)) if str(x).isdigit() else float('inf')):
                text = q_texts.get(qid, f'题目 {qid}')[:50]
                if len(text) > 47:
                    text = text[:47] + "..."

                # 检查配置状态
                status = self._get_question_status(qid, qtype)
                strategy = self._get_question_strategy(qid, qtype)

                self.question_tree.insert(type_node, 'end', text=f"Q{qid}: {text}",
                                        values=(type_info['name'], status, strategy),
                                        tags=(qid, qtype))

    def _get_question_status(self, qid, qtype):
        """获取题目配置状态"""
        config_keys = {
            '3': 'single_prob', '4': 'multiple_prob', '5': 'scale_prob',
            '6': 'matrix_prob', '7': 'droplist_prob', '8': 'matrix_scale_prob',
            '11': 'reorder_prob', '1': 'texts', '2': 'multiple_texts'
        }

        if qtype == '0':  # 指导语
            return '无需配置'

        config_key = config_keys.get(qtype)
        if config_key and qid in self.config.get(config_key, {}):
            return '已配置'
        else:
            return '未配置'

    def _get_question_strategy(self, qid, qtype):
        """获取题目策略"""
        if qtype in ['0', '1', '2']:  # 无需策略的题型
            return '-'

        config_keys = {
            '3': 'single_prob', '4': 'multiple_prob', '5': 'scale_prob',
            '6': 'matrix_prob', '7': 'droplist_prob', '8': 'matrix_scale_prob',
            '11': 'reorder_prob'
        }

        config_key = config_keys.get(qtype)
        if config_key:
            config_data = self.config.get(config_key, {}).get(qid)
            if config_data:
                if isinstance(config_data, list) and len(config_data) > 0:
                    if config_data[0] == -1:
                        return '随机'
                    else:
                        return '自定义'

        return '默认'

    def _update_statistics(self):
        """更新统计信息"""
        q_texts = self.config.get('question_texts', {})
        q_types = self.config.get('question_types', {})

        total_count = len(q_texts)
        configured_count = 0

        # 统计已配置题目
        config_keys = ['single_prob', 'multiple_prob', 'scale_prob', 'matrix_prob',
                      'droplist_prob', 'matrix_scale_prob', 'reorder_prob', 'texts', 'multiple_texts']

        configured_qids = set()
        for key in config_keys:
            configured_qids.update(self.config.get(key, {}).keys())

        configured_count = len(configured_qids)

        # 更新状态变量
        self.total_questions_var.set(f"题目总数: {total_count}")
        self.configured_questions_var.set(f"已配置: {configured_count}")

        # 更新进度
        if total_count > 0:
            progress = (configured_count / total_count) * 100
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{progress:.1f}%")
        else:
            self.progress_var.set(0)
            self.progress_label.config(text="0%")

        # 更新统计图表
        self._draw_statistics_chart(q_types)

    def _draw_statistics_chart(self, q_types):
        """绘制统计图表"""
        self.stats_canvas.delete("all")

        if not q_types:
            return

        # 统计各类型数量
        type_counts = {}
        for qtype in q_types.values():
            type_name = self.question_types.get(qtype, {}).get('name', f'类型{qtype}')
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        if not type_counts:
            return

        # 绘制简单柱状图
        canvas_width = self.stats_canvas.winfo_width()
        canvas_height = self.stats_canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            self.root.after(100, lambda: self._draw_statistics_chart(q_types))
            return

        max_count = max(type_counts.values())
        bar_width = (canvas_width - 40) // len(type_counts)

        x = 20
        colors = [self.theme.PRIMARY, self.theme.SUCCESS, self.theme.WARNING,
                 self.theme.ERROR, self.theme.INFO, self.theme.SECONDARY]

        for i, (type_name, count) in enumerate(type_counts.items()):
            bar_height = (count / max_count) * (canvas_height - 40)
            color = colors[i % len(colors)]

            # 绘制柱子
            self.stats_canvas.create_rectangle(
                x, canvas_height - bar_height - 10,
                x + bar_width - 5, canvas_height - 10,
                fill=color, outline=""
            )

            # 绘制标签
            self.stats_canvas.create_text(
                x + bar_width // 2, canvas_height - 5,
                text=type_name[:4], font=('Microsoft YaHei UI', 8),
                fill=self.theme.TEXT_PRIMARY
            )

            # 绘制数值
            self.stats_canvas.create_text(
                x + bar_width // 2, canvas_height - bar_height - 15,
                text=str(count), font=('Microsoft YaHei UI', 10, 'bold'),
                fill=color
            )

            x += bar_width

    def _update_filter_options(self):
        """更新筛选选项"""
        q_types = self.config.get('question_types', {})

        # 获取所有题型
        type_names = set()
        for qtype in q_types.values():
            type_name = self.question_types.get(qtype, {}).get('name', f'类型{qtype}')
            type_names.add(type_name)

        # 更新筛选下拉框
        filter_values = ['全部', '已配置', '未配置'] + sorted(type_names)

        # 找到筛选组合框并更新
        for widget in self.left_panel.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Frame):
                        for subchild in child.winfo_children():
                            if isinstance(subchild, ttk.Combobox) and hasattr(self, 'filter_var') and subchild['textvariable'] == str(self.filter_var):
                                subchild['values'] = filter_values
                                break

    def _clear_config_panels(self):
        """清空配置面板"""
        # 清空基础配置标签页
        for widget in self.basic_scrollable_frame.winfo_children():
            widget.destroy()

        # 显示选择提示
        placeholder = ttk.Label(self.basic_scrollable_frame,
                               text="请在左侧选择一个题目进行配置",
                               font=('Microsoft YaHei UI', 12),
                               foreground=self.theme.TEXT_MUTED)
        placeholder.pack(expand=True, pady=50)

    def _on_question_select(self, event):
        """题目选择事件"""
        selected_items = self.question_tree.selection()
        if not selected_items:
            return

        item = selected_items[0]
        tags = self.question_tree.item(item, 'tags')

        if len(tags) >= 2:  # 确保有qid和qtype
            qid, qtype = tags[0], tags[1]
            self.current_question = qid
            self.current_question_var.set(f"当前题目: Q{qid}")

            # 加载题目配置
            self._load_question_config(qid, qtype)

    def _on_question_double_click(self, event):
        """题目双击事件"""
        # 可以添加快速配置或编辑功能
        pass

    def _on_view_mode_change(self, event):
        """视图模式改变"""
        mode = self.view_mode_var.get()
        # 根据模式调整界面显示
        if self.current_question:
            qtype = self.config.get('question_types', {}).get(self.current_question, '3')
            self._load_question_config(self.current_question, qtype)

    def _on_filter_change(self, event):
        """筛选改变"""
        filter_value = self.filter_var.get()
        self._apply_tree_filter(filter_value)

    def _apply_tree_filter(self, filter_value):
        """应用树视图筛选"""
        # 获取所有项目
        all_items = []

        def collect_items(parent=""):
            for item in self.question_tree.get_children(parent):
                all_items.append(item)
                collect_items(item)

        collect_items()

        # 应用筛选
        for item in all_items:
            tags = self.question_tree.item(item, 'tags')
            if len(tags) >= 2:  # 题目项
                qid, qtype = tags[0], tags[1]

                show_item = True
                if filter_value == '已配置':
                    show_item = self._get_question_status(qid, qtype) == '已配置'
                elif filter_value == '未配置':
                    show_item = self._get_question_status(qid, qtype) == '未配置'
                elif filter_value != '全部':
                    type_name = self.question_types.get(qtype, {}).get('name', '')
                    show_item = type_name == filter_value

                # 控制显示/隐藏（简化实现）
                if not show_item:
                    self.question_tree.detach(item)
                else:
                    # 重新附加到父节点（需要找到正确的父节点）
                    pass

    def _load_question_config(self, qid, qtype):
        """加载题目配置界面"""
        # 清空配置面板
        for widget in self.basic_scrollable_frame.winfo_children():
            widget.destroy()

        # 创建题目信息头部
        self._create_question_header(qid, qtype)

        # 根据题型创建配置界面
        if qtype == '0':
            self._create_instruction_config(qid)
        elif qtype in ['1', '2']:
            self._create_text_config(qid, qtype)
        else:
            self._create_choice_config(qid, qtype)

        # 更新预览和推荐
        self._update_preview(qid, qtype)
        self._update_recommendations(qid, qtype)

    def _create_question_header(self, qid, qtype):
        """创建题目信息头部"""
        header_frame = ttk.Frame(self.basic_scrollable_frame, style='Card.TFrame')
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        inner_frame = ttk.Frame(header_frame)
        inner_frame.pack(fill=tk.X, padx=15, pady=15)

        # 题目基本信息
        type_info = self.question_types.get(qtype, {'name': '未知类型', 'icon': '❓'})

        # 题目标题
        title_text = f"Q{qid} - {type_info['icon']} {type_info['name']}"
        title_label = ttk.Label(inner_frame, text=title_text,
                               font=('Microsoft YaHei UI', 14, 'bold'),
                               foreground=type_info.get('color', self.theme.PRIMARY))
        title_label.pack(anchor=tk.W, pady=(0, 5))

        # 题目内容
        q_text = self.config.get('question_texts', {}).get(qid, '').strip()
        if q_text:
            # 清理题目文本
            clean_text = q_text.replace('*', '').strip()
            content_label = ttk.Label(inner_frame, text=clean_text,
                                    font=('Microsoft YaHei UI', 10),
                                    wraplength=600, justify=tk.LEFT,
                                    foreground=self.theme.TEXT_PRIMARY)
            content_label.pack(anchor=tk.W, pady=(0, 10))

        # 状态信息
        status_frame = ttk.Frame(inner_frame)
        status_frame.pack(fill=tk.X)

        status = self._get_question_status(qid, qtype)
        strategy = self._get_question_strategy(qid, qtype)

        status_color = self.theme.SUCCESS if status == '已配置' else self.theme.WARNING

        status_label = tk.Label(status_frame, text=f"状态: {status}",
                              bg=status_color, fg='white', padx=8, pady=2,
                              font=('Microsoft YaHei UI', 9))
        status_label.pack(side=tk.LEFT)

        if strategy != '-':
            strategy_label = tk.Label(status_frame, text=f"策略: {strategy}",
                                    bg=self.theme.INFO, fg='white', padx=8, pady=2,
                                    font=('Microsoft YaHei UI', 9))
            strategy_label.pack(side=tk.LEFT, padx=(5, 0))

    def _create_instruction_config(self, qid):
        """创建指导语配置"""
        config_frame = ttk.LabelFrame(self.basic_scrollable_frame, text="指导语配置", padding=15)
        config_frame.pack(fill=tk.X, padx=10, pady=10)

        info_label = ttk.Label(config_frame,
                              text="指导语题目无需特殊配置，将在问卷中正常显示。",
                              font=('Microsoft YaHei UI', 10),
                              foreground=self.theme.TEXT_SECONDARY)
        info_label.pack(pady=10)

    def _create_text_config(self, qid, qtype):
        """创建文本题配置"""
        config_frame = ttk.LabelFrame(self.basic_scrollable_frame, text="文本生成配置", padding=15)
        config_frame.pack(fill=tk.X, padx=10, pady=10)

        # 获取当前配置
        if qtype == '1':
            current_config = self.config.get('texts', {}).get(qid, [""])
            current_text = current_config[0] if current_config else ""
        else:  # qtype == '2'
            current_config = self.config.get('multiple_texts', {}).get(qid, [[""]])
            current_text = current_config[0][0] if current_config and current_config[0] else ""

        # 文本模板输入
        ttk.Label(config_frame, text="生成文本模板:").pack(anchor=tk.W, pady=(0, 5))

        text_var = tk.StringVar(value=current_text)
        text_entry = ttk.Entry(config_frame, textvariable=text_var, width=60)
        text_entry.pack(fill=tk.X, pady=(0, 10))

        # 保存变量引用
        if qid not in self.option_entries:
            self.option_entries[qid] = []
        self.option_entries[qid] = [text_var]

        # 预设模板
        templates_frame = ttk.LabelFrame(config_frame, text="常用模板", padding=10)
        templates_frame.pack(fill=tk.X, pady=10)

        templates = [
            ("随机姓名", "张三"),
            ("随机邮箱", "user@example.com"),
            ("随机手机", "13800138000"),
            ("随机地址", "北京市朝阳区"),
            ("自定义文本", "请填写自定义内容")
        ]

        for i, (name, template) in enumerate(templates):
            btn = tk.Button(templates_frame, text=name,
                          command=lambda t=template: text_var.set(t),
                          bg=self.theme.BG_SECONDARY, relief='flat',
                          font=('Microsoft YaHei UI', 9))
            btn.grid(row=i//3, column=i%3, padx=5, pady=5, sticky='w')

    def _create_choice_config(self, qid, qtype):
        """创建选择题配置"""
        # 策略选择区域
        strategy_frame = ttk.LabelFrame(self.basic_scrollable_frame, text="分布策略", padding=15)
        strategy_frame.pack(fill=tk.X, padx=10, pady=10)

        # 当前策略
        strategy_var = tk.StringVar(value='uniform')
        if qid not in self.strategy_vars:
            self.strategy_vars[qid] = strategy_var

        # 策略选择下拉列表
        strategy_combo_frame = ttk.Frame(strategy_frame)
        strategy_combo_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(strategy_combo_frame, text="选择策略:",
                 font=('Microsoft YaHei UI', 9, 'bold')).pack(side=tk.LEFT)

        # 创建策略选项列表
        strategy_options = []
        strategy_values = []
        for strategy_key, strategy_info in self.distribution_strategies.items():
            display_text = f"{strategy_info['name']} - {strategy_info['desc']}"
            strategy_options.append(display_text)
            strategy_values.append(strategy_key)

        strategy_combo = ttk.Combobox(strategy_combo_frame,
                                    textvariable=strategy_var,
                                    values=strategy_values,
                                    state='readonly',
                                    width=25,
                                    font=('Microsoft YaHei UI', 9))
        strategy_combo.pack(side=tk.LEFT, padx=(10, 0))

        # 设置显示文本映射
        def update_display_text(*args):
            current_value = strategy_var.get()
            if current_value in self.distribution_strategies:
                strategy_info = self.distribution_strategies[current_value]
                display_text = f"{strategy_info['name']} - {strategy_info['desc']}"
                strategy_combo.set(display_text)
            self._apply_strategy(qid, qtype)

        strategy_var.trace('w', update_display_text)

        # 应用按钮
        apply_btn = tk.Button(strategy_combo_frame, text="应用策略",
                            command=lambda: self._apply_strategy(qid, qtype),
                            bg=self.theme.SUCCESS, fg='white', relief='flat',
                            font=('Microsoft YaHei UI', 9))
        apply_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # 策略描述区域
        desc_frame = ttk.Frame(strategy_frame)
        desc_frame.pack(fill=tk.X, pady=(5, 0))

        desc_label = ttk.Label(desc_frame, text="策略说明:",
                             font=('Microsoft YaHei UI', 9, 'bold'))
        desc_label.pack(anchor=tk.W)

        self.strategy_desc_text = tk.Text(desc_frame, height=3, wrap=tk.WORD,
                                        font=('Microsoft YaHei UI', 9),
                                        bg=self.theme.BG_SECONDARY)
        self.strategy_desc_text.pack(fill=tk.X, pady=(5, 0))

        # 更新策略描述
        def update_strategy_desc(*args):
            current_value = strategy_var.get()
            if current_value in self.distribution_strategies:
                desc = self.distribution_strategies[current_value]['desc']
                self.strategy_desc_text.delete(1.0, tk.END)
                self.strategy_desc_text.insert(tk.END, desc)

        strategy_var.trace('w', update_strategy_desc)
        update_strategy_desc()  # 初始化描述

        # 选项配置区域
        options_frame = ttk.LabelFrame(self.basic_scrollable_frame, text="选项权重配置", padding=15)
        options_frame.pack(fill=tk.X, padx=10, pady=10)

        # 获取选项
        options = self.config.get('option_texts', {}).get(qid, [])
        if not options:
            ttk.Label(options_frame, text="该题目没有选项数据",
                     foreground=self.theme.WARNING).pack(pady=10)
            return

        # 选项权重表格
        self._create_options_weight_table(options_frame, qid, options)

    def _create_options_weight_table(self, parent, qid, options):
        """创建选项权重表格"""
        # 表格头部
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        headers = ['选项', '内容', '权重', '预计概率', '操作']
        # 增加内容列宽度以充分利用横屏空间
        widths = [60, 500, 80, 80, 120]

        for i, (header, width) in enumerate(zip(headers, widths)):
            label = ttk.Label(header_frame, text=header, font=self._ui_font_bold)
            label.grid(row=0, column=i, padx=8, pady=6, sticky='w')
            header_frame.grid_columnconfigure(i, minsize=width)

        # 初始化变量
        if qid not in self.option_entries:
            self.option_entries[qid] = []
        else:
            self.option_entries[qid].clear()

        # 选项行
        for i, option_text in enumerate(options):
            row_frame = ttk.Frame(parent)
            row_frame.pack(fill=tk.X, pady=3)

            # 选项标识
            option_label = tk.Label(row_frame, text=chr(65 + i),
                                  bg=self.theme.PRIMARY, fg='white',
                                  font=self._ui_font_bold,
                                  width=4, height=1)
            option_label.grid(row=0, column=0, padx=6, pady=3)

            # 选项内容 - 增加显示长度以充分利用横屏空间
            content = option_text[:80] + "..." if len(option_text) > 80 else option_text
            content_label = ttk.Label(row_frame, text=content,
                                    font=self._ui_font)
            content_label.grid(row=0, column=1, padx=6, pady=3, sticky='w')
            row_frame.grid_columnconfigure(1, minsize=500)

            # 权重输入
            weight_var = tk.DoubleVar(value=1.0)
            weight_entry = ttk.Entry(row_frame, textvariable=weight_var, width=12, justify='center',
                                    font=self._ui_font)
            weight_entry.grid(row=0, column=2, padx=6, pady=3)

            # 预计概率显示
            prob_var = tk.StringVar(value="0.0%")
            prob_label = ttk.Label(row_frame, textvariable=prob_var,
                                 font=self._ui_font,
                                 foreground=self.theme.INFO)
            prob_label.grid(row=0, column=3, padx=6, pady=3)

            # 操作按钮
            btn_frame = ttk.Frame(row_frame)
            btn_frame.grid(row=0, column=4, padx=5, pady=2)

            # 复制权重按钮
            copy_btn = tk.Button(btn_frame, text="复制",
                               command=lambda idx=i: self._copy_weight(qid, idx),
                               bg=self.theme.INFO, fg='white', relief='flat',
                               font=self._ui_font_small)
            copy_btn.pack(side=tk.LEFT, padx=2, ipadx=4, ipady=1)

            # 重置按钮
            reset_btn = tk.Button(btn_frame, text="重置",
                                command=lambda var=weight_var: var.set(1.0),
                                bg=self.theme.WARNING, fg='white', relief='flat',
                                font=self._ui_font_small)
            reset_btn.pack(side=tk.LEFT, padx=2, ipadx=4, ipady=1)

            # 保存变量引用
            self.option_entries[qid].append(weight_var)

            # 绑定权重变化事件
            weight_var.trace('w', lambda *args, q=qid: self._update_probabilities(q))

        # 操作按钮区域
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=(15, 0))

        # 归一化按钮
        normalize_btn = tk.Button(action_frame, text="归一化权重",
                                command=lambda: self._normalize_weights(qid),
                                bg=self.theme.SUCCESS, fg='white', relief='flat',
                                font=self._ui_font)
        normalize_btn.pack(side=tk.LEFT, padx=(0, 10), ipadx=8, ipady=3)

        # 保存配置按钮
        save_btn = tk.Button(action_frame, text="保存配置",
                           command=lambda: self._save_question_config(qid),
                           bg=self.theme.PRIMARY, fg='white', relief='flat',
                           font=self._ui_font_bold)
        save_btn.pack(side=tk.RIGHT, ipadx=8, ipady=3)

        # 初始更新概率显示
        self._update_probabilities(qid)

    def _apply_strategy(self, qid, qtype):
        """应用选择的策略"""
        try:
            if qid not in self.strategy_vars:
                logging.warning(f"题目 {qid} 没有策略变量")
                return

            strategy = self.strategy_vars[qid].get()
            if qid not in self.option_entries:
                logging.warning(f"题目 {qid} 没有选项变量")
                return

            option_vars = self.option_entries[qid]
            option_count = len(option_vars)

            if option_count == 0:
                return

            # 根据策略应用不同的分布
            if strategy == 'random':
                self._set_random_distribution(qid)
            elif strategy == 'uniform':
                self._set_uniform_distribution(qid, option_count)
            elif strategy == 'normal':
                self._set_normal_distribution(qid, option_count)
            elif strategy == 'normal_left':
                self._set_normal_left_distribution(qid, option_count)
            elif strategy == 'normal_right':
                self._set_normal_right_distribution(qid, option_count)
            elif strategy == 'beta_22':
                self._set_beta_distribution(qid, option_count, 2, 2)
            elif strategy == 'beta_15':
                self._set_beta_distribution(qid, option_count, 1, 5)
            elif strategy == 'beta_51':
                self._set_beta_distribution(qid, option_count, 5, 1)
            elif strategy == 'exponential':
                self._set_exponential_distribution(qid, option_count, False)
            elif strategy == 'exponential_reverse':
                self._set_exponential_distribution(qid, option_count, True)
            elif strategy == 'u_shaped':
                self._set_u_shaped_distribution(qid, option_count)
            elif strategy == 'likert_5_optimal':
                self._set_likert_5_optimal(qid, option_count)
            elif strategy == 'likert_7_optimal':
                self._set_likert_7_optimal(qid, option_count)
            elif strategy == 'extreme_avoidance':
                self._set_extreme_avoidance(qid, option_count)
            elif strategy == 'social_desirability':
                self._set_social_desirability(qid, option_count)
            else:
                # 默认均匀分布
                self._set_uniform_distribution(qid, option_count)

            # 更新概率显示
            self._update_probabilities(qid)

            logging.info(f"成功应用策略 {strategy} 到题目 {qid}")

        except Exception as e:
            logging.error(f"应用策略失败 {qid}: {e}")
            messagebox.showerror("错误", f"应用策略失败: {str(e)}")

    def _set_normal_distribution(self, qid, option_count):
        """设置正态分布"""
        if qid not in self.option_entries:
            return

        center = (option_count - 1) / 2.0
        std = option_count / 6.0  # 标准差

        for i, var in enumerate(self.option_entries[qid]):
            x = (i - center) / std
            weight = math.exp(-0.5 * x * x)
            var.set(weight)

    def _set_normal_left_distribution(self, qid, option_count):
        """设置左偏正态分布"""
        if qid not in self.option_entries:
            return

        center = option_count * 0.3  # 偏向左侧
        std = option_count / 6.0

        for i, var in enumerate(self.option_entries[qid]):
            x = (i - center) / std
            weight = math.exp(-0.5 * x * x)
            var.set(weight)

    def _set_normal_right_distribution(self, qid, option_count):
        """设置右偏正态分布"""
        if qid not in self.option_entries:
            return

        center = option_count * 0.7  # 偏向右侧
        std = option_count / 6.0

        for i, var in enumerate(self.option_entries[qid]):
            x = (i - center) / std
            weight = math.exp(-0.5 * x * x)
            var.set(weight)

    def _set_beta_distribution(self, qid, option_count, alpha, beta):
        """设置Beta分布"""
        if qid not in self.option_entries:
            return

        for i, var in enumerate(self.option_entries[qid]):
            x = (i + 0.5) / option_count
            # Beta分布密度函数近似
            if x > 0 and x < 1:
                weight = (x ** (alpha - 1)) * ((1 - x) ** (beta - 1))
            else:
                weight = 0.1
            var.set(weight)

    def _set_exponential_distribution(self, qid, option_count, reverse):
        """设置指数分布"""
        if qid not in self.option_entries:
            return

        rate = 2.0

        for i, var in enumerate(self.option_entries[qid]):
            if reverse:
                x = 1 - (i + 0.5) / option_count
            else:
                x = (i + 0.5) / option_count

            weight = rate * math.exp(-rate * x)
            var.set(weight)

    def _set_u_shaped_distribution(self, qid, option_count):
        """设置U型分布"""
        if qid not in self.option_entries:
            return

        for i, var in enumerate(self.option_entries[qid]):
            x = (i + 0.5) / option_count
            # U型函数
            weight = (x - 0.5) ** 2 + 0.1
            var.set(1/weight)

    def _set_likert_5_optimal(self, qid, option_count):
        """设置5点量表最优分布"""
        if qid not in self.option_entries:
            return

        if option_count != 5:
            self._set_normal_distribution(qid, option_count)
            return

        # 基于心理学研究的最优分布
        optimal_weights = [0.1, 0.2, 0.4, 0.25, 0.05]

        for i, var in enumerate(self.option_entries[qid]):
            var.set(f"{optimal_weights[i]:.3f}")

    def _set_likert_7_optimal(self, qid, option_count):
        """设置7点量表最优分布"""
        if qid not in self.option_entries:
            return

        if option_count != 7:
            self._set_normal_distribution(qid, option_count)
            return

        optimal_weights = [0.05, 0.1, 0.2, 0.3, 0.2, 0.1, 0.05]

        for i, var in enumerate(self.option_entries[qid]):
            var.set(f"{optimal_weights[i]:.3f}")

    def _set_extreme_avoidance(self, qid, option_count):
        """设置避免极端分布"""
        if qid not in self.option_entries:
            return

        for i, var in enumerate(self.option_entries[qid]):
            if i == 0 or i == option_count - 1:  # 极端选项
                weight = 0.3
            else:
                weight = 1.0
            var.set(weight)

    def _set_social_desirability(self, qid, option_count):
        """设置社会期望分布"""
        if qid not in self.option_entries:
            return

        # 假设社会期望倾向于中间和正面选项
        for i, var in enumerate(self.option_entries[qid]):
            if option_count <= 3:
                # 3选项或以下
                if i == 1:  # 中间选项
                    weight = 1.5
                else:
                    weight = 0.8
            else:
                # 多选项
                center = (option_count - 1) / 2
                distance = abs(i - center)
                weight = 1.2 - distance * 0.1
                weight = max(0.5, weight)
            var.set(weight)

    def _update_probabilities(self, qid):
        """更新概率显示"""
        try:
            if qid not in self.option_entries:
                return

            option_vars = self.option_entries[qid]
            values = []

            # 收集所有权重值
            for var in option_vars:
                try:
                    value = float(var.get())
                    values.append(value)
                except ValueError:
                    values.append(0.0)

            # 计算总权重
            total_weight = sum(max(0, v) for v in values)
            if total_weight == 0:
                total_weight = len(values)

            # 更新概率显示（暂时注释，需要时取消注释）
            # for i, var in enumerate(option_vars):
            #     try:
            #         weight = max(0, values[i])
            #         probability = weight / total_weight * 100
            #         # 这里可以更新概率标签显示，如果有的话
            #         # self.prob_labels[qid][i].config(text=f"{probability:.1f}%")
            #     except:
            #         pass

        except Exception as e:
            logging.error(f"更新概率显示失败 {qid}: {e}")

    def _copy_weight(self, qid, idx):
        """复制权重到其他选项"""
        try:
            if qid not in self.option_entries:
                return

            option_vars = self.option_entries[qid]
            if idx >= len(option_vars):
                return

            source_value = option_vars[idx].get()

            # 复制到其他所有选项
            for var in option_vars:
                var.set(source_value)

            self._update_probabilities(qid)
            messagebox.showinfo("成功", f"已复制权重 {source_value} 到所有选项")

        except Exception as e:
            logging.error(f"复制权重失败: {e}")
            messagebox.showerror("错误", f"复制权重失败: {str(e)}")

    def _normalize_weights(self, qid):
        """归一化权重"""
        try:
            if qid not in self.option_entries:
                return

            option_vars = self.option_entries[qid]
            values = []

            # 收集有效权重
            for var in option_vars:
                try:
                    value = float(var.get())
                    if value > 0:  # 只处理正权重
                        values.append(value)
                    else:
                        values.append(0.0)
                except ValueError:
                    values.append(1.0)  # 无效值设为默认值

            # 计算总权重
            total_weight = sum(values)
            if total_weight == 0:
                # 如果总权重为0，设为均匀分布
                normalized_value = 1.0 / len(option_vars)
                for var in option_vars:
                    var.set(normalized_value)
            else:
                # 归一化
                for var in option_vars:
                    try:
                        original_value = float(var.get())
                        if original_value > 0:
                            normalized_value = original_value / total_weight
                            var.set(normalized_value)
                        else:
                            var.set(0.0)
                    except ValueError:
                        var.set(0.333)  # 默认值

            self._update_probabilities(qid)
            messagebox.showinfo("成功", "权重已归一化")

        except Exception as e:
            logging.error(f"归一化权重失败 {qid}: {e}")
            messagebox.showerror("错误", f"归一化权重失败: {str(e)}")

    def _save_question_config(self, qid):
        """保存题目配置"""
        try:
            success = self._apply_question_weights(qid)
            if success:
                messagebox.showinfo("成功", f"题目 {qid} 配置已保存")
            return success

        except Exception as e:
            logging.error(f"保存题目配置失败 {qid}: {e}")
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            return False

    def _update_preview(self, qid, qtype):
        """更新预览"""
        try:
            self.preview_canvas.delete("all")
            self.summary_text.delete(1.0, tk.END)

            # 简单的预览图表
            options = self.config.get('option_texts', {}).get(qid, [])
            if options and qid in self.option_entries:
                option_vars = self.option_entries[qid]
                values = []

                for var in option_vars:
                    try:
                        values.append(float(var.get()))
                    except:
                        values.append(1.0)

                # 绘制简单条形图
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()

                if canvas_width > 1 and canvas_height > 1:
                    max_value = max(values) if values else 1
                    bar_width = (canvas_width - 40) // len(values)

                    for i, value in enumerate(values):
                        bar_height = (value / max_value) * (canvas_height - 40)
                        x = 20 + i * bar_width
                        self.preview_canvas.create_rectangle(
                            x, canvas_height - bar_height - 10,
                            x + bar_width - 5, canvas_height - 10,
                            fill=self.theme.PRIMARY
                        )

            # 配置摘要
            summary = f"题目类型: {self.question_types.get(qtype, {}).get('name', '未知')}\n"
            summary += f"选项数量: {len(options)}\n"

            if qid in self.strategy_vars:
                strategy = self.strategy_vars[qid].get()
                strategy_info = self.distribution_strategies.get(strategy, {})
                summary += f"当前策略: {strategy_info.get('name', strategy)}\n"

            self.summary_text.insert(tk.END, summary)

        except Exception as e:
            logging.error(f"更新预览失败 {qid}: {e}")

    def _update_recommendations(self, qid, qtype):
        """更新推荐"""
        try:
            self.recommendation_text.delete(1.0, tk.END)

            options = self.config.get('option_texts', {}).get(qid, [])
            option_count = len(options)

            if option_count == 0:
                return

            # 根据题型和选项数量给出推荐
            recommendations = []

            if qtype == '3':  # 单选题
                if option_count <= 3:
                    recommendations.append("建议使用均匀分布")
                else:
                    recommendations.append("建议使用正态分布，中间选项概率较高")
            elif qtype == '4':  # 多选题
                recommendations.append("建议使用随机分布或均匀分布")
            elif qtype == '5':  # 量表题
                if option_count == 5:
                    recommendations.append("建议使用5点量表最优分布")
                elif option_count == 7:
                    recommendations.append("建议使用7点量表最优分布")
                else:
                    recommendations.append("建议使用正态分布")
            elif qtype == '6':  # 矩阵题
                recommendations.append("建议使用均匀分布")
            elif qtype == '7':  # 下拉题
                recommendations.append("建议使用随机分布")

            if recommendations:
                self.recommendation_text.insert(tk.END, "\n".join(recommendations))
            else:
                self.recommendation_text.insert(tk.END, "暂无推荐策略")

        except Exception as e:
            logging.error(f"更新推荐失败 {qid}: {e}")

    def _apply_question_weights(self, question_id):
        """应用题目权重"""
        try:
            qtype = self.config.get('question_types', {}).get(question_id, '3')

            if qtype in ['1', '2']:  # 填空题
                if question_id in self.option_entries and self.option_entries[question_id]:
                    text_value = self.option_entries[question_id][0].get()
                    if qtype == '1':
                        self.config.setdefault('texts', {})[question_id] = [text_value]
                    else:
                        opts = self.config.get('option_texts', {}).get(question_id, [])
                        num_blanks = len(opts) if opts else 1
                        self.config.setdefault('multiple_texts', {})[question_id] = [[text_value]] * num_blanks

                    messagebox.showinfo("成功", f"已保存填空题{question_id}的配置")
                    return True

            else:  # 选择题型
                if question_id in self.option_entries and self.option_entries[question_id]:
                    values = []
                    for var in self.option_entries[question_id]:
                        # Get the value from DoubleVar
                        var_value = var.get()

                        # Handle both DoubleVar (float) and StringVar (string) cases
                        if isinstance(var_value, (int, float)):
                            # For DoubleVar, use the float value directly
                            value = float(var_value)
                        else:
                            # For StringVar, convert string to float
                            str_value = str(var_value).strip()
                            if str_value:
                                try:
                                    value = float(str_value)
                                except ValueError:
                                    if str_value == "-1":
                                        value = -1.0
                                    else:
                                        value = 1.0
                            else:
                                value = 1.0

                        # Only add non-zero values or special values
                        if value != 0.0 or value == -1.0:
                            values.append(value)

                    if values:
                        # 根据题型保存配置
                        config_keys = {
                            '3': 'single_prob', '4': 'multiple_prob', '5': 'scale_prob',
                            '6': 'matrix_prob', '7': 'droplist_prob', '8': 'matrix_scale_prob',
                            '11': 'reorder_prob'
                        }

                        if qtype in config_keys:
                            self.config.setdefault(config_keys[qtype], {})[question_id] = values

                messagebox.showinfo("成功", f"已保存题目{question_id}的配置")
            return True

        except Exception as e:
            logging.error(f"应用题目配置失败 {question_id}: {e}")
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            return False

    # ==================== 工具栏功能方法 ====================

    def save_all_configurations(self):
        """保存所有配置"""
        try:
            saved_count = 0
            failed_count = 0

            # 保存所有当前配置
            for qid in list(self.option_entries.keys()):
                try:
                    if self._apply_question_weights(qid):
                        saved_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logging.error(f"保存题目 {qid} 失败: {e}")
                    failed_count += 1

            if saved_count > 0:
                message = f"成功保存 {saved_count} 个题目的配置"
                if failed_count > 0:
                    message += f"，{failed_count} 个题目保存失败"
                messagebox.showinfo("保存结果", message)
            else:
                messagebox.showwarning("警告", "没有成功保存任何配置")

            return saved_count > 0

        except Exception as e:
            logging.error(f"批量保存失败: {e}")
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            return False

    def smart_configuration(self):
        """智能配置"""
        try:
            # 分析问卷结构
            summary = self.get_config_summary()
            if not summary:
                messagebox.showwarning("警告", "无法获取问卷信息")
                return

            # 根据题型自动推荐策略
            recommendations = []

            q_types = self.config.get('question_types', {})
            for qid, qtype in q_types.items():
                if qtype == '3':  # 单选题
                    recommendations.append((qid, 'uniform', '单选题适合均匀分布'))
                elif qtype == '4':  # 多选题
                    recommendations.append((qid, 'random', '多选题适合随机分布'))
                elif qtype == '5':  # 量表题
                    recommendations.append((qid, 'normal', '量表题适合正态分布'))
                elif qtype == '1' or qtype == '2':  # 填空题
                    recommendations.append((qid, 'auto', '填空题自动生成内容'))

            # 显示推荐
            if recommendations:
                rec_text = "智能配置推荐:\n\n"
                for qid, strategy, reason in recommendations:
                    rec_text += f"题目 {qid}: {strategy} - {reason}\n"

                if messagebox.askyesno("智能配置", f"{rec_text}\n\n是否应用这些推荐？"):
                    applied_count = 0
                    for qid, strategy, _ in recommendations:
                        try:
                            if strategy == 'auto':
                                self._apply_question_weights(qid)
                            else:
                                if qid in self.strategy_vars:
                                    self.strategy_vars[qid].set(strategy)
                                    qtype = q_types[qid]
                                    self._apply_strategy(qid, qtype)
                            applied_count += 1
                        except:
                            pass

                    messagebox.showinfo("成功", f"已应用 {applied_count} 个智能配置")

        except Exception as e:
            logging.error(f"智能配置失败: {e}")
            messagebox.showerror("错误", f"智能配置失败: {str(e)}")

    def advanced_batch_settings(self):
        """高级批量设置"""
        try:
            # 创建高级设置对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("高级批量设置")
            dialog.geometry("500x400")
            dialog.transient(self.root)
            dialog.grab_set()

            # 居中显示
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")

            # 标题
            ttk.Label(dialog, text="高级批量设置",
                     font=('Microsoft YaHei UI', 14, 'bold')).pack(pady=15)

            # 条件设置区域
            condition_frame = ttk.LabelFrame(dialog, text="应用条件", padding=10)
            condition_frame.pack(fill='x', padx=20, pady=10)

            # 题型选择
            ttk.Label(condition_frame, text="选择题型:").pack(anchor='w', pady=(0, 5))

            type_vars = {}
            for qtype_code, qtype_info in self.question_types.items():
                if qtype_code != '0':  # 排除指导语
                    var = tk.BooleanVar(value=True)
                    type_vars[qtype_code] = var
                    ttk.Checkbutton(condition_frame, text=qtype_info['name'],
                                   variable=var).pack(anchor='w', pady=1)

            # 策略选择
            strategy_frame = ttk.LabelFrame(dialog, text="分布策略", padding=10)
            strategy_frame.pack(fill='x', padx=20, pady=10)

            advanced_strategy_var = tk.StringVar(value='uniform')
            strategies = ['random', 'uniform', 'normal', 'beta_22', 'likert_5_optimal']

            for strategy in strategies:
                ttk.Radiobutton(strategy_frame, text=self.distribution_strategies.get(strategy, {}).get('name', strategy),
                               variable=advanced_strategy_var,
                               value=strategy).pack(anchor='w', pady=2)

            # 应用按钮
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=20)

            def apply_advanced_batch():
                try:
                    selected_strategy = advanced_strategy_var.get()
                    affected_count = 0

                    for qid, qtype_code in self.config.get("question_types", {}).items():
                        if qtype_code in type_vars and type_vars[qtype_code].get():
                            try:
                                if qid in self.strategy_vars:
                                    self.strategy_vars[qid].set(selected_strategy)
                                    self._apply_strategy(qid, qtype_code)
                                    affected_count += 1
                            except Exception as e:
                                logging.error(f"应用高级设置到题目 {qid} 失败: {e}")

                    dialog.destroy()
                    messagebox.showinfo("成功", f"高级批量设置已应用到 {affected_count} 个题目")

                except Exception as e:
                    messagebox.showerror("错误", f"高级批量设置失败: {str(e)}")

            ttk.Button(button_frame, text="应用设置", command=apply_advanced_batch).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        except Exception as e:
            logging.error(f"打开高级批量设置失败: {e}")
            messagebox.showerror("错误", f"打开高级批量设置失败: {str(e)}")

    def recommend_strategies(self):
        """策略推荐"""
        try:
            # 分析当前配置
            summary = self.get_config_summary()
            if not summary:
                messagebox.showwarning("警告", "无法分析配置")
                return

            # 生成推荐报告
            report = "策略推荐报告\n\n"

            q_types = self.config.get('question_types', {})
            type_counts = {}

            for qtype in q_types.values():
                type_name = self.question_types.get(qtype, {}).get('name', f'类型{qtype}')
                type_counts[type_name] = type_counts.get(type_name, 0) + 1

            report += "当前题型分布:\n"
            for type_name, count in type_counts.items():
                report += f"  {type_name}: {count} 题\n"

            report += "\n推荐策略:\n"

            # 根据题型给出推荐
            recommendations = {
                '单选题': '均匀分布 - 适合选项较少的单选题',
                '多选题': '随机分布 - 多选题适合随机选择',
                '量表题': '正态分布 - 基于心理学研究的分布',
                '矩阵题': '均匀分布 - 矩阵题选项较多时使用',
                '下拉题': '随机分布 - 下拉题随机选择即可',
                '排序题': '均匀分布 - 排序题保持随机性',
                '填空题': '自动填写 - 使用模板自动生成'
            }

            for type_name, recommendation in recommendations.items():
                if type_name in type_counts:
                    report += f"  {type_name}: {recommendation}\n"

            messagebox.showinfo("策略推荐", report)

        except Exception as e:
            logging.error(f"生成策略推荐失败: {e}")
            messagebox.showerror("错误", f"生成策略推荐失败: {str(e)}")

    def apply_batch_strategy(self):
        """应用批量策略"""
        try:
            strategy = self.batch_strategy_var.get()
            if not strategy:
                messagebox.showwarning("警告", "请先选择策略")
                return

            affected_count = 0
            q_types = self.config.get('question_types', {})

            for qid in self.strategy_vars.keys():
                try:
                    if qid in self.strategy_vars:
                        self.strategy_vars[qid].set(strategy)
                        qtype = q_types.get(qid, '3')
                        self._apply_strategy(qid, qtype)
                        affected_count += 1
                except Exception as e:
                    logging.error(f"应用策略到题目 {qid} 失败: {e}")

            messagebox.showinfo("成功", f"批量策略已应用到 {affected_count} 个题目")

        except Exception as e:
            logging.error(f"批量应用策略失败: {e}")
            messagebox.showerror("错误", f"批量应用策略失败: {str(e)}")

    # ==================== 辅助方法 ====================

    def get_config_summary(self):
        """获取配置摘要"""
        try:
            summary = {
                'total_questions': len(self.config.get('question_texts', {})),
                'configured_questions': 0,
                'type_distribution': {}
            }

            # 统计已配置题目
            config_keys = ['single_prob', 'multiple_prob', 'scale_prob', 'matrix_prob',
                          'droplist_prob', 'matrix_scale_prob', 'reorder_prob', 'texts', 'multiple_texts']

            configured_qids = set()
            for key in config_keys:
                configured_qids.update(self.config.get(key, {}).keys())

            summary['configured_questions'] = len(configured_qids)

            # 统计题型分布
            for qid, qtype in self.config.get('question_types', {}).items():
                type_name = self.question_types.get(qtype, {}).get('name', f'类型{qtype}')
                summary['type_distribution'][type_name] = summary['type_distribution'].get(type_name, 0) + 1

            return summary

        except Exception as e:
            logging.error(f"获取配置摘要失败: {e}")
            return None

    def validate_config(self):
        """验证配置完整性"""
        try:
            issues = []

            q_texts = self.config.get('question_texts', {})
            q_types = self.config.get('question_types', {})

            # 检查基本完整性
            if not q_texts:
                issues.append("缺少题目文本数据")

            if not q_types:
                issues.append("缺少题型映射数据")

            # 检查题型配置完整性
            for qid, qtype in q_types.items():
                if qtype not in ['0', '1', '2']:  # 非指导语和填空题需要选项配置
                    config_key_map = {
                        '3': 'single_prob', '4': 'multiple_prob', '5': 'scale_prob',
                        '6': 'matrix_prob', '7': 'droplist_prob', '8': 'matrix_scale_prob',
                        '11': 'reorder_prob'
                    }

                    if qtype in config_key_map:
                        config_key = config_key_map[qtype]
                        if qid not in self.config.get(config_key, {}):
                            type_name = self.question_types.get(qtype, {}).get('name', qtype)
                            issues.append(f"题目 {qid} ({type_name}) 缺少概率配置")

            return issues

        except Exception as e:
            logging.error(f"配置验证失败: {e}")
            return [f"验证过程出错: {str(e)}"]

    def show_config_info(self):
        """显示配置信息"""
        try:
            summary = self.get_config_summary()
            if not summary:
                messagebox.showerror("错误", "无法获取配置信息")
                return

            info_text = f"""配置信息摘要

题目总数: {summary['total_questions']}
已配置题目: {summary['configured_questions']}
配置完成率: {summary['configured_questions']/max(1,summary['total_questions'])*100:.1f}%

题型分布:"""

            for type_name, count in summary['type_distribution'].items():
                info_text += f"\n  {type_name}: {count} 题"

            # 验证问题
            issues = self.validate_config()
            if issues:
                info_text += f"\n\n配置问题 ({len(issues)} 个):"
                for issue in issues[:5]:  # 只显示前5个
                    info_text += f"\n  • {issue}"
                if len(issues) > 5:
                    info_text += f"\n  • ... 还有 {len(issues)-5} 个问题"
            else:
                info_text += "\n\n✅ 配置检查通过"

            messagebox.showinfo("配置信息", info_text)

        except Exception as e:
            messagebox.showerror("错误", f"显示配置信息失败: {str(e)}")

    # ==================== 导入导出方法 ====================

    def import_config(self):
        """导入配置"""
        from tkinter import filedialog

        filename = filedialog.askopenfilename(
            title="导入配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    imported_config = json.load(f)

                # 合并配置
                for key, value in imported_config.items():
                    if isinstance(value, dict):
                        self.config.setdefault(key, {}).update(value)
                    else:
                        self.config[key] = value

                self.refresh_interface()
                messagebox.showinfo("成功", "配置导入成功！")
            except Exception as e:
                messagebox.showerror("错误", f"导入配置失败: {str(e)}")

    def export_config(self):
        """导出配置"""
        from tkinter import filedialog

        filename = filedialog.asksaveasfilename(
            title="导出配置文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )

        if filename:
            try:
                # 收集当前配置
                export_config = {
                    "question_texts": self.config.get("question_texts", {}),
                    "question_types": self.config.get("question_types", {}),
                    "option_texts": self.config.get("option_texts", {}),
                    "single_prob": self.config.get("single_prob", {}),
                    "multiple_prob": self.config.get("multiple_prob", {}),
                    "scale_prob": self.config.get("scale_prob", {}),
                    "matrix_prob": self.config.get("matrix_prob", {}),
                    "droplist_prob": self.config.get("droplist_prob", {}),
                    "matrix_scale_prob": self.config.get("matrix_scale_prob", {}),
                    "reorder_prob": self.config.get("reorder_prob", {}),
                    "texts": self.config.get("texts", {}),
                    "multiple_texts": self.config.get("multiple_texts", {}),
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_config, f, ensure_ascii=False, indent=2)

                messagebox.showinfo("成功", "配置导出成功！")
            except Exception as e:
                messagebox.showerror("错误", f"导出配置失败: {str(e)}")

    def reset_to_defaults(self):
        """重置为默认设置"""
        if not messagebox.askyesno("确认", "确定要重置所有设置为默认值吗？"):
            return

        try:
            # 重置策略变量
            for strategy_var in self.strategy_vars.values():
                strategy_var.set('uniform')

            # 重置概率设置
            for qid, option_vars in self.option_entries.items():
                for var in option_vars:
                    var.set("1.0")

            # 清除配置中的概率设置
            prob_keys = ['single_prob', 'multiple_prob', 'scale_prob', 'matrix_prob',
                        'droplist_prob', 'matrix_scale_prob', 'reorder_prob']
            for key in prob_keys:
                if key in self.config:
                    self.config[key].clear()

            messagebox.showinfo("成功", "已重置所有设置为默认值")

        except Exception as e:
            messagebox.showerror("错误", f"重置失败: {str(e)}")

    def batch_settings(self):
        """批量设置"""
        host = self.root if self.root else self.parent
        dialog = tk.Toplevel(host)
        dialog.title("批量设置")
        dialog.geometry("400x300")
        dialog.transient(host)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        # 标题
        ttk.Label(dialog, text="批量设置选项",
                 font=('Microsoft YaHei UI', 14, 'bold')).pack(pady=15)

        # 策略选择
        strategy_frame = ttk.LabelFrame(dialog, text="分布策略", padding=10)
        strategy_frame.pack(fill='x', padx=20, pady=10)

        strategy_var = tk.StringVar(value='uniform')
        for strategy_name in ['随机分布', '均匀分布', '正态分布', '中心分布']:
            ttk.Radiobutton(strategy_frame, text=strategy_name, variable=strategy_var,
                           value=strategy_name).pack(anchor='w', pady=2)

        # 题型选择
        type_frame = ttk.LabelFrame(dialog, text="应用题型", padding=10)
        type_frame.pack(fill='x', padx=20, pady=10)

        type_vars = {}
        for qtype_code, qtype_info in self.question_types.items():
            if qtype_code != '0':  # 排除指导语
                var = tk.BooleanVar(value=True)
                type_vars[qtype_code] = var
                ttk.Checkbutton(type_frame, text=qtype_info['name'],
                               variable=var).pack(anchor='w', pady=2)

        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)

        def apply_batch():
            try:
                selected_strategy = strategy_var.get()
                affected_count = 0

                # 策略映射
                strategy_map = {
                    '随机分布': 'random',
                    '均匀分布': 'uniform',
                    '正态分布': 'normal',
                    '中心分布': 'normal'
                }

                mapped_strategy = strategy_map.get(selected_strategy, 'uniform')

                for qid, strategy_var_obj in self.strategy_vars.items():
                    qtype = self.config.get('question_types', {}).get(qid, '3')
                    if qtype in type_vars and type_vars[qtype].get():
                        strategy_var_obj.set(mapped_strategy)
                        self._apply_strategy(qid, qtype)
                        affected_count += 1

                dialog.destroy()
                messagebox.showinfo("成功", f"已批量设置 {affected_count} 个题目")

            except Exception as e:
                messagebox.showerror("错误", f"批量设置失败: {str(e)}")

        ttk.Button(button_frame, text="应用设置", command=apply_batch).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def apply_wjx2_style(self):
        """应用WJX2风格设置"""
        if not messagebox.askyesno("确认", "确定要应用WJX2风格的参数设置吗？\n这将覆盖当前配置。"):
            return

        try:
            affected_count = 0

            for qid, qtype_code in self.config.get("question_types", {}).items():
                if qtype_code == '3':  # 单选题
                    self.config.setdefault("single_prob", {})[qid] = [-1]
                    affected_count += 1
                elif qtype_code == '4':  # 多选题
                    option_count = len(self.config.get("option_texts", {}).get(qid, []))
                    if option_count > 0:
                        # WJX2风格：每个选项50%概率
                        self.config.setdefault("multiple_prob", {})[qid] = [50.0] * option_count
                        affected_count += 1
                elif qtype_code == '5':  # 量表题
                    self.config.setdefault("scale_prob", {})[qid] = [-1]
                    affected_count += 1
                elif qtype_code == '6':  # 矩阵题
                    self.config.setdefault("matrix_prob", {})[qid] = [-1]
                    affected_count += 1
                elif qtype_code == '7':  # 下拉题
                    self.config.setdefault("droplist_prob", {})[qid] = [-1]
                    affected_count += 1
                elif qtype_code == '8':  # 矩阵量表题
                    self.config.setdefault("matrix_scale_prob", {})[qid] = [-1]
                    affected_count += 1
                elif qtype_code == '11':  # 排序题
                    self.config.setdefault("reorder_prob", {})[qid] = [-1]
                    affected_count += 1
                elif qtype_code == '1':  # 填空题
                    self.config.setdefault("texts", {})[qid] = ["自动填写内容"]
                    affected_count += 1
                elif qtype_code == '2':  # 多项填空
                    option_count = len(self.config.get("option_texts", {}).get(qid, []))
                    self.config.setdefault("multiple_texts", {})[qid] = [["自动填写内容"]] * max(1, option_count)
                    affected_count += 1

            self.refresh_interface()
            messagebox.showinfo("成功", f"已按WJX2风格配置 {affected_count} 个题目")

        except Exception as e:
            messagebox.showerror("错误", f"应用WJX2风格失败：{str(e)}")

    def normalize_all_probabilities(self):
        """概率归一化"""
        if not messagebox.askyesno("确认", "确定要对所有概率进行归一化处理吗？"):
            return

        try:
            normalized_count = 0

            # 处理各种题型的概率配置
            prob_configs = [
                ('single_prob', '单选题'),
                ('scale_prob', '量表题'),
                ('matrix_prob', '矩阵题'),
                ('droplist_prob', '下拉题'),
                ('matrix_scale_prob', '矩阵量表题'),
                ('reorder_prob', '排序题')
            ]

            for config_key, type_name in prob_configs:
                for qid, probs in self.config.get(config_key, {}).items():
                    if isinstance(probs, list) and len(probs) > 1:
                        # 过滤有效数值
                        valid_probs = []
                        for p in probs:
                            try:
                                val = float(p)
                                if val >= 0:  # 排除-1等特殊值
                                    valid_probs.append(val)
                                else:
                                    valid_probs.append(p)  # 保持特殊值
                            except:
                                valid_probs.append(1.0)  # 默认值

                        # 归一化处理
                        positive_vals = [v for v in valid_probs if isinstance(v, (int, float)) and v > 0]
                        if len(positive_vals) > 1:
                            total = sum(positive_vals)
                            if total > 0:
                                factor = 1.0 / total
                                normalized = []
                                for v in valid_probs:
                                    if isinstance(v, (int, float)) and v > 0:
                                        normalized.append(v * factor)
                                    else:
                                        normalized.append(v)

                                self.config[config_key][qid] = normalized
                                normalized_count += 1

            # 特殊处理多选题（百分比制）
            for qid, probs in self.config.get("multiple_prob", {}).items():
                if isinstance(probs, list):
                    valid_probs = []
                    for p in probs:
                        try:
                            val = float(p)
                            valid_probs.append(max(0, min(100, val)))  # 限制在0-100之间
                        except:
                            valid_probs.append(50.0)  # 默认50%

                    self.config["multiple_prob"][qid] = valid_probs
                    normalized_count += 1

            self.refresh_interface()
            messagebox.showinfo("成功", f"已归一化 {normalized_count} 个题目的概率设置")

        except Exception as e:
            messagebox.showerror("错误", f"概率归一化失败：{str(e)}")

    def save_from_table(self):
        """从表格保存配置"""
        try:
            saved_count = 0
            failed_count = 0

            # 保存所有当前配置
            for qid in list(self.option_entries.keys()):
                try:
                    if self._apply_question_weights(qid):
                        saved_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logging.error(f"保存题目 {qid} 失败: {e}")
                    failed_count += 1

            if saved_count > 0:
                message = f"成功保存 {saved_count} 个题目的配置"
                if failed_count > 0:
                    message += f"，{failed_count} 个题目保存失败"
                messagebox.showinfo("保存结果", message)
            else:
                messagebox.showwarning("警告", "没有成功保存任何配置")

            return saved_count > 0

        except Exception as e:
            logging.error(f"批量保存失败: {e}")
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            return False

    # ==================== 缺失的基础方法 ====================

    def _set_random_distribution(self, qid):
        """随机分布设置"""
        if qid in self.option_entries:
            for var in self.option_entries[qid]:
                var.set("-1")

    def _set_uniform_distribution(self, qid, option_count):
        """均匀分布设置"""
        if qid not in self.option_entries:
            return

        if option_count > 0:
            value = 1.0 / option_count
            for var in self.option_entries[qid]:
                var.set(value)

    def _set_center_distribution(self, qid, option_count):
        """中心分布设置"""
        if qid not in self.option_entries:
            return

        for i, var in enumerate(self.option_entries[qid]):
            if i == option_count // 2:
                var.set("2.0")  # 中心选项
            else:
                var.set("0.5")  # 其他选项

    def _apply_spss_strategy(self, qid):
        """SPSS统计学策略应用"""
        if qid in self.option_entries:
            # 应用统计学上常用的分布
            count = len(self.option_entries[qid])
            if count == 5:  # 5点量表
                values = ["0.1", "0.2", "0.4", "0.2", "0.1"]
            elif count == 7:  # 7点量表
                values = ["0.05", "0.1", "0.2", "0.3", "0.2", "0.1", "0.05"]
            else:
                # 默认正态分布近似
                values = ["1.0"] * count

            for i, var in enumerate(self.option_entries[qid]):
                if i < len(values):
                    var.set(values[i])


# ==================== 模块级别的辅助函数 ====================

def create_wjx_question_settings(parent, config):
    """创建问卷星智能题型配置系统界面的工厂函数"""
    try:
        ui = WJXQuestionSettingsUI(parent, config)
        return ui
    except Exception as e:
        logging.error(f"创建WJX题型设置界面失败: {e}")
        return None

def get_default_config():
    """获取默认配置"""
    return {
        'question_texts': {},
        'question_types': {},
        'option_texts': {},
        'single_prob': {},
        'multiple_prob': {},
        'scale_prob': {},
        'matrix_prob': {},
        'droplist_prob': {},
        'matrix_scale_prob': {},
        'reorder_prob': {},
        'texts': {},
        'multiple_texts': {}
    }

# ==================== 主程序测试 ====================

if __name__ == "__main__":
    # 测试现代化界面
    import tkinter as tk
    from tkinter import ttk

    def test_ui():
        root = tk.Tk()
        root.title("问卷星智能题型配置系统 - 现代化重构版")
        root.geometry("1400x900")

        # 模拟配置数据
        test_config = {
            'question_texts': {
                '1': '您的性别是？',
                '2': '您的年龄段？',
                '3': '您对我们产品的满意度？',
                '4': '您希望我们在哪些方面改进？（多选）',
                '5': '请填写您的姓名',
                '6': '请评价以下服务质量',
                '7': '您的月收入水平？',
                '8': '您每周使用我们产品的时间？'
            },
            'question_types': {
                '1': '3', '2': '3', '3': '5',
                '4': '4', '5': '1', '6': '6',
                '7': '7', '8': '8'
            },
            'option_texts': {
                '1': ['男', '女'],
                '2': ['18-25岁', '26-35岁', '36-45岁', '46岁以上'],
                '3': ['非常满意', '满意', '一般', '不满意', '非常不满意'],
                '4': ['产品功能', '用户体验', '客户服务', '价格优惠', '其他'],
                '6': ['服务态度', '响应速度', '专业水平', '整体体验'],
                '7': ['3000元以下', '3000-5000元', '5000-8000元', '8000-12000元', '12000元以上'],
                '8': ['很少使用', '每周少于1小时', '每周1-3小时', '每周3-5小时', '每周超过5小时']
            }
        }

        # 创建界面
        ui = WJXQuestionSettingsUI(root, test_config)
        ui.create_question_settings_frame(root)

        root.mainloop()

    test_ui()