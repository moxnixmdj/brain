# The Right Question Is an Experiment — 2026-11-24

**What this round asked.** The previous round (`THE_GUIDE_IS_A_TEST_SUITE_20261204_V1`) measured
that 94% of documentation bytes are prose, not transcripts, and that prose was never read. This
round reads it and asks the only question that can make a sentence checkable:

> not *"what does this sentence say?"* but *"what experiment would make this claim TRUE or FALSE?"*

**What was built.** `canonical/tools/the_right_question_is_an_experiment_v1.py` — a compiler from
a prose claim to an executable witness, with seven gates that each refuse by name. Nothing is
admitted because it sounds right; a claim is admitted only when the witness separates a wrong
version, is **false of the program that does nothing**, and repeats on a second room.

**What was fixed.** The instant-knowledge circuit in `perfect_algorithm_v1.run()` was open in
three places. All three are closed and regression-tested:

1. `run()` read `instant["documents"]`, a key nothing ever set, and the fetcher returned
   snippets rather than documents. Now the fetcher returns the document's **text** and `run()`
   reads it (`documents_with_text` is in the receipt).
2. `_plan_from_document` refused every non-Python document at its first gate (`">>>" not in
   text`). A shell guide is the same thing in the other dialect, so it now reads `$ command`
   transcripts, replays them in a scratch room, and uses the author's printed output as the
   oracle — the same four gates, the same vocabulary restriction.
3. When a document has neither `>>>` nor `$` transcripts (94% of documentation bytes),
   `_plan_from_document` now delegates to `_plan_from_prose`, which compiles prose sentences to
   executable witnesses, induces typed data-flow signatures, and runs counterexample-guided
   composition (`synthesize_plan`) in a scratch mental model before returning a plan.

