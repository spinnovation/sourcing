import os
import requests
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
from src.analysis.margin_calculator import calculate_customs_and_margin

class SourcingHandler:
    def __init__(self):
        load_dotenv(".env")
        self.api_key = os.getenv("RAPIDAPI_KEY", "")
        self.api_host = os.getenv("RAPIDAPI_HOST", "1688-datahub.p.rapidapi.com")
        self.exchange_rate = 190.0
        self.update_exchange_rate()

    def update_exchange_rate(self):
        """Update CNY to KRW exchange rate using Frankfurter API."""
        try:
            response = requests.get("https://api.frankfurter.app/latest?from=CNY&to=KRW", timeout=5)
            if response.status_code == 200:
                data = response.json()
                rate = data.get("rates", {}).get("KRW")
                if rate:
                    self.exchange_rate = float(rate)
        except Exception as e:
            print(f"Exchange rate error: {e}")

    def search_1688_by_image(self, img_url: str) -> Dict[str, Any]:
        """RapidAPI disabled. Returns placeholder for manual input."""
        print(f"🚫 [1688 API] RapidAPI disabled. Please use manual clipboard (Ctrl+V).")
        return {
            "product_id": "MANUAL",
            "price_cny": 0.0,
            "price_krw": 0,
            "detail_link": "N/A",
            "thumbnail_url": img_url
        }

    def calculate_margin(self, naver_price: int, price_cny: float, shipping_fee: int = 7000, quantity: int = 1) -> Dict[str, Any]:
        """실무 통관 비중을 고려한 상세 마진 계산 (수량 반영)"""
        # 총 물품 대금 (위안)
        total_cny = price_cny * quantity
        
        calc_res = calculate_customs_and_margin(
            price_cny=total_cny, 
            exchange_rate=self.exchange_rate, 
            shipping_fee_krw=shipping_fee, 
            is_b2b=False
        )
        
        # 총 매출 (원화)
        total_revenue = naver_price * quantity
        total_cost = calc_res["total_sourcing_cost"]
        
        margin = total_revenue - total_cost
        margin_pct = (margin / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            "unit_cost_krw": int(total_cost / quantity) if quantity > 0 else 0,
            "total_cost": total_cost,
            "margin_krw": margin,
            "margin_pct": round(margin_pct, 1),
            "customs_detail": calc_res
        }



    def _generate_mock_result(self, img_url: str) -> Dict[str, Any]:
        return self.search_1688_by_image(img_url)
