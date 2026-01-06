# compare_step4_outputs.py
import json

OPENAI_FILE = "step4_with_sentiment_openai.json"
US4_FILE = "step4_with_sentiment_us4_finllama.json"
OUT_FILE = "step4_compare.json"

def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    a = _load(OPENAI_FILE)
    b = _load(US4_FILE)

    # url 기준으로 매칭 (id는 실행마다 달라질 수 있음)
    a_by_url = {x.get("url"): x for x in a if x.get("url")}
    b_by_url = {x.get("url"): x for x in b if x.get("url")}

    common_urls = sorted(set(a_by_url.keys()) & set(b_by_url.keys()))
    rows = []

    for url in common_urls:
        aa = a_by_url[url]
        bb = b_by_url[url]

        rows.append({
            "url": url,
            "company_name": aa.get("company_name") or bb.get("company_name"),
            "title": aa.get("title") or bb.get("title"),

            "openai_summary": aa.get("summary_text"),
            "openai_sentiment_label": aa.get("sentiment_label"),
            "openai_p_positive": aa.get("p_positive"),
            "openai_p_neutral": aa.get("p_neutral"),
            "openai_p_negative": aa.get("p_negative"),
            "openai_k_index": aa.get("k_index"),
            "openai_model": aa.get("sentiment_model"),

            "us4_summary": bb.get("summary_text"),
            "us4_sentiment_label": bb.get("sentiment_label"),
            "us4_p_positive": bb.get("p_positive"),
            "us4_p_neutral": bb.get("p_neutral"),
            "us4_p_negative": bb.get("p_negative"),
            "us4_k_index": bb.get("k_index"),
            "us4_model": bb.get("sentiment_model"),
        })

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "common_count": len(common_urls),
            "openai_file": OPENAI_FILE,
            "us4_file": US4_FILE,
            "rows": rows,
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] 공통 기사 수: {len(common_urls)}")
    print(f"[OK] 비교 저장: {OUT_FILE}")

if __name__ == "__main__":
    main()