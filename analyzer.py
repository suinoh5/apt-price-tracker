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


def get_regional_macro_timeseries(region_code: Optional[str] = None) -> pd.DataFrame:
    """
    18개년 월별 매크로 평당가, 거래량, 최고/최저가 시계열 집계
    """
    from database import get_connection
    where_clause = "WHERE is_cancel = 0"
    params = []
    if region_code:
        where_clause += " AND region_code = ?"
        params.append(region_code)
    else:
        where_clause += " AND region_code IN ('41595', '41461')"
        
    query = f"""
        SELECT 
            deal_year,
            deal_month,
            strftime('%Y-%m', deal_date) as deal_ym,
            COUNT(*) as trade_count,
            ROUND(AVG(deal_amount), 1) as avg_amount,
            ROUND(AVG(deal_amount / (exclusive_area / 3.305785)), 1) as avg_pyeong_price,
            MAX(deal_amount) as max_amount,
            MIN(deal_amount) as min_amount
        FROM transactions
        {where_clause}
        GROUP BY deal_year, deal_month
        ORDER BY deal_year ASC, deal_month ASC
    """
    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df


def get_regional_head_to_head() -> Dict[str, Any]:
    """
    경기 화성시(41595) vs 용인시 처인구(41461) 18개년 맞비교 지표 산출
    """
    from database import get_connection
    with get_connection() as conn:
        query = """
            SELECT 
                deal_year,
                region_code,
                COUNT(*) as trade_count,
                ROUND(AVG(deal_amount / (exclusive_area / 3.305785)), 1) as avg_pyeong_price,
                ROUND(AVG(deal_amount), 1) as avg_amount
            FROM transactions
            WHERE is_cancel = 0 AND region_code IN ('41595', '41461')
            GROUP BY deal_year, region_code
            ORDER BY deal_year ASC
        """
        df = pd.read_sql_query(query, conn)
        
    if df.empty:
        return {}
        
    hw_df = df[df["region_code"] == "41595"].copy()
    yi_df = df[df["region_code"] == "41461"].copy()
    
    def calc_cagr(sub_df):
        if len(sub_df) < 2:
            return 0.0, 0, 0
        p_start = sub_df.iloc[0]["avg_pyeong_price"]
        p_end = sub_df.iloc[-1]["avg_pyeong_price"]
        growth_pct = round(((p_end - p_start) / p_start) * 100, 1) if p_start > 0 else 0.0
        return growth_pct, int(p_start), int(p_end)
        
    hw_growth, hw_start, hw_end = calc_cagr(hw_df)
    yi_growth, yi_start, yi_end = calc_cagr(yi_df)
    
    merged_years = pd.merge(
        hw_df[["deal_year", "avg_pyeong_price", "trade_count"]].rename(columns={"avg_pyeong_price": "hw_pyeong", "trade_count": "hw_vol"}),
        yi_df[["deal_year", "avg_pyeong_price", "trade_count"]].rename(columns={"avg_pyeong_price": "yi_pyeong", "trade_count": "yi_vol"}),
        on="deal_year",
        how="outer"
    ).sort_values("deal_year").fillna(0)
    
    merged_years["spread_pyeong"] = merged_years["hw_pyeong"] - merged_years["yi_pyeong"]
    
    return {
        "hw_total_trades": int(hw_df["trade_count"].sum()) if not hw_df.empty else 0,
        "yi_total_trades": int(yi_df["trade_count"].sum()) if not yi_df.empty else 0,
        "hw_growth": hw_growth,
        "yi_growth": yi_growth,
        "hw_start_pyeong": hw_start,
        "hw_end_pyeong": hw_end,
        "yi_start_pyeong": yi_start,
        "yi_end_pyeong": yi_end,
        "yearly_comparison_df": merged_years
    }


