# The repair gap: a dependency you cannot see is a repair you cannot make

*2026-11-16. Real programs, real chains, real sabotage, real perturbations. AUTHORITY: NONE — producer-run measurement.*

---

## 1. Where the previous answer stopped

The last receipt closed detection: a ledger of standing facts re-validates exactly the facts the current
step's frame can touch, so a **legal** step that falsifies an earlier proof is caught at the causal step,
two steps before the symptom, for 3 hashes instead of 69.

Detection is not repair. That receipt ended with its own named next step, and the 2026 record names the same
hole from three directions:

- **TRACE-FIX** (arXiv 2610.25776) binds evidence to the *versions of the resources it depends on* and then
  states its limit plainly: *"missing dependencies, unobserved side effects, or incorrect resource links can
  exclude relevant events; dependency links narrow hypotheses without establishing causality."*
- **CausalFlow** (arXiv 2605.25338) does counterfactual step-level repair, but the alternatives are proposed
  by a model and scored by re-executing the suffix.
- An open engineering question (agent-interface #165, Sep 2026) asks for the primitive directly: how to
  discover *"the smallest complete dependency footprint instead of receiving a hand-authored ground-truth
  set"*, and warns that over-declaration causes stops on work that was never related.

So the question is not "can the agent notice the fact went false". It is: **which steps consumed the fact
that went false** — and can the agent find that out without being told?

## 2. Why the obvious answer is wrong

The obvious read set is the command line: every path that appears as a word. It is free, and it is wrong in
both directions at once.

**It under-declares**, because a path is often named by *data* rather than by an argument:

```
tar -cf bundle.tar -T list.txt      # reads payload.dat, because list.txt names it
xargs sha256sum < list.txt          # reads payload.dat, because xargs is handed the name
```

Neither command contains the string `payload.dat`. Any repair built on the argv read set will not re-run
those steps, and will therefore declare the work repaired while the artifact still holds the old bytes.
That is not a corner case; it is how archives, package tools, `find -exec`, linker scripts and build systems
work.

**It over-declares**, because naming a path is not reading it. `ls payload.dat > list.txt` mentions
`payload.dat` and depends only on the name; its content can change all day and `list.txt` is unchanged.
Re-running it is wasted work — and worse, in a chain it can *drag the repair forward by luck*, hiding that
the set was wrong.

## 3. The discovery rule

> A step depends on path `p` **iff** perturbing `p` changes that step's consequence.

Concretely, for a step and the state it ran against: for each candidate path, write the state again with that
one file's content altered, re-run the step, and compare the *consequence* — its exit code and the set of
`(path, bytes)` it left behind — against the unperturbed run. One extra real run per candidate path. No model,
no tracing infrastructure, no annotations, no hand-authored ground truth.

Two properties matter and both are measured below:

- The candidate set is **the state the step can see**, not the frame its contract declares. Using the
  contract's frame would make the answer depend on the very declaration under test.
- The probe **matches the kind of the fact**. The ledger records content; a content perturbation answers the
  matching question. This is why `ls payload.dat` is correctly *not* flagged: if the content changes and the
  listing does not, the step never depended on the content, and the fact was never its input.

Repair is then a replay in plan order: redo every step whose read set meets a path that has **actually moved**,
and extend the frontier only when a re-run changes something. The distinction is load-bearing: a closure that
propagates on the *intention* to re-run rather than on a real change invents work, and (measured here) can
wander into the one step that needed redoing and pass for the wrong reason.

Every step is considered, not only those that ran after the invalidation. A product built from good content
*before* the content changed is exactly as stale as one built after — more so, since nothing downstream ever
touched it again.

## 4. The measurement

Three chains, 17 real steps, one legal sabotage each, one control chain, 86 intervention probes. Machines
used: `cp`, `ls`, `tar`, `xargs`, `sort`, `sha256sum`, `cmp`.

| arm | goal restored | steps redone |
|---|---|---|
| declared read set (hand-authored truth, for reference) | **3 / 3** | 8 |
| **argv read set** (syntax) | **1 / 3** | 5 |
| **intervention read set** | **3 / 3** | **8** |
| redo every step | 3 / 3 | 14 |

The intervention arm does not approximate the declared set. It **recovers it exactly**: 0 missed, 0
over-declared, on all three chains. Rebuilding everything also works and costs 14 steps instead of 8, so the
saving is not the point — the point is that an agent without the discovered set does not know *what* to rebuild.

The chain that fails:

| step | command | declared | argv | intervention |
|---|---|---|---|---|
| `copy_in` | `cp in.txt payload.dat` | `in.txt` | `in.txt` | `in.txt` |
| `list_it` | `ls payload.dat > list.txt` | — | `payload.dat` | — |
| `bundle_by_list` | `tar -cf bundle.tar -T list.txt` | `list.txt`,`payload.dat` | **`list.txt`** | `list.txt`,`payload.dat` |
| *sabotage* | `cp decoy.txt payload.dat` | `decoy.txt` | `decoy.txt`,`payload.dat` | `decoy.txt` |
| `digest_the_bundle` | `sha256sum bundle.tar > bundle.digest` | `bundle.tar` | `bundle.tar` | `bundle.tar` |
| `keep_the_digest` | `cp bundle.digest bundle.digest.bak` | `bundle.digest` | `bundle.digest` | `bundle.digest` |

The ledger invalidates the fact `payload.dat`. The argv set blames `list_it`, re-runs it, changes nothing, and
then runs the independent goal — which says

```
- payload.dat differ: char 1, line 1
```

and the repair is over, reported done, with the archive still holding the previous bytes. The intervention set
blames `bundle_by_list`, re-runs it, follows `bundle.tar → bundle.digest → bundle.digest.bak` because each
re-run actually moved something, and the goal returns `bundle.tar: OK`.

The `xargs sha256sum < list.txt` chain is the same story with a checksum manifest:
`payload.dat: FAILED … 1 computed checksum did NOT match` under argv, `payload.dat: OK` under intervention.

The control chain — where the dependency *is* syntactic — makes both arms agree (same 3 steps, goal OK), and
the intervention arm raises nothing extra. So the difference in the two chains above is the dependency, not
the method being favoured.

## 5. Cost, and the shape of the cost

86 probes for 17 steps and 8 dependencies: one run per (step, candidate path). That is `O(steps × state)`,
bin-packed by the fact that a probe is a subprocess on a copy of a directory — cheap, parallel, and never
needed for a step whose read set is already known. It is *not* free, and it is *not* what you would do for
every step of a long run; the natural economies are to probe once per action contract (which is exactly the
reuse the contract layer already gives), and to bound the candidates by what the step could possibly read.
Both are separate measurements, not claims here.

## 6. What this does not show

- **The candidate set is the state the step can see.** A dependency on a config file outside the sandbox, a
  lock held by another process, or a remote resource is outside the probe. The rule extends to a wider
  observable; it is not measured here.
- **Content, not existence.** The probe answers a content question because the ledger records content. A step
  that depends on a file merely existing needs the matching existence-perturbation; it is not measured here.
- **n = 3 real chains.** The claim is the mechanism — one intervention is sufficient to recover the read set
  exactly — and not a rate over a distribution of software.
- **No natural-language goal grounding**, no GUI projection, no terminal credit. The goals here are shell
  commands, and they are the frozen, checkable kind.

## 7. Where this lands in the answer

The standing answer to the original question is unchanged and now has one more link measured. "Experience each
action once → permanent learning" is **half true**. The true half: one execution is enough to acquire a
*contract* — what the action needs, what it may touch, what relation its output bears to its input — and that
contract transfers to a binding never executed (0.5000 → 1.0000, zero false alarms), and the facts it
establishes can be kept honest across a sequence (detection 3/3, 0 false invalidations, cause two steps before
symptom), and the work can now be **repaired** from the dependency discovered by intervention (goal restored
3/3, 8 steps instead of 14, 0 missed, 0 over-declared).

The false half is unchanged: one trace does not identify the edit (0.5469 supply against a ~0.70 ceiling for
a full inducer), and replay does not compose new work (~2.2%). A single observation plus one intervention per
candidate path is enough to know *what the step depended on*; it is not enough to know *what the new step
should be*. That is synthesis, it is the remaining measured bottleneck, and it is not this receipt.

`p_correct` is untouched at **0.5469 × 0.5445 = 0.2978**. What changed is what survives a long run: before
this line of work, a legal step could silently falsify earlier progress and nothing noticed; then the ledger
noticed; now the agent can act on the notice with a dependency set it discovered itself, at a third of the
cost of rebuilding.

---

*Receipt: `canonical/verification/CAUSAL_DEPENDENCY_REPAIR_20261116_V1.json`. Code:
`canonical/swe_kernel/causal_dependency_repair_v1.py`. Tests:
`canonical/tests/test_causal_dependency_repair_v1.py` (11 live + pinned checks). Law:
`canonical/verification/CAPABILITY_LAW_20261116_V1.json`, `repair` block, pinned by sha.*
