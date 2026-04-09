from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import get_supabase
from app.schemas import (
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

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def list_raw_holdings() -> list[dict]:
    response = get_supabase().table("holdings").select("*").order("created_at").execute()
    return response.data or []


def get_goal_record() -> GoalResponse:
    response = get_supabase().table("goal").select("*").limit(1).execute()
    rows = response.data or []

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
    existing = (
        supabase.table("dividend_history").select("id").eq("month", current_month).limit(1).execute().data or []
    )
    payload = {"month": current_month, "total_monthly_income": round(total_monthly_income, 2)}

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


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/holdings", response_model=list[HoldingResponse])
def get_holdings() -> list[HoldingResponse]:
    return enrich_holdings(list_raw_holdings())


@app.post("/holdings", response_model=HoldingResponse, status_code=201)
def create_holding(payload: HoldingCreate) -> HoldingResponse:
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
    rows = response.data or []

    if not rows:
        raise HTTPException(status_code=500, detail="Unable to save holding.")

    return enrich_holdings(rows)[0]


@app.put("/holdings/{holding_id}", response_model=HoldingResponse)
def update_holding(holding_id: int, payload: HoldingUpdate) -> HoldingResponse:
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
    rows = response.data or []

    if not rows:
        raise HTTPException(status_code=404, detail="Holding not found.")

    return enrich_holdings(rows)[0]


@app.delete("/holdings/{holding_id}", status_code=204, response_class=Response)
def delete_holding(holding_id: int) -> Response:
    get_supabase().table("holdings").delete().eq("id", holding_id).execute()
    return Response(status_code=204)


@app.get("/goal", response_model=GoalResponse)
def get_goal() -> GoalResponse:
    return get_goal_record()


@app.post("/goal", response_model=GoalResponse)
def save_goal(payload: GoalCreate) -> GoalResponse:
    response = (
        get_supabase()
        .table("goal")
        .upsert(
            {"id": 1, "monthly_target": payload.monthly_target, "weekly_investment": payload.weekly_investment}
        )
        .execute()
    )
    rows = response.data or []

    if not rows:
        raise HTTPException(status_code=500, detail="Unable to save goal.")

    row = rows[0]
    return GoalResponse(
        id=int(row["id"]),
        monthly_target=float(row["monthly_target"]),
        weekly_investment=float(row["weekly_investment"]),
    )


@app.get("/dashboard", response_model=DashboardResponse)
def get_dashboard() -> DashboardResponse:
    return load_dashboard()


@app.get("/chart", response_model=list[ChartPoint])
def get_chart() -> list[ChartPoint]:
    dashboard = load_dashboard()
    response = get_supabase().table("dividend_history").select("*").order("month").execute()
    rows = response.data or []

    if not rows and dashboard.current_monthly_income >= 0:
        save_dividend_history(dashboard.current_monthly_income)
        rows = get_supabase().table("dividend_history").select("*").order("month").execute().data or []

    return [
        ChartPoint(
            month=date.fromisoformat(row["month"]),
            total_monthly_income=float(row["total_monthly_income"]),
            created_at=row.get("created_at"),
        )
        for row in rows
    ]
