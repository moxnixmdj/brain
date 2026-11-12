"""Actions the front door was taught: one self-contained program each.

A program here is the *demonstration* half of a lesson.  `canonical/tools/teach_actions_v1.py` runs it
once on a first example, hands it to `causal_trace_to_skill_compiler_v1` together with a second,
different example, and exports what qualifies to
`canonical/astra_runtime/skills/COMPILED_WORKFLOWS_BUNDLE_V1.json`, which the front door recalls from.

Rules a program follows, because the compiler generalizes it by replacing the taught values textually:

* the taught values appear once, in the ``REQUEST`` line, inside string literals, and nowhere else;
* everything is checked in memory first and the file is written last, so a refusal changes nothing;
* on success it prints exactly one line, which is the lesson's postcondition;
* when it cannot keep behaviour the same it prints ``REFUSED: <why>`` and exits non-zero.
"""
