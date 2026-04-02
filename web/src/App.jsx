import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const Categories = [
  "전체", "패션의류", "패션잡화", "화장품/미용", "디지털/가전", 
  "가구/인테리어", "출산/육아", "식품", "스포츠/레저", "생활/건강"
];

function App() {
  const [keyword, setKeyword] = useState('');  // 사용자가 입력한 검색어 상태 변수
  const [category, setCategory] = useState('전체');  // 선택된 쇼핑 카테고리 상태 변수
  const [results, setResults] = useState([]);  // API로부터 받아온 상품 리스트 변수
  const [loading, setLoading] = useState(false);  // 데이터 수집 중인지 나타내는 상태 변수
  const [sortBy, setSortBy] = useState('rank');  // 현재 정렬 기준 (rank, views, sales 등)

  // 검색 버튼 클릭 시 백엔드 API를 호출하여 데이터를 확보합니다.
  const handleSearch = async () => {
    if (!keyword.trim()) return;
    setLoading(true);

    try {
      // 로컬 프록시 서버(server.js)에 검색어와 카테고리를 전달하여 결과 요청 (API 브리지 연계)
      const response = await axios.get(`http://localhost:5000/api/search`, {
        params: {
          keyword: keyword,
          category: category === '전체' ? '' : category
        }
      });
      setResults(response.data.items);  // 수집된 상품 리스트를 결과 상태에 저장
    } catch (error) {
      console.error("Search Fail:", error);
      alert("데이터를 가져오는 도중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  // 정렬 기준이 변경될 때마다 데이터를 정렬하여 상위 50위까지 표시합니다.
  const getSortedResults = () => {
    let sorted = [...results];
    
    // 선택된 필터 지표(조회수, 판매량 등)를 기준으로 내림차순 정렬 (데이터 필터링 연계)
    if (sortBy !== 'rank') {
      sorted.sort((a, b) => b[sortBy] - a[sortBy]);
    }
    
    return sorted.slice(0, 50);  // 1위부터 50위까지만 반환하여 랭킹 목록 구성
  };

  return (
    <div className="dashboard-container">
      {/* 프리미엄 헤더: 검색창 및 카테고리 드롭다운 레이아웃 */}
      <header className="premium-header">
        <h1>📊 Product Trend Explorer</h1>
        <div className="search-box">
          <select 
            value={category} 
            onChange={(e) => setCategory(e.target.value)}
            className="category-select"
          >
            {Categories.map(cat => <option key={cat} value={cat}>{cat}</option>)}
          </select>
          <input 
            type="text" 
            placeholder="검색어를 입력하세요..." 
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button onClick={handleSearch} disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </header>

      {/* 필터 바: 사용자의 요구사항에 따른 다중 정렬 기능 버튼 제공 */}
      <nav className="filter-bar">
        <label>Sort By:</label>
        <button className={sortBy === 'rank' ? 'active' : ''} onClick={() => setSortBy('rank')}>인기순</button>
        <button className={sortBy === 'views' ? 'active' : ''} onClick={() => setSortBy('views')}>조회수</button>
        <button className={sortBy === 'sales' ? 'active' : ''} onClick={() => setSortBy('sales')}>판매량</button>
        <button className={sortBy === 'review_count' ? 'active' : ''} onClick={() => setSortBy('review_count')}>리뷰수</button>
        <button className={sortBy === 'review_score' ? 'active' : ''} onClick={() => setSortBy('review_score')}>리뷰평점</button>
      </nav>

      <main className="ranking-table">
        {loading ? (
          <div className="loading-spinner">Analyzing Market Data...</div>
        ) : (
          <div className="grid-container">
            {getSortedResults().map((item, index) => (
              <div key={item.productId} className="product-card">
                <div className="rank-badge">#{index + 1}</div>
                <img src={item.image} alt={item.title} />
                <div className="product-info">
                  <h3 dangerouslySetInnerHTML={{ __html: item.title }} />
                  <p className="price">{parseInt(item.lprice).toLocaleString()}원</p>
                  <p className="mall">{item.mallName}</p>
                  <div className="stats">
                    <span>👁 {item.views.toLocaleString()}</span>
                    <span>🛒 {item.sales.toLocaleString()}</span>
                    <span>⭐ {item.review_score}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
