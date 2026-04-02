import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def get_top_keywords(category_id, category_name):
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    url = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json"
    }
    
    # 지연 반영을 고려해 3일 전 기준으로 조회 (2일 전도 400 에러 가능성 있음)
    target_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    body = {
        "startDate": target_date,
        "endDate": target_date,
        "timeUnit": "date",
        "category": category_id
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(body))
        if response.status_code == 200:
            data = response.json()
            # results[0]['data'] 리스트의 첫 번째 항목(당일 데이터)을 가져옴
            results = data.get('results', [])
            if results and results[0].get('data'):
                return [item['title'] for item in results[0]['data'][:10]]
            return ["No Data Found"]
        else:
            print(f"Error {response.status_code}: {response.text}")
            return [f"Error: {response.status_code}"]
    except Exception as e:
        return [f"Network Error: {e}"]

if __name__ == "__main__":
    categories = {
        "50000000": "패션의류",
        "50000003": "디지털/가전",
        "50000007": "스포츠/레저",
        "50000008": "생활/건강"
    }
    
    print(f"🛍️ [네이버 쇼핑 인기 검색어 - {datetime.now().strftime('%Y-%m-%d')} 기준]")
    for cat_id, cat_name in categories.items():
        results = get_top_keywords(cat_id, cat_name)
        print(f"\n[{cat_name}]:")
        print(", ".join(results))
