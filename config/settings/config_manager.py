#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版配置管理模块 - 专门处理问卷星系统的各种配置参数
支持矩阵量表题、题型设置、AI配置等复杂配置管理
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class EnhancedConfigManager:
    """增强版配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        self.config = self._load_default_config()
        self.load_config()
        
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            # 基础配置
            "url": "https://www.wjx.cn/vm/OaRP2BF.aspx",
            "target_num": 100,
            "min_duration": 1,
            "max_duration": 20,
            "weixin_ratio": 0.5,
            
            # 延迟配置
            "min_delay": 1,
            "max_delay": 2,
            "submit_delay": 1,
            "page_load_delay": 2,
            "per_question_delay": (0.5, 1),
            "per_page_delay": (2.0, 6.0),
            
            # 提交间隔配置
            "min_submit_gap": 5,
            "max_submit_gap": 15,
            "batch_size": 5,
            "batch_pause": 15,
            "enable_smart_gap": True,
            
            # 浏览器配置
            "headless": False,
            "num_threads": 4,
            "use_ip": False,
            "ip_api": "https://service.ipzan.com/core-extract?num=1&minute=1&pool=quality&secret=YOUR_SECRET",
            "ip_change_mode": "per_submit",
            "ip_change_batch": 5,
            
            # 题型概率配置
            "single_prob": {
                "1": -1,  # -1表示随机选择
                "2": [0.3, 0.7],
                "3": [0.2, 0.2, 0.6]
            },
            "multiple_prob": {
                "4": {
                    "prob": [0.4, 0.3, 0.3],
                    "min_selection": 1,
                    "max_selection": 2
                },
                "5": {
                    "prob": [0.5, 0.5, 0.5, 0.5],
                    "min_selection": 2,
                    "max_selection": 3
                }
            },
            
            # 矩阵量表题配置
            "matrix_config": {
                "fill_strategy": "random",  # random, average, bias, pattern
                "bias_direction": "center",  # left, center, right
                "bias_strength": 0.3,
                "pattern_type": "normal",  # normal, extreme, conservative
                "row_strategies": {},
                "column_weights": {},
                "scale_config": {
                    "likert_bias": "center",
                    "numeric_range": (1, 5),
                    "semantic_pairs": []
                }
            },
            
            # 文本题配置
            "text_config": {
                "templates": [
                    "这是一个很好的问题，我认为...",
                    "根据我的经验，我觉得...",
                    "从专业角度来看，这个问题...",
                    "个人认为这个情况...",
                    "基于实际情况分析..."
                ],
                "min_length": 10,
                "max_length": 200,
                "use_ai": False,
                "ai_prompts": []
            },
            
            # AI配置
            "ai_config": {
                "enabled": False,
                "api_key": "",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 150,
                "prompt_templates": {
                    "text": "请根据以下问题生成一个自然、真实的回答：{question}",
                    "matrix": "请为以下矩阵题选择一个合适的评分：{question}，选项：{options}",
                    "multiple": "请为以下多选题选择合适的选项：{question}，选项：{options}"
                }
            },
            
            # 验证配置
            "validation_config": {
                "check_required": True,
                "validate_answers": True,
                "skip_invalid": False,
                "retry_failed": 3
            },
            
            # 日志配置
            "logging_config": {
                "level": "INFO",
                "file_enabled": True,
                "console_enabled": True,
                "max_file_size": 10 * 1024 * 1024,  # 10MB
                "backup_count": 5
            },
            
            # 界面配置
            "ui_config": {
                "theme": "default",
                "font_family": "Microsoft YaHei",
                "font_size": 10,
                "window_size": "1200x800",
                "auto_save": True,
                "auto_save_interval": 300  # 5分钟
            },
            
            # 其他文本配置
            "other_texts": {
                "4": ["自定义内容A", "自定义内容B", "自定义内容C"],
                "5": ["随便写点", "哈哈哈", "其他情况"]
            },
            
            # 路径配置
            "paths": [],
            "path_priority": []
        }
    
    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并配置，保留默认值
                    self._merge_config(self.config, loaded_config)
                self.logger.info(f"配置加载成功: {self.config_file}")
                return True
            else:
                self.logger.info("配置文件不存在，使用默认配置")
                return False
        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            return False
    
    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_file) if os.path.dirname(self.config_file) else '.', exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"配置保存成功: {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"配置保存失败: {e}")
            return False
    
    def _merge_config(self, default_config: Dict[str, Any], loaded_config: Dict[str, Any]):
        """合并配置，保留默认值"""
        for key, value in loaded_config.items():
            if key in default_config:
                if isinstance(value, dict) and isinstance(default_config[key], dict):
                    self._merge_config(default_config[key], value)
                else:
                    default_config[key] = value
            else:
                default_config[key] = value
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        try:
            keys = key.split('.')
            value = self.config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_config(self, key: str, value: Any) -> bool:
        """设置配置值"""
        try:
            keys = key.split('.')
            config = self.config
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value
            return True
        except Exception as e:
            self.logger.error(f"设置配置失败: {e}")
            return False
    
    def get_matrix_config(self, question_id: str) -> Dict[str, Any]:
        """获取矩阵题配置"""
        matrix_config = self.config.get('matrix_config', {}).copy()
        
        # 获取特定题目的配置
        row_strategies = matrix_config.get('row_strategies', {})
        if question_id in row_strategies:
            matrix_config['row_strategies'] = {question_id: row_strategies[question_id]}
        
        return matrix_config
    
    def set_matrix_config(self, question_id: str, config: Dict[str, Any]) -> bool:
        """设置矩阵题配置"""
        try:
            if 'matrix_config' not in self.config:
                self.config['matrix_config'] = {}
            
            # 更新行策略
            if 'row_strategies' not in self.config['matrix_config']:
                self.config['matrix_config']['row_strategies'] = {}
            
            self.config['matrix_config']['row_strategies'][question_id] = config.get('row_strategies', {})
            
            # 更新其他配置
            for key, value in config.items():
                if key != 'row_strategies':
                    self.config['matrix_config'][key] = value
            
            return True
        except Exception as e:
            self.logger.error(f"设置矩阵配置失败: {e}")
            return False
    
    def get_question_config(self, question_id: str, question_type: str) -> Dict[str, Any]:
        """获取题目配置"""
        config = {}
        
        if question_type == 'matrix':
            config = self.get_matrix_config(question_id)
        elif question_type == 'single':
            config = {
                'probabilities': self.config.get('single_prob', {}).get(question_id, -1),
                'strategy': 'random'
            }
        elif question_type == 'multiple':
            config = self.config.get('multiple_prob', {}).get(question_id, {
                'prob': [0.5] * 4,
                'min_selection': 1,
                'max_selection': 2
            })
        elif question_type == 'text':
            config = self.config.get('text_config', {})
        
        return config
    
    def set_question_config(self, question_id: str, question_type: str, config: Dict[str, Any]) -> bool:
        """设置题目配置"""
        try:
            if question_type == 'matrix':
                return self.set_matrix_config(question_id, config)
            elif question_type == 'single':
                if 'single_prob' not in self.config:
                    self.config['single_prob'] = {}
                self.config['single_prob'][question_id] = config.get('probabilities', -1)
            elif question_type == 'multiple':
                if 'multiple_prob' not in self.config:
                    self.config['multiple_prob'] = {}
                self.config['multiple_prob'][question_id] = config
            elif question_type == 'text':
                self.config['text_config'] = config
            
            return True
        except Exception as e:
            self.logger.error(f"设置题目配置失败: {e}")
            return False
    
    def export_config(self, file_path: str) -> bool:
        """导出配置"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self.logger.info(f"配置导出成功: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"配置导出失败: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 合并配置
            self._merge_config(self.config, imported_config)
            self.logger.info(f"配置导入成功: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"配置导入失败: {e}")
            return False
    
    def reset_config(self) -> bool:
        """重置配置"""
        try:
            self.config = self._load_default_config()
            self.logger.info("配置已重置为默认值")
            return True
        except Exception as e:
            self.logger.error(f"配置重置失败: {e}")
            return False
    
    def validate_config(self) -> List[str]:
        """验证配置"""
        errors = []
        
        # 验证基础配置
        if not self.config.get('url'):
            errors.append("URL不能为空")
        
        if self.config.get('target_num', 0) <= 0:
            errors.append("目标数量必须大于0")
        
        if self.config.get('min_delay', 0) < 0:
            errors.append("最小延迟不能为负数")
        
        if self.config.get('max_delay', 0) < self.config.get('min_delay', 0):
            errors.append("最大延迟不能小于最小延迟")
        
        # 验证AI配置
        ai_config = self.config.get('ai_config', {})
        if ai_config.get('enabled', False) and not ai_config.get('api_key'):
            errors.append("启用AI功能时必须提供API密钥")
        
        # 验证矩阵配置
        matrix_config = self.config.get('matrix_config', {})
        bias_strength = matrix_config.get('bias_strength', 0.3)
        if not (0 <= bias_strength <= 1):
            errors.append("矩阵偏置强度必须在0-1之间")
        
        return errors

class ConfigUI:
    """配置界面"""
    
    def __init__(self, parent, config_manager: EnhancedConfigManager):
        self.parent = parent
        self.config_manager = config_manager
        self.create_ui()
    
    def create_ui(self):
        """创建配置界面"""
        # 创建主框架
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建选项卡
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 基础配置选项卡
        self.basic_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.basic_frame, text="基础配置")
        self.create_basic_config()
        
        # 矩阵配置选项卡
        self.matrix_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.matrix_frame, text="矩阵量表配置")
        self.create_matrix_config()
        
        # AI配置选项卡
        self.ai_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ai_frame, text="AI配置")
        self.create_ai_config()
        
        # 高级配置选项卡
        self.advanced_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.advanced_frame, text="高级配置")
        self.create_advanced_config()
        
        # 按钮框架
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 按钮
        ttk.Button(self.button_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="加载配置", command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="重置配置", command=self.reset_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="导出配置", command=self.export_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="导入配置", command=self.import_config).pack(side=tk.LEFT, padx=5)
    
    def create_basic_config(self):
        """创建基础配置界面"""
        # URL配置
        ttk.Label(self.basic_frame, text="问卷URL:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.url_var = tk.StringVar(value=self.config_manager.get_config('url'))
        ttk.Entry(self.basic_frame, textvariable=self.url_var, width=50).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 目标数量
        ttk.Label(self.basic_frame, text="目标数量:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.target_num_var = tk.IntVar(value=self.config_manager.get_config('target_num'))
        ttk.Entry(self.basic_frame, textvariable=self.target_num_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 延迟配置
        ttk.Label(self.basic_frame, text="最小延迟(秒):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.min_delay_var = tk.DoubleVar(value=self.config_manager.get_config('min_delay'))
        ttk.Entry(self.basic_frame, textvariable=self.min_delay_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(self.basic_frame, text="最大延迟(秒):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.max_delay_var = tk.DoubleVar(value=self.config_manager.get_config('max_delay'))
        ttk.Entry(self.basic_frame, textvariable=self.max_delay_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 线程数
        ttk.Label(self.basic_frame, text="线程数:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.threads_var = tk.IntVar(value=self.config_manager.get_config('num_threads'))
        ttk.Entry(self.basic_frame, textvariable=self.threads_var, width=10).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
    
    def create_matrix_config(self):
        """创建矩阵配置界面"""
        # 填充策略
        ttk.Label(self.matrix_frame, text="填充策略:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.matrix_strategy_var = tk.StringVar(value=self.config_manager.get_config('matrix_config.fill_strategy'))
        strategy_combo = ttk.Combobox(self.matrix_frame, textvariable=self.matrix_strategy_var, 
                                    values=['random', 'average', 'bias', 'pattern'])
        strategy_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 偏置方向
        ttk.Label(self.matrix_frame, text="偏置方向:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.bias_direction_var = tk.StringVar(value=self.config_manager.get_config('matrix_config.bias_direction'))
        bias_combo = ttk.Combobox(self.matrix_frame, textvariable=self.bias_direction_var,
                                values=['left', 'center', 'right'])
        bias_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 偏置强度
        ttk.Label(self.matrix_frame, text="偏置强度:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.bias_strength_var = tk.DoubleVar(value=self.config_manager.get_config('matrix_config.bias_strength'))
        ttk.Entry(self.matrix_frame, textvariable=self.bias_strength_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 模式类型
        ttk.Label(self.matrix_frame, text="模式类型:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.pattern_type_var = tk.StringVar(value=self.config_manager.get_config('matrix_config.pattern_type'))
        pattern_combo = ttk.Combobox(self.matrix_frame, textvariable=self.pattern_type_var,
                                   values=['normal', 'extreme', 'conservative'])
        pattern_combo.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
    
    def create_ai_config(self):
        """创建AI配置界面"""
        # 启用AI
        self.ai_enabled_var = tk.BooleanVar(value=self.config_manager.get_config('ai_config.enabled'))
        ttk.Checkbutton(self.ai_frame, text="启用AI功能", variable=self.ai_enabled_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # API密钥
        ttk.Label(self.ai_frame, text="API密钥:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.api_key_var = tk.StringVar(value=self.config_manager.get_config('ai_config.api_key'))
        ttk.Entry(self.ai_frame, textvariable=self.api_key_var, width=50, show="*").grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 模型
        ttk.Label(self.ai_frame, text="模型:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.model_var = tk.StringVar(value=self.config_manager.get_config('ai_config.model'))
        model_combo = ttk.Combobox(self.ai_frame, textvariable=self.model_var,
                                 values=['gpt-3.5-turbo', 'gpt-4', 'claude-3-sonnet'])
        model_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 温度
        ttk.Label(self.ai_frame, text="温度:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.temperature_var = tk.DoubleVar(value=self.config_manager.get_config('ai_config.temperature'))
        ttk.Entry(self.ai_frame, textvariable=self.temperature_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
    
    def create_advanced_config(self):
        """创建高级配置界面"""
        # 无头模式
        self.headless_var = tk.BooleanVar(value=self.config_manager.get_config('headless'))
        ttk.Checkbutton(self.advanced_frame, text="无头模式", variable=self.headless_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 使用代理
        self.use_ip_var = tk.BooleanVar(value=self.config_manager.get_config('use_ip'))
        ttk.Checkbutton(self.advanced_frame, text="使用代理", variable=self.use_ip_var).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 智能间隔
        self.smart_gap_var = tk.BooleanVar(value=self.config_manager.get_config('enable_smart_gap'))
        ttk.Checkbutton(self.advanced_frame, text="智能提交间隔", variable=self.smart_gap_var).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 验证配置
        self.check_required_var = tk.BooleanVar(value=self.config_manager.get_config('validation_config.check_required'))
        ttk.Checkbutton(self.advanced_frame, text="检查必填项", variable=self.check_required_var).grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
    
    def save_config(self):
        """保存配置"""
        try:
            # 更新配置值
            self.config_manager.set_config('url', self.url_var.get())
            self.config_manager.set_config('target_num', self.target_num_var.get())
            self.config_manager.set_config('min_delay', self.min_delay_var.get())
            self.config_manager.set_config('max_delay', self.max_delay_var.get())
            self.config_manager.set_config('num_threads', self.threads_var.get())
            
            # 矩阵配置
            self.config_manager.set_config('matrix_config.fill_strategy', self.matrix_strategy_var.get())
            self.config_manager.set_config('matrix_config.bias_direction', self.bias_direction_var.get())
            self.config_manager.set_config('matrix_config.bias_strength', self.bias_strength_var.get())
            self.config_manager.set_config('matrix_config.pattern_type', self.pattern_type_var.get())
            
            # AI配置
            self.config_manager.set_config('ai_config.enabled', self.ai_enabled_var.get())
            self.config_manager.set_config('ai_config.api_key', self.api_key_var.get())
            self.config_manager.set_config('ai_config.model', self.model_var.get())
            self.config_manager.set_config('ai_config.temperature', self.temperature_var.get())
            
            # 高级配置
            self.config_manager.set_config('headless', self.headless_var.get())
            self.config_manager.set_config('use_ip', self.use_ip_var.get())
            self.config_manager.set_config('enable_smart_gap', self.smart_gap_var.get())
            self.config_manager.set_config('validation_config.check_required', self.check_required_var.get())
            
            # 保存到文件
            if self.config_manager.save_config():
                messagebox.showinfo("成功", "配置保存成功！")
            else:
                messagebox.showerror("错误", "配置保存失败！")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存配置时出错：{e}")
    
    def load_config(self):
        """加载配置"""
        if self.config_manager.load_config():
            messagebox.showinfo("成功", "配置加载成功！")
            self.refresh_ui()
        else:
            messagebox.showerror("错误", "配置加载失败！")
    
    def reset_config(self):
        """重置配置"""
        if messagebox.askyesno("确认", "确定要重置所有配置吗？"):
            if self.config_manager.reset_config():
                messagebox.showinfo("成功", "配置已重置！")
                self.refresh_ui()
            else:
                messagebox.showerror("错误", "配置重置失败！")
    
    def export_config(self):
        """导出配置"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            if self.config_manager.export_config(file_path):
                messagebox.showinfo("成功", "配置导出成功！")
            else:
                messagebox.showerror("错误", "配置导出失败！")
    
    def import_config(self):
        """导入配置"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            if self.config_manager.import_config(file_path):
                messagebox.showinfo("成功", "配置导入成功！")
                self.refresh_ui()
            else:
                messagebox.showerror("错误", "配置导入失败！")
    
    def refresh_ui(self):
        """刷新界面"""
        # 重新加载所有变量
        self.url_var.set(self.config_manager.get_config('url'))
        self.target_num_var.set(self.config_manager.get_config('target_num'))
        self.min_delay_var.set(self.config_manager.get_config('min_delay'))
        self.max_delay_var.set(self.config_manager.get_config('max_delay'))
        self.threads_var.set(self.config_manager.get_config('num_threads'))
        
        self.matrix_strategy_var.set(self.config_manager.get_config('matrix_config.fill_strategy'))
        self.bias_direction_var.set(self.config_manager.get_config('matrix_config.bias_direction'))
        self.bias_strength_var.set(self.config_manager.get_config('matrix_config.bias_strength'))
        self.pattern_type_var.set(self.config_manager.get_config('matrix_config.pattern_type'))
        
        self.ai_enabled_var.set(self.config_manager.get_config('ai_config.enabled'))
        self.api_key_var.set(self.config_manager.get_config('ai_config.api_key'))
        self.model_var.set(self.config_manager.get_config('ai_config.model'))
        self.temperature_var.set(self.config_manager.get_config('ai_config.temperature'))
        
        self.headless_var.set(self.config_manager.get_config('headless'))
        self.use_ip_var.set(self.config_manager.get_config('use_ip'))
        self.smart_gap_var.set(self.config_manager.get_config('enable_smart_gap'))
        self.check_required_var.set(self.config_manager.get_config('validation_config.check_required'))

# 导出主要类
__all__ = ['EnhancedConfigManager', 'ConfigUI']
