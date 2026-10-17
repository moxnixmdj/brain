"""The declared runner. Cannot work: pytest is not installed."""
import pytest, pathlib, subprocess
r = subprocess.run(["pytest", "-q"], capture_output=True, text=True)
pathlib.Path("out/report.txt").write_text(r.stdout + r.stderr)
