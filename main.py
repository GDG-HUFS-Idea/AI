import json
import logging
import re
import datetime
import asyncio
import uuid
import enum
from typing import Dict, Any, Optional, List, AsyncGenerator
from fastapi import FastAPI, Request, HTTPException, status, Query
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from modules.ksicclassifier import KSICClassifier
from modules.market_analyzer import MarketAnalyzer
from modules.similar_service_finder import SimilarServiceFinder
from modules.opportunity_analyzer import OpportunityAnalyzer
from modules.limitation_analyzer import LimitationAnalyzer
from modules.team_analyzer import TeamAnalyzer
from modules.report_validators import ReportValidator
from modules.prompt_builder import PromptBuilder
from openai import APIError, AuthenticationError, RateLimitError, OpenAI
from config.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

TASKS = {}

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

def _generate_report(data: dict, task_id: str = None) -> dict:
    """
    최종 보고서를 생성할 때만 OpenAI(GPT) 사용.
    task_id가 제공되면 진행 상태를 업데이트합니다.
    """
    # OpenAI import
    from openai import OpenAI

    logger.info(f"OpenAI GPT 호출 시작 (task_id: {task_id})")
    openai_client = OpenAI(api_key=Settings.OPENAI_API_KEY)

    prompt = PromptBuilder.build(data)
    try:
        logger.debug(f"OpenAI API 호출 - {data.get('idea', '')[:30]}...")
        
        if task_id and task_id in TASKS:
            TASKS[task_id]['message'] = "수집 데이터 취합하여 분석 중..."
            TASKS[task_id]['progress'] = 0.6
        
        # 스트리밍 모드로 API 호출
        stream = openai_client.chat.completions.create(
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
            max_tokens=4000,
            stream=True
        )
        
        logger.debug("OpenAI API 스트리밍 응답 수신 시작")
        
        if task_id and task_id in TASKS:
            TASKS[task_id]['message'] = "수집된 데이터를 바탕으로로 보고서 작성 중..."
            TASKS[task_id]['progress'] = 0.7
        
        # 스트리밍 응답을 모아서 처리
        content_chunks = []
        total_chunks_received = 0
        last_update_time = datetime.datetime.now()
        
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content_part = chunk.choices[0].delta.content
                content_chunks.append(content_part)
                total_chunks_received += 1
                
                # 약 30초마다 진행 상태 업데이트
                current_time = datetime.datetime.now()
                if task_id and task_id in TASKS and (current_time - last_update_time).total_seconds() > 30:
                    # 0.7에서 0.85 사이로 진행률 업데이트
                    progress_increment = min(0.05, (0.85 - 0.7) / 3)
                    new_progress = min(0.85, TASKS[task_id]['progress'] + progress_increment)
                    TASKS[task_id]['progress'] = new_progress
                    last_update_time = current_time
        
        # 모든 청크를 합쳐 전체 내용 구성
        content = ''.join(content_chunks)
        logger.debug(f"OpenAI API 스트리밍 응답 수신 완료 (총 {len(content_chunks)}개 청크)")
        
        # 마무리 단계로 설정
        if task_id and task_id in TASKS:
            TASKS[task_id]['message'] = "보고서 최종 정리 중..."
            TASKS[task_id]['progress'] = 0.85

        if not content or len(content.strip()) < 20:
            logger.error(f"API 응답이 비어있거나 너무 짧습니다 (task_id: {task_id})")
            return _create_fallback_report(data)

        logger.debug(f"원시 응답 데이터 (일부): {content[:200]}...")
        report = _extract_json_from_content(content)

        if not report or not isinstance(report, dict):
            logger.error(f"파싱된 리포트가 유효한 딕셔너리가 아닙니다 (task_id: {task_id})")
            return _create_fallback_report(data)

        report = _ensure_required_fields(report, data)
        logger.info(f"보고서 생성 완료 (task_id: {task_id})")
        return report

    except (APIError, AuthenticationError, RateLimitError) as oe:
        logger.error(f"OpenAI API 관련 오류 (task_id: {task_id}): {str(oe)}")
        return _create_fallback_report(data)
    except Exception as e:
        logger.error(f"리포트 생성 중 오류 발생 (task_id: {task_id}): {str(e)}")
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
    """
    필수 필드가 존재하는지 확인하고, 빈 값이 있는 경우 GPT에게 다시 요청합니다.
    """
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

    def is_empty(value):
        """값이 비어있는지 확인하는 헬퍼 함수"""
        if value is None:
            return True
        if isinstance(value, (str, list, dict)):
            return len(value) == 0
        return False

    def check_nested_fields(obj, required):
        """중첩된 필드의 빈 값 확인"""
        if isinstance(required, dict):
            for key, sub_required in required.items():
                if key not in obj or is_empty(obj[key]):
                    return False
                if not check_nested_fields(obj[key], sub_required):
                    return False
        elif isinstance(required, list):
            if not obj or not all(not is_empty(item) for item in obj):
                return False
        return True

    # 필수 필드 존재 여부 확인
    for field, default_value in required_fields.items():
        if field not in report:
            report[field] = default_value

    # 빈 값이 있는지 확인
    has_empty_values = False
    for field, required in required_fields.items():
        if not check_nested_fields(report[field], required):
            has_empty_values = True
            break

    # 빈 값이 있으면 GPT에게 다시 요청
    if has_empty_values:
        logger.warning("보고서에 빈 값이 있어 GPT에게 다시 요청합니다")
        return _generate_report(data)

    # scores 필드 처리
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

