import requests
import logging
from config.settings import Settings

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
        try:
            payload = {
                "model": "sonar",  # 모델명 업데이트
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that provides accurate and detailed information. Please search and respond with comprehensive data."},
                    {"role": "user", "content": query}
                ]
            }
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=Settings.PERPLEXITY_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Perplexity API 요청 실패: {str(e)}")
            # 실패 시 최소한의 구조를 반환하여 흐름 유지
            return {
                "choices": [
                    {
                        "message": {
                            "content": f"API 요청 실패: {str(e)}"
                        }
                    }
                ]
            }