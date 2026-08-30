"""
Apt Price Tracker - Statistical Analysis Engine
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


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """거래일에 기반한 이동평균선(30일, 90일, 180일) 및 추세선 산출"""
    if df.empty:
        return df
        
    df_sorted = df.sort_values("deal_date").copy()
    
    # 일별 평균 거래가격으로 리샘플링 후 롤링
    daily_df = df_sorted.groupby(df_sorted["deal_date"].dt.date)["deal_amount"].mean().reset_index()
    daily_df["deal_date"] = pd.to_datetime(daily_df["deal_date"])
    daily_df = daily_df.set_index("deal_date").asfreq("D").interpolate(method="time")
    
    daily_df["ma_30"] = daily_df["deal_amount"].rolling(window=30, min_periods=5).mean()
    daily_df["ma_90"] = daily_df["deal_amount"].rolling(window=90, min_periods=10).mean()
    daily_df["ma_180"] = daily_df["deal_amount"].rolling(window=180, min_periods=15).mean()
    
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
