from .base_client import BaseAnalyzer
import json
import logging
import re

logger = logging.getLogger(__name__)

class KSICClassifier(BaseAnalyzer):
    """한국 표준 산업 분류기"""

    def __init__(self):
        super().__init__(api_type='perplexity')

    def classify(self, idea: str) -> dict:
        query = (
            f"다음 형식으로 정확히 응답해주세요:\n"
            "{\n"
            ' "large": {"code": "A", "name": "대분류명"},\n'
            ' "medium": {"code": "A1", "name": "중분류명"},\n'
            ' "small": {"code": "A11", "name": "소분류명"},\n'
            ' "detail": {"code": "A111", "name": "세분류명"}\n'
            "}\n\n"
            f"비즈니스 아이디어: {idea}\n"
            f"위 형식의 JSON으로만 응답해주세요."
        )

        response = self.client.search(query)
        return self._parse(response)

    def _parse(self, data: dict) -> dict:
        try:
            content = data['choices'][0]['message']['content'].strip()
            
            # 코드 블록 처리 제거
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()

            # JSON 파싱 시도
            try:
                parsed = json.loads(content)
                return {
                    "large": parsed.get("large", {"code": "Unknown", "name": "Unknown"}),
                    "medium": parsed.get("medium", {"code": "Unknown", "name": "Unknown"}),
                    "small": parsed.get("small", {"code": "Unknown", "name": "Unknown"}),
                    "detail": parsed.get("detail", {"code": "Unknown", "name": "Unknown"})
                }
            except json.JSONDecodeError:
                # 자연어 응답에서 코드/명 추출 시도 (fallback)
                logger.warning("KSIC JSON 파싱 실패, 자연어 응답 분석 시도")
                return self._fallback_parse_from_text(content)

        except Exception as e:
            logger.error(f"KSIC 응답 처리 중 예외 발생: {str(e)}")
            return self._empty_result("Exception")

    def _fallback_parse_from_text(self, content: str) -> dict:
        try:
            return {
                "large": self._extract_code_name(content, "대분류"),
                "medium": self._extract_code_name(content, "중분류"),
                "small": self._extract_code_name(content, "소분류"),
                "detail": self._extract_code_name(content, "세분류"),
            }
        except Exception as e:
            logger.error(f"자연어 응답에서 KSIC 추출 실패: {str(e)}")
            return self._empty_result("FallbackError")

    def _extract_code_name(self, text: str, level: str) -> dict:
        pattern = rf"{level}[:\s]*([A-Z0-9]+)[^\w가-힣]*([가-힣\w ]+)"
        match = re.search(pattern, text)
        if match:
            return {"code": match.group(1).strip(), "name": match.group(2).strip()}
        return {"code": "Unknown", "name": "Unknown"}

    def _empty_result(self, reason: str = "") -> dict:
        logger.warning(f"KSIC 분류 실패 - {reason}")
        return {
            "large": {"code": "Unknown", "name": "Unknown"},
            "medium": {"code": "Unknown", "name": "Unknown"},
            "small": {"code": "Unknown", "name": "Unknown"},
            "detail": {"code": "Unknown", "name": "Unknown"}
        }