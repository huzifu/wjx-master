#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI问卷解析模块 - 专门处理矩阵量表题和复杂题型的智能解析
支持多行问题、多列选项的矩阵量表题解析
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

class MatrixQuestionParser:
    """矩阵量表题解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def parse_matrix_structure(self, question_element: WebElement) -> Dict[str, Any]:
        """
        解析矩阵量表题的结构
        返回包含行、列、选项等完整信息的字典
        """
        try:
            matrix_info = {
                'type': 'matrix',
                'rows': [],
                'columns': [],
                'options': [],
                'matrix_data': {},
                'row_questions': [],
                'column_options': []
            }
            
            # 查找矩阵表格
            table = question_element.find_element(By.CSS_SELECTOR, 'table.matrix-table, .matrix-table, table[class*="matrix"]')
            
            # 解析表头（列选项）
            headers = table.find_elements(By.CSS_SELECTOR, 'thead th, tr:first-child th, .matrix-header')
            for i, header in enumerate(headers[1:], 1):  # 跳过第一列（通常是空的）
                header_text = header.text.strip()
                if header_text:
                    matrix_info['columns'].append({
                        'index': i,
                        'text': header_text,
                        'element': header
                    })
                    matrix_info['column_options'].append(header_text)
            
            # 解析行（问题）
            rows = table.find_elements(By.CSS_SELECTOR, 'tbody tr, tr:not(:first-child)')
            for row_idx, row in enumerate(rows):
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                if len(cells) > 1:
                    # 第一列是问题文本
                    question_text = cells[0].text.strip()
                    if question_text:
                        row_info = {
                            'index': row_idx,
                            'text': question_text,
                            'element': cells[0],
                            'cells': []
                        }
                        matrix_info['rows'].append(row_info)
                        matrix_info['row_questions'].append(question_text)
                        
                        # 解析该行的选项单元格
                        for col_idx, cell in enumerate(cells[1:], 1):
                            if col_idx <= len(matrix_info['columns']):
                                cell_info = {
                                    'row': row_idx,
                                    'col': col_idx,
                                    'element': cell,
                                    'input_type': self._detect_input_type(cell),
                                    'question_text': question_text,
                                    'option_text': matrix_info['columns'][col_idx-1]['text']
                                }
                                row_info['cells'].append(cell_info)
                                matrix_info['matrix_data'][(row_idx, col_idx)] = cell_info
            
            self.logger.info(f"矩阵题解析完成: {len(matrix_info['rows'])}行 x {len(matrix_info['columns'])}列")
            return matrix_info
            
        except Exception as e:
            self.logger.error(f"矩阵题解析失败: {e}")
            return {'type': 'matrix', 'error': str(e)}

    def _detect_input_type(self, cell: WebElement) -> str:
        """检测单元格中的输入类型"""
        try:
            # 检查单选按钮
            if cell.find_elements(By.CSS_SELECTOR, 'input[type="radio"]'):
                return 'radio'
            # 检查复选框
            elif cell.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]'):
                return 'checkbox'
            # 检查文本输入
            elif cell.find_elements(By.CSS_SELECTOR, 'input[type="text"], textarea'):
                return 'text'
            # 检查下拉选择
            elif cell.find_elements(By.CSS_SELECTOR, 'select'):
                return 'select'
            # 检查评分量表
            elif cell.find_elements(By.CSS_SELECTOR, '.rating, .scale, [class*="rating"], [class*="scale"]'):
                return 'rating'
            else:
                return 'unknown'
        except:
            return 'unknown'

class AdvancedQuestionParser:
    """高级问卷解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.matrix_parser = MatrixQuestionParser()
        
    def parse_questionnaire_structure(self, driver, url: str) -> Dict[str, Any]:
        """
        解析整个问卷结构
        """
        try:
            driver.get(url)
            time.sleep(2)
            
            questionnaire_data = {
                'url': url,
                'title': '',
                'pages': [],
                'total_questions': 0,
                'matrix_questions': [],
                'question_types': {}
            }
            
            # 获取问卷标题
            try:
                title_element = driver.find_element(By.CSS_SELECTOR, '.survey-title, .title, h1')
                questionnaire_data['title'] = title_element.text.strip()
            except:
                questionnaire_data['title'] = '问卷标题'
            
            # 解析所有页面
            page_num = 1
            while True:
                page_data = self._parse_current_page(driver, page_num)
                if not page_data['questions']:
                    break
                    
                questionnaire_data['pages'].append(page_data)
                questionnaire_data['total_questions'] += len(page_data['questions'])
                
                # 检查是否有下一页
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, '.next-btn, .next, [class*="next"]')
                    if not next_button.is_enabled():
                        break
                    next_button.click()
                    time.sleep(2)
                    page_num += 1
                except:
                    break
            
            self.logger.info(f"问卷解析完成: {len(questionnaire_data['pages'])}页, {questionnaire_data['total_questions']}题")
            return questionnaire_data
            
        except Exception as e:
            self.logger.error(f"问卷解析失败: {e}")
            return {'error': str(e)}

    def _parse_current_page(self, driver, page_num: int) -> Dict[str, Any]:
        """解析当前页面的所有题目"""
        page_data = {
            'page_num': page_num,
            'questions': [],
            'matrix_questions': []
        }
        
        try:
            # 查找所有题目容器
            question_containers = driver.find_elements(By.CSS_SELECTOR, '.question, .q-item, [class*="question"]')
            
            for q_idx, container in enumerate(question_containers, 1):
                question_data = self._parse_single_question(container, q_idx, page_num)
                if question_data:
                    page_data['questions'].append(question_data)
                    
                    # 如果是矩阵题，单独记录
                    if question_data.get('type') == 'matrix':
                        page_data['matrix_questions'].append(question_data)
            
        except Exception as e:
            self.logger.error(f"页面{page_num}解析失败: {e}")
            
        return page_data

    def _parse_single_question(self, container: WebElement, q_idx: int, page_num: int) -> Optional[Dict[str, Any]]:
        """解析单个题目"""
        try:
            question_data = {
                'page_num': page_num,
                'question_num': q_idx,
                'type': 'unknown',
                'text': '',
                'options': [],
                'required': False,
                'matrix_data': None
            }
            
            # 获取题目文本
            try:
                text_element = container.find_element(By.CSS_SELECTOR, '.question-text, .q-text, .title')
                question_data['text'] = text_element.text.strip()
            except:
                question_data['text'] = f"题目{q_idx}"
            
            # 检查是否必填
            try:
                required_mark = container.find_element(By.CSS_SELECTOR, '.required, .must, [class*="required"]')
                question_data['required'] = True
            except:
                question_data['required'] = False
            
            # 检测题目类型
            question_type = self._detect_question_type(container)
            question_data['type'] = question_type
            
            # 根据类型解析选项
            if question_type == 'matrix':
                matrix_data = self.matrix_parser.parse_matrix_structure(container)
                question_data['matrix_data'] = matrix_data
                question_data['options'] = matrix_data.get('column_options', [])
            else:
                options = self._parse_options(container, question_type)
                question_data['options'] = options
            
            return question_data
            
        except Exception as e:
            self.logger.error(f"题目{q_idx}解析失败: {e}")
            return None

    def _detect_question_type(self, container: WebElement) -> str:
        """检测题目类型"""
        try:
            # 检查矩阵题
            if container.find_elements(By.CSS_SELECTOR, 'table.matrix-table, .matrix-table, table[class*="matrix"]'):
                return 'matrix'
            
            # 检查单选题
            if container.find_elements(By.CSS_SELECTOR, 'input[type="radio"]'):
                return 'single'
            
            # 检查多选题
            if container.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]'):
                return 'multiple'
            
            # 检查文本题
            if container.find_elements(By.CSS_SELECTOR, 'input[type="text"], textarea'):
                return 'text'
            
            # 检查下拉题
            if container.find_elements(By.CSS_SELECTOR, 'select'):
                return 'dropdown'
            
            # 检查排序题
            if container.find_elements(By.CSS_SELECTOR, '.sort-item, [class*="sort"]'):
                return 'sort'
            
            # 检查量表题
            if container.find_elements(By.CSS_SELECTOR, '.scale, .rating, [class*="scale"], [class*="rating"]'):
                return 'scale'
            
            return 'unknown'
            
        except:
            return 'unknown'

    def _parse_options(self, container: WebElement, question_type: str) -> List[str]:
        """解析题目选项"""
        options = []
        try:
            if question_type in ['single', 'multiple']:
                option_elements = container.find_elements(By.CSS_SELECTOR, '.option, .choice, label')
                for opt in option_elements:
                    opt_text = opt.text.strip()
                    if opt_text:
                        options.append(opt_text)
            
            elif question_type == 'dropdown':
                select_element = container.find_element(By.CSS_SELECTOR, 'select')
                option_elements = select_element.find_elements(By.CSS_SELECTOR, 'option')
                for opt in option_elements:
                    opt_text = opt.text.strip()
                    if opt_text and opt_text != '请选择':
                        options.append(opt_text)
            
            elif question_type == 'scale':
                scale_elements = container.find_elements(By.CSS_SELECTOR, '.scale-option, .rating-option')
                for opt in scale_elements:
                    opt_text = opt.text.strip()
                    if opt_text:
                        options.append(opt_text)
                        
        except Exception as e:
            self.logger.error(f"选项解析失败: {e}")
            
        return options

def ai_parse_questionnaire(driver, url: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    AI问卷解析主函数
    """
    parser = AdvancedQuestionParser()
    result = parser.parse_questionnaire_structure(driver, url)
    
    # 添加配置信息
    if config:
        result['config'] = config
    
    return result

# 导出主要函数
__all__ = ['ai_parse_questionnaire', 'AdvancedQuestionParser', 'MatrixQuestionParser']
