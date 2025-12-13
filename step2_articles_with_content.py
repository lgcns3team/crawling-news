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

    # 디버깅용 카운터
    cnt_no_url = 0
    cnt_dup_url = 0
    cnt_download_fail = 0
    cnt_empty_text = 0


    for item in result_by_step1:
        url = item.get("originallink")
        title = item.get("title")
        pub_date = item.get("pubDate")
        company_id = item.get("company_id")
        company_name = item.get("company_name")
    
        if not url:
            cnt_no_url += 1
            continue

        url_seen_count[url] = url_seen_count.get(url, 0) + 1
        
        if url_seen_count[url] > 1:
            cnt_dup_url += 1
            continue
        
        # 본문 추출
        article = Article(url, language="ko")
        try:
            article.download()
            article.parse()
        except ArticleException:
            print(f"step2: id({item.get('id')}) newspaper 본문 추출 실패 - {url}")
            cnt_download_fail += 1
            continue
        
        raw_text = article.text 
        if not raw_text or not raw_text.strip():
            print(f"step2: id({item.get('id')}) 본문 공백만 존재 - {url}")
            cnt_empty_text += 1
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
    
    #디버깅용
    print("step2 필터링 결과")
    print(f" - URL 없음 제거: {cnt_no_url}")
    print(f" - 중복 URL 제거: {cnt_dup_url}")
    print(f" - 본문 다운로드 실패: {cnt_download_fail}")
    print(f" - 본문 비어 있음 제거: {cnt_empty_text}")
    print(f" - 총 제거된 기사 수: {cnt_no_url + cnt_dup_url + cnt_download_fail + cnt_empty_text}")
    print(f" - 제거 후 본문 추출 성공 기사 수: {len(result_with_content)}")
    
    full_pipeline_articles = [] 
    db_only_articles = []       

    for art in result_with_content:
        if art["company_name"] in FULL_PIPELINE_COMPANY_NAMES:
            full_pipeline_articles.append(art)
        else:
            db_only_articles.append(art)
            
            
    print("step2 완료: 본문 추출 완료")
    print(f" - 핵심 종목 (FULL_PIPELINE): {len(full_pipeline_articles)}")
    print(f" - 나머지 종목 (DB_ONLY): {len(db_only_articles)}")
    
    ### json 확인용 ###

    # 핵심 종목 json 확인
    with open("step2_full_pipeline.json", "w", encoding="utf-8") as f:
        json.dump(full_pipeline_articles, f, ensure_ascii=False, indent=4)

    # 나머지 종목 json 확인
    with open("step2_db_only.json", "w", encoding="utf-8") as f:
        json.dump(db_only_articles, f, ensure_ascii=False, indent=4)

    return full_pipeline_articles, db_only_articles



