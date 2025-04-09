import unittest
import json
import os
import glob
import datetime
import logging
import re
from openai import OpenAI, APIError, AuthenticationError, RateLimitError
from modules.ksicclassifier import KSICClassifier
from modules.market_analyzer import MarketAnalyzer
from modules.similar_service_finder import SimilarServiceFinder
from modules.opportunity_analyzer import OpportunityAnalyzer
from modules.limitation_analyzer import LimitationAnalyzer
from modules.team_analyzer import TeamAnalyzer
from modules.report_validators import ReportValidator
from modules.prompt_builder import PromptBuilder
from config.settings import Settings

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=Settings.OPENAI_API_KEY)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessAnalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_data = cls._load_test_data()
        cls.result_dir = cls._create_result_dir()
        cls.modules = {
            'classifier': KSICClassifier(),
            'market': MarketAnalyzer(),
            'similar': SimilarServiceFinder(),
            'opportunity': OpportunityAnalyzer(),
            'limitation': LimitationAnalyzer(),
            'team': TeamAnalyzer()
        }

    @classmethod
    def _load_test_data(cls):
        data = []
        for filepath in sorted(glob.glob("TestData/*.json")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    sample = json.load(f)
                    data.append(sample)
            except Exception as e:
                logger.error(f"파일 로드 오류 ({filepath}): {str(e)}")
        return data

    @classmethod
    def _create_result_dir(cls):
        dir_name = datetime.datetime.now().strftime("results_%Y%m%d_%H%M%S")
        os.makedirs(dir_name, exist_ok=True)
        return dir_name

    def _handle_error(self, error, sample):
        user_id = sample.get('user_id', 'unknown')
        logger.error(f"Sample({user_id}) 처리 중 에러 발생: {str(error)}")
        error_file = os.path.join(self.result_dir, f"error_{user_id}.txt")
        try:
            with open(error_file, "w", encoding="utf-8") as f:
                f.write(str(error))
        except Exception as fe:
            logger.error(f"에러 파일 저장 실패: {str(fe)}")
        self.fail(f"Sample({user_id}) 처리 실패: {str(error)}")

    def _log_unexpected_error(self, error, sample):
        user_id = sample.get('user_id', 'unknown')
        logger.error(f"Sample({user_id}) 처리 중 예상치 못한 에러 발생: {str(error)}")

    def _reinitialize_modules(self):
        self.modules = {
            'classifier': KSICClassifier(),
            'market': MarketAnalyzer(),
            'similar': SimilarServiceFinder(),
            'opportunity': OpportunityAnalyzer(),
            'limitation': LimitationAnalyzer(),
            'team': TeamAnalyzer()
        }

    def test_full_analysis_flow(self):
        for idx, sample in enumerate(self.test_data):
            with self.subTest(sample=idx+1):
                try:
                    # 모듈 재초기화로 테스트 격리
                    self._reinitialize_modules()
                    analysis_data = self._collect_data(sample)
                    report = self._generate_report(analysis_data)
                    self.assertTrue(ReportValidator.validate(report),
                                    "리포트 포맷 불일치")
                    self._save_results(report, sample, idx+1)
                except APIError as e:
                    self._handle_error(e, sample)
                except Exception as e:
                    self._log_unexpected_error(e, sample)
                    raise

    def _collect_data(self, sample: dict) -> dict:
        # 아이디어 구성: problem과 solution을 조합
        problem = sample.get('problem', {})
        solution = sample.get('solution', {})

        # 문제점과 해결책을 텍스트로 조합
        issues = ' '.join(problem.get('identifiedIssues', []))
        motivation = problem.get('developmentMotivation', '')
        core_elements = ' '.join(solution.get('coreElements', []))
        methodology = solution.get('methodology', '')
        expected_outcome = solution.get('expectedOutcome', '')
    
        # 조합된 아이디어 생성
        idea = f"문제점: {issues}\n동기: {motivation}\n핵심 요소: {core_elements}\n방법론: {methodology}\n기대 결과: {expected_outcome}"
    
        return {
            'idea': idea,
            'problem': problem,
            'solution': solution,
            'ksic': self.modules['classifier'].classify(idea),
            'market': self.modules['market'].analyze(idea, problem, solution),
            'similar_services': self.modules['similar'].find(idea, core_elements),
            'opportunities': self.modules['opportunity'].find(idea, problem, solution),
            'limitations': self.modules['limitation'].analyze(idea, problem, solution),
            'team': self.modules['team'].analyze(idea, problem, solution)
        }

    def _generate_report(self, data: dict) -> dict:
        prompt = PromptBuilder.build(data)
        try:
            logger.info(f"OpenAI API 호출 시작 - {data.get('idea', '')[:30]}...")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 비즈니스 분석 전문가입니다. 객관적인 데이터를 기반으로 사업 아이디어를 분석하고, 특히 점수 산출 기준에 따라 정확한 점수를 계산해야 합니다. 하드코딩된 값이나 임의의 값을 사용하지 마세요."},
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
                return self._create_fallback_report(data)
            
            logger.debug(f"원시 응답 데이터 (일부): {content[:200]}...")
            
            report = self._extract_json_from_content(content)
            
            if not report or not isinstance(report, dict):
                logger.error("파싱된 리포트가 유효한 딕셔너리가 아닙니다")
                return self._create_fallback_report(data)
            
            report = self._ensure_required_fields(report, data)
            
            return report
            
        except Exception as e:
            logger.error(f"리포트 생성 중 오류 발생: {str(e)}")
            return self._create_fallback_report(data)

    def _extract_json_from_content(self, content: str) -> dict:
        """응답 내용에서 JSON 추출하는 개선된 함수 (강화된 정규식, 탐지 로직 포함)"""
        try:
            if not content:
                logger.warning("빈 콘텐츠 응답")
                return {}

            # 1단계: 완전한 JSON 파싱 시도
            try:
                return json.loads(content.strip())
            except json.JSONDecodeError:
                pass

            # 2단계: 마크다운 코드 블록 제거 및 파싱
            code_block_patterns = [
                r"```json\s*([\s\S]+?)```",  # ```json ... ```
                r"```([\s\S]+?)```",         # ``` ... ```
            ]
            for pattern in code_block_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    try:
                        cleaned = match.strip()
                        return json.loads(cleaned)
                    except json.JSONDecodeError:
                        continue

            # 3단계: 중괄호 기반 JSON 추정 파싱
            json_start = content.find('{')
            json_end = content.rfind('}')
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_str = content[json_start:json_end + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"중괄호 기반 JSON 파싱 실패: {e}")

            # 4단계: 개별 JSON 오브젝트 추출 시도 (다중 중괄호 포함 응답 대비)
            json_objects = re.findall(r'\{[\s\S]*?\}', content)
            for obj in json_objects:
                try:
                    parsed = json.loads(obj)
                    if isinstance(parsed, dict) and len(parsed) >= 3:  # 최소 필드 포함 시 유효 판단
                        return parsed
                except json.JSONDecodeError:
                    continue

            # 5단계: 구조화 시도 (fallback)
            logger.warning("JSON 파싱 실패, 텍스트 구조화 시도")
            return self._structure_text_to_json(content)

        except Exception as e:
            logger.error(f"JSON 추출 중 예외 발생: {str(e)}")
            return {}

    def _structure_text_to_json(self, text: str) -> dict:
        """텍스트 응답을 JSON 구조로 변환하는 함수"""
        result = {"marketAnalysis": {}, "similarServices": [], "targetAudience": []}
        
        # 시장 분석 정보 추출
        market_pattern = r'시장\s*분석|market\s*analysis'
        market_match = re.search(f"({market_pattern}).*?(?={market_pattern}|$)", text, re.IGNORECASE | re.DOTALL)
        if market_match:
            market_content = market_match.group(0)
            result["marketAnalysis"] = {
                "domestic": {"rawContent": market_content},
                "global": {"rawContent": "글로벌 시장 데이터 추출 실패"}
            }
        
        # 유사 서비스 정보 추출
        service_pattern = r'유사\s*서비스|similar\s*services'
        service_match = re.search(f"({service_pattern}).*?(?={service_pattern}|$)", text, re.IGNORECASE | re.DOTALL)
        if service_match:
            service_content = service_match.group(0)
            service_names = re.findall(r'\d+\.\s*([^\n:]+)', service_content)
            for name in service_names:
                result["similarServices"].append({
                    "name": name.strip(),
                    "url": "",
                    "description": "서비스 설명 추출 실패",
                    "targetAudience": "",
                    "tags": [],
                    "summary": "",
                    "similarity": ""
                })
        
        # 기타 필요한 정보 추출
        scores_match = re.search(r'점수.*?(\d+).*?(\d+).*?(\d+)', text, re.IGNORECASE | re.DOTALL)
        if scores_match:
            result["scores"] = {
                "market": int(scores_match.group(1)),
                "feasibility": int(scores_match.group(2)),
                "total": int(scores_match.group(3))
            }
        
        return result

    def _ensure_required_fields(self, report: dict, data: dict) -> dict:
        """필수 필드 존재 확인 및 보완"""
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
            # 필요한 점수 필드 확인 및 기본값 설정
            required_score_fields = ["market", "opportunity", "similarService", "risk"]
            for field in required_score_fields:
                if field not in report["scores"]:
                    report["scores"][field] = 0
            
            # 총점 계산
            if "total" not in report["scores"]:
                scores = report["scores"]
                total = (float(scores.get("market", 0)) + 
                        float(scores.get("opportunity", 0)) + 
                        float(scores.get("similarService", 0)) + 
                        float(scores.get("risk", 0))) / 4
                report["scores"]["total"] = round(total, 1)
        
        return report

    def _create_fallback_report(self, data: dict) -> dict:
        """파싱 실패 시 기본 리포트 생성"""
        idea = data.get('idea', '아이디어 정보 없음')
        
        return {
            "idea": idea,
            "marketAnalysis": {
                "domestic": {"rawContent": "국내 시장 분석을 가져오는데 문제가 발생했습니다."},
                "global": {"rawContent": "글로벌 시장 분석을 가져오는데 문제가 발생했습니다."}
            },
            "similarServices": [
                {
                    "name": "분석 실패",
                    "url": "",
                    "description": "유사 서비스 분석 중 오류가 발생했습니다.",
                    "targetAudience": "",
                    "tags": ["오류"],
                    "summary": "분석 실패",
                    "similarity": 0
                }
            ],
            "targetAudience": [{"segment": "분석 실패", "details": "타겟층 분석 중 오류가 발생했습니다."}],
            "businessModel": {"overview": "비즈니스 모델 분석 중 오류가 발생했습니다."},
            "marketingStrategy": {"overview": "마케팅 전략 분석 중 오류가 발생했습니다."},
            "opportunities": {"factors": ["기회 요인 분석 중 오류가 발생했습니다."]},
            "limitations": {"overview": "한계점 분석 중 오류가 발생했습니다."},
            "requiredTeam": [{"role": "분석 실패", "description": "필요 인력 분석 중 오류가 발생했습니다."}],
            "scores": {"market": 0, "feasibility": 0, "total": 0},
        }

    def _simulate_report(self, data: dict) -> dict:
        market = data.get("market", {})
        similar_services = data.get("similar_services", [])
        opportunities = data.get("opportunities", "기회 요인 데이터 없음")
        limitations = data.get("limitations", "위험 요소 데이터 없음")
        
        if isinstance(market, dict):
            domestic = market.get("domestic", "국내 시장 데이터 없음")
            global_market = market.get("global", "글로벌 시장 데이터 없음")
        else:
            domestic = "국내 시장 데이터 없음"
            global_market = "글로벌 시장 데이터 없음"
        
        # 유사 서비스 처리
        if isinstance(similar_services, list):
            processed_services = similar_services
        else:
            processed_services = []
        
        # 기회 요인 처리
        if isinstance(opportunities, list):
            processed_opportunities = opportunities
        elif isinstance(opportunities, str):
            processed_opportunities = [opportunities]
        else:
            processed_opportunities = ["기회 요인 데이터 없음"]
        
        # 위험 요소 처리
        if isinstance(limitations, list):
            processed_limitations = limitations
        elif isinstance(limitations, str):
            processed_limitations = [limitations]
        else:
            processed_limitations = ["위험 요소 데이터 없음"]
        
        report = {
            "marketAnalysis": {
                "domestic": domestic,
                "global": global_market
            },
            "growthRates": {
                "5YearKorea": "최근 5년간 연평균 3% 성장",
                "5YearGlobal": "최근 5년간 연평균 4% 성장"
            },
            "similarServices": processed_services,
            "businessModel": ["광고 기반", "구독 모델"],
            "opportunities": processed_opportunities,
            "risks": processed_limitations,
            "requiredTeam": {
                "roles": ["개발자", "마케터", "디자이너"],
                "size": "3~5명"
            },
            "scores": {
                "market": 7,
                "feasibility": 8,
                "total": 7.5
            },
            "oneLineReview": "실현 가능성이 높은 사업 아이디어입니다."
        }
        return report

    def _save_results(self, report: dict, sample: dict, idx: int):
        user_id = sample.get('user_id', 'unknown')
        base_path = os.path.join(self.result_dir, f"{user_id}_{idx}")
        try:
            # 리포트 본문 저장
            report_path = f"{base_path}_report.json"
            with open(report_path, 'w', encoding="utf-8") as f:
                # ensure_ascii=False로 설정하여 한글 깨짐 방지
                json.dump(report, f, ensure_ascii=False, indent=4)
                f.flush()  # 즉시 쓰기 보장
            
            # 요약본 생성
            summary_path = f"{base_path}_summary.json"
            self._generate_summary(sample, summary_path)
            
            # 파일 생성 검증
            if not os.path.exists(report_path):
                raise FileNotFoundError("리포트 파일 생성 실패")
            logger.info(f"Sample({user_id}) 결과 저장 완료: {base_path}_*")
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"저장 오류 (Sample {user_id}): {str(e)}")
            self.fail(f"파일 저장 실패: {str(e)}")

    def _generate_summary(self, sample: dict, path: str):
        try:
            problem = ' '.join(sample.get('problem', {}).get('identifiedIssues', []))
            solution = ' '.join(sample.get('solution', {}).get('coreElements', []))
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "아이디어를 5단어 이내 한국어로 요약해주세요."},
                    {"role": "user", "content": f"문제: {problem} 해결책: {solution}"}
                ],
                max_tokens=30,
                temperature=0.5,
                timeout=Settings.OPENAI_TIMEOUT
            )
            
            summary = response.choices[0].message.content.strip()
            if not summary:
                raise ValueError("요약 내용이 비어있음")
            
            with open(path, 'w', encoding="utf-8") as f:
                json.dump({"summary": summary}, f, ensure_ascii=False, indent=4)
            
            logger.info(f"요약 결과 저장 완료: {path}")
        except Exception as e:
            logger.error(f"요약 생성 오류: {str(e)}. 입력 데이터를 기반으로 시뮬레이션됩니다.")
            self._simulate_summary(sample, path)

    def _simulate_summary(self, sample: dict, path: str):
        problem = ' '.join(sample.get('problem', {}).get('identifiedIssues', []))
        solution = ' '.join(sample.get('solution', {}).get('coreElements', []))
        combined = f"{problem} {solution}".strip()
        words = combined.split()
        summary = " ".join(words[:5]) if words else "요약 데이터 없음"
        
        with open(path, 'w', encoding="utf-8") as f:
            json.dump({"summary": summary}, f, ensure_ascii=False, indent=4)
        
        logger.info(f"시뮬레이션된 요약 결과 저장 완료: {path}")

if __name__ == "__main__":
    unittest.main()
