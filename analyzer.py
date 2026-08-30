"""
Apt Price Tracker - Statistical Analysis & Proptech Metrics Engine
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from config import sqm_to_pyeong, format_price_krw


def calculate_complex_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    특정 단지 및 평형의 실거래 데이터프레임으로부터 핵심 지표(최근가, 전고점, 평당가, 변동률 등) 산출
    """
    if df.empty:
        return {}
        
    df_sorted = df.sort_values("deal_date", ascending=True).copy()
    
    # 1. 최근 거래 정보
    recent_deal = df_sorted.iloc[-1]
    recent_price = int(recent_deal["deal_amount"])
    recent_date = recent_deal["deal_date"].strftime("%Y-%m-%d")
    recent_floor = int(recent_deal["floor"])
    recent_area = float(recent_deal["exclusive_area"])
    recent_pyeong = sqm_to_pyeong(recent_area)
    
    # 3.3㎡당 단가 (만원 / 평)
    price_per_pyeong = round(recent_price / recent_pyeong) if recent_pyeong > 0 else 0
    
    # 2. 직전 거래 대비 변동
    if len(df_sorted) > 1:
        prev_deal = df_sorted.iloc[-2]
        prev_price = int(prev_deal["deal_amount"])
        diff_price = recent_price - prev_price
        diff_pct = round((diff_price / prev_price) * 100, 2)
    else:
        diff_price = 0
        diff_pct = 0.0
        
    # 3. 역대 최고가(전고점) 및 최고가 대비 하락률
    ath_idx = df_sorted["deal_amount"].idxmax()
    ath_deal = df_sorted.loc[ath_idx]
    ath_price = int(ath_deal["deal_amount"])
    ath_date = ath_deal["deal_date"].strftime("%Y-%m-%d")
    ath_floor = int(ath_deal["floor"])
    
    ath_diff_pct = round(((recent_price - ath_price) / ath_price) * 100, 2)
    
    # 4. 최근 1년 최저가
    one_year_ago = df_sorted["deal_date"].max() - pd.Timedelta(days=365)
    df_1y = df_sorted[df_sorted["deal_date"] >= one_year_ago]
    if not df_1y.empty:
        low_1y_idx = df_1y["deal_amount"].idxmin()
        low_1y_deal = df_1y.loc[low_1y_idx]
        low_1y_price = int(low_1y_deal["deal_amount"])
        low_1y_date = low_1y_deal["deal_date"].strftime("%Y-%m-%d")
        low_1y_diff_pct = round(((recent_price - low_1y_price) / low_1y_price) * 100, 2)
    else:
        low_1y_price = recent_price
        low_1y_date = recent_date
        low_1y_diff_pct = 0.0
        
    # 5. 총 거래 건수 및 평균 거래가
    total_trades = len(df_sorted)
    avg_price = int(round(df_sorted["deal_amount"].mean()))
    
    return {
        "recent_price": recent_price,
        "recent_price_str": format_price_krw(recent_price),
        "recent_date": recent_date,
        "recent_floor": recent_floor,
        "recent_area": recent_area,
        "recent_pyeong": recent_pyeong,
        "price_per_pyeong": price_per_pyeong,
        "price_per_pyeong_str": f"{price_per_pyeong:,}만원/평",
        "diff_price": diff_price,
        "diff_pct": diff_pct,
        "ath_price": ath_price,
        "ath_price_str": format_price_krw(ath_price),
        "ath_date": ath_date,
        "ath_floor": ath_floor,
        "ath_diff_pct": ath_diff_pct,
        "low_1y_price": low_1y_price,
        "low_1y_price_str": format_price_krw(low_1y_price),
        "low_1y_date": low_1y_date,
        "low_1y_diff_pct": low_1y_diff_pct,
        "total_trades": total_trades,
        "avg_price": avg_price,
        "avg_price_str": format_price_krw(avg_price),
    }


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
    """
    부동산 실거래가 기반 상대강도지수(RSI, 0~100) 산출
    - 70 이상: 단기 과열 (추격 매수 주의)
    - 35 이하: 과매도 / 바닥권 (저가 매수 구간)
    - 35~70: 적정 / 중립 구간
    """
    if df.empty or len(df) < 3:
        return {
            "rsi": 50.0,
            "status": "⚖️ 중립 / 적정 구간",
            "color": "#4a5568",
            "desc": "거래 건수가 누적되는 중입니다. 안정적인 횡보 흐름을 보이고 있습니다."
        }
        
    df_sorted = df.sort_values("deal_date").copy()
    diffs = df_sorted["deal_amount"].diff().dropna()
    
    recent_diffs = diffs.tail(period)
    gains = recent_diffs[recent_diffs > 0].sum()
    losses = abs(recent_diffs[recent_diffs < 0].sum())
    
    if losses == 0 and gains > 0:
        rsi = 85.0
    elif gains == 0 and losses > 0:
        rsi = 20.0
    elif gains == 0 and losses == 0:
        rsi = 50.0
    else:
        rs = gains / losses
        rsi = round(100.0 - (100.0 / (1.0 + rs)), 1)
        
    rsi = max(10.0, min(95.0, rsi))
    
    if rsi >= 70.0:
        status = "🔥 단기 과열 구간 (Overbought)"
        color = "#e53e3e"
        desc = "최근 체결 가격이 가파르게 상승하여 과열권에 진입했습니다. 단기 추격 매수보다는 숨고르기 지지선 형성을 지켜보는 것이 유리합니다."
    elif rsi <= 35.0:
        status = "💎 과매도 / 바닥권 (Oversold)"
        color = "#3182ce"
        desc = "낙폭이 과대하여 장기 저점에 근접한 바닥권 구간입니다. 가격 메리트가 높아 분할 매수 관점에서 유리한 시점입니다."
    else:
        status = "⚖️ 적정 / 중립 구간 (Neutral)"
        color = "#38a169"
        desc = "매수세와 매도세가 균형을 이루며 안정적인 시세를 형성하고 있는 건강한 구간입니다."
        
    return {
        "rsi": rsi,
        "status": status,
        "color": color,
        "desc": desc
    }


