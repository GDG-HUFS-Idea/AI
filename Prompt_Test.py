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
        """GPT-4o API를 호출하여 기대한 JSON 응답을 생성하는지 테스트"""
        response_text = generate_prompt(self.sample_request, self.sample_rag_data)
        
        # 응답을 JSON 형식으로 변환
        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError:
            self.fail("API 응답이 올바른 JSON 형식이 아닙니다.")

        # 기대한 JSON 키가 포함되어 있는지 확인
        expected_keys = [
            "swotAnalysis", "pestelAnalysis", "towsAnalysis",
            "similarServices", "marketAnalysis", "marketGrowth", "ideaSuitability"
        ]
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
        "serviceSummary": input("서비스 요약: "),
        "serviceMotivation": {
            "external": input("외부 동기(사회·경제·기술 분야 국내·외 시장의 기회): "),
            "internal": input("내부 동기(가치관, 비전 등): ")
        },
        "problem": input("문제점: "),
        "solution": input("해결책: "),
        "team": {
            "members": [
                {
                    "name": input("팀원 이름: "),
                    "role": input("역할: "),
                    "experience": input("경력: ")
                }
            ],
            "networks": input("기술적·인적 네트워크: ")
        },
        "difference": input("차별화 방안: ")
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
    """GPT-4o API를 활용한 프롬프트 생성 함수"""
    if not request or not rag_data:
        raise ValueError("입력 데이터 또는 RAG 데이터가 비어 있습니다.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

    # === 개선된 프롬프트 템플릿 ===
    prompt_template = """
    당신은 AI 기반 시장 조사 및 경쟁 분석 전문가입니다. 주어진 데이터를 기반으로 SWOT, PESTEL, TOWS 분석을 수행하고, 유사 서비스 비교 및 시장 규모, 성장률, 아이디어 적합성 평가를 제공하세요.

    - 서비스 요약: {serviceSummary}
    - 외부 동기: {externalMotivation}
    - 내부 동기: {internalMotivation}
    - 문제점: {problem}
    - 해결책: {solution}
    - 팀 정보: {team}
    - 차별화 방안: {difference}
    
    최신 시장 데이터:
    {rag_data}

    분석 결과를 아래 JSON 형식으로 반환하세요:
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
        "towsAnalysis": {{
            "soStrategies": "강점과 기회를 활용한 전략",
            "woStrategies": "약점을 개선하며 기회를 활용하는 전략",
            "stStrategies": "강점을 활용하여 위협을 극복하는 전략",
            "wtStrategies": "약점과 위협을 최소화하는 전략"
        }},
        "similarServices": [
            {{
                "name": "유사 서비스명",
                "score": "유사도 점수 (0~1)",
                "source": "출처"
            }}
        ],
        "marketAnalysis": "시장 분석 결과",
        "marketGrowth": "시장 성장률 및 전망",
        "ideaSuitability": "이 아이디어의 시장 적합성 평가"
    }}
    """

    # 데이터 적용
    formatted_prompt = prompt_template.format(
        serviceSummary=request.get("serviceSummary", "N/A"),
        externalMotivation=request.get("serviceMotivation", {}).get("external", "N/A"),
        internalMotivation=request.get("serviceMotivation", {}).get("internal", "N/A"),
        problem=request.get("problem", "N/A"),
        solution=request.get("solution", "N/A"),
        team=json.dumps(request.get("team", {}), ensure_ascii=False),
        difference=request.get("difference", "N/A"),
        rag_data=json.dumps(rag_data, ensure_ascii=False)
    )

    # OpenAI API 호출
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a market analysis AI consultant."},
                      {"role": "user", "content": formatted_prompt}],
            max_tokens=1000
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"OpenAI API 호출 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    unittest.main()