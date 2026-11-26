"""Producer localization must find the frame that actually held the observed value."""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import value_producer_localization_v1 as vpl  # noqa: E402


class ProducerTests(unittest.TestCase):
    def test_locates_a_real_return_value(self):
        with tempfile.TemporaryDirectory() as where:
            root = pathlib.Path(where)
            (root / "mod.py").write_text(
                "def produce():\n    value = 'bad-output'\n    return value\n",
                encoding="utf-8",
            )
            (root / "test_mod.py").write_text(
                "from mod import produce\n\ndef test_case():\n    assert produce() == 'good-output'\n",
                encoding="utf-8",
            )
            result = vpl.locate(root, "test_mod.py", "test_mod.py::test_case",
                                "bad-output", 20)
            self.assertEqual(result["outcome"], "LOCATED")
            names = {(item["function"], item["line"]) for item in result["producers"]}
            self.assertIn(("produce", 3), names)


if __name__ == "__main__":
    unittest.main()
