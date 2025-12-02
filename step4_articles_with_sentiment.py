from datetime import datetime
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv
import os
from transformers import pipeline
import pymysql

load_dotenv()
DB_HOST = os.getenv("db_host")
DB_PORT = os.getenv("db_port")
DB_USER = os.getenv("db_user")
DB_PASSWORD = os.getenv("db_password")
DB_NAME = os.getenv("db_name")
HF_TOKEN = os.getenv("huggingface_api_token") 
if not HF_TOKEN:
    raise RuntimeError(".env 파일에 hf_token 이 없습니다. hfcl_token=... 형태로 추가해 주세요.")
MODEL_NAME = "DataWizardd/finbert-sentiment-ko"

print(f"감정분석 모델 로딩 중: {MODEL_NAME}")
sentiment_pipe = pipeline(
    "text-classification",
    model=MODEL_NAME,
    token=HF_TOKEN,      
    top_k=None,         
    max_length=512,
)

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

def save_sentiments_to_db(articles: List[Dict[str, Any]]):
    """
    STEP4 감정분석 결과만 Sentiments 테이블에 저장한다.

    요구되는 필드:
      - news_id
      - sentiment_label -> label
      - prob_pos / prob_neg / prob_neu
      - sentiment_score -> score
      - sentiment_date -> date (없으면 NOW())
    """

    if not articles:
        print("감정 저장할 데이터 없음, 스킵")
        return

    conn = get_connection()

    sql_sent = """
        INSERT INTO Sentiments (
            label, prob_pos, prob_neg, prob_neu, score, date, news_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    inserted_count = 0

    try:
        with conn.cursor() as cur:
            for art in articles:
                news_id = art.get("news_id")
                if not news_id:
                    print(f"news_id 없음 → 스킵: {art.get('title', '')}")
                    continue

                sent_date = datetime.now()

                cur.execute(
                    sql_sent,
                    (
                        art.get("sentiment_label", ""),
                        float(art.get("prob_pos", 0.0)),
                        float(art.get("prob_neg", 0.0)),
                        float(art.get("prob_neu", 0.0)),
                        float(art.get("sentiment_score", 0.0)),
                        sent_date,
                        news_id,
                    ),
                )
                inserted_count += 1

        conn.commit()
        print(f"Sentiments 저장 완료: {inserted_count}건")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] save_sentiments_to_db 실패: {e}")
        raise

    finally:
        conn.close()

def compute_k_index(p_pos: float, p_neu: float, p_neg: float):
    """
    0~100 점수 계산:

    base = 긍정 - 부정
    confidence = 1 - 중립
    S = base * confidence
    score = (S + 1) / 2 * 100
    """

    base = p_pos - p_neg          # 긍정 - 부정
    confidence = 1.0 - p_neu      # 1 - 중립
    S = base * confidence
    raw_score = (S + 1.0) / 2.0 * 100.0
    score = max(0.0, min(100.0, raw_score))  # 0~100 클램프

    if score >= 80:
        zone = "강한 매수 감정 (FOMO/과열 가능 구간)"
    elif score >= 60:
        zone = "매수 우위"
    elif score >= 40:
        zone = "중립 구간"
    elif score >= 20:
        zone = "매수 비추천"
    else:
        zone = "강한 매수 금지"

    return score, zone

def analyze_sentiment(text: str) -> Tuple[str, float]:
    """
    요약문(또는 본문)에 대해 감성 분석.
    리턴: (label, score)
      - label: "positive" / "neutral" / "negative"
      - score: 0.0 ~ 1.0 (또는 네가 쓰는 스케일)
    """

    if not text or not text.strip():
        return {
            "label": "UNKNOWN",
            "raw_score": 0.0,
            "prob_positive": 0.0,
            "prob_neutral": 1.0,
            "prob_negative": 0.0,
            "sentiment_index": 50.0,
            "sentiment_zone": "데이터 없음",
        }

    snippet = text.strip()
    if len(snippet) > 512:
        snippet = snippet[:512]

    try:
        # top_k=None → 모든 라벨 확률 반환
        # 결과 형태: [[{"label": "...", "score": ...}, ...]]
        outputs = sentiment_pipe(snippet, truncation=True)[0]
    except Exception as e:
        print(f"감정분석 중 오류 발생: {e}")
        return {
            "label": "ERROR",
            "raw_score": 0.0,
            "prob_positive": 0.0,
            "prob_neutral": 1.0,
            "prob_negative": 0.0,
            "sentiment_index": 50.0,
            "sentiment_zone": "오류",
        }

    p_pos = 0.0
    p_neu = 0.0
    p_neg = 0.0

    for item in outputs:
        label = item.get("label", "")
        score = float(item.get("score", 0.0))

        if label in ["긍정", "positive", "POSITIVE", "LABEL_2"]:
            p_pos = score
        elif label in ["중립", "neutral", "NEUTRAL", "LABEL_1"]:
            p_neu = score
        elif label in ["부정", "negative", "NEGATIVE", "LABEL_0"]:
            p_neg = score

    if (p_pos + p_neu + p_neg) == 0.0:
        best = max(outputs, key=lambda x: x.get("score", 0.0))
        p_pos = float(best.get("score", 1.0))
        p_neu = 0.0
        p_neg = 0.0

    best_label_item = max(outputs, key=lambda x: x.get("score", 0.0))
    best_label = best_label_item.get("label", "UNKNOWN")
    best_score = float(best_label_item.get("score", 0.0))

    sentiment_index, sentiment_zone = compute_k_index(p_pos, p_neu, p_neg)

    return {
        "label": best_label,
        "raw_score": best_score,
        "prob_positive": p_pos,
        "prob_neutral": p_neu,
        "prob_negative": p_neg,
        "sentiment_index": sentiment_index,
        "sentiment_zone": sentiment_zone,
    }


def run_step4(articles_with_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    print(f"=== [STEP4] 시작: 입력 기사 수 = {len(articles_with_summary)} ===")
    result: List[Dict[str, Any]] = []

    for idx, article in enumerate(articles_with_summary, start=1):
        text = article.get("summary_text") or article.get("content") or ""
        if not text:
            print(f"[WARN] 요약/본문 없음, 스킵 (id={article.get('id')})")
            continue

        print(f"\n[{idx}/{len(articles_with_summary)}] 감성분석 중... id={article.get('id')}")
        sent = analyze_sentiment(text)
        print(
            f"   → label={sent['label']}, "
            f"p_pos={sent['prob_positive']:.3f}, "
            f"p_neu={sent['prob_neutral']:.3f}, "
            f"p_neg={sent['prob_negative']:.3f}, "
            f"index={sent['sentiment_index']:.2f}"
        )

        new_article = {
            **article,
            "sentiment_label": sent["label"],
            "prob_pos": sent["prob_positive"],
            "prob_neu": sent["prob_neutral"],
            "prob_neg": sent["prob_negative"],
            # Sentiments.score 에 들어갈 값 (0~100 점수)
            "sentiment_score": sent["sentiment_index"],
            "sentiment_zone": sent["sentiment_zone"],
            # DB date용 – step3에서 기사 시간 필드를 "datetime"으로 넣어줬다고 가정
            "sentiment_date": article.get("datetime"),
        }
        result.append(new_article)

    print(f"\n[STEP4] 완료: 감성분석 완료 기사 수 = {len(result)}")
    save_sentiments_to_db(result)
    return result


if __name__ == "__main__":
    import json

    with open("step3_articles_with_summary_and_groups.json", "r", encoding="utf-8") as f:
        step3_data = json.load(f)

    articles = step3_data.get("articles", [])
    result = run_step4(articles)

    with open("step4_articles_with_sentiment.json", "w", encoding="utf-8") as f:
        json.dump({"articles": result}, f, ensure_ascii=False, indent=2)
