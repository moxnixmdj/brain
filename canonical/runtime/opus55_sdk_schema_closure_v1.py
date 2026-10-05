from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Iterable

SOURCE_REPOSITORY = "anthropics/anthropic-sdk-python"
SOURCE_REF = "v1.11.0"

DEFAULT_ROOTS = [
    "types/message_create_params.py",
    "types/message.py",
    "types/message_param.py",
    "types/content_block.py",
    "types/stop_reason.py",
    "types/tool_union_param.py",
    "types/beta/message_create_params.py",
    "types/beta/beta_message.py",
    "types/beta/beta_message_param.py",
    "types/beta/beta_content_block.py",
    "types/beta/beta_content_block_param.py",
    "types/beta/beta_stop_reason.py",
    "types/beta/beta_tool_union_param.py",
    "types/anthropic_beta_param.py",
]

EXPECTED_ROOT_BLOBS = {
    "types/message_create_params.py": "585e92451d6399aba980aff392fbc0ba942e85d4",
    "types/message.py": "34dc178ccec1f6b49bfacd0743dcd18689bc3c0d",
    "types/message_param.py": "c3a2046f2ad752cd87722fac4bae8545e317d474",
    "types/content_block.py": "a0baaeb69bab7c74ae6e6aa9613f3381ad416811",
    "types/stop_reason.py": "d28f681b8464057da3ddac61a83548e266880e10",
    "types/tool_union_param.py": "53ddbcb4490ac96b2797c2d952109e40b3d9ae56",
    "types/beta/message_create_params.py": "7f688b24dfc9744f5e0df2678c5fe0bba1b50f44",
    "types/beta/beta_message.py": "afaff2d6ba64aa16943c8788d9b913c8dab56d87",
    "types/beta/beta_message_param.py": "aad1d9c11bffa5975a3203e5633490d0de96968d",
    "types/beta/beta_content_block.py": "8034b978b7fdb990faf0e3c9fdb0e1a338817f2d",
    "types/beta/beta_content_block_param.py": "84f0e1466477a278371f88b507ae86ab308ba8d1",
    "types/beta/beta_stop_reason.py": "f3d0d3070d0eac3065917a5d11cbbc935faebeb8",
    "types/beta/beta_tool_union_param.py": "8a82fb5a4048935e4c0fef28351500e99687bd18",
    "types/anthropic_beta_param.py": "735b323c6676c66246935c95e9ecced63911060c",
}


