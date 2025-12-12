import os
from dotenv import load_dotenv
from config_companies import COMPANIES
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import json

### Naver News Search API Response Fields ###
#rss/channel/lastBuildDate	    dateTime	검색 결과를 생성한 시간
#rss/channel/total	            Integer     총 검색 결과 개수
#rss/channel/start	            Integer     검색 시작 위치
#rss/channel/display	        Integer     한 번에 표시할 검색 결과 개수
#rss/channel/item	            -	        개별 검색 결과. JSON 형식의 결괏값에서는 items 속성의 JSON 배열로 개별 검색 결과를 반환합니다.
#rss/channel/item/title	        String	    뉴스 기사의 제목. 제목에서 검색어와 일치하는 부분은 <b> 태그로 감싸져 있습니다.
#rss/channel/item/originallink	String	    뉴스 기사 원문의 URL
#rss/channel/item/link	        String	    뉴스 기사의 네이버 뉴스 URL. 네이버에 제공되지 않은 기사라면 기사 원문의 URL을 반환합니다.
#rss/channel/item/description	String	    뉴스 기사의 내용을 요약한 패시지 정보. 패시지 정보에서 검색어와 일치하는 부분은 <b> 태그로 감싸져 있습니다.
#rss/channel/item/pubDate	    dateTime	뉴스 기사가 네이버에 제공된 시간. 네이버에 제공되지 않은 기사라면 기사 원문이 제공된 시간을 반환합니다.


### Naver News Search API Error Codes ###
#SE01	400	Incorrect query request (잘못된 쿼리요청입니다.)              API 요청 URL의 프로토콜, 파라미터 등에 오류가 있는지 확인합니다.
#SE02	400	Invalid display value (부적절한 display 값입니다.)            display 파라미터의 값이 허용 범위의 값(1~100)인지 확인합니다.
#SE03	400	Invalid start value (부적절한 start 값입니다.)	              start 파라미터의 값이 허용 범위의 값(1~1000)인지 확인합니다.
#SE04	400	Invalid sort value (부적절한 sort 값입니다.)	              sort 파라미터의 값에 오타가 있는지 확인합니다.
#SE06	400	Malformed encoding (잘못된 형식의 인코딩입니다.)               검색어를 UTF-8로 인코딩합니다.
#SE05	404	Invalid search api (존재하지 않는 검색 api 입니다.)            API 요청 URL에 오타가 있는지 확인합니다.
#SE99	500	System Error (시스템 에러)	서버 내부에 오류가 발생했습니다."   개발자 포럼"에 오류를 신고해 주십시오.


def get_env_variables():
    load_dotenv()
    return os.getenv("client_id"), os.getenv("client_secret")

def build_headers(client_id, client_secret):
    return {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

def fetch_news(query, headers, display=20):
    url = "https://openapi.naver.com/v1/search/news.json"
    params = {"query": query, "display": display, "sort": "date"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        err = response.json()
        print(f"step1: ({err.get('errorCode')}) {err.get('errorMessage')} ")
        return []
    return response.json().get("items", [])

def clean_html_tags(text):
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text()

def step1_naver_articles():
    
    internal_id = 1
    client_id, client_secret = get_env_variables()
    
    if not client_id or not client_secret:
        raise EnvironmentError("step1: NAVER API KEY 또는 SECRET 설정 오류")
    
    headers = build_headers(client_id, client_secret)
    
    results = []
    
    for company in COMPANIES:
        for item in fetch_news(company["query"], headers):
            raw_time = item.get("pubDate") or ""
            dt = datetime.strptime(raw_time, "%a, %d %b %Y %H:%M:%S %z") if raw_time else None
            db_time = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None
            results.append({
                "id": internal_id,
                "company_id": company["company_id"],
                "sector": company["sector"],
                "company_name": company["company_name"],
                "title": clean_html_tags(item["title"]),
                "originallink": item["originallink"],
                "pubDate": db_time,
            })
            internal_id += 1
    
    #json 확인용
    #with open("step1_naver_articles.json", "w", encoding="utf-8") as f:
    #    json.dump(results, f, ensure_ascii=False, indent=2)
        
    return results
