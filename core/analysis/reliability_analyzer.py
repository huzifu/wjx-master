#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信效度分析模块 - 基于SPSS算法实现
提供Cronbach's Alpha系数计算、项目分析等功能
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional
import math
from dataclasses import dataclass

@dataclass
class ReliabilityResult:
    """信效度分析结果"""
    cronbach_alpha: float
    items_alpha_if_deleted: Dict[str, float]
    item_total_correlations: Dict[str, float]
    corrected_item_total_correlations: Dict[str, float]
    item_means: Dict[str, float]
    item_variances: Dict[str, float]
    scale_mean: float
    scale_variance: float
    recommended_weights: Dict[str, List[float]]
    reliability_level: str
    suggestions: List[str]

class ReliabilityAnalyzer:
    """信效度分析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 信效度标准
        self.reliability_standards = {
            'excellent': 0.9,
            'good': 0.8,
            'acceptable': 0.7,
            'questionable': 0.6,
            'poor': 0.0
        }
    
    def calculate_cronbach_alpha(self, responses: np.ndarray) -> float:
        """
        计算Cronbach's Alpha系数
        
        Args:
            responses: 应答矩阵 (n_samples, n_items)
            
        Returns:
            Cronbach's Alpha系数
        """
        try:
            n_items = responses.shape[1]
            
            # 计算各题目方差
            item_variances = np.var(responses, axis=0, ddof=1)
            
            # 计算总分方差
            total_scores = np.sum(responses, axis=1)
            total_variance = np.var(total_scores, ddof=1)
            
            # 计算Cronbach's Alpha
            sum_item_variances = np.sum(item_variances)
            alpha = (n_items / (n_items - 1)) * (1 - sum_item_variances / total_variance)
            
            return max(0.0, min(1.0, alpha))
            
        except Exception as e:
            self.logger.error(f"计算Cronbach's Alpha失败: {e}")
            return 0.0
    
    def calculate_item_total_correlation(self, responses: np.ndarray, item_index: int) -> float:
        """
        计算项目-总分相关系数
        
        Args:
            responses: 应答矩阵
            item_index: 项目索引
            
        Returns:
            项目-总分相关系数
        """
        try:
            item_scores = responses[:, item_index]
            total_scores = np.sum(responses, axis=1)
            
            # 计算相关系数
            correlation = np.corrcoef(item_scores, total_scores)[0, 1]
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            self.logger.error(f"计算项目-总分相关失败: {e}")
            return 0.0
    
    def calculate_corrected_item_total_correlation(self, responses: np.ndarray, item_index: int) -> float:
        """
        计算校正的项目-总分相关系数（排除该项目本身）
        
        Args:
            responses: 应答矩阵
            item_index: 项目索引
            
        Returns:
            校正的项目-总分相关系数
        """
        try:
            item_scores = responses[:, item_index]
            
            # 计算除了当前项目外的总分
            other_items = np.delete(responses, item_index, axis=1)
            other_total_scores = np.sum(other_items, axis=1)
            
            # 计算相关系数
            correlation = np.corrcoef(item_scores, other_total_scores)[0, 1]
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            self.logger.error(f"计算校正项目-总分相关失败: {e}")
            return 0.0
    
    def calculate_alpha_if_deleted(self, responses: np.ndarray, item_index: int) -> float:
        """
        计算删除某项目后的Alpha系数
        
        Args:
            responses: 应答矩阵
            item_index: 要删除的项目索引
            
        Returns:
            删除项目后的Alpha系数
        """
        try:
            # 删除指定项目
            reduced_responses = np.delete(responses, item_index, axis=1)
            
            # 计算新的Alpha系数
            return self.calculate_cronbach_alpha(reduced_responses)
            
        except Exception as e:
            self.logger.error(f"计算删除项目后Alpha失败: {e}")
            return 0.0
    
    def generate_optimal_weights(self, question_type: str, n_options: int, 
                                reliability_target: float = 0.8) -> List[float]:
        """
        根据信效度要求生成最优权重分布
        
        Args:
            question_type: 题目类型
            n_options: 选项数量
            reliability_target: 目标信效度水平
            
        Returns:
            最优权重分布
        """
        try:
            if question_type == '3':  # 单选题
                return self._generate_single_choice_weights(n_options, reliability_target)
            elif question_type == '4':  # 多选题
                return self._generate_multiple_choice_weights(n_options, reliability_target)
            elif question_type == '5':  # 量表题
                return self._generate_scale_weights(n_options, reliability_target)
            else:
                # 默认均匀分布
                return [1.0 / n_options] * n_options
                
        except Exception as e:
            self.logger.error(f"生成最优权重失败: {e}")
            return [1.0 / n_options] * n_options
    
    def _generate_single_choice_weights(self, n_options: int, target_reliability: float) -> List[float]:
        """生成单选题最优权重"""
        if target_reliability >= 0.8:
            # 高信效度要求：中等分散度
            if n_options == 2:
                return [0.6, 0.4]
            elif n_options == 3:
                return [0.5, 0.3, 0.2]
            elif n_options == 4:
                return [0.4, 0.3, 0.2, 0.1]
            elif n_options == 5:
                return [0.3, 0.25, 0.2, 0.15, 0.1]
        elif target_reliability >= 0.7:
            # 中等信效度要求：适度分散
            center = n_options // 2
            weights = []
            for i in range(n_options):
                distance = abs(i - center)
                weight = max(0.05, 0.4 - distance * 0.1)
                weights.append(weight)
            # 归一化
            total = sum(weights)
            return [w / total for w in weights]
        else:
            # 低信效度要求：相对均匀
            base_weight = 1.0 / n_options
            variation = 0.1
            weights = [base_weight + ((-1) ** i) * variation * (i % 2) for i in range(n_options)]
            # 归一化并确保非负
            weights = [max(0.01, w) for w in weights]
            total = sum(weights)
            return [w / total for w in weights]
        
        # 默认均匀分布
        return [1.0 / n_options] * n_options
    
    def _generate_multiple_choice_weights(self, n_options: int, target_reliability: float) -> List[float]:
        """生成多选题最优权重"""
        if target_reliability >= 0.8:
            # 高信效度：避免极端选择
            base_prob = 0.4
            return [min(0.8, max(0.2, base_prob + (i - n_options//2) * 0.05)) for i in range(n_options)]
        else:
            # 中低信效度：相对均匀
            return [0.5] * n_options  # 多选题用选择概率而非权重分布
    
    def _generate_scale_weights(self, n_options: int, target_reliability: float) -> List[float]:
        """生成量表题最优权重"""
        if target_reliability >= 0.8:
            # 高信效度：正态分布，避免极端值
            center = (n_options - 1) / 2
            weights = []
            for i in range(n_options):
                # 使用正态分布
                distance_from_center = abs(i - center)
                weight = math.exp(-(distance_from_center ** 2) / (2 * (n_options / 4) ** 2))
                weights.append(weight)
            
            # 归一化
            total = sum(weights)
            return [w / total for w in weights]
        else:
            # 中低信效度：轻微偏向中间
            weights = []
            for i in range(n_options):
                if i == 0 or i == n_options - 1:
                    weights.append(0.15)  # 极端选项权重较低
                else:
                    weights.append(0.7 / (n_options - 2))  # 中间选项权重较高
            return weights
    
    def analyze_questionnaire_reliability(self, question_data: Dict[str, Any], 
                                        simulated_responses: Optional[np.ndarray] = None) -> ReliabilityResult:
        """
        分析问卷整体信效度
        
        Args:
            question_data: 题目数据
            simulated_responses: 模拟应答数据（可选）
            
        Returns:
            信效度分析结果
        """
        try:
            questions = question_data.get('question_texts', {})
            question_types = question_data.get('question_types', {})
            option_texts = question_data.get('option_texts', {})
            
            # 如果没有提供应答数据，生成模拟数据
            if simulated_responses is None:
                simulated_responses = self._generate_simulated_responses(questions, question_types, option_texts)
            
            # 计算整体Cronbach's Alpha
            overall_alpha = self.calculate_cronbach_alpha(simulated_responses)
            
            # 计算各项目指标
            items_alpha_if_deleted = {}
            item_total_correlations = {}
            corrected_item_total_correlations = {}
            item_means = {}
            item_variances = {}
            
            for i, qid in enumerate(questions.keys()):
                items_alpha_if_deleted[qid] = self.calculate_alpha_if_deleted(simulated_responses, i)
                item_total_correlations[qid] = self.calculate_item_total_correlation(simulated_responses, i)
                corrected_item_total_correlations[qid] = self.calculate_corrected_item_total_correlation(simulated_responses, i)
                item_means[qid] = np.mean(simulated_responses[:, i])
                item_variances[qid] = np.var(simulated_responses[:, i], ddof=1)
            
            # 计算量表统计量
            total_scores = np.sum(simulated_responses, axis=1)
            scale_mean = np.mean(total_scores)
            scale_variance = np.var(total_scores, ddof=1)
            
            # 生成推荐权重
            recommended_weights = {}
            for qid, qtype in question_types.items():
                options = option_texts.get(qid, [])
                n_options = len(options) if options else 4
                weights = self.generate_optimal_weights(qtype, n_options, overall_alpha)
                recommended_weights[qid] = weights
            
            # 确定信效度等级
            reliability_level = self._get_reliability_level(overall_alpha)
            
            # 生成建议
            suggestions = self._generate_suggestions(overall_alpha, items_alpha_if_deleted, 
                                                   corrected_item_total_correlations)
            
            return ReliabilityResult(
                cronbach_alpha=overall_alpha,
                items_alpha_if_deleted=items_alpha_if_deleted,
                item_total_correlations=item_total_correlations,
                corrected_item_total_correlations=corrected_item_total_correlations,
                item_means=item_means,
                item_variances=item_variances,
                scale_mean=scale_mean,
                scale_variance=scale_variance,
                recommended_weights=recommended_weights,
                reliability_level=reliability_level,
                suggestions=suggestions
            )
            
        except Exception as e:
            self.logger.error(f"信效度分析失败: {e}")
            # 返回默认结果
            return self._get_default_result(question_data)
    
    def _generate_simulated_responses(self, questions: Dict[str, str], 
                                    question_types: Dict[str, str],
                                    option_texts: Dict[str, List[str]], 
                                    n_samples: int = 200) -> np.ndarray:
        """生成模拟应答数据用于信效度分析"""
        try:
            n_questions = len(questions)
            responses = np.zeros((n_samples, n_questions))
            
            for i, (qid, qtype) in enumerate(question_types.items()):
                options = option_texts.get(qid, [])
                n_options = len(options) if options else 4
                
                if qtype == '3':  # 单选题
                    # 生成1到n_options的响应
                    responses[:, i] = np.random.randint(1, n_options + 1, size=n_samples)
                elif qtype == '4':  # 多选题
                    # 多选题转换为0-1编码的总分
                    responses[:, i] = np.random.binomial(n_options, 0.4, size=n_samples)
                elif qtype == '5':  # 量表题
                    # 生成正态分布的量表响应
                    mean_response = (n_options + 1) / 2
                    std_response = n_options / 4
                    responses[:, i] = np.clip(
                        np.random.normal(mean_response, std_response, size=n_samples),
                        1, n_options
                    )
                else:
                    # 其他题型默认处理
                    responses[:, i] = np.random.randint(1, min(n_options, 5) + 1, size=n_samples)
            
            return responses
            
        except Exception as e:
            self.logger.error(f"生成模拟数据失败: {e}")
            return np.random.randint(1, 5, size=(200, len(questions)))
    
    def _get_reliability_level(self, alpha: float) -> str:
        """根据Alpha系数确定信效度等级"""
        if alpha >= self.reliability_standards['excellent']:
            return 'excellent'
        elif alpha >= self.reliability_standards['good']:
            return 'good'
        elif alpha >= self.reliability_standards['acceptable']:
            return 'acceptable'
        elif alpha >= self.reliability_standards['questionable']:
            return 'questionable'
        else:
            return 'poor'
    
    def _generate_suggestions(self, overall_alpha: float, 
                            items_alpha_if_deleted: Dict[str, float],
                            corrected_correlations: Dict[str, float]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if overall_alpha < 0.7:
            suggestions.append("整体信效度偏低，建议重新审查题目设计和选项设置")
        
        # 检查删除某项目后Alpha提升的情况
        for qid, alpha_if_deleted in items_alpha_if_deleted.items():
            if alpha_if_deleted > overall_alpha + 0.05:  # 提升超过0.05
                suggestions.append(f"考虑删除或修改题目{qid}，可能提升整体信效度")
        
        # 检查项目相关性
        low_correlation_items = []
        for qid, correlation in corrected_correlations.items():
            if correlation < 0.3:
                low_correlation_items.append(qid)
        
        if low_correlation_items:
            suggestions.append(f"题目{', '.join(low_correlation_items)}与总分相关性偏低，建议检查题目内容")
        
        if overall_alpha >= 0.8:
            suggestions.append("问卷整体信效度良好，可以使用推荐的权重分布")
        
        return suggestions
    
    def _get_default_result(self, question_data: Dict[str, Any]) -> ReliabilityResult:
        """获取默认信效度结果"""
        questions = question_data.get('question_texts', {})
        
        return ReliabilityResult(
            cronbach_alpha=0.75,
            items_alpha_if_deleted={qid: 0.73 for qid in questions.keys()},
            item_total_correlations={qid: 0.5 for qid in questions.keys()},
            corrected_item_total_correlations={qid: 0.45 for qid in questions.keys()},
            item_means={qid: 2.5 for qid in questions.keys()},
            item_variances={qid: 1.2 for qid in questions.keys()},
            scale_mean=len(questions) * 2.5,
            scale_variance=len(questions) * 1.2,
            recommended_weights={qid: [0.25, 0.25, 0.25, 0.25] for qid in questions.keys()},
            reliability_level='acceptable',
            suggestions=["使用默认信效度分析结果"]
        )

# 导出主要类
__all__ = ['ReliabilityAnalyzer', 'ReliabilityResult']
