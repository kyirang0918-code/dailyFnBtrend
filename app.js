document.addEventListener('DOMContentLoaded', () => {
    try {
        // 브라우저 로컬 보안 차단을 피하기 위해 fetch() 대신 HTML에 포함된 trendData 변수를 직접 사용합니다.
        const data = trendData;
        
        // 날짜와 전체 요약 텍스트 업데이트
        document.getElementById('update-date').textContent = data.updated_at;
        document.getElementById('summary-text').textContent = data.summary;
        
        const grid = document.getElementById('trends-grid');
        grid.innerHTML = ''; // 렌더링 영역 초기화
        
        // 트렌드 배열을 반복하며 카드(Card) UI를 생성합니다.
        data.trends.forEach((trend, index) => {
            const card = document.createElement('div');
            card.className = `trend-card card-${index + 1}`;
            
            // 키워드 태그 생성
            const keywordsHTML = trend.keywords.map(kw => `<span class="keyword">#${kw}</span>`).join('');
            
            card.innerHTML = `
                <div class="trend-number">${index + 1}</div>
                <div class="card-content">
                    <div class="trend-header">
                        <span class="sentiment ${trend.sentiment}">${trend.sentiment}</span>
                    </div>
                    <h3 class="trend-title">${trend.title}</h3>
                    <p class="trend-desc">${trend.description}</p>
                    <div class="keywords">
                        ${keywordsHTML}
                    </div>
                    <a href="${trend.source_video}" target="_blank" class="source-btn">유튜브에서 검색 결과 확인</a>
                </div>
            `;
            
            grid.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading trend data:', error);
        document.getElementById('summary-text').textContent = "트렌드 데이터를 불러오는 데 실패했습니다.";
    }
});
