# The 69 drift failures: what they are, and the one decision only the owner can make

**2026-11-03**, `37b8ea2`. Outcome of ranked item #2 — "fix the door where it is not gated."
The honest result is that **it is not mine to fix**, and here is why in enough detail that the
owner can decide in one reading rather than a session.

Authority: **NONE**. This is an inventory and one worked example.

---

## 1. What a drift failure is

A runtime module records a git blob sha of a file it depends on and **re-checks it at import**:

```python
EXPECTED_ASTRA_BLOB = "0c613137b9c578c8afadb9482da08e2fc268deb7"
_ALLOWED_ASTRA_BLOBS = {"15dd59ad…", "85977747…", "0c613137…"}
```

Every legitimate change to that file breaks the pin. So the repository accumulates two reds that
look identical:

| | meaning | correct action |
|---|---|---|
| (a) stale pin, nothing happened | an ordinary commit touched the file | re-pin — one line |
| (b) pin is stale **because something happened** | a security property moved | **that is the finding** |

**Updating a pin without telling (a) from (b) is how a mediation invariant becomes a rubber
stamp.** That is the whole reason I did not touch these.

## 2. The exact state, worked example: the process-creation registry

This one is the most important pin in the tree — it is the finite census of every place the
runtime can start a child process. Its own status line is
`PASS__WHOLE_CURRENT_REPO_RUNTIME_CHILD_PROCESS_UNIVERSE_FINITE__18_EXACT_PROCESS_CREATION_SITES…`.

Reported failure: `ASTRA_RUNTIME_BLOB_DRIFT`, then `CHILD_PROCESS_MODULE_COUNT_DRIFT:11`.

Measured today, bypassing **only** the blob pin and re-running the registry's own substantive
checks:

| invariant | pinned | measured | verdict |
|---|---|---|---|
| process-creation sites | 18 | **18** | holds |
| `subprocess.run` sites | 17 | **17** | holds |
| `Popen` sites | 1 | **1** | holds |
| unregistered process APIs | 0 | **0** | holds |
| **modules containing them** | **12** | **11** | **moved** |
| `astra_runtime.py` own blob | 3 allowed | `aa91d571…` | moved |

So: **the security property the registry exists to protect is intact.** The count of effect sites
did not grow, no unregistered API appeared, and the single `Popen` chokepoint is still single.
What moved is the *spread*: 18 sites now live in 11 modules instead of 12.

**Which means re-pinning is very likely correct — and I still will not do it.** "Very likely" is
not compliance: a 6-site module versus 5-site + 1-site elsewhere is a real architectural change to
the mediation surface, and the whole point of the pin is that a human looks when it moves. The
correct artefact is this table, so the look costs minutes.

## 3. The inventory, so the decision is one list

`scripts/pinned_invariant_report_v1.py` (new, 4 tests) finds every module-level pin, **without
importing the modules it audits** (importing a drift-checking registry raises, which would make
the report say "no drift found" — the most dangerous possible answer), and **joins each pin to the
measured failures that name it**.

| | |
|---|---|
| pins found | **157 across 76 modules** |
| pins a measured drift failure points at | **9** |
| measured drift failures | **69** |
| their classes | `SOURCE_BLOB_DRIFT` 15, `ASTRA_RUNTIME_BLOB_DRIFT` 12, `CURRENTNESS_GUARD__DRIFT` 11, `SOURCE_DRIFT` 8, `ROOT_PARTITION_IDENTITY_DRIFT` 4, 9 others |

The report deliberately does **not** answer "is this benign". It lists, and stops.

## 4. What I recommend, concretely, and what it costs

1. **Owner decision, one sitting:** for each of the 9 pinned sites, read the diff since the pin and
   record *benign* or *substantive*. That converts 69 red tests into either a one-line re-pin or a
   real finding. Nobody else can do this, because nobody else can say what the invariant was for.
2. **Then re-pin in a dedicated commit per invariant**, with the diff quoted in the message. Never
   batched: a batch is unreviewable, and unreviewable is how (b) hides inside (a).
3. **Then make the pin self-announcing.** A pin that raises at import cannot report *how far* it
   moved. The registry above already does this well (`…DRIFT:11` names the number); the blob-only
   pins do not. That is a real, safe improvement available to me later without touching any value.

## 5. Why this is ranked #2 and still blocked by #1

It is the largest self-contained red block that is **not** behind the execution gate (69 failures,
0 of them `COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`). It is cheap. It is also entirely
gated on one person's reading, which puts it in the same class as the carrier review: **two of the
three largest blocks in this repository are waiting on a human, not on code.**

The 789-line backlog is not 789 units of work. It is roughly: 189 blocked on a review, 69 blocked
on a reading, 48 blocked on a `pip install`, and the rest real.
