"""Empty-payload guards must come from observed values and pass the real test."""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import empty_payload_suppression_v1 as eps  # noqa: E402


class EmptyPayloadTests(unittest.TestCase):
    def test_tightens_is_not_none_for_an_observed_empty_name(self):
        source = "def render(value):\n    if value is not None:\n        return '[' + value + ']'\n    return ''\n"
        proposals = eps.tightenings(source, [{"name": "value"}])
        self.assertTrue(proposals)
        self.assertIn("if value:", proposals[0][0])

    def test_tightens_membership_for_an_observed_empty_mapping(self):
        source = "def render(extra):\n    if 'envvars' in extra:\n        return extra['envvars']\n    return ''\n"
        proposals = eps.tightenings(source, [{"name": "extra"}])
        self.assertTrue(proposals)
        self.assertIn("extra.get('envvars')", proposals[0][0])

    def test_verifies_a_real_empty_payload_fix(self):
        with tempfile.TemporaryDirectory() as where:
            root = pathlib.Path(where)
            (root / "mod.py").write_text(
                "def render(value):\n"
                "    parts = []\n"
                "    if value is not None:\n"
                "        parts.append('[v: ' + value + ']')\n"
                "    return ''.join(parts)\n",
                encoding="utf-8",
            )
            (root / "test_mod.py").write_text(
                "from mod import render\n\n"
                "def test_empty():\n    assert render('') == ''\n",
                encoding="utf-8",
            )
            from canonical.swe_kernel import value_producer_localization_v1 as unused  # noqa: F401
            import sys as _sys
            sys.path.insert(0, str(root))
            _sys.modules.pop("mod", None)
            payloads = eps.empty_payloads(root, "test_mod.py", "test_mod.py::test_empty", 20)
            self.assertTrue(any(item["name"] == "value" for item in payloads))
            source = (root / "mod.py").read_text(encoding="utf-8")
            proposals = eps.tightenings(source, payloads)
            accepted = None
            for candidate, _ in proposals:
                (root / "mod.py").write_text(candidate, encoding="utf-8")
                import subprocess
                done = subprocess.run([sys.executable, "-m", "pytest", "test_mod.py", "-q",
                                       "-p", "no:cacheprovider"],
                                      cwd=root, capture_output=True, text=True)
                (root / "mod.py").write_text(source, encoding="utf-8")
                if done.returncode == 0:
                    accepted = candidate
                    break
            self.assertIsNotNone(accepted)
            self.assertIn("if value:", accepted)


if __name__ == "__main__":
    unittest.main()
