#!/usr/bin/env python3
"""The enrollment gate must count real defects, refuse to invent predicates, and be satisfiable.

Two of these tests build a fixture registry so the assertions are known to bite: a tool that only
ever agrees with the file it reads is decoration. The first test recomputes three of the four defect
classes straight from the JSON, so the gate cannot quietly stop looking at rows it should.

The gate reads all four registry sources now, and one class was demoted from defect to fact: the live
registry and the snapshot floor are allowed to disagree (the merge is a union with the snapshot as a
floor), so a divergence is drift to read, not something to block on. The last test pins that
recomputation is not the reason the numbers went down: point the same code at a root without the spec
files and the queue, and all nine certified capabilities are unenrolled again.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

from canonical.tools import capability_enrollment_gate_v1 as gate

ROOT = pathlib.Path(gate.ROOT)
LIVE = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
SNAPSHOT = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json"
EXTENDED = ROOT / "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
PROJECTION = ROOT / "canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json"
PENDING = ROOT / "canonical/astra_runtime/pending_bindings"


def _merged_rows() -> dict:
    """The same four sources, in the loader's precedence order, read independently of the gate."""
    def rows_of(path, key="capabilities"):
        d = json.loads(path.read_text(encoding="utf-8"))
        return dict(d.get(key) or {})
    return {**rows_of(EXTENDED), **rows_of(PROJECTION, "entries"), **rows_of(LIVE), **rows_of(SNAPSHOT)}
LEDGER = ROOT / "canonical/capabilities/true/TRUE_CAPABILITY_LEDGER_V1.json"
ADAPTERS = ROOT / "canonical/runtime/bound_capabilities"


def _fixture(tmp: pathlib.Path, rows: dict, ledger_rows: dict | None = None) -> dict[str, pathlib.Path]:
    """A miniature repo: registry + snapshot + adapters dir + evidence dir + true-capability ledger."""
    adir = tmp / "canonical/runtime/bound_capabilities"
    adir.mkdir(parents=True, exist_ok=True)
    reg = tmp / "registry.json"
    reg.write_text(json.dumps({"capabilities": rows}), encoding="utf-8")
    snap = tmp / "snapshot.json"
    snap.write_text(json.dumps({"capabilities": rows}), encoding="utf-8")
    ledger = tmp / "ledger.json"
    ledger.write_text(json.dumps({"rows": ledger_rows or {}}), encoding="utf-8")
    (tmp / "evidence").mkdir(exist_ok=True)
    return {"root": tmp, "registry": reg, "snapshot": snap, "ledger": ledger, "adapters": adir}


def _build(f: dict) -> dict:
    return gate.build(f["root"], f["registry"], f["snapshot"], f["ledger"], f["adapters"])


def test_real_tree_defect_counts_match_an_independent_recomputation() -> None:
    r = gate.build(ROOT, LIVE, SNAPSHOT, LEDGER, ADAPTERS)
    rows = _merged_rows()
    assert len(rows) == r["registry_rows_merged"] > 2000, (
        "the gate must be looking at the whole dispatch surface, not the curated pair it started with"
    )

    missing = {cid for cid, row in rows.items()
               if isinstance(row.get("verification"), dict) and row["verification"].get("receipt_path")
               and not (ROOT / row["verification"]["receipt_path"]).is_file()}
    assert missing, "the known-missing receipts must still be named, not summarized away"
    assert missing == {x.split(" -> ")[0] for x in r["defects"]["MISSING_VERIFICATION_RECEIPT"]}

    def resolvable(row) -> bool:
        # Two conventions are in use and both are honoured by the code that dispatches: an adapter
        # module under bound_capabilities/, or an explicit `source.path` / `source.adapter_path`.
        # The row that used to be flagged here, python.task.acceptance.measured.objective.v1, is a
        # stdlib composition living in canonical/runtime/ -- my first rule could not see it, and a
        # defect class that reports the checker's blind spot is not a defect class.
        am = row.get("adapter_module")
        if not am or am == "runtime_native_action":
            return True
        if (ADAPTERS / f"{am}.py").is_file():
            return True
        src = row.get("source") or {}
        return any((ROOT / str(src[k])).is_file() for k in ("path", "adapter_path") if src.get(k))

    dangling = {cid for cid, row in rows.items() if not resolvable(row)}
    assert dangling == {x.split(" -> ")[0] for x in r["defects"]["DANGLING_ADAPTER"]}

    # `runtime_native_action` is a declared kind, so it is listed apart and never counted as broken.
    native = {cid for cid, row in rows.items() if row.get("adapter_module") == "runtime_native_action"}
    assert r["native_kind_rows"] == len(native) and native
    assert not any("runtime_native_action" in x for x in r["defects"]["DANGLING_ADAPTER"])

    assert r["certified_capabilities"] == 9
    # Enrollment is graded, because the tree has two legitimate states: a row the root already reads,
    # and a pending binding queued for the receipt only CI may mint. Anything else is a defect.
    assert r["registry_rows_extended"] == 2319, "the generated rows are registered, and one is not a typo"
    # Every measured capability now has a row the dispatch surface reads. Before the enrollment tool
    # existed this was `["SACCR_CREDIT_ADDON_V1"]` and eight unenrolled; the count is the point, and the
    # bite test below is what stops it from being satisfied by a loosened rule.
    assert set(r["certified_registry_bound"]) == set(json.loads(LEDGER.read_text())["rows"]), (
        f"bound: {r['certified_registry_bound']}"
    )
    assert r["certified_pending_binding_only"] == []
    assert r["defect_counts"]["UNENROLLED_CERTIFIED_CAPABILITY"] == 0
    assert r["pending_bindings"] == len(list(PENDING.glob("*.json"))) == 16
    assert "REGISTRY_VS_SNAPSHOT_DIVERGENCE" not in r["defect_counts"], (
        "a by-design floor may not be a blocker: making it one is how a gate gets deleted"
    )
    assert "floor" in r["facts"]["REGISTRY_VS_SNAPSHOT_DIVERGENCE_note"]
    assert isinstance(r["facts"]["REGISTRY_VS_SNAPSHOT_DIVERGENCE"], list)
    assert r["registry_rows_admitted_by_root"] == r["registry_rows_admitted_by_root"] is not None
    assert r["admission_probe_error"] is None
    assert r["clean"] is False, "8 cited receipts are still absent and 25 preconditions still unsatisfied"


