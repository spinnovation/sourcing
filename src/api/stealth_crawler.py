import time
import json
import urllib.parse
import random
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright
import playwright_stealth

class StealthCrawler:
    """
    [Playwright-Stealth Mobile Engine]
    방어가 삼엄한 데스크탑(PC) 웹을 버리고, 보안 검열이 느슨한 모바일 네이버 쇼핑(m.shopping)을 타격합니다.
    랜덤 모바일 UA와 사람 수준의 Random Delay, Stealth 옵션으로 네이버 WAF를 기만합니다.
    """
    def __init__(self):
        # 최신 모바일 브라우저 User-Agent 리스트 (랜덤 순환을 통한 봇 식별 무력화)
        self.mobile_uas = [
            "Mozilla/5.0 (Linux; Android 13; SM-S918N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 12; SM-F936N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1"
        ]
        
        # 봇 차단 회피를 위한 후퇴(Backoff) 지연 시간 세팅
        self.block_delay = 5.0

    def search_products(self, keyword: str, display: int = 100) -> Dict[str, Any]:
        items = []
        total_products = 0
        encoded_kw = urllib.parse.quote(keyword)
        
        with sync_playwright() as p:
            # 헤드리스(모니터 숨김)로 리소스 절약
            browser = p.chromium.launch(headless=True)
            
            # 랜덤 UA 주입 및 모바일 Viewport 해상도 강제 지정
            context = p.chromium.launch_persistent_context(
                user_data_dir="",
                headless=True,
                user_agent=random.choice(self.mobile_uas),
                viewport={'width': 390, 'height': 844},
                is_mobile=True,
                has_touch=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            page = context.new_page()
            
            # Playwright Stealth 구동 (webdriver=true 등의 모든 봇 표식을 지워버림)
            playwright_stealth.stealth.Stealth().apply_stealth_sync(page)
            
            try:
                for page_idx in range(1, 4):
                    # 모바일 최적화 타격 루트 (m.shopping.naver.com)
                    url = f"https://m.shopping.naver.com/search/all?query={encoded_kw}&pagingIndex={page_idx}&pagingSize=40"
                    
                    response = page.goto(url, wait_until="networkidle")
                    
                    # 403 Forbidden(차단) 발생 시, 백오프(Backoff) 대응 에러 핸들링
                    if response and response.status == 403:
                        print(f"🚨 [Stealth Alert] 403 차단 발동! 봇 감지 레이더에 노출되었습니다. 즉시 크롤링을 중단하고 {self.block_delay}초 지연 패시브 발동합니다.")
                        # 다음 공격을 위해 봇 타임아웃 패널티 확장
                        self.block_delay += 3.0 
                        break
                    
                    # 진짜 인간이 페이지를 보고 고민하는 것처럼 1~3초간 무작위(Random) 대기 스킬 발동
                    time.sleep(random.uniform(1.2, 3.5))
                    
                    # 네이버 모바일 쇼핑 역시 내부적으론 JSON "__NEXT_DATA__"에 모든 팩트가 담겨있음
                    next_script = page.locator('script#__NEXT_DATA__').first
                    if not next_script:
                        print(f"[Stealth Error] 모바일 페이지 렌더링 실패 또는 캡챠 발동. (키워드: {keyword})")
                        break
                        
                    data_json = next_script.inner_text()
                    data = json.loads(data_json)
                    
                    # 모바일 파싱 구조 타격
                    initial_state = data.get('props', {}).get('pageProps', {}).get('initialState', {})
                    products_obj = initial_state.get('products', {})
                    product_list = products_obj.get('list', [])
                    
                    if page_idx == 1:
                        total_products = products_obj.get('total', 0)
                        
                    for p in product_list:
                        item_data = p.get('item', {})
                        if not item_data: continue
                        
                        title = item_data.get('productTitle', '')
                        price = item_data.get('price', 0)
                        link = item_data.get('adUrl', item_data.get('mallProductUrl', ''))
                        
                        review_count = item_data.get('reviewCount', 0)
                        keep_cnt = item_data.get('keepCnt', 0)
                        score_info = item_data.get('scoreInfo', 0.0)
                        open_date = item_data.get('openDate', '')
                        
                        items.append({
                            'title': title,
                            'lprice': str(price),
                            'link': link,
                            'reviews': int(review_count) if review_count else 0,
                            'likes': int(keep_cnt) if keep_cnt else 0,
                            'rating': float(score_info) if score_info else 0.0,
                            'open_date': str(open_date)
                        })
                        
                        if len(items) >= display: break
                        
                    if len(items) >= display or not product_list: break
                    
            except Exception as e:
                 print(f"☠️ [Stealth Critical] 우회 작전 중 치명적 오류 발생: {str(e)}")
            finally:
                context.close()
                browser.close()
                
        return {'items': items, 'total': total_products}
