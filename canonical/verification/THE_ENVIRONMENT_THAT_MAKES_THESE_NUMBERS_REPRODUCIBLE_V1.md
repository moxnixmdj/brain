# The environment that makes these numbers reproducible

The sandbox is not snapshotted outside this repository, so `/home/user/repos` and the
virtualenvs vanish between sessions. That is not a detail: the first thing the next session
must do is rebuild them, because **8 verified rows were reported last turn and I could only
confirm 3 of 4 before rebuilding.**

```sh
mkdir -p /home/user/repos && cd /home/user/repos
for r in attrs click packaging more-itertools jinja werkzeug urllib3 httpx pluggy starlette tqdm; do
  case $r in
    attrs) u=python-attrs/attrs;; click) u=pallets/click;; packaging) u=pypa/packaging;;
    more-itertools) u=more-itertools/more-itertools;; jinja) u=pallets/jinja;;
    werkzeug) u=pallets/werkzeug;; urllib3) u=urllib3/urllib3;; httpx) u=encode/httpx;;
    pluggy) u=pytest-dev/pluggy;; starlette) u=encode/starlette;; tqdm) u=tqdm/tqdm;;
  esac
  git clone -q --filter=blob:none "https://github.com/$u.git" "$r"
done

python3 -m venv /home/user/venv && python3 -m venv /home/user/venv8
for py in venv venv8; do
  /home/user/$py/bin/pip install -q pytest hypothesis pytest-asyncio "pytest-asyncio<0.24" \
    pytest-timeout ephemeral_port_reserve trustme pytest-xprocess uvicorn tornado trio \
    sniffio certifi brotli chardet httpcore h11 anyio idna
done
```

## The pin that matters, and why

`pytest-asyncio>=0.24` emits a `PytestDeprecationWarning` about
`asyncio_default_fixture_loop_scope`. Several of these repositories set
`filterwarnings = ["error"]`, which turns that warning into an INTERNALERROR and the whole
suite refuses to run.

Measured this session: with `pytest-asyncio 1.5.0`, `click 1b0e19f5` reported
`THE_NAMED_TEST_DID_NOT_FAIL_IN_THIS_SESSION` — the row looked like a miss. With
`pytest-asyncio 0.23.8` it verifies. **The difference was an unpinned dependency, not the
tool.**

So the pin is part of the experiment, not housekeeping. A repair benchmark whose harness can
silently turn every row into a miss, and whose misses are then reported as the tool's
limitations, is measuring the wrong thing.

## The rule this file exists to enforce

Any number in `canonical/verification/` is a claim about *this* environment. If the
environment is rebuilt and the number does not reproduce, the number was never a fact about
the tool — it was a fact about a machine that no longer exists. Re-run before quoting; the
regression gate in `THE_REGRESSION_GATE_RECEIPT_*` is the artifact that proves it was re-run.