A README with ```` ```console ```` `$ echo hello` / `hello` now ends in
`PASS__PLAN_FROM_A_DOCUMENT` with `plan: ['echo hello']`, and a prose-only README (`tar archives a
directory. tar extracts an archive. gzip compresses a file.`) now ends in
`PASS__PLAN_FROM_A_DOCUMENT` with the 3-step verified chain. Before this round both ended in
`OPEN__NO_PLAN_AFTER_SCAN` with `documents_returned: 0`.

---

## 1. The measurement

Three corpora, reported **separately**, because they are not interchangeable kinds of text.

| corpus | documents | bytes | sentences | claims | admitted | claim yield | prose yield |
|---|---:|---:|---:|---:|---:|---:|---:|
| `--help` of the fleet | 37 | 94,098 | 336 | 28 | **18** | 64.3% | 5.36% |
| Python stdlib docstrings | 6 | 76,760 | 1,179 | **0** | 0 | — | 0% |
| GNU manuals (texinfo) | 285 | 470,392 | 6,595 | 496 | **106** | 21.7% | 1.61% |

Transfer to a **third** room, never seen: 58 tested, **50 admitted, 8 refused**. The eight are the
honest part: a relation that held in two rooms and failed in a third was about the rooms.

Operations, not sentences, are the honest denominator: **161 distinct (program, relation) pairs
are named in the manuals, and 44 are admitted — 27.3% coverage.**

### The store as a typed data-flow graph (semantic equivalence + CEGIS composition)

A single relation opens one door; a goal is usually a chain of doors (`directory → archives →
extracts → compresses`). Rather than hand-declaring output types, `induce_signatures()` induces
each relation's signature `input_kind → output_kind` from the artifact its witness actually
produced (`PRODUCING_RELATIONS`), while reader relations (`checks`, `compares`, `counts`, `lists`,
`prints`, `searches`) induce `output_kind = None` and serve as goals rather than intermediate
steps.

Three mechanisms make multi-step composition exact without hardcoded rules:

1. **Semantic equivalence of kinds (`_canonical_kind`).** English names the same room artifact
   three ways (`line`, `text`, `file`). Inspecting the witness's initial room artifact collapses
   lexical synonyms onto one node (`file`), eliminating phantom coercion steps (`sort` inserted
   merely to convert `line` into `file`, which scrambled line order before `tar`).
2. **Program equivalence classes per edge.** Every witnessed `(program, template)` for the same
   `(relation, input_kind)` edge is retained (`compresses:file → [gzip, bzip2]`,
   `decompresses:compressed → [bzip2, gzip]`).
3. **Counterexample-guided composition (`synthesize_plan`, Executable Mental Model).** When an
   edge has multiple candidate programs, the first type-correct chain (`gzip` followed by
   `bzip2 --decompress`) can fail at a sub-type boundary (`bzip2: Data.txt.gz is not a bzip2
   file`). `synthesize_plan()` tests candidate assignments in the scratch mental model
   (`run_composed_plan`), records the failing pair as a structured counterexample, and advances
   to the compatible assignment (`gzip → gzip --decompress`).

| metric | before CEGIS + canonical kinds | with CEGIS + canonical kinds |
|---|---:|---:|
| kind nodes | 6 (`archive`, `compressed`, `directory`, `file`, `line`, `text`) | **4** (`archive`, `compressed`, `directory`, `file`) |
| producing edges | 9 | **7** |
| equivalence classes (`>1` program) | — | **3** (`compresses:file`, `decompresses:compressed`, `prints:file`) |
| goals composed `(start_kind, goal_relation)` | 66 (18 one-step, 48 multi-step) | **44** (13 one-step, 31 multi-step) |
| multi-step chains executed | 48 / 48 | **31 / 31** |
| multi-step chains that ran and met the goal | 33 / 48 (68.8%) | **30 / 31 (96.8%)** |
| counterexamples refuted in mental model | 0 | **6** |
| `REFUSED__CHAIN_BROKE_AT_A_STEP` | 5 | **0** |
| `REFUSED__CHAIN_RAN_BUT_MISSED_THE_GOAL` | 10 | **1** (`directory → decompresses`: directory room has no single-file `original`) |

Running the composed chains exposed two defects in single-step admission that two-room testing
alone had missed: `tar a b` exited 2 on syntax error and had been admitted as `compares` until
`same_exit == 0` on identical files (`tar a a`) was required; and `tar --test-label` had been
run without `-f` and against a half-truncated 10,240-byte tar archive whose zero padding left the
first 512-byte header block intact. Both are now fixed and held by regression tests.

**The one change that moved the number.** 152 claims were refused `NO_PRODUCER_FOR_KIND`, and all
152 named **no object at all** — `cat normally reads and writes in binary mode` says what cat
does and leaves the object implicit. Guessing the object from the sentence is the wrong move;
reading it from the **program's own usage line** is the right one, and it is the same reading the
flag already gets. Admitted went 38 → 107 and claim yield 7.8% → 21.9% on that single change.

**Why the stdlib corpus is zero, and why that is a finding rather than a failure.** A docstring is
prose about a *function*. The extractor requires a program the machine has and a relation word
with that program as its subject; `statistics.median` names no CLI program, so the corpus
contributes 1,179 sentences and no claims. The instrument's vocabulary is about **operations on
objects**, which is the right shape for a shell and the wrong shape for a library. That boundary
is now measured rather than assumed.

---

## 2. Verdict on the hypothesis

**"Everything on a computer already has a guide, so an agent that reads guides can enter any
environment knowing nothing."**

### What is real

- A document **is** a test suite in two dialects, and the author's printed output **is** an
  oracle. 189 examples in the previous round, 496 claims here, both replayed.
- Prose **does** compile to an executable witness, and the witness is strict enough to refuse
  161 claims as `CLAIM_IS_FALSE` — including `sort reverses the lines`, `gzip grows the size of a
  file`, and `cat sorts the lines of a file`. Wrong prose comes back wrong.
- The admitted relations are **content-invariant**: 51 of 57 held on a third room with different
  content and a different name. The six that did not are reported, not averaged away.

### What is false

- **"Prose is knowledge at scale."** 1.62% of prose sentences become an admitted relation. That
  is not because the extractor is weak — 7.5% of sentences even name a program-and-relation —
  but because a manual is mostly *options, portability notes and edge cases*, and an option is a
  claim about a flag, not about the program. `--help` already covers that dialect (57% claim
  yield there, because a help page is a catalogue of exactly those claims).
- **"The relation preserves the claim."** It does not, and cannot: the stored relation is
  `{program, kind, observable, relation, witness}`, so `ls lists each directory's contents
  alphabetically` is stored as `ls lists directory` and the word *alphabetically* is gone. The
  witness verifies a **coarsening** of the sentence. For a door that is enough; for a
  specification it is not.

### What is unproven

- That any of this yields capability on an unseen GUI or a hard SWE task. Nothing here touches a
  GUI, a browser, or a coding benchmark. The corpus is documentation about 37 CLI programs on one
  machine.

### Why one experience is not permanent competence

Because the relation is **content-invariant but environment-variant**, and the witness is re-run
at use. A relation admitted in one room can be refused in the next — that is what the third-room
transfer measures, and it is a measurement, not a guarantee. What survives an experience is the
**question** ("what experiment would decide this?"), not the answer. The store holds the question
plus the last witness that answered it; the next room re-asks.

---

## 3. The defects this round found in its own instrument

Each was a wrong admission or a wrong refusal, and each is held by a test in
`canonical/tests/test_the_right_question_is_an_experiment_v1.py` (59 cases).

| # | Defect | Symptom | Fix |
|---|---|---|---|
| 1 | A wrapped clause read as a sentence | `sort` admitted a claim from `natural sort of (version) numbers within text` | join physical lines into the author's statement |
| 2 | A program that is not the subject | `The locale affects sort order` became `sort sorts` | require the program before the verb |
| 3 | An option table read as prose | `cat counts lines` from `-b, --number-nonblank` | drop `@table`/`@optItem` blocks |
| 4 | A witness with no object | `tar` run bare, predicate over nothing | `WITNESS_IGNORES_THE_OBJECT` |
| 5 | A witness true of the null program | `wc counts` was true of `cat` too | `WITNESS_IS_TRUE_OF_A_NULL_PROGRAM` |
| 6 | Two relations, one witness | `computes` and `prints` both meant "stdout non-empty" | one experiment per name |
| 7 | A degenerate room | identical lines are trivially sorted, so `sort sorts` was false | unsorted + compressible + variant-stable bodies |
| 8 | Another program's grammar | `unzip --extract -f archive` (tar's operands) | read the usage line and the flag table |
| 9 | A help page read as lines | `-x` for "extract into exdir", `-Z` for "list" | split rows on two-or-more spaces |
| 10 | A decompressor handed the wrong stream | `bzip2 decompresses` refused about the room | the room speaks the claimed program's format |
| 11 | A binary stream written as text | `gzip -t` said "not in gzip format" about gzip's own output | bytes, not decoded text |
| 12 | Unbounded child output | `yes file` filled memory; the kernel SIGKILLed the measurement | `RLIMIT_FSIZE`/`RLIMIT_CPU` in the child |
| 13 | `@c` matched `@command` | every sentence naming a program was dropped from the corpus | exact comment match |
| 14 | A predicate true of nothing | `str(None) == str(None)` admitted `cp copies a directory` | presence, not truthiness |
| 15 | The subject matched as its own object kind | `bzip2` (5 chars) outvoted `file` (4 chars), claiming `bzip2` compresses `.bz2` | strip the subject occurrence before matching `KINDS` |
| 16 | `decompresses` paired with a plain `file` | `Compress or uncompress FILEs` set `object_kind = "file"` for both verbs | `_refine_kind("decompresses", "file") → "compressed"` |
| 17 | Lexical synonyms treated as disjoint nodes | `line → extracts` inserted `sort` just to coerce `line` to `file`, scrambling order | `_canonical_kind` maps kind via observed room artifact |
| 18 | Incompatible programs in an equivalence class | `gzip` followed by `bzip2 --decompress` type-checked on `compressed` and failed | `synthesize_plan` refutes incompatible pairs in the mental model |

---

## 4. The single next bottleneck

**The relation is a coarsening of the sentence, and the coarsening is where the value is lost.**
`ls lists each directory's contents alphabetically` is stored as `ls lists directory`: the
adverb is gone, so the store can open the door and cannot state the rule. 102 claims are refused
`RELATION_KIND_MISMATCH` and 33 `WITNESS_IGNORES_THE_OBJECT` — both are the same disease seen
from two sides, a claim whose object or operation the closed vocabulary cannot hold.

