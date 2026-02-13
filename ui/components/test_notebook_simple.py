#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的Notebook测试 - 验证基本功能
"""

import tkinter as tk
from tkinter import ttk
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SimpleNotebookTest:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Notebook测试")
        self.root.geometry("800x600")
        
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建Notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 测试标签页
        self.create_test_tabs()
        
        # 添加按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="检查标签页", command=self.check_tabs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="添加标签页", command=self.add_tab).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空标签页", command=self.clear_tabs).pack(side=tk.LEFT, padx=5)
        
    def create_test_tabs(self):
        """创建测试标签页"""
        # 标签页1
        tab1 = ttk.Frame(self.notebook)
        ttk.Label(tab1, text="这是第一个标签页", font=('微软雅黑', 16)).pack(expand=True)
        self.notebook.add(tab1, text="标签页1")
        
        # 标签页2
        tab2 = ttk.Frame(self.notebook)
        ttk.Label(tab2, text="这是第二个标签页", font=('微软雅黑', 16)).pack(expand=True)
        self.notebook.add(tab2, text="标签页2")
        
        # 标签页3
        tab3 = ttk.Frame(self.notebook)
        ttk.Label(tab3, text="这是第三个标签页", font=('微软雅黑', 16)).pack(expand=True)
        self.notebook.add(tab3, text="标签页3")
        
        logging.info(f"创建了 {len(self.notebook.tabs())} 个测试标签页")
        
    def check_tabs(self):
        """检查标签页状态"""
        tabs = self.notebook.tabs()
        logging.info(f"当前标签页数量: {len(tabs)}")
        
        for i, tab_id in enumerate(tabs):
            try:
                tab_text = self.notebook.tab(tab_id, "text")
                logging.info(f"标签页 {i}: ID={tab_id}, 文本={tab_text}")
            except Exception as e:
                logging.error(f"获取标签页 {i} 信息失败: {e}")
        
        # 检查Notebook状态
        logging.info(f"Notebook可见性: {self.notebook.winfo_viewable()}")
        logging.info(f"Notebook几何信息: {self.notebook.winfo_geometry()}")
        logging.info(f"Notebook子组件数量: {len(self.notebook.winfo_children())}")
        
    def add_tab(self):
        """添加新标签页"""
        new_tab = ttk.Frame(self.notebook)
        ttk.Label(new_tab, text=f"新标签页 {len(self.notebook.tabs())+1}", 
                 font=('微软雅黑', 16)).pack(expand=True)
        
        try:
            self.notebook.add(new_tab, text=f"新标签页 {len(self.notebook.tabs())+1}")
            logging.info("新标签页添加成功")
        except Exception as e:
            logging.error(f"添加新标签页失败: {e}")
            
    def clear_tabs(self):
        """清空所有标签页"""
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        logging.info("已清空所有标签页")
        
    def run(self):
        """运行测试"""
        self.root.mainloop()

if __name__ == "__main__":
    test = SimpleNotebookTest()
    test.run()
