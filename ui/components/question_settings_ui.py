#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
题型设置界面模块 - 基于cankao.py的设计
提供完整的问卷题型配置界面，支持各种题型的概率设置
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, List, Any, Optional

class ToolTip:
    """工具提示类"""
    def __init__(self, widget, text='', delay=300, wraplength=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wraplength = wraplength
        self.tooltip = None
        self.scheduled = False
        
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<Motion>', self.motion)
    
    def enter(self, event=None):
        self.schedule()
    
    def leave(self, event=None):
        self.unschedule()
        self.hidetip()
    
    def motion(self, event=None):
        if self.scheduled:
            self.unschedule()
        self.schedule()
    
    def schedule(self):
        self.scheduled = True
        self.widget.after(self.delay, self.showtip)
    
    def unschedule(self):
        if self.scheduled:
            self.scheduled = False
    
    def showtip(self):
        if self.tooltip:
            return
        
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        wraplength=self.wraplength, font=("Arial", 9))
        label.pack()
    
    def hidetip(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class QuestionSettingsUI:
    """题型设置界面类"""
    
    def __init__(self, parent, config: Dict[str, Any]):
        self.parent = parent
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 存储各种题型的输入控件
        self.single_entries = []
        self.multi_entries = []
        self.matrix_entries = []
        self.reorder_entries = []
        self.droplist_entries = []
        self.scale_entries = []
        self.text_entries = []
        self.multiple_text_entries = []
        self.other_entries = {}
        self.min_selection_entries = []
        self.max_selection_entries = []
        
        # 创建界面
        self.create_ui()
    
    def create_ui(self):
        """创建主界面"""
        # 创建滚动框架
        self.question_canvas = tk.Canvas(self.parent)
        self.question_scrollbar = ttk.Scrollbar(self.parent, orient="vertical",
                                                command=self.question_canvas.yview)
        self.scrollable_question_frame = ttk.Frame(self.question_canvas)
        
        self.scrollable_question_frame.bind(
            "<Configure>",
            lambda e: self.question_canvas.configure(scrollregion=self.question_canvas.bbox("all"))
        )
        
        self.question_canvas.create_window((0, 0), window=self.scrollable_question_frame, anchor="nw")
        self.question_canvas.configure(yscrollcommand=self.question_scrollbar.set)
        
        self.question_scrollbar.pack(side="right", fill="y")
        self.question_canvas.pack(side="left", fill="both", expand=True)
        
        # 绑定鼠标滚轮
        self.bind_mousewheel_to_scrollbar(self.question_canvas)
        
        # 创建Notebook
        self.question_notebook = ttk.Notebook(self.scrollable_question_frame)
        self.question_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 题型配置
        question_types = [
            ('single_prob', "单选题", self.create_single_settings),
            ('multiple_prob', "多选题", self.create_multi_settings),
            ('matrix_prob', "矩阵题", self.create_matrix_settings),
            ('texts', "填空题", self.create_text_settings),
            ('multiple_texts', "多项填空", self.create_multiple_text_settings),
            ('reorder_prob', "排序题", self.create_reorder_settings),
            ('droplist_prob', "下拉框", self.create_droplist_settings),
            ('scale_prob', "量表题", self.create_scale_settings)
        ]
        
        for config_key, label_text, create_func in question_types:
            count = len(self.config.get(config_key, {}))
            frame = ttk.Frame(self.question_notebook)
            self.question_notebook.add(frame, text=f"{label_text}({count})")
            
            desc_frame = ttk.Frame(frame)
            desc_frame.pack(fill=tk.X, padx=8, pady=5)
            
            if count == 0:
                ttk.Label(desc_frame, text=f"暂无{label_text}题目", 
                          font=("Arial", 10, "italic"), foreground="gray").pack(pady=20)
            else:
                create_func(frame)
        
        # 添加提示
        tip_frame = ttk.Frame(self.scrollable_question_frame)
        tip_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(tip_frame, text="提示: 鼠标悬停在题号上可查看题目内容",
                  style='Warning.TLabel').pack(side=tk.LEFT, padx=5)
        
        # 更新滚动区域
        self.scrollable_question_frame.update_idletasks()
        self.question_canvas.configure(scrollregion=self.question_canvas.bbox("all"))
    
    def bind_mousewheel_to_scrollbar(self, canvas):
        """绑定鼠标滚轮到滚动条"""
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_mousewheel)
        canvas.bind('<Leave>', _unbind_mousewheel)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self.config
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置 - 完整同步题目信息"""
        self.logger.info("开始更新题型设置配置")
        self.config = new_config
        
        # 统计更新的题目数量
        total_questions = 0
        for key in ["single_prob", "multiple_prob", "matrix_prob", "texts", 
                   "multiple_texts", "reorder_prob", "droplist_prob", "scale_prob"]:
            count = len(self.config.get(key, {}))
            if count > 0:
                self.logger.info(f"更新 {key}: {count} 道题目")
                total_questions += count
        
        self.logger.info(f"总计更新 {total_questions} 道题目")
        
        # 重新加载界面以反映新配置
        self.reload_ui()
    
    def reload_ui(self):
        """重新加载界面 - 解析问卷后同步题型设置"""
        try:
            # 清空所有输入框列表
            self.single_entries.clear()
            self.multi_entries.clear()
            self.matrix_entries.clear()
            self.reorder_entries.clear()
            self.droplist_entries.clear()
            self.scale_entries.clear()
            self.text_entries.clear()
            self.multiple_text_entries.clear()
            self.other_entries.clear()
            self.min_selection_entries.clear()
            self.max_selection_entries.clear()
            
            # 销毁所有子控件
            for widget in self.parent.winfo_children():
                widget.destroy()
            
            # 重新创建界面
            self.create_ui()
            
            self.logger.info("题型设置界面已重新加载")
        except Exception as e:
            self.logger.error(f"重新加载界面失败: {str(e)}")

    def create_single_settings(self, frame):
        """创建单选题设置界面 - 真正的横向Excel表格布局：题目文本 | 参数设置 | 快捷按钮"""
        padx, pady = 4, 2
        
        # 说明框架
        desc_frame = ttk.LabelFrame(frame, text="单选题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(
            desc_frame,
            text="• -1表示随机；其余为小数且总和=1（如 0.3, 0.7）",
            font=("Arial", 9)
        ).pack(anchor=tk.W)
        
        # 创建滚动框架以支持大量题目
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 表格框架
        table_frame = ttk.Frame(scrollable_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 表头 - 真正的Excel风格三列
        headers = ["题目文本", "参数设置", "快捷操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=padx, pady=pady, sticky=tk.W)
        
        # 题目行 - 每题一行，横向分布，动态根据选项数量生成输入框
        for row_idx, (q_num, probs) in enumerate(self.config.get("single_prob", {}).items(), start=1):
            q_text = self.config.get("question_texts", {}).get(q_num, f"单选题 {q_num}")
            option_texts = self.config.get("option_texts", {}).get(q_num, [])
            option_count = len(option_texts) if option_texts else 1
            
            self.logger.info(f"创建单选题 {q_num}: {option_count} 个选项")
            
            # 第一列：题目文本（完整显示）
            text_container = ttk.Frame(table_frame)
            text_container.grid(row=row_idx, column=0, padx=padx, pady=pady, sticky=tk.W)
            
            # 题号 + 题目文本，横向排列
            ttk.Label(text_container, text=f"第{q_num}题:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            text_label = ttk.Label(text_container, text=q_text, width=35, anchor="w", 
                                  wraplength=250, font=("Arial", 9))
            text_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # 完整题目文本和选项的工具提示
            full_text = f"题目: {q_text}\n\n选项:\n"
            for i, opt in enumerate(option_texts):
                full_text += f"{i+1}. {opt}\n"
            ToolTip(text_label, text=full_text)
            
            # 第二列：参数设置输入框（根据实际选项数量动态生成）
            param_container = ttk.Frame(table_frame)
            param_container.grid(row=row_idx, column=1, padx=padx, pady=pady, sticky=tk.W)
            
            entry_row = []
            for opt_idx in range(option_count):
                # 获取具体的选项文本
                opt_text = option_texts[opt_idx] if opt_idx < len(option_texts) else f"选项{opt_idx + 1}"
                # 选项标签和输入框横向排列
                ttk.Label(param_container, text=f"{opt_text[:8]}:", width=8).pack(side=tk.LEFT, padx=(0, 2))
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
            
            # 第三列：快捷按钮（含预览）
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
            ttk.Button(btn_container, text="预览", width=4,
                       command=lambda q=q_num: self.preview_question(q)).pack(
                side=tk.LEFT, padx=1)
        
        # 配置滚动
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def create_multi_settings(self, frame):
        """创建多选题设置界面 - Excel表格风格，横向布局，动态生成选项"""
        padx, pady = 4, 2
        
        # 说明框架
        desc_frame = ttk.LabelFrame(frame, text="多选题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 每个选项概率为0-100，表示被选的独立概率", 
                  font=("Arial", 9)).pack(anchor=tk.W)
        
        # 创建滚动框架以支持大量题目
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 表格框架
        table_frame = ttk.Frame(scrollable_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 表头 - Excel风格
        headers = ["题目文本", "参数设置", "快捷操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=padx, pady=pady, sticky=tk.W)
        
        # 题目行 - 每题一行，横向布局，动态根据选项数量生成
        for row_idx, (q_num, config) in enumerate(self.config.get("multiple_prob", {}).items(), start=1):
            q_text = self.config.get("question_texts", {}).get(q_num, f"多选题 {q_num}")
            option_texts = self.config.get("option_texts", {}).get(q_num, [])
            option_count = len(option_texts) if option_texts else 1
            
            self.logger.info(f"创建多选题 {q_num}: {option_count} 个选项")
            
            # 第一列：题目文本（较宽，显示完整题目）
            text_frame = ttk.Frame(table_frame)
            text_frame.grid(row=row_idx, column=0, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Label(text_frame, text=f"第{q_num}题:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            preview_label = ttk.Label(text_frame, text=q_text, width=30, 
                                     anchor="w", wraplength=200, font=("Arial", 9))
            preview_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # 完整题目文本和选项的工具提示
            full_text = f"题目: {q_text}\n\n选项:\n"
            for i, opt in enumerate(option_texts):
                full_text += f"{i+1}. {opt}\n"
            ToolTip(preview_label, text=full_text)
            
            # 第二列：参数设置输入框（紧凑排列）
            param_frame = ttk.Frame(table_frame)
            param_frame.grid(row=row_idx, column=1, padx=padx, pady=pady, sticky=tk.W)
            
            # 最小和最大选择数
            ttk.Label(param_frame, text="最小:", width=4).pack(side=tk.LEFT, padx=(0, 2))
            min_entry = ttk.Spinbox(param_frame, from_=1, to=option_count, width=3)
            min_entry.set(config.get("min_selection", 1))
            min_entry.pack(side=tk.LEFT, padx=(0, 4))
            self.min_selection_entries.append(min_entry)
            
            ttk.Label(param_frame, text="最大:", width=4).pack(side=tk.LEFT, padx=(0, 2))
            max_entry = ttk.Spinbox(param_frame, from_=1, to=option_count, width=3)
            max_entry.set(config.get("max_selection", option_count))
            max_entry.pack(side=tk.LEFT, padx=(0, 6))
            self.max_selection_entries.append(max_entry)
            
            # 选项概率设置 - 根据实际选项数量动态生成
            entry_row = []
            for opt_idx in range(option_count):
                # 获取具体的选项文本
                opt_text = option_texts[opt_idx] if opt_idx < len(option_texts) else f"选项{opt_idx + 1}"
                ttk.Label(param_frame, text=f"{opt_text[:6]}:", width=7).pack(side=tk.LEFT, padx=(0, 2))
                entry = ttk.Entry(param_frame, width=5)
                
                if isinstance(config.get("prob", []), list) and opt_idx < len(config["prob"]):
                    entry.insert(0, str(config["prob"][opt_idx]))
                else:
                    entry.insert(0, "50")
                
                entry.pack(side=tk.LEFT, padx=(0, 4))
                entry_row.append(entry)
                
                # 处理"其他"选项
                if opt_idx < len(option_texts):
                    if "其他" in option_texts[opt_idx] or "other" in option_texts[opt_idx].lower():
                        other_edit = ttk.Entry(param_frame, width=10)
                        other_values = self.config.get("other_texts", {}).get(q_num, ["自定义"])
                        other_edit.insert(0, ", ".join(other_values))
                        other_edit.pack(side=tk.LEFT, padx=(6, 0))
                        self.other_entries[q_num] = other_edit
            
            self.multi_entries.append(entry_row)
            
            # 第三列：快捷按钮（含预览）
            btn_frame = ttk.Frame(table_frame)
            btn_frame.grid(row=row_idx, column=2, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Button(btn_frame, text="偏左", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("multiple", "left", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="偏右", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("multiple", "right", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="随机", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_random("multiple", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="50%", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_value("multiple", q, e, 50)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="预览", width=4,
                       command=lambda q=q_num: self.preview_question(q)).pack(
                side=tk.LEFT, padx=1)
        
        # 配置滚动
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def create_matrix_settings(self, frame):
        """创建矩阵题设置界面 - Excel表格风格，横向布局，动态生成选项"""
        padx, pady = 4, 2
        
        # 说明框架
        desc_frame = ttk.LabelFrame(frame, text="矩阵题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 输入-1为随机，正数为权重", 
                  font=("Arial", 9)).pack(anchor=tk.W)
        
        # 创建滚动框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 表格框架
        table_frame = ttk.Frame(scrollable_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 表头 - Excel风格
        headers = ["题目文本", "参数设置", "快捷操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=padx, pady=pady, sticky=tk.W)
        
        # 题目行 - 每题一行，横向布局，动态生成选项
        for row_idx, (q_num, probs) in enumerate(self.config.get("matrix_prob", {}).items(), start=1):
            q_text = self.config.get("question_texts", {}).get(q_num, f"矩阵题 {q_num}")
            option_texts = self.config.get("option_texts", {}).get(q_num, [])
            option_count = len(option_texts) if option_texts else 1
            
            self.logger.info(f"创建矩阵题 {q_num}: {option_count} 个选项")
            
            # 第一列：题目文本（较宽，显示完整题目）
            text_frame = ttk.Frame(table_frame)
            text_frame.grid(row=row_idx, column=0, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Label(text_frame, text=f"第{q_num}题:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            preview_label = ttk.Label(text_frame, text=q_text, width=30, 
                                     anchor="w", wraplength=200, font=("Arial", 9))
            preview_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # 完整题目文本和选项的工具提示
            full_text = f"题目: {q_text}\n\n选项:\n"
            for i, opt in enumerate(option_texts):
                full_text += f"{i+1}. {opt}\n"
            ToolTip(preview_label, text=full_text)
            
            # 第二列：参数设置输入框（紧凑排列）
            param_frame = ttk.Frame(table_frame)
            param_frame.grid(row=row_idx, column=1, padx=padx, pady=pady, sticky=tk.W)
            
            entry_row = []
            for opt_idx in range(option_count):
                opt_text = option_texts[opt_idx] if opt_idx < len(option_texts) else f"选项{opt_idx + 1}"
                ttk.Label(param_frame, text=f"{opt_text[:6]}:", width=7).pack(side=tk.LEFT, padx=(0, 2))
                entry = ttk.Entry(param_frame, width=5)
                
                if isinstance(probs, list) and opt_idx < len(probs):
                    entry.insert(0, str(probs[opt_idx]))
                elif probs == -1:
                    entry.insert(0, "-1")
                else:
                    entry.insert(0, "1")
                
                entry.pack(side=tk.LEFT, padx=(0, 4))
                entry_row.append(entry)
            
            self.matrix_entries.append(entry_row)
            
            # 第三列：快捷按钮（含预览）
            btn_frame = ttk.Frame(table_frame)
            btn_frame.grid(row=row_idx, column=2, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Button(btn_frame, text="偏左", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("matrix", "left", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="偏右", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("matrix", "right", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="随机", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_random("matrix", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="平均", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_average("matrix", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="预览", width=4,
                       command=lambda q=q_num: self.preview_question(q)).pack(
                side=tk.LEFT, padx=1)
        
        # 配置滚动
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def create_text_settings(self, frame):
        """创建填空题设置界面 - Excel表格风格，横向布局，滚动支持"""
        padx, pady = 4, 2
        
        # 说明框架
        desc_frame = ttk.LabelFrame(frame, text="填空题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 配置填空题的文本模板和填写策略", 
                  font=("Arial", 9)).pack(anchor=tk.W)
        
        # 创建滚动框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 表格框架
        table_frame = ttk.Frame(scrollable_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 表头 - Excel风格
        headers = ["题目文本", "参数设置", "快捷操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=padx, pady=pady, sticky=tk.W)
        
        # 题目行 - 每题一行，横向布局，显示完整题目内容
        for row_idx, (q_num, texts) in enumerate(self.config.get("texts", {}).items(), start=1):
            q_text = self.config.get("question_texts", {}).get(q_num, f"填空题 {q_num}")
            
            self.logger.info(f"创建填空题 {q_num}: {q_text[:30]}...")
            
            # 第一列：题目文本（较宽，显示完整题目）
            text_frame = ttk.Frame(table_frame)
            text_frame.grid(row=row_idx, column=0, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Label(text_frame, text=f"第{q_num}题:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            preview_label = ttk.Label(text_frame, text=q_text, width=30, 
                                     anchor="w", wraplength=200, font=("Arial", 9))
            preview_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # 添加工具提示显示完整题目
            ToolTip(preview_label, text=f"题目: {q_text}")
            
            # 第二列：参数设置输入框（文本模板）
            param_frame = ttk.Frame(table_frame)
            param_frame.grid(row=row_idx, column=1, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Label(param_frame, text="文本模板:", width=8).pack(side=tk.LEFT, padx=(0, 2))
            text_entry = ttk.Entry(param_frame, width=35)
            if isinstance(texts, list):
                text_entry.insert(0, ", ".join(texts))
            else:
                text_entry.insert(0, str(texts))
            text_entry.pack(side=tk.LEFT, padx=(0, 4))
            
            self.text_entries.append(text_entry)
            
            # 第三列：快捷按钮（含预览）
            btn_frame = ttk.Frame(table_frame)
            btn_frame.grid(row=row_idx, column=2, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Button(btn_frame, text="示例1", width=4,
                       command=lambda q=q_num, e=text_entry: self.set_text_template(q, e, "示例答案1")).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="示例2", width=4,
                       command=lambda q=q_num, e=text_entry: self.set_text_template(q, e, "示例答案2")).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="随机", width=4,
                       command=lambda q=q_num, e=text_entry: self.set_text_template(q, e, "随机文本1, 随机文本2, 随机文本3")).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="清空", width=4,
                       command=lambda q=q_num, e=text_entry: self.clear_text_template(q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="预览", width=4,
                       command=lambda q=q_num: self.preview_question(q)).pack(
                side=tk.LEFT, padx=1)
    
    def create_multiple_text_settings(self, frame):
        """创建多项填空设置界面 - Excel表格风格，横向布局"""
        padx, pady = 4, 2
        
        # 说明框架
        desc_frame = ttk.LabelFrame(frame, text="多项填空配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 配置多项填空题的文本模板", 
                  font=("Arial", 9)).pack(anchor=tk.W)
        
        # 表格框架
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 表头 - Excel风格
        headers = ["题目文本", "参数设置", "快捷操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=padx, pady=pady, sticky=tk.W)
        
        # 题目行 - 每题一行，横向布局
        for row_idx, (q_num, texts) in enumerate(self.config.get("multiple_texts", {}).items(), start=1):
            q_text = self.config.get("question_texts", {}).get(q_num, f"多项填空 {q_num}")
            
            # 第一列：题目文本（较宽，显示完整题目）
            text_frame = ttk.Frame(table_frame)
            text_frame.grid(row=row_idx, column=0, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Label(text_frame, text=f"第{q_num}题:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            preview_label = ttk.Label(text_frame, text=q_text, width=30, 
                                     anchor="w", wraplength=200, font=("Arial", 9))
            preview_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # 添加工具提示
            ToolTip(preview_label, text=q_text)
            
            # 第二列：参数设置输入框（文本模板）
            param_frame = ttk.Frame(table_frame)
            param_frame.grid(row=row_idx, column=1, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Label(param_frame, text="文本模板:", width=8).pack(side=tk.LEFT, padx=(0, 2))
            text_entry = ttk.Entry(param_frame, width=35)
            if isinstance(texts, list):
                text_entry.insert(0, ", ".join(texts))
            else:
                text_entry.insert(0, str(texts))
            text_entry.pack(side=tk.LEFT, padx=(0, 4))
            
            self.multiple_text_entries.append(text_entry)
            
            # 第三列：快捷按钮（含预览）
            btn_frame = ttk.Frame(table_frame)
            btn_frame.grid(row=row_idx, column=2, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Button(btn_frame, text="示例1", width=4,
                       command=lambda q=q_num, e=text_entry: self.set_text_template(q, e, "选项1, 选项2, 选项3")).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="示例2", width=4,
                       command=lambda q=q_num, e=text_entry: self.set_text_template(q, e, "选项A, 选项B, 选项C")).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="随机", width=4,
                       command=lambda q=q_num, e=text_entry: self.set_text_template(q, e, "随机1, 随机2, 随机3")).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="清空", width=4,
                       command=lambda q=q_num, e=text_entry: self.clear_text_template(q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="预览", width=4,
                       command=lambda q=q_num: self.preview_question(q)).pack(
                side=tk.LEFT, padx=1)
    
    def create_reorder_settings(self, frame):
        """创建排序题设置界面 - Excel表格风格，横向布局，动态生成选项"""
        padx, pady = 4, 2
        
        # 说明框架
        desc_frame = ttk.LabelFrame(frame, text="排序题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 每个位置的概率为相对权重", 
                  font=("Arial", 9)).pack(anchor=tk.W)
        
        # 创建滚动框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 表格框架
        table_frame = ttk.Frame(scrollable_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 表头 - Excel风格
        headers = ["题目文本", "参数设置", "快捷操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=padx, pady=pady, sticky=tk.W)
        
        # 题目行 - 每题一行，横向布局，动态生成位置
        for row_idx, (q_num, probs) in enumerate(self.config.get("reorder_prob", {}).items(), start=1):
            q_text = self.config.get("question_texts", {}).get(q_num, f"排序题 {q_num}")
            option_texts = self.config.get("option_texts", {}).get(q_num, [])
            option_count = len(option_texts) if option_texts else 1
            
            self.logger.info(f"创建排序题 {q_num}: {option_count} 个选项")
            
            # 第一列：题目文本（较宽，显示完整题目）
            text_frame = ttk.Frame(table_frame)
            text_frame.grid(row=row_idx, column=0, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Label(text_frame, text=f"第{q_num}题:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            preview_label = ttk.Label(text_frame, text=q_text, width=30, 
                                     anchor="w", wraplength=200, font=("Arial", 9))
            preview_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # 完整题目文本和排序选项的工具提示
            full_text = f"题目: {q_text}\n\n排序选项:\n"
            for i, opt in enumerate(option_texts):
                full_text += f"{i+1}. {opt}\n"
            ToolTip(preview_label, text=full_text)
            
            # 第二列：参数设置输入框（紧凑排列）
            param_frame = ttk.Frame(table_frame)
            param_frame.grid(row=row_idx, column=1, padx=padx, pady=pady, sticky=tk.W)
            
            entry_row = []
            for pos_idx in range(option_count):
                # 显示实际选项名称
                opt_text = option_texts[pos_idx] if pos_idx < len(option_texts) else f"选项{pos_idx + 1}"
                ttk.Label(param_frame, text=f"{opt_text[:6]}:", width=7).pack(side=tk.LEFT, padx=(0, 2))
                entry = ttk.Entry(param_frame, width=5)
                
                if isinstance(probs, list) and pos_idx < len(probs):
                    entry.insert(0, str(probs[pos_idx]))
                else:
                    entry.insert(0, f"{1 / option_count:.2f}")
                
                entry.pack(side=tk.LEFT, padx=(0, 4))
                entry_row.append(entry)
            
            self.reorder_entries.append(entry_row)
            
            # 第三列：快捷按钮（含预览）
            btn_frame = ttk.Frame(table_frame)
            btn_frame.grid(row=row_idx, column=2, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Button(btn_frame, text="偏前", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("reorder", "left", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="偏后", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("reorder", "right", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="随机", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_random("reorder", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="平均", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_average("reorder", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="预览", width=4,
                       command=lambda q=q_num: self.preview_question(q)).pack(
                side=tk.LEFT, padx=1)
        
        # 配置滚动
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def create_droplist_settings(self, frame):
        """创建下拉框设置界面 - Excel表格风格，横向布局，动态生成选项"""
        padx, pady = 4, 2
        
        # 说明框架
        desc_frame = ttk.LabelFrame(frame, text="下拉框配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 配置下拉框选项的选择概率", 
                  font=("Arial", 9)).pack(anchor=tk.W)
        
        # 创建滚动框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 表格框架
        table_frame = ttk.Frame(scrollable_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 表头 - Excel风格
        headers = ["题目文本", "参数设置", "快捷操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=padx, pady=pady, sticky=tk.W)
        
        # 题目行 - 每题一行，横向布局，动态生成选项
        for row_idx, (q_num, probs) in enumerate(self.config.get("droplist_prob", {}).items(), start=1):
            q_text = self.config.get("question_texts", {}).get(q_num, f"下拉框 {q_num}")
            option_texts = self.config.get("option_texts", {}).get(q_num, [])
            option_count = len(option_texts) if option_texts else 1
            
            self.logger.info(f"创建下拉框 {q_num}: {option_count} 个选项")
            
            # 第一列：题目文本（较宽，显示完整题目）
            text_frame = ttk.Frame(table_frame)
            text_frame.grid(row=row_idx, column=0, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Label(text_frame, text=f"第{q_num}题:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            preview_label = ttk.Label(text_frame, text=q_text, width=30, 
                                     anchor="w", wraplength=200, font=("Arial", 9))
            preview_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # 完整题目文本和下拉选项的工具提示
            full_text = f"题目: {q_text}\n\n下拉选项:\n"
            for i, opt in enumerate(option_texts):
                full_text += f"{i+1}. {opt}\n"
            ToolTip(preview_label, text=full_text)
            
            # 第二列：参数设置输入框（紧凑排列）
            param_frame = ttk.Frame(table_frame)
            param_frame.grid(row=row_idx, column=1, padx=padx, pady=pady, sticky=tk.W)
            
            entry_row = []
            for opt_idx in range(option_count):
                opt_text = option_texts[opt_idx] if opt_idx < len(option_texts) else f"选项{opt_idx + 1}"
                ttk.Label(param_frame, text=f"{opt_text[:6]}:", width=7).pack(side=tk.LEFT, padx=(0, 2))
                entry = ttk.Entry(param_frame, width=5)
                
                if isinstance(probs, list) and opt_idx < len(probs):
                    entry.insert(0, str(probs[opt_idx]))
                elif probs == -1:
                    entry.insert(0, "-1")
                else:
                    entry.insert(0, "1")
                
                entry.pack(side=tk.LEFT, padx=(0, 4))
                entry_row.append(entry)
            
            self.droplist_entries.append(entry_row)
            
            # 第三列：快捷按钮（含预览）
            btn_frame = ttk.Frame(table_frame)
            btn_frame.grid(row=row_idx, column=2, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Button(btn_frame, text="偏左", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("droplist", "left", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="偏右", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("droplist", "right", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="随机", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_random("droplist", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="平均", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_average("droplist", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="预览", width=4,
                       command=lambda q=q_num: self.preview_question(q)).pack(
                side=tk.LEFT, padx=1)
        
        # 配置滚动
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def create_scale_settings(self, frame):
        """创建量表题设置界面 - Excel表格风格，横向布局，动态生成选项"""
        padx, pady = 4, 2
        
        # 说明框架
        desc_frame = ttk.LabelFrame(frame, text="量表题配置说明")
        desc_frame.pack(fill=tk.X, padx=padx, pady=pady)
        ttk.Label(desc_frame, text="• 配置量表题的选择概率", 
                  font=("Arial", 9)).pack(anchor=tk.W)
        
        # 创建滚动框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 表格框架
        table_frame = ttk.Frame(scrollable_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 表头 - Excel风格
        headers = ["题目文本", "参数设置", "快捷操作"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=padx, pady=pady, sticky=tk.W)
        
        # 题目行 - 每题一行，横向布局，动态生成选项
        for row_idx, (q_num, probs) in enumerate(self.config.get("scale_prob", {}).items(), start=1):
            q_text = self.config.get("question_texts", {}).get(q_num, f"量表题 {q_num}")
            option_texts = self.config.get("option_texts", {}).get(q_num, [])
            option_count = len(option_texts) if option_texts else 1
            
            self.logger.info(f"创建量表题 {q_num}: {option_count} 个选项")
            
            # 第一列：题目文本（较宽，显示完整题目）
            text_frame = ttk.Frame(table_frame)
            text_frame.grid(row=row_idx, column=0, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Label(text_frame, text=f"第{q_num}题:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            preview_label = ttk.Label(text_frame, text=q_text, width=30, 
                                     anchor="w", wraplength=200, font=("Arial", 9))
            preview_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # 完整题目文本和量表选项的工具提示
            full_text = f"题目: {q_text}\n\n量表选项:\n"
            for i, opt in enumerate(option_texts):
                full_text += f"{i+1}. {opt}\n"
            ToolTip(preview_label, text=full_text)
            
            # 第二列：参数设置输入框（紧凑排列）
            param_frame = ttk.Frame(table_frame)
            param_frame.grid(row=row_idx, column=1, padx=padx, pady=pady, sticky=tk.W)
            
            entry_row = []
            for opt_idx in range(option_count):
                opt_text = option_texts[opt_idx] if opt_idx < len(option_texts) else f"选项{opt_idx + 1}"
                ttk.Label(param_frame, text=f"{opt_text[:6]}:", width=7).pack(side=tk.LEFT, padx=(0, 2))
                entry = ttk.Entry(param_frame, width=5)
                
                if isinstance(probs, list) and opt_idx < len(probs):
                    entry.insert(0, str(probs[opt_idx]))
                elif probs == -1:
                    entry.insert(0, "-1")
                else:
                    entry.insert(0, "1")
                
                entry.pack(side=tk.LEFT, padx=(0, 4))
                entry_row.append(entry)
            
            self.scale_entries.append(entry_row)
            
            # 第三列：快捷按钮（含预览）
            btn_frame = ttk.Frame(table_frame)
            btn_frame.grid(row=row_idx, column=2, padx=padx, pady=pady, sticky=tk.W)
            
            ttk.Button(btn_frame, text="偏左", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("scale", "left", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="偏右", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_bias("scale", "right", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="随机", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_random("scale", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="平均", width=4,
                       command=lambda q=q_num, e=entry_row: self.set_question_average("scale", q, e)).pack(
                side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="预览", width=4,
                       command=lambda q=q_num: self.preview_question(q)).pack(
                side=tk.LEFT, padx=1)
        
        # 配置滚动
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def set_question_bias(self, q_type, direction, q_num, entries):
        """为单个题目设置偏左或偏右分布"""
        self.logger.info(f"开始为第{q_num}题({q_type})设置{direction}偏置，共{len(entries)}个选项")
        
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
            self.logger.debug(f"  选项{i+1}设置为: {prob_value}")
        # 单选题保证和为1（考虑四舍五入矫正）
        if q_type == "single" and entries:
            vals = []
            for e in entries:
                try:
                    v = float(str(e.get()).replace('%','').strip())
                except Exception:
                    v = 0.0
                # 单选输入若>1视为百分比
                v = v/100.0 if v > 1.0 else v
                vals.append(max(0.0, v))
            s = sum(vals)
            if s <= 0:
                vals = [1.0/len(entries)]*len(entries)
            else:
                vals = [v/s for v in vals]
            # 矫正最后一个确保精确为1
            rounded = [round(v, 2) for v in vals]
            diff = round(1.0 - sum(rounded), 2)
            if rounded:
                rounded[-1] = round(rounded[-1] + diff, 2)
            for e, v in zip(entries, rounded):
                e.delete(0, tk.END)
                e.insert(0, f"{v:.2f}")
        
        self.logger.info(f"第{q_num}题已成功设置为{direction}偏置")
    
    def set_question_random(self, q_type, q_num, entries):
        """为单个题目设置随机选择"""
        self.logger.info(f"开始为第{q_num}题({q_type})设置随机选择，共{len(entries)}个选项")
        
        for i, entry in enumerate(entries):
            entry.delete(0, tk.END)
            entry.insert(0, "-1")
            self.logger.debug(f"  选项{i+1}设置为随机(-1)")
        
        self.logger.info(f"第{q_num}题已成功设置为随机选择")
    
    def set_question_average(self, q_type, q_num, entries):
        """为单个题目设置平均概率"""
        option_count = len(entries)
        if option_count == 0:
            self.logger.warning(f"第{q_num}题没有选项，无法设置平均概率")
            return
        
        self.logger.info(f"开始为第{q_num}题({q_type})设置平均概率，共{option_count}个选项")
        
        avg_prob = 1.0 / option_count
        
        for i, entry in enumerate(entries):
            entry.delete(0, tk.END)
            if q_type == "multiple":
                prob_value = str(int(avg_prob * 100))
                entry.insert(0, prob_value)
            else:
                prob_value = f"{avg_prob:.2f}"
                entry.insert(0, prob_value)
            self.logger.debug(f"  选项{i+1}设置为: {prob_value}")
        # 单选题矫正最后一项保证总和=1
        if q_type != "multiple" and entries:
            try:
                vals = [float(e.get()) for e in entries]
                rounded = [round(v, 2) for v in vals]
                diff = round(1.0 - sum(rounded), 2)
                rounded[-1] = round(rounded[-1] + diff, 2)
                for e, v in zip(entries, rounded):
                    e.delete(0, tk.END)
                    e.insert(0, f"{v:.2f}")
            except Exception:
                pass
        
        self.logger.info(f"第{q_num}题已成功设置为平均概率")
    
    def set_question_value(self, q_type, q_num, entries, value):
        """为单个题目设置指定值（多用于多选题）"""
        self.logger.info(f"开始为第{q_num}题({q_type})设置指定值{value}，共{len(entries)}个选项")
        
        for i, entry in enumerate(entries):
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
            self.logger.debug(f"  选项{i+1}设置为: {value}")
        
        self.logger.info(f"第{q_num}题已成功设置为{value}%概率")
    
    def set_text_template(self, q_num, entry, template):
        """为填空题设置文本模板"""
        self.logger.info(f"为第{q_num}题设置文本模板: {template[:50]}...")
        entry.delete(0, tk.END)
        entry.insert(0, template)
        self.logger.info(f"第{q_num}题文本模板设置完成")
    
    def clear_text_template(self, q_num, entry):
        """清空填空题文本模板"""
        self.logger.info(f"清空第{q_num}题文本模板")
        entry.delete(0, tk.END)
        self.logger.info(f"第{q_num}题文本模板已清空")
    
    def save_settings_to_config(self):
        """保存界面设置到配置中 - 确保UI更改同步回配置"""
        self.logger.info("开始保存题型设置到配置文件")
        try:
            # 保存单选题设置（小数且总和=1）
            if hasattr(self, 'single_entries') and self.single_entries:
                for idx, (q_num, _) in enumerate(self.config.get("single_prob", {}).items()):
                    if idx < len(self.single_entries):
                        entry_row = self.single_entries[idx]
                        values = []
                        for entry in entry_row:
                            try:
                                val = entry.get().strip()
                                if val == "-1":
                                    values = -1
                                    break
                                raw = val.replace('%','').strip()
                                f = float(raw)
                                # 单选：输入>1视为百分比
                                f = f/100.0 if f > 1.0 else f
                                values.append(max(0.0, f))
                            except ValueError:
                                values.append(0.0)
                        if values == -1:
                            self.config["single_prob"][q_num] = -1
                        else:
                            s = sum(values)
                            if s <= 0:
                                norm = [1.0/len(values)]*len(values)
                            else:
                                norm = [v/s for v in values]
                            # 保留两位并矫正合计1
                            rounded = [round(v, 2) for v in norm]
                            diff = round(1.0 - sum(rounded), 2)
                            if rounded:
                                rounded[-1] = round(rounded[-1] + diff, 2)
                            self.config["single_prob"][q_num] = rounded
            
            # 保存多选题设置
            if hasattr(self, 'multi_entries') and self.multi_entries:
                for idx, (q_num, _) in enumerate(self.config.get("multiple_prob", {}).items()):
                    if idx < len(self.multi_entries):
                        entry_row = self.multi_entries[idx]
                        values = []
                        for entry in entry_row:
                            try:
                                values.append(int(entry.get().strip()))
                            except ValueError:
                                values.append(50)
                        if "prob" in self.config["multiple_prob"][q_num]:
                            self.config["multiple_prob"][q_num]["prob"] = values
                        
                        # 保存最小/最大选择数
                        if idx < len(self.min_selection_entries):
                            try:
                                min_val = int(self.min_selection_entries[idx].get())
                                self.config["multiple_prob"][q_num]["min_selection"] = min_val
                            except ValueError:
                                pass
                        
                        if idx < len(self.max_selection_entries):
                            try:
                                max_val = int(self.max_selection_entries[idx].get())
                                self.config["multiple_prob"][q_num]["max_selection"] = max_val
                            except ValueError:
                                pass
            
            # 保存矩阵题设置
            if hasattr(self, 'matrix_entries') and self.matrix_entries:
                for idx, (q_num, _) in enumerate(self.config.get("matrix_prob", {}).items()):
                    if idx < len(self.matrix_entries):
                        entry_row = self.matrix_entries[idx]
                        values = []
                        for entry in entry_row:
                            try:
                                val = entry.get().strip()
                                if val == "-1":
                                    values = -1
                                    break
                                values.append(float(val) if '.' in val else int(val))
                            except ValueError:
                                values.append(1)
                        self.config["matrix_prob"][q_num] = values if values != -1 else -1
            
            # 保存填空题设置
            if hasattr(self, 'text_entries') and self.text_entries:
                for idx, (q_num, _) in enumerate(self.config.get("texts", {}).items()):
                    if idx < len(self.text_entries):
                        text_value = self.text_entries[idx].get().strip()
                        if text_value:
                            self.config["texts"][q_num] = text_value.split(", ")
            
            # 保存多项填空设置
            if hasattr(self, 'multiple_text_entries') and self.multiple_text_entries:
                for idx, (q_num, _) in enumerate(self.config.get("multiple_texts", {}).items()):
                    if idx < len(self.multiple_text_entries):
                        text_value = self.multiple_text_entries[idx].get().strip()
                        if text_value:
                            self.config["multiple_texts"][q_num] = text_value.split(", ")
            
            # 保存排序题设置
            if hasattr(self, 'reorder_entries') and self.reorder_entries:
                for idx, (q_num, _) in enumerate(self.config.get("reorder_prob", {}).items()):
                    if idx < len(self.reorder_entries):
                        entry_row = self.reorder_entries[idx]
                        values = []
                        for entry in entry_row:
                            try:
                                values.append(float(entry.get().strip()))
                            except ValueError:
                                values.append(0.25)
                        self.config["reorder_prob"][q_num] = values
            
            # 保存下拉框设置
            if hasattr(self, 'droplist_entries') and self.droplist_entries:
                for idx, (q_num, _) in enumerate(self.config.get("droplist_prob", {}).items()):
                    if idx < len(self.droplist_entries):
                        entry_row = self.droplist_entries[idx]
                        values = []
                        for entry in entry_row:
                            try:
                                val = entry.get().strip()
                                if val == "-1":
                                    values = -1
                                    break
                                values.append(float(val) if '.' in val else int(val))
                            except ValueError:
                                values.append(1)
                        self.config["droplist_prob"][q_num] = values if values != -1 else -1
            
            # 保存量表题设置
            if hasattr(self, 'scale_entries') and self.scale_entries:
                for idx, (q_num, _) in enumerate(self.config.get("scale_prob", {}).items()):
                    if idx < len(self.scale_entries):
                        entry_row = self.scale_entries[idx]
                        values = []
                        for entry in entry_row:
                            try:
                                val = entry.get().strip()
                                if val == "-1":
                                    values = -1
                                    break
                                values.append(float(val) if '.' in val else int(val))
                            except ValueError:
                                values.append(1)
                        self.config["scale_prob"][q_num] = values if values != -1 else -1
            
            # 保存其他选项文本
            if hasattr(self, 'other_entries') and self.other_entries:
                for q_num, entry in self.other_entries.items():
                    other_text = entry.get().strip()
                    if other_text:
                        self.config.setdefault("other_texts", {})[q_num] = other_text.split(", ")
            
            self.logger.info("题型设置已保存到配置")
            return True
            
        except Exception as e:
            self.logger.error(f"保存设置失败: {str(e)}")
            return False

    def preview_question(self, q_num: str):
        """弹窗预览指定题号的题目文本与选项"""
        try:
            q_text = self.config.get("question_texts", {}).get(q_num, f"题目 {q_num}")
            options = self.config.get("option_texts", {}).get(q_num, [])
            preview = f"题号: {q_num}\n\n题目: {q_text}\n\n选项:\n"
            if options:
                for i, opt in enumerate(options, 1):
                    preview += f"{i}. {opt}\n"
            else:
                preview += "(无选项/非选项题)\n"
            messagebox.showinfo("题目预览", preview)
        except Exception as e:
            self.logger.error(f"预览题目失败: {e}")

    def sync_with_main_system(self, main_app):
        """与主系统同步 - 解析问卷后自动更新界面"""
        try:
            self.logger.info("开始与主系统同步题型设置")
            
            # 获取主系统的配置
            if hasattr(main_app, 'config'):
                new_config = main_app.config
                self.logger.info(f"从主系统获取配置，包含 {len(new_config.get('question_texts', {}))} 道题目")
                
                # 更新配置并重新加载界面
                self.update_config(new_config)
                
                self.logger.info("题型设置界面已与主系统同步完成")
                return True
            else:
                self.logger.warning("主系统未提供配置信息")
                return False
                
        except Exception as e:
            self.logger.error(f"与主系统同步失败: {str(e)}")
            return False

    def get_statistics(self):
        """获取当前题型统计信息"""
        stats = {}
        for key in ["single_prob", "multiple_prob", "matrix_prob", "texts", 
                   "multiple_texts", "reorder_prob", "droplist_prob", "scale_prob"]:
            count = len(self.config.get(key, {}))
            if count > 0:
                stats[key] = count
        
        total = sum(stats.values())
        self.logger.info(f"当前题型统计: 总计{total}题，详情={stats}")
        return stats, total
