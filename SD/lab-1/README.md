# Lab 1: Define the Initial Product

## Personal Investment Dashboard

# 1. Product Research

### Research question

**How do existing products help a User follow market information, and which parts belong in this Dashboard's first version?**

Two existing products were examined:

- **Yahoo Finance** as a market-data and portfolio-tracking product;
- **TradingView** as a trading and market-analysis product.

| Product | Likely User and goal | Reusable pattern |
|---|---|---|
| **Yahoo Finance** | An individual investor who wants to follow owned investments, understand portfolio performance and compare multiple holdings in one place. | Use portfolio holdings, current value, daily change and total change to give the User a simple overview of investment performance. |
| **TradingView** | An investor or trader who wants to monitor selected market instruments and understand their recent market movement. | Use customizable watchlists to group selected symbols and show market performance and relevant information for each tracked instrument. |

Yahoo Finance provides portfolio tracking with portfolio-performance views, daily and total changes, holdings comparisons and additional portfolio metrics. It also allows investments to be added manually or through supported brokerage connections.

TradingView provides customizable watchlists that allow Users to add and remove symbols and follow information such as performance, fundamentals, technical summaries and news.

TradingView goes further by supporting alerts for individual symbols and whole watchlists. These alerts can notify the User when selected market conditions occur.

TradingView also supports actual trading through connected brokers and exchanges, which makes it broader than a simple investment-monitoring product.

### Scope decision from research

The research confirms that several patterns are useful for a small Personal Investment Dashboard:

- recording investment holdings;
- seeing current portfolio value;
- seeing absolute and percentage gain or loss;
- following current market prices;
- maintaining a watchlist;
- inspecting recent price movement.

Yahoo Finance demonstrates the usefulness of **portfolio-oriented monitoring**, while TradingView demonstrates the usefulness of **symbol-oriented market monitoring**.

The first version of the Personal Investment Dashboard will therefore combine the smallest useful parts of these two approaches:

- manually recorded investment holdings;
- portfolio value and gain/loss;
- latest available market information;
- recent price history;
- a personal watchlist.

The research also identifies functionality that is useful but unnecessary for the first version.

Yahoo Finance can connect portfolios with supported brokerage accounts, while TradingView provides trading, advanced analysis and market alerts.

These capabilities will be deferred.

The first version will therefore **not** include:

- brokerage synchronization;
- buy or sell transactions;
- market alerts;
- personalized investment recommendations;
- advanced technical analysis;
- aggregated financial news.

This keeps the product focused on the original client problem:

**Help me follow my investments.**

The Dashboard helps the User **understand investments that they already own or want to monitor**, rather than helping the User actively trade or decide what to buy.

---

# 2. Stakeholders and Actors

The stakeholder analysis follows the motivation and influence approach described in Lecture 2.

**Motivation** represents how much a stakeholder cares about or depends on the Dashboard's result.

**Influence** represents how much the stakeholder can enable, block or change product decisions.

## Stakeholder table

| Stakeholder | Motivation | Influence | Reason |
|---|---|---|---|
| Individual Investor | High | Low | The Investor directly depends on accurate and understandable investment information but normally has limited control over product decisions. |
| Product Owner | High | High | Defines the product scope, priorities and acceptance criteria for the first version. |
| Market Data Provider | Low | High | The Dashboard is not its main concern, but the availability and coverage of its market information directly affect Dashboard results. |
| Financial Regulatory Authority | Low | High | Does not directly use the Dashboard but may influence how investment information and financial claims are presented. |
| Product Support / Operations | High | Low | Depends on predictable Dashboard behaviour and understandable User-visible results but does not define the main product scope. |

## Stakeholder matrix

| Motivation | Low influence | High influence |
|---|---|---|
| **High** | Individual Investor; Product Support / Operations | Product Owner |
| **Low** | — | Market Data Provider; Financial Regulatory Authority |

## Actor classification

