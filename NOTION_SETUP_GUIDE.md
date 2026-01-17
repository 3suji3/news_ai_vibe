# Notion 통합 가이드

## 개요

뉴스 검색 챗봇에서 검색한 기사를 자동으로 Notion 데이터베이스에 저장할 수 있습니다.

## 설정 방법

### 1단계: Notion Integration 생성

1. **[Notion Developers](https://www.notion.com/my-integrations) 접속**
   - Notion 계정으로 로그인

2. **"Create new integration" 클릭**
   - Name: `News Chatbot` (또는 원하는 이름)
   - Logo: 선택사항
   - Submit 클릭

3. **Integration Token 복사**
   - "Show" 클릭하여 토큰 복사
   - 이것이 `NOTION_API_KEY`입니다

### 2단계: Notion Database 생성

1. **Notion 워크스페이스에서 새 Database 생성**
   - 새 페이지 → Database → Table

2. **다음 속성 추가:**

   | 속성명 | 타입 | 설명 |
   |--------|------|------|
   | 제목 | Title | 기사 제목 (기본 속성) |
   | 링크 | URL | 기사 링크 |
   | 키워드 | Select | 검색 키워드 |
   | 발행일 | Date | 기사 발행 날짜 |
   | 요약 | Rich Text | 기사 요약 내용 |

3. **Database 속성 설정 예시:**

   ```
   제목 (Title)
   ├── 링크 (URL)
   ├── 키워드 (Select)
   │   └── 옵션: AI, 기술, 경제, 정치, 스포츠
   ├── 발행일 (Date)
   └── 요약 (Rich Text)
   ```

### 3단계: Integration 권한 추가

1. **Database 우측 상단 "Share" 클릭**
2. **Integration 추가**
   - "Add connections" → Integration 선택
   - "Allow" 클릭

### 4단계: Database ID 확인

1. **Database 열기**
2. **주소창(URL) 확인**
   ```
   https://www.notion.so/{DATABASE_ID}?v={VIEW_ID}
   ```
3. **Database ID 추출**
   - `https://www.notion.so/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6?v=...`
   - Database ID = `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

### 5단계: 환경변수 설정

#### 로컬 개발 (.env 파일)

```env
OPENAI_API_KEY=your-openai-api-key
NOTION_API_KEY=your-notion-integration-token
NOTION_DATABASE_ID=your-database-id
```

#### Streamlit Cloud (Secrets)

앱 설정 → Secrets에서:

```toml
OPENAI_API_KEY = "your-openai-api-key"
NOTION_API_KEY = "your-notion-integration-token"
NOTION_DATABASE_ID = "your-database-id"
```

## 사용 방법

### 자동 저장

- **검색 시**: 기사를 검색하면 자동으로 SQLite와 Notion에 저장
- **정시 수집**: 매일 9시, 15시, 21시에 수집된 기사가 Notion에 저장

### Notion에서 기사 보기

1. Notion Database 열기
2. 저장된 기사 확인
3. "링크" 속성의 URL을 클릭하여 원문 열기
4. 키워드별로 필터링 가능

## 문제 해결

### Notion 저장이 안 될 때

1. **API Key 확인**
   - Notion Integration Token이 올바른지 확인
   - 토큰에 공백이 없는지 확인

2. **Database ID 확인**
   - Database ID 형식 확인 (32자 alphanumeric)
   - 대시(-) 제거 필요 (하이픈 제거)

3. **권한 확인**
   - Integration이 Database에 추가되었는지 확인
   - "Allow" 버튼 클릭 여부 확인

4. **속성 확인**
   - Database에 모든 필수 속성이 있는지 확인
   - 속성명 정확성 확인 (한글 정확히 일치)

### 에러 메시지별 해결법

| 에러 | 원인 | 해결 |
|------|------|------|
| `Could not find database` | 잘못된 Database ID | Database URL에서 ID 재확인 |
| `API token invalid` | 잘못된 API Key | Notion Integration Token 재생성 |
| `Invalid property name` | 속성명 불일치 | Database 속성명 재확인 |
| `Unauthorized` | 권한 부족 | Database 공유 설정 재확인 |

## 선택적 기능

### Notion 필터 추가

Database 뷰에서:
- **키워드 필터**: 특정 키워드만 보기
- **발행일 필터**: 최근 기사만 보기
- **정렬**: 발행일 최신순으로 정렬

### Notion 템플릿 커스터마이징

각 기사 항목을 클릭하여:
- 기사 요약 추가
- 개인 메모 작성
- 태그 추가 등

## 추가 정보

- [Notion API 문서](https://developers.notion.com)
- [notion-client 라이브러리](https://github.com/ramnes/notion-sdk-py)
- [Notion Integration 가이드](https://www.notion.so/integrations)
