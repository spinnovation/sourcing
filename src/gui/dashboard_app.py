import sys
import os
import random
import urllib.parse
import datetime
import webbrowser
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# .env 환경변수 자동 로드 (API 키 등)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
except ImportError:
    pass  # python-dotenv 미설치 시 무시 (시스템 환경변수 사용)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QComboBox, QTableWidget, QTableWidgetItem, 
    QLabel, QTextEdit, QHeaderView, QFrame, QTabWidget, QListWidget, 
    QMessageBox, QFileDialog, QDialog, QFormLayout, QDoubleSpinBox, QSpinBox,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QIcon

# 시각화 차트 연동을 위한 Matplotlib 위젯 (그래프 렌더링 연계)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Matplotlib 한글 폰트 설정 (맑은 고딕 적용)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 프로젝트 루트 경로 연동
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

try:
    from src.api.shopping import ShoppingAPI
    from src.api.trend import TrendAPI
    from src.api.sourcing_handler import SourcingHandler
    from src.api.naver_ad import NaverAdAPI
    from src.analysis.scorer import MomentumScorer
    from src.analysis.ai_analyzer import AIAnalyzer
    from src.analysis.vector_search import VectorSearch
    from src.analysis.pain_point_analyzer import get_blog_reviews, analyze_pain_points
except ImportError:
    from api.shopping import ShoppingAPI
    from api.trend import TrendAPI
    from api.sourcing_handler import SourcingHandler
    from api.naver_ad import NaverAdAPI
    from analysis.scorer import MomentumScorer
    from analysis.ai_analyzer import AIAnalyzer
    from analysis.vector_search import VectorSearch
    from analysis.pain_point_analyzer import get_blog_reviews, analyze_pain_points

class NumericItem(QTableWidgetItem):
    """
    QTableWidget 정렬 시 1, 10, 2 와 같은 텍스트(알파벳)순 정렬을 무시하고, 
    저장된 실제 숫자 크기(1, 2, 10 순서)를 기준으로 수학적인 등락을 완벽히 계산해주는 커스텀 코어 아이템입니다.
    """
    def __lt__(self, other):
        try:
            val1 = float(self.data(Qt.ItemDataRole.UserRole))
            val2 = float(other.data(Qt.ItemDataRole.UserRole))
            # N/A(-1.0)는 항상 가장 뒤로 정렬되도록 처리
            if val1 < 0: return False
            if val2 < 0: return True
            return val1 < val2
        except (ValueError, TypeError):
            return super().__lt__(other)

class MarginCalculatorDialog(QDialog):
    """실시간 환율 및 다양한 비용을 반영하는 순마진 정밀 계산기"""
    def __init__(self, parent=None, naver_price=0, cny_price=0.0, exchange_rate=190.0):
        super().__init__(parent)
        self.setWindowTitle("💰 순마진 정밀 시뮬레이터")
        self.setFixedWidth(400)
        self.exchange_rate = exchange_rate
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # 입력 필드 설정
        self.qty = QSpinBox()
        self.qty.setRange(1, 10000); self.qty.setValue(1)
        
        self.cny_price = QDoubleSpinBox()
        self.cny_price.setRange(0, 1000000); self.cny_price.setValue(cny_price)
        
        self.shipping = QSpinBox()
        self.shipping.setRange(0, 1000000); self.shipping.setValue(7000)
        
        self.customs = QSpinBox()
        self.customs.setRange(0, 1000000); self.customs.setValue(0)
        
        self.sales_price = QSpinBox()
        self.sales_price.setRange(0, 10000000); self.sales_price.setValue(naver_price)
        
        form.addRow("📦 구매 수량:", self.qty)
        form.addRow("💴 1688 단가 (CNY):", self.cny_price)
        form.addRow("🚚 총 국내배송비 (KRW):", self.shipping)
        form.addRow("🛂 통관/기타 비용 (KRW):", self.customs)
        form.addRow("🛍️ 네이버 판매가 (KRW):", self.sales_price)
        
        layout.addLayout(form)
        
        # 결과 대시보드
        self.result_label = QLabel("\n[ 계 산 결 과 ]\n개당 구매비용: 0원\n최종 순마진: 0원")
        self.result_label.setStyleSheet("background: #2a2a2a; color: #00ff00; padding: 15px; border-radius: 5px; font-weight: bold;")
        layout.addWidget(self.result_label)
        
        # 실시간 자동 계산 연결
        for widget in [self.qty, self.cny_price, self.shipping, self.customs, self.sales_price]:
            widget.valueChanged.connect(self.calculate)
            
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.calculate()

    def calculate(self):
        Q = self.qty.value()
        C = self.cny_price.value()
        S = self.shipping.value()
        T = self.customs.value()
        P = self.sales_price.value()
        
        # ((단가 * 환율 * 수량) + 배송비 + 통관비) / 수량 = 개당 원가
        total_buy_krw = (C * self.exchange_rate * Q) + S + T
        landed_cost_per_unit = int(total_buy_krw / Q)
        
        # 마진 (네이버 판매가 - 개당 원가)
        net_margin_per_unit = P - landed_cost_per_unit
        total_net_margin = net_margin_per_unit * Q
        
        text = (
            f"📈 적용 환율: {self.exchange_rate:.2f}원\n"
            f"💵 개당 구매원가: {landed_cost_per_unit:,}원\n"
            f"✅ 개당 순마진: {net_margin_per_unit:,}원\n"
            f"💰 총 예상수익: {total_net_margin:,}원"
        )
        self.result_label.setText(text)

class TrendChartCanvas(FigureCanvas):
    """
    네이버 데이터랩의 30일 시계열 데이터를 시각화하는 Matplotlib 캔버스 클래스입니다.
    데이터의 흐름을 시각적으로 파악하도록 도와줍니다.
    """
    def __init__(self, parent=None, width=5, height=4, dpi=100) -> None:
        fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#1E1E1E')
        self.axes = fig.add_subplot(111)
        self.axes.set_facecolor('#1E1E1E')
        super().__init__(fig)
        self.setParent(parent)

    def plot_trend(self, df: pd.DataFrame, keyword: str) -> None:
        # 기존 그래프를 초기화하고 새로운 데이터를 렌더링합니다 (차트 업데이트 연계)
        self.axes.clear()
        self.axes.plot(df['period'], df['ratio'], color='#00D2FF', marker='o', linewidth=2, markersize=4)
        self.axes.set_title(f"[{keyword}] 30-Day Search Trend", color='white', fontsize=12)
        self.axes.set_xlabel("Date", color='#AAA')
        self.axes.set_ylabel("Search Volume", color='#AAA')
        self.axes.tick_params(colors='#777', labelsize=8)
        self.axes.grid(True, alpha=0.1, color='white')
        self.draw()

