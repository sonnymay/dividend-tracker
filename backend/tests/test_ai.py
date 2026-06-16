import unittest
from unittest.mock import Mock, patch

from app.ai import answer_portfolio_question


class AIServiceTests(unittest.TestCase):
    @patch("app.ai._portfolio_context")
    def test_answer_portfolio_question_returns_setup_message_when_no_holdings(
        self,
        mock_portfolio_context,
    ) -> None:
        mock_portfolio_context.return_value = {"holdings": []}

        answer = answer_portfolio_question("When can I retire?")

        self.assertIn("Add dividend positions first", answer)
        mock_portfolio_context.assert_called_once()

    @patch("app.ai._portfolio_context")
    @patch("app.ai.requests.post")
    def test_answer_portfolio_question_answers_current_monthly_income_directly(
        self,
        mock_post,
        mock_portfolio_context,
    ) -> None:
        mock_portfolio_context.return_value = {
            "monthly_income": 10.2,
            "annual_income": 122.4,
            "monthly_target": 5000,
            "progress_percent": 0.2,
            "remaining_monthly_income": 4989.8,
            "holdings": [{"ticker": "SCHD"}],
        }

        answer = answer_portfolio_question("What is my current monthly dividend income?")

        self.assertEqual(answer, "Your current monthly dividend income is $10.20.")
        mock_post.assert_not_called()

    @patch("app.ai._portfolio_context")
    @patch("app.ai.requests.post")
    def test_answer_portfolio_question_answers_goal_tracking_directly(
        self,
        mock_post,
        mock_portfolio_context,
    ) -> None:
        mock_portfolio_context.return_value = {
            "monthly_income": 10.2,
            "annual_income": 122.4,
            "monthly_target": 5000,
            "progress_percent": 0.2,
            "remaining_monthly_income": 4989.8,
            "holdings": [{"ticker": "SCHD"}],
        }

        answer = answer_portfolio_question("How am I tracking toward my goal?")

        self.assertEqual(answer, "You are 0.20% of the way to your $5,000.00/month target.")
        mock_post.assert_not_called()

    @patch("app.ai._portfolio_context")
    @patch("app.ai._get_openrouter_headers")
    @patch("app.ai.requests.post")
    def test_answer_portfolio_question_sends_context_and_returns_response_text(
        self,
        mock_post,
        mock_get_openrouter_headers,
        mock_portfolio_context,
    ) -> None:
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Buy more SCHD carefully."}}]
        }
        mock_post.return_value = mock_response
        mock_get_openrouter_headers.return_value = {"Authorization": "Bearer key"}
        mock_portfolio_context.return_value = {
            "monthly_income": 10.2,
            "holdings": [{"ticker": "SCHD"}],
        }

        answer = answer_portfolio_question("  What should I buy next?  ")

        self.assertEqual(answer, "Buy more SCHD carefully.")
        mock_post.assert_called_once()
        create_kwargs = mock_post.call_args.kwargs
        self.assertEqual(create_kwargs["json"]["model"], "openrouter/free")
        self.assertEqual(create_kwargs["json"]["max_tokens"], 900)
        self.assertIn("What should I buy next?", create_kwargs["json"]["messages"][0]["content"])
        self.assertIn('"ticker": "SCHD"', create_kwargs["json"]["messages"][0]["content"])
        mock_response.raise_for_status.assert_called_once()


if __name__ == "__main__":
    unittest.main()
