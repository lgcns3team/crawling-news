from config_companies import FULL_PIPELINE_COMPANY_NAMES

from step1_naver_articles import run_step1
from step2_articles_with_content import run_step2
from step3_articles_with_summary_and_groups import run_step3
from step4_articles_with_sentiment import run_step4


# ---------- 메인 파이프라인 (1시간마다 실행할 애) ----------

def main():
    # 1) STEP1: 20개 종목 * 기사 20개 메타데이터
    step1_result = run_step1()
    articles_step1 = step1_result["articles"]

    # 2) STEP2: 전체 기사에 대해 본문 크롤링
    articles_step2 = run_step2(articles_step1)

    # 3) 회사별로 분리 (company_name 기준)
    full_target_articles = [
        a for a in articles_step2
        if a.get("company_name") in FULL_PIPELINE_COMPANY_NAMES
    ]
    raw_only_articles = [
        a for a in articles_step2
        if a.get("company_name") not in FULL_PIPELINE_COMPANY_NAMES
    ]

    print(f"\nFULL PIPELINE 대상 기사 수: {len(full_target_articles)}")
    print(f"RAW ONLY 대상 기사 수: {len(raw_only_articles)}")

    # 4) 15종목: STEP1+2만 → DB에 raw 저장
    # save_raw_news_to_db(raw_only_articles)

    # 5) 5종목: STEP3 → STEP4 
    if full_target_articles:
        # run_step3 는 {"articles": [...], "groups": [...]} 구조를 리턴함
        step3_result = run_step3(full_target_articles)
        articles_step3 = step3_result["articles"]     # 요약 붙은 리스트만 꺼내기

        # run_step4 는 리스트를 받아서 sentiment 붙인 리스트를 리턴
        step4_result = run_step4(articles_step3)


if __name__ == "__main__":
    main()
