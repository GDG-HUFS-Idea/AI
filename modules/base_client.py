from pplx_api import PerplexityClient
from config.settings import Settings
import logging

logger = logging.getLogger(__name__)

# API 클라이언트 인스턴스를 저장할 전역 딕셔너리
_API_CLIENTS = {
    'perplexity': None,
    'openai': None
}

class BaseAnalyzer:
    """모든 분석 모듈의 기본 클래스"""
    def __init__(self, api_type: str = 'perplexity'):
        self.client = None
        self.api_type = api_type
        self._init_client(api_type)
    
    def _init_client(self, api_type):
        try:
            # 이미 초기화된 클라이언트가 있는지 확인
            if _API_CLIENTS[api_type] is not None:
                self.client = _API_CLIENTS[api_type]
                return
                
            if api_type == 'perplexity':
                self.client = PerplexityClient(
                    api_key=Settings.PERPLEXITY_API_KEY
                )
                logger.info(f"{api_type.upper()} 클라이언트 초기화 완료")
                _API_CLIENTS[api_type] = self.client
            elif api_type == 'openai':
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=Settings.OPENAI_API_KEY,
                    timeout=Settings.OPENAI_TIMEOUT
                )
                logger.info(f"{api_type.upper()} 클라이언트 초기화 완료")
                _API_CLIENTS[api_type] = self.client
        except Exception as e:
            logger.error(f"클라이언트 초기화 실패: {str(e)}")
            raise
    
    # Perplexity API 사용 확인을 위한 메서드 추가
    def search(self, query: str):
        """API에 따른 검색 수행"""
        logger.info(f"검색 수행: {self.api_type} (쿼리 길이: {len(query)})")
        if self.api_type == 'perplexity':
            return self.client.search(query)
        elif self.api_type == 'openai':
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,
                timeout=Settings.OPENAI_TIMEOUT
            )
            return {
                "choices": [
                    {
                        "message": {
                            "content": response.choices[0].message.content
                        }
                    }
                ]
            }
        else:
            logger.error(f"지원하지 않는 API 유형: {self.api_type}")
            return {"error": f"지원하지 않는 API 유형: {self.api_type}"}
