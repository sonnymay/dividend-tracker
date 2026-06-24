from __future__ import annotations

import logging
from datetime import date
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from app.ai import answer_portfolio_question
from app.config import get_settings
from app.database import get_supabase
from app.schemas import (
    AIChatRequest,
    AIChatResponse,
    ChartPoint,
    DashboardResponse,
    GoalCreate,
    GoalResponse,
    HoldingCreate,
    HoldingResponse,
    HoldingUpdate,
)
from app.services.dividend_service import build_dashboard, enrich_holdings, fetch_ticker_snapshot

settings = get_settings()
logger = logging.getLogger(__name__)

DATABASE_UNAVAILABLE_DETAIL = (
    "Portfolio database is unavailable. Check SUPABASE_URL, SUPABASE_KEY, "
    "and Supabase table setup in Render."
)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Dividend portfolio tracker API. "
        "Provides live holdings data, income projections, "
        "payout history, and an AI portfolio chat backed by OpenRouter."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _database_unavailable(error: Exception, action: str) -> HTTPException:
    logger.exception("Supabase %s failed.", action)

    if "SUPABASE_URL and SUPABASE_KEY" in str(error):
        detail = "SUPABASE_URL and SUPABASE_KEY must be configured in Render."
    else:
        detail = DATABASE_UNAVAILABLE_DETAIL

    return HTTPException(status_code=503, detail=detail)

def execute_supabase(query: Any, action: str) -> Any:
    try:
        return query.execute()
    except Exception as error:
        raise _database_unavailable(error, action) from error

def supabase_table(name: str) -> Any:
    try:
        return get_supabase().table(name)
    except Exception as error:
        raise _database_unavailable(error, f"connect to {name}") from error

def list_raw_holdings() -> list[dict[str, Any]]:
    response = execute_supabase(
        supabase_table("holdings").select("*").order("created_at"),
        "list holdings",
    )
    return cast(list[dict[str, Any]], response.data or [])

def get_goal_record() -> GoalResponse:
    response = execute_supabase(
        supabase_table("goal").select("*").limit(1),
        "load goal",
    )
    rows = cast(list[dict[str, Any]], response.data or [])

    if not rows:
        return GoalResponse(id=None, monthly_target=0, weekly_investment=0)

    row = rows[0]
    return GoalResponse(
        id=int(row["id"]),
        monthly_target=float(row["monthly_target"]),
        weekly_investment=float(row["weekly_investment"]),
    )

def save_dividend_history(total_monthly_income: float) -> None:
    current_month = date.today().replace(day=1).isoformat()
    existing = cast(
        list[dict[str, Any]],
        execute_supabase(
            supabase_table("dividend_history").select("id").eq("month", current_month).limit(1),
            "load dividend history",
        ).data
        or [],
    )
    payload: dict[str, Any] = {
        "month": current_month,
        "total_monthly_income": round(total_monthly_income, 2),
    }

    if existing:
        execute_supabase(
            supabase_table("dividend_history").update(payload).eq("id", existing[0]["id"]),
            "update dividend history",
        )
    else:
        execute_supabase(
            supabase_table("dividend_history").insert(payload),
            "insert dividend history",
        )

def load_dashboard() -> DashboardResponse:
    goal = get_goal_record()
    holdings = enrich_holdings(list_raw_holdings())
    dashboard = build_dashboard(holdings, goal)
    save_dividend_history(dashboard.current_monthly_income)
    return dashboard

@app.get("/health", tags=["Meta"])
def healthcheck() -> dict[str, str]:
    """Return a simple liveness check."""
    return {"status": "ok"}

