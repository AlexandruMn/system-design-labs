"""Personal Investment Dashboard - API contract (Lab 5).

!!! STUB IMPLEMENTATION !!!
Routes, models, validation, errors, authentication and examples are real and
drive the generated OpenAPI. Handlers only read tiny in-memory sample data;
there is no database, cache, Market Data Collector or Identity Provider here.
Every place marked `STUB` is replaced by a real integration later.
"""
from __future__ import annotations

import base64
import json
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

API_PREFIX = "/api/v1"

# Freshness policy from Labs 2-4 (provider timestamp, not cache time).
CURRENT_MAX_MIN = 15
STALE_MAX_MIN = 30
WATCHLIST_LIMIT = 100


# --------------------------------------------------------------------------
# Models (API fields are camelCase; stored fields are snake_case, see SOLUTION)
# --------------------------------------------------------------------------
class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Exchange(str, Enum):
    NASDAQ = "NASDAQ"
    NYSE = "NYSE"


class InstrumentType(str, Enum):
    COMMON_STOCK = "COMMON_STOCK"
    ADR = "ADR"


class PriceState(str, Enum):
    current = "current"          # age <= 15 min
    stale = "stale"              # 15 < age <= 30 min
    unavailable = "unavailable"  # age > 30 min or no accepted price


class StockSort(str, Enum):
    symbol = "symbol"      # market overview: A-Z
    trending = "trending"  # |changePercent| descending, then symbol


class PriceQuote(ApiModel):
    """Latest accepted price of one Stock, classified by provider timestamp."""

    symbol: str = Field(examples=["AAPL"])
    price: float | None = Field(
        None, description="Latest accepted price. `null` when state is `unavailable`; never 0 as a substitute.",
        examples=[231.42])
    previous_close: float | None = Field(None, examples=[229.10])
    change: float | None = Field(None, description="Derived: price - previousClose.", examples=[2.32])
    change_percent: float | None = Field(None, description="Derived: change / previousClose * 100.", examples=[1.01])
    currency: Literal["USD"] = "USD"
    state: PriceState
    provider_timestamp: datetime | None = Field(
        None, description="Source time from the Market Data Provider (ISO 8601 with offset).",
        examples=["2026-10-08T14:29:00-04:00"])
    age_seconds: int | None = Field(None, description="Derived at read time: now - providerTimestamp.", examples=[48])


class StockSummary(ApiModel):
    symbol: str = Field(examples=["AAPL"])
    name: str = Field(examples=["Apple Inc."])
    exchange: Exchange
    type: InstrumentType
    active: bool = Field(description="`false` for delisted/inactive instruments (history only).")
    price: PriceQuote


class StockDetail(StockSummary):
    country: str = Field(examples=["US"])
    currency: Literal["USD"] = "USD"


class PageInfo(ApiModel):
    limit: int = Field(examples=[20])
    next_cursor: str | None = Field(None, description="Opaque. `null` on the last page.", examples=["eyJzIjoiQUFQTCJ9"])
    has_more: bool


class StockPage(ApiModel):
    items: list[StockSummary]
    page: PageInfo


class DailyBar(ApiModel):
    """One trading day, derived from stored 1-minute price points."""

    date: date
    open: float
    high: float
    low: float
    close: float
    point_count: int = Field(description="Minute points used; at most 390 per regular day.", examples=[390])


class PriceHistory(ApiModel):
    symbol: str
    interval: Literal["1d"] = "1d"
    from_: date = Field(alias="from")
    to: date
    items: list[DailyBar] = Field(description="Ascending by date. Days without data are omitted, never filled with 0.")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class WatchlistItem(ApiModel):
    symbol: str
    name: str
    active: bool
    added_at: datetime = Field(examples=["2026-10-08T09:12:44-04:00"])
    price: PriceQuote


class Watchlist(ApiModel):
    items: list[WatchlistItem] = Field(description="Newest first. At most 100, so no pagination.")
    count: int = Field(description="Derived: len(items).")
    limit: int = Field(WATCHLIST_LIMIT, description="Maximum items per Watchlist.")


class AddWatchlistItem(ApiModel):
    symbol: str = Field(min_length=1, max_length=10, pattern=r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$", examples=["AAPL"])


class ErrorDetail(ApiModel):
    field: str | None = Field(None, examples=["limit"])
    issue: str = Field(examples=["must be between 1 and 100"])


class ErrorBody(ApiModel):
    code: str = Field(examples=["invalid_request"])
    message: str = Field(examples=["One or more parameters are invalid."])
    details: list[ErrorDetail] = []
    request_id: str = Field(examples=["req_8f3a1c"])


class ErrorResponse(ApiModel):
    error: ErrorBody


# --------------------------------------------------------------------------
# Errors: one JSON shape for every non-2xx response
# --------------------------------------------------------------------------
class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict | None = None):
        self.status, self.code, self.message, self.headers = status, code, message, headers or {}


