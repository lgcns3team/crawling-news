import os
import time
from typing import Dict, Any, List

import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from config_companies import COMPANIES
from datetime import datetime


load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID") or os.getenv("client_id")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET") or os.getenv("client_secret")

NAVER_URL = "https://openapi.naver.com/v1/search/news.json"

HEADERS = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
}

def clean_html_tags(text: str) -> str:
    """
    네이버 검색 결과 title/description에 섞인 <b> 태그 등 제거
    """
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text()

def fetch_naver_news(query: str, display: int = 20, sort: str = "date") -> List[Dict[str, Any]]:
    """
    네이버 뉴스 검색 결과를 그대로 반환 (items 리스트).
    """
    params = {
        "query": query,
        "display": display,
        "start": 1,
        "sort": sort,
    }
    resp = requests.get(NAVER_URL, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("items", [])


def run_step1() -> Dict[str, List[Dict[str, Any]]]:
    """
    20개 종목 * 기사 20개 = 최대 400개 기사 메타데이터 생성.

    리턴 예시:
    {
        "articles": [
            {
                "id": 1,
                "company_id": "005930,
                "company_name": "삼성전자",
                "sector": "반도체",
                "query": "삼성전자",
                "title": "...",
                "description": "...",
                "originallink": "...",
                "link": "...",
            },
            ...
        ]
    }
    """
    all_articles: List[Dict[str, Any]] = []
    internal_id = 1

    for comp in COMPANIES:
        company_id = comp["company_id"]
        company_name = comp["company_name"]
        sector = comp["sector"]
        query = comp["query"]

        print(f"\n=== [STEP1] {company_name} ({sector}) 기사 검색 시작 ===")

        try:
            items = fetch_naver_news(query=query, display=20, sort="date") # 기사 수 여기서 조정
        except Exception as e:
            print(f"[WARN] 네이버 API 에러 ({company_name}): {e}")
            continue

        print(f"   → 검색 결과 개수: {len(items)}")
        for item in items:
            title = clean_html_tags(item.get("title"))
            raw_time = item.get("pubDate") or ""
            dt = datetime.strptime(raw_time, "%a, %d %b %Y %H:%M:%S %z") if raw_time else None
            db_time = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None
            article = {
                "id": internal_id,
                "company_id": company_id,
                "company_name": company_name,
                "sector": sector,
                "query": query,
                "title": title or "",
                "description": item.get("description") or "",
                "originallink": item.get("originallink") or "",
                "link": item.get("link") or "",
                "datetime": db_time or "",
            }
            all_articles.append(article)
            internal_id += 1

        # 네이버 API 호출 사이에 살짝 쉼
        time.sleep(0.2)

    print(f"\n[STEP1] 완료: 총 기사 수 = {len(all_articles)}")
    return {"articles": all_articles}


if __name__ == "__main__":
    import json
    result = run_step1()
    with open("step1_naver_articles.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
