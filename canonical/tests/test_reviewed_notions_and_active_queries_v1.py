"""Executable checks for tentative notions, active queries, and evidence provenance.

The fixture oracles in this file are external specifications. They do not come
from the program being repaired. Passing these bounded tests is not evidence of
sentience or a general proof of program correctness.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import pathlib

import pytest

from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.runtime import creature_runtime_v1 as creature
from canonical.runtime.memory_policy_v1 import OFF, READ_ONLY, memory_policy_scope
from canonical.swe_kernel.autonomous_awake_loop_v1 import (
    AwakeAgencyDaemon,
    _fair_candidates,
    _screen_observations,
)
from canonical.swe_kernel.expression_hypotheses_v1 import function_models, investigate, only_target_expression_changed
from canonical.swe_kernel.interpretive_repair_v1 import InterpretiveRepair, parse_evidence
from canonical.swe_kernel.notions_v1 import Notion, NotionStore, live_notions, notions_for_source


GEOM = """def rect_area(w, h):
    return w + h

def rect_perimeter(w, h):
    return 2 * (w + h)

def square_area(s):
    return s * s
"""

DECOY = """def area_of_circle(r):
    return 3 * r * r

def area_of_rect(w, h):
    return w * h
"""

HIDDEN_NAMES = """def plain(s):
    return s * s

def wide(w, h):
    return w + h
"""

ADDITION_BUG = """def one_measure(x):
    return x + x

def two_measure(a, b):
    return a - b
"""

DIFFERENCE_BUG = """def one_delta(x):
    return x - x

def two_delta(a, b):
    return a + b
"""

WIDE_BUG = """def cube_volume(s):
    return s * s * s

def box_volume(l, w, h):
    return l + w + h

def box_surface(l, w, h):
    return 2 * (l * w + l * h + w * h)
"""

NARROW_BUG = """def cube_volume(s):
    return 6 * s

def box_volume(l, w, h):
    return l * w * h

def box_surface(l, w, h):
    return 2 * (l * w + l * h + w * h)
