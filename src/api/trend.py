import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
try:
    # 패키지 구조 하에서 실행될 때와 단독 실행될 때를 모두 고려한 임포트 방식 (모듈 연계)
    from .base import NaverApiClient
except ImportError:
    from base import NaverApiClient

class TrendAPI(NaverApiClient):
    """
    네이버 데이터랩 통합검색어 트렌드 API를 통해 시계열 검색량 데이터를 추출하는 클래스입니다.
    이 데이터는 'MomentumScorer' 연산의 핵심인 검색량 변화율 및 가속도 계산에 필수적입니다.
    """

    def __init__(self) -> None:
        super().__init__()
        self.trend_url: str = "https://openapi.naver.com/v1/datalab/search"

    def get_daily_trend(self, keyword: str, days: int = 30) -> Optional[pd.DataFrame]:
        end_date_str: str = datetime.now().strftime("%Y-%m-%d")
        start_date_str: str = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        request_body: Dict[str, Any] = {
            "startDate": start_date_str,
            "endDate": end_date_str,
            "timeUnit": "date",
            "keywordGroups": [
                {
                    "groupName": keyword,
                    "keywords": [keyword]
                }
            ]
        }

        response = self._send_request("POST", self.trend_url, data=json.dumps(request_body))
        
        if response:
            try:
                # 1. JSON 응답 파싱
                result_json = response.json()
                
                # 2. 결과 데이터 구조 검증 및 추출
                results = result_json.get('results', [])
                if not results or 'data' not in results[0] or not results[0]['data']:
                    return None
                
                items = results[0]['data']
                df = pd.DataFrame(items)
                
                # 3. 컬럼 개수 및 데이터 유무 확인 (Length mismatch 방지)
                if df.empty or len(df.columns) < 2:
                    return None
                    
                # 컬럼명을 'period'와 'ratio'로 통일
                df.columns = ['period', 'ratio']
                
                # 4. 시계열 데이터 타입 변환
                df['period'] = pd.to_datetime(df['period'])
                
                return df

            except Exception as e:
                # 모든 예외 상황에 대해 안전하게 None을 반환하여 메인 프로세스 유지
                print(f"⚠️ [TrendAPI 데이터 정제 오류] {e}")
                return None
        return None

if __name__ == "__main__":
    trend_tester = TrendAPI()
    keyword_example: str = "캠핑"
    df_result = trend_tester.get_daily_trend(keyword_example, days=30)
    
    if df_result is not None:
        print(f"\n--- '{keyword_example}' 유효 데이터 발견 ---")
        print(df_result.head())
    else:
        print("유효한 트렌드 데이터가 없거나 로드에 실패했습니다.")
