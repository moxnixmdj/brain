from canonical.runtime.osworld_v21_state_ops_v1 import StateOpsError, compile_state_ops


def test_compile_file_ops_and_allowlisted_cli():
    src = compile_state_ops({
        "ops": [
            {"type": "MKDIR", "path": "/home/oai/share/x"},
            {"type": "WRITE_TEXT", "path": "/home/oai/share/x/a.txt", "text": "hello"},
            {"type": "RUN_CLI", "argv": ["ffprobe", "-version"], "timeout_s": 5},
        ]
    })
    assert "pathlib.Path('/home/oai/share/x').mkdir" in src
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
        compile_state_ops({"ops": [{"type": "RUN_CLI", "argv": ["unzip", "/benchmark_releases/x.zip"]}]})
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
