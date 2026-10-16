"""Promote repository inventory into the extended registry only when an oracle proves it works.

    python3 -m canonical.runtime.extended_capability_promoter_v1 --batch bytes_research_tools --check
    python3 -m canonical.runtime.extended_capability_promoter_v1 --batch bytes_research_tools --write

For one batch (a directory of inventoried sources) the promoter:

1. Triages every file statically (AST only, nothing imported): import-time side effects,
   SHA-256 snapshot pins, absolute host paths, public functions, and copy-paste duplicates.
2. For each promotion spec (a capability contract, an adapter in
   ``canonical/runtime/bound_capabilities`` that reuses the research code, and an oracle):
   runs the adapter through ``live_brain_route_admission_v1.run_adapter_locally`` (the same call
   the live router makes) on fixtures, checks every output with a stdlib oracle that imports
   neither the adapter nor the research code, and checks that bad inputs fail closed.
3. Writes ``VERIFIED_BOUND_CAPABILITY`` only for specs whose every case passed, records which
   inventory files each promoted capability reuses, and leaves every other file as inventory.

``--check`` recomputes everything and fails when the registry or batch report differs, so a
change to an adapter, a reused research file, or the oracle shows up as drift.  The recorded
verification block holds counts and hashes only, so it is reproducible run to run.
"""
from __future__ import annotations

import argparse
import ast
import cmath
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import platform
import random
import re
import shutil
import sys
import tokenize
from fractions import Fraction
from typing import Any, Callable

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime.bound_capabilities import research_tool_loader_v1 as loader  # noqa: E402

EXTENDED = ROOT / "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
EXTENDED_SCHEMA = "PROJECT_BRAIN_AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1"
REPORT_SCHEMA = "PROJECT_BRAIN_EXTENDED_CAPABILITY_PROMOTION_BATCH_REPORT_V1"
WORK = ROOT / "canonical/astra_runtime/tmp/extended_capability_promoter_v1"
WORK_REL = WORK.relative_to(ROOT).as_posix()
METHOD = "EXTENDED_CAPABILITY_PROMOTER_V1_ROUTER_CALL_PLUS_STDLIB_ORACLE"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ABS_HOST_PATH = re.compile(r"['\"](/opt/|/mnt/|/tmp/|/home/|/root/|[A-Za-z]:\\\\)")


class OracleFailure(AssertionError):
    pass


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise OracleFailure(message)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- triage

def triage_file(path: pathlib.Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {"parse_error": "line %s" % exc.lineno}
    pins = sorted({n.value.value for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))
                   and isinstance(getattr(n, "value", None), ast.Constant) and isinstance(n.value.value, str)
                   and HEX64.match(n.value.value)})
    public = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            public.append({"name": node.name, "ast_sha256": _sha(ast.dump(node).encode())[:16]})
    return {
        "import_time_effects": len(loader.import_time_effects(tree)),
        "snapshot_hash_pins": len(pins),
        "absolute_host_paths": bool(ABS_HOST_PATH.search(text)),
        "public_symbols": public,
    }


def triage_batch(directory: str, reused: dict[str, list[str]]) -> dict[str, Any]:
    files = sorted((ROOT / directory).glob("*.py"))
    rows: dict[str, Any] = {}
    first_owner: dict[str, str] = {}
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        info = triage_file(path)
        reasons = []
        if "parse_error" in info:
            reasons.append("UNPARSEABLE")
        else:
            if info["import_time_effects"]:
                reasons.append("IMPORT_TIME_SIDE_EFFECTS")
            if info["snapshot_hash_pins"]:
                reasons.append("PINNED_TO_ONE_SNAPSHOT_BY_SHA256")
            if info["absolute_host_paths"]:
                reasons.append("ABSOLUTE_HOST_PATHS")
            if not info["public_symbols"]:
                reasons.append("NO_PUBLIC_ENTRYPOINT")
            dupes = []
            for sym in info["public_symbols"]:
                key = sym["name"] + ":" + sym["ast_sha256"]
                if key in first_owner:
                    dupes.append(sym["name"] + "=" + first_owner[key])
                else:
                    first_owner[key] = rel
            if dupes and len(dupes) == len(info["public_symbols"]):
                reasons.append("ALL_PUBLIC_SYMBOLS_DUPLICATE_EARLIER_FILES")
        disposition = "REUSED_BY_PROMOTED_CAPABILITY" if rel in reused else "REMAINS_INVENTORY"
        rows[rel] = dict(info, disposition=disposition, promoted_to=sorted(reused.get(rel, [])), inventory_reasons=reasons)
    return {"directory": directory, "file_count": len(files), "files": rows,
            "distinct_public_symbols": len(first_owner),
            "public_symbols_total": sum(len(r.get("public_symbols", [])) for r in rows.values())}


# --------------------------------------------------------------------------- oracle helpers

