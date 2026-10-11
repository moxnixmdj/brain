import contextlib
import hashlib
import io

from canonical.runtime.osworld_v21_state_ops_v1 import StateOpsError, compile_state_ops


def test_compile_file_ops_and_allowlisted_cli():
    src = compile_state_ops({
        "ops": [
            {"type": "MKDIR", "path": "/home/oai/share/x"},
            {"type": "WRITE_TEXT", "path": "/home/oai/share/x/a.txt", "text": "hello"},
            {"type": "RUN_CLI", "argv": ["ffprobe", "-version"], "timeout_s": 5},
        ]
    })
    assert "MKDIR:PASS:/home/oai/share/x" in src
    assert "write_text('hello'" in src
    assert "subprocess.run(['ffprobe', '-version']" in src


def test_protected_paths_fail_closed():
    try:
        compile_state_ops({"ops": [{"type": "WRITE_TEXT", "path": "/evaluation_examples/task_class/task_001.py", "text": "x"}]})
    except StateOpsError as exc:
        assert str(exc) == "PROTECTED_PATH_FORBIDDEN"
    else:
        raise AssertionError("expected protected path rejection")


def test_arbitrary_cli_rejected():
    try:
        compile_state_ops({"ops": [{"type": "RUN_CLI", "argv": ["curl", "https://example.com"]}]})
    except StateOpsError as exc:
        assert str(exc).startswith("RUN_CLI_EXECUTABLE_NOT_ALLOWED")
    else:
        raise AssertionError("expected cli rejection")


def test_shell_and_interpreter_escape_hatches_rejected():
    for exe in ("bash", "python", "python3"):
        try:
            compile_state_ops({"ops": [{"type": "RUN_CLI", "argv": [exe, "-c", "print(1)"]}]})
        except StateOpsError as exc:
            assert str(exc).startswith("RUN_CLI_EXECUTABLE_NOT_ALLOWED")
        else:
            raise AssertionError("expected interpreter rejection")


def test_cli_absolute_args_respect_protected_paths():
    try:
        compile_state_ops({"ops": [{"type": "RUN_CLI", "argv": ["pdftotext", "/benchmark_releases/x.pdf", "/home/oai/share/x.txt"]}]})
    except StateOpsError as exc:
        assert str(exc) == "PROTECTED_PATH_FORBIDDEN"
    else:
        raise AssertionError("expected protected path rejection")


def test_verification_operations_compile():
    src = compile_state_ops({
        "ops": [
            {"type": "ASSERT_PATH_EXISTS", "path": "/home/oai/share/a.txt"},
            {"type": "ASSERT_TEXT_EQUALS", "path": "/home/oai/share/a.txt", "text": "alpha"},
            {"type": "SHA256_FILE", "path": "/home/oai/share/a.txt"},
            {"type": "READ_TEXT", "path": "/home/oai/share/a.txt", "max_chars": 100},
        ]
    })
    assert "ASSERT_PATH_EXISTS:PASS:/home/oai/share/a.txt" in src
    assert "ASSERT_TEXT_EQUALS:PASS:/home/oai/share/a.txt" in src
    assert "hashlib.sha256" in src
    assert "read_text" in src


def test_git_removed_from_cli_allowlist():
    try:
        compile_state_ops({"ops": [{"type": "RUN_CLI", "argv": ["git", "status"]}]})
    except StateOpsError as exc:
        assert str(exc).startswith("RUN_CLI_EXECUTABLE_NOT_ALLOWED")
    else:
        raise AssertionError("expected git rejection")


def test_script_capable_application_clis_removed():
    for exe in ("blender", "freecadcmd", "FreeCADCmd", "tar", "unzip", "zip"):
        try:
            compile_state_ops({"ops": [{"type": "RUN_CLI", "argv": [exe, "--help"]}]})
        except StateOpsError as exc:
            assert str(exc).startswith("RUN_CLI_EXECUTABLE_NOT_ALLOWED")
        else:
            raise AssertionError("expected script-capable CLI rejection")


def test_pandoc_filter_escape_hatches_rejected():
    for argv in (
        ["pandoc", "/home/oai/share/a.md", "--filter", "/home/oai/share/filter"],
        ["pandoc", "/home/oai/share/a.md", "--lua-filter=/home/oai/share/f.lua"],
        ["pandoc", "/home/oai/share/a.md", "-F", "/home/oai/share/filter"],
        ["pandoc", "/home/oai/share/a.md", "-L", "/home/oai/share/f.lua"],
    ):
        try:
            compile_state_ops({"ops": [{"type": "RUN_CLI", "argv": argv}]})
        except StateOpsError as exc:
            assert str(exc).startswith("RUN_CLI_ARGUMENT_NOT_ALLOWED:pandoc:")
        else:
            raise AssertionError("expected pandoc filter rejection")


def test_libreoffice_remote_accept_rejected():
    for exe in ("libreoffice", "soffice"):
        try:
            compile_state_ops({"ops": [{"type": "RUN_CLI", "argv": [exe, "--accept=socket,host=0.0.0.0,port=2002;urp;"]}]})
        except StateOpsError as exc:
            assert str(exc).startswith("RUN_CLI_ARGUMENT_NOT_ALLOWED:" + exe)
        else:
            raise AssertionError("expected office accept rejection")


