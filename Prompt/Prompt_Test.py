import unittest
import json
import os
import glob
from typing import Dict, Any
from openai import OpenAI, APIError, AuthenticationError, RateLimitError
import datetime

client = OpenAI()

class TestPromptGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_data = cls.load_test_data()
        cls.result_folder = cls._create_result_folder()  # 결과 파일 저장 폴더 설정

    @classmethod
    def load_test_data(cls):
        test_files = sorted(glob.glob("TestData/*.json"))
        data = []
        for file_path in test_files:
            with open(file_path, "r", encoding="utf-8") as file:
                sample = json.load(file)
                data.append(sample)
        return data

    @classmethod
    def _create_result_folder(cls):
        # 결과 폴더를 현재 작업 디렉토리에 생성
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        result_folder = f"result_{timestamp}"
        os.makedirs(result_folder, exist_ok=True)  # result 폴더 생성 (덮어쓰기 방지)
        return result_folder

    def test_generate_prompts(self):
        for index, sample_request in enumerate(self.test_data):
            with self.subTest(sample=index + 1):
                try:
                    response_text = generate_prompt(sample_request)
                    response_json = json.loads(response_text)

                    user_id = sample_request.get("user_id", "default_user")
                    # 각 입력에 대해 고유한 파일 이름 생성
                    result_filename = f"{self.result_folder}/{user_id}_result_{index + 1}.json"
                    summary_filename = f"{self.result_folder}/{user_id}_summary_{index + 1}.json"

                    # 결과 파일 생성
                    with open(result_filename, "w", encoding="utf-8") as file:
                        json.dump(response_json, file, ensure_ascii=False, indent=4)

                    # 요약 파일 생성
                    summary_text = self.summarize_idea(sample_request)  # 아이디어 요약
                    with open(summary_filename, "w", encoding="utf-8") as file:
                        json.dump({"summary": summary_text}, file, ensure_ascii=False, indent=4)

                    # 결과 출력
                    print(f"✅ {result_filename} 및 {summary_filename} 생성 완료.")

                except json.JSONDecodeError:
                    self.fail(f"API 응답이 올바른 JSON 형식이 아닙니다. (샘플 {index + 1})")
                except Exception as e:
                    self.fail(f"테스트 실패: {str(e)} (샘플 {index + 1})")

    def summarize_idea(self, sample_request):
        """사용자의 아이디어를 5단어 이내로 요약하는 함수 (생성형 AI 활용)"""
        problem = sample_request.get("problem", {}).get("identifiedIssues", [])
        solution = sample_request.get("solution", {}).get("coreElements", [])

        # 문제와 해결책을 결합하여 아이디어 텍스트 생성
        idea_text = f"문제: {' '.join(problem)}, 해결책: {' '.join(solution)}"

        # 요약 프롬프트 작성 (5단어 이내 요약 지시)
        summary_system_prompt = "당신은 5단어 이내로 아이디어를 요약하는 전문가입니다."
        summary_user_prompt = f"다음 아이디어를 5단어 이내로 요약해 주세요: {idea_text}"

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # 요약에도 gpt-4o-mini 모델 사용
                messages=[
                    {"role": "system", "content": summary_system_prompt},
                    {"role": "user", "content": summary_user_prompt}
                ],
                max_tokens=30,  # 요약문 생성을 위한 max_tokens 값 조정
                n=1,
                stop=None,
                temperature=0.5, # temperature 값 조정 (선택 사항)
            )
            summary_text = response.choices[0].message.content.strip()
            # summary_text = response.choices[0].message.content.strip() # 요약 결과 텍스트 추출 및 공백 제거
            return summary_text


        except Exception as e:
            print(f"요약 생성 실패: {e}")
            return "요약 실패"  # 요약 실패 시 에러 메시지 반환


