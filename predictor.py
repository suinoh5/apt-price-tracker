"""
Apt Price Tracker - Advanced ML 3-Scenario Forecasting & Investment Scoring Engine
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
    3대 시나리오(Bull / Base / Bear) 및 머신러닝 회귀 기반 미래 시세 전망 산출
    """
    if df.empty or len(df) < 5:
        return {
            "success": False,
            "message": "정밀 예측을 위한 실거래 데이터가 충분하지 않습니다 (최소 5건 이상 필요)."
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
    current_price = float(y[-1])
    future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1, 15)]
    future_days = [(dt - base_date).days for dt in future_dates]
    
    future_X = np.array(future_days).reshape(-1, 1)
    base_preds = model.predict(future_X)
    
    # 3대 시나리오 궤적 계산
    # 1) Bull Case (상승 시나리오): Base + 1.28 * std_error (상단 80% 밴드)
    # 2) Base Case (기본 시나리오): Base model 추세 연속
    # 3) Bear Case (보수 시나리오): Base - 1.28 * std_error (하단 지지선)
    band_width = max(std_error * 1.28, current_price * 0.035)
    bull_preds = base_preds + band_width
    bear_preds = base_preds - band_width
    
    # 특정 시점(3m, 6m, 12m)별 3대 시나리오 수치 함수
    def get_scenario_forecast(days_ahead: int) -> Dict[str, Any]:
        target_dt = last_date + timedelta(days=days_ahead)
        t_day = (target_dt - base_date).days
        base_v = float(model.predict([[t_day]])[0])
        bull_v = float(base_v + band_width)
        bear_v = float(base_v - band_width)
        
        return {
            "date": target_dt.strftime("%Y-%m-%d"),
            "base_price": int(round(base_v)),
            "base_price_str": format_price_krw(base_v),
            "base_pct": round(((base_v - current_price) / current_price) * 100, 2),
            "bull_price": int(round(bull_v)),
            "bull_price_str": format_price_krw(bull_v),
            "bull_pct": round(((bull_v - current_price) / current_price) * 100, 2),
            "bear_price": int(round(bear_v)),
            "bear_price_str": format_price_krw(bear_v),
            "bear_pct": round(((bear_v - current_price) / current_price) * 100, 2),
        }
        
    f_3m = get_scenario_forecast(90)
    f_6m = get_scenario_forecast(180)
    f_12m = get_scenario_forecast(365)
    
    # 최근 6개월 모멘텀 계산
    recent_6m_date = last_date - timedelta(days=180)
    recent_df = df_sorted[df_sorted["deal_date"] >= recent_6m_date]
    if len(recent_df) >= 3:
        p_start = recent_df.iloc[0]["deal_amount"]
        p_end = recent_df.iloc[-1]["deal_amount"]
        recent_momentum_pct = ((p_end - p_start) / p_start) * 100
    else:
        recent_momentum_pct = f_3m["base_pct"]
        
    if recent_momentum_pct >= 4.0:
        momentum_status = "🔥 강한 상승 모멘텀 (Bullish)"
        momentum_color = "#e53e3e"
        diagnosis = "최근 신고가 경신 및 상승 거래 비중이 높아 단기 상승 탄력이 강력합니다. 상단 저항선 돌파 시 추가 랠리가 가능합니다."
    elif recent_momentum_pct >= 1.0:
        momentum_status = "📈 완만한 우상향 / 회복세"
        momentum_color = "#dd6b20"
        diagnosis = "저점을 점진적으로 높여가며 안정적인 우상향 궤적을 형성하고 있습니다. 실거래량이 뒷받침되는 건강한 상승 흐름입니다."
    elif recent_momentum_pct > -3.0:
        momentum_status = "⚖️ 보합 및 관망세 (Neutral)"
        momentum_color = "#3182ce"
        diagnosis = "매수자와 매도자 간 호가 격차로 횡보 국면입니다. 거시 금리 및 정책 변화에 따른 방향성 확인이 필요합니다."
    else:
        momentum_status = "📉 조정 및 하방 압력 (Bearish)"
        momentum_color = "#718096"
        diagnosis = "단기 매수세 둔화로 가격 조정이 진행 중입니다. 주요 지지선에서의 거래량 유입 여부를 점검하세요."
        
    # 결과 시계열 데이터프레임
    future_df = pd.DataFrame({
        "deal_date": future_dates,
        "base_price": base_preds,
        "bull_price": bull_preds,
        "bear_price": bear_preds,
    })
    
    return {
        "success": True,
        "current_price": current_price,
        "current_price_str": format_price_krw(current_price),
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


def calculate_investment_score(metrics: Dict[str, Any], rsi_data: Dict[str, Any], supply_demand: Dict[str, Any], momentum_pct: float) -> Dict[str, Any]:
    """
    4대 핵심 팩터(모멘텀 30%, 가격 메리트 25%, 거래량 에너지 25%, 가격 안정성 20%)를 종합하여 0~100점 투자 매력도 산출
    """
    # 1. 모멘텀 점수 (30점 만점): 최근 6개월 상승률 + 상승거래 비율
    adv_ratio = supply_demand.get("advance_ratio", 50.0)
    m_score = np.clip(50 + momentum_pct * 4.0 + (adv_ratio - 50) * 0.6, 10, 100)
    
    # 2. 가격 메리트 점수 (25점 만점): 전고점 대비 할인율 & 저점 대비 반등 건강도
    ath_diff = metrics.get("ath_diff_pct", 0.0)  # 예: -15.0%
    if ath_diff <= -20.0:
        v_score = 90.0  # 저평가 매력 매우 높음
    elif ath_diff <= -10.0:
        v_score = 80.0
    elif ath_diff <= 0.0:
        v_score = 65.0 + (ath_diff + 10.0) * 1.5
    else:
        v_score = 75.0  # 신고가 돌파 프리미엄
        
    # 3. 거래량 에너지 점수 (25점 만점): 거래 회전율 및 최근 거래량
    turnover = supply_demand.get("turnover_rate", 0.5)
    tx_count = supply_demand.get("tx_count_6m", 5)
    vol_score = np.clip(40 + turnover * 25.0 + tx_count * 1.5, 20, 100)
    
    # 4. 가격 안정성 점수 (20점 만점): RSI 적정성(50에 가까울수록 안정적)
    rsi_val = rsi_data.get("rsi", 50.0)
    rsi_penalty = abs(rsi_val - 50.0) * 0.8
    stab_score = np.clip(90 - rsi_penalty, 25, 100)
    
    # 종합 점수 (0~100)
    total_score = int(round(m_score * 0.30 + v_score * 0.25 + vol_score * 0.25 + stab_score * 0.20))
    total_score = np.clip(total_score, 15, 98)
    
    if total_score >= 80:
        grade = "🔥 적극 관심 / 매수 유망 (Strong Buy)"
        color = "#e53e3e"
        verdict = "강력한 상승 모멘텀과 거래량 에너지가 결합되어 우상향 탄력이 높습니다. 시장 주도 평형으로 적극적인 관심을 가질 만합니다."
    elif total_score >= 65:
        grade = "📈 분할 접근 / 안정 성장 (Buy)"
        color = "#dd6b20"
        verdict = "안정적인 시세 지지선과 완만한 거래 회전을 유지하고 있습니다. 중장기 실거주 및 분할 매수 관점에서 긍정적인 구간입니다."
    elif total_score >= 45:
        grade = "⚖️ 보합 / 관망 및 탐색 (Neutral)"
        color = "#3182ce"
        verdict = "가격과 수급이 팽팽한 균형을 이루며 방향성을 탐색 중입니다. 추가적인 거래량 급증이나 거시 금리 변화를 확인 후 진입이 추천됩니다."
    else:
        grade = "📉 단기 조정 주의 / 지지선 확인 (Caution)"
        color = "#718096"
        verdict = "단기 매수세가 둔화되며 하방 압력이 존재합니다. 주요 지지선에서의 거래 반등을 확인하는 보수적 접근이 필요합니다."
        
    return {
        "total_score": total_score,
        "grade": grade,
        "color": color,
        "verdict": verdict,
        "sub_scores": {
            "모멘텀 (추세 강도)": int(round(m_score)),
            "가격 메리트 (저평가도)": int(round(v_score)),
            "거래량 에너지 (수급)": int(round(vol_score)),
            "가격 변동 안정성": int(round(stab_score))
        }
    }