class AdvancedTrendApp(QMainWindow):
    """
    히스토리 관리, 가속도 분석, 시각화 및 엑셀 수출 기능을 모두 포함한 
    최상급 통합 리서치 대시보드 클래스입니다.
    """

    def __init__(self) -> None:
        super().__init__()
        self.config_dir = "config"  # 환경 변수 및 설정 파일 경로
        
        # [WAF 스크래핑 전면 포기 -> 안정성 최우선 공식 API 롤백]
        self.shopping_api = ShoppingAPI() 
        self.trend_api = TrendAPI()
        self.naver_ad_api = NaverAdAPI()   # 광고 API: 실제 검색량 / 연관 키워드
        self.scorer = MomentumScorer()
        self.sourcing_handler = SourcingHandler()
        self.ai_analyzer = AIAnalyzer()
        self.vector_search = VectorSearch()
        
        self.search_history: List[str] = []  # 최근 검색 키워드 보관함
        self.analysis_cache: Dict[str, Any] = {} # 세션용 AI 분석 로그 (종료 시 자동 삭제)
        self.all_fetched_items: List[Dict[str, Any]] = []  # 100위까지의 NLP 시맨틱 전용 데이터 풀 변수
        self.current_raw_items: List[Dict[str, Any]] = []  # 표시용 50위 원본 상품 데이터 보관 변수
        self.current_keyword: str = ""  # 현재 분석 중인 검색어 변수
        self.shopping_api = ShoppingAPI()
        self.sourcing_handler = SourcingHandler()
    
        self.init_ui()
        self.load_history()  # 저장된 검색 내역 불러오기
        
        # [수정] 모든 객체 준비 완료 후 데이터 트렌드 패널 업데이트 (딜레이 없이 즉시 실행)
        print("🚀 [System] 초기 데이터랩 트렌드 로드 시도 중...")
        self.update_trends_panel()
        self.refresh_realtime_trends() # [추가] 실시간 트렌드 탭 초기화
        
        # [추가] 트렌드 키워드 클릭 시 자동 검색 연결
        self.trend_shopping_list.itemDoubleClicked.connect(lambda item: self.search_input.setText(item.text().split(": ")[-1]))
        self.trend_shopping_list.itemDoubleClicked.connect(self.perform_research)
        
        self.apply_style()

    def init_ui(self) -> None:
        self.setWindowTitle("💎 Product Research Pro - Integrated Workspace")
        self.setMinimumSize(1250, 850)
        
        main_central = QWidget()
        self.setCentralWidget(main_central)
        layout = QHBoxLayout(main_central)  # 사이드바와 메인을 나누기 위한 가로 레이아웃 변수
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # A. 좌측 사이드바 (Search History Area)
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setObjectName("sidebar")
        sidebar_vbox = QVBoxLayout(sidebar)
        
        hist_header = QHBoxLayout()
        sb_title = QLabel("SEARCH HISTORY")
        sb_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb_title.setStyleSheet("font-weight: bold; color: #AAA; margin: 10px 0;")
        
        clear_hist_btn = QPushButton("\U0001f5d1 삭제")
        clear_hist_btn.setStyleSheet("background-color: #EF4444; color: white; border-radius: 3px; padding: 2px 5px;")
        clear_hist_btn.setFixedWidth(40)
        clear_hist_btn.clicked.connect(self.clear_history)
        
        hist_header.addWidget(sb_title)
        hist_header.addWidget(clear_hist_btn)
        
        self.history_list = QListWidget()  # 히스토리 목록 위젯 변수
        self.history_list.itemClicked.connect(self.load_from_history)
        
        # [추가] 트렌드 패널용 리스트
        trend_panel = QVBoxLayout()
        sidebar_vbox.addLayout(hist_header)
        sidebar_vbox.addWidget(self.history_list)
        trend_panel.addWidget(QLabel("⭐ SHOPPING TREND"))
        self.trend_shopping_list = QListWidget()
        trend_panel.addWidget(self.trend_shopping_list)
        
        trend_panel.addWidget(QLabel("📱 DEVICE & CATEGORY")) # [추가] 기기 비중 패널
        self.trend_device_list = QListWidget()
        trend_panel.addWidget(self.trend_device_list)
        
        trend_panel.addWidget(QLabel("📊 SEARCH TREND"))
        self.trend_search_list = QListWidget()
        trend_panel.addWidget(self.trend_search_list)
        
        sidebar_vbox.addLayout(trend_panel)
        
        layout.addWidget(sidebar)

        # B. 중앙 메인 작업 영역 (Main Workspace Selection)
        workspace = QVBoxLayout()
        layout.addLayout(workspace, stretch=1)

        # 1. 상단 컨트롤 바 (Search & Filters)
        top_bar = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItems(["전체", "스포츠/레저", "패션의류", "디지털/가전", "식품", "생활/건강"])
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("리서치할 키워드 입력...")
        self.search_input.returnPressed.connect(self.perform_research)
        
        # [추가] 조회 기간 설정 드롭다운
        self.period_combo = QComboBox()
        self.period_combo.addItems(["1개월", "3개월", "1주일", "1일"])
        self.period_days_map = {"1개월": 30, "3개월": 90, "1주일": 7, "1일": 1}
        
        self.search_btn = QPushButton("Analysis Start")
        self.search_btn.clicked.connect(self.perform_research)
        
        top_bar.addWidget(self.category_combo)
        top_bar.addWidget(self.search_input)
        top_bar.addWidget(self.period_combo) # 기간 선택 추가
        top_bar.addWidget(self.search_btn)
        workspace.addLayout(top_bar)

        # 2. 가격 필터 바 (Price Range UI)
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Price Range:"))
        self.min_price_input = QLineEdit()
        self.min_price_input.setPlaceholderText("Min (원)")
        self.max_price_input = QLineEdit()
        self.max_price_input.setPlaceholderText("Max (원)")
        self.filter_apply_btn = QPushButton("Apply Filter")
        self.filter_apply_btn.clicked.connect(self.apply_price_filter)
        
        self.excel_export_btn = QPushButton("Export to Excel")  # 엑셀 저장 버튼 변수
        self.excel_export_btn.setStyleSheet("background-color: #166534;")  # 엑셀 녹색 계열 적용
        self.excel_export_btn.clicked.connect(self.export_excel)
        
        filter_bar.addWidget(self.min_price_input)
        filter_bar.addWidget(self.max_price_input)
        filter_bar.addWidget(self.filter_apply_btn)
        filter_bar.addStretch()
        filter_bar.addWidget(self.excel_export_btn)
        workspace.addLayout(filter_bar)

        # 3. 분석 보고서 섹션 (Report Panel)
        reports_layout = QHBoxLayout()
        self.report_box = QTextEdit()
        self.report_box.setReadOnly(True)
        self.report_box.setFixedHeight(150)
        self.ai_report_box = QTextEdit()
        self.ai_report_box.setObjectName("ai_report_box")
        self.ai_report_box.setReadOnly(True)
        self.ai_report_box.setFixedHeight(150)
        
        self.sourcing_tab = QWidget()
        self.init_sourcing_tab()
        
        self.nav_trend_tab = QWidget() # [신설] 네이버 인기 검색어 탭
        self.init_nav_trend_tab()

        self.hidden_tab = QWidget()
        self.init_hidden_tab()
        
        self.cross_tab = QWidget()
        self.init_cross_tab()

        reports_layout.addWidget(self.report_box)
        reports_layout.addWidget(self.ai_report_box)
        workspace.addLayout(reports_layout)

        # 4. 데이터/시각화 통합 탭 (Visual & Data Tabs)
        self.tabs = QTabWidget()
        
        # [혁신] 모든 기능을 6개의 독립 탭으로 완전히 분리하여 초기화
        # 각 탭은 고유의 init 메서드를 통해 레이아웃과 테이블이 완벽하게 세팅됩니다.
        self.main_tab = QWidget(); self.init_main_tab(); self.tabs.addTab(self.main_tab, "📊 Market Discovery")
        self.chart_tab = QWidget(); self.init_chart_tab(); self.tabs.addTab(self.chart_tab, "📈 Trend Chart")
        self.nav_trend_tab = QWidget(); self.init_nav_trend_tab(); self.tabs.addTab(self.nav_trend_tab, "🔍 상품 키워드 분석")
        self.sourcing_tab = QWidget(); self.init_sourcing_tab(); self.tabs.addTab(self.sourcing_tab, "💰 Product Sourcing")
        self.hidden_tab = QWidget(); self.init_hidden_tab(); self.tabs.addTab(self.hidden_tab, "🎯 Hidden Semantic")
        self.cross_tab = QWidget(); self.init_cross_tab(); self.tabs.addTab(self.cross_tab, "🌐 Cross Semantic")
        self.pain_tab = QWidget(); self.init_pain_point_tab(); self.tabs.addTab(self.pain_tab, "🥊 Pain Point 분석")
        self.trend_list_tab = QWidget(); self.init_trend_list_tab(); self.tabs.addTab(self.trend_list_tab, "🚀 실시간 트렌드")

        workspace.addWidget(self.tabs)

    def perform_research(self) -> None:
        keyword = self.search_input.text().strip()
        category = self.category_combo.currentText()
        period_text = self.period_combo.currentText()
        days = self.period_days_map.get(period_text, 30)
        
        if not keyword: return

        self.current_keyword = keyword
        self._add_history(keyword)
        self._set_loading_state(True)
        
        # [추가] 세션 로그 체크 (중복 분석 방지)
        cache_key = f"{keyword}_{category}_{period_text}"
        if cache_key in self.analysis_cache:
            print(f"📦 [System] '{cache_key}' 분석 로그 발견. 캐시 데이터를 로드합니다.")
            cached_data = self.analysis_cache[cache_key]
            self.display_cached_results(cached_data)
            self._set_loading_state(False)
            return

        try:
            full_query = keyword if category == "전체" else f"{category} {keyword}"
            shop_data = self.shopping_api.search_products(full_query, display=100)
            trend_df = self.trend_api.get_daily_trend(keyword, days=days)
            
            if not shop_data or trend_df is None:
                self.report_box.setText("데이터 호출 오류가 발생했습니다.")
                return

            # 분석 엔진 및 시각화 업데이트 (경쟁 강도 추가)
            total_items_count = shop_data.get('total', 0)
            scores = self.scorer.calculate_scores(trend_df, total_products=total_items_count)
            self.display_report_summary(keyword, scores, total_items_count)
            self.chart_canvas.plot_trend(trend_df, keyword)  # 검색 데이터 그래프 시각화 연계함

            import os, json
            
            # 상품 데이터 처리
            self.all_fetched_items = shop_data.get('items', [])[:100]  # 시맨틱 숨겨진 상품 발굴을 위해 100위까지 보관
            self.current_raw_items = self.all_fetched_items[:50]  # 메인 랭킹 테이블은 50위까지만 표출
            
            # API 기반 소싱 파이프라인의 핵심: 임시 JSON 덤프 자동 저장
            os.makedirs("data", exist_ok=True)
            with open("data/naver_results.json", "w", encoding="utf-8") as f:
                json.dump(self.current_raw_items, f, ensure_ascii=False, indent=4)
            
            # [수정] 검색 결과로부터 실제 우세 카테고리 추출하여 트렌드 패널 연동
            try:
                from collections import Counter
                categories = [it.get('category1', '') for it in self.all_fetched_items if it.get('category1')]
                if categories:
                    most_common_cat = Counter(categories).most_common(1)[0][0]
                    print(f"🎯 [System] 분석된 대표 카테고리: {most_common_cat}")
                    self.update_trends_panel(keyword, most_common_cat, days=days)
                else:
                    self.update_trends_panel(keyword, days=days)
            except Exception as e:
                print(f"⚠️ [System] 카테고리 자동 분석 실패: {e}")
            
            self.render_table(self.current_raw_items)  # UI 테이블 렌더(랭킹) 가동
            self.render_sourcing_table(self.current_raw_items) # UI 소싱 탭 병렬 가동
            self.render_top_keywords_table(self.current_raw_items) # 네이버 인기 키워드 탭 (실시간 추출)
            
            # AI 분석 플로우 시작 (AI 트렌드 도출 후 -> 시맨틱 검색)
            self.ai_report_box.setText(f"Gemini 2.0이 {period_text}간의 트렌드를 심층 분석 중입니다... 🤖")
            QApplication.processEvents()
            
            # 1. Gemini 대용량 분석 및 핵심 키워드/상위 추상 개념 동시 추출
            titles = [item['title'].replace("<b>", "").replace("</b>", "") for item in self.current_raw_items]
            ai_insight, trend_keywords, cross_concepts = self.ai_analyzer.analyze_trends(titles, keyword)
            
            # 도출된 인사이트와 키워드를 즉시 화면에 기록 (사용자 경험 향상 연계)
            final_report = f"{ai_insight}\n\n[✨ 핵심 트렌드 10선]:\n{trend_keywords}\n\n[🚀 타 카테고리 확장을 위한 상위 개념 5선]:\n{cross_concepts}"
            self.ai_report_box.setText(final_report)
            
            # 세션 캐시에 저장 (로그 기록)
            self.analysis_cache[cache_key] = {
                "report": final_report,
                "scores": scores,
                "total_items": total_items_count,
                "trend_df": trend_df,
                "raw_items": self.current_raw_items,
                "all_items": self.all_fetched_items,
                "trend_keywords": trend_keywords
            }
            
            self.ai_report_box.append("\n\n(위 10대 트렌드 키워드를 기준 좌표로 삼아 100위 권 내에서 '진짜 히든 상품'을 탐색하고 있습니다... 🎯)")
            QApplication.processEvents()
            
            # 2. 추출된 트렌드 키워드 시퀀스(trend_keywords)를 NLP 모델에 기준 앵커로 주입하여 100위 풀에서 연산 수행
            hidden_recs = self.vector_search.find_hidden_recommendations(trend_keywords, self.all_fetched_items, top_k=10)
            self.render_hidden_table(hidden_recs, self.current_raw_items)  # 중복 여부 확인용으로 상위 50위 데이터 전달
            
            # 3. 최상위 추상 개념을 활용한 진짜 크로스 카테고리 시맨틱 검색 시작 (Cross-Category Discovery 연계)
            self.ai_report_box.append("\n\n(완전히 분리된 '상위 추상 개념'을 통해 타 카테고리를 넘나드는 통합 탐색을 시작합니다... 🌐)")
            QApplication.processEvents()
            
            # 네이버 API가 5개 단어를 모두 AND 검색하여 0건이 나오는 현상을 방지합니다.
            # 가장 강력한 상위 2개 개념만 조합하여 검색하고, 결과가 없으면 상위 1개로 재검색(Fallback)합니다.
            top_abstract_list = [k.strip() for k in cross_concepts.split(",")]
            cross_query = " ".join(top_abstract_list[:2]) if len(top_abstract_list) >= 2 else top_abstract_list[0]
            
            cross_shop_data = self.shopping_api.search_products(cross_query, display=100)
            cross_fetched_items = cross_shop_data.get('items', [])
            
            # 2개 조합으로 실패 시(0건), 가장 핵심인 1번 추상 개념으로만 파격적인 넓은 범위(Broad Search) 재검색 진행
            if not cross_fetched_items and len(top_abstract_list) > 0:
                self.ai_report_box.append(f"  └ ⚠️ '{cross_query}'(으)로 융합 결과가 없어, '{top_abstract_list[0]}' 단일 개념으로 확장 검색합니다.")
                QApplication.processEvents()
                cross_query = top_abstract_list[0]
                cross_shop_data = self.shopping_api.search_products(cross_query, display=100)
                cross_fetched_items = cross_shop_data.get('items', [])
            
            if cross_fetched_items:
                # 찾아온 타 카테고리 아이템 100개에 대해서는, 5개 '전체' 추상 개념(cross_concepts) 벡터를 기준으로 코사인 유사도를 정밀 측정함
                cross_recs = self.vector_search.find_hidden_recommendations(cross_concepts, cross_fetched_items, top_k=10)
                self.render_cross_table(cross_recs, keyword)
                self.ai_report_box.append(f"\n✅ [크로스 탐색 완료!] Cross Semantic 탭에서 이종 카테고리의 융합 상품을 확인하세요. (기준: {cross_query})")
            else:
                self.ai_report_box.append(f"\n❌ 크로스 검색('{cross_query}') 결과가 시장에 전혀 없어 4번째 탭의 갱신을 생략합니다.")
            
            # 4. 소비자 Pain Point 분석 (Blog API + Gemini)
            self.ai_report_box.append(f"\n\n(실제 소비자들의 블로그 후기를 수집하여 페인 포인트를 분석하는 중입니다... 📝)")
            QApplication.processEvents()
            
            blog_context = get_blog_reviews(f"{keyword} 단점")
            if blog_context:
                pain_point_report = analyze_pain_points(blog_context)
                self.pain_text_box.setText(pain_point_report)
                self.ai_report_box.append(f"✅ [분석 완료] 'Pain Point 분석' 탭에서 소비자 불만 및 소싱 전략을 확인하세요.")
            else:
                self.pain_text_box.setText("블로그 리뷰 데이터를 수집하지 못했습니다.")
                
        finally:
            self._set_loading_state(False)

    def init_main_tab(self):
        """메인 랭킹 데이터 탭을 초기화합니다."""
        layout = QVBoxLayout(self.main_tab)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Rank", "Product Name", "Price", "Views", "1M Sales", "Reviews", "Rating", "2W Growth(%)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self.open_product_link)
        layout.addWidget(self.table)

    def init_chart_tab(self):
        """트렌드 시계열 차트 탭을 초기화합니다."""
        layout = QVBoxLayout(self.chart_tab)
        self.chart_canvas = TrendChartCanvas(self)
        layout.addWidget(self.chart_canvas)

    def init_sourcing_tab(self):
        """1688 소싱 상품 탭의 UI를 초기화합니다."""
        layout = QVBoxLayout(self.sourcing_tab)
        self.fx_label = QLabel("💰 환율 로딩 중...")
        self.fx_label.setStyleSheet("color: #FFD700; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(self.fx_label)
        
        self.sourcing_table = QTableWidget()
        self.sourcing_table.setColumnCount(10)
        self.sourcing_table.setHorizontalHeaderLabels(["Rank", "Naver Name", "LPrice(KRW)", "1688 Price(CNY)", "1688 Cost(KRW)", "Margin(KRW)", "Margin(%)", "Link", "Run Sourcing", "Calc"])
        self.sourcing_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.sourcing_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sourcing_table.cellDoubleClicked.connect(self.open_sourcing_link)
        layout.addWidget(self.sourcing_table)

    def init_hidden_tab(self):
        """AI 시맨틱 숨겨진 상품 탭의 UI를 초기화합니다."""
        layout = QVBoxLayout(self.hidden_tab)
        label = QLabel("🎯 AI Semantic Analysis: Top 100위 권 내에서 현재 트렌드와 가장 밀접한 '히든 상품'을 발굴합니다.")
        label.setStyleSheet("color: #A5F3FC; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(label)
        
        self.hidden_table = QTableWidget()
        self.hidden_table.setColumnCount(4)
        self.hidden_table.setHorizontalHeaderLabels(["랭킹", "상품명", "유사도(%)", "가격"])
        self.hidden_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.hidden_table)

    def init_cross_tab(self):
        """크로스 카테고리 시맨틱 탭의 UI를 초기화합니다."""
        layout = QVBoxLayout(self.cross_tab)
        label = QLabel("🌐 Cross-Category Insights: AI가 분석한 상위 추상 개념을 바탕으로 타 카테고리의 융합 지점을 탐색합니다.")
        label.setStyleSheet("color: #C084FC; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(label)
        
        self.cross_table = QTableWidget()
        self.cross_table.setColumnCount(6) # 3개에서 6개로 복구
        self.cross_table.setHorizontalHeaderLabels(["Rank", "Score", "Product Name", "Price", "1M Sales", "2W Growth(%)"])
        self.cross_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.cross_table.cellDoubleClicked.connect(self.open_cross_link)
        layout.addWidget(self.cross_table)

    def init_nav_trend_tab(self):
        """검색어 기반 키워드 분석 탭의 UI를 초기화합니다."""
        layout = QVBoxLayout(self.nav_trend_tab)
        label = QLabel("🔍 검색어 기반 연관 키워드 분석 (NaverAd 연동)")
        label.setStyleSheet("font-size: 14px; font-weight: bold; color: #38BDF8; margin: 8px 0;")
        layout.addWidget(label)
        
        self.nav_trend_table = QTableWidget()
        self.nav_trend_table.setColumnCount(6)
        self.nav_trend_table.setHorizontalHeaderLabels(["순위", "키워드", "월간 검색량", "경쟁도", "\U0001f30a 블루오션", "분석"])
        self.nav_trend_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.nav_trend_table)

    def init_pain_point_tab(self):
        """소비자 불만(Pain Point) 분석 탭의 UI를 초기화합니다."""
        layout = QVBoxLayout(self.pain_tab)
        
        header = QLabel("🔍 소비자 Real Voice 분석: 블로그 리뷰 데이터 기반 단점 및 소싱 전략")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #FCA5A5; margin: 10px 0;")
        layout.addWidget(header)
        
        self.pain_text_box = QTextEdit()
        self.pain_text_box.setReadOnly(True)
        self.pain_text_box.setStyleSheet("""
            background-color: #1A1A1A;
            color: #F8FAFC;
            font-size: 13px;
            line-height: 1.6;
            padding: 15px;
            border: 1px solid #334155;
            border-radius: 8px;
        """)
        layout.addWidget(self.pain_text_box)
        
        tip_label = QLabel("💡 Tip: 여기서 도출된 '개선점'이 반영된 제품을 1688에서 찾으면 강력한 경쟁력을 가질 수 있습니다.")
        tip_label.setStyleSheet("color: #94A3B8; font-style: italic; margin-top: 5px;")
        layout.addWidget(tip_label)

    def init_trend_list_tab(self):
        """네이버 쇼핑 및 분야별 실시간 인기 검색어 탭 초기화"""
        layout = QVBoxLayout(self.trend_list_tab)
        
        top_ctrl = QHBoxLayout()
        self.trend_cat_combo = QComboBox()
        self.trend_cat_combo.addItems([
            "패션의류 (50000000)", "패션잡화 (50000001)", "화장품/미용 (50000002)", 
            "디지털/가전 (50000003)", "가구/인테리어 (50000004)", "출산/육아 (50000005)",
            "식품 (50000006)", "스포츠/레저 (50000007)", "생활/건강 (50000008)"
        ])
        refresh_btn = QPushButton("🔄 새시침")
        refresh_btn.clicked.connect(self.refresh_realtime_trends)
        top_ctrl.addWidget(QLabel("🎯 카테고리 선택:"))
        top_ctrl.addWidget(self.trend_cat_combo)
        top_ctrl.addWidget(refresh_btn)
        top_ctrl.addStretch()
        layout.addLayout(top_ctrl)

        self.trend_list_table = QTableWidget()
        self.trend_list_table.setColumnCount(3)
        self.trend_list_table.setHorizontalHeaderLabels(["순위", "급상승 키워드", "비고"])
        self.trend_list_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.trend_list_table.cellDoubleClicked.connect(lambda r, c: self.search_input.setText(self.trend_list_table.item(r, 1).text()) or self.perform_research())
        layout.addWidget(self.trend_list_table)

    def refresh_realtime_trends(self):
        """데이터랩 내부 API를 호출하여 테이블을 갱신합니다."""
        selected_text = self.trend_cat_combo.currentText()
        cid = selected_text.split("(")[-1].replace(")", "").strip()
        
        url = "https://datalab.naver.com/shoppingInsight/getCategoryKeywordRank.naver"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://datalab.naver.com/shoppingInsight/sCategory.naver",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        payload = {
            "cid": cid, "timeUnit": "date", "startDate": start_date, "endDate": end_date,
            "device": "", "gender": "", "ages": "", "page": 1, "count": 20
        }
        
        try:
            import requests
            resp = requests.post(url, headers=headers, data=payload)
            if resp.status_code == 200:
                data = resp.json()
                ranks = data.get("ranks", [])
                self.trend_list_table.setRowCount(0)
                for i, item in enumerate(ranks):
                    self.trend_list_table.insertRow(i)
                    self.trend_list_table.setItem(i, 0, QTableWidgetItem(str(item['rank'])))
                    self.trend_list_table.setItem(i, 1, QTableWidgetItem(item['keyword']))
                    self.trend_list_table.setItem(i, 2, QTableWidgetItem("HOT"))
                print(f"✅ [Trend] {selected_text} 실시간 트렌드 로드 완료")
        except Exception as e:
            print(f"❌ [Trend Error] {e}")

    def render_top_keywords_table(self, items: List[Dict[str, Any]]):
        """
        🔍 상품 키워드 분석 탭:
        - 1순위: 네이버 광고 API (실제 월간 검색량 + 경쟁도 + 연관 키워드)
        - Fallback: 수집된 상품명 빈도 분석
        """
        if not hasattr(self, 'nav_trend_table'):
            return

        current_kw = self.search_input.text().strip()
        if not current_kw:
            return

        # ── 상품명에서 힌트 단어 추출 (최대 5개, NaverAd 결과 확장용) ──────
        hint_words = []
        try:
            import re
            from collections import Counter
            all_text = " ".join([i['title'].replace("<b>", "").replace("</b>", "") for i in items])
            words = re.findall(r'[가-힣]{2,}', all_text)
            hint_words = [w for w, _ in Counter(words).most_common(10) if w != current_kw][:5]
        except Exception:
            pass

        # ── NaverAd API 호출 (씨드 + 힌트 단어 병합, 실패 시 씨드 단독 재시도) ──
        ad_data = []
        try:
            print(f"\U0001f4f2 [NaverAd] '{current_kw}' 연관 키워드 조회 중...")
            ad_data = self.naver_ad_api.get_related_keywords(current_kw, hint_words=hint_words, top_k=20)
            # 결과 없으면 씨드 단독으로 재시도
            if not ad_data:
                print(f"   └ 힌트 포함 조회 결과 없음 → 씨드 단독 재시도")
                ad_data = self.naver_ad_api.get_related_keywords(current_kw, hint_words=[], top_k=20)
            if ad_data:
                print(f"\u2705 [NaverAd] {len(ad_data)}개 연관 키워드 수신")
        except Exception as e:
            print(f"\u26a0\ufe0f [NaverAd] API 오류, Fallback 실행: {e}")

        self.nav_trend_table.setRowCount(0)

        if ad_data:
            # ── 블루오션 지수 사전 계산 ───────────────────────────────────
            ad_score_map = {"낮음": 1.0, "중간": 0.5, "높음": 0.0}
            max_vol = max((r.get("totalQcCnt", 0) for r in ad_data), default=1) or 1

            for row_data in ad_data:
                vol   = row_data.get("totalQcCnt", 0)
                comp  = row_data.get("compIdx", "높음")
                vol_score  = vol / max_vol                      # 0~1 (높을수록 수요 많음)
                comp_score = ad_score_map.get(comp, 0.0)       # 0~1 (낮을수록 경쟁 적음)
                row_data["_blue_ocean"] = round(vol_score * 0.6 + comp_score * 0.4, 3)

            # ── 6컬럼 테이블: 순위/키워드/검색량/경쟁도/블루오션지수/분석 ──
            self.nav_trend_table.setColumnCount(6)
            self.nav_trend_table.setHorizontalHeaderLabels(
                ["순위", "키워드", "월간 검색량", "경쟁도", "🌊 블루오션", "분석"]
            )
            self.nav_trend_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

            for i, row_data in enumerate(ad_data):
                keyword  = row_data.get("relKeyword", "")
                total    = row_data.get("totalQcCnt", 0)
                comp_raw = row_data.get("compIdx", "-")
                blue     = row_data.get("_blue_ocean", 0.0)

                total_str = f"{total:,}" if isinstance(total, int) else str(total)
                comp_icon = {"낮음": "🟢", "중간": "🟡", "높음": "🔴"}.get(comp_raw, "⚪")

                # 블루오션 등급
                if blue >= 0.75:
                    blue_str   = f"⭐ {int(blue*100)}점"
                    blue_color = QColor("#34D399")   # 진입 강력 추천 (민트)
                elif blue >= 0.5:
                    blue_str   = f"✅ {int(blue*100)}점"
                    blue_color = QColor("#FDE047")   # 진입 고려 (노랑)
                else:
                    blue_str   = f"⚠️ {int(blue*100)}점"
                    blue_color = QColor("#F87171")   # 경쟁 과열 (빨강)

                self.nav_trend_table.insertRow(i)
                self.nav_trend_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                self.nav_trend_table.setItem(i, 1, QTableWidgetItem(keyword))
                self.nav_trend_table.setItem(i, 2, QTableWidgetItem(total_str))
                self.nav_trend_table.setItem(i, 3, QTableWidgetItem(f"{comp_icon} {comp_raw}"))

                blue_item = QTableWidgetItem(blue_str)
                blue_item.setForeground(blue_color)
                self.nav_trend_table.setItem(i, 4, blue_item)

                btn = QPushButton("🔍 분석")
                btn.clicked.connect(lambda _, w=keyword: (self.search_input.setText(w), self.perform_research()))
                self.nav_trend_table.setCellWidget(i, 5, btn)

            print("✅ [System] 키워드 분석 탭 갱신 완료 (NaverAd + 블루오션 지수)")

        else:
            # ── Fallback: 상품명 빈도 분석 (3컬럼, 최소 빈도 2회 이상만) ──
            print("\U0001f504 [System] Fallback: 상품명 빈도 분석 실행")
            import re
            from collections import Counter
            all_text = " ".join([i['title'].replace("<b>", "").replace("</b>", "") for i in items])
            # 한글 2자 이상, 영문 3자 이상만 추출 (짧은 의미없는 단어 제거)
            words = re.findall(r'[가-힣]{2,}', all_text)
            counter = Counter(words)
            # 최소 2회 이상 등장 + 현재 검색어 단어 제외
            kw_parts = set(current_kw.split())
            filtered = [
                (w, c) for w, c in counter.most_common(60)
                if c >= 2 and w not in kw_parts and len(w) >= 2
            ][:20]

            self.nav_trend_table.setColumnCount(3)
            self.nav_trend_table.setHorizontalHeaderLabels(["순위", "키워드 (상품명 분석)", "분석"])
            self.nav_trend_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

            for i, (word, count) in enumerate(filtered):
                self.nav_trend_table.insertRow(i)
                self.nav_trend_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                self.nav_trend_table.setItem(i, 1, QTableWidgetItem(f"{word}  ({count}회)"))
                btn = QPushButton("\U0001f50d 분석")
                btn.clicked.connect(lambda _, w=word: (self.search_input.setText(w), self.perform_research()))
                self.nav_trend_table.setCellWidget(i, 2, btn)

            print(f"\u2705 [System] Fallback 키워드 탭 갱신 완료 ({len(filtered)}개)")

    def display_cached_results(self, data: Dict[str, Any]):
        """이미 분석된 로그가 있을 경우 즉시 리포트와 테이블을 렌더링합니다."""
        self.ai_report_box.setText(data["report"])
        self.display_report_summary(self.current_keyword, data["scores"], data["total_items"])
        self.chart_canvas.plot_trend(data["trend_df"], self.current_keyword)
        self.current_raw_items = data["raw_items"]
        self.all_fetched_items = data["all_items"]
        
        self.render_table(self.current_raw_items)
        self.render_sourcing_table(self.current_raw_items)
        
        recs = self.vector_search.find_hidden_recommendations(data["trend_keywords"], self.all_fetched_items, top_k=10)
        self.render_hidden_table(recs, self.current_raw_items)

    def load_history(self):
        """저장된 검색 키워드 내역만 불러옵니다 (Gemini 분석 결과는 로드하지 않음)."""
        history_path = os.path.join(self.config_dir, "history.json")
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    self.search_history = json.load(f)
                    self.history_list.addItems(self.search_history[:10])
            except Exception: pass

    def clear_history(self):
        """저장된 검색 내역을 모두 삭제합니다."""
        self.search_history = []
        self.history_list.clear()
        history_path = os.path.join(self.config_dir, "history.json")
        try:
            if os.path.exists(history_path):
                os.remove(history_path)
            print("\U0001f5d1 [System] 검색 내역이 모두 삭제되었습니다.")
        except Exception:
            pass

    def save_history(self):
        """프로그램 종료 시 최근 검색어(글자)만 저장하고 분석 내용은 삭제(기본값)합니다."""
        os.makedirs(self.config_dir, exist_ok=True)
        history_path = os.path.join(self.config_dir, "history.json")
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(self.search_history[:10], f, ensure_ascii=False, indent=4)

    def closeEvent(self, event):
        """윈도우 종료 시 히스토리만 저장합니다."""
        self.save_history()
        print("📁 [System] 검색 히스토리가 저장되었습니다. (분석 로그는 삭제되었습니다.)")
        event.accept()

    # 전체 상품 리스트를 테이블에 표시합니다. 필터링 결과를 표시할 때도 재사용됨
    def render_table(self, items: List[Dict[str, Any]]) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            title = item['title'].replace("<b>", "").replace("</b>", "")
            
            # 💡 [데이터 무결성 강화] 
            # 네이버 쇼핑 API에서 직접 제공하지 않는 지표(조회수, 판매량 등)는 
            # 사용자 요청에 따라 가상 데이터를 생성하지 않고 N/A로 표시합니다.
            
            # 셀 아이템 주입
            self.table.setItem(row, 0, self._create_int_item(row + 1, "위"))
            name_item = QTableWidgetItem(title)
            name_item.setData(Qt.ItemDataRole.UserRole, item['link'])
            name_item.setForeground(QColor("#00D2FF"))
            self.table.setItem(row, 1, name_item)
            
            self.table.setItem(row, 2, self._create_int_item(int(item['lprice']), "원"))
            self.table.setItem(row, 3, self._create_int_item("N/A"))
            self.table.setItem(row, 4, self._create_int_item("N/A"))
            self.table.setItem(row, 5, self._create_int_item("N/A"))
            self.table.setItem(row, 6, self._create_int_item("N/A"))
            self.table.setItem(row, 7, self._create_int_item("N/A"))
            
        self.table.setSortingEnabled(True)

    # 코사인 유사도 기반 히든 추천 데이터를 테이블에 렌더링합니다.
    def render_hidden_table(self, items: List[Dict[str, Any]], baseline_items: List[Dict[str, Any]] = None) -> None:
        if baseline_items is None:
            baseline_items = []
        baseline_links = {it['link'] for it in baseline_items}  # 메인 데이터 중복 검사용 해시셋 생성
        
        self.hidden_table.setSortingEnabled(False)
        self.hidden_table.setRowCount(len(items))
        for row, item in enumerate(items):
            # 0~1 사이의 코사인 유사도를 백분율(%)로 표기하여 직관적으로 보여줌 (스코어 시각화 연계)
            sim_score = int(item.get('semantic_similarity', 0.0) * 100)
            clean_title = item.get('clean_title', '')
            
            # 셀 아이템 주입
            self.hidden_table.setItem(row, 0, self._create_int_item(row + 1, "순위"))
            
            # 시맨틱 유사도 점수 시각화 컬러 그레이딩 (높을수록 강조)
            score_item = self._create_int_item(sim_score, "% 유사도")
            if sim_score >= 80: score_item.setForeground(QColor("#F472B6")) # 마젠타
            elif sim_score >= 60: score_item.setForeground(QColor("#38BDF8")) # 스카이블루
            self.hidden_table.setItem(row, 1, score_item)
            
            name_item = QTableWidgetItem(clean_title)
            name_item.setData(Qt.ItemDataRole.UserRole, item['link'])
            
            # 핵심 로직: Ranking Data(1~50위)에 포함된 일반 상품이면 노란색, 순위 밖에서 끌어올려진 진짜 히든 상품이면 파란색 
            if item['link'] in baseline_links:
                name_item.setForeground(QColor("#FDE047")) # 중복 상품 노란색(Yellow) 강조 마킹
            else:
                name_item.setForeground(QColor("#00D2FF")) # 순위 밖의 진주(Hidden) 파란색 마킹
                
            self.hidden_table.setItem(row, 2, name_item)
            
            self.hidden_table.setItem(row, 3, QTableWidgetItem(f"{int(item['lprice']):,}원"))
            
        self.hidden_table.setSortingEnabled(True)

    # 타 카테고리에서 융합되어 추출된 진짜 크로스 시맨틱 추천 데이터를 에메랄드 컬러로 렌더링합니다.
    def render_cross_table(self, items: List[Dict[str, Any]], keyword: str) -> None:
        self.cross_table.setSortingEnabled(False)
        self.cross_table.setRowCount(len(items))
        for row, item in enumerate(items):
            title = item.get('clean_title', '')
            self.cross_table.setItem(row, 0, self._create_int_item(row + 1, "순위"))
            
            sim_score = int(item.get('semantic_similarity', 0.0) * 100)
            score_item = self._create_int_item(sim_score, "% 유사도")
            if sim_score >= 80: score_item.setForeground(QColor("#A7F3D0"))
            elif sim_score >= 60: score_item.setForeground(QColor("#34D399")) 
            self.cross_table.setItem(row, 1, score_item)
            
            name_item = QTableWidgetItem(title)
            name_item.setData(Qt.ItemDataRole.UserRole, item['link'])
            name_item.setForeground(QColor("#10B981"))
            self.cross_table.setItem(row, 2, name_item)
            
            self.cross_table.setItem(row, 3, self._create_int_item(int(item.get('lprice', 0)), "원"))
            self.cross_table.setItem(row, 4, self._create_int_item("N/A"))
            self.cross_table.setItem(row, 5, self._create_int_item("N/A"))
            
        self.cross_table.setSortingEnabled(True)

    # 가격 범위 필터링을 수행하여 테이블을 갱신합니다.
    def apply_price_filter(self) -> None:
        try:
            min_p = int(self.min_price_input.text()) if self.min_price_input.text() else 0
            max_p = int(self.max_price_input.text()) if self.max_price_input.text() else 999999999
            
            # 현재 수집된 항목 중 가격 대역이 맞는 것만 선별 (필터링 엔진 연계)
            filtered = [it for it in self.current_raw_items if min_p <= int(it['lprice']) <= max_p]
            self.render_table(filtered)
        except ValueError:
            QMessageBox.warning(self, "Input Error", "가격은 숫자만 입력해 주세요.")

    # 현재 테이블의 결과물과 AI 인사이트를 엑셀 파일로 추출합니다.
    def export_excel(self) -> None:
        if not self.current_raw_items: return
        
        path, _ = QFileDialog.getSaveFileName(self, "Excel 저장", f"Research_{self.current_keyword}.xlsx", "Excel Files (*.xlsx)")
        if not path: return
        
        try:
            # 1. 랭킹 데이터 시트 생성 (데이터 변환 연계)
            df_rows = []
            for row in range(self.table.rowCount()):
                df_rows.append({
                    "Rank": self.table.item(row, 0).data(Qt.ItemDataRole.EditRole),
                    "Product": self.table.item(row, 1).text(),
                    "Price": self.table.item(row, 2).text(),
                    "Views": self.table.item(row, 3).data(Qt.ItemDataRole.EditRole),
                    "1M Sales": self.table.item(row, 4).data(Qt.ItemDataRole.EditRole),
                    "2W Growth(%)": self.table.item(row, 7).data(Qt.ItemDataRole.EditRole),
                    "경쟁 강도(전체상품수/상대검색량)": getattr(self, 'current_competition_index', 0.0),
                    "진입 장벽 점수": getattr(self, 'current_entry_barrier', 0.0),
                    "블루오션 뱃지": "초강력 추천(Blue Ocean)" if getattr(self, 'current_is_blue_ocean', False) else "일반 경합군",
                    "Link": self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
                })
            
            with pd.ExcelWriter(path, engine='openpyxl') as writer:
                # 1. 랭킹 데이터 먼저 시트에 작성 (메인 필드 연계)
                main_df = pd.DataFrame(df_rows)
                main_df.to_excel(writer, index=False, sheet_name="Research_Report")
                
                # 2. 동일 시트 하단에 리포트 텍스트 추가 (상세 리포트 병합)
                worksheet = writer.sheets["Research_Report"]
                start_row = len(df_rows) + 3 # 데이터 종료 후 2줄 공간 확보
                
                # 분석 진단 및 AI 경향성 조사 섹션 추가
                worksheet.cell(row=start_row, column=1, value="[공식 시장 진단 리포트]")
                worksheet.cell(row=start_row+1, column=1, value=self.report_box.toPlainText())
                
                worksheet.cell(row=start_row+4, column=1, value="[Gemini AI 시장 경향성 조사]")
                worksheet.cell(row=start_row+5, column=1, value=self.ai_report_box.toPlainText())
                
            QMessageBox.information(self, "Success", "통합 리포트가 엑셀로 저장되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"저장 실패: {str(e)}")

    def _add_history(self, keyword: str) -> None:
        if keyword in self.search_history: self.search_history.remove(keyword)
        self.search_history.insert(0, keyword)
        self.history_list.clear()
        self.history_list.addItems(self.search_history[:10])
        
        # 히스토리만 갱신 (트렌드 갱신은 데이터 수집 후 결과에 따라 정밀하게 수행)

    def load_from_history(self, item) -> None:
        self.search_input.setText(item.text())
        self.perform_research()

    def _set_loading_state(self, is_loading: bool) -> None:
        txt = "Analysing Market..." if is_loading else "Analysis Start"
        self.search_btn.setText(txt)
        self.search_btn.setEnabled(not is_loading)

    def open_product_link(self, row: int, col: int) -> None:
        item = self.table.item(row, 1)
        if item:
            url = item.data(Qt.ItemDataRole.UserRole)
            if url: webbrowser.open(url)

    # 히든 테이블 셀(인덱스 2가 상품명)을 클릭했을 때 링크를 여는 독립 메서드
    def open_hidden_link(self, row: int, col: int) -> None:
        item = self.hidden_table.item(row, 2)
        if item:
            url = item.data(Qt.ItemDataRole.UserRole)
            if url: webbrowser.open(url)

    def render_sourcing_table(self, items: List[Dict[str, Any]]) -> None:
        self.sourcing_table.setRowCount(len(items))
        for row, item in enumerate(items):
            title = item['title'].replace("<b>", "").replace("</b>", "")
            lprice = int(item.get('lprice', 0))
            
            self.sourcing_table.setItem(row, 0, self._create_int_item(row + 1, "위"))
            self.sourcing_table.setItem(row, 1, QTableWidgetItem(title))
            self.sourcing_table.setItem(row, 2, self._create_int_item(lprice, "원"))
            
            # 1688 통신 대기 상태 세팅
            self.sourcing_table.setItem(row, 3, QTableWidgetItem("Ready"))
            self.sourcing_table.setItem(row, 4, QTableWidgetItem("-"))
            self.sourcing_table.setItem(row, 5, QTableWidgetItem("-"))
            self.sourcing_table.setItem(row, 6, QTableWidgetItem("-"))
            
            # 링크 (7번 열)
            link_item = QTableWidgetItem("Wait...")
            link_item.setData(Qt.ItemDataRole.UserRole, "")
            self.sourcing_table.setItem(row, 7, link_item)
            
            # 소싱 측정 버튼 (8번 열)
            btn = QPushButton("Source Now")
            btn.setStyleSheet("background-color: #8B5CF6; color: white; font-weight: bold;")
            btn.clicked.connect(lambda checked, r=row, img=item.get('image', ''), lp=lprice: self.run_single_sourcing(r, img, lp))
            self.sourcing_table.setCellWidget(row, 8, btn)
            
            # 순마진 계산기 버튼 (9번 열)
            calc_btn = QPushButton("💰 Margin")
            calc_btn.setStyleSheet("background: #008cba; color: white; font-weight: bold;")
            calc_btn.clicked.connect(lambda _, r=row: self.open_margin_calculator(r))
            self.sourcing_table.setCellWidget(row, 9, calc_btn)
            
    def open_margin_calculator(self, row: int):
        """해당 상품의 정보를 기반으로 정밀 계산기 팝업을 엽니다."""
        try:
            # 네이버 판매가 및 현재까지 알려진 중국 원가(위안) 획득
            naver_price_text = self.sourcing_table.item(row, 2).text().replace(",","").replace("원","")
            np = int(naver_price_text) if naver_price_text.isdigit() else 0
            
            cny_price_text = self.sourcing_table.item(row, 3).text().replace("¥","")
            # 만약 아직 데이터를 못가져왔다면 0.0 처리
            cp = float(cny_price_text) if (cny_price_text and cny_price_text[0].isdigit()) else 0.0
            
            # 팝업 실행 (부모 위젯, 네이버가, 위안가, 실시간환율 전달)
            dialog = MarginCalculatorDialog(self, np, cp, self.sourcing_handler.exchange_rate)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "계산기 오류", f"상품 정보를 읽을 수 없습니다: {e}")

    def run_single_sourcing(self, row: int, img_url: str, naver_price: int) -> None:
        self.sourcing_table.item(row, 3).setText("1688 연결 중...")
        QApplication.processEvents() # 화면 멈춤 해소
        
        try:
            # 1. 1688 이미지 기반 RapidAPI 소싱 실행
            result = self.sourcing_handler.search_1688_by_image(img_url)
            
            if "error" in result:
                self.sourcing_table.item(row, 3).setText("검색 실패")
                return
                
            cny = result.get('price_cny', 0)
            krw_cost = result.get('price_krw', 0)
            detail_link = result.get('detail_link', '')
            
            # 2. 마진 계산식 돌입 (네이버최저가 - (1688통관환산비용 + 위탁배송비 7000원))
            margin_result = self.sourcing_handler.calculate_margin(naver_price, cny, shipping_fee=7000)
            
            # 3. 렌더링 주입
            self.sourcing_table.setItem(row, 3, self._create_int_item(cny, "¥"))
            self.sourcing_table.setItem(row, 4, self._create_int_item(krw_cost, "원 (단가)"))
            
            margin_krw = margin_result['margin_krw']
            margin_pct = margin_result['margin_pct']
            
            m_item = self._create_int_item(margin_krw, "원")
            
            # [오류 해결] NumericItem 인자 오류를 방지하기 위해 텍스트 수동 생성 후 주입
            p_item = NumericItem()
            p_item.setData(Qt.ItemDataRole.EditRole, margin_pct)
            p_item.setData(Qt.ItemDataRole.UserRole, float(margin_pct))
            p_item.setText(f"{margin_pct}%")
            
            # 마진 마커 (초록/빨강 스펙트럼)
            if margin_pct >= 40:
                p_item.setForeground(QColor("#34D399")) # High Margin (초록)
                m_item.setForeground(QColor("#34D399"))
            elif margin_pct <= 10:
                p_item.setForeground(QColor("#F87171")) # Low Margin (빨강)
                m_item.setForeground(QColor("#F87171"))
                
            self.sourcing_table.setItem(row, 5, m_item)
            self.sourcing_table.setItem(row, 6, p_item)
            
            # 1688 원본 링크
            link_item = QTableWidgetItem("1688 링크 이동")
            link_item.setForeground(QColor("#60A5FA"))
            font = link_item.font()
            font.setUnderline(True)
            link_item.setFont(font)
            link_item.setData(Qt.ItemDataRole.UserRole, detail_link)
            self.sourcing_table.setItem(row, 7, link_item)
            
            # 버튼 상태 변화
            btn = self.sourcing_table.cellWidget(row, 8)
            if btn:
                btn.setText("추적 완료")
                btn.setStyleSheet("background-color: #059669; color: white; border-radius: 4px; padding: 4px;")
                btn.setEnabled(False)

        except Exception as e:
            self.sourcing_table.item(row, 3).setText(f"오류: {str(e)[:10]}")

    def open_sourcing_link(self, row: int, col: int) -> None:
        """클릭된 행의 1688 최저가 상세 주소를 브라우저로 엽니다."""
        if col == 7: # Link 열 인덱스
            item = self.sourcing_table.item(row, col)
            if item:
                link = item.data(Qt.ItemDataRole.UserRole)
                if link:
                    import webbrowser
                    webbrowser.open(link)

    # 크로스 시맨틱 탭에서 상품명 클릭 시 쇼핑 페이지를 엽니다.
    def open_cross_link(self, row: int, col: int) -> None:
        item = self.cross_table.item(row, 2)
        if item:
            url = item.data(Qt.ItemDataRole.UserRole)
            if url: webbrowser.open(url)

    def display_report_summary(self, keyword: str, scores: Dict[str, Any], total_products: int) -> None:
        # 멤버 변수로 저장하여 엑셀 내보내기 시 참조할 수 있도록 조치 (컨텍스트 유지)
        self.current_competition_index = scores.get('competition_index', 0.0)
        self.current_entry_barrier = scores.get('entry_barrier_score', 0.0)
        self.current_is_blue_ocean = scores.get('is_blue_ocean', False)
        
        fs = scores.get('final_score', 0.0)
        diag = "🚀 [Lising Star]" if fs >= 1.5 else "✅ [Steady]" if fs >= 1.0 else "📉 [Stagnant]"
        
        report = (f"\U0001f50d Keyword: {keyword}\n"
                  f"\U0001f4c8 Diagnosis: {diag} | 전체 상품 수: {total_products:,}\n"
                  f"\u2694\ufe0f 경쟁 강도(상품수 비율): {self.current_competition_index:,.2f} | \U0001f6e1\ufe0f 진입 장벽 점수: {self.current_entry_barrier:.4f}\n"
                  f"\U0001f4ca Scorer: Acceleration({scores.get('acceleration', 0)}) | Velocity({scores.get('velocity', 0)}) | Total({fs})\n")

        # 지표 안내문은 앱 세션당 1회만 출력하여 피로도를 줄임
        if not getattr(self, '_summary_guide_shown', False):
            report += (f"-"*50 + "\n"
                       f"[\U0001f4d6 전체 지표 안내]\n"
                       f" \u2022 \U0001f30a 블루오션: 광고 경쟁도와 검색량을 종합한 점수입니다. (\u2b5075점 이상 진입 권장)\n"
                       f" \u2022 \U0001f4ca Scorer: Acceleration은 급상승 동력을, Velocity는 꾸준한 수요의 속도를 뜻합니다.\n"
                       f" \u2022 \u2694\ufe0f 경쟁 강도: 전체 상품 수 대비 검색량 비교값으로, 낮을수록 시장 공급이 적어 판매에 유리합니다.\n"
                       f"-"*50)
            self._summary_guide_shown = True
                  
        # 블루오션일 경우 텍스트 색상(StyleSheet) 강조 및 시그널 텍스트 추가
        if self.current_is_blue_ocean:
            report += "\n\n🌊 [초강력 추천(Blue Ocean)] 검색량 가속도는 폭발적인데, 시장 포화도가 낮아 지금 당장 진입하기 최적의 아이템입니다!"
            self.report_box.setStyleSheet("color: #38BDF8; font-weight: bold;") 
        else:
            self.report_box.setStyleSheet("color: #F8FAF6; font-weight: normal;")
            
        self.report_box.setText(report)


    def update_trends_panel(self, keyword: str = "", category_name: str = "", days: int = 30):
        """네이버 데이터랩 API를 호출하여 왼쪽 3단 패널의 트렌드 정보를 로드합니다."""
        
        # 분류명 -> ID 변환 시도 (정확한 대분류 매핑 필요)
        cat_mapper = {
            "패션의류": "50000000", "패션잡화": "50000001", "화장품/미용": "50000002",
            "디지털/가전": "50000003", "가구/인테리어": "50000004", "출산/육아": "50000005",
            "식품": "50000006", "스포츠/레저": "50000007", "생활/건강": "50000008", "여가/생활편의": "50000009"
        }
        target_cat_id = cat_mapper.get(category_name, "50000000") # 기본값 패션의류
        
        # (1) 쇼핑인사이트 카테고리 비중 (성별/기기/연령 등)
        try:
            print(f"📡 [System] '{category_name or '전체'}' 카테고리 통계 요청 중...")
            if hasattr(self.shopping_api, 'get_category_demographics'):
                resp = self.shopping_api.get_category_demographics(target_cat_id, days=days)
                if resp and 'results' in resp:
                    self.trend_shopping_list.clear()
                    
                    # [추가] 성별 통계 데이터 병렬 호출 및 표시
                    gender_resp = self.shopping_api.get_category_gender_demographics(target_cat_id, days=days)
                    if gender_resp and 'results' in gender_resp:
                        gender_data = gender_resp['results'][0].get('data', [])
                        if gender_data:
                            # 성별 데이터의 최신 스냅샷(남/여 2개) 추출
                            latest_g = gender_data[-2:]
                            for g in latest_g:
                                g_label = "여성" if g['group'] == 'f' else "남성"
                                icon = "👩" if g['group'] == 'f' else "👨"
                                self.trend_shopping_list.addItem(f"{icon} {g_label} 관심도: {int(g['ratio'])}%")
                            
                        # [추가] 기기별 트렌드 호출 및 표시
                        device_resp = self.shopping_api.get_device_trend(target_cat_id, days=days)
                        if device_resp and 'results' in device_resp:
                            device_data = device_resp['results'][0].get('data', [])
                            if device_data:
                                self.trend_device_list.clear()
                                self.trend_device_list.addItem(f"[{category_name or '전체'}] 기기 비중:")
                                for d in device_data[-2:]:
                                    dev_name = "PC" if d['group'] == 'pc' else "모바일"
                                    dev_icon = "💻" if d['group'] == 'pc' else "📱"
                                    self.trend_device_list.addItem(f"  {dev_icon} {dev_name}: {int(d['ratio'])}%")

                        # [수정] 네이버 API 에러 방지를 위해 실시간 상품 키워드 분석 로직 호출
                        self.render_top_keywords_table(self.all_fetched_items)

                        self.trend_shopping_list.addItem("-" * 20) # 구분선

                    # JSON 트리 구조 파싱 (results -> data -> ratio/group)
                    data_list = []
                    # [수정] 키워드가 있으면 키워드 정밀 연령 분석, 없으면 카테고리 일반 분석
                    if keyword:
                        k_demo = self.shopping_api.get_keyword_demographics(target_cat_id, keyword, days=days)
                        if k_demo and 'results' in k_demo:
                            data_list = k_demo['results'][0].get('data', [])
                            if data_list: self.trend_shopping_list.addItem(f"🎯 '{keyword}' 정밀 분석:")
                    
                    if not data_list: # 키워드 분석 데이터가 없거나 키워드가 없을 때 보조로 카테고리 분석
                        data_list = resp['results'][0].get('data', [])
                    if data_list:
                        # [수정] 현재 시점에 대해 가장 높은 연령대를 100%로 하는 상대적 비중 재계산
                        latest_items = data_list[-6:]
                        # 연령대 중 최댓값을 찾아 기준으로 삼음 (정규화 연계)
                        max_val = max([it.get('ratio', 0) for it in latest_items]) if latest_items else 1
                        
                        for item in latest_items:
                            group = item.get('group', 'Unknown')
                            raw_ratio = item.get('ratio', 0)
                            # 현재 스냅샷 기준 정규화 (최고점 연령대가 항상 100%로 보이도록 처리)
                            normalized_ratio = (raw_ratio / max_val) * 100 if max_val > 0 else 0
                            self.trend_shopping_list.addItem(f"{group}대 비중: {int(normalized_ratio)}%")
                        print(f"✅ [System] 쇼핑 연령별 통계 로드 완료")
                    else:
                        self.trend_shopping_list.addItem("데이터 없음")
                else:
                    print("⚠️ [System] 쇼핑 통계 데이터 형식이 올바르지 않음")
            else:
                print("🚨 [System] ShoppingAPI에 get_category_demographics 메서드가 없습니다!")
        except Exception as e:
            print(f"🚨 [System] 쇼핑 트렌드 업데이트 실패: {e}")
            import traceback
            traceback.print_exc()
        
        # (2) 검색어 트렌드 (현재 검색어 기준)
        if keyword:
            try:
                print(f"📡 [System] '{keyword}' 검색어 트렌드 요청 중...")
                trends = self.shopping_api.get_keyword_trend(keyword)
                if trends:
                    self.trend_search_list.clear()
                    self.trend_search_list.addItem(f"[{keyword}] 최근 추이:")
                    for t in trends:
                        self.trend_search_list.addItem(f"  - {t}")
                    print(f"✅ [System] '{keyword}' 트렌드 로드 완료")
            except Exception as e:
                print(f"🚨 [System] 검색어 트렌드 업데이트 실패: {e}")
        else:
            self.trend_search_list.clear()
            self.trend_search_list.addItem("검색 시 트렌드가 표시됩니다.")

    # 숫자형 데이터를 정렬 가능한 테이블 커스텀 아이템(NumericItem)으로 파싱하는 헬퍼 메서드
    def _create_int_item(self, value: Any, suffix: str = "") -> QTableWidgetItem:
        item = NumericItem()
        
        # N/A 또는 데이터 없음 처리
        if value == "N/A" or value is None:
            item.setData(Qt.ItemDataRole.UserRole, -1.0)
            item.setData(Qt.ItemDataRole.EditRole, -1.0)
            item.setText("N/A")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor("#64748B")) # 흐릿한 회색 처리
            return item

        item.setData(Qt.ItemDataRole.UserRole, float(value))
        item.setData(Qt.ItemDataRole.EditRole, value)
        
        if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
            item.setText(f"{int(value):,}{suffix}")
        else:
            item.setText(f"{value}{suffix}")
            
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return item

    def apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow { background-color: #0F172A; }
            #sidebar { background-color: #1E293B; border-right: 1px solid #334155; }
            QWidget { background-color: #0F172A; color: #F8FAF6; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'NanumGothic', sans-serif; font-size: 14px; }
            QLineEdit, QComboBox, QListWidget { 
                background-color: #1E293B; border: 1px solid #334155; border-radius: 6px; padding: 8px; color: white;
            }
            QPushButton { background-color: #38BDF8; color: #0F172A; border-radius: 6px; font-weight: bold; padding: 10px; }
            QPushButton:hover { background-color: #7DD3FC; }
            QTabWidget::pane { border: 1px solid #334155; background: #0F172A; border-radius: 10px; }
            QTabBar::tab { background: #1E293B; color: #94A3B8; padding: 10px 20px; border-top-left-radius: 10px; border-top-right-radius: 10px; }
            QTabBar::tab:selected { background: #0F172A; color: #38BDF8; font-weight: bold; }
            QTableWidget { background-color: #1E293B; gridline-color: #334155; border-radius: 10px; }
            QHeaderView::section { background-color: #334155; color: #CBD5E1; padding: 8px; border: none; }
            #ai_report_box { color: #F472B6; font-style: italic; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdvancedTrendApp()
    window.show()
    sys.exit(app.exec())