| Candidate | Classification | Reason |
|---|---|---|
| Individual Investor | **Direct human actor** | Directly records investments, maintains tracked symbols and reads investment results. |
| Market Data Provider | **External system** | Directly supplies the source market results required by the Dashboard. |
| Product Owner | **Other stakeholder** | Influences product decisions but does not participate directly in the investment-following journey. |
| Financial Regulatory Authority | **Other stakeholder** | May influence constraints but does not directly interact with the Dashboard. |
| Product Support / Operations | **Other stakeholder** | Is affected by product behaviour but does not participate in the main first-version User journey. |

Only directly connected actors and external systems belong in the C4 System Context view.

Therefore, the first-version Context view contains:

- **Individual Investor** — direct human actor;
- **Market Data Provider** — directly connected external system.

---

# 3. Product Promise and Scope

## Product promise

**Personal Investment Dashboard helps individual investors follow their manually recorded investments and selected market symbols so that they can understand current portfolio value, gain/loss and recent market movement in one place.**

## Goals

1. Let the User record the investments that they currently want to follow.

2. Let the User see the current estimated value and gain or loss of their recorded portfolio.

3. Let the User follow the latest available market price and daily movement of each tracked investment.

4. Let the User inspect recent price history for a tracked investment.

5. Let the User maintain a watchlist of market symbols independently from owned investments.

## Non-goals

1. The first version will **not execute investment transactions or synchronize automatically with brokerage accounts**.

2. The first version will **not provide personalized investment advice, recommendations or portfolio optimization decisions**.

3. The first version will **not actively notify the User about market changes or provide advanced trading analysis**.

## Constraints and assumptions

| Type | Statement |
|---|---|
| Constraint | Investment holdings are entered and maintained manually by the User in the first version. |
| Constraint | Only market instruments supported by the selected market-data source can receive current market results. |
| Constraint | The Dashboard is an informational product and does not execute investment transactions. |
| Assumption | The Market Data Provider can return a usable current price and recent history for supported instruments. |
| Assumption | Market information may sometimes be delayed, stale or unavailable. |
| Assumption | The User provides correct quantity and acquisition-cost information for manually recorded investments. |

---

# 4. Functional Requirements

The functional requirements use actor goals, user stories and observable definitions of done.

Each story follows the form:

**As a \<actor\>, I want \<goal\>, so that \<useful result\>.**

---

## DASH-1 — Record an investment

### Actor goal

The Individual Investor needs to record an investment they own so that it becomes part of the portfolio being followed.

### User story

**As an Individual Investor, I want to record an investment I own, so that I can include it in my portfolio results.**

### Definitions of done

- A supported market symbol can be recorded together with its quantity and acquisition cost.
- After it is recorded, the investment contributes to the User's portfolio results.
- If the market symbol is unsupported, the User is clearly informed that it is unsupported and the investment is not treated as successfully added.
- The User can only change investment information belonging to their own portfolio.

---

## DASH-2 — Correct or remove an investment

### Actor goal

The Individual Investor needs to keep recorded investment information consistent with the investments they currently own.

### User story

**As an Individual Investor, I want to update or remove a recorded investment, so that my portfolio represents the investments I currently want to follow.**

### Definitions of done

- The User can change the recorded quantity or acquisition cost of an existing investment.
- Updated investment information is reflected in subsequent portfolio results.
- A removed investment no longer contributes to portfolio value or gain/loss.
- Removing an investment does not automatically remove the same symbol from the User's watchlist.

---

## DASH-3 — Understand current portfolio value

### Actor goal

The Individual Investor needs to understand the current estimated result of the investments they have recorded.

### User story

**As an Individual Investor, I want to see the current value and gain or loss of my portfolio, so that I can understand my current investment position.**

### Definitions of done

- The User can see the current estimated market value of their recorded investments when the required market results are available.
- The User can see absolute and percentage gain or loss based on their recorded acquisition information and available market results.
- If a required market result is missing or stale, the affected investment is identified and the portfolio result is not presented as fully current.
- The User sees results only for their own recorded portfolio.

---

## DASH-4 — Follow current market movement

### Actor goal

The Individual Investor needs to understand how a tracked investment is currently moving in the market.

### User story

**As an Individual Investor, I want to see the latest available market result for a tracked investment, so that I can understand its current market movement.**

