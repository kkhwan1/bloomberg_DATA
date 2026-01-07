# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

59개국 글로벌 주가지수를 Bloomberg에서 수집하는 크롤러

## 핵심 실행 명령어

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
    ├── IN_BSE30/                # 인도 SENSEX
    │   ├── 20260107.json        # 일별 JSON 결과
    │   └── 20260107.csv         # 일별 CSV 결과
    ├── ZA_ALSH/                  # 남아프리카 JALSH
    │   └── ...
    └── crawl_summary_*.json     # 크롤링 요약
```

## 결과 데이터 예시

`data/indices/IN_BSE30/20260107.json`:
```json
{
  "crawl_info": {
    "code": "IN@BSE30",
    "country": "India",
    "bloomberg_symbol": "SENSEX:IND",
    "cost_usd": 0.0015
  },
  "quote_data": {
    "name": "S&P BSEセンセックス",
    "price": 85063.34,
    "change": -376.28,
    "change_percent": -0.44,
    "day_high": 85397.78,
    "day_low": 84900.1
  }
}
```

## 주요 파일

| 파일 | 설명 |
|------|------|
| `scripts/crawl_indices.py` | 메인 크롤링 스크립트 |
| `data/index_urls.json` | 59개 인덱스 URL 매핑 |
| `src/parsers/bloomberg_parser.py` | Bloomberg HTML 파서 |
| `src/clients/bright_data.py` | Bright Data API 클라이언트 |

## 환경 설정

```bash
# .env 파일에 토큰 설정
BRIGHT_DATA_TOKEN=your_token_here
```

## 비용

- 요청당: $0.0015
- 전체 59개: $0.0885
- 예산: $5.50

## 테스트

```bash
python -m pytest tests/ -v
```
