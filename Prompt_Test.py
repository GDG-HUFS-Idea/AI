import unittest
import json
import os
import glob
from typing import Dict, Any
from openai import OpenAI
from openai import APIError, AuthenticationError, RateLimitError

client = OpenAI()

class TestPromptGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """테스트 시작 시 예제 데이터를 파일에서 로드"""
        cls.user_id = "test_user"  # 테스트용 사용자 ID
        cls.sample_request = load_test_data(cls.user_id)

    def test_generate_prompt(self):
        """GPT-4o API를 호출하여 JSON 응답을 생성하는지 테스트"""
        response_text = generate_prompt(self.user_id, self.sample_request)

        # 응답을 JSON 형식으로 변환
        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError:
            self.fail("API 응답이 올바른 JSON 형식이 아닙니다.")

        # 기대한 JSON 키가 포함되어 있는지 확인
        expected_keys = [
            "summary", "marketAnalysis", "scores", "opportunities",
            "limitations", "requiredTeam", "overall"
        ]
        for key in expected_keys:
            self.assertIn(key, response_json, f"응답에 {key} 키가 포함되어야 합니다.")

def load_test_data(user_id: str) -> Dict[str, Any]:
    """가장 최신 사용자 입력 파일을 찾아서 로드"""
    input_files = sorted(glob.glob(f"{user_id}_input(*).json"), key=os.path.getctime, reverse=True)

    if input_files:
        latest_file = input_files[0]
        with open(latest_file, "r", encoding="utf-8") as file:
            print(f"[INFO] {latest_file}에서 테스트 데이터를 로드했습니다.")
            return json.load(file)

    print("[ERROR] 입력 파일을 찾을 수 없습니다.")
    return {}

def generate_prompt(user_id: str, request: Dict[str, Any]) -> str:
    """GPT-4o API를 활용한 프롬프트 생성 함수"""
    if not request:
        raise ValueError("입력 데이터가 비어 있습니다.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

    system_prompt = """
    당신은 **스타트업 컨설턴트 겸 시장 분석 전문가**입니다.
    사용자의 아이디어를 바탕으로 분석을 수행하고, JSON 형식으로 보고서를 제공합니다.
    결과는 다음과 같은 JSON 구조를 따라야 합니다:

    ```json
    {
        "summary": "아이디어 요약",
        "marketAnalysis": "시장 분석",
        "scores": {
            "similarServices": "유사 서비스 점수",
            "expectedBM": "예상 BM 점수"
        },
        "opportunities": "사업 기회 분석",
        "limitations": "한계점 및 리스크",
        "requiredTeam": "필요 팀원 구성",
        "overall": "종합 평가"
    }
    ```
    """

    formatted_prompt = json.dumps(request, ensure_ascii=False, indent=4)

    # OpenAI API 호출
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": formatted_prompt}
            ],
            max_tokens=1000,
            response_format={ "type": "json_object" }
        )
        
        response_content = response.choices[0].message.content
        save_response(user_id, response_content)
        return response_content
    except AuthenticationError:
        raise RuntimeError("OpenAI API 키 인증 실패")
    except RateLimitError:
        raise RuntimeError("API 호출 제한 초과")
    except APIError:
        raise RuntimeError("OpenAI API 서버 연결 실패")
    except Exception as e:
        raise RuntimeError(f"OpenAI API 호출 중 오류 발생: {str(e)}")

def save_response(user_id: str, response_text: str):
    """API 응답 결과를 JSON 파일로 저장"""
    try:
        response_json = json.loads(response_text)
    except json.JSONDecodeError:
        print("[ERROR] 응답이 JSON 형식이 아닙니다.")
        return

    output_files = {
        "summary": f"{user_id}_summary.json",
        "marketAnalysis": f"{user_id}_marketAnalysis.json",
        "scores": f"{user_id}_scores.json",
        "opportunities": f"{user_id}_opportunities.json",
        "limitations": f"{user_id}_limitations.json",
        "requiredTeam": f"{user_id}_requiredTeam.json",
        "overall": f"{user_id}_overall.json"
    }

    for key, file_name in output_files.items():
        if key in response_json:
            with open(file_name, "w", encoding="utf-8") as file:
                json.dump(response_json[key], file, ensure_ascii=False, indent=4)
                print(f"[INFO] {file_name} 파일을 저장했습니다.")

if __name__ == "__main__":
    unittest.main()