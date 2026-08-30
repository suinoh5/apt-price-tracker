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
from analyzer import (
    calculate_complex_metrics, 
    add_moving_averages, 
    calculate_rsi, 
    calculate_supply_demand_metrics,
    get_regional_macro_timeseries,
    get_regional_head_to_head,
    get_area_mix_distribution,
    get_dong_price_leaderboard,
    get_complex_ath_recovery_leaderboard
)
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

# Auto-seed verified real transactions
with st.spinner("국토교통부 검증 실거래가 데이터베이스를 동기화 중입니다..."):
    sample_check = get_transactions_df()
    if len(sample_check) < 130:
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
    
    if len(df_filtered) < 3:
        st.info("신뢰도 높은 AI 시세 예측 및 매매 분석을 위해 최소 3건 이상의 실거래 데이터가 필요합니다.")
    else:
        # 단지 세대수
        households = complex_info.get("total_households", 1000) if complex_info else 1000
        
        # 1. AI 지표 계산
        with st.spinner("AI 투자 매력도 및 3대 시나리오 전망 모델을 연산 중입니다..."):
            pred_res = predict_future_prices(df_filtered, forecast_days=365)
            rsi_data = calculate_rsi(df_filtered)
            sn_data = calculate_supply_demand_metrics(df_filtered, total_households=households)
            
            if pred_res.get("success", False):
                inv_score = calculate_investment_score(
                    metrics=metrics,
                    rsi_data=rsi_data,
                    supply_demand=sn_data,
                    momentum_pct=pred_res.get("recent_momentum_pct", 0.0)
                )
            else:
                inv_score = None
            
        if pred_res.get("success", False) and inv_score:
            # =========================================================
            # 🏆 SECTION 1: 종합 AI 투자 매력도 & 부동산 RSI 계기판
            # =========================================================
            c_score1, c_score2 = st.columns([1.2, 1])
            
            with c_score1:
                st.markdown(f"""
                <div class="score-card">
                    <div style="font-size: 0.95rem; font-weight: 700; color: #4a5568; margin-bottom: 6px;">
                        🏆 종합 AI 부동산 투자 매력도 점수
                    </div>
                    <div style="display: flex; align-items: baseline; justify-content: center; gap: 8px;">
                        <span class="score-number">{inv_score['total_score']}</span>
                        <span style="font-size: 1.3rem; color: #718096; font-weight: 600;">/ 100점</span>
                    </div>
                    <div style="margin-top: 4px;">
                        <span class="score-grade" style="color: {inv_score['color']};">
                            {inv_score['grade']} ({inv_score['action']})
                        </span>
                    </div>
                    <div class="score-desc">
                        {inv_score['desc']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 4대 팩터별 세부 레이더/프로그레스 바
                st.write("")
                st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#4a5568; margin-bottom:4px;'>📊 4대 팩터별 세부 점수</div>", unsafe_allow_html=True)
                for f_name, f_val in inv_score["factors"].items():
                    f_col1, f_col2 = st.columns([2, 1])
                    with f_col1:
                        st.progress(f_val / 100, text=f_name)
                    with f_col2:
                        st.markdown(f"<div style='text-align:right; font-weight:700; color:#2b6cb0; font-size:0.9rem;'>{f_val}점</div>", unsafe_allow_html=True)

            with c_score2:
                st.markdown(f"""
                <div class="rsi-gauge-card">
                    <div style="font-size: 0.95rem; font-weight: 700; color: #4a5568; margin-bottom: 6px;">
                        🧭 부동산 시장 RSI (상대강도지수)
                    </div>
                    <div class="rsi-value" style="color: {rsi_data['color']};">
                        {rsi_data['rsi']}
                    </div>
                    <div class="rsi-status" style="color: {rsi_data['color']};">
                        {rsi_data['status']}
                    </div>
                    <div style="font-size: 0.85rem; color: #718096; line-height: 1.4; margin-top: 6px;">
                        {rsi_data['desc']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 게이지 바 시각화
                st.write("")
                st.progress(rsi_data["rsi"] / 100, text="RSI 과열/침체 계기판 (0: 극심한 침체 / 100: 단기 과열)")
                st.caption("• 70 이상: 단기 과열 (추격 매수 유의) | • 30 이하: 과매도 저평가 (저점 매수 기회)")

            # =========================================================
            # 🌊 SECTION 2: 거래 회전율 & 실거래 수급 에너지 분석
            # =========================================================
            st.markdown("---")
            st.markdown("##### 🌊 거래 회전율 & 실거래 수급 에너지 분석")
            
            c_sd1, c_sd2, c_sd3, c_sd4 = st.columns(4)
            with c_sd1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">최근 6개월 거래 회전율</div>
                    <div class="metric-value">{sn_data.get('turnover_rate_str', '0%')}</div>
                    <div class="metric-sub">
                        <span>총 {households:,}세대 중 {sn_data.get('tx_count_6m', 0)}건 손바뀜</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with c_sd2:
                adv_ratio = sn_data.get('advance_ratio', 50)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">상승 거래 비중</div>
                    <div class="metric-value" style="color: {'#e53e3e' if adv_ratio >= 60 else '#2d3748'};">{adv_ratio}%</div>
                    <div class="metric-sub">
                        <span>직전가 대비 상승 체결 비율</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with c_sd3:
                dec_ratio = sn_data.get('decline_ratio', 50)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">하락/조정 거래 비중</div>
                    <div class="metric-value" style="color: {'#3182ce' if dec_ratio >= 60 else '#2d3748'};">{dec_ratio}%</div>
                    <div class="metric-sub">
                        <span>직전가 대비 하락 체결 비율</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with c_sd4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">평균 거래 발생 주기</div>
                    <div class="metric-value">{sn_data.get('avg_interval_days', 30)}일</div>
                    <div class="metric-sub">
                        <span>신규 계약 체결 평균 소요 시간</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # =========================================================
            # 🎯 SECTION 3: 3대 시나리오 미래 전망 차트 & 예측 비교표
            # =========================================================
            st.markdown("---")
            st.markdown("##### 🎯 3대 시나리오(Bull / Base / Bear) 기반 시세 예측 전망")
            st.caption("과거 3개년 시계열 가중 추세 모델에 거시 유동성 및 가격 저평가 밴드를 복합 적용한 시뮬레이션입니다.")
            
            future_df = pred_res["future_df"]
            hist_fit_df = pred_res["historical_fit_df"]
            
            fig_sc = go.Figure()
            
            # 1. 과거 실거래 체결가 포인트
            fig_sc.add_trace(go.Scatter(
                x=df_filtered["deal_date"], y=df_filtered["deal_amount"] / 10000,
                mode="markers", name="실제 실거래가",
                marker=dict(size=7, color="#2b6cb0", opacity=0.8),
                hovertemplate="<b>일자</b>: %{x|%Y-%m-%d}<br><b>실거래가</b>: %{y:.2f}억원<extra></extra>"
            ))
            
            # 2. 과거 추세선
            fig_sc.add_trace(go.Scatter(
                x=hist_fit_df["deal_date"], y=hist_fit_df["fitted_price"] / 10000,
                mode="lines", name="과거 추세선",
                line=dict(color="#a0aec0", width=1.5, dash="dot"),
                hoverinfo="skip"
            ))
            
            # 3. 🚀 상승 시나리오 (Bull)
            fig_sc.add_trace(go.Scatter(
                x=future_df["deal_date"], y=future_df["bull_price"] / 10000,
                mode="lines", name="🚀 상승 시나리오 (Bull)",
                line=dict(color="#e53e3e", width=2.5, dash="dash"),
                hovertemplate="<b>일자</b>: %{x|%Y-%m-%d}<br><b>Bull 예상가</b>: %{y:.2f}억원<extra></extra>"
            ))
            
            # 4. 🎯 기본 시나리오 (Base)
            fig_sc.add_trace(go.Scatter(
                x=future_df["deal_date"], y=future_df["base_price"] / 10000,
                mode="lines", name="🎯 기본 시나리오 (Base)",
                line=dict(color="#38a169", width=3),
                hovertemplate="<b>일자</b>: %{x|%Y-%m-%d}<br><b>Base 예상가</b>: %{y:.2f}억원<extra></extra>"
            ))
            
            # 5. 🛡️ 보수 시나리오 (Bear)
            fig_sc.add_trace(go.Scatter(
                x=future_df["deal_date"], y=future_df["bear_price"] / 10000,
                mode="lines", name="🛡️ 보수 시나리오 (Bear)",
                line=dict(color="#718096", width=2, dash="dot"),
                hovertemplate="<b>일자</b>: %{x|%Y-%m-%d}<br><b>Bear 예상가</b>: %{y:.2f}억원<extra></extra>"
            ))
            
            # 신뢰구간 음영
            fig_sc.add_trace(go.Scatter(
                x=pd.concat([future_df["deal_date"], future_df["deal_date"].iloc[::-1]]),
                y=pd.concat([future_df["bull_price"], future_df["bear_price"].iloc[::-1]]) / 10000,
                fill="toself",
                fillcolor="rgba(56, 161, 105, 0.08)",
                line=dict(color="rgba(255,255,255,0)"),
                hoverinfo="skip",
                showlegend=False,
                name="예측 밴드"
            ))
            
            fig_sc.update_layout(
                height=420,
                margin=dict(l=15, r=15, t=25, b=15),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            fig_sc.update_xaxes(showgrid=True, gridcolor="#edf2f7")
            fig_sc.update_yaxes(showgrid=True, gridcolor="#edf2f7")
            
            st.plotly_chart(fig_sc, use_container_width=True, config={"scrollZoom": False, "displayModeBar": False})


# -------------------------------------------------------------
# TAB 3: 🌐 18개년 지역 빅데이터 & 매크로 분석
# -------------------------------------------------------------
with tab3:
    st.markdown("##### 🌐 경기 남부 핵심 벨트 (화성시 병점 · 용인 처인구) 18개년(2006~2024) 실거래 빅데이터 분석")
    st.caption("국토교통부 224개월 전수 실거래 데이터(85,000+건) 기반 매크로 시세 사이클, 반도체 벨트 맞비교, 평형대 믹스 및 동별 시세 지도")
    
    # 컨트롤 바
    c_m_reg, c_m_year = st.columns([1.5, 2.5])
    with c_m_reg:
        macro_reg_opt = st.selectbox(
            "분석 대상 권역 선택",
            options=["통합 (화성시 병점 + 용인 처인구)", "경기 화성시 (병점·동부 권역)", "경기 용인시 처인구"],
            index=0
        )
        reg_code_map = {
            "통합 (화성시 병점 + 용인 처인구)": None,
            "경기 화성시 (병점·동부 권역)": "41595",
            "경기 용인시 처인구": "41461"
        }
        sel_macro_reg_code = reg_code_map[macro_reg_opt]
        
    with c_m_year:
        year_range = st.slider(
            "시계열 분석 기간 범위 (년도)",
            min_value=2006,
            max_value=2026,
            value=(2006, 2026),
            step=1
        )
        
    # =========================================================
    # 📊 SECTION 1: 18개년 매크로 시세 사이클 & 거래량 타임라인 (Dual-Axis)
    # =========================================================
    st.markdown("---")
    st.markdown("##### 📊 1. 18개년 평당 시세 & 거래량 매크로 사이클 (거시 경제 이벤트 맵)")
    
    macro_df = get_regional_macro_timeseries(sel_macro_reg_code)
    if not macro_df.empty:
        macro_filtered = macro_df[
            (macro_df["deal_year"] >= year_range[0]) & 
            (macro_df["deal_year"] <= year_range[1])
        ].copy()
        
        fig_macro = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=("월별 평균 평당가 (만원 / 3.3㎡)", "월별 총 거래량 (건)"),
            row_heights=[0.7, 0.3]
        )
        
        # 1. 평당가 Line & Fill
        fig_macro.add_trace(
            go.Scatter(
                x=macro_filtered["deal_ym"],
                y=macro_filtered["avg_pyeong_price"],
                mode="lines",
                name="평균 평당가",
                line=dict(color="#2b6cb0", width=2.5),
                fill="tozeroy",
                fillcolor="rgba(43, 108, 176, 0.08)",
                hovertemplate="<b>%{x}</b><br>평균 평당가: <b>%{y:,.1f}만원/평</b><extra></extra>"
            ),
            row=1, col=1
        )
        
        # 2. 거래량 Bar
        fig_macro.add_trace(
            go.Bar(
                x=macro_filtered["deal_ym"],
                y=macro_filtered["trade_count"],
                name="월별 거래량",
                marker_color="#a0aec0",
                opacity=0.7,
                hovertemplate="<b>%{x}</b><br>거래량: <b>%{y:,}건</b><extra></extra>"
            ),
            row=2, col=1
        )
        
        # 주요 거시 경제 이벤트 음영 구간 하이라이트
        events = [
            {"x0": "2008-09", "x1": "2009-06", "label": "글로벌 금융위기", "color": "rgba(229, 62, 62, 0.12)"},
            {"x0": "2013-01", "x1": "2013-12", "label": "취득세 감면 바닥기", "color": "rgba(49, 151, 149, 0.12)"},
            {"x0": "2017-06", "x1": "2021-10", "label": "대세상승 유동성장", "color": "rgba(221, 107, 32, 0.12)"},
            {"x0": "2022-01", "x1": "2023-01", "label": "금리인상 조정기", "color": "rgba(113, 128, 150, 0.15)"},
            {"x0": "2024-01", "x1": "2026-08", "label": "반도체벨트 신고가장", "color": "rgba(56, 161, 105, 0.12)"}
        ]
        for ev in events:
            fig_macro.add_vrect(
                x0=ev["x0"], x1=ev["x1"],
                fillcolor=ev["color"], layer="below", line_width=0,
                annotation_text=ev["label"], annotation_position="top left",
                annotation=dict(font_size=10, font_color="#4a5568")
            )
            
        fig_macro.update_layout(
            height=460,
            margin=dict(l=15, r=15, t=35, b=15),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        fig_macro.update_xaxes(showgrid=True, gridcolor="#edf2f7")
        fig_macro.update_yaxes(showgrid=True, gridcolor="#edf2f7")
        
        st.plotly_chart(fig_macro, use_container_width=True, config={"scrollZoom": False, "displayModeBar": False})
    else:
        st.info("선택된 조건의 매크로 데이터가 없습니다.")

    # =========================================================
    # ⚔️ SECTION 2: 경기 남부 반도체 벨트 맞비교: 화성시 vs 용인 처인구
    # =========================================================
    st.markdown("---")
    st.markdown("##### ⚔️ 2. 경기 남부 반도체 벨트 맞비교: 화성시 vs 용인 처인구")
    
    h2h_data = get_regional_head_to_head()
    if h2h_data:
        c_h1, c_h2, c_h3, c_h4 = st.columns(4)
        with c_h1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">화성시 (병점) 18개년 상승률</div>
                <div class="metric-value">+{h2h_data['hw_growth']}%</div>
                <div class="metric-sub">
                    <span>평당 {h2h_data['hw_start_pyeong']:,}만 ➔ {h2h_data['hw_end_pyeong']:,}만원</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_h2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">용인 처인구 18개년 상승률</div>
                <div class="metric-value">+{h2h_data['yi_growth']}%</div>
                <div class="metric-sub">
                    <span>평당 {h2h_data['yi_start_pyeong']:,}만 ➔ {h2h_data['yi_end_pyeong']:,}만원</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_h3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">총 누적 실거래 확보량</div>
                <div class="metric-value">{h2h_data['hw_total_trades'] + h2h_data['yi_total_trades']:,}건</div>
                <div class="metric-sub">
                    <span>화성 {h2h_data['hw_total_trades']:,}건 / 처인 {h2h_data['yi_total_trades']:,}건</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_h4:
            spread = h2h_data['hw_end_pyeong'] - h2h_data['yi_end_pyeong']
            spread_sign = "+" if spread > 0 else ""
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">현재 평당 시세 격차 (Gap)</div>
                <div class="metric-value">{spread_sign}{spread:,}만원</div>
                <div class="metric-sub">
                    <span>화성시 평당가 우위 스프레드</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        # 연도별 비교 추이 차트
        cmp_df = h2h_data["yearly_comparison_df"]
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Scatter(
            x=cmp_df["deal_year"], y=cmp_df["hw_pyeong"],
            mode="lines+markers", name="화성시 (병점)",
            line=dict(color="#3182ce", width=3),
            marker=dict(size=6)
        ))
        fig_cmp.add_trace(go.Scatter(
            x=cmp_df["deal_year"], y=cmp_df["yi_pyeong"],
            mode="lines+markers", name="용인시 처인구",
            line=dict(color="#dd6b20", width=3),
            marker=dict(size=6)
        ))
        fig_cmp.update_layout(
            title="화성시 vs 용인 처인구 연도별 평균 평당가 추이 비교 (만원 / 평)",
            height=350,
            margin=dict(l=15, r=15, t=40, b=15),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        fig_cmp.update_xaxes(showgrid=True, gridcolor="#edf2f7", dtick=1)
        fig_cmp.update_yaxes(showgrid=True, gridcolor="#edf2f7")
        st.plotly_chart(fig_cmp, use_container_width=True, config={"scrollZoom": False, "displayModeBar": False})

    # =========================================================
    # 🧩 SECTION 3: 18개년 평형대별 거래 비중 변화 (Area Mix)
    # =========================================================
    st.markdown("---")
    st.markdown("##### 🧩 3. 18개년 시대별 평형대 거래 비중 변화 (Area Mix)")
    st.caption("소형(전용 59㎡ 이하), 국민평형(59~85㎡), 대형(85㎡ 초과)의 연도별 거래 쏠림 현상 추이")
    
    area_mix_df = get_area_mix_distribution(sel_macro_reg_code)
    if not area_mix_df.empty:
        fig_area = go.Figure()
        color_map = {
            "소형 (59㎡ 이하)": "#4299e1",
            "중형 (59~85㎡ 국평)": "#38a169",
            "대형 (85㎡ 초과)": "#805ad5"
        }
        for cat in ["소형 (59㎡ 이하)", "중형 (59~85㎡ 국평)", "대형 (85㎡ 초과)"]:
            sub = area_mix_df[area_mix_df["area_category"] == cat]
            if not sub.empty:
                fig_area.add_trace(go.Bar(
                    x=sub["deal_year"],
                    y=sub["share_pct"],
                    name=cat,
                    marker_color=color_map.get(cat, "#718096"),
                    hovertemplate="<b>%{x}년 " + cat + "</b><br>거래 비중: <b>%{y:.1f}%</b><extra></extra>"
                ))
        fig_area.update_layout(
            barmode="stack",
            height=340,
            margin=dict(l=15, r=15, t=20, b=15),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        fig_area.update_xaxes(showgrid=True, gridcolor="#edf2f7", dtick=1)
        fig_area.update_yaxes(showgrid=True, gridcolor="#edf2f7", range=[0, 100], ticksuffix="%")
        st.plotly_chart(fig_area, use_container_width=True, config={"scrollZoom": False, "displayModeBar": False})

    # =========================================================
    # 🏆 SECTION 4: 읍·면·동별 시세 랭킹 & 2021년 역대 최고가(ATH) 회복률 리더보드
    # =========================================================
    st.markdown("---")
    st.markdown("##### 🏆 4. 읍·면·동별 평당 시세 랭킹 & 역대 최고가(ATH) 회복률 리더보드")
    
    col_rank1, col_rank2 = st.columns(2)
    with col_rank1:
        st.markdown("###### 📍 법정동별 평균 평당가 순위 TOP 12")
        dong_df = get_dong_price_leaderboard(sel_macro_reg_code, top_n=12)
        if not dong_df.empty:
            fig_dong = go.Figure(go.Bar(
                x=dong_df["avg_pyeong_price"],
                y=dong_df["dong"] + " (" + dong_df["region_name"] + ")",
                orientation="h",
                marker_color="#3182ce",
                text=[f"{v:,.0f}만" for v in dong_df["avg_pyeong_price"]],
                textposition="auto",
                hovertemplate="<b>%{y}</b><br>평당가: %{x:,.1f}만원/평<extra></extra>"
            ))
            fig_dong.update_layout(
                height=420,
                margin=dict(l=15, r=15, t=10, b=15),
                yaxis=dict(autorange="reversed"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            fig_dong.update_xaxes(showgrid=True, gridcolor="#edf2f7")
            st.plotly_chart(fig_dong, use_container_width=True, config={"scrollZoom": False, "displayModeBar": False})
            
    with col_rank2:
        st.markdown("###### 🚀 주요 단지별 2021년 전고점(ATH) 대비 현재 회복률 TOP 15")
        rec_df = get_complex_ath_recovery_leaderboard(sel_macro_reg_code, top_n=15)
        if not rec_df.empty:
            rec_display = rec_df[["complex_name", "dong", "region_label", "ath_price", "latest_price", "recovery_rate"]].copy()
            rec_display["ath_price_str"] = rec_display["ath_price"].apply(format_price_krw)
            rec_display["latest_price_str"] = rec_display["latest_price"].apply(format_price_krw)
            rec_display["recovery_rate_str"] = rec_display["recovery_rate"].apply(lambda x: f"{x:.1f}%")
            
            table_show = rec_display[["complex_name", "dong", "region_label", "ath_price_str", "latest_price_str", "recovery_rate_str"]].rename(
                columns={
                    "complex_name": "단지명",
                    "dong": "법정동",
                    "region_label": "지역",
                    "ath_price_str": "역대 최고가 (ATH)",
                    "latest_price_str": "최근 실거래가",
                    "recovery_rate_str": "전고점 회복률"
                }
            )
            st.dataframe(table_show, use_container_width=True, hide_index=True, height=420)


# -------------------------------------------------------------
# TAB 4: 실거래 알림 & 관심단지 관리
# -------------------------------------------------------------
with tab4:
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
                with st.spinner(f"국토교통부 API로부터 {target_ym} 실거래 데이터를 수집 중입니다..."):
                    try:
                        if complex_info:
                            reg_cd = complex_info.get("region_code", "41595")
                            fetched = fetch_molit_api(service_key, reg_cd, target_ym)
                            if fetched:
                                count = insert_transactions(fetched)
                                detect_and_log_alerts()
                                matching = [tx for tx in fetched if complex_info["complex_name"] in tx["complex_name"]]
                                st.success(f"🎉 국토교통부 API로부터 {complex_info['region_name']} 총 {len(fetched)}건 조회 성공! ('{complex_info['complex_name']}' {len(matching)}건 포함, 신규 {count}건 저장 완료)")
                                st.rerun()
                            else:
                                st.warning(f"⚠️ {target_ym} 년월에 국토교통부에서 조회된 데이터가 없거나 인증키가 유효하지 않습니다.")
                    except Exception as e:
                        st.error(f"데이터 수집 및 저장 처리 중 예외 발생: {e}")
                            
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
