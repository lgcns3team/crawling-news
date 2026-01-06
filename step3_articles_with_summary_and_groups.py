# step3_articles_with_summary_and_groups.py
import os
import json
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------
# Backend 선택
#   - openai: 기존 STEP3 (한국어 입력 -> 한국어 요약)
#   - us4_finllama: 한국어 기사 -> OpenAI 번역 -> fin-llama 영어 요약
# -------------------------------------------------
STEP3_BACKEND = os.getenv("STEP3_BACKEND", "openai").strip().lower()

# -------------------------------------------------
# OpenAI 설정 (요약/번역 공통 사용)
# -------------------------------------------------
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("gpt_key")
OPENAI_STEP3_MODEL = os.getenv("OPENAI_STEP3_MODEL", "gpt-4o-mini")
OPENAI_TRANSLATE_MODEL = os.getenv("OPENAI_TRANSLATE_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    raise EnvironmentError("OpenAI API KEY가 필요합니다. OPENAI_API_KEY 또는 gpt_key를 설정하세요.")

client = OpenAI(api_key=OPENAI_API_KEY)

MAX_TRANSLATE_CHARS = int(os.getenv("MAX_TRANSLATE_CHARS", "5000"))

# -------------------------------------------------
# OpenAI 요약 (한국어)
# -------------------------------------------------
SYSTEM_PROMPT_KO = """
너의 역할은 한국어 뉴스 기사를 분석해서,
특정 회사에 대한 기사인지 여부를 판단하고, 관련 있을 경우에만 요약을 생성하는 것이다.

[관련성 판단 규칙]
- [회사]가 기사 내용의 '주된 주제'이면 "관련 있음"으로 본다.
- 회사가 그냥 예시, 비교 대상, 시장 참여자 중 하나로 잠깐 언급만 되는 수준이면 "관련 없음"으로 본다.
- 전체 맥락이 정치, 거시경제, 시장 전반 이야기이고 회사는 곁다리 수준이면 "관련 없음"으로 본다.

[출력 형식]
- 회사가 '주된 주제'인 기사인 경우:
    - 한 줄로 출력하되, 다음 형식을 지켜라:
      [RELATED] 실제 요약 내용...
- 회사가 주된 주제가 아닌 경우:
    - 정확히 아래 한 줄만 출력하라:
      [NOT_RELATED]

[요약 규칙]
- [RELATED]인 경우에만 요약을 쓴다.
- 한국어로만 작성한다.
- 1~3문장, 150자 이내로 핵심만 정리한다.
- 기업명, 핵심 사건, 수치/변동(있다면) 위주로 정리한다.
- "요약하겠습니다", "기사에 따르면" 같은 말은 쓰지 않는다.
- 바로 내용 문장으로 시작한다.
                """.strip()


def summarize_article_openai(company_name: str, full_text: str):
    user_content = f"""
[회사]
{company_name}

[본문]
{full_text}
""".strip()

    try:
        resp = client.chat.completions.create(
            model=OPENAI_STEP3_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_KO},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=256,
        )
        raw = (resp.choices[0].message.content or "").strip()

        if raw.startswith("[NOT_RELATED]"):
            return "", False, raw
        if raw.startswith("[RELATED]"):
            return raw[len("[RELATED]"):].strip(), True, raw

        if "[NOT_RELATED]" in raw:
            return "", False, raw
        if "[RELATED]" in raw:
            return raw.split("[RELATED]", 1)[1].strip(), True, raw

        return raw, True, raw

    except Exception as e:
        print(f"step3(OpenAI): 요약 오류: {e}")
        return "", False, ""


# -------------------------------------------------
# OpenAI 번역 (한국어 -> 영어)
# -------------------------------------------------
TRANSLATE_SYSTEM = """
You are a professional translator.
Translate the given Korean news article into natural, fluent English.
Do NOT summarize. Do NOT add explanations.
Return ONLY the translated English text.
""".strip()


