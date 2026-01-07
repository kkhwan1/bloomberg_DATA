# 비용 관리 전략

## 문서 개요

이 문서는 Bloomberg 데이터 수집 시스템의 비용 관리 전략과 구현 방법을 설명합니다.

## 예산 개요

### 총 예산 및 요청 비용

| 항목 | 금액/수량 |
|------|-----------|
| **총 예산** | $5.50 |
| **요청당 비용** | $0.0015 |
| **계산 기준** | $1.50/1,000 requests |
| **사용 가능 요청 수** | ~3,667 requests |

### 비용 계산 공식

```python
# 기본 계산
COST_PER_REQUEST = 0.0015  # $1.50 / 1000
TOTAL_BUDGET = 5.50
MAX_REQUESTS = TOTAL_BUDGET / COST_PER_REQUEST  # 3,666.67

# 일일 비용 계산
def calculate_daily_cost(requests_per_day):
    return requests_per_day * COST_PER_REQUEST

# 예산 지속 기간 계산
def calculate_budget_duration(requests_per_day):
    return MAX_REQUESTS / requests_per_day
```

## 예산 사용 전략

### 전략별 비교표

| 전략 | 수집 간격 | 일일 요청 수 | 일일 비용 | 예산 지속 기간 | 권장 사용 |
|------|-----------|-------------|----------|---------------|----------|
| **고빈도 전체** | 15분 | 96 | $0.144 | ~38일 | 초기 테스트 |
| **중빈도 전체** | 30분 | 48 | $0.072 | ~76일 | 균형잡힌 운영 |
| **Bloomberg 전용** | 30분 | 24-48 | $0.036-0.072 | ~76-152일 | 장기 운영 |
| **선택적 수집** | 1시간 | 24 | $0.036 | ~152일 | 최대 절약 |

### 전략 1: 고빈도 전체 수집 (15분 간격)

**장점:**
- 최신 데이터 보장
- 빠른 변화 감지
- 백테스팅 정확도 향상

**단점:**
- 예산 소진 빠름 (~38일)
- API 호출 부담 증가
- 중복 데이터 가능성

**권장 용도:**
```yaml
use_case: "초기 시스템 검증 및 단기 프로젝트"
duration: "1-2주"
monitoring: "집중적인 데이터 품질 검증"
```

### 전략 2: 중빈도 전체 수집 (30분 간격)

**장점:**
- 비용 효율성 2배 향상
- 충분한 데이터 신선도
- 2개월 이상 운영 가능

**단점:**
- 빠른 가격 변동 누락 가능
- 15분 간격 대비 데이터 포인트 절반

**권장 용도:**
```yaml
use_case: "일반적인 데이터 수집 및 분석"
duration: "2-3개월"
monitoring: "균형잡힌 운영"
```

### 전략 3: Bloomberg 전용 수집 (선택적)

**장점:**
- 예산 지속 기간 최대 (~152일)
- 유료 API의 가치 극대화
- 무료 API로 주식/FX 보완

**단점:**
- 통합 데이터 소스 관리 필요
- 복잡도 증가

**권장 용도:**
```yaml
use_case: "장기 운영 및 특수 자산 집중"
assets:
  - bonds (채권)
  - exotic_commodities (희귀 원자재)
  - alternative_investments (대체투자)
free_sources:
  - stocks: "yfinance, Alpha Vantage"
  - forex: "ECB, FRED"
  - major_commodities: "EIA, USDA"
```

### 전략 4: 선택적 수집 (1시간 간격)

**장점:**
- 최대 예산 효율 (~152일)
- 장기 트렌드 분석 적합
- 서버 부하 최소화

**단점:**
- 실시간성 부족
- 단기 거래 전략 부적합

**권장 용도:**
```yaml
use_case: "장기 트렌드 분석 및 연구"
duration: "5개월+"
monitoring: "비용 최적화 중심"
```

## CostTracker 구현

### Singleton 패턴 설계

