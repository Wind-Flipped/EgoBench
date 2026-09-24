"""Regression tests for the repository's textual tool-call protocol."""

import json
import tempfile
import unittest
from pathlib import Path

from run.utils import build_message_with_media, check_tool_call, execute_tool


class _FakeDatabase:
    def expected_tool(self, value: str) -> dict[str, str]:
        return {"value": value}


class ToolCallProtocolTests(unittest.TestCase):
    def test_prose_wrapped_call_does_not_treat_parameter_name_as_tool(self) -> None:
        response = """I will add it now.
[{"tool_name": "expected_tool", "parameters": {"name": "Eyeglasses", "value": "ok"}}]
"""

        is_tool, calls = check_tool_call(response)

        self.assertTrue(is_tool)
        self.assertEqual("expected_tool", calls[0]["tool_name"])
        self.assertEqual("Eyeglasses", calls[0]["parameters"]["name"])

    def test_name_and_tool_call_are_not_tool_identifiers(self) -> None:
        for response in (
            '{"name": "expected_tool", "arguments": {"value": "ok"}}',
            '{"tool_call": "expected_tool", "parameters": {"value": "ok"}}',
        ):
            with self.subTest(response=response):
                self.assertEqual((False, None), check_tool_call(response))

    def test_execute_tool_requires_tool_name(self) -> None:
        result = execute_tool(
            _FakeDatabase(),
            {"name": "expected_tool", "arguments": {"value": "ok"}},
        )

        self.assertEqual("unknown", result[0]["tool_name"])
        self.assertEqual(
            {"error": "Missing tool identifier 'tool_name'"},
            json.loads(result[0]["content"]),
        )

    def test_execute_tool_accepts_tool_name(self) -> None:
        result = execute_tool(
            _FakeDatabase(),
            {"tool_name": "expected_tool", "parameters": {"value": "ok"}},
        )

        self.assertEqual({"value": "ok"}, json.loads(result[0]["content"]))

    def test_local_video_is_encoded_for_openai_compatible_models(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir, "sample.mp4")
            path.write_bytes(b"video")

            content = build_message_with_media(
                "hello",
                str(path),
                use_vision=True,
                service_model_name="qwen3.6-plus",
            )

            self.assertTrue(
                content[1]["video_url"]["url"].startswith(
                    "data:video/mp4;base64,"
                )
            )

    def test_kimi_receives_local_path_for_its_compression_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir, "sample.mp4")
            path.write_bytes(b"video")

            content = build_message_with_media(
                "hello",
                str(path),
                use_vision=True,
                service_model_name="kimi-k2.6",
            )

            self.assertEqual(str(path), content[1]["video_url"]["url"])


if __name__ == "__main__":
    unittest.main()
