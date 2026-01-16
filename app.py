import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import feedparser
from datetime import datetime
from urllib.parse import quote
import sqlite3
from pathlib import Path
import re
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from playwright.sync_api import sync_playwright

# 환경변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="뉴스 검색 챗봇",
    page_icon="🤖",
    layout="wide"
)

# ==================== DATABASE 초기화 ====================
DB_PATH = Path("articles.db")

def init_database():
    """데이터베이스 초기화"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 기사 저장 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            keyword TEXT,
            published TEXT,
            summary TEXT,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 검색 히스토리 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            article_count INTEGER,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# 데이터베이스 초기화
init_database()

def save_article(title, link, keyword, published, summary=""):
    """기사를 데이터베이스에 저장"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR IGNORE INTO articles 
            (title, link, keyword, published, summary) 
            VALUES (?, ?, ?, ?, ?)
        ''', (title, link, keyword, published, summary))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"기사 저장 중 오류: {str(e)}")
        return False

def get_saved_articles(keyword=None, limit=10):
    """저장된 기사 조회"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        if keyword:
            c.execute('''
                SELECT title, link, keyword, published, saved_at 
                FROM articles 
                WHERE keyword = ? 
                ORDER BY saved_at DESC 
                LIMIT ?
            ''', (keyword, limit))
        else:
            c.execute('''
                SELECT title, link, keyword, published, saved_at 
                FROM articles 
                ORDER BY saved_at DESC 
                LIMIT ?
            ''', (limit,))
        
        articles = c.fetchall()
        conn.close()
        return articles
    except Exception as e:
        st.error(f"기사 조회 중 오류: {str(e)}")
        return []

def get_search_history(limit=5):
    """검색 히스토리 조회"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            SELECT keyword, article_count, searched_at 
            FROM search_history 
            ORDER BY searched_at DESC 
            LIMIT ?
        ''', (limit,))
        
        history = c.fetchall()
        conn.close()
        return history
    except Exception as e:
        return []