def test_gate_detects_a_fabricated_adapter_and_a_lost_receipt(tmp_path: pathlib.Path) -> None:
    rows = {
        "a.real": {"adapter_module": "a_real_adapter", "provides": ["x"], "requires": ["y"],
                   "verification": {"receipt_path": "evidence/a.json"}},
        "b.broken": {"adapter_module": "no_such_adapter", "provides": ["y"],
                      "verification": {"receipt_path": "evidence/gone.json"}},
        "c.native": {"adapter_module": "runtime_native_action", "provides": ["z"]},
    }
    f = _fixture(tmp_path, rows)
    (f["adapters"] / "a_real_adapter.py").write_text("#\n", encoding="utf-8")
    (tmp_path / "evidence/a.json").write_text("{}\n", encoding="utf-8")
    r = _build(f)
    assert r["defects"]["DANGLING_ADAPTER"] == ["b.broken -> no_such_adapter"]
    assert r["defects"]["MISSING_VERIFICATION_RECEIPT"] == ["b.broken -> evidence/gone.json"]
    assert r["native_kind_rows"] == 1
    assert r["defect_counts"]["UNENROLLED_CERTIFIED_CAPABILITY"] == 0
    assert r["clean"] is False


def test_unsatisfiable_requires_is_about_providers_not_spellings(tmp_path: pathlib.Path) -> None:
    """A requires term no row provides is a planning dead end; renaming the fixture fixes it, which
    is the point: the gate is checking the vocabulary, not the files."""
    base = {"p": {"adapter_module": "a", "provides": ["x"], "requires": ["y"]}}
    f = _fixture(tmp_path, base)
    (f["adapters"] / "a.py").write_text("#\n", encoding="utf-8")
    assert _build(f)["defects"]["UNSATISFIABLE_REQUIRES"] == ["y"]
    fixed = {**base, "q": {"adapter_module": "a", "provides": ["y"]}}
    f2 = _fixture(tmp_path, fixed)
    (f2["adapters"] / "a.py").write_text("#\n", encoding="utf-8")
    assert _build(f2)["clean"] is True


def test_cli_exit_code_is_the_defect_verdict(tmp_path: pathlib.Path) -> None:
    f = _fixture(tmp_path, {"p": {"adapter_module": "a", "provides": ["x"], "requires": ["y"],
                                  "verification": {"receipt_path": "evidence/y.json"}}})
    (f["adapters"] / "a.py").write_text("#\n", encoding="utf-8")
    (tmp_path / "evidence/y.json").write_text("{}\n", encoding="utf-8")

    def run() -> int:
        return subprocess.run(
            [sys.executable, str(ROOT / "canonical/tools/capability_enrollment_gate_v1.py"),
             "--root", str(tmp_path), "--registry", str(f["registry"]), "--snapshot", str(f["snapshot"]),
             "--ledger", str(f["ledger"]), "--adapters", str(f["adapters"]), "--fail-on-defect"],
            capture_output=True, text=True, check=False,
        ).returncode

    assert run() == 1, "y has no provider: a planner cannot reach this row, so CI must fail"
    # now give y a provider and confirm the same command exits 0: the gate is satisfiable, which is
    # what makes it a gate rather than a complaint.
    f["registry"].write_text(json.dumps({"capabilities": {
        "p": {"adapter_module": "a", "provides": ["x"], "requires": ["y"],
              "verification": {"receipt_path": "evidence/y.json"}},
        "q": {"adapter_module": "a", "provides": ["y"]},
    }}), encoding="utf-8")
    f["snapshot"].write_text(f["registry"].read_text(encoding="utf-8"), encoding="utf-8")
    assert run() == 0, "with a provider for y, the fixture is genuinely clean"


