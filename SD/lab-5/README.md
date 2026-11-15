# Laboratorul 5: Modelează Dashboard-ul și definește API-ul

## Personal Investment Dashboard

## Context

În Laboratoarele 1–4 am stabilit produsul, țintele de calitate, limita sistemului și traseul de citire scalat. Aici descriu **modelul de date** și **API-ul HTTP** pentru domeniul de piață și pentru Watchlist, apoi generez OpenAPI dintr-un cod sursă care respectă proiectarea.

```text
Model de date -> endpoint-uri -> definiții în cod -> OpenAPI -> flux client
```

Reguli păstrate din laboratoarele anterioare:

- utilizatorul este autentificat printr-un Identity Provider extern (fără tabel local `User`, fără endpoint-uri de autentificare);
- citirile utilizatorului nu apelează Market Data Provider; Collector-ul este o integrare de server, nu un endpoint client;
- prospețime după **provider timestamp**: ≤ 15 min `current`, 15–30 min `stale`, > 30 min sau lipsă `unavailable`; un preț lipsă nu este niciodată `0`;
- Watchlist-ul este privat, nu intră în cache-ul partajat și respectă *read-your-writes*;
- piața SUA, Nasdaq + NYSE, common stock + ADR; instrumentele delistate rămân pentru istoric.

În afara scopului: Orders, Holdings, profit/pierdere, SSE, partajare publică.

---

# 1. Modelul de date

## 1.1 Entități

| Entitate | Scop | Identitate | Relații | Proprietar |
|---|---|---|---|---|
| `stock` | Date de referință pentru Search/Filter/detaliu | `symbol` | 1 — 1 `latest_price`; 1 — N `price_point`; 1 — N `watchlist_item` | Market Data Store (scris doar de Collector) |
| `latest_price` | Ultimul preț acceptat pentru Stock price/Overview | `symbol` (și FK către `stock`) | N — 1 `stock` (cel mult unul pe Stock) | Market Data Store |
| `price_point` | Un punct de preț la 1 minut pentru History | (`symbol`, `point_timestamp`) | N — 1 `stock` | Market Data Store |
| `sync_run` | Înregistrare **internă** a unei sincronizări Collector (diagnostic, cât de proaspete sunt datele) | `sync_run_id` | nu are FK către utilizator; referă simbolurile doar prin numere agregate | Market Data Store, **neexpusă** clientului |
| `watchlist` | Lista privată a unui utilizator | `watchlist_id`; `owner_id` unic | 1 — N `watchlist_item`; aparține unui utilizator extern | User Data Store |
| `watchlist_item` | Un Stock urmărit | (`watchlist_id`, `symbol`) | N — 1 `watchlist`; N — 1 `stock` | User Data Store |
| *Utilizator (extern)* | Identitate emisă de Identity Provider | `sub` din token → `owner_id` | referit doar prin `owner_id` | Identity Provider, nu îl stocăm |

## 1.2 Diagrama ER

```mermaid
erDiagram
    IDP_USER ||--o| WATCHLIST : "owner_id = sub (extern)"
    WATCHLIST ||--o{ WATCHLIST_ITEM : "conține (max 100)"
    STOCK ||--o{ WATCHLIST_ITEM : "este urmărit în"
    STOCK ||--o| LATEST_PRICE : "are"
    STOCK ||--o{ PRICE_POINT : "are istoric 1 minut, retenție 1 an"
    SYNC_RUN }o..o{ LATEST_PRICE : "actualizează (intern, fără FK)"

    IDP_USER {
        string sub "extern, nu e stocat local"
    }
    STOCK {
        string symbol PK
        string company_name
        string exchange
        string instrument_type
        string currency
        string country
        boolean active
    }
    LATEST_PRICE {
        string symbol PK, FK
        decimal latest_price
        decimal previous_close
        datetime provider_timestamp
        datetime accepted_at
    }
    PRICE_POINT {
        string symbol PK, FK
        datetime point_timestamp PK
        decimal price
    }
    SYNC_RUN {
        string sync_run_id PK
        datetime started_at
        datetime finished_at
        string outcome
        int symbols_received
        int symbols_accepted
        datetime provider_timestamp_max
    }
    WATCHLIST {
        string watchlist_id PK
        string owner_id "unic"
        datetime created_at
    }
    WATCHLIST_ITEM {
        string watchlist_id PK, FK
        string symbol PK, FK
        datetime added_at
    }
```

