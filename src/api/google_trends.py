import pandas as pd
from pytrends.request import TrendReq
from typing import Dict, Any, Optional

class GoogleTrendAPI:
    """
    비공식 라이브러리 pytrends를 활용하여 구글 트렌드 데이터를 수집하는 클래스입니다.
    키워드 기반 관심도 변화 및 관련 검색어를 추출합니다.
    """
    
    def __init__(self) -> None:
        # hl: Host Language (한국어), tz: Timezone offset (540 = GMT+9 한국)
        self.pytrends = TrendReq(hl='ko-KR', tz=540)
        
    def get_google_trends(self, keyword: str) -> Dict[str, Any]:
        """
        주어진 키워드에 대해 구글 트렌드 데이터(주간 관심도, 급상승 검색어)를 수집합니다.
        
        Args:
            keyword: 분석할 검색어 문자열
            
        Returns:
            결과를 포함한 딕셔너리 (interest_over_time, related_queries)
        """
        results = {
            "interest_over_time": None,
            "related_queries": None
        }
        
        try:
            # 1. 페이로드 빌드 (timeframe='today 3-m': 최근 3개월, geo='KR': 한국 지역 제한)
            # 주간 데이터를 위해 기간을 조정하거나 집계할 수 있으나, 기본 3개월은 일별 데이터를 반환합니다.
            self.pytrends.build_payload(kw_list=[keyword], timeframe='today 3-m', geo='KR')
            
            # 2. 시간 흐름에 따른 관심도 수집 (Interest Over Time)
            iot_df = self.pytrends.interest_over_time()
            
            if not iot_df.empty:
                # 3개월 데이터는 일 단위로 나오므로, 요청한 '주간' 흐름을 위해 주차별로 리샘플링(평균)합니다.
                # W: 일요일 기준 주간 집계
                weekly_df = iot_df.resample('W').mean()
                results["interest_over_time"] = weekly_df
            
            # 3. 관련 검색어 수집 (Related Queries)
            related_data = self.pytrends.related_queries()
            if keyword in related_data:
                # 'rising': 급상승 검색어, 'top': 인기 검색어
                results["related_queries"] = related_data[keyword].get('rising')
                
            return results
        
        except Exception as e:
            print(f"❌ [Google Trends API Error] {e}")
            return results

if __name__ == "__main__":
    # 간단한 테스트 코드
    api = GoogleTrendAPI()
    test_keyword = '차박 텐트'
    print(f"\n🔍 '{test_keyword}' 구글 트렌드 분석 시작 (최근 3개월 주간 데이터)\n")
    
    data = api.get_google_trends(test_keyword)
    
    # 1. 관심도 변화 출력
    if data["interest_over_time"] is not None:
        print("[📊 관심도 변화 (주간 평균)]")
        # 보기 좋게 출력하기 위해 컬럼 포맷팅
        df = data["interest_over_time"]
        for date, row in df.iterrows():
            # 관심도 값은 0~100 사이의 점수임
            score = int(row[test_keyword])
            print(f" - {date.strftime('%Y-%m-%d')}: {score}점")
    else:
        print("관심도 데이터를 가져오지 못했습니다.")
        
    print("\n" + "="*40 + "\n")
    
    # 2. 관련 급상승 검색어 출력
    if data["related_queries"] is not None and not data["related_queries"].empty:
        print("[🚀 관련 급상승 검색어 TOP 10]")
        rising_df = data["related_queries"].head(10)
        for idx, row in rising_df.iterrows():
            print(f" {idx+1}. {row['query']} (+{row['value']}%)")
    else:
        print("급상승 검색어 결과가 없거나 가져오지 못했습니다.")
