"""The external audit only applies a one-file target diff."""
from canonical.tools.diagnose_branch_comparison_v1 import safe_single_file_diff


def test_diff_scope_is_explicit():
    assert safe_single_file_diff('--- a/subject.py\n+++ b/subject.py\n@@ -1 +1 @@\n-a\n+b\n')
    assert not safe_single_file_diff('--- a/subject.py\n+++ b/other.py\n')
    assert not safe_single_file_diff('--- a/subject.py\n+++ b/subject.py\n--- a/test_subject.py\n+++ b/test_subject.py\n')
    assert not safe_single_file_diff('--- a/../subject.py\n+++ b/../subject.py\n')
