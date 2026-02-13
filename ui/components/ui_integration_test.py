#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI集成测试和演示模块
展示增强型题型设置界面的功能和设计效果
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from enhanced_question_settings_ui import EnhancedQuestionSettingsUI

def create_demo_config():
    """创建演示用的配置数据"""
    return {
        "single_prob": {
            "1": [0.3, 0.4, 0.2, 0.1],
            "3": [0.25, 0.25, 0.25, 0.25],
            "5": [0.1, 0.2, 0.4, 0.2, 0.1]
        },
        "multiple_prob": {
            "2": {
                "prob": [60, 40, 30, 50, 70], 
                "min_selection": 2, 
                "max_selection": 4
            },
            "4": {
                "prob": [45, 55, 35, 65], 
                "min_selection": 1, 
                "max_selection": 3
            }
        },
        "matrix_prob": {
            "6": [1, 2, 3, 2, 1],
            "7": [-1]  # 随机
        },
        "scale_prob": {
            "8": [0.1, 0.2, 0.4, 0.2, 0.1],  # 5点Likert量表
            "9": [0.05, 0.15, 0.3, 0.3, 0.15, 0.05]  # 6点量表
        },
        "texts": {
            "10": ["示例答案1", "示例答案2", "示例答案3"],
            "11": ["文本模板A", "文本模板B"]
        },
        "multiple_texts": {
            "12": ["选项A", "选项B", "选项C"],
            "13": ["答案1", "答案2", "答案3", "答案4"]
        },
        "reorder_prob": {
            "14": [0.3, 0.25, 0.2, 0.15, 0.1],
            "15": [0.2, 0.2, 0.2, 0.2, 0.2]
        },
        "droplist_prob": {
            "16": [2, 3, 1, 4],
            "17": [-1]
        },
        "question_texts": {
            "1": "您认为以下哪个选项最能代表您的观点？这是一道关于用户偏好的单选题，请仔细考虑后选择最符合您情况的答案。",
            "2": "请选择所有适用于您情况的选项（可多选）。这道题目旨在了解您的多重偏好和需求。",
            "3": "在以下选项中，哪一个是您的首选？请根据您的实际情况和经验进行选择。",
            "4": "以下哪些因素对您来说比较重要？（可选择多个）您可以根据重要程度选择1-3个最重要的因素。",
            "5": "请对以下陈述选择您的同意程度，这将帮助我们更好地了解您的态度和观点。",
            "6": "请为以下各项进行评分，1表示最不重要，5表示最重要。这是一个矩阵评分题目。",
            "7": "请对以下各个维度进行随机评价，系统将自动为您分配评分结果。",
            "8": "请使用5点量表对以下陈述表达您的同意程度（1=完全不同意，5=完全同意）。",
            "9": "使用6点量表评价以下描述的准确性（1=完全不准确，6=完全准确）。",
            "10": "请在下面的文本框中填写您的答案，可以是简短的词语或短语。",
            "11": "请填写相关信息，可以参考提供的模板格式进行填写。",
            "12": "请在下面的多个文本框中分别填写不同的信息，每个框填写一项内容。",
            "13": "请按照提示在各个文本框中填写对应的答案，确保信息的准确性和完整性。",
            "14": "请将以下选项按照您认为的重要性顺序进行排列，最重要的排在最前面。",
            "15": "请对以下项目进行排序，按照您的偏好程度从高到低排列。",
            "16": "请从下拉菜单中选择最符合您情况的选项，系统根据权重进行选择。",
            "17": "从以下下拉选项中随机选择一个答案，系统将自动处理选择逻辑。"
        },
        "option_texts": {
            "1": ["非常同意", "比较同意", "一般", "不太同意"],
            "2": ["价格因素", "质量因素", "服务因素", "品牌因素", "便利性因素"],
            "3": ["选项A", "选项B", "选项C", "选项D"],
            "4": ["重要性高", "重要性中等", "重要性较低", "不重要"],
            "5": ["强烈反对", "反对", "中性", "支持", "强烈支持"],
            "6": ["维度1", "维度2", "维度3", "维度4", "维度5"],
            "7": ["项目A", "项目B", "项目C"],
            "8": ["完全不同意", "不同意", "中性", "同意", "完全同意"],
            "9": ["完全不准确", "不太准确", "较不准确", "较准确", "准确", "完全准确"],
            "14": ["最重要项目", "重要项目", "一般项目", "次要项目", "不重要项目"],
            "15": ["首选项", "次选项", "第三选择", "第四选择", "最后选择"],
            "16": ["下拉选项1", "下拉选项2", "下拉选项3", "下拉选项4"],
            "17": ["随机选项A", "随机选项B", "随机选项C"]
        }
    }

