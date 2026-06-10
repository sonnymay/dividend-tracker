import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app, save_dividend_history
from app.schemas import HoldingResponse


class HealthCheckTests(unittest.TestCase):
    def test_healthcheck_returns_ok(self) -> None:
        client = TestClient(app)

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class CreateHoldingTests(unittest.TestCase):
    @patch("app.main.enrich_holdings")
    @patch("app.main.fetch_ticker_snapshot")
    @patch("app.main.get_supabase")
    def test_create_holding_returns_201_with_enriched_holding(
        self,
        mock_get_supabase,
        mock_fetch_ticker_snapshot,
        mock_enrich_holdings,
    ) -> None:
        client = TestClient(app)

        mock_fetch_ticker_snapshot.return_value = object()
        mock_table = mock_get_supabase.return_value.table.return_value
        mock_table.insert.return_value.execute.return_value.data = [
            {"id": 1, "ticker": "VYM", "shares": 10, "created_at": datetime.now().isoformat()}
        ]
        mock_enrich_holdings.return_value = [
            HoldingResponse(
                id=1,
                ticker="VYM",
                shares=10,
                price=120.0,
                dividend_yield_percent=3.2,
                annual_dividend_per_share=3.84,
                annual_income=38.4,
                monthly_income=3.2,
                market_value=1200.0,
                created_at=datetime.now(),
            )
        ]

        response = client.post("/holdings", json={"ticker": "vym", "shares": 10})

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["ticker"], "VYM")
        self.assertEqual(data["shares"], 10)
        mock_fetch_ticker_snapshot.assert_called_once_with("VYM")
        mock_table.insert.assert_called_once_with({"ticker": "VYM", "shares": 10.0})
        mock_enrich_holdings.assert_called_once()

    @patch("app.main.fetch_ticker_snapshot")
    def test_create_holding_returns_400_for_invalid_ticker(
        self,
        mock_fetch_ticker_snapshot,
    ) -> None:
        client = TestClient(app)
        mock_fetch_ticker_snapshot.side_effect = ValueError("Unknown ticker: FAKE")

        response = client.post("/holdings", json={"ticker": "FAKE", "shares": 5})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown ticker", response.json()["detail"])


class ListHoldingTests(unittest.TestCase):
    @patch("app.main.enrich_holdings")
    @patch("app.main.list_raw_holdings")
    def test_get_holdings_returns_enriched_holdings(
        self,
        mock_list_raw_holdings,
        mock_enrich_holdings,
    ) -> None:
        client = TestClient(app)
        raw_holdings = [{"id": 1, "ticker": "VYM", "shares": 10}]
        mock_list_raw_holdings.return_value = raw_holdings
        mock_enrich_holdings.return_value = [
            HoldingResponse(
                id=1,
                ticker="VYM",
                shares=10,
                price=120.0,
                dividend_yield_percent=3.2,
                annual_dividend_per_share=3.84,
                annual_income=38.4,
                monthly_income=3.2,
                market_value=1200.0,
                created_at=datetime.now(),
            )
        ]

        response = client.get("/holdings")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["ticker"], "VYM")
        mock_enrich_holdings.assert_called_once_with(raw_holdings)


class ReplaceHoldingGroupTests(unittest.TestCase):
    @patch("app.main.enrich_holdings")
    @patch("app.main.fetch_ticker_snapshot")
    @patch("app.main.get_supabase")
    def test_replace_holding_group_returns_enriched_replacement(
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
            {"id": 12, "ticker": "VOO", "shares": 3, "created_at": datetime.now().isoformat()}
        ]
        mock_enrich_holdings.return_value = [
            HoldingResponse(
                id=12,
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

        response = client.put("/holdings/by-ticker/schd", json={"ticker": "voo", "shares": 3})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ticker"], "VOO")
        mock_fetch_ticker_snapshot.assert_called_once_with("VOO")
        mock_table.select.return_value.eq.assert_called_once_with("ticker", "SCHD")
        mock_table.delete.return_value.eq.assert_called_once_with("ticker", "SCHD")
        mock_table.insert.assert_called_once_with({"ticker": "VOO", "shares": 3.0})
        mock_enrich_holdings.assert_called_once()


class DeleteHoldingTests(unittest.TestCase):
    @patch("app.main.get_supabase")
    def test_delete_holding_returns_204(self, mock_get_supabase) -> None:
        client = TestClient(app)
        mock_table = mock_get_supabase.return_value.table.return_value
        mock_table.delete.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete("/holdings/42")

        self.assertEqual(response.status_code, 204)
        mock_table.delete.return_value.eq.assert_called_once_with("id", 42)

    @patch("app.main.get_supabase")
    def test_delete_holding_group_by_ticker_returns_204(self, mock_get_supabase) -> None:
        client = TestClient(app)
        mock_table = mock_get_supabase.return_value.table.return_value
        mock_table.delete.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete("/holdings/by-ticker/SCHD")

        self.assertEqual(response.status_code, 204)
        mock_table.delete.return_value.eq.assert_called_once_with("ticker", "SCHD")


class GoalTests(unittest.TestCase):
    @patch("app.main.get_supabase")
    def test_get_goal_returns_default_when_no_rows(self, mock_get_supabase) -> None:
        client = TestClient(app)
        mock_get_supabase.return_value.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []

        response = client.get("/goal")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["monthly_target"], 0)
        self.assertEqual(data["weekly_investment"], 0)

    @patch("app.main.get_supabase")
    def test_save_goal_persists_and_returns_goal(self, mock_get_supabase) -> None:
        client = TestClient(app)
        mock_table = mock_get_supabase.return_value.table.return_value
        mock_table.upsert.return_value.execute.return_value.data = [
            {"id": 1, "monthly_target": 5000.0, "weekly_investment": 500.0}
        ]

        response = client.post("/goal", json={"monthly_target": 5000, "weekly_investment": 500})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["monthly_target"], 5000.0)
        self.assertEqual(data["weekly_investment"], 500.0)
        mock_table.upsert.assert_called_once_with(
            {"id": 1, "monthly_target": 5000.0, "weekly_investment": 500.0}
        )

    @patch("app.main.get_supabase")
    def test_save_goal_returns_500_when_supabase_returns_no_data(self, mock_get_supabase) -> None:
        client = TestClient(app)
        mock_table = mock_get_supabase.return_value.table.return_value
        mock_table.upsert.return_value.execute.return_value.data = []

        response = client.post("/goal", json={"monthly_target": 1000, "weekly_investment": 200})

        self.assertEqual(response.status_code, 500)


