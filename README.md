## **프로젝트 개요**

SparkLens는 비즈니스 아이디어를 가진 개인이나 팀에게 데이터 기반의 객관적인 사업화 가능성 평가를 제공합니다. 사용자가 자신의 아이디어(문제점과 해결책)를 입력하면 시스템은 다양한 분석 모듈을 통해 종합적인 사업 평가 리포트를 생성합니다.

## **핵심 기능**

- KSIC(한국표준산업분류) 기반 산업 분류
- 국내 및 글로벌 시장 분석 (규모, 성장률, 평균 매출)
- 유사 서비스 분석 및 유사도 평가
- 타겟 고객층 분석
- 비즈니스 모델 및 수익 구조 제안
- 마케팅 전략 수립
- 기회 요인 및 지원 사업 정보 제공
- 한계점 및 리스크 분석
- 필요 팀원 구성 제안
- 분야별 점수 및 종합 평가

## **기술 스택**

- **데이터 수집**: Perplexity AI의 Sonar API
- **데이터 처리 및 리포트 생성**: OpenAI의 GPT-4o-mini API
- **개발 언어**: Python
- **테스트 프레임워크**: unittest

### 1. 시스템 아키텍쳐 개요

SparkLens는 모듈화된 아키텍처를 채택하여 유지보수성을 높이고 기능별 테스트가 용이하도록 설계되었습니다.

```mermaid
graph TB
    User[사용자] --> |비즈니스 아이디어 입력| API[API 엔드포인트]
    API --> Controller[비즈니스 분석 컨트롤러]
    
    Controller --> KSICClassifier[산업 분류기]
    Controller --> MarketAnalyzer[시장 분석기]
    Controller --> SimilarServiceFinder[유사 서비스 탐색기]
    Controller --> OpportunityAnalyzer[기회 요인 분석기]
    Controller --> LimitationAnalyzer[한계점 분석기]
    Controller --> TeamAnalyzer[팀 구성 분석기]
    
    subgraph ExternalAPIs[외부 API]
        Perplexity[Perplexity AI Sonar]
        OpenAI[OpenAI GPT-4o-mini]
    end
    
    KSICClassifier --> Perplexity
    MarketAnalyzer --> Perplexity
    SimilarServiceFinder --> Perplexity
    OpportunityAnalyzer --> Perplexity
    LimitationAnalyzer --> Perplexity
    TeamAnalyzer --> Perplexity
    
    Controller --> PromptBuilder[프롬프트 생성기]
    PromptBuilder --> OpenAI
    OpenAI --> |최종 리포트| Controller
    
    Controller --> ReportValidator[리포트 검증기]
    ReportValidator --> |검증 완료된 리포트| API
    API --> |분석 리포트| User

```

## **컴포넌트 상세 설명**

## **1. 클라이언트 및 API 모듈**

## **BaseAnalyzer (modules/base_client.py)**

모든 분석 모듈의 기본 클래스로, API 클라이언트 초기화 및 검색 기능을 제공합니다.

```mermaid
classDiagram
    class BaseAnalyzer {
        -client
        -api_type
        +__init__(api_type)
        +_init_client(api_type)
        +search(query)
    }
    
    class PerplexityClient {
        -api_key
        -headers
        -api_url
        +__init__(api_key)
        +search(query)
    }
    
    class AsyncAnalyzer {
        +async_search(query)
        -_create_error_response(error_message)
        +is_error_response(response)
    }
    
    BaseAnalyzer <|-- AsyncAnalyzer
    BaseAnalyzer --> PerplexityClient : uses

```

## **PerplexityClient (pplx_api.py)**

Perplexity AI API와의 통신을 담당하는 클라이언트 클래스입니다.

## **AsyncAnalyzer (async_client.py)**

비동기적으로 API 요청을 수행하는 분석기 클래스입니다. 백오프 재시도 로직을 포함합니다.

## **2. 분석 모듈**

각 분석 모듈은 특정 영역의 데이터를 수집하고 처리하는 역할을 담당합니다.

```mermaid
classDiagram
    class BaseAnalyzer {
        +search(query)
    }
    
    class KSICClassifier {
        +classify(idea)
        -_parse(data)
    }
    
    class MarketAnalyzer {
        +analyze(idea, problem, solution)
        -_parse_structured(data)
        -_validate_market_data(data)
    }
    
    class SimilarServiceFinder {
        +find(idea, core_elements)
        -_parse_services(data)
        -_validate_services(services)
        -_extract_services_from_text(text)
        -_calculate_similarity_scores(services, idea, core_elements)
        -_simple_cosine_similarity(text1, text2)
        -_jaccard_similarity(text1, text2)
    }
    
    class OpportunityAnalyzer {
        +find(idea, problem, solution)
        -_parse(data)
    }
    
    class LimitationAnalyzer {
        +analyze(idea, problem, solution)
        -_parse(data)
    }
    
    class TeamAnalyzer {
        +analyze(idea, problem, solution)
        -_parse(data)
    }
    
    BaseAnalyzer <|-- KSICClassifier
    BaseAnalyzer <|-- MarketAnalyzer
    BaseAnalyzer <|-- SimilarServiceFinder
    BaseAnalyzer <|-- OpportunityAnalyzer
    BaseAnalyzer <|-- LimitationAnalyzer
    BaseAnalyzer <|-- TeamAnalyzer

```

