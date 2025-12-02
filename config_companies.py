COMPANIES = [
    {"company_id": "005930", "sector": "반도체", "company_name": "삼성전자",       "query": "삼성전자"},
    {"company_id": "005380", "sector": "모빌리티", "company_name": "현대차",     "query": "현대차"},
    {"company_id": "373220",  "sector": "2차전지", "company_name": "LG에너지솔루션", "query": "LG에너지솔루션"},
    {"company_id": "009830", "sector": "재생에너지", "company_name": "한화솔루션",          "query": "한화솔루션"},
    {"company_id": "034020", "sector": "원자력", "company_name": "두산에너빌리티", "query": "두산에너빌리티"},
    
    # 1. 반도체
    {"company_id": "000660", "sector": "반도체", "company_name": "SK 하이닉스",  "query": "SK하이닉스"},
    {"company_id": "000990", "sector": "반도체", "company_name": "DB 하이텍",    "query": "DB하이텍"},
    {"company_id": "042700", "sector": "반도체", "company_name": "한미반도체",   "query": "한미반도체"},

    # 2. 모빌리티
    {"company_id": "000270", "sector": "모빌리티", "company_name": "기아차",     "query": "기아차"},
    {"company_id": "012330", "sector": "모빌리티", "company_name": "현대모비스", "query": "현대모비스"},
    {"company_id": "204320", "sector": "모빌리티", "company_name": "HL만도",     "query": "HL만도"},

    # 3. 2차전지
    {"company_id": "006400", "sector": "2차전지", "company_name": "삼성SDI",        "query": "삼성SDI"},
    {"company_id": "096770", "sector": "2차전지", "company_name": "SK 이노베이션",  "query": "SK이노베이션"},
    {"company_id": "003670", "sector": "2차전지", "company_name": "포스코퓨처엠",   "query": "포스코퓨처엠"},

    # 4. 재생에너지
    {"company_id": "112610", "sector": "재생에너지", "company_name": "씨에스윈드",          "query": "씨에스윈드"},
    {"company_id": "322000", "sector": "재생에너지", "company_name": "HD현대에너지솔루션",  "query": "HD현대에너지솔루션"},
    {"company_id": "100090", "sector": "재생에너지", "company_name": "SK 오션플랜트",       "query": "SK오션플랜트"},

    # 5. 원자력 에너지
    {"company_id": "052690", "sector": "원자력", "company_name": "한전기술",       "query": "한전기술"},
    {"company_id": "298040", "sector": "원자력", "company_name": "효성중공업",     "query": "효성중공업"},
    {"company_id": "015760", "sector": "원자력", "company_name": "한국전력",       "query": "한국전력"},
]

# 풀 파이프라인(1~4) 돌릴 5개 종목: 섹터 대표
FULL_PIPELINE_COMPANY_NAMES = {
    "삼성전자",
    "현대차",
    "LG에너지솔루션",
    "한화솔루션",
    "두산에너빌리티",
}
