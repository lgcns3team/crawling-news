import os
import time
from typing import Dict, Any, List, Optional

from newspaper import Article
from newspaper.article import ArticleException
from dotenv import load_dotenv

import pymysql

# 0. DB 설정
load_dotenv()
DB_HOST = os.getenv("db_host")
DB_PORT = os.getenv("db_port")
DB_USER = os.getenv("db_user")
DB_PASSWORD = os.getenv("db_password")
DB_NAME = os.getenv("db_name")

def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        autocommit=True,
    )

# 1. 대표 5개 / 나머지 15개 구분

# 여기 회사 이름은 config_companies.py의 company_name 값이랑 똑같이 맞춰줘야 함
FULL_PIPELINE_COMPANY_NAMES = {
    "삼성전자",
    "현대차",
    "LG에너지솔루션",
    "한화솔루션",
    "두산에너빌리티",
}


def is_full_pipeline_company(company_name: str) -> bool:
    """
    발표용 5개 종목인지 여부.
    True  → 1~4스텝 전부 돌릴 애들 (STEP2에서 DB 저장 안 함)
    False → 1~2스텝까지만 우선 돌릴 애들 (STEP2에서 본문 DB 저장)
    """
    return company_name in FULL_PIPELINE_COMPANY_NAMES

# 2. newspaper3k 본문 추출

def fetch_article_with_newspaper(url: str, language: str = "ko") -> Optional[Dict[str, Any]]:
    if not url:
        return None

    try:
        article = Article(url, language=language)
        article.download()
        article.parse()

        text = (article.text or "").strip()
        if len(text) < 100:
            print(f"[WARN] 본문 너무 짧음(len={len(text)}), 스킵: {url}")
            return None

        return {"content": text}

    except ArticleException as e:
        print(f"[WARN] ArticleException: {url} ({e})")
        return None
    except Exception as e:
        print(f"[WARN] newspaper3k 예외: {url} ({e})")
        return None


# 3. DB 저장 (20개 전부)

def save_raw_article_to_db(conn, article: Dict[str, Any]) -> None:
    """
    20개 종목 전부에 대해 호출:
    - full_text: STEP2에서 추출한 content
    - summary_text: 아직 없음 → NULL

    News 테이블 컬럼 (현재 ERD 기준):
      id (PK, AI)
      title
      date
      full_text
      url
      summary_text
      company_id
    """
    sql = """
    INSERT INTO News (
        title,
        date,
        full_text,
        url,
        summary_text,
        company_id
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    """

    title = article.get("title", "")
    full_text = article.get("content", "")
    url = article.get("url", "")
    date = article.get("datetime", "")
    company_id = article.get("company_id", "")
    summary_text = None  # STEP3에서 요약문 UPDATE 예정

    with conn.cursor() as cur:
        try:
            cur.execute(
                sql,
                (
                    title,
                    date,
                    full_text,
                    url,
                    summary_text,
                    company_id,
                ),
            )
            news_id = cur.lastrowid #이번에 INSERT된 row의 PK(id) 를 가져오는 기능
            return news_id

        except pymysql.err.IntegrityError:
            # 이미 같은 url이 있는 경우 → 기존 id 재사용
            print("[SKIP] 이미 저장된 뉴스(URL 중복) → 기존 id 재사용")
            cur.execute("SELECT id FROM News WHERE url = %s", (url,))
            row = cur.fetchone()
            if row:
                return row[0]
            else:
                raise

# 4. STEP2 메인 로직

def run_step2(
    articles_from_step1: List[Dict[str, Any]],
    sleep_sec: float = 0.3,
) -> List[Dict[str, Any]]:
    """
    STEP1 결과에 'content' 필드를 붙여서 리턴.
    + 나머지 15개 종목에 대해서는 여기서 본문을 DB(news)에 바로 저장.

    ● 공통:
      - return 값에는 20개 종목 전체(본문 추출 성공한 기사들)가 다 포함됨.
      - 이후 대표 5개 종목은 STEP3/4에서 요약/감정분석에 사용.

    ● DB 저장:
      - company_name이 FULL_PIPELINE_COMPANY_NAMES에 포함되지 않는 경우에만
        save_raw_article_to_db()를 호출해서 news 테이블에 INSERT.
    """
    print(f"=== [STEP2] 시작: 입력 기사 수 = {len(articles_from_step1)} ===")

    conn = get_connection()

    articles_with_content: List[Dict[str, Any]] = []
    db_saved_count = 0
    

    try:
        for idx, article in enumerate(articles_from_step1, start=1):
            url = article.get("originallink") or article.get("link")
            aid = article.get("id")
            company_name = article.get("company_name", "")

            print(f"\n▶ [{idx}/{len(articles_from_step1)}] step1_id={aid}")
            print(f"   회사: {company_name}")
            print(f"   URL: {url}")
            if not url:
                print("   [WARN] URL 없음, 스킵")
                continue

            with conn.cursor() as cur:
                cur.execute("SELECT id FROM News WHERE url = %s", (url,))
                row = cur.fetchone()

            if row:
                print("[SKIP] 이미 DB에 저장된 기사 → 이번 파이프라인에서 제외")
                continue

            np_data = fetch_article_with_newspaper(url) # newspaper3k 본문 추출
            if not np_data:
                print("   → 본문 없음/실패, 스킵")
                continue

            content = np_data["content"]
            print(f"   → 본문 추출 성공: 길이={len(content)}자")

            merged = {
                **article,
                "url": url,
                "content": content,
            }
            try:
                news_id = save_raw_article_to_db(conn, merged)
                merged["news_id"] = news_id
                db_saved_count += 1
                print(f"   → [DB] news 테이블에 full_text 저장/재사용 완료 (news_id={news_id})")
            except Exception as e:
                print(f"   [ERROR] DB 저장 실패 (step1_id={aid}): {e}")
                # DB에 저장 못 했으면 FK 연결이 안 되므로, 이 기사는 다음 스텝으로 넘기지 않음
                continue

            
            if is_full_pipeline_company(company_name):
                articles_with_content.append(merged)
                print("   → 대표 5개 종목 기사이므로 STEP3/4 대상으로 포함")
            else:
                print("   → 나머지 15개 종목: DB 저장만 하고 STEP3/4에는 넘기지 않음")


            if sleep_sec > 0:
                time.sleep(sleep_sec)

    finally:
        conn.close()

    print(f"\n[STEP2] 완료: 본문 있는 기사 수 = {len(articles_with_content)}")
    print(f"   ↳  20개 종목 DB 저장 건수 = {db_saved_count}")
    return articles_with_content

# 5. 단독 실행 모드

if __name__ == "__main__":
    import json

    with open("step1_naver_articles.json", "r", encoding="utf-8") as f:
        step1_data = json.load(f)

    articles = step1_data.get("articles", [])
    result = run_step2(articles)

    with open("step2_articles_with_content.json", "w", encoding="utf-8") as f:
        json.dump({"articles": result}, f, ensure_ascii=False, indent=2)

    print("\nstep2_articles_with_content.json 저장 완료")

