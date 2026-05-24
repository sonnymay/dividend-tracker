# dividend-tracker — v1.0.0 Spec

## What this is

A focused dashboard for dividend-stock investors who want three things on one screen:

1. **Forward yield** across the whole portfolio.
2. **When and how much** their next payouts are.
3. **Which positions** are actually carrying the income.

Built for a real, personal use case: tracking a portfolio targeting $5,000/month passive income for early retirement.

## Who it's for

Long-term dividend investors who:
- Hold 5–50 dividend-paying positions across one or more brokerages.
- Don't want to log into 3 brokerage portals to see what's coming in.
- Care about income stability, not day-trading.

Explicitly NOT for: active traders, options players, crypto-only portfolios, or financial advisors managing client accounts.

## v1.0.0 scope (in)

- Add / edit / remove positions (ticker + shares + cost basis).
- Live price + forward dividend data via yfinance.
- Portfolio overview card: total value, cost basis, forward annual yield.
- Payout history chart (past 24 months).
- Upcoming payouts list (next 90 days) with ex-div and pay dates.
- Per-position breakdown table: yield, weight, est. annual income.
- AI Portfolio Chat for retirement-timing / goal-tracking questions.
- Public live demo on Vercel + Render.
- Test suite (pytest backend, vitest frontend) with at least the critical paths covered.
- Ruff + mypy clean on the backend.
- GitHub Actions CI green on every PR.
- Published v1.0.0 tag with a CHANGELOG entry.

## Explicitly out of scope (post-v1.0.0)

- DRIP simulation, dividend growth CAGR, sector/geography breakdowns, CSV import, payout safety flags — listed in the roadmap, not in v1.0.0.
- Multi-user auth. Single-user for now.
- Mobile native app.
- Real-time price streaming.
- Tax-lot tracking.
- Broker integrations (Schwab, Fidelity, etc.) beyond CSV.

## Definition of done for v1.0.0

- [ ] Backend covered by pytest, key endpoints have happy-path + one error-path test.
- [ ] CI workflow runs tests + ruff + mypy on every PR; main branch green.
- [ ] README has badges, screenshots, 30-second local setup, disclaimer.
- [ ] Live demo URL works end-to-end on a freshly cleared browser.
- [ ] Tagged release v1.0.0 with a CHANGELOG.md entry.
- [ ] Shared once on Hacker News (Show HN) and r/Python.

## Why this is the signature project

Real personal use case (not a tutorial), real domain knowledge (dividends, payout dates), live deploy, multi-component (FastAPI + React + Supabase + LLM), and reachable to v1.0.0 in 4–6 weeks of focused work. Stronger interview demo than starting something new from scratch.
