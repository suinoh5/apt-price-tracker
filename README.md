# 🏢 아파트 실거래가 추적 & 시세 예측 대시보드 (Apt Price Tracker)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://suin-apt-tracker.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive%20Charts-3F4F75?logo=plotly&logoColor=white)](https://plotly.com)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-ML%20Forecasting-F7931E?logo=scikitlearn&logoColor=white)](https://scikit-learn.org)

국토교통부 공식 실거래가 공공데이터(85,000+건)를 기반으로 개별 아파트 단지의 시세를 정밀 분석하고, 머신러닝 3대 시나리오 시세 전망과 18개년(2006~2024년) 경기 남부 반도체 벨트(화성시·용인 처인구)의 매크로 실거래 빅데이터를 시각화한 **차세대 부동산 퀀트 분석 대시보드**입니다.

🌐 **실시간 웹 서비스**: **[https://suin-apt-tracker.streamlit.app](https://suin-apt-tracker.streamlit.app)**  
📁 **GitHub 저장소**: **[https://github.com/suinoh5/apt-price-tracker](https://github.com/suinoh5/apt-price-tracker)**

---

## 🌟 2대 핵심 대시보드 구조

좌측 사이드바 최상단의 **`🧭 대시보드 메뉴`**를 통해 2개의 독립적인 분석 페이지를 상호 간섭 없이 자유롭게 전환할 수 있습니다.

```
🧭 대시보드 메뉴
 ├── 🏢 개별 아파트 단지 분석 (4대 탭)
 │    ├── 📊 Tab 1: 실거래가 추이 & 거래량
 │    ├── 🤖 Tab 2: 전문가급 AI 시세 예측 & 종합 투자 매력도
 │    ├── 🔔 Tab 3: 실거래 알림 & 관심단지 관리
 │    └── 💾 Tab 4: 데이터 수집 & 내보내기
 │
 └── 🌐 18개년 지역 빅데이터 & 매크로 분석 (독립 대시보드)
      ├── 📊 1. 18개년 평당 시세 & 거래량 매크로 사이클 (거시 이벤트 맵)
      ├── ⚔️ 2. 경기 남부 반도체 벨트 맞비교: 화성시 vs 용인 처인구
      ├── 🧩 3. 18개년 시대별 평형대 거래 비중 변화 (Area Mix)
      └── 🏆 4. 읍·면·동별 평당 시세 랭킹 & ATH 회복률 리더보드
```

---

## 🚀 상세 기능 소개

### 1. 🏢 개별 아파트 단지 분석 (4대 탭)

- **📊 Tab 1: 실거래가 추이 & 거래량**
  - 단지별, 평형별(전용면적별) 실거래 체결가 시계열 차트 (Plotly Interactive)
  - 30일 / 90일 / 180일 이동평균선(MA) 및 월별 거래량 바 차트
  - 직전 대비 등락액/등락률, 전고점 대비 회복률, 층수 및 거래유형 상세 테이블
- **🤖 Tab 2: 전문가급 AI 시세 예측 & 미래 전망**
  - **🏆 종합 AI 부동산 투자 매력도 점수 (0~100점)**: 모멘텀(30%), 저평가 메리트(25%), 수급 에너지(25%), 가격 안정성(20%)을 종합한 4대 팩터 스코어링
  - **🧭 부동산 시장 RSI (상대강도지수)**: 과열(70 이상) / 균형(35~70) / 과매도 저평가(35 이하) 계기판 진단
  - **🌊 실거래 수급 에너지 분석**: 최근 6개월 거래 회전율(%), 상승/하락 거래 체결 비중(%), 평균 계약 체결 주기
  - **🎯 3대 시나리오(Bull / Base / Bear) 예측 밴드**: 시간 가중 다항 릿지 회귀(Ridge) 모델 기반 향후 3개월 / 6개월 / 12개월 시세 전망선
- **🔔 Tab 3: 실거래 알림 & 관심단지 관리**
  - 최근 신고가 경신 및 단기 급락 거래 자동 탐지 피드
  - 관심 단지 신규 등록, 세대수/준공년도 관리 및 삭제 기능
- **💾 Tab 4: 데이터 수집 & 내보내기**
  - 국토교통부 아파트매매 실거래 상세 자료 OpenAPI 실시간 연동 수집
  - 단지별 실거래 데이터 CSV 및 Excel 원클릭 다운로드

---

### 2. 🌐 18개년(2006~2024) 지역 빅데이터 & 매크로 분석

- **📊 1. 18개년 평당 시세 & 거래량 매크로 사이클**
  - 2006년 1월부터 현재까지 224개월간의 월별 평균 평당가(만원/평) 곡선과 월별 거래량 추세
  - **5대 거시 경제 이벤트 음영 하이라이트**: 2008 금융위기, 2013 취득세 감면 바닥기, 2017~2021 대세상승 유동성장, 2022 금리인상 조정기, 2024~2026 반도체 클러스터 신고가장
- **⚔️ 2. 경기 남부 반도체 벨트 맞비교: 화성시 vs 용인 처인구**
  - 18개년 누적 상승률 (화성 +141.3% vs 처인 +402.8%)
  - 총 누적 실거래 확보량 (화성 50,465건 vs 처인 34,490건)
  - 연도별 평균 평당가 추이 및 시세 격차(Gap Spread) 비교
- **🧩 3. 18개년 시대별 평형대 거래 비중 변화 (Area Mix)**
  - 소형(59㎡ 이하), 중형(59~85㎡ 국민평형), 대형(85㎡ 초과)의 연도별 거래 쏠림 비중 Stacked Bar 차트
- **🏆 4. 읍·면·동별 평당 시세 랭킹 & 역대 최고가(ATH) 회복률 리더보드**
  - 법정동별 평균 평당가 TOP 12 시세 지도
  - 주요 아파트 단지별 2021년 역대 최고가(ATH) 대비 최근 실거래가 회복률(%) 리더보드 테이블

---

## 📦 탑재된 국토교통부 실거래 데이터셋 (85,000+건)

저장소(`data/real_estate.db`)에 국토교통부 검증 실거래가가 전수 탑재되어 있어, 별도의 API 호출 대기 없이 즉시 모든 기능을 활용할 수 있습니다.

| 권역 / 지역 | 법정동 코드 | 수집 기간 | 총 실거래 건수 | 대표 단지 |
| :--- | :---: | :---: | :---: | :--- |
| **경기 화성시 (병점·동부)** | `41595` | 2006.01 ~ 2024.08 (224개월) | **50,465건** | 안화동마을주공7단지 (2,069건 전수) |
| **경기 용인시 처인구** | `41461` | 2006.01 ~ 2024.08 (224개월) | **34,490건** | 용인푸르지오원클러스터1단지 |
| **서울 주요 4대 구** | `11710` 등 | 2021.01 ~ 2026.08 | **17,759건** | 잠실엘스, 헬리오시티, 반포자이, 은마, 아크로리버파크, 마포래미안푸르지오 |

---

## 🛠️ 기술적 특징 및 안정성

1. **SQLite WAL 모드 & 고동시성 보장**:
   - `PRAGMA journal_mode = WAL;` 및 `PRAGMA busy_timeout = 30000;` 적용으로 동시 읽기/쓰기 시 `database is locked` 오류 원천 차단.
2. **국토교통부 OpenAPI 연동 최적화**:
   - 인증키 이중 URL 인코딩 방지(`urllib.parse.unquote`) 및 화성시 세부 법정동코드(`41595`) 자동 매핑 엔진 적용.
3. **독립 모듈형 아키텍처**:
   - 개별 단지 분석(`app.py`)과 매크로 빅데이터 대시보드(`macro_page.py`)의 상태 분리로 상호 간섭 없는 쾌적한 렌더링 지원.

---

## 💻 로컬 개발 및 실행 방법

### 1. 저장소 클론 및 가상환경 설정
```bash
# 1. 저장소 클론
git clone https://github.com/suinoh5/apt-price-tracker.git
cd apt-price-tracker

# 2. 파이썬 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 의존성 패키지 설치
pip install -r requirements.txt
```

### 2. Streamlit 대시보드 실행
```bash
streamlit run app.py
```
브라우저에서 `http://localhost:8501`로 자동 접속됩니다.

---

## 📁 프로젝트 파일 구조

```
apt-price-tracker/
├── app.py                  # Streamlit 메인 웹 애플리케이션 및 라우터
├── macro_page.py           # 18개년 지역 빅데이터 & 매크로 분석 전용 모듈
├── config.py               # 지역 법정동 코드, 기본 프리셋, 서식 헬퍼
├── database.py             # SQLite DB 매니저 (WAL 모드, 30초 타임아웃, 인덱스 최적화)
├── collector.py            # 국토교통부 실시간 OpenAPI 수집기 및 알림 엔진
├── analyzer.py             # 이평선, RSI, 수급 회전율, 18개년 매크로 시계열 집계 엔진
├── predictor.py            # AI 4대 팩터 투자 매력도 스코어링 및 3대 시나리오 예측 모델
├── real_data_loader.py     # 초기 데이터 동기화 모듈
├── requirements.txt        # 의존성 패키지 목록
├── .streamlit/
│   └── config.toml         # 서버 설정 및 사이드바 네비게이션 옵션
└── data/
    └── real_estate.db      # 18개년 85,000+건 검증 실거래가 SQLite 데이터베이스
```

---

## 📄 라이선스 & 데이터 출처
- **데이터 출처**: [공공데이터포털(data.go.kr)](https://www.data.go.kr) 국토교통부 아파트매매 실거래 상세 자료
- **라이선스**: MIT License
