import sys
import os

# 현재 디렉토리를 경로에 추가하여 src 모듈을 임포트할 수 있게 함
sys.path.append(os.getcwd())

from src.api.google_trends import GoogleTrendAPI

def test_google_trends(keyword='차박 텐트'):
    """
    사용자가 요청한 구글 트렌드 관심도 변화 및 관련 급상승 검색어를 
    가져와서 콘솔에 출력하는 테스트 코드입니다.
    """
    print(f"\n🚀 구글 트렌드 분석 테스트를 시작합니다. (키워드: {keyword})\n")
    
    api = GoogleTrendAPI()
    data = api.get_google_trends(keyword)
    
    # 1. 주간 데이터 변화 출력
    print("[📈 관심도 변화 (최근 3개월 주간 데이터)]")
    if data["interest_over_time"] is not None:
        # 데이터프레임에서 날짜와 관심도 점수를 보기 좋게 출력
        df = data["interest_over_time"]
        for date, row in df.iterrows():
            # 관심도 결과는 0~100 사이의 상대적 비율 점수(score)입니다.
            score = int(row[keyword])
            print(f" - {date.strftime('%Y-%m-%d')}: {score}점")
    else:
        print("관심도 데이터를 가져오지 못했습니다. (접속 제한 혹은 키워드 부족)")
        
    print("\n" + "="*50 + "\n")
    
    # 2. 관련 급상승 검색어 출력
    print("[🔥 관련 급상승 검색어 (Rising Queries)]")
    if data["related_queries"] is not None and not data["related_queries"].empty:
        # 상위 10개만 리스트업
        rising_df = data["related_queries"].head(10)
        for i, row in enumerate(rising_df.itertuples(), 1):
            # 'query'는 검색어, 'value'는 상승률(breakout 등 정보 포함 가능)
            print(f" {i:2d}. {row.query} (상승률: {row.value}%)")
    else:
        print("관심 키워드와 연관된 급상승 검색어 데이터가 없습니다.")

if __name__ == "__main__":
    test_google_trends()
