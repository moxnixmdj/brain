# The Witness: what the agent must know is what its goal can see

**Date:** 2026-11-23 · **Branch:** `arena/eac85348-brain` · **Base:** `68bf0400`
**Authority:** NONE__PRODUCER_RUN_SANDBOX · **Model calls:** 0 · **Network:** 0 · **Parameters:** 0
**Instrument:** `canonical/runtime/interrogation_v1.py` · **Tests:** `canonical/tests/test_interrogation_v1.py` (25 passed)
**Receipt:** `intake/RECEIPT_INTERROGATION_20261123_V1.json`

---

## 1. The requirements I am bound by, restated before acting

Own model, own runtime, zero model calls at runtime; no parametric world-fact warehouse; every
parameter computed and justified; instant knowledge from an external, inspectable, deletable
store; one experience in an unseen environment; hardest honest tests; no borrowed output, no
leakage, no hand-solving; research the project and the frontier first; kill bad ideas before
building them; one minimal plan; verified / unverified / failed separated; `truth.achieved`
stays `false`.

**The §2 contradiction, resolved the same way as every earlier round, and re-tested here.**
Forbidden: parameters as a lookup of memorized facts, and any runtime model call. Allowed: an
external store the system computes with, written from a single experience. The test is
*can the store be edited without retraining*. Everything this round writes is JSON keyed by
`(the tool's bytes, the invoked name, the surface form, the goal's observation domain)`. Delete
the file and the system re-derives it in seconds. The boundary holds; this round does not move
it.

---

## 2. What the project already had, and what it had already proved *false*

Searched exhaustively before building, including the non-obvious names (`perfect_algorithm_v1`,
`ignorance_loop_v1`, `contrast_selection_v1`, `environment_basis_v1`, `one_shot_identifiability`,
`the_environment_broker_v1`, `scan_retrieve_fetch_v1`, `compose_a_host_never_seen_v1`).

What is **real and reused**:

| instrument | what it established | how this round uses it |
|---|---|---|
| `scan_retrieve_fetch_v1` | the memory key must be `(content digest, invoked name)`; `/usr/bin` has 635 names for 481 files and `xz`/`unxz` are byte-identical and opposite | the memory key here is the same shape, extended by the goal |
| `exact_information_gain` | information gain comparable in exact rationals, no floats, no epsilon | used to rank questions and to report the exact order next to the heuristic one |
| `contrast_selection_v1` | "identical repeats add no information; choose the state that splits the survivors" | the same principle, made exact and minimax instead of eager-greedy |
| `the_environment_broker_v1` | a declaration is cheaper and harder to fake than a description; memory must be re-checked, never believed | the same law applied to a *behaviour* instead of a maniest |
| `WHAT_TO_SAVE_20261121_V1` | save the typed fact and the named refusal; never chains, bytes, or names | the same rule, with the type now read from a closed algebra |

What the project had already proved **false**, and this round did not re-test:

1. *"One demonstration identifies."* 14.1 of 47 hypotheses survive; 0/10 identified.
2. *"A lesson learned from a diff transfers."* 0 solved in 90 executions.
3. *"Learn everything eagerly."* OOM-killed twice; negative transfer; 0/164.
4. *"An unguarded commit can be made checkable."* 0 of 6.

And the sentence that named this round's bottleneck, from `THE_BOTTLENECK_IS_NOT_LEARNING`:

> "The disambiguating input is itself knowledge, and nothing manufactures it."

---

## 3. The frontier, read as input only

Everything below is an input to a design; none of it is a runtime dependency.

- **OSWorld 2.1** (108 long-horizon workflows, median human time ~1.6 h, ≥250 agent steps):
  best published *binary* completion 48.7% (Claude Opus 5.5, max effort), partial 81.8%. The
  gap is attributed to tracking constraints, catching mid-task changes and verifying work —
  not to basic GUI control.
- **Terminal-Bench 4.0**: leader 64.8% ± 3.1%. 2.x is saturated (87–92%) and not comparable.
- **Agent-Diff** (arXiv 2602.11224, Apr 2026): documentation improves pass rate +7.0 pp but not
  partial-credit score, and *hurts* on one service; agents with no docs at all still lead,
  because they discover endpoints by probing. That is evidence for probing over reading.
- **"Sampling Is Not Curiosity"** (arXiv 2611.10501, 19 Nov 2026, a position paper): nearly all
  current agents only *sample* — they vary temperature or take best-of-N and never estimate
  which test reduces uncertainty most, and none originates its own inquiry targets.
- **"Wild Guesses and Mild Guesses in Active Concept Learning"** (arXiv 2602.06818): eager
  expected-information-gain selection proposes queries outside the region it can realise.
- **GNU `sort -V`**: the comparator is documented as *not transitive*.

