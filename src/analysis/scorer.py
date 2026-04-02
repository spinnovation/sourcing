import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class MomentumScorer:
    """
    시계열 검색 트렌드 데이터로부터 성장 속도와 가속도를 계산하여 
    분석 대상 상품이나 키워드의 유망성 점수를 산출하는 엔진 클래스입니다.
    'plan-agent.md'의 Phase 3 '모멘텀 스코어러' 로직을 담당합니다.
    """

    # 분석 엔진을 초기화하며 점수 산출에 필요한 가중치를 설정함
    # 이 가중치는 비즈니스 전략에 따라 '현재 인기'와 '미래 성장성' 비중을 조절함 (가중치 전략 연계)
    def __init__(self) -> None:
        self.volume_weight: float = 0.4  # 현재의 절대적인 검색 규모(속도)가 차지하는 비중 변수
        self.growth_weight: float = 0.6  # 검색량의 증가폭(가속도)이 차지하는 비중 변수 (성장성 중심 설정)

    # 데이터프레임 형태의 시계열 트렌드 데이터 및 쇼핑 포화도(total_products)를 융합 분석하여 유망성을 판독합니다.
    def calculate_scores(self, df: pd.DataFrame, total_products: int = 0) -> Dict[str, Any]:
        # 분석을 진행하기 위한 데이터 최소 길이를 검사함 (데이터 무결성 연계)
        # 최소 14일 이상의 시계열이 있어야 전후 비교가 가능하므로 필터링함 (에러 핸들링 연계)
        if df is None or df.empty or len(df) < 14:
            print("[WARN] 분석을 위한 데이터가 부족합니다 (최소 14일 이상 필요).")
            return {
                "velocity": 0.0, "acceleration": 0.0, "final_score": 0.0,
                "competition_index": 0.0, "entry_barrier_score": 0.0, "is_blue_ocean": False
            }

        # 1. 속도(Velocity) 산출: 최근 7일 평균 검색량 / 전체 데이터 평균 검색량 (상대적 활성도 연계)
        # 현재 시장에서 이 키워드가 얼마나 뜨거운지를 나타내는 상대 지표를 산출함
        recent_7d_avg: float = df['ratio'].iloc[-7:].mean()  # 가장 최근의 일주일 검색 수치 평균 변수
        overall_avg: float = df['ratio'].mean()  # 분석 대상으로 잡은 전체 샘플 기간의 평균 수치 변수
        
        # 전체 평균 대비 최근 수치가 얼마나 높은지 비율로 환산함
        velocity: float = recent_7d_avg / overall_avg if overall_avg > 0 else 0.0  # 현재의 인기 속도 변수

        # 2. 가속도(Acceleration) 산출: (최근 7일 평균 - 이전 7일 평균) / 이전 7일 평균 (성장 기여도 연계)
        # 속도가 단순히 빠른지, 혹은 점점 더 빨라지고 있는지를 판별하여 '미래 유망성'을 점수화함
        prev_7d_avg: float = df['ratio'].iloc[-14:-7].mean()  # 최근 7일 바로 전 일주일의 검색 수치 평균 변수
        
        # 전주 대비 이번 주 검색량이 몇 퍼센트 증가했는지 계산함
        acceleration: float = (recent_7d_avg - prev_7d_avg) / prev_7d_avg if prev_7d_avg > 0 else 0.0  # 성장의 변화량 변수

        # 3. 종합 점수(Final Score) 도출: 기설정된 가중치를 적용하여 단일 평가 수치 생성
        final_score: float = (velocity * self.volume_weight) + (acceleration * self.growth_weight)  # 최종 트렌드 스코어 변수

        # 4. 경쟁 강도 및 블루오션(Blue Ocean) 파악 (신규 분석 지표 연계)
        entry_barrier_score = 0.0
        competition_index = 0.0
        is_blue_ocean = False
        
        if total_products > 0 and recent_7d_avg > 0:
            # 진입 장벽 점수 = (최근 검색량 / 전체 유통 상품 수) * 가독성 스케일업 상수
            entry_barrier_score = (recent_7d_avg / total_products) * 100000
            
            # 경쟁 강도 = 전체 유통 상품 수 / 최근 검색량 (낮을수록 블루오션)
            competition_index = total_products / recent_7d_avg
            
            # 검색 가속도가 폭발적(0.15 이상)인데, 경쟁 강도 자체는 아직 낮은 유니콘 시장을 판별!
            if acceleration > 0.15 and entry_barrier_score > 0.5:
                is_blue_ocean = True

        # 결과값을 딕셔너리에 담아 반올림 처리함 (엑셀 및 대시보드 출력 연계)
        return {
            "velocity": float(round(velocity, 4)), 
            "acceleration": float(round(acceleration, 4)), 
            "final_score": float(round(final_score, 4)),
            "competition_index": float(round(competition_index, 2)),
            "entry_barrier_score": float(round(entry_barrier_score, 4)),
            "is_blue_ocean": is_blue_ocean
        }

if __name__ == "__main__":
    # MomentumScorer의 수치 분석 로직을 검증하기 위한 가상 시나리오 테스트 (수치 안정성 연계)
    scorer = MomentumScorer()  # 분석 엔진 객체 생성
    
    # 가상의 상승 추세 데이터 생성 (데이터 정제 모듈 결과물 모방)
    test_trend: pd.DataFrame = pd.DataFrame({
        'period': pd.date_range(start='2024-01-01', periods=15),  # 15일치 가상의 시각 데이터 변수
        'ratio': [10, 11, 12, 13, 14, 15, 16, 20, 25, 30, 40, 50, 65, 80, 100]  # 가속도가 붙는 검색량 수치 변수
    })
    
    # 모션 분석 및 스코어 런칭
    scores = scorer.calculate_scores(test_trend)  # 점수 산출 수행
    
    print("\n--- 가상 모멘텀 분석 테스트 결과 ---")
    for key, value in scores.items():
        print(f"{key}: {value}")