def error_response(status: int, code: str, message: str, details: list | None = None, headers: dict | None = None):
    body = {"error": {"code": code, "message": message, "details": details or [], "requestId": "req_8f3a1c"}}
    return JSONResponse(body, status_code=status, headers=headers)


def ex(code: str, message: str, details: list | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or [], "requestId": "req_8f3a1c"}}


def err(description: str, code: str, message: str, details: list | None = None) -> dict:
    return {"model": ErrorResponse, "description": description,
            "content": {"application/json": {"example": ex(code, message, details)}}}


R400 = err("Invalid input.", "invalid_request", "One or more parameters are invalid.",
           [{"field": "limit", "issue": "must be between 1 and 100"}])
R401 = err("Missing, malformed, expired or invalid bearer token.", "unauthorized", "Authentication required.")
R404_STOCK = err("Unknown symbol.", "stock_not_found", "No Stock with symbol 'ZZZZ'.")
R429 = {"model": ErrorResponse, "description": "Rate limit exceeded. Wait `Retry-After` seconds, then retry.",
        "headers": {"Retry-After": {"description": "Seconds to wait.", "schema": {"type": "integer", "example": 2}}},
        "content": {"application/json": {"example": ex("rate_limited", "Too many requests.")}}}
R503 = err("Required data store unavailable. Nothing was changed.", "unavailable", "Service temporarily unavailable.")


# --------------------------------------------------------------------------
# Authentication - STUB. Real: validate the IdP-issued JWT (signature, exp, aud).
# The owner id is ALWAYS taken from the token's `sub`, never from path/body.
# --------------------------------------------------------------------------
def current_user_id(authorization: Annotated[str | None, Header(description="`Bearer <JWT from the external Identity Provider>`")] = None) -> str:
    if not authorization or not authorization.startswith("Bearer ") or len(authorization) < 12:
        raise ApiError(401, "unauthorized", "Authentication required.", {"WWW-Authenticate": "Bearer"})
    return "idp|user-123"  # STUB: pretend every well-formed token belongs to this user


UserId = Annotated[str, Depends(current_user_id)]


# --------------------------------------------------------------------------
# Sample data - STUB (replaces Market Data Store read replicas / User Data Store)
# --------------------------------------------------------------------------
NOW = datetime(2026, 10, 8, 14, 30, tzinfo=timezone(timedelta(hours=-4)))
_STOCKS = [  # symbol, name, exchange, type, active, price, prev_close, age_minutes
    ("AAPL", "Apple Inc.", "NASDAQ", "COMMON_STOCK", True, 231.42, 229.10, 1),
    ("MSFT", "Microsoft Corporation", "NASDAQ", "COMMON_STOCK", True, 521.18, 524.00, 1),
    ("TSM", "Taiwan Semiconductor Manufacturing", "NYSE", "ADR", True, 301.55, 290.00, 20),
    ("APLE", "Apple Hospitality REIT", "NYSE", "COMMON_STOCK", True, 14.20, 14.05, 1),
    ("OLDCO", "Old Co Holdings", "NYSE", "COMMON_STOCK", False, None, 3.10, 9999),
]
_WATCHLIST = {"AAPL": "2026-10-08T09:12:44-04:00", "OLDCO": "2026-09-01T10:00:00-04:00"}


def quote(symbol: str, price, prev, age_min) -> PriceQuote:
    if price is None or age_min > STALE_MAX_MIN:
        return PriceQuote(symbol=symbol, price=None, previous_close=None, change=None, change_percent=None,
                          state=PriceState.unavailable, provider_timestamp=None, age_seconds=None)
    state = PriceState.current if age_min <= CURRENT_MAX_MIN else PriceState.stale
    return PriceQuote(symbol=symbol, price=price, previous_close=prev, change=round(price - prev, 2),
                      change_percent=round((price - prev) / prev * 100, 2), state=state,
                      provider_timestamp=NOW - timedelta(minutes=age_min), age_seconds=age_min * 60)


def all_summaries() -> list[StockSummary]:
    return [StockSummary(symbol=s, name=n, exchange=e, type=t, active=a, price=quote(s, p, pc, age))
            for s, n, e, t, a, p, pc, age in _STOCKS]


def find(symbol: str) -> StockSummary:
    for s in all_summaries():
        if s.symbol == symbol.upper():
            return s
    raise ApiError(404, "stock_not_found", f"No Stock with symbol '{symbol.upper()}'.")