Those last two are the design pressure this round responds to: information gain must be
computed over *realisable* questions, and a mechanism a system cannot specify exactly must not
sit in its hypothesis space.

---

## 4. §3 verdict: what is real, what is not, and the one real bottleneck

**False — "the agent should learn everything in the environment."** Re-measured here as a
design-space question: a candidate universe of 173 readings over two transform families
collapses to 36 behaviours, and a full sweep of a host's line/JSON filters costs seconds but
buys only 10 held-out-verified surfaces out of 158 examined (10 certified and survived, 1
certified and falsified, 5 not identifiable, 141 refused by name). Learning everything is not
a strategy; it is a cache.

**False — "instant learning is solved."** It is not, and the reason is sharper than "one point
is not a rule". In this round a *hand-built* model of eight Unix comparators was wrong **eleven
separate times**: the numeric key was parsed from anywhere in the line instead of the start,
the tie-break was removed on a plausible story and the program disagreed on the very first
input with a repeated key, the dictionary key used Unicode `isalnum` where the pinned C locale
uses ASCII, the version comparator's blank-line and punctuation rules were each wrong, JSON
input was treated as outside a line filter's domain, a composed pipeline over JSON was kept as
a "hypothesis" it could never be, and an argument-taking form was "certified" from a usage
error it produced on every shape. Every one of these was found by running the real program,
and each produced a confidently wrong certificate first. That is the honest size of the
problem: the mechanism that turns a run into a fact is where the errors live.

**True — the owner's idea, in a precise form the measurements support.** The smartest thing in
the message is not "learn everything" and not "be goal-directed" as poles. It is the middle
term the message kept circling: *know what you know and what you don't, and ask for only the
part of the difference that matters.* That is exact, it is cheap, and it is what closed the
0-of-6-checkable gap — because **a disambiguating input does not have to be knowledge at all.
It can be a witness, and a witness is computable from the competing readings the interface's
own words produced.**

**The invariant that makes it finite, and that no earlier round stated:**

> A distinction the goal cannot observe is a distinction the agent need not resolve.

So a surface is *known* when every surviving reading prints the same thing on every shape the
goal can produce. Not when the reading is the truth — that question is unanswerable and always
will be. The measurable question is the only one that matters.

---

## 5. The build: one mechanism, five parts, each with the measurement that justifies it

`canonical/runtime/interrogation_v1.py`. Nothing in it branches on a tool's name.

**The algebra (a closed vocabulary, not a table).** Thirteen total functions over bytes — four
line orders (lexicographic, numeric, dictionary, month), their descending forms, adjacent
dedupe, global dedupe, line count, run-length counting, three counted quantities, two JSON key
orders, and identity/reject. A reading is a pipeline of at most two. Each primitive declares
the input kinds it is defined on; a pipeline is defined on the intersection. That one
declaration deletes an entire class of nonsense: a JSON transform stacked on a text transform
has an empty domain, is not a hypothesis about anything, and is removed from the universe
rather than left to sit there. Composition is then canonicalised (a sort absorbs what follows
it; a JSON reading absorbs a text one), which is why **173 spellings become 36 behaviours** and
why an exact minimax search is affordable at all.

**Declarations are a refusal gate, not a constraint.** The surface's own help line is read for
verbs in the algebra. A line naming nothing in it is refused by name (`-b`, `-f`, `-i`, 88 of
158 surfaces here). A form whose own declaration demands an argument is refused by name (51 of
158), because running it produces a usage error on *every* shape — which every reading
"predicts" as a rejection, and a first version of this file certified `nl -n` in one probe that
way. The line must be the one that *declares* the flag: `uniq --help` mentions "sort -u" in a
footnote, and a version of this file read the footnote as `uniq -u`'s description.

**The scan is a control, not a census.** The default form is run once per shape. Its job is
attribution: `jq -S` exits 4 on text because *jq* cannot read text, not because of `-S`. Without
that control, "the form rejected the input" and "the interface cannot read the input" are one
observation — the same confusion `bzless` once caused by inheriting `bzip2`'s help page.

**The right question is chosen by exact minimax, and the alternative is reported.** The optimum
worst-case number of witnesses is computed by search over the finite partition lattice:
`depth(S) = 1 + min over shapes of max over outcomes depth(branch)`. Greedy information gain is
then played out *honestly* on the same table — as a worst-case tree, with silent readings
surviving outcomes — and compared. On this design space both agree: **4 witnesses worst case,
against 12 shapes a naive agent would run.** Two earlier baselines under-reported at 2 by
measuring a single path instead of a tree; they were replaced, because a flattering baseline is
worse than no baseline.

