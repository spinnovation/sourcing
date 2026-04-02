import json
import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional

class DataStorage:
    """
    데이터를 파일 시스템(JSON, CSV)에 저장하고 관리하는 유틸리티 클래스입니다.
    수집된 원본 데이터와 가공된 분석 데이터를 영구적으로 보존하는 역할을 하며,
    'plan-agent.md'의 2.2 섹션인 '데이터 정제 및 영속화'를 담당합니다.
    """

    # 저장소 클래스를 초기화하며 필요한 데이터 디렉토리를 설정함
    # 초기 실행 시 폴더 존재 여부를 체크하여 데이터 유실 실패를 방지함 (환경 설정 연계)
    def __init__(self) -> None:
        self.raw_dir: str = "data/raw"  # API 응답 원본을 보관할 디렉토리 경로 변수
        self.processed_dir: str = "data/processed"  # 정제 및 분석이 완료된 평면 데이터를 저장할 경로 변수
        self._ensure_directories()  # 필요한 폴더 구조가 있는지 확인하고 생성함

    # 데이터 저장에 필요한 폴더 구조가 물리적으로 존재하는지 확인하고 생성함
    # 이 메서드는 초기화 시 호출되어 이후 모든 파일 쓰기 작업의 안정성을 보장함 (파일 시스템 가용성 연계)
    def _ensure_directories(self) -> None:
        # 순회하며 폴더 생성 (이미 존재할 경우 생성하지 않음)
        for directory in [self.raw_dir, self.processed_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)  # 실제 OS 폴더 생성 명령 수행 (OS 모듈 연계)
                print(f"디렉토리 생성 완료: {directory}")

    # API 결과와 같은 파이썬 객체를 JSON 형식으로 파일에 저장함
    # 'DataOrchestrator'에서 수집한 원본 정보를 아카이빙할 때 주 목적으로 사용됨 (데이터 보존 연계)
    def save_as_json(self, data: Any, filename: str) -> str:
        # 루트 경로와 파일명을 결합하여 절대적인 저장 경로를 만듦
        file_path: str = os.path.join(self.raw_dir, filename)  # 생성될 JSON 파일의 전체 경로 변수
        
        with open(file_path, 'w', encoding='utf-8') as f:
            # 한글 깨짐 방지 및 가독성을 위해 indent를 적용하여 저장함
            json.dump(data, f, ensure_ascii=False, indent=4)  # 파일 쓰기 작업 수행
            
        return file_path

    # Pandas DataFrame 객체를 CSV 형식으로 저장하여 분석 도구와의 호환성을 높임
    # 트렌드 수치나 스코어링이 완료된 리스틀르 엑셀 등에서 열어볼 수 있도록 지원함 (데이터 활용 연계)
    def save_as_csv(self, df: pd.DataFrame, filename: str) -> str:
        # 데이터 처리 완료 폴더 내에 결과 파일을 생성할 경로 구성
        file_path: str = os.path.join(self.processed_dir, filename)  # 생성될 CSV 파일의 전체 경로 변수
        
        # 인덱스를 제외하고 엑셀에서 바로 읽을 수 있는 인코딩(utf-8-sig)으로 저장함
        df.to_csv(file_path, index=False, encoding='utf-8-sig')  # 데이터프레임 내보내기 수행
        
        return file_path

if __name__ == "__main__":
    # 데이터 저장소 모듈의 작동 확인을 위한 테스트 코드 (단위 기능 검증 연계)
    storage = DataStorage()  # 스토리지 서비스 인스턴스화
    
    # 더미 데이터를 활용해 JSON 저장 기능 테스트
    dummy_data: Dict[str, str] = {"status": "test", "message": "hello world"}  # 테스트용 딕셔너리 변수
    json_path = storage.save_as_json(dummy_data, "test_file.json")  # JSON 저장 시도
    print(f"JSON 저장 테스트 완료: {json_path}")
    
    # 샘플 데이터프레임을 활용해 CSV 저장 기능 테스트
    sample_df: pd.DataFrame = pd.DataFrame([{"id": 1, "name": "test_item"}])  # 테스트용 데이터프레임 객체 변수
    csv_path = storage.save_as_csv(sample_df, "test_file.csv")  # CSV 저장 시도
    print(f"CSV 저장 테스트 완료: {csv_path}")
