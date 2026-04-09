import os
import json
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
import google.generativeai as genai

# ==========================================
# 1. API 키 설정 (보안을 위해 GitHub 시스템 내부 비밀금고에서 불러옵니다)
# ==========================================
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 네이버 데이터랩 (검색 트렌드 분석용)
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

# ==========================================
# 2. ✨ 사용자 요청: "최근 3일 기준" 날짜 계산
# ==========================================
# 현재 시간 기준으로 정확히 3일(72시간) 전의 시간을 계산하여 유튜브에 전달할 형식(ISO 8601)으로 만듭니다.
time_limit = datetime.now(timezone.utc) - timedelta(days=3)
three_days_ago = time_limit.isoformat()

def get_latest_youtube_trends(keywords, max_results=15):
    print(f"🎬 유튜브에서 최근 3일 내('{three_days_ago}' 이후) 업로드된 '{keywords}' 관련 영상 수집 중...")
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    
    # 핵심 기능: publishedAfter 파라미터를 통해 최근 영상만 필터링합니다.
    request = youtube.search().list(
        part="snippet",
        q=keywords,
        type="video",
        order="viewCount",  # 조회수 높은 순
        publishedAfter=three_days_ago, 
        maxResults=max_results
    )
    response = request.execute()
    
    videos = []
    for item in response.get("items", []):
        videos.append({
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"],
            "video_id": item["id"]["videoId"],
            "url": f"https://youtube.com/watch?v={item['id']['videoId']}"
        })
    return videos

def summarize_with_ai(videos_data):
    print("🧠 AI가 수집된 유튜브 데이터에서 상업적 트렌드나 IT를 제외하고 F&B 트렌드만 식별하여 요약 중...")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    당신은 식음료 트렌드 분석 전문가입니다. 아래는 최근 3일 동안 유튜브에서 '유행, 오픈런, 신상' 키워드로 검색된 유튜브 영상들의 데이터입니다.
    이 데이터 속에서 **IT, 패션, 단순 브이로그 등 식음료(F&B)와 무관한 내용은 철저히 무시**하고, 
    오로지 **식음료(F&B), 맛집, 디저트, 편의점 신상품**과 관련된 최신 트렌드만 추출하여 아래의 JSON 형식으로만 응답하세요.
    단, 마크다운(```json) 기호 없이 순수 JSON 텍스트만 출력하세요.

    데이터:
    {json.dumps(videos_data, ensure_ascii=False)}

    출력형식 (JSON):
    {{
      "updated_at": "{datetime.now().strftime('%Y-%m-%d')}",
      "summary": "오늘의 전체 요약 한 줄",
      "trends": [
        {{
          "id": 1,
          "title": "트렌드 제목",
          "description": "구체적인 트렌드 설명 (어떤 영상들에서 주로 등장했는지 등)",
          "sentiment": "hot 또는 positive 또는 growing",
          "keywords": ["키워드1", "키워드2", "키워드3"],
          "source_video": "참조한 메인 비디오 링크 하나"
        }}
      ]
    }}
    """
    
    response = model.generate_content(prompt)
    return response.text

if __name__ == "__main__":
    if YOUTUBE_API_KEY == "여기에_유튜브_API_키를_넣으세요":
        print("❌ 동작 실패: 코드 상단(11, 12번째 줄)에 유튜브 API 키와 AI API 키를 먼저 입력해주세요!")
        exit(1)
        
    search_keywords = "편의점 신상 OR 디저트 오픈런 OR 먹방 유행템"
    
    try:
        recent_videos = get_latest_youtube_trends(search_keywords)
        ai_json_result = summarize_with_ai(recent_videos)
        
        # 앞서 만든 대시보드가 브라우저 보안 이슈 없이 읽을 수 있도록 data.js 형태로 저장합니다.
        js_content = f"const trendData = {ai_json_result.strip()};\n"
        
        with open("data.js", "w", encoding="utf-8") as f:
            f.write(js_content)
            
        print("✅ 성공! 대시보드의 data.js 파일이 오늘로부터 정확히 '최근 3일 이내' 트렌드로 업데이트 되었습니다.")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
