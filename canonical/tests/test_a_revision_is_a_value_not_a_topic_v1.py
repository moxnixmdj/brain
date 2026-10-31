"""A git revision is a value, not a topic.

Measured 2026-10-31 on the advanced census, request 44.  Two sentences that differ only by a
revision phrase took different routes:

    "Show the diff of <f>."                 matched [diff, show] -> git.repository.operate.v1  PASS
    "Show the diff of <f> against HEAD~1."  matched [head]       -> git.history.bisect_regression.v1
                                                                    FAIL__LIVE_CONTROLLER_EXECUTION

The revision is the ARGUMENT of the diff.  `git.history.bisect_regression.v1` carries "head" as a
keyword, so the second sentence's only distinctive token named a capability nobody asked for -- the
same failure class as the word "python" scoring a fleet row on an audit request, which the
repository already fixed the same way, in `goal_compiler.GENERIC_MATCH_TOKENS`.

These tests pin both directions, because a rule that only removes matches would also silence a
genuine history request:

  * a revision phrase is not evidence for the history row  (score 0);
  * a request that says what changed is still evidence      (score > 0);
  * the wrong row is never executed for the diff request;
  * falsification: removing the exclusion restores the wrong match.

The oracle is the compiler's own scorer and the door's own route, not a transcription of intent.
"""
from __future__ import annotations

import sys
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

BISECT = "git.history.bisect_regression.v1"
DIFF = "git.repository.operate.v1"
FILE = "canonical/astra_runtime/tmp/swe_advanced_probe/44_git/pkg/calc.py"
DIFF_WITH_REVISION = "Show the diff of %s against HEAD~1." % FILE
HISTORY_REQUEST = "Find the commit that broke the test in %s." % FILE


class ARevisionIsAnArgumentNotATopic(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_verified_registry()

    def test_a_revision_phrase_earns_no_capability(self) -> None:
        score, _specificity, evidence = gc._score(DIFF_WITH_REVISION, BISECT,
                                                  self.registry[BISECT])
        self.assertEqual(score, 0, evidence.get("matched_keywords"))
        self.assertFalse([t for t in (evidence.get("matched_identity") or []) if t == "head"])

    def test_a_request_that_states_the_effect_still_earns_it(self) -> None:
        """The rule must not silence a genuine history request."""
        score, _specificity, evidence = gc._score(HISTORY_REQUEST, BISECT,
                                                 self.registry[BISECT])
        self.assertGreater(score, 0, evidence)

    def test_the_diff_row_still_earns_the_plain_diff_request(self) -> None:
        score, _specificity, _evidence = gc._score("Show the diff of %s." % FILE, DIFF,
                                                   self.registry[DIFF])
        self.assertGreater(score, 0)

    def test_the_wrong_row_is_never_selected_for_the_revision_request(self) -> None:
        """Whatever the route becomes, it may not be a row that would bisect."""
        from canonical.runtime import live_brain_route_admission_v1 as door
        result = door.solve({"task_id": "REVISION_IS_A_VALUE", "goal": DIFF_WITH_REVISION}) or {}
        self.assertNotEqual(result.get("compiled_capability_id"), BISECT,
                            "a diff against a revision is not a bisect")

    def test_the_exclusion_can_fail(self) -> None:
        """Falsification: drop the rule and the revision becomes the only evidence again."""
        self.assertIn("head", gc.GENERIC_MATCH_TOKENS)
        try:
            gc.GENERIC_MATCH_TOKENS.discard("head")
            gc._S = None if hasattr(gc, "_S") else None  # no cache to clear; scorer is pure
            score, _s, _e = gc._score(DIFF_WITH_REVISION, BISECT, self.registry[BISECT])
            self.assertGreater(score, 0, "without the rule the revision must match again")
        finally:
            gc.GENERIC_MATCH_TOKENS.add("head")


if __name__ == "__main__":
    unittest.main()