```python
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

class CostTracker:
    """
    Thread-safe singleton 비용 추적 시스템

    Features:
    - 스레드 안전성 보장
    - 영구 저장 (JSON)
    - 예산 알림 시스템
    - 실시간 비용 모니터링
    """

    _instance = None
    _lock = threading.Lock()

    # 설정
    COST_PER_REQUEST = 0.0015
    TOTAL_BUDGET = 5.50
    TRACKING_FILE = Path("logs/cost_tracking.json")

    # 알림 임계값
    ALERT_THRESHOLDS = {
        'warning': 0.50,   # 50% 사용
        'critical': 0.80,  # 80% 사용
        'danger': 0.95     # 95% 사용
    }

    def __new__(cls):
        """Singleton 인스턴스 생성"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """초기화 (한 번만 실행)"""
        if self._initialized:
            return

        self._initialized = True
        self._lock = threading.Lock()

        # 추적 데이터 구조
        self.data = {
            'total_requests': 0,
            'total_cost': 0.0,
            'remaining_budget': self.TOTAL_BUDGET,
            'requests_by_date': {},
            'requests_by_asset': {},
            'last_alert_level': None,
            'created_at': datetime.now().isoformat(),
            'last_updated': None
        }

        # 저장소 초기화
        self._ensure_tracking_file()
        self._load_state()

    def _ensure_tracking_file(self):
        """추적 파일 디렉토리 생성"""
        self.TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)

        if not self.TRACKING_FILE.exists():
            self._save_state()

    def _load_state(self):
        """저장된 상태 로드"""
        try:
            if self.TRACKING_FILE.exists():
                with open(self.TRACKING_FILE, 'r') as f:
                    loaded_data = json.load(f)
                    self.data.update(loaded_data)
        except Exception as e:
            print(f"⚠️ 비용 추적 상태 로드 실패: {e}")

    def _save_state(self):
        """현재 상태 저장"""
        try:
            with open(self.TRACKING_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"⚠️ 비용 추적 상태 저장 실패: {e}")

    def can_make_request(self) -> bool:
        """
        요청 가능 여부 확인

        Returns:
            bool: 예산 내에서 요청 가능한 경우 True
        """
        with self._lock:
            return self.data['remaining_budget'] >= self.COST_PER_REQUEST

    def record_request(self, asset_class: str, symbol: str,
                      success: bool = True) -> Dict:
        """
        요청 기록 및 비용 차감

        Args:
            asset_class: 자산 클래스 (stocks, bonds 등)
            symbol: 심볼명
            success: 요청 성공 여부

        Returns:
            dict: 업데이트된 비용 정보
        """
        with self._lock:
            if not self.can_make_request():
                return {
                    'success': False,
                    'error': 'Budget exhausted',
                    'remaining_budget': self.data['remaining_budget']
                }

            # 비용 차감
            if success:
                self.data['total_requests'] += 1
                self.data['total_cost'] += self.COST_PER_REQUEST
                self.data['remaining_budget'] -= self.COST_PER_REQUEST

            # 날짜별 기록
            today = datetime.now().date().isoformat()
            if today not in self.data['requests_by_date']:
                self.data['requests_by_date'][today] = {
                    'count': 0,
                    'cost': 0.0
                }

            if success:
                self.data['requests_by_date'][today]['count'] += 1
                self.data['requests_by_date'][today]['cost'] += self.COST_PER_REQUEST

            # 자산별 기록
            asset_key = f"{asset_class}:{symbol}"
            if asset_key not in self.data['requests_by_asset']:
                self.data['requests_by_asset'][asset_key] = {
                    'count': 0,
                    'cost': 0.0,
                    'first_request': datetime.now().isoformat()
                }

            if success:
                self.data['requests_by_asset'][asset_key]['count'] += 1
                self.data['requests_by_asset'][asset_key]['cost'] += self.COST_PER_REQUEST
                self.data['requests_by_asset'][asset_key]['last_request'] = datetime.now().isoformat()

            # 타임스탬프 업데이트
            self.data['last_updated'] = datetime.now().isoformat()

            # 알림 확인
            alert = self._check_alert_threshold()

            # 상태 저장
            self._save_state()

            return {
                'success': True,
                'total_requests': self.data['total_requests'],
                'total_cost': round(self.data['total_cost'], 4),
                'remaining_budget': round(self.data['remaining_budget'], 4),
                'budget_used_percent': round(
                    (self.data['total_cost'] / self.TOTAL_BUDGET) * 100, 2
                ),
                'alert': alert
            }

    def _check_alert_threshold(self) -> Optional[Dict]:
        """
        예산 사용 알림 확인

        Returns:
            dict: 알림 정보 또는 None
        """
        usage_percent = self.data['total_cost'] / self.TOTAL_BUDGET

        for level, threshold in sorted(
            self.ALERT_THRESHOLDS.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if usage_percent >= threshold:
                if self.data['last_alert_level'] != level:
                    self.data['last_alert_level'] = level
                    return {
                        'level': level,
                        'threshold': threshold,
                        'current_usage': round(usage_percent * 100, 2),
                        'remaining_budget': round(self.data['remaining_budget'], 4),
                        'estimated_requests_left': int(
                            self.data['remaining_budget'] / self.COST_PER_REQUEST
                        )
                    }

        return None

    def get_statistics(self) -> Dict:
        """
        비용 통계 조회

        Returns:
            dict: 상세 비용 통계
        """
        with self._lock:
            return {
                'budget': {
                    'total': self.TOTAL_BUDGET,
                    'used': round(self.data['total_cost'], 4),
                    'remaining': round(self.data['remaining_budget'], 4),
                    'usage_percent': round(
                        (self.data['total_cost'] / self.TOTAL_BUDGET) * 100, 2
                    )
                },
                'requests': {
                    'total': self.data['total_requests'],
                    'estimated_remaining': int(
                        self.data['remaining_budget'] / self.COST_PER_REQUEST
                    ),
                    'by_date': self.data['requests_by_date'],
                    'by_asset': self.data['requests_by_asset']
                },
                'projection': self._calculate_projection(),
                'metadata': {
                    'created_at': self.data['created_at'],
                    'last_updated': self.data['last_updated']
                }
            }

    def _calculate_projection(self) -> Dict:
        """예산 소진 예측"""
        if self.data['total_requests'] == 0:
            return {'days_remaining': 'N/A'}

        # 최근 7일 평균 사용량
        recent_dates = sorted(self.data['requests_by_date'].keys())[-7:]
        if not recent_dates:
            return {'days_remaining': 'N/A'}

        avg_daily_requests = sum(
            self.data['requests_by_date'][date]['count']
            for date in recent_dates
        ) / len(recent_dates)

        if avg_daily_requests == 0:
            return {'days_remaining': 'N/A'}

        avg_daily_cost = avg_daily_requests * self.COST_PER_REQUEST
        days_remaining = self.data['remaining_budget'] / avg_daily_cost

        return {
            'avg_daily_requests': round(avg_daily_requests, 2),
            'avg_daily_cost': round(avg_daily_cost, 4),
            'estimated_days_remaining': round(days_remaining, 1),
            'projected_exhaustion_date': (
                datetime.now() + timedelta(days=days_remaining)
            ).date().isoformat()
        }

    def reset(self, confirm: bool = False):
        """
        비용 추적 리셋 (주의: 모든 데이터 삭제)

        Args:
            confirm: 안전장치, True로 설정 필요
        """
        if not confirm:
            raise ValueError("리셋을 위해서는 confirm=True 필요")

        with self._lock:
            self.data = {
                'total_requests': 0,
                'total_cost': 0.0,
                'remaining_budget': self.TOTAL_BUDGET,
                'requests_by_date': {},
                'requests_by_asset': {},
                'last_alert_level': None,
                'created_at': datetime.now().isoformat(),
                'last_updated': None
            }
            self._save_state()
```

