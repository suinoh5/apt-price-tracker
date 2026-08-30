"""
Apt Price Tracker - Streamlit Interactive Web Application
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
from datetime import datetime

from config import DEFAULT_COMPLEXES, LAWD_CODES, format_price_krw, sqm_to_pyeong
from database import (
    init_db,
    get_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    get_transactions_df,
    get_recent_alerts
)
from collector import generate_realistic_historical_data, fetch_molit_api, detect_and_log_alerts
from analyzer import calculate_complex_metrics, add_moving_averages, calculate_rsi, calculate_supply_demand_metrics
from predictor import predict_future_prices, calculate_investment_score


# Page Config
st.set_page_config(
    page_title="아파트 실거래가 추적 & 시세 예측 대시보드",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern High-End UI
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    
    /* 카드 공통 스타일 */
    .metric-card {
        background: linear-gradient(135deg, #f8fafc 0%, #edf2f7 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        margin-bottom: 10px;
    }
    .metric-title {
        font-size: 0.85rem;
        color: #718096;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a202c;
        line-height: 1.2;
    }
    .metric-sub {
        font-size: 0.82rem;
        margin-top: 4px;
    }
    .badge-up {
        color: #e53e3e;
        font-weight: 600;
    }
    .badge-down {
        color: #3182ce;
        font-weight: 600;
    }
    .badge-neutral {
        color: #718096;
        font-weight: 600;
    }
    
    .diagnosis-box {
        background-color: #f7fafc;
        border-left: 4px solid #3182ce;
        border-radius: 0 8px 8px 0;
        padding: 14px 18px;
        margin: 12px 0;
    }
    
    .alert-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #e53e3e;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 8px;
    }

    /* 📱 모바일 화면 (스마트폰 / 태블릿) 반응형 최적화 */
    @media (max-width: 768px) {
        .metric-card {
            padding: 12px 14px !important;
            margin-bottom: 8px !important;
            border-radius: 10px !important;
        }
        .metric-title {
            font-size: 0.78rem !important;
            margin-bottom: 2px !important;
        }
        .metric-value {
            font-size: 1.28rem !important;
        }
        .metric-sub {
            font-size: 0.75rem !important;
        }
        .diagnosis-box {
            padding: 12px 14px !important;
            margin: 8px 0 !important;
        }
        /* 탭 바 모바일 최적화 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px !important;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 8px !important;
            font-size: 0.85rem !important;
        }
        /* 데이터프레임 높이 조절 */
        div[data-testid="stDataFrame"] {
            font-size: 0.82rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)


from real_data_loader import load_real_data_into_db

# Initialize DB
init_db()

# Auto-seed verified real transactions if database is empty
with st.spinner("국토교통부 검증 실거래가 데이터베이스를 로드 중입니다..."):
    sample_check = get_transactions_df()
    if sample_check.empty:
        load_real_data_into_db()


# -------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/real-estate.png", width=64)
    st.title("🏢 아파트 시세 트래커")
    st.caption("실거래가 추적 & AI 시세 예측 플랫폼")
    st.divider()
    
    # 1. 관심 단지 선택
    watchlist = get_watchlist()
    complex_names = [item["complex_name"] for item in watchlist] if watchlist else ["잠실엘스"]
    
    selected_complex = st.selectbox(
        "📍 분석할 아파트 단지 선택",
        options=complex_names,
        index=0 if complex_names else None
    )
    
    # 선택된 단지의 거래 데이터 로드하여 가능한 평형 목록 추출
    complex_tx_df = get_transactions_df(complex_name=selected_complex)
    
    if not complex_tx_df.empty:
        available_areas = sorted(complex_tx_df["exclusive_area"].unique())
        area_labels = [f"{a:.2f}㎡ ({sqm_to_pyeong(a):.0f}평)" for a in available_areas]
        area_mapping = dict(zip(area_labels, available_areas))
        
        selected_area_label = st.selectbox(
            "📐 전용면적(평형) 선택",
            options=area_labels,
            index=0 if len(area_labels) <= 1 else 1  # 국민평형(84) 디폴트 선호
        )
        selected_area = area_mapping[selected_area_label]
    else:
        selected_area = None
        st.warning("선택한 단지의 거래 데이터가 없습니다.")

    st.divider()

    # 2. 신규 관심 단지 등록
    with st.expander("➕ 새 관심단지 등록"):
        with st.form("add_complex_form"):
            new_name = st.text_input("단지명 (예: 래미안대치팰리스)")
            new_region_name = st.selectbox("지역 선택", list(LAWD_CODES.keys()))
            new_dong = st.text_input("법정동 (예: 대치동)")
            new_build_year = st.number_input("준공년도", min_value=1970, max_value=2030, value=2015)
            new_households = st.number_input("총 세대수", min_value=10, max_value=20000, value=1500)
            new_memo = st.text_input("메모", value="관심 단지")
            
            submit_btn = st.form_submit_button("관심 단지 추가", use_container_width=True)
            if submit_btn:
                if new_name.strip():
                    reg_code = LAWD_CODES[new_region_name]
                    ok = add_to_watchlist(new_name, reg_code, new_region_name, new_dong, new_build_year, new_households, new_memo)
                    if ok:
                        st.success(f"'{new_name}' 단지가 등록되었습니다!")
                        st.rerun()
                    else:
                        st.error("이미 등록된 단지명이거나 오류가 발생했습니다.")
                else:
                    st.warning("단지명을 입력해주세요.")

    st.caption("© 2026 Apt Price Tracker. All Rights Reserved.")


# -------------------------------------------------------------
# MAIN VIEW
# -------------------------------------------------------------
if not selected_complex:
    st.info("사이드바에서 분석할 아파트 단지를 선택해주세요.")
    st.stop()

# Get selected complex details
complex_info = next((item for item in watchlist if item["complex_name"] == selected_complex), None)

# Header Section
col_title, col_badge = st.columns([3, 1])
with col_title:
    st.subheader(f"🏢 {selected_complex}")
    if complex_info:
        st.markdown(
            f"📍 **{complex_info['region_name']} {complex_info.get('dong', '')}** | "
            f"🏗️ **{complex_info.get('build_year', '-')}년 준공** | "
            f"👥 **{complex_info.get('total_households', '-'):,}세대**"
        )
    st.caption("🛡️ **데이터 신뢰도**: 국토교통부 실거래가 공개시스템 및 부동산 공시 검증 실거래가 데이터")
with col_badge:
    st.write("")
    if selected_area:
        st.info(f"선택 평형: **{selected_area:.2f}㎡ ({sqm_to_pyeong(selected_area):.0f}평)**")

st.markdown("---")

# Filter transactions for selected complex and area
if selected_area is not None:
    df_filtered = complex_tx_df[complex_tx_df["exclusive_area"] == selected_area].sort_values("deal_date").copy()
else:
    df_filtered = complex_tx_df.sort_values("deal_date").copy()

# Metric Calculations
metrics = calculate_complex_metrics(df_filtered)

if metrics:
    # 4 KPI Cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    with kpi1:
        diff_str = f"+{metrics['diff_price']//10000}억 {abs(metrics['diff_price']%10000):,}만" if metrics['diff_price'] > 0 else (
            f"-{abs(metrics['diff_price'])//10000}억 {abs(metrics['diff_price'])%10000:,}만" if metrics['diff_price'] < 0 else "변동 없음"
        )
        badge_cls = "badge-up" if metrics['diff_pct'] > 0 else ("badge-down" if metrics['diff_pct'] < 0 else "badge-neutral")
        sign = "+" if metrics['diff_pct'] > 0 else ""
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">최근 실거래가 ({metrics['recent_floor']}층)</div>
            <div class="metric-value">{metrics['recent_price_str']}</div>
            <div class="metric-sub">
                <span class="{badge_cls}">직전 대비 {sign}{metrics['diff_pct']}% ({diff_str})</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">3.3㎡(평)당 단가</div>
            <div class="metric-value">{metrics['price_per_pyeong']:,}만원</div>
            <div class="metric-sub text-muted">기준 면적: {metrics['recent_area']}㎡ ({metrics['recent_pyeong']}평)</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi3:
        ath_diff = metrics['ath_diff_pct']
        ath_sign = "+" if ath_diff > 0 else ""
        ath_badge = "badge-up" if ath_diff >= 0 else "badge-down"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">역대 최고가 (전고점)</div>
            <div class="metric-value">{metrics['ath_price_str']}</div>
            <div class="metric-sub">
                <span class="{ath_badge}">전고점 대비 {ath_sign}{ath_diff}% ({metrics['ath_date']})</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi4:
        low_diff = metrics['low_1y_diff_pct']
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">최근 1년 최저가</div>
            <div class="metric-value">{metrics['low_1y_price_str']}</div>
            <div class="metric-sub">
                <span class="badge-up">저점 대비 +{low_diff}% 반등</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.write("")

# -------------------------------------------------------------
# TABS SECTION
# -------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 실거래가 추이 & 거래량",
    "🤖 AI 시세 예측 & 미래 전망",
    "🔔 실거래 알림 & 관심단지 관리",
    "💾 데이터 수집 & 내보내기"
])


# -------------------------------------------------------------
# TAB 1: 실거래가 추이 & 차트
# -------------------------------------------------------------
with tab1:
    if df_filtered.empty:
        st.warning("조회된 실거래 내역이 없습니다.")
    else:
        # 차트 옵션 컨트롤
        c_opt1, c_opt2 = st.columns([2, 1])
        with c_opt1:
            st.markdown("##### 📈 시세 추이 및 이동평균선 (Plotly Interactive Chart)")
        with c_opt2:
            show_ma = st.checkbox("이동평균선(30/90/180일) 표시", value=True)
            
        df_ma = add_moving_averages(df_filtered)
        
        # Plotly Subplots (상단: 실거래가 산점도+이평선, 하단: 월별 거래량 바 차트)
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=("실거래 체결가 (억원)", "월별 거래량 (건)"),
            row_heights=[0.75, 0.25]
        )
        
        # 1. 개별 실거래가 산점도 (Scatter)
        fig.add_trace(
            go.Scatter(
                x=df_ma["deal_date"],
                y=df_ma["deal_amount"] / 10000,
                mode="markers+lines",
                name="실거래가",
                marker=dict(size=8, color="#3182ce", opacity=0.8),
                line=dict(color="rgba(49, 130, 206, 0.3)", width=1, dash="dot"),
                customdata=np.stack((df_ma["floor"], df_ma["exclusive_area"]), axis=-1),
                hovertemplate="<b>일자</b>: %{x|%Y-%m-%d}<br><b>가격</b>: %{y:.2f}억원<br><b>층수</b>: %{customdata[0]}층<br><b>전용면적</b>: %{customdata[1]}㎡<extra></extra>"
            ),
            row=1, col=1
        )
        
        # 2. 이동평균선
        if show_ma and "ma_30" in df_ma:
            fig.add_trace(
                go.Scatter(
                    x=df_ma["deal_date"],
                    y=df_ma["ma_30"] / 10000,
                    mode="lines",
                    name="30일 이동평균",
                    line=dict(color="#dd6b20", width=1.5)
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=df_ma["deal_date"],
                    y=df_ma["ma_90"] / 10000,
                    mode="lines",
                    name="90일 이동평균",
                    line=dict(color="#805ad5", width=1.8)
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=df_ma["deal_date"],
                    y=df_ma["ma_180"] / 10000,
                    mode="lines",
                    name="180일 이동평균",
                    line=dict(color="#38a169", width=2.0)
                ),
                row=1, col=1
            )
            
        # 3. 전고점 가로 기준선
        if metrics:
            fig.add_hline(
                y=metrics["ath_price"] / 10000,
                line_dash="dash",
                line_color="#e53e3e",
                annotation_text=f"전고점 ({metrics['ath_price_str']})",
                annotation_position="top right",
                row=1, col=1
            )
            
        # 4. 월별 거래량 (Bar)
        monthly_vol = df_filtered.set_index("deal_date").resample("ME")["deal_amount"].count().reset_index()
        fig.add_trace(
            go.Bar(
                x=monthly_vol["deal_date"],
                y=monthly_vol["deal_amount"],
                name="월 거래량",
                marker_color="#a0aec0",
                opacity=0.7,
                hovertemplate="<b>년월</b>: %{x|%Y-%m}<br><b>거래건수</b>: %{y}건<extra></extra>"
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            height=480,
            template="plotly_white",
            margin=dict(l=15, r=15, t=35, b=15),
            hovermode="closest",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                font=dict(size=10.5)
            ),
            font=dict(family="Pretendard, sans-serif", size=11)
        )
        fig.update_yaxes(title_text="가격 (억원)", row=1, col=1, title_font=dict(size=11), tickfont=dict(size=10))
        fig.update_yaxes(title_text="건수", row=2, col=1, title_font=dict(size=11), tickfont=dict(size=10))
        fig.update_xaxes(tickformat="%y.%m", nticks=8, tickfont=dict(size=10))
        
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "responsive": True,
                "displayModeBar": False,
                "scrollZoom": False
            }
        )
        
        # 상세 실거래가 내역 테이블
        st.markdown("##### 📋 상세 실거래가 체결 내역")
        
        # 시간순(과거->현재) 정렬 후 직전 거래 대비 등락 및 전고점 회복률 계산
        df_chron = df_filtered.sort_values(["deal_date", "id"]).copy()
        
        # 1. 직전 거래 대비 등락 계산
        df_chron["prev_amount"] = df_chron["deal_amount"].shift(1)
        df_chron["diff_amt"] = df_chron["deal_amount"] - df_chron["prev_amount"]
        df_chron["diff_pct"] = (df_chron["diff_amt"] / df_chron["prev_amount"]) * 100
        
        # 2. 역대 최고가 및 전고점 대비 회복률
        overall_ath = df_chron["deal_amount"].max() if not df_chron.empty else 0
        df_chron["ath_gap_pct"] = ((df_chron["deal_amount"] - overall_ath) / overall_ath) * 100 if overall_ath > 0 else 0.0
        
        def assign_badge(row):
            if row.get("is_cancel") == 1 or row.get("cancel_deal_type"):
                return "❌ 취소"
            if row.get("req_gbn") == "직거래":
                return "⚡ 직거래"
            if row["deal_amount"] >= overall_ath:
                return "🔥 신고가"
            if pd.notna(row["diff_pct"]):
                if row["diff_pct"] >= 2.0:
                    return "📈 상승"
                elif row["diff_pct"] <= -2.0:
                    return "📉 하락"
            return "➖ 보합"

        def format_diff(row):
            if pd.isna(row["diff_amt"]):
                return "-"
            amt = int(row["diff_amt"])
            pct = row["diff_pct"]
            if amt > 0:
                eok = amt // 10000
                man = amt % 10000
                amt_str = f"+{eok}억 {man:,}만" if eok > 0 else f"+{man:,}만"
                return f"{amt_str} (+{pct:.1f}%)"
            elif amt < 0:
                amt_abs = abs(amt)
                eok = amt_abs // 10000
                man = amt_abs % 10000
                amt_str = f"-{eok}억 {man:,}만" if eok > 0 else f"-{man:,}만"
                return f"{amt_str} ({pct:.1f}%)"
            else:
                return "보합 (0.0%)"
                
        def format_ath_gap(row):
            gap = row["ath_gap_pct"]
            if gap >= 0:
                return "0.0% (전고점)"
            else:
                return f"{gap:.1f}%"

        df_chron["거래분류"] = df_chron.apply(assign_badge, axis=1)
        df_chron["직전대비등락"] = df_chron.apply(format_diff, axis=1)
        df_chron["전고점대비"] = df_chron.apply(format_ath_gap, axis=1)
        df_chron["거래유형"] = df_chron.get("req_gbn", "중개거래").fillna("중개거래")
        df_chron["중개사소재지"] = df_chron.get("rdealer_lawdnm", "현지 중개사").fillna("현지 중개사")
        df_chron["거래일자"] = df_chron["deal_date"].dt.strftime("%Y-%m-%d")
        df_chron["거래금액"] = df_chron["deal_amount"].apply(format_price_krw)
        df_chron["전용면적"] = df_chron["exclusive_area"].apply(lambda x: f"{x:.2f}㎡ ({sqm_to_pyeong(x):.0f}평)")
        df_chron["층수"] = df_chron["floor"].apply(lambda x: f"{x}층")
        
        # 최근 거래가 위로 오도록 역순(최신순) 정렬
        display_df = df_chron.sort_values("deal_date", ascending=False)
        
        st.dataframe(
            display_df[[
                "거래일자",
                "거래분류",
                "거래금액",
                "직전대비등락",
                "전고점대비",
                "전용면적",
                "층수",
                "거래유형",
                "중개사소재지"
            ]].rename(columns={
                "직전대비등락": "직전 대비 등락",
                "전고점대비": "전고점 대비 회복률",
                "중개사소재지": "중개사 소재지"
            }),
            use_container_width=True,
            hide_index=True
        )


# -------------------------------------------------------------
# TAB 2: AI 시세 예측 & 미래 전망
# -------------------------------------------------------------
with tab2:
    st.markdown("##### 🤖 전문가급 AI 시세 예측 & 종합 투자 매력도 분석")
    st.caption("부동산 퀀트 지표(RSI, 수급 회전율), 4대 팩터 종합 매력도 스코어링 및 3대 시나리오(Bull/Base/Bear) 시뮬레이션 모델")
    
    if df_filtered.empty or len(df_filtered) < 5:
        st.warning("정밀 예측을 위해 최소 5건 이상의 실거래 데이터가 필요합니다.")
    else:
        total_hh = complex_info.get("total_households", 1000) if complex_info else 1000
        
        # 1. 지표 계산
        rsi_data = calculate_rsi(df_filtered)
        supply_demand = calculate_supply_demand_metrics(df_filtered, total_households=total_hh)
        pred_res = predict_future_prices(df_filtered, forecast_days=365)
        
        if pred_res["success"]:
            score_data = calculate_investment_score(
                metrics=metrics,
                rsi_data=rsi_data,
                supply_demand=supply_demand,
                momentum_pct=pred_res["recent_momentum_pct"]
            )
            
            # =========================================================
            # 🏆 SECTION 1: 종합 AI 투자 매력도 스코어 & RSI 계기판
            # =========================================================
            sec1_col1, sec1_col2 = st.columns([1.1, 0.9])
            
            with sec1_col1:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%); border-radius: 12px; padding: 20px 22px; color: white; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span style="font-size: 0.82rem; background: rgba(255,255,255,0.15); padding: 3px 8px; border-radius: 4px; font-weight: 600;">AI 종합 투자 매력도</span>
                            <h2 style="font-size: 2.2rem; font-weight: 800; margin: 8px 0 2px 0; color: #f7fafc;">
                                {score_data['total_score']} <span style="font-size: 1.1rem; font-weight: 500; color: #a0aec0;">/ 100점</span>
                            </h2>
                            <div style="font-size: 0.95rem; font-weight: 700; color: {score_data['color']}; margin-bottom: 6px;">
                                {score_data['grade']}
                            </div>
                        </div>
                        <div style="text-align: right; font-size: 2.4rem;">
                            🏆
                        </div>
                    </div>
                    <div style="font-size: 0.84rem; color: #e2e8f0; line-height: 1.5; margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px;">
                        {score_data['verdict']}
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; font-size: 0.78rem; color: #cbd5e0;">
                        <div>• 모멘텀: <strong>{score_data['sub_scores']['모멘텀 (추세 강도)']}점</strong></div>
                        <div>• 저평가 메리트: <strong>{score_data['sub_scores']['가격 메리트 (저평가도)']}점</strong></div>
                        <div>• 수급 에너지: <strong>{score_data['sub_scores']['거래량 에너지 (수급)']}점</strong></div>
                        <div>• 가격 안정성: <strong>{score_data['sub_scores']['가격 변동 안정성']}점</strong></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with sec1_col2:
                st.markdown(f"""
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px 22px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.03);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span style="font-size: 0.82rem; color: #718096; font-weight: 600;">부동산 RSI 상대강도지수</span>
                            <h2 style="font-size: 2.2rem; font-weight: 800; margin: 8px 0 2px 0; color: {rsi_data['color']};">
                                {rsi_data['rsi']} <span style="font-size: 1.0rem; font-weight: 500; color: #718096;">/ 100</span>
                            </h2>
                            <div style="font-size: 0.95rem; font-weight: 700; color: {rsi_data['color']}; margin-bottom: 6px;">
                                {rsi_data['status']}
                            </div>
                        </div>
                        <div style="text-align: right; font-size: 2.2rem;">
                            🧭
                        </div>
                    </div>
                    <div style="font-size: 0.84rem; color: #4a5568; line-height: 1.5; margin-top: 6px; border-top: 1px solid #edf2f7; padding-top: 8px;">
                        {rsi_data['desc']}
                    </div>
                    <div style="margin-top: 10px; font-size: 0.76rem; color: #718096;">
                        기준: 70 이상(과열 주의) | 35~70(적정 균형) | 35 이하(바닥권 매수)
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # =========================================================
            # 🌊 SECTION 2: 거래 회전율 & 수급 진단 지표 카드 (4-Grid)
            # =========================================================
            st.markdown("###### 🌊 거래량 & 수급 에너지 진단")
            sq1, sq2, sq3, sq4 = st.columns(4)
            
            with sq1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">최근 6개월 거래 회전율</div>
                    <div class="metric-value">{supply_demand['turnover_rate_str']}</div>
                    <div class="metric-sub">총 세대수 중 {supply_demand['tx_count_6m']}건 체결</div>
                </div>
                """, unsafe_allow_html=True)
                
            with sq2:
                adv_color = "#e53e3e" if supply_demand['advance_ratio'] >= 50 else "#3182ce"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">상승 거래 체결 비중</div>
                    <div class="metric-value" style="color: {adv_color};">{supply_demand['advance_ratio']}%</div>
                    <div class="metric-sub">상승 {supply_demand['up_count']}건 / 하락 {supply_demand['down_count']}건</div>
                </div>
                """, unsafe_allow_html=True)
                
            with sq3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">평균 거래 체결 주기</div>
                    <div class="metric-value">{supply_demand['avg_interval_days']}일</div>
                    <div class="metric-sub">약 {supply_demand['avg_interval_days']:.0f}일마다 1건 발생</div>
                </div>
                """, unsafe_allow_html=True)
                
            with sq4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">최근 6개월 가격 모멘텀</div>
                    <div class="metric-value" style="color: {pred_res['momentum_color']};">{pred_res['recent_momentum_pct']:+0.2f}%</div>
                    <div class="metric-sub">{pred_res['momentum_status'].split(' ')[1]}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()

            # =========================================================
            # 🎯 SECTION 3: 3대 시나리오 (Bull / Base / Bear) 예측 차트 & 비교 표
            # =========================================================
            st.markdown("###### 🎯 AI 3대 시나리오 (상승 🚀 / 기본 🎯 / 보수 🛡️) 시세 전망")
            
            future_df = pred_res["future_df"]
            hist_fit_df = pred_res["historical_fit_df"]
            
            fig_pred = go.Figure()
            
            # 1. 과거 실거래가 포인트
            fig_pred.add_trace(go.Scatter(
                x=df_filtered["deal_date"],
                y=df_filtered["deal_amount"] / 10000,
                mode="markers",
                name="실제 실거래가",
                marker=dict(color="#4a5568", size=7, opacity=0.75),
                hovertemplate="<b>일자</b>: %{x|%Y-%m-%d}<br><b>실거래가</b>: %{y:.2f}억원<extra></extra>"
            ))
            
            # 2. 과거 추세선
            fig_pred.add_trace(go.Scatter(
                x=hist_fit_df["deal_date"],
                y=hist_fit_df["fitted_price"] / 10000,
                mode="lines",
                name="과거 추세선",
                line=dict(color="#a0aec0", width=1.5, dash="dot"),
                hoverinfo="skip"
            ))
            
            # 3. 🚀 상승 시나리오 (Bull Case)
            fig_pred.add_trace(go.Scatter(
                x=future_df["deal_date"],
                y=future_df["bull_price"] / 10000,
                mode="lines",
                name="🚀 상승 시나리오 (Bull)",
                line=dict(color="#38a169", width=2.5, dash="dash"),
                hovertemplate="<b>상승 시나리오</b>: %{y:.2f}억원<extra></extra>"
            ))
            
            # 4. 🎯 기본 시나리오 (Base Case)
            fig_pred.add_trace(go.Scatter(
                x=future_df["deal_date"],
                y=future_df["base_price"] / 10000,
                mode="lines",
                name="🎯 기본 시나리오 (Base)",
                line=dict(color="#e53e3e", width=3.0),
                hovertemplate="<b>기본 시나리오</b>: %{y:.2f}억원<extra></extra>"
            ))
            
            # 5. 🛡️ 보수 시나리오 (Bear Case)
            fig_pred.add_trace(go.Scatter(
                x=future_df["deal_date"],
                y=future_df["bear_price"] / 10000,
                mode="lines",
                name="🛡️ 보수 시나리오 (Bear)",
                line=dict(color="#3182ce", width=2.0, dash="dash"),
                hovertemplate="<b>보수 시나리오 (지지선)</b>: %{y:.2f}억원<extra></extra>"
            ))
            
            fig_pred.update_layout(
                title=dict(
                    text=f"📈 {selected_complex} ({selected_area}㎡) 향후 12개월 3대 시나리오 전망선",
                    font=dict(size=13.5, color="#1a202c")
                ),
                template="plotly_white",
                height=440,
                margin=dict(l=15, r=15, t=45, b=15),
                hovermode="closest",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0,
                    font=dict(size=10.5)
                ),
                font=dict(family="Pretendard, sans-serif", size=11)
            )
            fig_pred.update_xaxes(tickformat="%y.%m", nticks=8, tickfont=dict(size=10))
            fig_pred.update_yaxes(title_text="가격 (억원)", title_font=dict(size=11), tickfont=dict(size=10))
            
            st.plotly_chart(
                fig_pred,
                use_container_width=True,
                config={
                    "responsive": True,
                    "displayModeBar": False,
                    "scrollZoom": False
                }
            )
            
            # 3대 시나리오 비교 테이블
            f3 = pred_res["forecast_3m"]
            f6 = pred_res["forecast_6m"]
            f12 = pred_res["forecast_12m"]
            
            scenario_table = pd.DataFrame([
                {
                    "예측 시점": f"3개월 후 ({f3['date']})",
                    "🚀 상승 시나리오 (Bull)": f"{f3['bull_price_str']} ({f3['bull_pct']:+0.1f}%)",
                    "🎯 기본 시나리오 (Base)": f"{f3['base_price_str']} ({f3['base_pct']:+0.1f}%)",
                    "🛡️ 보수 시나리오 (Bear)": f"{f3['bear_price_str']} ({f3['bear_pct']:+0.1f}%)",
                },
                {
                    "예측 시점": f"6개월 후 ({f6['date']})",
                    "🚀 상승 시나리오 (Bull)": f"{f6['bull_price_str']} ({f6['bull_pct']:+0.1f}%)",
                    "🎯 기본 시나리오 (Base)": f"{f6['base_price_str']} ({f6['base_pct']:+0.1f}%)",
                    "🛡️ 보수 시나리오 (Bear)": f"{f6['bear_price_str']} ({f6['bear_pct']:+0.1f}%)",
                },
                {
                    "예측 시점": f"1년 후 ({f12['date']})",
                    "🚀 상승 시나리오 (Bull)": f"{f12['bull_price_str']} ({f12['bull_pct']:+0.1f}%)",
                    "🎯 기본 시나리오 (Base)": f"{f12['base_price_str']} ({f12['base_pct']:+0.1f}%)",
                    "🛡️ 보수 시나리오 (Bear)": f"{f12['bear_price_str']} ({f12['bear_pct']:+0.1f}%)",
                }
            ])
            st.dataframe(scenario_table, use_container_width=True, hide_index=True)
            
            # =========================================================
            # 💡 SECTION 4: AI 시장 진단 및 종합 투자 전략 리포트
            # =========================================================
            with st.expander("💡 AI 시장 진단 및 종합 투자 가이드 리포트", expanded=True):
                st.markdown(f"""
                - **핵심 모멘텀 진단**: **{pred_res['momentum_status']}** (최근 6개월 등락: **{pred_res['recent_momentum_pct']:+0.2f}%**)
                - **RSI 매수/매도 심리**: **{rsi_data['status']}** (현재 RSI: **{rsi_data['rsi']}점**) - {rsi_data['desc']}
                - **단기 매매 전략**: 향후 3개월 내 기본 시나리오 기준 약 **{f3['base_price_str']}** 형성 가능성이 높으며, 상단 돌파 시 **{f3['bull_price_str']}**까지 상승 여력이 존재합니다.
                - **중장기 1년 시세 밴드**: **{f12['bear_price_str']} (보수 하방 지지선) ~ {f12['bull_price_str']} (상승 목표가)** 범위 내에서 형성될 것으로 예상됩니다.
                - **투자 리스크 요인**: 본 모델은 과거 국토교통부 실거래가의 시간 가중 통계 회귀 모델에 기반하며, 한국은행 기준금리 변동, DSR 대출 규제 정책 및 지역 입주 물량 등 거시적 변수에 따라 실제 거래가격에 차이가 발생할 수 있습니다.
                """)


# -------------------------------------------------------------
# TAB 3: 실거래 알림 & 관심단지 관리
# -------------------------------------------------------------
with tab3:
    st.markdown("##### 🔔 최근 등록된 주요 실거래가 알림 피드")
    
    recent_alerts = get_recent_alerts(limit=15)
    if recent_alerts:
        for alert in recent_alerts:
            st.markdown(f"""
            <div class="alert-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>{alert['alert_type']}</strong>
                    <span style="font-size: 0.8rem; color: #718096;">{alert['deal_date']}</span>
                </div>
                <div style="margin-top: 4px; color: #2d3748; font-size: 0.95rem;">
                    {alert['message']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("아직 등록된 알림이 없습니다.")
        
    st.divider()
    
    st.markdown("##### 📌 관심 단지 목록 관리")
    w_df = pd.DataFrame(watchlist)
    if not w_df.empty:
        w_df_display = w_df[["id", "complex_name", "region_name", "dong", "build_year", "total_households", "memo"]].rename(
            columns={
                "id": "ID",
                "complex_name": "단지명",
                "region_name": "지역",
                "dong": "법정동",
                "build_year": "준공년도",
                "total_households": "세대수",
                "memo": "메모"
            }
        )
        st.dataframe(w_df_display, use_container_width=True, hide_index=True)
        
        # 단지 삭제
        c_del1, c_del2 = st.columns([3, 1])
        with c_del1:
            del_id = st.selectbox("삭제할 관심 단지 ID 선택", options=w_df["id"].tolist(), format_func=lambda x: f"ID {x}: {w_df[w_df['id']==x]['complex_name'].values[0]}")
        with c_del2:
            st.write("")
            st.write("")
            if st.button("관심 단지 삭제", type="primary", use_container_width=True):
                remove_from_watchlist(del_id)
                st.success("관심 단지가 삭제되었습니다.")
                st.rerun()


# -------------------------------------------------------------
# TAB 4: 데이터 수집 & 내보내기
# -------------------------------------------------------------
with tab4:
    st.markdown("##### 🌐 공공데이터포털 실거래가 API 연동 & 데이터 관리")
    
    col_api1, col_api2 = st.columns(2)
    with col_api1:
        st.markdown("###### 1. 국토교통부 OpenAPI 실시간 수집")
        service_key = st.text_input("공공데이터포털 API 인증키 (ServiceKey)", type="password", help="공공데이터포털(data.go.kr)에서 발급받은 '국토교통부 아파트매매 실거래 상세자료' API 키")
        target_ym = st.text_input("수집 대상 년월 (YYYYMM)", value=datetime.now().strftime("%Y%m"))
        
        if st.button("공공데이터 API 실거래가 수집 실행", use_container_width=True):
            if not service_key:
                st.error("공공데이터 API 인증키를 입력해주세요.")
            else:
                with st.spinner("국토교통부 API로부터 실거래 데이터를 수집 중입니다..."):
                    if complex_info:
                        reg_cd = complex_info["region_code"]
                        fetched = fetch_molit_api(service_key, reg_cd, target_ym)
                        if fetched:
                            count = insert_transactions(fetched)
                            detect_and_log_alerts()
                            st.success(f"{len(fetched)}건의 데이터를 조회하여 {count}건의 신규 실거래가를 저장했습니다!")
                            st.rerun()
                        else:
                            st.warning("해당 년월에 조회된 데이터가 없거나 인증키가 유효하지 않습니다.")
                            
    with col_api2:
        st.markdown("###### 2. 국토교통부 검증 실거래가 데이터 동기화")
        st.caption("국토교통부 실거래가 공개시스템 기반 검증 데이터셋으로 데이터베이스를 즉시 리셋/동기화합니다.")
        if st.button("🔄 검증 실거래가 데이터셋으로 100% 동기화", use_container_width=True):
            with st.spinner("검증 실거래가 데이터를 로드하고 통계를 갱신 중입니다..."):
                import sqlite3
                from config import DB_PATH
                with sqlite3.connect(str(DB_PATH)) as conn:
                    conn.cursor().execute("DELETE FROM transactions")
                    conn.commit()
                count = load_real_data_into_db()
                st.success(f"국토교통부 검증 실거래 데이터 {count}건으로 100% 동기화 완료!")
                st.rerun()
                
    st.divider()
    
    st.markdown("##### 📥 수집 데이터 내보내기 (Export)")
    
    # 내보내기용 정돈된 한글 컬럼 데이터프레임 생성
    export_df = df_filtered.sort_values("deal_date", ascending=False).copy()
    export_df["거래일자"] = export_df["deal_date"].dt.strftime("%Y-%m-%d")
    export_df["단지명"] = export_df["complex_name"]
    export_df["지역"] = export_df.get("region_name", "")
    export_df["법정동"] = export_df.get("dong", "")
    export_df["전용면적(㎡)"] = export_df["exclusive_area"]
    export_df["평수(평)"] = export_df["exclusive_area"].apply(sqm_to_pyeong)
    export_df["층수"] = export_df["floor"].apply(lambda x: f"{x}층")
    export_df["거래금액(만원)"] = export_df["deal_amount"]
    export_df["거래금액(한글)"] = export_df["deal_amount"].apply(format_price_krw)
    export_df["거래유형"] = export_df.get("req_gbn", "중개거래").fillna("중개거래")
    export_df["중개사소재지"] = export_df.get("rdealer_lawdnm", "현지 중개사").fillna("현지 중개사")
    export_df["건축년도"] = export_df.get("build_year", "-")
    
    export_cols = [
        "거래일자", "단지명", "지역", "법정동", "전용면적(㎡)", "평수(평)",
        "층수", "거래금액(만원)", "거래금액(한글)", "거래유형", "중개사소재지", "건축년도"
    ]
    final_export_df = export_df[export_cols]
    
    exp_col1, exp_col2 = st.columns(2)
    
    # 1. CSV Download (Excel 한글 깨짐 완벽 방지: utf-8-sig 바이트 인코딩)
    csv_bytes = final_export_df.to_csv(index=False).encode("utf-8-sig")
    with exp_col1:
        st.download_button(
            label="📄 현재 단지 실거래가 CSV 다운로드",
            data=csv_bytes,
            file_name=f"{selected_complex}_실거래가_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv; charset=utf-8-sig",
            use_container_width=True
        )
        
    # 2. Excel Download
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        final_export_df.to_excel(writer, index=False, sheet_name="실거래가_내역")
    excel_bytes = excel_buffer.getvalue()
    
    with exp_col2:
        st.download_button(
            label="📊 현재 단지 실거래가 Excel 다운로드",
            data=excel_bytes,
            file_name=f"{selected_complex}_실거래가_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
