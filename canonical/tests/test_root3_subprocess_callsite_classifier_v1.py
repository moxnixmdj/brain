from __future__ import annotations

import unittest

from canonical.runtime.root3_subprocess_callsite_classifier_v1 import (
    RuntimeCallsiteClassificationError,
    classify_frame_chain,
    detect_effect_class,
)
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import EXPECTED


class RuntimeCallsiteClassifierTests(unittest.TestCase):
    def test_registry_is_exact_current_18_site_universe(self):
        self.assertEqual(len(EXPECTED), 18)
        self.assertEqual(sum(1 for k in EXPECTED if k[2].endswith("run")), 17)
        self.assertEqual(sum(1 for k in EXPECTED if k[2].endswith("Popen")), 1)

    def test_direct_unregistered_test_call_fails_closed(self):
        with self.assertRaises(RuntimeCallsiteClassificationError):
            detect_effect_class("subprocess.run")

    def test_unsupported_api_fails_closed(self):
        with self.assertRaisesRegex(
            RuntimeCallsiteClassificationError,
            "PROCESS_API_UNSUPPORTED",
        ):
            classify_frame_chain("os.system", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