The move this round made is to **store the qualifier as a second, optional witness**: the
relation stays the door, and a qualifier (`alphabetically`) becomes a predicate the room can test
on the program's own output. A qualifier that no read-only sensor can decide is not extracted at
all — matching every `-ly` word made `only` a qualifier, and a word is not a test.

Measured on the corpus: **1 qualifier witnessed, 0 contradicted**. The manuals' adverbs are
manner (`normally`, `automatically`, `recursively`), not order, and manner is not decidable by a
read-only sensor over the output. So the qualifier mechanism is real and exercised by tests, and
it is not where this corpus's value is. That is a finding, not a gap in the mechanism.

**Rejected instead:** adding relations by hand (a vocabulary that grows with every corpus), a
learned qualifier model (a parameter that memorises world facts, which §2 forbids), and asking
the user (never).

---

## 5. What this is not

- Not a benchmark. One machine, 37 CLI programs, zero GUI, zero network at run time.
- Not a claim that prose is mostly checkable. The yield **is** the measurement, and it is small.
- Not a proof. A witness separated one wrong version, was false of one null program, and repeated
  on two more rooms; 6 of 57 were refused by a third. A fourth room may refuse the rest.
- Not a capability. A stored relation is external knowledge, labelled with its source and
  re-verified at use. `model_calls: 0`, `parameters: 0`, `spend_usd: 0`.

Receipt: `canonical/verification/THE_RIGHT_QUESTION_IS_AN_EXPERIMENT_20261124_V1.json`.
Tests: `canonical/tests/test_the_right_question_is_an_experiment_v1.py` — 59 cases, each a defect
above; `canonical/tests/test_perfect_algorithm_v1.py` still passes (23).
Prose corpus: fetched from the upstream manuals by `--fetch-prose`, cached machine-locally, never
committed; the receipt records each tarball's sha256.