def encode_cursor(sort_value: float, symbol: str) -> str:
    return base64.urlsafe_b64encode(json.dumps({"v": sort_value, "s": symbol}).encode()).decode()


def decode_cursor(c: str) -> tuple[float, str]:
    try:
        d = json.loads(base64.urlsafe_b64decode(c.encode()))
        return float(d["v"]), str(d["s"])
    except Exception:
        raise ApiError(400, "invalid_cursor", "The cursor is invalid or expired.")


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------
app = FastAPI(
    title="Personal Investment Dashboard API",
    version="1.0.0",
    summary="Market data and private Watchlist (Lab 5 scope).",
    description=(
        "All paths are under `/api/v1`. Authenticate with `Authorization: Bearer <JWT>` issued by the "
        "external Identity Provider. Market data endpoints are readable by any authenticated user; "
        "Watchlist endpoints only ever touch the caller's own Watchlist.\n\n"
        "**Stub:** handlers return in-memory sample data; the contract is real."
    ),
    openapi_tags=[{"name": "Market", "description": "Public market data (cacheable)."},
                  {"name": "Watchlist", "description": "Private to the authenticated user (never cached)."}],
)


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, e: ApiError):
    return error_response(e.status, e.code, e.message, headers=e.headers)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, e: RequestValidationError):
    details = [{"field": ".".join(str(x) for x in err_["loc"][1:]) or None, "issue": err_["msg"]} for err_ in e.errors()]
    return error_response(400, "invalid_request", "One or more parameters are invalid.", details)


def page_example(items, limit, nxt, more):
    return {"items": items, "page": {"limit": limit, "nextCursor": nxt, "hasMore": more}}


_AAPL_Q = {"symbol": "AAPL", "price": 231.42, "previousClose": 229.1, "change": 2.32, "changePercent": 1.01,
           "currency": "USD", "state": "current", "providerTimestamp": "2026-10-08T14:29:00-04:00", "ageSeconds": 60}
_TSM_Q = {"symbol": "TSM", "price": 301.55, "previousClose": 290.0, "change": 11.55, "changePercent": 3.98,
          "currency": "USD", "state": "stale", "providerTimestamp": "2026-10-08T14:10:00-04:00", "ageSeconds": 1200}
_UNAVAIL_Q = {"symbol": "OLDCO", "price": None, "previousClose": None, "change": None, "changePercent": None,
              "currency": "USD", "state": "unavailable", "providerTimestamp": None, "ageSeconds": None}


