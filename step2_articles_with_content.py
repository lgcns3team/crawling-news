from newspaper import Article
from newspaper.article import ArticleException
from config_companies import FULL_PIPELINE_COMPANY_NAMES
from collections import Counter
import json

######################################################
# 본문 추출 후에 15개는 db저장, 5개는 요약하러 보내기? # 
######################################################


def step2_articles_with_content(result_by_step1):
    
    url_seen_count = {}
    result_with_content = []

    for item in result_by_step1:
        url = item.get("originallink")
        title = item.get("title")
        pub_date = item.get("pubDate")
        company_id = item.get("company_id")
        company_name = item.get("company_name")
    
        if not url:
            continue

        url_seen_count[url] = url_seen_count.get(url, 0) + 1
        
        if url_seen_count[url] > 1:
            continue
        
        # 본문 추출
        article = Article(url, language="ko")
        try:
            article.download()
            article.parse()
        except ArticleException:
            print(f"STEP2: newspaper 본문 추출 실패 - {url}")
            continue
        
        raw_text = article.text 
        if not raw_text or not raw_text.strip():
            print(f"STEP2: 본문 공백만 존재 - {url}")
            continue

        full_text = raw_text.strip()

        result_with_content.append(
            {
                "id": item.get("id"),              
                "company_id": company_id,
                "company_name": company_name,
                "sector": item.get("sector"),
                "title": title,
                "url": url,
                "date": pub_date,
                "full_text": full_text,
            }
        )
    
    full_pipeline_articles = []   # GPT 요약까지 돌릴 5개 종목들
    db_only_articles = []         # 나머지 종목 (DB 저장만)

    for art in result_with_content:
        if art["company_name"] in FULL_PIPELINE_COMPANY_NAMES:
            full_pipeline_articles.append(art)
        else:
            db_only_articles.append(art)

    ### json 확인용 ###

    # 핵심 종목 json 확인
    #with open("step2_full_pipeline.json", "w", encoding="utf-8") as f:
    #    json.dump(full_pipeline_articles, f, ensure_ascii=False, indent=4)

    # 나머지 종목 json 확인
    #with open("step2_db_only.json", "w", encoding="utf-8") as f:
    #    json.dump(db_only_articles, f, ensure_ascii=False, indent=4)

    return {
        "full_pipeline_articles": full_pipeline_articles,
        "db_only_articles": db_only_articles,
    }



