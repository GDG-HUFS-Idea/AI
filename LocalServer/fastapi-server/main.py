import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import logging

# .env 파일 로드
load_dotenv()

# FastAPI 인스턴스 생성
app = FastAPI()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수에서 GPT API 키 가져오기
GPT_API_KEY = os.getenv("GPT_API_KEY")

if not GPT_API_KEY:
    logger.error(" 환경 변수 GPT_API_KEY가 설정되지 않았습니다! .env 파일을 확인하세요.")
    raise ValueError("GPT_API_KEY가 설정되지 않았습니다! .env 파일을 확인하세요.")

# 요청 바디 형식 정의
class AnalysisRequest(BaseModel):
    prompt: str

async def call_gpt_api(prompt: str):
    """
    OpenAI GPT-4o mini API를 호출하여 응답을 반환하는 함수
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GPT_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    logger.info(f" GPT API 요청: {payload}")  # 요청 로그 추가

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            logger.info(f" GPT API 응답 코드: {response.status_code}")  # 응답 코드 확인
            logger.info(f" GPT API 응답 데이터: {response.text}")  # 응답 내용을 직접 출력

            # 응답 코드가 200이 아닐 경우 예외 처리
            if response.status_code != 200:
                logger.error(f" GPT API 호출 실패: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail=f"GPT API 호출 실패: {response.text}")

            return response.json()
    
    except httpx.HTTPStatusError as http_err:
        logger.error(f" HTTP 오류 발생: {http_err.response.status_code} - {http_err.response.text}")
        raise HTTPException(status_code=http_err.response.status_code, detail=f"HTTP 오류 발생: {http_err.response.text}")

    except httpx.RequestError as req_err:
        logger.error(f" 요청 오류 발생: {str(req_err)}")
        raise HTTPException(status_code=500, detail=f"요청 오류 발생: {str(req_err)}")

    except Exception as e:
        logger.error(f" GPT API 요청 중 알 수 없는 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GPT API 요청 중 오류 발생: {str(e)}")

@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    """
    NestJS에서 분석 요청을 받으면 GPT-4o mini API를 호출한 후 결과를 반환
    """
    try:
        gpt_response = await call_gpt_api(request.prompt)

        logger.info(f" 분석 완료: gpt_response={gpt_response}")

        return {
            "gpt_response": gpt_response
        }
    except HTTPException as http_exc:
        logger.error(f" 분석 요청 처리 중 HTTP 오류 발생: {http_exc.detail}")
        raise http_exc  # FastAPI 기본 HTTP 예외 반환
    except Exception as e:
        logger.error(f" 분석 요청 처리 중 알 수 없는 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"분석 요청 처리 중 오류 발생: {str(e)}")