def test_owned_family_routes_are_counted_and_not_confused_with_enrollment() -> None:
    """The other capability class in the repo: ownership-matrix families whose route is a module.

    A `.auto.v1` inventory row means the file was seen, not that the brain can run it. The receipt lane
    only executes modules that speak `run(args, root) -> dict`, so today all four named route modules are
    reachable-but-unenrollable, and the gate has to say so rather than let "it is in the registry" slide.
    """
    r = gate.build(ROOT, LIVE, SNAPSHOT, LEDGER, ADAPTERS)
    census = r["family_routes"]
    assert len(census) == 4, sorted(census)
    assert r["family_route_verdicts"] == {"INVENTORY_ONLY__NOT_DISPATCH_SHAPE": 3,
                                         "RECEIPTED__NO_INDEPENDENT_VERIFICATION": 1}, r["family_route_verdicts"]
    assert "ADMITTED" not in r["family_route_verdicts"], (
        "if an owned-family route ever becomes admitted, that is real news: the point of this test is "
        "that none of them are dispatchable today, and a green here must mean the tree changed, not that "
        "the rule got looser"
    )
    for fam, v in census.items():
        assert v["inventory_status"] == "UNVERIFIED_INVENTORY", f"{fam}: {v['inventory_status']}"
        assert v["bound_by_other_rows"] == [], f"{fam}: bound by {v['bound_by_other_rows']}"
        assert v["producer_receipt"] is (fam == "COMPLEX_MULTI_TOOL_AGENCY"), f"{fam}: {v['producer_receipt']}"
        if v["producer_receipt"]:
            assert v["independent_verification"] is False, f"{fam}: receipt got independent too"
        else:
            assert not v["dispatch_shape"], f"{fam}: no receipt but a valid dispatch shape -- recheck the ladder"
    assert r["defects"]["FAMILY_ROUTE_FILE_MISSING"] == []
    # The bite, on a fixture: a family citing a module that is not in the tree is a defect, not a fact.
    f = _fixture(tmp_path := pathlib.Path("/tmp/gate-family-fixture"), {})
    matrix = f["root"] / "canonical/capabilities/opus55"
    matrix.mkdir(parents=True, exist_ok=True)
    (matrix / "OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json").write_text(json.dumps(
        {"rows": [{"family": "MADE_UP", "verified_route": {"path": "canonical/runtime/nope_v1.py"}}]}),
        encoding="utf-8")
    r2 = gate.build(f["root"], f["registry"], f["snapshot"], f["ledger"], f["adapters"])
    assert r2["defects"]["FAMILY_ROUTE_FILE_MISSING"] == ["MADE_UP -> canonical/runtime/nope_v1.py"]


def test_a_root_without_specs_or_queue_unenrolls_all_nine(tmp_path: pathlib.Path) -> None:
    """The bite: the good numbers above come from files, not from a rule that stopped looking.

    Same registry and ledger JSON, same code, but a root with no spec files and no pending bindings:
    nothing is traceable, so all nine certified capabilities are unenrolled and the root probe refuses
    to answer rather than reporting the repository's counts.
    """
    r = gate.build(tmp_path, LIVE, SNAPSHOT, LEDGER, ADAPTERS)
    assert r["defect_counts"]["UNENROLLED_CERTIFIED_CAPABILITY"] == 9
    assert r["certified_registry_bound"] == [] and r["certified_pending_binding_only"] == []
    assert r["registry_rows_admitted_by_root"] is None
    assert "skipped" in (r["admission_probe_error"] or "")


def test_candidates_carry_evidence_and_refuse_to_invent_predicates() -> None:
    r = gate.build(pathlib.Path("/nonexistent-but-a-real-shape"), LIVE, SNAPSHOT, LEDGER, ADAPTERS)
    cands = gate.candidates(ROOT, LEDGER, r)
    assert len(cands) == 9
    assert len(cands) == r["defect_counts"]["UNENROLLED_CERTIFIED_CAPABILITY"]
    for c in cands:
        assert c["provides"] is None and c["requires"] is None, "a predicate invented here is an unmeasured claim"
        assert c["incremental_spend_usd"] == 0
        assert c["status"].startswith("CANDIDATE_NOT_ADMITTED")
        assert c["evidence"]["true_capability_receipt"] and c["evidence"]["receipt_sha256_16_present"] is True
        assert (ROOT / c["evidence"]["true_capability_receipt"]).is_file()
        assert len(c["admission_blocked_until"]) == 3, "the two-condition rule must travel with the candidate"
        assert c["kernel_module"] and (ROOT / c["kernel_module"]).is_file()


def test_markdown_names_every_class_even_when_empty() -> None:
    r = gate.build(ROOT, LIVE, SNAPSHOT, LEDGER, ADAPTERS)
    md = gate.to_markdown(r)
    for k in gate.DEFECT_ORDER:
        assert f"`{k}`" in md
    for k in gate.FACT_ORDER:
        assert f"`{k}`" in md and "fact, not a defect" in md
    assert "admitted by" in md and "pending binding only" in md
