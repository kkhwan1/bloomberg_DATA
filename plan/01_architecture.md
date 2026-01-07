# 01. 시스템 아키텍처

## 프로젝트 구조

```
bloomberg_data/
├── plan/                          # 프로젝트 계획 문서
│   ├── 00_overview.md
│   ├── 01_architecture.md
│   ├── 02_bright_data_api.md
│   ├── 03_bloomberg_parser.md
│   ├── 04_cost_management.md
│   ├── 05_implementation.md
│   └── 06_testing.md
│
├── src/
│   ├── __init__.py
│   ├── config.py                  # 설정 (API 키, 예산, 심볼 목록)
│   │
│   ├── clients/                   # API 클라이언트
│   │   ├── __init__.py
│   │   ├── base.py                # 추상 베이스 클래스
│   │   ├── bright_data.py         # Bright Data Web Unlocker
│   │   ├── yfinance_client.py     # yfinance 폴링
│   │   ├── finnhub_ws.py          # Finnhub WebSocket
│   │   └── alpha_vantage.py       # Alpha Vantage (백업)
│   │
│   ├── parsers/                   # HTML/JSON 파서
│   │   ├── __init__.py
│   │   └── bloomberg_parser.py    # Bloomberg HTML 파싱
│   │
│   ├── orchestrator/              # 오케스트레이션
│   │   ├── __init__.py
│   │   ├── hybrid_source.py       # 하이브리드 데이터 소스
│   │   ├── cost_tracker.py        # 비용 추적 (싱글톤)
│   │   ├── cache_manager.py       # SQLite 캐시 (15분 TTL)
│   │   ├── scheduler.py           # APScheduler
│   │   └── circuit_breaker.py     # 장애 복구
│   │
│   ├── normalizer/                # 데이터 정규화
│   │   ├── __init__.py
│   │   ├── schemas.py             # Pydantic 모델
│   │   └── transformer.py         # 소스별 데이터 변환
│   │
│   ├── storage/                   # 저장소
│   │   ├── __init__.py
│   │   ├── csv_writer.py
│   │   └── json_writer.py
│   │
│   └── main.py                    # 엔트리포인트
│
├── data/                          # 출력 데이터
│   ├── stocks/
│   ├── forex/
│   ├── commodities/
│   └── bonds/
│
├── cache/                         # SQLite 캐시
│   └── bloomberg_cache.db
│
├── logs/                          # 로그 및 비용 추적
│   └── cost_tracking.json
│
├── tests/
│   ├── __init__.py
│   ├── test_bright_data.py
│   ├── test_parser.py
│   └── test_cost_tracker.py
│
├── requirements.txt
├── .env                           # API 키 (gitignore)
├── .env.example
└── .gitignore
```

## 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py (Entry Point)                     │
│                    Scheduler: 15분 간격 실행                       │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HybridDataSource                              │
│            (orchestrator/hybrid_source.py)                       │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │ CacheManager │   │ CostTracker  │   │   CircuitBreaker     │ │
│  │  (15min TTL) │   │  (싱글톤)     │   │   (장애 복구)         │ │
│  └──────┬───────┘   └──────┬───────┘   └──────────┬───────────┘ │
└─────────┼──────────────────┼─────────────────────┼──────────────┘
          │                  │                     │
          ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      데이터 소스 우선순위                          │
│                                                                  │
│  1. Cache Hit? ─────Yes────▶ Return Cached Data                 │
│       │                                                          │
│       No                                                         │
│       ▼                                                          │
│  2. yfinance/Finnhub (무료)                                      │
│       │                                                          │
│       실패 또는 Bloomberg 전용                                     │
│       ▼                                                          │
│  3. Bright Data API (유료) ────▶ CostTracker.record()            │
│       │                                                          │
│       ▼                                                          │
│  4. Parse HTML ────▶ BloombergParser                             │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Normalizer                                  │
│            (normalizer/transformer.py)                           │
│                                                                  │
│  - UTC 타임스탬프 변환                                             │
│  - Pydantic 스키마 검증                                           │
│  - 소스별 필드 매핑                                                │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Storage                                     │
│            (storage/csv_writer.py)                               │
│                                                                  │
│  data/                                                           │
│  ├── stocks/AAPL/2025-01-07.csv                                 │
│  ├── forex/EURUSD/2025-01-07.csv                                │
│  ├── commodities/GOLD/2025-01-07.csv                            │
│  └── bonds/US10Y/2025-01-07.csv                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 컴포넌트 설명

### 1. Clients (API 클라이언트)

| 파일 | 역할 | 비용 |
|-----|-----|-----|
| `bright_data.py` | Bloomberg 크롤링 (Cloudflare 우회) | $0.0015/req |
| `yfinance_client.py` | 주식, FX, 원자재 데이터 | 무료 |
| `finnhub_ws.py` | 실시간 WebSocket 스트림 | 무료 |
| `alpha_vantage.py` | 백업 데이터 소스 | 무료 (25 req/day) |

### 2. Orchestrator (오케스트레이션)

| 파일 | 역할 |
|-----|-----|
| `hybrid_source.py` | 데이터 소스 우선순위 관리 |
| `cost_tracker.py` | Bright Data 비용 추적/알림 |
| `cache_manager.py` | SQLite 캐시 (15분 TTL) |
| `scheduler.py` | APScheduler 기반 스케줄링 |
| `circuit_breaker.py` | 장애 감지 및 복구 |

### 3. Parsers (파서)

| 파일 | 역할 |
|-----|-----|
| `bloomberg_parser.py` | Bloomberg HTML/JSON 파싱 (다중 전략) |

### 4. Normalizer (정규화)

| 파일 | 역할 |
|-----|-----|
| `schemas.py` | Pydantic 모델 정의 |
| `transformer.py` | 소스별 데이터 변환 |

### 5. Storage (저장소)

| 파일 | 역할 |
|-----|-----|
| `csv_writer.py` | CSV 파일 저장 (일별 파티션) |
| `json_writer.py` | JSON 스트리밍 저장 |

## 의존성

```
# requirements.txt

# Core
python-dotenv>=1.0.0
pydantic>=2.5.0
pandas>=2.1.0

# API Clients
yfinance>=0.2.36
websocket-client>=1.7.0
aiohttp>=3.9.0

# HTML Parsing
beautifulsoup4>=4.12.0
lxml>=5.1.0

# Rate Limiting & Scheduling
aiolimiter>=1.2.0
apscheduler>=3.10.0

# Storage
orjson>=3.9.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.23.0
```