Proprietatea datelor: `stock`, `latest_price`, `price_point`, `sync_run` sunt scrise numai de Market Data Collector. `watchlist` și `watchlist_item` sunt scrise numai de Dashboard în numele proprietarului din token.

## 1.3 Câmpuri

Câmpurile stocate sunt `snake_case`; în API apar `camelCase`. Tipurile SQL, constrângerile și indexurile sunt etapa următoare.

### `stock`

| Câmp stocat | Câmp API | Semnificație | Exemplu | Valoare lipsă |
|---|---|---|---|---|
| `symbol` | `symbol` | Ticker, majuscule, identitate | `AAPL` | obligatoriu |
| `company_name` | `name` | Denumirea companiei | `Apple Inc.` | obligatoriu; înregistrarea fără nume este respinsă la sincronizare |
| `exchange` | `exchange` | `NASDAQ` sau `NYSE` | `NASDAQ` | obligatoriu |
| `instrument_type` | `type` | `COMMON_STOCK` sau `ADR` | `COMMON_STOCK` | obligatoriu |
| `currency` | `currency` | Moneda cotației | `USD` | implicit `USD` (piața SUA) |
| `country` | `country` | Țara listării | `US` | implicit `US` |
| `active` | `active` | `false` dacă este delistat/inactiv (nu mai poate intra în Watchlist; istoricul rămâne) | `true` | obligatoriu; înlocuiește `status` din Lab 2 (`ACTIVE`/`DELISTED` → boolean) |

### `latest_price`

| Câmp stocat | Câmp API | Semnificație | Exemplu | Valoare lipsă |
|---|---|---|---|---|
| `symbol` | `symbol` | Stock-ul | `AAPL` | obligatoriu |
| `latest_price` | `price` | Ultimul preț **acceptat** | `231.42` | `null` → `state = unavailable`; niciodată `0` |
| `previous_close` | `previousClose` | Închiderea anterioară | `229.10` | `null` → `change`/`changePercent` sunt `null` |
| `provider_timestamp` | `providerTimestamp` | Ora sursei (furnizorului) | `2026-10-08T14:29:00-04:00` | `null` → `unavailable` |
| `accepted_at` | — (intern) | Când l-a acceptat Collector-ul; **nu** înlocuiește `provider_timestamp` | `2026-10-08T14:29:08-04:00` | obligatoriu |

### `price_point`

| Câmp stocat | Câmp API | Semnificație | Exemplu | Valoare lipsă |
|---|---|---|---|---|
| `symbol` | `symbol` | Stock-ul | `AAPL` | obligatoriu |
| `point_timestamp` | (în `date`) | Minutul sursei | `2026-10-08T14:29:00-04:00` | obligatoriu |
| `price` | `open/high/low/close` (agregat) | Preț la acel minut | `231.42` | punctul lipsă **nu este creat**; zilele fără date sunt omise din răspuns |

### `watchlist` / `watchlist_item`

| Câmp stocat | Câmp API | Semnificație | Exemplu | Valoare lipsă |
|---|---|---|---|---|
| `watchlist.owner_id` | — (niciodată în API) | `sub` din token | `idp\|user-123` | obligatoriu, unic |
| `watchlist_item.symbol` | `symbol` | Stock urmărit | `AAPL` | obligatoriu |
| `watchlist_item.added_at` | `addedAt` | Momentul confirmării scrierii | `2026-10-08T09:12:44-04:00` | obligatoriu, setat de server |

### `sync_run` (intern)

`sync_run_id`, `started_at`, `finished_at`, `outcome` (`success` / `partial` / `failed`), `symbols_received`, `symbols_accepted`, `provider_timestamp_max`. Un `outcome = failed` **nu șterge** ultimele valori valide din `latest_price` (regula din Lab 3).

## 1.4 Fapte stocate vs. valori derivate