def save_search_history(keyword, article_count):
    """검색 히스토리 저장"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO search_history (keyword, article_count) 
            VALUES (?, ?)
        ''', (keyword, article_count))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def delete_article(link):
    """기사 삭제"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('DELETE FROM articles WHERE link = ?', (link,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def clear_all_articles():
    """모든 기사 삭제"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('DELETE FROM articles')
        c.execute('DELETE FROM search_history')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

# ==================== 정시 기사 수집 스케줄러 ====================

# 전역 스케줄러 초기화
scheduler = None

def auto_collect_news():
    """자동 기사 수집 함수"""
    try:
        # 기본 검색 키워드 목록
        default_keywords = ['AI', '기술', '경제', '정치', '스포츠']
        
        for keyword in default_keywords:
            articles = fetch_google_news(keyword, max_results=3)
            if articles:
                for article in articles:
                    save_article(
                        title=article['title'],
                        link=article['link'],
                        keyword=keyword,
                        published=article['published'],
                        summary=article.get('summary', '')
                    )
        
        # 수집 완료 로그
        with open("collection_log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 자동 기사 수집 완료\n")
        
        return True
    except Exception as e:
        with open("collection_log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 오류: {str(e)}\n")
        return False

def init_scheduler():
    """스케줄러 초기화"""
    global scheduler
    
    # 이미 실행 중인 스케줄러가 있으면 중지
    if scheduler and scheduler.running:
        return scheduler
    
    # 새로운 스케줄러 생성
    scheduler = BackgroundScheduler(daemon=True, timezone=pytz.timezone('Asia/Seoul'))
    
    # 매일 오전 9시, 오후 3시, 오후 9시에 기사 수집
    scheduler.add_job(
        auto_collect_news,
        CronTrigger(hour='9,15,21', minute=0, second=0),
        id='auto_collect_news',
        name='자동 기사 수집',
        replace_existing=True
    )
    
    # 스케줄러 시작
    scheduler.start()
    
    return scheduler

# 페이지 시작 시 스케줄러 초기화
try:
    init_scheduler()
except Exception as e:
    pass  # 이미 초기화된 경우 무시

# ==================== GMS 클라이언트 초기화 ====================
@st.cache_resource
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("❌ API Key를 찾을 수 없습니다. .env 파일을 확인하세요.")
        st.stop()
    
    return OpenAI(
        base_url='https://gms.ssafy.io/gmsapi/api.openai.com/v1',
        api_key=api_key
    )

client = get_openai_client()

# 세션 상태 초기화 (대화 히스토리 저장용)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 기사 검색 의도 판단 함수
def check_news_search_intent(user_input):
    """
    사용자 입력이 기사 검색 요청인지 판단하는 함수
    
    Args:
        user_input: 사용자 입력 텍스트
        
    Returns:
        bool: True(기사 검색 요청) / False(일반 대화)
    """
    # 키워드 기반 간단 판단
    news_keywords = ['뉴스', '기사', '소식', '보도', '언론', '신문', '최신', '최근']
    
    user_lower = user_input.lower()
    
    # 뉴스 관련 키워드가 포함되어 있으면 기사 검색으로 판단
    for keyword in news_keywords:
        if keyword in user_lower:
            if "intent_log" not in st.session_state:
                st.session_state.intent_log = []
            st.session_state.intent_log.append({
                "input": user_input,
                "result": "YES (키워드 매칭)",
                "is_search": True
            })
            return True
    
    # 키워드가 없으면 일반 대화
    if "intent_log" not in st.session_state:
        st.session_state.intent_log = []
    st.session_state.intent_log.append({
        "input": user_input,
        "result": "NO (키워드 없음)",
        "is_search": False
    })
    return False

# 검색 키워드 추출 함수
def extract_search_keyword(user_input):
    """
    사용자 입력에서 검색 키워드를 추출하는 함수
    
    Args:
        user_input: 사용자 입력 텍스트
        
    Returns:
        str: 추출된 검색 키워드
    """
    # 불필요한 단어/조사/종결어 제거
    remove_words = [
        # 동사/조동사
        '알려줘', '알려주세요', '찾아줘', '검색해줘', '보여줘', '해줄래', '해주세요',
        # 명사 (뉴스 관련)
        '기사', '뉴스', '소식', '보도', '속보', '긴급',
        # 조사
        '을', '를', '이', '가', '은', '는', '에', '서', '에게', '께', '로', '에서', '로부터', '에 대한', '의',
        # 한국어 종결어미 및 의존명사
        '거', '거지', '거가', '거네', '거라', '거야', '것', '네', '네요', '네길',
        '고', '곤', '고야', '고말', '고들', '고곤', '일', '해', '해요',
        # 시간 표현
        '오늘', '어제', '요즘', '지금', '현재', '최신', '최근',
        # 형용사
        '많은', '인기', '인기있는', '인기많은',
        # 인사말
        '안녕', '안녕하세요', '반가워', '반갑습니다', '만나서',
        # 기타
        '아', '어', '음', '어떻게', '어떤', '뭔지', '뭐야', '뭐지', '뭘', '뭐냐',
        '서치', '조회', '검색', '찾기', '말해줘', '설명해줘', '안내', '정보',
        '나', '날', '너', '우리', '우리가'
    ]
    
    # 1단계: 텍스트 정규화
    keyword = user_input.strip()
    
    # 2단계: 불필요한 단어 제거 (가장 긴 단어부터 처리)
    for word in sorted(remove_words, key=len, reverse=True):
        keyword = re.sub(rf'\b{re.escape(word)}\b', ' ', keyword, flags=re.IGNORECASE)
    
    # 3단계: 특수문자 제거 (한글, 영문, 숫자만 유지)
    keyword = re.sub(r'[^가-힣a-zA-Z0-9\s]', '', keyword)
    
    # 4단계: 연속된 공백 정리
    keyword = ' '.join(keyword.split()).strip()
    
    # 5단계: 최종 검증
    if len(keyword) < 2:
        # 키워드가 너무 짧으면 원본 중 가장 긴 단어 찾기
        original_words = user_input.split()
        filtered_words = [w for w in original_words if len(w) >= 2 and w not in remove_words]
        if filtered_words:
            keyword = filtered_words[0]  # 가장 먼저 나온 주요 단어 선택
        else:
            keyword = user_input
    
    return keyword

# Google News RSS 기사 수집 함수
def fetch_google_news(keyword, max_results=5):
    """
    Google News RSS를 통해 기사를 수집하는 함수
    
    Args:
        keyword: 검색 키워드
        max_results: 최대 수집 기사 수
        
    Returns:
        list: 기사 정보 리스트
    """
    try:
        # Google News RSS URL 생성
        encoded_keyword = quote(keyword)
        rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
        
        # RSS 파싱
        feed = feedparser.parse(rss_url)
        
        articles = []
        for entry in feed.entries[:max_results]:
            article = {
                'title': entry.title,
                'link': entry.link,
                'published': entry.published if 'published' in entry else '날짜 정보 없음',
                'summary': entry.summary if 'summary' in entry else ''
            }
            articles.append(article)
        
        return articles
        
    except Exception as e:
        st.error(f"기사 수집 중 오류 발생: {str(e)}")
        return []

# Playwright를 사용한 크롤링 함수
def fetch_articles_with_playwright(keyword, max_results=5):
    """
    Playwright를 사용하여 동적 웹사이트에서 기사를 크롤링하는 함수
    
    Args:
        keyword: 검색 키워드
        max_results: 최대 수집 기사 수
        
    Returns:
        list: 기사 정보 리스트
    """
    try:
        articles = []
        
        with sync_playwright() as p:
            # Chrome 브라우저 실행
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 네이버 뉴스 검색
            search_url = f"https://search.naver.com/search.naver?where=news&sm=tab_jum&query={quote(keyword)}"
            page.goto(search_url, wait_until="load")
            
            # 뉴스 항목 수집
            news_items = page.query_selector_all("div.news_area")
            
            for item in news_items[:max_results]:
                try:
                    # 제목과 링크 추출
                    title_elem = item.query_selector("a.news_tit")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_attribute("title")
                    link = title_elem.get_attribute("href")
                    
                    # 요약 및 날짜 추출
                    text_elem = item.query_selector("div.news_dsc")
                    summary = text_elem.inner_text() if text_elem else ""
                    
                    date_elem = item.query_selector("span.info")
                    published = date_elem.inner_text() if date_elem else "날짜 정보 없음"
                    
                    if title and link:
                        articles.append({
                            'title': title,
                            'link': link,
                            'published': published,
                            'summary': summary,
                            'source': 'Playwright (Naver News)'
                        })
                
                except Exception as e:
                    continue
            
            browser.close()
        
        return articles
        
    except Exception as e:
        st.warning(f"Playwright 크롤링 중 오류: {str(e)}")
        return []

# 기사 요약 함수
def summarize_articles(articles, user_query):
    """
    수집된 기사들을 GPT로 요약하는 함수
    
    Args:
        articles: 기사 리스트
        user_query: 사용자 원본 질문
        
    Returns:
        str: 요약된 기사 정보
    """
    if not articles:
        return "❌ 검색 결과가 없습니다. 다른 키워드로 시도해주세요."
    
    # 기사를 데이터베이스에 저장
    keyword = extract_search_keyword(user_query)
    for article in articles:
        save_article(
            title=article['title'],
            link=article['link'],
            keyword=keyword,
            published=article['published'],
            summary=article.get('summary', '')
        )
    
    # 검색 히스토리 저장
    save_search_history(keyword, len(articles))
    
    # 기사 정보를 텍스트로 변환
    articles_text = ""
    for idx, article in enumerate(articles, 1):
        articles_text += f"\n\n[기사 {idx}]\n"
        articles_text += f"제목: {article['title']}\n"
        articles_text += f"링크: {article['link']}\n"
        articles_text += f"발행: {article['published']}\n"
    
    try:
        # GPT에게 요약 요청
        response = client.chat.completions.create(
            model='gpt-5-nano',
            messages=[
                {
                    "role": "system",
                    "content": """당신은 뉴스 기사를 요약하고 분석하는 전문가입니다.
