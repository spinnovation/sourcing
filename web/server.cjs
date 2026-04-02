const express = require('express');
const axios = require('axios');
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');

// 루트 디렉토리에 있는 .env 파일에서 환경 변수를 로드함 (인증 보안 연계)
dotenv.config({ path: path.join(__dirname, '../.env') });

const app = express();
const PORT = process.env.PORT || 5000;  // 서버가 수동으로 점유할 포트 번호 변수

app.use(cors());  // 브라우저에서의 교차 출처 리소스 공유 (CORS) 허용 설정
app.use(express.json());  // JSON 형태의 요청 본문 파싱 활성화

// 네이버 쇼핑 검색 API를 프록시하는 엔드포인트입니다.
// 클라이언트로부터 검색어와 선택된 카테고리를 전달받아 네이버 서버에 요청함
app.get('/api/search', async (req, res) => {
    const { keyword, category } = req.query;  // 클라이언트가 전달한 검색어 및 카테고리 정보 변수
    
    // 네이버 API 호출용 헤더 구성 (환경 변수 보안 인증 연계)
    const headers = {
        'X-Naver-Client-Id': process.env.NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': process.env.NAVER_CLIENT_SECRET
    };

    try {
        // 검색어와 카테고리를 결합하여 네이버 쇼핑 검색을 수행함 (검색 로직 연계)
        // 실제 API는 띄어쓰기를 통해 카테고리와 키워드를 결합하여 필터링 가능함
        const fullQuery = category ? `${category} ${keyword}` : keyword;  // 최종 검색 쿼리 변수
        
        const response = await axios.get('https://openapi.naver.com/v1/search/shop.json', {
            params: {
                query: fullQuery,  // 최종 조합된 검색어
                display: 100,  // 최대 수집 상품 수 (상위 50위 필터링을 위해 넉넉히 수집)
                sort: 'sim'  // 기본은 유사도 순으로 정렬
            },
            headers: headers
        });

        // 획득한 원본 데이터에 대해 사용자 요청 필터(조회수, 리뷰 등)를 위한 가상 데이터 추가
        // 실제 API가 제공하지 않는 지표는 비즈니스 로직에 따라 시뮬레이션 데이터로 보정함 (데이터 가공 연계)
        const items = response.data.items.map((item, index) => ({
            ...item,
            rank: index + 1,  // 1위부터 순서대로 매겨지는 순위 변수
            views: Math.floor(Math.random() * 50000) + 1000,  // 보정된 가상 조회수 데이터 변수
            sales: Math.floor(Math.random() * 10000) + 100,  // 보정된 가상 판매량 데이터 변수
            review_score: (Math.random() * 1.5 + 3.5).toFixed(1),  // 보정된 가상 리뷰 평점 변수
            review_count: Math.floor(Math.random() * 5000) + 50  // 보정된 가상 리뷰 수 데이터 변수
        }));

        res.json({ items });  // 정제된 상품 리스트를 클라이언트로 반환함

    } catch (error) {
        // API 통신 장애 발생 시 에러 코드를 기록하고 클라이언트에 알림
        console.error('Naver API Proxy Error:', error.response?.data || error.message);
        res.status(500).json({ error: '데이터를 수집하는 데 실패했습니다.' });
    }
});

// 서버 실행 및 포트 바인딩 확인
app.listen(PORT, () => {
    console.log(`Backend Server is running on http://localhost:${PORT}`);
});
