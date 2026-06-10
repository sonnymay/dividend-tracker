from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, cast

from anthropic import Anthropic

from app.config import get_settings
from app.database import get_supabase
from app.schemas import GoalResponse
from app.services.dividend_service import build_dashboard, enrich_holdings


def _get_goal_record() -> GoalResponse:
    response = get_supabase().table("goal").select("*").limit(1).execute()
    rows = cast(list[dict[str, Any]], response.data or [])

    if not rows:
        return GoalResponse(id=None, monthly_target=0, weekly_investment=0)

    row = rows[0]
    return GoalResponse(
        id=int(row["id"]),
        monthly_target=float(row["monthly_target"]),
        weekly_investment=float(row["weekly_investment"]),
    )


def _portfolio_context() -> dict[str, Any]:
    holdings_response = get_supabase().table("holdings").select("*").order("created_at").execute()
    raw_holdings = cast(list[dict[str, Any]], holdings_response.data or [])
    holdings = enrich_holdings(raw_holdings)
    dashboard = build_dashboard(holdings, _get_goal_record())

    total_market_value = round(sum(holding.market_value for holding in holdings), 2)
    total_annual_income = round(sum(holding.annual_income for holding in holdings), 2)

    return {
        "monthly_income": dashboard.current_monthly_income,
        "annual_income": total_annual_income,
        "monthly_target": dashboard.monthly_target,
        "progress_percent": dashboard.progress_percent,
        "remaining_monthly_income": dashboard.projection.remaining_monthly_income,
        "estimated_weeks_to_goal": dashboard.projection.estimated_weeks_to_goal,
        "estimated_months_to_goal": dashboard.projection.estimated_months_to_goal,
        "estimated_goal_date": (
            dashboard.projection.estimated_goal_date.isoformat()
            if dashboard.projection.estimated_goal_date
            else None
        ),
        "total_market_value": total_market_value,
        "best_income_candidate": (
            dashboard.recommendation.model_dump() if dashboard.recommendation else None
        ),
        "holdings": [
            {
                "ticker": holding.ticker,
                "shares": holding.shares,
                "current_price": holding.price,
                "dividend_yield_percent": holding.dividend_yield_percent,
                "annual_dividend_per_share": holding.annual_dividend_per_share,
                "annual_income": holding.annual_income,
                "monthly_income": holding.monthly_income,
                "market_value": holding.market_value,
            }
            for holding in holdings
        ],
    }


@lru_cache
def _get_client() -> Anthropic:
    settings = get_settings()

    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

    return Anthropic(api_key=settings.anthropic_api_key)


def answer_portfolio_question(question: str) -> str:
    settings = get_settings()
    client = _get_client()
    context = _portfolio_context()

    if not context["holdings"]:
        return (
            "I do not see any holdings yet. Add dividend positions first, then I can ground "
            "retirement timing, buy-next, and monthly contribution answers in the portfolio."
        )

    prompt = (
        "You are an AI portfolio chat assistant for a dividend investor targeting "
        "$5,000/month passive income for early retirement. Answer only from the supplied "
        "portfolio JSON. Be practical, concise, and numerical when possible. You may do "
        "simple projections from the provided monthly income, target, holdings, yields, "
        "and goal progress. Do not invent holdings, prices, yields, account balances, tax "
        "rates, or personal facts. Include a brief non-financial-advice caveat when making "
        "buy or retirement suggestions.\n\n"
        f"PORTFOLIO JSON:\n{json.dumps(context, indent=2)}\n\n"
        f"USER QUESTION:\n{question.strip()}"
    )

    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}],
    )

    return "".join(
        str(getattr(block, "text", ""))
        for block in message.content
        if getattr(block, "type", None) == "text"
    ).strip()
