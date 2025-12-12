from config_companies import FULL_PIPELINE_COMPANY_NAMES
from step1_naver_articles import step1_naver_articles
from step2_articles_with_content import step2_articles_with_content
from step3_articles_with_summary_and_groups import step3_articles_with_summary_and_groups
from step4_articles_with_sentiment import setp4_articles_with_sentiment
from db_config import get_connection
from db_insert import save_step2_results_to_db,save_step3_results_to_db,save_step4_results_to_db

def main():

    conn = get_connection()
    
    result_by_step1 = step1_naver_articles()
    
    result_by_step2, result_by_step2_db = step2_articles_with_content(result_by_step1)
    
    result_by_step3 = step3_articles_with_summary_and_groups(result_by_step2)
    
    result_by_step4 = setp4_articles_with_sentiment(result_by_step3)

    save_step3_results_to_db(conn, result_by_step3)
    save_step2_results_to_db(conn, result_by_step2_db)
    #save_step4_results_to_db(conn, result_by_step4)

if __name__ == "__main__":
    main()
