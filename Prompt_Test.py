import unittest
import json
import os
import glob
from typing import Dict, Any
from openai import OpenAI, APIError, AuthenticationError, RateLimitError

client = OpenAI()

class TestPromptGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_data = cls.load_test_data()

    @classmethod
    def load_test_data(cls):
        test_files = sorted(glob.glob("Test_Files/*.json"))  
        data = []
        for file_path in test_files:
            with open(file_path, "r", encoding="utf-8") as file:
                sample = json.load(file)
                data.append(sample)
        return data

    def test_generate_prompts(self):
        for index, sample_request in enumerate(self.test_data):
            with self.subTest(sample=index + 1):
                try:
                    response_text = generate_prompt(sample_request)
                    response_json = json.loads(response_text)

                    user_id = sample_request.get("user_id", "default_user")
                    result_filename = f"{user_id}_result({index + 1}).json"
                    summary_filename = f"{user_id}_summary({index + 1}).json"

                    save_json(response_json, result_filename)
                    
                    # ✅ Summary 파일 개선: 아이디어 키워드만 포함
                    idea_keywords = response_json.get("marketAnalysis", {}).get("ideaKeywords", [])
                    save_json({"keywords": idea_keywords}, summary_filename)

                except json.JSONDecodeError:
                    self.fail(f"API 응답이 올바른 JSON 형식이 아닙니다. (샘플 {index + 1})")
                except Exception as e:
                    self.fail(f"테스트 실패: {str(e)} (샘플 {index + 1})")

def generate_prompt(request: Dict[str, Any]) -> str:
    if not request:
        raise ValueError("입력 데이터가 비어 있습니다.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

    system_prompt = """
    당신은 **스타트업 컨설턴트 겸 시장 분석 전문가**입니다.  
    사용자가 제시한 아이디어를 바탕으로 **시장 분석**, **기회 요인**, **한계점**, **비즈니스 모델 성공 가능성** 등을 평가하여 JSON 형식의 분석 보고서를 제공합니다.

    결과 JSON 형식:
    {
        "marketAnalysis": {
            "classification": { ... },
            "averageRevenue": { ... },  
            "last5YearsGrowthChart": { "growthRate": "15.2%", "source": "출처 링크" },  
            "scores": {  
                "similarServices": [  
                    { "name": "서비스명", "url": "링크", "similarityScore": "85%", "similarityFormula": "TF-IDF + Cosine Similarity" }  
                ],  
                "expectedBM": { ... }
            },  
            "opportunities": { ... },  
            "limitations": { ... },  
            "requiredTeam": [  
                { "role": "AI 전문가", "tasks": "자연어 처리 모델 개발 및 성능 최적화" },  
                { "role": "백엔드 개발자", "tasks": "API 및 서버 인프라 구축, 데이터베이스 설계" },  
                { "role": "디자이너", "tasks": "UX/UI 디자인 및 프로토타이핑" },  
                { "role": "마케팅 전문가", "tasks": "시장 조사, 홍보 전략 수립 및 실행" }  
            ],  
            "oneLineReview": "제안하신 아이디어는 혁신적인 기술적 접근 방식과 시장 성장 가능성 측면에서 강점이 될 수 있고, 초기 시장 진입 장벽과 법적 리스크 부분 때문에 위험이 될 수 있습니다. 시장 진출 타이밍은 업계 트렌드 변화가 가시화되는 시점이 적절할 것으로 보입니다.",
            "totalScore": 7.8  
        }
    }

    - **시장 구분**: 대분류 > 중분류 > 소분류 > 세분류 방식 적용
    - **업계 평균 매출**: 국내 및 글로벌 시장 비교
    - **최근 5년 성장률**: "~%" 형식 및 시장 조사 출처 포함
    - **유사 서비스 경쟁력 분석**: 유사 서비스 5개 제공 및 유사도 백분율 표기
    - **비즈니스 모델 평가**: 성공 가능성 점수 및 적용 가능 BM 설명
    - **기회 요인**: 정부 지원사업, 고객층, 제휴·파트너십 가능성 포함
    - **한계점**: 법률/특허 이슈, 시장 진입장벽, 기술적 리스크 포함
    - **핵심 직군**: 역할별 세부 작업 내용 포함
    - **아이디어 요약**: 강점/위험 요소/시장 진출 타이밍 포함
    """

    formatted_prompt = f"{system_prompt}\n{json.dumps(request, ensure_ascii=False)}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted_prompt}
        ],
        max_tokens=1200,
        response_format={"type": "json_object"}
    )
    
    response_content = response.choices[0].message.content
    return response_content

def save_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ {filename} 저장 완료")

if __name__ == "__main__":
    unittest.main()