def test_model_schema_aliases_normalize_without_widening_surface():
    src = compile_state_ops({
        "ops": [
            {"op": "MKDIR", "path": "/home/oai/share/x"},
            {"op": "WRITE_TEXT", "path": "/home/oai/share/x/a.txt", "text": "hello"},
            {
                "op": "RUN_CLI",
                "args": ["pandoc", "/home/oai/share/input.md", "-o", "/home/oai/share/output.pdf"],
            },
        ]
    })
    assert "mkdir" in src
    assert "write_text('hello'" in src
    assert "subprocess.run(['pandoc'" in src


def test_state_op_alias_conflicts_fail_closed():
    try:
        compile_state_ops({
            "ops": [{"type": "DELETE", "op": "READ_TEXT", "path": "/home/oai/share/a.txt"}]
        })
    except StateOpsError as exc:
        assert str(exc) == "OP_TYPE_ALIAS_CONFLICT"
    else:
        raise AssertionError("expected alias conflict")


def test_run_cli_argument_alias_conflicts_fail_closed():
    try:
        compile_state_ops({
            "ops": [{
                "type": "RUN_CLI",
                "argv": ["pandoc", "a"],
                "args": ["pandoc", "b"],
            }]
        })
    except StateOpsError as exc:
        assert str(exc) == "RUN_CLI_ARGV_ALIAS_CONFLICT"
    else:
        raise AssertionError("expected argv alias conflict")


def _execute_compiled(payload):
    source = compile_state_ops(payload)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        exec(source, {})
    return stream.getvalue()


def test_write_text_emits_postcondition_receipt(tmp_path):
    target = tmp_path / "receipt.txt"
    out = _execute_compiled({
        "ops": [{"type": "WRITE_TEXT", "path": str(target), "text": "alpha"}]
    })
    digest = hashlib.sha256(b"alpha").hexdigest()
    assert target.read_text(encoding="utf-8") == "alpha"
    assert "WRITE_TEXT:PASS:" + str(target) in out
    assert ":chars=5:bytes=5:sha256=" + digest in out


def test_mutation_then_assert_exposes_causal_progress(tmp_path):
    target = tmp_path / "verified.txt"
    out = _execute_compiled({
        "ops": [
            {"type": "WRITE_TEXT", "path": str(target), "text": "alpha"},
            {"type": "ASSERT_TEXT_EQUALS", "path": str(target), "text": "alpha"},
        ]
    })
    assert "WRITE_TEXT:PASS:" + str(target) in out
    assert "ASSERT_TEXT_EQUALS:PASS:" + str(target) in out


def test_mutating_ops_compile_explicit_receipts():
    source = compile_state_ops({
        "ops": [
            {"type": "MKDIR", "path": "/home/oai/share/x"},
            {"type": "DELETE", "path": "/home/oai/share/y"},
            {"type": "RUN_CLI", "argv": ["ffprobe", "-version"]},
        ]
    })
    assert "MKDIR:PASS:/home/oai/share/x" in source
    assert "DELETE:PASS:/home/oai/share/y" in source
    assert "RUN_CLI:PASS:ffprobe:returncode=" in source


def test_list_dir_emits_bounded_structured_receipt(tmp_path):
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    out = _execute_compiled({
        "ops": [{"type": "LIST_DIR", "path": str(tmp_path), "max_entries": 10}]
    })
    assert "LIST_DIR:PASS:" + str(tmp_path) + ":" in out
    assert '"name":"a.txt"' in out
    assert '"name":"b.txt"' in out


def test_text_replace_exact_and_receipted(tmp_path):
    target = tmp_path / "a.txt"
    target.write_text("alpha beta alpha", encoding="utf-8")
    out = _execute_compiled({
        "ops": [{
            "type": "TEXT_REPLACE",
            "path": str(target),
            "old": "alpha",
            "new": "omega",
            "replace_all": False,
        }]
    })
    assert target.read_text(encoding="utf-8") == "omega beta alpha"
    assert "TEXT_REPLACE:PASS:" + str(target) in out


def test_text_replace_missing_old_fails_at_execution(tmp_path):
    target = tmp_path / "a.txt"
    target.write_text("alpha", encoding="utf-8")
    source = compile_state_ops({
        "ops": [{"type": "TEXT_REPLACE", "path": str(target), "old": "missing", "new": "x"}]
    })
    try:
        exec(source, {})
    except AssertionError as exc:
        assert "TEXT_REPLACE_OLD_NOT_FOUND" in str(exc)
    else:
        raise AssertionError("expected exact old-text guard")


def test_list_dir_protected_path_rejected():
    try:
        compile_state_ops({"ops": [{"type": "LIST_DIR", "path": "/evaluation_examples"}]})
    except StateOpsError as exc:
        assert str(exc) == "PROTECTED_PATH_FORBIDDEN"
    else:
        raise AssertionError("expected protected path rejection")
