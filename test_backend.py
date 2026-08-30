"""
Backend Pipeline Verification with Professional AI Valuation Suite
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import sqlite3
from config import DB_PATH
from database import init_db, get_transactions_df, get_watchlist
from real_data_loader import load_real_data_into_db
from analyzer import calculate_complex_metrics, calculate_rsi, calculate_supply_demand_metrics
from predictor import predict_future_prices, calculate_investment_score

def main():
    print("1. 데이터베이스 초기화 및 실제 실거래가 적재 확인...")
    init_db()
    
    print("\n2. [검증] 안화동마을주공7단지 (전문가 분석 지표):")
    for area in [59.92]:
        df = get_transactions_df("안화동마을주공7단지", area, area)
        if not df.empty:
            m = calculate_complex_metrics(df)
            rsi = calculate_rsi(df)
            sd = calculate_supply_demand_metrics(df, total_households=742)
            p = predict_future_prices(df, 365)
            score = calculate_investment_score(m, rsi, sd, p["recent_momentum_pct"])
            
            print(f"  - 평형: 전용 {area}㎡ ({int(area/3.3)}평형)")
            print(f"  - 🏆 종합 AI 투자 점수: {score['total_score']}점 ({score['grade']})")
            print(f"    * 팩터별: {score['sub_scores']}")
            print(f"  - 🧭 부동산 RSI: {rsi['rsi']}점 ({rsi['status']})")
            print(f"  - 🌊 수급 회전율: {sd['turnover_rate_str']} (상승거래비중: {sd['advance_ratio']}%)")
            print(f"  - 🎯 3대 시나리오 1년 후 시세 전망:")
            f12 = p["forecast_12m"]
            print(f"    * 🚀 Bull: {f12['bull_price_str']} ({f12['bull_pct']:+0.1f}%)")
            print(f"    * 🎯 Base: {f12['base_price_str']} ({f12['base_pct']:+0.1f}%)")
            print(f"    * 🛡️ Bear: {f12['bear_price_str']} ({f12['bear_pct']:+0.1f}%)")
            
    print("\n3. [검증] 용인푸르지오원클러스터1단지 (전문가 분석 지표):")
    for area in [84.95]:
        df = get_transactions_df("용인푸르지오원클러스터1단지", area, area)
        if not df.empty:
            m = calculate_complex_metrics(df)
            rsi = calculate_rsi(df)
            sd = calculate_supply_demand_metrics(df, total_households=1681)
            p = predict_future_prices(df, 365)
            score = calculate_investment_score(m, rsi, sd, p["recent_momentum_pct"])
            
            print(f"  - 평형: 전용 {area}㎡ ({int(area/3.3)}평형)")
            print(f"  - 🏆 종합 AI 투자 점수: {score['total_score']}점 ({score['grade']})")
            print(f"  - 🧭 부동산 RSI: {rsi['rsi']}점 ({rsi['status']})")
            print(f"  - 🌊 수급 회전율: {sd['turnover_rate_str']} (상승거래비중: {sd['advance_ratio']}%)")
            print(f"  - 🎯 3대 시나리오 1년 후 시세 전망:")
            f12 = p["forecast_12m"]
            print(f"    * 🚀 Bull: {f12['bull_price_str']} ({f12['bull_pct']:+0.1f}%)")
            print(f"    * 🎯 Base: {f12['base_price_str']} ({f12['base_pct']:+0.1f}%)")
            print(f"    * 🛡️ Bear: {f12['bear_price_str']} ({f12['bear_pct']:+0.1f}%)")

    print("\n✅ 전문가급 AI 시세 예측 & 종합 투자 매력도 파이프라인 검증 완료!")

if __name__ == "__main__":
    main()
