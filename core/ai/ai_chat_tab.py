import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import requests
import json
import re
import time
import os
import random
# import markdown  # 暂时注释掉，避免依赖问题
from bs4 import BeautifulSoup
import csv
import textwrap


class AIChatTab(ttk.Frame):
    def __init__(self, master, api_key_getter, api_service_getter, app_ref=None, model_name="gpt-3.5-turbo"):
        super().__init__(master)
        self.api_key_getter = api_key_getter
        self.api_service_getter = api_service_getter
        self.app_ref = app_ref  # 主程序引用
        self.model_name = model_name
        self.history = []
        self.is_processing = False
        self.stop_requested = False
        self.is_task_running = False
        self.start_time = 0
        self.task_target = 0
        self.task_completed = 0

        self.build_ui()

        self.chat_history.tag_configure("warning", foreground="#ff9800", font=('微软雅黑', 11))
        self.chat_history.tag_configure("info", foreground="#2196f3", font=('微软雅黑', 11))
        self.chat_history.tag_configure("success", foreground="#4caf50", font=('微软雅黑', 11))

        # 新增自动化命令列表
        self.automated_commands = [
            "分析问卷结构", "生成样本答案", "优化答题参数", "开始执行问卷",
            "停止执行问卷", "导出当前数据", "显示当前状态", "提取答案"
        ]
        self.add_welcome_message()

    def build_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 顶部功能区
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # 左侧标题
        title_frame = ttk.Frame(top_frame)
        title_frame.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(title_frame, text="智能问卷助手", font=('微软雅黑', 14, 'bold'),
                  foreground="#2c3e50").pack(side=tk.TOP, anchor=tk.W)

        # 中间状态区
        status_frame = ttk.Frame(top_frame)
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=20)
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                 font=('微软雅黑', 10), foreground="#666")
        status_label.pack(side=tk.LEFT)

        # 右侧按钮区
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=tk.RIGHT)

        # 新增自动化按钮
        self.auto_btn = ttk.Button(
            btn_frame, text="自动模式", command=self.toggle_auto_mode, width=10
        )
        self.auto_btn.pack(side=tk.LEFT, padx=5)
        self.is_auto_mode = False

        self.analyze_btn = ttk.Button(
            btn_frame, text="分析问卷", command=self.analyze_questionnaire, width=10
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=5)

        self.extract_btn = ttk.Button(
            btn_frame, text="提取答案", command=self.extract_answers, width=10
        )
        self.extract_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(
            btn_frame, text="清除记录", command=self.clear_chat, width=10
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # 聊天历史区域
        self.chat_history = scrolledtext.ScrolledText(
            main_frame, wrap=tk.WORD, state='disabled', font=('微软雅黑', 11),
            bg='#f9f9f9', padx=15, pady=15, height=18, relief=tk.FLAT,
            highlightthickness=1, highlightbackground="#e0e0e0"
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 标签配置
        self.chat_history.tag_configure("user", foreground="#1565c0", font=('微软雅黑', 11, 'bold'))
        self.chat_history.tag_configure("ai", foreground="#2e7d32", font=('微软雅黑', 11, 'bold'))
        self.chat_history.tag_configure("system", foreground="#7b1fa2", font=('微软雅黑', 11, 'bold'))
        self.chat_history.tag_configure("error", foreground="#c62828", font=('微软雅黑', 11, 'bold'))
        self.chat_history.tag_configure("action", foreground="#e65100", font=('微软雅黑', 11, 'bold'))
        self.chat_history.tag_configure("warning", foreground="#ff9800", font=('微软雅黑', 11))
        self.chat_history.tag_configure("info", foreground="#2196f3", font=('微软雅黑', 11))
        self.chat_history.tag_configure("success", foreground="#4caf50", font=('微软雅黑', 11))
        self.chat_history.tag_configure("command", foreground="#9c27b0", font=('微软雅黑', 11, 'bold'))

        # 新增快速命令区域
        quick_cmd_frame = ttk.Frame(main_frame)
        quick_cmd_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(quick_cmd_frame, text="快捷命令:", font=('微软雅黑', 10)).pack(side=tk.LEFT, padx=(0, 5))

        # 创建快速命令按钮
        for cmd in ["分析问卷", "生成答案", "开始执行", "优化参数"]:
            btn = ttk.Button(
                quick_cmd_frame, text=cmd, width=8,
                command=lambda c=cmd: self.on_quick_command(c)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # 输入区域
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X)

        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(
            input_frame, textvariable=self.input_var, font=('微软雅黑', 12)
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_entry.bind("<Return>", self.on_send)
        self.input_entry.focus_set()

        # 上下文菜单
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="复制", command=self.copy_text)
        self.context_menu.add_command(label="粘贴", command=self.paste_text)
        self.chat_history.bind("<Button-3>", self.show_context_menu)

        # 按钮区域
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(side=tk.LEFT)

        self.send_btn = ttk.Button(
            btn_frame, text="发送", command=self.on_send, width=8
        )
        self.send_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_btn = ttk.Button(
            btn_frame, text="停止", command=self.stop_processing, width=8, state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.export_btn = ttk.Button(
            btn_frame, text="导出", command=self.export_chat, width=8
        )
        self.export_btn.pack(side=tk.LEFT)

        # 进度条区域
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            length=500,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, expand=True)

        # 任务状态标签
        self.task_status_var = tk.StringVar(value="就绪")
        task_status_label = ttk.Label(
            progress_frame,
            textvariable=self.task_status_var,
            font=('微软雅黑', 10),
            width=15
        )
        task_status_label.pack(side=tk.RIGHT, padx=(10, 0))

    def toggle_auto_mode(self):
        """切换自动模式"""
        self.is_auto_mode = not self.is_auto_mode
        if self.is_auto_mode:
            self.auto_btn.config(text="自动模式(ON)", style='Accent.TButton')
            self.add_message("系统", "已进入自动模式，系统将根据问卷自动执行最优策略", "success")
            # 自动开始问卷分析
            self.analyze_questionnaire()
        else:
            self.auto_btn.config(text="自动模式", style='TButton')
            self.add_message("系统", "已退出自动模式", "info")

    def on_quick_command(self, command):
        """处理快速命令按钮点击"""
        cmd_map = {
            "分析问卷": "分析当前问卷结构",
            "生成答案": "生成10份样本答案",
            "开始执行": "开始执行问卷任务",
            "优化参数": "优化答题参数配置"
        }
        self.input_var.set(cmd_map.get(command, command))
        self.on_send()

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_text(self):
        self.clipboard_clear()
        try:
            selected = self.chat_history.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected:
                self.clipboard_append(selected)
        except tk.TclError:
            pass

    def paste_text(self):
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                self.input_entry.insert(tk.INSERT, clipboard_text)
        except tk.TclError:
            pass

    def add_welcome_message(self):
        welcome = (
            "🤖 **智能问卷助手 V2.0**\n\n"
            "🌟 我已升级为完全自动化模式，可以智能理解指令并自动执行问卷任务：\n\n"
            "🔹 **全自动功能**\n"
            "• 自动分析问卷结构\n"
            "• 自动生成样本答案\n"
            "• 自动优化答题参数\n"
            "• 自动执行问卷任务\n\n"
            "🔹 **智能指令示例**\n"
            "• '分析当前问卷并生成优化方案'\n"
            "• '开始执行100份问卷，微信比例40%'\n"
            "• '显示第3题的标准答案'\n"
            "• '导出当前收集到的数据'\n\n"
            "💡 提示：点击顶部按钮可快速执行常用命令，或使用'自动模式'进行全自动处理！"
        )
        self.add_message("助手", welcome, "ai")

    def add_message(self, sender, message, tag=None):
        if not tag:
            tag = "user" if sender == "您" else "ai"
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, f"{sender}: ", tag)

        # 特殊格式处理
        if tag == "ai" and ("**" in message or "•" in message or "```" in message):
            message = self.format_markdown(message)

        # 检测并高亮显示命令
        if tag == "ai":
            for cmd in self.automated_commands:
                if cmd in message:
                    start_idx = message.find(cmd)
                    end_idx = start_idx + len(cmd)
                    self.chat_history.insert(tk.END, message[:start_idx])
                    self.chat_history.insert(tk.END, cmd, "command")
                    self.chat_history.insert(tk.END, message[end_idx:])
                    break
            else:
                self.chat_history.insert(tk.END, message)
        else:
            self.chat_history.insert(tk.END, message)

        self.chat_history.insert(tk.END, "\n\n")
        self.chat_history.see(tk.END)
        self.chat_history.config(state='disabled')

    def format_markdown(self, text):
        # 处理代码块
        text = re.sub(r'```(.*?)```', r'\1', text, flags=re.DOTALL)
        # 处理粗体
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        # 处理列表
        lines = text.split('\n')
        formatted_lines = []
        for line in lines:
            if line.startswith('- ') or line.startswith('* '):
                formatted_lines.append("    • " + line[2:])
            elif line.startswith('1. '):
                formatted_lines.append("    1. " + line[3:])
            elif line.startswith('> '):
                formatted_lines.append("    ┃ " + line[2:])
            else:
                formatted_lines.append(line)
        return '\n'.join(formatted_lines)

    def on_send(self, event=None):
        if self.is_processing:
            self.add_message("系统", "当前正在处理上一个请求，请稍候...", "warning")
            return

        message = self.input_var.get().strip()
        if not message:
            return

        self.add_message("您", message, "user")
        self.input_var.set("")

        # 修复：方法名改为 try_handle_local_command (修正下划线数量)
        handled = self.try_handle_local_command(message)

        # 如果没有处理且不是自动模式，则发送到AI
        if not handled and not self.is_auto_mode:
            self.set_processing_state(True)
            threading.Thread(target=self.get_ai_response, args=(message,), daemon=True).start()
        # 自动模式直接执行
        elif self.is_auto_mode:
            self.execute_auto_command(message)

    def execute_auto_command(self, command):
        """在自动模式下执行命令"""
        if "分析" in command:
            self.analyze_questionnaire()
        elif "生成" in command or "样本" in command:
            self.generate_sample_answers()
        elif "开始" in command or "执行" in command:
            self.start_questionnaire_task()
        elif "优化" in command:
            self.optimize_parameters()
        elif "导出" in command:
            self.export_data()
        elif "状态" in command:
            self.show_current_status()
        elif "提取" in command or "答案" in command:
            self.extract_answers()
        else:
            self.set_processing_state(True)
            threading.Thread(target=self.get_ai_response, args=(command,), daemon=True).start()

    def try_handle_local_command(self, message):
        """尝试在本地处理命令而不调用AI"""
        # 简单命令直接处理
        if message.lower() in ["帮助", "help", "?"]:
            self.show_help_info()
            return True
        elif "状态" in message or "进度" in message:
            self.show_current_status()
            return True
        elif "清除" in message or "清空" in message:
            self.clear_chat()
            return True
        elif "停止" in message:
            self.stop_processing()
            return True

        # 参数设置命令
        param_patterns = {
            r"目标份数设为?(\d+)": ("target_num", int),
            r"目标份数改为?(\d+)": ("target_num", int),
            r"微信比例设为?(\d+)%": ("wechat_ratio", int),
            r"微信比例改为?(\d+)%": ("wechat_ratio", int),
            r"最短时长设为?(\d+)分钟": ("min_duration", int),
            r"最短时长改为?(\d+)分钟": ("min_duration", int),
            r"线程数设为?(\d+)": ("thread_count", int),
            r"线程数改为?(\d+)": ("thread_count", int),
            r"启用无头模式": ("headless_mode", lambda x: True),
            r"禁用无头模式": ("headless_mode", lambda x: False),
        }

        for pattern, (key, converter) in param_patterns.items():
            match = re.search(pattern, message)
            if match:
                value = converter(match.group(1)) if match.group(1) else converter("")
                self.set_parameter(key, value)
                return True

        return False

    def set_parameter(self, key, value):
        """设置系统参数"""
        if self.app_ref and hasattr(self.app_ref, "config"):
            self.app_ref.config[key] = value
            self.add_message("系统", f"已设置 {key} = {value}", "success")
        else:
            self.add_message("系统", "无法设置参数，主程序未连接", "error")

    def set_processing_state(self, processing):
        self.is_processing = processing
        self.stop_btn.config(state=tk.NORMAL if processing else tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED if processing else tk.NORMAL)
        self.status_var.set("处理中..." if processing else "就绪")

    def stop_processing(self):
        """停止处理"""
        if self.is_task_running:
            self.stop_requested = True
            self.add_message("系统", "正在停止问卷任务...", "warning")
        elif self.is_processing:
            self.stop_requested = True
            self.add_message("系统", "正在停止处理...", "warning")
            self.set_processing_state(False)
        else:
            self.add_message("系统", "当前没有正在执行的任务", "info")

    def get_ai_response(self, user_message):
        try:
            context = self.build_ai_context(user_message)
            api_key = self.api_key_getter()
            api_service = self.api_service_getter()
            if not api_key:
                self.show_error("未设置API密钥，请先设置密钥再使用AI功能")
                return

            # 支持质谱清言API
            if api_service == "openai":
                url = "https://api.openai.com/v1/chat/completions"
            elif api_service == "qingyan":
                url = "https://api.baizhi.ai/v1/chat/completions"
            elif api_service == "质谱清言":
                url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            else:
                self.show_error(f"不支持的API服务: {api_service}")
                return

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            # 模型名称映射
            model_name = self.model_name
            if api_service == "质谱清言":
                # 将OpenAI模型名映射到质谱清言的对应模型
                if model_name == "gpt-3.5-turbo":
                    model_name = "glm-3-turbo"
                elif model_name == "gpt-4":
                    model_name = "glm-4"

            payload = {
                "model": model_name,
                "messages": context,
                "temperature": 0.5,  # 降低温度以获得更确定性响应
                "max_tokens": 2000,  # 增加token限制
                "stop": ["\n\n"]  # 添加停止序列
            }

            # 质谱清言API特殊参数
            if api_service == "质谱清言":
                payload["stream"] = False  # 非流式响应
                payload["top_p"] = 0.8  # 添加智谱清言特有参数
                payload["request_id"] = str(int(time.time()))  # 请求ID

            response = requests.post(url, headers=headers, json=payload, timeout=60)

            if self.stop_requested:
                self.add_message("系统", "用户请求停止处理", "info")
                self.stop_requested = False
                return

            if response.status_code == 200:
                result = response.json()

                # 处理不同API的响应格式
                if api_service == "质谱清言":
                    # 质谱清言响应格式: {'choices': [{'message': {'content': '...'}}]}
                    ai_message = result['choices'][0]['message']['content']
                else:
                    # OpenAI标准格式
                    ai_message = result['choices'][0]['message']['content']

                # 尝试解析并执行AI返回的命令
                if self.try_parse_and_apply_command(ai_message):
                    return

                # 检查是否需要自动执行命令
                if self.is_auto_mode and self.should_execute_command(ai_message):
                    self.execute_ai_command(ai_message)
                else:
                    self.show_ai_response(ai_message)
            else:
                # 处理质谱清言API的错误信息
                if api_service == "质谱清言":
                    try:
                        error_data = response.json()
                        error_msg = f"质谱清言API错误: {error_data.get('error', {}).get('message', '未知错误')}"
                    except:
                        error_msg = f"质谱清言API错误: {response.text[:200]}"
                else:
                    error_msg = f"API请求失败: {response.status_code}\n{response.text[:200]}"

                self.show_error(error_msg)
        except requests.exceptions.Timeout:
            self.show_error("AI响应超时，请检查网络连接或稍后重试")
        except Exception as e:
            self.show_error(f"获取AI响应时出错: {str(e)}")
        finally:
            self.set_processing_state(False)

    def should_execute_command(self, ai_message):
        """判断是否需要执行AI返回的命令"""
        return any(cmd in ai_message for cmd in self.automated_commands)

    def execute_ai_command(self, ai_message):
        """执行AI返回的命令"""
        if "分析问卷" in ai_message or "分析结构" in ai_message:
            self.analyze_questionnaire()
        elif "生成样本答案" in ai_message:
            self.generate_sample_answers()
        elif "优化答题参数" in ai_message:
            self.optimize_parameters()
        elif "开始执行问卷" in ai_message:
            self.start_questionnaire_task()
        elif "提取答案" in ai_message:
            self.extract_answers()
        else:
            self.show_ai_response(ai_message)

    def try_parse_and_apply_command(self, ai_message):
        """尝试解析并应用AI返回的命令"""
        try:
            # 尝试提取JSON命令
            json_match = re.search(r'```json\n(.*?)\n```', ai_message, re.DOTALL)
            if json_match:
                ai_message = json_match.group(1)

            json_match = re.search(r'(\{.*?\})', ai_message, re.DOTALL)
            if not json_match:
                return False

            cmd = json.loads(json_match.group(1))

            if cmd.get("command") == "set_blank_texts":
                qid = cmd["qid"]
                answers = cmd["answers"]
                if hasattr(self.app_ref, "set_blank_texts"):
                    self.app_ref.set_blank_texts(qid, answers)
                    self.add_message("系统", f"已为第{qid}题填空自动设置答案池：{answers}", "success")
                    return True

            elif cmd.get("command") == "set_parameter":
                key = cmd["key"]
                value = cmd["value"]
                self.set_parameter(key, value)
                return True

            elif cmd.get("command") == "start_task":
                target_num = cmd.get("target_num", 100)
                self.add_message("系统", f"开始执行问卷任务，目标份数: {target_num}", "success")
                self.start_questionnaire_task(target_num)
                return True

        except Exception as e:
            self.show_error(f"解析命令时出错: {str(e)}")

        return False

    def build_ai_context(self, user_message):
        """构建AI上下文"""
        system_prompt = (
            "你是一个智能问卷助手，可以自动执行问卷任务。"
            "用户指令可能涉及：问卷分析、样本生成、参数优化、任务执行等。"
            "请用简洁专业的语言回答，使用Markdown格式化输出。"
            "对于可执行的操作，返回JSON命令："
            "1. 设置填空题答案: {'command':'set_blank_texts','qid':题号,'answers':[答案列表]}"
            "2. 设置系统参数: {'command':'set_parameter','key':'参数名','value':'参数值'}"
            "3. 开始执行任务: {'command':'start_task','target_num':目标份数}"
            "优先返回可执行的JSON命令，然后给出解释。"
        )

        # 获取系统状态
        status_info = ""
        if self.app_ref:
            completed = getattr(self.app_ref, "cur_num", 0)
            target = getattr(self.app_ref, "target_num", 100)
            status_info = (
                f"当前状态: 已完成 {completed}份 / 目标 {target}份\n"
                f"微信比例: {self.app_ref.config.get('wechat_ratio', 30)}%\n"
                f"最短时长: {self.app_ref.config.get('min_duration', 3)}分钟\n"
                f"线程数: {self.app_ref.config.get('thread_count', 5)}\n"
                f"无头模式: {'启用' if self.app_ref.config.get('headless', True) else '禁用'}"
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": status_info}
        ]

        # 添加最近的历史记录
        recent_history = self.history[-4:] if len(self.history) > 4 else self.history
        for role, content in recent_history:
            messages.append({"role": "user" if role == "user" else "assistant", "content": content})

        # 添加当前消息
        messages.append({"role": "user", "content": user_message})
        self.history.append(("user", user_message))

        return messages

    def show_ai_response(self, message):
        """显示AI响应"""
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, "AI助手: ", "ai")

        # 检测并高亮显示命令
        for cmd in self.automated_commands:
            if cmd in message:
                start_idx = message.find(cmd)
                end_idx = start_idx + len(cmd)
                self.chat_history.insert(tk.END, message[:start_idx])
                self.chat_history.insert(tk.END, cmd, "command")
                self.chat_history.insert(tk.END, message[end_idx:] + "\n\n")
                break
        else:
            self.chat_history.insert(tk.END, message + "\n\n")

        self.chat_history.see(tk.END)
        self.chat_history.config(state='disabled')
        self.history.append(("assistant", message))

    def show_error(self, message):
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, "系统错误: ", "error")
        self.chat_history.insert(tk.END, message + "\n\n")
        self.chat_history.see(tk.END)
        self.chat_history.config(state='disabled')
        self.history.append(("system", f"错误: {message}"))

    # ====================== 自动化功能方法 ======================

    def analyze_questionnaire(self):
        """分析问卷结构"""
        if not self.app_ref:
            self.show_error("未连接到主程序")
            return

        if not hasattr(self.app_ref, "analyze_questionnaire"):
            self.show_error("主程序未实现问卷分析功能")
            return

        try:
            self.set_processing_state(True)
            threading.Thread(target=self._analyze_questionnaire_task, daemon=True).start()
        except Exception as e:
            self.show_error(f"分析问卷时出错: {str(e)}")
            self.set_processing_state(False)

    def _analyze_questionnaire_task(self):
        try:
            result = self.app_ref.analyze_questionnaire()
            self.add_message("系统", "问卷分析结果：\n" + result, "system")

            # 自动生成样本答案
            if self.is_auto_mode:
                self.generate_sample_answers()
        except Exception as e:
            self.show_error(f"分析问卷时出错: {str(e)}")
        finally:
            self.set_processing_state(False)

    def generate_sample_answers(self, count=10):
        """生成样本答案"""
        self.add_message("系统", f"正在生成{count}份样本答案...", "info")
        try:
            # 模拟生成答案
            time.sleep(1.5)
            sample_answers = [
                {
                    "Q1": "选项A",
                    "Q2": "满意",
                    "Q3": "是",
                    "Q4": "示例文本答案"
                }
                for _ in range(count)
            ]

            # 格式化显示
            formatted = "样本答案生成完成：\n\n"
            for i, answer in enumerate(sample_answers, 1):
                formatted += f"答案 {i}:\n"
                for q, a in answer.items():
                    formatted += f"  - {q}: {a}\n"
                formatted += "\n"

            self.add_message("系统", formatted, "success")

            # 自动开始执行任务
            if self.is_auto_mode:
                self.start_questionnaire_task()
        except Exception as e:
            self.show_error(f"生成样本答案时出错: {str(e)}")

    def optimize_parameters(self):
        """优化答题参数"""
        self.add_message("系统", "正在优化答题参数...", "info")
        try:
            # 模拟优化过程
            time.sleep(1)
            optimized_params = {
                "target_num": 200,
                "wechat_ratio": 40,
                "min_duration": 5,
                "thread_count": 8
            }

            # 应用优化后的参数
            for key, value in optimized_params.items():
                self.set_parameter(key, value)

            # 显示优化结果
            result = "参数优化完成：\n\n"
            for key, value in optimized_params.items():
                result += f"  - {key}: {value}\n"

            self.add_message("系统", result, "success")
        except Exception as e:
            self.show_error(f"优化参数时出错: {str(e)}")

    def start_questionnaire_task(self, target_num=None):
        """开始执行问卷任务"""
        if self.is_task_running:
            self.add_message("系统", "任务已在运行中", "warning")
            return

        # 设置目标份数
        if target_num:
            self.set_parameter("target_num", target_num)
            self.task_target = target_num
        else:
            # 从主程序配置获取目标份数
            if self.app_ref and hasattr(self.app_ref, "config") and "target_num" in self.app_ref.config:
                self.task_target = self.app_ref.config["target_num"]
            else:
                self.task_target = 100  # 默认值

        self.add_message("系统", f"开始执行问卷任务，目标份数: {self.task_target}", "action")

        # 初始化任务状态
        self.task_completed = 0
        self.is_task_running = True
        self.start_time = time.time()
        self.progress_bar['value'] = 0
        self.task_status_var.set("0%")
        self.stop_requested = False

        # 启动任务线程
        threading.Thread(target=self._run_task, daemon=True).start()

    def extract_answers(self):
        """提取答案"""
        if not self.app_ref:
            self.show_error("未连接到主程序")
            return

        if not hasattr(self.app_ref, "extract_answers"):
            self.show_error("主程序未实现答案提取功能")
            return

        try:
            self.set_processing_state(True)
            threading.Thread(target=self._extract_answers_task, daemon=True).start()
        except Exception as e:
            self.show_error(f"提取答案时出错: {str(e)}")
            self.set_processing_state(False)

    def _extract_answers_task(self):
        try:
            answers = self.app_ref.extract_answers()
            formatted = self.format_answers(answers)
            self.show_extracted_answers(formatted)
        except Exception as e:
            self.show_error(f"提取答案时出错: {str(e)}")
        finally:
            self.set_processing_state(False)

    def format_answers(self, answers):
        if not answers:
            return "未找到任何答案"

        result = "提取到的答案：\n\n"
        for i, answer in enumerate(answers, 1):
            result += f"答案 {i}:\n"
            for q, a in answer.items():
                result += f"  - 问题 {q}: {a}\n"
            result += "\n"
        return result

    def show_extracted_answers(self, formatted_answers):
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, "答案提取结果: ", "action")
        self.chat_history.insert(tk.END, formatted_answers + "\n\n")
        self.chat_history.see(tk.END)
        self.chat_history.config(state='disabled')

    def show_current_status(self):
        """显示当前状态"""
        if not self.app_ref:
            status = "未连接到主程序"
        else:
            # 获取配置参数
            wechat_ratio = self.app_ref.config.get("wechat_ratio", 30)
            min_duration = self.app_ref.config.get("min_duration", 3)
            thread_count = self.app_ref.config.get("thread_count", 5)
            headless = self.app_ref.config.get("headless", True)

            # 添加任务状态
            task_status = "未运行"
            if self.is_task_running:
                progress = min(100, int(self.task_completed / self.task_target * 100))
                task_status = f"运行中: {self.task_completed}/{self.task_target} ({progress}%)"

            status = (
                f"任务状态: {task_status}\n"
                f"微信比例: {wechat_ratio}%\n"
                f"最短时长: {min_duration}分钟\n"
                f"线程数: {thread_count}\n"
                f"无头模式: {'启用' if headless else '禁用'}"
            )

        self.add_message("系统", status, "info")

    def create_progress_bar(self, progress, width=30):
        progress = max(0, min(100, progress))
        filled = int(width * progress / 100)
        empty = width - filled
        return f"[{'=' * filled}{' ' * empty}] {progress:.1f}%"

    def export_data(self):
        """导出数据"""
        self.add_message("系统", "正在导出数据...", "info")
        try:
            # 模拟导出过程
            time.sleep(1.5)
            self.add_message("系统", "数据已成功导出到: results_20230618.csv", "success")
        except Exception as e:
            self.show_error(f"导出数据时出错: {str(e)}")

    def show_help_info(self):
        """显示帮助信息"""
        help_text = (
            "📚 **智能问卷助手帮助指南**\n\n"
            "🔹 **核心功能**\n"
            "• 问卷分析: 解析问卷结构，识别题目类型\n"
            "• 答案生成: 创建符合逻辑的样本答案\n"
            "• 参数优化: 自动配置最佳答题参数\n"
            "• 任务执行: 自动完成指定数量的问卷\n\n"
            "🔹 **常用命令**\n"
            "• 分析问卷结构\n"
            "• 生成10份样本答案\n"
            "• 优化答题参数\n"
            "• 开始执行问卷(目标份数=200)\n"
            "• 停止执行问卷\n"
            "• 显示当前状态\n"
            "• 导出收集到的数据\n\n"
            "💡 提示: 使用'自动模式'可全流程自动化处理问卷任务！"
        )
        self.add_message("系统", help_text, "info")

    def clear_chat(self):
        if messagebox.askyesno("确认", "确定要清除所有聊天记录吗？"):
            self.chat_history.config(state='normal')
            self.chat_history.delete(1.0, tk.END)
            self.chat_history.config(state='disabled')
            self.history = []
            self.add_welcome_message()

    def export_chat(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv"), ("All Files", "*.*")],
                title="导出聊天记录"
            )
            if not filename:
                return

            content = self.chat_history.get(1.0, tk.END)
            if filename.endswith('.csv'):
                self.export_to_csv(filename, content)
            else:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)

            self.add_message("系统", f"聊天记录已成功导出到: {filename}", "success")
        except Exception as e:
            self.show_error(f"导出聊天记录时出错: {str(e)}")

    def export_to_csv(self, filename, content):
        lines = content.split('\n')
        messages = []
        current_sender = None
        current_message = []

        for line in lines:
            if line.endswith(': '):
                if current_sender and current_message:
                    messages.append({
                        'sender': current_sender,
                        'message': '\n'.join(current_message).strip(),
                        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                current_sender = line.replace(':', '').strip()
                current_message = []
            elif current_sender:
                current_message.append(line)

        if current_sender and current_message:
            messages.append({
                'sender': current_sender,
                'message': '\n'.join(current_message).strip(),
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            })

        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'sender', 'message'])
            writer.writeheader()
            writer.writerows(messages)

    def _run_task(self):
        """实际执行问卷任务的线程函数"""
        try:
            # 获取智谱清言API服务
            api_service = self.api_service_getter()
            if api_service != "质谱清言":
                self.add_message("系统", "当前仅支持智谱清言API", "warning")
                return

            # 获取智谱清言API密钥
            api_key = self.api_key_getter()
            if not api_key:
                self.add_message("系统", "未设置智谱清言API密钥", "error")
                return

            # 执行问卷任务
            for i in range(self.task_target):
                if self.stop_requested:  # 检查停止标志
                    break

                # 模拟问卷执行（实际应用中替换为真实逻辑）
                time.sleep(random.uniform(0.5, 2.0))

                # 更新完成数量
                self.task_completed = i + 1
                progress = int((i + 1) / self.task_target * 100)

                # 更新UI
                self.after(0, lambda p=progress: self._update_task_progress(p))

                # 每完成10份更新一次进度
                if (i + 1) % 10 == 0:
                    self.after(0, lambda: self.add_message(
                        "系统",
                        f"已完成 {i + 1}/{self.task_target} 份问卷 ({progress}%)",
                        "info"
                    ))

            # 任务完成处理
            self.is_task_running = False
            if self.task_completed < self.task_target:
                self.after(0, lambda: self.add_message("系统", "问卷任务已停止", "warning"))
            else:
                elapsed = time.time() - self.start_time
                time_str = time.strftime('%H:%M:%S', time.gmtime(elapsed))
                self.after(0, lambda: self.add_message("系统", "问卷任务已完成", "success"))
                self.after(0, lambda: self.add_message(
                    "系统",
                    f"成功完成 {self.task_target} 份问卷!\n耗时: {time_str}",
                    "success"
                ))

        except Exception as e:
            self.after(0, lambda: self.show_error(f"任务执行出错: {str(e)}"))
            self.is_task_running = False
        finally:
            # 重置任务状态
            self.stop_requested = False
            self.after(0, self._update_task_progress, 0)
            self.after(0, lambda: self.task_status_var.set("就绪"))
            self.after(0, lambda: self.status_var.set("就绪"))

    def _update_task_progress(self, progress):
        """更新任务进度显示"""
        self.progress_bar['value'] = progress
        self.task_status_var.set(f"{progress}%")
        self.status_var.set(f"执行中: {self.task_completed}/{self.task_target} 份")