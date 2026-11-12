# The gate asks whether a file was written

**2026-11-12.** Base `6a5936b9`. Branch `arena/7cb4cbf4-brain`. Round 5.

Round 4 found seven adapters that assign `output_verified: True` unconditionally and called them
"weak gates". This round reads them, and the reading is worse than the label.

The seven share a shape. Here is one, compressed exactly as it appears in the tree:

```python
result = {"status": "PASS__…" if winner else "OPEN__NO_VERIFIED_REPAIR_IN_STRICT_OR_COUPLED_BOUNDS",
          "pass": winner is not None, ...}
out.write_text(json.dumps(result))
result["output_verified"] = True
return result
```

The adapter computes the answer and puts it in **`pass`**. Then it writes the result to disk,
marks the artifact verified, and returns. A run that found nothing writes its "nothing", marks it
verified, and satisfies the registered acceptance predicate:

```json
"expect": {"type": "field_equals", "field": "output_verified", "value": true}
```

**The gate answers "was a file produced?" while the answer to "was the problem solved?" is two keys
away, already computed.** That is the mechanism behind the 5/5 false success this repository spent a
session repairing by hand. It is not a mystery and it is not subtle; it is a predicate pointed at
the wrong field.

Authority **NONE**. Static analysis of source text at this commit. Nothing executed. $0, zero model.

---

## 1. The measurement

`acceptance_predicate_target_probe_20261112.py` classifies every bound capability by which question
its predicate asks:

| class | count |
|---|---|
| `READS_INDEPENDENT_CHECK` — a digest comparison or a recomputation | 4 |
| `READS_OUTCOME` — the predicate field is itself an outcome | 24 |
| `READS_TRANSPORT_OUTCOME_AVAILABLE` — reads existence, while an outcome is computed | **55** |
| `READS_TRANSPORT_NO_OUTCOME` — reads existence and computes nothing better | 44 |
| `READS_NEITHER` | 18 |

Of the 55, only a strict subset is unambiguous: the predicate reads a transport field, the adapter
computes a **boolean** outcome, and the capability **declares** that boolean in `result_fields`.
Nine qualify.

```
python.software.repair.loop.coupled.ast.v1
python.software.repair.loop.strict_progress.ast.v1
python.software.repair.loop.test_guided.ast.v1
python.software.repair.guided.provenance.coupled.v1
python.software.repair.measured_acceptance.v1
python.software.repair.semantic_acceptance.v1
python.patch.search.test_guided.ast.v1
python.software.request.semantic_behavior.compile.v1
python.task.acceptance.measured.objective.v1
```

**Every one of the nine is software repair or software acceptance** — the surface the owner cares
most about, and the one where "learn it once and keep it" would do the most damage. The other 46
are candidates for a human to read: eleven read a field they do not declare, and the rest offer a
status string or an unthresholded score rather than a boolean.

## 2. Why the fix is not in this PR

Repointing `expect` from `output_verified` to `pass` is one line per capability. It is also a
**narrowing of what the planner accepts**: a repair that currently "passes" because it wrote a file
would start failing, which is correct and would turn currently-green paths red. That decision needs
its own evidence and its own PR, not a rider on a measurement.

What this PR does instead is make the debt impossible to grow silently. The nine are pinned in
`canonical/tests/test_acceptance_predicate_target_v1.py` as `DEFINITE_DEBT`:

```python
assert definite <= DEFINITE_DEBT   # the list may shrink; it may never grow
```

A new capability that computes `pass` and registers a transport predicate changes the set and fails
the test until someone either repoints the predicate or extends the debt in the open.

## 3. Why this is the answer to the question, in one sentence

A learner's safety is its acceptance test. Round 2 showed one demonstration leaves 14 of 47
programs standing; Round 3 counted 60 capabilities structurally able to learn from one try; Round 4
showed the gate is mostly not a rubber stamp. This round finds the place where it is, and it is the
place with the most to lose:

> **If the gate passes when a file was written, then "learn it once and keep it permanently" is a
> guarantee that the wrong patch is kept permanently.**

That is not a hypothetical. It is what the registry currently asks of the nine capabilities that do
the most important work in this tree.

## 4. What to do, in order

1. **Repoint the nine.** `output_verified` → `pass`, one line each, with a test that a
   no-repair run is rejected by the predicate. Expect some currently-green paths to go red; those
   are the false successes, not regressions.
2. **Read the 46 candidates.** Eleven read an undeclared field — the same declaration-mismatch
   defect found last round — and the rest need a boolean added to the adapter before a predicate
   can use it.
3. **Then re-run Round 3's census.** The one-shot-safe count should *fall* when this is done,
   because several of the 60 were "safe" on a receipt while their runtime gate was transport. A
   falling number here is progress, and it is the only kind of progress this project has ever been
   able to trust.

## 5. Receipts

```
python3 acceptance_predicate_target_probe_20261112.py --list-fixes
canonical/tests/test_acceptance_predicate_target_v1.py     7 tests, all passing
```

The tests are written to let the census fail: a digest comparison must not be called transport
(`file.copy.v1` would be slandered); a display string or unthresholded score must not be called a
definite fix; a literal assignment must not count as computed; and the definite set must stay inside
the pinned debt.

## 6. Non-claims

Static. "Computes `pass`" is not "computes `pass` correctly" — these adapters' own internal checks
were not audited here, only the wiring between their answer and the registry's predicate. Nothing
was executed, no receipt replayed, no capability re-verified. The 46 candidates are a reading list,
not findings. No capability registered, no family flipped, `truth.achieved` false, $0, zero model
dependency.
