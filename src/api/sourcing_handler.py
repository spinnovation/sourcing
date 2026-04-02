import os
import requests
import time
import json
from decimal import Decimal
from typing import Dict, Any, List
from dotenv import load_dotenv

class SourcingHandler:
    """
    [1688 Image Sourcing Engine]
    네이버 쇼핑 상품의 이미지(URL)를 RapidAPI '1688 Product Search'로 역추적하여
    중국 현지 제조사 도매가(CNY)를 추출, 한국 원화로 환산하고 실 마진율을 계산합니다.
    """
    def __init__(self):
        load_dotenv(".env")
        # RapidAPI 인증키
        self.api_key = os.getenv("RAPIDAPI_KEY", "")
        # 1688-datahub API 호스트
        self.api_host = os.getenv("RAPIDAPI_HOST", "1688-datahub.p.rapidapi.com")
        self.url = f"https://{self.api_host}/item_search_image_2"
        
        # 위안화(CNY) 환율 (기본값 190원, 실시간 업데이트 지원)
        self.exchange_rate = 190.0
        self.update_exchange_rate()
        
    def update_exchange_rate(self):
        """실시간 환율 API(Frankfurter)를 통해 최신 위안화 환율을 가져옵니다."""
        try:
            # Frankfurter API (CNY -> KRW)
            response = requests.get("https://api.frankfurter.app/latest?from=CNY&to=KRW", timeout=5)
            if response.status_code == 200:
                data = response.json()
                rate = data.get("rates", {}).get("KRW")
                if rate:
                    self.exchange_rate = float(rate)
                    print(f"💰 [실시간 환율] 1 CNY = {self.exchange_rate} KRW (업데이트 완료)")
        except Exception as e:
            print(f"⚠️ [환율 업데이트 실패] 기본값({self.exchange_rate}원)을 사용합니다. 사유: {e}")

    def search_1688_by_image(self, img_url: str) -> Dict[str, Any]:
        """
        주어진 이미지 URL을 RapidAPI로 전송하여 1688 도매 상품 결과를 반환합니다.
        (네이버 이미지 서버의 간헐적 차단을 대비해 205 에러 발생 시 자동 재시도)
        """
        if not self.api_key:
            return {
                "product_id": "N/A",
                "price_cny": 0.0,
                "price_krw": 0,
                "detail_link": "N/A",
                "thumbnail_url": ""
            }

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host,
            "Content-Type": "application/json"
        }
        
        # 시도해볼 이미지 URL 포맷 리스트 (1. 원본 https, 2. 성공로그에서 포착된 // 상대경로)
        url_candidates = [img_url, img_url.replace("https:", "")]
        
        for attempt, target_url in enumerate(url_candidates):
            querystring = {"imgUrl": target_url, "page": "1", "sort": "default"}
            
            try:
                print(f"📡 [1688 API] 시도 {attempt+1}... 요청 주소: {target_url}")
                response = requests.get(self.url, headers=headers, params=querystring, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    status_obj = data.get("result", {}).get("status", {})
                    biz_code = status_obj.get("code")
                    
                    if biz_code == 200:
                        print(f"✅ [1688 API] 데이터 획득 성공")
                        result_list = data.get("result", {}).get("resultList", [])
                        
                        if result_list and len(result_list) > 0:
                            # 🎯 [최고 정확도 로직] 루프 없이 가장 상위(0번) 아이템을 바로 채택합니다. 
                            top_node = result_list[0].get("item", {})
                            
                            # 가격 추출 (sku -> def -> price 우선순위)
                            sku_def = top_node.get("sku", {}).get("def", {})
                            raw_price = sku_def.get("price") or top_node.get("price") or top_node.get("promotion_price", 0)
                            
                            # 최종 가격 CNY (float)
                            final_p = float(raw_price) if raw_price else 0.0

                            # 링크 추출 및 보정
                            raw_url = top_node.get("itemUrl", "")
                            if raw_url.startswith("//"): raw_url = "https:" + raw_url
                            
                            # 썸네일 추출 및 보정
                            thumb = top_node.get("image", "")
                            if thumb.startswith("//"): thumb = "https:" + thumb

                            return {
                                "product_id": str(top_node.get("itemId", "N/A")),
                                "price_cny": final_p,
                                "price_krw": int(final_p * self.exchange_rate),
                                "detail_link": raw_url,
                                "thumbnail_url": thumb
                            }
                        else:
                            print(f"⚠️ [1688 API] 결과 리스트가 비어있습니다. (데이터: {data})")
                            return {"error": "결과 없음"}
                    
                    # 만약 code가 205(no results)라면 한 번 더 시도 (다음 URL 포맷으로)
                    if biz_code == 205:
                        print(f"⚠️ [1688 API] 205 에러 (결과 없음): 다음 포맷으로 재시도합니다...")
                        time.sleep(0.5)
                        continue
                        
                else:
                    print(f"❌ [1688 API] HTTP 오류 {response.status_code}")
                    
            except Exception as e:
                print(f"🚨 [1688 API] 통신 예외: {str(e)}")
                
        return {"error": "반복 시도 실패 (이미지 서버 차단 가능성)"}

    def calculate_margin(self, naver_price: int, price_cny: float, shipping_fee: int = 7000) -> Dict[str, Any]:
        """
        1688 원가와 네이버 판매가를 비교하여 순 마진(Margin) 구조를 파악합니다.
        (배송비/통관비 디폴트 7,000원 가정)
        """
        cost_krw = int(price_cny * self.exchange_rate)
        total_cost = cost_krw + shipping_fee
        margin = naver_price - total_cost
        margin_pct = (margin / naver_price * 100) if naver_price > 0 else 0
        
        return {
            "cost_krw": cost_krw,
            "total_cost": total_cost,
            "margin_krw": margin,
            "margin_pct": round(margin_pct, 1)
        }

    def _generate_mock_result(self, img_url: str) -> Dict[str, Any]:
        """가공 데이터를 반환하지 않고 N/A 템플릿을 반환합니다."""
        return {
            "product_id": "N/A",
            "price_cny": 0.0,
            "price_krw": 0,
            "detail_link": "N/A",
            "thumbnail_url": ""
        }
