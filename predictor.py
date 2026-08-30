"""
Apt Price Tracker - Machine Learning Price Forecasting & Market Momentum Engine
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from typing import Dict, Any, List, Tuple

from config import format_price_krw


def predict_future_prices(df: pd.DataFrame, forecast_days: int = 365) -> Dict[str, Any]:
    """
    실거래가 시계열 데이터를 바탕으로 회귀 모델을 학습하고, 향후 3/6/12개월 예상 시세 및 신뢰구간을 산출
    """
    if df.empty or len(df) < 5:
        return {
            "success": False,
            "message": "예측을 위한 실거래 데이터가 충분하지 않습니다 (최소 5건 이상 필요)."
        }
        
    df_sorted = df.sort_values("deal_date").copy()
    
    # 기준일 (시작일)로부터의 경과 일수
    base_date = df_sorted["deal_date"].min()
    df_sorted["days"] = (df_sorted["deal_date"] - base_date).dt.days
    
    X = df_sorted[["days"]].values
    y = df_sorted["deal_amount"].values
    
    # 최근 거래일수록 높은 가중치를 부여하는 지수 감쇄 가중치 (Half-life = 180일)
    max_days = df_sorted["days"].max()
    weights = np.exp((X.ravel() - max_days) / 180.0)
    weights = np.clip(weights, 0.1, 1.0)
    
    # 다항 릿지 회귀 모델 (Degree=2, 과적합 방지)
    model = make_pipeline(PolynomialFeatures(degree=2, include_bias=False), Ridge(alpha=1.0))
    model.fit(X, y, ridge__sample_weight=weights)
    
    # 모델 잔차 표준편차 계산 (예측 신뢰구간 밴드 산출용)
    preds_historical = model.predict(X)
    residuals = y - preds_historical
    std_error = np.std(residuals)
    
    # 미래 예측 일자 생성
    last_date = df_sorted["deal_date"].max()
    future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1, 15)]
    future_days = [(dt - base_date).days for dt in future_dates]
    
    future_X = np.array(future_days).reshape(-1, 1)
    future_preds = model.predict(future_X)
    
    # 상단/하단 예측 밴드 (Confidence Band, 80% 신뢰수준 ~ 1.28 * std)
    band_width = max(std_error * 1.28, y[-1] * 0.03)
    upper_band = future_preds + band_width
    lower_band = future_preds - band_width
    
    # 특정 시점 예측값 (3개월 후, 6개월 후, 12개월 후)
    def get_forecast_at(days_ahead: int) -> Dict[str, Any]:
        target_dt = last_date + timedelta(days=days_ahead)
        t_day = (target_dt - base_date).days
        val = float(model.predict([[t_day]])[0])
        val_upper = float(val + band_width)
        val_lower = float(val - band_width)
        
        current_price = y[-1]
        change_pct = round(((val - current_price) / current_price) * 100, 2)
        
        return {
            "date": target_dt.strftime("%Y-%m-%d"),
            "price": int(round(val)),
            "price_str": format_price_krw(val),
            "upper": int(round(val_upper)),
            "upper_str": format_price_krw(val_upper),
            "lower": int(round(val_lower)),
            "lower_str": format_price_krw(val_lower),
            "change_pct": change_pct
        }
        
    f_3m = get_forecast_at(90)
    f_6m = get_forecast_at(180)
    f_12m = get_forecast_at(365)
    
    # 시장 모멘텀 및 진단 산출
    # 최근 6개월간의 가격 기울기
    recent_6m_date = last_date - timedelta(days=180)
    recent_df = df_sorted[df_sorted["deal_date"] >= recent_6m_date]
    
    if len(recent_df) >= 3:
        p_start = recent_df.iloc[0]["deal_amount"]
        p_end = recent_df.iloc[-1]["deal_amount"]
        recent_momentum_pct = ((p_end - p_start) / p_start) * 100
    else:
        recent_momentum_pct = f_3m["change_pct"]
        
    # 모멘텀 상태 판정
    if recent_momentum_pct >= 5.0:
        momentum_status = "🔥 강한 상승세 (Bullish)"
        momentum_color = "#e53e3e"
        diagnosis = "최근 6개월간 신고가 경신 및 매수세 유입으로 단기 상승 탄력이 높습니다. 상단 저항선 돌파 여부를 주목할 필요가 있습니다."
    elif recent_momentum_pct >= 1.5:
        momentum_status = "📈 완만한 상승 / 회복세"
        momentum_color = "#dd6b20"
        diagnosis = "완만한 우상향 흐름을 유지하며 저점을 점진적으로 높여가고 있습니다. 실거래량이 뒷받침될 경우 추가 상승이 기대됩니다."
    elif recent_momentum_pct > -2.0:
        momentum_status = "⚖️ 보합 및 관망세 (Neutral)"
        momentum_color = "#3182ce"
        diagnosis = "매수/매도 호가 차이로 인해 횡보 국면을 보이고 있습니다. 대출 금리 및 거시 환경 변화에 따른 방향성 확인이 필요합니다."
    else:
        momentum_status = "📉 조정 및 하락 압력 (Bearish)"
        momentum_color = "#38a169"
        diagnosis = "직전 거래 대비 매수세가 둔화되며 가격 조정이 진행 중입니다. 주요 지지선에서의 거래량 반등 여부를 모니터링하세요."
        
    # 결과 시계열 데이터프레임
    future_df = pd.DataFrame({
        "deal_date": future_dates,
        "predicted_price": future_preds,
        "upper_band": upper_band,
        "lower_band": lower_band
    })
    
    return {
        "success": True,
        "forecast_3m": f_3m,
        "forecast_6m": f_6m,
        "forecast_12m": f_12m,
        "momentum_status": momentum_status,
        "momentum_color": momentum_color,
        "recent_momentum_pct": round(recent_momentum_pct, 2),
        "diagnosis": diagnosis,
        "future_df": future_df,
        "historical_fit_df": pd.DataFrame({
            "deal_date": df_sorted["deal_date"],
            "fitted_price": preds_historical
        })
    }