def preprocess_idea_with_llm(raw_input: dict) -> dict:
    """사용자 입력을 GPT를 통해 Spark1의 TestData 구조로 전처리"""
    # OpenAI 클라이언트 초기화
    client = OpenAI(api_key=Settings.OPENAI_API_KEY)
    
    prompt = (
        "다음 사용자 입력을 기반으로 SparkLens 분석을 위한 테스트 데이터 형식으로 구조화해주세요. "
        "JSON 형식은 반드시 다음과 같아야 합니다:\n\n"
        "{\n"
        '  "user_id": "사용자 ID (기본값: testUser)",\n'
        '  "problem": {\n'
        '    "identifiedIssues": ["문제점1", "문제점2"],\n'
        '    "developmentMotivation": "이 문제를 해결하고자 하는 동기"\n'
        "  },\n"
        '  "solution": {\n'
        '    "coreElements": ["핵심 요소1", "핵심 요소2"],\n'
        '    "methodology": "핵심 구현 방법",\n'
        '    "expectedOutcome": "기대 효과"\n'
        "  }\n"
        "}\n\n"
        f"사용자 입력:\n"
        f"문제:\n{raw_input.get('problem', '')}\n"
        f"동기:\n{raw_input.get('motivation', '')}\n"
        f"기능/특징:\n{raw_input.get('features', '')}\n"
        f"방법론:\n{raw_input.get('method', '')}\n"
        f"결과물:\n{raw_input.get('deliverable', '')}\n\n"
        "중요: 모든 필드는 필수이며, 빈 값이 없어야 합니다. "
        "각 필드에 적절한 값을 제공하되, 없는 정보는 'N/A'로 표시하세요. "
        "반드시 위 JSON 형식에 맞춰 응답해주세요."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 입력을 구조화하는 AI 도우미입니다. JSON 포맷만 출력하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1000,
            timeout=Settings.OPENAI_TIMEOUT
        )
        content = response.choices[0].message.content.strip()
        logger.info(f"[전처리 요청 Prompt]:\n{prompt[:200]}...\n")
        logger.info(f"[전처리 GPT 응답]:\n{content[:200]}...\n")
        
        # 마크다운 코드 블록 제거
        if content.startswith("```json"):
            content = content.removeprefix("```json").strip()
        if content.startswith("```"):
            content = content.removeprefix("```").strip()
        if content.endswith("```"):
            content = content.removesuffix("```").strip()
        
        # 쉼표 후행 문제 제거
        content = re.sub(r",\s*}", "}", content)
        content = re.sub(r",\s*]", "]", content)
        
        # 완전한 JSON 파싱 시도
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # 중괄호 기반 JSON 블록 정규식 추출 시도
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                logger.warning(f"[전처리 정규식 JSON 파싱 실패] {str(e)}")
        
        # 모든 시도가 실패한 경우
        logger.error("[전처리 실패] GPT 응답이 JSON 형식이 아님")
        raise ValueError("GPT 응답이 유효한 JSON이 아님")
        
    except Exception as e:
        logger.error(f"[전처리 실패] {str(e)}")
        # fallback: 최소 구조 반환
        return {
            "user_id": "testUser",
            "problem": {
                "identifiedIssues": [raw_input.get("problem", "")],
                "developmentMotivation": raw_input.get("motivation", "")
            },
            "solution": {
                "coreElements": [raw_input.get("features", "")],
                "methodology": raw_input.get("method", ""),
                "expectedOutcome": raw_input.get("deliverable", "")
            }
        }

