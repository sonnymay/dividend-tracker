from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from math import ceil

import yfinance as yf

from app.schemas import DashboardResponse, GoalResponse, HoldingResponse, Projection, Recommendation


@dataclass
class TickerSnapshot:
    ticker: str
    price: float
    annual_dividend_per_share: float
    dividend_yield_percent: float


def _first_number(*values: object) -> float | None:
    for value in values:
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def _annual_dividend_from_history(stock: yf.Ticker) -> float:
    dividends = stock.dividends
    if dividends is None or len(dividends) == 0:
        return 0.0

    cutoff = datetime.now(UTC) - timedelta(days=365)
    trailing_total = 0.0

    for timestamp, amount in dividends.items():
        payout_date = timestamp.to_pydatetime()
        if payout_date.tzinfo is None:
            payout_date = payout_date.replace(tzinfo=UTC)
        else:
            payout_date = payout_date.astimezone(UTC)

        if payout_date >= cutoff:
            trailing_total += float(amount)

    return trailing_total


def normalize_dividend_yield_percent(raw_yield: float | None, price: float, annual_dividend_per_share: float) -> float:
    if raw_yield is None:
        return round((annual_dividend_per_share / price) * 100, 4) if price else 0.0

    # Yahoo fields can be returned either as 0.0344 or 3.44 depending on the endpoint/data source.
    if raw_yield <= 1:
        return round(raw_yield * 100, 4)

    return round(raw_yield, 4)


def fetch_ticker_snapshot(ticker: str) -> TickerSnapshot:
    stock = yf.Ticker(ticker)
    info = stock.info or {}
    fast_info = dict(stock.fast_info or {})

    price = _first_number(
        fast_info.get("lastPrice"),
        fast_info.get("last_price"),
        info.get("regularMarketPrice"),
        info.get("currentPrice"),
        info.get("previousClose"),
    )

    if price is None:
        raise ValueError(f"Unable to find a live price for {ticker}.")

    annual_dividend_per_share = _first_number(
        info.get("dividendRate"),
        info.get("trailingAnnualDividendRate"),
    )

    if annual_dividend_per_share is None:
        annual_dividend_per_share = _annual_dividend_from_history(stock)

    dividend_yield_decimal = _first_number(
        info.get("dividendYield"),
        info.get("trailingAnnualDividendYield"),
    )

    dividend_yield_percent = normalize_dividend_yield_percent(
        dividend_yield_decimal,
        price=price,
        annual_dividend_per_share=annual_dividend_per_share or 0.0,
    )

    return TickerSnapshot(
        ticker=ticker,
        price=round(price, 4),
        annual_dividend_per_share=round(annual_dividend_per_share or 0.0, 4),
        dividend_yield_percent=dividend_yield_percent,
    )


def enrich_holdings(raw_holdings: list[dict]) -> list[HoldingResponse]:
    snapshots: dict[str, TickerSnapshot] = {}
    enriched: list[HoldingResponse] = []

    for holding in raw_holdings:
        ticker = holding["ticker"]
        snapshot = snapshots.get(ticker)
        if snapshot is None:
            snapshot = fetch_ticker_snapshot(ticker)
            snapshots[ticker] = snapshot

        shares = float(holding["shares"])
        annual_income = shares * snapshot.annual_dividend_per_share
        monthly_income = annual_income / 12 if annual_income else 0.0
        market_value = shares * snapshot.price

        enriched.append(
            HoldingResponse(
                id=int(holding["id"]),
                ticker=ticker,
                shares=shares,
                price=round(snapshot.price, 2),
                dividend_yield_percent=round(snapshot.dividend_yield_percent, 2),
                annual_dividend_per_share=round(snapshot.annual_dividend_per_share, 2),
                annual_income=round(annual_income, 2),
                monthly_income=round(monthly_income, 2),
                market_value=round(market_value, 2),
                created_at=datetime.fromisoformat(holding["created_at"].replace("Z", "+00:00")),
            )
        )

    return enriched


def build_dashboard(holdings: list[HoldingResponse], goal: GoalResponse) -> DashboardResponse:
    current_monthly_income = round(sum(holding.monthly_income for holding in holdings), 2)
    remaining_monthly_income = round(max(goal.monthly_target - current_monthly_income, 0), 2)
    progress_percent = (
        round(min((current_monthly_income / goal.monthly_target) * 100, 100), 2)
        if goal.monthly_target > 0
        else 0.0
    )

    recommendation: Recommendation | None = None
    best_income_per_dollar = 0.0

    for holding in holdings:
        if holding.price <= 0:
            continue

        monthly_income_per_dollar = holding.monthly_income / holding.market_value if holding.market_value else 0.0
        if monthly_income_per_dollar > best_income_per_dollar:
            best_income_per_dollar = monthly_income_per_dollar
            recommendation = Recommendation(
                ticker=holding.ticker,
                monthly_income_per_dollar=round(monthly_income_per_dollar, 6),
                annual_dividend_yield_percent=holding.dividend_yield_percent,
                share_price=holding.price,
            )

    estimated_weeks_to_goal: float | None = None
    estimated_months_to_goal: float | None = None
    estimated_goal_date: date | None = None

    if remaining_monthly_income == 0:
        estimated_weeks_to_goal = 0.0
        estimated_months_to_goal = 0.0
        estimated_goal_date = date.today()
    elif (
        goal.weekly_investment > 0
        and recommendation is not None
        and recommendation.monthly_income_per_dollar > 0
    ):
        monthly_income_added_per_week = goal.weekly_investment * recommendation.monthly_income_per_dollar
        estimated_weeks_to_goal = round(remaining_monthly_income / monthly_income_added_per_week, 1)
        estimated_months_to_goal = round(estimated_weeks_to_goal / 4.345, 1)
        estimated_goal_date = date.today() + timedelta(days=ceil(estimated_weeks_to_goal * 7))

    return DashboardResponse(
        current_monthly_income=current_monthly_income,
        monthly_target=goal.monthly_target,
        progress_percent=progress_percent,
        projection=Projection(
            remaining_monthly_income=remaining_monthly_income,
            estimated_weeks_to_goal=estimated_weeks_to_goal,
            estimated_months_to_goal=estimated_months_to_goal,
            estimated_goal_date=estimated_goal_date,
        ),
        recommendation=recommendation,
        holdings=holdings,
    )
