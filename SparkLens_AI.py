from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, Field, validator
import httpx
import os
import json
import re
import html
import logging
import asyncio
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from typing import List, Optional

# 비동기 캐싱을 위한 Redis 초기화
app = FastAPI()
@app.on_event("startup")
async def startup():
    FastAPICache.init(RedisBackend("redis://localhost:6379"))  # 캐싱 성능 개선

# 입력 데이터 검증 강화
class SimilarService(BaseModel):
    name: str = Field(..., min_length=2)
    difference: str
    similarityScore: float = Field(..., ge=0, le=1)  # 0~1 범위 검증
    source: Optional[str] = None  # 데이터 출처 추적

class SWOTAnalysis(BaseModel):
    strengths: List[str] = Field(..., min_items=3)  # 최소 3개 항목 강제
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]

    @validator('*', each_item=True)
    def check_length(cls, v):
        if len(v) < 10:  # 항목별 최소 길이 검증
            raise ValueError('Each item must be at least 10 characters')
        return v

class MarketAnalysis(BaseModel):
    tam: str = Field(..., regex=r"\$?\d+억?|\d+ million USD")  # 형식 검증
    sam: str
    cagr: str = Field(..., regex=r"\d+%")  # 성장률 형식 강제
    dataSources: List[str] = Field(..., min_items=1)  # 출처 필수

# 보안 강화: 입력 전처리
def sanitize_input(text: str) -> str:
    """XSS & SQL 인젝션 방지"""
    sanitized = html.escape(text)
    return re.sub(r"[;'\"{}]", "", sanitized)  # 위험 문자 제거

# RAG 시스템 연동 (예시 구현)
async def retrieve_rag_data(idea: str) -> dict:
    """실제 구현 시 벡터 DB 검색 로직 추가"""
    return {
        "market_size": "2030년 $1.2조 (출처: Gartner 2024)",
        "similar_services": [
            {"name": "ServiceA", "score": 0.85, "source": "Crunchbase"}
        ]
    }

# 구조화된 프롬프트 엔지니어링
def generate_prompt(data: AnalysisRequest, rag_data: dict) -> str:
    """JSON 출력 형식 템플릿 포함"""
    return f"""
    ## 분석 요구사항
    1. 유사 서비스 비교 (차이점, 유사도 점수)
    2. RAG 데이터 기반 시장 규모 추정
    3. 출처 명시 필수

    ## 출력 형식
    {{
        "similarServices": [{{
            "name": "서비스명",
            "difference": "차이점 (출처)",
            "similarityScore": 0.95,
            "source": "출처"
        }}],
        "marketAnalysis": {{
            "tam": "$100억 (출처)",
            "sam": "$30억",
            "cagr": "12%",
            "dataSources": ["출처1"]
        }},
        "swotAnalysis": {{
            "strengths": ["기술 우위 (출처: 특허 DB)"],
            "weaknesses": ["자본력 부족 (출처: 유사 서비스)"],
            "opportunities": ["신시장 개척 (출처: 보고서)"],
            "threats": ["규제 강화 (출처: 뉴스)"]
        }}
    }}
    """

# API 엔드포인트 최적화
@app.post("/analyze", response_model=AnalysisResponse)
@cache(expire=600)  # 10분 캐싱으로 성능 향상
async def analyze_idea(
    request: AnalysisRequest,
    user_id: str = Query(..., regex=r"^[a-zA-Z0-9_-]{{5,20}}$")  # 사용자 ID 검증
):
    try:
        # 병렬 처리: RAG 검색과 프롬프트 생성 동시 실행
        rag_data, prompt = await asyncio.gather(
            retrieve_rag_data(request.summary),
            generate_prompt(request, {})
        )

        # GPT API 호출 최적화
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GPT_API_URL,
                headers={"Authorization": f"Bearer {GPT_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{
                        "role": "system",
                        "content": "JSON 형식을 엄격히 준수하세요"
                    }, {
                        "role": "user", 
                        "content": prompt
                    }],
                    "temperature": 0.3,  # 낮은 창의성 설정
                    "response_format": {"type": "json_object"}  # JSON 강제
                },
                timeout=30  # 타임아웃 설정
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]

        # 응답 검증 및 변환
        return AnalysisResponse.parse_raw(content)

    except httpx.HTTPStatusError as e:
        logging.error(f"API Error: {e.response.text}")  # 에러 로깅 강화
        raise HTTPException(status_code=503, detail="External service error")
    except json.JSONDecodeError:
        raise HTTPException(500, "Response parsing failed")

# 모니터링을 위한 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)