### 사용 예제

```python
from datetime import timedelta

# Singleton 인스턴스 사용
tracker = CostTracker()

# 요청 전 확인
if tracker.can_make_request():
    # Bloomberg API 호출
    result = tracker.record_request(
        asset_class='bonds',
        symbol='US10Y',
        success=True
    )

    print(f"✅ 요청 성공")
    print(f"💰 남은 예산: ${result['remaining_budget']}")
    print(f"📊 사용률: {result['budget_used_percent']}%")

    # 알림 확인
    if result.get('alert'):
        alert = result['alert']
        print(f"⚠️ {alert['level'].upper()} 알림!")
        print(f"📈 현재 사용: {alert['current_usage']}%")
        print(f"🔢 남은 요청 수: {alert['estimated_requests_left']}")
else:
    print("❌ 예산 소진")

# 통계 조회
stats = tracker.get_statistics()
print(f"\n📊 비용 통계:")
print(f"예산 사용: ${stats['budget']['used']} / ${stats['budget']['total']}")
print(f"총 요청 수: {stats['requests']['total']}")
print(f"예상 잔여 일수: {stats['projection'].get('estimated_days_remaining', 'N/A')}")
```

## CacheManager 구현

### SQLite 기반 캐시 시스템

```python
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

class CacheManager:
    """
    SQLite 기반 데이터 캐시 관리 시스템

    Features:
    - 15분 TTL (Time To Live)
    - 자동 만료 데이터 정리
    - 효율적인 조회
    - 스레드 안전성
    """

    DB_PATH = Path("data/cache.db")
    DEFAULT_TTL_MINUTES = 15

    def __init__(self, ttl_minutes: int = DEFAULT_TTL_MINUTES):
        """
        초기화

        Args:
            ttl_minutes: 캐시 유효 시간 (분)
        """
        self.ttl_minutes = ttl_minutes
        self._ensure_database()

    def _ensure_database(self):
        """데이터베이스 및 테이블 생성"""
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    cache_key TEXT PRIMARY KEY,
                    asset_class TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    last_accessed TEXT
                )
            """)

            # 인덱스 생성 (조회 성능 향상)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON cache(expires_at)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_asset_symbol
                ON cache(asset_class, symbol)
            """)

            conn.commit()

    def _generate_cache_key(self, asset_class: str, symbol: str) -> str:
        """
        캐시 키 생성

        Args:
            asset_class: 자산 클래스
            symbol: 심볼명

        Returns:
            str: 캐시 키
        """
        return f"{asset_class}:{symbol}"

    def get(self, asset_class: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        캐시 조회

        Args:
            asset_class: 자산 클래스
            symbol: 심볼명

        Returns:
            dict: 캐시된 데이터 또는 None
        """
        cache_key = self._generate_cache_key(asset_class, symbol)
        now = datetime.now()

        with sqlite3.connect(self.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT data, expires_at, hit_count
                FROM cache
                WHERE cache_key = ?
            """, (cache_key,))

            row = cursor.fetchone()

            if row is None:
                return None

            # 만료 확인
            expires_at = datetime.fromisoformat(row['expires_at'])
            if now > expires_at:
                # 만료된 캐시 삭제
                cursor.execute("""
                    DELETE FROM cache WHERE cache_key = ?
                """, (cache_key,))
                conn.commit()
                return None

            # 히트 카운트 및 접근 시간 업데이트
            cursor.execute("""
                UPDATE cache
                SET hit_count = hit_count + 1,
                    last_accessed = ?
                WHERE cache_key = ?
            """, (now.isoformat(), cache_key))
            conn.commit()

            # 데이터 반환
            return json.loads(row['data'])

    def set(self, asset_class: str, symbol: str, data: Dict[str, Any]) -> bool:
        """
        캐시 저장

        Args:
            asset_class: 자산 클래스
            symbol: 심볼명
            data: 저장할 데이터

        Returns:
            bool: 저장 성공 여부
        """
        cache_key = self._generate_cache_key(asset_class, symbol)
        now = datetime.now()
        expires_at = now + timedelta(minutes=self.ttl_minutes)

        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache
                    (cache_key, asset_class, symbol, data, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    cache_key,
                    asset_class,
                    symbol,
                    json.dumps(data),
                    now.isoformat(),
                    expires_at.isoformat()
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"⚠️ 캐시 저장 실패: {e}")
            return False

    def clear_expired(self) -> int:
        """
        만료된 캐시 삭제

        Returns:
            int: 삭제된 레코드 수
        """
        now = datetime.now()

        with sqlite3.connect(self.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM cache WHERE expires_at < ?
            """, (now.isoformat(),))
            deleted_count = cursor.rowcount
            conn.commit()

        return deleted_count

    def get_statistics(self) -> Dict:
        """
        캐시 통계 조회

        Returns:
            dict: 캐시 통계
        """
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 전체 통계
            cursor.execute("""
                SELECT
                    COUNT(*) as total_entries,
                    SUM(hit_count) as total_hits,
                    AVG(hit_count) as avg_hits_per_entry
                FROM cache
            """)
            overall = cursor.fetchone()

            # 자산 클래스별 통계
            cursor.execute("""
                SELECT
                    asset_class,
                    COUNT(*) as entry_count,
                    SUM(hit_count) as total_hits
                FROM cache
                GROUP BY asset_class
                ORDER BY total_hits DESC
            """)
            by_asset = [dict(row) for row in cursor.fetchall()]

            # 상위 심볼
            cursor.execute("""
                SELECT
                    asset_class,
                    symbol,
                    hit_count,
                    last_accessed
                FROM cache
                ORDER BY hit_count DESC
                LIMIT 10
            """)
            top_symbols = [dict(row) for row in cursor.fetchall()]

            return {
                'overall': dict(overall),
                'by_asset_class': by_asset,
                'top_symbols': top_symbols
            }

    def clear_all(self, confirm: bool = False):
        """
        모든 캐시 삭제

        Args:
            confirm: 안전장치
        """
        if not confirm:
            raise ValueError("전체 삭제를 위해서는 confirm=True 필요")

        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()
```

