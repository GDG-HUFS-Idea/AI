import requests
import logging
from config.settings import Settings
from time import sleep

logger = logging.getLogger(__name__)

class PerplexityClient:
    """Perplexity API 클라이언트"""
    def __init__(self, api_key=None):
        self.api_key = api_key or Settings.PERPLEXITY_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.api_url = "https://api.perplexity.ai/chat/completions"

    def search(self, query: str):
        """Perplexity AI를 통한 검색 실행"""
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that provides accurate and detailed information. Please search and respond with comprehensive data."},
                {"role": "user", "content": query}
            ]
        }

        max_retries = Settings.MAX_RETRIES
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=Settings.PERPLEXITY_TIMEOUT
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                logger.warning(f"[시도 {attempt+1}/{max_retries}] Perplexity 요청 타임아웃 - 재시도 중...")
                sleep(2 ** attempt)  # 지수적 백오프
            except requests.exceptions.RequestException as e:
                logger.error(f"Perplexity API 요청 실패: {str(e)}")
                break

        # 실패 시 최소한의 구조 반환
        return {
            "choices": [
                {
                    "message": {
                        "content": "Perplexity API 요청 실패 또는 응답 없음"
                    }
                }
            ],
            "error": "API 요청 실패"
        }
