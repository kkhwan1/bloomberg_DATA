# 구현 체크리스트

Bloomberg 데이터 수집 시스템 단계별 구현 가이드

---

## Phase 1: 인프라 구축 (Day 1)

### 1.1 프로젝트 구조 생성
- [ ] **루트 디렉토리 생성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\`
  - 확인: 디렉토리 구조가 아키텍처 문서와 일치하는지 검증

```
bloomberg_data/
├── src/
│   ├── __init__.py
│   ├── brightdata/
│   │   └── __init__.py
│   ├── parsers/
│   │   └── __init__.py
│   ├── free_apis/
│   │   └── __init__.py
│   ├── orchestrator/
│   │   └── __init__.py
│   ├── storage/
│   │   └── __init__.py
│   └── utils/
│       └── __init__.py
├── tests/
│   └── __init__.py
├── data/
│   ├── cache/
│   └── output/
├── logs/
└── plan/
```

- [ ] **모든 `__init__.py` 파일 생성**
  - 각 패키지 디렉토리에 빈 `__init__.py` 생성
  - Python 패키지로 인식되도록 설정

### 1.2 설정 파일 생성
- [ ] **`src/config.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\config.py`
  - 내용:
    ```python
    from pathlib import Path
    from typing import Optional
    import os
    from dotenv import load_dotenv

    load_dotenv()

    class Config:
        # 프로젝트 경로
        BASE_DIR = Path(__file__).parent.parent
        DATA_DIR = BASE_DIR / "data"
        CACHE_DIR = DATA_DIR / "cache"
        OUTPUT_DIR = DATA_DIR / "output"
        LOGS_DIR = BASE_DIR / "logs"

        # Bright Data 설정
        BRIGHTDATA_API_KEY: str = os.getenv("BRIGHTDATA_API_KEY", "")
        BRIGHTDATA_ZONE: str = os.getenv("BRIGHTDATA_ZONE", "")
        BRIGHTDATA_HOST: str = "brd.superproxy.io"
        BRIGHTDATA_PORT: int = 22225

        # 비용 관리
        DAILY_BUDGET_USD: float = 5.0
        COST_PER_REQUEST: float = 0.02
        ALERT_THRESHOLD: float = 0.8  # 80% 도달 시 알림

        # 캐시 설정
        CACHE_ENABLED: bool = True
        CACHE_TTL_SECONDS: int = 3600  # 1시간
        CACHE_DB_PATH: str = str(CACHE_DIR / "bloomberg_cache.db")

        # 무료 API 설정
        FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")

        # 스케줄링
        SCHEDULE_ENABLED: bool = True
        UPDATE_INTERVAL_MINUTES: int = 15

        # 로깅
        LOG_LEVEL: str = "INFO"
        LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        @classmethod
        def validate(cls) -> bool:
            """필수 설정 검증"""
            if not cls.BRIGHTDATA_API_KEY:
                raise ValueError("BRIGHTDATA_API_KEY is required")
            if not cls.BRIGHTDATA_ZONE:
                raise ValueError("BRIGHTDATA_ZONE is required")
            return True
    ```

### 1.3 의존성 관리
- [ ] **`requirements.txt` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\requirements.txt`
  - 내용:
    ```
    # 핵심 의존성
    requests>=2.31.0
    beautifulsoup4>=4.12.0
    lxml>=4.9.0

    # 무료 API
    yfinance>=0.2.28
    finnhub-python>=2.4.18
    websocket-client>=1.6.1

    # 스케줄링
    APScheduler>=3.10.4

    # 데이터 처리
    pandas>=2.0.0

    # 환경 변수
    python-dotenv>=1.0.0

    # 테스팅
    pytest>=7.4.0
    pytest-cov>=4.1.0
    pytest-mock>=3.11.1
    responses>=0.23.1

    # 로깅
    colorlog>=6.7.0
    ```

### 1.4 환경 변수 설정
- [ ] **`.env.example` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\.env.example`
  - 내용:
    ```
    # Bright Data 설정
    BRIGHTDATA_API_KEY=your_api_key_here
    BRIGHTDATA_ZONE=your_zone_here

    # Finnhub 설정 (선택사항)
    FINNHUB_API_KEY=your_finnhub_api_key_here

    # 비용 관리
    DAILY_BUDGET_USD=5.0
    COST_PER_REQUEST=0.02

    # 캐시 설정
    CACHE_ENABLED=true
    CACHE_TTL_SECONDS=3600
    ```

- [ ] **`.env` 파일 생성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\.env`
  - `.env.example` 복사 후 실제 값 입력
  - **주의**: 절대 Git에 커밋하지 않음

