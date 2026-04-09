"""
Web 演示界面模块
使用 Streamlit 构建交互式诈骗核查演示系统
"""

import streamlit as st
import json
import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fraud_anti_fraud.verifier import AntiFraudVerifier

# 页面配置
st.set_page_config(
    page_title="诈骗谣言事实核查系统",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .result-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .fraud-alert {
        background-color: #ffe6e6;
        border-left: 5px solid #ff4444;
    }
    .safe-alert {
        background-color: #e6ffe6;
        border-left: 5px solid #44ff44;
    }
    .warning-alert {
        background-color: #fff9e6;
        border-left: 5px solid #ffaa00;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<h1 class="main-header">🛡️ 诈骗谣言事实核查系统</h1>', unsafe_allow_html=True)
st.markdown("基于网络搜索智能体的诈骗信息自动识别与验证平台")

# 侧边栏
with st.sidebar:
    st.header("系统信息")
    st.info("本系统采用迭代式检索验证框架，自动搜索权威证据进行事实核查。")
    
    st.subheader("支持的诈骗类型")
    fraud_types = [
        "刷单返利",
        "虚假投资理财", 
        "虚假网络贷款",
        "冒充公检法",
        "冒充电商客服",
        "冒充熟人领导",
        "虚假购物服务",
        "婚恋交友",
        "社会谣言"
    ]
    for ft in fraud_types:
        st.write(f"• {ft}")
        
    st.subheader("使用说明")
    st.markdown("""
    1. 在下方输入框输入可疑信息
    2. 点击'开始核查'按钮
    3. 等待系统自动搜索和分析
    4. 查看核查结果和证据链
    """)

# 初始化验证器
@st.cache_resource
def get_verifier():
    """获取验证器实例（缓存）"""
    try:
        return AntiFraudVerifier()
    except Exception as e:
        st.error(f"验证器初始化失败：{e}")
        return None

verifier = get_verifier()

# 主输入区域
st.subheader("📝 输入可疑信息")
claim_input = st.text_area(
    "请输入需要核查的信息内容：",
    height=150,
    placeholder="例如：'某投资平台承诺月收益 30%，保本保息，限时抢购...'"
)

col1, col2 = st.columns([1, 4])
with col1:
    max_steps = st.slider("最大搜索步数", 1, 10, 5)
    
with col2:
    verify_button = st.button("🔍 开始核查", type="primary", use_container_width=True)

# 核查结果显示
if verify_button and claim_input:
    if not verifier:
        st.error("验证器未就绪，请检查 API 配置")
    else:
        with st.spinner("正在核查中，请稍候..."):
            try:
                # 执行核查
                result = verifier.verify(claim_input, max_steps=max_steps)
                
                # 显示结果
                st.subheader("📊 核查结果")
                
                # 风险等级标识
                risk_level = result.get('risk_level', 'medium')
                label = result.get('label', 'unverified')
                
                if label == 'fraud':
                    alert_class = "fraud-alert"
                    alert_icon = "🚨"
                    alert_text = "高危预警：该信息疑似诈骗"
                elif label == 'rumor':
                    alert_class = "warning-alert"
                    alert_icon = "⚠️"
                    alert_text = "风险提示：该信息可能为谣言"
                elif label == 'truth':
                    alert_class = "safe-alert"
                    alert_icon = "✅"
                    alert_text = "安全提示：该信息可信度较高"
                else:
                    alert_class = "warning-alert"
                    alert_icon = "❓"
                    alert_text = "无法确定：证据不足，无法判断"
                
                st.markdown(f'<div class="result-box {alert_class}"><h3>{alert_icon} {alert_text}</h3></div>', 
                           unsafe_allow_html=True)
                
                # 详细信息
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("置信度", f"{result.get('confidence', 0):.2%}")
                    st.metric("诈骗类型", result.get('fraud_type', '未知'))
                    st.metric("搜索步数", result.get('search_steps', 0))
                    
                with col2:
                    st.metric("风险等级", risk_level.upper())
                    st.metric("判定标签", label.upper())
                
                # 推理过程
                st.subheader("🧠 推理分析")
                reasoning = result.get('reasoning', '无推理过程')
                st.write(reasoning)
                
                # 证据列表
                evidence = result.get('evidence', [])
                if evidence:
                    st.subheader("📚 参考证据")
                    for i, ev in enumerate(evidence, 1):
                        with st.expander(f"证据{i}: {ev.get('title', '无标题')}"):
                            st.write(f"**来源**: {ev.get('source', '未知')}")
                            st.write(f"**摘要**: {ev.get('snippet', '无摘要')}")
                            if ev.get('url'):
                                st.markdown(f"[查看详情]({ev['url']})")
                else:
                    st.info("未找到相关证据")
                
                # 时间戳
                st.caption(f"核查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
            except Exception as e:
                st.error(f"核查过程中出错：{str(e)}")
                st.exception(e)

elif verify_button and not claim_input:
    st.warning("请输入需要核查的信息内容")

# 示例案例
st.subheader("💡 示例案例")
examples = [
    "兼职刷单，日赚 300-500 元，时间自由，在家可做",
    "某投资公司推出新项目，月收益 20%-30%，保本保息，限额认购",
    "公安局紧急通知：您的银行卡涉嫌洗钱，请立即转账到安全账户",
    "微信好友借钱：我手机丢了，这是新号，急需用钱帮忙转一下"
]

selected_example = st.selectbox("选择示例快速测试：", [""] + examples)
if selected_example:
    st.session_state.claim_input = selected_example
    st.rerun()

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>本项目基于 FIRE 框架开发 | 仅供科研和演示使用</p>
</div>
""", unsafe_allow_html=True)
