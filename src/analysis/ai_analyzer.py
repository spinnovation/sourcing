import os
import warnings

# Gemini 라이브러리 관련 불필요한 안내 경고문을 터미널에서 차단함 (사용자 경험 개선)
warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from dotenv import load_dotenv
from typing import List, Tuple

# 환경 변수 로드 (.env 파일에서 API 키 정보를 읽어옴)
load_dotenv()

class AIAnalyzer:
    """
    Gemini 모델을 활용하여 수집된 상품 데이터를 인문학적으로 분석하고 
    현재 시장의 트렌드 인사이트를 도출하는 분석 전문가 클래스입니다.
    """

    # Gemini 모델 인프라를 초기화하고 분석용 프롬프트를 설정함 (AI 인프라 연계)
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # API 키 누락 시 앱 중단을 방지하기 위해 경고 로그를 남기고 빈 인스턴스로 처리
            print("[WARNING] GEMINI_API_KEY is not found in .env file.")
            self.model = None
            return

        genai.configure(api_key=api_key)
        # 최신 고성능 모델인 Gemini 2.0 Flash를 선택하여 분석 속도와 정확도를 극대화함
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    # 50개의 상품 제목 리스트를 입력받아 시장의 [경향성 조사] 보고서와 [10대 핵심 키워드], [5대 상위 개념]을 생성합니다.
    def analyze_trends(self, titles: List[str], keyword: str) -> Tuple[str, List[str], List[str]]:
        
        titles_text = "\n".join([f"- {title}" for title in titles[:50]])
        
        # AI에게 분석 기준, 페르소나, 그리고 강제 출력 형식을 부여하는 전문 프롬프트 구성 (분석 고도화)
        prompt = f"""
        당신은 글로벌 톱 이커머스 컨설턴트이자 데이터 분석 전문가입니다.
        현재 네이버 쇼핑에서 핵심 트렌드 키워드 '{keyword}'로 상위 노출된 최상위 제품 리스트가 있습니다.
        
        [분석 대상 상품 리스트]
        {titles_text}
        
        시장의 최신 트렌드를 파악하고, 상위 노출 상품들이 공통적으로 공략하는 소비자의 니즈를 분석하여 다음 3가지를 도출하십시오.
        아래는 '{keyword}' 키워드로 검색된 네이버 쇼핑 상위 50개 상품의 제목들입니다.
        이 제목들을 심층 분석하여 다음 관점에서 '경향성 조사' 보고서를 작성해 주세요.

        1. 주요 브랜드 및 인기 모델 패턴 (시장의 지배적 브랜드)
        2. 소비자 소구 포인트 (사용자들이 가장 매력적으로 느끼는 특성, 재질, 태그)
        3. 전체적인 시장 트렌드 한 줄 평 (한 줄로 시장의 현재 분위기를 진단)

        [전달된 상품 제목 리스트]
        {", ".join(titles)}

        **반드시 지켜야 할 출력 형식:**
        [경향성 조사 - {keyword}]
        (여기에 1, 2, 3번에 대한 상세한 분석 내용을 자유롭게 작성하세요.)
        
        [핵심 트렌드 키워드 10선]
        키워드1, 키워드2, 키워드3, 키워드4, 키워드5, 키워드6, 키워드7, 키워드8, 키워드9, 키워드10
        (↑ 위의 '핵심 트렌드 키워드 10선' 문구 아래에, 이 시장의 직접적이고 핵심적인 경향성을 함축하는 명사형 단어 10개만 정확히 쉼표로 구분하여 출력해 주세요. 
        **[매우중요] 특정 '브랜드명'이나 '제조사명'은 절대로 포함시키지 마세요.** 오직 제품의 속성, 기능, 디자인, 소재, 용도, 감성과 관련된 일반명사만 추출하세요.)

        [크로스 카테고리 확장을 위한 최상위 추상 개념 5선]
        개념1, 개념2, 개념3, 개념4, 개념5
        (↑ 추출된 10개의 구체적인 속성 단어들을 모두 아우르는, 완전히 제품군을 탈피한 더 높고 거시적인 '최상위 추상 명사(개념)' 5개만 쉼표로 구분하여 출력해주세요. 예시: '실용성', '가성비', '아웃도어', '미니멀리즘', '모빌리티', '효율성')
        """

        try:
            # Gemini 모델 호출 및 분석 텍스트 생성 (실시간 추론 연계)
            response = self.model.generate_content(prompt)
            full_text = response.text
            
            report_body = full_text
            trend_keywords = keyword  # 분리 실패 시 안전망
            cross_concepts = keyword
            
            # 파싱: [핵심 트렌드 키워드 10선]과 [최상위 상위 개념 5선]을 프로그래밍적으로 분리
            marker_10 = "[핵심 트렌드 키워드 10선]"
            marker_5 = "[크로스 카테고리 확장을 위한 최상위 추상 개념 5선]"
            
            if marker_10 in full_text and marker_5 in full_text:
                parts = full_text.split(marker_10)
                report_body = parts[0].strip()
                
                sub_parts = parts[1].split(marker_5)
                # 앞부분은 10대 키워드, 뒷부분은 5대 체계 개념
                trend_keywords = sub_parts[0].replace("\n", "").strip()
                cross_concepts = sub_parts[1].replace("\n", "").strip()
                
            return report_body, trend_keywords, cross_concepts
        except Exception as e:
            # 호출 실패 시 오류 메시지를 튜플 포맷에 맞춰 반환
            return f"Gemini 분석 중 오류가 발생했습니다: {str(e)}", keyword, keyword
