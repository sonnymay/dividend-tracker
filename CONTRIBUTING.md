# Contributing to Dividend Tracker

Thank you for your interest in contributing! This project tracks dividend portfolio data and I welcome improvements — especially around data sources, chart types, and broker-import formats.

## Before You Start

Please open an issue describing what you want to change before sending a large PR. This saves us both time if the approach doesn't fit the project direction.

## Setting Up Locally

```bash
# Clone the repo
git clone https://github.com/sonnymay/dividend-tracker.git
cd dividend-tracker

# Start everything with Docker
docker compose up --build
```

The API runs at http://localhost:8000 and the frontend at http://localhost:5173.

See README.md for full setup instructions including environment variables.

## Code Style

- **Backend**: Python 3.11+, FastAPI. Run `pre-commit install` after cloning — hooks enforce formatting (black, isort, flake8).
- **Frontend**: TypeScript strict mode, Tailwind CSS. Run `npm run lint` before committing.
- **Tests**: `pytest` for backend. Keep tests passing — CI will check.

## Pull Request Guidelines

1. Fork the repo and create a feature branch (`git checkout -b feat/your-feature`)
2. Write or update tests for your changes
3. Make sure `pytest` passes locally
4. Open a PR with a clear description of what changed and why
5. Reference the related issue if one exists

## Good First Issues

Look for issues labeled **good first issue** or **help wanted** — these are scoped to be approachable without deep knowledge of the codebase.

## Questions?

Open a GitHub issue or reach out at sonnymaywi@gmail.com.
