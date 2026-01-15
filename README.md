# crawling-news
<img width="2303" height="1038" alt="image" src="https://github.com/user-attachments/assets/35418ddb-1c69-453b-8a13-ad34ac7441e4" />

>국내 주식 관련 뉴스를 수집하여 데이터베이스에 저장하는 크롤링 레포지토리입니다.  
>외부 뉴스 API 및 웹 크롤링을 통해 기사를 수집하고,  
>후속 감정 분석·백엔드 서비스에서 활용할 수 있도록 정형화된 형태로 저장합니다.


## :star: Repository Purpose
이 레포지토리는 다음 목적을 가집니다.
- 국내 주식/금융 **뉴스 데이터 수집**
- 뉴스 API 및 크롤링 로직 관리
- 기사 메타데이터 및 본문 **DB 저장**
- 감정 분석 파이프라인의 **입력 데이터 소스 역할**

---
## ⚙️Prerequisites

### Environment
- python 3.10

### Project Setup
```
pip install python-dotenv
pip install requests
pip install pymysql
pip install beautifulsoup4

pip install newspaper3k
pip install "lxml[html_clean]"
pip install openai
pip install transformers
pip install torch
```
### Excute
```
python run_pipeline.py
```
- 로컬 서버에서는 crontab으로, 배포환경에서는 cronjob으로 5분마다 실행
---
## 🤖 Sentiment Analysis Model

본 레포지토리는 뉴스 요약 텍스트에 대해 **한국어 금융 도메인에 특화된 감정 분석 모델**을 사용하여
긍정·중립·부정 확률과 종합 감정 지표를 산출합니다.

### Model Information

- **Model Name**: `DataWizardd/finbert-sentiment-ko`
- **Framework**: Hugging Face Transformers
- **Task**: Text Classification (Sentiment Analysis)
- **Language / Domain**: Korean / Finance
- **Inference Method**: `pipeline("text-classification")`

해당 모델은 금융 뉴스 및 투자 관련 문맥에서의 감정 표현을 보다 정확하게 반영하도록 학습된 모델로,
일반 감정 분석 모델 대비 **투자 심리 분석에 적합**합니다.
- Reference: https://huggingface.co/DataWizardd/finbert-sentiment-ko
---
### :key: Key Components

`run_pipeline.py`
- 전체 뉴스 수집·처리 파이프라인 실행 스크립트
- Step1 ~ Step4 모듈을 순차적으로 호출하여 데이터 흐름을 제어

`step1_naver_articles.py`
- 네이버 뉴스 API를 통한 기사 메타데이터 수집
- 종목/키워드 기반 뉴스 목록 조회 및 원본 데이터 저장

`step2_articles_with_content.py`
- 수집된 뉴스 URL 기반 기사 본문 크롤링
- 불필요한 HTML/광고 영역 제거 및 본문 정제

`step3_articles_with_summary_and_groups.py`
- 기사 본문 요약 생성 (LLM 또는 규칙 기반)
- 유사 뉴스 그룹화 및 중복 기사 정리

`step4_articles_with_sentiment.py`
- 뉴스 요약 텍스트 기반 감정 분석 수행
- 감정 점수 및 라벨을 DB에 저장하여 후속 분석에 활용


### 📊 Collected News Data Fields

본 레포지토리는 NAVER Open API를 통해 다음과 같은 주가 정보를 수집합니다.

| Field Name        | Source (NAVER Response) | Description |
|------------------|--------------------------|-------------|
| `title`          | `item.title`             | 뉴스 기사 제목 (검색어 일치 부분은 `<b>` 태그로 감싸져 있을 수 있어 제거 후 저장) :contentReference[oaicite:2]{index=2} |
| `originallink`   | `item.originallink`      | 뉴스 기사 **원문 URL** :contentReference[oaicite:3]{index=3} |
| `link`           | `item.link`              | 네이버 뉴스 URL (네이버에 없으면 원문 URL이 올 수 있음) :contentReference[oaicite:4]{index=4} |
| `description`    | `item.description`       | 기사 요약 패시지(검색어 일치 부분 `<b>` 포함 가능) :contentReference[oaicite:5]{index=5} |
| `pubDate`        | `item.pubDate`           | 네이버에 제공된 기사 시간 (RFC 822 형태로 옴) :contentReference[oaicite:6]{index=6} |

- Reference: https://developers.naver.com/docs/serviceapi/search/news/news.md

### 🔄 Data Flow
1. NAVER OPEN API를 통한 데이터 수집
2. 수집된 링크를 통해 Newspaper3k 라이브러리를 통한 본문 수집
3. 본문에 대해 OPEN AI(GPT)를 통해 본문 요약 및 데이터 검증
4. 요약된 본문에 대해 KR-Finbert 모델을 통해 감정 라벨 추출
5. 추출된 라벨로 감정점수 산출 및 데이터를 분석/백엔드 서비스에서 활용

### :file_folder: Data Structure

```
📦crawling-news
 ┣ 📜.gitignore
 ┣ 📜aggregate_stock_score.py
 ┣ 📜config_companies.py
 ┣ 📜db_config.py
 ┣ 📜db_insert.py
 ┣ 📜Dockerfile
 ┣ 📜README.md
 ┣ 📜requirements.txt
 ┣ 📜run_pipeline.py
 ┣ 📜step1_naver_articles.py
 ┣ 📜step2_articles_with_content.py
 ┣ 📜step3_articles_with_summary_and_groups.py
 ┗ 📜step4_articles_with_sentiment.py
```


