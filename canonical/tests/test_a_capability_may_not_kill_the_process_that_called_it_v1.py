#!/usr/bin/env python3
"""A capability may not kill the process that called it.

19 of the bound adapters report failure by ending the interpreter:

    raise SystemExit(json.dumps({"error": True, "capability": ..., "reason": ...}))
    sys.exit(1)

`SystemExit` is a **BaseException**, so the `except Exception` in `_execute_locally` never saw
it.  Measured on this branch with `run_adapter_locally(entry, {})`, one call per capability in
its own subprocess (`execution_guard/adapter_failure_law_probe_v1.py`):

    before the guard:  16 of 16  PROCESS_KILLED   -- no verdict, no caller, no diagnosis
    after  the guard:  16 of 16  TYPED_REFUSAL    -- the adapter's own reason, delivered

A machine that is supposed to run thousands of capabilities in one life cannot be killed by one
of them, and the caller cannot even name the culprit afterwards: the process is gone.  The
adapter's exit payload was always the right diagnosis; it just had no way to be heard.

Why the assertion is on the exception TYPE and not on a string: the defect WAS the type.  A
regression that reintroduces it takes the whole test process down, which is why this file also
asserts that the guard is present in the source of the one door every local call uses.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as live  # noqa: E402

# Two shapes that are really used: one raises SystemExit with a JSON body, the other with an
# exit code.  Both were measured dead before the guard and typed after it.
EXITING = ("python.issue.natural_language.parse_edit_intent.v1",
           "python.source.symbols.resolve.v1")


def _entry(cid: str) -> dict:
    entry = live.load_verified_registry().get(cid)
    assert entry, cid
    return entry


@pytest.mark.parametrize("cid", EXITING)
def test_an_adapter_that_exits_is_converted_into_a_closed_failure(cid):
    with pytest.raises(adm.LocalExecutionFailure):
        adm.run_adapter_locally(_entry(cid), {"type": "invoke_capability", "args": {}})


def test_system_exit_never_escapes_the_local_door():
    """If this ever fails the test run dies, which is exactly the production behaviour."""
    try:
        adm.run_adapter_locally(_entry(EXITING[0]), {"type": "invoke_capability", "args": {}})
    except SystemExit:  # pragma: no cover - the regression this file exists for
        raise AssertionError("SystemExit escaped run_adapter_locally")
    except Exception:
        pass


def test_the_guard_is_in_the_door_every_local_call_uses():
    source = pathlib.Path(adm.__file__).read_text(encoding="utf-8")
    assert "except SystemExit as exc:" in source, \
        "the local door lost the guard that turns an adapter's exit into a verdict"


def test_the_probe_measures_the_same_thing_it_claims():
    """The instrument must be able to see a kill, or its 'all typed' number means nothing."""
    probe = (ROOT / "execution_guard/adapter_failure_law_probe_v1.py").read_text(encoding="utf-8")
    # The child must NOT catch BaseException: catching it hid 16 real deaths from the probe
    # on the first run, which reported 16/16 refusals both before and after the fix.
    assert "except Exception as exc:" in probe
    assert "except BaseException" not in probe
    assert "PROBE_VERDICT " in probe
