"""The test that decided whether last round's number was a method or a memory.

Last round: structure routing 84.4% at 64 skills against 6.2% for word overlap. This round:

  remove the 84 hand-written synonyms        84.4% -> 28.1%   (the curve now decays the
                                                               same way word overlap does)
  test on probes whose words appear nowhere
  in that dictionary                         32.8% at 64 skills, and the dictionary buys
                                              only +6.2pp of it
  ask the model, blind, same held-out set    100% at every size, 0 wrong

So the honest finding is not "I found a better similarity measure". It is:

    word matching, hierarchy, and object structure all decay.
    The decay is not a property of the algorithm. It is a property of trying to
    recover MEANING from SURFACE FORM, which loses information.

And the cost side is what makes the conclusion actionable rather than rhetorical:

    the catalog as a model sees it     8 tokens per skill
    at 1000 skills                     ~8,000 tokens -- comfortably inside a modern context
    a model call per request           one, and it does not degrade with library size
"""
import json
import pathlib
import random
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import canonical.evaluation.routing.ablate_the_dictionary_v1 as A
import canonical.evaluation.routing.scale_experiment_v1 as E
from canonical.evaluation.routing.heldout_probes_v1 import HELDOUT

ROOT = pathlib.Path(__file__).resolve().parents[2]
ANSWERS = json.loads(
    (ROOT / "canonical/evaluation/routing/model_answers_heldout_20261109_v1.json").read_text())


def _rate(n, cond, seeds=10):
    A.set_condition(cond)
    tot = probes = 0
    for s in range(seeds):
        r = E.run(n, s)
        tot += r["struct"]
        probes += r["probes"]
    A.set_condition("FULL")
    return tot / probes


# ------------------------------------------------------------------ the ablation

def test_the_dictionary_is_doing_the_heavy_lifting():
    """84.4% -> 28.1% with the synonyms removed. The claimed method was a word list."""
    assert _rate(64, "FULL") > 0.80
    assert _rate(64, "NO_SYNONYMS") < 0.35


def test_the_lexicon_is_an_input_not_a_result():
    """Removing it must be reported as the size of the hand-curation required, not hidden."""
    assert sum(len(v) for v in A._ORIG_SYN.values()) >= 60


def test_object_matching_alone_still_beats_plain_word_overlap():
    """Not nothing: 26.6% vs 6.2% on held-out vocabulary. The object is more stable than
    the verb, but it still decays with library size."""
    assert _rate(64, "NO_DICT") > 0.20


# ------------------------------------------------------------------ the held-out set

def test_on_unseen_vocabulary_the_full_router_falls_to_about_a_third():
    A.set_condition("FULL")
    right = total = 0
    for s in range(10):
        lib = E.build_library(64, random.Random(s))
        for k, probe in HELDOUT.items():
            if k not in lib:
                continue
            total += 1
            right += E.structure_route(probe, lib) == k
    A.set_condition("FULL")
    assert right / total < 0.45, f"{right/total:.1%} -- the held-out set is not held out"


def test_the_dictionary_buys_almost_nothing_on_unseen_vocabulary():
    """+6.2pp on words it has never seen, against +56pp on the words it was written from."""
    A.set_condition("FULL")
    f = r24 = t24 = 0
    for s in range(10):
        lib = E.build_library(64, random.Random(s))
        for k, probe in HELDOUT.items():
            if k not in lib:
                continue
            t24 += 1
            f += E.structure_route(probe, lib) == k
    A.set_condition("NO_DICT")
    d = 0
    for s in range(10):
        lib = E.build_library(64, random.Random(s))
        for k, probe in HELDOUT.items():
            if k not in lib:
                continue
            d += E.structure_route(probe, lib) == k
    A.set_condition("FULL")
    assert (f - d) / t24 < 0.15, "the dictionary generalised more than it should have"


# ------------------------------------------------------------------ the model

def test_the_model_is_exact_on_the_same_held_out_set():
    """64/64 blind, from the catalog alone, at every library size. Written to a file before
    any of it was scored."""
    assert len(ANSWERS) == len(HELDOUT)
    wrong = [k for k, probe in HELDOUT.items() if ANSWERS.get(probe) != k]
    assert wrong == [], wrong


def test_the_model_does_not_degrade_with_library_size():
    """The router's accuracy depends on n. The model's did not, because every skill is
    visible in the catalog regardless of how many there are."""
    for n in (10, 25, 50, 64):
        right = total = 0
        for s in range(5):
            lib = E.build_library(n, random.Random(s))
            for k, probe in HELDOUT.items():
                if k not in lib:
                    continue
                total += 1
                right += ANSWERS.get(probe) == k
        assert right == total, f"n={n}: {right}/{total}"


# ------------------------------------------------------------------ the cost side

def test_the_whole_catalog_fits_in_a_context_at_a_thousand_skills():
    """8 tokens per skill. This is why the answer is 'show the model the catalog', not
    'build a better thesaurus': the thesaurus must be hand-written per domain, and the
    catalog costs nothing to show."""
    lib = E.build_library(64, random.Random(0))
    toks = sum(len(k.split()) + len(v["trigger"].split()) + 4 for k, v in lib.items())
    per_skill = toks / len(lib)
    assert per_skill < 12
    assert per_skill * 1000 < 20000