| Valoare | Tip | Cum se obține |
|---|---|---|
| `latest_price`, `previous_close`, `provider_timestamp`, `active`, `added_at` | stocată | scrisă de Collector / Dashboard |
| `state` (`current`/`stale`/`unavailable`) | **derivată** | din `now − provider_timestamp` la momentul citirii, cu pragurile 15/30 min. *Schimbare față de Lab 2*: nu o stochez (`price_state`), fiindcă se schimbă fără nicio scriere |
| `ageSeconds` | derivată | `now − provider_timestamp` |
| `change`, `changePercent` | derivate | `price − previous_close`; `change / previous_close × 100` |
| `count` din Watchlist | derivată | numărul de `watchlist_item` |
| bare zilnice `open/high/low/close/pointCount` | derivate | agregare a `price_point` pe zi de tranzacționare (max 390 puncte/zi) |
| `hasMore`, `nextCursor` | derivate | din ordonare și limită |

## 1.5 Clasamentul „Trending”

`sort=trending` = Stock-uri **active** cu `state ≠ unavailable`, ordonate descrescător după `abs(changePercent)`, apoi după `symbol` A–Z (ordine totală, deci cursorul este stabil). Un Stock fără preț valid nu poate fi clasat și este exclus (nu primește `0`). Este o regulă simplă, explicabilă, calculabilă din date deja sincronizate; volumul nu face parte din model.

---

# 2. Endpoint-uri client

Bază: `https://api.dashboard.example/api/v1` (domeniu fictiv). Toate cer `Authorization: Bearer <JWT>`.

## 2.1 Inventar

| Acțiune de produs | Metodă și cale | Parametri / corp | Succes | Acces |
|---|---|---|---|---|
| Market overview | `GET /api/v1/stocks` | `sort=symbol` (implicit), `limit`, `cursor` | `200` pagină | autentificat; date publice |
| Trending | `GET /api/v1/stocks?sort=trending` | `limit`, `cursor` | `200` pagină | autentificat; date publice |
| Filtrare | `GET /api/v1/stocks` | `exchange`, `type`, `active` | `200` pagină | autentificat; date publice |
| Căutare după nume/simbol | `GET /api/v1/stocks` | `q` (2–50 caractere) | `200` pagină | autentificat; date publice |
| Detaliu Stock | `GET /api/v1/stocks/{symbol}` | `symbol` | `200` | autentificat; date publice |
| Ultimul preț acceptat | `GET /api/v1/stocks/{symbol}/price` | `symbol` | `200` | autentificat; date publice |
| Istoric zilnic | `GET /api/v1/stocks/{symbol}/history` | `from`, `to` | `200` | autentificat; date publice |
| Citire Watchlist | `GET /api/v1/watchlist` | — | `200` | **doar proprietarul** (din token) |
| Adăugare în Watchlist | `POST /api/v1/watchlist/items` | corp `{ "symbol" }` | `201` (nou) / `200` (exista) | doar proprietarul |
| Eliminare din Watchlist | `DELETE /api/v1/watchlist/items/{symbol}` | `symbol` | `204` | doar proprietarul |

Un singur `GET /stocks` acoperă patru acțiuni (overview, trending, filtrare, căutare) prin parametri. Nu există niciun endpoint care primește un `userId`: proprietarul vine **numai** din token, deci nu se poate cere Watchlist-ul altcuiva.

## 2.2 Politici comune

| Politică | Decizie |
|---|---|
| **Versiune** | În cale: `/api/v1`. *Schimbare compatibilă*: adăugarea unui câmp opțional în răspuns (de ex. `volume`) sau a unui filtru opțional — clienții ignoră câmpurile necunoscute. *Schimbare incompatibilă*: redenumirea `changePercent` sau schimbarea semnificației `state` → `/api/v2`, `v1` rămâne activ o perioadă de tranziție. |
| **Autentificare** | JWT „Bearer” emis de Identity Provider extern; Dashboard verifică semnătura, `exp`, `aud`; `sub` = `owner_id`. Lipsă/invalid/expirat → `401` + `WWW-Authenticate: Bearer`. |
| **Autorizare** | Fiecare citire/modificare de Watchlist filtrează pe `owner_id = sub`. Datele de piață sunt aceleași pentru toți utilizatorii autentificați. |
| **Paginare** | Cursor opac. `limit` 1–100, implicit 20. Răspuns `page: { limit, nextCursor, hasMore }`. `nextCursor = null` la ultima pagină. Cursorul este valid doar cu aceiași filtre și același `sort`; altfel `400 invalid_cursor`. Watchlist (max 100) și istoricul (max 366 zile) sunt mărginite, deci fără cursor. |
| **Rate limit `429`** | Pe utilizator. Răspunsul include `Retry-After` (secunde). Clientul oprește cererile pe acel endpoint, așteaptă cel puțin `Retry-After`, reîncearcă cu *backoff* exponențial + jitter (max 3 încercări) și afișează ultimele date cu marcajul vechimii. Cererile de modificare se reîncearcă doar fiindcă sunt idempotente (§2.3). |
| **Format de eroare** | Unul singur pentru orice non-2xx. |
| **Statusuri** | `200/201/204`; `400` input invalid; `401`; `404`; `409` conflict de stare; `429`; `503` stocare indisponibilă. |
| **Timp** | ISO 8601 cu offset. Prețurile sunt numere, moneda `USD`. |

