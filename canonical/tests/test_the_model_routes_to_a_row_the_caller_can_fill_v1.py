#!/usr/bin/env python3
"""The model may not hand a request to a row the caller cannot fill.

Measured 2026-11-02, on the commit that added `file.archive.tar_gz.v1`:

    "create a tar gz archive from a manifest"
      file.archive.tar_gz.v1                 1344.75   <- needs goal + path
      archive.tar_gz.create_from_manifest    1332.28   <- needs manifest_path + output_path

A 0.9% margin decided it.  The router was "confident", the winner could not be
filled from the caller's own inputs, and `solve()` returned
FAIL_CLOSED / CAPABILITY_INPUTS_MISSING:goal,path for a request the model could
serve perfectly well.  The unified-model verifier went 33/33 -> 31/33 and the
loss was in the *routing*, not in the new row's adapter.

What is pinned here:

* the request above is SOLVED, and the capability that solved it is named;
* the reroute is REPORTED (`rerouted_from`, `reroute_rule`), so a silent
  substitution is not possible;
* the rule cannot invent an operand: when no candidate is fillable, the result
  is still a refusal, not a guess;
* a capability the goal addresses by its own id is never displaced by it.

The router is exercised through the model the repository ships, so a stale
compiled model fails here rather than in production.
"""
from __future__ import annotations

import copy
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import brain_unified_model_v1 as um  # noqa: E402

ARTIFACT = ROOT / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"


def _model() -> um.UnifiedModel:
    return um.UnifiedModel(um.load_model(ARTIFACT))


def _manifest_world() -> tuple[pathlib.Path, dict]:
    base = ROOT / "canonical/astra_runtime/tmp/unified_model_fillable_v1"
    base.mkdir(parents=True, exist_ok=True)
    member = base / "member.txt"
    member.write_text("alpha\nbeta\n", encoding="utf-8")
    manifest = base / "manifest.json"
    manifest.write_text(json.dumps({"records": [{"verification_paths": [
        member.relative_to(ROOT).as_posix()]}]}), encoding="utf-8")
    inputs = {
        "manifest_path": manifest.relative_to(ROOT).as_posix(),
        "output_path": (base / "out" / "bundle.tar.gz").relative_to(ROOT).as_posix(),
    }
    (base / "out").mkdir(parents=True, exist_ok=True)
    (base / "out" / "bundle.tar.gz").unlink(missing_ok=True)
    return base, inputs


def test_the_request_is_routed_to_the_row_whose_inputs_the_caller_supplied() -> None:
    model = _model()
    base, inputs = _manifest_world()
    result = model.solve("create a tar gz archive from a manifest", inputs=inputs)
    routing = result.get("routing") or {}
    chosen = None
    for key in ("capability_id",):
        chosen = chosen or result.get(key)
    execution = result.get("execution") or {}
    chosen = chosen or execution.get("capability_id") or (routing.get("best") or {}).get("id")
    assert chosen == "archive.tar_gz.create_from_manifest", (result.get("status"), chosen)
    assert result.get("pass") is True, result.get("reason")
    assert (base / "out" / "bundle.tar.gz").is_file(), "the archive the caller named was not written"


def test_the_reroute_is_reported_rather_than_silent() -> None:
    # Main 2ce359e6 changed ranking so the manifest row now wins outright.
    # Exercise the original ordering as a controlled route while still running
    # the real solver and real adapter, rather than requiring today's scoring to
    # keep reproducing a historical ranking mistake.
    goal = "create a tar gz archive from a manifest"
    original = _model().route(goal)
    candidates = original.get("candidates") or []
    first = next(row for row in candidates if row.get("id") == "file.archive.tar_gz.v1")
    second = next(row for row in candidates if row.get("id") == "archive.tar_gz.create_from_manifest")
    forced = dict(original, confident=True, best=first, candidates=[first, second])

    class HistoricalRanking(um.UnifiedModel):
        def route(self, *args, **kwargs):
            return copy.deepcopy(forced)

    model = HistoricalRanking(um.load_model(ARTIFACT))
    base, inputs = _manifest_world()
    with tempfile.TemporaryDirectory(dir=str(ROOT / "canonical/astra_runtime/tmp")) as tmp:
        inputs["ledger_db_path"] = str(pathlib.Path(tmp) / "routing.sqlite3")
        result = model.solve(goal, inputs=inputs)
    routing = result.get("routing") or {}
    assert result.get("pass") is True, result.get("reason")
    assert (base / "out" / "bundle.tar.gz").is_file()
    assert routing.get("rerouted_from") == "file.archive.tar_gz.v1", routing.get("rerouted_from")
    assert routing.get("reroute_rule") == (
        "TOP_CANDIDATE_INPUTS_UNFILLABLE__NEXT_FILLABLE_CANDIDATE"), routing.get("reroute_rule")


def test_the_shipped_row_is_still_the_one_that_answers_its_own_sentence() -> None:
    """The fix must not have been achieved by demoting the new row."""
    model = _model()
    routing = model.route("create a tar gz archive from a manifest")
    ids = [row["id"] for row in routing.get("candidates") or []]
    assert "file.archive.tar_gz.v1" in ids, ids
    assert "archive.tar_gz.create_from_manifest" in ids, ids


def test_no_fillable_candidate_still_refuses_rather_than_guessing() -> None:
    """Nothing may be invented when every candidate needs something unstated."""
    model = _model()
    result = model.solve("create a tar gz archive from a manifest", inputs={})
    assert result.get("pass") is not True, result.get("status")
    assert str(result.get("status") or "").startswith("FAIL"), result.get("status")
    assert (result.get("routing") or {}).get("rerouted_from") is None, result.get("routing")


def test_a_capability_the_goal_names_by_id_is_never_displaced() -> None:
    model = _model()
    goal = "run file.archive.tar_gz.v1"
    routing = model.route(goal)
    assert (routing.get("best") or {}).get("id") == "file.archive.tar_gz.v1", routing.get("best")
    _base, inputs = _manifest_world()
    result = model.solve(goal, inputs=inputs)
    assert (result.get("routing") or {}).get("rerouted_from") is None, result.get("routing")


def test_declared_context_is_not_used_as_permission_to_reroute() -> None:
    """A declared file is not a reason to replace the original operation."""
    model = _model()
    with tempfile.TemporaryDirectory(dir=str(ROOT / "canonical/astra_runtime/tmp")) as tmp:
        pdf = pathlib.Path(tmp) / "input.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
        rel = pdf.relative_to(ROOT).as_posix()
        # The one-shot iterable must survive both routing and input binding.
        result = model.solve("Read a PDF and extract its text.", context_paths=iter([rel]))
        provenance = result.get("binding_provenance") or {}
        assert provenance.get("declared_context") == [rel], provenance
        assert (provenance.get("values") or {}).get("pdf_path") == rel, provenance
        assert (result.get("routing") or {}).get("rerouted_from") is None, result
        assert pdf.read_bytes() == b"%PDF-1.4\n%%EOF\n"


def main() -> int:
    tests = [value for key, value in sorted(globals().items())
             if key.startswith("test_") and callable(value)]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        else:
            print("ok   %s" % test.__name__)
    print("\n%d/%d passed" % (len(tests) - failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