def calculate_supply_demand_metrics(df: pd.DataFrame, total_households: int = 1000) -> Dict[str, Any]:
    """
    거래 회전율, 상승/하락 거래 비율, 평균 거래 주기 등 수급 에너지 지표 산출
    """
    if df.empty:
        return {}
        
    df_sorted = df.sort_values("deal_date").copy()
    
    # 1. 최근 6개월 거래 건수 및 세대수 대비 회전율
    six_months_ago = df_sorted["deal_date"].max() - pd.Timedelta(days=180)
    df_6m = df_sorted[df_sorted["deal_date"] >= six_months_ago]
    tx_count_6m = len(df_6m)
    
    households = total_households if total_households and total_households > 0 else 1000
    turnover_rate = round((tx_count_6m / households) * 100, 2)
    
    # 2. 상승거래 vs 하락거래 비율 (최근 15건 기준)
    recent_tx = df_sorted.tail(15).copy()
    diffs = recent_tx["deal_amount"].diff().dropna()
    
    up_count = int((diffs > 0).sum())
    down_count = int((diffs < 0).sum())
    flat_count = int((diffs == 0).sum())
    total_diff_count = len(diffs)
    
    if total_diff_count > 0:
        advance_ratio = round((up_count / total_diff_count) * 100, 1)
        decline_ratio = round((down_count / total_diff_count) * 100, 1)
    else:
        advance_ratio = 50.0
        decline_ratio = 50.0
        
    # 3. 평균 거래 발생 주기 (일수)
    if len(df_sorted) > 1:
        date_span_days = (df_sorted["deal_date"].max() - df_sorted["deal_date"].min()).days
        avg_interval_days = round(date_span_days / max(len(df_sorted) - 1, 1), 1)
    else:
        avg_interval_days = 30.0
        
    return {
        "tx_count_6m": tx_count_6m,
        "turnover_rate": turnover_rate,
        "turnover_rate_str": f"{turnover_rate:.2f}%",
        "advance_ratio": advance_ratio,
        "decline_ratio": decline_ratio,
        "up_count": up_count,
        "down_count": down_count,
        "flat_count": flat_count,
        "avg_interval_days": avg_interval_days,
    }


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """거래일에 기반한 이동평균선(30일, 90일, 180일) 및 추세선 산출"""
    if df.empty:
        return df
        
    df_sorted = df.sort_values("deal_date").copy()
    
    # 일별 평균 거래가격으로 리샘플링 후 롤링
    daily_df = df_sorted.groupby(df_sorted["deal_date"].dt.date)["deal_amount"].mean().reset_index()
    daily_df["deal_date"] = pd.to_datetime(daily_df["deal_date"])
    daily_df = daily_df.set_index("deal_date").asfreq("D").interpolate(method="time")
    
    daily_df["ma_30"] = daily_df["deal_amount"].rolling(window=30, min_periods=3).mean()
    daily_df["ma_90"] = daily_df["deal_amount"].rolling(window=90, min_periods=5).mean()
    daily_df["ma_180"] = daily_df["deal_amount"].rolling(window=180, min_periods=8).mean()
    
    # 원본 거래 데이터에 매핑
    df_sorted["deal_date_only"] = df_sorted["deal_date"].dt.date
    daily_df_reset = daily_df.reset_index()
    daily_df_reset["deal_date_only"] = daily_df_reset["deal_date"].dt.date
    
    merged = pd.merge(
        df_sorted,
        daily_df_reset[["deal_date_only", "ma_30", "ma_90", "ma_180"]],
        on="deal_date_only",
        how="left"
    ).drop(columns=["deal_date_only"])
    
    return merged