def generate_prompt(request: Dict[str, Any]) -> str:
    if not request:
        raise ValueError("입력 데이터가 비어 있습니다.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")  # 모델 버전 명시 (환경 변수 사용)

    system_prompt = """
    당신은 **스타트업 컨설턴트 겸 시장 분석 전문가**입니다.
    사용자가 제시한 아이디어를 바탕으로 **시장 분석**, **기회 요인**, **한계점**, **비즈니스 모델 성공 가능성** 등을 평가하여 JSON 형식의 분석 보고서를 제공합니다.

    결과 JSON 형식:
    {
        "marketAnalysis": {
            "classification": {
                "large": "대분류",
                "medium": "중분류",
                "small": "소분류"
            },
            "averageRevenue": {
                "domestic": "연 매출 약 3조 원 추정",
                "global": "연 매출 약 20조 원 추정"
            },
            "last5YearsGrowthChart": {
                "2018": "5%",
                "2019": "7%",
                "2020": "9%",
                "2021": "11%",
                "2022": "13%"
            },
            "scores": {
                "similarServices": [
                    { "name": "서비스1", "url": "링크1", "similarityScore": "85%", "similarityFormula": "TF-IDF + Cosine Similarity" },
                    { "name": "서비스2", "url": "링크2", "similarityScore": "80%", "similarityFormula": "TF-IDF + Cosine Similarity" },
                    { "name": "서비스3", "url": "링크3", "similarityScore": "75%", "similarityFormula": "TF-IDF + Cosine Similarity" },
                    { "name": "서비스4", "url": "링크4", "similarityScore": "70%", "similarityFormula": "TF-IDF + Cosine Similarity" },
                    { "name": "서비스5", "url": "링크5", "similarityScore": "65%", "similarityFormula": "TF-IDF + Cosine Similarity" }
                ],
                "expectedBM": { ... },
                "fieldScores": {
                    "marketSize": 8.5,
                    "growthPotential": 9.0,
                    "bmViability": 7.5,
                    "competitiveAdvantage": 8.0,
                    "overallScore": 8.2
                },
                "totalScore": 8.2
            },
            "opportunities": { ... },
            "limitations": { ... },
            "requiredTeam": [
                {
                    "role": "AI 전문가",
                    "tasks": "자연어 처리 모델 개발 및 성능 최적화",
                    "competencies": ["자연어 처리", "머신러닝", "딥러닝", "Python", "TensorFlow/PyTorch"]
                },
                {
                    "role": "백엔드 개발자",
                    "tasks": "API 및 서버 인프라 구축, 데이터베이스 설계",
                    "competencies": ["Python", "Django/Flask", "REST API 설계", "Database (SQL/NoSQL)", "AWS/GCP"]
                },
                {
                    "role": "디자이너",
                    "tasks": "UX/UI 디자인 및 프로토타이핑",
                    "competencies": ["UX/UI 디자인", "Figma/Sketch", "GUI 디자인", "사용자 리서치"]
                },
                {
                    "role": "마케팅 전문가",
                    "tasks": "시장 조사, 홍보 전략 수립 및 실행",
                    "competencies": ["시장 조사", "데이터 분석", "디지털 마케팅", "콘텐츠 마케팅", "SEO/SEM"]
                }
            ],
            "oneLineReview": "제안하신 아이디어는 혁신적인 기술적 접근 방식과 시장 성장 가능성 측면에서 강점이 될 수 있고, 초기 시장 진입 장벽과 법적 리스크 부분 때문에 위험이 될 수 있습니다."
        }
    }
    """

    formatted_prompt = f"{system_prompt}\n{json.dumps(request, ensure_ascii=False)}"

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": formatted_prompt}
            ],
            max_tokens=1500,
            response_format={"type": "json_object"},
            timeout=30,  # 타임아웃 설정 (초 단위)
        )

        response_content = response.choices[0].message.content

    except AuthenticationError as auth_err:
        print(f"인증 오류: {auth_err}")
        raise
    except RateLimitError as rate_limit_err:
        print(f"API Rate Limit 초과: {rate_limit_err}")
        raise
    except APIError as api_err:
        print(f"API 오류: {api_err}")
        print(f"API 응답 내용: {api_err.response.text}")  # 에러 응답 내용 출력
        raise
    except Exception as e:
        print(f"기타 오류 발생: {e}")
        raise

    return response_content

def save_json(data, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)  # 폴더가 없다면 생성
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ {filename} 저장 완료")

if __name__ == "__main__":
    unittest.main()