# 오버뷰 입력 데이터를 분석 시스템용 형식으로 변환
def _convert_overview_to_analysis_format(overview_data: Dict) -> Dict:
    """
    오버뷰 요청 데이터를 기존 분석 시스템이 이해할 수 있는 형식으로 변환합니다.
    """
    # 이미 SparkLens 형식인 경우 (전처리 완료된 경우)
    if isinstance(overview_data.get('problem'), dict) and isinstance(overview_data.get('solution'), dict):
        return overview_data
    
    # 평면화된 구조인 경우 (이전 형식)
    return {
        'problem': {
            'identifiedIssues': [overview_data.get('problem', '')],
            'developmentMotivation': overview_data.get('motivation', '')
        },
        'solution': {
            'coreElements': [overview_data.get('features', '')],
            'methodology': overview_data.get('method', ''),
            'expectedOutcome': overview_data.get('deliverable', '')
        }
    }

# 백그라운드에서 분석 작업을 실행하는 함수
async def run_analysis_task(task_id: str, data: Dict):
    """
    비동기로 분석 작업을 수행하고 결과를 저장합니다.
    """
    try:
        # 태스크 상태 업데이트
        TASKS[task_id]['status'] = TaskStatus.PROCESSING
        TASKS[task_id]['progress'] = 0.05
        TASKS[task_id]['message'] = "분석 시스템 초기화 중... 입력 데이터 검증 및 분석 모듈 준비"
        
        # 데이터가 이미 SparkLens 형식인지 확인하고 필요시 변환
        analysis_data = data
        if 'user_id' in data and 'problem' in data and 'solution' in data:
            logger.debug("전처리된 SparkLens 형식 데이터 사용")
        else:
            analysis_data = _convert_overview_to_analysis_format(data)
            logger.debug("데이터를 분석 시스템 형식으로 변환")
        
        # 분석 모듈 초기화
        modules = await run_in_threadpool(_reinitialize_modules)
        
        # === 간소화된 첫 번째 단계: 데이터 수집 ===
        TASKS[task_id]['progress'] = 0.1
        TASKS[task_id]['message'] = "외부 데이터 수집 시작... (산업 분류, 시장 분석, 유사 서비스 검색, 기회/한계점 분석)"
        
        # 병렬로 데이터 수집 시작
        collection_start = datetime.datetime.now()
        logger.info(f"데이터 수집 시작 (task_id: {task_id})")

        # 각 모듈의 결과를 저장할 딕셔너리
        results = {
            'idea': analysis_data.get('idea', ''),
            'problem': analysis_data.get('problem', {}),
            'solution': analysis_data.get('solution', {}),
        }

        # 중간 진행 업데이트 함수
        async def update_collection_progress():
            progress_points = [0.15, 0.25, 0.35, 0.45]
            await asyncio.sleep(30)  # 첫 30초 후 업데이트
            
            for progress in progress_points:
                if task_id in TASKS and TASKS[task_id]['status'] == TaskStatus.PROCESSING:
                    TASKS[task_id]['progress'] = progress
                await asyncio.sleep(30)  # 30초마다 업데이트
        
        # 백그라운드에서 진행 상황 업데이트 시작
        progress_task = asyncio.create_task(update_collection_progress())
        
        try:
            # KSIC 분류 및 시장 분석
            results['ksic'] = await run_in_threadpool(modules['classifier'].classify, results['idea'])
            results['market'] = await run_in_threadpool(modules['market'].analyze, results['idea'], results['problem'], results['solution'])

            # 유사 서비스 찾기
            core_elements = ' '.join(results['solution'].get('coreElements', []))
            results['similar_services'] = await run_in_threadpool(modules['similar'].find, results['idea'], core_elements)

            # 기회 및 한계점 분석
            results['opportunities'] = await run_in_threadpool(modules['opportunity'].find, results['idea'], results['problem'], results['solution'])
            results['limitations'] = await run_in_threadpool(modules['limitation'].analyze, results['idea'], results['problem'], results['solution'])

            # 팀 분석
            results['team'] = await run_in_threadpool(modules['team'].analyze, results['idea'], results['problem'], results['solution'])
            
            # 진행 상황 업데이트 태스크 취소
            progress_task.cancel()
            
        except Exception as e:
            # 진행 상황 업데이트 태스크 취소
            progress_task.cancel()
            logger.error(f"데이터 수집 중 오류 (task_id: {task_id}): {str(e)}")
            raise

        collection_end = datetime.datetime.now()
        logger.info(f"데이터 수집 완료 (task_id: {task_id}), 소요 시간: {(collection_end - collection_start).total_seconds():.2f}초")

        # === 간소화된 두 번째 단계: 보고서 생성 ===
        TASKS[task_id]['progress'] = 0.5
        TASKS[task_id]['message'] = "데이터 수집 완료. 보고서 작성을 시작합니다..."
        
        # 최종 보고서 생성
        report = await run_in_threadpool(lambda: _generate_report(results, task_id))
        
        # 보고서 검증
        TASKS[task_id]['progress'] = 0.9
        TASKS[task_id]['message'] = "보고서 최종 검증 중... 필수 항목 확인, 데이터 일관성 검사, 점수 산출 검증을 진행합니다"
        await run_in_threadpool(ReportValidator.validate, report)
        
        # 분석 완료 및 결과 저장
        TASKS[task_id]['status'] = TaskStatus.COMPLETED
        TASKS[task_id]['progress'] = 1.0
        TASKS[task_id]['message'] = "분석 완료"
        TASKS[task_id]['result'] = report
        
        logger.info(f"분석 작업 완료 (task_id: {task_id})")
        
    except Exception as e:
        logger.error(f"분석 작업 실패 (task_id: {task_id}): {str(e)}")
        TASKS[task_id]['status'] = TaskStatus.FAILED
        TASKS[task_id]['message'] = f"분석 실패: {str(e)}"
        TASKS[task_id]['error'] = str(e)