@app.get("/health/dependencies", tags=["Meta"])
def dependency_healthcheck(response: Response) -> dict[str, Any]:
    """Return dependency readiness without exposing secrets."""
    current_settings = get_settings()
    supabase_configured = bool(current_settings.supabase_url and current_settings.supabase_key)
    supabase_reachable = False
    detail = None

    if supabase_configured:
        try:
            execute_supabase(supabase_table("goal").select("id").limit(1), "healthcheck goal")
            supabase_reachable = True
        except HTTPException as error:
            response.status_code = error.status_code
            detail = error.detail
    else:
        response.status_code = 503
        detail = "SUPABASE_URL and SUPABASE_KEY must be configured in Render."

    return {
        "status": "ok" if supabase_reachable else "error",
        "supabase": {
            "configured": supabase_configured,
            "reachable": supabase_reachable,
            "detail": detail,
        },
    }

@app.get("/holdings", response_model=list[HoldingResponse], tags=["Holdings"])
def get_holdings() -> list[HoldingResponse]:
    """Return all holdings enriched with live market data."""
    return enrich_holdings(list_raw_holdings())

@app.get("/holdings/income-summary", tags=["Holdings"])
def get_income_summary() -> dict[str, Any]:
    """Return a portfolio-level income summary suitable for CAGR and trend analysis.

    Aggregates enriched holdings into:
    - total_annual_income: sum of all annual dividend income across holdings
    - total_monthly_income: total_annual_income / 12
    - total_market_value: total portfolio market value
    - blended_yield_percent: income-weighted average yield across all positions
    - top_income_contributors: top 5 holdings ranked by annual_income descending
    - holding_count: number of distinct positions

    The chart history endpoint (/chart) provides the monthly time-series needed
    to compute 1y/3y/5y CAGR on the frontend.
    """
    holdings = enrich_holdings(list_raw_holdings())

    total_annual_income = round(sum(h.annual_income for h in holdings), 2)
    total_monthly_income = round(total_annual_income / 12, 2)
    total_market_value = round(sum(h.market_value for h in holdings), 2)

    blended_yield = (
        round((total_annual_income / total_market_value) * 100, 4)
        if total_market_value > 0
        else 0.0
    )

    top_contributors = sorted(holdings, key=lambda h: h.annual_income, reverse=True)[:5]

    return {
        "total_annual_income": total_annual_income,
        "total_monthly_income": total_monthly_income,
        "total_market_value": total_market_value,
        "blended_yield_percent": blended_yield,
        "holding_count": len(holdings),
        "top_income_contributors": [
            {
                "ticker": h.ticker,
                "shares": h.shares,
                "annual_income": h.annual_income,
                "monthly_income": h.monthly_income,
                "dividend_yield_percent": h.dividend_yield_percent,
                "market_value": h.market_value,
            }
            for h in top_contributors
        ],
    }

@app.post("/holdings", response_model=HoldingResponse, status_code=201, tags=["Holdings"])
def create_holding(payload: HoldingCreate) -> HoldingResponse:
    """Add a new holding. Validates the ticker against yfinance before persisting."""
    try:
        fetch_ticker_snapshot(payload.ticker)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    response = execute_supabase(
        supabase_table("holdings").insert({"ticker": payload.ticker, "shares": payload.shares}),
        "create holding",
    )
    rows = cast(list[dict[str, Any]], response.data or [])

    if not rows:
        raise HTTPException(status_code=500, detail="Unable to save holding.")

    return enrich_holdings(rows)[0]

@app.put("/holdings/{holding_id}", response_model=HoldingResponse, tags=["Holdings"])
def update_holding(holding_id: int, payload: HoldingUpdate) -> HoldingResponse:
    """Update shares or ticker for a specific holding by ID."""
    try:
        fetch_ticker_snapshot(payload.ticker)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    response = execute_supabase(
        supabase_table("holdings")
        .update({"ticker": payload.ticker, "shares": payload.shares})
        .eq("id", holding_id),
        "update holding",
    )
    rows = cast(list[dict[str, Any]], response.data or [])

    if not rows:
        raise HTTPException(status_code=404, detail="Holding not found.")

    return enrich_holdings(rows)[0]

