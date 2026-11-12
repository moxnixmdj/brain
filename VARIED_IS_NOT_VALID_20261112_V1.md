# Varied is not valid

**2026-11-12.** Base `56ea779d`. Branch `arena/c5583428-brain`. Round 18.

Round 17 named a six-line fix and refused to ship it blind. This round shipped it — with the one
property that made it safe to ship — and discovered, by running it, that the fix is necessary and not
sufficient.

## What shipped

`canonical/runtime/capability_receipt_lane_v1.py`:

```python
def _at_instance(base: str, instance_index: int, is_path: bool = False) -> str:
    if instance_index <= 0:
        return base                      # byte-identical to every receipt already issued
    if not is_path:
        return f"{base}#i{instance_index}"
    stem, dot, ext = base.rpartition(".")
    return f"{stem}__i{instance_index}.{ext}"
```

* `declared_probe_args(..., instance_index=0)` and `execute_and_receipt(..., instance_index=0)`, both
  defaulting to 0, so no existing caller changes behaviour and none of the 296 attestations is
  disturbed;
* `--instance-index k` on the lane, and the receipt records it when non-zero;
* `--verify` replays **the producer's** index rather than assuming zero — a verifier that assumed zero
  would attest a different instance than the one receipted, which is the exact kind of silent
  mismatch this whole lane exists to prevent.

## What was proved, and how

```
_at_instance("canonical/x/a.json", 0, is_path=True)  -> canonical/x/a.json      (unchanged)
_at_instance("cap.id.v1",          1, is_path=False) -> cap.id.v1#i1            (distinct)
_at_instance("d/file.json",        3, is_path=True)  -> d/file__i3.json         (distinct)
```

`declared_probe_args` at 0, 1 and 2 for a real declared capability gives three different argument
dicts. And executed, not just inspected — `evidence.oracle.concrete_execution.v1` at three instances:

```
i=0  status=ERROR__PROPERTY_CHECK  error=NameError: name 'evidence' is not defined
i=1  status=ERROR__PROPERTY_CHECK  error=NameError: name 'evidence' is not defined
i=2  status=ERROR__PROPERTY_CHECK  error=NameError: name 'evidence' is not defined
```

**Three distinct invocations, three identical failures.** The instance index varies the input; it does
not make the input *valid*. The probe fills free text with the capability id and paths with a sink, so
`i=1` hands the capability a string that is syntactically varied and semantically meaningless.

## Why that is the useful result

If I had reported "instance index shipped, corpus can now be deepened", the next round would have
generated 2 000 receipts that all say `ERROR__PROPERTY_CHECK`, and the count would have gone up while
the evidence went to zero. That is the same failure mode as rounds 15 and 16 in a new costume: **a
number rising while its meaning falls.**

So the honest state is now:

| property | state |
|---|---|
| permanence of an experience | solved (three independent measurements) |
| independence of verification | solved (296 OIDC-attested reproductions) |
| **variation of inputs** | **mechanism shipped this round** |
| **validity of varied inputs** | **not solved — measured failing above** |

Variation without validity is noise; validity without variation is a constant. Both are needed, and
only the first exists now.

## The next piece, concretely

Per-capability input generation, and the tree is already full of the material for it: every capability
that declares `${input.*}` also ships fixtures, schemas or example documents that its own tests use.
The cheap version is to take the capability's own test fixture set as its instance set — k fixtures, k
instances, k receipts, each one a document that the capability is designed to accept.

That is a build, not a discovery, and it is now the only thing between 296 constants and a corpus.

## Receipts

```
python3 -m pytest -q canonical/tests/test_capability_receipt_lane_instance_index_v1.py    6 passed
```

The six tests pin: index 0 unchanged; 1 and 2 distinct; free text and paths handled differently;
defaults still 0; the verifier replays the producer's index; and 126 of the 145 curated capabilities
declare inputs — the inputs were never the missing thing, varying and validating them was.

## Non-claims

No new attestation was produced by this round; the CI lane is the only thing that can make one, and it
was not run. The three executions above are the probe's own output and are reported as failures. The
change touches only the value derivation, the receipt, and the verifier's replay — it adds no
capability, no registry entry, and no predicate. `truth.achieved` false, $0, zero model dependency.
