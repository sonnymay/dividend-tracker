# Changelog

All notable changes to **dividend-tracker** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Planned
- DRIP simulation (reinvested vs cash payout)
- Dividend growth rate (1y / 3y / 5y CAGR)
- Sector + geography breakdown
- CSV import from broker statements
- Dividend safety / payout ratio flags
- Tests + CI (GitHub Actions)
- Multi-currency support
- Email alerts for upcoming ex-dividend dates
- Tax year summary and qualified vs. ordinary dividend breakdown

---

## [0.5.0] – 2026-06-17

### Added
- AI Portfolio Chat: ask natural language questions about your holdings via OpenRouter
- Goal tracking: direct answers to retirement timeline questions
- Forward yield projections based on current positions

### Changed
- Switched to OpenRouter free router for portfolio chat backend

---

## [0.4.0] – 2026-05-01

### Added
- Upcoming payouts panel — ex-div and pay dates per holding
- Position breakdown chart — yield, weight, and income contribution per holding
- Dark mode toggle

### Changed
- Migrated to Supabase for portfolio persistence
- Live price and dividend data now pulled from Yahoo Finance via yfinance

---

## [0.3.0] – 2026-03-15

### Added
- Stock search: add any ticker with live data lookup
- Payout history chart (Recharts)
- Portfolio overview: total value, cost basis, forward yield

### Fixed
- Market data render fallback for tickers with missing yfinance data

---

## [0.2.0] – 2026-02-01

### Added
- FastAPI backend with Pydantic settings
- Docker Compose setup for local development
- .env.example for environment variable documentation
- Render + Vercel deployment configs

### Changed
- Added mypy, ruff, and pre-commit for code quality

---

## [0.1.0] – 2026-01-10

### Added
- Initial project scaffold: React 19 + Vite + TypeScript frontend
- FastAPI Python 3.11+ backend
- Basic dividend portfolio data model
- README with architecture overview and local dev instructions
