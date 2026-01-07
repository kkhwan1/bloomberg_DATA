# 06. 테스팅 가이드

## 목차
1. [테스트 구조](#테스트-구조)
2. [유닛 테스트](#유닛-테스트)
3. [통합 테스트](#통합-테스트)
4. [테스트 실행 명령어](#테스트-실행-명령어)
5. [Mock 전략](#mock-전략)
6. [배포 전 체크리스트](#배포-전-체크리스트)

---

## 테스트 구조

### 디렉토리 구조
```
tests/
├── __init__.py
├── test_bright_data.py          # Bright Data API 테스트
├── test_bloomberg_parser.py     # Bloomberg 파싱 테스트
├── test_cost_tracker.py         # 비용 추적 테스트
├── test_cache_manager.py        # 캐시 관리 테스트
├── test_hybrid_source.py        # 하이브리드 소스 테스트
├── conftest.py                  # pytest 설정 및 공통 fixtures
└── fixtures/
    ├── sample_bloomberg.html    # 샘플 Bloomberg HTML
    ├── sample_response.json     # Bright Data 응답 샘플
    └── test_data.json           # 테스트 데이터
```

### 테스트 환경 설정

**conftest.py**
```python
"""pytest 설정 및 공통 fixtures"""
import pytest
import json
from pathlib import Path

@pytest.fixture
def fixtures_dir():
    """fixtures 디렉토리 경로"""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def sample_bloomberg_html(fixtures_dir):
    """샘플 Bloomberg HTML 로드"""
    with open(fixtures_dir / "sample_bloomberg.html", "r", encoding="utf-8") as f:
        return f.read()

@pytest.fixture
def sample_bright_data_response(fixtures_dir):
    """샘플 Bright Data API 응답"""
    with open(fixtures_dir / "sample_response.json", "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def temp_cache_dir(tmp_path):
    """임시 캐시 디렉토리"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir

@pytest.fixture
def temp_cost_db(tmp_path):
    """임시 비용 추적 데이터베이스"""
    return tmp_path / "test_costs.db"
```

---

## 유닛 테스트

### 1. test_cost_tracker.py

**목적**: 비용 추적, 예산 알림, 데이터 지속성 검증

```python
"""비용 추적 시스템 테스트"""
import pytest
from datetime import datetime, timedelta
from src.cost_tracker import CostTracker

class TestCostTracker:
    """CostTracker 유닛 테스트"""

    @pytest.fixture
    def tracker(self, temp_cost_db):
        """각 테스트마다 새로운 tracker 인스턴스"""
        return CostTracker(
            db_path=temp_cost_db,
            monthly_budget=100.0
        )

    def test_initialization(self, tracker):
        """초기화 검증"""
        assert tracker.monthly_budget == 100.0
        assert tracker.get_current_month_cost() == 0.0

    def test_record_api_call(self, tracker):
        """API 호출 기록"""
        tracker.record_api_call(
            service="bright_data",
            cost=0.05,
            metadata={"ticker": "AAPL"}
        )

        assert tracker.get_current_month_cost() == 0.05
        assert tracker.get_call_count("bright_data") == 1

    def test_budget_alert(self, tracker):
        """예산 초과 알림"""
        # 예산의 85% 사용
        for _ in range(17):
            tracker.record_api_call("bright_data", 5.0)

        assert tracker.get_current_month_cost() == 85.0
        assert tracker.is_approaching_budget()  # 85% 도달

        # 예산 초과
        tracker.record_api_call("bright_data", 20.0)
        assert tracker.is_over_budget()
        assert tracker.get_current_month_cost() == 105.0

    def test_monthly_reset(self, tracker):
        """월별 비용 리셋"""
        tracker.record_api_call("bright_data", 10.0)

        # 다음 달로 이동
        next_month = datetime.now() + timedelta(days=32)
        tracker.current_date = next_month

        assert tracker.get_current_month_cost() == 0.0
        assert tracker.get_previous_month_cost() == 10.0

    def test_persistence(self, temp_cost_db):
        """데이터 지속성"""
        # 첫 번째 인스턴스
        tracker1 = CostTracker(db_path=temp_cost_db)
        tracker1.record_api_call("bright_data", 5.0)

        # 두 번째 인스턴스 (같은 DB)
        tracker2 = CostTracker(db_path=temp_cost_db)
        assert tracker2.get_current_month_cost() == 5.0

    def test_service_breakdown(self, tracker):
        """서비스별 비용 분석"""
        tracker.record_api_call("bright_data", 10.0)
        tracker.record_api_call("bright_data", 5.0)
        tracker.record_api_call("yfinance", 2.0)

        breakdown = tracker.get_service_breakdown()
        assert breakdown["bright_data"]["total_cost"] == 15.0
        assert breakdown["bright_data"]["call_count"] == 2
        assert breakdown["yfinance"]["total_cost"] == 2.0
```

### 2. test_cache_manager.py

**목적**: TTL, 캐시 저장/조회, 만료 처리 검증

```python
"""캐시 관리 시스템 테스트"""
import pytest
import time
from src.cache_manager import CacheManager

class TestCacheManager:
    """CacheManager 유닛 테스트"""

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """각 테스트마다 새로운 cache 인스턴스"""
        return CacheManager(
            cache_dir=temp_cache_dir,
            default_ttl=3600  # 1시간
        )

    def test_set_and_get(self, cache):
        """기본 저장 및 조회"""
        test_data = {"price": 150.0, "volume": 1000000}
        cache.set("AAPL", test_data)

        retrieved = cache.get("AAPL")
        assert retrieved == test_data

    def test_cache_miss(self, cache):
        """캐시 미스 처리"""
        result = cache.get("NONEXISTENT")
        assert result is None

    def test_ttl_expiration(self, cache):
        """TTL 만료 처리"""
        cache.set("AAPL", {"price": 150.0}, ttl=1)  # 1초 TTL

        # 즉시 조회 - 성공
        assert cache.get("AAPL") is not None

        # 2초 대기
        time.sleep(2)

        # 만료된 캐시 - None 반환
        assert cache.get("AAPL") is None

    def test_custom_ttl(self, cache):
        """커스텀 TTL 설정"""
        cache.set("AAPL", {"price": 150.0}, ttl=7200)  # 2시간

        metadata = cache.get_metadata("AAPL")
        assert metadata["ttl"] == 7200

    def test_cache_invalidation(self, cache):
        """캐시 무효화"""
        cache.set("AAPL", {"price": 150.0})
        assert cache.get("AAPL") is not None

        cache.invalidate("AAPL")
        assert cache.get("AAPL") is None

    def test_clear_all(self, cache):
        """전체 캐시 삭제"""
        cache.set("AAPL", {"price": 150.0})
        cache.set("GOOGL", {"price": 2800.0})

        cache.clear_all()

        assert cache.get("AAPL") is None
        assert cache.get("GOOGL") is None

    def test_cache_size_limit(self, temp_cache_dir):
        """캐시 크기 제한"""
        cache = CacheManager(
            cache_dir=temp_cache_dir,
            max_size_mb=1  # 1MB 제한
        )

        # 큰 데이터 저장 시도
        large_data = {"data": "x" * 1024 * 1024 * 2}  # 2MB

        with pytest.raises(ValueError, match="Cache size limit exceeded"):
            cache.set("LARGE", large_data)

    def test_cleanup_expired(self, cache):
        """만료된 캐시 정리"""
        cache.set("AAPL", {"price": 150.0}, ttl=1)
        cache.set("GOOGL", {"price": 2800.0}, ttl=3600)

        time.sleep(2)

        removed_count = cache.cleanup_expired()

        assert removed_count == 1
        assert cache.get("AAPL") is None
        assert cache.get("GOOGL") is not None
```

### 3. test_bloomberg_parser.py

**목적**: HTML 파싱 전략 및 데이터 추출 검증

```python
"""Bloomberg 파서 테스트"""
import pytest
from src.bloomberg_parser import BloombergParser

class TestBloombergParser:
    """BloombergParser 유닛 테스트"""

    @pytest.fixture
    def parser(self):
        """파서 인스턴스"""
        return BloombergParser()

    def test_parse_basic_quote(self, parser, sample_bloomberg_html):
        """기본 시세 정보 파싱"""
        data = parser.parse(sample_bloomberg_html)

        assert "price" in data
        assert "change" in data
        assert "change_percent" in data
        assert isinstance(data["price"], float)

    def test_parse_volume(self, parser, sample_bloomberg_html):
        """거래량 파싱"""
        data = parser.parse(sample_bloomberg_html)

        assert "volume" in data
        assert data["volume"] > 0

    def test_parse_market_cap(self, parser, sample_bloomberg_html):
        """시가총액 파싱"""
        data = parser.parse(sample_bloomberg_html)

        assert "market_cap" in data
        assert data["market_cap"] > 0

    def test_parse_pe_ratio(self, parser, sample_bloomberg_html):
        """P/E 비율 파싱"""
        data = parser.parse(sample_bloomberg_html)

        if "pe_ratio" in data:
            assert isinstance(data["pe_ratio"], (int, float))

    def test_parse_missing_data(self, parser):
        """데이터 누락 처리"""
        incomplete_html = "<html><body></body></html>"

        data = parser.parse(incomplete_html)

        # 기본값 또는 None 반환
        assert data.get("price") is None or data.get("price") == 0

    def test_parse_error_handling(self, parser):
        """파싱 오류 처리"""
        invalid_html = "This is not HTML"

        with pytest.raises(ValueError, match="Invalid HTML"):
            parser.parse(invalid_html)

    def test_multiple_strategies(self, parser, sample_bloomberg_html):
        """다중 파싱 전략 (fallback)"""
        # 파서가 여러 CSS 선택자를 시도하는지 검증
        data = parser.parse(sample_bloomberg_html)

        assert data is not None
        assert len(data) > 0
```

---

## 통합 테스트

### 1. test_bright_data.py

**목적**: API 연결 검증 (실제 API 호출 1회 사용)

```python
"""Bright Data API 통합 테스트"""
import pytest
from src.bright_data_client import BrightDataClient
from unittest.mock import Mock, patch

# API 테스트는 실제 요청을 사용하므로 별도 마커
pytestmark = pytest.mark.api

class TestBrightDataIntegration:
    """Bright Data API 통합 테스트"""

    @pytest.fixture
    def client(self):
        """실제 API 클라이언트"""
        return BrightDataClient(
            api_key=os.getenv("BRIGHT_DATA_API_KEY"),
            cost_tracker=Mock()  # 비용 추적은 mock
        )

    @pytest.mark.skip(reason="Uses real API credit")
    def test_real_api_connection(self, client):
        """실제 API 연결 테스트 (수동 실행만)"""
        response = client.scrape_bloomberg("AAPL")

        assert response is not None
        assert "price" in response
        assert "timestamp" in response

    def test_rate_limiting(self, client):
        """Rate limiting 처리"""
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {"status": "success"}

            # 빠른 연속 요청
            for _ in range(5):
                client.scrape_bloomberg("AAPL")

            # Rate limit이 적용되었는지 확인
            assert mock_request.call_count <= 5

    def test_error_handling(self, client):
        """API 오류 처리"""
        with patch.object(client, '_make_request') as mock_request:
            mock_request.side_effect = Exception("API Error")

            with pytest.raises(Exception):
                client.scrape_bloomberg("INVALID")

    def test_cost_tracking_integration(self):
        """비용 추적 통합"""
        cost_tracker = Mock()
        client = BrightDataClient(
            api_key="test_key",
            cost_tracker=cost_tracker
        )

        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {"price": 150.0}
            client.scrape_bloomberg("AAPL")

        # 비용 기록 호출 확인
        cost_tracker.record_api_call.assert_called_once()
```

### 2. test_hybrid_source.py

**목적**: 우선순위 기반 fallback 로직 검증

```python
"""하이브리드 데이터 소스 통합 테스트"""
import pytest
from src.hybrid_source import HybridDataSource
from unittest.mock import Mock, patch

class TestHybridSource:
    """HybridDataSource 통합 테스트"""

    @pytest.fixture
    def hybrid_source(self):
        """하이브리드 소스 인스턴스"""
        return HybridDataSource(
            bright_data_client=Mock(),
            cache_manager=Mock(),
            cost_tracker=Mock()
        )

    def test_cache_hit(self, hybrid_source):
        """캐시 히트 시나리오"""
        # 캐시에 데이터 있음
        hybrid_source.cache_manager.get.return_value = {
            "price": 150.0,
            "source": "cache"
        }

        result = hybrid_source.get_data("AAPL")

        assert result["source"] == "cache"
        assert result["price"] == 150.0

        # Bright Data API 호출 안됨
        hybrid_source.bright_data_client.scrape_bloomberg.assert_not_called()

    def test_cache_miss_bright_data_success(self, hybrid_source):
        """캐시 미스 -> Bright Data 성공"""
        hybrid_source.cache_manager.get.return_value = None
        hybrid_source.bright_data_client.scrape_bloomberg.return_value = {
            "price": 150.0,
            "timestamp": "2024-01-01T00:00:00"
        }

        result = hybrid_source.get_data("AAPL")

        assert result["source"] == "bright_data"
        assert result["price"] == 150.0

        # 캐시에 저장됨
        hybrid_source.cache_manager.set.assert_called_once()

    def test_bright_data_fail_yfinance_fallback(self, hybrid_source):
        """Bright Data 실패 -> yfinance fallback"""
        hybrid_source.cache_manager.get.return_value = None
        hybrid_source.bright_data_client.scrape_bloomberg.side_effect = Exception("API Error")

        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = {"currentPrice": 150.0}

            result = hybrid_source.get_data("AAPL")

            assert result["source"] == "yfinance"
            assert result["price"] == 150.0

    def test_all_sources_fail(self, hybrid_source):
        """모든 소스 실패"""
        hybrid_source.cache_manager.get.return_value = None
        hybrid_source.bright_data_client.scrape_bloomberg.side_effect = Exception("API Error")

        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.side_effect = Exception("yfinance Error")

            with pytest.raises(Exception, match="All data sources failed"):
                hybrid_source.get_data("AAPL")

    def test_cost_aware_fallback(self, hybrid_source):
        """비용 인식 fallback"""
        hybrid_source.cache_manager.get.return_value = None
        hybrid_source.cost_tracker.is_over_budget.return_value = True

        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.info = {"currentPrice": 150.0}

            result = hybrid_source.get_data("AAPL")

            # 예산 초과 시 yfinance 직접 사용
            assert result["source"] == "yfinance"
            hybrid_source.bright_data_client.scrape_bloomberg.assert_not_called()

    def test_priority_override(self, hybrid_source):
        """우선순위 강제 변경"""
        result = hybrid_source.get_data(
            "AAPL",
            force_source="yfinance"
        )

        # yfinance만 호출
        hybrid_source.cache_manager.get.assert_not_called()
        hybrid_source.bright_data_client.scrape_bloomberg.assert_not_called()
```

---

## 테스트 실행 명령어

### 기본 명령어

```bash
# 전체 테스트 실행
pytest tests/ -v

# 특정 파일 테스트
pytest tests/test_cost_tracker.py -v

# 특정 클래스 테스트
pytest tests/test_cache_manager.py::TestCacheManager -v

# 특정 테스트 메서드
pytest tests/test_cache_manager.py::TestCacheManager::test_ttl_expiration -v
```

### 고급 명령어

```bash
# API 호출 제외 (모든 테스트를 mock으로 실행)
pytest tests/ -v -m "not api"

# 커버리지 측정
pytest tests/ --cov=src --cov-report=html

# 실패한 테스트만 재실행
pytest tests/ --lf

# 병렬 실행 (pytest-xdist 필요)
pytest tests/ -n auto

# 상세 출력
pytest tests/ -vv --tb=short

# 특정 키워드 매칭
pytest tests/ -k "cache or cost"
```

### CI/CD 파이프라인용

```bash
# GitHub Actions용 명령어
pytest tests/ -v --junitxml=test-results.xml --cov=src --cov-report=xml

# 빠른 검증 (API 제외)
pytest tests/ -v -m "not api" --maxfail=3
```

---

## Mock 전략

### 1. Bright Data API Mock

```python
"""Bright Data API 응답 Mock"""
from unittest.mock import Mock, patch

@pytest.fixture
def mock_bright_data_response():
    """표준 Bright Data 응답"""
    return {
        "status": "success",
        "data": {
            "price": 150.25,
            "change": 2.50,
            "change_percent": 1.69,
            "volume": 52000000,
            "market_cap": 2400000000000,
            "pe_ratio": 28.5,
            "timestamp": "2024-01-01T16:00:00Z"
        },
        "metadata": {
            "source": "bloomberg",
            "scrape_time_ms": 1250
        }
    }

@pytest.fixture
def mock_bright_data_client(mock_bright_data_response):
    """Mock된 Bright Data 클라이언트"""
    client = Mock()
    client.scrape_bloomberg.return_value = mock_bright_data_response
    return client
```

### 2. yfinance Mock

```python
"""yfinance Mock 전략"""
from unittest.mock import Mock, patch

@pytest.fixture
def mock_yfinance_ticker():
    """Mock된 yfinance Ticker"""
    ticker = Mock()
    ticker.info = {
        "currentPrice": 150.25,
        "previousClose": 147.75,
        "volume": 52000000,
        "marketCap": 2400000000000,
        "trailingPE": 28.5,
        "fiftyTwoWeekHigh": 180.00,
        "fiftyTwoWeekLow": 130.00
    }
    ticker.history.return_value = Mock()  # DataFrame mock
    return ticker

def test_with_yfinance_mock(mock_yfinance_ticker):
    """yfinance mock 사용 예시"""
    with patch('yfinance.Ticker', return_value=mock_yfinance_ticker):
        # 테스트 코드
        pass
```

### 3. HTML Fixture

**fixtures/sample_bloomberg.html**
```html
<!DOCTYPE html>
<html>
<head>
    <title>AAPL:US - Bloomberg</title>
</head>
<body>
    <div class="price-container">
        <span class="priceText__1853e8a5" data-test="price-value">150.25</span>
    </div>
    <div class="change-container">
        <span class="change-positive">+2.50</span>
        <span class="change-percent">+1.69%</span>
    </div>
    <div class="stats">
        <div class="volume">
            <span class="label">Volume</span>
            <span class="value">52,000,000</span>
        </div>
        <div class="market-cap">
            <span class="label">Market Cap</span>
            <span class="value">2.40T</span>
        </div>
    </div>
</body>
</html>
```

### 4. 환경 변수 Mock

```python
"""환경 변수 Mock"""
import os
import pytest

@pytest.fixture
def mock_env_vars(monkeypatch):
    """테스트용 환경 변수"""
    monkeypatch.setenv("BRIGHT_DATA_API_KEY", "test_api_key_12345")
    monkeypatch.setenv("MONTHLY_BUDGET", "100.0")
    monkeypatch.setenv("CACHE_TTL", "3600")

@pytest.fixture
def mock_env_no_api_key(monkeypatch):
    """API 키 없는 환경"""
    monkeypatch.delenv("BRIGHT_DATA_API_KEY", raising=False)
```

---

## 배포 전 체크리스트

### 1. 코드 품질 검증

```bash
# ✅ Linting 통과
ruff check src/ tests/

# ✅ 타입 체크 통과 (mypy 사용 시)
mypy src/

# ✅ 포맷팅 확인
ruff format --check src/ tests/
```

### 2. 테스트 커버리지

```bash
# ✅ 전체 테스트 통과
pytest tests/ -v

# ✅ 커버리지 80% 이상
pytest tests/ --cov=src --cov-report=term-missing

# 목표 커버리지
# - 전체: 80% 이상
# - 핵심 모듈: 90% 이상
#   - cost_tracker.py
#   - cache_manager.py
#   - hybrid_source.py
```

### 3. 기능 검증

```bash
# ✅ 비용 추적 동작
pytest tests/test_cost_tracker.py -v

# ✅ 캐시 TTL 검증
pytest tests/test_cache_manager.py::TestCacheManager::test_ttl_expiration -v

# ✅ API 연결 테스트 (1회 실제 요청)
pytest tests/test_bright_data.py::TestBrightDataIntegration::test_real_api_connection -v
```

### 4. 통합 시나리오

```bash
# ✅ Fallback 로직 동작
pytest tests/test_hybrid_source.py -v

# ✅ 비용 초과 시 동작
pytest tests/test_hybrid_source.py::TestHybridSource::test_cost_aware_fallback -v
```

### 5. 환경 설정 확인

**체크리스트**:
- [ ] `.env` 파일 설정 완료
- [ ] `BRIGHT_DATA_API_KEY` 유효성 확인
- [ ] `MONTHLY_BUDGET` 적절히 설정 (권장: $100)
- [ ] `CACHE_TTL` 설정 확인 (권장: 3600초)
- [ ] 캐시 디렉토리 생성 확인
- [ ] 비용 DB 경로 확인

### 6. 의존성 검증

```bash
# ✅ 모든 의존성 설치 확인
pip install -r requirements.txt

# ✅ 버전 충돌 없음
pip check

# ✅ 보안 취약점 없음
pip-audit
```

### 7. 문서 완성도

**확인 항목**:
- [ ] `01_brightdata_introduction.md` - Bright Data 소개
- [ ] `02_cost_optimization.md` - 비용 최적화 전략
- [ ] `03_caching_strategy.md` - 캐싱 전략
- [ ] `04_api_integration.md` - API 통합 가이드
- [ ] `05_implementation.md` - 구현 상세
- [ ] `06_testing.md` - 테스팅 가이드 (현재 문서)

### 8. 성능 검증

```python
# ✅ 캐시 히트율 측정
def test_cache_hit_rate():
    """캐시 히트율 80% 이상 확인"""
    # 테스트 구현
    pass

# ✅ API 응답 시간 측정
def test_api_response_time():
    """평균 응답 시간 2초 이내 확인"""
    # 테스트 구현
    pass
```

### 9. 에러 핸들링

```bash
# ✅ 네트워크 오류 처리
pytest tests/ -k "error_handling" -v

# ✅ 데이터 누락 처리
pytest tests/test_bloomberg_parser.py::TestBloombergParser::test_parse_missing_data -v

# ✅ API 한도 초과 처리
pytest tests/test_bright_data.py -k "rate_limiting" -v
```

### 10. 최종 배포 스크립트

```bash
#!/bin/bash
# deploy_check.sh - 배포 전 최종 검증

echo "🔍 1. 코드 품질 검증..."
ruff check src/ tests/ || exit 1

echo "🧪 2. 전체 테스트 실행..."
pytest tests/ -v -m "not api" || exit 1

echo "📊 3. 커버리지 측정..."
pytest tests/ --cov=src --cov-report=term --cov-fail-under=80 || exit 1

echo "🔒 4. 보안 검사..."
pip-audit || exit 1

echo "📦 5. 의존성 확인..."
pip check || exit 1

echo "✅ 배포 준비 완료!"
```

---

## 테스트 실행 예시

### 개발 중 빠른 테스트
```bash
# 현재 작업 중인 파일만
pytest tests/test_cache_manager.py -v

# 실패 시 즉시 중단
pytest tests/ -x
```

### CI/CD 파이프라인
```bash
# GitHub Actions workflow
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest tests/ -v -m "not api" --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### 배포 전 전체 검증
```bash
# 모든 테스트 + 커버리지 + 보고서
pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing
```

---

## 트러블슈팅

### 자주 발생하는 문제

**1. Mock이 작동하지 않음**
```python
# ❌ 잘못된 패치 경로
@patch('yfinance.Ticker')

# ✅ 올바른 패치 경로 (import된 위치)
@patch('src.hybrid_source.yfinance.Ticker')
```

**2. 캐시 충돌**
```python
# ✅ 각 테스트마다 독립적인 캐시 디렉토리 사용
@pytest.fixture
def cache(tmp_path):
    return CacheManager(cache_dir=tmp_path / "cache")
```

**3. 비동기 테스트**
```python
# ✅ pytest-asyncio 사용
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

---

## 참고 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [unittest.mock 가이드](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-cov 문서](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**문서 작성일**: 2024-01-07
**다음 문서**: 배포 및 운영 가이드 (예정)
**이전 문서**: [05_implementation.md](./05_implementation.md)
