#!/usr/bin/env python3
"""LLM judge for heimdall-eval, backed by OpenRouter's chat completions API."""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TIMEOUT = 300.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF = 2.0

RETRYABLE_STATUSES = frozenset({408, 409, 429, 500, 502, 503, 504})

FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n(.*?)\n?\s*```\s*$", re.DOTALL)

# Judge kinds: prompt file, required output keys, and the sections wrapping the inputs.
KINDS = {
    "decompilation": {
        "prompt": "DECOMPILATION_PROMPT.md",
        "required": ("score", "summary", "differences"),
        "source_tag": "original",
        "artifact_tag": "decompiled",
    },
    "cfg": {
        "prompt": "CFG_PROMPT.md",
        "required": ("score", "summary", "missing_paths", "extra_paths", "observations"),
        "source_tag": "original_solidity",
        "artifact_tag": 'cfg format="dot"',
    },
}


class JudgeError(Exception):
    """Fatal, non-retryable evaluation failure."""


def env_float(name, default):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        raise JudgeError(f"{name} must be a number, got {raw!r}")


def env_int(name, default):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise JudgeError(f"{name} must be an integer, got {raw!r}")


def require_api_key():
    """Return the API key, failing clearly before any expensive work is started."""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise JudgeError(
            "OPENROUTER_API_KEY is not set. Export an OpenRouter API key before running evaluations."
        )
    return key


def build_request_body(model, temperature, prompt):
    return {
        "model": model,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }


def strip_fence(text):
    """Remove a surrounding markdown fence, if present."""
    match = FENCE_RE.match(text.strip())
    return match.group(1) if match else text.strip()


def extract_content(payload):
    """Pull the assistant message content out of a chat completions response."""
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise JudgeError("API response did not contain an assistant message")
    if not isinstance(content, str) or not content.strip():
        raise JudgeError("API response contained an empty assistant message")
    return content


def parse_result(content, required_keys):
    """Parse and validate the judge output against the expected schema."""
    try:
        result = json.loads(strip_fence(content))
    except json.JSONDecodeError as exc:
        raise JudgeError(f"Model output was not valid JSON: {exc}")

    if not isinstance(result, dict):
        raise JudgeError("Model output was not a JSON object")

    missing = [key for key in required_keys if key not in result]
    if missing:
        raise JudgeError(f"Model output is missing required keys: {', '.join(missing)}")

    score = result["score"]
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
        raise JudgeError(f"Model output 'score' must be an integer 0-100, got {score!r}")

    return result


def create_ssl_context():
    """Create a verified TLS context, loading a common system bundle if needed.

    Some macOS Python installations have no configured trust store even though the
    operating system provides one at ``/etc/ssl/cert.pem``. Never disable
    certificate verification; use that system bundle only when the default store
    is empty.
    """
    context = ssl.create_default_context()
    if context.cert_store_stats().get("x509_ca", 0):
        return context

    for cafile in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.isfile(cafile):
            context.load_verify_locations(cafile=cafile)
            if context.cert_store_stats().get("x509_ca", 0):
                break
    return context


def post_chat_completion(body, api_key, base_url, timeout, max_retries, backoff):
    """POST to the chat completions endpoint, retrying only transient failures."""
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(
                request, timeout=timeout, context=create_ssl_context()
            ) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_STATUSES or attempt == max_retries:
                raise JudgeError(f"OpenRouter request failed with HTTP {exc.code}")
            reason = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == max_retries:
                raise JudgeError(f"OpenRouter request failed: {exc}")
            reason = str(exc)

        delay = backoff * (2**attempt)
        print(f"Transient failure ({reason}), retrying in {delay:.1f}s", file=sys.stderr)
        time.sleep(delay)

    raise JudgeError("OpenRouter request failed after exhausting retries")


def build_prompt(kind, prompts_dir, source_path, artifact_path):
    spec = KINDS[kind]
    with open(os.path.join(prompts_dir, spec["prompt"])) as handle:
        instructions = handle.read()
    with open(source_path) as handle:
        source = handle.read()
    with open(artifact_path) as handle:
        artifact = handle.read()

    source_tag = spec["source_tag"]
    artifact_tag = spec["artifact_tag"]
    return (
        f"{instructions}\n\n"
        f"<{source_tag}>\n{source}\n</{source_tag}>\n\n"
        f"<{artifact_tag}>\n{artifact}\n</{artifact_tag.split()[0]}>"
    )


def judge(kind, prompts_dir, source_path, artifact_path, output_path):
    api_key = require_api_key()
    body = build_request_body(
        os.environ.get("EVAL_MODEL", "").strip() or DEFAULT_MODEL,
        env_float("EVAL_TEMPERATURE", DEFAULT_TEMPERATURE),
        build_prompt(kind, prompts_dir, source_path, artifact_path),
    )
    payload = post_chat_completion(
        body,
        api_key,
        os.environ.get("OPENROUTER_BASE_URL", "").strip() or DEFAULT_BASE_URL,
        env_float("EVAL_TIMEOUT", DEFAULT_TIMEOUT),
        env_int("EVAL_MAX_RETRIES", DEFAULT_MAX_RETRIES),
        env_float("EVAL_RETRY_BACKOFF", DEFAULT_RETRY_BACKOFF),
    )
    result = parse_result(extract_content(payload), KINDS[kind]["required"])

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-env", action="store_true", help="validate configuration and exit")
    parser.add_argument("--kind", choices=sorted(KINDS))
    parser.add_argument("--prompts-dir", help="directory containing the judge prompts")
    parser.add_argument("--source", help="original Solidity source file")
    parser.add_argument("--artifact", help="decompiled source or CFG to evaluate")
    parser.add_argument("--output", help="path to write the evaluation JSON to")
    args = parser.parse_args(argv)

    try:
        if args.check_env:
            require_api_key()
            return 0

        missing = [
            name
            for name in ("kind", "prompts_dir", "source", "artifact", "output")
            if not getattr(args, name)
        ]
        if missing:
            parser.error("missing required arguments: " + ", ".join(f"--{n}" for n in missing))

        judge(args.kind, args.prompts_dir, args.source, args.artifact, args.output)
    except JudgeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
