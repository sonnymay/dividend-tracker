from __future__ import annotations

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

app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
                    "Dividend portfolio tracker API. "
                    "Provides live holdings data, income projections, "
                    "payout history, and an AI portfolio chat backed by Claude."
        ),
)

app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)


def list_raw_holdings() -> list[dict[str, Any]]:
        response = get_supabase().table("holdings").select("*").order("created_at").execute()
        return cast(list[dict[str, Any]], response.data or [])


def get_goal_record() -> GoalResponse:
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


def save_dividend_history(total_monthly_income: float) -> None:
        supabase = get_supabase()
        current_month = date.today().replace(day=1).isoformat()
        existing = cast(
            list[dict[str, Any]],
            supabase.table("dividend_history")
            .select("id")
            .eq("month", current_month)
            .limit(1)
            .execute()
            .data
            or [],
        )
        payload: dict[str, Any] = {
            "month": current_month,
            "total_monthly_income": round(total_monthly_income, 2),
        }

    if existing:
                supabase.table("dividend_history").update(payload).eq("id", existing[0]["id"]).execute()
else:
            supabase.table("dividend_history").insert(payload).execute()


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


@app.get("/holdings", response_model=list[HoldingResponse], tags=["Holdings"])
def get_holdings() -> list[HoldingResponse]:
        """Return all holdings enriched with live market data."""
        return enrich_holdings(list_raw_holdings())


@app.post("/holdings", response_model=HoldingResponse, status_code=201, tags=["Holdings"])
def create_holding(payload: HoldingCreate) -> HoldingResponse:
        """Add a new holding. Validates the ticker against yfinance before persisting."""
        try:
                    fetch_ticker_snapshot(payload.ticker)
except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    response = (
                get_supabase()
                .table("holdings")
                .insert({"ticker": payload.ticker, "shares": payload.shares})
                .execute()
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

    response = (
                get_supabase()
                .table("holdings")
                .update({"ticker": payload.ticker, "shares": payload.shares})
                .eq("id", holding_id)
                .execute()
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

    supabase = get_supabase()
    existing_rows = cast(
                list[dict[str, Any]],
                supabase.table("holdings").select("*").eq("ticker", normalized_ticker).execute().data or [],
    )

    if not existing_rows:
                raise HTTPException(status_code=404, detail="Holding group not found.")

    supabase.table("holdings").delete().eq("ticker", normalized_ticker).execute()
    response = (
                supabase.table("holdings")
                .insert({"ticker": payload.ticker, "shares": payload.shares})
                .execute()
    )
    rows = cast(list[dict[str, Any]], response.data or [])

    if not rows:
                raise HTTPException(status_code=500, detail="Unable to replace holding group.")

    return enrich_holdings(rows)[0]


@app.delete("/holdings/{holding_id}", status_code=204, response_class=Response, tags=["Holdings"])
def delete_holding(holding_id: int) -> Response:
        """Delete a single holding by ID."""
        get_supabase().table("holdings").delete().eq("id", holding_id).execute()
        return Response(status_code=204)


@app.delete(
        "/holdings/by-ticker/{ticker}", status_code=204, response_class=Response, tags=["Holdings"]
)
def delete_holding_group(ticker: str) -> Response:
        """Delete all holdings for a given ticker symbol."""
        normalized_ticker = ticker.strip().upper()
        get_supabase().table("holdings").delete().eq("ticker", normalized_ticker).execute()
        return Response(status_code=204)


@app.get("/goal", response_model=GoalResponse, tags=["Goal"])
def get_goal() -> GoalResponse:
        """Return the current monthly income goal and weekly investment target."""
        return get_goal_record()


@app.post("/goal", response_model=GoalResponse, tags=["Goal"])
def save_goal(payload: GoalCreate) -> GoalResponse:
        """Upsert the income goal (always stored as row id=1)."""
        response = (
            get_supabase()
            .table("goal")
            .upsert(
                {
                    "id": 1,
                    "monthly_target": payload.monthly_target,
                    "weekly_investment": payload.weekly_investment,
                }
            )
            .execute()
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
        response = get_supabase().table("dividend_history").select("*").order("month").execute()
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
        """Answer a natural-language question about the user's portfolio via Claude."""
        try:
                    answer = answer_portfolio_question(payload.question)
except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
except Exception as error:
        raise HTTPException(status_code=500, detail=f"AI chat failed: {error}") from error

    return AIChatResponse(answer=answer)
