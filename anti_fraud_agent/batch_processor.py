"""
批量处理工具模块
支持对大量可疑信息进行批量核查
"""

import json
import csv
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fraud_anti_fraud.verifier import AntiFraudVerifier


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.verifier = AntiFraudVerifier()
        
    def load_claims_from_file(self, file_path: str) -> List[str]:
        """从文件加载待核查的 claims"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在：{file_path}")
            
        claims = []
        
        if file_path.suffix == '.jsonl':
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        claims.append(data.get('claim', ''))
                        
        elif file_path.suffix == '.csv':
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    claim = row.get('claim', row.get('text', ''))
                    if claim:
                        claims.append(claim)
                        
        elif file_path.suffix == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        claims.append(line)
        else:
            raise ValueError(f"不支持的文件格式：{file_path.suffix}")
            
        return claims
    
    def process_batch(self, claims: List[str], 
                     max_steps: int = 8,
                     output_file: str = None,
                     progress_callback=None) -> List[Dict[str, Any]]:
        """
        批量处理 claims
        
        Args:
            claims: 待核查的文本列表
            max_steps: 每个 claim 的最大搜索步数
            output_file: 结果输出文件路径
            progress_callback: 进度回调函数 (current, total, result)
            
        Returns:
            核查结果列表
        """
        results = []
        total = len(claims)
        
        print(f"开始批量处理，共 {total} 条数据")
        print(f"最大搜索步数：{max_steps}")
        print("-" * 60)
        
        start_time = time.time()
        
        for i, claim in enumerate(claims, 1):
            try:
                print(f"[{i}/{total}] 正在核查...", end=" ")
                
                # 执行核查
                result = self.verifier.verify(claim, max_steps=max_steps)
                
                # 添加元信息
                result['claim'] = claim
                result['index'] = i
                result['timestamp'] = datetime.now().isoformat()
                
                results.append(result)
                
                # 显示简要结果
                label = result.get('label', 'unknown')
                fraud_type = result.get('fraud_type', 'unknown')
                confidence = result.get('confidence', 0)
                print(f"{label} ({fraud_type}, {confidence:.2f})")
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(i, total, result)
                    
            except Exception as e:
                print(f"错误：{str(e)}")
                error_result = {
                    'claim': claim,
                    'index': i,
                    'error': str(e),
                    'label': 'error',
                    'timestamp': datetime.now().isoformat()
                }
                results.append(error_result)
                
            # 避免请求过快
            if i < total:
                time.sleep(1)
                
        elapsed_time = time.time() - start_time
        
        # 统计信息
        success_count = sum(1 for r in results if r.get('label') != 'error')
        fraud_count = sum(1 for r in results if r.get('label') == 'fraud')
        rumor_count = sum(1 for r in results if r.get('label') == 'rumor')
        truth_count = sum(1 for r in results if r.get('label') == 'truth')
        
        print("\n" + "=" * 60)
        print("批量处理完成")
        print(f"总耗时：{elapsed_time:.2f} 秒")
        print(f"平均每条：{elapsed_time/total:.2f} 秒")
        print(f"成功处理：{success_count}/{total}")
        print(f"诈骗识别：{fraud_count} 条")
        print(f"谣言识别：{rumor_count} 条")
        print(f"真实信息：{truth_count} 条")
        print("=" * 60)
        
        # 保存结果
        if output_file:
            self.save_results(results, output_file)
            
        return results
    
    def save_results(self, results: List[Dict[str, Any]], output_file: str):
        """保存结果到文件"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_path.suffix == '.jsonl':
            with open(output_path, 'w', encoding='utf-8') as f:
                for result in results:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
                    
        elif output_path.suffix == '.csv':
            if results:
                fieldnames = ['index', 'claim', 'label', 'fraud_type', 
                             'confidence', 'risk_level', 'reasoning', 
                             'search_steps', 'timestamp', 'error']
                
                with open(output_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for result in results:
                        row = {k: result.get(k, '') for k in fieldnames}
                        # 简化 reasoning 字段（避免 CSV 格式问题）
                        if isinstance(row['reasoning'], str):
                            row['reasoning'] = row['reasoning'].replace('\n', ' ')[:500]
                        writer.writerow(row)
                        
        elif output_path.suffix == '.json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        else:
            # 默认保存为 JSONL
            with open(output_path.with_suffix('.jsonl'), 'w', encoding='utf-8') as f:
                for result in results:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
                    
        print(f"结果已保存到：{output_path}")
        

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="批量核查诈骗谣言")
    parser.add_argument("input_file", help="输入文件路径（JSONL/CSV/TXT）")
    parser.add_argument("-o", "--output", help="输出文件路径", default="results/batch_results.jsonl")
    parser.add_argument("-s", "--steps", type=int, help="最大搜索步数", default=8)
    parser.add_argument("--format", choices=['jsonl', 'csv', 'json'], 
                       help="输出格式", default='jsonl')
    
    args = parser.parse_args()
    
    # 调整输出文件格式
    output_file = args.output
    if '.' not in os.path.basename(output_file):
        output_file += f".{args.format}"
        
    # 创建处理器并运行
    processor = BatchProcessor()
    
    try:
        claims = processor.load_claims_from_file(args.input_file)
        processor.process_batch(
            claims,
            max_steps=args.steps,
            output_file=output_file
        )
    except Exception as e:
        print(f"错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
