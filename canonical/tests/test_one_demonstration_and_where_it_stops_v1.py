"""One demonstration, measured: what it buys, where it stops, and what "crystallized" hides.

These tests pin the numbers in `THE_YES_WAS_NOT_MEASURED_20261112_V1.md`. They are not a claim that
anything works; three of the five assert that a limit is still there, so that a future round cannot
quietly declare it fixed without this file going red.

The distinctions that matter, all of which this repository has got wrong before:

* `crystallized: True` is a **return value**, not an event. Teaching a rule the bundle already ships
  reinforces it and leaves the row count unchanged. Counting that as learning is how the go arm of
  the probe was first mis-read.
* A rule generalises over **surface** (the identifier hole is real) and not over **meaning** (the same
  off-by-one in another shape is refused), and it carries no guard against firing where the original
  operator was required. Only the caller's verifier stands between the two.
* `recall_and_apply_verified` requires that verifier as a keyword-only argument. That is deliberate.
  Its absence, not the learner, is the limiting factor.

Zero model calls, no network, temp directories only. Authority: NONE.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

BEFORE = "def below_limit(n):\n    return n <= 10\n"
AFTER = "def below_limit(n):\n    return n < 10\n"


@pytest.fixture()
def rule():
    out = cry.anti_unify_code_rule(BEFORE, AFTER, language="python", error_class="py_repair")
    assert out, "a one-line repair must anti-unify into a rule"
    return out


def _store(tmp_path: pathlib.Path) -> "cry.VerifiedSkillStore":
    return cry.VerifiedSkillStore(tmp_path / "skills.sqlite")


# ---------------------------------------------------------------- what one demonstration buys


def test_one_demonstration_becomes_a_rule_and_survives_its_mutated_twin(rule):
    """The part that is real: a single before/after pair yields a hole-bearing rule."""
    pattern = [t[1] for t in rule["pattern_tokens"]]
    replacement = [t[1] for t in rule["replacement_tokens"]]
    assert "?id0" in pattern and "?num0" in pattern, pattern
    assert "?id0" in replacement and "?num0" in replacement, replacement
    assert cry.verify_rule_on_mutated_twin(BEFORE, rule) is True


def test_the_rule_generalises_over_the_identifier_it_saw(rule):
    """`n` becomes `total`. This is transfer over surface, and it is genuine."""
    rewritten = cry.apply_crystallized_code_rule(
        "def cap(total):\n    return total <= 3\n", rule
    )
    assert rewritten is not None
    assert rewritten.rstrip().endswith("return total < 3")


def test_the_rule_refuses_what_it_cannot_see_including_the_same_meaning(rule):
    """The same off-by-one, spelled as a range, is invisible to a token matcher."""
    assert cry.apply_crystallized_code_rule(
        "fn below_limit(n: usize) -> bool {\n    n <= 10\n}\n", rule
    ) is None
    assert cry.apply_crystallized_code_rule(
        "def walk(n):\n    for i in range(n + 1):\n        yield i\n", rule
    ) is None


# ---------------------------------------------------------------- what it does not buy


def test_the_rule_has_no_guard_and_will_rewrite_a_required_operator(rule):
    """KNOWN LIMIT, pinned on purpose.

    `x <= 60` may be a deliberate edge-inclusive bound. The rule fires anyway. The only thing that
    can stop it is the verifier the caller passes to `recall_and_apply_verified`. If a future round
    adds a semantic guard, this test should be flipped deliberately -- with the guard named.
    """
    rewritten = cry.apply_crystallized_code_rule(
        "def allows_edge(x):\n    return x <= 60\n", rule
    )
    assert rewritten is not None
    assert rewritten.rstrip().endswith("return x < 60")


def test_recall_demands_an_oracle_as_a_keyword_only_argument(rule, tmp_path):
    """Fail-closed by design: there is no no-oracle recall path to abuse."""
    store = _store(tmp_path)
    store.crystallize_verified_fix("python", "py_repair", BEFORE, AFTER, "ONE_DEMONSTRATION")
    with pytest.raises(TypeError):
        store.recall_and_apply_verified(  # type: ignore[call-arg]
            source_text="def other(n):\n    return n <= 999\n",
            language="python",
            error_class="py_repair",
        )


def test_a_vacuous_oracle_lets_a_wrong_lesson_through(tmp_path):
    """The limiting factor, stated as a test: correctness is the caller's oracle, not the store."""
    store = _store(tmp_path)
    wrong_before = "def scale(xs, k):\n    return [x * k for x in xs]\n"
    wrong_after = "def scale(xs, k):\n    return [x + k for x in xs]\n"
    rec = store.crystallize_verified_fix("python", "compile_only", wrong_before, wrong_after,
                                         "COMPILE_ONLY")
    assert rec is not None
    hit = store.recall_and_apply_verified(
        source_text="def scale2(xs, k):\n    return [x * k for x in xs]\n",
        language="python", error_class="compile_only",
        verifier=lambda c: compile(c, "<c>", "exec") is not None,
    )
    assert hit is not None, "with 'it compiles' as the only oracle, the wrong lesson is replayed"
    assert "[x + k for x in xs]" in hit["patched_source"]


