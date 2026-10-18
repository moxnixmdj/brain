"""Bound capability adapters.

This directory is imported as a package (`from canonical.runtime.bound_capabilities
import X`) by the adapter modules themselves. It worked at runtime as a PEP 420
namespace package, but `brain_owned_python_closure_census_v1._module_file` resolves
an owned import to either `<name>.py` or `<name>/__init__.py`, and with neither
present it raised CANONICAL_IMPORT_UNRESOLVED and failed the closure census.

Kept empty on purpose: no shared symbols are re-exported, so importing this package
must not execute adapter code or change what any existing import binds to.
"""
