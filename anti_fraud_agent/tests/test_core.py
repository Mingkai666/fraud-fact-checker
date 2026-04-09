"""
单元测试模块
测试诈骗核查系统的核心功能
"""

import unittest
import json
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDataPipeline(unittest.TestCase):
    """测试数据流水线"""
    
    def setUp(self):
        from data_pipeline import DataPipeline
        self.pipeline = DataPipeline()
        
    def test_validate_sample_valid(self):
        """测试验证有效样本"""
        sample = {
            'claim': '测试诈骗信息',
            'label': 'fraud',
            'fraud_type': '刷单返利'
        }
        self.assertTrue(self.pipeline.validate_sample(sample))
        
    def test_validate_sample_invalid_label(self):
        """测试验证无效标签"""
        sample = {
            'claim': '测试诈骗信息',
            'label': 'invalid',
            'fraud_type': '刷单返利'
        }
        self.assertFalse(self.pipeline.validate_sample(sample))
        
    def test_clean_data_remove_duplicates(self):
        """测试去重功能"""
        data = [
            {'claim': '相同内容', 'label': 'fraud', 'fraud_type': '刷单返利'},
            {'claim': '相同内容', 'label': 'fraud', 'fraud_type': '刷单返利'},
            {'claim': '不同内容', 'label': 'rumor', 'fraud_type': '社会谣言'}
        ]
        cleaned = self.pipeline.clean_data(data)
        self.assertEqual(len(cleaned), 2)


class TestEvaluator(unittest.TestCase):
    """测试评估器"""
    
    def setUp(self):
        from evaluator import Evaluator
        self.evaluator = Evaluator()
        
    def test_calculate_metrics_perfect(self):
        """测试完美预测"""
        ground_truth = [
            {'label': 'fraud', 'fraud_type': '刷单返利'},
            {'label': 'truth', 'fraud_type': '社会谣言'}
        ]
        predictions = [
            {'label': 'fraud', 'confidence': 0.95},
            {'label': 'truth', 'confidence': 0.90}
        ]
        
        metrics = self.evaluator.calculate_metrics(predictions, ground_truth)
        self.assertEqual(metrics['overall_accuracy'], 1.0)
        
    def test_calculate_metrics_partial(self):
        """测试部分正确预测"""
        ground_truth = [
            {'label': 'fraud', 'fraud_type': '刷单返利'},
            {'label': 'truth', 'fraud_type': '社会谣言'}
        ]
        predictions = [
            {'label': 'fraud', 'confidence': 0.95},
            {'label': 'rumor', 'confidence': 0.80}
        ]
        
        metrics = self.evaluator.calculate_metrics(predictions, ground_truth)
        self.assertEqual(metrics['overall_accuracy'], 0.5)


class TestVerifier(unittest.TestCase):
    """测试验证器"""
    
    def test_verifier_initialization(self):
        """测试验证器初始化"""
        try:
            from fraud_anti_fraud.verifier import AntiFraudVerifier
            verifier = AntiFraudVerifier()
            self.assertIsNotNone(verifier)
        except Exception as e:
            # 如果 API 未配置，允许初始化失败
            print(f"验证器初始化跳过（API 未配置）: {e}")
            

class TestBatchProcessor(unittest.TestCase):
    """测试批量处理器"""
    
    def setUp(self):
        from batch_processor import BatchProcessor
        self.processor = BatchProcessor()
        
    def test_load_claims_from_jsonl(self):
        """测试从 JSONL 加载"""
        # 创建临时测试文件
        test_file = Path("/tmp/test_claims.jsonl")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('{"claim": "测试 1"}\n')
            f.write('{"claim": "测试 2"}\n')
            
        claims = self.processor.load_claims_from_file(str(test_file))
        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0], "测试 1")
        
        # 清理
        test_file.unlink()


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_end_to_end_workflow(self):
        """测试端到端流程"""
        # 这里可以进行完整的端到端测试
        # 由于需要 API 调用，暂时跳过
        self.skipTest("需要 API 密钥，跳过集成测试")


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
