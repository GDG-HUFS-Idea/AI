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
    # 타임아웃 설정 증가
    PERPLEXITY_TIMEOUT = 90  # 60초에서 90초로 증가
    OPENAI_TIMEOUT = 90      # 60초에서 90초로 증가
    MAX_RETRIES = 5          # 3에서 5로 재시도 횟수 증가
    
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    @classmethod
    def get_env(cls, var_name: str) -> str:
        value = os.getenv(var_name)
        if not value:
            raise ValueError(f"{var_name} 환경 변수 미설정")
        return value
