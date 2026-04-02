import os
import requests
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드하여 API 인증 정보를 준비함 (인증 관리 연계)
load_dotenv()

class NaverApiClient:
    """
    계획서(plan-agent.md) 1.2 섹션의 '공통 API 클라이언트' 구현체입니다.
    네이버 API와 통신하는 모든 하위 모듈이 이 클래스를 상속받아 사용합니다.
    """

    # 클래스 초기화 시 API ID와 Secret 정보를 환경 변수로부터 설정함
    # 이후 하위 클래스의 모든 요청에 공통으로 사용될 통신 레이어를 제공함
    def __init__(self) -> None:
        self.client_id: str = os.getenv("NAVER_CLIENT_ID", "")  # 네이버 개발자 센터에서 발급받은 클라이언트 ID 변수
        self.client_secret: str = os.getenv("NAVER_CLIENT_SECRET", "")  # 네이버 개발자 센터에서 발급받은 클라이언트 비밀키 변수
        
        # API 인증 및 컨텐츠 타입을 정의한 공통 헤더 (보안 인증 및 데이터 형식 연계)
        self.headers: Dict[str, str] = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "Content-Type": "application/json"
        }

    # HTTP 요청을 보내고 응답을 처리하는 공통 메서드이며, 재시도 로직을 내장함
    # 하위 API 모듈(ShoppingAPI, TrendAPI)의 구체적인 호출 로직과 연계되어 안정성을 보장함
    def _send_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        max_retries: int = 3  # 네트워크 지연이나 속도 제한 시 최대 재시도하는 횟수 변수
        
        for attempt in range(max_retries):
            try:
                # 지정된 메서드(GET/POST)로 URL에 요청을 보냄 (통신 라이브러리 연계)
                response = requests.request(method, url, headers=self.headers, **kwargs)
                
                # API 호출 빈도 제한(429) 발생 시 점진적으로 대기 시간을 늘려 재시도함
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # 대기 시간을 지수적으로 늘려주는 변수
                    print(f"API 한도 초합(429). {wait_time}초 후 다시 시도합니다.")
                    time.sleep(wait_time)
                    continue
                
                # 응답 코드가 200번대가 아닐 경우 예외를 발생시켜 에러 핸들링을 유도함
                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                # 네트워크 장애나 타임아웃 등의 오류를 캐치하여 로깅 처리함
                if hasattr(e, 'response') and e.response is not None:
                    print(f"❌ [API Error] HTTP {e.response.status_code}: {e.response.text}")
                else:
                    print(f"[{attempt + 1}/{max_retries}] API 요청 중 예외 발생: {e}")
                
                if attempt == max_retries - 1:
                    return None
                time.sleep(1)
        return None
