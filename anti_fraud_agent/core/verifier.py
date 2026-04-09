"""
诈骗谣言验证器 - 集成阿里百炼 API
"""
import json
import re
import os
from typing import Dict, List, Any

try:
    import dashscope
    from dashscope import Generation
except ImportError:
    print("请安装 dashscope: pip install dashscope")
    dashscope = None


class AntiFraudVerifier:
    """诈骗谣言专用验证器"""
    
    FRAUD_TYPES = {
        "刷单返利": "通过承诺高额返利诱导受害者先垫付资金的诈骗",
        "虚假投资理财": "以高收益为诱饵诱导投资的诈骗，包括虚假股票、基金、虚拟货币等",
        "虚假网络贷款": "以贷款为名骗取费用的诈骗，特征包括'无抵押''秒批'等",
        "冒充公检法": "冒充公安、检察院、法院工作人员实施诈骗，关键词'安全账户'",
        "冒充电商客服": "冒充淘宝、京东等平台客服，以退款、理赔为由索要信息",
        "冒充熟人领导": "冒充亲友、同事、领导借钱或要求转账",
        "虚假购物服务": "低价销售商品/服务骗取钱财，包括假手机、假证件等",
        "婚恋交友 (杀猪盘)": "通过网络交友建立信任后诱导投资或借钱",
        "社会谣言": "传播虚假信息造成社会恐慌，包括伪科学、灾害谣言等"
    }
    
    def __init__(self, api_key: str = None, model: str = "qwen-max"):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量")
        
        if dashscope:
            dashscope.api_key = self.api_key
        self.model = model
    
    def verify(self, claim: str, search_results: List[Dict] = None) -> Dict[str, Any]:
        """验证可疑文本"""
        
        # 构建提示词
        prompt = self._build_prompt(claim, search_results)
        
        try:
            if not dashscope:
                return self._fallback_analysis(claim, "dashscope 未安装")
            
            response = Generation.call(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500
            )
            
            if response.status_code == 200:
                # 新版 API 返回格式：response.output.text
                result_text = response.output.get('text', '') if isinstance(response.output, dict) else str(response.output)
                if not result_text and hasattr(response.output, 'choices') and response.output.choices:
                    result_text = response.output.choices[0].message.content
                return self._parse_result(result_text, claim)
            else:
                return self._fallback_analysis(claim, f"API 错误：{response.message}")
                
        except Exception as e:
            return self._fallback_analysis(claim, str(e))
    
    def _build_prompt(self, claim: str, search_results: List[Dict] = None) -> str:
        """构建验证提示词"""
        
        system_instruction = """你是一个专业的反诈骗事实核查专家。判断给定文本是否为诈骗或谣言。

## 9 大类诈骗/谣言定义：
"""
        for fraud_type, definition in self.FRAUD_TYPES.items():
            system_instruction += f"- **{fraud_type}**: {definition}\n"
        
        system_instruction += """
## 输出格式（严格 JSON）：
{
    "label": "fraud|rumor|truth|unverified",
    "fraud_type": "具体类型",
    "confidence": 0.0-1.0,
    "risk_level": "high|medium|low",
    "reasoning": "判定依据",
    "warning": "风险警示"
}

## 待核查文本：
""" + claim
        
        if search_results:
            system_instruction += "\n\n## 搜索结果：\n"
            for i, r in enumerate(search_results[:3], 1):
                system_instruction += f"{i}. {r.get('title', '')}: {r.get('snippet', '')}\n"
        
        return system_instruction
    
    def _parse_result(self, result_text: str, claim: str) -> Dict[str, Any]:
        """解析 LLM 输出"""
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            try:
                result = json.loads(json_match.group())
                result['claim'] = claim
                result['raw_output'] = result_text
                return result
            except:
                pass
        
        # 如果没有 JSON，尝试从文本中提取关键信息
        label = 'unverified'
        if '诈骗' in result_text or '欺诈' in result_text:
            label = 'fraud'
        elif '谣言' in result_text or '虚假' in result_text:
            label = 'rumor'
        elif '真实' in result_text or '属实' in result_text:
            label = 'truth'
        
        return {
            'claim': claim,
            'label': label,
            'fraud_type': '未知',
            'confidence': 0.5,
            'risk_level': 'medium',
            'reasoning': result_text[:200] if result_text else '无法解析输出',
            'warning': '建议通过官方渠道核实',
            'raw_output': result_text
        }
    
    def _fallback_analysis(self, claim: str, error_msg: str) -> Dict[str, Any]:
        """降级分析"""
        fraud_keywords = [
            ('刷单', '刷单返利'), ('返利', '刷单返利'),
            ('投资', '虚假投资理财'), ('理财', '虚假投资理财'),
            ('贷款', '虚假网络贷款'), ('秒批', '虚假网络贷款'),
            ('公安局', '冒充公检法'), ('安全账户', '冒充公检法'),
            ('客服', '冒充电商客服'), ('退款', '冒充电商客服'),
            ('我是你', '冒充熟人领导'), ('借钱', '冒充熟人领导'),
            ('特价', '虚假购物服务'), ('低价', '虚假购物服务'),
            ('交友', '婚恋交友 (杀猪盘)'), ('网恋', '婚恋交友 (杀猪盘)'),
        ]
        
        detected_type = '社会谣言'
        for keyword, fraud_type in fraud_keywords:
            if keyword in claim:
                detected_type = fraud_type
                break
        
        return {
            'claim': claim,
            'label': 'unverified',
            'fraud_type': detected_type,
            'confidence': 0.3,
            'risk_level': 'medium',
            'reasoning': f'API 调用失败 ({error_msg[:80]})，基于关键词初步识别为{detected_type}',
            'warning': '系统暂时无法深度分析，建议通过官方渠道核实',
            'error': error_msg
        }


if __name__ == "__main__":
    # 简单测试
    verifier = AntiFraudVerifier()
    test_claims = [
        "动动手指刷单，日赚 300-500 元！",
        "我是公安局的，你涉嫌洗钱，请转账到安全账户",
    ]
    
    for claim in test_claims:
        print(f"\n测试：{claim}")
        result = verifier.verify(claim)
        print(f"结果：{result.get('label')} - {result.get('fraud_type')}")
        print(f"置信度：{result.get('confidence')}")
