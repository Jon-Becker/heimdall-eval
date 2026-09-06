#!/usr/bin/env python3
"""End-to-end test for the OpenRouter judge harness.

Unlike scripts/test_judge.py, this makes one real, bounded OpenRouter request and
requires OPENROUTER_API_KEY. It is deliberately named outside the `test_*.py`
discovery pattern so that `make test` stays offline; run it with `make test-e2e`.
"""

import os
import unittest

import judge

# One request, no retries, and a short timeout: this must never fan out or hang.
E2E_TIMEOUT = 60.0
E2E_MAX_RETRIES = 0
E2E_RETRY_BACKOFF = 0.0

REQUIRED_KEYS = judge.KINDS["decompilation"]["required"]
PROMPT = (
    "Reply with a single JSON object and nothing else. Use exactly these keys: "
    '"score" set to the integer 100, "summary" set to the string "ok", and '
    '"differences" set to an empty array.'
)


class JudgeEndToEndTest(unittest.TestCase):
    """Exercises the live request path without repository, Foundry or heimdall fixtures."""

    def test_live_request_returns_valid_judge_json(self):
        api_key = judge.require_api_key()
        body = judge.build_request_body(
            os.environ.get("EVAL_MODEL", "").strip() or judge.DEFAULT_MODEL,
            judge.DEFAULT_TEMPERATURE,
            PROMPT,
        )
        payload = judge.post_chat_completion(
            body,
            api_key,
            os.environ.get("OPENROUTER_BASE_URL", "").strip() or judge.DEFAULT_BASE_URL,
            E2E_TIMEOUT,
            E2E_MAX_RETRIES,
            E2E_RETRY_BACKOFF,
        )

        result = judge.parse_result(judge.extract_content(payload), REQUIRED_KEYS)
        self.assertEqual(result["score"], 100)
        self.assertIsInstance(result["summary"], str)
        self.assertIsInstance(result["differences"], list)


if __name__ == "__main__":
    unittest.main()
