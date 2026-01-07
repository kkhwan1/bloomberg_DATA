# Bloomberg Data Crawler

알고리즘 트레이딩을 위한 비용 최적화 금융 데이터 수집 시스템

## 프로젝트 개요

Bloomberg, YFinance 등 다양한 소스에서 금융 데이터를 수집하는 하이브리드 크롤러입니다.
비용 효율적인 데이터 수집을 위해 **캐시 → 무료 API → 유료 API** 순서로 데이터를 조회합니다.

**예산**: $5.50 (요청당 $0.0015 = 약 3,667회 유료 요청 가능)

## 폴더 구조

```
bloomberg_data/
│
├── src/                          # 소스 코드
│   ├── main.py                   # CLI 진입점
│   ├── config.py                 # 환경설정
│   │
│   ├── orchestrator/             # 핵심 조율 모듈
│   │   ├── scheduler.py          # 스케줄러 (APScheduler, 15분 간격)
│   │   ├── hybrid_source.py      # 하이브리드 데이터 소스
│   │   ├── cost_tracker.py       # 비용 추적 (싱글톤)
│   │   ├── cache_manager.py      # SQLite 캐시 (15분 TTL)
│   │   └── circuit_breaker.py    # 서킷 브레이커 (3상태)
│   │
│   ├── clients/                  # API 클라이언트
│   │   ├── yfinance_client.py    # YFinance (무료)
│   │   ├── finnhub_ws.py         # Finnhub WebSocket (무료)
│   │   └── bright_data.py        # Bright Data (유료)
│   │
│   ├── parsers/                  # 데이터 파서
│   │   └── bloomberg_parser.py   # Bloomberg HTML 파서
│   │
│   ├── normalizer/               # 데이터 정규화
│   │   ├── schemas.py            # Pydantic 스키마
│   │   └── transformer.py        # 데이터 변환기
│   │
│   ├── storage/                  # 저장소
│   │   ├── csv_writer.py         # CSV 저장
│   │   └── json_writer.py        # JSON 저장
│   │
│   └── utils/                    # 유틸리티
│       ├── exceptions.py         # 커스텀 예외
│       └── logger.py             # 로깅 설정
│
├── scripts/                      # 유틸리티 스크립트
│   ├── crawl_indices.py          # 글로벌 인덱스 크롤러
│   ├── compare_sources.py        # 데이터 소스 비교
│   ├── test_bright_data_api.py   # Bright Data API 테스트
│   └── ...
│
├── data/                         # 수집된 데이터
│   ├── index_urls.json           # 59개 글로벌 인덱스 URL 매핑
│   ├── indices/{CODE}/           # 인덱스별 데이터 (예: IN_BSE30/)
│   │   └── YYYYMMDD.json
│   ├── stocks/{SYMBOL}/          # 주식 데이터
│   ├── forex/{PAIR}/             # 외환 데이터
│   └── commodities/{SYMBOL}/     # 원자재 데이터
│
├── tests/                        # 테스트 코드
│   ├── conftest.py               # pytest 픽스처
│   └── test_*.py                 # 단위 테스트
│
├── docs/                         # 상세 문서
│   ├── bloomberg_parser.md
│   ├── bright_data_*.md
│   ├── cache_manager.md
│   └── ...
│
├── examples/                     # 사용 예제
├── plan/                         # 개발 계획 문서
├── logs/                         # 로그 파일
│
├── .env.example                  # 환경변수 템플릿
├── requirements.txt              # Python 의존성
├── CLAUDE.md                     # Claude Code 가이드
└── CLI_USAGE.md                  # CLI 상세 사용법
```

## 설치

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env 파일에서 BRIGHT_DATA_TOKEN 설정
```

## 주요 기능

### 1. 개별 종목 데이터 수집

```bash
# 단일 조회
python -m src.main AAPL MSFT GOOGL --once

# 15분 간격 스케줄링
python -m src.main AAPL MSFT --interval 15

# 예산 상태 확인
python -m src.main --budget
```

### 2. 글로벌 인덱스 크롤링 (59개국)

```bash
# 전체 59개 인덱스 크롤링
python scripts/crawl_indices.py

# 테스트 (처음 2개만)
python scripts/crawl_indices.py --test

# 특정 인덱스 크롤링 (ID 지정)
python scripts/crawl_indices.py --index 25

# 범위 지정
python scripts/crawl_indices.py --range 1 10
```

### 3. 테스트 실행

```bash
# 전체 테스트
python -m pytest tests/ -v

# 특정 테스트 파일
python -m pytest tests/test_bloomberg_parser.py -v

# 커버리지 포함
python -m pytest tests/ --cov=src --cov-report=html
```

## 데이터 구조

### 글로벌 인덱스 (59개)

`data/index_urls.json`에 매핑 정보 저장:
- **코드 형식**: `{국가코드}@{인덱스}` (예: `IN@BSE30`, `ZA@ALSH`)
- **Bloomberg 심볼**: `IN@BSE30` → `SENSEX:IND`

### 인덱스 데이터 예시

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
    "ticker": "SENSEX:IND",
    "name": "S&P BSE센섹스",
    "price": 85063.34,
    "change": -376.28,
    "change_percent": -0.44,
    "day_high": 85397.78,
    "day_low": 84900.1
  }
}
```

## 핵심 설계

### 데이터 소스 우선순위
1. **캐시** (SQLite, 15분 TTL) - 무료
2. **YFinance** - 무료
3. **Finnhub** - 무료 (WebSocket)
4. **Bright Data** - 유료 ($0.0015/요청)

### 비용 관리
- `logs/cost_tracking.json`에 사용량 기록
- 80% 사용 시 경고
- 100% 도달 시 유료 API 차단

### 서킷 브레이커
- **CLOSED**: 정상 작동
- **OPEN**: 장애 감지, 요청 차단
- **HALF_OPEN**: 복구 시도

## 환경변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `BRIGHT_DATA_TOKEN` | Bright Data API 토큰 | (필수) |
| `TOTAL_BUDGET` | 총 예산 (USD) | 5.50 |
| `COST_PER_REQUEST` | 요청당 비용 | 0.0015 |
| `CACHE_TTL_SECONDS` | 캐시 유효시간 | 900 |
| `ALERT_THRESHOLD` | 경고 임계값 | 0.80 |

## 지원 인덱스 (59개국)

| 지역 | 국가 |
|------|------|
| 아시아 | 인도, 인도네시아, 말레이시아, 싱가포르, 태국, 베트남, 파키스탄, 필리핀, 스리랑카 |
| 중동 | UAE, 사우디아라비아, 카타르, 쿠웨이트, 바레인, 오만, 요르단, 이스라엘 |
| 유럽 | 오스트리아, 벨기에, 불가리아, 덴마크, 에스토니아, 핀란드, 그리스, 헝가리, 아일랜드, 이탈리아, 라트비아, 리투아니아, 몰타, 네덜란드, 노르웨이, 폴란드, 포르투갈, 슬로베니아, 스페인, 스웨덴, 스위스, 터키 |
| 아프리카 | 남아프리카, 이집트, 모로코, 나이지리아 |
| 아메리카 | 아르헨티나, 브라질, 캐나다, 칠레, 콜롬비아, 멕시코, 파나마, 베네수엘라 |
| 오세아니아 | 호주, 뉴질랜드, 아이슬란드 |

## 문서

- `CLAUDE.md` - Claude Code용 프로젝트 가이드
- `CLI_USAGE.md` - CLI 상세 사용법
- `docs/` - 각 모듈별 상세 문서
- `plan/` - 개발 계획 및 아키텍처 문서

## 라이선스

Private - 내부 사용 전용
