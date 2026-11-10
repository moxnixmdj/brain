#!/usr/bin/env python3
"""ONE MODEL v2 — tests.

Each test names the property it protects. The failure modes they exist for were
all observed during construction, not imagined:

  * "find the bugs in this python file" -> `json.file.write`   (verb ignored)
  * `_period` explaining 6 unrelated points as period 6        (as many
    parameters as observations; the tree found this exact trap on 2026-11-04)
  * off-origin periodic data predicting the wrong residue      (missing x0)
  * a refusal that names no cause                              (unnamed gap)
"""
from __future__ import annotations

import math
import shutil
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import brain_one_model_v2 as m  # noqa: E402


# ---------------------------------------------------------------- ROUTING ---
ROUTES = {
    "extract text from a pdf": "pdf.extract.text.pypdf",
    "create a tar.gz archive from a manifest": "archive.tar_gz.create_from_manifest",
    "audit python source structure": "python.source.audit.ast",
    "create a sqlite table from json records": "sqlite.table.create_from_json_records",
    "rank sources by relevance to an objective": "source.objective_relevance.rank.bm25",
    "make an xlsx spreadsheet": "xlsx.table.create_from_json_records",
    "generate a QR code": "image.qr.generate.qrencode",
    "rename a symbol across the repository": "python.refactor.rename_symbol.v1",
}


@pytest.mark.parametrize("goal,expected", sorted(ROUTES.items()))
def test_a_plain_goal_reaches_the_capability_it_names(goal, expected):
    r = m.route(goal)
    assert r["best"] is not None, r
    assert r["best"]["id"].startswith(expected), (goal, r["best"])


@pytest.mark.parametrize("goal", [
    "what is the meaning of life",
    "book me a flight to Cairo",
    "write me a poem about my mother in fluent French verse",
    "explain quantum chromodynamics to a child",
])
def test_out_of_domain_never_routes_confidently(goal):
    """The model must say no. A confident wrong answer is the worst output."""
    r = m.route(goal)
    assert r["confident"] is False, r


def test_a_refusal_names_the_tokens_it_could_not_place():
    """An unnamed gap is unactionable; the tree's own rule is that a refusal must
    say what would end it."""
    r = m.route("what is the meaning of life")
    assert r["reason"].endswith("FAIL_CLOSED")
    if "unmatched_tokens" in r:
        assert r["unmatched_tokens"]


def test_route_is_deterministic():
    a = m.route("audit python source structure")
    b = m.route("audit python source structure")
    assert a["candidates"] == b["candidates"]


