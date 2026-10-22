#!/usr/bin/env python3
"""The blocker-lease dedupe call must survive a transient gateway error.

`enforce_blocker_lease` turns any exception from the GitHub API into
BLOCKER_LEASE_DEDUPE_CHECK_FAILED, which fails the whole guard. Measured on PR
#5983 that produced a rejection caused by a 502 and then a 504 from
api.github.com, with the identical guard command passing either side of it. These
tests pin the retry without weakening the check: a client error must still fail at
once, and an API that never recovers must still fail the guard.
"""
from __future__ import annotations

import io
import os
import pathlib
import sys
import unittest
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import enforce_goal_hierarchy as guard  # noqa: E402


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _http_error(code):
    return urllib.error.HTTPError(
        "https://api.github.com/x", code, "err", {}, io.BytesIO(b"")  # type: ignore[arg-type]
    )


class RetryTests(unittest.TestCase):
    # The retry takes its opener and sleep by injection, so no network entry point
    # is ever reassigned -- repo_integrity_guard_v1 forbids that in test code.
    def _run(self, build, opener):
        return guard._urlopen_with_retry(build, 5, opener=opener, sleep=lambda *_: None)

    def test_a_transient_gateway_error_is_retried_and_recovers(self):
        calls = {"n": 0}

        def fake(req, timeout=None):
            calls["n"] += 1
            if calls["n"] < 3:
                raise _http_error(502)
            return _Resp(b'{"ok": true}')

        with self._run(lambda: object(), fake) as resp:
            self.assertEqual(resp.read(), b'{"ok": true}')
        self.assertEqual(calls["n"], 3)

    def test_a_client_error_is_not_retried(self):
        """A 404 is a real answer, not a gateway hiccup; retrying it would hide it."""
        calls = {"n": 0}

        def fake(req, timeout=None):
            calls["n"] += 1
            raise _http_error(404)

        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._run(lambda: object(), fake)
        self.assertEqual(ctx.exception.code, 404)
        self.assertEqual(calls["n"], 1, "a 4xx must fail on the first attempt")

    def test_a_persistently_unreachable_api_still_fails_closed(self):
        """The retry must not turn 'cannot check' into 'check passed'."""
        calls = {"n": 0}

        def fake(req, timeout=None):
            calls["n"] += 1
            raise _http_error(504)

        with self.assertRaises(urllib.error.HTTPError):
            self._run(lambda: object(), fake)
        self.assertEqual(calls["n"], guard._DEDUPE_ATTEMPTS)

    def test_a_transport_timeout_is_retried(self):
        calls = {"n": 0}

        def fake(req, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.URLError("timed out")
            return _Resp(b"{}")

        with self._run(lambda: object(), fake) as resp:
            self.assertEqual(resp.read(), b"{}")
        self.assertEqual(calls["n"], 2)

    def test_the_request_is_rebuilt_for_every_attempt(self):
        """A Request already sent is not guaranteed reusable, so it must be rebuilt."""
        built = []
        calls = {"n": 0}

        def fake(req, timeout=None):
            calls["n"] += 1
            if calls["n"] < 2:
                raise _http_error(503)
            return _Resp(b"{}")

        def build():
            token = object()
            built.append(token)
            return token

        with self._run(build, fake):
            pass
        self.assertEqual(len(built), 2)
        self.assertIsNot(built[0], built[1])

    def test_both_dedupe_callers_route_through_the_retry(self):
        """The fix is worthless if either caller still calls urlopen directly."""
        import inspect

        for name in ("_github_json", "_github_graphql"):
            src = inspect.getsource(getattr(guard, name))
            self.assertIn("_urlopen_with_retry", src, f"{name} bypasses the retry")
            self.assertNotIn("urllib.request.urlopen(", src, f"{name} still calls urlopen directly")


if __name__ == "__main__":
    unittest.main()


class FailureAnnotationTests(unittest.TestCase):
    """A guard failure must be readable without the workflow logs."""

    def test_reasons_are_emitted_as_annotations_under_actions(self):
        import io
        import contextlib

        buf = io.StringIO()
        real = os.environ.get("GITHUB_ACTIONS")
        os.environ["GITHUB_ACTIONS"] = "true"
        try:
            with contextlib.redirect_stdout(buf):
                guard._annotate_failures(["BLOCKER_LEASE_DEDUPE_CHECK_FAILED:HTTP Error 504"])
        finally:
            if real is None:
                os.environ.pop("GITHUB_ACTIONS", None)
            else:
                os.environ["GITHUB_ACTIONS"] = real
        self.assertIn("::error::BLOCKER_LEASE_DEDUPE_CHECK_FAILED:HTTP Error 504", buf.getvalue())

    def test_local_runs_keep_their_existing_output(self):
        """Emitting annotations outside Actions would pollute every local invocation."""
        import io
        import contextlib

        buf = io.StringIO()
        real = os.environ.pop("GITHUB_ACTIONS", None)
        try:
            with contextlib.redirect_stdout(buf):
                guard._annotate_failures(["SOME_REASON"])
        finally:
            if real is not None:
                os.environ["GITHUB_ACTIONS"] = real
        self.assertEqual(buf.getvalue(), "")

    def test_annotation_special_characters_are_escaped(self):
        """An unescaped newline would truncate the annotation and hide the rest."""
        import io
        import contextlib

        buf = io.StringIO()
        real = os.environ.get("GITHUB_ACTIONS")
        os.environ["GITHUB_ACTIONS"] = "true"
        try:
            with contextlib.redirect_stdout(buf):
                guard._annotate_failures(["A:B\nsecond line"])
        finally:
            if real is None:
                os.environ.pop("GITHUB_ACTIONS", None)
            else:
                os.environ["GITHUB_ACTIONS"] = real
        out = buf.getvalue()
        self.assertEqual(out.count("\n"), 1, "the payload must stay on one line")
        self.assertIn("%0A", out)


class CrashReportingTests(unittest.TestCase):
    """A crash must be as readable as a policy rejection, and must still exit non-zero."""

    def test_the_entry_point_reports_and_reraises_a_crash(self):
        import contextlib
        import io
        import runpy

        src = (ROOT / "canonical/runtime/enforce_goal_hierarchy.py").read_text(encoding="utf-8")
        # The handler must exist and must not swallow the exception.
        self.assertIn("DRIFT_GUARD_CRASH:", src)
        tail = src[src.index('if __name__=="__main__":'):]
        self.assertIn("raise", tail.split("DRIFT_GUARD_CRASH:")[1],
                      "a crash handler that swallows the exception would hide a real failure")

    def test_annotate_handles_an_empty_reason_list(self):
        import contextlib
        import io

        buf = io.StringIO()
        real = os.environ.get("GITHUB_ACTIONS")
        os.environ["GITHUB_ACTIONS"] = "true"
        try:
            with contextlib.redirect_stdout(buf):
                guard._annotate_failures([])
        finally:
            if real is None:
                os.environ.pop("GITHUB_ACTIONS", None)
            else:
                os.environ["GITHUB_ACTIONS"] = real
        self.assertEqual(buf.getvalue(), "")
