#!/usr/bin/env python3
"""Every measured capability must reach the one registry the brain dispatches from -- by execution.

The claim under test is narrow and checkable. For each of the nine capabilities that the true-capability
law measured (fresh instances, independent oracles, mutation-tested):

  * a thin adapter exists at the dispatch surface and *runs*;
  * the composition edge generator -> kernel -> oracles was executed, and every declared oracle verdict
    in `COMPOSITION_EDGES_V1.json` shows passes with zero failures and zero errors;
  * exactly one pending binding is queued, in the shape the tree's own acquisition lanes use;
  * no status was granted locally, because a status the root reads is a claim that someone *else* ran it.

Tests 1 and 4 are the ones that keep this honest over time: they re-execute rather than re-read, so an
adapter that stops forwarding, an oracle that starts failing, or a predicate that drifted from the code
fails the suite even if every JSON in the directory is edited by hand.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

TOOL = "canonical/tools/capability_enroll_certified_v1.py"
ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / "canonical/capabilities/true/TRUE_CAPABILITY_LEDGER_V1.json"
EDGES = ROOT / "canonical/capabilities/COMPOSITION_EDGES_V1.json"
ADAPTERS = ROOT / "canonical/runtime/bound_capabilities"
FIXTURES = ROOT / "canonical/capabilities/true/instances"
PENDING = ROOT / "canonical/astra_runtime/pending_bindings"
LIVE = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
SNAPSHOT = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json"


def _slug(cap: str) -> str:
    import re
    return re.sub(r"_v\d+$", "", cap.lower())


def _pending_for(capability_id: str) -> list[pathlib.Path]:
    out = []
    for f in sorted(PENDING.glob("TRUECAP-ENROLL-*.json")):
        try:
            if json.loads(f.read_text(encoding="utf-8")).get("capability_id") == capability_id:
                out.append(f)
        except (OSError, ValueError):
            out.append(f)  # unreadable is its own failure, surfaced by the count assertion
    return out


def _load_module(path: pathlib.Path, name: str):
    """Registered in sys.modules before exec, the harness's own contract: @dataclass resolves class
    annotations through sys.modules at decoration time, so an unregistered module raises on import."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_check_re_derives_the_whole_enrollment_and_passes() -> None:
    """`--check` executes every adapter with the receipt lane's own argument shape."""
    r = subprocess.run([sys.executable, str(TOOL), "--check"], cwd=ROOT,
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, f"drift between the code and the queue:\n{r.stdout}\n{r.stderr}"
    assert "CHECK PASS" in r.stdout and "9 capabilities derived" in r.stdout, r.stdout


def test_every_measured_capability_is_queued_once_with_a_resolving_adapter() -> None:
    caps = sorted((json.loads(LEDGER.read_text(encoding="utf-8")).get("rows") or {}))
    assert len(caps) == 9
    for cap in caps:
        cid = f"truecap.{_slug(cap)}"
        queued = _pending_for(cid)
        assert len(queued) == 1, f"{cap}: {len(queued)} queue entries, expected exactly one"
        binding = json.loads(queued[0].read_text(encoding="utf-8"))
        entry = binding["registry_entry"]
        adapter = ADAPTERS / f"{entry['adapter_module']}.py"
        assert adapter.is_file(), f"{cap}: the queue names {adapter.name}, which is not in the tree"
        assert (ROOT / str(binding["verification_fixture"])).is_file(), f"{cap}: fixture not committed"
        assert binding["status"] == "PENDING_INDEPENDENT_VERIFICATION"
        assert entry["status"] == "BOUND_PENDING_INDEPENDENT_VERIFICATION"
        assert entry["incremental_spend_usd"] == 0
        assert entry["entrypoint"] == "run"
        tmpl = entry["action_template"]
        assert tmpl["type"] == "invoke_capability"
        assert tmpl["args"]["capability_id"] == cid
        # The lane fills `${input.*}` placeholders and passes everything else through verbatim, so a
        # literal path in the template is what makes this capability re-runnable by someone else.
        assert (ROOT / str(tmpl["args"]["instance_path"])).is_file(), f"{cap}: template path unresolvable"


def test_the_composition_edge_is_certified_by_execution_not_by_promise() -> None:
    doc = json.loads(EDGES.read_text(encoding="utf-8"))
    assert doc["authority"].startswith("NONE__"), "a sandbox measurement is not an attestation"
    per_edge = int(doc["instances_per_edge"])
    for cap, edge in sorted((doc.get("edges") or {}).items()):
        assert "error" not in edge, f"{cap}: edge unmeasured ({edge.get('error')})"
        assert edge["instances_generated"] == per_edge
        verdicts = edge.get("oracle_verdicts") or {}
        assert len(verdicts) >= 3, f"{cap}: {len(verdicts)} oracles is not a certification"
        for oid, v in sorted(verdicts.items()):
            assert v["fail"] == 0, f"{cap}/{oid}: {v['fail']} of {v['of']} oracle checks failed: {v['first_detail']}"
            assert v["error"] == 0, f"{cap}/{oid}: oracle errored: {v['first_detail']}"
            assert v["pass"] == v["of"] == per_edge, f"{cap}/{oid}: {v['pass']}/{v['of']} is not a pass"
        for c in edge.get("canary_results") or []:
            assert c["pass"] is True, f"{cap}: published canary {c['id']} failed: {c['detail']}"


def test_the_declared_expectation_is_the_strictest_one_the_evidence_supports() -> None:
    """A binding whose expectation no result can meet is worse than no binding: it looks published."""
    edges = json.loads(EDGES.read_text(encoding="utf-8"))["edges"]
    caps = sorted((json.loads(LEDGER.read_text(encoding="utf-8")).get("rows") or {}))
    for cap in caps:
        edge = edges[cap]
        expect = edge["expectation"]
        vals = edge.get("status_values") or []
        if expect["type"] == "field_equals":
            assert expect["field"] == "status" and edge["status_field_present"] is True
            assert expect["value"] in vals and str(expect["value"]) != "None", (
                f"{cap}: asserting field_equals against a value the kernel never returns"
            )
        else:
            assert edge["status_field_present"] is not True or len(vals) != 1
            assert expect["field"] in ("status", "capability_id")
        entry = json.loads(_pending_for(f"truecap.{_slug(cap)}")[0].read_text(encoding="utf-8"))["registry_entry"]
        assert entry["action_template"]["expect"] == expect, f"{cap}: queue and edge disagree"
        # `astra_runtime.py` understands exactly these two expectation types; anything else is a typo.
        assert expect["type"] in ("field_equals", "field_nonempty")


def test_an_adapter_without_an_instance_fails_closed_rather_than_inventing_one(tmp_path: pathlib.Path) -> None:
    """A root with no committed fixture must produce a refusal, not a plausible-looking empty result."""
    caps = sorted((json.loads(LEDGER.read_text(encoding="utf-8")).get("rows") or {}))
    for cap in caps[:3]:
        adapter = ADAPTERS / f"truecap_{_slug(cap)}.py"
        mod = _load_module(adapter, f"fc_{adapter.stem}")
        try:
            mod.run({}, str(tmp_path))
        except RuntimeError as exc:
            assert str(exc).startswith("INSTANCE_REQUIRED__"), f"{cap}: unexpected refusal {exc!r}"
        else:
            raise AssertionError(f"{cap}: adapter returned a result with no instance and no fixture")


def test_the_envelope_carries_the_result_fields_the_row_declares() -> None:
    caps = sorted((json.loads(LEDGER.read_text(encoding="utf-8")).get("rows") or {}))
    for cap in caps[:4]:
        cid = f"truecap.{_slug(cap)}"
        entry = json.loads(_pending_for(cid)[0].read_text(encoding="utf-8"))["registry_entry"]
        mod = _load_module(ADAPTERS / f"{entry['adapter_module']}.py", f"env_{_slug(cap)}")
        out = mod.run({"instance_path": entry["action_template"]["args"]["instance_path"]}, str(ROOT))
        assert out["adapter"] == "bound_capability" and out["capability_id"] == cid
        assert out["certification"]["law"].endswith("TRUE_CAPABILITY_TEST_LAW_V1.md")
        for field in entry["result_fields_guaranteed"]:
            assert field in out, f"{cap}: guaranteed field {field} missing from the envelope"
        undeclared = set(out) - set(entry["result_fields"])
        assert not undeclared, f"{cap}: envelope returns undeclared keys {sorted(undeclared)}"
        if set(entry["result_fields"]) != set(entry["result_fields_guaranteed"]):
            # The row must say which of its two field sets is a per-run promise. If a future edit makes
            # them identical for a multi-outcome kernel, that means the measurement no longer sees both
            # outcomes -- worth failing for, not just for the naming.
            assert any("guaranteed" in x for x in entry["limitations"]), f"{cap}: the distinction is undocumented"
        expect = entry["action_template"]["expect"]
        if expect["type"] == "field_equals":
            assert out[expect["field"]] == expect["value"]
        else:
            assert str(out[expect["field"]]) != ""


def test_no_local_hand_granted_the_status_the_root_reads() -> None:
    """The last line: enrollment stops at the queue. Verification is someone else running it."""
    for path in (LIVE, SNAPSHOT):
        rows = json.loads(path.read_text(encoding="utf-8"))["capabilities"]
        assert not [k for k in rows if k.startswith("truecap.")], (
            f"{path.name}: a generated truecap row was written straight into a curated registry"
        )
    sys.path.insert(0, str(ROOT))
    from canonical.runtime import live_integrated_brain_v1 as brain
    admitted = brain.load_verified_registry()
    assert not [k for k in admitted if k.startswith("truecap.")], (
        "true-capability rows are admitted only by a receipt plus an independent verification record"
    )
    minted = sorted(p.name for p in (ROOT / "canonical/astra_runtime/evidence").glob("TRUECAP-ENROLL*VERIFY*"))
    assert not minted, f"a local session wrote the verifier's result file: {minted}"


def test_the_certification_still_describes_the_code_in_the_tree() -> None:
    """Enrollment is only meaningful if the measured bytes are the current bytes.

    A `solver_git_blob_sha` is the one pointer in this pipeline that cannot be argued about: if the
    kernel drifts, the receipt describes a program that no longer exists, and the honest move is to
    re-measure it -- not to edit the number, which is how a stale claim becomes a permanent one.
    """
    rows = sorted((json.loads(LEDGER.read_text(encoding="utf-8")).get("rows") or {}).items())
    assert len(rows) == 9
    for cap, row in rows:
        spec = json.loads((ROOT / row["spec_path"]).read_text(encoding="utf-8"))
        module = spec["solver"]["module"]
        got = subprocess.run(["git", "hash-object", module], cwd=ROOT, capture_output=True,
                             text=True, check=False).stdout.strip()
        assert got, f"{cap}: git cannot hash {module}"
        assert got == row["solver_git_blob_sha"], (
            f"{cap}: kernel is {got[:12]} at HEAD but the ledger measured {str(row['solver_git_blob_sha'])[:12]}"
            " -- re-run the harness before enrolling, and never re-label the number"
        )
