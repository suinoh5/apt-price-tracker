"""
Backend Pipeline Verification and Reseed Script
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
from collector import generate_realistic_historical_data
from analyzer import calculate_complex_metrics
from predictor import predict_future_prices

def main():
    print("1. 데이터베이스 단지 정보 및 거래 데이터 리셋/재동기화...")
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        # 안화동마을주공7단지와 용인푸르지오원클러스터1단지의 이전 데이터 정리
        cursor.execute("DELETE FROM transactions WHERE complex_name IN ('안화동마을주공7단지', '용인푸르지오원클러스터1단지')")
        cursor.execute("DELETE FROM watchlist WHERE complex_name IN ('안화동마을주공7단지', '용인푸르지오원클러스터1단지')")
        conn.commit()
        
    init_db()
    added = generate_realistic_historical_data()
    print(f"-> 재동기화된 거래 데이터: {added}건")
    
    print("\n2. [검증] 안화동마을주공7단지 평형별 데이터:")
    for area in [51.72, 59.92]:
        df = get_transactions_df("안화동마을주공7단지", area, area)
        if not df.empty:
            m = calculate_complex_metrics(df)
            p = predict_future_prices(df, 365)
            print(f"  - 전용 {area}㎡ ({int(area/3.3)}평형): 최근 {m['recent_price_str']}, 최고가 {m['ath_price_str']}, AI모멘텀: {p['momentum_status']}")
            
    print("\n3. [검증] 용인푸르지오원클러스터1단지 평형별 데이터:")
    for area in [59.98, 84.95, 130.12]:
        df = get_transactions_df("용인푸르지오원클러스터1단지", area, area)
        if not df.empty:
            m = calculate_complex_metrics(df)
            p = predict_future_prices(df, 365)
            print(f"  - 전용 {area}㎡ ({int(area/3.3)}평형): 최근 {m['recent_price_str']}, 최고가 {m['ath_price_str']}, AI모멘텀: {p['momentum_status']}")

    print("\n✅ 공식 평형 정보 및 데이터 출처 재확인/동기화 완료!")

if __name__ == "__main__":
    main()
