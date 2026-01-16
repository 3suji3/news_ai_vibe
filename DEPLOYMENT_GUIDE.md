# 🚀 Streamlit Cloud 배포 완벽 가이드

## 📋 배포 전 체크리스트

- [x] requirements.txt 생성
- [x] .streamlit/config.toml 생성
- [x] .streamlit/secrets.toml 생성 (로컬용)
- [x] .gitignore 설정
- [x] README.md 작성
- [ ] GitHub 리포지토리 생성
- [ ] Streamlit Cloud에 배포
- [ ] 환경변수 설정

---

## Step 1️⃣: GitHub 리포지토리 준비

### 1.1 Git 설정

```powershell
# 현재 디렉토리에서 Git 초기화 (이미 되어있을 수 있음)
cd c:\Users\SSAFY\Desktop\startcamp
git init

# 사용자 정보 설정 (처음이면)
git config user.name "Your Name"
git config user.email "your.email@example.com"

# 또는 글로벌 설정
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 1.2 파일 추가 및 커밋

```powershell
# 모든 파일 추가
git add .

# 상태 확인 (.gitignore 적용되었는지 확인)
git status

# 커밋
git commit -m "Initial commit: News Search Chatbot"

# 브랜치명을 main으로 변경 (필요시)
git branch -M main
```

---

## Step 2️⃣: GitHub에 리포지토리 생성

### 2.1 GitHub 웹사이트에서

1. [github.com](https://github.com) 접속
2. 우측 상단 "+" → "New repository" 클릭
3. 리포지토리 이름: `news-chatbot` (또는 원하는 이름)
4. Description: `AI-powered News Search Chatbot`
5. Public 선택 (Streamlit Cloud에서 접근 가능하도록)
6. "Create repository" 클릭

### 2.2 로컬에서 원격 연결

```powershell
# 원격 저장소 추가
git remote add origin https://github.com/your-username/news-chatbot.git

# 첫 푸시
git push -u origin main

# 이후 푸시
git push origin main
```

---

## Step 3️⃣: Streamlit Cloud 배포

### 3.1 Streamlit Cloud 계정 생성

1. [share.streamlit.io](https://share.streamlit.io) 방문
2. "Sign up" 클릭
3. GitHub 계정으로 로그인
4. Streamlit 앱 접근 권한 승인

### 3.2 배포 시작

1. Streamlit Cloud 대시보드에서 "New app" 클릭
2. 설정:
   - **Repository**: `your-username/news-chatbot`
   - **Branch**: `main`
   - **Main file path**: `app.py`
3. "Deploy" 클릭

### 3.3 배포 진행 상황 확인

- 배포 로그 실시간 표시
- "Running" 상태가 되면 준비 완료
- 우측 상단에 "Deployed" 배지 표시

---

## Step 4️⃣: 환경변수 설정 (⚠️ 중요)

### 4.1 Secrets 설정

1. Streamlit Cloud 대시보드에서 배포된 앱 선택
2. 우측 상단 "⋮" (메뉴) → "Settings" 클릭
3. "Secrets" 탭 선택
4. 아래 내용 복사하여 입력:

```toml
# Streamlit Secrets Manager에 입력
OPENAI_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxx"
```

5. "Save" 클릭

### 4.2 API 키 확인

- OpenAI API 키는 [platform.openai.com](https://platform.openai.com)에서 획득
- GMS API (SSAFY)를 사용하는 경우 해당 API 키 입력
- **절대 GitHub에 올리지 마세요!**

---

## Step 5️⃣: 배포 확인

### 5.1 앱 테스트

배포 URL (share.streamlit.io에서 제공)로 접속하여:

1. **기본 동작 확인**
   ```
   입력: "안녕하세요"
   예상: 인사 응답 + 자세한 설명
   ```

2. **기사 검색 확인**
   ```
   입력: "AI 뉴스"
   예상: 기사 검색 결과 표시
   ```

3. **데이터베이스 확인**
   - 사이드바 "💾 저장된 기사" 확인
   - 기사 조회 가능한지 확인

### 5.2 로그 확인

- Streamlit Cloud 대시보드에서 "Logs" 탭 확인
- 에러 발생 시 로그에서 원인 파악

---

## 🔄 업데이트 배포

코드 수정 후 다시 배포:

```powershell
# 코드 수정
# ...

# 변경사항 커밋
git add .
git commit -m "Fix: keyword extraction logic"

# GitHub에 푸시
git push origin main

# Streamlit Cloud는 자동으로 감지하고 재배포
# (몇 초~1분 소요)
```

---

## ⚙️ Streamlit Cloud 자동 재배포 설정

### 원인
- GitHub에 푸시할 때마다 자동 감지
- 약 1-2분 후 자동으로 앱 업데이트

### 수동 재배포
1. 대시보드에서 앱 선택
2. 우측 상단 "⋮" → "Reboot app" 클릭

---

## 🐛 배포 후 문제 해결

### 1. "ModuleNotFoundError" 오류

**원인**: requirements.txt에 패키지 누락

**해결**:
```powershell
# requirements.txt에 누락된 패키지 추가
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push origin main
```

### 2. "API Key를 찾을 수 없습니다" 오류

**원인**: Secrets이 설정되지 않음

**해결**:
1. Settings → Secrets 탭 확인
2. OPENAI_API_KEY 추가
3. "Save" 클릭
4. 앱 재실행 (Reboot app)

### 3. 데이터베이스 오류

**원인**: 로컬 DB 파일이 Streamlit Cloud에 배포됨

**해결**: .gitignore에 `articles.db` 추가되어 있으므로 자동 해결
```
articles.db  # 로컬에만 생성
```

### 4. 느린 속도

**원인**: 
- Playwright 크롤링 시 지연
- 첫 실행 시 브라우저 다운로드

**해결**: 일반적인 현상, 캐싱으로 개선됨

---

## 📊 배포 후 모니터링

### 1. 앱 상태 확인

```
Streamlit Cloud 대시보드
├── App status
│   ├── Running (초록색) ✅
│   └── Error (빨강색) ❌
├── Logs
└── Settings
```

### 2. 정기적인 확인

- 매주 1회 앱 접속하여 동작 확인
- 로그에서 에러 확인
- 사용자 피드백 수집

---

## 📱 앱 공유

배포 후 사용자들과 공유:

```
📱 배포 URL: https://share.streamlit.io/your-username/news-chatbot

✨ 뉴스 검색 챗봇
일반 대화와 기사 검색이 가능한 AI 어시스턴트입니다!

🎯 사용 예시:
- 일반 대화: "파이썬 설명해줘"
- 기사 검색: "AI 뉴스 알려줘"
```

---

## 🎓 배포 완료!

축하합니다! 🎉

이제 전 세계 누구나 당신의 챗봇을 사용할 수 있습니다!

### ✅ 완료된 항목
- [x] 로컬 개발 완료
- [x] GitHub에 배포
- [x] Streamlit Cloud 배포
- [x] 환경변수 설정
- [x] 앱 테스트

### 🚀 다음 단계 (선택사항)
- [ ] 커스텀 도메인 설정
- [ ] 사용자 인증 추가
- [ ] 분석 대시보드 추가
- [ ] 모바일 최적화
- [ ] 팀 협업 설정

---

**즐거운 배포 되세요! 🚀✨**