# ---------------------------------------------------------------- what "crystallized" hides


def test_teaching_a_shipped_rule_again_reinforces_and_does_not_inflate_the_count(tmp_path):
    """`crystallized: True` twice, one row. A return value is not an event."""
    store = _store(tmp_path)
    go_before = (
        "package main\nfunc main() {\n\tvar m map[string]int\n\tm[\"a\"] = 1\n}\n"
    )
    go_after = (
        "package main\nfunc main() {\n\tm := make(map[string]int)\n\tm[\"a\"] = 1\n}\n"
    )
    first = store.crystallize_verified_fix("go", "go_repair", go_before, go_after, "SHOWN_ONCE")
    second = store.crystallize_verified_fix("go", "go_repair", go_before, go_after, "SHOWN_TWICE")
    assert first is not None and second is not None
    assert first["skill_id"] == second["skill_id"]
    shipped_ids = {r["skill_id"] for r in store.provenance()}
    assert first["skill_id"] in shipped_ids
    assert len(store.lookup_rules("go")) == 1, "no duplicate row for one rule"


def test_a_lesson_learned_here_is_there_in_a_fresh_interpreter(tmp_path):
    """Permanence across process death, measured rather than asserted."""
    db = tmp_path / "survive.sqlite"
    store = cry.VerifiedSkillStore(db)
    store.crystallize_verified_fix("python", "py_repair", BEFORE, AFTER, "ONE_DEMONSTRATION")
    learned = store.count()

    child = subprocess.run(
        [sys.executable, "-c",
         "import pathlib,sys;"
         f"sys.path.insert(0, {str(ROOT)!r});"
         "from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry;"
         f"print(cry.VerifiedSkillStore(pathlib.Path({str(db)!r})).count())"],
        capture_output=True, text=True, timeout=120,
    )
    assert child.returncode == 0, child.stderr[-500:]
    assert int(child.stdout.strip().splitlines()[-1]) == learned


# ---------------------------------------------------------------- the document that lied


def test_the_retracted_note_cannot_return_without_its_receipts():
    """The bundle was never empty, and the front door never learned. Both were checkable."""
    note = ROOT / "YOU_WERE_RIGHT_ALL_ALONG.md"
    if note.is_file():
        text = note.read_text(encoding="utf-8")
        assert "RETRACTED IN FULL" in text, (
            "the retracted 'you were right' note must carry its retraction banner"
        )
    bundle = ROOT / "canonical/astra_runtime/skills/VERIFIED_SKILLS_BUNDLE_V1.json"
    import json

    shipped = json.loads(bundle.read_text(encoding="utf-8"))
    assert shipped.get("rule_count") == len(shipped.get("rules", [])) > 0, (
        "the skills bundle ships rules; any document claiming it is EMPTY is false"
    )
