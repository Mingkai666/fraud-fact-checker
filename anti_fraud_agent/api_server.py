"""
REST API 服务模块
提供 HTTP 接口用于诈骗谣言核查
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fraud_anti_fraud.verifier import AntiFraudVerifier

app = FastAPI(
    title="诈骗谣言事实核查 API",
    description="基于网络搜索智能体的诈骗谣言信息事实核查系统",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化验证器
verifier = None


class ClaimRequest(BaseModel):
    """单个核查请求"""
    claim: str
    max_steps: Optional[int] = 8


class BatchClaimRequest(BaseModel):
    """批量核查请求"""
    claims: List[str]
    max_steps: Optional[int] = 8


class VerificationResult(BaseModel):
    """核查结果"""
    claim: str
    label: str
    fraud_type: Optional[str]
    confidence: float
    reasoning: str
    evidence: List[Dict[str, Any]]
    risk_level: str
    search_steps: int


@app.on_event("startup")
async def startup_event():
    """启动时初始化验证器"""
    global verifier
    try:
        verifier = AntiFraudVerifier()
        print("✓ 验证器初始化成功")
    except Exception as e:
        print(f"✗ 验证器初始化失败：{e}")
        verifier = None


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy" if verifier else "unhealthy",
        "verifier_ready": verifier is not None
    }


@app.post("/verify", response_model=VerificationResult)
async def verify_claim(request: ClaimRequest):
    """
    核查单个可疑信息
    
    - **claim**: 待核查的文本内容
    - **max_steps**: 最大搜索步数（默认 8）
    """
    if not verifier:
        raise HTTPException(status_code=503, detail="验证器未就绪")
        
    try:
        result = await verifier.verify_async(
            claim=request.claim,
            max_steps=request.max_steps
        )
        
        return VerificationResult(
            claim=request.claim,
            label=result.get('label', 'unverified'),
            fraud_type=result.get('fraud_type'),
            confidence=result.get('confidence', 0.0),
            reasoning=result.get('reasoning', ''),
            evidence=result.get('evidence', []),
            risk_level=result.get('risk_level', 'medium'),
            search_steps=result.get('search_steps', 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"核查失败：{str(e)}")


@app.post("/verify/batch")
async def verify_batch(request: BatchClaimRequest):
    """
    批量核查可疑信息
    
    返回每个 claim 的核查结果
    """
    if not verifier:
        raise HTTPException(status_code=503, detail="验证器未就绪")
        
    results = []
    for claim in request.claims:
        try:
            result = await verifier.verify_async(
                claim=claim,
                max_steps=request.max_steps
            )
            results.append({
                "claim": claim,
                "label": result.get('label', 'unverified'),
                "fraud_type": result.get('fraud_type'),
                "confidence": result.get('confidence', 0.0),
                "risk_level": result.get('risk_level', 'medium')
            })
        except Exception as e:
            results.append({
                "claim": claim,
                "error": str(e)
            })
            
    return {"results": results, "total": len(results)}


@app.get("/fraud-types")
async def get_fraud_types():
    """获取支持的诈骗类型列表"""
    return {
        "fraud_types": [
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
    }


if __name__ == "__main__":
    # 启动服务
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
