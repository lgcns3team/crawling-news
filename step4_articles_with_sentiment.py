import json
import os
from dotenv import load_dotenv
from transformers import pipeline

load_dotenv()
HF_TOKEN = os.getenv("huggingface_api_token") 
MODEL_NAME = "DataWizardd/finbert-sentiment-ko"
sentiment_pipe = pipeline(
    "text-classification",
    model=MODEL_NAME,
    token=HF_TOKEN,      
    top_k=None,
    truncation=True,    
    max_length=512,
)

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
    score = max(0.0, min(100.0, raw_score))  
    return score

def analyze_sentiment(text):
    if not text or not text.strip():
        return None, 0.0, 1.0, 0.0, 50.0
    out = sentiment_pipe(text.strip())

    if isinstance(out, list) and len(out) > 0 and isinstance(out[0], list):
        out = out[0]

    scores = {}
    for r in out:
        lab = str(r["label"]).upper()
        scores[lab] = float(r["score"])

    p_pos = scores.get("POSITIVE", scores.get("LABEL_2", 0.0))
    p_neu = scores.get("NEUTRAL", scores.get("LABEL_1", 0.0))
    p_neg = scores.get("NEGATIVE", scores.get("LABEL_0", 0.0))

    best_label = max(
        [("POSITIVE", p_pos), ("NEUTRAL", p_neu), ("NEGATIVE", p_neg)],
        key=lambda x: x[1]
    )[0]

    k_index = compute_k_index(p_pos, p_neu, p_neg)
    return best_label, p_pos, p_neu, p_neg, k_index

    

def step4_articles_with_sentiment(result_by_step3):
    result_with_sentiment = []
    for art in result_by_step3:
        summary = art.get("summary_text")
        label, p_pos, p_neu, p_neg, k_index = analyze_sentiment(summary)
        if label is None:
                skipped += 1
                continue
        
        new_art = {
                **art,
                "sentiment_label": label,
                "p_positive": round(p_pos, 6),
                "p_neutral": round(p_neu, 6),
                "p_negative": round(p_neg, 6),
                "k_index": round(k_index, 2),
            }
        result_with_sentiment.append(new_art)
    
    print("step4 결과")
    print(f" - 감정분석 성공: {len(result_with_sentiment)}")

    # 디버깅 JSON 저장
    with open("step4_with_sentiment.json", "w", encoding="utf-8") as f:
        json.dump(result_with_sentiment, f, ensure_ascii=False, indent=4)

    return result_with_sentiment