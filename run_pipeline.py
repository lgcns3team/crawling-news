from config_companies import FULL_PIPELINE_COMPANY_NAMES
from step1_naver_articles import step1_naver_articles
from step2_articles_with_content import step2_articles_with_content
from step3_articles_with_summary_and_groups import step3_articles_with_summary_and_groups
from step4_articles_with_sentiment import setp4_articles_with_sentiment
from db_config import get_connection


def main():

    result_by_step1= step1_naver_articles()
    step2_articles_with_content()
    step3_articles_with_summary_and_groups()
    setp4_articles_with_sentiment()


if __name__ == "__main__":
    get_connection()
    main()
