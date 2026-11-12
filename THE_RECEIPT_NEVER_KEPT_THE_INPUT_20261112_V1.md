# The receipt never kept the input

**2026-11-12.** Base `79df0c78`. Branch `arena/c7ee9442-brain`. Round 19.

Round 18 shipped the instance index and then found that varied inputs are not valid ones. This round
went looking for the validity the tree was supposed to already have — the fixtures its own tests use —
and found something more fundamental.

```
532 execution receipts
  1  records any argument at all
  3  path arguments in total
  2  of those 3 already point at files that no longer exist
```

**The receipts never kept their inputs.** Not badly — not at all. Every receipt in this tree is a
statement of the form "this module ran, and here is the hash of what it returned". There is no
addressable input anywhere in 532 records, which means:

* nothing can be *replayed as an instance*, only re-run on whatever the probe synthesises;
* no corpus of input → verified-output pairs can be built from the history;
* and "run it again on another input", which is the whole of the depth plan, has never once been
  possible from what this repo stored.

Rounds 16, 17 and 18 each assumed the missing thing was deeper in the stack — independence, then
variation, then validity. It was shallower each time. The inputs were never captured.

## What shipped

```python
INSTANCE_STORE = os.path.join("canonical", "astra_runtime", "instances")
MAX_SNAPSHOT_BYTES = 1 << 20

def snapshot_inputs(root, args) -> dict[str, str]:
    """Content-address every file argument, so the *inputs* of a run survive the run."""
```

Every file argument of an invocation is hashed, copied into a content-addressed store, and recorded on
the receipt as `input_digests: {argument_name: sha256}`. The field is added **only when there is
something to add**, so every receipt already in the tree keeps its shape and the 296 attestations are
untouched.

Executed:

```
two file args, one duplicated content  -> 2 digests, 1 stored file
a free-text arg and an integer         -> not recorded as inputs
argument whose file is missing         -> skipped, never a fake digest
original path deleted afterwards       -> bytes still in the store, digest still matches
```

## Why content-addressing rather than copying the path

A path is a claim that a file *was* there. Two of the three path arguments this repo ever recorded now
point at nothing, which is the proof. A digest is a claim that these exact bytes existed, and the store
makes it checkable at any time afterwards — by this session, by CI, by a future student channel that
needs to know what the model was shown.

## What this unlocks, precisely

With `input_digests` present, three previously impossible things become trivial:

1. **Instance identity.** Two receipts with the same `capability_id` and different `input_digests` are
   two instances, not two runs of one.
2. **A real corpus.** Join receipts that carry `input_digests` with the ones CI reproduced, and you
   have input → verified-output pairs, which is exactly the OaTTT shape (verified trajectory, single
   pass, consolidated offline).
3. **Non-regression on real inputs.** Replay a stored instance against a new module build and see
   whether the output hash changed — a regression test made of work that already happened.

## The honest scoreboard after nineteen rounds

| property | state |
|---|---|
| permanence of an experience | solved, three independent measurements |
| independence of verification | solved, 296 OIDC-attested reproductions |
| variation of inputs | shipped (round 18, `--instance-index`) |
| **input capture** | **shipped this round; the corpus starts empty because history has none** |
| validity of inputs | open — needs real documents, not synthesised strings |

Every layer of this problem has turned out to be one level lower than the previous answer. That is not
a failure of method; it is what it looks like to actually descend. The corpus is now zero and will
grow every time the lane runs on a real task — which is the first time in nineteen rounds that a
number in this project can only go up by *doing work* rather than by writing a fixture.

## Receipts

```
python3 -m pytest -q canonical/tests/test_receipt_input_snapshot_v1.py \
                    canonical/tests/test_capability_receipt_lane_instance_index_v1.py    12 passed
```

## Non-claims

No receipt in the tree has `input_digests` yet — the field exists and is proven on synthetic
arguments; history cannot be retro-fitted and is not pretended to be. Nothing here measures
generalisation and nothing here is a capability claim. No registry entry, no predicate, no
capability added. `truth.achieved` false, $0, zero model dependency.
