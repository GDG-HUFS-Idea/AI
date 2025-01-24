from flask import Flask, request, jsonify
import openai

app = Flask(__name__)

# OpenAI API 키 설정
openai.api_key = 'your_openai_api_key_here'

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    user_input = data.get('input')

    # 분석 수행
    similar_services = find_similar_services(user_input)
    market_analysis = analyze_market(user_input)
    swot_analysis = perform_swot_analysis(user_input)

    # 결과 정리
    result = {
        'similar_services': similar_services,
        'market_analysis': market_analysis,
        'swot_analysis': swot_analysis
    }
    return jsonify(result)

def find_similar_services(user_input):
    prompt = (
        f"아이디어 '{user_input}'에 유사한 서비스를 찾아 주세요. "
        "서비스의 이름, 주요 기능, 목표 시장, 사용자 층, 이 아이디어와의 차별점을 구체적으로 설명해 주세요. "
        "서비스를 나열하기 전에 유사 서비스를 선정하는 기준도 간략히 설명해 주세요. "
        "예시:\n\n"
        "서비스: Spotify\n"
        "기능: 스트리밍 음악 서비스\n"
        "시장: 글로벌 음악 애호가\n"
        "사용자 층: 18-35세 음악 팬\n"
        "차별점: 사용자 개인화된 음악 추천\n"
        "\n"
        "이 형식을 참고하여 아이디어와 유사한 서비스들을 분석해 주세요."
    )
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=500,
        temperature=0.7
    )
    return response.choices[0].text.strip()

def analyze_market(user_input):
    prompt = (
        f"아이디어 '{user_input}'와 관련된 시장을 분석해 주세요. "
        "1. 시장의 전체 규모와 성장률을 설명해 주세요.\n"
        "2. 주요 동향을 나열해 주세요.\n"
        "3. 시장에 영향을 미치는 경제적, 기술적, 사회적 요인을 분석해 주세요.\n"
        "분석에 앞서, 시장 규모와 성장률을 추정하는 방법을 간략히 설명해 주세요. "
        "예시:\n\n"
        "1. 시장 규모: $1 billion, 연평균 성장률(CAGR) 5%\n"
        "2. 주요 동향: 전자상거래 증가, 모바일 쇼핑 트렌드\n"
        "3. 영향 요인: 기술 발전, 경제 회복세, 사회적 트렌드 변화\n"
        "\n"
        "이 형식을 참고하여 시장을 분석해 주세요."
    )
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=600,
        temperature=0.7
    )
    return response.choices[0].text.strip()

def perform_swot_analysis(user_input):
    prompt = (
        f"다음 아이디어에 대해 SWOT 분석을 해주세요: '{user_input}'. "
        f"각각의 Strengths(강점), Weaknesses(약점), Opportunities(기회), Threats(위협)을 상세하게 설명해 주세요."
    )
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=300,
        temperature=0.7
    )
    return response.choices[0].text.strip()

if __name__ == '__main__':
    app.run(debug=True)