#!/usr/bin/env python3
"""Unit tests for the OpenRouter judge harness. These never call the real API."""

import json
import unittest
import urllib.error
from unittest import mock

import judge


def http_error(code):
    return urllib.error.HTTPError("https://example.test", code, "err", {}, None)


def ok_response(payload):
    response = mock.MagicMock()
    response.read.return_value = json.dumps(payload).encode()
    response.__enter__.return_value = response
    return response


class ExtractContentTest(unittest.TestCase):
    def test_extracts_assistant_message(self):
        payload = {"choices": [{"message": {"content": "{}"}}]}
        self.assertEqual(judge.extract_content(payload), "{}")

    def test_rejects_missing_choices(self):
        with self.assertRaises(judge.JudgeError):
            judge.extract_content({"choices": []})

    def test_rejects_empty_content(self):
        with self.assertRaises(judge.JudgeError):
            judge.extract_content({"choices": [{"message": {"content": "   "}}]})


class ParseResultTest(unittest.TestCase):
    required = ("score", "summary", "differences")
    result = {"score": 80, "summary": "ok", "differences": []}

    def test_parses_bare_json(self):
        self.assertEqual(judge.parse_result(json.dumps(self.result), self.required), self.result)

    def test_tolerates_markdown_fence(self):
        fenced = f"```json\n{json.dumps(self.result)}\n```"
        self.assertEqual(judge.parse_result(fenced, self.required), self.result)

    def test_tolerates_unlabelled_fence(self):
        fenced = f"```\n{json.dumps(self.result)}\n```"
        self.assertEqual(judge.parse_result(fenced, self.required), self.result)

    def test_rejects_invalid_json(self):
        with self.assertRaises(judge.JudgeError):
            judge.parse_result("not json", self.required)

    def test_rejects_non_object(self):
        with self.assertRaises(judge.JudgeError):
            judge.parse_result("[1, 2]", self.required)

    def test_rejects_missing_keys(self):
        with self.assertRaises(judge.JudgeError):
            judge.parse_result('{"score": 80}', self.required)

    def test_rejects_out_of_range_score(self):
        with self.assertRaises(judge.JudgeError):
            judge.parse_result('{"score": 101, "summary": "", "differences": []}', self.required)

    def test_rejects_non_integer_score(self):
        with self.assertRaises(judge.JudgeError):
            judge.parse_result('{"score": "80", "summary": "", "differences": []}', self.required)


class RequestBodyTest(unittest.TestCase):
    def test_temperature_is_numeric(self):
        body = judge.build_request_body("vendor/model", 0.0, "prompt")
        self.assertEqual(body["model"], "vendor/model")
        self.assertIsInstance(body["temperature"], float)
        self.assertEqual(body["messages"], [{"role": "user", "content": "prompt"}])
        self.assertIn('"temperature": 0.0', json.dumps(body, indent=2))

    def test_temperature_is_read_from_environment(self):
        with mock.patch.dict(judge.os.environ, {"EVAL_TEMPERATURE": "0.7"}):
            self.assertEqual(judge.env_float("EVAL_TEMPERATURE", judge.DEFAULT_TEMPERATURE), 0.7)

    def test_temperature_defaults_to_zero(self):
        with mock.patch.dict(judge.os.environ, {"EVAL_TEMPERATURE": ""}):
            self.assertEqual(judge.env_float("EVAL_TEMPERATURE", judge.DEFAULT_TEMPERATURE), 0.0)


class ApiKeyTest(unittest.TestCase):
    def test_missing_key_fails(self):
        with mock.patch.dict(judge.os.environ, {"OPENROUTER_API_KEY": ""}):
            with self.assertRaises(judge.JudgeError):
                judge.require_api_key()

    def test_check_env_exits_non_zero_without_key(self):
        with mock.patch.dict(judge.os.environ, {"OPENROUTER_API_KEY": ""}):
            self.assertEqual(judge.main(["--check-env"]), 1)

    def test_check_env_succeeds_with_key(self):
        with mock.patch.dict(judge.os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            self.assertEqual(judge.main(["--check-env"]), 0)


class RetryTest(unittest.TestCase):
    def post(self, timeout=1.0, max_retries=2, backoff=0.0):
        return judge.post_chat_completion(
            {"model": "vendor/model"}, "test-key", judge.DEFAULT_BASE_URL, timeout, max_retries, backoff
        )

    @mock.patch("judge.time.sleep")
    @mock.patch("judge.urllib.request.urlopen")
    def test_retries_transient_status_then_succeeds(self, urlopen, sleep):
        urlopen.side_effect = [http_error(429), http_error(503), ok_response({"ok": True})]
        self.assertEqual(self.post(), {"ok": True})
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @mock.patch("judge.time.sleep")
    @mock.patch("judge.urllib.request.urlopen")
    def test_does_not_retry_permanent_status(self, urlopen, sleep):
        urlopen.side_effect = http_error(401)
        with self.assertRaises(judge.JudgeError):
            self.post()
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @mock.patch("judge.time.sleep")
    @mock.patch("judge.urllib.request.urlopen")
    def test_retries_are_bounded(self, urlopen, sleep):
        urlopen.side_effect = http_error(500)
        with self.assertRaises(judge.JudgeError):
            self.post(max_retries=2)
        self.assertEqual(urlopen.call_count, 3)

    @mock.patch("judge.time.sleep")
    @mock.patch("judge.urllib.request.urlopen")
    def test_backoff_grows(self, urlopen, sleep):
        urlopen.side_effect = [http_error(500), http_error(500), ok_response({"ok": True})]
        self.post(backoff=1.0)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1.0, 2.0])

    @mock.patch("judge.time.sleep")
    @mock.patch("judge.urllib.request.urlopen")
    def test_retries_network_errors(self, urlopen, sleep):
        urlopen.side_effect = [urllib.error.URLError("timed out"), ok_response({"ok": True})]
        self.assertEqual(self.post(), {"ok": True})


if __name__ == "__main__":
    unittest.main()