### 사용 예제

```python
# CacheManager 초기화
cache = CacheManager(ttl_minutes=15)

# 데이터 조회 전 캐시 확인
asset_class = 'bonds'
symbol = 'US10Y'

cached_data = cache.get(asset_class, symbol)

if cached_data:
    print(f"✅ 캐시 히트: {symbol}")
    print(f"💰 비용 절감: $0.0015")
    return cached_data
else:
    print(f"❌ 캐시 미스: {symbol}")

    # API 호출 (비용 발생)
    if tracker.can_make_request():
        data = fetch_from_bloomberg(symbol)

        # 비용 기록
        tracker.record_request(asset_class, symbol, success=True)

        # 캐시 저장
        cache.set(asset_class, symbol, data)

        return data

# 정기 정리 (크론잡 또는 스케줄러에서 실행)
expired_count = cache.clear_expired()
print(f"🗑️ 만료된 캐시 {expired_count}개 삭제")

# 통계 조회
stats = cache.get_statistics()
print(f"📊 캐시 통계:")
print(f"총 엔트리: {stats['overall']['total_entries']}")
print(f"총 히트: {stats['overall']['total_hits']}")
print(f"절감 비용: ${stats['overall']['total_hits'] * 0.0015:.4f}")
```

## 비용 최적화 모범 사례

