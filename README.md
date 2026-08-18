# Лихвомер

**What happens to my mortgage payment?** — a question most people can only answer
after their bank tells them. This app answers it beforehand, in euros, from data
anyone can verify.

Live at **[xbotics.ai](https://xbotics.ai)** · Interface is in Bulgarian

---

## What it does

Bulgaria joined the euro area in January 2026. Mortgages here are priced off
Euribor, Euribor follows the ECB, and the ECB reacts to the same forces that move
German Bunds. That chain is public, measurable, and almost nobody translates it
into the one number a borrower cares about: **next month's payment**.

Лихвомер closes that gap.

- **Payment forecast** — an econometric model estimates how your instalment
  changes over the next 30/60/90/180 days, with a confidence interval
- **Market comparison** — is your rate above what banks charge on new loans today,
  and what does the difference cost you per month and over the remaining term
- **Real APRC check** — enter a bank's offer and see its true annual cost with
  fees and insurance folded in, measured against the market average
- **Refinancing break-even** — the month your switching costs are repaid
- **Savings erosion** — what inflation takes from your deposit each year
- **Cost of waiting** — house prices and savings grow at different speeds; the
  gap is the real price of postponing a purchase
- **Fiscal dashboard** — government debt, deficit against the EU threshold, and
  the Bulgaria–Germany bond spread, the earliest signal that lending will get
  more expensive
- **News in plain language** — ECB and EU releases translated to Bulgarian
  offline, each tagged with what it means for your wallet

## Data — every number is traceable

No mock data, no placeholder arrays, no invented figures. **26 time series** pulled
automatically from four official APIs:

| Source | What | Series |
|---|---|---|
| [European Central Bank](https://data.ecb.europa.eu/) | Euribor, ECB policy rate, yield curve, Bulgarian lending and deposit statistics, APRC | 17 |
| [Deutsche Bundesbank](https://www.bundesbank.de/en/statistics) | German 10-year Bund yield, daily | 1 |
| [Eurostat](https://ec.europa.eu/eurostat/web/main/data/database) | Inflation, government debt and deficit, house prices, spending by function | 7 |
| [US Treasury](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve) | US 10-year yield | 1 |

Every indicator in the app carries its publication date and a link to the
original source, so any figure can be checked at the origin. The app also states
when a series is stale rather than presenting old numbers as current.

**Two deliberate omissions.** Per-bank tariffs are not published in machine-readable
form anywhere in Bulgaria, so the comparison table measures your offer against the
ECB market average instead of inventing rates. Bulgarian government portals
(Ministry of Finance, NSI, State Gazette) block automated access, so quarterly
Eurostat data is used where monthly national data would be better.

## Architecture

```
backend/                 FastAPI · SQLAlchemy · PostgreSQL · Celery
  app/ingestion/         one module per upstream API, single series registry
  app/analytics/         annuity maths, APRC, regression, timing score, advice
  app/news/              RSS, offline translation, hawkish/dovish lexicon
  app/notifications/     rules, delivery, deduplication
  app/worker/            scheduled jobs
frontend/                Next.js 14 · TypeScript · Tailwind · Recharts
  app/                   nine pages, PWA
  components/            Apple-style design system, iOS components
```

### The econometrics, honestly

Both the Bulgarian mortgage rate and the German yield are I(1) — the ADF test does
not reject a unit root in levels (p=0.115) but does in first differences (p<0.001).
A regression in levels between such series is spurious; a trial run gave a
Durbin-Watson of 0.04 and an economically meaningless negative pass-through.

The model is therefore estimated in first differences:

```
Δy_t = c + φ·Δy_(t-1) + δ·Δx_(t-L)
```

| Parameter | Value | p |
|---|---|---|
| δ (pass-through) | +0.341 | 0.0015 |
| φ (mean reversion) | −0.459 | <0.0001 |
| L (selected lag) | 4 months | — |
| R² / adj R² | 0.257 / 0.247 | — |
| Durbin-Watson | 2.17 | — |

Out of sample it beats both a naive no-change forecast and a trend-only forecast.
For Euribor 3M the same specification reaches R²=0.80.

**For consumer loans the model does not work** — δ is insignificant (p=0.21,
R²=0.03), which is expected: they are priced on credit risk, not market rates. The
endpoint refuses that target rather than returning an untrustworthy forecast.

---

## Installation

### Requirements

- Python 3.11+
- Node.js 20+
- PostgreSQL 14+
- Redis

### 1. Database

```bash
createdb lihvomer
psql -c "CREATE ROLE lihvomer LOGIN PASSWORD 'choose-a-password';"
psql -c "ALTER DATABASE lihvomer OWNER TO lihvomer;"
```

### 2. Backend

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` — at minimum `DATABASE_URL`, `REDIS_URL` and a `JWT_SECRET`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Create the schema and load real data:

```bash
.venv/bin/python -c "from app.db import Base, engine; import app.models; Base.metadata.create_all(engine)"
.venv/bin/python -m scripts.ingest
```

Install the offline translator (no API key, nothing leaves the machine):

```bash
.venv/bin/python -c "
import argostranslate.package as pkg
pkg.update_package_index()
p = next(x for x in pkg.get_available_packages() if x.from_code=='en' and x.to_code=='bg')
pkg.install_from_path(p.download())"
.venv/bin/python -m scripts.ingest_news
```

Run it:

```bash
.venv/bin/uvicorn app.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

### 3. Scheduled updates

```bash
cd backend
.venv/bin/celery -A app.worker.celery_app worker --beat --loglevel=info
```

| Job | Schedule |
|---|---|
| Macro data | every 3 hours (00:15, 03:15, … 21:15) |
| News and translation | every 3 hours (00:05, 03:05, … 21:05) |
| Model refresh | whenever ingestion brings a newer observation, plus 19:00 daily |
| Notifications | 19:30 daily |
| External link check | Mondays 04:15 |
| Job history pruning | Mondays 03:30 |

The schedule lives in one place — `JOBS` in `backend/app/worker/celery_app.py`. Both
the beat schedule and the Bulgarian text the app shows are derived from it, so the
two cannot drift apart.

Status is visible at `/api/v1/system/automation`.

### 4. Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000" > .env.local
npm run dev
```

In production the frontend and API share a domain, so `NEXT_PUBLIC_API_BASE`
must be **absent** — relative paths are used. Setting it to a localhost value in
a production build ships that address to every visitor.

---

## API

Base URL `/api/v1`. Interactive documentation at `/docs`.

### Public

| Endpoint | Returns |
|---|---|
| `GET /macro/live-dashboard` | All indicators, real interest rate, timing score |
| `GET /macro/series/{code}` | Full history of one series |
| `GET /macro/sources` | Every source with its API key and a verification link |
| `GET /macro/freshness` | Age of each series and whether it is stale |
| `GET /forecast/mortgage-rates` | Forecast with confidence interval and diagnostics |
| `GET /fiscal/overview` | Debt, deficit, BG–DE spread with history |
| `GET /fiscal/spending` | Government spending by function (COFOG) |
| `GET /news/translated-sentiment` | News with translation and wallet impact |
| `GET /system/automation` | Scheduled job status |
| `POST /calculator/payment` | Annuity, APRC, full amortisation schedule |
| `POST /calculator/compare-banks` | Comparison against market average |
| `POST /advice/savings` | Real return on deposits (Fisher) |
| `POST /advice/cost-of-waiting` | Price of postponing a purchase |
| `POST /advice/evaluate-offer` | An offer's true APRC vs the market |

### Authenticated

| Endpoint | Returns |
|---|---|
| `POST /auth/register`, `POST /auth/login` | JWT |
| `GET`/`POST`/`PUT`/`DELETE /user/loans` | Loan CRUD |
| `GET /user/loans/projections` | Payment forecast per loan |
| `GET /advice/loan-health` | Market comparison, refinancing, early repayment |
| `GET /notifications` | Inbox |
| `PUT /notifications/preferences` | Threshold and channels |

### Example

```bash
curl -s https://xbotics.ai/api/v1/advice/evaluate-offer \
  -H 'Content-Type: application/json' \
  -d '{"amount":200000,"months":300,"nominal_rate_pct":2.5,
       "monthly_fee":15,"upfront_fee":2000,
       "property_insurance_annual_pct":0.1,"life_insurance_annual_pct":0.3}'
```

A 2.50% headline rate with those fees is a **3.25% APRC** — worse than a "higher"
2.60% offer with no fees, whose APRC is 2.63%. That difference is what the app
exists to show.

---

## Verification

Financial figures shown to people deserve proof, not assertion.

- **Sources** — all 26 series are checked against the upstream API, not against
  the local database
- **Arithmetic** — annuity, APRC, Fisher and spread are verified independently
  with `Decimal` at 40 significant digits
- **Amortisation** — schedules are computed in whole cents, the way a bank
  charges, so principal sums to the loan exactly and the balance closes at zero
- **Forecast** — stationarity, autocorrelation and coefficient significance are
  reported with the result, not hidden

---

## Licence

MIT — see [LICENSE](LICENSE).

Data belongs to the respective institutions and is used under their terms for
free reuse with attribution.

---

## Author

**Ivaylo Borisov** — with the power of Claude Code

We love open source ❤️

[linkedin.com/in/borisovivaylo](https://www.linkedin.com/in/borisovivaylo/)

---

## A note on what this is not

This application does not give financial advice. It shows publicly available
official data and states its own uncertainty. Forecasts are statistical estimates
with a stated confidence interval, not promises. Before any credit decision,
talk to your bank or a licensed adviser.
