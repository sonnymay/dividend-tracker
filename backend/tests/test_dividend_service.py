import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
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

    @patch("app.main.enrich_holdings")
    @patch("app.main.fetch_ticker_snapshot")
    @patch("app.main.get_supabase")
    def test_update_holding_returns_enriched_record(
        self,
        mock_get_supabase,
        mock_fetch_ticker_snapshot,
        mock_enrich_holdings,
    ) -> None:
        client = TestClient(app)

        mock_fetch_ticker_snapshot.return_value = object()
        mock_table = mock_get_supabase.return_value.table.return_value
        mock_update = mock_table.update.return_value
        mock_eq = mock_update.eq.return_value
        mock_eq.execute.return_value.data = [
            {"id": 7, "ticker": "SCHD", "shares": 12, "created_at": datetime.now().isoformat()}
        ]
        mock_enrich_holdings.return_value = [
            HoldingResponse(
                id=7,
                ticker="SCHD",
                shares=12,
                price=30.94,
                dividend_yield_percent=3.44,
                annual_dividend_per_share=1.05,
                annual_income=12.66,
                monthly_income=1.05,
                market_value=371.28,
                created_at=datetime.now(),
            )
        ]

        response = client.put("/holdings/7", json={"ticker": "schd", "shares": 12})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ticker"], "SCHD")
        mock_fetch_ticker_snapshot.assert_called_once_with("SCHD")
        mock_table.update.assert_called_once_with({"ticker": "SCHD", "shares": 12.0})
        mock_update.eq.assert_called_once_with("id", 7)

    @patch("app.main.enrich_holdings")
    @patch("app.main.fetch_ticker_snapshot")
    @patch("app.main.get_supabase")
    def test_replace_holding_group_replaces_all_matching_rows(
        self,
        mock_get_supabase,
        mock_fetch_ticker_snapshot,
        mock_enrich_holdings,
    ) -> None:
        client = TestClient(app)

        mock_fetch_ticker_snapshot.return_value = object()
        mock_table = mock_get_supabase.return_value.table.return_value

        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1, "ticker": "SCHD", "shares": 10},
            {"id": 2, "ticker": "SCHD", "shares": 5},
        ]
        mock_table.insert.return_value.execute.return_value.data = [
            {"id": 9, "ticker": "VOO", "shares": 3, "created_at": datetime.now().isoformat()}
        ]
        mock_enrich_holdings.return_value = [
            HoldingResponse(
                id=9,
                ticker="VOO",
                shares=3,
                price=500,
                dividend_yield_percent=1.25,
                annual_dividend_per_share=6.25,
                annual_income=18.75,
                monthly_income=1.56,
                market_value=1500,
                created_at=datetime.now(),
            )
        ]

        response = client.put("/holdings/by-ticker/SCHD", json={"ticker": "voo", "shares": 3})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ticker"], "VOO")
        mock_fetch_ticker_snapshot.assert_called_once_with("VOO")
        mock_table.delete.return_value.eq.assert_called_once_with("ticker", "SCHD")
        mock_table.insert.assert_called_once_with({"ticker": "VOO", "shares": 3.0})


if __name__ == "__main__":
    unittest.main()
