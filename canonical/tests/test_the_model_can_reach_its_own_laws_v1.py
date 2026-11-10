"""The one model must be able to reach its own laws.

MEASURED DEFECT THIS PINS
-------------------------
`BRAIN_UNIFIED_MODEL_V1.json` stores 781 action-intent LAW records. Each carries a
causal blocker, a measurement, a falsification condition and a stop condition -- they
are the most valuable records in the repository. `recall()` scored only the knowledge
documents and never the laws, so:

    ['a chain that ran no step is not a pass',
     'a census that cannot fail is not a gate',
     'a report verb is not a source write']          ->  0 law hits out of 6, three times

A second, independent cause: `tokenize` keeps `_` inside a token, so an unsplit law stem
became the single token `a_census_that_cannot_fail_is_not_a_gate`, which can never
overlap a query written in words. Both are fixed; both are pinned here.

These tests are about REACHABILITY, not about ranking quality in general. They assert
that a stated rule can be found by its own words, which is the minimum a model owes the
records that govern it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import brain_unified_model_v1 as U  # noqa: E402

ARTIFACT = ROOT / U.DEFAULT_ARTIFACT

# Rules stated in this repository, asked in the words the rule itself uses.
LAW_QUERIES = [
    "a chain that ran no step is not a pass",
    "a census that cannot fail is not a gate",
    "a report verb is not a source write",
    "a question is not closed by a file appearing",
    "fail closed means the world is unchanged",
    "a repair search must contain the defect",
    "a promise about a file is read before the work",
    "a tie between capabilities is not ambiguity",
]


@pytest.fixture(scope="module")
def model():
    if not ARTIFACT.is_file():
        pytest.skip("unified model artifact not compiled")
    return U.UnifiedModel(U.load_model())


def test_the_artifact_stores_the_laws(model):
    laws = [r for r in model.research_index.values()
            if "action_intents" in str(r.get("path"))]
    assert len(laws) > 500, f"only {len(laws)} law records in the artifact"


def test_recall_searches_the_laws_not_only_the_knowledge(model):
    corpus = model._recall_corpus()
    knowledge = len(model.knowledge)
    assert len(corpus) > knowledge, "the laws are in the artifact but not in recall's corpus"
    laws = [r for r in corpus if r.get("authority") == "ACTION_INTENT_LAW"]
    assert len(laws) > 500


def test_a_law_stem_is_split_into_words_not_one_giant_token(model):
    # the exact bug: one token that can never overlap a worded query
    laws = [r for r in model._recall_corpus()
            if r.get("authority") == "ACTION_INTENT_LAW"]
    assert laws
    for r in laws:
        for term in r["title_terms"]:
            assert len(term) < 60, f"unsplit law stem token: {term!r}"
            assert "_" not in term, f"underscore survived tokenisation: {term!r}"


@pytest.mark.parametrize("query", LAW_QUERIES)
def test_a_stated_law_is_found_by_its_own_words(model, query):
    hits = model.recall(query, top_k=6)["hits"]
    assert hits, f"no hits at all for {query!r}"
    assert "action_intents" in str(hits[0].get("path")), (
        f"{query!r} was answered by {hits[0].get('path')!r}, not by the law")


def test_recall_stays_fast_with_the_laws_in_the_corpus(model):
    import time
    model.recall("warm", top_k=5)
    times = []
    for _ in range(20):
        t = time.perf_counter()
        model.recall("a census that cannot fail is not a gate", top_k=5)
        times.append((time.perf_counter() - t) * 1000)
    times.sort()
    assert times[len(times) // 2] < 50.0, "recall must stay in the millisecond range"
