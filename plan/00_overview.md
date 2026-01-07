# Bloomberg Data Crawler - 프로젝트 개요

## 프로젝트 목표

알고리즘 트레이딩을 위한 Bloomberg Markets 데이터 크롤링 시스템 구축

## 핵심 전략

```
┌─────────────────────────────────────────────────────┐
│                 Trading Algorithm                    │
└──────────────────────┬──────────────────────────────┘
                       │ Read
┌──────────────────────▼──────────────────────────────┐
│              CSV/JSON Storage                        │
└──────────────────────┬──────────────────────────────┘
                       │ Write
┌──────────────────────▼──────────────────────────────┐
│              Hybrid Orchestrator                     │
│  Cost Tracker | Cache (15min TTL) | Failover         │
└───────┬───────────┬───────────┬───────────┬─────────┘
        │           │           │           │
   ┌────▼────┐ ┌────▼────┐ ┌────▼────┐ ┌────▼─────────┐
   │yfinance │ │Finnhub  │ │Alpha    │ │ Bright Data  │
   │FREE     │ │FREE     │ │Vantage  │ │ Bloomberg    │
   │(Primary)│ │WebSocket│ │FREE     │ │ (Paid Backup)│
   └─────────┘ └─────────┘ └─────────┘ └──────────────┘
```

## 데이터 소스 우선순위

1. **캐시** (무료) - 15분 TTL SQLite 캐시
2. **yfinance** (무료) - 주식, FX, 일부 원자재
3. **Finnhub** (무료) - 실시간 WebSocket
4. **Bright Data** (유료) - Bloomberg 전용 데이터

## Bright Data 계정 정보

| 항목 | 값 |
|-----|-----|
| Zone | bloomberg |
| 비용 | $1.50/CPM (1,000 요청당) |
| 잔액 | $5.50 |
| 가용 요청 | ~3,667회 |

## 데이터 유형

| 자산 | Primary (무료) | Backup (유료) | 주기 |
|-----|---------------|--------------|-----|
| Stocks | yfinance + Finnhub | Bright Data | 실시간/5분 |
| Forex | yfinance + Finnhub | Bright Data | 실시간/5분 |
| Commodities | yfinance | Bright Data | 15분 |
| Bonds | yfinance | Bright Data | 15분 |

## 문서 구조

```
plan/
├── 00_overview.md          # 이 파일 - 프로젝트 개요
├── 01_architecture.md      # 시스템 아키텍처
├── 02_bright_data_api.md   # Bright Data API 사용법
├── 03_bloomberg_parser.md  # Bloomberg HTML 파싱 전략
├── 04_cost_management.md   # 비용 관리 시스템
├── 05_implementation.md    # 구현 순서 및 체크리스트
└── 06_testing.md           # 테스트 계획
```

## 구현 타임라인

- **Day 1**: 기초 인프라 + 비용 관리 시스템
- **Day 2**: Bright Data 클라이언트 + Bloomberg 파서
- **Day 3**: 무료 API 클라이언트 + 하이브리드 오케스트레이터
- **Day 4**: 저장소 + 스케줄러
- **Day 5**: 테스트 및 검증
