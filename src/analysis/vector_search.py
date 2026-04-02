import numpy as np
import traceback
from typing import List, Dict, Any, Tuple

# sentence-transformers를 활용한 한국어 특화 벡터화 (NLP 엔진 연계)
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    SentenceTransformer = None
    cosine_similarity = None

class VectorSearch:
    """
    수집된 텍스트 데이터를 Sentence-Transformer로 벡터화하고, 
    트렌드 키워드와의 코사인 유사도를 기반으로 의미적으로 연관된(Semantic) 상품을 발굴합니다.
    """
    
    def __init__(self, model_name: str = "snunlp/KR-SBERT-V40K-klueNLI-augSTS") -> None:
        self.model_name = model_name
        self.model = None
        self.is_loaded = False
        
        # 모델 사전 로드 시도
        self._load_model()

    def _load_model(self) -> None:
        try:
            if SentenceTransformer is None:
                print("[VectorSearch] 라이브러리(sentence-transformers)가 설치되지 않았습니다. AI 검색 기능을 비활성 상태로 유지합니다.")
                return

            print(f"[VectorSearch] 로컬 AI 모델({self.model_name}) 로딩 중... (처음엔 다운로드 시간이 소요될 수 있습니다)")
            self.model = SentenceTransformer(self.model_name)
            self.is_loaded = True
            print("[VectorSearch] 모델 로딩 완료!")
        except Exception as e:
            print(f"[VectorSearch] 모델 로딩 실패, 환경을 확인하세요: {str(e)}")
            traceback.print_exc()

    def find_hidden_recommendations(self, keyword: str, items: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        주어진 트렌드 키워드를 기준으로 유사도가 높은 추천 상품(top_k)를 반환합니다.
        - sentence-transformers 설치 시: 코사인 유사도 (고정밀)
        - 미설치 시: Jaccard + 가중 키워드 매칭 (Fallback, 라이브러리 불필요)
        """
        if not items:
            return []

        product_titles = [item.get('title', '').replace("<b>", "").replace("</b>", "") for item in items]

        # ── Case 1: sentence-transformers 사용 가능 (고정밀 코사인 유사도) ──
        if self.is_loaded and self.model is not None:
            try:
                keyword_embedding = self.model.encode([keyword])
                product_embeddings = self.model.encode(product_titles)
                similarities = cosine_similarity(keyword_embedding, product_embeddings)[0]

                scored_items = []
                for item, sim, title in zip(items, similarities, product_titles):
                    cloned_item = dict(item)
                    cloned_item['semantic_similarity'] = float(sim)
                    cloned_item['clean_title'] = title
                    scored_items.append(cloned_item)

                scored_items.sort(key=lambda x: x['semantic_similarity'], reverse=True)
                return scored_items[:top_k]
            except Exception as e:
                print(f"[VectorSearch] 코사인 유사도 계산 실패, Fallback으로 전환: {e}")

        # ── Case 2: Fallback — Jaccard + 가중 키워드 매칭 ──
        print("[VectorSearch] Fallback 모드: Jaccard 유사도 기반 키워드 매칭 사용")
        import re

        # 기준 키워드 집합 생성 (쉼표/공백으로 분리된 복합 키워드 처리)
        ref_words = set(re.findall(r'[가-힣a-zA-Z0-9]{2,}', keyword.lower()))

        scored_items = []
        for item, title in zip(items, product_titles):
            title_words = set(re.findall(r'[가-힣a-zA-Z0-9]{2,}', title.lower()))

            # Jaccard 유사도: 교집합 / 합집합
            if not ref_words or not title_words:
                score = 0.0
            else:
                intersection = len(ref_words & title_words)
                union = len(ref_words | title_words)
                jaccard = intersection / union

                # 가중치: 기준 키워드 중 몇 개나 포함되어 있는지 (포함율)
                coverage = intersection / len(ref_words) if ref_words else 0.0

                # 최종 점수 = Jaccard(50%) + Coverage(50%)
                score = (jaccard * 0.5) + (coverage * 0.5)

            cloned_item = dict(item)
            cloned_item['semantic_similarity'] = round(score, 4)
            cloned_item['clean_title'] = title
            scored_items.append(cloned_item)

        scored_items.sort(key=lambda x: x['semantic_similarity'], reverse=True)
        print(f"[VectorSearch] Fallback 완료: 상위 {top_k}개 추출 (최고점: {scored_items[0]['semantic_similarity'] if scored_items else 0:.2%})")
        return scored_items[:top_k]
