"""
Apt Price Tracker - Data Collection and Realistic Historical Data Generator
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import random
import pandas as pd
from typing import List, Dict, Any, Optional

from config import DEFAULT_COMPLEXES, LAWD_CODES
from database import insert_transactions, add_alert, get_transactions_df, get_watchlist


MOLIT_API_URL = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"


def fetch_molit_api(service_key: str, lawd_cd: str, deal_ymd: str) -> List[Dict[str, Any]]:
    """
    국토교통부 아파트매매 실거래 상세 자료 OpenAPI 호출 및 파싱
    :param service_key: 공공데이터포털 디코딩/인코딩 인증키
    :param lawd_cd: 5자리 지역코드 (예: 11710 송파구)
    :param deal_ymd: 거래년월 6자리 (예: 202405)
    """
    params = {
        "serviceKey": service_key,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "numOfRows": "1000",
        "pageNo": "1",
    }
    
    try:
        response = requests.get(MOLIT_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        
        results = []
        for item in items:
            def get_text(tag: str, default: str = "") -> str:
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else default

            deal_amount_str = get_text("dealAmount").replace(",", "")
            if not deal_amount_str:
                continue
                
            deal_amount = int(deal_amount_str)
            deal_year = int(get_text("dealYear", "2024"))
            deal_month = int(get_text("dealMonth", "1"))
            deal_day = int(get_text("dealDay", "1"))
            deal_date = f"{deal_year:04d}-{deal_month:02d}-{deal_day:02d}"
            
            apt_name = get_text("aptNm")
            exclusive_area = float(get_text("excluUseAr", "0.0"))
            floor = int(get_text("floor", "0"))
            build_year = int(get_text("buildYear", "0"))
            dong = get_text("umdNm", "")
            cancel_deal_type = get_text("cdealType", "")
            req_gbn = get_text("reqGbn", "중개거래")
            rdealer_lawdnm = get_text("rdealerLawdnm", "")
            if not rdealer_lawdnm:
                rdealer_lawdnm = get_text("estateAgentSggNm", "현지 중개사")
            
            results.append({
                "complex_name": apt_name,
                "region_code": lawd_cd,
                "dong": dong,
                "deal_year": deal_year,
                "deal_month": deal_month,
                "deal_day": deal_day,
                "deal_date": deal_date,
                "deal_amount": deal_amount,
                "exclusive_area": exclusive_area,
                "floor": floor,
                "build_year": build_year,
                "cancel_deal_type": cancel_deal_type,
                "req_gbn": req_gbn,
                "rdealer_lawdnm": rdealer_lawdnm,
            })
        return results
    except Exception as e:
        print(f"Error fetching MOLIT API: {e}")
        return []


def generate_realistic_historical_data() -> int:
    """
    대표 아파트 단지들의 실제 과거 3~4년(2022~2025/2026) 시세 사이클을 반영한
    실감나는 실거래가 시계열 데이터셋 생성 및 DB 적재.
    (2022년 금리 인상기 하락 -> 2023년 초 저점 터치 -> 2023~2024년 점진적 회복 -> 2024~2025년 신고가 랠리 패턴 구현)
    """
    random.seed(42)
    
    # 단지별 기준 시세 프로필 (평형별 2021고점, 2023저점, 현재 2025/2026 시세 - 단위: 만원)
    profiles = {
        "안화동마을주공7단지": {
            51.72: {"peak": 31000, "trough": 19000, "current": 26500, "floors": (1, 15)},
            59.92: {"peak": 38500, "trough": 24000, "current": 32500, "floors": (1, 15)},
        },
        "용인푸르지오원클러스터1단지": {
            59.98: {"peak": 49000, "trough": 46500, "current": 52000, "floors": (2, 28)},
            84.95: {"peak": 61000, "trough": 56900, "current": 64500, "floors": (2, 28)},
            130.12: {"peak": 125000, "trough": 120000, "current": 130000, "floors": (2, 28)},
        },
        "잠실엘스": {
            59.96: {"peak": 215000, "trough": 150000, "current": 225000, "floors": (2, 34)},
            84.80: {"peak": 270000, "trough": 195000, "current": 278000, "floors": (2, 34)},
            119.93: {"peak": 340000, "trough": 250000, "current": 355000, "floors": (2, 34)},
        },
        "마포래미안푸르지오": {
            59.92: {"peak": 145000, "trough": 105000, "current": 148000, "floors": (1, 30)},
            84.59: {"peak": 190000, "trough": 142000, "current": 195000, "floors": (1, 30)},
            114.72: {"peak": 230000, "trough": 180000, "current": 238000, "floors": (1, 28)},
        },
        "반포자이": {
            59.98: {"peak": 275000, "trough": 210000, "current": 290000, "floors": (2, 29)},
            84.94: {"peak": 390000, "trough": 310000, "current": 415000, "floors": (2, 29)},
            132.17: {"peak": 520000, "trough": 420000, "current": 550000, "floors": (2, 29)},
        },
        "은마": {
            76.79: {"peak": 260000, "trough": 180000, "current": 265000, "floors": (1, 14)},
            84.43: {"peak": 285000, "trough": 205000, "current": 295000, "floors": (1, 14)},
        },
        "헬리오시티": {
            59.96: {"peak": 180000, "trough": 125000, "current": 182000, "floors": (2, 35)},
            84.98: {"peak": 238000, "trough": 165000, "current": 242000, "floors": (2, 35)},
            110.48: {"peak": 290000, "trough": 215000, "current": 300000, "floors": (2, 35)},
        },
        "아크로리버파크": {
            59.95: {"peak": 290000, "trough": 235000, "current": 320000, "floors": (2, 38)},
            84.97: {"peak": 466000, "trough": 360000, "current": 500000, "floors": (2, 38)},
            112.96: {"peak": 580000, "trough": 480000, "current": 630000, "floors": (2, 38)},
        }
    }
    
    # 2022년 1월부터 2026년 8월까지 (약 56개월)
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2026, 8, 25)
    total_days = (end_date - start_date).days
    
    all_transactions = []
    
    for complex_info in DEFAULT_COMPLEXES:
        c_name = complex_info["name"]
        if c_name not in profiles:
            continue
            
        c_profile = profiles[c_name]
        
        for area, spec in c_profile.items():
            peak = spec["peak"]
            trough = spec["trough"]
            curr = spec["current"]
            min_fl, max_fl = spec["floors"]
            
            # 매월 평균 2~6건 거래 생성
            current_dt = start_date
            while current_dt <= end_date:
                days_from_start = (current_dt - start_date).days
                progress = days_from_start / total_days  # 0.0 ~ 1.0
                
                # 시장 사이클 곡선 계산:
                # 0.0 ~ 0.25 (2022): peak -> trough 급락
                # 0.25 ~ 0.45 (2023초): 바닥 다지기
                # 0.45 ~ 0.75 (2023후~2024): 점진적 회복
                # 0.75 ~ 1.00 (2025~2026): 전고점 돌파 & 신고가 형성
                if progress < 0.25:
                    sub_p = progress / 0.25
                    base_price = peak - (peak - trough) * sub_p
                elif progress < 0.45:
                    sub_p = (progress - 0.25) / 0.20
                    base_price = trough + (peak - trough) * 0.15 * sub_p
                elif progress < 0.75:
                    sub_p = (progress - 0.45) / 0.30
                    base_price = (trough + (peak - trough) * 0.15) + (peak - (trough + (peak - trough) * 0.15)) * 0.9 * sub_p
                else:
                    sub_p = (progress - 0.75) / 0.25
                    base_price = peak * 0.95 + (curr - peak * 0.95) * sub_p
                
                # 월별 거래 건수 (하락장엔 거래량 급감, 상승장엔 거래량 증가)
                month_volume = random.randint(1, 3) if progress < 0.35 else random.randint(2, 6)
                
                for _ in range(month_volume):
                    day_offset = random.randint(1, 28)
                    deal_dt = datetime(current_dt.year, current_dt.month, min(day_offset, 28))
                    if deal_dt > end_date:
                        break
                        
                    floor = random.randint(min_fl, max_fl)
                    # 층수 프리미엄: 저층(-3~5%), 로얄층(+2~5%)
                    floor_factor = 0.96 if floor <= 3 else (1.03 if floor >= max_fl * 0.6 else 1.0)
                    
                    # 노이즈 (+/- 2.5%)
                    noise = random.uniform(-0.025, 0.025)
                    deal_price = int(round((base_price * floor_factor * (1.0 + noise)) / 100) * 100)
                    
                    # 거래유형 및 중개사소재지 시뮬레이션
                    is_direct = random.random() < 0.06
                    req_gbn = "직거래" if is_direct else "중개거래"
                    if is_direct:
                        rdealer_lawdnm = "당사자 직거래"
                    else:
                        if random.random() < 0.85:
                            rdealer_lawdnm = complex_info["region_name"]
                        else:
                            neighbor_agents = ["서울 강남구", "서울 서초구", "경기 수원시", "경기 성남시 분당구"]
                            rdealer_lawdnm = random.choice(neighbor_agents)
                    
                    all_transactions.append({
                        "complex_name": c_name,
                        "region_code": complex_info["region_code"],
                        "region_name": complex_info["region_name"],
                        "dong": complex_info["dong"],
                        "deal_year": deal_dt.year,
                        "deal_month": deal_dt.month,
                        "deal_day": deal_dt.day,
                        "deal_date": deal_dt.strftime("%Y-%m-%d"),
                        "deal_amount": deal_price,
                        "exclusive_area": area,
                        "floor": floor,
                        "build_year": complex_info["build_year"],
                        "cancel_deal_type": "",
                        "req_gbn": req_gbn,
                        "rdealer_lawdnm": rdealer_lawdnm,
                    })
                
                # 다음 달로 이동
                if current_dt.month == 12:
                    current_dt = datetime(current_dt.year + 1, 1, 1)
                else:
                    current_dt = datetime(current_dt.year, current_dt.month + 1, 1)
                    
    inserted = insert_transactions(all_transactions)
    
    # 알림 데이터도 함께 업데이트 (최근 신고가/주요 거래)
    detect_and_log_alerts()
    return inserted


def detect_and_log_alerts():
    """DB 내의 거래들을 분석하여 최근 6개월 내 발생한 신고가 및 특이 거래를 alerts 테이블에 기록"""
    watchlist = get_watchlist()
    for item in watchlist:
        c_name = item["complex_name"]
        df = get_transactions_df(complex_name=c_name)
        if df.empty or len(df) < 5:
            continue
            
        # 평형별 그룹화
        areas = df["exclusive_area"].unique()
        for area in areas:
            area_df = df[df["exclusive_area"] == area].sort_values("deal_date")
            if len(area_df) < 5:
                continue
                
            # 역대 최고가 계산
            ath_row = area_df.loc[area_df["deal_amount"].idxmax()]
            recent_rows = area_df.tail(3)
            
            for idx, r in recent_rows.iterrows():
                # 역대 최고가와 동일하거나 경신한 최근 거래인 경우
                if r["deal_amount"] >= ath_row["deal_amount"]:
                    add_alert(
                        complex_name=c_name,
                        alert_type="🔥 신고가 경신",
                        message=f"{c_name} {area}㎡({int(area/3.3)}평) {r['floor']}층 역대 최고가 {r['deal_amount']//10000}억 {r['deal_amount']%10000}만원 계약 체결!",
                        deal_date=r["deal_date"].strftime("%Y-%m-%d"),
                        deal_amount=int(r["deal_amount"]),
                        exclusive_area=float(area),
                        floor=int(r["floor"])
                    )
                # 직전 거래 대비 5% 이상 하락 거래
                elif idx > 0 and len(area_df) > 1:
                    prev_deal = area_df.iloc[area_df.index.get_loc(idx) - 1]
                    diff_pct = (r["deal_amount"] - prev_deal["deal_amount"]) / prev_deal["deal_amount"] * 100
                    if diff_pct <= -5.0:
                        add_alert(
                            complex_name=c_name,
                            alert_type="📉 급락 거래",
                            message=f"{c_name} {area}㎡({int(area/3.3)}평) 직전 거래 대비 {abs(diff_pct):.1f}% 하락한 {r['deal_amount']//10000}억 {r['deal_amount']%10000}만원에 거래",
                            deal_date=r["deal_date"].strftime("%Y-%m-%d"),
                            deal_amount=int(r["deal_amount"]),
                            exclusive_area=float(area),
                            floor=int(r["floor"])
                        )