## **KSICClassifier (modules/industry_classifier.py)**

한국표준산업분류(KSIC) 기준으로 아이디어의 산업 분류를 제공합니다.

## **MarketAnalyzer (modules/market_analyzer.py)**

국내 및 글로벌 시장 규모, 성장률, 평균 매출 등의 시장 분석 데이터를 수집합니다.

## **SimilarServiceFinder (modules/similar_service_finder.py)**

아이디어와 유사한 서비스들을 찾고, 유사도 점수를 계산합니다. 코사인 유사도(70%)와 자카드 유사도(30%)를 결합한 가중 평균 방식을 사용합니다.

## **OpportunityAnalyzer (modules/opportunity_analyzer.py)**

아이디어의 시장 기회 요인과 활용 가능한 지원 사업 정보를 제공합니다.

## **LimitationAnalyzer (modules/limitation_analyzer.py)**

아이디어의 법률적 규제, 특허 관련 이슈, 시장 진입 장벽, 기술적 제약 등의 한계점을 분석합니다.

## **TeamAnalyzer (modules/team_analyzer.py)**

아이디어 실현에 필요한 팀 구성, 역할, 필요 역량, 예상 인건비 등을 분석합니다.

## **3. 프롬프트 및 리포트 처리 모듈**

```mermaid
classDiagram
    class PromptBuilder {
        +build(data)
    }
    
    class ReportValidator {
        +validate(report)
        +format_field(field, default_value)
    }
    
    class BusinessAnalysisTest {
        -test_data
        -result_dir
        -modules
        +setUpClass()
        +_load_test_data()
        +_create_result_dir()
        +_handle_error(error, sample)
        +_log_unexpected_error(error, sample)
        +_reinitialize_modules()
        +test_full_analysis_flow()
        -_collect_data(sample)
        -_generate_report(data)
        -_extract_json_from_content(content)
        -_structure_text_to_json(text)
        -_ensure_required_fields(report, data)
        -_create_fallback_report(data)
        -_simulate_report(data)
        -_save_results(report, sample, idx)
        -_generate_summary(sample, path)
        -_simulate_summary(sample, path)
    }

```

## **PromptBuilder (modules/prompt_builder.py)**

수집된 데이터를 바탕으로 GPT-4o-mini용 프롬프트를 생성합니다. 최종 리포트 형식과 필요한 항목들을 상세히 정의합니다.

## **ReportValidator (modules/report_validators.py)**

생성된 리포트의 구조와 내용을 검증하고, 누락된 필드가 있는 경우 기본값을 제공합니다.

## **4. 테스트 및 설정 모듈**

## **BusinessAnalysisTest (tests/test_business_analysis.py)**

테스트 시나리오를 실행하고 결과를 검증하는 테스트 클래스입니다. 실제 아이디어 데이터를 로드하여 전체 분석 흐름을 테스트합니다.

## **Settings (config/settings.py)**

환경 변수와 시스템 설정을 관리하는 설정 클래스입니다. API 키, 타임아웃, 재시도 횟수 등을 설정합니다.

## **5. 데이터 흐름도**

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Test as 테스트 모듈
    participant Modules as 분석 모듈들
    participant Perplexity as Perplexity AI
    participant PromptBuilder as 프롬프트 생성기
    participant OpenAI as GPT-4o-mini
    participant Validator as 리포트 검증기
    
    User->>Test: 비즈니스 아이디어 입력
    
    Test->>Modules: 데이터 수집 요청
    
    loop 각 분석 모듈별 처리
        Modules->>Perplexity: 쿼리 요청
        Perplexity-->>Modules: 데이터 반환
    end
    
    Modules-->>Test: 수집된 데이터 반환
    
    Test->>PromptBuilder: 데이터 통합 및 프롬프트 생성
    PromptBuilder-->>Test: 생성된 프롬프트 반환
    
    Test->>OpenAI: 프롬프트 전송
    OpenAI-->>Test: 리포트 생성 및 반환
    
    Test->>Validator: 리포트 검증
    Validator-->>Test: 검증된 리포트 반환
    
    Test->>User: 최종 리포트 및 요약 제공

```
