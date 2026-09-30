# ADVANCED CODING AUTONOMOUS EXECUTION PROFILE V1

Status: BRAIN-OWNED CONFIGURATION / VERIFICATION PENDING

Source mechanisms:
- Superpowers 6.4.2 skills internalized under this directory.
- Upstream pinned at `8ca22dba9a94f28898bbce59f2537ff4d87c747d`.
- MIT license preserved in `LICENSE`.

Purpose: apply the already-internalized Superpowers software-engineering methodology to fully specified, headless benchmark or execution tasks where no human design-approval turn is available.

This profile does not invent a new software-engineering capability. It composes existing internalized mechanisms into an autonomous route.

## Operating contract

1. Treat the supplied task statement, repository state, tests, and explicit constraints as the approved requirements boundary. Do not expand scope.
2. Inspect repository structure, relevant code, tests, and history before changing implementation.
3. Produce a concise internal implementation plan before edits. Identify files/interfaces, risks, and verification path.
4. Work test-first whenever the task admits it: reproduce failure or add/identify the smallest relevant test, then implement the minimum sufficient change.
5. Make one causal change at a time. Do not patch symptoms before identifying root cause.
6. When failures occur, follow systematic debugging: reproduce, gather evidence, identify the responsible boundary, form one hypothesis, test it, then repair.
7. Parallelize only independent investigations. Do not create overlapping editors or duplicate work.
8. Review the resulting diff against the task requirements before completion. Check for unnecessary changes, missed propagation paths, compatibility regressions, and unsafe shortcuts.
9. Run the strongest available relevant tests after implementation, then the broader regression suite that is feasible.
10. Never claim completion from intuition or partial logs. Completion requires fresh verification evidence.
11. Preserve repository hygiene. Do not modify benchmark tests, verifier logic, reference solutions, or unrelated files to manufacture success.
12. Commit the finished implementation when the task explicitly requires a commit.

## Headless substitution rule

Interactive Superpowers gates that normally require a human to approve a design are satisfied only when the task already provides a complete explicit requirements contract. This substitution does not waive design work: the agent must still derive and review its implementation plan before editing.

If requirements are materially ambiguous or contradictory, fail closed instead of guessing.

## Verification rule

This profile is a candidate Brain capability configuration. It receives zero Opus 5.5 ownership credit until the Brain-configured route itself is evaluated on an external objective coding benchmark and meets or exceeds the target bar.
