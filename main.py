import json
import logging
import re
import datetime
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import httpx

# --- 모듈 임포트 (원본 구조 유지) ---
from modules.ksicclassifier import KSICClassifier
from modules.market_analyzer import MarketAnalyzer
from modules.similar_service_finder import SimilarServiceFinder
from modules.opportunity_analyzer import OpportunityAnalyzer
from modules.limitation_analyzer import LimitationAnalyzer
from modules.team_analyzer import TeamAnalyzer
from modules.report_validators import ReportValidator
from modules.prompt_builder import PromptBuilder
# 기존: from openai import OpenAI
# 다음처럼 예외클래스는 필요하다면 남겨도 됨
from openai import APIError, AuthenticationError, RateLimitError
from config.settings import Settings

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI()

# -- 전역 OpenAI 클라이언트 제거 --
# client = OpenAI(api_key=Settings.OPENAI_API_KEY)  # << 제거

def _reinitialize_modules():
    return {
        'classifier': KSICClassifier(),        # Perplexity
        'market': MarketAnalyzer(),            # Perplexity
        'similar': SimilarServiceFinder(),     # Perplexity
        'opportunity': OpportunityAnalyzer(),  # Perplexity
        'limitation': LimitationAnalyzer(),    # Perplexity
        'team': TeamAnalyzer()                 # Perplexity
    }

def _collect_data(sample: dict, modules: Dict[str, Any]) -> dict:
    """아이디어, 문제, 해결책 등을 합쳐 분석에 필요한 구조화 데이터를 만든다."""
    problem = sample.get('problem', {})
    solution = sample.get('solution', {})

    issues = ' '.join(problem.get('identifiedIssues', []))
    motivation = problem.get('developmentMotivation', '')
    core_elements = ' '.join(solution.get('coreElements', []))
    methodology = solution.get('methodology', '')
    expected_outcome = solution.get('expectedOutcome', '')

    idea = (
        f"문제점: {issues}\n"
        f"동기: {motivation}\n"
        f"핵심 요소: {core_elements}\n"
        f"방법론: {methodology}\n"
        f"기대 결과: {expected_outcome}"
    )

    return {
        'idea': idea,
        'problem': problem,
        'solution': solution,
        'ksic': modules['classifier'].classify(idea),
        'market': modules['market'].analyze(idea, problem, solution),
        'similar_services': modules['similar'].find(idea, core_elements),
        'opportunities': modules['opportunity'].find(idea, problem, solution),
        'limitations': modules['limitation'].analyze(idea, problem, solution),
        'team': modules['team'].analyze(idea, problem, solution)
    }

def _generate_report(data: dict) -> dict:
    """
    최종 보고서를 생성할 때만 OpenAI(GPT) 사용.
    """
    # OpenAI import
    from openai import OpenAI

    logger.info("[_generate_report] OpenAI GPT 호출 시작")
    openai_client = OpenAI(api_key=Settings.OPENAI_API_KEY)

    prompt = PromptBuilder.build(data)
    try:
        logger.info(f"OpenAI API 호출 - {data.get('idea', '')[:30]}...")
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 비즈니스 분석 전문가입니다. "
                        "객관적인 데이터를 기반으로 사업 아이디어를 분석하고, 점수를 산출하세요."
                        "추가 설명이나 불필요한 문장은 포함하지 마세요. "
    "반드시 중괄호 { }로 시작하는 순수 JSON을 반환해야 합니다."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            timeout=Settings.OPENAI_TIMEOUT,
            max_tokens=4000
        )
        logger.info("OpenAI API 응답 수신 완료")
        content = response.choices[0].message.content

        if not content or len(content.strip()) < 20:
            logger.error(f"API 응답이 비어있거나 너무 짧습니다: {content}")
            return _create_fallback_report(data)

        logger.debug(f"원시 응답 데이터 (일부): {content[:200]}...")
        report = _extract_json_from_content(content)

        if not report or not isinstance(report, dict):
            logger.error("파싱된 리포트가 유효한 딕셔너리가 아닙니다")
            return _create_fallback_report(data)

        report = _ensure_required_fields(report, data)
        return report

    except (APIError, AuthenticationError, RateLimitError) as oe:
        logger.error(f"OpenAI API 관련 오류: {str(oe)}")
        return _create_fallback_report(data)
    except Exception as e:
        logger.error(f"리포트 생성 중 오류 발생: {str(e)}")
        return _create_fallback_report(data)

def _extract_json_from_content(content: str) -> dict:
    try:
        cleaned = content.strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    code_block_patterns = [
        r'```json([\s\S]*?)```',
        r'```([\s\S]*?)```'
    ]
    for pattern in code_block_patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        for match in matches:
            match = match.strip()
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

    json_start = content.find('{')
    json_end = content.rfind('}')
    if json_start != -1 and json_end != -1:
        json_str = content[json_start:json_end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    logger.warning("JSON 파싱 실패, 텍스트 구조화 시도")
    return _structure_text_to_json(content)

def _structure_text_to_json(text: str) -> dict:
    result = {"marketAnalysis": {}, "similarServices": [], "targetAudience": []}
    result["rawContent"] = text
    return result

def _ensure_required_fields(report: dict, data: dict) -> dict:
    required_fields = {
        "marketAnalysis": {"domestic": {}, "global": {}},
        "similarServices": [],
        "targetAudience": [],
        "businessModel": {},
        "marketingStrategy": {},
        "opportunities": {},
        "limitations": {},
        "requiredTeam": [],
        "scores": {"market": 0, "opportunity": 0, "similarService": 0, "risk": 0, "total": 0},
    }
    for field, default_value in required_fields.items():
        if field not in report:
            report[field] = default_value

    if "scores" in report:
        for sf in ["market", "opportunity", "similarService", "risk"]:
            if sf not in report["scores"]:
                report["scores"][sf] = 0
        if "total" not in report["scores"]:
            sc = report["scores"]
            total = (
                float(sc["market"]) + 
                float(sc["opportunity"]) + 
                float(sc["similarService"]) + 
                float(sc["risk"])
            ) / 4
            report["scores"]["total"] = round(total, 1)

    return report

def _create_fallback_report(data: dict) -> dict:
    idea = data.get('idea', '아이디어 정보 없음')
    return {
        "idea": idea,
        "marketAnalysis": {
            "domestic": {"rawContent": "국내 시장 분석 실패"},
            "global": {"rawContent": "글로벌 시장 분석 실패"}
        },
        "similarServices": [],
        "targetAudience": [],
        "businessModel": {},
        "marketingStrategy": {},
        "opportunities": {},
        "limitations": {},
        "requiredTeam": [],
        "scores": {
            "market": 0, "opportunity": 0, "similarService": 0, "risk": 0, "total": 0
        }
    }

@app.post("/analyze")
async def analyze(request: Request):
    """
    1) JSON 수신 → Perplexity 모듈로 데이터 분석
    2) 최종 보고서만 OpenAI(GPT)를 통해 생성
    3) 스트리밍 방식으로 반환
    """
    try:
        sample = await request.json()
        modules = _reinitialize_modules()

        # Perplexity 기반 분석 데이터
        analysis_data = _collect_data(sample, modules)

        # 최종 보고서(오직 GPT)
        report = _generate_report(analysis_data)

        # 보고서 검증
        ReportValidator.validate(report)

        async def json_streamer(data: dict):
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            for chunk in json_str.splitlines(keepends=True):
                yield chunk.encode("utf-8")
                await asyncio.sleep(0)

        return StreamingResponse(
            json_streamer(report),
            media_type="application/json"
        )

    except Exception as e:
        logger.error(f"분석 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")
