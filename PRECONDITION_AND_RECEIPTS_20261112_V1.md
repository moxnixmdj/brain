# A fix for a bug that isn't there, and a receipt for a program that no longer exists

**2026-11-12.** Branch `arena/b8bb9d9c-brain`. Authority **NONE**. `truth.achieved` = `false`.

Two defects found this pass, both the same shape as everything before: **a record that cannot
fail.** Both now have a check that can return no, with tests that prove it.

---

## 1. The store will crystallize a fix for a defect that is not present

`crystallize_code_fix` requires a *failing baseline*, which is a condition on the **verifier**,
not on the code. A caller-supplied verifier can report failure for any input. Measured:

```
before: `def ok(x): return x < 10`      correct code, no defect
after : `def ok(x): return x <= 10`     the "fix" makes it wrong
crystallized: True   state: ACTIVE
```

and the rule is then **applied to a different, correct function**:

```
victim (correct)   : return a < 100
after skill applied: return a <= 100        INTRODUCED A BUG: True
```

The stored rule's justification is whatever the caller asserted. Nothing establishes that the
defect it repairs was ever there.

### The check

`canonical/swe_kernel/skill_precondition_presence_v1.py`

```
PRESENT       the observed value changed, and before holds the value the fix claims is wrong
ABSENT        the values already agree -- there is nothing to repair
REFUSED       the accessor raised on the before-snippet
UNOBSERVABLE  no accessor supplied, so nothing was measured
```

**`PRESENT` is the only verdict that permits learning.** Everything else refuses, because a
rule learned against a defect that was not there has a false justification and the store has
no way to notice later — it only knows the rule applied cleanly.

### Its honest limit, stated in the module

The gate proves *a caller-chosen observable changed*. It does not prove the change is a
repair: `x <= 10` → `x + 1` also counts as a change. Choosing the accessor is the caller's
responsibility, and a bad accessor produces a confident wrong answer. That is the same limit
`domain_of_verification_v1` records for hypotheses — *a test that can only fail to find what
it can express will always look confident about what it cannot express* — applied to one edit
instead of a hypothesis. It is written down rather than papered over.

---

## 2. Receipts name a program; nothing ever checks the program still exists

`python_repository_acceptance_measurement_v1.py:338` writes:

```python
program_sha = _sha_bytes(pathlib.Path(__file__).read_bytes())
...
"measurement_program_sha256": program_sha,
```

Consumers copy it forward (`python_repair_measured_acceptance_controller_v1.py:465`). **No
code anywhere compares the carried value to the program on disk** — a grep for an equality
test finds only a test that blanks the field.

Measured across the tree:

```
files carrying measurement_program_sha256: 4
  MATCH       0
  MISMATCH    0
  NO_PROGRAM  67      <- a hash, and no program that can be located
  checkable   0
```

**67 receipts assert the identity of a program and none of them identify one.** The field
looks like evidence and is unfalsifiable in every instance.

### The check

`canonical/tools/receipt_program_identity_v1.py`

| verdict | meaning |
|---|---|
| `MATCH` | the carried hash equals the program on disk |
| `MISMATCH` | it does not — the receipt describes a program that no longer exists |
| `NO_PROGRAM` | a hash with no locatable program: unfalsifiable |
| `ABSENT` / `INVALID` | no field, or an empty one |

10 tests, green, and two of them exist solely to prove `MATCH` and `MISMATCH` are both
reachable — *a field that can only ever be `MATCH` is not evidence*.

---

## The report now has six layers

```
layer             records  checkable  auditability
capabilities          294          0          0.0%
skills                  5          0          0.0%
process_sites          18          0          0.0%
test_modules        18238      18196         99.8%
binary_identity         5          5        100.0%
receipts               67          0          0.0%
```

Four of six layers are at zero, and each zero means something different and specific:
dead pins, no taught source, no locatable program, no re-executable check. The reference
layer — `binary_identity` — is the one where every record is an assertion that can be
contradicted on the next run.

---

## What this says about the question, again

The chain is *one exposure → permanent skill → any computer use*. This pass closed two more
places where a link was asserted rather than checked:

- **the exposure may not have contained the defect** — now `PRESENT` is required to learn;
- **the receipt may describe a program that no longer exists** — now `MISMATCH` is reachable.

Neither makes the chain true. Both make it possible to be told *no*, which is the only
property that separates a mechanism from a claim.
