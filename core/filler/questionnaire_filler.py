#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版问卷填写模块 - 专门处理问卷星的各种题型填写
支持矩阵量表题、多选题、单选题等复杂题型的智能填写
"""

import random
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import numpy as np

class EnhancedQuestionnaireFiller:
    """增强版问卷填写器"""
    
    def __init__(self, config_manager=None):
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.matrix_filler = MatrixScaleFiller(config_manager)
        self.ai_filler = AIQuestionFiller(config_manager)
        
    def fill_questionnaire(self, driver, questionnaire_data: Dict[str, Any]) -> bool:
        """填写整个问卷"""
        try:
            self.logger.info("开始填写问卷...")
            
            # 遍历所有页面
            for page in questionnaire_data.get('pages', []):
                if not self._fill_page(driver, page):
                    self.logger.error(f"页面{page.get('page_num', 'unknown')}填写失败")
                    return False
                
                # 检查是否需要跳转到下一页
                if not self._go_to_next_page(driver):
                    break
                    
                # 页面间延迟
                time.sleep(random.uniform(1, 3))
            
            self.logger.info("问卷填写完成")
            return True
            
        except Exception as e:
            self.logger.error(f"问卷填写失败: {e}")
            return False
    
    def _fill_page(self, driver, page_data: Dict[str, Any]) -> bool:
        """填写单个页面"""
        try:
            questions = page_data.get('questions', [])
            self.logger.info(f"填写页面{page_data.get('page_num', 'unknown')}，共{len(questions)}题")
            
            for question in questions:
                if not self._fill_single_question(driver, question):
                    self.logger.warning(f"题目{question.get('question_num', 'unknown')}填写失败")
                    continue
                
                # 题目间延迟
                time.sleep(random.uniform(0.5, 1.5))
            
            return True
            
        except Exception as e:
            self.logger.error(f"页面填写失败: {e}")
            return False
    
    def _fill_single_question(self, driver, question_data: Dict[str, Any]) -> bool:
        """填写单个题目"""
        try:
            question_type = question_data.get('type', 'unknown')
            question_num = question_data.get('question_num', 'unknown')
            
            self.logger.debug(f"填写题目{question_num}，类型：{question_type}")
            
            # 根据题型选择填写方法
            if question_type == 'matrix':
                return self.matrix_filler.fill_matrix_question(driver, question_data)
            elif question_type == 'single':
                return self._fill_single_choice(driver, question_data)
            elif question_type == 'multiple':
                return self._fill_multiple_choice(driver, question_data)
            elif question_type == 'text':
                return self._fill_text_question(driver, question_data)
            elif question_type == 'dropdown':
                return self._fill_dropdown_question(driver, question_data)
            elif question_type == 'scale':
                return self._fill_scale_question(driver, question_data)
            elif question_type == 'sort':
                return self._fill_sort_question(driver, question_data)
            else:
                self.logger.warning(f"未知题型：{question_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"题目填写失败: {e}")
            return False
    
    def _fill_single_choice(self, driver, question_data: Dict[str, Any]) -> bool:
        """填写单选题"""
        try:
            options = question_data.get('options', [])
            if not options:
                self.logger.warning("单选题没有选项")
                return False
            
            # 获取配置的概率
            config = self.config_manager.get_question_config(question_data.get('global_num', ''), 'single') if self.config_manager else {}
            probabilities = config.get('probabilities', -1)
            
            # 选择选项
            if probabilities == -1:
                # 随机选择
                selected_index = random.randint(0, len(options) - 1)
            elif isinstance(probabilities, list) and len(probabilities) == len(options):
                # 按概率选择
                selected_index = np.random.choice(len(options), p=probabilities)
            else:
                # 默认随机选择
                selected_index = random.randint(0, len(options) - 1)
            
            # 查找并点击选项
            option_elements = driver.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
            if selected_index < len(option_elements):
                self._safe_click(driver, option_elements[selected_index])
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"单选题填写失败: {e}")
            return False
    
    def _fill_multiple_choice(self, driver, question_data: Dict[str, Any]) -> bool:
        """填写多选题"""
        try:
            options = question_data.get('options', [])
            if not options:
                self.logger.warning("多选题没有选项")
                return False
            
            # 获取配置
            config = self.config_manager.get_question_config(question_data.get('global_num', ''), 'multiple') if self.config_manager else {}
            min_selection = config.get('min_selection', 1)
            max_selection = config.get('max_selection', len(options))
            probabilities = config.get('prob', [0.5] * len(options))
            
            # 确定选择数量
            num_selections = random.randint(min_selection, min(max_selection, len(options)))
            
            # 按概率选择选项
            selected_indices = np.random.choice(len(options), size=num_selections, replace=False, p=probabilities)
            
            # 查找并点击选项
            option_elements = driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
            for index in selected_indices:
                if index < len(option_elements):
                    self._safe_click(driver, option_elements[index])
            
            return True
            
        except Exception as e:
            self.logger.error(f"多选题填写失败: {e}")
            return False
    
    def _fill_text_question(self, driver, question_data: Dict[str, Any]) -> bool:
        """填写文本题"""
        try:
            # 获取配置
            config = self.config_manager.get_question_config(question_data.get('global_num', ''), 'text') if self.config_manager else {}
            templates = config.get('templates', ['自动填写内容'])
            use_ai = config.get('use_ai', False)
            
            # 生成文本内容
            if use_ai and self.ai_filler:
                text = self.ai_filler.generate_text_answer(question_data.get('text', ''))
            else:
                text = random.choice(templates)
            
            # 查找文本输入框
            text_elements = driver.find_elements(By.CSS_SELECTOR, 'input[type="text"], textarea')
            if text_elements:
                text_element = text_elements[0]
                text_element.clear()
                text_element.send_keys(text)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"文本题填写失败: {e}")
            return False
    
    def _fill_dropdown_question(self, driver, question_data: Dict[str, Any]) -> bool:
        """填写下拉题"""
        try:
            options = question_data.get('options', [])
            if not options:
                self.logger.warning("下拉题没有选项")
                return False
            
            # 随机选择选项
            selected_option = random.choice(options)
            
            # 查找下拉框
            select_element = driver.find_element(By.CSS_SELECTOR, 'select')
            from selenium.webdriver.support.ui import Select
            select = Select(select_element)
            
            # 选择选项
            select.select_by_visible_text(selected_option)
            return True
            
        except Exception as e:
            self.logger.error(f"下拉题填写失败: {e}")
            return False
    
    def _fill_scale_question(self, driver, question_data: Dict[str, Any]) -> bool:
        """填写量表题"""
        try:
            options = question_data.get('options', [])
            if not options:
                self.logger.warning("量表题没有选项")
                return False
            
            # 随机选择选项
            selected_index = random.randint(0, len(options) - 1)
            
            # 查找并点击选项
            scale_elements = driver.find_elements(By.CSS_SELECTOR, '.scale-option, .rating-option, input[type="radio"]')
            if selected_index < len(scale_elements):
                self._safe_click(driver, scale_elements[selected_index])
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"量表题填写失败: {e}")
            return False
    
    def _fill_sort_question(self, driver, question_data: Dict[str, Any]) -> bool:
        """填写排序题"""
        try:
            # 获取排序项
            sort_elements = driver.find_elements(By.CSS_SELECTOR, '.sort-item, .drag-item')
            if not sort_elements:
                self.logger.warning("排序题没有选项")
                return False
            
            # 随机排序
            indices = list(range(len(sort_elements)))
            random.shuffle(indices)
            
            # 执行拖拽排序
            for i, target_index in enumerate(indices):
                if i != target_index:
                    # 这里需要实现拖拽逻辑
                    pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"排序题填写失败: {e}")
            return False
    
    def _safe_click(self, driver, element: WebElement) -> bool:
        """安全点击元素"""
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(element))
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            element.click()
            return True
        except Exception as e:
            self.logger.warning(f"点击元素失败: {e}")
            return False
    
    def _go_to_next_page(self, driver) -> bool:
        """跳转到下一页"""
        try:
            next_selectors = [
                '.next-btn', '.next', '[class*="next"]', '.next-page',
                '.continue-btn', '.submit-btn'
            ]
            
            for selector in next_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button.is_enabled() and next_button.is_displayed():
                        next_button.click()
                        time.sleep(2)
                        return True
                except:
                    continue
                    
            return False
            
        except Exception as e:
            self.logger.debug(f"跳转下一页失败: {e}")
            return False

class MatrixScaleFiller:
    """矩阵量表题填写器"""
    
    def __init__(self, config_manager=None):
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
    
    def fill_matrix_question(self, driver, question_data: Dict[str, Any]) -> bool:
        """填写矩阵量表题"""
        try:
            matrix_data = question_data.get('matrix_data', {})
            if not matrix_data:
                self.logger.warning("矩阵题数据为空")
                return False
            
            # 获取矩阵配置
            config = self.config_manager.get_matrix_config(question_data.get('global_num', '')) if self.config_manager else {}
            fill_strategy = config.get('fill_strategy', 'random')
            
            # 根据策略填写矩阵
            if fill_strategy == 'random':
                return self._fill_matrix_random(driver, matrix_data)
            elif fill_strategy == 'average':
                return self._fill_matrix_average(driver, matrix_data)
            elif fill_strategy == 'bias':
                return self._fill_matrix_bias(driver, matrix_data, config)
            elif fill_strategy == 'pattern':
                return self._fill_matrix_pattern(driver, matrix_data, config)
            else:
                return self._fill_matrix_random(driver, matrix_data)
                
        except Exception as e:
            self.logger.error(f"矩阵题填写失败: {e}")
            return False
    
    def _fill_matrix_random(self, driver, matrix_data: Dict[str, Any]) -> bool:
        """随机填写矩阵"""
        try:
            rows = matrix_data.get('rows', [])
            columns = matrix_data.get('columns', [])
            
            for row in rows:
                # 为每行随机选择一个列
                selected_col = random.randint(0, len(columns) - 1)
                cell_info = matrix_data.get('matrix_data', {}).get((row['index'], selected_col + 1))
                
                if cell_info and cell_info.get('input_element'):
                    self._safe_click(driver, cell_info['input_element'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"随机填写矩阵失败: {e}")
            return False
    
    def _fill_matrix_average(self, driver, matrix_data: Dict[str, Any]) -> bool:
        """平均分布填写矩阵"""
        try:
            rows = matrix_data.get('rows', [])
            columns = matrix_data.get('columns', [])
            
            # 计算每列的选择概率（平均分布）
            col_probabilities = [1.0 / len(columns)] * len(columns)
            
            for row in rows:
                # 按概率选择列
                selected_col = np.random.choice(len(columns), p=col_probabilities)
                cell_info = matrix_data.get('matrix_data', {}).get((row['index'], selected_col + 1))
                
                if cell_info and cell_info.get('input_element'):
                    self._safe_click(driver, cell_info['input_element'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"平均分布填写矩阵失败: {e}")
            return False
    
    def _fill_matrix_bias(self, driver, matrix_data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """偏置填写矩阵"""
        try:
            rows = matrix_data.get('rows', [])
            columns = matrix_data.get('columns', [])
            
            bias_direction = config.get('bias_direction', 'center')
            bias_strength = config.get('bias_strength', 0.3)
            
            # 根据偏置方向计算概率
            col_probabilities = self._calculate_bias_probabilities(len(columns), bias_direction, bias_strength)
            
            for row in rows:
                # 按偏置概率选择列
                selected_col = np.random.choice(len(columns), p=col_probabilities)
                cell_info = matrix_data.get('matrix_data', {}).get((row['index'], selected_col + 1))
                
                if cell_info and cell_info.get('input_element'):
                    self._safe_click(driver, cell_info['input_element'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"偏置填写矩阵失败: {e}")
            return False
    
    def _fill_matrix_pattern(self, driver, matrix_data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """模式填写矩阵"""
        try:
            rows = matrix_data.get('rows', [])
            columns = matrix_data.get('columns', [])
            pattern_type = config.get('pattern_type', 'normal')
            
            # 根据模式类型生成填写模式
            if pattern_type == 'extreme':
                # 极端模式：倾向于选择两端
                pattern = self._generate_extreme_pattern(len(columns))
            elif pattern_type == 'conservative':
                # 保守模式：倾向于选择中间
                pattern = self._generate_conservative_pattern(len(columns))
            else:
                # 正常模式：随机但有规律
                pattern = self._generate_normal_pattern(len(columns))
            
            for i, row in enumerate(rows):
                # 根据模式选择列
                selected_col = pattern[i % len(pattern)]
                cell_info = matrix_data.get('matrix_data', {}).get((row['index'], selected_col + 1))
                
                if cell_info and cell_info.get('input_element'):
                    self._safe_click(driver, cell_info['input_element'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"模式填写矩阵失败: {e}")
            return False
    
    def _calculate_bias_probabilities(self, num_columns: int, bias_direction: str, bias_strength: float) -> List[float]:
        """计算偏置概率"""
        base_prob = 1.0 / num_columns
        probabilities = [base_prob] * num_columns
        
        if bias_direction == 'left':
            # 偏向左侧
            for i in range(num_columns):
                probabilities[i] *= (1 + bias_strength * (num_columns - i) / num_columns)
        elif bias_direction == 'right':
            # 偏向右侧
            for i in range(num_columns):
                probabilities[i] *= (1 + bias_strength * (i + 1) / num_columns)
        elif bias_direction == 'center':
            # 偏向中间
            center = num_columns // 2
            for i in range(num_columns):
                distance = abs(i - center)
                probabilities[i] *= (1 + bias_strength * (1 - distance / center))
        
        # 归一化概率
        total = sum(probabilities)
        return [p / total for p in probabilities]
    
    def _generate_extreme_pattern(self, num_columns: int) -> List[int]:
        """生成极端模式"""
        pattern = []
        for _ in range(num_columns):
            if random.random() < 0.7:
                # 70%概率选择两端
                pattern.append(random.choice([0, num_columns - 1]))
            else:
                # 30%概率随机选择
                pattern.append(random.randint(0, num_columns - 1))
        return pattern
    
    def _generate_conservative_pattern(self, num_columns: int) -> List[int]:
        """生成保守模式"""
        pattern = []
        center = num_columns // 2
        for _ in range(num_columns):
            if random.random() < 0.7:
                # 70%概率选择中间
                pattern.append(center)
            else:
                # 30%概率随机选择
                pattern.append(random.randint(0, num_columns - 1))
        return pattern
    
    def _generate_normal_pattern(self, num_columns: int) -> List[int]:
        """生成正常模式"""
        pattern = []
        for _ in range(num_columns):
            # 正态分布选择
            col = int(np.random.normal(num_columns / 2, num_columns / 4))
            col = max(0, min(col, num_columns - 1))
            pattern.append(col)
        return pattern
    
    def _safe_click(self, driver, element: WebElement) -> bool:
        """安全点击元素"""
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(element))
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            element.click()
            return True
        except Exception as e:
            self.logger.warning(f"点击元素失败: {e}")
            return False

class AIQuestionFiller:
    """AI题目填写器"""
    
    def __init__(self, config_manager=None):
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
    
    def generate_text_answer(self, question_text: str) -> str:
        """生成文本答案"""
        try:
            if not self.config_manager:
                return "自动填写内容"
            
            ai_config = self.config_manager.get_config('ai_config', {})
            if not ai_config.get('enabled', False):
                return "自动填写内容"
            
            # 这里可以集成AI API生成答案
            # 暂时返回模板答案
            templates = [
                "这是一个很好的问题，我认为需要综合考虑多个因素。",
                "根据我的经验，这个问题可以从不同角度来分析。",
                "从专业角度来看，这个情况需要具体情况具体分析。",
                "个人认为这个问题很有意义，值得深入思考。",
                "基于实际情况，我认为需要平衡各方利益。"
            ]
            
            return random.choice(templates)
            
        except Exception as e:
            self.logger.error(f"生成AI答案失败: {e}")
            return "自动填写内容"

# 导出主要类
__all__ = ['EnhancedQuestionnaireFiller', 'MatrixScaleFiller', 'AIQuestionFiller']