class ProjectOverviewRequest(dict):
    @classmethod
    def validate(cls, data: Dict) -> bool:
        """
        요청 데이터의 유효성을 검증합니다.
        """
        required_fields = ['problem', 'motivation', 'features', 'method', 'deliverable']
        
        # 필수 필드 존재 여부 확인
        for field in required_fields:
            if field not in data or not data[field]:
                return False
            
        # 각 필드의 값이 문자열인지 확인
        for field in required_fields:
            if not isinstance(data[field], str):
                return False
            
        # 각 필드의 최소 길이 확인
        min_lengths = {
            'problem': 10,
            'motivation': 5,
            'features': 10,
            'method': 10,
            'deliverable': 5
        }
        
        for field, min_length in min_lengths.items():
            if len(data[field]) < min_length:
                return False
                
        return True

@app.post("/analyses/projects/overview")
async def analyze_project_overview(data: Dict):
    """
    프로젝트 개요 분석을 시작하고 task_id를 반환합니다.
    """
    try:
        # 데이터 검증
        if not data or not isinstance(data, dict):
            logger.error("잘못된 입력 데이터 형식")
            raise HTTPException(status_code=400, detail="잘못된 입력 데이터 형식")
        
        # task_id 생성 및 초기화
        task_id = str(uuid.uuid4())
        TASKS[task_id] = {
            'status': TaskStatus.PENDING,
            'progress': 0,
            'message': '분석 대기 중...',
            'start_time': datetime.datetime.now(),
            'data': data
        }
        
        logger.info(f"새 분석 작업 시작 (task_id: {task_id})")
        
        # 백그라운드에서 분석 실행
        asyncio.create_task(run_analysis_task(task_id, data))
        
        return {"task_id": task_id}
        
    except Exception as e:
        logger.error(f"분석 작업 초기화 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_task_status_events(task_id: str) -> AsyncGenerator[str, None]:
    """
    태스크 상태를 SSE 형식으로 생성하는 제너레이터 함수
    """
    # 먼저 현재 상태 전송
    if task_id not in TASKS:
        yield f"data: {json.dumps({'error': '존재하지 않는 작업 ID'})}\n\n"
        return
    
    # 초기 상태 전송
    task_info = TASKS[task_id].copy()
    
    # 필수 필드만 포함한 응답 구성
    response_data = {
        "is_complete": task_info['status'] in [TaskStatus.COMPLETED, TaskStatus.FAILED]
    }
    
    # 선택적 필드 추가
    if 'progress' in task_info:
        response_data["progress"] = task_info['progress']
    
    if 'message' in task_info:
        response_data["message"] = task_info['message']
    
    # 완료된 경우 결과 포함
    if task_info['status'] == TaskStatus.COMPLETED and 'result' in task_info:
        response_data["result"] = task_info['result']
    
    yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
    
    # 작업이 완료 또는 실패 상태가 아니면 계속 업데이트 전송
    if task_info['status'] not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        previous_progress = task_info.get('progress', 0)
        previous_message = task_info.get('message', '')
        
        while True:
            # 5초마다 업데이트 (통신 부하 감소)
            await asyncio.sleep(5)
            
            # 작업 정보 가져오기
            current_info = TASKS[task_id].copy()
            
            # 완료 또는 실패 시 즉시 업데이트
            if current_info['status'] in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                current_response = {
                    "is_complete": True
                }
                
                if 'progress' in current_info:
                    current_response["progress"] = current_info['progress']
                
                if 'message' in current_info:
                    current_response["message"] = current_info['message']
                
                # 완료된 경우만 결과 포함
                if current_info['status'] == TaskStatus.COMPLETED and 'result' in current_info:
                    current_response["result"] = current_info['result']
                
                yield f"data: {json.dumps(current_response, ensure_ascii=False)}\n\n"
                return
            
            # 진행률이 5% 이상 변경되었거나, 메시지가 변경된 경우에만 업데이트 (통신 부하 감소)
            current_progress = current_info.get('progress', 0)
            current_message = current_info.get('message', '')
            
            # 진행률이 5% 이상 변경되었거나, 메시지가 변경된 경우에만 업데이트
            progress_change_significant = abs(current_progress - previous_progress) >= 0.05
            message_changed = current_message != previous_message
            
            if progress_change_significant or message_changed:
                current_response = {
                    "is_complete": False,
                    "progress": current_progress,
                    "message": current_message
                }
                
                yield f"data: {json.dumps(current_response, ensure_ascii=False)}\n\n"
                
                # 이전 값 업데이트
                previous_progress = current_progress
                previous_message = current_message

@app.get("/analyses/projects/overview/status")
async def get_task_status(task_id: str = Query(..., description="분석 작업 ID")):
    """
    작업 상태를 SSE 형식으로 스트리밍합니다.
    """
    if task_id not in TASKS:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "존재하지 않는 작업 ID"}
        )
    
    return StreamingResponse(
        generate_task_status_events(task_id),
        media_type="text/event-stream"
    )

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
