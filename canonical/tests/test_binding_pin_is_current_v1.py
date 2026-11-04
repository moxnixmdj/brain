"""Tests for the binding-pin kernel: a pin that is claimed must still be true.

Every test here is written so that breaking the mechanism makes it fail. A test that
passes on a kernel returning `{"pass": True}` unconditionally is not evidence.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import binding_pin_is_current_v1 as K  # noqa: E402


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _tree(tmp_path: Path, *, binding: bytes = b"BINDING = 1\n",
          pin: str | None = None, extra: dict | None = None) -> Path:
    """A miniature repository with one bound row and one adapter module."""
    adapter = tmp_path / "canonical/runtime/bound_capabilities/demo_v1.py"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_bytes(binding)
    verification = {"runtime_sha256": pin if pin is not None else _sha(binding)}
    if extra:
        verification.update(extra)
    # Mirrors the real registry's shape: `capabilities` is a DICT keyed by capability id.
    reg = {"schema": "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1",
           "capabilities": {"DEMO_V1": {"adapter_module": "demo_v1", "entrypoint": "run",
                                        "verification": verification}}}
    path = tmp_path / K.REGISTRY
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg), encoding="utf-8")
    return tmp_path


def _contract(G) -> dict:
    return json.loads((REPO / G.CONTRACT_PATH).read_text(encoding="utf-8"))


def _contract_sha(G) -> str:
    return hashlib.sha256((REPO / G.CONTRACT_PATH).read_bytes()).hexdigest()


def _intent(G) -> dict:
    """The smallest intent that reaches past the orientation gate's early returns."""
    contract = _contract(G)
    must_read = ((contract.get("current_laws") or {})
                 .get("must_read_before_consequential_action") or [])
    return {G.INTENT_FIELD: {
        "contract": G.CONTRACT_PATH,
        "contract_sha256": _contract_sha(G),
        "route_class": "REUSE",
        "laws_read_this_session": list(must_read),
        "producer_cognition_model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "conversation_memory_is_authority": False,
    }}


def test_a_pin_that_matches_the_file_passes(tmp_path):
    root = _tree(tmp_path)
    report = K.audit(root)
    assert report["stale"] == []
    assert report["checked"], "a matching pin must actually be compared, not skipped"
    assert report["checked"][0]["match"] is True
    assert K.refusal(root) is None


def test_a_pin_the_file_contradicts_is_refused(tmp_path):
    """The measured live defect: the adapter moved, the advertised sha did not."""
    root = _tree(tmp_path, pin="0" * 64)
    report = K.audit(root)
    assert len(report["stale"]) == 1
    assert report["stale"][0]["claimed"] == "0" * 64
    assert report["stale"][0]["actual"] == _sha(b"BINDING = 1\n")

    refusal = K.refusal(root)
    assert refusal is not None
    assert refusal["status"] == "FAIL_CLOSED__" + K.REFUSAL
    assert refusal["reason"] == "A_BOUND_ROW_CLAIMS_A_PIN_THE_FILE_NO_LONGER_MATCHES"
    assert refusal["pass"] is False


def test_stale_rows_that_predate_the_baseline_are_grandfathered(tmp_path):
    """History is not rewritten. The 3 rows already stale at a70480d4 must not wedge
    every pull request forever; a NEW stale row must."""
    root = _tree(tmp_path, pin="0" * 64)
    frozen = K.baseline(K.audit(root))
    assert frozen["stale_count"] == 1
    assert K.refusal(root, frozen=frozen) is None, "a frozen stale row must not refuse"

    reg_path = root / K.REGISTRY
    reg = json.loads(reg_path.read_text())
    reg["capabilities"]["SECOND_V1"] = {"adapter_module": "demo_v1", "entrypoint": "run",
                                        "verification": {"runtime_sha256": "1" * 64}}
    reg_path.write_text(json.dumps(reg), encoding="utf-8")

    refusal = K.refusal(root, frozen=frozen)
    assert refusal is not None, "a NEW stale pin must refuse"
    assert refusal["reason"] == "A_BOUND_ROW_CLAIMS_A_PIN_THE_FILE_NO_LONGER_MATCHES"
    assert refusal["was"] == 1 and refusal["now"] == 2


def test_editing_the_adapter_after_pinning_makes_it_stale(tmp_path):
    """Same tree, one byte changed: the pin must stop being true by itself."""
    root = _tree(tmp_path)
    assert K.refusal(root) is None
    adapter = root / "canonical/runtime/bound_capabilities/demo_v1.py"
    adapter.write_bytes(b"BINDING = 2\n")
    assert K.refusal(root) is not None


