"""
评估系统模块
负责模型性能评估、混淆矩阵生成、错误分析和报告输出
"""

import json
from typing import List, Dict, Any
from pathlib import Path
from collections import defaultdict


class Evaluator:
    """诈骗核查系统评估器"""
    
    def __init__(self, fraud_types: List[str] = None):
        if fraud_types is None:
            self.fraud_types = [
                '刷单返利', '虚假投资理财', '虚假网络贷款',
                '冒充公检法', '冒充电商客服', '冒充熟人领导',
                '虚假购物服务', '婚恋交友', '社会谣言'
            ]
        else:
            self.fraud_types = fraud_types
            
        self.labels = ['fraud', 'rumor', 'truth', 'unverified']
        
    def calculate_metrics(self, predictions: List[Dict[str, Any]], 
                         ground_truth: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算整体评估指标"""
        if len(predictions) != len(ground_truth):
            raise ValueError("预测结果和真实标签数量不一致")
            
        # 统计混淆矩阵
        confusion_matrix = defaultdict(lambda: defaultdict(int))
        label_correct = defaultdict(int)
        label_total = defaultdict(int)
        
        for pred, truth in zip(predictions, ground_truth):
            pred_label = pred.get('label', 'unknown')
            true_label = truth.get('label', 'unknown')
            
            confusion_matrix[true_label][pred_label] += 1
            label_total[true_label] += 1
            
            if pred_label == true_label:
                label_correct[true_label] += 1
                
        # 计算各标签的精确率、召回率、F1
        metrics_per_label = {}
        for label in self.labels:
            tp = confusion_matrix[label][label]
            fp = sum(confusion_matrix[other][label] for other in self.labels if other != label)
            fn = sum(confusion_matrix[label][other] for other in self.labels if other != label)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            
            metrics_per_label[label] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'support': label_total[label]
            }
            
        # 计算宏平均和微平均
        macro_precision = sum(m['precision'] for m in metrics_per_label.values()) / len(self.labels)
        macro_recall = sum(m['recall'] for m in metrics_per_label.values()) / len(self.labels)
        macro_f1 = sum(m['f1'] for m in metrics_per_label.values()) / len(self.labels)
        
        total_tp = sum(label_correct.values())
        total_samples = sum(label_total.values())
        micro_accuracy = total_tp / total_samples if total_samples > 0 else 0.0
        
        return {
            'overall_accuracy': micro_accuracy,
            'macro_precision': macro_precision,
            'macro_recall': macro_recall,
            'macro_f1': macro_f1,
            'per_label_metrics': metrics_per_label,
            'confusion_matrix': dict(confusion_matrix),
            'total_samples': total_samples
        }
    
    def evaluate_by_fraud_type(self, predictions: List[Dict[str, Any]], 
                               ground_truth: List[Dict[str, Any]]) -> Dict[str, Any]:
        """按诈骗类型分别评估"""
        type_results = {}
        
        # 按诈骗类型分组
        type_groups = defaultdict(list)
        for i, truth in enumerate(ground_truth):
            fraud_type = truth.get('fraud_type', 'unknown')
            type_groups[fraud_type].append(i)
            
        # 对每种类型单独评估
        for fraud_type, indices in type_groups.items():
            type_preds = [predictions[i] for i in indices]
            type_truth = [ground_truth[i] for i in indices]
            
            metrics = self.calculate_metrics(type_preds, type_truth)
            type_results[fraud_type] = metrics
            
        return type_results
    
    def analyze_errors(self, predictions: List[Dict[str, Any]], 
                      ground_truth: List[Dict[str, Any]], 
                      top_k: int = 10) -> List[Dict[str, Any]]:
        """分析典型错误案例"""
        errors = []
        
        for i, (pred, truth) in enumerate(zip(predictions, ground_truth)):
            pred_label = pred.get('label', 'unknown')
            true_label = truth.get('label', 'unknown')
            
            if pred_label != true_label:
                error_case = {
                    'index': i,
                    'claim': truth.get('claim', ''),
                    'true_label': true_label,
                    'pred_label': pred_label,
                    'fraud_type': truth.get('fraud_type', 'unknown'),
                    'confidence': pred.get('confidence', 0.0),
                    'reasoning': pred.get('reasoning', '')
                }
                errors.append(error_case)
                
        # 按置信度排序，返回最典型的错误
        errors.sort(key=lambda x: x['confidence'], reverse=True)
        return errors[:top_k]
    
    def generate_report(self, predictions: List[Dict[str, Any]], 
                       ground_truth: List[Dict[str, Any]], 
                       output_file: str = None) -> Dict[str, Any]:
        """生成完整评估报告"""
        # 整体指标
        overall_metrics = self.calculate_metrics(predictions, ground_truth)
        
        # 按诈骗类型评估
        type_metrics = self.evaluate_by_fraud_type(predictions, ground_truth)
        
        # 错误分析
        error_cases = self.analyze_errors(predictions, ground_truth)
        
        report = {
            'overall_metrics': overall_metrics,
            'metrics_by_fraud_type': type_metrics,
            'error_cases': error_cases,
            'summary': {
                'total_samples': overall_metrics['total_samples'],
                'accuracy': overall_metrics['overall_accuracy'],
                'macro_f1': overall_metrics['macro_f1'],
                'num_error_cases': len(error_cases)
            }
        }
        
        # 保存报告
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                
        return report
    
    def print_summary(self, report: Dict[str, Any]):
        """打印评估摘要"""
        print("\n" + "="*60)
        print("诈骗核查系统评估报告")
        print("="*60)
        
        summary = report['summary']
        print(f"\n总样本数：{summary['total_samples']}")
        print(f"整体准确率：{summary['accuracy']:.4f}")
        print(f"宏平均 F1: {summary['macro_f1']:.4f}")
        print(f"错误案例数：{summary['num_error_cases']}")
        
        print("\n各类别性能:")
        per_label = report['overall_metrics']['per_label_metrics']
        for label, metrics in per_label.items():
            if metrics['support'] > 0:
                print(f"  {label}: P={metrics['precision']:.3f}, R={metrics['recall']:.3f}, F1={metrics['f1']:.3f} (n={metrics['support']})")
                
        print("\n各诈骗类型准确率:")
        type_metrics = report['metrics_by_fraud_type']
        for fraud_type, metrics in type_metrics.items():
            acc = metrics['overall_accuracy']
            print(f"  {fraud_type}: {acc:.3f}")
            
        if report['error_cases']:
            print("\n典型错误案例:")
            for i, case in enumerate(report['error_cases'][:3], 1):
                print(f"\n  案例{i}:")
                print(f"    文本：{case['claim'][:50]}...")
                print(f"    真实标签：{case['true_label']}, 预测标签：{case['pred_label']}")
                print(f"    诈骗类型：{case['fraud_type']}, 置信度：{case['confidence']:.3f}")
                
        print("="*60)


if __name__ == "__main__":
    # 示例用法
    evaluator = Evaluator()
    
    # 模拟预测结果和真实标签
    ground_truth = [
        {'claim': '刷单诈骗', 'label': 'fraud', 'fraud_type': '刷单返利'},
        {'claim': '投资诈骗', 'label': 'fraud', 'fraud_type': '虚假投资理财'},
        {'claim': '真实新闻', 'label': 'truth', 'fraud_type': '社会谣言'},
    ]
    
    predictions = [
        {'label': 'fraud', 'confidence': 0.95, 'fraud_type': '刷单返利'},
        {'label': 'fraud', 'confidence': 0.88, 'fraud_type': '虚假投资理财'},
        {'label': 'rumor', 'confidence': 0.75, 'fraud_type': '社会谣言'},
    ]
    
    report = evaluator.generate_report(predictions, ground_truth, "results/example_report.json")
    evaluator.print_summary(report)
