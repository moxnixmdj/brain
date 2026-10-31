# SWE problem probes — 2026-10-29

Every number in `HARDCORE_SWE_PROBLEM_INVENTORY_20261029_V2.md` comes from one of these scripts.
Run them **from the repository root**; they create their fixtures under
`canonical/astra_runtime/tmp/` (gitignored) except `outside_root.py`, which creates `/tmp/outside_project`
on purpose (P0-3: the door cannot address a project outside this repository).

| script | what it proves | headline |
|---|---|---|
| `swe_probe.py` | 18 human SWE sentences, one `solve()` each, filesystem oracle | 1/18 PASS; 9/18 reach a SWE cap; 3/18 wrong domain |
| `layout_matrix.py` | 6 tasks × 4 repository layouts | repair: flat PASS, `pkg/`, `src/app/`, `app/` all fail |
| `writes.py` | does a repair PASS modify the source? | no — `PASS__VERIFIED_MULTI_EDIT_PATCH_FOUND`, source byte-identical |
| `falsepass.py` | door PASS vs the goal's own stated acceptance | PASS=True, `unittest` rc=1 on the real tree |
| `report_clause2.py` | minimal pairs, ±"…and save the report to X" | 3/4 pairs change route, 2/4 flip PASS↔FAIL |
| `hang.py` / `hang2.py` | 25-40 s `faulthandler` dump of a live request | `python_test_audit.py:136`, no deadline |
| `state.py` | same goal, same tree, after one unrelated request | PASS → FAIL_CLOSED |
| `outside_root.py` | project outside the repo root | no `root` parameter; repair → evidence oracle |
| `repair_flat_and_pkg.py` | naive `[python, -B, file]` vs `suite_argv()` | flat+naive → `BASELINE_ALREADY_PASSES`; flat+loader → PASS |
| `layout2.py` | same, over `pkg/`, `src/`, `tests/` layouts | all package layouts → `OPEN__NO_VERIFIED_CANDIDATE…` |
| `repair_direct.py`, `detail.py`, `plan.py`, `rename_detail.py` | adapter-level and plan-level detail | patch search finds nothing on a package; decisive plans exist but the door skips them |
| `determinism.py` | same goal × 3 fresh trees | stable for 5 goals (P2-8 does not reproduce on these) |
| `transact.py` | destructive-sentence check | old P0-1 destruction did not reproduce on this tree; wrong-domain routing did |
| `compose2.py` | "A and then B" + stated directories | composition fails; "run the tests in D" audits Brain's own corpus and hangs |

Caveats, so nobody over-reads the numbers:

- `python.patch.search.test_guided.ast.v1`'s correctness is not in question — it finds the right fix
  on a flat module in ~1.4 s. The failures here are reachability, layout, argv and authority.
- This sandbox has no `pytest`, `mypy`, `ruff`, `crosshair`, `z3`, `sympy`, `pandoc`, `tesseract`.
  Capabilities gated on those report absent-dependency refusals, not cognitive failures (§6).
- `solve()` writes to `canonical/runtime/state/experience_v1.json`,
  `canonical/astra_runtime/state/*CONTROLLER_CHECKPOINT.json` and `canonical/tmp_*.json` during a
  run. Clean those up afterwards if you care about a clean `git status` — their creation is itself
  evidence for P0-9/P2-4.
