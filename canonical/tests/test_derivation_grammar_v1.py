"""What the generated space must not be allowed to claim.

Three of the tests below exist because the measurement was already wrong in that exact way on
2026-11-04, and each was found by running it rather than by reading it:

  * `countdistinct|pathlist|raw` "bound" a 396-record field at 100% by computing on 47 records
    and being silently skipped on the other 349. Agreement was counted only where a value came
    out. Coverage is now a precondition, not a tie-breaker.
  * the same audit applied to the previous layer: **32 of its 66 "attributed" fields had their
    winning derivation computing on under 90% of their records**, the worst at 2.5%. Its
    headline 98.86% held-out accuracy was measured on the subset that happened to work.
  * `git_blob_sha` was "proven nondeterministic" -- a field that demonstrably is a blob id. The
    collision was five action intents quoting one path at five commits, none of which the
    receipt names. The verdict is now `INPUTS_NOT_RECORDED`: the record is under-specified.

A fourth class of error is pinned too: a verdict about this instrument (`NOT_FOUND_IN_
GENERATED_SPACE`) must never be reported as a fact about the data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import derivation_grammar_v1 as gram  # noqa: E402
from canonical.tools import derivation_inference_v1 as base  # noqa: E402


# --------------------------------------------------------------------------- fixtures
def _site(doc, path, field, value, record=None):
    rec = record if record is not None else {"path": path, field: value}
    return base.Site(doc, f"/{field}", field, rec, value, base.value_class(value))


@pytest.fixture()
def tree(tmp_path):
    return base.Tree(root=tmp_path)


def _sized(tmp_path, n=12):
    """n files whose sizes are distinct and deliberately NOT monotone.

    Monotone sizes trip `EVIDENCE_OF_WRITE_TIME_CHOICE` (a field that increases with order
    looks like a counter), which is correct behaviour and would stop the search before the
    recipe ever got tried -- so the fixture avoids it on purpose.
    """
    sites = []
    for i in range(n):
        size = (i * 37) % 97 + 1
        name = f"f{i}.txt"
        (tmp_path / name).write_bytes(b"x" * size)
        sites.append(_site(f"d{i}.json", name, "nbytes", size))
    return sites


# --------------------------------------------------------------------------- the space
def test_the_space_is_generated_and_larger_than_the_list_it_replaces():
    """A search over a list somebody typed has a ceiling that is their imagination."""
    space = gram.space_size()
    assert space["cross_product"] == (len(gram.ARRANGEABLE) * len(gram.PRES)
                                      * len(gram.TRANSFORMS)
                                      + (len(gram.ELEMENTS) - len(gram.ARRANGEABLE))
                                      * len(gram.TRANSFORMS))
    assert space["generated"] > space["hand_written_in_previous_layer"] * 5
    assert len({r for r in gram.recipes()}) == space["generated"], "duplicate recipes generated"


def test_arranging_a_single_element_is_not_a_second_hypothesis():
    """`len|file|sortnl` computes exactly what `len|file|raw` computes. Duplicates in the
    space waste search and let a different NAME win a field and be credited in the yields."""
    got = gram.recipes()
    assert "len|file|sortnl" not in got
    assert "len|pathlist|sortnl" in got
    assert gram.space_size()["duplicates_removed"] == 36


def test_the_generated_space_is_honestly_smaller_than_the_old_one_in_one_respect():
    """It cannot select `the commit that last wrote this record`. Saying so is the point."""
    missing = [k for k, v in gram.PREVIOUS_COVERAGE.items() if v is None]
    assert "git_blob_at_record_commit" in missing
    assert sum(1 for v in gram.PREVIOUS_COVERAGE.values() if v) == 6


def test_every_recipe_is_a_string_that_rebuilds_the_same_derivation(tmp_path):
    """A learning that cannot be written down cannot outlive the process that had it."""
    (tmp_path / "a.txt").write_bytes(b"hello")
    site = _site("d.json", "a.txt", "sig", base.git_blob_sha(b"hello"), {"path": "a.txt"})
    tree = base.Tree(root=tmp_path)
    for recipe in gram.recipes():
        assert isinstance(recipe, str)
        before = gram.derive(recipe, site, tree)
        restored = json.loads(json.dumps(recipe))
        assert gram.derive(restored, site, tree) == before


def test_a_recipe_from_a_fresh_process_derives_the_same_value(tmp_path):
    """The loop rebuilds predicates from JSON in another process, so this has to hold."""
    import subprocess
    (tmp_path / "a.txt").write_bytes(b"seven!!")
    tree = base.Tree(root=tmp_path)
    site = _site("d.json", "a.txt", "n", 7)
    got = gram.derive("len|file|raw", site, tree)
    out = subprocess.check_output(
        [sys.executable, "-c",
         "import sys;sys.path.insert(0,%r);"
         "from canonical.tools import derivation_grammar_v1 as g, derivation_inference_v1 as b;"
         "from pathlib import Path;"
         "s=b.Site('d.json','/n','n',{'path':'a.txt'},7,'int');"
         "print(g.derive('len|file|raw', s, b.Tree(root=Path(%r))))"
         % (str(ROOT), str(tmp_path))], text=True).strip()
    assert got == 7 and out == "7"


# --------------------------------------------------------------------------- coverage
def test_a_recipe_that_only_computes_for_a_tenth_of_the_field_cannot_bind(tmp_path):
    """The 47-of-396 bug. A silent skip is not agreement."""
    sites = []
    for i in range(40):
        name = f"g{i}.txt"
        if i < 4:
            (tmp_path / name).write_bytes(b"x" * (i + 1))
            sites.append(_site("d.json", name, "nbytes", (i * 37) % 97 + 1))
        else:
            # no file on disk: the recipe cannot compute here, and must not be credited.
            # Values are deliberately non-monotone so the write-time heuristics stay quiet and
            # the only thing that can reject the recipe is coverage.
            sites.append(_site("d.json", name, "nbytes", (i * 37) % 97 + 1))
    tree = base.Tree(root=tmp_path)
    got = gram.search_field("nbytes|int", sites, tree, gram.load_yields("/nonexistent.json"))
    assert got["outcome"] == "NOT_LEARNED", got
    reasons = {r.get("reason") for r in got.get("rejected_on_holdout", [])}
    # specifically coverage, not "it happened not to generalise". Dropping the coverage check
    # still leaves the holdout check rejecting this, so an `or` here would let the bug live.
    assert "LOW_COVERAGE" in reasons, reasons


def test_coverage_is_a_precondition_in_the_previous_layer_too():
    """The audit that mattered: 32 of 66 fields were attributed on a subset."""
    assert base.COVERAGE_MIN >= 0.9
    sites = []
    for i in range(20):
        name = f"h{i}.txt"
        if i < 2:
            (Path("/tmp") / f"cov_{name}").write_bytes(b"abc")
        sites.append(base.Site("d.json", f"/nbytes", "nbytes",
                               {"path": f"missing_{name}", "nbytes": 3} if i > 1 else
                               {"path": f"missing_{name}", "nbytes": 3}, 3, "int"))
    tree = base.Tree(root=Path("/tmp"))
    fields = base.attribute(sites, tree)
    got = fields["nbytes|int"]
    assert got["state"] in {"LOW_COVERAGE", "INSUFFICIENT_SUPPORT", "UNEXPLAINED"}, got
    assert got["state"] != "ATTRIBUTED"


def test_a_constant_predictor_is_rejected_even_when_it_is_almost_always_right(tmp_path):
    """A recipe that returns one value for every record explains nothing about any of them.

    The fixture matters. If every recorded value were 1, the `UNDECIDABLE_FROM_CORPUS` check
    would fire first and this guard would never be reached -- a test that passes for the wrong
    reason. So the field is *almost* constant: 11 ones and a two. That defeats the constancy
    check, defeats the position and counter checks, and leaves a constant-output recipe
    matching 91.7% of records -- above the binding threshold, and pure coincidence.
    """
    sites = []
    for i in range(12):
        name = f"k{i}.txt"
        (tmp_path / name).write_bytes(b"zz")
        sites.append(_site("d.json", name, "ones", 2 if i == 0 else 1))
    tree = base.Tree(root=tmp_path)

    facts = gram.probe_values(sites, tree)
    assert not facts["all_equal"], "the constancy check would decide this, not the guard"
    assert not facts["equals_own_position"] and not facts["strictly_increasing"]

    assert gram._is_constant_predictor("count|pathlist|raw", sites, tree) is True
    got = gram.search_field("ones|int", sites, tree, gram.load_yields("/nonexistent.json"))
    assert got["outcome"] == "NOT_LEARNED", got
    reasons = {r.get("reason") for r in got.get("rejected_on_holdout", [])}
    assert "CONSTANT_PREDICTOR" in reasons, reasons


# --------------------------------------------------------------------------- falsification
def test_a_recipe_that_wins_the_fit_and_loses_the_holdout_is_rejected(tmp_path, monkeypatch):
    """Without this the holdout is decoration."""
    sites = _sized(tmp_path, n=12)
    tree = base.Tree(root=tmp_path)

    real = gram._agreement
    calls = {"len|file|raw": 0}

    def rigged(recipe, group, t):
        ok, computed, total = real(recipe, group, t)
        if recipe == "len|file|raw":
            calls[recipe] += 1
            if calls[recipe] > 1:
                return 0, computed, total            # perfect on the fit, wrong when held out
        return ok, computed, total

    monkeypatch.setattr(gram, "_agreement", rigged)
    got = gram.search_field("nbytes|int", sites, tree, gram.load_yields("/nonexistent.json"))
    attempted = [r for r in got.get("rejected_on_holdout", []) if r.get("recipe") == "len|file|raw"]
    assert attempted, "the rigged recipe was never held out"
    assert got["outcome"] in {"NOT_LEARNED", "LEARNED"}
    if got["outcome"] == "LEARNED":
        assert got["recipe"] != "len|file|raw"


# --------------------------------------------------------------------------- epistemics
def test_a_fact_about_the_instrument_is_never_reported_as_a_fact_about_the_data():
    assert gram.tier_of("NOT_FOUND_IN_GENERATED_SPACE") == "FACT_ABOUT_INSTRUMENT"
    assert gram.tier_of("INPUTS_NOT_RECORDED") == "FACT_ABOUT_DATA"
    assert gram.tier_of("UNDECIDABLE_FROM_CORPUS") == "FACT_ABOUT_DATA"
    assert gram.tier_of("EVIDENCE_OF_WRITE_TIME_CHOICE") == "FACT_ABOUT_DATA"


def test_an_under_specified_record_is_not_called_nondeterministic():
    """The field is a blob id; the receipts just do not name their commit."""
    facts = {"records": 10, "identical_inputs_with_different_values": 3, "all_equal": False}
    verdict = gram.classify_non_derivable(facts, searched=True)
    assert verdict == "INPUTS_NOT_RECORDED"
    assert "under-specified" in gram.TIERS[verdict][1]
    assert "proof" in gram.TIERS[verdict][1]


def test_a_constant_field_is_undecidable_rather_than_explained():
    facts = {"records": 10, "all_equal": True, "identical_inputs_with_different_values": 0}
    assert gram.classify_non_derivable(facts, searched=True) == "UNDECIDABLE_FROM_CORPUS"


# --------------------------------------------------------------------------- learning order
def test_what_has_paid_off_is_tried_first_next_time():
    """Behaviour changes between runs; the unit reported is recipes tried, never a solve rate."""
    yields = {"primitives": {}, "runs": 0}
    recipes = gram.recipes("hex64")
    assert gram.order_recipes(recipes, yields)[0] == sorted(recipes)[0]
    gram.credit(yields, "sha256|valuelist|sortnl")
    assert gram.order_recipes(recipes, yields)[0] == "sha256|valuelist|sortnl"
    assert yields["primitives"]["pre:sortnl"]["confirmed"] == 1


def test_yields_persist_across_processes(tmp_path):
    path = tmp_path / "Y.json"
    yields = gram.load_yields(path)
    gram.credit(yields, "sha1|file|raw")
    gram.save_yields(yields, path)
    again = gram.load_yields(path)
    assert again["primitives"]["transform:sha1"]["confirmed"] == 1


# --------------------------------------------------------------------------- accounting
def test_the_accounting_closes(tmp_path, monkeypatch):
    """Every field is in exactly one bucket, or the report is hiding something."""
    (tmp_path / "a.txt").write_bytes(b"abc")
    doc = tmp_path / "d.json"
    doc.write_text(json.dumps({"files": [{"path": "a.txt", "nbytes": 3},
                                         {"path": "a.txt", "nbytes": 3},
                                         {"path": "a.txt", "nbytes": 3}]}), encoding="utf-8")
    monkeypatch.setattr(gram.base, "ROOT", tmp_path)
    report = gram.measure(search=True, limit_files=1)
    b = report["after"]["breakdown"]
    assert b["closes"] is True, b
    assert b["accounted"] == b["total_fields"]


def test_the_report_claims_no_capability():
    globals_ = Path(ROOT / "canonical/tools/derivation_grammar_v1.py").read_text()
    assert "NO_CAPABILITY_CREDIT_A_RECIPE_IS_NOT_A_CAPABILITY" in globals_