### Bright Data 유료 API 사용 기준

#### 사용해야 할 경우 (Worth Paying)

| 자산 클래스 | 이유 | 대체 가능성 |
|------------|------|------------|
| **채권 (Bonds)** | 무료 소스 부족, Bloomberg 독점 데이터 | ❌ 낮음 |
| **희귀 원자재** | 니켈, 팔라듐 등 특수 상품 | ❌ 낮음 |
| **대체투자** | 부동산 지수, 인프라 펀드 | ❌ 낮음 |
| **신흥시장 채권** | EM 국채, 회사채 | ❌ 낮음 |
| **구조화 상품** | MBS, ABS, CDO | ❌ 없음 |

#### 무료로 대체 가능한 경우 (Free Alternatives Available)

| 자산 클래스 | 무료 소스 | API |
|------------|----------|-----|
| **주식 (Stocks)** | Yahoo Finance, Alpha Vantage | yfinance, alpha_vantage |
| **주요 FX** | ECB, Federal Reserve | ECB API, FRED |
| **금/은/구리** | World Bank, USGS | World Bank API |
| **원유/천연가스** | EIA (미국 에너지정보청) | EIA API |
| **농산물** | USDA, FAO | USDA API |

### 비용 절감 전략

#### 1. 하이브리드 접근법

```python
class DataFetcher:
    """비용 최적화 데이터 수집기"""

    def __init__(self):
        self.cache = CacheManager()
        self.tracker = CostTracker()

        # 무료/유료 소스 매핑
        self.source_strategy = {
            'stocks': 'free',       # yfinance
            'forex': 'free',        # ECB/FRED
            'commodities': {
                'gold': 'free',     # World Bank
                'silver': 'free',
                'copper': 'free',
                'oil': 'free',      # EIA
                'nickel': 'paid',   # Bloomberg
                'palladium': 'paid'
            },
            'bonds': 'paid',        # Bloomberg 전용
            'alternatives': 'paid'
        }

    def fetch_data(self, asset_class: str, symbol: str):
        """스마트 데이터 수집"""

        # 1. 캐시 확인
        cached = self.cache.get(asset_class, symbol)
        if cached:
            return {'source': 'cache', 'data': cached, 'cost': 0}

        # 2. 소스 전략 결정
        strategy = self._get_source_strategy(asset_class, symbol)

        if strategy == 'free':
            # 무료 API 사용
            data = self._fetch_free_source(asset_class, symbol)
            self.cache.set(asset_class, symbol, data)
            return {'source': 'free', 'data': data, 'cost': 0}
        else:
            # 유료 API 사용 (예산 확인)
            if not self.tracker.can_make_request():
                raise BudgetExhaustedError()

            data = self._fetch_bloomberg(symbol)
            self.tracker.record_request(asset_class, symbol, success=True)
            self.cache.set(asset_class, symbol, data)

            return {'source': 'bloomberg', 'data': data, 'cost': 0.0015}

    def _get_source_strategy(self, asset_class: str, symbol: str) -> str:
        """소스 전략 결정"""
        strategy = self.source_strategy.get(asset_class)

        if isinstance(strategy, dict):
            # 원자재는 심볼별로 구분
            commodity_type = self._identify_commodity(symbol)
            return strategy.get(commodity_type, 'paid')

        return strategy or 'paid'
```