Eroare (același format peste tot):

```json
{
  "error": {
    "code": "invalid_request",
    "message": "One or more parameters are invalid.",
    "details": [{ "field": "limit", "issue": "must be between 1 and 100" }],
    "requestId": "req_8f3a1c"
  }
}
```

Coduri folosite: `invalid_request`, `invalid_cursor`, `unauthorized`, `stock_not_found`, `stock_inactive`, `watchlist_full`, `watchlist_item_not_found`, `rate_limited`, `unavailable`.

Apelurile Collector → Market Data Provider sunt **integrări de server** (pull la 1 minut). Nu au endpoint client, iar copiile din cache (L1/Redis din Lab 4) nu au endpoint propriu.

## 2.3 Detalii pe operație

### `GET /api/v1/stocks` — overview / trending / filtru / căutare

| Parametru | Validare | Implicit |
|---|---|---|
| `q` | 2–50 caractere; prefix pe `symbol` sau subșir în nume, fără diferență majuscule/minuscule | — |
| `exchange` | `NASDAQ` \| `NYSE` | toate |
| `type` | `COMMON_STOCK` \| `ADR` | toate |
| `active` | boolean | `true` (delistatele se văd doar cu `active=false`) |
| `sort` | `symbol` \| `trending` | `symbol` |
| `limit` | întreg 1–100 | 20 |
| `cursor` | opac | prima pagină |

Ordonare: `symbol` A–Z, sau `trending` (§1.5). Răspuns `StockPage`. Nu conține nimic specific utilizatorului, deci rămâne cache-abil conform Lab 4.

**Pagină filtrată** — `GET /api/v1/stocks?exchange=NASDAQ&type=COMMON_STOCK&q=app`

```json
{
  "items": [
    {
      "symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "type": "COMMON_STOCK", "active": true,
      "price": { "symbol": "AAPL", "price": 231.42, "previousClose": 229.1, "change": 2.32, "changePercent": 1.01,
                 "currency": "USD", "state": "current", "providerTimestamp": "2026-10-08T14:29:00-04:00", "ageSeconds": 60 }
    }
  ],
  "page": { "limit": 20, "nextCursor": null, "hasMore": false }
}
```

**Rezultat gol** — `GET /api/v1/stocks?q=zz` → `200` (nu `404`):

```json
{ "items": [], "page": { "limit": 20, "nextCursor": null, "hasMore": false } }
```

**Trending, prima pagină** — `GET /api/v1/stocks?sort=trending&limit=2` returnează `TSM` (`+3.98%`, `state: "stale"`) apoi `AAPL` (`+1.01%`), `hasMore: true` și un `nextCursor`.

Erori: `400` (`limit=500`, `cursor` invalid, `q` prea scurt), `401`, `429`, `503`.

### `GET /api/v1/stocks/{symbol}` — detaliu

`200`:

```json
{
  "symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "type": "COMMON_STOCK", "active": true,
  "country": "US", "currency": "USD",
  "price": { "symbol": "AAPL", "price": 231.42, "previousClose": 229.1, "change": 2.32, "changePercent": 1.01,
             "currency": "USD", "state": "current", "providerTimestamp": "2026-10-08T14:29:00-04:00", "ageSeconds": 60 }
}
```

`symbol`: 1–10 caractere `[A-Za-z][A-Za-z0-9.-]*`, insensibil la majuscule. Erori: `400`, `401`, `404 stock_not_found`.

### `GET /api/v1/stocks/{symbol}/price` — ultimul preț acceptat

Același obiect `price` ca mai sus; endpoint ușor pentru reîmprospătare (Stock price este citirea cu cel mai mare trafic, 600 RPS pentru 3.000 de utilizatori). Cele trei stări:

