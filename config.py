"""
Apt Price Tracker Configuration & Constants
"""
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "real_estate.db"

# Major District Lawd Codes (법정동 코드 앞 5자리)
LAWD_CODES = {
    "서울 강남구": "11680",
    "서울 서초구": "11650",
    "서울 송파구": "11710",
    "서울 마포구": "11440",
    "서울 용산구": "11170",
    "서울 성동구": "11200",
    "서울 강동구": "11740",
    "서울 영등포구": "11560",
    "서울 동작구": "11590",
    "서울 양천구": "11470",
    "경기 성남시 분당구": "41135",
    "경기 과천시": "41290",
    "경기 하남시": "41450",
    "인천 연수구 (송도)": "28185",
    "경기 화성시 (병점)": "41595",
    "경기 화성시 (동탄)": "41597",
    "경기 용인시 처인구": "41461",
}

# Default Preset Complexes for Quick Start
DEFAULT_COMPLEXES = [
    {
        "name": "잠실엘스",
        "region_name": "서울 송파구",
        "region_code": "11710",
        "dong": "잠실동",
        "build_year": 2008,
        "total_households": 5678,
        "representative_areas": [59.96, 84.80, 119.93],
    },
    {
        "name": "마포래미안푸르지오",
        "region_name": "서울 마포구",
        "region_code": "11440",
        "dong": "아현동",
        "build_year": 2014,
        "total_households": 3885,
        "representative_areas": [59.92, 84.59, 114.72],
    },
    {
        "name": "반포자이",
        "region_name": "서울 서초구",
        "region_code": "11650",
        "dong": "반포동",
        "build_year": 2009,
        "total_households": 3410,
        "representative_areas": [59.98, 84.94, 132.17],
    },
    {
        "name": "은마",
        "region_name": "서울 강남구",
        "region_code": "11680",
        "dong": "대치동",
        "build_year": 1979,
        "total_households": 4424,
        "representative_areas": [76.79, 84.43],
    },
    {
        "name": "헬리오시티",
        "region_name": "서울 송파구",
        "region_code": "11710",
        "dong": "가락동",
        "build_year": 2018,
        "total_households": 9510,
        "representative_areas": [59.96, 84.98, 110.48],
    },
    {
        "name": "아크로리버파크",
        "region_name": "서울 서초구",
        "region_code": "11650",
        "dong": "반포동",
        "build_year": 2016,
        "total_households": 1612,
        "representative_areas": [59.95, 84.97, 112.96],
    },
    {
        "name": "안화동마을주공7단지",
        "region_name": "경기 화성시 (병점)",
        "region_code": "41595",
        "dong": "병점동",
        "build_year": 2004,
        "total_households": 742,
        "representative_areas": [51.72, 59.92],
    },
    {
        "name": "용인푸르지오원클러스터1단지",
        "region_name": "경기 용인시 처인구",
        "region_code": "41461",
        "dong": "남동",
        "build_year": 2027,
        "total_households": 1681,
        "representative_areas": [59.98, 84.95, 130.12],
    }
]

# Formatting Helpers
def format_price_krw(amount_manwon: float) -> str:
    """만원 단위 금액을 'X억 Y천만원' 형식으로 변환"""
    if not amount_manwon or amount_manwon <= 0:
        return "0원"
    
    amount_manwon = int(round(amount_manwon))
    eok = amount_manwon // 10000
    cheon = amount_manwon % 10000
    
    if eok > 0 and cheon > 0:
        return f"{eok}억 {cheon:,}만원"
    elif eok > 0 and cheon == 0:
        return f"{eok}억원"
    else:
        return f"{cheon:,}만원"

def sqm_to_pyeong(sqm: float) -> float:
    """전용면적(㎡)을 평수로 변환 (3.305785㎡ = 1평)"""
    if not sqm:
        return 0.0
    return round(sqm / 3.305785, 1)
