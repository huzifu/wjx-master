#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版问卷解析模块 - 专门处理问卷星的各种题型
支持矩阵量表题、多选题、单选题、文本题等复杂题型的智能解析
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

class EnhancedQuestionnaireParser:
    """增强版问卷解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.matrix_parser = MatrixScaleParser()
        self.config_parser = ConfigParser()
        
    def parse_questionnaire(self, driver, url: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        解析整个问卷结构
        """
        try:
            driver.get(url)
            time.sleep(3)
            
            questionnaire_data = {
                'url': url,
                'title': '',
                'description': '',
                'pages': [],
                'total_questions': 0,
                'matrix_questions': [],
                'question_types': {},
                'config': config or {},
                'parse_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 获取问卷基本信息
            self._parse_basic_info(driver, questionnaire_data)
            
            # 解析所有页面
            page_num = 1
            while True:
                page_data = self._parse_current_page(driver, page_num)
                if not page_data['questions']:
                    break
                    
                questionnaire_data['pages'].append(page_data)
                questionnaire_data['total_questions'] += len(page_data['questions'])
                
                # 统计题型
                for question in page_data['questions']:
                    q_type = question['type']
                    if q_type not in questionnaire_data['question_types']:
                        questionnaire_data['question_types'][q_type] = 0
                    questionnaire_data['question_types'][q_type] += 1
                    
                    # 记录矩阵题
                    if q_type == 'matrix':
                        questionnaire_data['matrix_questions'].append(question)
                
                # 检查是否有下一页
                if not self._go_to_next_page(driver):
                    break
                page_num += 1
            
            self.logger.info(f"问卷解析完成: {len(questionnaire_data['pages'])}页, {questionnaire_data['total_questions']}题")
            return questionnaire_data
            
        except Exception as e:
            self.logger.error(f"问卷解析失败: {e}")
            return {'error': str(e), 'url': url}

    def _parse_basic_info(self, driver, questionnaire_data: Dict[str, Any]):
        """解析问卷基本信息"""
        try:
            # 获取标题
            title_selectors = [
                '.survey-title', '.title', 'h1', '.questionnaire-title',
                '[class*="title"]', '.header h1', '.main-title'
            ]
            for selector in title_selectors:
                try:
                    title_element = driver.find_element(By.CSS_SELECTOR, selector)
                    questionnaire_data['title'] = title_element.text.strip()
                    if questionnaire_data['title']:
                        break
                except:
                    continue
            
            # 获取描述
            desc_selectors = [
                '.description', '.desc', '.intro', '.survey-desc',
                '[class*="description"]', '.header p'
            ]
            for selector in desc_selectors:
                try:
                    desc_element = driver.find_element(By.CSS_SELECTOR, selector)
                    questionnaire_data['description'] = desc_element.text.strip()
                    if questionnaire_data['description']:
                        break
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"基本信息解析失败: {e}")

    def _parse_current_page(self, driver, page_num: int) -> Dict[str, Any]:
        """解析当前页面的所有题目"""
        page_data = {
            'page_num': page_num,
            'questions': [],
            'matrix_questions': [],
            'page_title': f'第{page_num}页'
        }
        
        try:
            # 获取页面标题
            try:
                page_title_element = driver.find_element(By.CSS_SELECTOR, '.page-title, .current-page')
                page_data['page_title'] = page_title_element.text.strip()
            except:
                pass
            
            # 查找所有题目容器
            question_selectors = [
                '.question', '.q-item', '[class*="question"]', '.survey-item',
                '.question-container', '.q-container', '.item'
            ]
            
            question_containers = []
            for selector in question_selectors:
                containers = driver.find_elements(By.CSS_SELECTOR, selector)
                if containers:
                    question_containers = containers
                    break
            
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
                'global_num': f"{page_num}_{q_idx}",
                'type': 'unknown',
                'text': '',
                'sub_text': '',
                'options': [],
                'required': False,
                'matrix_data': None,
                'config': {},
                'validation_rules': [],
                'jump_rules': []
            }
            
            # 获取题目文本
            text_selectors = [
                '.question-text', '.q-text', '.title', '.question-title',
                '.question-content', '.content', 'h3', 'h4', 'h5'
            ]
            for selector in text_selectors:
                try:
                    text_element = container.find_element(By.CSS_SELECTOR, selector)
                    question_data['text'] = text_element.text.strip()
                    if question_data['text']:
                        break
                except:
                    continue
            
            # 获取副标题或说明
            sub_text_selectors = [
                '.sub-text', '.description', '.hint', '.note',
                '.question-desc', '.desc'
            ]
            for selector in sub_text_selectors:
                try:
                    sub_element = container.find_element(By.CSS_SELECTOR, selector)
                    question_data['sub_text'] = sub_element.text.strip()
                    if question_data['sub_text']:
                        break
                except:
                    continue
            
            # 检查是否必填
            required_selectors = [
                '.required', '.must', '[class*="required"]', '.asterisk',
                '.required-mark', '.mandatory'
            ]
            for selector in required_selectors:
                try:
                    required_mark = container.find_element(By.CSS_SELECTOR, selector)
                    question_data['required'] = True
                    break
                except:
                    continue
            
            # 检测题目类型
            question_type = self._detect_question_type(container)
            question_data['type'] = question_type
            
            # 根据类型解析选项和配置
            if question_type == 'matrix':
                matrix_data = self.matrix_parser.parse_matrix_structure(container)
                question_data['matrix_data'] = matrix_data
                question_data['options'] = matrix_data.get('column_options', [])
                question_data['config'] = self.config_parser.parse_matrix_config(matrix_data)
            else:
                options = self._parse_options(container, question_type)
                question_data['options'] = options
                question_data['config'] = self.config_parser.parse_question_config(container, question_type)
            
            # 解析验证规则
            question_data['validation_rules'] = self._parse_validation_rules(container)
            
            # 解析跳转规则
            question_data['jump_rules'] = self._parse_jump_rules(container)
            
            return question_data
            
        except Exception as e:
            self.logger.error(f"题目{q_idx}解析失败: {e}")
            return None

    def _detect_question_type(self, container: WebElement) -> str:
        """检测题目类型"""
        try:
            # 检查矩阵题
            matrix_selectors = [
                'table.matrix-table', '.matrix-table', 'table[class*="matrix"]',
                '.matrix-question', '[class*="matrix"]', '.scale-matrix'
            ]
            for selector in matrix_selectors:
                if container.find_elements(By.CSS_SELECTOR, selector):
                    return 'matrix'
            
            # 检查单选题
            if container.find_elements(By.CSS_SELECTOR, 'input[type="radio"]'):
                return 'single'
            
            # 检查多选题
            if container.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]'):
                return 'multiple'
            
            # 检查文本题
            text_selectors = [
                'input[type="text"]', 'textarea', '.text-input',
                '.text-area', '[class*="text"]'
            ]
            for selector in text_selectors:
                if container.find_elements(By.CSS_SELECTOR, selector):
                    return 'text'
            
            # 检查下拉题
            if container.find_elements(By.CSS_SELECTOR, 'select'):
                return 'dropdown'
            
            # 检查排序题
            sort_selectors = [
                '.sort-item', '[class*="sort"]', '.drag-item',
                '.reorder-item', '.rank-item'
            ]
            for selector in sort_selectors:
                if container.find_elements(By.CSS_SELECTOR, selector):
                    return 'sort'
            
            # 检查量表题
            scale_selectors = [
                '.scale', '.rating', '[class*="scale"]', '[class*="rating"]',
                '.likert', '.star-rating', '.number-scale'
            ]
            for selector in scale_selectors:
                if container.find_elements(By.CSS_SELECTOR, selector):
                    return 'scale'
            
            # 检查日期题
            if container.find_elements(By.CSS_SELECTOR, 'input[type="date"], input[type="datetime-local"]'):
                return 'date'
            
            # 检查数字题
            if container.find_elements(By.CSS_SELECTOR, 'input[type="number"]'):
                return 'number'
            
            return 'unknown'
            
        except:
            return 'unknown'

    def _parse_options(self, container: WebElement, question_type: str) -> List[Dict[str, Any]]:
        """解析题目选项"""
        options = []
        try:
            if question_type in ['single', 'multiple']:
                option_selectors = [
                    '.option', '.choice', 'label', '.radio-option',
                    '.checkbox-option', '.answer-option'
                ]
                
                for selector in option_selectors:
                    option_elements = container.find_elements(By.CSS_SELECTOR, selector)
                    if option_elements:
                        for opt in option_elements:
                            opt_text = opt.text.strip()
                            if opt_text:
                                option_data = {
                                    'text': opt_text,
                                    'value': opt_text,
                                    'has_other': '其他' in opt_text or 'other' in opt_text.lower(),
                                    'element': opt
                                }
                                options.append(option_data)
                        break
            
            elif question_type == 'dropdown':
                select_element = container.find_element(By.CSS_SELECTOR, 'select')
                option_elements = select_element.find_elements(By.CSS_SELECTOR, 'option')
                for opt in option_elements:
                    opt_text = opt.text.strip()
                    if opt_text and opt_text not in ['请选择', '请选择...', 'Select']:
                        option_data = {
                            'text': opt_text,
                            'value': opt.get_attribute('value') or opt_text,
                            'selected': opt.get_attribute('selected') is not None
                        }
                        options.append(option_data)
            
            elif question_type == 'scale':
                scale_selectors = [
                    '.scale-option', '.rating-option', '.likert-option',
                    '.star', '.number', '.scale-item'
                ]
                for selector in scale_selectors:
                    scale_elements = container.find_elements(By.CSS_SELECTOR, selector)
                    if scale_elements:
                        for opt in scale_elements:
                            opt_text = opt.text.strip()
                            if opt_text:
                                option_data = {
                                    'text': opt_text,
                                    'value': opt_text,
                                    'numeric_value': self._extract_number(opt_text)
                                }
                                options.append(option_data)
                        break
                        
        except Exception as e:
            self.logger.error(f"选项解析失败: {e}")
            
        return options

    def _extract_number(self, text: str) -> Optional[float]:
        """从文本中提取数字"""
        try:
            numbers = re.findall(r'\d+(?:\.\d+)?', text)
            if numbers:
                return float(numbers[0])
        except:
            pass
        return None

    def _parse_validation_rules(self, container: WebElement) -> List[Dict[str, Any]]:
        """解析验证规则"""
        rules = []
        try:
            # 检查最小/最大选择数
            min_select = container.get_attribute('data-min-select')
            max_select = container.get_attribute('data-max-select')
            
            if min_select:
                rules.append({'type': 'min_select', 'value': int(min_select)})
            if max_select:
                rules.append({'type': 'max_select', 'value': int(max_select)})
            
            # 检查文本长度限制
            text_length = container.get_attribute('data-max-length')
            if text_length:
                rules.append({'type': 'max_length', 'value': int(text_length)})
                
        except Exception as e:
            self.logger.debug(f"验证规则解析失败: {e}")
            
        return rules

    def _parse_jump_rules(self, container: WebElement) -> List[Dict[str, Any]]:
        """解析跳转规则"""
        rules = []
        try:
            # 查找跳转相关的属性
            jump_attrs = ['data-jump', 'data-skip', 'data-goto']
            for attr in jump_attrs:
                jump_value = container.get_attribute(attr)
                if jump_value:
                    rules.append({'type': 'jump', 'condition': attr, 'target': jump_value})
                    
        except Exception as e:
            self.logger.debug(f"跳转规则解析失败: {e}")
            
        return rules

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