#### 2. 우선순위 기반 수집

```python
# 우선순위 설정
PRIORITY_CONFIG = {
    'critical': {
        'assets': ['bonds:US10Y', 'bonds:US2Y', 'forex:EURUSD'],
        'interval_minutes': 15,
        'use_paid_api': True
    },
    'high': {
        'assets': ['commodities:GOLD', 'stocks:SPY'],
        'interval_minutes': 30,
        'use_paid_api': False  # 무료 소스 우선
    },
    'normal': {
        'assets': ['*'],  # 나머지 전부
        'interval_minutes': 60,
        'use_paid_api': False
    }
}

def schedule_collection():
    """우선순위 기반 스케줄링"""
    for priority, config in PRIORITY_CONFIG.items():
        schedule.every(config['interval_minutes']).minutes.do(
            collect_with_priority,
            assets=config['assets'],
            use_paid=config['use_paid_api']
        )
```

#### 3. 시장 시간 기반 수집

```python
from datetime import time

def is_market_hours(asset_class: str) -> bool:
    """시장 거래 시간 확인"""
    now = datetime.now()
    current_time = now.time()

    market_hours = {
        'stocks': {
            'start': time(9, 30),   # 09:30
            'end': time(16, 0)      # 16:00
        },
        'forex': {
            'start': time(0, 0),    # 24시간
            'end': time(23, 59)
        },
        'bonds': {
            'start': time(8, 0),
            'end': time(17, 0)
        }
    }

    hours = market_hours.get(asset_class)
    if not hours:
        return True  # 기본값: 항상 수집

    # 주말 제외
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    return hours['start'] <= current_time <= hours['end']

# 스케줄러에 적용
def smart_collect(asset_class: str, symbol: str):
    """시장 시간 고려 수집"""
    if not is_market_hours(asset_class):
        print(f"⏰ 시장 폐장: {asset_class} 수집 스킵")
        return None

    return fetcher.fetch_data(asset_class, symbol)
```

#### 4. 배치 처리 최적화

```python
def batch_collect_with_budget_check(assets: list) -> dict:
    """예산 확인 후 배치 수집"""

    tracker = CostTracker()
    results = {
        'collected': [],
        'skipped': [],
        'failed': []
    }

    # 예상 비용 계산
    paid_assets = [a for a in assets if requires_paid_api(a)]
    estimated_cost = len(paid_assets) * CostTracker.COST_PER_REQUEST

    if tracker.data['remaining_budget'] < estimated_cost:
        print(f"⚠️ 예산 부족: 필요 ${estimated_cost:.4f}, 잔액 ${tracker.data['remaining_budget']:.4f}")

        # 우선순위 높은 자산만 수집
        paid_assets = filter_by_priority(paid_assets, limit=10)

    for asset in assets:
        try:
            if requires_paid_api(asset):
                if not tracker.can_make_request():
                    results['skipped'].append(asset)
                    continue

            data = fetcher.fetch_data(asset['class'], asset['symbol'])
            results['collected'].append(asset)

        except Exception as e:
            results['failed'].append({'asset': asset, 'error': str(e)})

    return results
```

### 예산 알림 시스템

