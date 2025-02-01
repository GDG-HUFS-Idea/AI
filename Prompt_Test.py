import unittest
import json
import openai
import os
from typing import Dict, Any

class TestPromptGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """테스트 시작 시 예제 데이터를 파일에서 로드하거나 사용자 입력을 받음"""
        cls.sample_request, cls.sample_rag_data = load_test_data()

    def test_generate_prompt(self):
        """GPT-4o mini API를 호출하여 기대한 JSON 응답을 생성하는지 테스트"""
        response_text = generate_prompt(self.sample_request, self.sample_rag_data)
        
        # 응답을 JSON 형식으로 변환
        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError:
            self.fail("API 응답이 올바른 JSON 형식이 아닙니다.")

        # 기대한 JSON 키가 포함되어 있는지 확인
        expected_keys = ["swotAnalysis", "pestelAnalysis", "similarServices", "marketAnalysis"]
        for key in expected_keys:
            self.assertIn(key, response_json, f"응답에 {key} 키가 포함되어야 합니다.")

    def test_rag_data_integration(self):
        """RAG 데이터가 API 응답 내에 반영되는지 테스트"""
        response_text = generate_prompt(self.sample_request, self.sample_rag_data)
        self.assertIn("Crunchbase", response_text)
        self.assertIn("ServiceA", response_text)
        self.assertIn("0.85", response_text)  # 유사도 점수 포함 여부 확인

def load_test_data():
    """테스트용 데이터를 JSON 파일에서 읽거나 사용자 입력을 통해 로드"""
    file_path = "test_data.json"
    
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            print("[INFO] 테스트 데이터를 test_data.json에서 로드했습니다.")
            return data["request"], data["rag_data"]
    
    print("[INFO] test_data.json 파일이 없습니다. 직접 입력해주세요.")
    request = {
        "ideaName": input("아이디어 이름: "),
        "summary": input("아이디어 개요: "),
        "features": input("주요 기능(쉼표로 구분): ").split(","),
        "targetAudience": input("대상 고객: ")
    }
    rag_data = {
        "market_size": input("시장 규모 정보: "),
        "similar_services": [
            {
                "name": input("유사 서비스 이름: "),
                "score": float(input("유사도 점수(0~1): ")),
                "source": input("출처: ")
            }
        ]
    }
    
    return request, rag_data

def generate_prompt(request: Dict[str, Any], rag_data: Dict[str, Any]) -> str:
    """GPT-4o mini API를 활용한 프롬프트 생성 함수"""
    if not request or not rag_data:
        raise ValueError("입력 데이터 또는 RAG 데이터가 비어 있습니다.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

    # === 사전 작성한 프롬프트 템플릿 ===
    prompt_template = """
    당신은 시장 분석 전문가입니다. 다음 정보를 바탕으로 시장 분석 및 경쟁 분석을 수행하세요.

    - 아이디어명: {ideaName}
    - 개요: {summary}
    - 주요 기능: {features}
    - 대상 고객: {targetAudience}
    
    최신 시장 데이터:
    {rag_data}

    당신의 분석 결과를 JSON 형식으로 제공하세요:
    {{
        "swotAnalysis": {{
            "strengths": "이 아이디어의 강점",
            "weaknesses": "이 아이디어의 약점",
            "opportunities": "시장 기회",
            "threats": "시장 위협"
        }},
        "pestelAnalysis": {{
            "political": "정치적 요인",
            "economic": "경제적 요인",
            "social": "사회적 요인",
            "technological": "기술적 요인",
            "environmental": "환경적 요인",
            "legal": "법적 요인"
        }},
        "similarServices": [...],
        "marketAnalysis": "시장 분석 결과"
    }}
    """

    # 데이터 적용
    formatted_prompt = prompt_template.format(
        ideaName=request.get("ideaName", "N/A"),
        summary=request.get("summary", "N/A"),
        features=", ".join(request.get("features", [])),
        targetAudience=request.get("targetAudience", "N/A"),
        rag_data=json.dumps(rag_data, ensure_ascii=False)
    )

    # OpenAI API 호출
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a helpful AI consultant."},
                      {"role": "user", "content": formatted_prompt}],
            max_tokens=1000
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"OpenAI API 호출 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    unittest.main()