def test_a_row_with_no_pin_is_unfalsifiable_not_false(tmp_path):
    """The distinction is load-bearing: 138 of 141 live rows are in this state."""
    root = _tree(tmp_path)
    reg_path = root / K.REGISTRY
    reg = json.loads(reg_path.read_text())
    reg["capabilities"]["DEMO_V1"]["verification"] = {"status": "ok", "mission_id": "M-1"}
    reg_path.write_text(json.dumps(reg), encoding="utf-8")

    report = K.audit(root)
    assert report["unfalsifiable"] == ["DEMO_V1"]
    assert report["stale"] == [], "an absent pin is not a false pin"
    assert report["checked"] == []
    assert K.refusal(root) is None


def test_output_hashes_are_not_compared_to_source_files(tmp_path):
    """`independent_output_sha256` is a run's product. Comparing it to the adapter
    would invent a staleness that is not real -- so it must be excluded."""
    root = _tree(tmp_path, extra={"independent_output_sha256": "a" * 64})
    report = K.audit(root)
    assert report["stale"] == []
    assert all(c["key"] != "independent_output_sha256" for c in report["checked"])


def test_a_new_synonym_key_is_checked_without_editing_the_kernel(tmp_path):
    """The generalization claim, tested directly.

    The live registry uses 23 sha-shaped key names and 86 keys private to one row. A
    kernel that only knew `runtime_sha256` would pass every other row forever.
    """
    for key in ("pin_green", "we_checked_it_honestly", "exact_runtime_blob_sha",
                "totally_new_name"):
        root = _tree(tmp_path / key, pin="f" * 64, extra={})
        reg_path = root / K.REGISTRY
        reg = json.loads(reg_path.read_text())
        v = reg["capabilities"]["DEMO_V1"]["verification"]
        v[key] = v.pop("runtime_sha256")
        reg_path.write_text(json.dumps(reg), encoding="utf-8")

        report = K.audit(root)
        assert len(report["stale"]) == 1, f"{key} was not checked -- kernel is vocabulary-bound"
        assert report["stale"][0]["key"] == key


def test_a_non_sha_value_under_a_sha_key_grants_nothing(tmp_path):
    """A key called `runtime_sha256` holding "ok" is not a pin. It must not pass,
    and it must not fail: it is simply not checkable."""
    root = _tree(tmp_path)
    reg_path = root / K.REGISTRY
    reg = json.loads(reg_path.read_text())
    reg["capabilities"]["DEMO_V1"]["verification"] = {"runtime_sha256": "ok"}
    reg_path.write_text(json.dumps(reg), encoding="utf-8")

    report = K.audit(root)
    assert report["checked"] == []
    assert report["unfalsifiable"] == ["DEMO_V1"]


def test_missing_target_is_reported_not_passed(tmp_path):
    """A real pin naming no file in the tree confirms nothing either way."""
    root = _tree(tmp_path)
    reg_path = root / K.REGISTRY
    reg = json.loads(reg_path.read_text())
    # a test-blob pin on a row whose test file is not present
    reg["capabilities"]["DEMO_V1"]["verification"] = {"test_sha256": "b" * 64}
    reg_path.write_text(json.dumps(reg), encoding="utf-8")

    report = K.audit(root)
    assert report["missing"], "an unconfirmable pin must be reported, not silently dropped"
    assert report["missing"][0]["why"] == "NO_TARGET_FILE"


def test_the_ratchet_refuses_growth_but_allows_history(tmp_path):
    root = _tree(tmp_path)
    reg_path = root / K.REGISTRY
    reg = json.loads(reg_path.read_text())
    reg["capabilities"]["DEMO_V1"]["verification"] = {"status": "ok"}  # 1 unfalsifiable
    reg_path.write_text(json.dumps(reg), encoding="utf-8")

    frozen = K.baseline(K.audit(root))
    assert frozen["unfalsifiable_count"] == 1
    assert K.refusal(root, frozen=frozen) is None, "the frozen state must not refuse itself"

    reg["capabilities"]["SECOND_V1"] = {"adapter_module": "second_v1", "entrypoint": "run",
                                        "verification": {"status": "ok"}}
    reg_path.write_text(json.dumps(reg), encoding="utf-8")

    refusal = K.refusal(root, frozen=frozen)
    assert refusal is not None
    assert refusal["reason"] == "UNFALSIFIABLE_BOUND_CLAIMS_GREW"
    assert refusal["was"] == 1 and refusal["now"] == 2


