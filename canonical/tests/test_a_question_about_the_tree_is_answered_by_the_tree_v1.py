# PROJECT_BRAIN
"""An analysis question is answered by the tree, and its delivery is not a second task.

Three capability families that the census has scored zero on since revision 2 —
*which function is never executed*, *where is the hardcoded credential*, *which
function is quadratic* — are one query each over artifacts this repository already
builds.  Measured on the census fixtures, first run, from `814ae41`:

    python.source.dead_code.v1     -> audit_total      1.7 ms   (oracle: audit_total)
    python.source.secret_scan.v1   -> app/aws.py:1     0.2 ms   (oracle: app/aws.py)
    python.source.complexity.v1    -> has_dupes        0.5 ms   (oracle: has_dupes)

Nothing here is a new parser.  The dead-code answer is a set membership test
against `callers_of`, which `python.source.symbol_index` already emits; the
secret answer is the issuers' published credential shapes; the complexity answer
is loop-nesting depth over `ast`.

Two laws make the sentences reachable, and both are narrowings:

1. WITNESS.  "the tests in X" names the oracle, not the subject.  Both directories
   exist, so the binder refused `source_root` for `.../app` versus `.../tests` —
   correctly.  The destination was already decided by the sentence.

2. DELIVERY.  "Write its name to <path>" names where the previous answer goes.
   It has an anaphoric object, so it cannot name a new subject and cannot name a
   new capability.  Before this rule the delivery clause was handed to
   `python.software.request.semantic_behavior.compile.v1` as its own step, which
   failed, which reported
   `FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS` — for a question the machine had just
   answered correctly.

Both rules must not widen anything: a sentence naming two SUBJECTS still fails
closed, and "and write the report to R" is not consumed (the repair lane's own
gate reads that artifact).
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime.bound_capabilities import python_source_complexity as complexity  # noqa: E402
from canonical.runtime.bound_capabilities import python_source_dead_code as dead_code  # noqa: E402
from canonical.runtime.bound_capabilities import python_source_secret_scan as secret  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/pin_analysis_lane"

DEAD_APP = '''"""Logic."""


def line_total(item):
    return item["price_cents"] * item["qty"]


def cart_total(items):
    return sum(line_total(i) for i in items)


def audit_total(items):
    return sum(i["price_cents"] for i in items)
'''

DEAD_TEST = '''import unittest
from app.service import cart_total


class T(unittest.TestCase):
    def test_total(self):
        self.assertEqual(cart_total([{"price_cents": 100, "qty": 2}]), 200)
'''

SECRET_APP = '''DEBUG = True
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"


def client():
    return {"key": AWS_ACCESS_KEY_ID}
'''

NEST_APP = '''def has_dupes(items):
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                return True
    return False


def total_prices(items):
    out = 0
    for item in items:
        out += item
    return out
'''


class Base(unittest.TestCase):
    files = {}

    def setUp(self):
        shutil.rmtree(WORK, ignore_errors=True)
        for rel, text in self.files.items():
            path = WORK / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    def _run(self, module, args=None):
        return module.run(dict({"source_root": str(WORK / "app"),
                                "output_path": str(WORK / "answer.json")}, **(args or {})),
                          str(ROOT))


class TestTheTreeAnswersTheQuestion(Base):
    files = {"app/__init__.py": "", "app/service.py": DEAD_APP,
             "tests/__init__.py": "", "tests/test_service.py": DEAD_TEST}

    def test_a_function_nothing_executes_is_named(self):
        out = self._run(dead_code)
        self.assertEqual(out["answer"], "audit_total")
        self.assertEqual(out["dead_symbols"], ["audit_total"])
        self.assertTrue(out["output_verified"])

    def test_the_answer_is_the_artifact_the_sentence_asked_for(self):
        self._run(dead_code)
        report = json.loads((WORK / "answer.json").read_text(encoding="utf-8"))
        self.assertEqual(report["answer"], "audit_total")
        self.assertEqual(report["schema"], "PROJECT_BRAIN_PYTHON_DEAD_CODE_V1")

    def test_a_function_the_tests_execute_is_not_dead(self):
        # cart_total's only caller is in tests/, which is why the index scope is
        # the parent of the subject and not the subject itself.
        self.assertNotIn("cart_total", self._run(dead_code)["dead_symbols"])


class TestTheCredentialHasAShape(Base):
    files = {"app/__init__.py": "", "app/aws.py": SECRET_APP}

    def test_the_published_key_shape_is_found(self):
        out = self._run(secret)
        self.assertTrue(out["answer"].endswith("app/aws.py:2"), out["answer"])
        self.assertEqual(out["findings"][0]["signature"], "aws_access_key_id")

    def test_the_secret_is_never_written_into_the_report(self):
        self._run(secret)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", (WORK / "answer.json").read_text(encoding="utf-8"))

    def test_an_ordinary_string_is_not_a_credential(self):
        (WORK / "app/plain.py").write_text('REGION = "eu-west-1"\n', encoding="utf-8")
        report = json.loads((WORK / "answer.json").read_text(encoding="utf-8")) if False else None
        out = self._run(secret)
        self.assertEqual(out["finding_count"], 1)  # only the key, never the region


class TestTheClassComesFromTheNesting(Base):
    files = {"app/__init__.py": "", "app/service.py": NEST_APP}

    def test_the_nested_loop_is_quadratic(self):
        out = self._run(complexity)
        self.assertEqual(out["answer"], "has_dupes")
        self.assertEqual(out["worst_nesting"], 2)
        self.assertEqual(out["worst_class"], "O(n^2)")

    def test_a_single_loop_is_linear(self):
        rows = {r["name"]: r for r in self._run(complexity)["functions"]
                if isinstance(self._run(complexity).get("functions"), list)} \
            if False else None
        out = self._run(complexity)
        report = json.loads((WORK / "answer.json").read_text(encoding="utf-8"))
        rows = {r["name"]: r for r in report["functions"]}
        self.assertEqual(rows["total_prices"]["nesting"], 1)
        self.assertEqual(rows["total_prices"]["complexity_class"], "O(n)")


class TestTheSentenceSaysWhichDirectoryIsTheWitness(unittest.TestCase):
    def test_a_test_directory_is_the_witness_not_the_subject(self):
        goal = ("Which function in canonical/astra_runtime/tmp/x/app is never executed "
                "by the tests in canonical/astra_runtime/tmp/x/tests? Write its name to "
                "canonical/astra_runtime/tmp/x/answer.json")
        paths = list(gc._repo_paths(goal, ROOT))
        witness = gc._witness_directories(goal, paths)
        self.assertEqual(len(witness), 1)
        self.assertTrue(next(iter(witness)).endswith("/tests"))

    def test_a_sentence_naming_two_subjects_names_no_witness(self):
        goal = ("Compare canonical/runtime and canonical/tests and write the difference to "
                "canonical/astra_runtime/tmp/x/answer.json")
        paths = list(gc._repo_paths(goal, ROOT))
        self.assertEqual(gc._witness_directories(goal, paths), set())


class TestDeliveryIsNotASecondTask(unittest.TestCase):
    def test_the_anaphoric_delivery_clause_is_consumed(self):
        actions = [{"type": "invoke_capability",
                    "args": {"capability_id": "python.source.dead_code.v1",
                             "output_path": "canonical/astra_runtime/tmp/placeholder.json",
                             "source_root": "canonical/runtime"}}]
        parts = [{"inputs": {"output_path": "canonical/astra_runtime/tmp/placeholder.json"}}]
        clause = "Write its name to canonical/astra_runtime/tmp/x/answer.json"
        self.assertTrue(gc._compile_answer_delivery(clause, actions, parts, ROOT))
        self.assertEqual(actions[0]["args"]["output_path"],
                         "canonical/astra_runtime/tmp/x/answer.json")
        self.assertEqual(parts[0]["inputs"]["output_path"],
                         "canonical/astra_runtime/tmp/x/answer.json")

    def test_the_repair_report_clause_is_not_consumed(self):
        # "and write the repair report to R" is a promise the source-change gate
        # reads.  Consuming it here would unbind the artifact that gate inspects.
        actions = [{"type": "invoke_capability",
                    "args": {"capability_id": "x", "output_path": "a.json"}}]
        for clause in ("write the repair report to canonical/astra_runtime/tmp/x/r.json",
                       "save the report to canonical/astra_runtime/tmp/x/r.json",
                       "write the text 'hello' to canonical/astra_runtime/tmp/x/out.txt"):
            self.assertFalse(gc._compile_answer_delivery(clause, actions, [], ROOT), clause)

    def test_nothing_to_deliver_is_not_consumed(self):
        self.assertFalse(gc._compile_answer_delivery(
            "Write its name to canonical/astra_runtime/tmp/x/answer.json", [], [], ROOT))


if __name__ == "__main__":
    unittest.main()
