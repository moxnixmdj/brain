# The loop was open at the live entry

**2026-11-12.** Base `d677e54e`. Branch `arena/91d09142-brain`. Round 26.

Rounds 23–25 measured compress → admit → replay and were honest about one thing each time: the
measurement supplied what the live path supplies. Round 25 says it in its own words —

> *the bridge stays SKILL-only and correctly admits nothing it cannot probe … string-domain organs
> enter the library only through a caller that can supply real domain probes.*

That sentence describes a MECHANISM WITH A HUMAN IN THE LOOP. The owner's question is about the
live path, where nobody supplies anything. This round drove the live path and found that it did not
work at all.

Authority **NONE**. Producer-run, one machine, temp directories, `$0`, zero model dependency, no
capability registered, no family flipped, `truth.achieved` stays `false`.

---

## 1. What the live path did before this round

`canonical/tools/one_try_compounding_probe_20261112_v1.py` drives `register_organ` →
`CompoundingConceptLibrary` → `rewrite_source_with_concepts` with no caller-supplied probe domain
anywhere, on three world-model organs of one structural family plus a never-seen fourth.

```
LIVE PATH (register_organ -> library -> wake replay, no caller probes)
  organs registered          3
  library entries            0          <- three experiences, nothing kept
  abstractions admitted      0
  never-seen organ replay    REFUSED
```

Five defects, each independently sufficient to stop the loop:

| # | defect | the fact |
|---|---|---|
| 1 | **no probe domain at the live entry** | `_skill_organ_to_concept_entry` called `compress_corpus(corpus)` with no `probes`, so the numeric default grid ran against a string-keyed table, every probe answered identically, and the (correct) `PROBE_GRID_NON_DISCRIMINATING` gate refused |
| 2 | **a comparator that assumed total functions** | both gates read ANY exception as a disagreement, so a keyed lookup that raises off-domain was reported as *changed behaviour* — "identical except where the table has no row" was unmeasurable by construction |
| 3 | **one identifier for every organ** | the bridge built `"c_" + organ_id.replace("organ_skill_", "")[:18]`; a 10-character prefix plus an 18-character truncation of a 27-character id leaves `organ_skill`, so every SKILL organ mapped to `c_organ_skill_`. Measured: three different organs → one id → **one slot** |
| 4 | **a stratum gate that excluded the family it was built for** | admission fired only for `organ.stratum == SKILL`, but the second family is emitted by `synthesize_world_model_organ`, a **WORLD_MODEL** organ — the live writer for the family round 25 measured did not exist |
| 5 | **one branch returned a dict, then a program that could not run** | `rewrite_source_with_concepts` returned the replay engine's report on the abstraction branch and source text everywhere else; returning the source alone then produced a program whose concept id was undefined (`NameError`), because the helper lives beside it |

Defect 3 alone is the strongest answer to *"learn it once and keep it"*: a memory that can hold one
item per stratum has no reuse to compound, and every measurement above it was of a different object
than the one the creature runs.

## 2. What was built, and why each step is the smallest correct one

- **`derive_probe_domain(sources)`** — the probe domain derived from the corpus's own string/int/
  float literals. This is a **prior, not an oracle**: it is the same move
  `settlement.derive_probe_space` already makes for numeric hypotheses, applied to the literals the
  lifter has just decided are data. It cannot invent an input the corpus never mentions, which is
  precisely why both existing gates stay exactly as strict — verified by
  `test_a_non_discriminating_domain_is_still_refused`.
- **`admit_corpus_abstraction(...)`** — one admission call for the live path: supplied domain if a
  caller has one, derived otherwise, and the report says **which**. No measurement can now conflate
  the two.
- **partial-function equivalence** at both gates — two programs are the same function when they
  agree wherever either is defined; an exception is an outcome to be compared, never a refusal.
  This is what "behaviour preserved" always meant; the code could not express it.
- **`concept_id_for_source`** — an id that is a function of the bytes: distinct programs get
  distinct slots and replays survive a restart.
- **`_ADMISSIBLE_STRATA = (SKILL, WORLD_MODEL)`** — PERCEPTOR and VERIFIER stay out on purpose: their
  entrypoints parse raw samples, so lifting their literals probes a parser with tokens it was never
  written to accept, and a refusal there would read as a compression failure.
