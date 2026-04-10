import os
import json
import traceback
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build

# 환경 변수 로드
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "").strip()
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "").strip() # 구글 맞춤검색용
GOOGLE_CX = os.environ.get("GOOGLE_CX", "").strip()         # 구글 맞춤검색 엔진 ID

# 시간 설정
time_limit = datetime.now(timezone.utc) - timedelta(days=3)
three_days_ago = time_limit.strftime('%Y-%m-%dT%H:%M:%SZ')
today_str = datetime.now().strftime('%Y-%m-%d')
one_month_ago_str = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')


def get_latest_youtube_trends(keywords, max_results=10):
    """YouTube에서 최신 F&B 트렌드 영상을 가져옵니다."""
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    request = youtube.search().list(
        part="snippet", q=keywords, type="video",
        order="viewCount", publishedAfter=three_days_ago, maxResults=max_results
    )
    response = request.execute()
    videos = []
    for item in response.get("items", []):
        videos.append({
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"][:200],
            "url": f"https://youtube.com/watch?v={item['id']['videoId']}"
        })
    return videos


def get_naver_blog_trends(keyword, max_results=10):
    """네이버 검색 API를 통해 블로그 '내돈내산/솔직후기' 반응을 수집합니다."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return []
    
    encText = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display={max_results}&sort=sim"
    
    req = urllib.request.Request(url, headers={
        'X-Naver-Client-Id': NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': NAVER_CLIENT_SECRET
    })
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return [{
                "title": item['title'].replace("<b>", "").replace("</b>", ""),
                "description": item['description'].replace("<b>", "").replace("</b>", ""),
                "link": item['link']
            } for item in result.get('items', [])]
    except Exception as e:
        print(f"  ⚠️ 네이버 블로그 검색 오류: {e}")
        return []


def get_community_trends(query, max_results=10):
    """Google Custom Search API를 통해 X, 더쿠, 인스티즈를 우회 검색합니다."""
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        return []
    
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        # dateRestrict="w1" -> 최근 1주일 데이터만 제한
        res = service.cse().list(
            q=query, cx=GOOGLE_CX, dateRestrict="w1", num=max_results
        ).execute()
        
        return [{
            "title": item.get('title', ''),
            "snippet": item.get('snippet', ''),
            "link": item.get('link', '')
        } for item in res.get("items", [])]
    except Exception as e:
        print(f"  ⚠️ 구글 커스텀 검색 오류: {e}")
        return []


def get_naver_trend(keyword):
    """네이버 데이터랩 API로 특정 키워드의 최근 1달 검색량 트렌드를 조회합니다."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return None
    url = "https://openapi.naver.com/v1/datalab/search"
    body = json.dumps({
        "startDate": one_month_ago_str,
        "endDate": today_str,
        "timeUnit": "week",
        "keywordGroups": [{"groupName": keyword, "keywords": [keyword]}]
    }).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': 'application/json',
        'X-Naver-Client-Id': NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': NAVER_CLIENT_SECRET
    })
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            ratios = [d['ratio'] for d in result['results'][0]['data']]
            is_rising = ratios[-1] > ratios[0] if len(ratios) >= 2 else True
            return {"ratios": ratios, "is_rising": is_rising}
    except Exception:
        return None


def summarize_with_ai(videos_data, blogs_data, community_data, max_retries=3):
    """Gemini 2.5 Flash로 다각적(유튜브/블로그/커뮤니티) 데이터를 분석하고 출처 간 교차 검증을 수행합니다."""
    import time
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
당신은 대한민국 F&B(식음료) 트렌드 전문 분석가입니다.
아래는 최근 수집된 유튜브, 네이버 블로그, 그리고 주요 커뮤니티(X, 더쿠, 인스티즈 등)의 데이터입니다.

[유튜브 데이터 (조회수 높은 핫한 영상)]
{json.dumps(videos_data, ensure_ascii=False)}

[네이버 블로그 데이터 (내돈내산/솔직후기 반응)]
{json.dumps(blogs_data, ensure_ascii=False)}

[커뮤니티 및 X(트위터) 실시간 반응]
{json.dumps(community_data, ensure_ascii=False)}

[분석 및 교차 검증 지시]
위 세 가지 데이터를 종합하여, 현재 한국 소비자들 사이에서 실제로 유행하거나 입소문을 타고 있는 구체적인 F&B 아이템 5개를 추출하세요.
특히, "단일 출처에서만 언급된 것"보다 **"여러 출처(예: 유튜브와 커뮤니티 모두)에서 공통으로 언급되는 찐 유행 아이템"**을 최우선으로 선정하세요.

중요:
- "디저트가 유행", "편의점 트렌드" 같은 모호한 양상 표현은 절대 금지.
- 반드시 실제 상품명, 메뉴명, 또는 브랜드명을 중심으로 작성할 것.
- sentiment 값은 "hot"(지금 난리남), "growing"(상승세), "new"(신상) 중 하나.
- mentioned_in 배열에는 해당 아이템이 언급된 출처를 "youtube", "naver_blog", "community" 중에서 찾아 모두 넣으세요. (최소 1개 이상, 가급적 2개 이상 교차 검증된 아이템 위주로 선정)

[출력 형식] 반드시 아래 JSON만 출력하고, 마크다운(```json 등)은 절대 붙이지 말 것:
{{"updated_at": "{today_str}", "summary": "한 문장으로 오늘의 F&B 트렌드 핵심 요약", "trends": [{{"id": 1, "title": "구체적인 상품명 또는 메뉴명", "description": "왜 화제인지, 사람들의 실제 반응은 어떤지 요약", "sentiment": "hot", "keywords": ["키워드1", "키워드2"], "mentioned_in": ["youtube", "community"], "source_link": "참고한 데이터 중 가장 대표적인 URL 하나"}}]}}
"""

    data = {"contents": [{"parts": [{"text": prompt}]}]}

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url, data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                if text.startswith('
