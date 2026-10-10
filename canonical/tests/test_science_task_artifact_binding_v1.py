from canonical.runtime.science_task_artifact_binding_v1 import bind


def test_task_toml_artifacts_are_primary_authority():
    task = 'schema_version = "1.3"\nartifacts = ["/root/results/answer.csv"]\n'
    out = bind(
        task_toml=task,
        instruction="Save the results to a file named /tmp/fallback.csv.",
    )
    assert out["pass"] is True, out
    assert out["paths"] == ["/root/results/answer.csv"]
    assert out["source"] == "TASK_TOML_ARTIFACTS"
    assert out["instruction_fallback_used"] is False


def test_common_file_named_output_phrase_is_bound():
    out = bind(
        task_toml='schema_version = "1.3"\n',
        instruction="Save the results to a file named /root/results/output.csv with columns a,b.",
    )
    assert out["pass"] is True, out
    assert out["paths"] == ["/root/results/output.csv"]
    assert out["source"] == "INSTRUCTION_EXPLICIT_OUTPUT_FALLBACK"


def test_plain_input_reference_is_not_misclassified_as_output():
    out = bind(
        task_toml='schema_version = "1.3"\n',
        instruction="Read data from /root/data/input.csv and classify every row.",
    )
    assert out["pass"] is True, out
    assert out["paths"] == []
    assert out["source"] == "NONE"


def test_task_authority_rejects_unsafe_relative_or_parent_paths():
    bad = 'schema_version = "1.3"\nartifacts = ["../results/out.csv"]\n'
    out = bind(task_toml=bad, instruction="Create the result.")
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"


def test_duplicate_task_artifacts_are_deduplicated_without_drift():
    task = (
        'schema_version = "1.3"\n'
        'artifacts = ["/root/results/out.csv", "/root/results/out.csv"]\n'
    )
    out = bind(task_toml=task, instruction="")
    assert out["pass"] is True, out
    assert out["paths"] == ["/root/results/out.csv"]
    assert out["artifact_count"] == 1


if __name__ == "__main__":
    test_task_toml_artifacts_are_primary_authority()
    test_common_file_named_output_phrase_is_bound()
    test_plain_input_reference_is_not_misclassified_as_output()
    test_task_authority_rejects_unsafe_relative_or_parent_paths()
    test_duplicate_task_artifacts_are_deduplicated_without_drift()
    print("PASS__SCIENCE_TASK_ARTIFACT_BINDING_V1")
