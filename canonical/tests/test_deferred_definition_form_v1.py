"""The DEFER form: what it must emit, and what it must refuse to emit.

These tests pin the two things the calibration showed were fragile: the form must
be derived from the traceback rather than the fix, and it must emit nothing when
the failure shape is absent. The last test is the one that matters most -- it is
the negative control that stops the form from quietly becoming a file rewriter.
"""
from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.tools import deferred_definition_form_v1 as FORM  # noqa: E402

# The measured traceback shape: __init__ mid-assignment, calling into the object's
# own __str__ while assigning the attribute that __str__ reads.
TRACEBACK = """tests/test_markers.py:402: in test_invalid_marker_defers_argument_formatting
    err = InvalidMarker(message)
src/packaging/markers.py:89: in __init__
    self.message: str = str(self) if message is None else message
tests/test_markers.py:399: in __str__
    return self.text
E   AttributeError: 'Message' object has no attribute 'text'
"""

_HEAD = "class InvalidMarker(ValueError):\n    def __init__(self, *args, message=None, source=None, span=None):\n        super().__init__(*args)\n"
_ASSIGN = "        self.message: str = str(self) if message is None else message\n"
_TAIL = '        """The error message."""\n        self.source: str | None = source\n'
# The real traceback names line 89, so the fixture is padded to match it exactly.
# A fixture whose statement sits on a different line would pass a detector that
# ignores the line number, which is the defect this pins.
SOURCE = _HEAD + "# pad\n" * (89 - len(_HEAD.splitlines()) - 1) + _ASSIGN + _TAIL


def test_detects_reentrant_self_failure():
    facts = FORM.reentrant_self_failure(TRACEBACK, SOURCE)
    assert facts is not None
    assert facts["init_line"] == 89 or facts["init_statement"].startswith("self.message")
    assert facts["missing_attribute"] == "text"


def test_emits_both_deferral_spellings_on_the_named_line():
    result = FORM.emit_for_traceback(TRACEBACK, SOURCE)
    assert result["applies"] is True
    spellings = {c["spelling"] for c in result["candidates"]}
    assert spellings == {"property", "cached_property"}
    for cand in result["candidates"]:
        assert cand["attr"] == "message"
        # The whole physical line, including the `if`, so a truncated capture
        # cannot pass.
        assert cand["replaces"] == (
            "self.message: str = str(self) if message is None else message"
        )


def test_the_definition_is_appended_at_class_scope_not_inside_init():
    """Inline emission ended __init__ early and silently dropped later attributes."""
    result = FORM.emit_for_traceback(TRACEBACK, SOURCE)
    patched = FORM.apply_candidate(SOURCE, result["candidates"][1])
    # `self.source` must still be assigned: it is below the edited line.
    assert "self.source: str | None = source" in patched
    body = patched.splitlines()
    method_idx = next(i for i, l in enumerate(body) if "def message" in l)
    source_idx = next(i for i, l in enumerate(body) if "self.source: str" in l)
    assert method_idx > source_idx, "the definition must follow the rest of __init__"
    indent = len(body[method_idx]) - len(body[method_idx].lstrip())
    assert indent == 4, f"definition must be at class scope, got indent {indent}"


def test_cached_property_is_qualified_or_imported():
    result = FORM.emit_for_traceback(TRACEBACK, SOURCE)
    cached = next(c for c in result["candidates"] if c["spelling"] == "cached_property")
    patched = FORM.apply_candidate(SOURCE, cached)
    qualified = "@functools.cached_property" in patched
    imported = "from functools import cached_property" in patched
    assert qualified or imported, "an unqualified @cached_property raises NameError"


def test_plain_property_can_accept_the_conditional_assignment():
    """Without a setter the conditional assignment raises, so one must be emitted."""
    result = FORM.emit_for_traceback(TRACEBACK, SOURCE)
    plain = next(c for c in result["candidates"] if c["spelling"] == "property")
    patched = FORM.apply_candidate(SOURCE, plain)
    assert ".setter" in patched, "a plain property needs a setter for the stored value"


def test_refuses_a_traceback_without_the_reentrant_shape():
    """The negative control: an ordinary assertion failure is not this repair."""
    plain = """tests/test_x.py:12: in test_y
    assert f() == 3
E   assert 2 == 3
"""
    result = FORM.emit_for_traceback(plain, SOURCE)
    assert result["applies"] is False
    assert result["candidates"] == []


def test_emits_only_on_the_line_the_traceback_names():
    """Every other attribute in __init__ must be left alone."""
    result = FORM.emit_for_traceback(TRACEBACK, SOURCE)
    lines = {c["replaces_line"] for c in result["candidates"]}
    assert len(lines) == 1, f"form fired on more than one line: {lines}"