```json
{ "symbol": "AAPL", "price": 231.42, "previousClose": 229.1, "change": 2.32, "changePercent": 1.01, "currency": "USD", "state": "current",     "providerTimestamp": "2026-10-08T14:29:00-04:00", "ageSeconds": 60 }
{ "symbol": "TSM",  "price": 301.55, "previousClose": 290.0, "change": 11.55, "changePercent": 3.98, "currency": "USD", "state": "stale",       "providerTimestamp": "2026-10-08T14:10:00-04:00", "ageSeconds": 1200 }
{ "symbol": "OLDCO","price": null,   "previousClose": null,  "change": null,  "changePercent": null, "currency": "USD", "state": "unavailable", "providerTimestamp": null, "ageSeconds": null }
```

`unavailable` este un rezultat **valid** (`200`) cu `price: null`, nu o eroare HTTP și nu `0`. `503` rămâne pentru cazul în care nici Market Data Store, nici cache-ul nu pot răspunde.

### `GET /api/v1/stocks/{symbol}/history` — istoric zilnic

| Parametru | Validare | Implicit |
|---|---|---|
| `from` | dată `YYYY-MM-DD`, inclusiv | `to` − 29 zile |
| `to` | dată, inclusiv | astăzi |

`from ≤ to` și intervalul ≤ 366 zile (retenție 1 an) altfel `400`. Ordine: crescător după dată; max 366 elemente. Funcționează și pentru Stock-uri delistate.

```json
{
  "symbol": "AAPL", "interval": "1d", "from": "2026-10-06", "to": "2026-10-07",
  "items": [
    { "date": "2026-10-06", "open": 227.9, "high": 230.1, "low": 226.8, "close": 229.1, "pointCount": 390 },
    { "date": "2026-10-07", "open": 229.3, "high": 232.0, "low": 228.7, "close": 231.0, "pointCount": 390 }
  ]
}
```

Zilele fără date lipsesc din listă; nu sunt completate cu `0`.

### `GET /api/v1/watchlist`

Privat; citit mereu din User Data Store (niciodată din cache partajat), deci reflectă orice modificare deja confirmată. Intrările delistate rămân, cu `active: false` și `price.state = unavailable`. Ordine: cele mai noi primele.

```json
{
  "items": [
    { "symbol": "AAPL", "name": "Apple Inc.", "active": true, "addedAt": "2026-10-08T09:12:44-04:00",
      "price": { "symbol": "AAPL", "price": 231.42, "previousClose": 229.1, "change": 2.32, "changePercent": 1.01,
                 "currency": "USD", "state": "current", "providerTimestamp": "2026-10-08T14:29:00-04:00", "ageSeconds": 60 } }
  ],
  "count": 1,
  "limit": 100
}
```

Watchlist gol: `{ "items": [], "count": 0, "limit": 100 }` cu `200`.

### `POST /api/v1/watchlist/items`

Corp (doar câmpul din client; `addedAt`, `owner` sunt controlate de server și nu sunt acceptate):

```json
{ "symbol": "AAPL" }
```

| Caz | Răspuns |
|---|---|
| adăugat | `201` + `WatchlistItem` (la fel ca elementul de mai sus) |
| era deja în listă | `200` + elementul existent (idempotent, sigur la retry) |
| `symbol` nevalid | `400 invalid_request` |
| Stock inexistent | `404 stock_not_found` |
| Stock delistat | `409 stock_inactive` |
| 100 de elemente | `409 watchlist_full` |
| scriere eșuată | `503 unavailable` — nu s-a modificat nimic, UI nu afirmă succesul |

Succesul se întoarce **numai după** confirmarea scrierii (Lab 3, secvența C).

### `DELETE /api/v1/watchlist/items/{symbol}`

`204` fără corp după confirmare. `404 watchlist_item_not_found` dacă nu este în Watchlist-ul apelantului (un simbol din Watchlist-ul altcuiva arată identic: nu se află că există). Funcționează și pentru intrări delistate. Erori: `400`, `401`, `429`, `503`.

---

# 3. OpenAPI generat din cod

## 3.1 Sursa

Framework: **FastAPI** (Pydantic v2).