@app.put("/holdings/by-ticker/{ticker}", response_model=HoldingResponse, tags=["Holdings"])
def replace_holding_group(ticker: str, payload: HoldingUpdate) -> HoldingResponse:
    """Replace all rows for a ticker with a single consolidated holding."""
    normalized_ticker = ticker.strip().upper()

    try:
        fetch_ticker_snapshot(payload.ticker)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    existing_rows = cast(
        list[dict[str, Any]],
        execute_supabase(
            supabase_table("holdings").select("*").eq("ticker", normalized_ticker),
            "load holding group",
        ).data
        or [],
    )

    if not existing_rows:
        raise HTTPException(status_code=404, detail="Holding group not found.")

    execute_supabase(
        supabase_table("holdings").delete().eq("ticker", normalized_ticker),
        "delete holding group",
    )
    response = execute_supabase(
        supabase_table("holdings").insert({"ticker": payload.ticker, "shares": payload.shares}),
        "replace holding group",
    )
    rows = cast(list[dict[str, Any]], response.data or [])

    if not rows:
        raise HTTPException(status_code=500, detail="Unable to replace holding group.")

    return enrich_holdings(rows)[0]

@app.delete("/holdings/{holding_id}", status_code=204, response_class=Response, tags=["Holdings"])
def delete_holding(holding_id: int) -> Response:
    """Delete a single holding by ID."""
    execute_supabase(
        supabase_table("holdings").delete().eq("id", holding_id),
        "delete holding",
    )
    return Response(status_code=204)

@app.delete(
    "/holdings/by-ticker/{ticker}", status_code=204, response_class=Response, tags=["Holdings"]
)
def delete_holding_group(ticker: str) -> Response:
    """Delete all holdings for a given ticker symbol."""
    normalized_ticker = ticker.strip().upper()
    execute_supabase(
        supabase_table("holdings").delete().eq("ticker", normalized_ticker),
        "delete holding group",
    )
    return Response(status_code=204)

@app.get("/goal", response_model=GoalResponse, tags=["Goal"])
def get_goal() -> GoalResponse:
    """Return the current monthly income goal and weekly investment target."""
    return get_goal_record()

@app.post("/goal", response_model=GoalResponse, tags=["Goal"])
def save_goal(payload: GoalCreate) -> GoalResponse:
    """Upsert the income goal (always stored as row id=1)."""
    response = execute_supabase(
        supabase_table("goal").upsert(
            {
                "id": 1,
                "monthly_target": payload.monthly_target,
                "weekly_investment": payload.weekly_investment,
            }
        ),
        "save goal",
    )
    rows = cast(list[dict[str, Any]], response.data or [])

    if not rows:
        raise HTTPException(status_code=500, detail="Unable to save goal.")

    row = rows[0]
    return GoalResponse(
        id=int(row["id"]),
        monthly_target=float(row["monthly_target"]),
        weekly_investment=float(row["weekly_investment"]),
    )

@app.get("/dashboard", response_model=DashboardResponse, tags=["Dashboard"])
def get_dashboard() -> DashboardResponse:
    """Return the full dashboard: income summary, projection, and enriched holdings."""
    return load_dashboard()

@app.get("/chart", response_model=list[ChartPoint], tags=["Dashboard"])
def get_chart() -> list[ChartPoint]:
    """Return the monthly dividend history used to render the income chart."""
    response = execute_supabase(
        supabase_table("dividend_history").select("*").order("month"),
        "load chart",
    )
    rows = cast(list[dict[str, Any]], response.data or [])

    return [
        ChartPoint(
            month=date.fromisoformat(row["month"]),
            total_monthly_income=float(row["total_monthly_income"]),
            created_at=row.get("created_at"),
        )
        for row in rows
    ]

@app.post("/ai/chat", response_model=AIChatResponse, tags=["AI"])
def chat_with_portfolio(payload: AIChatRequest) -> AIChatResponse:
    """Answer a natural-language question about the user's portfolio via OpenRouter."""
    try:
        answer = answer_portfolio_question(payload.question)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"AI chat failed: {error}") from error

    return AIChatResponse(answer=answer)
