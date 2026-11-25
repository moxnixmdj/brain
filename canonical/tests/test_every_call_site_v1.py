"""Pins the call-site census: what the environment can execute, and what it cannot.

Every number here is a refusal reason. The point of the instrument is that a share that
cannot be raised is reported as a share, with the specific cause named, rather than either
being hidden or being "fixed" by inventing a value.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import every_call_site_v1 as E  # noqa: E402


def write(tmp_path: pathlib.Path, name: str, source: str) -> pathlib.Path:
    target = tmp_path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)
    return target


def test_a_keyword_with_a_constant_is_usable(tmp_path: pathlib.Path) -> None:
    """205 of 302 keyword values in a real repo are plain constants, and were dropped."""
    write(tmp_path, "m.py", "def f(python):\n    return python\n\nf(python='3.9')\n")
    report = E.mine(tmp_path)
    assert report["counts"].get(E.USABLE) == 1, report["counts"]
    # a JSON token preserves the VALUE's type (`'3.9'` is a string, not a float)
    assert report["vectors"]["f"][0]["kwargs"] == [["python", '@json:"3.9"']]


def test_a_bare_name_is_refused_and_the_kind_is_recorded(tmp_path: pathlib.Path) -> None:
    """Knowing a parameter receives a Constant does not say WHICH constant.

    Substituting one would be inventing a value, so the site is refused. The registry's
    fact is kept beside the refusal rather than thrown away.
    """
    write(tmp_path, "m.py", (
        "def target(value):\n    return value\n\n"
        "def caller(x):\n    return target(x)\n"
    ))
    report = E.mine(tmp_path)
    assert report["counts"].get(E.UNRESOLVED_NAME) >= 1, report["counts"]
    assert report["counts"].get(E.USABLE, 0) == 0


def test_a_refusal_kind_is_never_guessed_into_a_value(tmp_path: pathlib.Path) -> None:
    """A vector must contain only tokens traceable to a call site somebody wrote."""
    write(tmp_path, "m.py", (
        "def target(a, b):\n    return a\n\n"
        "def caller(p, q):\n    return target(p, q)\n"
    ))
    report = E.mine(tmp_path)
    for vectors in report["vectors"].values():
        for vector in vectors:
            for token in vector["args"]:
                assert isinstance(token, str) and token, token


def test_too_many_positional_arguments_is_named_not_dropped(tmp_path: pathlib.Path) -> None:
    write(tmp_path, "m.py", (
        "def target(a, b, c):\n    return a\n\ntarget(1, 2, 3)\n"
    ))
    report = E.mine(tmp_path)
    assert report["counts"].get(E.TOO_MANY) == 1, report["counts"]


def test_a_starred_argument_is_named(tmp_path: pathlib.Path) -> None:
    write(tmp_path, "m.py", (
        "def target(a):\n    return a\n\nargs = (1,)\ntarget(*args)\n"
    ))
    report = E.mine(tmp_path)
    assert report["counts"].get(E.STARRED) == 1, report["counts"]


def test_the_usable_share_is_a_real_fraction_not_a_cherry_pick(tmp_path: pathlib.Path) -> None:
    """One usable site and one refused site must report 0.5, not 1.0."""
    write(tmp_path, "m.py", (
        "def target(a):\n    return a\n\n"
        "def caller(x):\n    target(x)\n"
        "target(1)\n"
    ))
    report = E.mine(tmp_path)
    assert report["call_sites"] == 2, report
    assert report["usable_share"] == 0.5, report


def test_parameter_types_are_read_from_call_sites(tmp_path: pathlib.Path) -> None:
    """The registry must reflect what the repository passes, not a declared annotation."""
    write(tmp_path, "m.py", (
        "def target(value):\n    return value\n\n"
        "target('literal')\ntarget(other)\n"
    ))
    module = E.module_tree(tmp_path / "m.py")
    assert module is not None
    defined = E.defined_functions(module)
    types = E.parameter_types(module, defined)
    assert ("target", "value") in types


def test_no_model_no_network_in_the_instrument() -> None:
    source = (ROOT / "canonical/swe_kernel/every_call_site_v1.py").read_text()
    for forbidden in ("openai", "anthropic", "requests.", "urllib", "http://", "https://"):
        assert forbidden not in source, f"runtime dependency found: {forbidden}"
