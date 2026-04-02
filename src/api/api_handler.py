import os
import json
import time
from typing import Dict, Any, List
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import google.generativeai as genai
from dotenv import load_dotenv

class APIHandler:
    """
    [Vision AI 스크래핑 엔진]
    단순한 텍스트 수집을 넘어, 상품 URL로 진입해 특정 XPATH의 디스플레이를 캡처한 뒤,
    Gemini 2.0 Flash(Vision) 모델의 눈으로 리뷰, 평점, 디자인 요약을 뜯어와 JSON으로 반환합니다.
    """
    def __init__(self):
        load_dotenv(".env")
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            # 이미지 동시 처리에 압도적 성능을 내는 최신 flash 모델 지정
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            print("🚨 [WARN] GEMINI_API_KEY가 없습니다. Vision 연산이 불가능합니다.")
            self.model = None

    def analyze_single_product_vision(self, url: str) -> Dict[str, str]:
        if not self.model:
            return {"reviews": "N/A", "rating": "N/A", "design": "API Key 누락"}
            
        print(f"📸 [Vision 엔진 기동] 단일 상품 페이지 분석을 위해 다이렉트 침투: {url}")
        
        with sync_playwright() as p:
            # 💡 [Headless 해제]: 화면에 직접 렌더링되도록 하여 리다이렉션 게이트를 뚫고 
            # 봇 차단을 우회합니다.
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            page.set_default_timeout(15000) 
            
            # 사용자 지정 최신 XPATH 타겟 (카탈로그 서머리)
            xpath_target = '//*[@id="catalog_summary_info"]/div/div[3]'

            try:
                # 리다이렉트를 확실히 돌파하기 위해 wait_until을 강하게 설정
                page.goto(url, wait_until='load')
                time.sleep(3.0) 
                
                try:
                    element = page.wait_for_selector(f'xpath={xpath_target}', timeout=8000, state="attached")
                    element.scroll_into_view_if_needed()
                    time.sleep(1.0)
                    
                    # [핵심] 캡처를 없애고 요소 내의 "텍스트"만 가볍게 빼옵니다 (NLP 연산용)
                    extracted_text = element.inner_text()
                    
                except PlaywrightTimeoutError:
                    browser.close()
                    return {"reviews": "N/A", "rating": "N/A", "design": "영역 텍스트 못찾음 (카탈로그 아님)"}
                    
                prompt = f"""
                당신은 이커머스 상세 페이지의 구조화된 텍스트 데이터를 분석하는 AI입니다.
                아래는 네이버 가격비교 '카탈로그 속성' 영역에서 방금 긁어온 원시(Raw) 텍스트입니다.
                
                [수집된 실제 텍스트]
                {extracted_text}
                
                위 내용을 바탕으로 아래 3가지 항목을 정확히 추출하되, "오직 순수한 JSON 포맷"으로만 출력해 주십시오. (마크다운 백틱 제외)
                
                1. "reviews": 텍스트에 포함된 '리뷰 수' (예: "3,124", 없으면 "0")
                2. "rating": 텍스트에 포함된 '평점' (예: "4.8", 없으면 "0.0")
                3. "design": 관측된 상품의 특성, 재질, 형태적인 분류 1줄 요약 (디자인 관점)
                
                {{
                  "reviews": "...",
                  "rating": "...",
                  "design": "..."
                }}
                """
                
                # 가벼운 텍스트 파싱을 생성 모델에 넘김
                response = self.model.generate_content(prompt)
                
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text.replace("```json", "").replace("```", "").strip()
                elif text.startswith("```"):
                    text = text.replace("```", "").strip()
                    
                parsed_json = json.loads(text)
                browser.close()
                return parsed_json
                
            except Exception as e:
                print(f"Vision Capture Error: {str(e)}")
                browser.close()
                return {"reviews": "Err", "rating": "Err", "design": f"분석 오류: {str(e)[:15]}"}
