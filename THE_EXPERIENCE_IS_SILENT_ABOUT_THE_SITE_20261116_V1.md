# The experience is silent about the site

**Round 11 · 16 November 2026 · branch `arena/69e9029d-brain` · base `338568c9` (round 10 merged)**
Model calls 0 · network calls 0 · spend $0 · every execution a real commit's own test

---

## The question, in the user's words

> *Why can't we just give our model the most advanced coding actions and let him experience them once and
> then he will learn them? Can't we do this now?*

Rounds 9 and 10 answered the second half of this by measurement: the experience is available, it is cheap, and
it does not accumulate. Round 10 ended with a fact that should have been the whole answer — *a rewrite learned
from a real diff fails to fire at that very diff in four of five cases*. That said the representation, not the
experience count, was the limit.

This round went looking for the next layer down, and found something simpler and worse.

## First, the tree was searched before anything was built

The mechanism this round intended to construct — repair driven by the failing observation, with a vocabulary
induced at repair time — is already in the tree, and its own docstring names it:

```
canonical/swe_kernel/closed_loop_trace_abduction_repair_v1.py
"Closed-Loop Execution-Trace Abduction, Dynamic Vocabulary Induction & Counterfactual
 Falsification -- the $0 repair engine"
```

Trace slicing, Ochiai ranking, dynamic observables, assertion-case extraction, expression synthesis,
line-level replacement, degeneracy/perturbation/locality falsification — all present. It had been measured on
HumanEvalFix (58/100) and QuixBugs (20/40). It had never been measured on a real repository, and its
`Lessons` object had never been fed anything but benchmark bugs.

So nothing was rebuilt. The engine was handed the one thing it lacked: **edit-kind lessons learned from real
commits**, leaving each task's own repository out of its teaching set.

## Measurement 1 — the vocabulary fires, and it is parasitic

| condition | proposals per task | solved | executions |
|---|---|---|---|
| lessons from **other repositories' real diffs** | 30 | **0 / 7** | 90 |
| **empty** vocabulary (trace slice only) | **0** | 0 / 7 | 0 |

Two things at once. The engine's own dynamic-vocabulary path produces **nothing at all** on a real
repository file — every candidate it generated came from the learned edit kinds. And the learned candidates
never solve.

Reading the candidates explains both. They do not transfer a *meaning*; they transfer the syntax together
with the words of the place they were learned in. One candidate for `tomli/_parser.py` contains

```
... or pathlib.PureWindowsPath(path).drive
```

which is **packaging's operand**, grafted into a TOML parser. Another rewrites a docstring. The proposals
touched the real hunk and ninety unrelated lines at once. A lesson keeps the source's operands and loses its
point. That is why experience does not accumulate: what transfers is the sentence, not the argument.

## Measurement 2 — the failing run never touches the defective file

If the traceback could localise, the parasitic vocabulary would at least have a site. It cannot:

| commit | defective file | frames in that file | failure |
|---|---|---|---|
| 7f4dcf83 | itsdangerous/signer.py | **0** | error elsewhere |
| 022ae6c6 | packaging/metadata.py | **0** | `DID NOT RAISE` |
| 4b243af9 | packaging/requirements.py | **0** | error elsewhere |
| a1f70564 | packaging/licenses/__init__.py | **0** | wrong value |
| 12314bde | tomli/_parser.py | **0** | error elsewhere |
| 5ab9ec92 | tomli/_parser.py | **0** | error elsewhere |
| 96dfe2ce | tomli/__init__.py | **0** | wrong value |

**7 of 7.** In no case does the failing execution enter the file that has to change. The dominant failure
shape is not "it crashed here" but "**it did not raise**" — a check that is *absent*. Absence leaves no frame,
no value, no observable. The experience is silent about its own site.

This is round 8's observation wall and round 10's non-firing oracle, seen from below: both were the same
silence. It is also the mechanistic reason the user's proposal cannot work as stated. Learning needs a
signal; for a missing check the signal is not in the failing run.

## Measurement 3 — where the signal actually is

One place still carries information: the failing test **ran**, and it ran with a specific input.

Every parametrized case in `packaging`'s suite is a value of `license_files`. The failing cases are
`C:LICENSE` and `d:secrets/key.txt`; the passing siblings are `../LICENSE`, `licenses/*`, `/licenses/LICENSE`
and five more. A predicate that is true on all failing values and false on all passing ones *is* the missing
check. Enumerating candidate predicates over the target file's **own imports**, by real introspection
(`getattr` on the actual `pathlib` module — no model, no network, no list written by hand), yields
**exactly one**:

```
pathlib.PureWindowsPath(x).drive
```

— which is the operand the real commit introduced. Bound to the seat's own loop variable and adjoined to the
guard inside `_process_license_files`, it raises `InvalidMetadata` exactly where the test requires:

| | |
|---|---|
| commit | `pypa/packaging` 022ae6c6 |
| predicate found | `pathlib.PureWindowsPath(x).drive` (unique) |
| seat | line 766, `if ".." in path` inside `_process_license_files` |
| bound name | `path` (that function's own loop variable) |
| executions | **1** |
| result | **344 tests pass** |

The other six commits are refused with a named reason — no separating predicate exists in the attribute space
of the modules they import, or their parameters are not literal `parametrize` tables. A refusal is a
measurement, not a failure to try.

Two mistakes were made and are recorded because they are the kind that would recur: the negative set was
first built as "all cases other than this one", which put the *other failing case* inside the negatives and
made every real predicate look non-separating — it returned nothing, silently. And the term was first bound
by string substitution that produced `pathlib.PureWindowsPathpath.drive`. Both are now tests.

## What this says about the question

**"Give it the advanced coding actions, let it experience them once, and it will learn them."** — False, and
now for a reason that can be pointed at:

1. the actions it would learn are represented as *edits*, and an edit transfers its source's words, not its
   meaning (measured: 0 of 90 candidates solve, one carrying another repository's operand);
2. the failing run contains no reference to the site it fails at (measured: 0 frames in the defective file,
   7 of 7), so there is nothing to attach the lesson to;
3. the operand that the fix needs is usually **absent from the file** — `PureWindowsPath` and `.drive` appear
   nowhere in `metadata.py` — so no amount of experience *with other diffs* can supply it.

What does supply it is the environment, and the environment is already enough: the module the file already
imports contains the word, and the test's own failing input says which predicate is missing. Three absences
in the experience, three presences in the world.

**"Can't we do this now?"** — Partly, and the part is new. One real fix commit of seven was solved by
construction — not replayed, not retrieved — with zero model calls, in one execution. The route is
`test input partition → separating predicate over the target's own imports → adjoin at a real seat under the
commit's own tests`. Nothing in it reads the commit's diff.

## Honest limits

- **1 of 7**, on the seven tasks where trees could be prepared. Six refusals, each named.
- The solved candidate lands on a *neighbouring* guard, not the commit's own line. The test requires
  `InvalidMetadata` and never says which guard must raise it, so the test **underdetermines the seat** — the
  identifiability wall again, now with a constructive edge: the failing input supplies the predicate even
  when it cannot supply the site.
- The predicate search covers attributes of classes the target imports. A fix needing a name from a module
  the file does *not* yet import would still be invisible, and would require reading the wider repository.
- Producer-run sandbox only; authority **NONE**.

## The single bottleneck, after this round

Not binding, not argument construction, not observation, not synthesis, not shape. It is:

> **The failing observation must be made to name the missing check, because for guard-omission bugs it names
> nothing at all — and the only surviving evidence is the partition of the test's own inputs, which fixes the
> predicate but not the seat.**

The next organ therefore does not learn from history and does not search a grammar. It reads the assertion's
intent — *which value is compared, and what a raise would protect* — and picks the seat that preserves every
passing case. That is a specification-reading problem, not an experience problem, which is exactly why more
experience has never helped.

## Files

- `canonical/swe_kernel/real_commit_repair_v1.py` — the engine, fed real-commit lessons, measured with a control
- `canonical/swe_kernel/operand_invention_v1.py` — failing-input differential, introspective operand supply, seat binding
- `canonical/tests/test_operand_invention_v1.py` — 12 tests, including both mistakes above
- `canonical/verification/REAL_COMMIT_REPAIR_20261116_V1.json`, `canonical/verification/OPERAND_INVENTION_20261116_V1.json`
- `canonical/action_intents/OPERAND_INVENTION_FROM_FAILING_INPUT_20261116_V1.json`
- reused unchanged: `closed_loop_trace_abduction_repair_v1`, `edit_kind_learning_v1`, `history_induced_edit_grammar_v1`, `structural_rewrite_induction_v1` (corpus preparation)