def get_area_mix_distribution(region_code: Optional[str] = None) -> pd.DataFrame:
    """
    18개년 시대별 평형대(소형/중형 국평/대형) 거래 비중 및 평균 매매가
    """
    from database import get_connection
    where_clause = "WHERE is_cancel = 0"
    params = []
    if region_code:
        where_clause += " AND region_code = ?"
        params.append(region_code)
    else:
        where_clause += " AND region_code IN ('41595', '41461')"
        
    query = f"""
        SELECT 
            deal_year,
            CASE 
                WHEN exclusive_area <= 59.99 THEN '소형 (59㎡ 이하)'
                WHEN exclusive_area <= 85.0 THEN '중형 (59~85㎡ 국평)'
                ELSE '대형 (85㎡ 초과)'
            END as area_category,
            COUNT(*) as trade_count,
            ROUND(AVG(deal_amount), 1) as avg_price,
            ROUND(AVG(deal_amount / (exclusive_area / 3.305785)), 1) as avg_pyeong_price
        FROM transactions
        {where_clause}
        GROUP BY deal_year, area_category
        ORDER BY deal_year ASC
    """
    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
        
    if not df.empty:
        yearly_totals = df.groupby("deal_year")["trade_count"].transform("sum")
        df["share_pct"] = round((df["trade_count"] / yearly_totals) * 100, 1)
        
    return df


def get_dong_price_leaderboard(region_code: Optional[str] = None, top_n: int = 12) -> pd.DataFrame:
    """
    법정동별 평당 평균 매매가 랭킹
    """
    from database import get_connection
    where_clause = "WHERE is_cancel = 0 AND dong != ''"
    params = []
    if region_code:
        where_clause += " AND region_code = ?"
        params.append(region_code)
    else:
        where_clause += " AND region_code IN ('41595', '41461')"
        
    query = f"""
        SELECT 
            dong,
            region_code,
            CASE 
                WHEN region_code = '41595' THEN '화성시 (병점)'
                WHEN region_code = '41461' THEN '용인시 처인구'
                ELSE region_code
            END as region_name,
            COUNT(*) as total_trades,
            ROUND(AVG(deal_amount / (exclusive_area / 3.305785)), 1) as avg_pyeong_price,
            ROUND(AVG(deal_amount), 1) as avg_deal_amount,
            MAX(deal_amount) as max_deal_amount
        FROM transactions
        {where_clause}
        GROUP BY dong, region_code
        HAVING total_trades >= 30
        ORDER BY avg_pyeong_price DESC
        LIMIT {top_n}
    """
    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df


def get_complex_ath_recovery_leaderboard(region_code: Optional[str] = None, top_n: int = 15) -> pd.DataFrame:
    """
    주요 아파트 단지별 2021년 역대 최고가(ATH) 대비 현재 실거래가 회복률 랭킹
    """
    from database import get_connection
    where_clause = "WHERE is_cancel = 0"
    params = []
    if region_code:
        where_clause += " AND region_code = ?"
        params.append(region_code)
    else:
        where_clause += " AND region_code IN ('41595', '41461')"
        
    query = f"""
        SELECT 
            complex_name,
            dong,
            region_code,
            CASE 
                WHEN region_code = '41595' THEN '화성시'
                WHEN region_code = '41461' THEN '용인 처인구'
                ELSE region_code
            END as region_label,
            COUNT(*) as total_trades,
            MAX(deal_amount) as ath_price,
            ROUND(AVG(exclusive_area), 1) as avg_area
        FROM transactions
        {where_clause}
        GROUP BY complex_name, dong, region_code
        HAVING total_trades >= 20
    """
    with get_connection() as conn:
        base_df = pd.read_sql_query(query, conn, params=params)
        
    if base_df.empty:
        return pd.DataFrame()
        
    with get_connection() as conn:
        latest_query = f"""
            SELECT t.complex_name, t.deal_amount as latest_price, t.deal_date as latest_date, t.exclusive_area as latest_area, t.floor as latest_floor
            FROM transactions t
            INNER JOIN (
                SELECT complex_name, MAX(deal_date) as max_date
                FROM transactions
                {where_clause}
                GROUP BY complex_name
            ) lm ON t.complex_name = lm.complex_name AND t.deal_date = lm.max_date
            WHERE t.is_cancel = 0
            GROUP BY t.complex_name
        """
        latest_df = pd.read_sql_query(latest_query, conn, params=params)
        
    merged = pd.merge(base_df, latest_df, on="complex_name", how="inner")
    merged["recovery_rate"] = round((merged["latest_price"] / merged["ath_price"]) * 100, 1)
    merged = merged.sort_values("recovery_rate", ascending=False).head(top_n)
    return merged
