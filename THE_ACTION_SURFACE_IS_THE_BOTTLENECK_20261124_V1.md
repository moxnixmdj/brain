# The action surface is the bottleneck, not the reasoning

**2026-11-24 · branch `arena/0964738f-brain` · authority: NONE (producer-run sandbox measurement)**

The owner's proposal was: *one perfect algorithm that walks into an arbitrary environment,
scans it, asks the right question, retrieves what it knows, fetches the rest instantly, and
saves a generalization rather than a trace.*

That algorithm already exists in this tree (`canonical/swe_kernel/perfect_algorithm_v1.py`)
and it is not the limiting factor. **The environment interface it consumes is.** This
document measures that, removes the largest part of it, and refuses to call the result
completion.

---

## 1. The contradiction in the standing requirements, resolved

The standing laws forbid parameters that hold memorized world facts, and forbid any runtime
dependency on another model; they permit an external, inspectable store that the system
computes with. Adopted boundary, unchanged from the earlier resolution and re-verified
against this build:

| Layer | Status | Test applied |
|---|---|---|
| Weights | **0.** `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` declares `weights: 0` and the compiler has no training step. | Nothing in this work adds a parameter. |
| Rules / skills / ledgers | **External, inspectable, editable JSON/MD.** Knowledge can be added or deleted without retraining anything. | `DOOR_WITNESS_LEDGER_V1.json` is plain JSON; deleting it changes no code path. |
| Facts about the world | Acquired at the moment of need, never stored as weights. | No table of program names, flags or flag meanings appears in the search path — there is a test that forbids it. |
| Another model as producer | **Zero calls.** | The module imports no client; the receipt records `model_calls: 0`. |

The new artifact obeys the owner's boundary in the hardest case: it learns *how to search*,
not *what the world contains*, and every member of its alphabet is a value a POSIX program
can be handed on any machine in any locale.

---

## 2. What already exists in this project (searched by concept, not by filename)

The tree is 18,207 files. The load-bearing pieces for this question, including the
non-obvious names, are:

| Thing | Where | What it actually is |
|---|---|---|
| The whole compiled surface | `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` | 447 capabilities, 26 engines, 18 skills, 597 indexed documents, **0 weights** |
| One entry point | `canonical/runtime/brain_unified_model_v1.py` | route / recall / solve; fails closed off-domain |
| **The owner's idea, built** | `canonical/swe_kernel/perfect_algorithm_v1.py` (1,114 lines) | scan → ask → retrieve → fetch → plan → act → learn → admit → save |
| Learned transition model + planning | `canonical/runtime/environment_learning_v1.py` | canonical observation, BFS shortest plan, probe/restore |
| The machine's own declarations | `canonical/runtime/tool_census_v1.py` (1,939 lines) | parses each program's own help text into operations, binds, runs, classifies |
| **The machine publishes its own doors** | `canonical/tools/the_machine_publishes_its_own_doors_v1.py` | proves the census output can drive `scan()` with no hand-written action list |
| Instant learning, one demonstration | `instant_one_shot_learning_v1.py`, `one_demonstration_{reach,identifies,basin}_v1.py`, `contrastive_oracle_bootstrap_v1.py` | hill-climbing over hypotheses from a single run |
| The four "leaps" the owner named | `causal_dependency_repair_v1.py`, `language_neutral_skill_bridge_v1.py`, `egraph_and_deductive_synthesizer_v1.py`, `operand_invention_v1.py` | data-flow repair, language-neutral skill IR, e-graph synthesis, operand invention |
| Honest limits of one shot | `WHY_ONE_EXPERIENCE_IS_NOT_ENOUGH_20261116_V1.md`, `one_experience_is_a_point_a_chosen_contrast_is_a_boundary_probe_20261112.py` | one experience is a point; what it yields is a hypothesis plus the question that separates survivors |
| The environment probe | `canonical/runtime/environment_probe_v1.py` | act → snapshot → the DELTA is the signal, not the exit code |

