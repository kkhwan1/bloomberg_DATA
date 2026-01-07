# Bloomberg 글로벌 인덱스 크롤링 계획

## 목표
Google Sheets의 59개 글로벌 주가지수 데이터를 Bloomberg에서 크롤링

## 대상 인덱스 목록 (59개)

### 시트 1 (1-20)
| # | Code | Country |
|---|------|---------|
| 1 | AE@DFM | UAE |
| 2 | AR@MERV | Argentina |
| 3 | AT@ATX | Austria |
| 4 | AU@AORD | Australia |
| 5 | BE@MFX | Belgium |
| 6 | BH@ASI | Bahrain |
| 7 | BR@BVSP | Brazil |
| 8 | BR@BVSPX | Brazil |
| 9 | BU@SOFIX | Bulgaria |
| 10 | CA@SPTSX | Canada |
| 11 | CA@SPTSXX | Canada |
| 12 | CH@SSMI | Switzerland |
| 13 | CL@IGPA | Chile |
| 14 | CO@COLCAP | Colombia |
| 15 | DK@KFX | Denmark |
| 16 | EG@CASE30 | Egypt |
| 17 | ES@IBEX | Spain |
| 18 | ET@TALSE | Estonia |
| 19 | FI@HEX | Finland |
| 20 | GR@ASE | Greece |

### 시트 2 (21-40)
| # | Code | Country |
|---|------|---------|
| 21 | HU@BUX | Hungary |
| 22 | ID@JKSE | Indonesia |
| 23 | IE@ISEQ | Ireland |
| 24 | IL@TA125 | Israel |
| 25 | IN@BSE30 | India |
| 26 | IS@ICEXI | Iceland |
| 27 | IT@FTSEMIB | Italy |
| 28 | JO@FTI | Jordan |
| 29 | KW@MKIX | Kuwait |
| 30 | LT@VILSE | Lithuania |
| 31 | LV@RIGSE | Latvia |
| 32 | MA@MASI | Morocco |
| 33 | MT@MALTEX | Malta |
| 34 | MX@INMEX | Mexico |
| 35 | MX@IPC | Mexico |
| 36 | MY@KLSE | Malaysia |
| 37 | NG@NGSE | Nigeria |
| 38 | NL@AEX | Netherlands |
| 39 | NO@OSEAX | Norway |
| 40 | NZ@NZ50 | New Zealand |

### 시트 3 (41-59)
| # | Code | Country |
|---|------|---------|
| 41 | OM@MSMI | Oman |
| 42 | PA@PX50 | Panama |
| 43 | PH@COMP | Philippines |
| 44 | PK@KSE100 | Pakistan |
| 45 | PL@WIGI | Poland |
| 46 | PT@PSI20 | Portugal |
| 47 | QA@MKIX | Qatar |
| 48 | SA@TASI | Saudi Arabia |
| 49 | SE@OMXS30 | Sweden |
| 50 | SE@SXASI | Sweden |
| 51 | SG@STI | Singapore |
| 52 | SR@CSEALL | Sri Lanka |
| 53 | SV@SBITOP | Slovenia |
| 54 | TH@SET | Thailand |
| 55 | TR@ISE100 | Turkey |
| 56 | VE@INDG | Venezuela |
| 57 | VN@VHIN | Vietnam |
| 58 | VN@VIDX | Vietnam |
| 59 | ZA@ALSH | South Africa |

## 예상 비용
- 59개 URL × $0.0015 = **$0.0885**
- 현재 잔액: $5.50

---

## 구현 계획

### 생성할 파일들
1. `data/index_urls.json` - 59개 인덱스 URL 목록
2. `scripts/crawl_indices.py` - 크롤링 스크립트

### 구현 단계

#### Step 1: URL 매핑 분석
- 각 코드(예: AE@DFM)와 Bloomberg 심볼 매핑 확인
- bloomberg.co.jp URL 패턴 분석

#### Step 2: JSON 파일 생성
- 59개 인덱스의 code, country, bloomberg_url 저장

#### Step 3: 크롤링 스크립트 작성
- Bright Data API 사용 (Bearer 토큰)
- 기존 BloombergParser 재사용
- Rate limiting (1초 딜레이)
- 진행률 표시
- 결과 저장 (CSV/JSON)

### 주요 기능
- 기존 `src/parsers/bloomberg_parser.py` 재사용
- 기존 `src/clients/bright_data.py` 참조
- 비용 추적 통합
- 에러 핸들링 및 재시도 로직

---

## 분석 필요 사항
1. [ ] 코드 → Bloomberg 심볼 매핑 확인 (예: AE@DFM → DFMGI:IND)
2. [ ] bloomberg.co.jp vs bloomberg.com 파서 호환성 확인
3. [ ] 기존 파서가 인덱스 데이터 추출 가능한지 테스트
