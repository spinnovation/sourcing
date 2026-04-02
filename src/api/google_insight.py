import os
from typing import Dict, Any, List
from dotenv import load_dotenv
from serpapi import GoogleSearch

class GoogleInsightEngine:
    """
    [Why/Context 발굴기]
    네이버(What)에서는 절대 알 수 없는 소비자의 속마음, 치명적 단점, 열광하는 진짜 이유(Why)를 
    구글의 방대한 검색 결과(장단점, 솔직 후기, 트렌드)에서 직접 긁어와 AI에게 먹이는 특수 부대.
    """
    def __init__(self):
        # 환경 변수 로드
        load_dotenv(".env")
        self.api_key = os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            print("🚨 [WARN] .env 파일에 'SERPAPI_API_KEY'가 누락되어 구글 인사이트 엔진이 대기 상태입니다.")
            
    def fetch_deep_context(self, keyword: str) -> str:
        """
        키워드를 기반으로 3개의 심층 탐색 쿼리를 생성, 구글을 털어 핵심 스니펫(결과 요약문)을 하나의 덩어리로 반환합니다.
        """
        if not self.api_key:
            return "구글 검색(SerpApi) 키가 연결되지 않아 시장 심층 Context 분석이 누락되었습니다."
            
        print(f"🔍 [Google Insight] '{keyword}'의 진짜 유행 원인과 현실 후기를 구글에서 털고 있습니다...")
        
        # 구글을 상대로 소비자의 속마음을 캐기 위한 심문(Query) 자동 생성
        queries = [
            f"{keyword} 현실적인 장단점",
            f"최신 {keyword} 유행하는 진짜 이유 트렌드",
            f"{keyword} 내돈내산 찐후기"
        ]
        
        aggregated_snippets = []
        
        for q in queries:
            params = {
              "engine": "google",
              "q": q,
              "hl": "ko",
              "gl": "kr",
              "api_key": self.api_key,
              "num": 3 # 토큰 낭비와 시간 낭비 방지를 위해 각 쿼리당 '구글 검색 1~3위'의 최상위 스니펫만 강력하게 수집
            }
            
            try:
                search = GoogleSearch(params)
                results = search.get_dict()
                
                organic_results = results.get("organic_results", [])
                for result in organic_results:
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    if snippet:
                        aggregated_snippets.append(f"● [검색어: {q}] {title}\n  -> {snippet}")
            except Exception as e:
                print(f"☠️ [Google Insight Error] {str(e)}")
                continue
                
        # AI가 단숨에 읽어 치울 수 있도록 하나의 정보 블록으로 압축
        context_block = "\n".join(aggregated_snippets)
        return context_block
