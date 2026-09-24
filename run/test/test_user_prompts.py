"""Regression tests for simulated-user prompt constraints."""

import unittest

from run.prompts import (
    STATIC_USER_PROMPT,
    USER_TEXT_ONLY_PROMPT_EASY,
    USER_TEXT_ONLY_PROMPT_HARD,
)


class UserPromptTests(unittest.TestCase):
    def test_all_user_modes_preserve_task_date_expressions(self) -> None:
        prompts = {
            "easy": USER_TEXT_ONLY_PROMPT_EASY,
            "hard": USER_TEXT_ONLY_PROMPT_HARD,
            "static": STATIC_USER_PROMPT,
        }

        for mode, prompt in prompts.items():
            with self.subTest(mode=mode):
                normalized = prompt.lower()
                self.assertIn("first-sentence date fidelity", normalized)
                self.assertIn("highest priority", normalized)
                self.assertIn("the first sentence", normalized)
                self.assertIn("copy the entire expression verbatim", normalized)
                self.assertIn("including every introductory word", normalized)
                self.assertIn(
                    "preserving its original language and wording", normalized
                )
                self.assertIn("calculate, resolve, normalize, translate", normalized)
                self.assertIn("may appear wherever it sounds natural", normalized)
                self.assertIn("has no required position", normalized)
                self.assertIn("normal, natural customer language", normalized)
                self.assertNotIn("nothing may appear before the user_id", normalized)
                self.assertNotIn("immediately after the user_id", normalized)


if __name__ == "__main__":
    unittest.main()