사용자가 요청한 주제에 대한 기사들을 읽기 쉽고 자세하게 요약해주세요.

요약 시 다음 형식을 따르세요:
1. 전체 트렌드 및 시황 요약 (여러 줄)
2. 각 기사별 핵심 내용 (제목과 함께 자세히)
3. 기사 링크 제공
4. 주요 포인트 및 통찰

자세하고 정보 전달에 집중해주세요. 불릿 포인트를 활용해주세요."""
                },
                {
                    "role": "user",
                    "content": f"사용자 질문: {user_query}\n\n수집된 기사 정보:\n{articles_text}\n\n위 기사들을 자세하고 읽기 쉽게 요약해주세요."
                }
            ],
            max_completion_tokens=4096
        )
        
        summary = response.choices[0].message.content
        return summary
        
    except Exception as e:
        # GPT 요약 실패 시 기본 포맷으로 표시
        result = f"📰 **'{user_query}' 관련 기사 {len(articles)}건**\n\n"
        
        for idx, article in enumerate(articles, 1):
            result += f"**[{idx}] {article['title']}**\n"
            result += f"🔗 {article['link']}\n"
            result += f"📅 {article['published']}\n\n"
        
        result += f"\n⚠️ AI 요약 생성 실패: {str(e)}\n위 기사 링크를 클릭하여 자세한 내용을 확인하세요."
        
        return result

# 일반 챗봇 응답 생성 함수
def generate_chat_response(messages):
    """
    일반 대화 응답을 생성하는 함수
    
    Args:
        messages: 대화 히스토리
        
    Returns:
        str: GPT 응답 텍스트
    """
    try:
        response = client.chat.completions.create(
            model='gpt-5-nano',
            messages=[
                {
                    "role": "system", 
                    "content": """당신은 친절하고 도움이 되는 AI 어시스턴트입니다. 
