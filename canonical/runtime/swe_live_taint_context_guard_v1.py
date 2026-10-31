"""Narrow producer-side guard around the pinned source-to-sink analyzer.

The adapter treats several context-specific quote/escape operations as universal
sanitizers. If such a call and a relevant sink are present, its negative result
may be wrong. Stage the actual adapter output and withhold that result rather
than assert safety. This is not a general taint analysis or an independent
security verification; direct and non-local calls are not covered.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import tempfile
from typing import Any, Callable, Mapping

from canonical.runtime import write_authority_v1


class TaintContextFailure(RuntimeError):
    pass


def _context_hazard(adapter: Any, files: list[pathlib.Path], sink: str) -> bool:
    """Conservatively detect the adapter's context-specific suppression vocabulary.

    These calls need not be on the same dataflow path: when we cannot prove
    that they are unrelated to a sink, we refuse the negative answer. Reuse the
    adapter's own call and sink matching so the check covers its actual contract.
    """
    contextual = {name for name in adapter._SANITIZERS
                  if 'quote' in name.rsplit('.', 1)[-1] or 'escape' in name.rsplit('.', 1)[-1]}
    has_contextual = False
    has_sink = False
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding='utf-8', errors='replace'), filename=str(path))
        except (SyntaxError, ValueError) as exc:
            # The original adapter silently skips such files; a negative result
            # is not justified if the guard cannot examine the subject.
            raise TaintContextFailure('TAINT_SUBJECT_UNPARSEABLE:' + str(path)) from exc
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = adapter._call_name(node)
            dotted = adapter._dotted(node)
            if called in contextual or dotted in contextual:
                has_contextual = True
            if sink:
                has_sink = has_sink or called == sink or dotted == sink
            else:
                has_sink = has_sink or called in adapter._SINKS or dotted.rsplit('.', 1)[-1] in adapter._SINKS
        if has_contextual and has_sink:
            return True
    return False


def run(adapter: Any, fn: Callable[..., Any], args: Mapping[str, Any], root: pathlib.Path) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    source_root = adapter._safe_root(root, args.get('source_root'))
    raw_out = str(args.get('output_path') or '')
    out = (root / raw_out).resolve()
    if out == root or root not in out.parents:
        raise TaintContextFailure('PATH_OUTSIDE_REPOSITORY')
    files = list(adapter._files(source_root))
    for path in files:
        resolved = path.resolve()
        if resolved != root and root not in resolved.parents:
            raise TaintContextFailure('TAINT_INPUT_OUTSIDE_REPOSITORY:' + str(path))
    write_authority_v1.check_report(root, out, files + ([source_root] if source_root.is_file() else []))

    scratch_parent = root / 'canonical/astra_runtime/tmp'
    scratch_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='taint_report_', dir=scratch_parent) as scratch:
        staged = pathlib.Path(scratch) / 'report.json'
        result = fn(dict(args, output_path=staged.relative_to(root).as_posix()), root)
        if not isinstance(result, dict) or result.get('output_verified') is not True or not staged.is_file():
            raise TaintContextFailure('TAINT_ADAPTER_DID_NOT_PRODUCE_REPORT')
        payload = staged.read_bytes()
        if hashlib.sha256(payload).hexdigest() != result.get('output_sha256'):
            raise TaintContextFailure('STAGED_TAINT_REPORT_DIGEST_MISMATCH')
        report = json.loads(payload)
        if report.get('answer') != result.get('answer') or report.get('reaches') != result.get('reaches'):
            raise TaintContextFailure('STAGED_TAINT_REPORT_RESULT_MISMATCH')
        if result.get('answer') == 'no' and _context_hazard(adapter, files, str(args.get('sink') or '')):
            raise TaintContextFailure('CONTEXTUAL_SANITIZER_MAY_HIDE_TAINT')
        # Not a lock: source and output can still change concurrently.
        write_authority_v1.check_report(root, out, files + ([source_root] if source_root.is_file() else []))
        out.parent.mkdir(parents=True, exist_ok=True)
        # Replace only after the complete report is written in the destination
        # directory. This protects an existing report against partial writes;
        # it is neither a concurrency lock nor a durability guarantee.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(prefix='.taint-report-', dir=out.parent, delete=False) as report_file:
                temporary = pathlib.Path(report_file.name)
                report_file.write(payload)
            os.replace(temporary, out)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        result['output_path'] = out.relative_to(root).as_posix()
        result['output_sha256'] = hashlib.sha256(out.read_bytes()).hexdigest()
        return result
