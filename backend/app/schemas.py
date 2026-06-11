from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class HoldingCreate(BaseModel):
        """Payload for creating a new portfolio holding."""

    ticker: str = Field(min_length=1, max_length=12)
    shares: float = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
                return value.strip().upper()


class HoldingUpdate(HoldingCreate):
        """Payload for updating an existing portfolio holding."""

    pass


class HoldingResponse(BaseModel):
        """Full holding record returned by the API, enriched with live market data."""

    id: int
    ticker: str
    shares: float
    price: float
    dividend_yield_percent: float
    annual_dividend_per_share: float
    annual_income: float
    monthly_income: float
    market_value: float
    created_at: datetime


class GoalCreate(BaseModel):
        """Payload for setting or updating the income goal."""

    monthly_target: float = Field(ge=0)
    weekly_investment: float = Field(ge=0)


class GoalResponse(BaseModel):
        """Persisted income goal record."""

    id: int | None = None
    monthly_target: float = 0
    weekly_investment: float = 0


class Recommendation(BaseModel):
        """Best-yield holding recommended for additional investment."""

    ticker: str
    monthly_income_per_dollar: float
    annual_dividend_yield_percent: float
    share_price: float


class Projection(BaseModel):
        """Forward-looking estimate of time to reach the monthly income goal."""

    remaining_monthly_income: float
    estimated_weeks_to_goal: float | None = None
    estimated_months_to_goal: float | None = None
    estimated_goal_date: date | None = None


class DashboardResponse(BaseModel):
        """Aggregated portfolio snapshot served to the frontend dashboard."""

    current_monthly_income: float
    monthly_target: float
    progress_percent: float
    projection: Projection
    recommendation: Recommendation | None = None
    holdings: list[HoldingResponse]


class ChartPoint(BaseModel):
        """Single data point in the dividend history chart."""

    month: date
    total_monthly_income: float
    created_at: datetime | None = None


class AIChatRequest(BaseModel):
        """User question submitted to the AI portfolio chat endpoint."""

    question: str = Field(min_length=1, max_length=1000)


class AIChatResponse(BaseModel):
        """AI-generated answer returned by the portfolio chat endpoint."""

    answer: str
