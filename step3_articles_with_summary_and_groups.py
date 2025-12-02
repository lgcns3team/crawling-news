from typing import Dict, Any, List
import json
import os
from datetime import datetime

import pymysql
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

# 0. LLM 설정
MODEL_NAME = "gpt-4o-mini"

client = OpenAI(
    api_key=os.environ.get("gpt_key")  # 환경변수에 키 넣어두기
)

SYSTEM_PROMPT = """
너의 역할은 두 가지다.

1) 각 기사에 대해 감정분석에 쓰기 좋은 요약 summary_ko를 생성한다.
   - summary_ko는 한국어 문장으로 작성한다.
   - 문장 수는 자유지만, 너무 길지 않게 1~4문장 정도로 간결하게 작성한다.
   - 인사말이나 자기소개 없이 바로 요약 내용으로 시작한다.
   - 기사에서 말하는 핵심 사건/주제, 관련 기업/인물/기관, 주요 수치(투자 규모, 실적, 손실 등)가 있으면 가능한 포함한다.
   - 기사 전체의 톤(호재, 악재, 우려, 갈등, 중립적 분석 등)이 드러나도록 쓴다.
   - 새로운 의견을 만들어내지 말고, 기사에 실제로 등장하는 평가/분위기만 반영한다.
   - 문장은 모두 평서형으로 끝낸다.

2) 서로 내용이 실질적으로 동일하거나, 같은 뉴스 이벤트를 약간 다른 표현으로 전하는 중복 기사들을 그룹으로 묶는다.
   - 같은 기업/인물/사건/날짜/수치 등을 공유하며, 사실상 같은 뉴스를 반복 보도한 것으로 판단되면 같은 그룹에 넣는다.
   - 제목이 다르더라도, 내용이 같은 사건을 다루면 같은 그룹이다.
   - 한 그룹은 2개 이상의 기사 id를 포함해야 한다. (1개만 있으면 그룹으로 만들지 않는다.)
   - 서로 겹치지 않는 단독 기사는 그룹에 포함시키지 않는다.
3) 출력 형식은 반드시 아래 JSON 구조를 따라야 한다.
    - 입력 JSON의 articles 배열에 들어온 각 기사 객체의 id 값은 절대로 변경하지 말라.
    - 새로운 번호(1,2,3...)를 다시 부여하지 말고, 입력에 있던 id 그대로를 사용하라.
    - 각 기사에 대한 summary_ko는 그 기사 객체의 id와 1:1로 대응되도록 작성하라.    
반드시 아래 형식의 JSON만 출력하라. 다른 설명 문장은 출력하지 마라.

{
  "articles": [
    {
      "id": 1,
      "summary_ko": "이곳에 id=1 기사에 대한 요약 문장"
    },
    {
      "id": 2,
      "summary_ko": "이곳에 id=2 기사에 대한 요약 문장"
    }
  ],
  "groups": [
    {
      "group_id": 1,
      "article_ids": [1, 3, 5],
      "reason": "예: 삼성전자 사장단 인사 발표를 다룬 중복 기사들"
    },
    {
      "group_id": 2,
      "article_ids": [2, 4],
      "reason": "예: 같은 반도체 투자 계약 관련 기사들"
    }
  ]
}
"""

# 1. DB 설정 (company_id 안 씀)

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

# 발표용 5개 종목 (STEP1~4 풀파이프라인)
# names는 step1/2에서 쓰는 company_name이랑 똑같이 맞춰야 함
FULL_PIPELINE_COMPANY_NAMES = {
    "삼성전자",
    "현대차",
    "LG에너지솔루션",
    "한화솔루션",
    "두산에너빌리티",
}

def is_full_pipeline_company(company_name: str) -> bool:
    return company_name in FULL_PIPELINE_COMPANY_NAMES

# 2. LLM 호출

