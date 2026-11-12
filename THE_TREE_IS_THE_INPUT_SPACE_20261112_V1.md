# The tree is the input space it was missing

**2026-11-12.** Base `d5d7cb90`. Branch `arena/06cc4027-brain`. Round 21.

**Authority: NONE.** Sandbox measurement and decision record. No capability, ownership,
benchmark, acceptance, terminal or sentience credit. `truth.achieved` stays `false`.
Incremental spend $0. Zero model dependency. Nothing registered. No guard weakened.

The owner asked whether solved instant learning plus the most advanced coding and
computer-use actions means one try in each new environment permanently teaches
everything, and whether that already makes the strongest agent on the planet.

Three prior rounds had already answered the optimistic version, from three angles:

| round | measured | result |
|---|---|---|
| 17 | 296 independently verified experiences | **zero arguments**, so a re-run is a constant |
| 18 | `--instance-index` shipped | nothing drove it past 0 |
| 20 | 56 file-input capabilities × 10 shipped fixtures | **0 reached success** |

Round 20's conclusion was that the corpus is "empty by construction", and that the only
thing that fills it is doing real work with a verifier attached.

That conclusion is correct about *fixtures* and *zero-argument module runs*. It is not
correct about the repository itself. `python.repository.acceptance.measure.v1` does not
want a document borrowed from another corner of the tree. It wants a source tree — and
this repository is made of them.

## 1. What was measured

`real_input_space_census_20261112.py`. No fixtures authored, no network, no model.

```
lane-reachable capabilities                191
  ... with declared inputs                  40
  ... verified on >=1 real tree instance     4
  ... with >=2 DISTINCT verified instances   4

Has a real input space today:
  python.repository.acceptance.measure.v1            3 distinct
  python.software.request.semantic_behavior.compile.v1 3 distinct
  python.fault.provenance.interprocedural.value.v1     2 distinct
  python.software.repair.loop.coupled.ast.v1           2 distinct
```

Four capabilities already have what three rounds said the tree did not have: two or
more real, distinct inputs, drawn from directories that already exist, on which they
reach a verified outcome. The `output_sha256` of the written artifact differs per
instance (2/2, 3/3, 2/2, 3/3), so the variation is in the subject measured, not in the
sink's name.

## 2. The loop closes on the real tree

`python.repository.acceptance.measure.v1` was run on five real directories. Four
verified; **`canonical/tools` failed**, with

```
MeasurementError: NO_TEST_FILES_UNDER_SOURCE_ROOT
```

That is a labelled failure, and the sensor already owns a fact for it. Established with
`world_probe_v1.established_facts` over the sensor's own 19-kind table, then handed to
`applicability_v1.learn` as `(facts, succeeded)` pairs:

```
status        IDENTIFIED__ONE_CONSISTENT_REQUIREMENT
required      ('python.test.corpus.available',)
survivor_count 1

canonical/tests                        real=True   admitted=True
canonical/runtime                      real=True   admitted=True
canonical/runtime/bound_capabilities   real=True   admitted=True
canonical/verification                 real=True   admitted=True
canonical/tools                        real=False  admitted=False
canonical/analysis                     real=False  admitted=False
```

**No new vocabulary, no new module, no weight update.** The requirement was induced from
real outcomes over the sensor that already exists, and it predicts held-out directories
exactly. This is the "one verified experience becomes a reusable, transferable skill"
loop — closing for the first time on inputs the tree actually supplied.

## 3. Two bugs I wrote, and what they would have cost

Both were silent, and either one alone would have manufactured the result above.

**(a) The directory chooser saw one directory.** It scanned only *children* of the base
directories, so `canonical/tools` and `canonical/tests` — which hold files directly —
never appeared. Every `source_root` instance was the same directory, and the first run
reported "4 capabilities with 2–3 distinct instances" from a pool of one.

**(b) The outcome digest included `output_path`.** Every instance gets a distinct sink by
construction, so digesting the whole result reported k "distinct outcomes" for k
identical runs. This is the worse bug: it produces a **passing** measurement of nothing.
The digest now excludes the sink, and separately records `output_sha256` so a reader can
check that the artifact content genuinely varies.

A third defect was found in the sensor itself and **named, not fixed**.

## 4. The sensor's matching rule is a substring test

```
_matches_kind:  if substrings and not any(s in low for s in substrings): return False
```

So `python.test.corpus.available` is satisfied by any path containing the substring
"test". On this tree the **verdicts are all correct** — a test asserts that the sensor's
verdict agrees with the count of genuine `test_*.py` modules for every directory the
learner saw — but the **evidence** is wrong:

```
canonical/runtime   real_test_files=14   sensor=True   evidence: attested_state_v1.py
```

`attested_state_v1.py` is not a test module. The fact is true for the right reason by
luck, and the recorded witness does not name it.

Why this is not shipped: the fix is to require the file stem to begin with `test_`. That
narrows a sensor every binding decision reads, including the one that just produced this
round's headline. A narrower rule could only ever turn `True` into `False` there, so it
cannot inflate the result — but it can invalidate the 296 existing attestations and the
whole binding surface. It is named with the exact line, the exact change and the exact
reason, and pinned as current behaviour by a test, so the next session that can run the
full workflow can make it and nothing else.

## 5. What this does and does not change

**Changes.** The claim "the corpus is empty by construction" is now false as stated for
at least four capabilities. The corpus is *nearly* empty, and the gap is not
environments, demonstrations, or fixtures — it is **inputs the tree already holds**. The
fastest route to a train/held-out split is not to author 2,000 tasks; it is to point the
126 parameterised capabilities at the directories and files this repository already
contains, run each k times, and keep the ones that verify. That is the same price the
2026 record pays, paid against data that exists rather than data that must be invented.

**Does not change.** Four of 191 is 2%. It is not "instant learning solved". It is not
"any computer use". `truth.achieved` is still false and no capability was registered.
The dominant failure mode remains what the census shows: **12 capabilities could not be
given a real value for a declared parameter**, 21 raised, 2 have no adapter at all. The
binding problem from round 11 is the same binding problem here — and now it has a
concrete, cheap next target instead of a philosophical one.

**On sentience.** A module that induces a boundary is not evidence of experience. This
round added a measurement, not a creature.

**On the 2026 record.** The direction is right and the mechanism matches what is
published: skill libraries that persist across rollouts (Voyager; SAGE), online
skill-evolution for computer-use agents (from interaction traces to persistent, versioned
procedures), polymorphic skill abstraction for continual learning across sites (ICLR
2026), and autonomous curriculum RL for environment adaptation with 3–29% gains and no
catastrophic forgetting. Every one of those uses the base model to *propose* and a
verifier to *keep*. The part this repository owns — and the part nobody else has — is a
deterministic, model-free induction step that turns `(facts, outcome)` pairs into a
requirement with a survivor count of one. That is real, and it just ran.

## 6. What is wrong with the plan in the question

> *Give it the most advanced actions, let it try once in every new environment, and it
> keeps them forever.*

Three specific errors, all measured:

1. **"Try once" has no content without an input space.** Round 17: 296 tries, zero
   arguments. Round 21: the same capability at k=0,1,2 produced one digest — replicas,
   not instances — until the input came from a real directory.
2. **An environment is a place to run, not an instance to learn from.** Round 20's zero
   out of 56 was not a data shortage. A capability is a function of a document *and* the
   packages, roots and contracts of the environment it was built for.
3. **What is learned is often not the thing that failed.** Round 21's failure was
   legible (`NO_TEST_FILES_UNDER_SOURCE_ROOT`) and a fact already existed for it. When
   it is not legible, more repetitions cannot help: the same fact vector is observed
   forever and the evidence is contradictory by construction. That is the vocabulary
   wall, and it is a different wall from this round's.

## 7. Receipts

```
python3 real_input_space_census_20261112.py --k 3 --json /tmp/real_space3.json
  self_checks: 5 directories, 12 files, pool varied, digest excludes output_path
  lane-reachable 191 | with declared inputs 40 | verified >=1 4 | >=2 distinct 4

python3 -m pytest -q canonical/tests/test_real_input_space_census_v1.py
  9 passed
```

The nine tests pin: the chooser finds more than one real directory; every chosen
directory really holds Python; the file pool is real; integer parameters are never given
paths; the capability verifies on real directories; distinctness does not come from the
sink name; the sensor separates real successes from real failures; the real-tree
separation is backed by genuine `test_*.py` modules; and the substring quirk is current
behaviour. Two of the nine failed when first written — one because my root was wrong, one
because I asserted `canonical/verification` held no test files and it holds two. Both
failures were the test being wrong about the tree, which is the correct reason to fail.

## 8. Non-claims

Four capabilities is a proof of mechanism, not a corpus. It does not show that k=3
generalises, that the held-out split is learnable, or that the same route works for any
capability outside the python-source family. The learned requirement is *one* consistent
conjunction over *four* facts; a richer vocabulary would likely leave it ambiguous.
Nothing was registered, no capability promoted, no benchmark moved, no guard weakened,
`truth.achieved` false, $0, zero model dependency.