**Falsification is part of the loop, not an audit.** A certificate says the survivors agree *inside*
the design space. Every known falsehood in this build passed that gate. So a second, adversarial
held-out set (adjacent repeats, month names, punctuation and case, multi-byte text, leading
blanks, nested JSON, digits in words) is run against the real program, and the class is checked
member by member. A single disagreement is reported as `FALSIFIED__HELD_OUT_DISAGREES`, and
**memory does not accept the record**. That gate is what caught the last two bugs: a vacuous
`identity` class for `uniq -u`/`fold -b` (no shape in the space had adjacent duplicates), and
`sort -V`.

**Memory is believed only after it is re-derived.** Key: `(tool bytes)[:16] : invoked name :
surface form : goal shapes`. Recall re-runs the 2–4 witnesses that certified the surface and
discards the record as `STALE` if any of them disagrees. Measured on four surfaces: cold
certification 5.52 s total (one surface pays the exact-search cost; the search result is cached
per design space), warm recall of all four records **0.12 s**, tampered record refused.

---

## 6. The measurements, and the failures reported as failures

**Design space:** 12 shapes, 173 readings, 36 behaviours, worst-case optimum 4 witnesses
(greedy 4), naive 12.

**Host sweep — 158 declared surfaces across 20 GNU text filters:**

| outcome | count |
|---|---|
| CERTIFIED and survived 15 held-out inputs | **10** |
| CERTIFIED and falsified out of space | **1** (`fold -b`) |
| OPEN / NOT_IDENTIFIABLE (named) | **6** |
| REFUSED by name (no reading in declaration / form takes an argument / cannot run) | **141** |
| witnesses spent to certify 11 surfaces | **25**, against **132** if every askable shape were run |

The ten verified, with their measured cost:

| surface | witnesses | worst-case bound | equiv class (surviving) | held-out |
|---|---|---|---|---|
| `sort -n` | 2 | 4 | `sort_num` | survived |
| `sort -g` | 2 | 4 | `sort_num` | survived |
| `sort -d` | 4 | 4 | `sort_dict` | survived |
| `sort -M` | 3 | 4 | `sort_month` | survived |
| `sort -r` | 4 | 4 | `sort_lex_desc` | survived |
| `uniq -c` | 2 | 4 | `count_runs` | survived |
| `wc -c` / `-m` | 1 | 4 | `count_bytes`/`count_chars` | survived |
| `wc -l` | 2 | 4 | `count` | survived |
| `wc -w` | 2 | 4 | `count_words` | survived |

**A second, independent implementation.** The same mechanism, with no per-tool change and a
declaration taken from that implementation's own help, certifies busybox's `sort -n` and
`uniq -c` with the same equivalence classes and the same held-out survival as GNU's:

| implementation | argv | class | held-out |
|---|---|---|---|
| GNU coreutils | `sort -n` | `sort_num` | survived |
| BusyBox 1.36.1 | `busybox sort -n` | `sort_num` | survived |
| GNU coreutils | `uniq -c` | `count_runs` | survived |
| BusyBox 1.36.1 | `busybox uniq -c` | `count_runs` | survived |

**Failures, stated as failures:**

- **`fold -b` was certified and is wrong.** Its declared line ("count bytes rather than columns")
  names a *count*, and on the design space the count reading and identity are indistinguishable
  because no shape is longer than the default width. Held out, the surface passes long lines
  through unchanged. This is the strongest counterexample to the current algebra and it is
  reported, not excused.
