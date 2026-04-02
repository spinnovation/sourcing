"""
네이버 검색광고 API 연동 모듈
- 실제 월간 검색량 (PC / 모바일 분리)
- 연관 키워드 추천 (최대 100개)
- 경쟁 정도 및 예상 입찰가 (CPC)

공식 문서: https://naver.github.io/naver-ad-api
"""

import os
import time
import hmac
import hashlib
import base64
import requests
from typing import List, Dict, Any, Optional

# .env 자동 로드 (프로젝트 루트 기준 절대 경로)
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), "../../.env")
    load_dotenv(_env_path)
except ImportError:
    pass


class NaverAdAPI:
    """
    네이버 검색광고 API 클라이언트.
    HMAC-SHA256 서명 방식으로 인증합니다.
    """

    BASE_URL = "https://api.naver.com"

    def __init__(self):
        self.api_key     = os.environ.get("NAVER_AD_API_KEY", "").strip()
        self.secret_key  = os.environ.get("NAVER_AD_API_SECRET_KEY", "").strip()
        self.customer_id = os.environ.get("CUSTOMER_ID", "").strip()

        if not all([self.api_key, self.secret_key, self.customer_id]):
            print("⚠️ [NaverAdAPI] .env에 NAVER_AD_API_KEY / NAVER_AD_API_SECRET_KEY / CUSTOMER_ID 가 필요합니다.")
        else:
            print(f"✅ [NaverAdAPI] 인증 정보 로드 완료 (Customer: {self.customer_id})")

    # ── 인증 헤더 생성 (HMAC-SHA256) ─────────────────────────────────────
    def _make_headers(self, method: str, path: str) -> Dict[str, str]:
        """네이버 광고 API 규격의 HMAC-SHA256 서명 헤더를 생성합니다."""
        timestamp = str(int(time.time() * 1000))
        signature = self._sign(timestamp, method, path)
        return {
            "Content-Type":           "application/json; charset=UTF-8",
            "X-Timestamp":            timestamp,
            "X-API-KEY":              self.api_key,
            "X-Customer":             self.customer_id,
            "X-Signature":            signature,
        }

    def _sign(self, timestamp: str, method: str, path: str) -> str:
        message = f"{timestamp}.{method}.{path}"
        raw = hmac.new(
            self.secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(raw).decode("utf-8")

    # ── 핵심 API: 키워드 도구 ────────────────────────────────────────────
    def get_keyword_stats(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        키워드 목록의 월간 검색량 / PC·모바일 분리 / 경쟁도 / 예상 CPC를 조회합니다.

        Returns:
            [
              {
                "relKeyword": "캠핑 의자",
                "monthlyPcQcCnt":    1234,   # 월간 PC 검색수
                "monthlyMobileQcCnt": 8765,  # 월간 모바일 검색수
                "monthlyAvePcClkCnt":  56,   # 월평균 PC 클릭수
                "monthlyAveMobileClkCnt": 320,
                "monthlyAvePcCtr":    0.045, # PC 클릭률
                "monthlyAveMobileCtr": 0.036,
                "plAvgDepth":         15,    # 평균 노출 상품 수 (경쟁 강도 대리 지표)
                "compIdx": "중",              # 경쟁 정도: 낮음 / 중간 / 높음
              },
              ...
            ]
        """
        if not keywords:
            return []

        path = "/keywordstool"
        url  = self.BASE_URL + path

        # 네이버 광고 API는 한 번에 최대 100개 키워드 허용
        chunks = [keywords[i:i + 100] for i in range(0, len(keywords), 100)]
        results = []

        for chunk in chunks:
            # API 규격: hintKeywords는 쉼표 구분, 각 키워드는 공백 없는 단어
            params = {"hintKeywords": ",".join(chunk), "showDetail": "1"}
            try:
                resp = requests.get(
                    url,
                    headers=self._make_headers("GET", path),
                    params=params,
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results.extend(data.get("keywordList", []))
                else:
                    print(f"🚨 [NaverAdAPI] 키워드 도구 오류 {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                print(f"🚨 [NaverAdAPI] 요청 실패: {e}")

        return results

    def get_related_keywords(
        self,
        seed_keyword: str,
        hint_words: List[str] = None,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        씨드 키워드 + 힌트 단어들로 연관 키워드를 조회합니다.

        네이버 광고 키워드 도구는 hintKeywords에 넘긴 단어들의
        '변형/연관어'를 keywordList로 반환합니다.
        씨드 하나만 넘기면 결과가 적을 수 있으므로,
        hint_words(상품명 빈도 상위 단어)를 함께 넘겨 풀을 넓힙니다.
        """
        # 힌트 목록: 씨드 + 상위 빈도 단어 (최대 5개, 중복 제거)
        # ⚠️ 네이버 광고 API는 공백 포함 키워드를 hintKeywords로 받지 않음
        #    → 씨드 분리 + 단일 어절 단어만 힌트로 허용
        seed_parts = [p for p in seed_keyword.split() if len(p) >= 2]  # "휴대폰 거치대" → ["휴대폰", "거치대"]
        hints = list(dict.fromkeys(seed_parts))[:3]   # 씨드 단어 최대 3개
        if hint_words:
            for w in hint_words:
                # 공백 없는 단일 어절만 허용
                if w and ' ' not in w and w not in hints and len(hints) < 6:
                    hints.append(w)
        if not hints:
            hints = [seed_keyword]

        print(f"   └ 힌트 키워드: {hints}")
        raw = self.get_keyword_stats(hints)
        if not raw:
            return []

        # 검색량 합산 및 정렬
        seen = set()
        enriched = []
        for item in raw:
            kw = item.get("relKeyword", "")
            if kw in seen:
                continue
            seen.add(kw)
            pc  = item.get("monthlyPcQcCnt", 0)
            mob = item.get("monthlyMobileQcCnt", 0)
            item["totalQcCnt"] = _safe_int(pc) + _safe_int(mob)
            enriched.append(item)

        enriched.sort(key=lambda x: x["totalQcCnt"], reverse=True)
        return enriched[:top_k]


def _safe_int(val) -> int:
    """'<10' 같은 문자열도 int 0으로 안전하게 변환합니다."""
    try:
        return int(str(val).replace("<", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return 0