def test_the_ratchet_is_satisfied_when_unfalsifiable_rows_are_fixed(tmp_path):
    """Growth fails; shrinkage must not."""
    root = _tree(tmp_path)
    reg_path = root / K.REGISTRY
    reg = json.loads(reg_path.read_text())
    reg["capabilities"]["SECOND_V1"] = {"adapter_module": "second_v1", "entrypoint": "run",
                                        "verification": {"status": "ok"}}
    reg_path.write_text(json.dumps(reg), encoding="utf-8")
    frozen = K.baseline(K.audit(root))
    assert frozen["unfalsifiable_count"] == 1

    del reg["capabilities"]["SECOND_V1"]  # the unpinned row is gone
    reg_path.write_text(json.dumps(reg), encoding="utf-8")
    assert K.refusal(root, frozen=frozen) is None


def test_the_live_registry_pin_verdict_is_stable():
    """Runs against the real registry: whatever it reports, nothing is stale-by-accident.

    This asserts the SHAPE of the live answer, not a hard-coded count, so it does not
    go red the moment someone legitimately re-pins a row.
    """
    report = K.audit(REPO)
    assert report["schema"] == K.SCHEMA
    assert report["rows"] > 100
    for row in report["stale"]:
        assert row["claimed"] != row["actual"]
    for row in report["checked"]:
        claimed = next((s["claimed"] for s in report["stale"]
                        if s["file"] == row["file"]), None)
        assert row["match"] == (claimed is None)


def test_run_contract_returns_a_dict_the_door_can_call():
    """`run(args, root) -> dict` is what the capability door invokes."""
    out = K.run({}, str(REPO))
    assert isinstance(out, dict)
    assert out["schema"] == K.SCHEMA
    assert "refusal" in out
    assert out["model_dependency_count"] == 0
    assert out["incremental_spend_usd"] == 0


def test_the_orientation_check_surfaces_a_false_pin(tmp_path):
    """The kernel is only a gate if the guard actually reports it.

    `orientation_errors` is the function the load-bearing admission gate calls for every
    pull-request intent; `verify` does not call it, which is why a broken wire here would
    have looked green. This test calls the function that matters, directly.
    """
    import execution_guard.agent_orientation_check_v1 as G

    root = _tree(tmp_path, pin="0" * 64)
    errors = G.orientation_errors(_intent(G), _contract(G), _contract_sha(G), (), None, root)
    # Contract and block errors are expected alongside; the pin error must be among them.
    assert any("A_BOUND_ROW_CLAIMS_A_PIN_THE_FILE_NO_LONGER_MATCHES" in e for e in errors), errors


def test_the_orientation_check_accepts_a_true_pin(tmp_path):
    import execution_guard.agent_orientation_check_v1 as G

    root = _tree(tmp_path)
    errors = G.orientation_errors(_intent(G), _contract(G), _contract_sha(G), (), None, root)
    assert not any("PIN" in e or "BOUND_ROW" in e for e in errors), errors


def test_the_wire_does_not_depend_on_canonical_being_importable(tmp_path, monkeypatch):
    """Regression for a REAL failure, written to actually fail when the fix is absent.

    `intent-check` reported ORIENTATION_BINDING_PIN_AUDIT_UNAVAILABLE:ModuleNotFoundError
    because the guard never puts the repo root on sys.path. A previous version of this
    test shelled out to the CLI from a temp cwd -- and passed even with the fix reverted,
    because the guard's early returns meant the wire never ran at all. That is a test
    proving nothing, so this one strips the repo root from sys.path and calls the
    function directly: the only way to observe the behaviour that actually broke.
    """
    import execution_guard.agent_orientation_check_v1 as G

    root = _tree(tmp_path, pin="0" * 64)
    monkeypatch.setattr(
        sys, "path", [p for p in sys.path if Path(p).resolve() != REPO])
    for name in [m for m in sys.modules if m.startswith("canonical")]:
        monkeypatch.delitem(sys.modules, name)

    errors = G.orientation_errors(_intent(G), _contract(G), _contract_sha(G), (), None, root)

    assert not any("BINDING_PIN_AUDIT_UNAVAILABLE" in e for e in errors), errors
    assert any("A_BOUND_ROW_CLAIMS_A_PIN_THE_FILE_NO_LONGER_MATCHES" in e for e in errors), errors


def test_a_green_flag_over_a_stale_pin_is_itself_a_false_claim(tmp_path):
    """Mutation gap, closed.

    Deleting the currency-flag check passed all sixteen tests, which means the flag
    branch was untested. A row that advertises both a hash and `pin_green: True` makes
    two claims; when the hash is wrong, the flag is false too, and must be reported.
    """
    root = _tree(tmp_path, pin="0" * 64, extra={"pin_green": True})
    report = K.audit(root)
    flags = [s for s in report["stale"] if s["key"] == "pin_green"]
    assert flags, "a green flag over a stale pin must be reported, not believed"
    assert flags[0]["claimed"] == "True (advertised)"


