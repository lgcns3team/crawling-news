# step4_articles_with_sentiment.py
import json
import os
from dotenv import load_dotenv
from transformers import pipeline

load_dotenv()

HF_TOKEN = os.getenv("huggingface_api_token") or os.getenv("HF_TOKEN")

# STEP3에서 어떤 백엔드를 썼는지에 따라 STEP4 모델도 바꿈
STEP3_BACKEND = os.getenv("STEP3_BACKEND", "openai").strip().lower()

# 한국어 (기존 KR-FinBert-SC)
KO_MODEL_NAME = os.getenv("KO_SENTIMENT_MODEL", "snunlp/KR-FinBert-SC")

# 영어 (ProsusAI/finbert)
EN_MODEL_NAME = os.getenv("EN_SENTIMENT_MODEL", "ProsusAI/finbert")

# (선택) 출력 확률 안정화를 위해 최대 길이 제한
MAX_LEN = int(os.getenv("SENTIMENT_MAX_LEN", "512"))

_sentiment_pipe_ko = None
_sentiment_pipe_en = None


def _load_pipe_ko():
    global _sentiment_pipe_ko
    if _sentiment_pipe_ko is None:
        _sentiment_pipe_ko = pipeline(
            "text-classification",
            model=KO_MODEL_NAME,
            token=HF_TOKEN,
            top_k=None,          # 모든 라벨 확률 반환
            truncation=True,
            max_length=MAX_LEN,
        )
    return _sentiment_pipe_ko


def _load_pipe_en():
    global _sentiment_pipe_en
    if _sentiment_pipe_en is None:
        _sentiment_pipe_en = pipeline(
            "text-classification",
            model=EN_MODEL_NAME,
            token=HF_TOKEN,
            top_k=None,          # 모든 라벨 확률 반환
            truncation=True,
            max_length=MAX_LEN,
        )
    return _sentiment_pipe_en


def compute_k_index(p_pos: float, p_neu: float, p_neg: float):
    """
    0~100 점수 계산:
    base = 긍정 - 부정
    confidence = 1 - 중립
    S = base * confidence
    score = (S + 1) / 2 * 100
    """
    base = p_pos - p_neg
    confidence = 1.0 - p_neu
    s = base * confidence
    raw_score = (s + 1.0) / 2.0 * 100.0
    score = max(0.0, min(100.0, raw_score))
    return score


def _normalize_scores(output):
    """
    pipeline 출력 형태가 버전에 따라
    - [[{label,score}...]] or [{label,score}...] 로 올 수 있어서 정규화
    """
    out = output
    if isinstance(out, list) and len(out) > 0 and isinstance(out[0], list):
        out = out[0]
    return out


def _extract_probs(scores_dict):
    """
    모델마다 label 네이밍이 다를 수 있어 보수적으로 처리:
    - POSITIVE/NEGATIVE/NEUTRAL
    - positive/negative/neutral
    - LABEL_0/1/2
    """
    # 우선순위: 명시 라벨
    p_pos = scores_dict.get("POSITIVE", scores_dict.get("POS", scores_dict.get("LABEL_POSITIVE", 0.0)))
    p_neu = scores_dict.get("NEUTRAL", scores_dict.get("NEU", scores_dict.get("LABEL_NEUTRAL", 0.0)))
    p_neg = scores_dict.get("NEGATIVE", scores_dict.get("NEG", scores_dict.get("LABEL_NEGATIVE", 0.0)))

    # ProsusAI/finbert는 보통 label이 "positive/negative/neutral" 형태로 나오는 경우가 많음
    if p_pos == 0.0 and "POSITIVE" not in scores_dict:
        p_pos = scores_dict.get("POSITIVE", scores_dict.get("POSITIVE".lower(), scores_dict.get("positive", p_pos)))
    if p_neu == 0.0 and "NEUTRAL" not in scores_dict:
        p_neu = scores_dict.get("NEUTRAL", scores_dict.get("NEUTRAL".lower(), scores_dict.get("neutral", p_neu)))
    if p_neg == 0.0 and "NEGATIVE" not in scores_dict:
        p_neg = scores_dict.get("NEGATIVE", scores_dict.get("NEGATIVE".lower(), scores_dict.get("negative", p_neg)))

    # 마지막 fallback: LABEL_0/1/2 (모델마다 매핑이 다를 수 있어 config 확인이 이상적이지만)
    # 일반적으로 finbert류는 {negative, neutral, positive} 순서가 흔해서:
    # LABEL_0=negative, LABEL_1=neutral, LABEL_2=positive 가 자주 등장
    if (p_pos, p_neu, p_neg) == (0.0, 0.0, 0.0):
        p_neg = scores_dict.get("LABEL_0", 0.0)
        p_neu = scores_dict.get("LABEL_1", 0.0)
        p_pos = scores_dict.get("LABEL_2", 0.0)

    # 혹시 일부만 0이면 보정은 하지 않고 그대로 둠 (모델 출력에 따름)
    return float(p_pos), float(p_neu), float(p_neg)


