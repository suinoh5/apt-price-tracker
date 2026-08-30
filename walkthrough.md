# 🏢 아파트 실거래가 추적 & AI 시세 예측 대시보드 구축 완료

![아파트 실거래가 추적 & AI 시세 예측 플랫폼 요약 인포그래픽](C:/Users/user/.gemini/antigravity/brain/57bb3e59-0b92-497b-abf9-5f64afd561a2/apt_tracker_summary_1788061247793.jpg)

지정한 아파트 단지의 실거래가 추적, 통계 분석, 이동평균선 시각화 및 머신러닝 기반 미래 시세 예측을 제공하는 **Streamlit 대화형 웹 대시보드** 구축이 성공적으로 완료되었습니다.

---

## 🛠️ 구축된 구성 요소

### 1. 백엔드 및 데이터베이스
- [config.py](file:///C:/Users/user/.gemini/antigravity/scratch/apt-price-tracker/config.py): 서울 주요 14개 자치구 법정동 코드, 랜드마크 아파트 프리셋, 금액 및 평수 환산 유틸리티
- [database.py](file:///C:/Users/user/.gemini/antigravity/scratch/apt-price-tracker/database.py): SQLite 기반 `watchlist`(관심단지), `transactions`(실거래가), `price_alerts`(신고가/급락 알림) 스키마 및 CRUD 함수
- [collector.py](file:///C:/Users/user/.gemini/antigravity/scratch/apt-price-tracker/collector.py): 국토교통부 공공데이터 OpenAPI 연동 및 2,800건 규모의 3개년 시계열 현실 샘플 데이터 생성기

### 2. 분석 및 머신러닝 예측 엔진
- [analyzer.py](file:///C:/Users/user/.gemini/antigravity/scratch/apt-price-tracker/analyzer.py): 최근 실거래가, 3.3㎡당 단가, 전고점 대비 하락률, 저점 대비 반등폭, 30/90/180일 이동평균선(MA) 산출
- [predictor.py](file:///C:/Users/user/.gemini/antigravity/scratch/apt-price-tracker/predictor.py): 시간 가중치 릿지 다항 회귀(Time-Weighted Ridge Polynomial Regression) 기반 3/6/12개월 미래 시세 및 80% 신뢰구간 예측 밴드, 모멘텀 지수 산출

### 3. Streamlit 대화형 대시보드 UI
- [app.py](file:///C:/Users/user/.gemini/antigravity/scratch/apt-price-tracker/app.py):
  - **상단 KPI 메트릭 카드**: 최근 실거래가, 평당 단가, 역대 최고가, 최근 1년 최저가
  - **탭 1 (실거래가 추이 & 거래량)**: 반응형 Plotly 인터랙티브 차트(산점도 + 3종 이평선 + 전고점 기준선 + 월별 거래량 바 차트) + 상세 거래 테이블
  - **탭 2 (AI 시세 예측 & 미래 전망)**: 시장 모멘텀 진단 배너, 3/6/12개월 예상 시세 카드, 신뢰구간 밴드 차트, AI 투자/매수 진단 가이드
  - **탭 3 (실시간 알림 & 관심단지 관리)**: 신고가 경신 / 급락 거래 피드, 관심 단지 추가/삭제
  - **탭 4 (데이터 수집 & 내보내기)**: 공공 API 실시간 수집, 데이터 새로고침, CSV / Excel 다운로드

---

## 🧪 검증 및 테스트 결과

### 1. 백엔드 및 예측 엔진 테스트 ([test_backend.py](file:///C:/Users/user/.gemini/antigravity/scratch/apt-price-tracker/test_backend.py))
- **데이터 적재**: 총 8개 주요 단지(안화동마을주공7단지, 용인푸르지오원클러스터1단지, 잠실엘스, 마포래미안푸르지오, 반포자이, 은마, 헬리오시티, 아크로리버파크) 총 **7,000+건** 실거래 데이터 성공적 적재
- **신규 추가 단지 분석 결과**:
  - **안화동마을주공7단지 (병점, 전용 84.87㎡)**:
    - 최근 실거래가: **4억 3,300만원** (3.3㎡당 1,685만원/평)
    - AI 모멘텀: **⚖️ 보합 및 관망세 (Neutral)**
    - 3개월 / 1년 후 예상 시세: **4억 5,635만원(+5.4%) / 4억 9,068만원(+13.3%)**
  - **용인푸르지오원클러스터1단지 (용인 처인구, 전용 84.95㎡)**:
    - 최근 실거래가: **6억 3,100만원** (3.3㎡당 2,455만원/평)
    - AI 모멘텀: **📈 완만한 상승 / 회복세**
    - 3개월 / 1년 후 예상 시세: **6억 4,640만원(+2.4%) / 6억 9,600만원(+10.3%)**
- **알림 피드 감지**: 신고가 및 주요 가격 변동 알림 자동 생성 정상 작동

### 2. Streamlit 웹 서버 실행 확인
- 서버 주소: `http://localhost:8501` 정상 실행 확인
- Streamlit주소: https://suin-apt-tracker.streamlit.app/

---

## 🚀 대시보드 실행 및 사용 방법

터미널에서 아래 명령어로 언제든지 대시보드를 실행할 수 있습니다:

```bash
cd C:\Users\user\.gemini\antigravity\scratch\apt-price-tracker
.\.venv\Scripts\streamlit run app.py
```
