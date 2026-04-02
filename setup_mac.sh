#!/bin/bash

echo "=================================================="
echo "🚀 Product Research Pro - Mac 환경 자동 설치 스크립트"
echo "=================================================="
echo ""

# 1. 설치 경로를 현재 디렉토리로 이동 (.command 파일 더블 클릭 실행 시의 경로 문제 방지)
cd "$(dirname "$0")"

# 2. 가상환경(venv) 생성 및 활성화
echo "📦 1/4: Python 가상환경(venv)을 생성합니다..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 가상환경 생성 완료"
else
    echo "✅ 가상환경이 이미 존재합니다."
fi

echo "🔄 가상환경 활성화 중..."
source venv/bin/activate

# 3. Pip 업그레이드
echo "📦 2/4: pip 패키지 매니저를 최신 버전으로 업데이트합니다..."
pip install --upgrade pip

# 4. 필수 의존성 패키지 설치
echo "📦 3/4: 필수 라이브러리 및 구성 요소를 설치합니다 (PyQt6, AI, 데이터 분석 등)..."
# GUI 및 기본 의존성
pip install PyQt6 requests python-dotenv

# 데이터 처리 및 시각화
pip install pandas matplotlib openpyxl numpy

# AI 및 시맨틱 렌더링 엔진
pip install google-generativeai sentence-transformers

# 스텔스 크롤링 관련 (1688 등)
pip install playwright playwright-stealth

# 5. Playwright 브라우저 에뮬레이터 설치
echo "📦 4/4: 웹 데이터 크롤링을 위한 Playwright 브라우저 엔진을 설치합니다..."
playwright install chromium

echo ""
echo "=================================================="
echo "🎉 모든 설치가 성공적으로 완료되었습니다!"
echo "=================================================="
echo ""
echo "[프로그램 실행 방법]"
echo "터미널에서 아래 두 줄의 명령어를 순서대로 입력하세요:"
echo "1) source venv/bin/activate"
echo "2) python3 src/gui/dashboard_app.py"
echo ""
echo "이제 이 터미널 창을 닫으셔도 됩니다."
