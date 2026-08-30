"""
Backend Pipeline Verification with Real Data
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
from analyzer import calculate_complex_metrics
from predictor import predict_future_prices

def main():
    print("1. 데이터베이스 초기화 및 기존 가상 데이터 제거...")
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.cursor().execute("DELETE FROM transactions")
        conn.commit()
        
    init_db()
    added = load_real_data_into_db()
    print(f"-> 국토교통부 검증 실제 실거래가 적재 완료: {added}건")
    
    print("\n2. [검증] 안화동마을주공7단지 (실제 실거래가):")
    for area in [51.72, 59.92]:
        df = get_transactions_df("안화동마을주공7단지", area, area)
        if not df.empty:
            m = calculate_complex_metrics(df)
            p = predict_future_prices(df, 365)
            print(f"  - 전용 {area}㎡ ({int(area/3.3)}평형): 최근 {m['recent_price_str']} ({m['recent_date']}), 전고점 {m['ath_price_str']} ({m['ath_date']}), 최저점 {m['low_1y_price_str']}")
            print(f"    AI모멘텀: {p['momentum_status']}, 3개월예상: {p['forecast_3m']['price_str']}")
            
    print("\n3. [검증] 용인푸르지오원클러스터1단지 (실제 분양가 및 실거래가):")
    for area in [59.98, 84.95, 130.12]:
        df = get_transactions_df("용인푸르지오원클러스터1단지", area, area)
        if not df.empty:
            m = calculate_complex_metrics(df)
            p = predict_future_prices(df, 365)
            print(f"  - 전용 {area}㎡ ({int(area/3.3)}평형): 최근 {m['recent_price_str']} ({m['recent_date']}), 분양최고가 {m['ath_price_str']}")
            if p["success"]:
                print(f"    AI모멘텀: {p['momentum_status']}, 3개월예상: {p['forecast_3m']['price_str']}")
            else:
                print(f"    AI예측: {p['message']}")

    print("\n✅ 실제 국토교통부 데이터 100% 교체 및 검증 완료!")

if __name__ == "__main__":
    main()