def translate_ko_to_en_openai(korean_text: str) -> str:
    if not korean_text or not korean_text.strip():
        return ""

    text = korean_text.strip()
    if len(text) > MAX_TRANSLATE_CHARS:
        text = text[:MAX_TRANSLATE_CHARS]

    try:
        resp = client.chat.completions.create(
            model=OPENAI_TRANSLATE_MODEL,
            messages=[
                {"role": "system", "content": TRANSLATE_SYSTEM},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=1800,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[translate] OpenAI 번역 실패: {e}")
        return ""


# -------------------------------------------------
# us4/fin-llama3.1-8b (GGUF + CPU)
# -------------------------------------------------
US4_REPO_ID = os.getenv("US4_FINLLAMA_REPO", "us4/fin-llama3.1-8b")
US4_GGUF_FILENAME = os.getenv("US4_FINLLAMA_GGUF", "model-q4_k_m.gguf")
US4_N_CTX = int(os.getenv("US4_FINLLAMA_N_CTX", "2048"))
US4_MAX_TOKENS = int(os.getenv("US4_FINLLAMA_MAX_TOKENS", "220"))
US4_THREADS = int(os.getenv("US4_FINLLAMA_THREADS", "8"))

_US4_LLAMA = None


def _load_us4_llama():
    global _US4_LLAMA
    if _US4_LLAMA is not None:
        return _US4_LLAMA

    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    gguf_path = hf_hub_download(
        repo_id=US4_REPO_ID,
        filename=US4_GGUF_FILENAME,
        token=os.getenv("HF_TOKEN") or os.getenv("huggingface_api_token"),
    )

    _US4_LLAMA = Llama(
        model_path=gguf_path,
        n_ctx=US4_N_CTX,
        n_threads=US4_THREADS,
        verbose=False,
    )
    return _US4_LLAMA


SYSTEM_PROMPT_EN = """
You are given a COMPANY and a news ARTICLE in English.
Decide whether the COMPANY is meaningfully discussed in the article.

Consider it [RELATED] if ANY of the following is true:
- The article discusses the COMPANY’s business, performance, products, strategy, management, or major events.
- The COMPANY is one of the key companies mentioned with non-trivial context (not just a passing mention).
- The COMPANY appears as a notable contributor/driver in market moves (e.g., stock surge, index contribution, sector rally).

Consider it [NOT_RELATED] ONLY if:
- The COMPANY is mentioned only in a list or as a minor example with no meaningful context.

Output exactly ONE line:
- If related: [RELATED] <concise summary in English, 1-3 sentences, <= 400 characters>
- If not related: [NOT_RELATED]
""".strip()



def _first_line_only(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    return t.splitlines()[0].strip()


def _parse_related_output(text: str):
    t = _first_line_only(text)
    if t.startswith("[NOT_RELATED]"):
        return "", False
    if t.startswith("[RELATED]"):
        return t[len("[RELATED]"):].strip(), True
    if "[NOT_RELATED]" in t:
        return "", False
    if "[RELATED]" in t:
        return t.split("[RELATED]", 1)[1].strip(), True
    return "", False


def summarize_article_us4_finllama(company_name: str, full_text_ko: str):
    en_text = translate_ko_to_en_openai(full_text_ko)
    if not en_text:
        return "", False, "[TRANSLATE_FAILED]"

    llm = _load_us4_llama()

    prompt = f"""{SYSTEM_PROMPT_EN}

[COMPANY]
{company_name}

[ARTICLE]
{en_text}

[OUTPUT]
""".strip()

    try:
        out = llm(
            prompt,
            max_tokens=US4_MAX_TOKENS,
            temperature=0.0,
            stop=["\n"],  # 한 줄만 강제
        )
        raw = (out.get("choices", [{}])[0].get("text") or "").strip()
        summary, is_related = _parse_related_output(raw)
        return summary, is_related, raw
    except Exception as e:
        print(f"step3(us4_finllama): 오류: {e}")
        return "", False, ""


def summarize_article(company_name: str, full_text: str):
    if STEP3_BACKEND == "openai":
        return summarize_article_openai(company_name, full_text)
    if STEP3_BACKEND == "us4_finllama":
        return summarize_article_us4_finllama(company_name, full_text)
    raise ValueError(f"Unknown STEP3_BACKEND: {STEP3_BACKEND}")


def step3_articles_with_summary_and_groups(result_by_step2):
    result_with_summary = []
    not_related_articles = []

    for art in result_by_step2:
        article_id = art.get("id")
        url = art.get("url")
        full_text = art.get("full_text") or ""
        company_name = art.get("company_name") or ""

        summary, is_related, raw = summarize_article(company_name, full_text)

        if not is_related:
            print(f"step3: id({article_id}) 회사와 관련 없는 기사 스킵  {url}")
            not_related_articles.append({**art, "step3_raw": raw})
            continue

        result_with_summary.append({**art, "summary_text": summary, "step3_raw": raw})

    print("step3 완료: 요약 및 관련성 판단 완료")
    print(f" - 백엔드: {STEP3_BACKEND}")
    print(f" - 회사와 관련 있는 기사: {len(result_with_summary)}")
    print(f" - 회사와 관련 없는 기사: {len(not_related_articles)}")

    related_out = f"step3_related_{STEP3_BACKEND}.json"
    not_related_out = f"step3_not_related_{STEP3_BACKEND}.json"

    with open(related_out, "w", encoding="utf-8") as f:
        json.dump(result_with_summary, f, ensure_ascii=False, indent=4)

    with open(not_related_out, "w", encoding="utf-8") as f:
        json.dump(not_related_articles, f, ensure_ascii=False, indent=4)

    print(f" - 저장: {related_out}")
    print(f" - 저장: {not_related_out}")

    return result_with_summary