def analyze_sentiment_ko(text: str):
    if not text or not text.strip():
        return None, 0.0, 1.0, 0.0, 50.0, []

    pipe = _load_pipe_ko()
    out = _normalize_scores(pipe(text.strip()))

    scores = {}
    for r in out:
        lab = str(r["label"]).strip()
        # 대소문자 정규화
        scores[lab.upper()] = float(r["score"])
        scores[lab.lower()] = float(r["score"])

    p_pos, p_neu, p_neg = _extract_probs(scores)

    best_label = max(
        [("POSITIVE", p_pos), ("NEUTRAL", p_neu), ("NEGATIVE", p_neg)],
        key=lambda x: x[1],
    )[0]

    k_index = compute_k_index(p_pos, p_neu, p_neg)
    return best_label, p_pos, p_neu, p_neg, k_index, out


def analyze_sentiment_en(text: str):
    if not text or not text.strip():
        return None, 0.0, 1.0, 0.0, 50.0, []

    pipe = _load_pipe_en()
    out = _normalize_scores(pipe(text.strip()))

    scores = {}
    for r in out:
        lab = str(r["label"]).strip()
        scores[lab.upper()] = float(r["score"])
        scores[lab.lower()] = float(r["score"])
        # finbert는 보통 "positive"/"neutral"/"negative"
        scores[lab] = float(r["score"])

    p_pos, p_neu, p_neg = _extract_probs(scores)

    best_label = max(
        [("POSITIVE", p_pos), ("NEUTRAL", p_neu), ("NEGATIVE", p_neg)],
        key=lambda x: x[1],
    )[0]

    k_index = compute_k_index(p_pos, p_neu, p_neg)
    return best_label, p_pos, p_neu, p_neg, k_index, out


def step4_articles_with_sentiment(result_by_step3):
    """
    STEP3_BACKEND에 따라:
    - openai: 한국어 요약 -> KO 모델 감성
    - us4_finllama: 영어 요약 -> EN 모델 감성
    """
    result_with_sentiment = []
    skipped = 0

    for art in result_by_step3:
        summary = art.get("summary_text") or ""
        if not summary.strip():
            skipped += 1
            continue

        if STEP3_BACKEND == "us4_finllama":
            label, p_pos, p_neu, p_neg, k_index, raw_scores = analyze_sentiment_en(summary)
            used_model = EN_MODEL_NAME
            used_lang = "en"
        else:
            label, p_pos, p_neu, p_neg, k_index, raw_scores = analyze_sentiment_ko(summary)
            used_model = KO_MODEL_NAME
            used_lang = "ko"

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
            "sentiment_model": used_model,
            "sentiment_lang": used_lang,
            # 비교/디버깅용: 원시 분류 결과도 남김(원하면 제거 가능)
            "sentiment_raw_scores": raw_scores,
        }
        result_with_sentiment.append(new_art)

    print("step4 결과")
    print(f" - 백엔드(STEP3): {STEP3_BACKEND}")
    print(f" - 사용 모델: {EN_MODEL_NAME if STEP3_BACKEND=='us4_finllama' else KO_MODEL_NAME}")
    print(f" - 감정분석 성공: {len(result_with_sentiment)}")
    print(f" - 스킵: {skipped}")

    out_file = f"step4_with_sentiment_{STEP3_BACKEND}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result_with_sentiment, f, ensure_ascii=False, indent=4)
    print(f" - 저장: {out_file}")

    return result_with_sentiment