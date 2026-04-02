import json
from typing import Dict, Any, Optional
try:
    # 패키지 구조 하에서 실행될 때와 단독 실행될 때를 모두 고려한 임포트 방식 (모듈 연계)
    from .base import NaverApiClient
except ImportError:
    from base import NaverApiClient

class ShoppingAPI(NaverApiClient):
    """
    네이버 쇼핑 API를 통해 실시간 상품 정보를 검색하고 가공하는 클래스로,
    이 클래스의 결과물은 'DataOrchestrator'에 전달되어 DB 또는 파일로 영속화됩니다.
    'plan-agent.md'의 Phase 1 'Shopping Data Module'에 해당합니다.
    """

    # 클래스를 초기화하며 쇼핑 검색 관련 엔드포인트 URL을 설정함
    # 부모 클래스의 통신 기반(base.py)을 그대로 상속받아 인증 작업을 간소화함 (상속 관계 연계)
    def __init__(self) -> None:
        super().__init__()
        self.search_url: str = "https://openapi.naver.com/v1/search/shop.json"  # 네이버 쇼핑 조회 API 주소 변수

    # 주어진 키워드(keyword)에 대하여 쇼핑 검색 결과를 JSON 객체로 반환합니다.
    # 수집된 쇼핑 데이터는 이후 'MomentumScorer' 연산 시 상품별 가중치 평가의 기본이 됨
    def search_products(self, keyword: str, display: int = 50) -> Optional[Dict[str, Any]]:
        # API 요청 파라미터를 구성함 (검색어, 검색 건수, 정렬 방식 등 포함 가능)
        query_params: Dict[str, Any] = {
            "query": keyword,  # 사용자가 분석 대상으로 지정한 검색 키워드 문자열
            "display": display  # 한 번에 결과로 반환받을 상품의 개수 (최대 100개 지정 가능)
        }

        # 부모 클래스의 _send_request 메서드를 통해 네트워크 요청을 보냄 (통용 엔드포인트 연계)
        response = self._send_request("GET", self.search_url, params=query_params)
        
        if response:
            try:
                # 결과값이 존재할 경우 API 성공 응답을 파이썬 딕셔너리 형태로 변환함 (데이터 파싱 연계)
                return response.json()
            except ValueError as e:
                # 응답을 JSON으로 변환하는 과정에서 문제 발생 시 에러 코드를 로깅함 (에러 핸들링 연계)
                print(f"JSON 데이터 파싱 오류: {e}")
                return None
        return None

    def get_shopping_insight(self, category_id: str) -> Dict[str, Any]:
        """쇼핑 인사이트 카테고리 기세 데이터를 가져옵니다 (사용자 제공 로직)"""
        url = "https://openapi.naver.com/v1/datalab/shopping/categories"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "Content-Type": "application/json"
        }
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        data = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "month",
            "category": [{"name": "분석 카테고리", "param": [category_id]}]
        }
        try:
            import requests, json
            response = requests.post(url, headers=headers, data=json.dumps(data))
            return response.json()
        except Exception: return {}

    # --- 데이터랩 4대장 API 통합 구현 영역 ---

    def get_category_trend(self, category_id: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """1. 분야별 트렌드 API (/v1/datalab/shopping/categories)"""
        url = "https://openapi.naver.com/v1/datalab/shopping/categories"
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        body = {
            "startDate": start_date, "endDate": end_date, "timeUnit": "date",
            "category": [{"name": "분야", "param": [category_id]}]
        }
        return self._post_datalab(url, body)

    def get_keyword_demographics(self, category_id: str, keyword: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """2. 키워드 연령 트렌드 API (/v1/datalab/shopping/category/keyword/age)"""
        url = "https://openapi.naver.com/v1/datalab/shopping/category/keyword/age"
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        body = {
            "startDate": start_date, "endDate": end_date, "timeUnit": "month",
            "category": category_id, "keyword": keyword
        }
        return self._post_datalab(url, body)

    def get_device_trend(self, category_id: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """3. 기기별 트렌드 API (/v1/datalab/shopping/category/device)"""
        url = "https://openapi.naver.com/v1/datalab/shopping/category/device"
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        body = {
            "startDate": start_date, "endDate": end_date, "timeUnit": "date",
            "category": category_id
        }
        return self._post_datalab(url, body)

    def get_search_trend(self, keyword_list: list, days: int = 30) -> Optional[Dict[str, Any]]:
        """4. 통합 검색어 트렌드 API (/v1/datalab/search) - 일반 검색량 변화"""
        url = "https://openapi.naver.com/v1/datalab/search"
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # 키워드 리스트를 네이버 규격(keywordGroups)으로 변환 (최대 5개)
        if isinstance(keyword_list, str): keyword_list = [keyword_list]
        groups = [{"groupName": k, "keywords": [k]} for k in keyword_list[:5]]
        
        body = {
            "startDate": start_date, "endDate": end_date, "timeUnit": "date",
            "keywordGroups": groups
        }
        return self._post_datalab(url, body)

    def get_category_top_keywords(self, category_id: str) -> Optional[Dict[str, Any]]:
        """5. 분야별 인기 검색어 TOP 500 API (/v1/datalab/shopping/category/keywords)"""
        url = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"
        from datetime import datetime, timedelta
        # 전날 혹은 그저께 기준 인기 검색어 추출 (집계 지연 대비)
        target_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        
        body = {
            "startDate": target_date, "endDate": target_date, "timeUnit": "date",
            "category": category_id
        }
        return self._post_datalab(url, body)

    def _post_datalab(self, url: str, body: dict) -> Optional[Dict[str, Any]]:
        """데이터랩 API 공통 POST 호출 및 에러 핸들링 유틸리티"""
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "Content-Type": "application/json"
        }
        try:
            import requests, json
            response = requests.post(url, headers=headers, data=json.dumps(body))
            if response.status_code == 200:
                return response.json()
            else:
                print(f"🚨 [DataLab API Error] {url}\n상태 코드: {response.status_code}\n응답 내용: {response.text}")
                return None
        except Exception as e:
            print(f"❌ [DataLab Network Error] {e}")
            return None

    def get_category_demographics(self, category_id: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """분야별 연령 분포 조회 (Keyword 없이 Category ID만 사용)"""
        url = "https://openapi.naver.com/v1/datalab/shopping/category/age"
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        body = {
            "startDate": start_date, "endDate": end_date, "timeUnit": "month",
            "category": category_id
        }
        return self._post_datalab(url, body)

    def get_category_gender_demographics(self, category_id: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """성별 분포 조회 (앱 호환성 유지)"""
        url = "https://openapi.naver.com/v1/datalab/shopping/category/gender"
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        body = {
            "startDate": start_date, "endDate": end_date, "timeUnit": "month",
            "category": category_id
        }
        return self._post_datalab(url, body)

    def get_keyword_trend(self, keyword: str, days: int = 30) -> list:
        """네이버 데이터랩 검색어트렌드에서 특정 키워드의 최근 검색 추이를 가져옵니다."""
        url = "https://openapi.naver.com/v1/datalab/search"
        
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d") 
        
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "date",
            "keywordGroups": [
                {"groupName": keyword, "keywords": [keyword]}
            ],
            "device": "",
            "ages": [],
            "gender": ""
        }
        
        response = self._send_request("POST", url, json=body)
        if response:
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    trend_data = results[0].get("data", [])[-5:]
                    print(f"📈 [DataLab Trend] '{keyword}' 추이 수집 성공")
                    return [f"{d['period']}: {int(d['ratio'])}%" for d in trend_data]
            else:
                print(f"❌ [DataLab Trend Error] HTTP {response.status_code}")
                print(f"📄 응답 내용: {response.text}")
        return []

if __name__ == "__main__":
    # --- 네이버 데이터랩 API 기능 테스트 로직 ---
    api = ShoppingAPI()
    test_cat_id = "50000000"  # [패션의류] 카테고리 ID

    print(f"\n🚀 [Test] 분야별 트렌드 API 호출 중... (ID: {test_cat_id})")
    trend_result = api.get_category_trend(test_cat_id)
    print("\n[계산 결과: 분야별 트렌드 지수]")
    print(json.dumps(trend_result, indent=4, ensure_ascii=False))

    print(f"\n🚀 [Test] 분야별 인구통계(연령) API 호출 중... (ID: {test_cat_id})")
    demo_result = api.get_category_demographics(test_cat_id)
    print("\n[계산 결과: 분야별 연령 통계]")
    print(json.dumps(demo_result, indent=4, ensure_ascii=False))
