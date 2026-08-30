"""
Apt Price Tracker - 18-Year Regional Big Data & Macro Analysis Page
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import format_price_krw
from analyzer import (
    get_regional_macro_timeseries,
    get_regional_head_to_head,
    get_area_mix_distribution,
    get_dong_price_leaderboard,
    get_complex_ath_recovery_leaderboard
)


def render_macro_page():
    """18개년 지역 빅데이터 & 매크로 분석 독립 페이지 렌더링"""
    st.markdown("### 🌐 경기 남부 핵심 벨트 (화성시 병점 · 용인 처인구) 18개년 실거래 빅데이터 분석")
    st.caption("국토교통부 224개월 전수 실거래 데이터(85,000+건) 기반 매크로 시세 사이클, 반도체 벨트 맞비교, 평형대 믹스 및 동별 시세 지도")
    
    # 상단 컨트롤 바
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
