import time
import json
import urllib.parse
from curl_cffi import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

class NaverWebScraper:
    """
    네이버 쇼핑 웹페이지를 직접 스크래핑하여 일반 오픈 API가 절대로 주지 않는 은닉 데이터
    (리뷰 수, 찜하기 수, 상품 등록일 등 리얼 마켓 지표)를 추적 추출하는 전문 크롤링 엔진입니다.
    """
    def __init__(self):
        # 파이썬 통신을 완전히 버리고 C언어 기반의 진짜 구글 크롬 브라우저 통신(TLS Fingerprint)을 복제하는 최상위 무기
        self.headers = {
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://shopping.naver.com/"
        }

    def search_products(self, keyword: str, display: int = 100) -> Dict[str, Any]:
        """
        주어진 키워드로 쇼핑 검색 결과를 스크래핑합니다.
        (기존 시스템 구조를 깨지 않기 위해, ShoppingAPI와 똑같은 Dict[str, Any] 인터페이스를 그대로 유지합니다)
        """
        items = []
        encoded_kw = urllib.parse.quote(keyword)
        
        # 1페이지당 최대 80개 데이터이므로, 100개 로딩을 위해 딱 2페이지만 조용히 순환합니다.
        for page in range(1, 3):
            url = f"https://search.shopping.naver.com/search/all?query={encoded_kw}&pagingIndex={page}&pagingSize=80"
            
            try:
                # 무자비한 공격으로 오해받지 않기 위해 2번째 페이지로 넘어가기 전 1초간 인간처럼 쉬어줍니다. (Human-like delay)
                if page > 1:
                    time.sleep(1.0)
                    
                # impersonate 옵션을 통해 완벽한 크롬(Chrome110) 브라우저 행세를 하여 WAF 우회 (418, 405 절대 차단)
                response = requests.get(url, headers=self.headers, impersonate="chrome110", timeout=15)
                
                if response.status_code != 200:
                    print(f"[Scraper] {response.status_code} Error: 네이버 방화벽 오류 또는 타임아웃 발생 (키워드: {keyword})")
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                # [해커의 시선]: 네이버 쇼핑은 Next.js 기반(React)이므로, "__NEXT_DATA__"라는 JSON 덩어리에 모든 진짜 데이터가 담겨 있습니다!
                next_data_script = soup.find('script', id='__NEXT_DATA__')
                
                if not next_data_script:
                    print(f"[Scraper] 아차! 네이버 구조가 변경되었거나 캡챠에 걸렸습니다. (키워드: {keyword})")
                    break
                    
                data = json.loads(next_data_script.string)
                
                # 깊은 숲 속, 은밀하게 숨겨진 제품 리스트 트리(Tree)에 무혈입성
                product_list = data.get('props', {}).get('pageProps', {}).get('initialState', {}).get('products', {}).get('list', [])
                
                for p in product_list:
                    item_data = p.get('item', {})
                    if not item_data:
                        continue
                        
                    # 필수 기본 정보 (기존 API 포맷 100% 호환)
                    title = item_data.get('productTitle', '')
                    price = item_data.get('price', 0)
                    link = item_data.get('adUrl', item_data.get('mallProductUrl', ''))
                    
                    # 💡 [핵심 비즈니스 지표 4대장] 리얼 데이터 무단 발췌
                    review_count = item_data.get('reviewCount', 0)
                    keep_cnt = item_data.get('keepCnt', 0) # 찜하기(관심도)
                    score_info = item_data.get('scoreInfo', 0.0) # 실제 구매자 평점
                    open_date = item_data.get('openDate', '') # 상품 최초 등록일 (예: 20230501)
                    
                    items.append({
                        'title': title,
                        'lprice': str(price),
                        'link': link,
                        'reviews': int(review_count) if review_count else 0,
                        'likes': int(keep_cnt) if keep_cnt else 0,
                        'rating': float(score_info) if score_info else 0.0,
                        'open_date': str(open_date)
                    })
                    
                    if len(items) >= display:
                        break
                        
            except Exception as e:
                print(f"[Scraper Error] 보안 장벽이나 통신 오류가 발생했습니다: {str(e)}")
                break
                
            if len(items) >= display:
                break
                
        return {'items': items, 'total': len(items)}