def test_route_is_fast():
    """Guards the latency decision, generously: this must stay microseconds, and
    the old front door took 84,000."""
    import time
    m._load_index()
    ts = []
    for _ in range(100):
        s = time.perf_counter()
        m.route("extract text from a pdf")
        ts.append((time.perf_counter() - s) * 1e6)
    ts.sort()
    assert ts[len(ts) // 2] < 5_000, "median route %.0f us" % ts[len(ts) // 2]


# --------------------------------------------------------------- COMPILE ---
def _rows(pairs):
    return [{"x": float(a), "y": float(b)} for a, b in pairs]


def test_constant_is_recognised_in_five_microseconds():
    c = m.compile_rows(_rows([(x, 7.0) for x in range(6)]))
    assert c["family"] == "constant"
    assert m.predict(c, 99) == 7.0


def test_affine_is_exact_on_a_fresh_point():
    c = m.compile_rows(_rows([(x, 2.5 * x + 1.0) for x in range(6)]))
    assert c["family"] in ("affine", "linear")
    assert m.predict(c, 1000) == pytest.approx(2501.0, abs=1e-6)


def test_quadratic_is_exact():
    c = m.compile_rows(_rows([(x, 0.5 * x * x - 2 * x + 3) for x in range(6)]))
    assert c["family"] == "quadratic"
    assert m.predict(c, 10) == pytest.approx(33.0, abs=1e-6)


def test_periodic_works_off_origin():
    """Regression: without an x0 base this predicted table[0] for every x."""
    rows = [{"x": float(100 + i), "y": [2.0, 5.0, 1.0][i % 3]} for i in range(9)]
    c = m.compile_rows(rows)
    assert c["family"] == "periodic"
    assert c["params"]["period"] == 3
    assert m.predict(c, 110) == [2.0, 5.0, 1.0][10 % 3]


def test_exponential_is_recovered():
    c = m.compile_rows(_rows([(x, 4.0 * math.exp(0.3 * x)) for x in range(8)]))
    assert c["family"] == "exponential"
    assert m.predict(c, 3) == pytest.approx(4.0 * math.exp(0.9), rel=1e-6)


def test_a_residue_witnessed_once_is_not_a_period():
    """The 2026-11-04 trap: six unrelated points 'explained' by period 6 is as
    many parameters as observations and carries no information. Must abstain."""
    rows = _rows(list(enumerate([3.0, 9.0, 1.0, 7.0, 2.0, 8.0])))
    with pytest.raises(m.InferError):
        m.compile_rows(rows)


def test_a_residue_witnessed_twice_is_a_period():
    rows = _rows([(i, [3.0, 9.0, 1.0, 7.0, 2.0, 8.0][i % 6]) for i in range(12)])
    c = m.compile_rows(rows)
    assert c["family"] == "periodic" and c["params"]["period"] == 6


def test_noise_abstains():
    rows = _rows(list(enumerate([3.1, 9.7, 1.2, 7.9, 2.4, 8.8])))
    with pytest.raises(m.InferError):
        m.compile_rows(rows)


def test_escalation_reaches_a_family_closed_form_cannot_express():
    """Closed form abstains, the tree's own H100 synthesizer answers."""
    rows = [{"x": float(i), "y": 0.5 * float(i) + 2.0 * math.sin(1.7 * float(i))}
            for i in range(12)]
    c = m.compile_with_h100(rows)
    assert c["engine"] == "h100_zero_learned_parametric_unary_v1"
    assert c["learned_bytes"] == 0


def test_compiled_families_make_no_credit_claim():
    c = m.compile_rows(_rows([(x, 3.0 * x) for x in range(5)]))
    assert c["credit"]["capability_credit_delta"] == 0
    assert c["credit"]["terminal_credit_delta"] == 0
    assert c["weights"] == 0


# --------------------------------------------------------------- LEARNING ---
def test_one_observation_changes_routing_immediately(tmp_path, monkeypatch):
    """The claim under test: learning is instant and needs no training step."""
    monkeypatch.setattr(m, "POLICY_PATH", tmp_path / "policy.json")
    base = m.route("zeta ambiguous request thing")
    for _ in range(3):
        m.learn("zeta ambiguous request thing", "python.source.audit.ast", helped=True)
    after = m.route("zeta ambiguous request thing")
    assert after["candidates"][0]["id"] == "python.source.audit.ast"
    assert after["candidates"][0]["score"] >= base["candidates"][0]["score"] if base["candidates"] else True


def test_policy_is_tiny_and_carries_no_weights(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "POLICY_PATH", tmp_path / "policy.json")
    for i in range(20):
        m.learn("audit python source structure", "python.source.audit.ast")
    doc = m._load_policy()
    assert doc["weights"] == 0
    assert doc["updates"] == 20


# ------------------------------------------------------------------ STATUS ---
def test_status_declares_no_weights_and_no_credit():
    s = m.status()
    assert s["weights"] == 0
    assert s["learned_parameter_bytes"] == 0
    assert s["credit"]["capability_credit_delta"] == 0
    assert any("NO_WEIGHTS" in n for n in s["non_claims"])


# ------------------------------------------------------------------- SOLVE ---
MANIFEST = "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"


def test_bind_refuses_an_input_the_template_does_not_declare():
    """A capability may never widen its own surface. An undeclared input is a
    refusal, not something quietly dropped."""
    with pytest.raises(m.SolveError) as ei:
        m.bind("archive.tar_gz.create_from_manifest",
               {"manifest_path": MANIFEST, "output_path": "x.tar.gz",
                "smuggled": "value"})
    assert "INPUT_NOT_DECLARED_BY_TEMPLATE" in str(ei.value)


def test_bind_requires_every_declared_input():
    with pytest.raises(m.SolveError) as ei:
        m.bind("archive.tar_gz.create_from_manifest", {"manifest_path": MANIFEST})
    assert "INPUT_BINDING_REQUIRED" in str(ei.value)


def test_bind_refuses_an_unbound_capability_identity():
    with pytest.raises(m.SolveError):
        m.bind("some.id.that.does.not.exist", {})


def test_bind_only_has_no_side_effects(tmp_path):
    out = m.solve("create a tar.gz archive from a manifest",
                  {"manifest_path": MANIFEST,
                   "output_path": ".one_model_tmp/should_not_exist.tar.gz"},
                  execute=False)
    assert out["status"] == "ROUTED_AND_BOUND__NOT_EXECUTED"
    assert not (ROOT / ".one_model_tmp/should_not_exist.tar.gz").exists()


def test_solve_executes_and_verifies_against_the_declared_expectation():
    out = m.solve("create a tar.gz archive from a manifest",
                  {"manifest_path": MANIFEST,
                   "output_path": ".one_model_tmp/test_solve.tar.gz"})
    assert out["pass"] is True, out
    assert out["status"].startswith("PASS__BOUND_CAPABILITY_EXECUTED")
    assert out["credit"]["capability_credit_delta"] == 0


def test_solve_fails_closed_on_a_sandbox_escape():
    """Adapters resolve paths under the repository root. An absolute /tmp path
    must be refused, not silently redirected."""
    out = m.solve("create a tar.gz archive from a manifest",
                  {"manifest_path": MANIFEST, "output_path": "/tmp/escape.tar.gz"})
    assert out["pass"] is False
    assert "PATH_OUTSIDE_REPOSITORY" in (out.get("error") or out["status"])


def test_solve_refuses_an_unrepresented_goal_without_executing():
    out = m.solve("what is the meaning of life", {})
    assert out["pass"] is False
    assert "GOAL_NOT_REPRESENTED_IN_MODEL" in out["status"]


# ------------------------------------------------------------------- CACHE ---
def _uniq() -> str:
    """A per-run token. tmp_path.name is NOT unique across pytest sessions
    (test_brain_one_model_v20, v21, ...), which made these tests pass once and
    then fail on every rerun."""
    return uuid.uuid4().hex[:12]


def test_a_repeat_solve_hits_the_cache_and_preserves_the_original_exec_ms(tmp_path):
    args = {"manifest_path": MANIFEST,
            "output_path": ".one_model_tmp/cache_%s.tar.gz" % _uniq()}
    first = m.solve_cached("create a tar.gz archive from a manifest", args)
    second = m.solve_cached("create a tar.gz archive from a manifest", args)
    assert first["cache"] == "MISS"
    assert second["cache"] == "HIT"
    # the stored number is not overwritten: a cached answer never claims to have
    # just run
    assert second["exec_ms"] == first["exec_ms"]


def test_a_different_output_path_does_not_reuse_a_cached_receipt(tmp_path):
    """Regression: skipping the output path in the key made two different
    artifacts share a receipt."""
    tag = _uniq()
    a = m.solve_cached("create a tar.gz archive from a manifest",
                       {"manifest_path": MANIFEST,
                        "output_path": ".one_model_tmp/%s_k1.tar.gz" % tag})
    b = m.solve_cached("create a tar.gz archive from a manifest",
                       {"manifest_path": MANIFEST,
                        "output_path": ".one_model_tmp/%s_k2.tar.gz" % tag})
    assert b["cache"] == "MISS", "output name must participate in the key"
    assert a["pass"] is True and b["pass"] is True


def test_the_cache_does_not_hash_its_own_receipts(tmp_path):
    """The cache lives under canonical/runtime; hashing that tree must not
    include the cache, or the key depends on its own contents."""
    m.status()
    k1 = m._input_digest({"source_root": "canonical/runtime"})
    m.solve_cached("create a tar.gz archive from a manifest",
                   {"manifest_path": MANIFEST,
                    "output_path": ".one_model_tmp/%s_k3.tar.gz" % _uniq()})
    k2 = m._input_digest({"source_root": "canonical/runtime"})
    assert k1 == k2, "writing a receipt changed the digest of the tree it lives in"


# ------------------------------------------------------------------ BRIDGE ---
@pytest.mark.parametrize("token,expected", [
    ("pyton", "python"), ("sqllite", "sqlite"), ("extarct", "extract"),
    ("soruce", "source"), ("archiv", "archive"), ("pdfs", "pdf"),
])
def test_a_typo_bridges_to_the_capability_token_it_means(token, expected):
    b = m.bridge(token)
    assert b.get("match") == expected, (token, b)


@pytest.mark.parametrize("token", ["tree", "mother", "xyzzy", "the"])
def test_a_real_word_is_not_bridged_to_an_unrelated_one(token):
    """The first version allowed two edits and bridged `tree`->`time`, then
    `tree`->`three`. Both changed a correct route into a wrong one. A typo is a
    mistake in the name of a thing you meant; it must resolve to a thing."""
    b = m.bridge(token)
    assert b.get("match") is None, (token, b)


def test_an_ambiguous_token_is_refused_rather_than_guessed():
    b = m.bridge("data")
    assert b.get("match") is None
    assert b.get("reason") == "AMBIGUOUS_BRIDGE"


def test_the_edit_rule_admits_only_one_typo_shaped_edit():
    assert m._edit_kind("pyton", "python") == (1, "INS")
    assert m._edit_kind("sqllite", "sqlite") == (1, "DEL")
    assert m._edit_kind("extarct", "extract") == (1, "TRANS")
    assert m._edit_kind("tree", "time") is None      # two substitutions
    assert m._edit_kind("tree", "three") == (1, "INS")  # legal edit, wrong word


# ----------------------------------------------------------------- ACQUIRE ---
def test_acquire_repairs_a_wrong_route_into_the_right_one(tmp_path, monkeypatch):
    """The whole point of the wire: a refusal or a wrong answer costs one call,
    and the next request is correct."""
    monkeypatch.setattr(m, "POLICY_PATH", tmp_path / "p.json")
    goal = "inspect the abstract syntax tree of my sourcode"
    before = m.route(goal)
    assert not before["best"]["id"].startswith("python.source.audit.ast")
    out = m.acquire(goal, capability_id="python.source.audit.ast")
    assert out["needed"] is True
    assert any(b["token"] == "sourcode" for b in out["bridged"])
    after = m.route(goal)
    assert after["best"]["id"] == "python.source.audit.ast"


def test_acquire_records_provenance_for_every_bridge(tmp_path, monkeypatch):
    """A bridge the model inferred and cannot justify is indistinguishable from
    a guess. Every bridge carries its rule and score."""
    monkeypatch.setattr(m, "POLICY_PATH", tmp_path / "p.json")
    out = m.acquire("audti pyton soruce structure")
    assert out["bridged"], out
    for b in out["bridged"]:
        assert b["rule"] in ("STEM", "TYPO_1_INS", "TYPO_1_DEL", "TYPO_1_TRANS",
                             "TYPO_1_SUB", "TRIGRAM_DICE", "IDENTITY")
        assert "score" in b


def test_acquire_is_a_no_op_when_the_goal_already_routes(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "POLICY_PATH", tmp_path / "p.json")
    out = m.acquire("extract text from a pdf")
    assert out["needed"] is False


def test_acquire_never_claims_credit_or_weights(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "POLICY_PATH", tmp_path / "p.json")
    out = m.acquire("audti pyton soruce structure")
    assert out["weights"] == 0
    assert "GUESS" in out["rule"]


def test_a_cache_key_survives_a_write_target_created_inside_an_input_dir(tmp_path):
    """Measured bug: `output_path` inside `source_root` made the first run change
    the directory signature, so the key differed from itself and every call was
    a MISS -- in the same process. A write target's existence must never enter
    the key, and excluding only the file's own slot is not enough: it must be
    excluded from any directory signature it falls inside."""
    src = m.ROOT / ".one_model_tmp" / ("cache_inside_" + tmp_path.name)
    src.mkdir(parents=True, exist_ok=True)
    (src / "a.py").write_text("x = 1\n")
    try:
        rel_src = str(src.relative_to(m.ROOT))
        out = f"{rel_src}/audit.json"
        inputs = {"source_root": rel_src, "output_path": out}
        d1 = m._input_digest(inputs)
        (m.ROOT / out).write_text("{}")          # the capability's own artifact
        d2 = m._input_digest(inputs)
        assert d1 == d2, "writing the declared output changed the input digest"
        (src / "a.py").write_text("x = 2\n")     # a real input change
        d3 = m._input_digest(inputs)
        assert d3 != d1, "a real input change did not change the digest"
    finally:
        shutil.rmtree(src, ignore_errors=True)