class ChartTests(unittest.TestCase):
    @patch("app.main.get_supabase")
    def test_get_chart_returns_sorted_chart_points(self, mock_get_supabase) -> None:
        client = TestClient(app)
        mock_get_supabase.return_value.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
            {
                "month": "2025-01-01",
                "total_monthly_income": 320.50,
                "created_at": "2025-01-31T12:00:00",
            },
            {
                "month": "2025-02-01",
                "total_monthly_income": 340.75,
                "created_at": "2025-02-28T12:00:00",
            },
        ]

        response = client.get("/chart")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["month"], "2025-01-01")
        self.assertAlmostEqual(data[0]["total_monthly_income"], 320.50)
        self.assertEqual(data[1]["month"], "2025-02-01")

    @patch("app.main.get_supabase")
    def test_get_chart_returns_empty_list_when_no_history(self, mock_get_supabase) -> None:
        client = TestClient(app)
        mock_get_supabase.return_value.table.return_value.select.return_value.order.return_value.execute.return_value.data = []

        response = client.get("/chart")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


class DividendHistoryTests(unittest.TestCase):
    @patch("app.main.get_supabase")
    def test_save_dividend_history_inserts_when_month_is_missing(self, mock_get_supabase) -> None:
        mock_table = mock_get_supabase.return_value.table.return_value
        mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        save_dividend_history(12.345)

        mock_table.insert.assert_called_once()
        self.assertEqual(mock_table.insert.call_args.args[0]["total_monthly_income"], 12.35)

    @patch("app.main.get_supabase")
    def test_save_dividend_history_updates_existing_month(self, mock_get_supabase) -> None:
        mock_table = mock_get_supabase.return_value.table.return_value
        mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": 7}
        ]

        save_dividend_history(8.0)

        mock_table.update.assert_called_once()
        mock_table.update.return_value.eq.assert_called_once_with("id", 7)


class AIChatTests(unittest.TestCase):
    @patch("app.main.answer_portfolio_question")
    def test_ai_chat_returns_answer(self, mock_answer_portfolio_question) -> None:
        client = TestClient(app)
        mock_answer_portfolio_question.return_value = "Buy more SCHD carefully."

        response = client.post("/ai/chat", json={"question": "What should I buy next?"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"answer": "Buy more SCHD carefully."})
        mock_answer_portfolio_question.assert_called_once_with("What should I buy next?")

    @patch("app.main.answer_portfolio_question")
    def test_ai_chat_returns_503_for_runtime_error(self, mock_answer_portfolio_question) -> None:
        client = TestClient(app)
        mock_answer_portfolio_question.side_effect = RuntimeError(
            "ANTHROPIC_API_KEY is not configured."
        )

        response = client.post("/ai/chat", json={"question": "Can you help?"})

        self.assertEqual(response.status_code, 503)
        self.assertIn("ANTHROPIC_API_KEY", response.json()["detail"])

    @patch("app.main.answer_portfolio_question")
    def test_ai_chat_returns_500_for_unexpected_error(self, mock_answer_portfolio_question) -> None:
        client = TestClient(app)
        mock_answer_portfolio_question.side_effect = ValueError("boom")

        response = client.post("/ai/chat", json={"question": "Can you help?"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "AI chat failed: boom")


if __name__ == "__main__":
    unittest.main()