- **`sort -V` was removed, not approximated.** Three implementations (a regex-tuple key, a
  two-key comparator, gnulib's `filevercmp` with the blank-line and version-string rules) were
  each falsified on held-out inputs — six disagreements in sixty randomised inputs on the
  third. The cause is structural: GNU documents the comparator as *intransitive*, and no
  key-based sort can reproduce an intransitive comparator. A part the system cannot specify
  exactly must not sit in its hypothesis space, because its presence manufactures false
  certificates. It is refused by name.
- **`jq -S` remains OPEN inside a 6-probe budget.** jq 1.6's help never describes the *rendering*
  it applies, so the prettifying must be inferred from runs; the budget stops before the class
  collapses. Reported as a budget, never as knowledge.
- **Six surfaces are honestly NOT_IDENTIFIABLE**: `sort -R` (random), `uniq -u`, `nl -p`,
  `od -a`, and the two above. Each needs a primitive the algebra does not have; the honest
  request is a wider type, which is a question for a document or an operator.

---

## 7. The one ultimate plan, with the rejected ideas and the measurement that killed each

The loop, and nothing else:

1. **Read the declaration** for the surface in question (`--help`, the line that declares it).
   Refuse by name if it names nothing in the algebra or demands an argument.
2. **Scan** the default form on the goal's shape domain — once, as a control.
3. **Enumerate** the readings the declaration admits, over an algebra whose primitives declare
   their domains.
4. **Ask the exact-minimax witness** over unasked shapes; stop the moment every survivor agrees
   on every shape the goal can produce.
5. **Falsify out of space** on adversarial inputs; a disagreement means do not store.
6. **Store** keyed by `(bytes, name, surface, goal)` with its evidence; **re-run the evidence on
   every reuse** and discard the record if it disagrees.

| rejected | the measurement that killed it |
|---|---|
| Predict the form's output from the default output | `sort -u`'s default is already sorted, so every derived prediction agreed and the surface was certified in zero probes as the wrong function |
| A larger hand-written primitive set | 11 comparator bugs in 8 primitives; the errors are in the mechanism, not in the count of parts |
| Greedy information gain as the choice rule | it agrees with the optimum here (4 vs 4), so it is not *wrong*, it is simply unproven; the exact minimax is kept because it is provable and costs the same |
| Naive "run every shape" | 12 witnesses against 4, measured |
| Learn every surface eagerly and generalise later | 10 verified out of 158 examined, and 141 correctly refused; breadth is the cache, not the strategy |
| Keep `sort -V` with a caveat | falsified three times on real inputs; a caveat on a mechanism that cannot be specified is a licence for false certificates |
| Trust the declaration's named reading | `sort -u`'s line says "unique" and the surface does a sorted global dedupe; `fold -b`'s line says "count" and it counts nothing. The words are a hint and a gate, never a conclusion |
| Write to memory before out-of-space falsification | every false certificate this round passed the in-space gate; the store would have filled with confident falsehoods |

**Expansion-rule test for the two expansions this touches.**

*GUI/browser surfaces.* ① Nothing in the storage boundary changes: still external, digest-keyed,
re-checked. ② The skeleton is identical — declaration, scan, witnesses, held-out, store — with
the declaration being the accessibility tree or the DOM instead of `--help`. ③ No new part that
fails either test: the same algebra would need visual primitives, which is a real addition, and
it is **not claimed here**. ④ Discipline: refuse by name anything whose observation domain is
not declared. ⑤ Constraints hold (zero model calls, zero parameters-as-facts). ⑥ **Not
verified**: this sandbox has no display, so a GUI result would have to be run elsewhere and is
not claimed.

*Web as the instant-knowledge source.* Unchanged in shape, and still bounded by what was
measured in the previous round: the machine-readable tier answers existence, version and
digests; prose does not answer anything a zero-model-call system can check. Nothing here
depends on the web.

---

## 8. Honest state, and the next bottleneck

- **Verified this round:** a closed algebra over line/JSON transforms, a declaration gate that
  refuses 141 of 158 real surfaces by name rather than guessing, an exact minimax witness
  selection with an independently checked optimum (4 vs naive 12), an adversarial held-out gate
  that caught two live falsehoods, and a memory that re-derives itself in 0.12 s for four
  surfaces and refuses tampering. Two independent implementations agree.
- **Unverified:** anything about GUIs, browsers, or images; any claim that this algebra
  transfers to a surface family whose transforms are not textual; and any claim about
  OSWorld 2.1, Terminal-Bench 4.0, or SWE-bench-class results. **No frontier benchmark was
  attempted**, because nothing in this build is a computer-use agent: it is the mechanism one
  would need before such an agent can act in an environment it has not seen.
- **Failed:** one certified-then-falsified surface (`fold -b`), one primitive removed
  (`sort -V`), and eleven comparator bugs found and fixed.
- `truth.achieved` remains `false`.

**The next bottleneck, named so the next round does not have to rediscover it.** The algebra is
the limiting factor now, not the search. Six surfaces are NOT_IDENTIFIABLE and `fold -b` was
certified wrongly, all for the same structural reason: a primitive is missing, or a primitive's
declared domain is a guess about a *display* property (width, columns) that no byte-level shape
can observe. The measure that would move it is a shape domain derived from the goal rather than
declared by hand — for a wrapping surface, the domain must contain a line longer than the width
the declaration implies. That is the same invariant as §4 applied one level up: **the shapes are
part of the hypothesis, and they must be falsifiable too.** Until shapes are derived from the
goal's own output distribution, every design space will be exactly as good as the person who
chose it.

---

## Reproduce

```sh
# the suite
/tmp/bv/bin/python -m pytest canonical/tests/test_interrogation_v1.py -q      # 25 passed

# one real surface, end to end: certify, falsify out of space, store
python3 - <<'PY'
import sys; sys.path.insert(0, '.')
from canonical.runtime import interrogation_v1 as I
line = I.declaration_line(I.help_text('sort'), ('-n',))
surface = I.Surface(tool='sort', base=(), form=('-n',), words=line)
memory = {"schema": I.MEMORY_SCHEMA, "entries": {}}
out = I.certify(surface, memory=memory, memory_path='/tmp/m.json')
print(out['status'], out['result']['witnesses'], out['held_out']['status'], out['stored'])
PY
```

Authority `NONE__PRODUCER_RUN_SANDBOX`. Zero model calls, zero network calls at measurement
time, zero stored parameters.
