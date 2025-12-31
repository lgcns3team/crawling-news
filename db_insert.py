import json
import os   # [DRY_RUN 수정] 환경변수 사용을 위해 추가 -

# [DRY_RUN 수정]
# DRY_RUN=true 이면 DB INSERT / UPDATE를 수행하지 않는다
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

def filter_step1_by_db_urls(conn, articles):
    urls = []
    for art in articles:
        url = art.get("originallink")
        if url:
            urls.append(url)

    urls = list(set(urls))
    if not urls:
        return articles

    placeholders = ",".join(["%s"] * len(urls))
    sql = f"SELECT url FROM News WHERE url IN ({placeholders})"

    with conn.cursor() as cur:
        cur.execute(sql, urls)
        existing = {row["url"] for row in cur.fetchall()}

    filtered = []
    for art in articles:
        url = art.get("originallink")
        if url and url in existing:
            continue
        filtered.append(art)
        
    print(f"step1 필터링 완료: 필터링 후 수집 기사 수 = {len(filtered)}건")
    
    #with open("step1_naver_articles_filtered.json", "w", encoding="utf-8") as f:
    #    json.dump(filtered, f, ensure_ascii=False, indent=2)
    
    return filtered



def save_step2_results_to_db(conn, articles):
     # [DRY_RUN 추가]
    # 테스트 모드에서는 DB에 News INSERT를 하지 않음
    if DRY_RUN:
        print(f"[DRY_RUN] step2 News(DBONLY) 저장 스킵 ({len(articles)}건)")
        return
    
    sql = """
        INSERT INTO News (title, date, full_text, url, company_id)
        VALUES (%s, %s, %s, %s, %s)
    """

    check_sql = "SELECT id FROM News WHERE url = %s LIMIT 1"

    with conn.cursor() as cur:
        for art in articles:
            cur.execute(check_sql, (art["url"]))
            exists = cur.fetchone()

            if exists:
                print(f"이미 존재하는 뉴스 URL {art['id']}")
                continue

            cur.execute(
                sql,
                (art["title"], art["date"], art["full_text"], art["url"], art["company_id"])
            )
    conn.commit()
    print(f" News(DBONLY) {len(articles)}건 저장 완료")

def save_step3_results_to_db(conn,articles):
    # [DRY_RUN 추가]
    # 테스트 모드에서는 요약된 뉴스 DB 저장을 전부 스킵
    if DRY_RUN:
        print(f"[DRY_RUN] step3 News(SUMMARY) 저장 스킵 ({len(articles)}건)")
        return
    
    sql = """
        INSERT INTO News (title, date, full_text, url, summary_text, company_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    check_sql = "SELECT id FROM News WHERE url = %s LIMIT 1"
    
    with conn.cursor() as cur:
        for art in articles:
            summary = art["summary_text"]
            if summary and len(summary) > 150:
                print("요약 너무 길면 스킵:", len(summary))
                continue
            cur.execute(check_sql, (art["url"],))
            exists = cur.fetchone()

            if exists:
                print(f"이미 존재하는 뉴스 URL {art['url']}")
                continue

            try:
                cur.execute(
                    sql,
                    (
                        art["title"],
                        art["date"],
                        art["full_text"],
                        art["url"],
                        art["summary_text"],
                        art["company_id"],
                    ),
                )
            except Exception as e:
                print(f"STEP3: DB 저장 중 오류 발생 - {art['url']}: {e}")
                continue

    conn.commit()
    print(f" News(SUMMARY) {len(articles)}건 저장 완료")

def save_step4_results_to_db(conn, articles):
    # [DRY_RUN 추가]
    # 감정 분석 결과 + News / Sentiments 테이블 반영을
    # 테스트 모드에서는 전부 차단
    if DRY_RUN:
        print(f"[DRY_RUN] step4 News + Sentiments 저장 스킵 ({len(articles)}건)")
        return

    # News 관련 SQL
    news_check_sql = "SELECT id FROM News WHERE url = %s LIMIT 1"
    news_insert_sql = """
        INSERT INTO News (title, date, full_text, url, summary_text, company_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    # Sentiments 관련 SQL
    sent_upsert_sql = """
        INSERT INTO Sentiments (label, prob_pos, prob_neg, prob_neu, score, date, news_id)
        VALUES (%s, %s, %s, %s, %s, NOW(), %s)
        ON DUPLICATE KEY UPDATE
            label = VALUES(label),
            prob_pos = VALUES(prob_pos),
            prob_neg = VALUES(prob_neg),
            prob_neu = VALUES(prob_neu),
            score = VALUES(score),
            date = NOW()
    """

    inserted_news = 0
    upserted_sent = 0
    skipped = 0

    with conn.cursor() as cur:
        for art in articles:
            url = art.get("url")
            if not url:
                skipped += 1
                continue

            summary = art.get("summary_text")
            if summary and len(summary) > 300:
                print("요약 너무 길면 스킵:", len(summary), url)
                skipped += 1
                continue
            
            # News: INSERT if not exists 
            cur.execute(news_check_sql, (url,))
            row = cur.fetchone()

            if row:
                news_id = row["id"] if isinstance(row, dict) else row[0]
            else:
                try:
                    cur.execute(
                        news_insert_sql,
                        (
                            art.get("title"),
                            art.get("date"),
                            art.get("full_text"),
                            url,
                            summary,
                            art.get("company_id"),
                        ),
                    )
                    news_id = cur.lastrowid
                    inserted_news += 1
                except Exception as e:
                    print(f"DB: News INSERT 실패 - {url}: {e}")
                    skipped += 1
                    continue

            # Sentiments: UPSERT
            label = art.get("sentiment_label")
            p_pos = art.get("p_positive")
            p_neg = art.get("p_negative")
            p_neu = art.get("p_neutral")
            score = art.get("k_index")

            if label is None or p_pos is None or p_neg is None or p_neu is None or score is None:
                print(f"DB: Sentiments 값 부족 스킵 - news_id={news_id}, url={url}")
                skipped += 1
                continue

            try:
                cur.execute(
                    sent_upsert_sql,
                    (label, p_pos, p_neg, p_neu, score, news_id),
                )
                upserted_sent += 1
            except Exception as e:
                print(f"DB: Sentiments UPSERT 실패 - news_id={news_id}, url={url}: {e}")
                skipped += 1
                continue

    conn.commit()
    print("STEP4 DB 저장 결과")
    print(f" - News(summary) 저장: {inserted_news}")
    print(f" - Sentiments(감정분석) 저장: {upserted_sent}")
    print(f" - 스킵: {skipped}")
