import os
import json
import logging
import asyncio
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from fastapi.responses import StreamingResponse
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv(override=True, encoding="utf-8")
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("🚨 OPENAI_API_KEY 환경 변수가 설정되지 않았습니다!")

client = OpenAI(api_key=api_key)

app = FastAPI()
import json

market_analysis_dict = {
 "summary": "입력된 프로젝트 데이터에 대한 한 줄 요약 (1문장)",

  "summary_review": "해당 아이디어에 대한 간단한 평가 (1~2문장)",
  
  "market_statistics": {
    "score": 50,
    
    "industry_path": "대분류 > 중분류 > 소분류 > 세분류",
    
    "domestic_market_trend_chart": {
      "data": [
        {
          "year": 2015, 
          "market_size": {
            "volume": 2400000000000,
            "currency": "KRW"
          },
          "growth_rate": 0.25
        },

      ],
      "source": "출처 URL"
    },
    
    "global_market_trend_chart": {
      "data": [
        {
          "year": 2015,
          "market_size": {
            "volume": 200000000000,
            "currency": "USD"
          },
          "growth_rate": 0.25
        },
      ],
      "source": "출처 URL"
    },
    
    "domestic_average_revenue": {
      "volume": 23000000000,
      "currency": "KRW",
      "source": "출처 URL"
    },
    
    "global_average_revenue": {
      "volume": 23000000000,
      "currency": "USD",
      "source": "출처 URL"
    }
  },
  
  "similar_service": {
    "score": 75,
    "services": [
      {
        "name": "서비스명",
        "description": "서비스 설명",
        "logo_url": "서비스 로고 이미지 URL",
        "website_url": "공식 웹사이트 URL",
        "tags": ["태그1", "태그2"],
        "full_description": "상세 설명"
      }
    ]
  },
  
  "expected_bm": {
    "revenue_model": "예상 수익 모델 (예: 광고 기반, 구독 모델 등)",
    "target_audience": "주요 타겟층 (예: 20대 사용자, 기업 고객 등)"
  },
  
  "support_program": {
    "score": 89,
    "programs": [
      {
        "name": "지원 프로그램명",
        "organizer": "주최 기관",
        "program_url": "신청 링크",
        "apply_start_date": "YYYY-MM-DD",
        "apply_end_date": "YYYY-MM-DD"
      }
    ]
  },
  
  "team_requirements": {
    "roles": [
      {
        "position": "예상 직군",
        "responsibilities": "해당 직군의 역할 및 필요 기술"
      }
    ]
  },
  
  "limitation": {
    "score": 60,
    "risks": [
      "기술적 한계",
      "시장 진입 장벽",
      "법적 문제",
      "초기 비용 부담"
    ]
  }
}

# ✅ JSON을 문자열로 변환
market_analysis_json_string = json.dumps(market_analysis_dict, ensure_ascii=False, indent=4)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IdeaBases(BaseModel):
    current_issue: List[str] = Field(..., description="현재 문제점 리스트")
    motivation: str = Field(..., description="아이디어의 동기")
    core_feature: List[str] = Field(..., description="핵심 기능 리스트")
    methodology: str = Field(..., description="사용할 방법론")
    expected_output: str = Field(..., description="예상되는 결과")

class AnalysisRequest(BaseModel):
    idea_bases: IdeaBases

async def openai_streaming(prompt: str):
    accumulated_text = ""
    progress = 0.00
    completed_sections = set()
    progress_stages = {
        "summary": {"progress": 5.00, "keyword": "Summary"},
        "market_statistics": {"progress": 20.00, "keyword": "market_statistics"},
        "similar_service": {"progress": 60.00, "keyword": "similar_service"},
        "expected_bm": {"progress": 70.00, "keyword": "expected_bm"},
        "support_program": {"progress": 80.00, "keyword": "support_program"},
        "limitation": {"progress": 90.00, "keyword": "Limitation"}
    }
    
    try:
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            stream=True
        )
        
        yield json.dumps({"progress": round(progress, 2), "message": "Streaming started."}, ensure_ascii=False) + "\n"
        
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                accumulated_text += token
                
                logger.info(f"🔎 현재 누적된 텍스트: {accumulated_text[-500:]}")  # 마지막 500자만 로깅하여 확인
                
                # 특정 키워드 등장 시 해당 구간의 퍼센트로 점프 (중복 방지)
                for key, value in progress_stages.items():
                    if value["keyword"].lower() in accumulated_text.lower() and key not in completed_sections:
                        completed_sections.add(key)
                        progress = max(progress, value["progress"])  # progress가 낮을 경우 업데이트
                        logger.info(f"✅ {value['keyword']} 감지됨, 진행률 {progress}%로 점프!")
                        yield json.dumps({"progress": round(progress, 2), "message": f"{value['keyword']} section complete."}, ensure_ascii=False) + "\n"
                        break  # 한 번 점프하면 중복 점프 방지
                
                # 점진적인 progress 증가 (최대 100%)
                progress = min(progress + 0.05, 100.00)
                yield json.dumps({"progress": round(progress, 2), "message": token}, ensure_ascii=False) + "\n"
                await asyncio.sleep(0.01)
        
        try:
            final_json = json.loads(accumulated_text)
        except Exception as e:
            final_json = {"is_complete": True, "result": {"error": "Invalid JSON", "raw_text": accumulated_text}}
        
        yield json.dumps({"is_complete": True, "result": final_json}, ensure_ascii=False) + "\n"
        
    except Exception as e:
        logger.error(f"🚨 OpenAI Streaming 요청 중 오류 발생: {str(e)}")
        yield json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False) + "\n"

@app.post("/analyze")
async def analyze(request: AnalysisRequest = Body(...)):
    try:
        request_data = request.model_dump()
        logger.info(f"📥 입력 데이터: {request_data}")
        
        prompt = f'''# 시스템 프롬프트
당신은 **스타트업 컨설턴트 겸 시장 분석 전문가**입니다.
사용자가 제시한 아이디어를 바탕으로, **필수 정보**를 파악하고, **추가 질문**을 통해 누락된 내용을 보완한 뒤,
**구체적인 조언**과 **분석 결과**를 **JSON 및 Markdown 리포트 형식**으로 제공합니다.

---

## 2. 사용자 입력 데이터 (JSON)
```json
{json.dumps(request_data, ensure_ascii=False, indent=2)}
```

---

## 3. 분석 리포트 생성 규칙
-사용자의 입력된 아이디어(Problem & Solution 정보)만을 활용하여,  **JSON 형식**으로 최종 답변을 자동 생성하십시오. 
-모든 점수는 **100점 만점** 기준으로 작성합니다.
- **JSON 리포트 형식으로 출력**하십시오.
당신은 **스타트업 컨설턴트 겸 시장 분석 전문가**입니다.  
**결과는 반드시 다음 형식을 따라야 합니다**
    결과 JSON 형식:
    ```json
{market_analysis_json_string}


위의 지침에 따라, **객관적이고 실용적인 리포트를 생성**하십시오.
'''
        return StreamingResponse(openai_streaming(prompt), media_type="text/event-stream")
    
    except Exception as e:
        logger.error(f"🚨 분석 요청 처리 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"분석 요청 처리 중 오류 발생: {str(e)}")
