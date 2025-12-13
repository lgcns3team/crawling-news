

def save_step2_results_to_db(conn, articles):
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
    print(f" News {len(articles)}건 저장 완료")

def save_step3_results_to_db(conn,articles):
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
    print(f" News(요약 포함) {len(articles)}건 저장 완료")

def save_step4_results_to_db():
    pass