| Fișier | Rol |
|---|---|
| [`app/main.py`](app/main.py) | rute, modele, validări, erori, autentificare, exemple. **Handlerele sunt stub-uri** marcate `STUB`, cu date de probă în memorie |
| [`generate_openapi.py`](generate_openapi.py) | scrie `openapi.json` și `openapi.yaml` din `app.openapi()` |
| [`requirements.txt`](requirements.txt) | dependențe |
| [`openapi.yaml`](openapi.yaml) / [`openapi.json`](openapi.json) | documentul generat |

Câmpurile din API sunt `camelCase` prin `alias_generator=to_camel` (modelele rămân `snake_case` în cod). Erorile de validare Pydantic (implicit `422`) sunt mapate la `400` cu formatul unic de eroare.

## 3.2 Comenzi

```bash
cd SD/lab-5
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python generate_openapi.py                      # -> openapi.json, openapi.yaml
uvicorn app.main:app --reload                   # Swagger UI: http://127.0.0.1:8000/docs
```

## 3.3 Verificare

Document verificat cu `openapi-spec-validator` (pe `openapi.json`): `OK`. Am comparat apoi inventarul din §2.1 cu `paths` din document:

| Inventar §2.1 | În OpenAPI (`operationId`) | Exemple în document |
|---|---|---|
| overview / trending / filtru / căutare | `GET /api/v1/stocks` (`listStocks`) | `trending_page`, `filtered_page`, `empty`; erori `400/401/429/503` |
| detaliu | `GET /api/v1/stocks/{symbol}` (`getStock`) | `200`, `404` |
| preț | `GET /api/v1/stocks/{symbol}/price` (`getStockPrice`) | `current`, `stale`, `unavailable` |
| istoric | `GET /api/v1/stocks/{symbol}/history` (`getStockHistory`) | `200`, `400` interval invalid |
| citire Watchlist | `GET /api/v1/watchlist` (`getWatchlist`) | `with_items`, `empty` |
| adăugare | `POST /api/v1/watchlist/items` (`addWatchlistItem`) | `201`, `200`, `400`, `404`, `409` |
| eliminare | `DELETE /api/v1/watchlist/items/{symbol}` (`removeWatchlistItem`) | `204`, `404` |

Cele 7 rute din document corespund celor 10 acțiuni din inventar (patru acțiuni pe `listStocks`). Am apelat și fiecare exemplu cu `TestClient` pe stub-uri: pagină filtrată (`200`), listă goală (`200`), `limit=500` → `400` în formatul unic de eroare, fără token → `401`, simbol necunoscut → `404`, `POST` dublu → `201` apoi `200`, delistat → `409`, `DELETE` → `204`, al doilea `DELETE` → `404`, pagina a doua cu `cursor` → `200`.

Captură din viewerul Swagger UI (`uvicorn app.main:app`, pagina `/docs`), construit din documentul generat:

![Swagger UI: prezentare generală și rutele Market](assets/swagger-overview.png)

![Swagger UI: rutele Watchlist](assets/swagger-watchlist.png)

![Swagger UI: GET /api/v1/stocks, descriere și parametri](assets/swagger-list-stocks.png)

