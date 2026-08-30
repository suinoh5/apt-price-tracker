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


import urllib.parse

def fetch_molit_api(service_key: str, lawd_cd: str, deal_ymd: str) -> List[Dict[str, Any]]:
    """
    국토교통부 아파트매매 실거래 상세 자료 OpenAPI 호출 및 파싱
    :param service_key: 공공데이터포털 디코딩/인코딩 인증키 (자동 처리)
    :param lawd_cd: 5자리 지역코드 (예: 11710 송파구, 41595 화성시 병점동)
    :param deal_ymd: 거래년월 6자리 (예: 202405)
    """
    if not service_key or not lawd_cd or not deal_ymd:
        return []
        
    # URL 이중 인코딩 방지 (인코딩/디코딩 키 모두 호환)
    clean_key = urllib.parse.unquote(service_key.strip())
    
    # 화성시 구형 코드(41590)가 들어온 경우 실거래가 있는 세부 권역(병점 41595)으로 매핑
    target_cds = ["41595", "41597", "41591", "41593"] if lawd_cd == "41590" else [lawd_cd]
    
    results = []
    for cd in target_cds:
        params = {
            "serviceKey": clean_key,
            "LAWD_CD": cd,
            "DEAL_YMD": deal_ymd.strip(),
            "numOfRows": "1000",
            "pageNo": "1",
        }
        
        try:
            response = requests.get(MOLIT_API_URL, params=params, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            
            for item in items:
                def get_text(tags: List[str], default: str = "") -> str:
                    for t in tags:
                        el = item.find(t)
                        if el is not None and el.text:
                            return el.text.strip()
                    return default

                deal_amount_str = get_text(["dealAmount", "거래금액"]).replace(",", "")
                if not deal_amount_str:
                    continue
                    
                deal_amount = int(deal_amount_str)
                deal_year = int(get_text(["dealYear", "년"], "2024"))
                deal_month = int(get_text(["dealMonth", "월"], "1"))
                deal_day = int(get_text(["dealDay", "일"], "1"))
                deal_date = f"{deal_year:04d}-{deal_month:02d}-{deal_day:02d}"
                
                apt_name = get_text(["aptNm", "아파트", "단지"])
                exclusive_area = float(get_text(["excluUseAr", "전용면적"], "0.0"))
                floor = int(get_text(["floor", "층"], "0"))
                build_year = int(get_text(["buildYear", "건축년도"], "0"))
                dong = get_text(["umdNm", "법정동", "동"], "")
                cancel_deal_type = get_text(["cdealType", "해제사유발생일"], "")
                req_gbn = get_text(["reqGbn", "dealingGbn", "거래유형"], "중개거래")
                rdealer_lawdnm = get_text(["rdealerLawdnm", "estateAgentSggNm", "중개사소재지"], "현지 중개사")
                
                results.append({
                    "complex_name": apt_name,
                    "region_code": cd,
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
        except Exception as e:
            print(f"Error fetching MOLIT API for code {cd}: {e}")
            continue
            
    return results


def generate_realistic_historical_data() -> int:
    """국토교통부 실거래가 검증 실제 데이터셋 동기화"""
    from real_data_loader import load_real_data_into_db
    return load_real_data_into_db()


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
