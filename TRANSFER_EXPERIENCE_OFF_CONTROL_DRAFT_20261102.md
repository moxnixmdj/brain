# Transfer-driver experience-off control — draft, 2026-11-02

## What changed

`transfer_learning_v1.drive` now has `experience_mode='off'`. Within that function, the off path does not fingerprint by acting, read retained episodes, learn a model, or write an experience. It can execute and observe an explicit caller-supplied fixed plan; the same option is available in enabled mode. Without a fixed plan, or if that plan fails, the off arm does not invent an answer. Unknown mode values are rejected. If a fixed action or goal check raises, the driver stops and reports possible prior effects rather than retrying.

The fixed plan must come from an identical, genuinely fixed baseline for both arms; the driver cannot authenticate its provenance. Its environment, goal callback, caller, and every other subsystem are outside this control. In particular, `computer_env_v1.discover`, query caches, the unified front door, compiled workflow recall, R3 and the ignorance ledger are **not** governed by this switch. It does not make subprocess execution safe. This is not yet the requested system-wide learning-off control.

The old `use_transfer=False` option is deliberately unchanged: it prevents episode recall but still permits model learning and persistence. It is not a learning-off control. Both the off mode and the old option are covered by local tests against populated stores; the off path is also tested with guards on episode/fingerprint access and model learning, and with new interpreters.

## Small producer-run comparison

`transfer_experience_control_probe_20261102.py` uses a synthetic three-dial environment and four new Python processes. Every arm gets the same fixed plan `['+0']`. Teach learns target `(7,2,9)`; off and warm start with copies of the resulting episode store and target `(1,1,1)`; cold starts with an empty store and the same target. The parent separately replays reported plans against the simple lock rules. This is not an independent-personnel verification, a real-file task, or a general capability evaluation.

One local run:

| Arm | Result | Parent replay reaches target | Model trials including fixed baseline | Environment act calls | Episode store |
|---|---|---:|---:|---:|---|
| Teach | learned | yes | 9 | 345 | written |
| Off | fixed plan did not reach target | no | 1 | 1 | unchanged |
| Cold | learned without prior model | yes | 9 | 239 | written |
| Warm | solved with 79 prior transitions | yes | 9 | 257 | written |

The warm arm reused a model after process restart; this run did **not** demonstrate a speed or interaction saving: warm had the same trials and more `act` calls than cold. The off arm's failure is expected under its narrow fixed baseline, not proof that every reasonable nonlearning solver must fail. No claims of consciousness or general learning performance follow from the comparison.

## Remaining work

Propagate an explicit policy through all relevant unified-front-door memory and learning channels, including nested routes and process-local caches, while keeping a useful, fixed baseline available. Demonstrate no reads or writes across populated stores and restarts, and use fresh real goals only after a qualified carrier, broker and admission exist. The CLI safety draft currently blocks that computer loop, and there is no independently qualified carrier here.
