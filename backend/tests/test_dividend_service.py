import unittest
from datetime import datetime

from app.schemas import GoalResponse, HoldingResponse
from app.services.dividend_service import build_dashboard, normalize_dividend_yield_percent


class DividendServiceTests(unittest.TestCase):
    def test_normalize_dividend_yield_percent_handles_decimal_and_percent_inputs(self) -> None:
        self.assertEqual(normalize_dividend_yield_percent(0.0344, price=30.91, annual_dividend_per_share=1.05), 3.44)
        self.assertEqual(normalize_dividend_yield_percent(3.44, price=30.91, annual_dividend_per_share=1.05), 3.44)
        self.assertEqual(normalize_dividend_yield_percent(None, price=30.91, annual_dividend_per_share=1.05), 3.397)

    def test_build_dashboard_returns_progress_projection_and_recommendation(self) -> None:
        holdings = [
            HoldingResponse(
                id=1,
                ticker="VYM",
                shares=20,
                price=120,
                dividend_yield_percent=3.2,
                annual_dividend_per_share=3.84,
                annual_income=76.8,
                monthly_income=6.4,
                market_value=2400,
                created_at=datetime.now(),
            ),
            HoldingResponse(
                id=2,
                ticker="SCHD",
                shares=15,
                price=80,
                dividend_yield_percent=3.8,
                annual_dividend_per_share=3.04,
                annual_income=45.6,
                monthly_income=3.8,
                market_value=1200,
                created_at=datetime.now(),
            ),
        ]
        goal = GoalResponse(id=1, monthly_target=100, weekly_investment=250)

        dashboard = build_dashboard(holdings, goal)

        self.assertEqual(dashboard.current_monthly_income, 10.2)
        self.assertEqual(dashboard.progress_percent, 10.2)
        self.assertEqual(dashboard.recommendation.ticker if dashboard.recommendation else None, "SCHD")
        self.assertIsNotNone(dashboard.projection.estimated_weeks_to_goal)


if __name__ == "__main__":
    unittest.main()