class MatrixScaleParser:
    """矩阵量表题解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def parse_matrix_structure(self, question_element: WebElement) -> Dict[str, Any]:
        """解析矩阵量表题的结构"""
        try:
            matrix_info = {
                'type': 'matrix',
                'rows': [],
                'columns': [],
                'options': [],
                'matrix_data': {},
                'row_questions': [],
                'column_options': [],
                'input_type': 'radio',  # 默认单选
                'scale_type': 'likert'  # 默认李克特量表
            }
            
            # 查找矩阵表格
            table_selectors = [
                'table.matrix-table', '.matrix-table', 'table[class*="matrix"]',
                '.matrix-question table', '.scale-matrix table'
            ]
            
            table = None
            for selector in table_selectors:
                try:
                    table = question_element.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not table:
                self.logger.warning("未找到矩阵表格")
                return matrix_info
            
            # 解析表头（列选项）
            header_selectors = [
                'thead th', 'tr:first-child th', '.matrix-header',
                '.header-row th', '.column-header th'
            ]
            
            headers = []
            for selector in header_selectors:
                try:
                    headers = table.find_elements(By.CSS_SELECTOR, selector)
                    if headers:
                        break
                except:
                    continue
            
            for i, header in enumerate(headers[1:], 1):  # 跳过第一列
                header_text = header.text.strip()
                if header_text:
                    column_info = {
                        'index': i,
                        'text': header_text,
                        'element': header,
                        'numeric_value': self._extract_number(header_text)
                    }
                    matrix_info['columns'].append(column_info)
                    matrix_info['column_options'].append(header_text)
            
            # 解析行（问题）
            row_selectors = [
                'tbody tr', 'tr:not(:first-child)', '.matrix-row',
                '.question-row', '.row-item'
            ]
            
            rows = []
            for selector in row_selectors:
                try:
                    rows = table.find_elements(By.CSS_SELECTOR, selector)
                    if rows:
                        break
                except:
                    continue
            
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
                            'cells': [],
                            'sub_questions': self._parse_sub_questions(cells[0])
                        }
                        matrix_info['rows'].append(row_info)
                        matrix_info['row_questions'].append(question_text)
                        
                        # 解析该行的选项单元格
                        for col_idx, cell in enumerate(cells[1:], 1):
                            if col_idx <= len(matrix_info['columns']):
                                input_type = self._detect_cell_input_type(cell)
                                cell_info = {
                                    'row': row_idx,
                                    'col': col_idx,
                                    'element': cell,
                                    'input_type': input_type,
                                    'question_text': question_text,
                                    'option_text': matrix_info['columns'][col_idx-1]['text'],
                                    'input_element': self._find_input_element(cell, input_type)
                                }
                                row_info['cells'].append(cell_info)
                                matrix_info['matrix_data'][(row_idx, col_idx)] = cell_info
                                
                                # 更新整体输入类型
                                if input_type != matrix_info['input_type']:
                                    matrix_info['input_type'] = 'mixed'
            
            # 确定量表类型
            matrix_info['scale_type'] = self._determine_scale_type(matrix_info)
            
            self.logger.info(f"矩阵题解析完成: {len(matrix_info['rows'])}行 x {len(matrix_info['columns'])}列")
            return matrix_info
            
        except Exception as e:
            self.logger.error(f"矩阵题解析失败: {e}")
            return {'type': 'matrix', 'error': str(e)}

    def _parse_sub_questions(self, question_element: WebElement) -> List[str]:
        """解析子问题"""
        sub_questions = []
        try:
            # 查找子问题元素
            sub_selectors = [
                '.sub-question', '.sub-item', '.sub-text',
                'br + span', '.question-part'
            ]
            
            for selector in sub_selectors:
                try:
                    sub_elements = question_element.find_elements(By.CSS_SELECTOR, selector)
                    for sub in sub_elements:
                        sub_text = sub.text.strip()
                        if sub_text:
                            sub_questions.append(sub_text)
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"子问题解析失败: {e}")
            
        return sub_questions

    def _detect_cell_input_type(self, cell: WebElement) -> str:
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
            # 检查数字输入
            elif cell.find_elements(By.CSS_SELECTOR, 'input[type="number"]'):
                return 'number'
            else:
                return 'unknown'
        except:
            return 'unknown'

    def _find_input_element(self, cell: WebElement, input_type: str) -> Optional[WebElement]:
        """查找输入元素"""
        try:
            if input_type == 'radio':
                return cell.find_element(By.CSS_SELECTOR, 'input[type="radio"]')
            elif input_type == 'checkbox':
                return cell.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
            elif input_type == 'text':
                return cell.find_element(By.CSS_SELECTOR, 'input[type="text"], textarea')
            elif input_type == 'select':
                return cell.find_element(By.CSS_SELECTOR, 'select')
            elif input_type == 'number':
                return cell.find_element(By.CSS_SELECTOR, 'input[type="number"]')
            else:
                return None
        except:
            return None

    def _determine_scale_type(self, matrix_info: Dict[str, Any]) -> str:
        """确定量表类型"""
        try:
            column_texts = [col['text'] for col in matrix_info['columns']]
            
            # 检查李克特量表
            likert_keywords = ['非常同意', '同意', '一般', '不同意', '非常不同意',
                             '非常满意', '满意', '一般', '不满意', '非常不满意',
                             '完全同意', '比较同意', '中立', '比较不同意', '完全不同意']
            
            if any(keyword in ' '.join(column_texts) for keyword in likert_keywords):
                return 'likert'
            
            # 检查数字量表
            if all(self._extract_number(text) is not None for text in column_texts):
                return 'numeric'
            
            # 检查语义量表
            semantic_keywords = ['好', '坏', '高', '低', '强', '弱', '快', '慢']
            if any(keyword in ' '.join(column_texts) for keyword in semantic_keywords):
                return 'semantic'
            
            return 'custom'
            
        except:
            return 'custom'

    def _extract_number(self, text: str) -> Optional[float]:
        """从文本中提取数字"""
        try:
            numbers = re.findall(r'\d+(?:\.\d+)?', text)
            if numbers:
                return float(numbers[0])
        except:
            pass
        return None

class ConfigParser:
    """配置解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def parse_matrix_config(self, matrix_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析矩阵题配置"""
        config = {
            'fill_strategy': 'random',  # random, average, bias
            'bias_direction': 'center',  # left, center, right
            'bias_strength': 0.3,
            'row_strategies': {},
            'column_weights': {},
            'skip_empty_rows': False,
            'fill_all_columns': True
        }
        
        try:
            # 根据矩阵结构设置默认配置
            num_rows = len(matrix_data.get('rows', []))
            num_cols = len(matrix_data.get('columns', []))
            
            if num_rows > 0 and num_cols > 0:
                # 为每行设置策略
                for row in matrix_data.get('rows', []):
                    row_idx = row['index']
                    config['row_strategies'][row_idx] = {
                        'strategy': 'random',
                        'bias': 'center',
                        'weight': 1.0
                    }
                
                # 为每列设置权重
                for col in matrix_data.get('columns', []):
                    col_idx = col['index']
                    config['column_weights'][col_idx] = 1.0
                    
        except Exception as e:
            self.logger.error(f"矩阵配置解析失败: {e}")
            
        return config

    def parse_question_config(self, container: WebElement, question_type: str) -> Dict[str, Any]:
        """解析题目配置"""
        config = {
            'fill_strategy': 'random',
            'probability': {},
            'text_templates': [],
            'validation': {},
            'skip_probability': 0.0
        }
        
        try:
            if question_type == 'single':
                config.update({
                    'fill_strategy': 'random',
                    'probability': {'random': 1.0}
                })
            elif question_type == 'multiple':
                config.update({
                    'fill_strategy': 'random',
                    'min_selection': 1,
                    'max_selection': 3,
                    'probability': {'random': 1.0}
                })
            elif question_type == 'text':
                config.update({
                    'fill_strategy': 'template',
                    'text_templates': ['自动填写内容', '系统生成回答', '用户反馈'],
                    'min_length': 10,
                    'max_length': 200
                })
            elif question_type == 'dropdown':
                config.update({
                    'fill_strategy': 'random',
                    'probability': {'random': 1.0}
                })
                
        except Exception as e:
            self.logger.error(f"题目配置解析失败: {e}")
            
        return config

# 导出主要类
__all__ = ['EnhancedQuestionnaireParser', 'MatrixScaleParser', 'ConfigParser']
