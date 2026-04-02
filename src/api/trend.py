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

    # 클래스를 초기화하며 검색 트렌드 수집을 위한 엔드포인트와 기본 설정을 완료함
    # 부모 클래스의 통신 레이어(base.py)와 초기화 정보를 공유함 (상속 관계 연계)
    def __init__(self) -> None:
        super().__init__()
        self.trend_url: str = "https://openapi.naver.com/v1/datalab/search"  # 네이버 검색 트렌드 조회 API 주소 변수

    # 특정 키워드의 검색 트렌드를 일정 기간 동안 수집하여 Pandas DataFrame으로 반환합니다.
    # 수집된 시계열 결과물은 이후 'MomentumScorer' 클래스의 가속도 연산 기초 데이터가 됨
    def get_daily_trend(self, keyword: str, days: int = 30) -> Optional[pd.DataFrame]:
        # 데이터를 조회할 시작 날짜와 종료 날짜를 동적으로 계산함 (날짜 계산 유틸리티 연계)
        end_date_str: str = datetime.now().strftime("%Y-%m-%d")  # 시스템의 현재 날짜를 문자열로 변환한 변수
        start_date_str: str = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")  # 오늘로부터 지정된 일수만큼 과거 날짜를 계산한 변수
        
        # 네이버 데이터랩 API의 명세서(Spec)에 맞춰 요청 본문을 JSON 형식으로 구성함 (파칭 및 전송 연계)
        request_body: Dict[str, Any] = {
            "startDate": start_date_str,  # 트렌드 분석의 시작 시점
            "endDate": end_date_str,  # 트렌드 분석의 마지막 시점
            "timeUnit": "date",  # 결과 데이터의 시간 간격 (일간 단위)
            "keywordGroups": [
                {
                    "groupName": keyword,  # 분석 결과에 표시될 키워드 그룹의 대표 명칭 변수
                    "keywords": [keyword]  # 그룹에 포함되어 통합 분석될 실제 검색어 리스트
                }
            ]
        }

        # 공통 클라이언트(base.py)의 요청 메서드를 통해 데이터를 POST 방식으로 조회함 (네트워크 모듈 연계)
        response = self._send_request("POST", self.trend_url, data=json.dumps(request_body))
        
        if response:
            try:
                # 수신된 JSON 응답에서 분석에 필요한 데이터 부분만 추출함 (데이터 추출 연계)
                result_json: Dict[str, Any] = response.json()  # API 응답 원본 전체를 딕셔너리로 파싱한 결과
                
                # 응답 구조 내의 시계열 데이터 리스트를 가져옴 (데이터 가공 연계)
                items: List[Dict[str, Any]] = result_json['results'][0]['data']  # 일자별 검색량 수치를 담고 있는 리스트 변수
                
                # 가공된 리스트 데이터를 Pandas의 DataFrame 객체로 변환하여 분석 편의성을 확보함
                df: pd.DataFrame = pd.DataFrame(items)  # 이후의 수치 분석과 필터링 작업의 중심이 되는 데이터프레임 객체
                
                # 컬럼명을 의미에 맞는 이름으로 변경 (date: 날짜, ratio: 상대적 검색량)
                df.columns = ['period', 'ratio']  # 데이터프레임의 원본 컬럼명을 유의미한 이름으로 치환한 리스트
                
                # 'period' 컬럼을 문자열에서 실제 datetime 객체형으로 변환함 (시계열 데이터 연산 연계)
                df['period'] = pd.to_datetime(df['period'])  # 날짜 형식의 문자열을 시계열 연산이 가능한 타입으로 변경
                
                return df

            except (KeyError, IndexError, ValueError) as e:
                # API 응답 구조가 변경되었거나 예기치 못한 데이터 형식이 왔을 때의 예외 처리 (에러 로깅 연계)
                print(f"데이터 정제 중 오류 발생: {e}")
                return None
        return None

if __name__ == "__main__":
    # TrendAPI 모듈의 기능을 개별적으로 검증하기 위한 테스트용 실행 코드 (기능 테스트 연계)
    trend_tester = TrendAPI()  # 트렌드 수집 핸들러 클래스 인스턴스화
    
    # '캠핑'이라는 검색어를 대상으로 지난 30일간의 트렌드 조회를 시도함
    keyword_example: str = "캠핑"  # 트렌드 확인을 위한 테스트 검색어 변수
    df_result = trend_tester.get_daily_trend(keyword_example, days=30)  # 서버로부터 결과를 받아 데이터프레임 형태로 유지
    
    if df_result is not None:
        # 정상적으로 데이터를 받아왔을 경우 상위 샘플 5줄을 출력함
        print(f"\n--- '{keyword_example}' 키워드 검색 트렌드 (최근 30일) ---")
        print(df_result.head())
    else:
        # 데이터 수집이나 통신에 실패했을 경우 안내 메시지 출력
        print("데이터를 가져오는 데 실패했습니다.")