class SchemaClosureError(RuntimeError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _resolve_relative_import(
    package_root: Path,
    current_rel: Path,
    node: ast.ImportFrom,
) -> list[Path | None]:
    if node.level <= 0:
        return []

    current_package = list(current_rel.with_suffix("").parts[:-1])
    up = node.level - 1
    if up > len(current_package):
        return [None]

    base = current_package[: len(current_package) - up]
    module_parts = node.module.split(".") if node.module else []
    base.extend(module_parts)

    module_candidates: list[tuple[str, ...]] = []
    if node.module:
        module_candidates.append(tuple(base))
    else:
        for alias in node.names:
            module_candidates.append(tuple(base + [alias.name]))

    resolved: list[Path | None] = []
    for parts in module_candidates:
        stem = package_root.joinpath(*parts)
        py_file = stem.with_suffix(".py")
        init_file = stem / "__init__.py"
        if py_file.is_file():
            resolved.append(py_file.relative_to(package_root))
        elif init_file.is_file():
            resolved.append(init_file.relative_to(package_root))
        else:
            resolved.append(None)
    return resolved


def _alias_contract(expr: ast.expr) -> dict[str, object] | None:
    if not isinstance(expr, ast.Subscript):
        return None

    name = ast.unparse(expr.value)
    slice_node = expr.slice
    elements = list(slice_node.elts) if isinstance(slice_node, ast.Tuple) else [slice_node]

    if name.endswith("Annotated"):
        return _alias_contract(elements[0]) if elements else None

    if name.endswith("Union"):
        return {
            "kind": "union",
            "members": [ast.unparse(element) for element in elements],
        }

    if name.endswith("Literal"):
        values: list[object] = []
        for element in elements:
            try:
                values.append(ast.literal_eval(element))
            except Exception:
                values.append(ast.unparse(element))
        return {"kind": "literal", "values": values}

    return None


def extract_contracts(source: str) -> dict[str, object]:
    tree = ast.parse(source)
    aliases: dict[str, object] = {}
    typed_dicts: dict[str, object] = {}

    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            annotation = ast.unparse(node.annotation)
            if annotation == "TypeAlias" or annotation.endswith(".TypeAlias"):
                contract = _alias_contract(node.value)
                if contract is not None:
                    aliases[node.target.id] = contract

        elif isinstance(node, ast.ClassDef):
            bases = {ast.unparse(base) for base in node.bases}
            if any(base == "TypedDict" or base.endswith(".TypedDict") for base in bases):
                fields: dict[str, str] = {}
                for statement in node.body:
                    if (
                        isinstance(statement, ast.AnnAssign)
                        and isinstance(statement.target, ast.Name)
                    ):
                        fields[statement.target.id] = ast.unparse(statement.annotation)
                typed_dicts[node.name] = fields

    return {"aliases": aliases, "typed_dicts": typed_dicts}


def compile_schema_closure(
    package_root: Path,
    roots: Iterable[str] = DEFAULT_ROOTS,
    expected_root_blobs: dict[str, str] | None = EXPECTED_ROOT_BLOBS,
) -> dict[str, object]:
    package_root = package_root.resolve()
    expected = expected_root_blobs or {}
    queue = [Path(root) for root in roots]
    seen: dict[str, object] = {}
    unresolved: list[dict[str, object]] = []

    while queue:
        rel = queue.pop()
        key = rel.as_posix()
        if key in seen:
            continue

        full = package_root / rel
        if not full.is_file():
            raise SchemaClosureError(f"MISSING_ROOT_OR_DEPENDENCY {key}")

        data = full.read_bytes()
        blob_sha = git_blob_sha(data)
        expected_sha = expected.get(key)
        if expected_sha is not None and blob_sha != expected_sha:
            raise SchemaClosureError(
                f"ROOT_BLOB_DRIFT {key} {blob_sha} != {expected_sha}"
            )

        try:
            source = data.decode("utf-8")
            tree = ast.parse(source, filename=key)
        except Exception as exc:
            raise SchemaClosureError(f"PARSE_FAILURE {key}: {exc}") from exc

        seen[key] = {
            "git_blob_sha": blob_sha,
            "contracts": extract_contracts(source),
        }

        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level <= 0:
                continue

            targets = _resolve_relative_import(package_root, rel, node)
            for target in targets:
                if target is None:
                    unresolved.append(
                        {
                            "from": key,
                            "level": node.level,
                            "module": node.module,
                            "names": [alias.name for alias in node.names],
                        }
                    )
                    continue

                target_key = target.as_posix()
                if target_key not in seen:
                    queue.append(target)

    if unresolved:
        raise SchemaClosureError(
            "UNRESOLVED_INTERNAL_IMPORTS "
            + json.dumps(unresolved, sort_keys=True, separators=(",", ":"))
        )

    return {
        "schema": "PROJECT_BRAIN_OPUS55_SDK_TRANSITIVE_SCHEMA_CLOSURE_V1",
        "source_repository": SOURCE_REPOSITORY,
        "source_ref": SOURCE_REF,
        "root_files": list(roots),
        "file_count": len(seen),
        "files": dict(sorted(seen.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile a fail-closed transitive, content-addressed schema closure "
            "from the frozen Anthropic Python SDK package tree."
        )
    )
    parser.add_argument(
        "--package-root",
        type=Path,
        required=True,
        help="Path to the SDK's src/anthropic directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination JSON manifest.",
    )
    args = parser.parse_args()

    manifest = compile_schema_closure(args.package_root)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "OPUS55_SDK_SCHEMA_CLOSURE_PASS "
        f"files={manifest['file_count']} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