- **one return type, executable** — the wake entry returns the helper prelude plus the rewritten
  module: exactly the string the engine compiled and behaviour-checked, no second construction.

No gate was widened. Two were made *able to run* (1, 2), one was scoped to the strata it was always
about (4), and two bookkeeping defects were removed (3, 5).

## 3. The measurement

The prediction, written before the run: *after three organs of one family are experienced through
the live entry point, a never-seen fourth replays strictly smaller with behaviour preserved, and the
curve shows the abstraction arriving at the third site.*

```
CURVE (each row = one more organ experienced; never-seen member replayed after it)
  organs  library  abstractions  never-seen replay  program bytes
       1        1              0  REFUSED                  -
       2        2              0  REFUSED                  -
       3        3              1  REWRITTEN              277     (cold: 394)

behaviour mismatches on held-out ids incl. unknowns ("nope", "", "W"):  0
numeric grid on the same library:                                     REFUSED (vacuity gate)
supplied domain vs derived domain:                       same family admitted, derived alone suffices
identifier:                       3 organs offered -> 3 distinct ids -> 3 slots (was 1 -> 1)
```

The program goes **394 → 277 description bytes (−30%)**; the shared helper costs 250 bytes **once**
for the whole family (total 527 for the first replay). That asymmetry is the honest shape of reuse
here and it is why both numbers are printed instead of one: **reuse pays from the third site of the
family**, which is exactly the economics `compress_corpus` already enforces at admission. Round 25's
arithmetic (helper + call ≈ 262 vs a cold 179) said the same thing about emission; it is now true of
replay on the live path too.

## 4. What this does not claim

- **One experience is still not a rule.** The curve says it plainly: k=1 stores one program
  (gain 0), k=3 buys the abstraction. Nothing here moves that, and nothing should.
- **Cross-KIND compounding is still the pinned negative** (10 kinds, 1525 vs 1525 environment calls).
  This round closes the loop *within* a structurally-recognised family on the live path. It does not
  make kind A cheaper because kind B was seen.
- **No independent oracle judged anything.** Producer-run, one machine, no external board. The six
  pre-existing failures in `test_sentient_cognitive_core_v1.py` are identical before and after this
  change (measured by running both trees) and remain the repo's honest backlog.
- **No capability, ownership, benchmark or terminal credit.** No family flipped. `truth.achieved`
  stays `false`.

## 5. The plain answer to *"why can't we just give it the actions once?"*

The three questions were different questions and now have three different answers:

1. **"Give it the actions once and it keeps them."** For a family the engine can *check*, yes — and
   until this round that was true only inside tests, because the live writer had one slot, no probe
   domain and the wrong stratum. It now holds three programs and one abstraction, and the fourth
   member replays 30% smaller with zero behaviour changes. That is the first time this sentence is
   true of the creature rather than of a measurement harness.
2. **"Then it learns anything on a computer."** No, and the reason is unchanged: the two failure
   modes are coverage and identification, and a demonstration supplies neither a hypothesis language
   nor a discriminating question. What generalises is the *compression prior over solved programs*,
   not the inventory of experiences.
3. **"Then the corpus."** This is the lever this round makes usable: a corpus only comes from real
   work (`THE_CORPUS_CAN_ONLY_COME_FROM_REAL_WORK_20261112_V1.md`), and the loop that turns it into
   capability now runs on the live path. The next honest step is feeding it real solved programs
   and measuring whether the live curve keeps its shape on them — not widening anything.

## 6. Receipts

```
python3 canonical/tools/one_try_compounding_probe_20261112_v1.py
canonical/tests/test_live_compounding_loop_v1.py       9 tests
canonical/tests/test_wake_replay_compounds_into_programs_v1.py   (contract corrected: source text)
canonical/tests/test_compression_gain_abstraction_v1.py
canonical/tests/test_second_family_keyed_table_v1.py
```

44 tests pass across the four suites that own this mechanism; 145 pass across the ten suites that
import the three changed modules; changed modules are not byte-pinned by any capability record
(`git hash-object` checked against the tree). `$0`, zero model dependency.
