# Hardcore software-engineering problem inventory — V19

Measured 2026-10-31 on `9e6a366` (branch `arena/26b6e2d4-brain`).
Supersedes V18. V18 said containment was safe to attempt; this document records the first
containment that *served* instead of merely refusing.

---

## §0 The answer in one paragraph

The 49-request advanced census served **2**; it now serves **3**, and the third one is a real
refactoring that really happened. Request 38 — *"Extract the loop in the function total in
`<pkg>/util.py` into a helper."* — was refused `REGION_INVALID` on a region the repository
proves. Two defects, no new primitive: the front binder wrote the literal `0` into
`start_line`/`end_line` **before** anything asked `declared_input_derivation_v1`, and the
derivation itself could read a host only from `in <name>` (so it answered *"the"*) and would
widen a stated loop to its neighbouring assignment (2–4), which the adapter refuses. The proof
is now asked first, the host is read from its role phrase, and a stated region kind takes the
single statement of that kind. The adapter was never the problem: given `qualname=total`,
`start_line=3`, `end_line=4` it returns gate PASS and one edit. Nothing was missing but the
**order of the two answers**.

---

## §1 Measurements on `9e6a366` + this change

| instrument | before | after |
|---|---|---|
| advanced census (49 requests) | 2 served / 47 refused | **3 served / 46 refused** |
| request 38 | `FAIL_CLOSED__CAPABILITY_REFUSED_REGION_INVALID`, 42 ms | **PASS**, 48 ms, loop extracted |
| capability matrix (54 cases) | 22 REAL / 0 FALSE / 0 DAMAGED | **22 REAL / 0 FALSE / 0 DAMAGED** |
| matrix latency | median 68 ms | **median 68 ms** (unchanged) |
| new tests | — | **6 / 6 green** |
| unified model verify | 60 / 60 | **60 / 60** |

The matrix is unchanged in every cell, which is the point: the two rules only fire on a sentence
that names a host and a region kind, and no matrix case states a region that way.

---

## §2 What the two rules are

1. **A placeholder is not a statement.** `goal_front_compiler_v1.derive_declared_inputs` settled
   an unbound `start_line`/`end_line` by writing `0` on the spot. It now asks the derivation
   first and writes `0` only when the sentence states no region. The adapter's own
   `REGION_INVALID` refusal therefore still stands for every request that genuinely names none —
   pinned by a test, because a rule that stops refusing is not an improvement.

2. **The sentence names the host by its role, and the region by its kind.** `"the function
   total"` is how an engineer names a host; `"the loop"` is how they name a span. The derivation
   reads both, and when exactly one statement of that kind exists it takes *that* statement
   rather than the widest self-contained run — because the wider run is not a cosmetic
   difference, it is a refusal (`REGION_NOT_STATEMENT_ALIGNED`).

---

## §3 The neighbours the rules must not touch (pinned)

| sentence shape | decided by | expected |
|---|---|---|
| `Extract lines 3-4 of <f> into a helper` | the stated numbers | unchanged: numbers win over any derivation |
| `Extract the region in <f> into a helper` | nothing provable | **still `0` → `REGION_INVALID`** |
| `Extract the loop in <f> into a helper` (no host) | nothing provable | still refused |
| a host with two loops and no further qualifier | ambiguity | falls through to the block search, unchanged |

The fifth test in the new suite removes the role phrase and shows the proof disappears, so the
suite is able to fail.

---

## §4 Still open, in the order the measurements now support

1. **Selection, not reachability.** `capability_composer_v1.plan()` reaches the right rows in ≤2
   steps for the property/fuzz family; `composer_route_v1.route()` then picks the wrong chain
   (`add_parameter` for *"why does X return None"*, `shell.command.run` for a why-question).
   Requests 25 and 28 refuse there, not in any adapter. Do not widen chain wiring before this.
2. **Rows that refuse inside their own contract.** Requests 34 / 37 (`inline_helper`) reach the
   controller and fail `FAIL__LIVE_CONTROLLER_EXECUTION`; 33 / 35 refuse at plan time
   (`NO_DECISIVE_TYPED_PLAN`). Each needs its own measurement — none is a two-line fix.
3. **The 35 requests with no declaring row at all.** These need capability, not plumbing, and
   they are the honest remainder.

---

## §5 Pre-existing reds (unchanged, verified again here)

* 2 failures in `test_a_deliverable_is_not_a_measurement_v1` (identical with this change stashed).
* `test_git_sentence_routing_v1` — registry-args drift.
* `test_the_entry_is_a_verified_bound_capability` — `provides` mismatch.
* `test_crossfile_multiline_imports_v1` — `import pytest`, absent from this image.