def test_a_green_flag_over_a_true_pin_is_believed(tmp_path):
    root = _tree(tmp_path, extra={"pin_green": True})
    report = K.audit(root)
    assert [s for s in report["stale"] if s["key"] == "pin_green"] == []


def test_every_bound_row_reaches_exactly_one_verdict(tmp_path):
    """No row may be silently dropped.

    The registry keys rows by capability id, and 141 rows share only 132 adapter module
    names. Keying verdicts by module collapsed nine rows; this pins the fix.
    """
    root = _tree(tmp_path)
    reg_path = root / K.REGISTRY
    reg = json.loads(reg_path.read_text())
    # three rows, one module name: the case that collapsed
    reg["capabilities"] = {
        "A_V1": {"adapter_module": "demo_v1", "verification": {"runtime_sha256": _sha(b"BINDING = 1\n")}},
        "B_V1": {"adapter_module": "demo_v1", "verification": {}},
        "C_V1": {"adapter_module": "demo_v1", "verification": {"runtime_sha256": "0" * 64}},
    }
    reg_path.write_text(json.dumps(reg), encoding="utf-8")

    verdicts = K.resolve(root)
    assert set(verdicts) == {"A_V1", "B_V1", "C_V1"}, verdicts
    assert verdicts["A_V1"]["verdict"] == K.FRESH
    assert verdicts["B_V1"]["verdict"] == K.UNVERIFIED
    assert verdicts["C_V1"]["verdict"] == K.STALE
    assert K.counts(verdicts) == {K.FRESH: 1, K.STALE: 1, K.UNVERIFIED: 1, K.UNKNOWN: 0}


def test_stale_and_unverified_are_not_collapsed(tmp_path):
    """A refuted claim and an absent one are different failures.

    Treating 138 unpinned rows as suspect would discard 138 capabilities on a
    technicality -- its own kind of dishonesty, and the same error in mirror image.
    """
    root = _tree(tmp_path, pin="0" * 64)
    reg_path = root / K.REGISTRY
    reg = json.loads(reg_path.read_text())
    reg["capabilities"]["UNPINNED"] = {"adapter_module": "demo_v1", "verification": {}}
    reg_path.write_text(json.dumps(reg), encoding="utf-8")

    verdicts = K.resolve(root)
    assert verdicts["UNPINNED"]["verdict"] == K.UNVERIFIED
    assert verdicts["UNPINNED"]["verdict"] != K.STALE


def test_a_stale_capability_costs_the_capability_its_offer():
    """The consequence, not the report.

    A verdict nothing consumes is an observation. `availability_v1` is what
    `live_integrated_brain_v1` builds its bound set from, so this is where a refuted
    capability has to stop being offered.
    """
    from canonical.runtime import availability_v1 as A

    reg = A.load_registry()
    av = A.available(reg)
    stale = sorted(c for c, m in av.items() if "verification_evidence_is_stale" in m)
    assert stale == [
        "python.fault.provenance.interprocedural.value.v1",
        "python.patch.search.test_guided.ast.v1",
        "python.software.repair.guided.provenance.coupled.v1",
    ], stale
    assert not set(stale) & set(A.runnable(reg)), "a stale capability must not be runnable"


def test_unverified_capabilities_are_still_offered():
    """138 rows carry no checkable pin. Deleting them on a technicality would be the
    same dishonesty in mirror image, so UNVERIFIED must cost nothing."""
    from canonical.runtime import availability_v1 as A

    reg = A.load_registry()
    runnable = set(A.runnable(reg))
    assert len(reg) > 140
    assert len(runnable) >= len(reg) - 6, (
        "only refuted capabilities may be withdrawn; unpinned ones must survive")


def test_a_broken_audit_never_removes_capabilities(monkeypatch):
    """Fails OPEN and only open: silently deleting the option set is worse than not
    auditing it."""
    from canonical.runtime import availability_v1 as A
    import canonical.runtime.binding_pin_is_current_v1 as pins

    A._STALE_CACHE.clear()
    monkeypatch.setattr(pins, "resolve", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    reg = A.load_registry()
    av = A.available(reg)
    assert not any("verification_evidence_is_stale" in m for m in av.values())
    A._STALE_CACHE.clear()


@pytest.fixture(autouse=True)
def _no_persistent_memory():
    """A test run must not write to the creature's committed memory store."""
    from canonical.tests._memory import no_persistent_memory

    with no_persistent_memory():
        yield
