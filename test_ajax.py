import requests
import json
from datetime import datetime, timedelta

def get_realtime_shopping_rank(cid="50000000"):
    # 네이버 데이터랩 내부 AJAX 엔드포인트 시뮬레이션
    url = "https://datalab.naver.com/shoppingInsight/getCategoryKeywordRank.naver"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://datalab.naver.com/shoppingInsight/sCategory.naver",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # 최근 1주일간의 데이터 조회
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    payload = {
        "cid": cid,
        "timeUnit": "date",
        "startDate": start_date,
        "endDate": end_date,
        "device": "",
        "gender": "",
        "ages": "",
        "page": 1,
        "count": 20
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    result = get_realtime_shopping_rank()
    print(json.dumps(result, indent=4, ensure_ascii=False))
