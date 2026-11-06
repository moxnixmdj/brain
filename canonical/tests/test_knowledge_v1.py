"""Does the creature hold its own record, and does holding it change what it will accept?

Paired with the worlds where each claim must fail, per the repo laws. Two kinds of test here and
they are not interchangeable: the refusal tests are SAFETY properties and may block a widening
change; the paraphrase test is a LIMITATION and may never block one.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import knowledge_v1 as knowledge   # noqa: E402
from canonical.tools import knowledge_probe_v1 as probe   # noqa: E402


# ------------------------------------------------------------------- it holds the whole record
def test_every_record_is_either_held_or_named_with_a_reason():
    """`Knows everything` is only meaningful if it can also say what it does not hold. Anything
    silently skipped is invisible ignorance, which is the failure this whole log is about.
    """
    store = knowledge.harvest()
    coverage = store["coverage"]
    assert coverage["represented"] + coverage["unrepresented"] == coverage["evidence_files"]
    # Every record object is either in the store or in the missing list, never both and never neither.
    held = {record["source"] for record in store["records"]}
    missing = {entry["source"] for entry in store["unrepresented"]}
    assert not (held & missing), "a record is both held and reported missing"
    for entry in store["unrepresented"]:
        assert entry["why"], f"{entry['source']} was dropped without a reason"


def test_a_broken_record_is_reported_and_not_silently_dropped():
    """Measured 2026-11-06: with every file in the real corpus parseable, the accounting test could
    not tell "nothing was dropped" from "drops silently" -- a mutant that deleted the report
    survived. So the failure is forced: a corrupt file and a non-object file, in a stand-in corpus.
    """
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as box:
        evidence = Path(box) / "canonical" / "verification"
        evidence.mkdir(parents=True)
        (evidence / "good_v1.json").write_text(json.dumps({"schema": "GOOD", "verified": True}))
        (evidence / "corrupt_v1.json").write_text("{not json at all")
        (evidence / "a_list_v1.json").write_text(json.dumps([1, 2, 3]))
        store = knowledge.harvest(Path(box))
        coverage = store["coverage"]
        assert coverage["evidence_files"] == 3, coverage
        assert coverage["represented"] == 1, coverage
        assert coverage["unrepresented"] == 2, coverage
        reasons = {entry["source"].split("/")[-1]: entry["why"] for entry in store["unrepresented"]}
        assert "corrupt_v1.json" in reasons and reasons["corrupt_v1.json"], reasons
        assert "a_list_v1.json" in reasons and "list" in reasons["a_list_v1.json"], reasons


def test_it_holds_the_logs_and_not_only_their_tables():
    """Measured 2026-11-06: ingesting only verdict rows left it unable to answer `xor3 parity
    separability`, though both logs discuss it. The prose is part of the record.
    """
    store = knowledge.harvest()
    assert store["coverage"]["log_claims"] >= 60, store["coverage"]
    assert store["coverage"]["log_sections"] >= 100, (
        f"only {store['coverage']['log_sections']} log paragraphs held: the prose is missing")
    assert any(item["kind"] == "log_text" for item in store["sections"])


# ------------------------------------------------------------------------ answering and silence
def test_it_answers_about_its_own_record_with_provenance():
    store = knowledge.harvest()
    answer = knowledge.ask(store, "what did log 19 conclude about program synthesis")
    assert answer["status"] == "known", answer
    assert "Log 19" in answer["provenance"], answer["provenance"]
    assert answer["answer"] and len(answer["answer"]) > 20


def test_it_says_unknown_rather_than_guessing():
    """The paired failure: a topic the record has never contained must come back `unknown`.
    An assistant that answers confidently from an unrelated record is worse than one that admits
    it does not hold the answer.
    """
    store = knowledge.harvest()
    answer = knowledge.ask(store, "what is the population of the capital of Peru")
    assert answer["status"] == "unknown", answer
    assert answer["reason"], "it refused without saying why"


def test_an_empty_store_knows_nothing():
    """The null. If every question is answerable against an empty record, the answers were coming
    from the question, not from the record.
    """
    empty = {"schema": knowledge.SCHEMA, "records": [], "claims": [], "sections": [],
             "unrepresented": [], "coverage": {"evidence_files": 0, "represented": 0,
                                               "unrepresented": 0, "log_claims": 0}}
    for question in ("what did log 19 conclude about program synthesis", "xor3 parity separability"):
        assert knowledge.ask(empty, question)["status"] == "unknown", question


# ---------------------------------------------------------------- refusing its own regressions
def test_it_refuses_a_claim_its_own_record_falsified():
    """SAFETY property: a claim the record states FALSE must not be admissible again as TRUE.
    This is the seed of unaided closure -- you cannot catch your own regression if you do not
    remember what you disproved.
    """
    store = knowledge.harvest()
    for claim in ("the operator list is no longer mine",
                  "a deeper axis-aligned tree learns xor",
                  "the method primitives are no longer mine"):
        hits = knowledge.conflicts(store, {"claim": claim, "verdict": "TRUE"})
        assert hits, f"re-asserting a falsified claim was allowed: {claim}"
        assert all(hit["verdict"] == "FALSE" for hit in hits)


def test_it_does_not_refuse_something_it_never_judged():
    """The paired failure for the test above. A guard that fires on everything is not a guard."""
    store = knowledge.harvest()
    assert knowledge.conflicts(store, {"claim": "the moons of Jupiter are made of cheese",
                                       "verdict": "TRUE"}) == []
    # And an unjudged verdict is not a conflict at all.
    assert knowledge.conflicts(store, {"claim": "the operator list is no longer mine",
                                       "verdict": "MAYBE"}) == []


# ------------------------------------------------------------------------------ the instrument
def test_the_before_detector_finds_a_corpus_walker():
    """A measured zero is worthless if the instrument cannot see a one."""
    assert probe.walks_corpus(
        'import glob\nfor p in glob.glob("canonical/verification/*.json"):\n    pass\n')
    assert not probe.walks_corpus(
        'PATH = "canonical/verification/METHOD_V1.json"\nimport json\njson.load(open(PATH))\n')
    assert not probe.walks_corpus("GLOBAL_AUTHORITY = True\n")


# ---------------------------------------------------------------------------------- the limit
def test_a_paraphrase_is_unknown_and_that_is_the_limitation():
    """A LIMITATION, not a safety property: it may never block a widening change.

    Retrieval is token overlap, so "what did the twentieth log find" does not reach log 20. This is
    the difference between REMEMBERING and KNOWING, and it is the honest boundary of this log.
    """
    store = knowledge.harvest()
    answer = knowledge.ask(store, "what did the twentieth log find")
    assert answer["status"] == "unknown", (
        "paraphrase now works -- the limitation has lifted, so update the log")
