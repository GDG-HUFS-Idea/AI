import aiohttp
import asyncio
import logging
import backoff
import json
from typing import Dict, Any, Optional
from config.settings import Settings
from modules.base_client import BaseAnalyzer

logger = logging.getLogger(__name__)

class AsyncAnalyzer(BaseAnalyzer):
    """비동기 API 요청을 위한 분석기"""
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError),
        max_tries=Settings.MAX_RETRIES,
        jitter=backoff.full_jitter
    )
    async def async_search(self, query: str) -> Dict[str, Any]:
        """비동기 검색 요청 실행"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {Settings.PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "pplx-70b-online",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that provides accurate information."},
                        {"role": "user", "content": query}
                    ]
                }
                
                # 요청 시작 로깅
                logger.debug(f"API 요청 시작: {query[:50]}...")
                
                async with session.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=Settings.PERPLEXITY_TIMEOUT
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"비동기 API 오류: 상태 코드 {response.status}, 응답: {error_text}")
                        return self._create_error_response(f"API 오류: {response.status}")
                    
                    # 응답 로깅
                    logger.debug(f"API 응답 수신: 상태 코드 {response.status}")
                    
                    try:
                        result = await response.json()
                        return result
                    except json.JSONDecodeError as e:
                        raw_text = await response.text()
                        logger.error(f"JSON 파싱 오류: {str(e)}, 원시 응답: {raw_text[:200]}...")
                        return self._create_error_response(f"JSON 파싱 오류: {str(e)}")
                        
        except asyncio.TimeoutError:
            logger.error(f"비동기 요청 타임아웃: {query[:50]}...")
            raise  # 백오프 재시도를 위해 예외 다시 발생
            
        except Exception as e:
            logger.error(f"비동기 요청 예외: {str(e)}")
            return self._create_error_response(str(e))

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """오류 응답 생성"""
        return {
            "choices": [
                {
                    "message": {
                        "content": f"API 요청 실패: {error_message}"
                    }
                }
            ],
            "error": error_message
        }
    
    # 추가 유틸리티 메서드
    def is_error_response(self, response: Dict[str, Any]) -> bool:
        """응답이 오류인지 확인"""
        return "error" in response