def call_llm_for_summaries_and_groups(
    articles_with_content: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    여러 기사를 한 번에 LLM에 넘겨서:
    - 각 기사별 summary_ko 생성
    - 중복 기사 groups 생성
    을 JSON으로 받아온다.

    ⚠ 여기로 들어오는 articles_with_content는
      이미 "5개 종목만" 필터링된 상태라고 가정한다.
    """

    payload = {
    "articles": [
        {
            "id": article.get("news_id"),
            "title": article.get("title", ""),
            "content": article.get("content", ""),
        }
        for article in articles_with_content
        if article.get("content") and article.get("news_id")
    ]
}


    if not payload["articles"]:
        print("[WARN] content 있는 기사가 하나도 없음. LLM 호출 스킵.")
        return {"articles": [], "groups": []}

    user_input = json.dumps(payload, ensure_ascii=False)

    print(f"=== [STEP3] LLM 호출: 기사 수 = {len(payload['articles'])} ===")

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=SYSTEM_PROMPT.strip(),
        input=user_input,
    )

    raw_text = response.output_text

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        print("[ERROR] LLM 응답이 JSON 파싱에 실패했습니다.")
        print("----- raw_text begin -----")
        print(raw_text)
        print("----- raw_text end -----")
        return {"articles": [], "groups": []}

    if "articles" not in parsed:
        parsed["articles"] = []
    if "groups" not in parsed:
        parsed["groups"] = []

    return parsed


# 3. DB 저장 (대표 5개 요약본)

def save_summarized_article_to_db(conn, article: Dict[str, Any]) -> None:
    """
    대표 5개 종목 기사에 대해,
    STEP2에서 이미 생성된 News row의 summary_text만 UPDATE 한다.
    필요한 필드:
      - article["news_id"]  : News.id (PK)
      - article["summary_text"] : 요약문
    """
    news_id = article.get("news_id")
    if not news_id:
        print("   [ERROR] save_summarized_article_to_db: news_id 없음 → UPDATE 불가")
        return False

    summary_text = article.get("summary_text", "")


    sql = """
    UPDATE News
    SET summary_text = %s
    WHERE id = %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, (summary_text, news_id))

    return True

# 4. STEP3 메인

def run_step3(
    articles_with_content: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    STEP2 결과(articles_with_content)에 대해:
      1) 대표 5개 종목 기사만 필터링
      2) LLM으로 summary_ko + groups 생성
      3) summary_ko를 summary_text로 붙인 articles 리스트 생성
      4) news 테이블에 (full_text + summary_text) 저장
      5) {"articles": [...], "groups": [...]} 형태로 리턴
    """
    print(f"=== [STEP3] 시작: 입력 기사 수 = {len(articles_with_content)} ===")

    # 1) 대표 5개 종목 기사만 추리기
    target_articles: List[Dict[str, Any]] = [
        a for a in articles_with_content
        if is_full_pipeline_company(a.get("company_name", ""))
    ]

    print(f"   ↳ 대표 5개 종목 기사 수 = {len(target_articles)}")

    if not target_articles:
        print("[WARN] 대표 5개 종목 기사 없음. STEP3 종료.")
        return {"articles": [], "groups": []}

    # 2) LLM 호출해서 요약 + 그룹 정보 받기
    llm_result = call_llm_for_summaries_and_groups(target_articles)
    summarized_articles = llm_result.get("articles", [])
    groups = llm_result.get("groups", [])

    # id -> summary_ko 매핑
    summary_map: Dict[Any, str] = {
        item.get("id"): item.get("summary_ko", "") for item in summarized_articles
    }

    # 3) summary_text 붙이기 + 4) DB 저장
    result_articles: List[Dict[str, Any]] = []
    missing_count = 0
    db_update_count = 0

    conn = get_connection()
    input_ids = sorted(a.get("news_id") for a in target_articles if a.get("news_id"))
    output_ids = sorted(item.get("id") for item in summarized_articles)
    
    print("입력 id 목록:", input_ids)
    print("LLM 출력 id 목록:", output_ids)
    try:
        for article in target_articles:
            news_id = article.get("news_id")
            content = article.get("content", "")

            if not news_id:
                print(f"[WARN] news_id 없음, 스킵 (title={article.get('title', '')})")
                continue
            
            if not content:
                print(f"[WARN] content 없음, 스킵 (news_id={news_id})")
                continue

            summary = summary_map.get(news_id)
            if not summary:
                missing_count += 1
                print(f"[WARN] LLM 결과에 요약이 없음 (news_id={news_id}), 빈 문자열로 처리.")
                summary = ""

            new_article = {
                **article,
                "summary_text": summary,
                "news_id": news_id,
            }

            # DB 저장 (대표 5개만)
            try:
                ok = save_summarized_article_to_db(conn, new_article)
                if ok:
                    db_update_count += 1
            except Exception as e:
                print(f"[ERROR] summary UPDATE 실패 (news_id={news_id}): {e}")

            result_articles.append(new_article)

    finally:
        conn.close()

    print(f"\n[STEP3] 완료: 요약된 기사 수 = {len(result_articles)}")
    if missing_count > 0:
        print(f"   ↳ 요약 누락 기사 수 = {missing_count}")
    print(f"   ↳ 그룹 수 = {len(groups)}")
    print(f"   ↳ [DB] summary_text UPDATE 건수 = {db_update_count}")

    return {
        "articles": result_articles,
        "groups": groups,
    }


# 5. 단독 실행 모드

if __name__ == "__main__":
    INPUT_FILE = "step2_articles_with_content.json"
    OUTPUT_FILE = "step3_articles_with_summary_and_groups.json"

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        step2_data = json.load(f)

    articles = step2_data.get("articles", [])
    output_data = run_step3(articles)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장 완료 → {OUTPUT_FILE}")
