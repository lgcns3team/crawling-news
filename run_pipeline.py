# run_pipeline.py
import os
import json
from dotenv import load_dotenv

from step1_naver_articles import step1_naver_articles
from step2_articles_with_content import step2_articles_with_content
from step3_articles_with_summary_and_groups import step3_articles_with_summary_and_groups
from step4_articles_with_sentiment import step4_articles_with_sentiment

load_dotenv()

# STEP3/4로 흘려보낼 기사 수 제한 (기본 20)
TEST_ARTICLE_LIMIT = int(os.getenv("TEST_ARTICLE_LIMIT", "20"))

# STEP2 캐시 사용 여부 (1이면 step2_full_pipeline.json을 읽어서 STEP3부터 실행)
USE_STEP2_CACHE = os.getenv("USE_STEP2_CACHE", "0").strip() == "1"
STEP2_CACHE_FILE = os.getenv("STEP2_CACHE_FILE", "step2_full_pipeline.json")


def main():
    # 1) STEP2 캐시가 있으면 그걸로 고정 입력 사용
    if USE_STEP2_CACHE and os.path.exists(STEP2_CACHE_FILE):
        print(f"[CACHE] STEP2 캐시 사용: {STEP2_CACHE_FILE}")
        with open(STEP2_CACHE_FILE, "r", encoding="utf-8") as f:
            result_by_step2 = json.load(f)

    # 2) 캐시 미사용이면 기존대로 STEP1/2 실행 (STEP2가 step2_full_pipeline.json 저장함)
    else:
        # 1) STEP1: 네이버 뉴스 후보 수집
        result_by_step1 = step1_naver_articles()

        # 2) STEP2: 본문 추출
        result_by_step2, _ = step2_articles_with_content(result_by_step1)

        # step2가 이미 step2_full_pipeline.json 저장하지만,
        # 파일명이 다를 수 있으니 여기서도 보장 저장
        try:
            with open(STEP2_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(result_by_step2, f, ensure_ascii=False, indent=2)
            print(f"[CACHE] STEP2 캐시 저장: {STEP2_CACHE_FILE}")
        except Exception as e:
            print(f"[CACHE] STEP2 캐시 저장 실패(무시): {e}")

    # 테스트를 위해 STEP3/4로 들어갈 기사 수를 제한
    limited_step2 = result_by_step2[:TEST_ARTICLE_LIMIT]
    print(f"\n[TEST MODE] STEP3/4 입력 기사 수 제한: {len(limited_step2)} / 원본 {len(result_by_step2)}\n")

    # 3) STEP3: 요약 + 관련성 판단 (백엔드는 STEP3_BACKEND 환경변수로)
    result_by_step3 = step3_articles_with_summary_and_groups(limited_step2)

    # 4) STEP4: 감성 분석 (STEP3_BACKEND에 따라 ko/en 모델 자동 전환)
    step4_articles_with_sentiment(result_by_step3)

    # DB 저장 비활성화
    print("\n[DB] 테스트 모드: DB 저장을 수행하지 않습니다.\n")


if __name__ == "__main__":
    main()