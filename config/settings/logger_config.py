#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置模块
提供统一的日志管理功能，支持文件日志、控制台日志和UI日志
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import traceback
import threading

class UILogHandler(logging.Handler):
    """自定义UI日志处理器，用于在界面中显示日志"""
    
    def __init__(self, log_callback=None):
        super().__init__()
        self.log_callback = log_callback
        self.logs = []  # 存储最近的日志
        self.max_logs = 1000  # 最大日志条数
        
    def emit(self, record):
        """发送日志记录"""
        try:
            msg = self.format(record)
            timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
            
            # 添加到内存存储
            log_entry = {
                'timestamp': timestamp,
                'level': record.levelname,
                'message': msg,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            self.logs.append(log_entry)
            if len(self.logs) > self.max_logs:
                self.logs.pop(0)
            
            # 如果有回调函数，调用它
            if self.log_callback:
                self.log_callback(log_entry)
                
        except Exception:
            self.handleError(record)
    
    def get_recent_logs(self, count=100):
        """获取最近的日志"""
        return self.logs[-count:] if count else self.logs

class OperationLogger:
    """操作日志记录器"""
    
    def __init__(self, logger_name="operation"):
        self.logger = logging.getLogger(logger_name)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def log_start(self, operation, **kwargs):
        """记录操作开始"""
        details = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        self.logger.info(f"🚀 开始操作: {operation} | {details}")
    
    def log_progress(self, operation, progress, total=None, message=""):
        """记录操作进度"""
        if total:
            percent = (progress / total) * 100
            self.logger.info(f"⏳ {operation} 进度: {progress}/{total} ({percent:.1f}%) | {message}")
        else:
            self.logger.info(f"⏳ {operation} 进度: {progress} | {message}")
    
    def log_success(self, operation, result=None, **kwargs):
        """记录操作成功"""
        details = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        result_str = f" | 结果: {result}" if result else ""
        self.logger.info(f"✅ 操作成功: {operation} | {details}{result_str}")
    
    def log_error(self, operation, error, **kwargs):
        """记录操作错误"""
        details = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        error_details = str(error)
        if hasattr(error, '__traceback__'):
            error_details += f"\n{traceback.format_exc()}"
        self.logger.error(f"❌ 操作失败: {operation} | {details} | 错误: {error_details}")
    
    def log_warning(self, operation, warning, **kwargs):
        """记录操作警告"""
        details = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        self.logger.warning(f"⚠️  操作警告: {operation} | {details} | 警告: {warning}")

class LoggerConfig:
    """日志配置管理器"""
    
    def __init__(self):
        self.ui_handler = None
        self.operation_logger = None
        self.setup_complete = False
        
    def setup_logging(self, 
                     log_dir="logs",
                     console_level=logging.INFO,
                     file_level=logging.DEBUG,
                     ui_callback=None):
        """设置日志系统"""
        
        # 创建日志目录
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 获取根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 设置日志格式
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-15s | %(funcName)-20s:%(lineno)-4d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # 1. 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
        
        # 2. 文件处理器 - 主日志
        log_file = os.path.join(log_dir, f"wjx_system_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # 3. 错误日志文件
        error_log_file = os.path.join(log_dir, f"wjx_errors_{datetime.now().strftime('%Y%m%d')}.log")
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
        
        # 4. 操作日志文件
        operation_log_file = os.path.join(log_dir, f"wjx_operations_{datetime.now().strftime('%Y%m%d')}.log")
        operation_handler = logging.handlers.RotatingFileHandler(
            operation_log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        operation_handler.setLevel(logging.INFO)
        operation_handler.setFormatter(detailed_formatter)
        
        # 5. UI处理器（如果提供了回调）
        if ui_callback:
            self.ui_handler = UILogHandler(ui_callback)
            self.ui_handler.setLevel(logging.INFO)
            self.ui_handler.setFormatter(simple_formatter)
            root_logger.addHandler(self.ui_handler)
        
        # 创建操作日志器
        operation_logger = logging.getLogger("operation")
        operation_logger.addHandler(operation_handler)
        self.operation_logger = OperationLogger("operation")
        
        # 记录日志系统启动
        root_logger.info("=" * 80)
        root_logger.info("🚀 问卷星系统启动")
        root_logger.info(f"📁 日志目录: {os.path.abspath(log_dir)}")
        root_logger.info(f"📄 主日志文件: {log_file}")
        root_logger.info(f"🔴 错误日志文件: {error_log_file}")
        root_logger.info(f"⚡ 操作日志文件: {operation_log_file}")
        root_logger.info("=" * 80)
        
        self.setup_complete = True
        return self.operation_logger
    
    def get_operation_logger(self):
        """获取操作日志器"""
        if not self.operation_logger:
            self.operation_logger = OperationLogger()
        return self.operation_logger
    
    def get_ui_logs(self, count=100):
        """获取UI日志"""
        if self.ui_handler:
            return self.ui_handler.get_recent_logs(count)
        return []

# 全局日志配置实例
logger_config = LoggerConfig()

def get_logger(name=None):
    """获取日志器"""
    return logging.getLogger(name)

def get_operation_logger():
    """获取操作日志器"""
    return logger_config.get_operation_logger()

def setup_logging(log_dir="logs", console_level=logging.INFO, ui_callback=None):
    """设置日志系统的便捷函数"""
    return logger_config.setup_logging(log_dir, console_level, ui_callback=ui_callback)

# 日志装饰器
def log_operation(operation_name):
    """操作日志装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_logger = get_operation_logger()
            op_logger.log_start(operation_name, function=func.__name__)
            try:
                result = func(*args, **kwargs)
                op_logger.log_success(operation_name, result=str(result)[:100] if result else "None")
                return result
            except Exception as e:
                op_logger.log_error(operation_name, e)
                raise
        return wrapper
    return decorator
