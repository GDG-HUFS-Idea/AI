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

    def test_generate_prompt(self):
        """프롬프트 생성 로직 테스트"""
        prompt = generate_prompt(self.sample_request, self.sample_rag_data)
        
        # 필수 키워드 포함 여부 확인
        self.assertIn(self.sample_request["ideaName"], prompt)
        self.assertIn(self.sample_request["summary"], prompt)
        self.assertIn(self.sample_rag_data["market_size"], prompt)

    def test_prompt_structure(self):
        """프롬프트가 JSON 구조를 포함하는지 검증"""
        prompt = generate_prompt(self.sample_request, self.sample_rag_data)

        # JSON 부분이 올바르게 생성되었는지 확인
        json_start = prompt.find('{')
        json_data = prompt[json_start:]  # JSON 부분만 추출
        try:
            parsed_json = json.loads(json_data)
            self.assertIsInstance(parsed_json, dict)
            self.assertIn("similarServices", parsed_json)
            self.assertIn("marketAnalysis", parsed_json)
        except json.JSONDecodeError:
            self.fail("생성된 프롬프트의 JSON 구조가 올바르지 않습니다.")

    def test_empty_input(self):
        """빈 입력에 대한 예외 처리 검증"""
        with self.assertRaises(ValueError):
            generate_prompt({}, {})

    def test_rag_data_integration(self):
        """RAG 데이터 통합 검증"""
        prompt = generate_prompt(self.sample_request, self.sample_rag_data)
        self.assertIn("Crunchbase", prompt)
        self.assertIn("ServiceA", prompt)
        self.assertIn("0.85", prompt)  # 유사도 점수 포함 여부 확인

def generate_prompt(request: Dict[str, Any], rag_data: Dict[str, Any]) -> str:
    """프롬프트 생성 함수 (AI 팀원의 프롬프트를 적용할 부분)"""
    if not request or not rag_data:
        raise ValueError("입력 데이터 또는 RAG 데이터가 비어 있습니다.")

    # === 프롬프트 적용 ==한
    # 아래 문자열을 사전 작성한 프롬프트로 교체하고, {변수명}을 적절히 매핑
    prompt_template = """
    여기에 AI 팀원이 작성한 프롬프트를 입력하세요.
    그리고 {ideaName}, {summary}, {features}, {targetAudience}, {rag_data} 등을 포함하도록 변수화하세요.
    """

    # 데이터 삽입
    formatted_prompt = prompt_template.format(
        ideaName=request.get("ideaName", "N/A"),
        summary=request.get("summary", "N/A"),
        features=", ".join(request.get("features", [])),
        targetAudience=request.get("targetAudience", "N/A"),
        rag_data=json.dumps(rag_data, ensure_ascii=False)
    )

    return formatted_prompt

if __name__ == "__main__":
    unittest.main()