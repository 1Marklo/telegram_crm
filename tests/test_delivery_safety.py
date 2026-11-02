"""Regression tests for safe handling of ambiguous Telegram delivery outcomes."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from src.outbox import mark_outbox_uncertain
from src.outbox_worker import is_retryable_error, is_uncertain_error


class DeliverySafetyTests(unittest.TestCase):
    def test_ambiguous_transport_errors_are_not_retried(self):
        for message in (
            "Ошибка отправки: connection reset",
            "network error while sending",
            "request timed out",
            "server disconnected",
        ):
            with self.subTest(message=message):
                self.assertTrue(is_uncertain_error(message))

    def test_privacy_and_floodwait_are_non_retryable(self):
        for message in (
            "Пользователь запретил сообщения от незнакомцев",
            "FloodWait после всех retry: нужно подождать 60s",
            "Контакт отказался от сообщений",
        ):
            with self.subTest(message=message):
                self.assertFalse(is_retryable_error(message))

    def test_uncertain_outcome_is_not_treated_as_retryable_transport_error(self):
        self.assertFalse(is_retryable_error("Ошибка отправки: connection reset"))
        self.assertTrue(is_uncertain_error("Ошибка отправки: connection reset"))

    def test_mark_outbox_uncertain_persists_non_retryable_state(self):
        async def run():
            db = MagicMock()
            db.commit = AsyncMock()
            db.rollback = AsyncMock()
            outbox = MagicMock()
            outbox.id = 42
            outbox.attempts = 1

            await mark_outbox_uncertain(db, outbox, "network timeout")

            self.assertEqual(outbox.status, "uncertain")
            self.assertIsNone(outbox.next_attempt_at)
            self.assertEqual(outbox.attempts, 2)
            db.add.assert_called_once()
            db.commit.assert_awaited_once()

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
