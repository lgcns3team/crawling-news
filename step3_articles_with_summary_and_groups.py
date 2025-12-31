import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
MODEL_NAME = "gpt-4o-mini"  

client = OpenAI(
    api_key=os.environ.get("gpt_key")  
)

SYSTEM_PROMPT = """
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
                """

def summarize_article(company_name, full_text):

    user_content = f"""
                        [회사]
                        {company_name}

                        [본문]
                        {full_text}
                    """

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=256,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith("[NOT_RELATED]"):
            return "", False
        if content.startswith("[RELATED]"):
            summary = content[len("[RELATED]"):].strip()
            return summary, True
        
        return content, True
    
    except Exception as e:
        print(f"step3: GPT 요약 중 오류 발생: {e}")
        return "", False

def step3_articles_with_summary_and_groups(result_by_step2):
    
    result_with_summary = []
    not_related_articles = []

    for art in result_by_step2:
        full_text = art.get("full_text")
        company_name  = art.get("company_name")
        summary, is_related = summarize_article(company_name, full_text)
        
        if not is_related:
            print(f"step3: id({art.get('id')}) 회사와 관련 없는 기사 스킵  {art.get('url')}")
            not_related_articles.append(art)
            continue

        new_art = {
            **art,
            "summary_text": summary,
        }
        
        result_with_summary.append(new_art)


    print("step3 완료: 요약 및 관련성 판단 완료")
    print(f" - 회사와 관련 있는 기사: {len(result_with_summary)}")
    print(f" - 회사와 관련 없는 기사: {len(not_related_articles)}")

    # 관련 있는 기사 + 요약본
    with open("step3_related.json", "w", encoding="utf-8") as f:
        json.dump(result_with_summary, f, ensure_ascii=False, indent=4)

    # 관련 없는 기사 리스트
    with open("step3_not_related.json", "w", encoding="utf-8") as f:
        json.dump(not_related_articles, f, ensure_ascii=False, indent=4)

    return result_with_summary