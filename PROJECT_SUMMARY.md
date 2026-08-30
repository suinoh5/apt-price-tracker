# 🏢 Apt Price Tracker - 프로젝트 메모리 및 세션 기억 저장소

본 문서는 다음 세션이나 Antigravity 재실행 시 프로젝트 맥락, 환경 설정, 배포 상태 및 주요 히스토리를 즉시 복원할 수 있도록 정리된 기억 저장소입니다.

---

## 📌 1. 프로젝트 기본 정보
- **프로젝트명**: 아파트 실거래가 추적 & AI 시세 예측 대시보드 (`apt-price-tracker`)
- **로컬 작업 경로**: `C:\Users\user\.gemini\antigravity\scratch\apt-price-tracker`
- **가상환경 경로**: `C:\Users\user\.gemini\antigravity\scratch\apt-price-tracker\.venv`
- **실행 명령어**: `.\.venv\Scripts\streamlit run app.py`

---

## 🌐 2. 배포 및 저장소 정보
- **GitHub 저장소**: [https://github.com/suinoh5/apt-price-tracker](https://github.com/suinoh5/apt-price-tracker)
- **GitHub 계정**: `suinoh5`
- **공개 배포 URL (Streamlit Community Cloud)**: **[https://suin-apt-tracker.streamlit.app](https://suin-apt-tracker.streamlit.app)**
- **CI/CD 파이프라인**: GitHub `main` 브랜치에 push 시 자동으로 Streamlit Cloud에 30초 내 실시간 자동 배포

---

## 🏢 3. 등록된 우선순위 및 주요 단지 정보

### [우선순위 1, 2순위 단지]
1. **안화동마을주공7단지** (경기 화성시 병점동)
   - 법정동코드: `41590` | 2004년 준공 | 742세대
   - 지원 평형: **51.72㎡ (20평형)**, **59.92㎡ (23평형)**
2. **용인푸르지오원클러스터1단지** (경기 용인시 처인구 남동)
   - 법정동코드: `41461` | 2027년 7월 준공 예정(분양권/입주권) | 1,681세대
   - 지원 평형: **59.98㎡ (24평형)**, **84.95㎡ (34평형)**, **130.12㎡ (52평형 펜트하우스)**

### [서울 주요 랜드마크 6개 단지]
- 잠실엘스, 마포래미안푸르지오, 반포자이, 은마, 헬리오시티, 아크로리버파크

---

## 🛠️ 4. 주요 구현 모듈 구조
- `app.py`: Streamlit 대시보드 메인 UI (모바일 반응형 CSS, 4개 탭, Plotly 차트)
- `config.py`: 서울/경기 14개 자치구 법정동 코드, 단지 프리셋, 서식 변환 유틸리티
- `database.py`: SQLite 로컬 DB 관리 (`watchlist`, `transactions`, `price_alerts`)
- `collector.py`: 국토부 OpenAPI 연동 및 3개년 시계열 실거래 샘플 생성기
- `analyzer.py`: 평당가, 전고점 대비 변동률, 30/90/180일 이동평균선 산출 엔진
- `predictor.py`: 시간 가중 릿지 다항 회귀 기반 3/6/12개월 AI 시세 예측 및 80% 신뢰구간 밴드
- `.gitignore`: 로컬 DB(`data/*.db`), `.env`, 가상환경(`.venv/`), 캐시 등 개인정보 완벽 제외

---

## 🔧 5. 최근 개선 및 해결 내역 (히스토리)
1. **모바일 웹 반응형 UI 최적화**: Plotly `scrollZoom: False`로 스마트폰 터치 스크롤 갇힘 방지, 여백 15px 축소, 모바일용 폰트/카드 패딩 자동 조절
2. **CSV 엑셀 한글 깨짐 방지**: `UTF-8-SIG` 바이트 인코딩 및 정돈된 한글 컬럼명 적용
3. **상세 실거래가 테이블 컬럼 확장**: 거래분류 배지(🔥 신고가 등), 거래유형(중개/직거래), 직전 거래 대비 등락액/률, 전고점 대비 회복률, 중개사 소재지 추가
4. **Git 인증 헬퍼 설정**: `gh auth setup-git` 설정 완료로 비밀번호 입력 없이 원격 푸시 가능
