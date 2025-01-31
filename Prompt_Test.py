import unittest
import json
from typing import Dict, Any

class TestPromptGeneration(unittest.TestCase):
    def setUp(self):
        """테스트에 사용할 샘플 데이터 초기화"""
        self.sample_request = {
            "ideaName": "AI 피트니스 코치",
            "summary": "건강 데이터 기반 개인화 운동 솔루션",
            "features": ["실시간 AI 분석", "맞춤형 운동 프로그램"],
            "targetAudience": "2030대 직장인"
        }
        self.sample_rag_data = {
            "market_size": "2030년 $1.2조 (출처: Gartner 2024)",
            "similar_services": [
                {"name": "ServiceA", "score": 0.85, "source": "Crunchbase"}
            ]
        }
        
        # 빈 프롬프트, 팀원이 입력할 예정
        self.test_prompt = ""  

    def test_generate_prompt(self):
        """프롬프트 생성 로직 테스트"""
        prompt = generate_prompt(self.sample_request, self.sample_rag_data)
        
        # 필수 키워드가 포함되었는지 확인
        self.assertIn("AI 피트니스 코치", prompt)
        self.assertIn("건강 데이터 기반 개인화 운동 솔루션", prompt)
        self.assertIn("실시간 AI 분석", prompt)
        self.assertIn("2030대 직장인", prompt)
        self.assertIn("2030년 $1.2조", prompt)  # RAG 데이터 검증

    def test_prompt_structure(self):
        """프롬프트 구조 검증"""
        prompt = generate_prompt(self.sample_request, self.sample_rag_data)
        
        # JSON 형식이 포함되었는지 확인
        self.assertIn('"similarServices"', prompt)
        self.assertIn('"marketAnalysis"', prompt)
        self.assertIn('"swotAnalysis"', prompt)

    def test_empty_input(self):
        """빈 입력에 대한 예외 처리"""
        with self.assertRaises(ValueError):
            generate_prompt({}, {})

    def test_partial_input(self):
        """부분 입력에 대한 처리"""
        partial_request = {"ideaName": "테스트 아이디어", "summary": "짧은 요약"}
        prompt = generate_prompt(partial_request, {})
        self.assertIn("테스트 아이디어", prompt)
        self.assertIn("짧은 요약", prompt)

    def test_rag_data_integration(self):
        """RAG 데이터 통합 검증"""
        prompt = generate_prompt(self.sample_request, self.sample_rag_data)
        self.assertIn("Crunchbase", prompt)  # RAG 데이터 출처 확인
        self.assertIn("ServiceA", prompt)    # 유사 서비스 이름 확인

    def test_prompt_execution(self):
        """실제 서비스 환경에서 프롬프트 실행 테스트"""
        response = run_prompt_test(self.test_prompt, self.sample_request, self.sample_rag_data)
        self.assertIsInstance(response, dict)  # 결과가 JSON 형식인지 확인
        self.assertIn("similarServices", response)
        self.assertIn("marketAnalysis", response)


def generate_prompt(request: Dict[str, Any], rag_data: Dict[str, Any]) -> str:
    """프롬프트 생성 함수"""
    if not request:
        raise ValueError("입력 데이터가 비어 있습니다.")

    return f"""
    ## 분석 요구사항
    1. 유사 서비스 비교 (차이점, 유사도 점수)
    2. RAG 데이터 기반 시장 규모 추정
    3. 출처 명시 필수

    ## 입력 데이터
    - 아이디어명: {request.get("ideaName", "N/A")}
    - 요약: {request.get("summary", "N/A")}
    - 주요 기능: {", ".join(request.get("features", []))}
    - 타겟층: {request.get("targetAudience", "N/A")}
    - RAG 데이터: {json.dumps(rag_data, ensure_ascii=False)}

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

def run_prompt_test(prompt: str, request: Dict[str, Any], rag_data: Dict[str, Any]) -> Dict[str, Any]:
    """실제 AI 모델에 프롬프트 전달 및 응답 받기"""
    if not prompt:
        prompt = generate_prompt(request, rag_data)
    
    # 여기에 실제 AI API 호출 코드 추가 필요 (예: OpenAI API)
    response = {
        "similarServices": [
            {"name": "ServiceA", "difference": "더 많은 기능 제공 (출처: 공식 웹사이트)", "similarityScore": 0.85, "source": "Crunchbase"}
        ],
        "marketAnalysis": {
            "tam": "$1.2조 (출처: Gartner 2024)",
            "sam": "$500억",
            "cagr": "15%",
            "dataSources": ["Gartner 2024"]
        },
        "swotAnalysis": {
            "strengths": ["AI 기반 혁신 (출처: 논문)"]
        }
    }
    return response

if __name__ == "__main__":
    unittest.main()