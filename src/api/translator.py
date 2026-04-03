from deep_translator import GoogleTranslator
import urllib.parse
import re

def translate_ko_to_zh(text: str) -> str:
    """원본 한글 제목의 정보를 최대한 보존하며 중국어 간체(zh-CN)로 번역합니다."""
    if not text: return ""
    try:
        # 공백 정리 (연속된 공백 한 개로 통일)
        text = ' '.join(text.split())
        
        # GoogleTranslator에 zh-CN을 명시하여 간체자로 확실히 결과 유도
        # 정보 유실을 최소화하기 위해 원문 그대로를 전달
        translated = GoogleTranslator(source='ko', target='zh-CN').translate(text)
        
        if not translated: return text
        return translated
    except Exception as e:
        print(f"❌ [Translation Error] {e}")
        return text

def translate_ko_to_zh_batch(texts: list) -> list:
    """리스트 형태의 한국어 키워드들을 한 번에 번역합니다."""
    try:
        if not texts: return []
        translated_list = GoogleTranslator(source='ko', target='zh-CN').translate_batch(texts)
        return translated_list
    except Exception as e:
        print(f"❌ [Batch Translation Error] {e}")
        return texts

def get_1688_search_url(keyword: str) -> str:
    """중국어 키워드를 1688 서버 표준인 GBK로 인코딩하여 검색 URL을 생성합니다."""
    try:
        # 1688 검색은 전통적으로 GBK 인코딩에서 가장 정밀한 결과를 냅니다.
        encoded_kw = urllib.parse.quote(keyword, encoding='gbk')
    except (UnicodeEncodeError, LookupError):
        # GBK로 처리 불가한 특수문자 등이 있을 경우 UTF-8로 폴백
        encoded_kw = urllib.parse.quote(keyword)
        
    return f"https://s.1688.com/selloffer/offer_search.htm?keywords={encoded_kw}"

def get_1688_image_search_url(img_url: str) -> str:
    """이미지 URL을 기반으로 1688 이미지 검색 URL을 생성합니다."""
    encoded_img = urllib.parse.quote(img_url)
    return f"https://s.1688.com/youyuan/index.htm?tab=image&imageAddress={encoded_img}"

def get_taobao_search_url(keyword: str) -> str:
    """중국어 키워드를 인코딩하여 타오바오 검색 URL을 생성합니다."""
    encoded_kw = urllib.parse.quote(keyword)
    return f"https://s.taobao.com/search?q={encoded_kw}"

if __name__ == "__main__":
    # 고해상도 테스트 (정보 유실 방지 확인)
    test_kw = "차박 텐트"
    zh_kw = translate_ko_to_zh(test_kw)
    print(f"KO: {test_kw} -> ZH: {zh_kw} (간체 확인)")
    print(f"GBK URL: {get_1688_search_url(zh_kw)}")