```python
def setup_budget_alerts():
    """예산 알림 설정"""

    tracker = CostTracker()

    # 이메일/Slack 통합
    def send_alert(alert_info: dict):
        level = alert_info['level']

        message = f"""
        🚨 예산 알림: {level.upper()}

        현재 사용률: {alert_info['current_usage']}%
        남은 예산: ${alert_info['remaining_budget']}
        예상 잔여 요청: {alert_info['estimated_requests_left']}

        권장 조치:
        """

        if level == 'warning':
            message += "- 수집 간격 검토 (30분 → 1시간)"
        elif level == 'critical':
            message += "- 긴급: Bloomberg 전용 자산만 수집"
        elif level == 'danger':
            message += "- 위험: 수집 중단 고려"

        # 알림 전송 (Slack, Email 등)
        send_notification(message)

    # 정기 체크
    schedule.every(1).hour.do(check_and_alert)
```

## 모니터링 대시보드

### 비용 추적 리포트

```python
def generate_cost_report() -> str:
    """비용 리포트 생성"""

    tracker = CostTracker()
    cache = CacheManager()

    stats = tracker.get_statistics()
    cache_stats = cache.get_statistics()

    # 비용 절감액 계산
    cache_hits = cache_stats['overall']['total_hits']
    savings = cache_hits * CostTracker.COST_PER_REQUEST

    report = f"""
    ╔══════════════════════════════════════════════╗
    ║        📊 Bloomberg 비용 추적 리포트         ║
    ╚══════════════════════════════════════════════╝

    💰 예산 현황
    ├─ 총 예산: ${CostTracker.TOTAL_BUDGET}
    ├─ 사용 금액: ${stats['budget']['used']}
    ├─ 남은 예산: ${stats['budget']['remaining']}
    └─ 사용률: {stats['budget']['usage_percent']}%

    📈 요청 통계
    ├─ 총 요청 수: {stats['requests']['total']}
    ├─ 캐시 히트: {cache_hits}
    ├─ 실제 API 호출: {stats['requests']['total']}
    └─ 예상 잔여 요청: {stats['requests']['estimated_remaining']}

    💡 비용 절감
    ├─ 캐시 절감액: ${savings:.4f}
    └─ 절감률: {(cache_hits / (stats['requests']['total'] + cache_hits) * 100):.1f}%

    🎯 예측
    ├─ 일평균 요청: {stats['projection'].get('avg_daily_requests', 'N/A')}
    ├─ 일평균 비용: ${stats['projection'].get('avg_daily_cost', 'N/A')}
    ├─ 예상 잔여 기간: {stats['projection'].get('estimated_days_remaining', 'N/A')}일
    └─ 예산 소진 예상일: {stats['projection'].get('projected_exhaustion_date', 'N/A')}

    📊 자산별 사용 현황
    """

    # 자산별 통계
    for asset_key, asset_data in list(stats['requests']['by_asset'].items())[:5]:
        report += f"\n    {asset_key}: {asset_data['count']}회 (${asset_data['cost']:.4f})"

    return report

# 일일 리포트 스케줄링
schedule.every().day.at("09:00").do(
    lambda: print(generate_cost_report())
)
```

## 요약

### 핵심 포인트

1. **예산 관리**: CostTracker로 실시간 비용 추적
2. **캐싱**: 15분 TTL로 중복 요청 방지
3. **하이브리드**: 무료/유료 API 전략적 사용
4. **우선순위**: 중요 자산에 예산 집중
5. **모니터링**: 알림 시스템으로 예산 초과 방지

### 권장 운영 방식

```yaml
phase_1_testing:
  duration: "1-2주"
  strategy: "30분 간격, 전체 자산"
  purpose: "시스템 검증"

phase_2_optimization:
  duration: "1개월"
  strategy: "Bloomberg 전용 + 무료 API"
  purpose: "비용 최적화"

phase_3_production:
  duration: "장기"
  strategy: "우선순위 기반 수집"
  purpose: "효율적 운영"
```

### 비용 절감 체크리스트

- [ ] CostTracker 설정 완료
- [ ] CacheManager 활성화
- [ ] 무료 API 통합 (yfinance, ECB 등)
- [ ] 우선순위 설정
- [ ] 시장 시간 필터링
- [ ] 예산 알림 설정
- [ ] 일일 리포트 스케줄링
- [ ] 주간 예산 검토

---

**문서 버전**: 1.0
**최종 수정**: 2026-01-07
**다음 문서**: [05_api_integration.md](./05_api_integration.md)
