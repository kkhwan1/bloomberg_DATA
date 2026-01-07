# Bloomberg Global Index Crawler

59개국 글로벌 주가지수를 Bloomberg에서 수집하는 크롤러

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env 파일에서 BRIGHT_DATA_TOKEN 설정

# 3. 크롤링 실행
python scripts/crawl_indices.py
```

## 실행 옵션

```bash
# 전체 59개 인덱스 크롤링
python scripts/crawl_indices.py

# 테스트 (처음 2개만)
python scripts/crawl_indices.py --test

# 특정 인덱스 크롤링 (ID: 1-59)
python scripts/crawl_indices.py --index 25

# 범위 지정 크롤링
python scripts/crawl_indices.py --range 1 10

# 딜레이 조정 (기본 1초)
python scripts/crawl_indices.py --delay 2.0
```

## 결과 저장 위치

```
data/
├── index_urls.json              # 59개 인덱스 URL 매핑
└── indices/
    ├── AE_DFM/                   # UAE
    ├── AR_MERV/                  # Argentina
    ├── IN_BSE30/                 # India (SENSEX)
    │   ├── 20260107.json         # 일별 JSON
    │   └── 20260107.csv          # 일별 CSV
    ├── ZA_ALSH/                  # South Africa
    └── crawl_summary_*.json      # 크롤링 요약
```

## 결과 데이터 형식

### JSON (`data/indices/{CODE}/YYYYMMDD.json`)

```json
{
  "crawl_info": {
    "id": 25,
    "code": "IN@BSE30",
    "country": "India",
    "bloomberg_symbol": "SENSEX:IND",
    "url": "https://www.bloomberg.co.jp/quote/SENSEX:IND",
    "crawled_at": "2026-01-07T09:54:41",
    "cost_usd": 0.0015
  },
  "quote_data": {
    "ticker": "SENSEX:IND",
    "name": "S&P BSEセンセックス",
    "price": 85063.34,
    "change": -376.28,
    "change_percent": -0.44,
    "day_high": 85397.78,
    "day_low": 84900.1,
    "year_high": 86159.02,
    "year_low": 71425.01
  }
}
```

### CSV (`data/indices/{CODE}/YYYYMMDD.csv`)

```csv
timestamp,code,country,bloomberg_symbol,name,price,change,change_percent,day_high,day_low,...
2026-01-07T09:54:41,IN@BSE30,India,SENSEX:IND,S&P BSEセンセックス,85063.34,-376.28,-0.44,...
```

## 지원 인덱스 (59개국)

| 지역 | 국가 |
|------|------|
| 아시아 | 인도, 인도네시아, 말레이시아, 싱가포르, 태국, 베트남, 파키스탄, 필리핀, 스리랑카 |
| 중동 | UAE, 사우디, 카타르, 쿠웨이트, 바레인, 오만, 요르단, 이스라엘 |
| 유럽 | 오스트리아, 벨기에, 덴마크, 핀란드, 그리스, 헝가리, 아일랜드, 이탈리아, 네덜란드, 노르웨이, 폴란드, 포르투갈, 스페인, 스웨덴, 스위스, 터키 등 |
| 아프리카 | 남아프리카, 이집트, 모로코, 나이지리아 |
| 아메리카 | 아르헨티나, 브라질, 캐나다, 칠레, 콜롬비아, 멕시코, 베네수엘라 |
| 오세아니아 | 호주, 뉴질랜드 |

## 프로젝트 구조

```
bloomberg_data/
├── scripts/
│   └── crawl_indices.py      # 메인 크롤링 스크립트
├── data/
│   ├── index_urls.json       # 59개 인덱스 URL 매핑
│   └── indices/              # 크롤링 결과
├── src/
│   ├── parsers/
│   │   └── bloomberg_parser.py
│   └── clients/
│       └── bright_data.py
└── tests/
```

## 비용

| 항목 | 비용 |
|------|------|
| 요청당 | $0.0015 |
| 전체 59개 | $0.0885 |
| 예산 | $5.50 |

## 환경변수

| 변수 | 설명 |
|------|------|
| `BRIGHT_DATA_TOKEN` | Bright Data API 토큰 (필수) |
| `BRIGHT_DATA_ZONE` | Zone 이름 (기본: bloomberg) |

## 테스트

```bash
python -m pytest tests/ -v
```
