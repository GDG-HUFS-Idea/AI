from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os

# FastAPI 애플리케이션 생성
app = FastAPI()

# OpenAI API 키 설정 (환경 변수 사용)
GPT_API_KEY = os.getenv("GPT_API_KEY")
GPT_API_URL = "https://api.openai.com/v1/chat/completions"  # GPT-4o mini 모델의 API 엔드포인트

# 데이터 모델 정의
class AnalysisRequest(BaseModel):
    ideaName: str
    summary: str
    features: list
    targetAudience: str

class AnalysisResponse(BaseModel):
    similarServices: list
    marketAnalysis: dict
    swotAnalysis: dict

# 백엔드에서 요청 처리
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_idea(request: AnalysisRequest):
    try:
        # 1. 프롬프트 생성
        prompt = generate_prompt(request)

        # 2. GPT-4o mini 모델 API 호출
        gpt_response = await call_gpt_api(prompt)

        # 3. 응답 데이터 파싱 및 변환
        result = parse_gpt_response(gpt_response)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 프롬프트 생성 함수
def generate_prompt(data: AnalysisRequest) -> str:
    return f"""
    Analyze the following business idea:
    - Idea Name: {data.ideaName}
    - Summary: {data.summary}
    - Features: {', '.join(data.features)}
    - Target Audience: {data.targetAudience}

    Provide the following details:
    1. List of similar services and how they differ.
    2. Market size, growth rate, and key trends.
    3. SWOT analysis (strengths, weaknesses, opportunities, threats).
    """

# GPT-4o mini 모델 API 호출 함수
async def call_gpt_api(prompt: str) -> dict:
    headers = {
        "Authorization": f"Bearer {GPT_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",  # GPT-4o mini 모델
        "messages": [
            {"role": "system", "content": "You are an expert assistant for analyzing business ideas."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    # 비동기 HTTP 요청
    async with httpx.AsyncClient() as client:
        response = await client.post(GPT_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"GPT API Error: {response.text}")
    
    return response.json()

# GPT API 응답 파싱 함수
def parse_gpt_response(gpt_response: dict) -> dict:
    # GPT-4o mini 모델의 응답 내용을 가정한 파싱
    content = gpt_response["choices"][0]["message"]["content"]

    # 아래는 결과를 가공한 예시입니다.
    return {
        "similarServices": [
            {"name": "Example Service 1", "difference": "This service focuses on X."},
            {"name": "Example Service 2", "difference": "This service provides Y."}
        ],
        "marketAnalysis": {
            "size": "3 billion USD",
            "growthRate": "10% per year",
            "trends": ["AI integration", "Personalized services"]
        },
        "swotAnalysis": {
            "strengths": "Innovative approach, advanced technology",
            "weaknesses": "High development costs",
            "opportunities": "Rapidly growing market",
            "threats": "Strong competition"
        }
    }