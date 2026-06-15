import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.ai import answer_portfolio_question


class AIServiceTests(unittest.TestCase):
    @patch("app.ai._portfolio_context")
    @patch("app.ai._get_client")
    def test_answer_portfolio_question_returns_setup_message_when_no_holdings(
        self,
        mock_get_client,
        mock_portfolio_context,
    ) -> None:
        mock_get_client.return_value = object()
        mock_portfolio_context.return_value = {"holdings": []}

        answer = answer_portfolio_question("When can I retire?")

        self.assertIn("Add dividend positions first", answer)
        mock_get_client.assert_called_once()
        mock_portfolio_context.assert_called_once()

    @patch("app.ai._portfolio_context")
    @patch("app.ai._get_client")
    def test_answer_portfolio_question_sends_context_and_returns_text_blocks(
        self,
        mock_get_client,
        mock_portfolio_context,
    ) -> None:
        mock_create = Mock(
            return_value=SimpleNamespace(
                content=[
                    SimpleNamespace(type="text", text="Buy more SCHD carefully."),
                    SimpleNamespace(type="tool_use", text="ignored"),
                ]
            )
        )
        mock_get_client.return_value = SimpleNamespace(messages=SimpleNamespace(create=mock_create))
        mock_portfolio_context.return_value = {
            "monthly_income": 10.2,
            "holdings": [{"ticker": "SCHD"}],
        }

        answer = answer_portfolio_question("  What should I buy next?  ")

        self.assertEqual(answer, "Buy more SCHD carefully.")
        mock_create.assert_called_once()
        create_kwargs = mock_create.call_args.kwargs
        self.assertEqual(create_kwargs["max_tokens"], 900)
        self.assertIn("What should I buy next?", create_kwargs["messages"][0]["content"])
        self.assertIn('"ticker": "SCHD"', create_kwargs["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
