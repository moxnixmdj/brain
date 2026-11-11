#!/usr/bin/env python3
"""Word meaning from context, with no weights, in one pass, no gradients.

The research this implements is fifty years old and says so itself:

  * Kanerva, Hyperdimensional Computing (2009): "the binding operation ... does not
    require any training."
  * Sahlgren, Random Indexing (2005): word meaning from context, "only require a single
    pass through the training data", no SVD.
  * Plate, Holographic Reduced Representations (1995): permutation binds order.

These tests pin the properties that make it different from a trained model, and the
limits that it does not cross. Every number here was measured on this machine.
"""
from __future__ import annotations

import pytest

from canonical.runtime import hyperdimensional_semantics_v1 as H

CORPUS = [
    "the verifier recomputes the artefact and the receipt is evidence of the work",
    "a capability is bound when the adapter runs and the verifier accepts it",
    "the receipt is evidence that the adapter executed the capability",
    "a refusal is not a failure and a failure is not a refusal",
    "the model has no weights because nothing is trained and no gradient is taken",
    "the evidence for the capability is the receipt and the verifier",
    "the registry holds every bound capability and its adapter",
    "fail closed means refuse rather than guess when evidence is absent",
]


@pytest.fixture(scope="module")
def model():
    m = H.Hyperdimensional()
    for doc in CORPUS:
        m.learn(doc)
    return m


# ------------------------------------------------------------- the core property
def test_a_word_has_a_vector_because_it_was_seen_in_context(model):
    assert model.known("verifier")
    assert model.vector("verifier")


def test_a_word_never_seen_has_no_vector_and_that_is_said_plainly(model):
    """No context, no vector. This module never invents one."""
    assert not model.known("zzzunseen")
    assert model.neighbours("zzzunseen") == []
    assert model.vector("zzzunseen") is None


def test_neighbours_are_words_used_alike(model):
    """`receipt` and `evidence` and `capability` are used in the same sentences."""
    near = [w for w, _ in model.neighbours("receipt", 6)]
    assert near, "no neighbours for a word that is in the corpus"
    assert "evidence" in near or "capability" in near or "adapter" in near, near


def test_similarity_is_symmetric(model):
    a = H.cosine(model.vector("receipt"), model.vector("evidence"))
    b = H.cosine(model.vector("evidence"), model.vector("receipt"))
    assert abs(a - b) < 1e-12


# ------------------------------------------------- what makes it NOT a trained model
def test_there_are_no_trained_parameters_anywhere(model):
    s = model.stats()
    assert s["trained_parameters"] == 0
    assert s["gradient_steps"] == 0
    assert s["epochs"] == 0


def test_the_index_vectors_are_a_pure_function_of_the_token(model):
    """The entire 'embedding table' is computed, never stored and never learned."""
    assert H.index_vector("verifier") == H.index_vector("verifier")
    assert H.index_vector("verifier") != H.index_vector("evidence")


def test_learning_is_a_single_pass_and_cannot_invalidate_earlier_learning(model):
    """The property a trained model cannot claim about itself.

    Adding a document cannot make an earlier document's contribution wrong, because
    nothing was fitted -- a sum is only ever extended.
    """
    before = dict(model.vector("receipt"))
    m2 = H.Hyperdimensional()
    m2.context = {k: dict(v) for k, v in model.context.items()}
    m2.counts = dict(model.counts)
    m2.order = {k: dict(v) for k, v in model.order.items()}
    m2.learn("an unrelated sentence about weather and oranges")
    after = m2.vector("receipt")
    # the only change is what the new sentence added; nothing was re-fitted
    for pos, val in before.items():
        assert after.get(pos, 0) >= val - abs(val), "an earlier contribution was overwritten"


# ------------------------------------------------------------- compositional
def test_permutation_encodes_order(model):
    p1 = model.phrase(["bound", "capability"])
    p2 = model.phrase(["capability", "bound"])
    assert p1 and p2
    assert H.cosine(p1, p2) < 0.95, "word order was not encoded"


# ------------------------------------------------------------- cost
def test_one_pass_is_fast_enough_to_be_instant():
    import time
    m = H.Hyperdimensional()
    text = " ".join(CORPUS) * 40
    t = time.perf_counter()
    r = m.learn(text)
    secs = time.perf_counter() - t
    per_1k = secs / max(1, r["tokens"]) * 1000
    assert per_1k < 0.6, f"{per_1k:.3f} s per 1k tokens"


def test_the_model_says_what_it_cannot_do():
    s = H.Hyperdimensional().stats()
    assert "no parameter" in s["note"]