**Names that do not exist in this tree, checked rather than assumed:** `Iteration 70/71`,
`BELIEFWEAVER`, `FOREIGN_IDENT_UNBOUND`, any `cJSON_Utils.c` case, and a "226 tricks" store.
The narrative those numbers come from is not this repository's history. What *is* here is the
machinery above, and it is further along than that narrative suggests.

---

## 3. Verdict on the proposal — what is real, what is not

**Real, and already built:** the shape of the perfect algorithm. Its loop is correct and its
docstring is honest about its own limits. Verification by execution, priors stored as an
environment model, rules admitted only after replay on instances they were not taught on —
all present.

**Real, and the actual blocker:** `scan(env, actions)` took its action set as an *argument*.
On an arbitrary machine there is nobody to pass it. `the_machine_publishes_its_own_doors_v1`
removed the hand-written list by reading programs' own help text — and then measured the
residue it left, and named it: *"It is not competence. Knowing 966 doors is not knowing which
one a request wants; that is the next question, and this file does not answer it."*

**Not real:** the claim that the agent could "know everything in a new environment from the
web." Measured here: the wall is not knowledge of the environment, it is **the ability to
invoke the environment's own programs at all.** No amount of web reading supplies that,
because the obstruction is an argument that has the wrong *form*, and the machine itself
answers that question for free.

**The owner's discriminating question — goal-directed or learn-everything — answered by
measurement:** *neither*. Learning everything is impossible (see §4: 52% of the machine's
declared surface cannot be driven by any of this, and 28% of it is one program with no
producer of its input on the machine). Learning only what the goal needs is impossible too,
because before you can ask "which door does this goal want", the doors have to exist as
runnable things. The correct unit of learning sits between them: **learn the FORM of a
declaration's slot, not the program, not the goal.** That unit is finite (nine rules covered
35 programs), transfers (six operations transferred to programs never seen), and is exactly
the "generalization, not the experience" the owner asked for.

---

## 4. The measurement that chose the work

`the_machine_publishes_its_own_doors_v1`, run here twice, every declared operation executed
as declared and the tree restored after each trial:

```
depth 2, 36 programs, 322 s :  5,760 declared | 219 DOOR | 1,189 SENSOR | 4,352 UNBOUND (75.6%)
depth 1, 36 programs,  26 s :    886 declared |  35 DOOR |   191 SENSOR |   660 UNBOUND (74.5%)
```

Of the 660 depth-1 unbound rows, **641 are `FAILED_NO_EFFECT`** — the process exited non-zero
and moved nothing. That is not a statement about the machine. Reading the machine's own stderr shows
one class:

```
grep --ignore-case in.txt          exit 1   in.txt is read as the PATTERN
grep --ignore-case alpha in.txt    exit 0
diff --normal in.txt               exit 2   FILES means two
diff --normal in.txt in.txt        exit 0
cut --bytes=out.bin in.txt         exit 1   BYTE-LIST, not a path
cut --bytes=1 in.txt               exit 0
tar --list --file=out.bin in.txt   exit 2   the trailing operand is not wanted
tar --list --file=<real archive>   exit 0
```

Every failure flips on the **form of a value**. The binder supplies one canned path
(`in.txt`) and one canned output (`out.bin`) for every slot in every program. The missing
mechanism was not knowledge. It was a search over a nine-member form alphabet, judged by the
machine's own exit code.

The frontier's own error taxonomy points at the same wall from the other side: Terminal-Bench
2.0's analysis attributes 24.1% of all failures to "command not found" (35.1% of execution
errors in the later ICLR 2026 reading) — *"an agent guessing what exists on a machine"*.
Frontier models fail because they cannot enumerate the machine. This system's failure was one
step later: it enumerates the machine and then cannot drive it.

---

## 5. The build: one part

`canonical/runtime/door_witness_search_v1.py` (744 lines, no parameters, no model calls).