Documentul poate fi deschis și în [Swagger Editor](https://editor.swagger.io/) (lipește `openapi.yaml`).

---

# 4. Flux client

```text
Deschide Stock-urile trending -> deschide un Stock pentru mai multe date -> adaugă-l în Watchlist
```

Token-ul se obține de la Identity Provider (în afara API-ului nostru) și se trimite la fiecare cerere:
`Authorization: Bearer eyJhbGciOi…`. Bază: `https://api.dashboard.example/api/v1`.

## 4.1 Apeluri în ordine

| # | Apel | Scop |
|---|---|---|
| 1 | `GET /stocks?sort=trending&limit=10` | lista trending |
| 2 | `GET /stocks/TSM` | ecranul de detaliu: date de referință + ultimul preț |
| 3 | `GET /stocks/TSM/history?from=2026-09-09&to=2026-10-08` | graficul zilnic (30 de zile) |
| 4 | `GET /stocks/TSM/price` | reîmprospătarea prețului (repetat, respectând `429`) |
| 5 | `POST /watchlist/items` cu `{"symbol":"TSM"}` | adăugare în Watchlist |
| 6 | `GET /watchlist` | confirmare/reafișare a listei (read-your-writes) |

Pașii 2–4 pot porni în paralel după ce utilizatorul alege Stock-ul.

Exemple (pașii 1, 2, 5 — răspunsurile sunt cele din §2.3):

```http
GET /api/v1/stocks?sort=trending&limit=10 HTTP/1.1
Host: api.dashboard.example
Authorization: Bearer eyJhbGciOi…
```
→ `200`, `items[0].symbol = "TSM"`, `price.state = "stale"`.

```http
GET /api/v1/stocks/TSM HTTP/1.1
Authorization: Bearer eyJhbGciOi…
```
→ `200` cu `StockDetail` (`price.state` = `stale`, `providerTimestamp` = `2026-10-08T14:10:00-04:00`).

```http
POST /api/v1/watchlist/items HTTP/1.1
Authorization: Bearer eyJhbGciOi…
Content-Type: application/json

{ "symbol": "TSM" }
```
→ `201`:
```json
{ "symbol": "TSM", "name": "Taiwan Semiconductor Manufacturing", "active": true, "addedAt": "2026-10-08T14:31:02-04:00",
  "price": { "symbol": "TSM", "price": 301.55, "previousClose": 290.0, "change": 11.55, "changePercent": 3.98,
             "currency": "USD", "state": "stale", "providerTimestamp": "2026-10-08T14:10:00-04:00", "ageSeconds": 1262 } }
```

## 4.2 Ce arată UI

| Ecran / apel | Încărcare | Succes | Listă goală | Eroare |
|---|---|---|---|---|
| Trending (1) | schelet de listă (rânduri placeholder) | rânduri cu simbol, nume, preț, `changePercent`; `stale` apare ca „preț vechi · 20 min”, cu timpul furnizorului, nu ca preț curent | „Nu există Stock-uri trending acum” (de ex. piață închisă / date indisponibile) | banner „Nu am putut încărca lista” + buton *Reîncearcă*; la `429`, mesaj cu așteptarea din `Retry-After`; la `401`, redirect către autentificare |
| Detaliu (2, 4) | schelet pentru antet și preț | preț + variație + ora furnizorului; la `unavailable` se afișează „Preț indisponibil” (niciodată `0`) | — | `404` → „Stock-ul nu există”; altfel eroare locală, ultimul preț rămâne cu marcajul vechimii |
| Grafic (3) | schelet de grafic | linie zilnică; zilele fără date sunt goluri în linie | „Nu există istoric pentru perioadă” (`items: []`) | doar graficul arată eroare + *Reîncearcă*; restul ecranului rămâne utilizabil |
| Adaugă în Watchlist (5) | butonul este dezactivat cu indicator de progres, fără a afișa succesul înainte de răspuns | butonul devine „În Watchlist ✓”; `200` (exista deja) se tratează la fel | — | `409 stock_inactive` → „Stock delistat, nu poate fi adăugat”; `409 watchlist_full` → „Watchlist plin (100)”; `503`/timeout → „Nu s-a salvat”, butonul rămâne activ (retry sigur: operația e idempotentă); `401` → autentificare |
| Watchlist (6) | schelet | listă cu prețuri; intrările delistate marcate „Delistat” | „Watchlist-ul tău este gol” | eroare cu *Reîncearcă*; fără valori inventate |

---

# 5. Concluzie

- Modelul separă datele de piață (scrise de Collector) de datele private (scrise de Dashboard). Utilizatorul rămâne o identitate externă, referită doar prin `owner_id`.
- `state` și variația sunt **derivate** la citire; un preț lipsă este `null`, niciodată `0`.
- Zece acțiuni de produs sunt acoperite de șapte rute; un singur `GET /stocks` servește overview, trending, filtrare și căutare, ceea ce se potrivește cu cache-ul public din Lab 4.
- Watchlist-ul nu primește niciodată un `userId` din client și nu este cache-uit partajat, deci păstrează proprietatea privată și *read-your-writes*.
- Modificările sunt idempotente (`POST` dublu → `200`, `DELETE` → `404` clar), deci sigure la reîncercare după `429`/timeout.
- `openapi.yaml` este generat din codul sursă și validat; exemplele pentru pagină filtrată, listă goală și eroare sunt incluse.

## Surse de curs

- Lecția 6: API design și modelare de date (`lectures/lecture-06-api-design-and-data-modeling-ro.md`)
- Laboratoarele 1–4 (reguli de produs, calitate, limita sistemului, cache)