class Workspace:
    def __init__(self, slug: str):
        self.dir = WORK / slug
        self.rel = WORK_REL + "/" + slug
        if self.dir.exists():
            shutil.rmtree(self.dir)
        self.dir.mkdir(parents=True)

    def write(self, name: str, data: str | bytes) -> str:
        path = self.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
        return self.rel + "/" + name

    def path(self, rel: str) -> pathlib.Path:
        return ROOT / rel

    def cleanup(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


class Invoker:
    """Calls one adapter exactly the way the live router does and counts outcomes."""

    def __init__(self, cid: str, entry: dict[str, Any]):
        self.cid, self.entry = cid, entry
        self.positive = 0
        self.negative = 0

    def __call__(self, **inputs: Any) -> dict[str, Any]:
        args = dict(inputs, capability_id=self.cid)
        action = {"type": "invoke_capability", "args": args, "expect": self.entry["action_template"]["expect"]}
        return adm.run_adapter_locally(self.entry, action)

    def ok(self, **inputs: Any) -> dict[str, Any]:
        result = self(**inputs)
        _require(result.get("output_verified") is True and result.get("status") == "PASS", "ADAPTER_DID_NOT_REPORT_PASS")
        self.positive += 1
        return result

    def must_fail(self, label: str, **inputs: Any) -> None:
        try:
            self(**inputs)
        except Exception:  # noqa: BLE001 - any closed failure is the expected outcome
            self.negative += 1
            return
        raise OracleFailure("BAD_INPUT_DID_NOT_FAIL_CLOSED:" + label)


def _strip_docstrings_reference(tree: ast.Module) -> ast.Module:
    """Oracle's own docstring removal, written from the definition, not from the research tool."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                node.body = body[1:] or ([] if isinstance(node, ast.Module) else [ast.Pass()])
    return tree


def _exec_probe(source: str) -> Any:
    namespace: dict[str, Any] = {"__name__": "promoter_probe"}
    exec(compile(source, "<probe>", "exec"), namespace)  # noqa: S102 - oracle-owned fixtures only
    return namespace["probe"]()


PY_FIXTURES = {
    "basic.py": '''"""Module docstring."""
# leading comment
import math  # trailing comment


def area(r: float) -> float:
    """Area of a circle."""
    return math.pi * r ** 2  # formula


class Shape:
    """A shape."""

    sides = 0

    def describe(self):
        """Describe."""
        text = "# not a comment"
        return f"{type(self).__name__} with {self.sides} sides {text}"


def probe():
    """Probe."""
    return [round(area(2), 9), Shape().describe(), area.__name__]
''',
    "nested.py": '''import asyncio


def deco(fn):
    def inner(*a, **k):
        # nested comment
        return ("wrapped", fn(*a, **k))
    return inner


@deco
def compute(values, *, scale=2):
    total = 0
    for v in values:
        if v % 2:
            total += v * scale
        else:
            while v > 0:
                v -= 3
                total += 1
    return total


async def agen(n):
    out = []
    for i in range(n):
        await asyncio.sleep(0)
        out.append(i * i)
    return out


def classify(x):
    match x:
        case 0:
            return "zero"
        case [a, b]:
            return "pair:%s" % (a + b)
        case _:
            return "other"


def probe():
    block = """line one
        indented inside a string # still string
    end"""
    if (n := len(block)) > 10:
        pass
    total = 1 + \\
        2
    return [compute([1, 2, 3, 8]), asyncio.run(agen(4)), classify(0), classify([2, 3]), classify("z"), block, n, total]
''',
    "only_docs.py": '''"""Only a module docstring and docstring-only bodies."""


def empty():
    """Nothing else here."""


class Holder:
    """Holder doc."""


def keeps_non_docstring_strings():
    x = 1
    "not a docstring: not the first statement"
    return x


def fstring_first():
    f"{1 + 1} is not a docstring"
    return 7


def probe():
    return [empty(), Holder.__name__, keeps_non_docstring_strings(), fstring_first()]
''',
}


# --------------------------------------------------------------------------- oracles

def oracle_tree_manifest(call: Invoker, ws: Workspace) -> dict[str, Any]:
    files = {"tree/a.py": "A = 1\n", "tree/pkg.py": "P = 2\n", "tree/pkg/b.py": "B = 'x'\n",
             "tree/pkg/sub/c.py": "def c():\n    return 3\n", "tree/README.md": "ignored\n", "tree/data.json": "{}\n",
             "tree/pkg/__init__.py": ""}
    for name, body in files.items():
        ws.write(name, body)
    root = ws.rel + "/tree"

    def expected() -> tuple[str, list[dict[str, Any]]]:
        base = ws.path(root)
        found = []
        for dirpath, _dirs, names in os.walk(base):
            for name in names:
                if name.endswith(".py"):
                    p = pathlib.Path(dirpath) / name
                    rel = p.relative_to(base)
                    found.append((rel.parts, {"path": rel.as_posix(), "bytes": p.stat().st_size, "sha256": _sha(p.read_bytes())}))
        items = [item for _parts, item in sorted(found, key=lambda pair: pair[0])]
        return _sha(json.dumps(items, sort_keys=True, separators=(",", ":")).encode()), items

    first = call.ok(source_root=root, output_path=ws.rel + "/m1.json")
    digest, items = expected()
    doc = json.loads(ws.path(ws.rel + "/m1.json").read_text())
    _require(doc["items"] == items, "MANIFEST_ITEMS_DIFFER_FROM_OS_WALK")
    _require(first["manifest_sha256"] == doc["manifest_sha256"] == digest, "MANIFEST_DIGEST_WRONG")
    _require(first["file_count"] == 5 and doc["total_bytes"] == sum(i["bytes"] for i in items), "MANIFEST_COUNTS_WRONG")
    again = call.ok(source_root=root, output_path=ws.rel + "/m2.json")
    _require(again["output_sha256"] == first["output_sha256"], "MANIFEST_NOT_DETERMINISTIC")
    ws.write("tree/README.md", "changed non-python file\n")
    _require(call.ok(source_root=root, output_path=ws.rel + "/m3.json")["manifest_sha256"] == digest, "NON_PY_FILE_CHANGED_DIGEST")
    ws.write("tree/pkg/b.py", "B = 'y'\n")
    changed = call.ok(source_root=root, output_path=ws.rel + "/m4.json")
    _require(changed["manifest_sha256"] != digest and changed["manifest_sha256"] == expected()[0], "ONE_BYTE_EDIT_NOT_DETECTED")
    (ws.path(root) / "pkg/b.py").rename(ws.path(root) / "pkg/b2.py")
    renamed = call.ok(source_root=root, output_path=ws.rel + "/m5.json")
    _require(renamed["manifest_sha256"] not in (digest, changed["manifest_sha256"]) and renamed["manifest_sha256"] == expected()[0], "RENAME_NOT_DETECTED")
    research = call.ok(source_root="canonical/research/bytes/tools", output_path=ws.rel + "/m6.json")
    _require(research["file_count"] == len(list((ROOT / "canonical/research/bytes/tools").glob("*.py"))), "REAL_DIRECTORY_COUNT_WRONG")
    ws.write("empty/notes.txt", "no python\n")
    call.must_fail("directory_without_python", source_root=ws.rel + "/empty", output_path=ws.rel + "/bad1.json")
    call.must_fail("input_is_a_file", source_root=ws.rel + "/tree/a.py", output_path=ws.rel + "/bad2.json")
    call.must_fail("non_json_output", source_root=root, output_path=ws.rel + "/bad3.txt")
    call.must_fail("escape_repository", source_root="..", output_path=ws.rel + "/bad4.json")
    return {"checks": ["items equal os.walk listing sorted by path components", "digest = sha256(canonical items json)",
                       "deterministic", "non-.py edits ignored", "one-byte edit and rename change the digest",
                       "real 106-file research directory counted"]}


def _compact_checks(original: str, produced: str) -> None:
    a = ast.dump(ast.parse(original, type_comments=True), include_attributes=False)
    b = ast.dump(ast.parse(produced, type_comments=True), include_attributes=False)
    _require(a == b, "COMPACT_AST_CHANGED")
    comments = [t for t in tokenize.generate_tokens(io.StringIO(produced).readline) if t.type == tokenize.COMMENT]
    _require(not comments, "COMPACT_LEFT_COMMENTS")
    _require(len(produced.encode()) <= len(original.encode()), "COMPACT_GREW_SOURCE")


def oracle_source_compact(call: Invoker, ws: Workspace) -> dict[str, Any]:
    for name, body in PY_FIXTURES.items():
        rel = ws.write("in/" + name, body)
        out = ws.rel + "/out/" + name
        result = call.ok(input_path=rel, output_path=out)
        produced = ws.path(out).read_text()
        _compact_checks(body, produced)
        _require(_exec_probe(produced) == _exec_probe(body), "COMPACT_CHANGED_BEHAVIOUR:" + name)
        _require(ws.path(rel).read_text() == body, "COMPACT_MODIFIED_INPUT")
        _require(result["bytes_saved"] == len(body.encode()) - len(produced.encode()), "COMPACT_BYTES_SAVED_WRONG")
    corpus = sorted((ROOT / "canonical/research/bytes/tools").glob("*.py"))
    for path in corpus:
        rel = path.relative_to(ROOT).as_posix()
        out = ws.rel + "/corpus/" + path.name
        try:
            call.ok(input_path=rel, output_path=out)
        except Exception as exc:  # noqa: BLE001 - name the real file the contract broke on
            raise OracleFailure("COMPACT_CONTRACT_BROKEN_ON_REAL_FILE:" + path.name + ":" + str(exc)[:160]) from None
        _compact_checks(path.read_text(encoding="utf-8"), ws.path(out).read_text(encoding="utf-8"))
    bad = ws.write("in/broken.py", "def broken(:\n    pass\n")
    call.must_fail("syntax_error", input_path=bad, output_path=ws.rel + "/out/broken.py")
    _require(not ws.path(ws.rel + "/out/broken.py").exists(), "COMPACT_LEFT_PARTIAL_OUTPUT")
    same = ws.rel + "/in/basic.py"
    call.must_fail("in_place", input_path=same, output_path=same)
    call.must_fail("non_python_input", input_path=ws.write("in/x.txt", "x = 1\n"), output_path=ws.rel + "/out/x.py")
    return {"checks": ["AST identical (oracle re-parse)", "no comment tokens", "never grows", "probe() behaviour identical",
                       "input untouched", "AST identity on all research tool files", "syntax error fails closed with no output"],
            "real_corpus_files": len(corpus)}


def _docstring_checks(original: str, produced: str) -> None:
    expected = _strip_docstrings_reference(ast.parse(original, type_comments=True))
    got = ast.parse(produced, type_comments=True)
    _require(ast.dump(expected, include_attributes=False) == ast.dump(got, include_attributes=False), "DOCSTRING_STRIP_AST_WRONG")
    for node in ast.walk(got):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            _require(ast.get_docstring(node, clean=False) is None, "DOCSTRING_REMAINS")


def oracle_docstring_strip(call: Invoker, ws: Workspace) -> dict[str, Any]:
    for name, body in PY_FIXTURES.items():
        rel = ws.write("in/" + name, body)
        out = ws.rel + "/out/" + name
        result = call.ok(input_path=rel, output_path=out)
        produced = ws.path(out).read_text()
        _docstring_checks(body, produced)
        _require(_exec_probe(produced) == _exec_probe(body), "DOCSTRING_STRIP_CHANGED_BEHAVIOUR:" + name)
        expected_removed = sum(1 for n in ast.walk(ast.parse(body)) if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                               and ast.get_docstring(n, clean=False) is not None)
        _require(result["docstrings_removed"] == expected_removed, "DOCSTRING_COUNT_WRONG:" + name)
    namespace: dict[str, Any] = {}
    exec(compile(ws.path(ws.rel + "/out/basic.py").read_text(), "<doc>", "exec"), namespace)  # noqa: S102
    _require(namespace["area"].__doc__ is None and namespace["Shape"].__doc__ is None, "RUNTIME_DOC_NOT_REMOVED")
    corpus = sorted((ROOT / "canonical/research/bytes/tools").glob("*.py"))
    for path in corpus:
        out = ws.rel + "/corpus/" + path.name
        call.ok(input_path=path.relative_to(ROOT).as_posix(), output_path=out)
        _docstring_checks(path.read_text(encoding="utf-8"), ws.path(out).read_text(encoding="utf-8"))
    call.must_fail("syntax_error", input_path=ws.write("in/broken.py", "class (:\n"), output_path=ws.rel + "/out/broken.py")
    call.must_fail("in_place", input_path=ws.rel + "/in/basic.py", output_path=ws.rel + "/in/basic.py")
    call.must_fail("escape_repository", input_path="../outside.py", output_path=ws.rel + "/out/o.py")
    return {"checks": ["AST equals oracle's own docstring removal", "no docstring remains", "probe() behaviour identical",
                       "__doc__ is None at runtime", "non-first strings and f-strings kept", "all research tool files"],
            "real_corpus_files": len(corpus)}


def oracle_semantic_digest(call: Invoker, ws: Workspace) -> dict[str, Any]:
    base = {"name": "brain", "values": [1, 2.5, True, None, "1"], "nested": {"b": {"y": 1, "x": [0.1]}, "a": "é"}}
    same_class = [
        base,
        {"nested": {"a": "é", "b": {"x": [0.1], "y": 1}}, "values": [1, 2.5, True, None, "1"], "name": "brain"},
    ]
    different = [
        dict(base, values=[1.0, 2.5, True, None, "1"]),   # int 1 vs float 1.0
        dict(base, values=[True, 2.5, True, None, "1"]),  # 1 vs true
        dict(base, values=[1, 2.5, True, None, 1]),       # "1" vs 1
        dict(base, values=[2.5, 1, True, None, "1"]),     # array order matters
        dict(base, nested={"b": {"y": 1, "x": [0.1]}}),   # missing key
        dict(base, extra=None),                            # null-valued key is not absence
        dict(base, nested={"b": {"y": 1, "x": [0.30000000000000004]}, "a": "é"}),
        dict(base, nested={"b": {"y": 1, "x": [0.3]}, "a": "é"}),
        [base],
        "brain",
    ]
    digests = []
    for i, value in enumerate(same_class + different):
        indent = 2 if i % 2 else None
        rel = ws.write("in/%02d.json" % i, json.dumps(value, indent=indent, ensure_ascii=bool(i % 3)))
        result = call.ok(input_path=rel, output_path=ws.rel + "/out/%02d.json" % i)
        _require(HEX64.match(result["semantic_digest"]) is not None, "DIGEST_NOT_SHA256_HEX")
        _require(json.loads(ws.path(ws.rel + "/out/%02d.json" % i).read_text())["semantic_digest"] == result["semantic_digest"], "DIGEST_FILE_MISMATCH")
        digests.append(result["semantic_digest"])
    _require(len(set(digests[:len(same_class)])) == 1, "KEY_ORDER_OR_WHITESPACE_CHANGED_DIGEST")
    _require(len(set(digests)) == 1 + len(different), "DISTINCT_VALUES_COLLIDED")
    repeat = call.ok(input_path=ws.rel + "/in/00.json", output_path=ws.rel + "/out/repeat.json")
    _require(repeat["semantic_digest"] == digests[0], "DIGEST_NOT_DETERMINISTIC")
    call.must_fail("invalid_json", input_path=ws.write("in/bad.json", "{"), output_path=ws.rel + "/out/bad.json")
    call.must_fail("nan_literal", input_path=ws.write("in/nan.json", '{"x": NaN}'), output_path=ws.rel + "/out/nan.json")
    call.must_fail("non_json_input", input_path=ws.write("in/x.txt", "{}"), output_path=ws.rel + "/out/x.json")
    call.must_fail("in_place", input_path=ws.rel + "/in/00.json", output_path=ws.rel + "/in/00.json")
    return {"checks": ["key order and whitespace invariant", "int/float/bool/string/null/order distinguished",
                       "exact float bits distinguished", "deterministic"], "equivalence_classes": 1 + len(different)}


# Exact symbolic oracle: a tiny exact evaluator over sympy's str() output.

_ALLOWED_BINOPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b}


def _eval_text(text: str, env: dict[str, Any], complex_mode: bool = False) -> Any:
    def ev(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Tuple):
            return tuple(ev(e) for e in node.elts)
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            return complex(node.value) if complex_mode else Fraction(node.value)
        if isinstance(node, ast.Name) and node.id in env:
            return env[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            v = ev(node.operand)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
            return _ALLOWED_BINOPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            base, exp = ev(node.left), ev(node.right)
            if not complex_mode:
                _require(isinstance(exp, Fraction) and exp.denominator == 1, "NON_INTEGER_POWER_IN_EXACT_MODE")
                return base ** int(exp)
            return complex(base) ** complex(exp)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sqrt" and complex_mode and len(node.args) == 1:
            return cmath.sqrt(complex(ev(node.args[0])))
        raise OracleFailure("UNSUPPORTED_RESULT_SYNTAX:" + ast.dump(node)[:80])
    return ev(ast.parse(text, mode="eval"))


def _poly_value(coeffs_high_to_low: list[int], x: Any) -> Any:
    value: Any = 0
    for c in coeffs_high_to_low:
        value = value * x + c
    return value


def _det(matrix: list[list[Fraction]]) -> Fraction:
    m = [row[:] for row in matrix]
    n, det = len(m), Fraction(1)
    for col in range(n):
        pivot = next((r for r in range(col, n) if m[r][col] != 0), None)
        if pivot is None:
            return Fraction(0)
        if pivot != col:
            m[col], m[pivot] = m[pivot], m[col]
            det = -det
        det *= m[col][col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            m[r] = [a - f * b for a, b in zip(m[r], m[col])]
    return det


def _solve(n: int, flat: list[int], vec: list[int]) -> list[Fraction]:
    m = [[Fraction(flat[i * n + j]) for j in range(n)] + [Fraction(vec[i])] for i in range(n)]
    for col in range(n):
        pivot = next(r for r in range(col, n) if m[r][col] != 0)
        m[col], m[pivot] = m[pivot], m[col]
        m[col] = [v / m[col][col] for v in m[col]]
        for r in range(n):
            if r != col and m[r][col] != 0:
                f = m[r][col]
                m[r] = [a - f * b for a, b in zip(m[r], m[col])]
    return [m[i][n] for i in range(n)]


def _binom(n: int, k: int) -> int:
    out = 1
    for i in range(1, k + 1):
        out = out * (n - k + i) // i
    return out


def _symbolic_cases(seed: int, per: int) -> list[dict[str, Any]]:
    r = random.Random(seed)
    nz = lambda lo, hi: r.choice([v for v in range(lo, hi + 1) if v])  # noqa: E731
    cases: list[dict[str, Any]] = []
    for _ in range(per):
        cases.append({"op": "rat", "p": [nz(-9, 9), r.randint(1, 9), nz(-9, 9), r.randint(1, 9), nz(-9, 9), r.randint(1, 9)]})
        deg = r.choice([2, 3, 4, 5, 6])
        cases.append({"op": "factor", "p": [nz(-4, 4)] + [r.randint(-5, 5) for _ in range(deg)]})
        deg = r.choice([2, 3, 4, 5, 6, 7])
        cases.append({"op": "coeff", "p": [[nz(-6, 6)] + [r.randint(-7, 7) for _ in range(deg)], r.randint(0, deg)]})
        roots_from = [r.randint(-4, 4) for _ in range(r.choice([2, 3]))]
        coeffs = [1]
        for root in roots_from:
            coeffs = [a - root * b for a, b in zip(coeffs + [0], [0] + coeffs)]
        cases.append({"op": "roots", "p": coeffs if r.random() < 0.5 else [nz(-4, 4)] + [r.randint(-6, 6) for _ in range(2)]})
        cases.append({"op": "diff", "p": [[[c, e] for e, c in enumerate(r.randint(-7, 7) for _ in range(r.randint(3, 9))) if c] or [[1, 2]], r.randint(1, 3)]})
        cases.append({"op": "sin_even_integral", "p": [r.randint(0, 12)]})
        cases.append({"op": "hilbert_det", "p": [r.randint(1, 6)]})
        cases.append({"op": "binomial_identity", "p": [r.randint(0, 40)]})
        cases.append({"op": "limit_poly_ratio", "p": [nz(-8, 8), r.randint(-8, 8), r.randint(-8, 8), nz(-8, 8), r.randint(1, 8)]})
        cases.append({"op": "limit_sinx", "p": [nz(-12, 12)]})
        while True:
            n = r.choice([2, 3])
            flat = [r.randint(-5, 5) for _ in range(n * n)]
            if _det([[Fraction(flat[i * n + j]) for j in range(n)] for i in range(n)]) != 0:
                break
        cases.append({"op": "linear_solve", "p": [n, flat, [r.randint(-6, 6) for _ in range(n)]]})
        cases.append({"op": "series_coeff", "p": [[r.randint(-5, 5) for _ in range(r.randint(2, 6))], r.randint(0, 9)]})
    return cases


def _check_symbolic(case: dict[str, Any], text: str) -> None:
    op, p = case["op"], case["p"]
    exact = lambda: _eval_text(text, {})  # noqa: E731
    if op == "rat":
        a, b, c, d, e, f = p
        _require(exact() == Fraction(a, b) + Fraction(c, d) * Fraction(e, f), "RAT")
    elif op == "coeff":
        coeffs, k = p
        _require(exact() == coeffs[len(coeffs) - 1 - k], "COEFF")
    elif op == "factor":
        for x in (Fraction(v, 3) for v in range(-5, 5)):
            _require(_eval_text(text, {"x": x}) == _poly_value(p, x), "FACTOR_NOT_EQUAL_TO_POLYNOMIAL")
    elif op == "diff":
        terms, n = p
        poly = {e: c for c, e in terms}
        for _ in range(n):
            poly = {e - 1: c * e for e, c in poly.items() if e > 0}
        for x in (Fraction(v, 2) for v in range(-6, 6)):
            got = _eval_text(text, {"x": x})
            _require(got == sum((c * x ** e for e, c in poly.items()), Fraction(0)), "DIFF")
    elif op == "roots":
        pairs = _eval_text(text, {"I": 1j}, complex_mode=True)
        _require(isinstance(pairs, tuple) and all(isinstance(t, tuple) and len(t) == 2 for t in pairs), "ROOTS_SHAPE")
        _require(sum(int(round(m.real)) for _r, m in pairs) == len(p) - 1, "ROOTS_MULTIPLICITY_SUM")
        rebuilt = [complex(p[0])]
        for root, mult in pairs:
            for _ in range(int(round(mult.real))):
                rebuilt = [a - root * b for a, b in zip(rebuilt + [0], [0] + rebuilt)]
        _require(all(abs(a - b) <= 1e-7 * max(1.0, abs(b)) for a, b in zip(rebuilt, p)), "ROOTS_DO_NOT_REBUILD_POLYNOMIAL")
    elif op == "sin_even_integral":
        n = p[0]
        at2, at3 = _eval_text(text, {"pi": Fraction(2)}), _eval_text(text, {"pi": Fraction(3)})
        _require(at2 / 2 == at3 / 3 == Fraction(_binom(2 * n, n), 4 ** n), "SIN_EVEN_INTEGRAL")
    elif op == "hilbert_det":
        n = p[0]
        _require(exact() == _det([[Fraction(1, i + j + 1) for j in range(n)] for i in range(n)]), "HILBERT_DET")
    elif op == "binomial_identity":
        _require(exact() == 2 ** p[0], "BINOMIAL_IDENTITY")
    elif op == "limit_poly_ratio":
        _require(exact() == Fraction(p[0], p[3]), "LIMIT_POLY_RATIO")
    elif op == "limit_sinx":
        _require(exact() == p[0], "LIMIT_SINX")
    elif op == "linear_solve":
        _require(list(exact()) == _solve(*p), "LINEAR_SOLVE")
    elif op == "series_coeff":
        coeffs, k = p
        _require(exact() == sum(c * (k - i + 1) for i, c in enumerate(coeffs) if i <= k), "SERIES_COEFF")
    else:
        raise OracleFailure("UNKNOWN_OP:" + op)


def oracle_exact_symbolic(call: Invoker, ws: Workspace) -> dict[str, Any]:
    cases = _symbolic_cases(seed=20261016, per=25)
    rel = ws.write("in/cases.json", json.dumps({"cases": cases}))
    result = call.ok(input_path=rel, output_path=ws.rel + "/out/results.json")
    doc = json.loads(ws.path(ws.rel + "/out/results.json").read_text())
    _require(result["case_count"] == doc["case_count"] == len(cases) == len(doc["results"]), "CASE_COUNT")
    per_op: dict[str, int] = {}
    for case, row in zip(cases, doc["results"]):
        _require(row["op"] == case["op"] and row["p"] == case["p"], "RESULT_ORDER")
        try:
            _check_symbolic(case, row["result_text"])
        except OracleFailure as exc:
            raise OracleFailure(str(exc) + ":" + json.dumps(case) + ":" + row["result_text"][:200]) from None
        per_op[case["op"]] = per_op.get(case["op"], 0) + 1
    again = call.ok(input_path=rel, output_path=ws.rel + "/out/results2.json")
    _require(again["output_sha256"] == result["output_sha256"], "SYMBOLIC_NOT_DETERMINISTIC")
    call.must_fail("unknown_op", input_path=ws.write("in/u.json", '{"cases":[{"op":"integrate_anything","p":[1]}]}'), output_path=ws.rel + "/out/u.json")
    call.must_fail("empty_cases", input_path=ws.write("in/e.json", '{"cases":[]}'), output_path=ws.rel + "/out/e.json")
    call.must_fail("too_many_cases", input_path=ws.write("in/m.json", json.dumps({"cases": [{"op": "rat", "p": [1, 1, 1, 1, 1, 1]}] * 2001})), output_path=ws.rel + "/out/m.json")
    call.must_fail("p_not_list", input_path=ws.write("in/p.json", '{"cases":[{"op":"rat","p":"1,2"}]}'), output_path=ws.rel + "/out/p.json")
    call.must_fail("singular_system", input_path=ws.write("in/s.json", '{"cases":[{"op":"linear_solve","p":[2,[1,2,2,4],[1,1]]}]}'), output_path=ws.rel + "/out/s.json")
    return {"checks": ["exact Fraction arithmetic for rat/coeff/diff/factor/hilbert/binomial/limits/linear/series",
                       "factor and diff compared as polynomials at 10-12 exact rational points",
                       "roots rebuild the polynomial (complex, 1e-7) with multiplicities summing to degree",
                       "sin^2n integral = pi*C(2n,n)/4^n checked by linearity in pi"],
            "cases_by_op": dict(sorted(per_op.items()))}


# --------------------------------------------------------------------------- promotion specs

PLATFORMS = ["linux"]
STDLIB_ADAPTER_MODULES = ["ast", "hashlib", "importlib", "json", "pathlib"]

BATCHES: dict[str, dict[str, Any]] = {
    "bytes_research_tools": {
        "directory": "canonical/research/bytes/tools",
        "specs": [
            {
                "capability_id": "python.source_tree.manifest.sha256",
                "adapter_module": "research_python_tree_manifest_v1",
                "input_key": "source_root",
                "research_sources": ["canonical/research/bytes/tools/conservative_algebraicnumber_prune_v42.py"],
                "modules": STDLIB_ADAPTER_MODULES,
                "requires": ["python.source_tree.available"],
                "provides": ["python.source_tree.manifest_sha256"],
                "keywords": ["manifest", "fingerprint", "sha256", "python", "source", "tree", "directory", "snapshot", "hash"],
                "result_fields": ["status", "manifest_sha256", "file_count", "total_bytes", "output_path", "output_sha256", "output_verified"],
                "limitations": ["Covers *.py files only; other files never affect the digest.",
                                "Paths are relative to the given directory, so the same tree elsewhere gives the same digest.",
                                "Fails closed when the directory holds no Python files."],
                "oracle": oracle_tree_manifest,
            },
            {
                "capability_id": "python.source.compact.ast_identical",
                "adapter_module": "research_python_source_compact_v1",
                "research_sources": ["canonical/research/bytes/tools/rebuild_v81_from_v78.py"],
                "modules": STDLIB_ADAPTER_MODULES + ["tokenize"],
                "requires": ["python.source_file.available"],
                "provides": ["python.source_file.compacted_ast_identical"],
                "keywords": ["compact", "minify", "comments", "indentation", "shrink", "python", "ast", "identical"],
                "result_fields": ["status", "bytes_saved", "ast_identical", "comments_remaining", "output_path", "output_sha256", "output_verified"],
                "limitations": ["Removes comments (including pragma, noqa, type: ignore and encoding comments) and re-indents one space per level.",
                                "Docstrings are kept; output formatting is not meant for human reading.",
                                "Code that reads its own source text (inspect.getsource, tracebacks) will see the compacted text."],
                "oracle": oracle_source_compact,
            },
            {
                "capability_id": "python.source.docstrings.strip",
                "adapter_module": "research_python_docstring_strip_v1",
                "research_sources": ["canonical/research/bytes/tools/conservative_docstring_strip_v76.py"],
                "modules": STDLIB_ADAPTER_MODULES,
                "requires": ["python.source_file.available"],
                "provides": ["python.source_file.docstrings_stripped"],
                "keywords": ["docstring", "docstrings", "strip", "remove", "python", "ast"],
                "result_fields": ["status", "docstrings_removed", "docstrings_remaining", "output_path", "output_sha256", "output_verified"],
                "limitations": ["Output is ast.unparse text: comments and original formatting are dropped.",
                                "Changes behaviour of code that reads __doc__ (argparse descriptions, doctest, help())."],
                "oracle": oracle_docstring_strip,
            },
            {
                "capability_id": "structured.document.semantic_digest.sha256",
                "adapter_module": "research_json_semantic_digest_v1",
                "research_sources": ["canonical/research/bytes/tools/semantic_digest_v1.py"],
                "modules": ["hashlib", "json", "pathlib"],
                "requires": ["structured.document.available"],
                "provides": ["structured.document.semantic_digest"],
                "keywords": ["semantic", "digest", "fingerprint", "sha256", "equality", "order", "invariant", "structured", "document"],
                "result_fields": ["status", "semantic_digest", "output_path", "output_sha256", "output_verified"],
                "limitations": ["Input must be a .json file. Object key order and whitespace are ignored; array order is significant.",
                                "Numbers are typed: 1 and 1.0 differ, and floats compare by exact binary value.",
                                "NaN and Infinity literals are rejected."],
                "oracle": oracle_semantic_digest,
            },
            {
                "capability_id": "math.exact_symbolic.compute.sympy",
                "adapter_module": "research_exact_symbolic_compute_v1",
                "research_sources": ["canonical/research/bytes/tools/exact_symbolic_route_v1.py",
                                     "canonical/research/bytes/tools/semantic_digest_v1.py"],
                "modules": ["sympy", "hashlib", "json", "pathlib"],
                "third_party": {"sympy": "1.14.0"},
                "source_type": "brain_owned_python_composition",
                "requires": ["math.exact_symbolic.cases.available"],
                "provides": ["math.exact_symbolic.results"],
                "keywords": ["symbolic", "exact", "sympy", "factor", "roots", "polynomial", "derivative", "limit", "determinant", "hilbert", "series", "rational"],
                "result_fields": ["status", "case_count", "output_path", "output_sha256", "output_verified"],
                "limitations": ["Only the 12 typed operations of exact_symbolic_route_v1 over the variable x; no free-form expressions.",
                                "Requires SymPy (pinned 1.14.0 by math.numeric_expression.sympy); fails closed when SymPy is absent.",
                                "At most 2000 cases per call; a singular linear system fails the whole call."],
                "oracle": oracle_exact_symbolic,
            },
        ],
    },
}


def _entry_skeleton(spec: dict[str, Any]) -> dict[str, Any]:
    adapter_rel = "canonical/runtime/bound_capabilities/" + spec["adapter_module"] + ".py"
    source = {"type": spec.get("source_type", "brain_native_deterministic"), "modules": list(spec["modules"]),
              "adapter_path": adapter_rel, "research_sources": list(spec["research_sources"])}
    if spec.get("third_party"):
        source["third_party_versions"] = dict(spec["third_party"])
    return {
        "status": "UNVERIFIED_CANDIDATE",
        "incremental_spend_usd": 0,
        "cost": 1,
        "requires": list(spec["requires"]),
        "provides": list(spec["provides"]),
        "result_fields": list(spec["result_fields"]),
        "keywords": list(spec["keywords"]),
        "action_template": {
            "type": "invoke_capability",
            "args": {"capability_id": spec["capability_id"], spec.get("input_key", "input_path"): "${input.%s}" % spec.get("input_key", "input_path"),
                     "output_path": "${input.output_path}"},
            "expect": {"type": "field_equals", "field": "output_verified", "value": True},
        },
        "adapter_module": spec["adapter_module"],
        "entrypoint": "run",
        "platforms": list(PLATFORMS),
        "limitations": list(spec["limitations"]),
        "source": source,
    }


def _dependency_gap(spec: dict[str, Any]) -> list[str]:
    return [m for m in spec["modules"] if importlib.util.find_spec(m.split(".")[0]) is None]


def _installed_versions(spec: dict[str, Any]) -> dict[str, str]:
    out = {}
    for name in sorted(spec.get("third_party") or {}):
        module = __import__(name)
        out[name] = str(getattr(module, "__version__", "unknown"))
    return out


def verify_spec(spec: dict[str, Any]) -> dict[str, Any]:
    cid = spec["capability_id"]
    entry = _entry_skeleton(spec)
    missing = _dependency_gap(spec)
    if missing:
        return {"capability_id": cid, "outcome": "DEPENDENCY_UNAVAILABLE", "missing_modules": missing}
    pinned = spec.get("third_party") or {}
    installed = _installed_versions(spec)
    if installed != pinned:
        return {"capability_id": cid, "outcome": "DEPENDENCY_VERSION_MISMATCH", "installed": installed, "pinned": pinned}
    unsafe = [rel for rel in spec["research_sources"] if loader.import_time_effects(ast.parse((ROOT / rel).read_text(encoding="utf-8")))]
    if unsafe:
        return {"capability_id": cid, "outcome": "RESEARCH_SOURCE_NOT_IMPORT_SAFE", "files": unsafe}
    call = Invoker(cid, dict(entry, capability_id=cid))
    ws = Workspace(re.sub(r"[^a-z0-9]+", "_", cid.lower()))
    try:
        detail = spec["oracle"](call, ws)
    except Exception as exc:  # noqa: BLE001 - any oracle or adapter failure keeps the candidate unpromoted
        return {"capability_id": cid, "outcome": "ORACLE_FAILED", "reason": type(exc).__name__ + ":" + str(exc)[:600],
                "cases_passed_before_failure": call.positive}
    finally:
        ws.cleanup()
    entry["status"] = "VERIFIED_BOUND_CAPABILITY"
    entry["verification"] = {
        "verified": True,
        "method": METHOD,
        "executed_through": "canonical/runtime/live_brain_route_admission_v1.py:run_adapter_locally",
        "positive_cases_passed": call.positive,
        "bad_inputs_failed_closed": call.negative,
        "oracle": "canonical/runtime/extended_capability_promoter_v1.py:" + spec["oracle"].__name__,
        "oracle_checks": detail.pop("checks"),
        "oracle_detail": detail,
        "adapter_sha256": _sha((ROOT / entry["source"]["adapter_path"]).read_bytes()),
        "loader_sha256": _sha((ROOT / "canonical/runtime/bound_capabilities/research_tool_loader_v1.py").read_bytes()),
        "research_source_sha256": {rel: loader.source_sha256(ROOT, rel) for rel in spec["research_sources"]},
        "measured_platform": sys.platform,
        "measured_python": "%d.%d" % sys.version_info[:2],
        "third_party_versions_measured": installed,
        "model_dependency_count": 0,
    }
    return {"capability_id": cid, "outcome": "PROMOTED", "entry": entry}


# --------------------------------------------------------------------------- registry + report

def report_path(batch: str) -> pathlib.Path:
    return ROOT / "canonical/research/bytes" / ("EXTENDED_CAPABILITY_PROMOTION_%s_V1.json" % batch.upper())


def run_batch(batch: str) -> dict[str, Any]:
    spec_list = BATCHES[batch]["specs"]
    outcomes = [verify_spec(spec) for spec in spec_list]
    reused: dict[str, list[str]] = {}
    for spec, outcome in zip(spec_list, outcomes):
        if outcome["outcome"] == "PROMOTED":
            for rel in spec["research_sources"]:
                reused.setdefault(rel, []).append(spec["capability_id"])
    triage = triage_batch(BATCHES[batch]["directory"], reused)
    reasons: dict[str, int] = {}
    for row in triage["files"].values():
        for reason in row["inventory_reasons"]:
            reasons[reason] = reasons.get(reason, 0) + 1
    report = {
        "schema": REPORT_SCHEMA,
        "batch": batch,
        "method": METHOD,
        "directory": triage["directory"],
        "file_count": triage["file_count"],
        "public_symbols_total": triage["public_symbols_total"],
        "distinct_public_symbols": triage["distinct_public_symbols"],
        "files_reused_by_promoted_capabilities": sum(1 for r in triage["files"].values() if r["promoted_to"]),
        "inventory_reason_counts": dict(sorted(reasons.items())),
        "candidate_count": len(spec_list),
        "promoted_count": sum(1 for o in outcomes if o["outcome"] == "PROMOTED"),
        "outcomes": [{k: v for k, v in o.items() if k != "entry"} | ({"positive_cases_passed": o["entry"]["verification"]["positive_cases_passed"],
                                                                      "bad_inputs_failed_closed": o["entry"]["verification"]["bad_inputs_failed_closed"]}
                                                                     if o["outcome"] == "PROMOTED" else {}) for o in outcomes],
        "files": triage["files"],
    }
    return {"report": report, "outcomes": outcomes, "reused": reused}


def apply_to_registry(doc: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    caps = dict(doc["capabilities"])
    for outcome in result["outcomes"]:
        if outcome["outcome"] == "PROMOTED":
            caps[outcome["capability_id"]] = outcome["entry"]
    for rel, cids in result["reused"].items():
        key = rel + ".auto.v1"
        if key in caps and caps[key].get("status") == "UNVERIFIED_INVENTORY":
            caps[key] = dict(caps[key], promoted_to=sorted(cids))
    return {"schema": doc["schema"], "capabilities": dict(sorted(caps.items()))}


def _dump(doc: Any) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--batch", required=True, choices=sorted(BATCHES))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail on any difference from the committed registry/report")
    mode.add_argument("--write", action="store_true", help="write promoted entries and the batch report")
    args = ap.parse_args(argv)
    result = run_batch(args.batch)
    doc = json.loads(EXTENDED.read_text(encoding="utf-8"))
    if doc.get("schema") != EXTENDED_SCHEMA or not isinstance(doc.get("capabilities"), dict):
        raise SystemExit("EXTENDED_REGISTRY_INVALID")
    for outcome in result["outcomes"]:
        print("%-42s %s" % (outcome["capability_id"], outcome["outcome"]
                            + ("" if outcome["outcome"] == "PROMOTED" else " " + json.dumps({k: v for k, v in outcome.items() if k not in ("capability_id", "outcome")})[:300])))
    unavailable = [o for o in result["outcomes"] if o["outcome"] in ("DEPENDENCY_UNAVAILABLE", "DEPENDENCY_VERSION_MISMATCH")]
    if args.write:
        if unavailable:
            print("refusing to write: install the pinned dependencies so every candidate is measured")
            return 2
        new_doc = apply_to_registry(doc, result)
        EXTENDED.write_text(_dump(new_doc), encoding="utf-8")
        report_path(args.batch).write_text(_dump(result["report"]), encoding="utf-8")
        print("promoted %d/%d; report %s" % (result["report"]["promoted_count"], result["report"]["candidate_count"],
                                             report_path(args.batch).relative_to(ROOT)))
        return 0
    drift = []
    skip = {o["capability_id"] for o in unavailable}
    expected = apply_to_registry(doc, result)["capabilities"]
    for outcome in result["outcomes"]:
        cid = outcome["capability_id"]
        if cid in skip:
            continue
        if expected.get(cid) != doc["capabilities"].get(cid) or (outcome["outcome"] != "PROMOTED" and cid in doc["capabilities"]):
            drift.append("REGISTRY_ENTRY_DRIFT:" + cid)
    committed = json.loads(report_path(args.batch).read_text(encoding="utf-8")) if report_path(args.batch).is_file() else None
    if not skip and committed != result["report"]:
        drift.append("BATCH_REPORT_DRIFT:" + str(report_path(args.batch).relative_to(ROOT)))
    for item in drift:
        print(item)
    if skip:
        print("not measured here (dependency unavailable): " + ", ".join(sorted(skip)))
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
