# The verification half is free. The synthesis half is empty.

*Round 9. 2026-11-16. Branch `arena/415fa359-brain`, base `9ee703a8`.*

## Your question, and the answer this round produced

> Give the model the smartest coding actions, let it experience each once, and it learns them permanently.

Round 8 established the first half of that as **true where it can be measured**: an environment that runs its
own tests hands over 73.7% of the actions no scalar witness could ever reach, twice-stable, for $0.

This round asked the question that decides whether *learning actions* can ever become *doing new work*:

> Can an edit grammar **read out of real repository history** produce a real fix — and when it cannot, is the
> failure the **grammar** or the **search**?

The answer, measured on real commits with real tests:

> **0 of 6 real fixes solved, in 62 executions, for $0 — and not one of the six failures is a search failure.**

That is the synchronous, hard number this series has been walking toward for nine rounds. It is not a defeat;
it is the first time the wall has been *named in the right place*.

## What was already in the tree (research exhaustion, before building)

- `induced_edit_basis_v1` states the defect in its own words: the repair machinery enumerates a **hand-written
  operator list** and *"that list decides everything, and it decides it BEFORE any search happens"*.
- `python_test_guided_patch_search_v1` already applies, judges, and restores candidates under a test gate.

Neither had ever been measured on **real commits**. So this round adds **no operator list**: the grammar is
induced from real diffs (`induce_templates`, reused, not rebuilt), and for every task it is induced **only from
other repositories' commits** — leave-one-repository-out, so a task can only be solved by an edit nobody in its
own repository taught.

## The corpus is real, and it is gated by execution

- Source: the last 600 commits of `pypa/packaging`, `pallets/itsdangerous`, `hukkin/tomli`.
- Rule: one source file and one test file changed; the commit's own test file must **fail at the parent** and
  **pass at the commit** — verified by running pytest, not by reading the diff.
- 73 candidates mined, **6 pass the gate**. The rest are excluded for honest reasons (packaging's tests import
  dependencies this sandbox does not have; the others already pass at the parent, meaning they changed tests,
  not behaviour).
- Six tasks from one repository is a **ceiling statement about the grammar**, not a benchmark score. Saying
  otherwise would be exactly the self-congratulation you warned about.

## The measurement

| | |
|---|---|
| real fix commits (fail at parent, pass at commit) | **6** |
| grammar templates, induced from the other two repos only | 73 |
| hand-written edit operators in this file | **0** |
| search budget per task | 400 executions (**exhaustive** over the grammar's firings — tomli's tests run in 0.02 s, so budget could not be the excuse) |
| **solved** | **0 / 6** |
| executions spent | 62 |
| runtime traceback sites found | **0 of 6** |

## The decomposition — where the failure actually lives

Because the commit's own edit is *executed* (not merely matched), every task lands in exactly one bucket:

| state | n | meaning |
|---|---|---|
| `COMPOSITE_EDIT_REQUIRED` | **2** | the commit's edit **is** a grammar template, it fires at the right place, and applying it alone does **not** pass — those commits changed more than one node |
| `NOT_EXPRESSIBLE` | **2** | the commit's edit is not a template in the basis at all — it changes the **shape** of an expression, which the inductor already classifies `NON_EXECUTABLE` |
| `REFUSED__NO_TEMPLATE_FIRES` | **2** | no template's precondition holds anywhere in the file |

**Zero search failures. Zero.** The choosing problem — the one everyone else solves with search — is not the
problem. The *proposing* problem is the problem, and a grammar of operator swaps cannot propose a shape change.

## A second finding, quiet but consequential

**No runtime traceback site exists for any of the six.** Every one of these real fixes is asserted on a
*message* or a return value inside the test, so the exception is captured by `pytest.raises` and never
propagates out of the source file. Localisation for this class of task cannot come from a traceback — the
"runtime traceback exception" the insufficiency certificate named as the missing observable is, here, simply
absent by construction. It has to come from the *asserted value*, matched against the code that produced it.

## Why the 2026 literature agrees, and why it does not settle it

- **PSearch** (2026) fixes 201/835 Defects4J and 54.67% on SWE-bench-Lite — but every candidate it searches
  comes from a 480B model. Search is its **selector**, never its generator. That is the same asymmetry, paid
  for with a model.
- **Vanilla LLM repair** sits at 37.67% on SWE-bench-Lite: the model *is* the grammar, and it is expensive,
  opaque, and unverifiable except by execution.
- **TraceRepair** (2026, 392 Defects4J fixes) names its carrying object "runtime facts as shared constraints" —
  the observation half this tree already owns, free.

So the field's answer to "where do edits come from" is *a model*. Ours has just been measured as *nothing yet*.
Both statements are now falsifiable; only one of them costs compute.

## What is real, what is not

**Real**
- Verification is a solved, free, exact primitive here: 62 executions, byte-exact restore after every candidate,
  a real test from a real commit as the only judge.
- Template transfer across repositories is real but **narrow**: 73 templates, and they fire — 2 of 6 times at
  the right kind of site — but a single firing is not a fix.
- The failure is **grammar**, and it is countable: 2 composite, 2 shape, 2 no-site.

**Not real**
- "Experience the action once and it is permanent" → still true only for **observing**. Nothing in this round
  composed a new edit, so permanence of *actions* has not been shown to imply capability.
- Any claim that a bigger budget or better localisation would have solved these. The budget was exhaustive and
  localisation was irrelevant: 6 of 6 had no runtime site to localise from.

## The single bottleneck, now named exactly

**Edit proposal — and specifically SHAPE CHANGES.** The commits the grammar cannot express are the ones where a
name becomes a call, a branch becomes a guard, a literal becomes a computed value. A truly ultimate solution
cannot enumerate those either. It must read them out of the environment, exactly as rounds 7 and 8 did for
arguments and observations — and the raw material is already in hand and currently **thrown away**:
`induced_edit_basis_v1` classifies those diffs `NON_EXECUTABLE` and discards them.

The next organ, therefore, is not a bigger operator list. It is a **shape-rewrite learner**: take the
`NON_EXECUTABLE` diffs the inductor already collects, generalize them into structural rewrite rules (pattern →
replacement, with holes), and accept a rule only when an execution moves a real failing test to passing. The
measurement is the same one used here, on the same corpus, so the comparison will be exact rather than
rhetorical.

## Where the series stands

| round | organ | result |
|---|---|---|
| 1 | experience → actions | cost law; `p_correct` 0.2978 |
| 2 | differential pins | 13 drivable, 0 pins |
| 3 | structure → laws | 188 laws, 0 kills |
| 4 | instruction → contract by occurrence | site missing |
| 5 | site by intervention | 1 of 40 usable |
| 6 | permanence on real releases | 31% move, all loud; 39% never learnable |
| 7 | arguments from the environment's proofs | 1 of 41 (2.4%): lookup is capped |
| 8 | observation by the environment's own execution | **28 of 38 (73.7%) reached; 22 move, both sides recorded** |
| 9 | **edit synthesis from history, verified by execution** | **0 of 6, all six failures in the grammar** |

Nine rounds, one continuous movement: from *what can be known* → *what can be seen* → *what can be changed*.
The first two are now solved, cheap, and exact. The third has a working judge and an empty grammar — and, for
the first time, an exact statement of what that grammar is missing.

*Reproduce:* `python canonical/swe_kernel/history_induced_edit_grammar_v1.py --corpus /tmp/corpus9/tasks.json
--json canonical/verification/HISTORY_INDUCED_EDIT_GRAMMAR_20261116_V1.json` (62 executions, no model, $0).
