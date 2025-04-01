from .base_client import BaseAnalyzer
import logging

logger = logging.getLogger(__name__)

class TeamAnalyzer(BaseAnalyzer):
    """팀 구성 분석 모듈"""
    
    def __init__(self):
        super().__init__(api_type='perplexity')
        
    def analyze(self, idea: str, problem: dict = None, solution: dict = None) -> dict:
        # 문제와 해결책에서 추가 정보 추출
        issues = ' '.join(problem.get('identifiedIssues', [])) if problem else ''
        core_elements = ' '.join(solution.get('coreElements', [])) if solution else ''
        
        query = (
            f"다음 비즈니스 아이디어를 성공적으로 실현하기 위해 필요한 팀 구성을 상세히 분석해주세요:\n\n"
            f"비즈니스 아이디어: {idea}\n"
            f"해결하고자 하는 문제: {issues}\n"
            f"핵심 기능/요소: {core_elements}\n\n"
            f"다음 정보를 포함한 분석이 필요합니다:\n"
            f"1. 필요한 직책/역할(최소 3가지): 구체적인 직함과 역할\n"
            f"2. 각 역할별 필요 역량 및 경험: 구체적인 기술, 지식, 자격 요건\n"
            f"3. 담당해야 할 업무 범위: 상세한 업무 내용\n"
            f"4. 팀 구성의 우선순위: 초기 스타트업 단계에서 먼저 영입해야 할 역할 순서\n"
            f"최소 필요 인력부터 이상적인 팀 구성까지 단계별로 제안해주세요.\n"
            f"응답은 한국어로 작성하고, 출처를 포함해주세요."
        )
        
        response = self.client.search(query)
        return self._parse(response)
        
    def _parse(self, data: dict) -> dict:
        try:
            content = data['choices'][0]['message']['content']
            return content
        except (KeyError, IndexError) as e:
            logger.error(f"팀 분석 응답 형식 오류: {str(e)}")
            return "팀 분석 데이터 없음"
