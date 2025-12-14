from db_config import get_connection


# 집계 주기마다 실행해서 Stocks_score 테이블 업데이트
# cron으로 감정점수 업데이트하는 주기와 일치해야함


def main():
    conn = get_connection()

    #집계 볌위가 1시간단위 -> 바꾸려면 where절 수정 ex)  INTERVAL 15 MINUTE, INTERVAL 1 DAY
    select_sql = """
        SELECT
            c.id AS company_id,
            AVG(s.score) AS avg_score
        FROM sentiments s
        JOIN news n ON s.news_id = n.id
        JOIN companies c ON n.company_id = c.id
        WHERE s.date >= NOW() - INTERVAL 1 HOUR
        GROUP BY c.id
    """

    upsert_sql = """
    INSERT INTO Stocks_score (company_id, score, date)
    VALUES (%s, %s, DATE_FORMAT(NOW(), '%%Y-%%m-%%d %%H:00:00'))
    ON DUPLICATE KEY UPDATE
        score = VALUES(score)
    """

    try:
        with conn.cursor() as cur:
            cur.execute(select_sql)
            rows = cur.fetchall()

            if not rows:
                return

            for row in rows:
                company_id = row["company_id"]
                avg_score = row["avg_score"]
                if avg_score is None:
                    continue

                cur.execute(upsert_sql, (company_id, float(avg_score)))

        conn.commit()

    finally:
        conn.close()

if __name__ == "__main__":
    main()
