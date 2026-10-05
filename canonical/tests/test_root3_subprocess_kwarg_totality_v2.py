from __future__ import annotations

import subprocess
import sys
import unittest

from canonical.runtime import root3_subprocess_mediator_v1 as m


class SubprocessKwargTotalityV2Tests(unittest.TestCase):
    def tearDown(self) -> None:
        try:
            m.uninstall()
        except Exception:
            subprocess.run = m._ORIGINAL_RUN
            subprocess.Popen = m._ORIGINAL_POPEN
            m._INSTALLED = False
            m._AUTHORIZER = None
            m._AUTHORITY_ID = None

    def test_executable_override_is_rejected(self):
        with self.assertRaisesRegex(
            m.ProcessEffectDenied,
            "SUBPROCESS_KWARG_NOT_YET_MEDIATED:executable",
        ):
            m._request(
                "subprocess.run",
                ([sys.executable, "-c", "pass"],),
                {"executable": sys.executable, "check": True},
            )

    def test_unclassified_future_kwarg_fails_closed(self):
        with self.assertRaisesRegex(
            m.ProcessEffectDenied,
            "SUBPROCESS_KWARG_UNCLASSIFIED:future_process_knob",
        ):
            m._request(
                "subprocess.run",
                ([sys.executable, "-c", "pass"],),
                {"future_process_knob": "surprise"},
            )

    def test_neutral_forbidden_kwarg_preserves_request_digest(self):
        command = ([sys.executable, "-c", "pass"],)
        base = m._request("subprocess.run", command, {"check": True})
        neutral = m._request(
            "subprocess.run",
            command,
            {"check": True, "executable": None},
        )
        self.assertEqual(neutral, base)

    def test_existing_check_true_call_remains_compatible(self):
        seen = []

        def allow(request):
            seen.append(dict(request))
            return {
                "allowed": True,
                "authorization_sha256": "a" * 64,
            }

        m.install(allow, authority_id="STDLIB_VERIFY")
        result = subprocess.run(
            [sys.executable, "-c", "print('ok')"],
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "ok")
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