사용자의 질문에 자세하고 정확하게 답변해주세요. 
필요하면 여러 가지 예시도 제공하고, 여러 문단으로 깊이 있게 설명해주세요.
최소 3-5 문단 이상으로 자세한 설명을 제공하세요.
사용자가 간단한 인사말을 하면, 친근하게 인사하면서 대화를 시작하세요.
"""
                },
                *messages
            ],
            max_completion_tokens=4096
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ 응답 생성 중 오류가 발생했습니다: {str(e)}"

# 기사 검색 처리 함수 (Phase 3 완성)
def search_news(user_input):
    """
    기사 검색을 처리하는 함수
    
    Args:
        user_input: 사용자 입력 텍스트
        
    Returns:
        str: 기사 검색 결과
    """
    # 1단계: 검색 키워드 추출
    keyword = extract_search_keyword(user_input)
    
    # 2단계: Google News에서 기사 수집
    articles = fetch_google_news(keyword, max_results=5)
    
    # 3단계: RSS 결과가 없으면 Playwright로 크롤링 시도
    if not articles:
        with st.spinner("⏳ 다른 소스에서 기사를 검색 중..."):
            articles = fetch_articles_with_playwright(keyword, max_results=5)
    
    # 4단계: 여전히 기사가 없으면 다른 키워드로 시도
    if not articles and len(keyword) > 2:
        # 원본 입력에서 뉴스 관련 키워드만 추출해서 다시 시도
        alternative_keywords = user_input.split()
        for alt_keyword in alternative_keywords:
            if len(alt_keyword) >= 2:
                articles = fetch_google_news(alt_keyword, max_results=5)
                if articles:
                    keyword = alt_keyword
                    break
    
    # 5단계: 여전히 기사가 없으면 안내 메시지
    if not articles:
        # GPT에게 관련 정보 제공 요청
        try:
            response = client.chat.completions.create(
                model='gpt-5-nano',
                messages=[
                    {
                        "role": "system",
                        "content": "사용자가 찾는 주제에 대해 현재 알고 있는 정보를 제공해주세요. 최근 뉴스나 트렌드 정보가 있다면 공유해주세요."
                    },
                    {
                        "role": "user",
                        "content": f"'{keyword}' 관련 최근 뉴스나 정보를 알려줄 수 있나요? 구글 뉴스에서 찾을 수 없어서 현재 알고 있는 정보를 공유해주세요."
                    }
                ],
                max_completion_tokens=2048
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ '{keyword}' 관련 기사를 찾을 수 없습니다.\\n\\n💡 다른 키워드로 다시 시도하거나, 일반 질문으로 물어봐주세요."
    
    # 6단계: GPT로 기사 요약
    summary = summarize_articles(articles, user_input)
    
    return summary

# 제목
st.title("🤖 뉴스 검색 챗봇")
st.caption("일반 대화와 기사 검색이 가능한 AI 챗봇입니다.")

# 사이드바 (옵션)
with st.sidebar:
    st.header("⚙️ 설정")
    st.write("**모델:** gpt-5-nano")
    st.write("**기능:** 일반 대화 + 기사 검색")
    
    # 대화 개수 표시
    st.write(f"**대화 개수:** {len(st.session_state.messages)}개")
    
    # 기능 상태 표시
    st.divider()
    st.write("**구현 상태:**")
    st.write("✅ 기본 챗봇")
    st.write("✅ 의도 판단 (키워드 방식)")
    st.write("✅ 기사 검색 (Google News RSS)")
    st.write("✅ AI 기사 요약")
    st.write("✅ 기사 저장 (SQLite)")
    st.write("✅ Playwright 크롤링 (네이버 뉴스)")
    
    # 의도 판단 디버깅 정보
    if "intent_log" in st.session_state and len(st.session_state.intent_log) > 0:
        st.divider()
        st.write("**🔍 의도 판단 로그 (최근 5개):**")
        for log in st.session_state.intent_log[-5:]:
            icon = "📰" if log["is_search"] else "💬"
            result_text = "기사검색" if log["is_search"] else "일반대화"
            st.text(f"{icon} '{log['input'][:25]}...'")
            st.caption(f"→ {result_text}")
    
    # ==================== 저장된 기사 관리 ====================
    st.divider()
    st.write("**📚 저장된 기사 관리:**")
    
    # 검색 히스토리
    history = get_search_history(limit=5)
    if history:
        st.write("**검색 히스토리:**")
        for keyword, count, timestamp in history:
            st.caption(f"🔎 {keyword} ({count}건) - {timestamp[:10]}")
    
    # 저장된 기사 통계
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM articles')
        total_articles = c.fetchone()[0]
        conn.close()
        st.metric("💾 저장된 기사", f"{total_articles}건")
    except:
        pass
    
    # DB 관리 버튼
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📖 기사 조회"):
            st.session_state.show_saved_articles = True
    
    with col2:
        if st.button("🗑️ 초기화"):
            if st.button("정말 삭제할까요?", key="confirm_delete"):
                clear_all_articles()
                st.session_state.messages = []
                st.session_state.intent_log = []
                st.success("✅ 모든 데이터가 초기화되었습니다!")
                st.rerun()
    
    # ==================== 정시 기사 수집 설정 ====================
    st.divider()
    st.write("**⏰ 정시 기사 수집 설정:**")
    
    # 스케줄러 상태 표시
    if scheduler and scheduler.running:
        st.success("✅ 자동 기사 수집 중 (매일 9시, 15시, 21시)")
    else:
        st.warning("⚠️ 자동 기사 수집 비활성화")
    
    # 수집 로그 표시
    if Path("collection_log.txt").exists():
        with open("collection_log.txt", "r", encoding="utf-8") as f:
            logs = f.readlines()[-5:]  # 최근 5개
        if logs:
            st.write("**최근 수집 로그:**")
            for log in logs:
                st.caption(log.strip())
    
    # 수동 수집 버튼
    if st.button("🔄 지금 바로 수집"):
        with st.spinner("기사 수집 중..."):
            if auto_collect_news():
                st.success("✅ 기사 수집 완료!")
                st.rerun()
            else:
                st.error("❌ 기사 수집 실패")
    
    # 기본 수집 키워드 설정
    st.write("**기본 수집 키워드:**")
    st.caption("매일 정시에 수집할 뉴스 키워드: AI, 기술, 경제, 정치, 스포츠")
    
    # ==================== Playwright 크롤링 설정 ====================
    st.divider()
    st.write("**🌐 Playwright 크롤링:**")
    st.caption("RSS에서 기사를 찾지 못할 때 자동으로 웹사이트에서 크롤링")
    st.write("📊 지원: 네이버 뉴스 (동적 검색)")
    
    st.divider()
    if st.button("🗑️ 대화 내역만 초기화"):
        st.session_state.messages = []
        st.session_state.intent_log = []
        st.success("✅ 대화 내역이 초기화되었습니다!")
        st.rerun()

# 대화 내역이 없을 때 안내 메시지
if len(st.session_state.messages) == 0:
    st.info("👋 안녕하세요! 일반 대화나 기사 검색을 요청해보세요.\n\n**예시:**\n- 일반 대화: '안녕하세요', '파이썬 설명해줘', '오늘 날씨 어때?'\n- 기사 검색: '최신 AI 뉴스', '삼성전자 기사', '오늘 뉴스 알려줘'")

# 대화 내역 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==================== 저장된 기사 표시 ====================
if st.session_state.get("show_saved_articles", False):
    st.divider()
    st.header("📚 저장된 기사 조회")
    
    # 탭: 전체 기사 / 키워드별 검색
    tab1, tab2 = st.tabs(["전체 기사", "키워드 검색"])
    
    with tab1:
        articles = get_saved_articles(limit=50)
        if articles:
            st.success(f"✅ 저장된 기사: {len(articles)}건")
            
            # 테이블 형식으로 표시
            for idx, (title, link, keyword, published, saved_at) in enumerate(articles, 1):
                with st.container(border=True):
                    col1, col2 = st.columns([0.9, 0.1])
                    
                    with col1:
                        st.markdown(f"**[{title}]({link})**")
                        st.caption(f"🔑 키워드: {keyword} | 📅 발행: {published} | 💾 저장: {saved_at[:10]}")
                    
                    with col2:
                        if st.button("❌", key=f"delete_{idx}_{link}", help="삭제"):
                            delete_article(link)
                            st.success("삭제되었습니다!")
                            st.rerun()
        else:
            st.info("💡 저장된 기사가 없습니다. 기사를 검색해서 저장해보세요!")
    
    with tab2:
        keyword_search = st.text_input("검색할 키워드를 입력하세요:", placeholder="예: 삼성, AI, 정치")
        if keyword_search:
            articles = get_saved_articles(keyword=keyword_search, limit=50)
            if articles:
                st.success(f"✅ '{keyword_search}' 관련 기사: {len(articles)}건")
                
                for idx, (title, link, keyword, published, saved_at) in enumerate(articles, 1):
                    with st.container(border=True):
                        col1, col2 = st.columns([0.9, 0.1])
                        
                        with col1:
                            st.markdown(f"**[{title}]({link})**")
                            st.caption(f"🔑 키워드: {keyword} | 📅 발행: {published} | 💾 저장: {saved_at[:10]}")
                        
                        with col2:
                            if st.button("❌", key=f"delete_keyword_{idx}_{link}", help="삭제"):
                                delete_article(link)
                                st.success("삭제되었습니다!")
                                st.rerun()
            else:
                st.warning(f"❌ '{keyword_search}' 관련 저장된 기사가 없습니다.")

# 사용자 입력 받기
if prompt := st.chat_input("메시지를 입력하세요..."):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 응답 생성을 위한 임시 변수
    assistant_message = None
    
    try:
        # 1단계: 의도 판단
        is_news_search = check_news_search_intent(prompt)
        
        # 2단계: 응답 생성
        with st.spinner("처리 중..."):
            if is_news_search:
                # 기사 검색 처리
                assistant_message = search_news(prompt)
            else:
                # 일반 대화 처리
                assistant_message = generate_chat_response(st.session_state.messages)
        
        # 3단계: 응답 저장
        if assistant_message:
            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_message
            })
        
        # 4단계: 화면 새로고침
        st.rerun()
            
    except Exception as e:
        st.error(f"❌ 오류 발생: {str(e)}")
        
        # 오류 메시지도 저장
        error_message = f"⚠️ 처리 중 오류가 발생했습니다: {str(e)}"
        st.session_state.messages.append({
            "role": "assistant",
            "content": error_message
        })
        st.rerun()

# 하단 안내
st.divider()
st.caption("💡 팁: 대화 내역은 자동으로 저장되며, 사이드바에서 초기화할 수 있습니다.")