"""


def make_daemon(tmp_path: pathlib.Path, source: str):
    workspace = tmp_path / "workspace"
    (workspace / "pkg").mkdir(parents=True)
    (workspace / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    module = workspace / "pkg" / "example.py"
    module.write_text(source, encoding="utf-8")
    root = tmp_path / "creature"
    sense = root / "awake_sense"
    sense.mkdir(parents=True)
    daemon = AwakeAgencyDaemon(workspace, ledger_path=sense / "ledger.json",
                               skill_store_path=sense / "skills.sqlite")
    return daemon, workspace, module, root


def finding_for(daemon, a: str, b: str):
    return next(f for f in daemon.investigate_workspace() if {f["left"], f["right"]} == {a, b})


def test_names_are_not_a_semantic_oracle_and_no_unreviewed_test_is_written(tmp_path):
    daemon, workspace, module, _ = make_daemon(tmp_path / "hidden", HIDDEN_NAMES)
    assert daemon._sense_failing_workspace_tests() == []
    assert module.read_text() == HIDDEN_NAMES
    assert not list(workspace.rglob("test_*.py"))
    finding = finding_for(daemon, "plain", "wide")
    assert finding["fired"] and finding["status"] == "needs_review"
    assert finding["authority"] == "hypothesis"

    other, other_ws, other_module, _ = make_daemon(tmp_path / "decoy", DECOY)
    assert other._sense_failing_workspace_tests() == []
    decoy = finding_for(other, "area_of_circle", "area_of_rect")
    assert decoy["fired"] and decoy["status"] == "needs_review"
    assert other_module.read_text() == DECOY
    assert not list(other_ws.rglob("test_*.py"))


def test_identical_source_with_incompatible_specs_cannot_be_disambiguated_without_feedback(tmp_path):
    daemon, workspace, module, _ = make_daemon(tmp_path, HIDDEN_NAMES)
    # The exact same bytes can mean "wide is a sum" or "wide is a product".
    # No source-only observation can choose between these contracts.
    before = finding_for(daemon, "plain", "wide")
    assert 2 + 3 != 2 * 3
    after = finding_for(daemon, "plain", "wide")
    assert before == after
    assert daemon._sense_failing_workspace_tests() == []
    assert module.read_text() == HIDDEN_NAMES
    assert not list(workspace.rglob("test_*.py"))


def test_declined_is_not_held_or_fired():
    def crash():
        raise RuntimeError("no observation")

    result = Notion("X", "subject", "claim", crash).evaluate()
    assert result["declined"] is True and result["fired"] is False
    source = "def narrow(x):\n    return 1 / (x - x)\n\ndef wider(x, y):\n    return x + y\n"
    result = notions_for_source(source, "m")[0].evaluate()
    assert result["declined"] is True and result["fired"] is False


def test_source_is_not_executed_while_sensing(tmp_path):
    marker = tmp_path / "host_marker"
    source = (f"open({str(marker)!r}, 'w').write('side effect')\n"
              "def narrow(x):\n    return x * x\n"
              "def wider(x, y):\n    return x + y\n")
    assert notions_for_source(source, "untrusted") == []
    assert not marker.exists()
    assert function_models("def f(x):\n    while True: pass\n") == {}


def test_static_model_declines_definition_time_execution_even_on_unrelated_functions():
    malicious_definitions = [
        "@__import__('atexit').register\ndef unrelated():\n    pass\n",
        "def unrelated(x=__import__('os').getpid()):\n    pass\n",
        "def unrelated(x: __import__('os').getpid()):\n    pass\n",
    ]
    for suffix in malicious_definitions:
        assert function_models(GEOM + "\n" + suffix) == {}
        assert notions_for_source(GEOM + "\n" + suffix, "example") == []


def test_reference_is_not_inferred_and_review_can_reject(tmp_path):
    daemon, workspace, _, _ = make_daemon(tmp_path, GEOM)
    finding = finding_for(daemon, "square_area", "rect_area")
    store = NotionStore(daemon.notions_path)
    store.review(finding["id"], decision="confirm", reviewer="fixture", basis="explicit contract")
    assert finding_for(daemon, "square_area", "rect_area")["status"] == "needs_reference"
    assert daemon._sense_failing_workspace_tests() == []
    assert not list(workspace.rglob("test_*.py"))
    store.review(finding["id"], decision="reject", reviewer="fixture", basis="corrected review")
    assert finding_for(daemon, "square_area", "rect_area")["status"] == "rejected_by_reviewer"
    with pytest.raises(ValueError):
        store.review(finding["id"], decision="confirm", reviewer="fixture", basis="x", trusted_function="other")


def test_queries_reduce_ambiguity_and_require_external_validation(tmp_path):
    daemon, workspace, _, _ = make_daemon(tmp_path, GEOM)
    finding = finding_for(daemon, "square_area", "rect_area")
    store = NotionStore(daemon.notions_path)
    store.review(finding["id"], decision="confirm", reviewer="fixture", basis="the relation is required",
                 trusted_function="square_area")
    plan = finding_for(daemon, "square_area", "rect_area")["plan"]
    assert plan["status"] == "needs_example" and plan["candidates"] == 4
    query = plan["next_query"]
    assert query["reason"] == "models_disagree" and query["args"] == [2, 3]
    assert set(query["predictions"]) == {4, 6, 9}
    # The example is independently supplied, not obtained from the broken function.
    with pytest.raises(ValueError):
        store.answer(finding["id"], args=[3, 2], expected=6, reviewer="fixture", basis="outside oracle")
    store.answer(finding["id"], args=[2, 3], expected=6, reviewer="fixture", basis="outside oracle")
    plan = finding_for(daemon, "square_area", "rect_area")["plan"]
    assert plan["candidates"] == 2 and plan["next_query"]["reason"] == "independent_validation"
    assert daemon._sense_failing_workspace_tests() == []
    assert not list(workspace.rglob("test_*.py"))
    args = plan["next_query"]["args"]
    store.answer(finding["id"], args=args, expected=args[0] * args[1], reviewer="fixture", basis="outside oracle")
    plan = finding_for(daemon, "square_area", "rect_area")["plan"]
    assert plan["status"] == "bounded_agreement" and plan["external_examples"] == 2
    assert plan["next_query"] is None


def test_ambiguous_module_stem_refuses_authorship_even_after_review(tmp_path):
    daemon, workspace, _, _ = make_daemon(tmp_path, GEOM)
    other = workspace / "other"
    other.mkdir()
    (other / "example.py").write_text("def unrelated():\n    return 42\n")
    finding = finding_for(daemon, "square_area", "rect_area")
    store = NotionStore(daemon.notions_path)
    store.review(finding["id"], decision="confirm", reviewer="fixture", basis="contract",
                 trusted_function="square_area")
    for _ in range(2):
        plan = finding_for(daemon, "square_area", "rect_area")["plan"]
        args = plan["next_query"]["args"]
        store.answer(finding["id"], args=args, expected=args[0] * args[1],
                     reviewer="fixture", basis="external examples")
    assert daemon._sense_failing_workspace_tests() == []
    assert not list(workspace.rglob("test_*.py"))
    assert any(f["id"] == finding["id"] and f["status"] == "ambiguous_module_stem"
               for f in daemon.notion_findings)


def test_contradictory_external_example_does_not_create_a_test(tmp_path):
    daemon, workspace, _, _ = make_daemon(tmp_path, GEOM)
    finding = finding_for(daemon, "square_area", "rect_area")
    store = NotionStore(daemon.notions_path)
    store.review(finding["id"], decision="confirm", reviewer="fixture", basis="contract", trusted_function="square_area")
    plan = finding_for(daemon, "square_area", "rect_area")["plan"]
    store.answer(finding["id"], args=plan["next_query"]["args"], expected=999,
                 reviewer="fixture", basis="different external contract")
    assert finding_for(daemon, "square_area", "rect_area")["status"] == "no_candidates"
    assert daemon._sense_failing_workspace_tests() == []
    assert not list(workspace.rglob("test_*.py"))


def test_source_changes_invalidate_review_and_repeated_sensing_is_not_new_feedback(tmp_path):
    daemon, _, module, _ = make_daemon(tmp_path, GEOM)
    first = finding_for(daemon, "square_area", "rect_area")
    store = NotionStore(daemon.notions_path)
    store.review(first["id"], decision="confirm", reviewer="fixture", basis="contract", trusted_function="square_area")
    for _ in range(4):
        finding_for(daemon, "square_area", "rect_area")
    persisted = NotionStore(daemon.notions_path)
    assert len(persisted.reviews) == 1
    assert len(persisted.findings) == 2
    assert all(row["evaluated"] == 1 for row in persisted.seen.values())
    module.write_text(GEOM + "\n# changed after review\n", encoding="utf-8")
    second = finding_for(daemon, "square_area", "rect_area")
    assert second["id"] != first["id"]
    assert second["status"] == "needs_review"


def test_review_priority_learns_from_feedback_without_granting_authority(tmp_path):
    store = NotionStore(tmp_path / "notions.json")

    def examples(token, negative, small, large, module):
        src = (f"def {small}_{token}(x):\n    return x * x\n\n"
               f"def {large}_{token}(a, b):\n    return a + b\n\n"
               f"def {large}_{negative}(a, b):\n    return 2 * (a + b)\n")
        return [result for n in notions_for_source(src, module) if (result := n.evaluate())["fired"]]

    training = examples("cost", "delay", "tiny", "long", "train1") + examples("mass", "density", "narrow", "broad", "train2")
    heldout = examples("cost", "delay", "flat", "box", "held1") + examples("mass", "density", "compact", "large", "held2")
    assert len(training) == len(heldout) == 4
    assert all(store.score(f) == 0 for f in heldout)
    store.record(training)
    for finding in training:
        correct_relation = finding["right"].endswith(("_cost", "_mass"))
        store.review(finding["id"], decision="confirm" if correct_relation else "reject",
                     reviewer="fixture", basis="external labels")
    reloaded = NotionStore(tmp_path / "notions.json")
    for pair in (heldout[:2], heldout[2:]):
        positive = next(f for f in pair if f["right"].endswith(("_cost", "_mass")))
        negative = next(f for f in pair if f is not positive)
        assert reloaded.score(positive) == 0.095238
        assert reloaded.score(negative) == -0.055556
    # A learned priority never confirms a new question or grants permission.
    assert all(f["id"] not in reloaded.reviews for f in heldout)
    # Even an object loaded before entering OFF must not consult its old labels.
    with memory_policy_scope(OFF):
        assert reloaded.score(positive) == 0.0


def test_duplicate_or_contradictory_reviews_are_not_extra_labels(tmp_path):
    store = NotionStore(tmp_path / "memory.json")
    first = notions_for_source(HIDDEN_NAMES, "one.py")[0].evaluate()
    duplicate = notions_for_source(HIDDEN_NAMES, "two.py")[0].evaluate()
    novel = notions_for_source(HIDDEN_NAMES.replace("plain", "small").replace("wide", "large"), "three.py")[0].evaluate()
    store.record([first, duplicate])
    store.review(first["id"], decision="confirm", reviewer="one", basis="first contract")
    assert store.score(novel) > 0
    store.review(duplicate["id"], decision="reject", reviewer="two", basis="incompatible contract")
    assert store.score(novel) == 0  # contested identical evidence is not an unopposed label


def test_feedback_cli_records_explicit_caller_input(tmp_path, capsys):
    from canonical.swe_kernel.notion_feedback_cli_v1 import main

    store = NotionStore(tmp_path / "memory.json")
    finding = notions_for_source(HIDDEN_NAMES, "m")[0].evaluate()
    store.record([finding])
    assert main(["--store", str(store.path), "review", finding["id"], "--decision", "confirm",
                 "--reviewer", "fixture", "--basis", "outside contract", "--trusted-function", "plain"]) == 0
    assert json.loads(capsys.readouterr().out)["trusted_function"] == "plain"
    assert main(["--store", str(store.path), "list"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["review"]["decision"] == "confirm"


def test_feedback_persistence_failure_is_reported_not_silently_accepted(tmp_path):
    blocked = tmp_path / "directory_not_file"
    blocked.mkdir()
    store = NotionStore(blocked)
    finding = notions_for_source(HIDDEN_NAMES, "m")[0].evaluate()
    with pytest.raises(OSError):
        store.record([finding])
    assert blocked.is_dir()


def test_memory_policy_blocks_feedback_and_off_does_not_read(tmp_path):
    store = NotionStore(tmp_path / "memory.json")
    finding = notions_for_source(HIDDEN_NAMES, "m")[0].evaluate()
    store.record([finding])
    before = store.path.read_bytes()
    with memory_policy_scope(READ_ONLY):
        readonly = NotionStore(store.path)
        assert finding["id"] in readonly.findings
        with pytest.raises(PermissionError):
            readonly.review(finding["id"], decision="confirm", reviewer="x", basis="y")
        readonly.record([finding])
    assert store.path.read_bytes() == before
    with memory_policy_scope(OFF):
        assert NotionStore(store.path).findings == {}
        assert live_notions(store.path).findings == {}


def test_pairwise_failure_preserves_ambiguity_in_pytest_and_zygote_reports():
    reports = [
        "E assert 9 == 18\nE + where 9 = cube(3)\nE + and 18 = box(3, 3, 3)\n",
        'SEEN [{"at":"box(3, 3, 3) == cube(3)","seen":["18","9"]}]',
    ]
    for report in reports:
        rows = parse_evidence(report)
        assert len(rows) == 2 and {r["subject"] for r in rows} == {"cube", "box"}
        assert all(r["expected_source"] == "peer_observation" for r in rows)
        assert InterpretiveRepair().interpret(report) == []
    report = "E assert 6 == 9\nE + where 6 = area(3, 3)"
    row = parse_evidence(report)[0]
    assert row["subject"] == "area" and row["expected"] == 9 and row["expected_source"] == "assertion"


def test_screen_never_learns_from_placeholders_timeouts_or_unreported_candidates():
    screen = {"ok": True, "confined": True, "screen_authoritative": True, "live_workspace_untouched": True,
              "passing_indices": [1],
              "candidates": [{"index": 0, "passed": False, "failure": "TEST_FAILED"},
                             {"index": 1, "passed": True, "failure": None},
                             {"index": 2, "passed": False, "failure": "WALLCLOCK_EXCEEDED"}]}
    assert _screen_observations(screen, 36, 1) == [(0, False), (1, True)]
    assert _screen_observations(screen, 36, None) == [(0, False)]
    assert _screen_observations({**screen, "ok": False, "passing_indices": list(range(36))}, 36, 1) == []
    assert _screen_observations({**screen, "screen_authoritative": False}, 36, 1) == []
    candidates = _fair_candidates({"flood": [f"c{i}" for i in range(60)], "later": ["correct"]},
                                  ["flood", "later"], "original")
    assert candidates.index("correct") < 36


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_real_broker_reports_only_prefix_and_placeholders_do_not_become_evidence(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "pkg").mkdir(parents=True)
    (workspace / "pkg" / "__init__.py").write_text("")
    (workspace / "pkg" / "m.py").write_text("def f(x):\n    return x - 1\n")
    (workspace / "tests").mkdir()
    (workspace / "tests" / "test_m.py").write_text("from pkg.m import f\ndef test_f():\n    assert f(2) == 3\n")
    candidates = [{"pkg/m.py": "def f(x):\n    return 0\n"},
                  {"pkg/m.py": "def f(x):\n    return x + 1\n"}]
    candidates.extend({"pkg/m.py": f"def f(x):\n    return x + {n}\n"} for n in range(2, 36))
    result = broker.run_confined_python_candidate_batch(workspace, "pkg/m.py", ["tests/test_m.py"], candidates,
                                                        stop_on_first_pass=True)
    assert result["ok"] and result["passing_indices"] == [1]
    assert [row["index"] for row in result["candidates"]] == [0, 1]
    assert _screen_observations(result, len(candidates), 1) == [(0, False), (1, True)]
    # The broker reports placeholder pass indices when it cannot snapshot the
    # workspace. They are not real passes and must not enter learned memory.
    (workspace / "unsafe_link").symlink_to(workspace / "pkg" / "m.py")
    denied = broker.run_confined_python_candidate_batch(workspace, "pkg/m.py", ["tests/test_m.py"], candidates)
    assert denied["ok"] is False and len(denied["passing_indices"]) == len(candidates)
    assert _screen_observations(denied, len(candidates), 1) == []


def test_scope_preserves_reference_other_functions_and_source_version(tmp_path):
    daemon, workspace, module, _ = make_daemon(tmp_path, GEOM)
    before = module.read_text()
    good = before.replace("return w + h", "return w * h", 1)
    bad = good.replace("return s * s", "return s + s", 1)
    assert only_target_expression_changed(before, good, "rect_area")
    assert not only_target_expression_changed(before, bad, "rect_area")
    test = workspace / "test_scope.py"
    binding = {"module": "pkg/example.py", "source_sha256": hashlib.sha256(before.encode()).hexdigest(),
               "target": "rect_area", "reference": "square_area", "finding_id": "fixture"}
    test.write_text("# brain-notion-v1 " + json.dumps(binding) + "\n")
    assert creature._notion_repair_scope(test, workspace, {"pkg/example.py": good}) is None
    assert creature._notion_repair_scope(test, workspace, {"pkg/example.py": bad}) == "NOTION_SCOPE_CHANGED_OTHER_CODE"
    assert creature._notion_repair_scope(test, workspace, {"pkg/example.py": good, "other.py": "x"}) == "NOTION_SCOPE_INVALID"
    module.write_text(before + "\n# stale\n")
    assert creature._notion_repair_scope(test, workspace, {"pkg/example.py": good}) == "NOTION_SOURCE_CHANGED"


def test_truncated_hypothesis_space_cannot_authorize(tmp_path):
    source = "def ref(x):\n    return x*x*x*x*x\n\ndef target(a,b,c,d):\n    return a+b+c+d\n"
    result = notions_for_source(source, "m")[0].evaluate()
    assert result["fired"]
    examples = [{"args": [2, 3, 4, 5], "expected": 2*3*4*5*5},
                {"args": [3, 4, 5, 6], "expected": 3*4*5*6*6}]
    plan = investigate(source, target_name="target", reference_name="ref",
                       observations=result["observations"], examples=examples)
    assert plan.get("truncated") is True
    assert plan["status"] != "bounded_agreement"


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_reviewed_candidate_is_checked_before_live_publication(tmp_path):
    d, workspace, module, _ = make_daemon(tmp_path, GEOM)
    before = module.read_text()
    finding = finding_for(d, "square_area", "rect_area")
    store = NotionStore(d.notions_path)
    store.review(finding["id"], decision="confirm", reviewer="fixture", basis="contract",
                 trusted_function="square_area")
    for _ in range(2):
        plan = finding_for(d, "square_area", "rect_area")["plan"]
        args = plan["next_query"]["args"]
        store.answer(finding["id"], args=args, expected=args[0] * args[1],
                     reviewer="fixture", basis="outside oracle")
    assert d._sense_failing_workspace_tests()
    test = workspace / "tests" / "test_example.py"
    wrong = before.replace("return w + h", "return w * w", 1)
    ok, _, _ = creature._publish_notion_candidate(workspace, test, {"pkg/example.py": wrong},
                                                  notions_path=d.notions_path)
    assert not ok and module.read_text() == before
    right = before.replace("return w + h", "return w * h", 1)
    ok, probe, reason = creature._publish_notion_candidate(workspace, test, {"pkg/example.py": right},
                                                           notions_path=d.notions_path)
    assert ok and reason is None and probe["generalizes"]
    assert module.read_text() == right


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_generalization_probe_does_not_execute_workspace_on_host(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "pkg").mkdir(parents=True)
    (workspace / "pkg" / "__init__.py").write_text("")
    (workspace / "tests").mkdir()
    marker = tmp_path / "host_marker"
    module = workspace / "pkg" / "example.py"
    module.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n"
                      "def f(x):\n    return x * 2\n")
    test = workspace / "tests" / "test_example.py"
    test.write_text("from pkg.example import f\ndef test_f():\n    assert f(2) == 4\n")
    result = creature._generalization_probe(test, workspace)
    assert result["generalizes"] is False
    assert not marker.exists()


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_generalization_probe_resists_simple_print_hijack(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "bad.py").write_text(
        "import builtins, sys\n"
        "def constant(x):\n"
        "    def forged(*args, **kwargs):\n"
        "        sys.stdout.write('BRAIN_PROBE_RESULT {\\\"generalizes\\\": true}\\n')\n"
        "    builtins.print = forged\n"
        "    return 5\n"
    )
    test = workspace / "test_bad.py"
    test.write_text("from bad import constant\ndef test_value():\n    assert constant(1) == 5\n")
    result = creature._generalization_probe(test, workspace)
    assert result["generalizes"] is False
    assert result["reason"] == "PROBE_SOURCE_UNSUPPORTED"



@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_generalization_probe_would_refuse_frame_introspection_spoof(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "bad.py").write_text(
        "import sys\n"
        "def constant(x):\n"
        "    frame = sys._getframe()\n"
        "    while frame is not None:\n"
        "        g = frame.f_globals\n"
        "        if 'payload' in g and '_emit_result' in g:\n"
        "            g['_emit_result'] = lambda _: sys.stdout.write("
        "'BRAIN_PROBE_RESULT {\\\"generalizes\\\": true, \\\"reason\\\": \\\"forged\\\"}\\n')\n"
        "            break\n"
        "        frame = frame.f_back\n"
        "    return 5\n"
    )
    test = workspace / "test_bad.py"
    test.write_text("from bad import constant\ndef test_value():\n    assert constant(1) == 5\n")
    result = creature._generalization_probe(test, workspace)
    assert result["generalizes"] is False
    assert result["reason"] == "PROBE_SOURCE_UNSUPPORTED"


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
def test_generalization_probe_refuses_duplicate_spoofed_records(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "bad.py").write_text(
        "print('BRAIN_PROBE_RESULT {\\\"generalizes\\\": true}')\n"
        "def constant(x):\n"
        "    return 5\n"
    )
    test = workspace / "test_bad.py"
    test.write_text("from bad import constant\ndef test_value():\n    assert constant(1) == 5\n")
    result = creature._generalization_probe(test, workspace)
    assert result["generalizes"] is False
    assert result["reason"] == "PROBE_SOURCE_UNSUPPORTED"


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
@pytest.mark.parametrize("source,trusted,target,oracle,holdout", [
    (GEOM, "square_area", "rect_area", lambda a: a[0] * a[1], [(5, 7), (9, 11)]),
    (HIDDEN_NAMES, "plain", "wide", lambda a: a[0] * a[1], [(5, 7), (9, 11)]),
    (ADDITION_BUG, "one_measure", "two_measure", lambda a: a[0] + a[1], [(5, 7), (-2, 3)]),
    (DIFFERENCE_BUG, "one_delta", "two_delta", lambda a: a[0] - a[1], [(5, 7), (-2, 3)]),
    (WIDE_BUG, "cube_volume", "box_volume", lambda a: a[0] * a[1] * a[2], [(3, 5, 7), (-2, 3, 5)]),
    (NARROW_BUG, "box_volume", "cube_volume", lambda a: a[0] * a[0] * a[0], [(8,), (-2,)]),
])
def test_reviewed_query_loop_reaches_board_and_held_out_inputs(tmp_path, source, trusted, target, oracle, holdout):
    daemon, workspace, module, root = make_daemon(tmp_path, source)
    assert daemon._sense_failing_workspace_tests() == []
    assert module.read_text() == source and not list(workspace.rglob("test_*.py"))
    finding = finding_for(daemon, trusted, target)
    store = NotionStore(daemon.notions_path)
    store.review(finding["id"], decision="confirm", reviewer="fixture", basis="independent relation contract",
                 trusted_function=trusted)
    queries = []
    for _ in range(12):
        finding = finding_for(daemon, trusted, target)
        plan = finding["plan"]
        if plan["status"] == "bounded_agreement":
            break
        assert plan["status"] == "needs_example", plan
        args = plan["next_query"]["args"]
        queries.append(tuple(args))
        store.answer(finding["id"], args=args, expected=oracle(args), reviewer="fixture",
                     basis="independent test oracle")
    else:
        pytest.fail("query budget exhausted")
    assert len(queries) >= 2 and len(set(queries)) == len(queries)
    assert not any(tuple(args) in queries for args in holdout)
    assert daemon._sense_failing_workspace_tests()
    test_file = workspace / "tests" / "test_example.py"
    assert test_file.is_file() and test_file.read_text().startswith("# brain-notion-v1 ")
    report = creature.run_sovereign_board(root, cycles=6, identity="p", life=480, slice_size=480, workspace=workspace)
    repair_steps = [step for step in report["run"].get("steps", []) if str(step.get("work", "")).startswith("repair:")]
    accepted = next((step for step in repair_steps if step.get("accepted_into_world") == ["pkg/example.py"]), None)
    assert accepted is not None, repair_steps
    assert accepted["verified"] is False and accepted["correct"] is None
    after = module.read_text()
    assert only_target_expression_changed(source, after, target)
    spec = importlib.util.spec_from_file_location("fixture_program", module)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    for args in holdout:
        assert getattr(loaded, target)(*args) == oracle(args)
    # Unrelated definitions are byte-identical because of the scope check above.
    assert ast.parse(after)
