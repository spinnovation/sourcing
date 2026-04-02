# 개발 계획서: 상품 트렌드 분석 시스템 (Product Trend Research)

이 문서는 `plan.md`의 내용을 바탕으로 구축한 AI 에이전트용 단계별 개발 로드맵입니다.

## 1단계: 기반 환경 및 API 인프라 구축
핵심 환경을 설정하고 안정적인 API 통신 레이어를 구현합니다.

### 1.1 <u>프로젝트 환경 초기화</u>
- [x] <u>디렉토리 구조 생성:</u>
  - `data/raw/`: <u>원본 API 응답 저장 공간.</u>
  - `data/processed/`: <u>정제 및 스코어링 완료된 데이터 저장 공간.</u>
  - `src/`: <u>소스 코드 (`api/`, `analysis/`, `utils/` 등).</u>
  - `tests/`: <u>단위 테스트 코드.</u>
- [x] <u>`requirements.txt` 정의 (requests, pandas, python-dotenv, numpy).</u>
- [x] <u>`.env` 템플릿 생성 (Naver API Client ID, Secret 등).</u>

### 1.2 <u>공통 API 클라이언트 (OOP 기반)</u>
- [x] <u>`src/api/base.py`: 모든 API의 기본이 되는 `NaverApiClient` 클래스 구현.</u>
  - <u>공통 에러 핸들링 (Rate Limit 초과, 타임아웃, JSON 파싱 오류).</u>
  - <u>API 인증 헤더 자동 생성 및 호출 로그 기록.</u>

### 1.3 <u>네이버 쇼핑 API 모듈</u>
- [x] <u>`src/api/shopping.py`: `ShoppingAPI` 클래스 구현.</u>
  - <u>`search_products(keyword, display=50)`: 키워드 기반 상품 목록 수집.</u>
  - <u>데이터 모델: 상품명, 가격, 카테고리(1~4단계), 판매처, 리뷰 수 등을 포함하는 스키마 정의.</u>

### 1.4 <u>네이버 데이터랩 (Trend) API 모듈</u>
- [x] <u>`src/api/trend.py`: `TrendAPI` 클래스 구현.</u>
  - <u>`get_daily_trend(keyword, start_date, end_date)`: 일별 검색 트렌드 데이터 수집.</u>
  - <u>데이터 모델: 시계열 분석을 위한 Pandas DataFrame 구조화.</u>

## 2단계: 데이터 수집 및 오케스트레이션
여러 API를 결합하여 데이터를 체계적으로 수집하고 관리합니다.

### 2.1 <u>통합 수집기 (Collector)</u>
- [x] <u>`src/orchestrator.py`: `DataOrchestrator` 클래스 구현.</u>
  - <u>특정 키워드에 대해 쇼핑 정보와 트렌드 데이터를 동시에 수집하고 매칭하는 로직.</u>
  - <u>`data/raw/{keyword}_{timestamp}.json` 형식으로 원본 데이터 아카이빙.</u>

### 2.2 <u>데이터 정제 및 영속화</u>
- [x] <u>`src/utils/storage.py`: CSV/JSON 저장 및 로직 구현.</u>
  - <u>상품명 HTML 태그 제거 및 텍스트 전처리 유틸리티 포함.</u>

## 3단계: 트렌드 분석 및 모멘텀 스코어링
모은 데이터를 분석하여 미래 유망 상품을 발굴하는 핵심 로직입니다.

### 3.1 <u>모멘텀 스코어러 (Momentum Scorer)</u>
- [x] <u>`src/analysis/scorer.py`: `MomentumScorer` 클래스 구현.</u>
  - <u>**속도 (Velocity)**: 최근 7일 평균 검색량 / 이전 30일 평균 검색량.</u>
  - <u>**가속도 (Acceleration)**: 속도의 변화율 (Momentum).</u>
  - <u>**종합 점수**: `(검색 볼륨 가중치 * v) + (성장성 가중치 * a)`.</u>

### 3.2 <u>검색 결과 필터링 및 GUI 통합</u>
- [x] <u>"급성장 유망주" (가속도 높음, 볼륨 중간 수준) 추출 로직 완료.</u>
- [x] <u>**PyQt6 기반 데스크탑 UI 완성**: 1~50위 랭킹 및 다중 정렬(조회수, 판매량, 리뷰 등) 지원.</u>

## 4단계: 향후 확장 (벡터 엔진 및 매칭)
더 고도화된 리서치를 위한 인텔리전스 단계입니다.

- [ ] 형태소 분석을 통한 키워드 정교화.
- [ ] OpenAI Embedding 연동을 통한 상품 간 유사도 계산.
- [ ] 구글 트렌드 등 멀티 플랫폼 데이터 확장.

---

## 작업 지침
- **모듈화**: 각 기능은 독립된 파일과 클래스로 관리하며 `src/` 하단에 배치합니다.
- **예외 처리**: 모든 네트워크 요청 및 데이터 파싱 시 예외 처리를 철저히 합니다.
- **문서화**: 모든 함수와 클래스에는 Type Hint와 설명을 포함합니다.
