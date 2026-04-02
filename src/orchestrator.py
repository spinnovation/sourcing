import os
import sys
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional

# 하위 모듈 임포트를 위해 현재 경로를 시스템 패스에 추가 (모듈 연계)
sys.path.append(os.path.join(os.path.dirname(__file__)))

# 각 도메인별 담당 클래스 임포트 (기능 분담 연계)
try:
    from api.shopping import ShoppingAPI
    from api.trend import TrendAPI
    from analysis.scorer import MomentumScorer
    from utils.storage import DataStorage
except ImportError:
    # 실행 위치에 따른 임포트 예외 처리 (패키지 구조 유연성 확보)
    from src.api.shopping import ShoppingAPI
    from src.api.trend import TrendAPI
    from src.analysis.scorer import MomentumScorer
    from src.utils.storage import DataStorage

class DataOrchestrator:
    """
    여러 API와 저장소 모듈을 조율하여 프로젝트 전체의 데이터 수집 프로세스를 관리하는 클래스입니다.
    키워드 하나로 쇼핑 검색 정보와 검색량 트렌드를 동시에 확보하도록 설계되었습니다.
    'plan-agent.md'의 Phase 2 '통합 수집기'를 담당합니다.
    """

    # 수집에 필요한 모든 서브 모듈(API, Storage)의 인스턴스를 초기화함
    # 이후 run_research 메서드에서 각 인스턴스 기능을 유기적으로 결합함 (컴포넌트 연합 연계)
    def __init__(self) -> None:
        self.shopping_api: ShoppingAPI = ShoppingAPI()  # 상품 상세 정보를 가져오는 쇼핑 API 객체 변수
        self.trend_api: TrendAPI = TrendAPI()  # 시계열 검색 추이를 가져오는 트렌드 API 객체 변수
        self.scorer: MomentumScorer = MomentumScorer()  # 트렌드 가속도를 분석하는 스코어링 엔진 변수
        self.storage: DataStorage = DataStorage()  # 수집 결과를 파일로 저장하는 스토리지 객체 변수

    # 키워드를 입력받아 쇼핑과 트렌드 데이터를 일괄 수집하고 파일 시스템에 영속화합니다.
    # 이 메서드를 통해 확보된 데이터는 Phase 3의 'MomentumScorer' 연산의 입력값이 됨
    def run_research(self, keyword: str) -> bool:
        # 데이터의 선후 관계를 식별하기 위한 고유 타임스탬프 문자열을 생성함 (로그 관리 연계)
        timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")  # 현재 시각을 담고 있는 식별용 변수
        print(f"\n[INFO] --- '{keyword}' 리서치 수집 프로세스 시작 ({timestamp}) ---")

        # 1. 네이버 쇼핑 데이터 조회 (검색 결과 수집 연계)
        shopping_raw: Optional[Dict[str, Any]] = self.shopping_api.search_products(keyword)
        if shopping_raw:
            # 원본 응답 JSON 데이터를 그대로 저장하여 보존함 (데이터 아카이빙 연계)
            shop_file: str = f"shop_{keyword}_{timestamp}.json"  # 저장용 JSON 파일명 변수
            self.storage.save_as_json(shopping_raw, shop_file)  # 스토리지 유틸리티로 파일 쓰기 수행
            print(f"[SUCCESS] 쇼핑 데이터 저장 완료: {shop_file}")
        
        # 2. 네이버 데이터랩 트렌드 데이터 조회 (시계열 추이 확인 연계)
        trend_df: Optional[pd.DataFrame] = self.trend_api.get_daily_trend(keyword)
        if trend_df is not None:
            # 트렌드 시계열 데이터프레임을 CSV 형식으로 변환하여 정제 폴더에 저장함 (데이터 영속화 연계)
            trend_file: str = f"trend_{keyword}_{timestamp}.csv"  # 저장용 CSV 파일명 변수
            self.storage.save_as_csv(trend_df, trend_file)  # 스토리지 유틸리티로 데이터 저장
            print(f"[SUCCESS] 트렌드 데이터 저장 완료: {trend_file}")

        # 모든 수집 프로세스가 정상적으로 마무리되었는지 판별함 (프로세스 제어 연계)
        if shopping_raw and trend_df is not None:
            print(f"[COMPLETE] '{keyword}' 데이터 수집을 마쳤습니다. 분석을 시작합니다.")
            
            # 3. 데이터 분석 및 스코어링 실행 (MomentumScorer 연계)
            analysis_result: Dict[str, float] = self.scorer.calculate_scores(trend_df)  # 분석 결과 지표를 담은 변수
            
            # 4. 최종 리서치 리포트 출력 (결과 시각화 연계)
            self._display_report(keyword, shopping_raw, analysis_result)
            
            return True
        else:
            # 하나라도 누락되면 리서치 실패로 간주하고 알림 (에러 핸들링 연계)
            print(f"[FAILED] '{keyword}' 데이터 수집 중 일부 모듈에서 응답을 받지 못했습니다.")
            return False

    # 분석된 수치를 바탕으로 트렌드 등급을 판별하고 종합 보고서를 콘솔에 출력합니다.
    # 이 보고서는 사용자에게 최종적으로 제공되는 리서치 핵심 요약 결과물입니다.
    def _display_report(self, keyword: str, shopping_data: Dict[str, Any], scores: Dict[str, float]) -> None:
        final_score: float = scores['final_score']  # 분석 엔진에서 산출한 최종 가치 점수 변수
        
        # 점수에 따른 트렌드 레벨 판별 (비즈니스 인사이트 도출 연계)
        if final_score >= 1.5:
            trend_level: str = "🚀 [라이징 스타] 현재 급격히 떠오르는 유망 상품군입니다!"  # 가장 높은 추천 등급 변수
        elif final_score >= 1.0:
            trend_level: str = "✅ [스테디셀러] 안정적인 수요를 유지 중인 활발한 시장입니다."  # 안정적인 시장 등급 변수
        else:
            trend_level: str = "📉 [하락/정체] 현재 수요가 감소하거나 정체된 구간입니다."  # 낮은 가치 등급 변수

        print("\n" + "="*60)
        print(f"📊 [{keyword}] 통합 리서치 분석 보고서")
        print("="*60)
        print(f"1. 트렌드 진단: {trend_level}")
        print(f"   - 가속도(Momentum): {scores['acceleration']}")
        print(f"   - 활성지수(Velocity): {scores['velocity']}")
        print(f"   - 최종 트렌드 점수: {final_score}")
        print("-" * 60)
        
        # 쇼핑 데이터 중 주요 상품 요약 (최상위 3개 추출 연계)
        items = shopping_data.get('items', [])[:3]  # 상위 3개의 상품 리스트 변수
        print(f"2. 주요 연관 상품 현황 (상위 {len(items)}개)")
        for idx, item in enumerate(items, 1):
            title: str = item['title'].replace("<b>", "").replace("</b>", "")  # 태그 제거된 깔끔한 상품명 변수
            price: str = format(int(item['lprice']), ',')  # 콤마가 찍힌 가격 문자열 변수
            print(f"   [{idx}] {title}")
            print(f"       최저가: {price}원 | 카테고리: {item['category3']} > {item['category4']}")
        
        print("="*60)
        print(f"상세 원본 데이터는 data/raw/ 폴더를 확인해 주세요.\n")

if __name__ == "__main__":
    # DataOrchestrator의 전체 워크플로우를 테스트함 (종합 통합 테스트 연계)
    research_manager = DataOrchestrator()  # 통합 관리자 서비스 객체 생성
    
    # '캠핑용품'이라는 포괄적인 검색어를 타겟으로 통합 리서치 및 수집 명령 실행
    target_keyword: str = "캠핑용품"  # 분석하고자 하는 타겟 검색어 변수
    research_manager.run_research(target_keyword)  # 실제 비즈니스 로직 수행
