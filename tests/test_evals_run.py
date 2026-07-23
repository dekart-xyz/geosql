import unittest
from unittest.mock import patch
import sys
from pathlib import Path

# Add evals to path so we can import run
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))

from run import (
    parse_args,
    build_assertion_prompt,
    build_isolated_assertion_prompt,
    format_generation_transcript,
    truncate_text,
)


class TestEvalsRun(unittest.TestCase):
    def test_parse_args_default_grading_mode(self):
        with patch.object(
            sys,
            "argv",
            ["run.py", "--model", "claude-sonnet-4-6", "--thinking-level", "high"],
        ):
            args = parse_args()
            self.assertEqual(args.grading_mode, "same-session")

    def test_parse_args_isolated_grading_mode(self):
        with patch.object(
            sys,
            "argv",
            [
                "run.py",
                "--model",
                "claude-sonnet-4-6",
                "--thinking-level",
                "high",
                "--grading-mode",
                "isolated",
            ],
        ):
            args = parse_args()
            self.assertEqual(args.grading_mode, "isolated")

    def test_truncate_text_short(self):
        text = "Short text under limit"
        res = truncate_text(text, max_chars=100)
        self.assertEqual(res, text)

    def test_truncate_text_long_head_tail(self):
        head_data = "START_" + ("A" * 200)
        middle_data = "M" * 500
        tail_data = ("B" * 200) + "_END"
        full_text = head_data + middle_data + tail_data
        max_chars = 100

        res = truncate_text(full_text, max_chars=max_chars)
        self.assertLessEqual(len(res), max_chars)
        self.assertTrue(res.startswith("START_"))
        self.assertTrue(res.endswith("_END"))
        self.assertIn("...[middle content truncated]...", res)

    def test_truncate_text_edge_cases(self):
        # Empty / None value
        self.assertEqual(truncate_text(None), "")
        self.assertEqual(truncate_text(""), "")
        # Small max_chars boundary
        self.assertEqual(truncate_text("abcdefghijk", max_chars=5), "abcde")

    def test_format_generation_transcript_single_block_and_total_cap(self):
        # Test long output inside a single block and total transcript limit
        long_stdout = "HEAD_" + ("X" * 1000) + "_TAIL"
        mock_events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Running tool..."},
                        {
                            "type": "tool_use",
                            "name": "bq_query",
                            "input": {"query": "SELECT 1"},
                        },
                    ]
                },
            },
            {
                "type": "user",
                "tool_use_result": {
                    "stdout": long_stdout,
                    "stderr": "",
                },
            },
        ]

        # Block max_chars=100, max_total_chars=500
        transcript = format_generation_transcript(
            mock_events, max_chars_per_block=100, max_total_chars=500
        )
        self.assertLessEqual(len(transcript), 500)
        self.assertIn("[ASSISTANT TEXT]", transcript)
        self.assertIn("[TOOL USE: bq_query]", transcript)
        self.assertIn("HEAD_", transcript)
        self.assertIn("_TAIL", transcript)
        self.assertIn("...[middle content truncated]...", transcript)

    def test_build_isolated_assertion_prompt(self):
        mock_events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "list_connections",
                            "input": {},
                        }
                    ]
                },
            }
        ]
        skill_prompt = "/geosql Show London Boroughs"
        output_text = "Here is the SQL query and map output."
        assertions = ["Used list_connections tool", "Cost under 10GB"]

        prompt = build_isolated_assertion_prompt(
            skill_prompt, output_text, assertions, gen_events=mock_events
        )
        self.assertIn("=== ORIGINAL TASK PROMPT ===", prompt)
        self.assertIn(skill_prompt, prompt)
        self.assertIn("=== READ-ONLY EXECUTION TRANSCRIPT (Tool Calls & Outputs) ===", prompt)
        self.assertIn("[TOOL USE: list_connections]", prompt)
        self.assertIn("=== FINAL GENERATED RESPONSE ===", prompt)
        self.assertIn(output_text, prompt)
        self.assertIn("Used list_connections tool", prompt)
        self.assertIn("Cost under 10GB", prompt)


if __name__ == "__main__":
    unittest.main()