### 1.5 Git 설정
- [ ] **`.gitignore` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\.gitignore`
  - 내용:
    ```
    # 환경 변수
    .env

    # Python
    __pycache__/
    *.py[cod]
    *$py.class
    *.so
    .Python
    build/
    develop-eggs/
    dist/
    downloads/
    eggs/
    .eggs/
    lib/
    lib64/
    parts/
    sdist/
    var/
    wheels/
    *.egg-info/
    .installed.cfg
    *.egg

    # 가상 환경
    venv/
    env/
    ENV/

    # IDE
    .vscode/
    .idea/
    *.swp
    *.swo
    *~

    # 데이터 및 캐시
    data/cache/*.db
    data/output/*.csv
    data/output/*.json
    logs/*.log

    # 테스트
    .pytest_cache/
    .coverage
    htmlcov/

    # OS
    .DS_Store
    Thumbs.db
    ```

### 1.6 디렉토리 초기화
- [ ] **필수 디렉토리 생성 스크립트**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\setup_dirs.py`
  - 내용:
    ```python
    from pathlib import Path
    from src.config import Config

    def setup_directories():
        """프로젝트 디렉토리 구조 생성"""
        directories = [
            Config.DATA_DIR,
            Config.CACHE_DIR,
            Config.OUTPUT_DIR,
            Config.LOGS_DIR,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created: {directory}")

    if __name__ == "__main__":
        setup_directories()
    ```

- [ ] **스크립트 실행**
  ```bash
  cd c:\Users\USER\claude_code\bloomberg_data
  python setup_dirs.py
  ```

---

## Phase 2: 비용 관리 시스템 (Day 1-2)

### 2.1 CostTracker 구현
- [ ] **`src/utils/cost_tracker.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\utils\cost_tracker.py`
  - 기능:
    - Singleton 패턴 구현
    - 일일 예산 추적
    - 요청당 비용 계산
    - 예산 초과 감지
    - 알림 임계값 설정 (80%)
  - 주요 메서드:
    ```python
    class CostTracker:
        def __init__(self):
            self.daily_budget = Config.DAILY_BUDGET_USD
            self.cost_per_request = Config.COST_PER_REQUEST
            self.today_spent = 0.0
            self.request_count = 0

        def can_make_request(self) -> bool:
            """예산 확인"""

        def record_request(self, cost: float = None):
            """요청 기록"""

        def get_remaining_budget(self) -> float:
            """남은 예산 반환"""

        def reset_daily_budget(self):
            """일일 예산 리셋"""

        def should_alert(self) -> bool:
            """알림 필요 여부"""
    ```

- [ ] **테스트 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\tests\test_cost_tracker.py`
  - 테스트 케이스:
    - 예산 초과 시 요청 차단
    - 알림 임계값 감지
    - 일일 리셋 기능

### 2.2 CacheManager 구현
- [ ] **`src/utils/cache_manager.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\utils\cache_manager.py`
  - 기능:
    - SQLite 기반 캐시 저장
    - TTL(Time-To-Live) 관리
    - 캐시 키 생성 (symbol + data_type)
    - 만료된 캐시 자동 정리
  - 주요 메서드:
    ```python
    class CacheManager:
        def __init__(self):
            self.db_path = Config.CACHE_DB_PATH
            self.ttl = Config.CACHE_TTL_SECONDS
            self._init_db()

        def get(self, key: str) -> Optional[dict]:
            """캐시 조회"""

        def set(self, key: str, value: dict):
            """캐시 저장"""

        def invalidate(self, key: str):
            """캐시 무효화"""

        def clear_expired(self):
            """만료된 캐시 삭제"""

        @staticmethod
        def generate_key(symbol: str, data_type: str) -> str:
            """캐시 키 생성"""
    ```

- [ ] **데이터베이스 스키마 설계**
  ```sql
  CREATE TABLE IF NOT EXISTS cache (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      expires_at TIMESTAMP NOT NULL
  );
  CREATE INDEX idx_expires_at ON cache(expires_at);
  ```

- [ ] **테스트 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\tests\test_cache_manager.py`
  - 테스트 케이스:
    - 캐시 저장/조회
    - TTL 만료 확인
    - 만료된 캐시 정리

### 2.3 예외 처리 클래스
- [ ] **`src/utils/exceptions.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\utils\exceptions.py`
  - 내용:
    ```python
    class BudgetExhaustedError(Exception):
        """일일 예산 초과 예외"""
        def __init__(self, spent: float, budget: float):
            self.spent = spent
            self.budget = budget
            super().__init__(
                f"Daily budget exhausted: ${spent:.2f} / ${budget:.2f}"
            )

    class CacheError(Exception):
        """캐시 관련 예외"""
        pass

    class ParsingError(Exception):
        """파싱 관련 예외"""
        pass
    ```

### 2.4 통합 테스트
- [ ] **예산 알림 시스템 테스트**
  - 80% 도달 시 경고 로그 출력 확인
  - 100% 도달 시 `BudgetExhaustedError` 발생 확인

---

## Phase 3: Bright Data 클라이언트 (Day 2)

### 3.1 Bright Data 설정 클래스
- [ ] **`src/brightdata/config.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\brightdata\config.py`
  - 내용:
    ```python
    from dataclasses import dataclass
    from src.config import Config

    @dataclass
    class BrightDataConfig:
        host: str = Config.BRIGHTDATA_HOST
        port: int = Config.BRIGHTDATA_PORT
        username: str = Config.BRIGHTDATA_API_KEY
        zone: str = Config.BRIGHTDATA_ZONE
        timeout: int = 30

        @property
        def proxy_url(self) -> str:
            """프록시 URL 생성"""
            return f"http://{self.username}:{self.zone}@{self.host}:{self.port}"
    ```

### 3.2 Bright Data 클라이언트 구현
- [ ] **`src/brightdata/client.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\brightdata\client.py`
  - 기능:
    - 프록시를 통한 HTTP 요청
    - 비용 추적 통합
    - 재시도 로직 (3회, 지수 백오프)
    - 에러 핸들링
  - 주요 메서드:
    ```python
    import requests
    from typing import Optional
    from src.utils.cost_tracker import CostTracker
    from src.utils.exceptions import BudgetExhaustedError

    class BrightDataClient:
        def __init__(self, config: BrightDataConfig):
            self.config = config
            self.cost_tracker = CostTracker()
            self.session = requests.Session()

        def fetch_url(self, url: str, headers: Optional[dict] = None) -> str:
            """URL에서 HTML 가져오기"""
            # 1. 예산 확인
            if not self.cost_tracker.can_make_request():
                raise BudgetExhaustedError(...)

            # 2. 프록시 요청
            proxies = {
                "http": self.config.proxy_url,
                "https": self.config.proxy_url
            }

            # 3. 요청 실행 (재시도 포함)
            response = self._request_with_retry(url, proxies, headers)

            # 4. 비용 기록
            self.cost_tracker.record_request()

            return response.text

        def _request_with_retry(self, url: str, proxies: dict,
                               headers: Optional[dict], max_retries: int = 3) -> requests.Response:
            """재시도 로직"""
    ```

- [ ] **User-Agent 설정**
  ```python
  DEFAULT_HEADERS = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  }
  ```

### 3.3 연결 테스트
- [ ] **테스트 스크립트 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\tests\test_brightdata_client.py`
  - 테스트 케이스:
    - API 연결 확인 (1회 요청)
    - 프록시 설정 검증
    - 에러 핸들링 (타임아웃, 네트워크 오류)

- [ ] **실제 연결 테스트**
  ```python
  # 간단한 테스트 URL (비용 발생 주의)
  test_url = "https://www.bloomberg.com/quote/AAPL:US"
  client = BrightDataClient(BrightDataConfig())
  html = client.fetch_url(test_url)
  print(f"Received {len(html)} bytes")
  ```

---

## Phase 4: Bloomberg 파서 (Day 2-3)

### 4.1 파서 기본 클래스
- [ ] **`src/parsers/bloomberg_parser.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\parsers\bloomberg_parser.py`
  - 기능:
    - HTML 파싱 (BeautifulSoup)
    - 다중 추출 전략 (우선순위 순서)
    - 데이터 정규화
  - 클래스 구조:
    ```python
    from bs4 import BeautifulSoup
    from typing import Optional, Dict, Any
    import json
    import re

    class BloombergParser:
        def __init__(self, html: str):
            self.soup = BeautifulSoup(html, 'lxml')
            self.data = {}

        def parse(self) -> Dict[str, Any]:
            """모든 추출 전략 시도"""
            # 전략 1: JSON-LD
            self.data = self._extract_json_ld()
            if self.data:
                return self._normalize_data(self.data)

            # 전략 2: Next.js 데이터
            self.data = self._extract_nextjs_data()
            if self.data:
                return self._normalize_data(self.data)

            # 전략 3: HTML 테이블
            self.data = self._extract_from_html()
            return self._normalize_data(self.data)
    ```

### 4.2 JSON-LD 추출
- [ ] **`_extract_json_ld()` 메서드 구현**
  ```python
  def _extract_json_ld(self) -> Optional[Dict]:
      """JSON-LD 스크립트에서 데이터 추출"""
      script = self.soup.find('script', type='application/ld+json')
      if script:
          try:
              return json.loads(script.string)
          except json.JSONDecodeError:
              return None
      return None
  ```

- [ ] **테스트**: 샘플 HTML에서 JSON-LD 추출 확인

### 4.3 Next.js 데이터 추출
- [ ] **`_extract_nextjs_data()` 메서드 구현**
  ```python
  def _extract_nextjs_data(self) -> Optional[Dict]:
      """Next.js __NEXT_DATA__ 스크립트에서 추출"""
      script = self.soup.find('script', id='__NEXT_DATA__')
      if script:
          try:
              data = json.loads(script.string)
              # props.pageProps.quote 경로 탐색
              return data.get('props', {}).get('pageProps', {}).get('quote')
          except (json.JSONDecodeError, KeyError):
              return None
      return None
  ```

- [ ] **테스트**: Next.js 데이터 추출 확인

### 4.4 HTML 테이블 추출 (Fallback)
- [ ] **`_extract_from_html()` 메서드 구현**
  ```python
  def _extract_from_html(self) -> Dict[str, Any]:
      """HTML 구조에서 직접 추출"""
      data = {}

      # 가격 추출
      price_elem = self.soup.select_one('[data-test="price"]')
      if price_elem:
          data['price'] = self._clean_number(price_elem.text)

      # 거래량 추출
      volume_elem = self.soup.select_one('[data-field="volume"]')
      if volume_elem:
          data['volume'] = self._clean_number(volume_elem.text)

      # 시가총액 추출
      market_cap = self.soup.select_one('[data-field="marketCap"]')
      if market_cap:
          data['market_cap'] = self._clean_number(market_cap.text)

      return data
  ```

- [ ] **숫자 정리 함수**
  ```python
  @staticmethod
  def _clean_number(text: str) -> Optional[float]:
      """숫자 문자열 정리 (쉼표, 단위 제거)"""
      text = re.sub(r'[,$%]', '', text.strip())
      try:
          return float(text)
      except ValueError:
          return None
  ```

### 4.5 데이터 정규화
- [ ] **`_normalize_data()` 메서드 구현**
  ```python
  def _normalize_data(self, raw_data: Dict) -> Dict[str, Any]:
      """표준 형식으로 변환"""
      return {
          'symbol': raw_data.get('ticker', ''),
          'name': raw_data.get('name', ''),
          'price': float(raw_data.get('price', 0)),
          'change': float(raw_data.get('change', 0)),
          'change_percent': float(raw_data.get('changePercent', 0)),
          'volume': int(raw_data.get('volume', 0)),
          'market_cap': float(raw_data.get('marketCap', 0)),
          'pe_ratio': float(raw_data.get('peRatio', 0)),
          'timestamp': raw_data.get('timestamp', ''),
          'source': 'bloomberg'
      }
  ```

### 4.6 통합 테스트
- [ ] **실제 Bloomberg HTML로 테스트**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\tests\test_bloomberg_parser.py`
  - 테스트 데이터: `tests/fixtures/bloomberg_sample.html` 생성
  - 모든 추출 전략 검증

---

## Phase 5: 무료 API 클라이언트 (Day 3)

### 5.1 YFinance 클라이언트
- [ ] **`src/free_apis/yfinance_client.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\free_apis\yfinance_client.py`
  - 기능:
    - yfinance 라이브러리 래퍼
    - 데이터 정규화
    - 에러 핸들링
  - 구현:
    ```python
    import yfinance as yf
    from typing import Dict, Any, Optional

    class YFinanceClient:
        def fetch_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
            """주식 시세 조회"""
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info

                return {
                    'symbol': symbol,
                    'name': info.get('longName', ''),
                    'price': info.get('currentPrice', 0),
                    'change': info.get('regularMarketChange', 0),
                    'change_percent': info.get('regularMarketChangePercent', 0),
                    'volume': info.get('volume', 0),
                    'market_cap': info.get('marketCap', 0),
                    'pe_ratio': info.get('trailingPE', 0),
                    'source': 'yfinance'
                }
            except Exception as e:
                print(f"YFinance error for {symbol}: {e}")
                return None
    ```

- [ ] **테스트**
  - 테스트 심볼: AAPL, MSFT
  - 데이터 형식 검증

### 5.2 Finnhub WebSocket 클라이언트
- [ ] **`src/free_apis/finnhub_client.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\free_apis\finnhub_client.py`
  - 기능:
    - WebSocket 실시간 데이터 수신
    - 자동 재연결
    - 메시지 파싱
  - 구현:
    ```python
    import websocket
    import json
    from typing import Callable, List
    from src.config import Config

    class FinnhubWebSocket:
        def __init__(self, symbols: List[str], on_message: Callable):
            self.api_key = Config.FINNHUB_API_KEY
            self.symbols = symbols
            self.on_message = on_message
            self.ws = None

        def connect(self):
            """WebSocket 연결"""
            url = f"wss://ws.finnhub.io?token={self.api_key}"
            self.ws = websocket.WebSocketApp(
                url,
                on_message=self._handle_message,
                on_error=self._handle_error,
                on_close=self._handle_close,
                on_open=self._handle_open
            )

        def _handle_open(self, ws):
            """연결 성공 시 심볼 구독"""
            for symbol in self.symbols:
                ws.send(json.dumps({
                    'type': 'subscribe',
                    'symbol': symbol
                }))

        def _handle_message(self, ws, message):
            """메시지 수신 및 파싱"""
            data = json.loads(message)
            if data.get('type') == 'trade':
                for trade in data.get('data', []):
                    self.on_message({
                        'symbol': trade['s'],
                        'price': trade['p'],
                        'volume': trade['v'],
                        'timestamp': trade['t'],
                        'source': 'finnhub'
                    })
    ```

- [ ] **테스트**
  - WebSocket 연결 확인
  - 실시간 데이터 수신 확인

### 5.3 데이터 정규화 유틸리티
- [ ] **`src/utils/normalizer.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\utils\normalizer.py`
  - 기능: 다양한 소스의 데이터를 표준 형식으로 변환
  - 구현:
    ```python
    from typing import Dict, Any
    from datetime import datetime

    class DataNormalizer:
        @staticmethod
        def normalize(data: Dict[str, Any], source: str) -> Dict[str, Any]:
            """소스에 관계없이 표준 형식으로 변환"""
            return {
                'symbol': data.get('symbol', ''),
                'name': data.get('name', ''),
                'price': float(data.get('price', 0)),
                'change': float(data.get('change', 0)),
                'change_percent': float(data.get('change_percent', 0)),
                'volume': int(data.get('volume', 0)),
                'market_cap': float(data.get('market_cap', 0)),
                'pe_ratio': float(data.get('pe_ratio', 0)),
                'timestamp': data.get('timestamp', datetime.now().isoformat()),
                'source': source
            }
    ```

---

## Phase 6: 하이브리드 오케스트레이터 (Day 3-4)

### 6.1 데이터 소스 통합
- [ ] **`src/orchestrator/hybrid_source.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\orchestrator\hybrid_source.py`
  - 기능:
    - 우선순위 기반 데이터 소스 선택
    - 캐시 → 무료 API → 유료 API 순서
    - Fallback 로직
  - 구현:
    ```python
    from typing import Optional, Dict, Any
    from src.utils.cache_manager import CacheManager
    from src.free_apis.yfinance_client import YFinanceClient
    from src.brightdata.client import BrightDataClient
    from src.parsers.bloomberg_parser import BloombergParser

    class HybridDataSource:
        def __init__(self):
            self.cache = CacheManager()
            self.yfinance = YFinanceClient()
            self.brightdata = BrightDataClient(BrightDataConfig())

        def get_quote(self, symbol: str, force_fresh: bool = False) -> Optional[Dict[str, Any]]:
            """하이브리드 데이터 조회"""
            # 1. 캐시 확인
            if not force_fresh:
                cache_key = CacheManager.generate_key(symbol, 'quote')
                cached = self.cache.get(cache_key)
                if cached:
                    print(f"✓ Cache hit for {symbol}")
                    return cached

            # 2. 무료 API 시도 (YFinance)
            data = self.yfinance.fetch_quote(symbol)
            if data:
                print(f"✓ YFinance data for {symbol}")
                self.cache.set(cache_key, data)
                return data

            # 3. 유료 API 시도 (Bright Data + Bloomberg)
            try:
                url = f"https://www.bloomberg.com/quote/{symbol}:US"
                html = self.brightdata.fetch_url(url)
                parser = BloombergParser(html)
                data = parser.parse()

                if data:
                    print(f"✓ Bloomberg data for {symbol} (PAID)")
                    self.cache.set(cache_key, data)
                    return data
            except BudgetExhaustedError as e:
                print(f"✗ Budget exhausted: {e}")
                return None

            return None
    ```

### 6.2 스케줄러 통합
- [ ] **`src/orchestrator/scheduler.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\orchestrator\scheduler.py`
  - 기능:
    - APScheduler 통합
    - 주기적 데이터 수집 (15분 간격)
    - 일일 예산 리셋 (자정)
  - 구현:
    ```python
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from src.orchestrator.hybrid_source import HybridDataSource
    from src.utils.cost_tracker import CostTracker
    from src.config import Config
    from typing import List

    class DataScheduler:
        def __init__(self, symbols: List[str]):
            self.symbols = symbols
            self.hybrid_source = HybridDataSource()
            self.cost_tracker = CostTracker()
            self.scheduler = BackgroundScheduler()

        def start(self):
            """스케줄러 시작"""
            # 15분마다 데이터 수집
            self.scheduler.add_job(
                self._collect_data,
                'interval',
                minutes=Config.UPDATE_INTERVAL_MINUTES,
                id='collect_data'
            )

            # 매일 자정 예산 리셋
            self.scheduler.add_job(
                self.cost_tracker.reset_daily_budget,
                CronTrigger(hour=0, minute=0),
                id='reset_budget'
            )

            self.scheduler.start()
            print("✓ Scheduler started")

        def _collect_data(self):
            """모든 심볼 데이터 수집"""
            for symbol in self.symbols:
                data = self.hybrid_source.get_quote(symbol)
                if data:
                    # 저장 로직 (Phase 7에서 구현)
                    print(f"Collected: {symbol} @ ${data['price']}")
    ```

- [ ] **테스트**
  - 스케줄러 시작 확인
  - 작업 실행 로그 확인

---

## Phase 7: 데이터 저장 (Day 4)

### 7.1 CSV Writer
- [ ] **`src/storage/csv_writer.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\storage\csv_writer.py`
  - 기능:
    - CSV 형식 저장
    - 일별 파티셔닝 (YYYYMMDD.csv)
    - 헤더 자동 생성
  - 구현:
    ```python
    import csv
    from pathlib import Path
    from datetime import datetime
    from typing import Dict, Any, List
    from src.config import Config

    class CSVWriter:
        def __init__(self):
            self.output_dir = Config.OUTPUT_DIR / "csv"
            self.output_dir.mkdir(parents=True, exist_ok=True)

        def write(self, data: Dict[str, Any]):
            """단일 레코드 저장"""
            date_str = datetime.now().strftime("%Y%m%d")
            filepath = self.output_dir / f"{date_str}.csv"

            # 파일이 없으면 헤더 작성
            file_exists = filepath.exists()

            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data.keys())

                if not file_exists:
                    writer.writeheader()

                writer.writerow(data)

        def write_batch(self, data_list: List[Dict[str, Any]]):
            """배치 저장"""
            for data in data_list:
                self.write(data)
    ```

### 7.2 JSON Writer
- [ ] **`src/storage/json_writer.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\storage\json_writer.py`
  - 기능:
    - JSON Lines 형식 저장
    - 일별 파티셔닝
  - 구현:
    ```python
    import json
    from pathlib import Path
    from datetime import datetime
    from typing import Dict, Any, List
    from src.config import Config

    class JSONWriter:
        def __init__(self):
            self.output_dir = Config.OUTPUT_DIR / "json"
            self.output_dir.mkdir(parents=True, exist_ok=True)

        def write(self, data: Dict[str, Any]):
            """JSON Lines 형식으로 저장"""
            date_str = datetime.now().strftime("%Y%m%d")
            filepath = self.output_dir / f"{date_str}.jsonl"

            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')

        def write_batch(self, data_list: List[Dict[str, Any]]):
            """배치 저장"""
            for data in data_list:
                self.write(data)
    ```

### 7.3 저장 통합
- [ ] **스케줄러에 저장 로직 추가**
  - `src/orchestrator/scheduler.py` 수정
  - `_collect_data()` 메서드에 CSV/JSON Writer 통합:
    ```python
    from src.storage.csv_writer import CSVWriter
    from src.storage.json_writer import JSONWriter

    class DataScheduler:
        def __init__(self, symbols: List[str]):
            # ... 기존 코드 ...
            self.csv_writer = CSVWriter()
            self.json_writer = JSONWriter()

        def _collect_data(self):
            """모든 심볼 데이터 수집 및 저장"""
            for symbol in self.symbols:
                data = self.hybrid_source.get_quote(symbol)
                if data:
                    # CSV 저장
                    self.csv_writer.write(data)
                    # JSON 저장
                    self.json_writer.write(data)
                    print(f"✓ Saved: {symbol} @ ${data['price']}")
    ```

### 7.4 테스트
- [ ] **저장 기능 검증**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\tests\test_storage.py`
  - 테스트 케이스:
    - CSV 헤더 생성
    - 일별 파티셔닝
    - JSON Lines 형식

---

## Phase 8: 테스트 및 검증 (Day 5)

### 8.1 단위 테스트
- [ ] **모든 컴포넌트 단위 테스트 작성**
  - `tests/test_cost_tracker.py`
  - `tests/test_cache_manager.py`
  - `tests/test_brightdata_client.py`
  - `tests/test_bloomberg_parser.py`
  - `tests/test_yfinance_client.py`
  - `tests/test_storage.py`

- [ ] **테스트 실행**
  ```bash
  cd c:\Users\USER\claude_code\bloomberg_data
  pytest tests/ -v --cov=src
  ```

### 8.2 통합 테스트
- [ ] **`tests/test_integration.py` 작성**
  - 전체 워크플로우 테스트:
    1. 하이브리드 소스로 데이터 조회
    2. 캐시 확인
    3. CSV/JSON 저장
    4. 비용 추적
  - 구현:
    ```python
    from src.orchestrator.hybrid_source import HybridDataSource
    from src.storage.csv_writer import CSVWriter
    from src.utils.cost_tracker import CostTracker

    def test_full_workflow():
        # 1. 데이터 조회
        hybrid = HybridDataSource()
        data = hybrid.get_quote("AAPL")
        assert data is not None

        # 2. 캐시 확인
        cached = hybrid.cache.get(
            CacheManager.generate_key("AAPL", "quote")
        )
        assert cached is not None

        # 3. 저장
        writer = CSVWriter()
        writer.write(data)

        # 4. 비용 확인
        tracker = CostTracker()
        assert tracker.request_count > 0
    ```

### 8.3 비용 추적 검증
- [ ] **비용 시뮬레이션 테스트**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\tests\test_cost_simulation.py`
  - 시나리오:
    1. 250회 요청 시뮬레이션 (일일 예산 $5 / $0.02 = 250)
    2. 80% 도달 시 알림 확인 (200회)
    3. 100% 도달 시 차단 확인
  - 구현:
    ```python
    from src.utils.cost_tracker import CostTracker
    from src.utils.exceptions import BudgetExhaustedError
    import pytest

    def test_budget_enforcement():
        tracker = CostTracker()
        tracker.daily_budget = 5.0
        tracker.cost_per_request = 0.02

        # 200회까지 성공
        for _ in range(200):
            assert tracker.can_make_request()
            tracker.record_request()

        # 80% 도달 알림
        assert tracker.should_alert()

        # 250회에서 차단
        for _ in range(50):
            tracker.record_request()

        assert not tracker.can_make_request()
    ```

### 8.4 엔드투엔드 테스트
- [ ] **실제 환경 테스트**
  - 테스트 심볼: AAPL, MSFT, GOOGL
  - 체크리스트:
    - [ ] 캐시 우선 조회
    - [ ] YFinance fallback
    - [ ] Bright Data 조회 (1-2회만)
    - [ ] 비용 기록
    - [ ] CSV/JSON 파일 생성
    - [ ] 스케줄러 15분 간격 실행

### 8.5 성능 벤치마크
- [ ] **응답 시간 측정**
  - 캐시 조회: <10ms
  - YFinance 조회: <500ms
  - Bright Data 조회: <3s

- [ ] **메모리 사용량 확인**
  - 캐시 DB 크기 모니터링
  - 메모리 누수 검사

---

## Phase 9: 메인 애플리케이션 (Day 5)

### 9.1 CLI 인터페이스
- [ ] **`src/main.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\main.py`
  - 기능:
    - 명령줄 인터페이스
    - 심볼 목록 관리
    - 스케줄러 제어
  - 구현:
    ```python
    import argparse
    import time
    from src.orchestrator.scheduler import DataScheduler
    from src.config import Config

    def main():
        parser = argparse.ArgumentParser(description="Bloomberg Data Collector")
        parser.add_argument(
            'symbols',
            nargs='+',
            help='Stock symbols to track (e.g., AAPL MSFT GOOGL)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=15,
            help='Update interval in minutes (default: 15)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run once and exit (no scheduling)'
        )

        args = parser.parse_args()

        # 설정 검증
        Config.validate()

        # 스케줄러 시작
        scheduler = DataScheduler(args.symbols)

        if args.once:
            # 1회 실행
            scheduler._collect_data()
        else:
            # 스케줄러 시작
            scheduler.start()
            print(f"Monitoring {len(args.symbols)} symbols...")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
                scheduler.scheduler.shutdown()

    if __name__ == "__main__":
        main()
    ```

### 9.2 실행 예제
- [ ] **기본 실행**
  ```bash
  cd c:\Users\USER\claude_code\bloomberg_data
  python -m src.main AAPL MSFT GOOGL
  ```

- [ ] **1회 실행 (테스트용)**
  ```bash
  python -m src.main AAPL --once
  ```

### 9.3 로깅 설정
- [ ] **`src/utils/logger.py` 작성**
  - 경로: `c:\Users\USER\claude_code\bloomberg_data\src\utils\logger.py`
  - 기능:
    - 파일 + 콘솔 로깅
    - 로그 레벨 설정
    - 일별 로그 파일
  - 구현:
    ```python
    import logging
    from pathlib import Path
    from datetime import datetime
    from src.config import Config

    def setup_logger(name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(Config.LOG_LEVEL)

        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 파일 핸들러 (일별)
        date_str = datetime.now().strftime("%Y%m%d")
        log_file = Config.LOGS_DIR / f"{date_str}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # 포맷터
        formatter = logging.Formatter(Config.LOG_FORMAT)
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger
    ```

---

## 체크포인트 및 마일스톤

### Day 1 완료 기준
- [x] 프로젝트 구조 생성
- [x] 설정 파일 완성
- [x] 가상 환경 및 의존성 설치
- [x] Git 초기화

### Day 2 완료 기준
- [x] 비용 추적 시스템 작동
- [x] 캐시 시스템 작동
- [x] Bright Data 연결 성공 (1회 테스트)

### Day 3 완료 기준
- [x] Bloomberg 파서 완성 (3가지 전략)
- [x] YFinance 통합 완료
- [x] Finnhub WebSocket 연결

### Day 4 완료 기준
- [x] 하이브리드 소스 작동
- [x] 스케줄러 작동
- [x] CSV/JSON 저장 확인

### Day 5 완료 기준
- [x] 모든 단위 테스트 통과
- [x] 통합 테스트 통과
- [x] 비용 추적 검증
- [x] 실제 환경 테스트 성공

---

## 최종 검증 체크리스트

### 기능 검증
- [ ] 캐시 우선 조회 작동
- [ ] 무료 API fallback 작동
- [ ] 유료 API 요청 최소화 (1일 250회 이하)
- [ ] 일일 예산 $5 준수
- [ ] 80% 알림 작동
- [ ] 데이터 파일 생성 (CSV/JSON)
- [ ] 스케줄러 15분 간격 실행

### 성능 검증
- [ ] 캐시 조회 <10ms
- [ ] API 응답 <3s
- [ ] 메모리 사용 정상

### 안정성 검증
- [ ] 네트워크 오류 핸들링
- [ ] API 타임아웃 처리
- [ ] 예산 초과 차단
- [ ] 캐시 만료 자동 정리

### 문서화
- [ ] README.md 작성
- [ ] API 문서화
- [ ] 사용 예제 작성
- [ ] 트러블슈팅 가이드

---

## 참고 파일 경로

| 문서 | 경로 |
|------|------|
| 아키텍처 | `c:\Users\USER\claude_code\bloomberg_data\plan\01_architecture.md` |
| 비용 분석 | `c:\Users\USER\claude_code\bloomberg_data\plan\02_cost_analysis.md` |
| 기술 스택 | `c:\Users\USER\claude_code\bloomberg_data\plan\03_tech_stack.md` |
| 개발 일정 | `c:\Users\USER\claude_code\bloomberg_data\plan\04_timeline.md` |

---

## 다음 단계

이 체크리스트를 완료한 후:

1. **프로덕션 배포** 문서 작성 (`06_deployment.md`)
2. **모니터링 시스템** 구축 (`07_monitoring.md`)
3. **확장성 계획** 수립 (`08_scalability.md`)

---

**작성일**: 2026-01-07
**최종 수정**: 2026-01-07
**상태**: 구현 준비 완료