@app.get(
    f"{API_PREFIX}/stocks", tags=["Market"], operation_id="listStocks", response_model=StockPage,
    summary="Market overview, trending, filter and search",
    description=(
        "One endpoint for four actions:\n\n"
        "* **Market overview** - `sort=symbol` (default), A-Z.\n"
        "* **Trending** - `sort=trending`: active Stocks with a non-unavailable price, ranked by "
        "`abs(changePercent)` descending, ties by `symbol` A-Z.\n"
        "* **Filter** - `exchange`, `type`, `active`.\n"
        "* **Search** - `q`, case-insensitive prefix match on symbol or substring of company name (2-50 chars).\n\n"
        "Cursor pagination. Public result: contains nothing user-specific, so it is cacheable (Lab 4)."
    ),
    responses={
        200: {"content": {"application/json": {"examples": {
            "trending_page": {"summary": "Trending, first page", "value": page_example(
                [{"symbol": "TSM", "name": "Taiwan Semiconductor Manufacturing", "exchange": "NYSE", "type": "ADR", "active": True, "price": _TSM_Q},
                 {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "type": "COMMON_STOCK", "active": True, "price": _AAPL_Q}],
                2, "eyJ2IjoxLjAxLCJzIjoiQUFQTCJ9", True)},
            "filtered_page": {"summary": "exchange=NASDAQ&type=COMMON_STOCK&q=app", "value": page_example(
                [{"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "type": "COMMON_STOCK", "active": True, "price": _AAPL_Q}],
                20, None, False)},
            "empty": {"summary": "No match (still 200)", "value": page_example([], 20, None, False)},
        }}}},
        400: R400, 401: R401, 429: R429, 503: R503,
    },
)
def list_stocks(
    _: UserId,
    q: Annotated[str | None, Query(min_length=2, max_length=50, description="Search by symbol prefix or company name.", examples=["app"])] = None,
    exchange: Annotated[Exchange | None, Query(description="Filter by exchange.")] = None,
    type: Annotated[InstrumentType | None, Query(description="Filter by instrument type.")] = None,
    active: Annotated[bool | None, Query(description="Default `true`: delisted Stocks are hidden unless `active=false`.")] = None,
    sort: Annotated[StockSort, Query(description="Ordering. See operation description.")] = StockSort.symbol,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size, 1-100.")] = 20,
    cursor: Annotated[str | None, Query(description="`page.nextCursor` of the previous page. Valid only with the same filters and sort.")] = None,
):
    wanted_active = True if active is None else active
    rows = [s for s in all_summaries() if s.active == wanted_active]
    if q:
        ql = q.lower()
        rows = [s for s in rows if s.symbol.lower().startswith(ql) or ql in s.name.lower()]
    if exchange:
        rows = [s for s in rows if s.exchange == exchange]
    if type:
        rows = [s for s in rows if s.type == type]

    def key(s: StockSummary):
        if sort == StockSort.trending:
            return (-(abs(s.price.change_percent)), s.symbol)
        return (0.0, s.symbol)

    if sort == StockSort.trending:
        rows = [s for s in rows if s.price.state != PriceState.unavailable]
    rows.sort(key=key)
    if cursor:
        v, sym = decode_cursor(cursor)
        rows = [s for s in rows if (-abs(s.price.change_percent) if sort == StockSort.trending else 0.0, s.symbol) > (v, sym)]
    more = len(rows) > limit
    rows = rows[:limit]
    nxt = encode_cursor(key(rows[-1])[0], rows[-1].symbol) if more else None
    return StockPage(items=rows, page=PageInfo(limit=limit, next_cursor=nxt, has_more=more))


SymbolPath = Annotated[str, Path(min_length=1, max_length=10, pattern=r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$", examples=["AAPL"],
                                 description="Ticker symbol, case-insensitive.")]


@app.get(
    f"{API_PREFIX}/stocks/{{symbol}}", tags=["Market"], operation_id="getStock", response_model=StockDetail,
    summary="Stock detail (reference data + latest price)",
    responses={200: {"content": {"application/json": {"example": {
        "symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "type": "COMMON_STOCK", "active": True,
        "country": "US", "currency": "USD", "price": _AAPL_Q}}}},
        400: R400, 401: R401, 404: R404_STOCK, 429: R429, 503: R503},
)
def get_stock(symbol: SymbolPath, _: UserId):
    s = find(symbol)
    return StockDetail(**s.model_dump(), country="US", currency="USD")


@app.get(
    f"{API_PREFIX}/stocks/{{symbol}}/price", tags=["Market"], operation_id="getStockPrice", response_model=PriceQuote,
    summary="Latest accepted price (cheap polling endpoint)",
    description="Reads already-synchronized data; never calls the Market Data Provider. "
                "`state` follows the provider-timestamp policy: current <=15 min, stale <=30 min, else unavailable (`price: null`).",
    responses={200: {"content": {"application/json": {"examples": {
        "current": {"value": _AAPL_Q}, "stale": {"value": _TSM_Q}, "unavailable": {"value": _UNAVAIL_Q}}}}},
        400: R400, 401: R401, 404: R404_STOCK, 429: R429, 503: R503},
)
def get_price(symbol: SymbolPath, _: UserId):
    return find(symbol).price


@app.get(
    f"{API_PREFIX}/stocks/{{symbol}}/history", tags=["Market"], operation_id="getStockHistory", response_model=PriceHistory,
    response_model_by_alias=True, summary="Daily price history",
    description="Daily bars derived from stored 1-minute points. Range is at most 366 days (1-year retention), "
                "so the result is bounded (max 366 items) and has no cursor. Works for delisted Stocks.",
    responses={200: {"content": {"application/json": {"example": {
        "symbol": "AAPL", "interval": "1d", "from": "2026-10-06", "to": "2026-10-07",
        "items": [{"date": "2026-10-06", "open": 227.9, "high": 230.1, "low": 226.8, "close": 229.1, "pointCount": 390},
                  {"date": "2026-10-07", "open": 229.3, "high": 232.0, "low": 228.7, "close": 231.0, "pointCount": 390}]}}}},
        400: err("Invalid range.", "invalid_request", "One or more parameters are invalid.",
                 [{"field": "from", "issue": "range must not exceed 366 days"}]),
        401: R401, 404: R404_STOCK, 429: R429, 503: R503},
)
def get_history(
    symbol: SymbolPath, _: UserId,
    from_: Annotated[date | None, Query(alias="from", description="Inclusive start date. Default: `to` minus 29 days.")] = None,
    to: Annotated[date | None, Query(description="Inclusive end date. Default: today (exchange time).")] = None,
):
    find(symbol)
    end = to or NOW.date()
    start = from_ or end - timedelta(days=29)
    if start > end or (end - start).days > 365:
        raise ApiError(400, "invalid_request", "One or more parameters are invalid.")
    items = [DailyBar(date=date(2026, 10, 6), open=227.9, high=230.1, low=226.8, close=229.1, point_count=390)]  # STUB
    return PriceHistory(symbol=symbol.upper(), from_=start, to=end, items=[i for i in items if start <= i.date <= end])


_WL_ITEM = {"symbol": "AAPL", "name": "Apple Inc.", "active": True, "addedAt": "2026-10-08T09:12:44-04:00", "price": _AAPL_Q}


@app.get(
    f"{API_PREFIX}/watchlist", tags=["Watchlist"], operation_id="getWatchlist", response_model=Watchlist,
    summary="Read my Watchlist",
    description="Private. Owner = token `sub`. Always read from the User Data Store (never a shared cache), "
                "so it reflects every previously confirmed change (read-your-writes). Delisted entries stay, with `active: false`.",
    responses={200: {"content": {"application/json": {"examples": {
        "with_items": {"value": {"items": [_WL_ITEM], "count": 1, "limit": 100}},
        "empty": {"value": {"items": [], "count": 0, "limit": 100}}}}}},
        401: R401, 429: R429, 503: R503},
)
def get_watchlist(user: UserId):
    items = []
    for sym, added in _WATCHLIST.items():
        s = find(sym)
        items.append(WatchlistItem(symbol=s.symbol, name=s.name, active=s.active,
                                   added_at=datetime.fromisoformat(added), price=s.price))
    items.sort(key=lambda i: i.added_at, reverse=True)
    return Watchlist(items=items, count=len(items), limit=WATCHLIST_LIMIT)


@app.post(
    f"{API_PREFIX}/watchlist/items", tags=["Watchlist"], operation_id="addWatchlistItem", response_model=WatchlistItem,
    status_code=201, summary="Add a Stock to my Watchlist",
    description="Idempotent: adding a Stock that is already present returns `200` with the existing item. "
                "Success is returned only after the write is confirmed in the User Data Store.",
    responses={
        200: {"model": WatchlistItem, "description": "Already in the Watchlist; nothing changed."},
        201: {"description": "Added.", "content": {"application/json": {"example": _WL_ITEM}}},
        400: err("Invalid body.", "invalid_request", "One or more parameters are invalid.",
                 [{"field": "body.symbol", "issue": "String should match pattern '^[A-Za-z][A-Za-z0-9.\\-]{0,9}$'"}]),
        401: R401, 404: R404_STOCK,
        409: err("Stock is inactive/delisted, or the Watchlist already has 100 items.", "stock_inactive",
                 "'OLDCO' is delisted and cannot be added."),
        429: R429, 503: R503},
)
def add_item(body: AddWatchlistItem, user: UserId):
    s = find(body.symbol)
    if not s.active:
        raise ApiError(409, "stock_inactive", f"'{s.symbol}' is delisted and cannot be added.")
    if len(_WATCHLIST) >= WATCHLIST_LIMIT:
        raise ApiError(409, "watchlist_full", "The Watchlist already has 100 items.")
    if s.symbol in _WATCHLIST:  # STUB: real code does INSERT ... ON CONFLICT DO NOTHING
        return JSONResponse(WatchlistItem(symbol=s.symbol, name=s.name, active=True,
                                          added_at=datetime.fromisoformat(_WATCHLIST[s.symbol]), price=s.price
                                          ).model_dump(mode="json", by_alias=True), status_code=200)
    _WATCHLIST[s.symbol] = NOW.isoformat()  # STUB
    return WatchlistItem(symbol=s.symbol, name=s.name, active=True, added_at=NOW, price=s.price)


@app.delete(
    f"{API_PREFIX}/watchlist/items/{{symbol}}", tags=["Watchlist"], operation_id="removeWatchlistItem",
    status_code=204, response_class=Response, summary="Remove a Stock from my Watchlist",
    description="Works for delisted entries too. Success only after the delete is confirmed.",
    responses={
        204: {"description": "Removed."},
        400: R400, 401: R401,
        404: err("Symbol is not in the caller's Watchlist.", "watchlist_item_not_found", "'MSFT' is not in your Watchlist."),
        429: R429, 503: R503},
)
def remove_item(symbol: SymbolPath, user: UserId):
    sym = symbol.upper()
    if sym not in _WATCHLIST:
        raise ApiError(404, "watchlist_item_not_found", f"'{sym}' is not in your Watchlist.")
    del _WATCHLIST[sym]  # STUB
    return Response(status_code=204)
