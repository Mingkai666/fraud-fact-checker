# 基于网络搜索智能体的诈骗谣言事实核查系统

## 项目状态：✅ 已完成核心开发

### 已完成内容

1. **核心模块** (3个Python文件)
   - `core/verifier.py` - 验证器，集成阿里百炼API和9大类诈骗特征库
   - `core/search_engine.py` - 搜索引擎，SerperAPI集成
   - `core/agent.py` - 智能代理，迭代式搜索 - 验证决策控制

2. **测试数据集** 
   - `data/test_dataset.jsonl` - 54条高质量样本（9大类×6条/类）

3. **测试脚本**
   - `run_full_test.py` - 端到端批量测试

### 运行方式

```bash
# 1. 安装依赖
pip install dashscope requests

# 2. 设置环境变量
export DASHSCOPE_API_KEY="sk-9e5a9b1755de4b7ea7a1653cab64b919"
export SERPER_API_KEY="85a6388fae2105bb525f11a0c3d3aa4cc1d56bc0"

# 3. 运行测试
python run_full_test.py
```

### 9大类诈骗类型

1. 刷单返利
2. 虚假投资理财
3. 虚假网络贷款
4. 冒充公检法
5. 冒充电商客服
6. 冒充熟人领导
7. 虚假购物服务
8. 婚恋交友 (杀猪盘)
9. 社会谣言

### 技术架构

- **LLM后端**: 阿里百炼 Qwen-Max
- **搜索引擎**: SerperAPI (Google Search)
- **分类体系**: 国家反诈中心 9 大高发诈骗类型
- **数据集**: 54 条均衡分布测试样本
