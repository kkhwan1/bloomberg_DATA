# Bright Data API 통합 가이드

## 목차
1. [계정 정보](#계정-정보)
2. [API 사용 예제](#api-사용-예제)
3. [응답 처리](#응답-처리)
4. [비용 최적화 전략](#비용-최적화-전략)
5. [Python 클라이언트 구현](#python-클라이언트-구현)
6. [모범 사례](#모범-사례)

---

## 계정 정보

### Zone 설정
- **Zone 이름**: `bloomberg`
- **용도**: Bloomberg 웹사이트 데이터 스크래핑
- **지역**: 전 세계 프록시 네트워크

### 비용 구조
- **요금제**: CPM (Cost Per Mille) - 1,000개 요청당 과금
- **단가**: $1.50/CPM
- **현재 잔액**: $5.50
- **사용 가능 요청 수**: 약 3,667회

### 계산 예시
```
잔액: $5.50
단가: $1.50 / 1,000 requests
사용 가능: ($5.50 / $1.50) × 1,000 = 3,667 requests
요청당 비용: $0.0015
```

### API 엔드포인트
```
https://api.brightdata.com/request
```

### 인증 방식
- **방법**: Bearer Token
- **헤더**: `Authorization: Bearer <API_TOKEN>`
- **토큰 위치**: 환경 변수 `BRIGHT_DATA_TOKEN`

---

## API 사용 예제

### 1. cURL 예제

#### 기본 요청
```bash
curl -X POST https://api.brightdata.com/request \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "zone": "bloomberg",
    "url": "https://www.bloomberg.com/markets/commodities",
    "format": "raw"
  }'
```

#### 성공 응답
```bash
HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
  <head>...</head>
  <body>
    <!-- Bloomberg HTML content -->
  </body>
</html>
```

#### 에러 응답
```bash
HTTP/1.1 401 Unauthorized
{
  "error": "Invalid authentication credentials"
}
```

### 2. Python aiohttp 비동기 예제

#### 단일 요청
```python
import aiohttp
import asyncio
from typing import Optional

async def fetch_bloomberg_page(url: str, api_token: str) -> Optional[str]:
    """
    Bright Data API를 통해 Bloomberg 페이지 가져오기

    Args:
        url: Bloomberg URL
        api_token: Bright Data API 토큰

    Returns:
        HTML 콘텐츠 또는 None (실패 시)
    """
    endpoint = "https://api.brightdata.com/request"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "zone": "bloomberg",
        "url": url,
        "format": "raw"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    print(f"✅ 성공: {url}")
                    return html
                else:
                    error_text = await response.text()
                    print(f"❌ 에러 {response.status}: {error_text}")
                    return None

        except asyncio.TimeoutError:
            print(f"⏱️ 타임아웃: {url}")
            return None
        except Exception as e:
            print(f"🚨 예외 발생: {e}")
            return None

# 사용 예시
async def main():
    token = "your_api_token_here"
    url = "https://www.bloomberg.com/markets/commodities"
    html = await fetch_bloomberg_page(url, token)
    if html:
        print(f"HTML 길이: {len(html)} bytes")

asyncio.run(main())
```

#### 병렬 다중 요청
```python
import aiohttp
import asyncio
from typing import List, Dict

async def fetch_multiple_pages(
    urls: List[str],
    api_token: str,
    max_concurrent: int = 5
) -> Dict[str, Optional[str]]:
    """
    여러 Bloomberg 페이지를 병렬로 가져오기

    Args:
        urls: Bloomberg URL 리스트
        api_token: Bright Data API 토큰
        max_concurrent: 최대 동시 요청 수

    Returns:
        URL을 키로, HTML 콘텐츠를 값으로 하는 딕셔너리
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_limit(url: str) -> tuple[str, Optional[str]]:
        async with semaphore:
            html = await fetch_bloomberg_page(url, api_token)
            return (url, html)

    tasks = [fetch_with_limit(url) for url in urls]
    results = await asyncio.gather(*tasks)

    return dict(results)

# 사용 예시
async def main():
    token = "your_api_token_here"
    urls = [
        "https://www.bloomberg.com/markets/commodities",
        "https://www.bloomberg.com/markets/currencies",
        "https://www.bloomberg.com/markets/stocks"
    ]

    results = await fetch_multiple_pages(urls, token, max_concurrent=3)

    for url, html in results.items():
        if html:
            print(f"✅ {url}: {len(html)} bytes")
        else:
            print(f"❌ {url}: 실패")

asyncio.run(main())
```

### 3. 요청 페이로드 구조

#### 필수 필드
```python
{
    "zone": "bloomberg",      # Zone 이름 (필수)
    "url": "https://...",     # 대상 URL (필수)
    "format": "raw"           # 응답 형식 (필수)
}
```

#### 선택적 필드
```python
{
    "zone": "bloomberg",
    "url": "https://www.bloomberg.com/markets/commodities",
    "format": "raw",
    "country": "us",           # 프록시 국가 지정
    "render": True,            # JavaScript 렌더링 활성화
    "session": "session_123",  # 세션 ID (동일 IP 유지)
    "timeout": 60000           # 타임아웃 (밀리초)
}
```

#### 형식 옵션
- `raw`: HTML 원본 (기본값, 권장)
- `json`: 구조화된 JSON 응답
- `screenshot`: 스크린샷 (추가 비용 발생)

---

## 응답 처리

### HTTP 상태 코드

#### 성공 응답
| 코드 | 의미 | 처리 방법 |
|------|------|----------|
| 200 | 성공 | HTML 콘텐츠 파싱 |

#### 클라이언트 에러
| 코드 | 의미 | 처리 방법 |
|------|------|----------|
| 400 | 잘못된 요청 | 페이로드 검증 |
| 401 | 인증 실패 | API 토큰 확인 |
| 403 | 권한 없음 | Zone 설정 확인 |
| 429 | 요청 제한 초과 | 재시도 지연 (exponential backoff) |

#### 서버 에러
| 코드 | 의미 | 처리 방법 |
|------|------|----------|
| 500 | 서버 에러 | 재시도 (최대 3회) |
| 502 | Bad Gateway | 재시도 (최대 3회) |
| 503 | 서비스 이용 불가 | 재시도 지연 |
| 504 | Gateway Timeout | 타임아웃 증가 후 재시도 |

### 에러 처리 패턴

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ErrorType(Enum):
    """에러 유형"""
    AUTH_ERROR = "authentication"      # 401, 403
    RATE_LIMIT = "rate_limit"         # 429
    SERVER_ERROR = "server_error"     # 500, 502, 503, 504
    TIMEOUT = "timeout"                # asyncio.TimeoutError
    INVALID_REQUEST = "invalid"       # 400
    UNKNOWN = "unknown"

@dataclass
class APIError:
    """API 에러 정보"""
    error_type: ErrorType
    status_code: Optional[int]
    message: str
    retry_after: Optional[int] = None  # 재시도까지 대기 시간 (초)

async def handle_response(response: aiohttp.ClientResponse) -> tuple[bool, Optional[str], Optional[APIError]]:
    """
    API 응답 처리

    Returns:
        (성공 여부, HTML 콘텐츠, 에러 정보)
    """
    if response.status == 200:
        html = await response.text()
        return (True, html, None)

    error_text = await response.text()

    # 에러 유형 분류
    if response.status in [401, 403]:
        error = APIError(
            error_type=ErrorType.AUTH_ERROR,
            status_code=response.status,
            message=f"인증 실패: {error_text}"
        )
    elif response.status == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        error = APIError(
            error_type=ErrorType.RATE_LIMIT,
            status_code=429,
            message="요청 제한 초과",
            retry_after=retry_after
        )
    elif response.status >= 500:
        error = APIError(
            error_type=ErrorType.SERVER_ERROR,
            status_code=response.status,
            message=f"서버 에러: {error_text}"
        )
    elif response.status == 400:
        error = APIError(
            error_type=ErrorType.INVALID_REQUEST,
            status_code=400,
            message=f"잘못된 요청: {error_text}"
        )
    else:
        error = APIError(
            error_type=ErrorType.UNKNOWN,
            status_code=response.status,
            message=error_text
        )

    return (False, None, error)
```

### 재시도 로직 (Exponential Backoff)

```python
import asyncio
from typing import Optional, Callable

async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0
) -> Optional[str]:
    """
    Exponential backoff을 사용한 재시도

    Args:
        func: 비동기 함수
        max_retries: 최대 재시도 횟수
        initial_delay: 초기 지연 시간 (초)
        max_delay: 최대 지연 시간 (초)
        backoff_factor: 지연 증가 배수

    Returns:
        함수 결과 또는 None
    """
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            result = await func()
            if result:
                return result

            # 실패 시 재시도
            if attempt < max_retries:
                print(f"🔄 재시도 {attempt + 1}/{max_retries} (대기: {delay}초)")
                await asyncio.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)

        except asyncio.TimeoutError:
            if attempt < max_retries:
                print(f"⏱️ 타임아웃 - 재시도 {attempt + 1}/{max_retries}")
                await asyncio.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)
            else:
                print(f"❌ 최대 재시도 횟수 초과")
                return None

        except Exception as e:
            print(f"🚨 예외 발생: {e}")
            return None

    return None

# 사용 예시
async def fetch_with_retry(url: str, api_token: str) -> Optional[str]:
    """재시도 로직이 포함된 페이지 가져오기"""
    return await retry_with_backoff(
        lambda: fetch_bloomberg_page(url, api_token),
        max_retries=3,
        initial_delay=2.0,
        backoff_factor=2.0
    )
```

---

## 비용 최적화 전략

### 1. 15분 캐싱 전략

#### 목표
- **요청 감소**: 70% 이상
- **비용 절감**: $1.05/1,000회 → $0.45/1,000회
- **신선도 유지**: 15분 이내 데이터

#### 캐싱 구조
```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict
import hashlib

@dataclass
class CacheEntry:
    """캐시 항목"""
    url: str
    html: str
    timestamp: datetime
    ttl_minutes: int = 15

    def is_expired(self) -> bool:
        """캐시 만료 여부 확인"""
        expiry = self.timestamp + timedelta(minutes=self.ttl_minutes)
        return datetime.now() > expiry

    def age_seconds(self) -> float:
        """캐시 나이 (초)"""
        return (datetime.now() - self.timestamp).total_seconds()

class SimpleCache:
    """간단한 인메모리 캐시"""

    def __init__(self, ttl_minutes: int = 15):
        self.cache: Dict[str, CacheEntry] = {}
        self.ttl_minutes = ttl_minutes
        self.hits = 0
        self.misses = 0

    def _generate_key(self, url: str) -> str:
        """URL을 캐시 키로 변환"""
        return hashlib.md5(url.encode()).hexdigest()

    def get(self, url: str) -> Optional[str]:
        """캐시에서 가져오기"""
        key = self._generate_key(url)
        entry = self.cache.get(key)

        if entry and not entry.is_expired():
            self.hits += 1
            print(f"✅ 캐시 히트: {url} (나이: {entry.age_seconds():.0f}초)")
            return entry.html

        self.misses += 1

        # 만료된 항목 제거
        if entry:
            del self.cache[key]
            print(f"🗑️ 만료된 캐시 제거: {url}")

        return None

    def set(self, url: str, html: str):
        """캐시에 저장"""
        key = self._generate_key(url)
        entry = CacheEntry(
            url=url,
            html=html,
            timestamp=datetime.now(),
            ttl_minutes=self.ttl_minutes
        )
        self.cache[key] = entry
        print(f"💾 캐시 저장: {url}")

    def clear_expired(self):
        """만료된 항목 일괄 제거"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            print(f"🗑️ 만료된 캐시 {len(expired_keys)}개 제거")

    def stats(self) -> Dict:
        """캐시 통계"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "cached_items": len(self.cache),
            "total_requests": total
        }
```

#### 캐시 사용 예시
```python
cache = SimpleCache(ttl_minutes=15)

async def fetch_with_cache(url: str, api_token: str) -> Optional[str]:
    """캐시를 사용한 페이지 가져오기"""
    # 1. 캐시 확인
    cached_html = cache.get(url)
    if cached_html:
        return cached_html

    # 2. API 요청
    html = await fetch_bloomberg_page(url, api_token)

    # 3. 캐시 저장
    if html:
        cache.set(url, html)

    return html

# 주기적 캐시 정리
async def periodic_cache_cleanup(interval_minutes: int = 30):
    """주기적으로 만료된 캐시 정리"""
    while True:
        await asyncio.sleep(interval_minutes * 60)
        cache.clear_expired()
        print(f"📊 캐시 통계: {cache.stats()}")
```

### 2. 하이브리드 접근 방식

#### 전략
1. **무료 API 우선 시도** (Yahoo Finance, Alpha Vantage)
2. **실패 시 Bright Data 사용**
3. **결과 캐싱으로 중복 방지**

#### 구현
```python
from enum import Enum
from typing import Optional, List, Callable

class DataSource(Enum):
    """데이터 소스"""
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    BRIGHT_DATA = "bright_data"

@dataclass
class FetchResult:
    """데이터 가져오기 결과"""
    success: bool
    data: Optional[str]
    source: DataSource
    cost: float  # USD
    error: Optional[str] = None

async def fetch_with_fallback(
    url: str,
    strategies: List[Callable]
) -> FetchResult:
    """
    여러 데이터 소스를 순차적으로 시도

    Args:
        url: 대상 URL
        strategies: 시도할 전략 리스트 (우선순위순)

    Returns:
        FetchResult
    """
    for strategy in strategies:
        try:
            result = await strategy(url)
            if result.success:
                return result
        except Exception as e:
            print(f"⚠️ {result.source.value} 실패: {e}")
            continue

    return FetchResult(
        success=False,
        data=None,
        source=DataSource.BRIGHT_DATA,
        cost=0.0,
        error="모든 데이터 소스 실패"
    )

# 전략 정의
async def yahoo_finance_strategy(url: str) -> FetchResult:
    """Yahoo Finance API 시도 (무료)"""
    # Yahoo Finance API 구현
    # ...
    return FetchResult(
        success=True,
        data="...",
        source=DataSource.YAHOO_FINANCE,
        cost=0.0
    )

async def alpha_vantage_strategy(url: str) -> FetchResult:
    """Alpha Vantage API 시도 (무료, 제한적)"""
    # Alpha Vantage API 구현
    # ...
    return FetchResult(
        success=False,
        data=None,
        source=DataSource.ALPHA_VANTAGE,
        cost=0.0,
        error="Rate limit exceeded"
    )

async def bright_data_strategy(url: str, api_token: str) -> FetchResult:
    """Bright Data API 시도 (유료)"""
    html = await fetch_bloomberg_page(url, api_token)
    return FetchResult(
        success=html is not None,
        data=html,
        source=DataSource.BRIGHT_DATA,
        cost=0.0015  # $1.50 / 1000
    )

# 사용 예시
async def fetch_market_data(url: str, api_token: str) -> FetchResult:
    """시장 데이터 가져오기 (하이브리드 접근)"""
    strategies = [
        yahoo_finance_strategy,
        alpha_vantage_strategy,
        lambda u: bright_data_strategy(u, api_token)
    ]

    result = await fetch_with_fallback(url, strategies)
    print(f"📊 데이터 소스: {result.source.value}, 비용: ${result.cost:.4f}")

    return result
```

### 3. 예산 알림 시스템

#### 임계값
- **50% ($2.75)**: 주의 - 로그 기록
- **80% ($4.40)**: 경고 - 이메일 알림
- **95% ($5.23)**: 긴급 - API 호출 중단

#### 구현
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum

class AlertLevel(Enum):
    """알림 수준"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class BudgetAlert:
    """예산 알림"""
    level: AlertLevel
    threshold: float  # 퍼센트
    current_usage: float  # USD
    total_budget: float  # USD
    message: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class CostTracker:
    """비용 추적기"""
    total_budget: float  # USD
    current_usage: float = 0.0
    request_count: int = 0
    alerts: List[BudgetAlert] = field(default_factory=list)
    alert_thresholds: List[float] = field(default_factory=lambda: [0.5, 0.8, 0.95])
    _alert_sent: set = field(default_factory=set)

    def add_request(self, cost: float = 0.0015):
        """요청 비용 추가"""
        self.current_usage += cost
        self.request_count += 1

        # 예산 초과 확인
        self._check_budget()

    def _check_budget(self):
        """예산 임계값 확인 및 알림"""
        usage_percent = self.current_usage / self.total_budget

        for threshold in self.alert_thresholds:
            if usage_percent >= threshold and threshold not in self._alert_sent:
                self._send_alert(threshold, usage_percent)
                self._alert_sent.add(threshold)

    def _send_alert(self, threshold: float, usage_percent: float):
        """알림 발송"""
        if threshold >= 0.95:
            level = AlertLevel.CRITICAL
            message = f"🚨 긴급: 예산의 {threshold*100:.0f}% 사용 - API 호출 중단 권장"
        elif threshold >= 0.8:
            level = AlertLevel.WARNING
            message = f"⚠️ 경고: 예산의 {threshold*100:.0f}% 사용"
        else:
            level = AlertLevel.INFO
            message = f"ℹ️ 주의: 예산의 {threshold*100:.0f}% 사용"

        alert = BudgetAlert(
            level=level,
            threshold=threshold,
            current_usage=self.current_usage,
            total_budget=self.total_budget,
            message=message
        )

        self.alerts.append(alert)
        print(f"{message} (${self.current_usage:.2f} / ${self.total_budget:.2f})")

        # 이메일/Slack 알림 발송 로직 추가 가능
        if level == AlertLevel.CRITICAL:
            self._emergency_shutdown()

    def _emergency_shutdown(self):
        """긴급 차단"""
        print("🛑 예산 한도 초과로 API 호출 차단")
        # API 호출 차단 로직 구현

    def can_make_request(self) -> bool:
        """요청 가능 여부 확인"""
        return self.current_usage / self.total_budget < 0.95

    def remaining_budget(self) -> float:
        """남은 예산"""
        return self.total_budget - self.current_usage

    def remaining_requests(self, cost_per_request: float = 0.0015) -> int:
        """남은 요청 가능 횟수"""
        return int(self.remaining_budget() / cost_per_request)

    def stats(self) -> Dict:
        """통계 정보"""
        usage_percent = (self.current_usage / self.total_budget) * 100

        return {
            "total_budget": f"${self.total_budget:.2f}",
            "current_usage": f"${self.current_usage:.2f}",
            "remaining": f"${self.remaining_budget():.2f}",
            "usage_percent": f"{usage_percent:.1f}%",
            "request_count": self.request_count,
            "remaining_requests": self.remaining_requests(),
            "alerts_triggered": len(self.alerts)
        }

# 사용 예시
tracker = CostTracker(total_budget=5.50)

async def fetch_with_budget_check(url: str, api_token: str) -> Optional[str]:
    """예산 확인 후 페이지 가져오기"""
    # 1. 예산 확인
    if not tracker.can_make_request():
        print("🛑 예산 한도 초과로 요청 차단")
        return None

    # 2. 캐시 확인
    cached_html = cache.get(url)
    if cached_html:
        return cached_html

    # 3. API 요청
    html = await fetch_bloomberg_page(url, api_token)

    # 4. 비용 기록
    if html:
        tracker.add_request(cost=0.0015)
        cache.set(url, html)

    # 5. 통계 출력
    if tracker.request_count % 10 == 0:
        print(f"📊 비용 통계: {tracker.stats()}")

    return html
```

### 4. 비용 최적화 요약

| 전략 | 절감 효과 | 구현 복잡도 |
|------|----------|------------|
| 15분 캐싱 | 70% | 낮음 |
| 하이브리드 접근 | 40-60% | 중간 |
| 예산 알림 | 과금 방지 | 낮음 |
| 요청 배치 처리 | 10-20% | 중간 |

#### 종합 효과
```
초기 비용: $1.50 / 1,000 requests
캐싱 적용 (70% 감소): $0.45 / 1,000 requests
하이브리드 (추가 50% 감소): $0.23 / 1,000 requests

예산 $5.50으로:
- 초기: 3,667 requests
- 최적화 후: ~23,913 requests (6.5배 증가)
```

---

## Python 클라이언트 구현

### 완전한 통합 클라이언트

```python
import aiohttp
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum
import hashlib
import os

# ============================================================
# Configuration
# ============================================================

@dataclass
class BrightDataConfig:
    """Bright Data 설정"""
    api_token: str
    zone: str = "bloomberg"
    endpoint: str = "https://api.brightdata.com/request"
    timeout_seconds: int = 30
    max_retries: int = 3
    initial_retry_delay: float = 2.0
    backoff_factor: float = 2.0
    max_retry_delay: float = 60.0

    @classmethod
    def from_env(cls) -> "BrightDataConfig":
        """환경 변수에서 설정 로드"""
        api_token = os.getenv("BRIGHT_DATA_TOKEN")
        if not api_token:
            raise ValueError("BRIGHT_DATA_TOKEN 환경 변수가 설정되지 않았습니다")

        return cls(
            api_token=api_token,
            zone=os.getenv("BRIGHT_DATA_ZONE", "bloomberg")
        )

# ============================================================
# Cache System
# ============================================================

@dataclass
class CacheEntry:
    """캐시 항목"""
    url: str
    html: str
    timestamp: datetime
    ttl_minutes: int = 15

    def is_expired(self) -> bool:
        """캐시 만료 여부"""
        from datetime import timedelta
        expiry = self.timestamp + timedelta(minutes=self.ttl_minutes)
        return datetime.now() > expiry

    def age_seconds(self) -> float:
        """캐시 나이 (초)"""
        return (datetime.now() - self.timestamp).total_seconds()

class Cache:
    """인메모리 캐시"""

    def __init__(self, ttl_minutes: int = 15):
        self.cache: Dict[str, CacheEntry] = {}
        self.ttl_minutes = ttl_minutes
        self.hits = 0
        self.misses = 0

    def _key(self, url: str) -> str:
        """URL을 캐시 키로 변환"""
        return hashlib.md5(url.encode()).hexdigest()

    def get(self, url: str) -> Optional[str]:
        """캐시에서 가져오기"""
        key = self._key(url)
        entry = self.cache.get(key)

        if entry and not entry.is_expired():
            self.hits += 1
            return entry.html

        self.misses += 1
        if entry:
            del self.cache[key]

        return None

    def set(self, url: str, html: str):
        """캐시에 저장"""
        key = self._key(url)
        self.cache[key] = CacheEntry(
            url=url,
            html=html,
            timestamp=datetime.now(),
            ttl_minutes=self.ttl_minutes
        )

    def clear_expired(self):
        """만료된 항목 제거"""
        expired = [k for k, v in self.cache.items() if v.is_expired()]
        for key in expired:
            del self.cache[key]

    def stats(self) -> Dict:
        """캐시 통계"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "cached_items": len(self.cache)
        }

# ============================================================
# Cost Tracking
# ============================================================

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class BudgetAlert:
    """예산 알림"""
    level: AlertLevel
    threshold: float
    current_usage: float
    total_budget: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class CostTracker:
    """비용 추적기"""
    total_budget: float
    cost_per_request: float = 0.0015
    current_usage: float = 0.0
    request_count: int = 0
    alerts: List[BudgetAlert] = field(default_factory=list)
    alert_thresholds: List[float] = field(default_factory=lambda: [0.5, 0.8, 0.95])
    _alert_sent: set = field(default_factory=set)

    def add_request(self, cost: Optional[float] = None):
        """요청 비용 추가"""
        cost = cost or self.cost_per_request
        self.current_usage += cost
        self.request_count += 1
        self._check_budget()

    def _check_budget(self):
        """예산 확인"""
        usage_percent = self.current_usage / self.total_budget

        for threshold in self.alert_thresholds:
            if usage_percent >= threshold and threshold not in self._alert_sent:
                self._send_alert(threshold)
                self._alert_sent.add(threshold)

    def _send_alert(self, threshold: float):
        """알림 발송"""
        if threshold >= 0.95:
            level = AlertLevel.CRITICAL
            message = f"🚨 긴급: 예산의 {threshold*100:.0f}% 사용"
        elif threshold >= 0.8:
            level = AlertLevel.WARNING
            message = f"⚠️ 경고: 예산의 {threshold*100:.0f}% 사용"
        else:
            level = AlertLevel.INFO
            message = f"ℹ️ 주의: 예산의 {threshold*100:.0f}% 사용"

        alert = BudgetAlert(
            level=level,
            threshold=threshold,
            current_usage=self.current_usage,
            total_budget=self.total_budget,
            message=message
        )
        self.alerts.append(alert)
        print(f"{message} (${self.current_usage:.2f} / ${self.total_budget:.2f})")

    def can_make_request(self) -> bool:
        """요청 가능 여부"""
        return self.current_usage / self.total_budget < 0.95

    def remaining_budget(self) -> float:
        """남은 예산"""
        return self.total_budget - self.current_usage

    def remaining_requests(self) -> int:
        """남은 요청 가능 횟수"""
        return int(self.remaining_budget() / self.cost_per_request)

    def stats(self) -> Dict:
        """통계"""
        usage_percent = (self.current_usage / self.total_budget) * 100
        return {
            "total_budget": f"${self.total_budget:.2f}",
            "current_usage": f"${self.current_usage:.2f}",
            "remaining": f"${self.remaining_budget():.2f}",
            "usage_percent": f"{usage_percent:.1f}%",
            "request_count": self.request_count,
            "remaining_requests": self.remaining_requests()
        }

# ============================================================
# Main Client
# ============================================================

class BrightDataClient:
    """Bright Data API 클라이언트"""

    def __init__(
        self,
        config: BrightDataConfig,
        cache: Optional[Cache] = None,
        cost_tracker: Optional[CostTracker] = None
    ):
        self.config = config
        self.cache = cache or Cache()
        self.cost_tracker = cost_tracker
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()

    async def fetch(
        self,
        url: str,
        use_cache: bool = True,
        render_js: bool = False
    ) -> Optional[str]:
        """
        페이지 가져오기

        Args:
            url: 대상 URL
            use_cache: 캐시 사용 여부
            render_js: JavaScript 렌더링 여부

        Returns:
            HTML 콘텐츠 또는 None
        """
        # 1. 캐시 확인
        if use_cache:
            cached = self.cache.get(url)
            if cached:
                return cached

        # 2. 예산 확인
        if self.cost_tracker and not self.cost_tracker.can_make_request():
            print("🛑 예산 한도 초과")
            return None

        # 3. API 요청
        html = await self._fetch_with_retry(url, render_js)

        # 4. 결과 처리
        if html:
            if use_cache:
                self.cache.set(url, html)
            if self.cost_tracker:
                self.cost_tracker.add_request()

        return html

    async def _fetch_with_retry(
        self,
        url: str,
        render_js: bool = False
    ) -> Optional[str]:
        """재시도 로직이 포함된 요청"""
        delay = self.config.initial_retry_delay

        for attempt in range(self.config.max_retries + 1):
            try:
                html = await self._make_request(url, render_js)
                if html:
                    return html

                if attempt < self.config.max_retries:
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.config.backoff_factor,
                        self.config.max_retry_delay
                    )

            except asyncio.TimeoutError:
                if attempt < self.config.max_retries:
                    print(f"⏱️ 타임아웃 - 재시도 {attempt + 1}")
                    await asyncio.sleep(delay)
                    delay = min(
                        delay * self.config.backoff_factor,
                        self.config.max_retry_delay
                    )

            except Exception as e:
                print(f"🚨 예외: {e}")
                return None

        return None

    async def _make_request(
        self,
        url: str,
        render_js: bool = False
    ) -> Optional[str]:
        """실제 API 요청"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context manager.")

        headers = {
            "Authorization": f"Bearer {self.config.api_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "zone": self.config.zone,
            "url": url,
            "format": "raw"
        }

        if render_js:
            payload["render"] = True

        try:
            async with self.session.post(
                self.config.endpoint,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    error = await response.text()
                    print(f"❌ 에러 {response.status}: {error}")
                    return None

        except asyncio.TimeoutError:
            raise
        except Exception as e:
            print(f"🚨 요청 실패: {e}")
            return None

    async def fetch_multiple(
        self,
        urls: List[str],
        max_concurrent: int = 5,
        use_cache: bool = True
    ) -> Dict[str, Optional[str]]:
        """
        여러 페이지 병렬 가져오기

        Args:
            urls: URL 리스트
            max_concurrent: 최대 동시 요청 수
            use_cache: 캐시 사용 여부

        Returns:
            URL을 키로, HTML을 값으로 하는 딕셔너리
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_limit(url: str):
            async with semaphore:
                html = await self.fetch(url, use_cache=use_cache)
                return (url, html)

        tasks = [fetch_with_limit(url) for url in urls]
        results = await asyncio.gather(*tasks)

        return dict(results)

    def get_cache_stats(self) -> Dict:
        """캐시 통계"""
        return self.cache.stats()

    def get_cost_stats(self) -> Optional[Dict]:
        """비용 통계"""
        return self.cost_tracker.stats() if self.cost_tracker else None

    def clear_cache(self):
        """캐시 초기화"""
        self.cache.cache.clear()
        self.cache.hits = 0
        self.cache.misses = 0

# ============================================================
# Usage Examples
# ============================================================

async def example_basic():
    """기본 사용 예시"""
    config = BrightDataConfig.from_env()

    async with BrightDataClient(config) as client:
        url = "https://www.bloomberg.com/markets/commodities"
        html = await client.fetch(url)

        if html:
            print(f"✅ 성공: {len(html)} bytes")
        else:
            print("❌ 실패")

async def example_with_tracking():
    """비용 추적 예시"""
    config = BrightDataConfig.from_env()
    cache = Cache(ttl_minutes=15)
    tracker = CostTracker(total_budget=5.50)

    async with BrightDataClient(config, cache, tracker) as client:
        urls = [
            "https://www.bloomberg.com/markets/commodities",
            "https://www.bloomberg.com/markets/currencies",
            "https://www.bloomberg.com/markets/stocks"
        ]

        results = await client.fetch_multiple(urls, max_concurrent=3)

        print("\n📊 결과:")
        for url, html in results.items():
            status = "✅" if html else "❌"
            print(f"{status} {url}")

        print(f"\n💰 비용 통계: {client.get_cost_stats()}")
        print(f"💾 캐시 통계: {client.get_cache_stats()}")

if __name__ == "__main__":
    # 환경 변수 설정 필요: BRIGHT_DATA_TOKEN
    asyncio.run(example_with_tracking())
```

---

## 모범 사례

### 1. 환경 변수 관리

#### `.env` 파일
```bash
# Bright Data
BRIGHT_DATA_TOKEN=your_api_token_here
BRIGHT_DATA_ZONE=bloomberg

# Budget
BRIGHT_DATA_BUDGET=5.50
BRIGHT_DATA_COST_PER_REQUEST=0.0015

# Cache
CACHE_TTL_MINUTES=15

# Retry
MAX_RETRIES=3
RETRY_DELAY_SECONDS=2.0
```

#### 환경 변수 로드
```python
from dotenv import load_dotenv
import os

load_dotenv()

config = BrightDataConfig(
    api_token=os.getenv("BRIGHT_DATA_TOKEN"),
    zone=os.getenv("BRIGHT_DATA_ZONE", "bloomberg")
)
```

### 2. 로깅

```python
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bright_data.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('BrightDataClient')

# 사용
logger.info(f"요청 성공: {url}")
logger.warning(f"캐시 미스: {url}")
logger.error(f"API 에러: {error}")
```

### 3. 메트릭 수집

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class RequestMetric:
    """요청 메트릭"""
    url: str
    timestamp: datetime
    duration_ms: float
    status_code: int
    cached: bool
    cost: float

class MetricsCollector:
    """메트릭 수집기"""

    def __init__(self):
        self.metrics: List[RequestMetric] = []

    def record(self, metric: RequestMetric):
        """메트릭 기록"""
        self.metrics.append(metric)

    def average_duration(self) -> float:
        """평균 응답 시간"""
        if not self.metrics:
            return 0.0
        return sum(m.duration_ms for m in self.metrics) / len(self.metrics)

    def cache_hit_rate(self) -> float:
        """캐시 적중률"""
        if not self.metrics:
            return 0.0
        cached = sum(1 for m in self.metrics if m.cached)
        return (cached / len(self.metrics)) * 100

    def total_cost(self) -> float:
        """총 비용"""
        return sum(m.cost for m in self.metrics)
```

### 4. 에러 처리 체크리스트

- [ ] API 토큰 검증
- [ ] 네트워크 타임아웃 처리
- [ ] 재시도 로직 구현
- [ ] 예산 한도 확인
- [ ] 캐시 만료 처리
- [ ] 로그 기록
- [ ] 알림 설정

### 5. 성능 최적화 체크리스트

- [ ] 15분 캐싱 활성화
- [ ] 병렬 요청 제한 (max 5-10)
- [ ] 예산 알림 설정
- [ ] 주기적 캐시 정리
- [ ] 메트릭 수집 및 분석
- [ ] 하이브리드 데이터 소스 활용

---

## 추가 참고 자료

### Bright Data 공식 문서
- [API Documentation](https://docs.brightdata.com/api-reference)
- [Zone Configuration](https://docs.brightdata.com/scraping-automation/web-data-apis/web-scraper-api/overview)
- [Error Codes](https://docs.brightdata.com/scraping-automation/web-data-apis/web-scraper-api/errors)

### Python 비동기 프로그래밍
- [aiohttp Documentation](https://docs.aiohttp.org/)
- [asyncio Official Docs](https://docs.python.org/3/library/asyncio.html)

### 비용 최적화
- Cache-Control 헤더 활용
- ETag를 통한 조건부 요청
- Compression (gzip, brotli)

---

**마지막 업데이트**: 2026-01-07
**작성자**: Bloomberg Data 프로젝트
**버전**: 1.0