```
FORM ALPHABET   in.txt  1  1-2  alpha  a.*  :  %s  in.json  real.tar  real.zip  out.bin
                + whatever artefacts the program itself produced (art0, art1, …)
MOVES           SUBSTITUTE a value inside --flag=VALUE or a positional operand
                DROP1/DROP2 the binder's over-supplied operand
                APPEND1/APPEND2 / PREPEND1/PREPEND2 operand placement, both orders
                COMPOSE two declared slots filled at once
JUDGE           the process exit code, then the program's own help text
LEARNED UNIT    a rule over the SLOT SIGNATURE  (required arity | value flags | optionals)
```

Nothing in the search path names a program, a flag or a meaning. The room is built from two
things and no third: the census's seed forms, and whatever the program's own declared
producers left behind.

### What was built, then removed, with the number that removed it

| Idea | Result | Disposition |
|---|---|---|
| Copy machine-made artefacts over `out.bin` (aliasing) | `tar` still dead: a producer that copies the seed passed the "did it read something" test and left a non-archive under the name every consumer reads | **removed** — artefacts get unique names and the *search* decides which is real |
| Run every operation to populate the room | 1,136 s on seven held-out programs; `wget`'s 136 network clients dominated | **removed** — only operations the census classed `WRITES` run |
| Add `COMPOSE` early in the move order | addressable fell 358 → 348: a bigger move set under a fixed budget buys nothing | **kept the move, moved it last** |
| Carry a *globally learned search order* from program to program | 344 < 358: what transfers is the signature rule, not the order | **removed** (recorded in the ledger as evidence, unused by the search) |
| Count `exit 0` as success | `convert -adjoin` exits 0 and prints its usage: **250 phantom recoveries** | **removed** — a usage dump is `INERT` |
| Then: treat *silence* as INERT too | `tar --diff` on an unchanged archive is a successful verification: 146 real recoveries thrown away | **reverted** — silence after exit 0 is a SENSOR |

That table is the honest core of this work. Each row was a plausible design that the machine
refuted in one measurement.

---

## 6. Results (producer-run, sandbox, authority NONE)

**Fleet — 35 programs, depth 1, 886 declared operations, 175 s. Two runs, and the
difference between them is the point:**

| | cold (empty ledger) | warm (ledger saved by the cold run) |
|---|---|---|
| DRIVEN as the census already bound them | 212 | 212 |
| RECOVERED by witness search | 157 | 70 |
| REUSED from a stored rule, **no trial spent** | 26 | **113** |
| **addressable = DOOR 42 + SENSOR 353** | **395 (44.6%)** | **395 (44.6%)** |
| RESIDUE, in **6** distinct signature gaps | 461 | 461 |
| INERT — exit 0, usage printed, refused | 30 | 30 |

**The identity that matters: the same 395 operations, reached with 157 searches the first
time and 70 the second, because 113 of them are now covered by a stored rule.** That is
instant learning with the only evidence that counts — a saved experience changing what the
next run has to do, with no retraining and nothing in the weights.

Against what the binder could reach on its own, the machine's usable action surface goes
**212 → 395 (1.86×)**, on nine learned rules and zero knowledge. Nine rules, not nine
hundred: that is the generalization the owner asked for.

**Held out (never searched while learning): `openssl`, `curl`, `wget`, `make`, `gcc`,
`zipinfo`, `unzip`, `zip`. 250 declared operations.**

| condition | addressable | of which by transfer alone |
|---|---|---|
| rules only, **zero search** | 64 (25.6%) | **6** |
| rules + search | 84 (33.6%) | — |

`unzip` 10/10 and `zipinfo` 7/7 recovered by search; `zip` inherited 6 operations from rules
with no trial at all. **Six operations of true zero-shot transfer is real and small.** Stated
plainly: the claim "learn one experience, transfer everywhere" is *partially* supported at
this layer, and the effect size is 2.4% of the held-out surface.

**Cost:** 168 s for 886 operations; median program under 5 s. No model calls, no network at
decision time, no parameters.

---

## 7. What still does not work — the residue is the honest output

Six signature gaps, and they are not all the same kind of thing:

| gap | operations | real cause |
|---|---|---|
| `arity=3\|values=1` | 250 (`convert`) | wants an **image**; nothing on this machine produces one, and the machine's own declaration says `geometry`, `color`, `filename` |
| `arity=0\|values=1\|option=1` | 155 (`tar`, `sort`, `sed`, `cut`) | structured values: tar labels, sed scripts, cut lists with delimiters |
| `arity=1\|values=1\|option=0` | 48 (`diff`, `stat`, `seq`) | a value that is one of a small set of **words** the program accepts |
| `arity=1\|values=1\|option=1` | 42 (`grep`) | the pattern and the file are both declared; the compose move reaches it but budget-starves |
| `arity=2\|values=1` | 18 (`comm`, `join`) | column numbers and a separator |
| `arity=2\|values=1\|option=1` | 5 (`timeout`) | a whole command line as one value |

`openssl` returns **0 operations at depth 1**: its help is a subcommand table with no usage
line, so the census has nothing to parse. That is a pre-existing gap in
`tool_census_v1`, not something this work introduced, and it is the single largest piece of
the machine (676 subcommand operations) that is still invisible.

---

## 8. Rejected, with reasons

- **A table of domain words** (`FILE` → path, `PATTERNS` → regex). It would have worked
  better on today's programs and made the mechanism dependent on English help text. The
  alphabet is searched instead, so it survives a localised machine and a GUI with no help
  text at all.
- **A produced-generalization store keyed by goal family.** The goal does not determine the
  form; the declaration does. Keying on the goal would have made the rules untransferable —
  which is precisely the failure the owner anticipated when they said saving the exact
  experience is dumb.
- **Wire this into `perfect_algorithm_v1.scan()` now.** Tempting, and it is the right join,
  but the census residue above is still 52%; wiring in a half-surface would make the loop
  look better while changing nothing about what it can reach. The join is the *next* step,
  not this one, and the API (`discover`, `operations_of`, `load_ledger`, `reuse_map`) is
  ready for it.
- **A neural or statistical policy over which move to try.** Nine rules over 886 operations
  do not justify one, and the cross-program order transfer measurably failed anyway.

---

## 9. The next bottleneck (single, chosen)

**`openssl`'s 676 operations are invisible to the census, and it is the same defect as the
52% residue: the census reads a program's help as a flat list of flags when it is a TREE
(program → subcommands → each subcommand's own usage line).** A machine where 676 of a
program's operations cannot be enumerated is a machine the agent cannot plan on, and the
subcommand tree is the most common shape in real environments (`git`, `docker`, `kubectl`,
`apt`, `systemctl` — every tool an SWE agent lives in).

The fix is not more search. It is to make the census *descend*: ask each admitted subcommand
for its own `--help`, and bind against the document that actually describes the operation.
Half of that exists (`interpretation_of_subcommand`-style paths and the `depth=2` walk); the
measured failure is at depth 1 with programs whose parent text has no usage line.

After that, in order: the six residue gaps as *typed witnesses* (a witness is a value the
machine accepts for one declared domain — image, word-set, column list), then the join into
`scan()`, then the first real Terminal-Bench 4.0 / OSWorld 2.1 task.

---

## 10. Not done

The mission is not done and this document does not claim it is. What changed:

- measured, for the first time in this tree, that the dominant blocker in an unseen
  environment is the **action surface**, not the reasoning loop;
- raised the machine's addressable surface 1.86x (212 → 395 operations) on nine rules and no knowledge, and showed a stored rule removing 87 of 157 searches on the next run;
- refused 30 fake successes that a naive `exit 0` test would have credited;
- produced one negative result worth as much as the positive ones: **a learned global search
  order does not transfer, a learned per-signature rule does.**

What remains: subcommand trees, typed witness domains, the join into the loop, and the
benchmarks. No benchmark score is claimed here, and no capability credit is taken.

### Files

| Path | Role |
|---|---|
| `canonical/runtime/door_witness_search_v1.py` | the mechanism |
| `canonical/tests/test_door_witness_search_v1.py` | 21 tests |
| `canonical/astra_runtime/state/DOOR_WITNESS_LEDGER_V1.json` | the nine learned rules |
| `canonical/verification/DOOR_WITNESS_SEARCH_FLEET_RECEIPT_20261124_V1.json` | the run |
