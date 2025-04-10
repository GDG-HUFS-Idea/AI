import os
from dotenv import load_dotenv
load_dotenv()

class SettingsMeta(type):
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        cls._validate_environment()
        return instance

    @classmethod
    def _validate_environment(cls):
        required_vars = ['PERPLEXITY_API_KEY', 'OPENAI_API_KEY']
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise EnvironmentError(f"필수 환경 변수 누락: {', '.join(missing)}")

class Settings(metaclass=SettingsMeta):
    # 서비스 설정
    SERVICE_NAME = "SparkLens Business Analysis"
    VERSION = "1.0.0"
    
    # API 키
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
    
    # 타임아웃 설정 (초)
    OPENAI_TIMEOUT = 90
    PERPLEXITY_TIMEOUT = 90  # 타임아웃 연장 (60초 -> 90초)
    
    # 분석 동시 요청 제한
    MAX_CONCURRENT_ANALYSES = 5
    
    # 쓰레딩 설정
    THREADPOOL_SIZE = 5
    
    # 로깅 설정
    LOG_LEVEL = "INFO"
    
    # 결과 캐싱 설정
    ENABLE_CACHING = True
    CACHE_TTL = 3600 * 24  # 24시간
    
    # 재시도 설정
    MAX_RETRIES = 5
    RETRY_DELAY = 3  # 초
    
    @classmethod
    def get_env(cls, var_name: str) -> str:
        value = os.getenv(var_name)
        if not value:
            raise ValueError(f"{var_name} 환경 변수 미설정")
        return value