class UITestApp:
    """UI测试应用"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("增强型题型设置界面 - 功能演示")
        self.root.geometry("1400x900")
        self.root.state('zoomed')  # Windows最大化
        
        # 设置现代化主题
        style = ttk.Style()
        available_themes = style.theme_names()
        if 'vista' in available_themes:
            style.theme_use('vista')
        elif 'clam' in available_themes:
            style.theme_use('clam')
        
        # 配置日志
        self.setup_logging()
        
        # 创建演示配置
        self.demo_config = create_demo_config()
        
        # 创建界面
        self.create_ui()
    
    def setup_logging(self):
        """配置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def create_ui(self):
        """创建主界面"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题区域
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(
            title_frame,
            text="🎯 增强型题型设置界面 - 专业版演示",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)
        
        # 功能说明按钮
        ttk.Button(
            title_frame,
            text="📖 功能说明",
            command=self.show_features
        ).pack(side=tk.RIGHT, padx=(10, 0))
        
        ttk.Button(
            title_frame,
            text="🔄 重新加载",
            command=self.reload_interface
        ).pack(side=tk.RIGHT, padx=(10, 0))
        
        # 创建增强型题型设置界面
        settings_frame = ttk.Frame(main_frame)
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        self.enhanced_ui = EnhancedQuestionSettingsUI(settings_frame, self.demo_config)
        
        # 底部状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Label(
            status_frame,
            text="✅ 界面已加载完成 | 支持8px网格对齐、滚轮交互、统计分布、表格化布局",
            font=("Segoe UI", 10),
            foreground="green"
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            status_frame,
            text="Version 2.0 Professional",
            font=("Segoe UI", 10),
            foreground="gray"
        ).pack(side=tk.RIGHT)
    
    def show_features(self):
        """显示功能说明"""
        features_text = """
🚀 增强型题型设置界面 - 主要特性

📊 1. 滚轮交互升级
   • 鼠标悬停时自动激活滚轮调节
   • 支持精确的数值调节（0.01步长）
   • 实时视觉反馈效果
   • 键盘快捷键支持（↑↓ Page Up/Down）

📐 2. 8px基准网格系统
   • 严格的布局对齐规范
   • 统一的间距标准（8px, 16px, 24px, 32px）
   • 视觉元素精确定位

📝 3. 题目文本框重构
   • 宽度优化为容器的65%
   • 高度增加1.5倍，字体18-20px
   • 内边距12-16px，支持多行显示
   • 现代化边框和背景样式

📊 4. 统计分布专业化
   • 支持正态分布（均值、标准差）
   • 支持均匀分布、Beta分布、指数分布
   • 符合SPSS统计学标准
   • 自定义权重分布

🗂️ 5. 表格化布局
   • Excel风格的专业表格
   • 清晰的列头和数据分离
   • 支持水平和垂直滚动
   • 批量操作功能

💫 6. 现代化样式
   • Segoe UI字体系统
   • 多层次的视觉效果
   • 智能工具提示
   • 响应式布局设计

🔧 7. 专业功能
   • 批量应用统计分布
   • 配置导出/导入
   • 实时参数验证
   • 详细的操作日志
        """
        
        messagebox.showinfo("功能说明", features_text)
    
    def reload_interface(self):
        """重新加载界面"""
        # 清除现有界面
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 重新创建界面
        self.create_ui()
        self.logger.info("界面已重新加载")

def main():
    """主函数"""
    root = tk.Tk()
    app = UITestApp(root)
    
    # 显示启动信息
    messagebox.showinfo(
        "欢迎使用", 
        "🎉 增强型题型设置界面 - 专业版\n\n"
        "本界面采用现代化设计理念，提供：\n"
        "• 8px网格对齐系统\n"
        "• 滚轮精确交互\n" 
        "• 统计分布支持\n"
        "• 表格化专业布局\n\n"
        "点击"功能说明"了解详细特性"
    )
    
    root.mainloop()

if __name__ == "__main__":
    main()
