import os
import re
import requests
import google.generativeai as genai
from dotenv import load_dotenv

def get_blog_reviews(keyword: str) -> str:
    """
    네이버 블로그 API를 사용하여 특정 키워드에 대한 리뷰 텍스트를 수집합니다.
    HTML 태그를 제거하고 하나의 긴 문자열로 반환합니다.
    """
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("[오류] 네이버 API 클라이언트 ID 또는 시크릿이 .env 파일에 없습니다.")
        return ""

    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {
        "query": keyword,
        "display": 15,  # 상위 15개 포스팅
        "sort": "sim"   # 정확도순
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        combined_text = ""
        for item in data.get("items", []):
            title = item.get("title", "")
            description = item.get("description", "")
            
            # <b>, </b> 등 모든 HTML 태그 제거 (정규식 사용)
            clean_title = re.sub(r'<[^>]*>', '', title)
            clean_desc = re.sub(r'<[^>]*>', '', description)
            
            combined_text += f"{clean_title} {clean_desc} "
            
        return combined_text.strip()
        
    except Exception as e:
        print(f"[오류] 네이버 블로그 수집 중 에러 발생: {e}")
        return ""

def analyze_pain_points(context: str) -> str:
    """
    수집된 텍스트를 Gemini API에 전달하여 소비자의 페인 포인트(단점)와 소싱 팁을 분석합니다.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[오류] GEMINI_API_KEY가 .env 파일에 없습니다.")
        return "API 키가 필요합니다."
    
    if not context:
        return "분석할 텍스트 데이터가 부족합니다."

    # Gemini 설정
    genai.configure(api_key=api_key)
    # 최신 고성능 모델인 gemini-2.0-flash 사용 (사용자 요청에 따라 최신 모델 적용)
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = f"""
다음 텍스트는 특정 상품에 대한 실제 소비자들의 리뷰야. 이 내용을 분석해서 소비자들이 공통적으로 느끼는 가장 치명적인 단점 또는 불편한 점 3가지를 뽑아줘. 
각 단점은 1줄로 요약하고, 1688에서 대체품을 소싱할 때 어떤 점을 개선한 제품을 찾아야 할지 소싱 팁도 1줄씩 덧붙여줘.

[분석 대상 리뷰 데이터]
{context}
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini 분석 중 오류 발생: {e}"

if __name__ == "__main__":
    # 환경 변수 로드
    load_dotenv()
    
    # 1. 테스트 키워드 설정
    test_keyword = "초음파 가습기 단점"
    print(f"🔍 분석 키워드: {test_keyword}")
    print("-" * 50)
    
    # 2. 리뷰 수집
    raw_text = get_blog_reviews(test_keyword)
    print(f"📊 수집된 원본 데이터 길이: {len(raw_text)}자")
    
    # 3. Gemini 분석 실행
    print("🤖 Gemini가 소비자의 Pain Point를 분석 중입니다...")
    analysis_result = analyze_pain_points(raw_text)
    
    # 4. 결과 출력
    print("-" * 50)
    print("🚀 [소비자 불만 분석 및 1688 소싱 전략]")
    print(analysis_result)
    print("-" * 50)
