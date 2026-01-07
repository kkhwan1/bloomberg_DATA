# Bloomberg 파서 구현 가이드

Bloomberg 웹사이트에서 금융 데이터를 추출하기 위한 파싱 전략과 구현 방법을 설명합니다.

## 목차

1. [Bloomberg URL 구조](#1-bloomberg-url-구조)
2. [HTML 파싱 전략](#2-html-파싱-전략)
3. [BloombergParser 클래스 구현](#3-bloombergparser-클래스-구현)
4. [데이터 모델](#4-데이터-모델)
5. [테스트 및 검증](#5-테스트-및-검증)

---

## 1. Bloomberg URL 구조

Bloomberg는 다양한 금융 시장 데이터를 제공하며, 각 섹션마다 고유한 URL 패턴을 가지고 있습니다.

### 1.1 주요 시장 페이지

| 카테고리 | URL | 설명 |
|---------|-----|------|
| 전체 시장 개요 | `https://www.bloomberg.com/markets` | 모든 시장 데이터 대시보드 |
| 주식 | `https://www.bloomberg.com/markets/stocks` | 글로벌 주식 시장 |
| 원자재 | `https://www.bloomberg.com/markets/commodities` | 상품/원자재 시장 |
| 채권/금리 | `https://www.bloomberg.com/markets/rates-bonds` | 국채, 회사채, 금리 |
| 외환 | `https://www.bloomberg.com/markets/currencies` | 환율, 통화 쌍 |

### 1.2 개별 종목 Quote 페이지

**URL 패턴**: `https://www.bloomberg.com/quote/{TICKER}:{EXCHANGE}`

**예시**:
```
애플 주식:        https://www.bloomberg.com/quote/AAPL:US
삼성전자:         https://www.bloomberg.com/quote/005930:KS
비트코인:         https://www.bloomberg.com/quote/XBTUSD:CUR
미국 10년물 국채: https://www.bloomberg.com/quote/USGG10YR:IND
금 선물:          https://www.bloomberg.com/quote/GC1:COM
```

**TICKER 형식**: `{종목코드}:{거래소코드}`
- `US` - 미국 증시
- `KS` - 한국 증시
- `CUR` - 통화
- `IND` - 지수
- `COM` - 원자재

### 1.3 URL 파라미터

Bloomberg URL은 추가 파라미터로 데이터 필터링이 가능합니다:

```
# 시간 범위
?timeframe=1D      # 1일
?timeframe=5D      # 5일
?timeframe=1M      # 1개월
?timeframe=1Y      # 1년

# 지역 필터
?region=US         # 미국
?region=ASIA       # 아시아
?region=EMEA       # 유럽/중동/아프리카
```

---

## 2. HTML 파싱 전략

Bloomberg 페이지는 동적으로 렌더링되는 Next.js 애플리케이션입니다. 여러 파싱 전략을 단계별로 시도하여 데이터를 추출합니다.

### 2.1 전략 개요

```
Strategy 1: JSON-LD 추출 (가장 구조화됨)
    ↓ 실패
Strategy 2: __NEXT_DATA__ 파싱 (Next.js 데이터)
    ↓ 실패
Strategy 3: HTML 테이블 파싱 (폴백)
    ↓ 실패
에러 처리 및 로깅
```

### 2.2 Strategy 1: JSON-LD 추출

**JSON-LD란?**
- Linked Data용 JavaScript Object Notation
- SEO를 위해 페이지에 임베드된 구조화된 데이터
- `<script type="application/ld+json">` 태그 내부에 위치

**장점**:
- 가장 구조화된 데이터
- 파싱이 간단하고 안정적
- schema.org 표준 준수

**추출 방법**:
```python
def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
    """
    JSON-LD 스크립트 태그에서 구조화된 데이터 추출

    Args:
        soup: BeautifulSoup 파싱된 HTML

    Returns:
        JSON-LD 데이터 딕셔너리 또는 None
    """
    scripts = soup.find_all('script', type='application/ld+json')

    for script in scripts:
        try:
            data = json.loads(script.string)

            # 금융 Quote 데이터 확인
            if isinstance(data, dict) and data.get('@type') in ['FinancialQuote', 'StockQuote']:
                return data

            # 배열 형태인 경우
            if isinstance(data, list):
                for item in data:
                    if item.get('@type') in ['FinancialQuote', 'StockQuote']:
                        return item
        except json.JSONDecodeError:
            continue

    return None
```

**JSON-LD 예시**:
```json
{
  "@context": "https://schema.org",
  "@type": "FinancialQuote",
  "name": "Apple Inc",
  "tickerSymbol": "AAPL:US",
  "price": {
    "@type": "MonetaryAmount",
    "value": "150.25",
    "currency": "USD"
  },
  "priceChange": "-2.35",
  "priceChangePercent": "-1.54",
  "volume": "85234567"
}
```

### 2.3 Strategy 2: __NEXT_DATA__ 파싱

**__NEXT_DATA__란?**
- Next.js가 서버 사이드 렌더링 시 사용하는 데이터
- `<script id="__NEXT_DATA__">` 태그 내부의 JSON
- 페이지 렌더링에 필요한 모든 데이터 포함

**장점**:
- 페이지에 표시되는 모든 데이터 포함
- 구조화된 JSON 형태
- 추가 API 호출 불필요

**추출 방법**:
```python
def _extract_next_data(self, soup: BeautifulSoup) -> Optional[Dict]:
    """
    Next.js __NEXT_DATA__ 스크립트에서 데이터 추출

    Args:
        soup: BeautifulSoup 파싱된 HTML

    Returns:
        __NEXT_DATA__ 딕셔너리 또는 None
    """
    script = soup.find('script', id='__NEXT_DATA__')

    if not script:
        return None

    try:
        data = json.loads(script.string)

        # props.pageProps 경로에서 데이터 추출
        page_props = data.get('props', {}).get('pageProps', {})

        # 시장 데이터 위치는 페이지 타입에 따라 다름
        if 'marketData' in page_props:
            return page_props['marketData']
        elif 'securityData' in page_props:
            return page_props['securityData']
        elif 'quoteData' in page_props:
            return page_props['quoteData']

        return page_props

    except json.JSONDecodeError as e:
        self.logger.error(f"__NEXT_DATA__ JSON 파싱 실패: {e}")
        return None
```

**__NEXT_DATA__ 구조 예시**:
```json
{
  "props": {
    "pageProps": {
      "securityData": {
        "ticker": "AAPL:US",
        "name": "Apple Inc",
        "price": 150.25,
        "change": -2.35,
        "changePercent": -1.54,
        "volume": 85234567,
        "marketCap": 2450000000000,
        "dayHigh": 152.50,
        "dayLow": 149.80
      }
    }
  }
}
```

### 2.4 Strategy 3: HTML 테이블 파싱 (폴백)

**사용 시나리오**:
- JSON-LD와 __NEXT_DATA__ 모두 실패한 경우
- 정적 HTML 테이블로 데이터가 표시되는 경우
- 가장 불안정하지만 최후의 수단

**파싱 방법**:
```python
def _parse_html_tables(self, soup: BeautifulSoup) -> List[Dict]:
    """
    HTML 테이블에서 시장 데이터 추출

    Args:
        soup: BeautifulSoup 파싱된 HTML

    Returns:
        추출된 데이터 리스트
    """
    results = []

    # data-component="market-table" 속성을 가진 테이블 찾기
    tables = soup.find_all('table', {'data-component': 'market-table'})

    if not tables:
        # 일반 테이블 탐색
        tables = soup.find_all('table')

    for table in tables:
        # 헤더 추출
        headers = []
        header_row = table.find('thead')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all('th')]

        # 데이터 행 추출
        tbody = table.find('tbody')
        if not tbody:
            continue

        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 2:
                continue

            row_data = {}

            for i, cell in enumerate(cells):
                header = headers[i] if i < len(headers) else f'column_{i}'
                value = cell.get_text(strip=True)

                # 링크가 있으면 ticker 추출
                link = cell.find('a', href=True)
                if link and '/quote/' in link['href']:
                    ticker = link['href'].split('/quote/')[-1]
                    row_data['ticker'] = ticker
                    row_data['name'] = value
                else:
                    row_data[header.lower().replace(' ', '_')] = value

            if row_data:
                results.append(row_data)

    return results
```

**HTML 구조 예시**:
```html
<table data-component="market-table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Last Price</th>
      <th>Change</th>
      <th>% Change</th>
      <th>Volume</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="/quote/AAPL:US">Apple Inc</a></td>
      <td>150.25</td>
      <td>-2.35</td>
      <td>-1.54%</td>
      <td>85.23M</td>
    </tr>
  </tbody>
</table>
```

### 2.5 숫자 파싱 유틸리티

Bloomberg는 다양한 숫자 표기법을 사용합니다:
- 천 단위 구분: `1,234.56`
- 약어: `85.23M` (Million), `2.45B` (Billion), `1.23T` (Trillion)
- 백분율: `1.54%`, `-0.25%`
- 통화 기호: `$150.25`, `€125.30`

```python
def _parse_number(self, value: str) -> Optional[float]:
    """
    다양한 형식의 숫자 문자열을 float으로 변환

    Args:
        value: 파싱할 숫자 문자열

    Returns:
        변환된 float 값 또는 None

    Examples:
        "1,234.56"   -> 1234.56
        "85.23M"     -> 85230000.0
        "2.45B"      -> 2450000000.0
        "-1.54%"     -> -1.54
        "$150.25"    -> 150.25
    """
    if not value or value == '-' or value == 'N/A':
        return None

    # 공백 제거
    value = value.strip()

    # 백분율 처리
    if '%' in value:
        return float(value.replace('%', '').replace(',', ''))

    # 통화 기호 제거
    value = re.sub(r'[$€£¥₩]', '', value)

    # 쉼표 제거
    value = value.replace(',', '')

    # 약어 처리
    multipliers = {
        'K': 1_000,
        'M': 1_000_000,
        'B': 1_000_000_000,
        'T': 1_000_000_000_000
    }

    for suffix, multiplier in multipliers.items():
        if value.endswith(suffix):
            try:
                return float(value[:-1]) * multiplier
            except ValueError:
                return None

    # 일반 숫자 변환
    try:
        return float(value)
    except ValueError:
        return None
```

---

## 3. BloombergParser 클래스 구현

### 3.1 클래스 구조

```python
from dataclasses import dataclass
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
import logging
import json
import re


@dataclass
class BloombergQuote:
    """Bloomberg 시장 데이터 모델"""
    ticker: str                    # 종목 코드 (예: "AAPL:US")
    name: str                      # 종목명
    price: Optional[float]         # 현재가
    change: Optional[float]        # 변동액
    change_percent: Optional[float] # 변동률 (%)
    volume: Optional[float]        # 거래량
    market_cap: Optional[float]    # 시가총액
    day_high: Optional[float]      # 당일 최고가
    day_low: Optional[float]       # 당일 최저가
    year_high: Optional[float]     # 52주 최고가
    year_low: Optional[float]      # 52주 최저가
    open_price: Optional[float]    # 시가
    prev_close: Optional[float]    # 전일 종가
    currency: Optional[str]        # 통화
    source: str                    # 데이터 소스 (json-ld/next-data/html)


class BloombergParser:
    """
    Bloomberg 웹페이지에서 금융 데이터를 추출하는 파서

    다중 전략 파싱:
    1. JSON-LD 구조화 데이터
    2. Next.js __NEXT_DATA__
    3. HTML 테이블 파싱 (폴백)
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Args:
            logger: 로거 인스턴스 (None이면 기본 로거 생성)
        """
        self.logger = logger or logging.getLogger(__name__)

    def parse_markets_page(self, html: str, url: str) -> List[BloombergQuote]:
        """
        Bloomberg 시장 페이지에서 여러 종목 데이터 추출

        Args:
            html: HTML 문자열
            url: 페이지 URL

        Returns:
            BloombergQuote 객체 리스트
        """
        pass  # 구현은 아래 참조

    def parse_quote_page(self, html: str, url: str) -> Optional[BloombergQuote]:
        """
        개별 종목 Quote 페이지에서 상세 데이터 추출

        Args:
            html: HTML 문자열
            url: 페이지 URL

        Returns:
            BloombergQuote 객체 또는 None
        """
        pass  # 구현은 아래 참조

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
        """JSON-LD 데이터 추출"""
        pass  # 위 섹션 참조

    def _extract_next_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """__NEXT_DATA__ 추출"""
        pass  # 위 섹션 참조

    def _parse_html_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """HTML 테이블 파싱"""
        pass  # 위 섹션 참조

    def _parse_number(self, value: str) -> Optional[float]:
        """숫자 문자열 파싱"""
        pass  # 위 섹션 참조
```

### 3.2 parse_markets_page() 구현

시장 개요 페이지에서 여러 종목의 데이터를 추출합니다.

```python
def parse_markets_page(self, html: str, url: str) -> List[BloombergQuote]:
    """
    Bloomberg 시장 페이지에서 여러 종목 데이터 추출

    파싱 순서:
    1. JSON-LD 시도
    2. __NEXT_DATA__ 시도
    3. HTML 테이블 파싱 (폴백)

    Args:
        html: HTML 문자열
        url: 페이지 URL

    Returns:
        BloombergQuote 객체 리스트

    Raises:
        ParsingError: 모든 파싱 전략이 실패한 경우
    """
    soup = BeautifulSoup(html, 'html.parser')
    results = []

    # Strategy 1: JSON-LD 시도
    self.logger.info("Strategy 1: JSON-LD 추출 시도")
    json_ld = self._extract_json_ld(soup)
    if json_ld:
        self.logger.info("JSON-LD 데이터 발견")
        # JSON-LD가 리스트 형태일 수 있음
        items = json_ld if isinstance(json_ld, list) else [json_ld]

        for item in items:
            quote = self._json_ld_to_quote(item, source='json-ld')
            if quote:
                results.append(quote)

        if results:
            return results

    # Strategy 2: __NEXT_DATA__ 시도
    self.logger.info("Strategy 2: __NEXT_DATA__ 추출 시도")
    next_data = self._extract_next_data(soup)
    if next_data:
        self.logger.info("__NEXT_DATA__ 발견")

        # 데이터 구조 탐색
        # 가능한 경로들
        possible_paths = [
            ['marketData', 'quotes'],
            ['securityList'],
            ['quotes'],
            ['data', 'quotes']
        ]

        for path in possible_paths:
            quotes_data = next_data
            for key in path:
                quotes_data = quotes_data.get(key, {})
                if not quotes_data:
                    break

            if quotes_data and isinstance(quotes_data, list):
                for item in quotes_data:
                    quote = self._next_data_to_quote(item, source='next-data')
                    if quote:
                        results.append(quote)
                break

        if results:
            return results

    # Strategy 3: HTML 테이블 파싱 (폴백)
    self.logger.info("Strategy 3: HTML 테이블 파싱 시도")
    table_data = self._parse_html_tables(soup)

    if table_data:
        self.logger.info(f"HTML 테이블에서 {len(table_data)}개 항목 발견")

        for item in table_data:
            quote = self._html_to_quote(item, source='html')
            if quote:
                results.append(quote)

    if not results:
        self.logger.error("모든 파싱 전략 실패")
        raise ParsingError(f"Failed to parse Bloomberg page: {url}")

    self.logger.info(f"총 {len(results)}개 종목 데이터 추출 완료")
    return results


def _json_ld_to_quote(self, data: Dict, source: str) -> Optional[BloombergQuote]:
    """JSON-LD 데이터를 BloombergQuote로 변환"""
    try:
        return BloombergQuote(
            ticker=data.get('tickerSymbol', ''),
            name=data.get('name', ''),
            price=self._parse_number(data.get('price', {}).get('value')),
            change=self._parse_number(data.get('priceChange')),
            change_percent=self._parse_number(data.get('priceChangePercent')),
            volume=self._parse_number(data.get('volume')),
            market_cap=self._parse_number(data.get('marketCap')),
            day_high=self._parse_number(data.get('dayHigh')),
            day_low=self._parse_number(data.get('dayLow')),
            year_high=self._parse_number(data.get('yearHigh')),
            year_low=self._parse_number(data.get('yearLow')),
            open_price=self._parse_number(data.get('openPrice')),
            prev_close=self._parse_number(data.get('previousClose')),
            currency=data.get('price', {}).get('currency'),
            source=source
        )
    except Exception as e:
        self.logger.error(f"JSON-LD 변환 실패: {e}")
        return None


def _next_data_to_quote(self, data: Dict, source: str) -> Optional[BloombergQuote]:
    """__NEXT_DATA__를 BloombergQuote로 변환"""
    try:
        return BloombergQuote(
            ticker=data.get('ticker', data.get('id', '')),
            name=data.get('name', data.get('securityName', '')),
            price=self._parse_number(data.get('price', data.get('lastPrice'))),
            change=self._parse_number(data.get('change', data.get('netChange'))),
            change_percent=self._parse_number(data.get('changePercent', data.get('pctChange'))),
            volume=self._parse_number(data.get('volume')),
            market_cap=self._parse_number(data.get('marketCap')),
            day_high=self._parse_number(data.get('dayHigh', data.get('high'))),
            day_low=self._parse_number(data.get('dayLow', data.get('low'))),
            year_high=self._parse_number(data.get('yearHigh', data.get('high52Week'))),
            year_low=self._parse_number(data.get('yearLow', data.get('low52Week'))),
            open_price=self._parse_number(data.get('open', data.get('openPrice'))),
            prev_close=self._parse_number(data.get('previousClose', data.get('prevClose'))),
            currency=data.get('currency', data.get('currencyCode')),
            source=source
        )
    except Exception as e:
        self.logger.error(f"__NEXT_DATA__ 변환 실패: {e}")
        return None


def _html_to_quote(self, data: Dict, source: str) -> Optional[BloombergQuote]:
    """HTML 테이블 데이터를 BloombergQuote로 변환"""
    try:
        return BloombergQuote(
            ticker=data.get('ticker', ''),
            name=data.get('name', ''),
            price=self._parse_number(data.get('last_price', data.get('price'))),
            change=self._parse_number(data.get('change', data.get('net_change'))),
            change_percent=self._parse_number(data.get('pct_change', data.get('%_change'))),
            volume=self._parse_number(data.get('volume')),
            market_cap=None,  # HTML 테이블에는 보통 없음
            day_high=None,
            day_low=None,
            year_high=None,
            year_low=None,
            open_price=None,
            prev_close=None,
            currency=None,
            source=source
        )
    except Exception as e:
        self.logger.error(f"HTML 데이터 변환 실패: {e}")
        return None
```

### 3.3 parse_quote_page() 구현

개별 종목의 상세 페이지에서 데이터를 추출합니다.

```python
def parse_quote_page(self, html: str, url: str) -> Optional[BloombergQuote]:
    """
    개별 종목 Quote 페이지에서 상세 데이터 추출

    Quote 페이지는 단일 종목에 대한 상세 정보를 제공합니다.
    parse_markets_page()와 동일한 전략을 사용하지만
    단일 객체를 반환합니다.

    Args:
        html: HTML 문자열
        url: 페이지 URL

    Returns:
        BloombergQuote 객체 또는 None
    """
    soup = BeautifulSoup(html, 'html.parser')

    # URL에서 ticker 추출
    ticker_match = re.search(r'/quote/([^/?]+)', url)
    ticker = ticker_match.group(1) if ticker_match else None

    # Strategy 1: JSON-LD
    json_ld = self._extract_json_ld(soup)
    if json_ld:
        quote = self._json_ld_to_quote(json_ld, source='json-ld')
        if quote:
            # URL에서 추출한 ticker로 검증
            if ticker and quote.ticker != ticker:
                self.logger.warning(f"Ticker 불일치: {quote.ticker} vs {ticker}")
            return quote

    # Strategy 2: __NEXT_DATA__
    next_data = self._extract_next_data(soup)
    if next_data:
        # Quote 페이지의 데이터 경로
        security_data = next_data.get('securityData') or next_data.get('quoteData')

        if security_data:
            quote = self._next_data_to_quote(security_data, source='next-data')
            if quote:
                return quote

    # Strategy 3: HTML 파싱
    # Quote 페이지는 특정 클래스/ID를 가진 요소에서 데이터 추출
    quote_data = {}

    # 종목명
    name_elem = soup.find('h1', class_=re.compile(r'name|title|security'))
    if name_elem:
        quote_data['name'] = name_elem.get_text(strip=True)

    # 가격 정보 - 다양한 셀렉터 시도
    price_selectors = [
        {'class': re.compile(r'price|last|current')},
        {'data-field': 'price'},
        {'class': 'priceText'}
    ]

    for selector in price_selectors:
        price_elem = soup.find(['span', 'div'], selector)
        if price_elem:
            quote_data['price'] = price_elem.get_text(strip=True)
            break

    # 변동 정보
    change_elem = soup.find(['span', 'div'], class_=re.compile(r'change|diff'))
    if change_elem:
        quote_data['change'] = change_elem.get_text(strip=True)

    # 데이터 테이블에서 추가 정보
    data_tables = soup.find_all('table', class_=re.compile(r'data|info|stats'))
    for table in data_tables:
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)

                field_mapping = {
                    'volume': 'volume',
                    'market cap': 'market_cap',
                    'day high': 'day_high',
                    'day low': 'day_low',
                    '52 week high': 'year_high',
                    '52 week low': 'year_low',
                    'open': 'open_price',
                    'previous close': 'prev_close'
                }

                for key, field in field_mapping.items():
                    if key in label:
                        quote_data[field] = value
                        break

    if quote_data:
        quote_data['ticker'] = ticker or ''
        return self._html_to_quote(quote_data, source='html')

    self.logger.error(f"Quote 페이지 파싱 실패: {url}")
    return None
```

---

## 4. 데이터 모델

### 4.1 BloombergQuote 상세 명세

```python
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class BloombergQuote:
    """
    Bloomberg 시장 데이터를 표현하는 데이터 클래스

    모든 금융 데이터 필드는 Optional로 정의되어
    부분적인 데이터도 처리 가능합니다.
    """

    # 필수 필드
    ticker: str                    # 종목 코드 (예: "AAPL:US")
    name: str                      # 종목명
    source: str                    # 데이터 소스 (json-ld/next-data/html)

    # 가격 정보
    price: Optional[float] = None              # 현재가
    change: Optional[float] = None             # 변동액
    change_percent: Optional[float] = None     # 변동률 (%)

    # 거래 정보
    volume: Optional[float] = None             # 거래량
    market_cap: Optional[float] = None         # 시가총액

    # 당일 가격 범위
    day_high: Optional[float] = None           # 당일 최고가
    day_low: Optional[float] = None            # 당일 최저가
    open_price: Optional[float] = None         # 시가
    prev_close: Optional[float] = None         # 전일 종가

    # 52주 가격 범위
    year_high: Optional[float] = None          # 52주 최고가
    year_low: Optional[float] = None           # 52주 최저가

    # 메타 정보
    currency: Optional[str] = None             # 통화 (USD, KRW 등)
    timestamp: datetime = field(default_factory=datetime.now)  # 데이터 수집 시각

    def to_dict(self) -> dict:
        """딕셔너리로 변환 (JSON 직렬화 용)"""
        data = asdict(self)
        # datetime을 ISO 형식 문자열로 변환
        data['timestamp'] = self.timestamp.isoformat()
        return data

    def is_valid(self) -> bool:
        """
        데이터 유효성 검사

        최소한 ticker, name, price 필드가 있어야 유효합니다.
        """
        return bool(self.ticker and self.name and self.price is not None)

    def calculate_metrics(self) -> dict:
        """
        추가 지표 계산

        Returns:
            계산된 지표 딕셔너리
        """
        metrics = {}

        # 일일 변동폭 (High-Low Range)
        if self.day_high is not None and self.day_low is not None:
            metrics['day_range'] = self.day_high - self.day_low
            metrics['day_range_percent'] = (metrics['day_range'] / self.day_low) * 100

        # 52주 변동폭
        if self.year_high is not None and self.year_low is not None:
            metrics['year_range'] = self.year_high - self.year_low
            metrics['year_range_percent'] = (metrics['year_range'] / self.year_low) * 100

        # 현재가 대비 52주 최고가 거리
        if self.price is not None and self.year_high is not None:
            metrics['distance_from_52w_high'] = ((self.year_high - self.price) / self.year_high) * 100

        # 현재가 대비 52주 최저가 거리
        if self.price is not None and self.year_low is not None:
            metrics['distance_from_52w_low'] = ((self.price - self.year_low) / self.year_low) * 100

        return metrics

    def __str__(self) -> str:
        """사람이 읽기 쉬운 문자열 표현"""
        change_sign = '+' if self.change and self.change > 0 else ''
        change_str = f"{change_sign}{self.change:.2f}" if self.change else "N/A"
        change_pct = f"({change_sign}{self.change_percent:.2f}%)" if self.change_percent else ""

        return (
            f"{self.name} ({self.ticker})\n"
            f"  Price: {self.price:.2f} {self.currency or ''}\n"
            f"  Change: {change_str} {change_pct}\n"
            f"  Volume: {self.volume:,.0f}" if self.volume else ""
        )
```

### 4.2 필드 매핑 테이블

Bloomberg HTML에서 나타나는 다양한 필드명을 표준화된 필드로 매핑합니다.

```python
FIELD_MAPPINGS = {
    # 종목 정보
    'ticker': ['ticker', 'symbol', 'tickerSymbol', 'id', 'securityId'],
    'name': ['name', 'securityName', 'companyName', 'title'],

    # 가격
    'price': ['price', 'lastPrice', 'last', 'currentPrice', 'value'],
    'change': ['change', 'netChange', 'priceChange', 'diff'],
    'change_percent': ['changePercent', 'pctChange', 'percentChange', '% change'],

    # 거래
    'volume': ['volume', 'vol', 'tradeVolume'],
    'market_cap': ['marketCap', 'market_cap', 'mktCap', 'cap'],

    # 당일 범위
    'day_high': ['dayHigh', 'high', 'todayHigh'],
    'day_low': ['dayLow', 'low', 'todayLow'],
    'open_price': ['open', 'openPrice', 'todayOpen'],
    'prev_close': ['previousClose', 'prevClose', 'yesterdayClose'],

    # 52주 범위
    'year_high': ['yearHigh', '52WeekHigh', 'high52Week', '52w high'],
    'year_low': ['yearLow', '52WeekLow', 'low52Week', '52w low'],

    # 메타
    'currency': ['currency', 'currencyCode', 'curr']
}


def normalize_field_name(field_name: str) -> Optional[str]:
    """
    다양한 필드명을 표준 필드명으로 정규화

    Args:
        field_name: 원본 필드명

    Returns:
        표준 필드명 또는 None
    """
    field_name_lower = field_name.lower().replace('_', '').replace(' ', '')

    for standard_field, variations in FIELD_MAPPINGS.items():
        for variation in variations:
            if variation.lower().replace('_', '').replace(' ', '') == field_name_lower:
                return standard_field

    return None
```

---

## 5. 테스트 및 검증

### 5.1 단위 테스트

```python
import unittest
from unittest.mock import Mock
import os


class TestBloombergParser(unittest.TestCase):
    """BloombergParser 단위 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.parser = BloombergParser()
        self.test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')

    def load_test_html(self, filename: str) -> str:
        """테스트 HTML 파일 로드"""
        filepath = os.path.join(self.test_data_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def test_parse_number_basic(self):
        """기본 숫자 파싱 테스트"""
        self.assertEqual(self.parser._parse_number("1234.56"), 1234.56)
        self.assertEqual(self.parser._parse_number("1,234.56"), 1234.56)
        self.assertEqual(self.parser._parse_number("-1,234.56"), -1234.56)

    def test_parse_number_with_suffix(self):
        """약어 포함 숫자 파싱 테스트"""
        self.assertEqual(self.parser._parse_number("1.5K"), 1500.0)
        self.assertEqual(self.parser._parse_number("85.23M"), 85_230_000.0)
        self.assertEqual(self.parser._parse_number("2.45B"), 2_450_000_000.0)
        self.assertEqual(self.parser._parse_number("1.23T"), 1_230_000_000_000.0)

    def test_parse_number_percentage(self):
        """백분율 파싱 테스트"""
        self.assertEqual(self.parser._parse_number("1.54%"), 1.54)
        self.assertEqual(self.parser._parse_number("-0.25%"), -0.25)

    def test_parse_number_currency(self):
        """통화 기호 포함 숫자 파싱 테스트"""
        self.assertEqual(self.parser._parse_number("$150.25"), 150.25)
        self.assertEqual(self.parser._parse_number("€125.30"), 125.30)
        self.assertEqual(self.parser._parse_number("₩1,500"), 1500.0)

    def test_parse_number_invalid(self):
        """잘못된 입력 처리 테스트"""
        self.assertIsNone(self.parser._parse_number(""))
        self.assertIsNone(self.parser._parse_number("-"))
        self.assertIsNone(self.parser._parse_number("N/A"))
        self.assertIsNone(self.parser._parse_number("invalid"))

    def test_json_ld_extraction(self):
        """JSON-LD 추출 테스트"""
        html = self.load_test_html('quote_page_with_jsonld.html')
        soup = BeautifulSoup(html, 'html.parser')

        json_ld = self.parser._extract_json_ld(soup)

        self.assertIsNotNone(json_ld)
        self.assertIn('@type', json_ld)
        self.assertIn(json_ld['@type'], ['FinancialQuote', 'StockQuote'])

    def test_next_data_extraction(self):
        """__NEXT_DATA__ 추출 테스트"""
        html = self.load_test_html('markets_page_with_nextdata.html')
        soup = BeautifulSoup(html, 'html.parser')

        next_data = self.parser._extract_next_data(soup)

        self.assertIsNotNone(next_data)
        self.assertIsInstance(next_data, dict)

    def test_parse_markets_page(self):
        """시장 페이지 파싱 통합 테스트"""
        html = self.load_test_html('markets_stocks.html')
        url = 'https://www.bloomberg.com/markets/stocks'

        quotes = self.parser.parse_markets_page(html, url)

        self.assertIsInstance(quotes, list)
        self.assertGreater(len(quotes), 0)

        # 첫 번째 quote 검증
        quote = quotes[0]
        self.assertIsInstance(quote, BloombergQuote)
        self.assertTrue(quote.ticker)
        self.assertTrue(quote.name)
        self.assertIsNotNone(quote.price)

    def test_parse_quote_page(self):
        """개별 종목 페이지 파싱 테스트"""
        html = self.load_test_html('quote_aapl.html')
        url = 'https://www.bloomberg.com/quote/AAPL:US'

        quote = self.parser.parse_quote_page(html, url)

        self.assertIsNotNone(quote)
        self.assertEqual(quote.ticker, 'AAPL:US')
        self.assertTrue(quote.name)
        self.assertIsNotNone(quote.price)

    def test_quote_validation(self):
        """BloombergQuote 유효성 검사 테스트"""
        # 유효한 quote
        valid_quote = BloombergQuote(
            ticker='AAPL:US',
            name='Apple Inc',
            price=150.25,
            source='test'
        )
        self.assertTrue(valid_quote.is_valid())

        # 가격 없는 quote
        invalid_quote = BloombergQuote(
            ticker='AAPL:US',
            name='Apple Inc',
            price=None,
            source='test'
        )
        self.assertFalse(invalid_quote.is_valid())

    def test_quote_metrics_calculation(self):
        """지표 계산 테스트"""
        quote = BloombergQuote(
            ticker='TEST:US',
            name='Test Corp',
            price=100.0,
            day_high=105.0,
            day_low=95.0,
            year_high=150.0,
            year_low=80.0,
            source='test'
        )

        metrics = quote.calculate_metrics()

        self.assertEqual(metrics['day_range'], 10.0)
        self.assertAlmostEqual(metrics['day_range_percent'], 10.526, places=2)
        self.assertAlmostEqual(metrics['distance_from_52w_high'], 33.333, places=2)
        self.assertAlmostEqual(metrics['distance_from_52w_low'], 25.0, places=2)


if __name__ == '__main__':
    unittest.main()
```

### 5.2 테스트 데이터 준비

테스트용 HTML 파일을 `test_data/` 디렉토리에 저장합니다:

```
test_data/
├── quote_page_with_jsonld.html      # JSON-LD 포함 Quote 페이지
├── markets_page_with_nextdata.html  # __NEXT_DATA__ 포함 시장 페이지
├── markets_stocks.html              # 실제 주식 시장 페이지
├── quote_aapl.html                  # 애플 종목 페이지
└── markets_commodities.html         # 원자재 시장 페이지
```

### 5.3 실전 테스트 스크립트

```python
import logging
from bloomberg_parser import BloombergParser
from scraper import BloombergScraper


def test_live_parsing():
    """
    실제 Bloomberg 웹사이트에서 데이터 파싱 테스트

    주의: 너무 자주 실행하면 IP 차단될 수 있습니다.
    """
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 스크래퍼 및 파서 초기화
    scraper = BloombergScraper(delay=5.0)  # 5초 딜레이
    parser = BloombergParser()

    # 테스트할 URL 목록
    test_urls = [
        ('https://www.bloomberg.com/markets/stocks', 'markets_page'),
        ('https://www.bloomberg.com/quote/AAPL:US', 'quote_page'),
        ('https://www.bloomberg.com/markets/commodities', 'commodities_page')
    ]

    results = {}

    for url, page_type in test_urls:
        print(f"\n{'='*60}")
        print(f"테스트: {page_type}")
        print(f"URL: {url}")
        print('='*60)

        try:
            # HTML 가져오기
            html = scraper.fetch_page(url)

            # 파싱
            if page_type == 'quote_page':
                quote = parser.parse_quote_page(html, url)
                if quote:
                    print(f"\n✅ 파싱 성공:")
                    print(quote)
                    print(f"\n지표:")
                    metrics = quote.calculate_metrics()
                    for key, value in metrics.items():
                        print(f"  {key}: {value:.2f}")
                    results[page_type] = quote
                else:
                    print("❌ 파싱 실패")
            else:
                quotes = parser.parse_markets_page(html, url)
                print(f"\n✅ {len(quotes)}개 종목 파싱 성공:")
                for i, quote in enumerate(quotes[:5], 1):  # 상위 5개만 출력
                    print(f"\n{i}. {quote.name} ({quote.ticker})")
                    print(f"   가격: {quote.price} {quote.currency or ''}")
                    if quote.change_percent:
                        sign = '+' if quote.change_percent > 0 else ''
                        print(f"   변동: {sign}{quote.change_percent:.2f}%")
                    print(f"   소스: {quote.source}")
                results[page_type] = quotes

        except Exception as e:
            print(f"❌ 에러 발생: {e}")
            logging.exception("상세 에러:")

    # 결과 요약
    print(f"\n{'='*60}")
    print("테스트 요약")
    print('='*60)

    for page_type, result in results.items():
        if isinstance(result, list):
            print(f"{page_type}: {len(result)}개 항목 추출")
        else:
            print(f"{page_type}: 1개 항목 추출")

    return results


if __name__ == '__main__':
    test_live_parsing()
```

### 5.4 에러 처리 가이드

```python
class ParsingError(Exception):
    """파싱 에러 기본 클래스"""
    pass


class NoDataFoundError(ParsingError):
    """데이터를 찾을 수 없는 경우"""
    pass


class InvalidHTMLError(ParsingError):
    """잘못된 HTML 구조"""
    pass


def parse_with_error_handling(parser: BloombergParser, html: str, url: str):
    """
    에러 처리를 포함한 파싱 래퍼

    Args:
        parser: BloombergParser 인스턴스
        html: HTML 문자열
        url: 페이지 URL

    Returns:
        파싱된 데이터 또는 None
    """
    try:
        # URL 타입 판별
        if '/quote/' in url:
            result = parser.parse_quote_page(html, url)
        else:
            result = parser.parse_markets_page(html, url)

        if not result:
            raise NoDataFoundError(f"No data found in {url}")

        return result

    except ParsingError as e:
        logging.error(f"파싱 에러: {e}")
        # 에러 리포트 저장
        save_error_report(url, html, str(e))
        return None

    except Exception as e:
        logging.exception(f"예상치 못한 에러: {e}")
        save_error_report(url, html, str(e))
        return None


def save_error_report(url: str, html: str, error: str):
    """
    에러 발생 시 디버깅용 리포트 저장

    Args:
        url: 에러 발생 URL
        html: 문제가 있는 HTML
        error: 에러 메시지
    """
    import hashlib
    from datetime import datetime

    # 에러 리포트 디렉토리
    report_dir = 'error_reports'
    os.makedirs(report_dir, exist_ok=True)

    # 고유 파일명 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    filename = f"{timestamp}_{url_hash}.txt"

    filepath = os.path.join(report_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"URL: {url}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Error: {error}\n")
        f.write("\n" + "="*60 + "\n")
        f.write("HTML Content:\n")
        f.write("="*60 + "\n")
        f.write(html)

    logging.info(f"에러 리포트 저장됨: {filepath}")
```

### 5.5 파싱 성공률 모니터링

```python
from dataclasses import dataclass, field
from typing import Dict
from datetime import datetime


@dataclass
class ParsingStats:
    """파싱 통계 추적"""
    total_attempts: int = 0
    successful_parses: int = 0
    failed_parses: int = 0
    strategy_usage: Dict[str, int] = field(default_factory=dict)
    error_types: Dict[str, int] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)

    def record_success(self, strategy: str):
        """성공 기록"""
        self.total_attempts += 1
        self.successful_parses += 1
        self.strategy_usage[strategy] = self.strategy_usage.get(strategy, 0) + 1

    def record_failure(self, error_type: str):
        """실패 기록"""
        self.total_attempts += 1
        self.failed_parses += 1
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1

    @property
    def success_rate(self) -> float:
        """성공률 계산"""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_parses / self.total_attempts) * 100

    def print_report(self):
        """통계 리포트 출력"""
        runtime = datetime.now() - self.start_time

        print("\n" + "="*60)
        print("파싱 통계 리포트")
        print("="*60)
        print(f"실행 시간: {runtime}")
        print(f"총 시도: {self.total_attempts}")
        print(f"성공: {self.successful_parses}")
        print(f"실패: {self.failed_parses}")
        print(f"성공률: {self.success_rate:.2f}%")

        print("\n전략별 사용 횟수:")
        for strategy, count in sorted(self.strategy_usage.items(),
                                     key=lambda x: x[1], reverse=True):
            percentage = (count / self.successful_parses) * 100
            print(f"  {strategy}: {count} ({percentage:.1f}%)")

        if self.error_types:
            print("\n에러 타입별 발생 횟수:")
            for error_type, count in sorted(self.error_types.items(),
                                          key=lambda x: x[1], reverse=True):
                percentage = (count / self.failed_parses) * 100
                print(f"  {error_type}: {count} ({percentage:.1f}%)")
```

---

## 결론

이 문서는 Bloomberg 웹사이트에서 금융 데이터를 추출하기 위한 포괄적인 파싱 전략을 제공합니다.

**핵심 포인트**:

1. **다중 전략 접근**: JSON-LD → __NEXT_DATA__ → HTML 파싱 순서로 시도
2. **유연한 데이터 모델**: Optional 필드로 부분 데이터도 처리
3. **강력한 숫자 파싱**: 다양한 표기법 (K/M/B/T, %, 통화) 지원
4. **체계적인 테스트**: 단위 테스트부터 실전 테스트까지
5. **에러 처리**: 상세한 로깅 및 디버깅 지원

**다음 단계**:
- 실제 HTML 샘플로 테스트 데이터 구축
- 파싱 성공률 모니터링 및 개선
- 추가 Bloomberg 페이지 타입 지원 확장