### Definitions of done

- For a supported tracked symbol, the User can see its latest available price and daily absolute and percentage change.
- The User can distinguish a current result from a result identified as stale.
- If current market information is unavailable, the Dashboard shows it as unavailable instead of presenting an assumed successful result.
- If the requested symbol is unsupported, the User receives a clear unsupported result.

---

## DASH-5 — Inspect recent price history

### Actor goal

The Individual Investor needs historical context to understand how a tracked investment has recently changed in value.

### User story

**As an Individual Investor, I want to inspect the recent price history of a tracked investment, so that I can understand how its market price has changed over time.**

### Definitions of done

- The User can inspect available historical market prices for the previous 30 calendar days for a supported tracked symbol.
- Historical market results are associated with their corresponding dates.
- If part or all of the requested history is unavailable, the missing result is made clear and is not replaced with invented market values.
- An unsupported symbol is not presented as having valid historical information.

---

## DASH-6 — Maintain a watchlist

### Actor goal

The Individual Investor needs to follow interesting market instruments without claiming to own them.

### User story

**As an Individual Investor, I want to maintain a watchlist of market symbols, so that I can follow investments that are interesting to me without adding them to my portfolio.**

### Definitions of done

- The User can add a supported market symbol to the watchlist without creating an owned investment.
- The User can remove a symbol from the watchlist.
- Removing a symbol from the watchlist does not change an existing recorded investment for the same symbol.
- If a symbol is unsupported, the User receives an unsupported result and it is not treated as a valid tracked symbol.

---

# 5. C4 System Context View

The C4 System Context view describes the Personal Investment Dashboard from the outside.

It shows:

- the system of interest;
- its direct human actor;
- directly connected external systems;
- the purpose of each relationship.

It does not describe internal architecture or implementation technology.

## System boundary

| Inside the Personal Investment Dashboard boundary | Outside the Personal Investment Dashboard boundary |
|---|---|
| Keep the User's manually recorded investments and watchlist as product information. | The User decides which investments they own or want to follow. |
| Calculate portfolio value and gain/loss from User-supplied investment information and available market results. | The User supplies investment quantities and acquisition costs. |
| Request market results required to follow supported instruments. | The Market Data Provider determines source prices, historical results and supported instruments. |
| Make missing, stale and unsupported market results clear to the User. | The Market Data Provider controls whether source market information is available and current. |
| Show current market movement and recent historical results. | Brokers and financial markets execute actual investment transactions and are outside the first-version product. |

---

## External dependency

### Market Data Provider

### Dashboard responsibility that needs it

The Personal Investment Dashboard requires external market information to:

- calculate the current estimated value of recorded investments;
- calculate gain or loss;
- show current market movement;
- show recent historical market results.

### Result supplied by the external system

The Market Data Provider supplies:

- supported or unsupported market symbol;
- latest available market price;
- previous market result required to determine daily movement;
- recent historical market prices;
- information that allows the Dashboard to determine whether the market result is current or unavailable.

### User-visible alternative results

If the market symbol is not supported:

**Unsupported**

If required market information cannot be obtained:

**Unavailable**

If available information is known to be older than the expected market result:

**Stale**

If unavailable or stale information affects the portfolio calculation, the Dashboard does not present the affected portfolio total as fully current.

The Market Data Provider owns the original market result.

The Personal Investment Dashboard remains responsible for interpreting that result and communicating it clearly and safely to the User.

---

## C4 System Context diagram

```mermaid
flowchart LR

    User["Individual Investor
    [Person]
    Records investments and follows
    portfolio and market results"]

    Dashboard["Personal Investment Dashboard
    [Software System]
    Helps the User follow manually recorded
    investments and selected market symbols"]

    Market["Market Data Provider
    [External Software System]
    Owns market prices, instrument coverage
    and historical market results"]

    User -->|"Records holdings, maintains a watchlist and follows investment results"| Dashboard

    Dashboard -->|"Requests symbol support, latest market results and recent price history"| Market

    Market -->|"Returns supported or unsupported symbols, market results, history and result availability"| Dashboard