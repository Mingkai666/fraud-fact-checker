"""
数据流水线模块
负责数据的加载、清洗、验证、划分、增强和统计报告生成
"""

import json
import random
import os
from typing import List, Dict, Any
from pathlib import Path
import hashlib


class DataPipeline:
    """数据处理流水线"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.splits_dir = self.data_dir / "splits"
        self.splits_dir.mkdir(parents=True, exist_ok=True)
        
    def load_data(self, file_path: str) -> List[Dict[str, Any]]:
        """从JSONL或CSV文件加载数据"""
        data = []
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        if file_path.suffix == '.jsonl':
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))
        elif file_path.suffix == '.csv':
            import csv
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(dict(row))
        else:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")
            
        return data
    
    def validate_sample(self, sample: Dict[str, Any]) -> bool:
        """验证单个样本的完整性"""
        required_fields = ['claim', 'label', 'fraud_type']
        
        for field in required_fields:
            if field not in sample or not sample[field]:
                return False
                
        # 验证标签有效性
        valid_labels = ['fraud', 'rumor', 'truth', 'unverified']
        if sample['label'] not in valid_labels:
            return False
            
        # 验证诈骗类型
        valid_types = [
            '刷单返利', '虚假投资理财', '虚假网络贷款', 
            '冒充公检法', '冒充电商客服', '冒充熟人领导',
            '虚假购物服务', '婚恋交友', '社会谣言'
        ]
        if sample['fraud_type'] not in valid_types:
            return False
            
        return True
    
    def clean_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """清洗数据：去重、去除无效样本"""
        cleaned = []
        seen_claims = set()
        
        for sample in data:
            # 跳过无效样本
            if not self.validate_sample(sample):
                continue
                
            # 去重
            claim_hash = hashlib.md5(sample['claim'].encode('utf-8')).hexdigest()
            if claim_hash in seen_claims:
                continue
                
            seen_claims.add(claim_hash)
            cleaned.append(sample)
            
        return cleaned
    
    def split_data(self, data: List[Dict[str, Any]], 
                   train_ratio: float = 0.7,
                   val_ratio: float = 0.15,
                   test_ratio: float = 0.15,
                   stratify_by: str = 'fraud_type') -> Dict[str, List[Dict[str, Any]]]:
        """按比例划分数据集，支持分层抽样"""
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 0.01:
            raise ValueError("比例之和必须为1")
            
        # 按指定字段分组
        groups = {}
        for sample in data:
            key = sample.get(stratify_by, 'default')
            if key not in groups:
                groups[key] = []
            groups[key].append(sample)
            
        # 对每组进行分层抽样
        train_data, val_data, test_data = [], [], []
        
        for key, samples in groups.items():
            random.shuffle(samples)
            n = len(samples)
            n_train = max(1, int(n * train_ratio))
            n_val = max(1, int(n * val_ratio))
            
            train_data.extend(samples[:n_train])
            val_data.extend(samples[n_train:n_train+n_val])
            test_data.extend(samples[n_train+n_val:])
            
        return {
            'train': train_data,
            'val': val_data,
            'test': test_data
        }
    
    def save_data(self, data: List[Dict[str, Any]], file_path: str):
        """保存数据到JSONL文件"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for sample in data:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
                
    def generate_report(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成数据统计报告"""
        report = {
            'total_samples': len(data),
            'label_distribution': {},
            'fraud_type_distribution': {},
            'risk_level_distribution': {},
            'avg_claim_length': 0,
            'samples_with_evidence': 0
        }
        
        if not data:
            return report
            
        # 统计标签分布
        for sample in data:
            label = sample.get('label', 'unknown')
            report['label_distribution'][label] = report['label_distribution'].get(label, 0) + 1
            
            # 统计诈骗类型分布
            fraud_type = sample.get('fraud_type', 'unknown')
            report['fraud_type_distribution'][fraud_type] = report['fraud_type_distribution'].get(fraud_type, 0) + 1
            
            # 统计风险等级分布
            risk_level = sample.get('risk_level', 'unknown')
            report['risk_level_distribution'][risk_level] = report['risk_level_distribution'].get(risk_level, 0) + 1
            
            # 统计平均文本长度
            report['avg_claim_length'] += len(sample.get('claim', ''))
            
            # 统计有证据的样本数
            if sample.get('evidence'):
                report['samples_with_evidence'] += 1
                
        report['avg_claim_length'] /= len(data)
        
        return report
    
    def process_full_pipeline(self, input_file: str, output_dir: str = None):
        """执行完整的数据处理流水线"""
        if output_dir is None:
            output_dir = self.splits_dir
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
        print(f"加载数据: {input_file}")
        data = self.load_data(input_file)
        print(f"原始数据量: {len(data)}")
        
        print("清洗数据...")
        cleaned_data = self.clean_data(data)
        print(f"清洗后数据量: {len(cleaned_data)}")
        
        print("划分数据集...")
        splits = self.split_data(cleaned_data)
        
        # 保存各部分数据
        for split_name, split_data in splits.items():
            output_file = output_dir / f"{split_name}.jsonl"
            self.save_data(split_data, output_file)
            print(f"保存 {split_name} 集到 {output_file} ({len(split_data)} 条)")
            
        # 生成并保存报告
        report = self.generate_report(cleaned_data)
        report_file = output_dir / "statistics.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"统计报告保存到 {report_file}")
        
        return splits, report


if __name__ == "__main__":
    # 示例用法
    pipeline = DataPipeline()
    
    # 处理测试数据集
    input_file = "data/test_dataset.jsonl"
    if os.path.exists(input_file):
        splits, report = pipeline.process_full_pipeline(input_file)
        print("\n数据统计报告:")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"输入文件不存在: {input_file}")
