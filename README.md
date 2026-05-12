# Dividend Tracker

> Track your dividend portfolio's yield, payout history, and breakdown — without juggling five brokerage tabs.

**Live demo:** [dividend-tracker-pi-navy.vercel.app](https://dividend-tracker-pi-navy.vercel.app)

---

## Why this exists

Most portfolio dashboards bury dividend data three clicks deep, or assume you only care about share price. As a long-term dividend investor I wanted answers to three questions at a glance:

- What's my forward yield across the whole portfolio?
- When am I getting paid, and how much?
- Which positions are actually carrying the income?

Dividend Tracker exists to answer those three questions on one screen.

---

## Features

- **Portfolio overview** — total value, cost basis, forward yield
- **Payout history** — past distributions visualized over time
- **Upcoming payouts** — ex-div and pay dates so you stop missing them
- **Position breakdown** — yield, weight, and income contribution per holding
- **Live price + dividend data** pulled from Yahoo Finance via `yfinance`

---

## Stack

| Layer    | Tech                                       |
|----------|--------------------------------------------|
| Frontend | React 19, Vite, TypeScript, Recharts, Tailwind CSS v4 |
| Backend  | FastAPI (Python), Pydantic Settings        |
| Data     | yfinance (Yahoo Finance) + Supabase        |
| Hosting  | Vercel (frontend) + Render (backend)       |

---

## Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  React + Vite │ ───▶ │   FastAPI    │ ───▶ │  yfinance    │
│   (Vercel)    │      │   (Render)   │      │  + Supabase  │
└──────────────┘      └──────────────┘      └──────────────┘
```

FastAPI handles ticker lookups via `yfinance` for live price and dividend history, then persists user holdings in Supabase. Recharts renders payout history and portfolio breakdown on the client.

---

## Local development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "SUPABASE_URL=your-url"  > .env
echo "SUPABASE_KEY=your-key" >> .env
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Roadmap

- [ ] DRIP simulation (reinvested vs cash payout)
- [ ] Dividend growth rate (1y / 3y / 5y CAGR)
- [ ] Sector + geography breakdown
- [ ] CSV import from broker statements
- [ ] Dividend safety / payout ratio flags

---

## About

Built by [Sonny May](https://github.com/sonnymay). Part of a portfolio of tools I build to solve problems I actually live with.

> Not financial advice. Dividend data sourced from Yahoo Finance and may lag or contain inaccuracies — verify with your broker before making decisions.
