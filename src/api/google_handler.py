import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
from serpapi import GoogleSearch

class GoogleHandler:
    """
    사용자가 입력한 트렌드 키워드의 구글 검색 결과 상위 10개를 가져와
    제목(Title)과 설명(Snippet)만 추출하여 JSON 포맷으로 저장 및 반환하는 모듈.
    이 데이터는 이후 제미나이(Gemini) 모델에 주입되어 구글 맥락 파악의 뼈대가 됩니다.
    """
    def __init__(self):
        load_dotenv(".env")
        self.api_key = os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            print("🚨 [WARN] .env 파일에 'SERPAPI_API_KEY'가 설정되지 않았습니다. 구글 검색 연동을 위해 키를 입력해 주세요.")
            
    def fetch_google_search_json(self, keyword: str) -> str:
        if not self.api_key:
            return json.dumps([{"error": "SERPAPI_API_KEY missing - 구글 검색 키 누락"}], ensure_ascii=False)
            
        print(f"🔍 [Google Handler] '{keyword}'에 대한 구글 상위 10개 검색 결과를 추출하여 JSON으로 변환 중입니다...")
        
        params = {
            "engine": "google",
            "q": keyword, # 사용자가 입력한 트렌드 키워드 그대로 질의
            "hl": "ko",
            "gl": "kr",
            "num": 10,    # 검색 결과 상위 10개 추출
            "api_key": self.api_key
        }
        
        extracted_data = []
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            organic_results = results.get("organic_results", [])
            for item in organic_results:
                # 검색 결과에서 제목(Title)과 설명(Snippet)만 철저히 분리 추출
                extracted_data.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", "")
                })
        except Exception as e:
            print(f"☠️ [Google Handler Error] {str(e)}")
            return json.dumps([{"error": str(e)}], ensure_ascii=False)
            
        # Gemini가 쉽게 파싱할 수 있도록 엄격한 JSON 배열 포맷으로 변환하여 반환
        return json.dumps(extracted_data, ensure_ascii=False, indent=2)
