#!/usr/bin/env python3
"""Deterministic bounded test-guided Python patch search.

Candidate-only search over one repository-local Python source file. The runtime:
- requires an isolated writable workspace,
- records exact source/test bytes,
- requires the baseline test command to fail,
- enumerates one-node AST mutations plus literal substitutions mined from tests,
- executes the test command for each candidate,
- restores original source bytes after every trial,
- replays the winning candidate twice before emitting a unified diff,
- never leaves the source modified.

No model calls, network calls, package installation, or canonical source writes.
"""
from __future__ import annotations
import ast, difflib, hashlib, importlib.util, json, os, pathlib, selectors, signal, stat, subprocess, sys, tempfile, time
from typing import Any, Iterable, Mapping

SCHEMA="PROJECT_BRAIN_PYTHON_TEST_GUIDED_PATCH_SEARCH_V1"

class PatchSearchError(RuntimeError): pass

# Match the existing namespace broker's bounded aggregate-payload policy.
MAX_TEST_OUTPUT_BYTES = 8_000_000

def _safe_file(root: pathlib.Path, raw: Any, *, suffix: str|None=None) -> pathlib.Path:
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents or not p.is_file() or p.is_symlink():
        raise PatchSearchError("PATH_INVALID:"+str(raw))
    if suffix and p.suffix!=suffix:
        raise PatchSearchError("PATH_SUFFIX_INVALID:"+str(raw))
    return p

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _run_tests(root: pathlib.Path, argv: list[str], timeout_s: int,
               extra_env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Run noninteractive test argv with bounded cleanup and report the outcome.

    POSIX commands get an owned session; ordinary descendants are terminated on
    completion, timeout or interruption. Escaped sessions and supervisor SIGKILL
    require stronger isolation. Other platforms retain direct-process cleanup.
    Pipe draining is bounded separately, and incomplete diagnostics are explicit.
    POSIX retained stdout+stderr bytes have a shared cap; overflow raises a named
    failure after cleanup, never a truncated success. Non-POSIX capture is unchanged.

    ``extra_env`` is merged over the inherited environment. It exists because the bound executor
    calls every adapter with the REPOSITORY ROOT as ``root``, and the subprocess inherits that as
    its working directory. A test that imports the module under repair - which is how ordinary
    Python test suites are written - then dies with ModuleNotFoundError instead of reaching its
    assertion. Measured: for ``def add(a, b): return a - b`` with ``assertEqual(add(2, 3), 5)``,
    cwd at the repository root gives ``errors=1`` (No module named 'calc') and cwd at the source
    directory gives ``failures=1`` (-1 != 5). Both score 1, so no edit to the source can ever
    strictly improve the metric and the repair loop reports OPEN__NO_STRICTLY_IMPROVING_CANDIDATE
    for every bug. The fix is to put the source directory on PYTHONPATH, which makes the module
    importable without changing the working directory the caller chose.
    """
    if not argv or any(not isinstance(x,str) or not x for x in argv):
        raise PatchSearchError("TEST_ARGV_INVALID")
    exe=pathlib.Path(argv[0]).name.lower()
    allowed={pathlib.Path(sys.executable).name.lower(),"python","python3","py"}
    if exe not in allowed:
        raise PatchSearchError("TEST_EXECUTABLE_NOT_PYTHON")
    started=time.monotonic()
    env=None if not extra_env else {**os.environ,**{k:str(v) for k,v in extra_env.items()}}
    grouped = os.name == 'posix'
    # Reuse zero_ambient_namespace_launcher_v1's owned-session/killpg pattern.
    # This controls ordinary descendants, NOT setsid escapes or hostile code.
    # POSIX pipes are drained incrementally before decoding, with an aggregate
    # budget, using the standard library rather than another process manager.
    capture = ({'bufsize': 0} if grouped else
               {'text': True, 'encoding': 'utf-8', 'errors': 'replace'})
    proc=subprocess.Popen(argv,cwd=root,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,
                          env=env,start_new_session=grouped,**capture)
    timed_out=False
    output_incomplete=False
    stdout=stderr=''

    def stop_owned():
        try:
            if grouped:
                os.killpg(proc.pid,signal.SIGKILL)
            elif proc.poll() is None:
                proc.kill()
        except ProcessLookupError:
            pass

    try:
        if grouped:
            buffers = {'stdout': bytearray(), 'stderr': bytearray()}
            total = 0
            deadline = started + timeout_s
            drain_deadline = None
            with selectors.DefaultSelector() as selector:
                for name, pipe in (('stdout', proc.stdout), ('stderr', proc.stderr)):
                    os.set_blocking(pipe.fileno(), False)
                    selector.register(pipe.fileno(), selectors.EVENT_READ, name)
                while selector.get_map() or proc.poll() is None:
                    now = time.monotonic()
                    if drain_deadline is None:
                        if proc.poll() is not None:
                            # Parent completion, not EOF from all descendants,
                            # ends the test. Clean inherited-pipe holders now.
                            stop_owned()
                            drain_deadline = now + 1
                        elif now >= deadline:
                            timed_out = True
                            stop_owned()
                            drain_deadline = now + 1
                    elif now >= drain_deadline:
                        output_incomplete = bool(selector.get_map()) or proc.poll() is None
                        break
                    remaining = max(0, (drain_deadline or deadline) - now)
                    if not selector.get_map():
                        try:
                            proc.wait(timeout=remaining)
                        except subprocess.TimeoutExpired:
                            pass
                        continue
                    for key, _ in selector.select(timeout=min(.05, remaining)):
                        try:
                            chunk = os.read(key.fd, 65536)
                        except BlockingIOError:
                            continue
                        if not chunk:
                            selector.unregister(key.fd)
                            continue
                        total += len(chunk)
                        if total > MAX_TEST_OUTPUT_BYTES:
                            # Never turn truncated output into a passing test.
                            # The enclosing finally still owns process cleanup.
                            raise PatchSearchError('TEST_OUTPUT_LIMIT_EXCEEDED')
                        buffers[key.data].extend(chunk)
            stdout, stderr = bytes(buffers['stdout']), bytes(buffers['stderr'])
        else:
            try:
                stdout,stderr=proc.communicate(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out=True
                stop_owned()
                try:
                    stdout,stderr=proc.communicate(timeout=1)
                except subprocess.TimeoutExpired as exc:
                    # A detached descendant may retain a pipe. Do not turn the
                    # timeout into an unbounded drain; retain partial diagnostics.
                    output_incomplete=True
                    stdout=exc.stdout or ''
                    stderr=exc.stderr or ''
    finally:
        # Also clean silent background children after success/failure and when
        # the caller interrupts us. SIGKILL of this supervisor cannot run finally.
        stop_owned()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            output_incomplete=True
        for pipe in (proc.stdout,proc.stderr):
            if pipe is not None:
                pipe.close()
    return {
        'returncode':None if timed_out else proc.returncode,
        'stdout':(stdout.decode('utf-8','replace') if isinstance(stdout,bytes) else stdout or '').replace('\r\n','\n').replace('\r','\n'),
        'stderr':(stderr.decode('utf-8','replace') if isinstance(stderr,bytes) else stderr or '').replace('\r\n','\n').replace('\r','\n'),
        'elapsed_s':round(time.monotonic()-started,6),
        'timed_out':timed_out,
        'process_cleanup_scope':'POSIX_PROCESS_GROUP' if grouped else 'DIRECT_PROCESS_ONLY',
        'output_incomplete':output_incomplete,
        'output_capture_scope':'BOUNDED_POSIX_PIPES' if grouped else 'UNBOUNDED_NON_POSIX_COMMUNICATE',
        'output_limit_bytes':MAX_TEST_OUTPUT_BYTES if grouped else None,
        # Preserve raw accounting before UTF-8 replacement/newline normalization.
        'captured_output_bytes':total if grouped else None,
    }


def _run_trace(root: pathlib.Path, argv: list[str], timeout_s: int,
               extra_env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Read a trace result separately from suite-controlled stdout/stderr.

    The wrapper receives an owned temporary result path as its last argument.
    Reuse _run_tests for all process supervision. A bounded regular-file read
    prevents transport confusion and unbounded result retention; it is NOT an
    authentication boundary against code executing inside that same wrapper.
    """
    with tempfile.TemporaryDirectory(prefix='brain_trace_result_') as scratch:
        path = pathlib.Path(scratch) / 'result.json'
        run = _run_tests(root, [*argv, str(path)], timeout_s, extra_env)
        if run['timed_out']:
            raise PatchSearchError('TEST_TIMEOUT')
        # POSIX diagnostics and structured result share the existing raw budget.
        # Non-POSIX diagnostics retain their explicitly unbounded legacy scope;
        # the separate artifact read is nevertheless bounded on every platform.
        remaining = MAX_TEST_OUTPUT_BYTES - (run['captured_output_bytes'] or 0)
        try:
            flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0)
            if path.is_symlink():
                raise PatchSearchError('TRACE_OUTPUT_INVALID')
            fd = os.open(path, flags)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode):
                    raise PatchSearchError('TRACE_OUTPUT_INVALID')
                if info.st_size > remaining:
                    raise PatchSearchError('TEST_OUTPUT_LIMIT_EXCEEDED')
                # Keep descriptor ownership explicit even if fdopen rejects it.
                with os.fdopen(fd, 'rb', closefd=False) as stream:
                    payload = stream.read(remaining + 1)
            finally:
                os.close(fd)
        except FileNotFoundError as exc:
            raise PatchSearchError('TRACE_OUTPUT_MISSING') from exc
        except OSError as exc:
            raise PatchSearchError('TRACE_OUTPUT_INVALID') from exc
        if len(payload) > remaining:
            raise PatchSearchError('TEST_OUTPUT_LIMIT_EXCEEDED')
        try:
            result = json.loads(payload.decode('utf-8'))
        except (UnicodeError, ValueError, RecursionError) as exc:
            raise PatchSearchError('TRACE_OUTPUT_INVALID') from exc
        if (not isinstance(result, dict) or type(result.get('pass')) is not bool
                or not isinstance(result.get('events'), list)
                or not isinstance(result.get('traceback'), list)
                or type(result.get('event_count')) is not int
                or result['event_count'] < 0):
            raise PatchSearchError('TRACE_OUTPUT_INVALID')
        result['returncode'] = run['returncode']
        return result

def _test_literals(paths: Iterable[pathlib.Path]) -> tuple[list[Any], list[str]]:
    nums=set()
    strings=set()
    for path in paths:
        tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant):
                value=node.value
                if isinstance(value,bool) or value is None:
                    continue
                if isinstance(value,(int,float)) and not isinstance(value,bool):
                    if isinstance(value,float) and not (value==value and abs(value)!=float("inf")):
                        continue
                    nums.add(value)
                elif isinstance(value,str) and 0 < len(value) <= 120:
                    strings.add(value)
    return sorted(nums,key=lambda x:(float(x),repr(x))), sorted(strings)

_COMPARE_SWAPS={
    ast.Eq:ast.NotEq, ast.NotEq:ast.Eq,
    ast.Lt:ast.LtE, ast.LtE:ast.Lt,
    ast.Gt:ast.GtE, ast.GtE:ast.Gt,
    ast.Is:ast.IsNot, ast.IsNot:ast.Is,
    ast.In:ast.NotIn, ast.NotIn:ast.In,
}
_BINOP_SWAPS={
    ast.Add:[ast.Sub],
    ast.Sub:[ast.Add],
    ast.Mult:[ast.FloorDiv,ast.Div],
    ast.FloorDiv:[ast.Mult,ast.Div],
    ast.Div:[ast.Mult,ast.FloorDiv],
    ast.Mod:[ast.FloorDiv],
}
_BOOLOP_SWAPS={ast.And:ast.Or, ast.Or:ast.And}

def _descriptor(node: ast.AST, kind: str, detail: str) -> dict[str, Any]:
    return {
        "kind":kind,
        "detail":detail,
        "lineno":getattr(node,"lineno",None),
        "col_offset":getattr(node,"col_offset",None),
        "end_lineno":getattr(node,"end_lineno",None),
        "end_col_offset":getattr(node,"end_col_offset",None),
    }

def _locations(tree: ast.AST) -> list[ast.AST]:
    nodes=[n for n in ast.walk(tree) if hasattr(n,"lineno")]
    nodes.sort(key=lambda n:(getattr(n,"lineno",10**9),getattr(n,"col_offset",10**9),type(n).__name__))
    return nodes

def _node_key(node: ast.AST) -> tuple:
    return (
        type(node).__name__,
        getattr(node,"lineno",None),getattr(node,"col_offset",None),
        getattr(node,"end_lineno",None),getattr(node,"end_col_offset",None),
    )

def _candidate_specs(tree: ast.AST, numeric_literals: list[Any], string_literals: list[str]):
    seen=set()
    for node in _locations(tree):
        key=_node_key(node)
        if isinstance(node,ast.Compare) and len(node.ops)==1:
            typ=type(node.ops[0])
            newtyp=_COMPARE_SWAPS.get(typ)
            if newtyp:
                sig=(key,"compare",newtyp.__name__)
                if sig not in seen:
                    seen.add(sig)
                    yield key, _descriptor(node,"COMPARE_SWAP",typ.__name__+"->"+newtyp.__name__), (
                        lambda n,newtyp=newtyp: ast.Compare(left=n.left,ops=[newtyp()],comparators=n.comparators)
                    )
        if isinstance(node,ast.BoolOp):
            newtyp=_BOOLOP_SWAPS.get(type(node.op))
            if newtyp:
                sig=(key,"bool",newtyp.__name__)
                if sig not in seen:
                    seen.add(sig)
                    yield key,_descriptor(node,"BOOL_SWAP",type(node.op).__name__+"->"+newtyp.__name__),(
                        lambda n,newtyp=newtyp: ast.BoolOp(op=newtyp(),values=n.values)
                    )
        if isinstance(node,ast.BinOp):
            for newtyp in _BINOP_SWAPS.get(type(node.op),[]):
                sig=(key,"bin",newtyp.__name__)
                if sig in seen: continue
                seen.add(sig)
                yield key,_descriptor(node,"BINOP_SWAP",type(node.op).__name__+"->"+newtyp.__name__),(
                    lambda n,newtyp=newtyp: ast.BinOp(left=n.left,op=newtyp(),right=n.right)
                )
        if isinstance(node,ast.Constant):
            value=node.value
            replacements=[]
            if isinstance(value,bool):
                replacements=[not value]
            elif isinstance(value,(int,float)) and not isinstance(value,bool):
                base=[0,1,-1]
                if isinstance(value,int):
                    base += [value-1,value+1]
                replacements=base+numeric_literals
            elif isinstance(value,str):
                replacements=string_literals
            uniq=[]
            for rep in replacements:
                if rep==value or type(rep) is not type(value) and isinstance(value,bool):
                    continue
                if isinstance(value,int) and isinstance(rep,float) and not float(rep).is_integer():
                    continue
                if isinstance(value,int) and isinstance(rep,float):
                    rep=int(rep)
                if rep not in uniq:
                    uniq.append(rep)
            for rep in uniq[:64]:
                sig=(key,"const",repr(rep))
                if sig in seen: continue
                seen.add(sig)
                yield key,_descriptor(node,"CONSTANT_REPLACE",repr(value)+"->"+repr(rep)),(
                    lambda n,rep=rep: ast.Constant(value=rep)
                )
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.Not):
            sig=(key,"dropnot")
            if sig not in seen:
                seen.add(sig)
                yield key,_descriptor(node,"DROP_NOT","not X -> X"),(lambda n:n.operand)
        if isinstance(node,(ast.If,ast.While,ast.Assert)) and hasattr(node,"test"):
            test=node.test
            tkey=_node_key(test)
            sig=(tkey,"addnot")
            if sig not in seen and not isinstance(test,ast.UnaryOp):
                seen.add(sig)
                yield tkey,_descriptor(test,"ADD_NOT","condition -> not condition"),(
                    lambda n: ast.UnaryOp(op=ast.Not(),operand=n)
                )

"""Child-side suite execution shared by repair, measurement and tracing.

Plain unittest suites keep their fast stdlib path. Pytest-style suites are run
by the real framework when available; fixtures, parametrization, configuration
and test classes are not reimplemented or silently skipped. When pytest is
needed but unavailable the run fails closed. Simple bare functions still work
without pytest. The first real failure retains its traceback for the localizer,
and the pytest reporter emits the same counted summary consumed by existing
repair and audit code. This is test execution, not an OS security sandbox.
"""
SUITE_RUNNER = r'''import ast,importlib.util,inspect,os,pathlib,runpy,sys,time,tokenize,unittest

def _brain_suite_shape(target):
 with tokenize.open(str(target)) as source:tree=ast.parse(source.read(),filename=str(target))
 prefer_pytest=False
 require_pytest=bool(os.environ.get("PYTEST_ADDOPTS") or os.environ.get("PYTEST_PLUGINS"))
 script=False
 for parent in (target.parent,*target.parent.parents):
  if (parent/"conftest.py").is_file() or (parent/"pytest.ini").is_file() or (parent/".pytest.ini").is_file():
   require_pytest=True
  for name,markers in (("pyproject.toml",("[tool.pytest",)),("setup.cfg",("[tool:pytest]",)),("tox.ini",("[pytest]",))):
   config=parent/name
   if config.is_file():
    try: content=config.read_text(encoding="utf-8")
    except (OSError,UnicodeError): require_pytest=True;continue
    if any(marker in content for marker in markers):require_pytest=True
 for node in ast.walk(tree):
  if isinstance(node,ast.Name) and node.id in ("pytest","pytestmark","pytest_plugins"):require_pytest=True
  if isinstance(node,ast.Import) and any(a.name.split(".")[0]=="pytest" for a in node.names):require_pytest=True
  if isinstance(node,ast.ImportFrom) and (node.module or "").split(".")[0]=="pytest":require_pytest=True
 unittest_modules=set();unittest_cases=set();case_names={"TestCase","IsolatedAsyncioTestCase"}
 for node in tree.body:
  if isinstance(node,ast.Import):
   unittest_modules.update(a.asname or a.name for a in node.names if a.name=="unittest")
  elif isinstance(node,ast.ImportFrom) and node.module in ("unittest","unittest.case","unittest.async_case"):
   for alias in node.names:
    if alias.name=="*":unittest_cases.update(case_names)
    elif alias.name in case_names:unittest_cases.add(alias.asname or alias.name)
 for node in tree.body:
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith("test_"):
   prefer_pytest=True
   args=node.args
   if (isinstance(node,ast.AsyncFunctionDef) or node.decorator_list or args.posonlyargs or args.args
       or args.kwonlyargs or args.vararg or args.kwarg or any(isinstance(x,(ast.Yield,ast.YieldFrom)) for x in ast.walk(node))):
    require_pytest=True
  elif isinstance(node,ast.ClassDef):
   unittest_base=any((isinstance(b,ast.Name) and b.id in unittest_cases) or
                     (isinstance(b,ast.Attribute) and b.attr in case_names and
                      isinstance(b.value,ast.Name) and b.value.id in unittest_modules) for b in node.bases)
   if unittest_base:unittest_cases.add(node.name)
   elif node.name.startswith("Test"):require_pytest=True
  elif isinstance(node,ast.Assert):script=True
  elif isinstance(node,ast.If):
   names={x.id for x in ast.walk(node.test) if isinstance(x,ast.Name)}
   values={x.value for x in ast.walk(node.test) if isinstance(x,ast.Constant) and isinstance(x.value,str)}
   if "__name__" in names and "__main__" in values:script=True
 return prefer_pytest,require_pytest,script

def _brain_project_file(frame,root,cache):
 if frame is None:return None
 filename=frame.f_code.co_filename
 if filename.startswith("<") and filename.endswith(">"):return None
 try:cwd=os.getcwd() if not os.path.isabs(filename) else None
 except OSError:return None
 key=(filename,cwd)
 if key not in cache:
  try:
   path=pathlib.Path(filename).resolve()
   libraries_key=("runtime_site_libraries",root,None)
   if libraries_key not in cache:
    # Discovery's directory-name blacklist also excludes build/env source.
    # Trace only excludes actual interpreter installation roots, discovered by
    # Python itself. Cache once; keep an explicitly selected library root visible.
    import site
    locations=list(site.getsitepackages())
    if site.ENABLE_USER_SITE:
     user=site.getusersitepackages()
     locations.extend([user] if isinstance(user,str) else user or [])
    libraries=[]
    for location in locations:
     try:library=pathlib.Path(location).resolve()
     except (OSError,ValueError):continue
     if root in library.parents:libraries.append(library)
    cache[libraries_key]=tuple(libraries)
   library_frame=any(library==path or library in path.parents for library in cache[libraries_key])
   cache[key]=path if not library_frame and path.is_file() and root in path.parents and path.suffix==".py" else None
  except (OSError,ValueError):cache[key]=None
 return cache[key]

def _brain_bare_functions(mod):
 out=[]
 for name in sorted(vars(mod)):
  if not name.startswith("test_"):continue
  fn=vars(mod)[name]
  if not callable(fn):continue
  try:params=list(inspect.signature(fn).parameters.values())
  except (TypeError,ValueError):raise RuntimeError("UNSUPPORTED_TEST_SIGNATURE:"+name)
  needs=[p for p in params if p.default is p.empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD,p.KEYWORD_ONLY)]
  if needs:raise RuntimeError("PYTEST_REQUIRED:"+name)
  out.append((name,fn))
 return out

def _brain_reraise_failure(exc,tb):
 # Re-raising SystemExit(0) would turn a failed test or aborted collection
 # into a successful process while still printing a failure summary.
 if isinstance(exc,SystemExit) and exc.code in (None,0):
  raise AssertionError("TEST_RAISED_SYSTEM_EXIT_ZERO").with_traceback(tb) from exc
 raise exc.with_traceback(tb)

def _brain_run_stdlib(target,script):
 directory=str(target.resolve().parent)
 if directory not in sys.path:sys.path.insert(0,directory)
 spec=importlib.util.spec_from_file_location("__brain_suite__",str(target))
 mod=importlib.util.module_from_spec(spec);sys.modules["__brain_suite__"]=mod
 spec.loader.exec_module(mod)
 suite=unittest.TestLoader().loadTestsFromModule(mod)
 for _,fn in _brain_bare_functions(mod):suite.addTest(unittest.FunctionTestCase(fn))
 if suite.countTestCases()==0:
  if not script:raise RuntimeError("NO_TESTS_COLLECTED:"+str(target))
  # A script is one oracle, not one case per assertion. Reuse unittest's
  # accounting and failure reporting instead of returning without a summary.
  def _script_oracle():
   try:runpy.run_path(str(target),run_name="__main__")
   except SystemExit as exc:
    if exc.code not in (None,0):raise
  suite.addTest(unittest.FunctionTestCase(_script_oracle))
 class _R(unittest.TestResult):
  def __init__(self,*a,**k):unittest.TestResult.__init__(self);self.err=None;self.no_passing=False
  def addFailure(self,test,err):unittest.TestResult.addFailure(self,test,err);self.err=err
  def addError(self,test,err):unittest.TestResult.addError(self,test,err);self.err=err
  def stopTestRun(self):
   unittest.TestResult.stopTestRun(self)
   # Existing consumers understand skipped, not unittest's expected-failure label.
   self.skipped.extend((test,"expected failure") for test,_ in self.expectedFailures)
   self.expectedFailures.clear()
   self.errors.extend((test,"unexpected success") for test in self.unexpectedSuccesses)
   self.unexpectedSuccesses.clear()
   if self.testsRun and self.testsRun==len(self.skipped):
    self.no_passing=True;self.testsRun+=1;self.errors.append((None,"no passing tests executed"))
 res=unittest.TextTestRunner(stream=sys.stderr,resultclass=_R).run(suite)
 if not res.wasSuccessful():
  if res.err:_brain_reraise_failure(res.err[1],res.err[2])
  if res.no_passing:raise RuntimeError("NO_PASSING_TESTS_EXECUTED")
  raise AssertionError("SUITE_FAILED_WITHOUT_EXCEPTION_INFO")

def _brain_run_pytest(targets,shapes):
 import pytest
 class _Report:
  def __init__(self):
   self.nodes=set();self.collected_files=set();self.selected_files=set()
   self.passed=0;self.failed=0;self.errors=0;self.skipped=0;self.exception=None
  def _file(self,item):
   path=getattr(item,"path",None) or getattr(item,"fspath",None)
   return pathlib.Path(str(path)).resolve() if path is not None else None
  def pytest_itemcollected(self,item):
   self.collected_files.add(self._file(item))
  def pytest_collection_finish(self,session):
   self.selected_files.update(self._file(item) for item in session.items)
  @pytest.hookimpl(hookwrapper=True)
  def pytest_runtest_makereport(self,item,call):
   outcome=yield
   report=outcome.get_result()
   if report.failed and call.excinfo and self.exception is None:
    self.exception=(call.excinfo.value,call.excinfo.tb)
  def pytest_runtest_logreport(self,report):
   if report.when=="call":
    self.nodes.add(report.nodeid)
    if report.failed:self.failed+=1
    elif report.skipped:self.skipped+=1
    elif report.passed:self.passed+=1
   elif report.when=="setup" and (report.failed or report.skipped):
    self.nodes.add(report.nodeid)
    if report.failed:self.errors+=1
    else:self.skipped+=1
   elif report.when=="teardown" and report.failed:self.errors+=1
  def pytest_collectreport(self,report):
   if report.failed:self.errors+=1
 report=_Report();started=time.monotonic()
 status=int(pytest.main(["-q","-p","no:cacheprovider"]+[str(t) for t in targets],plugins=[report]))
 if status in (0,5) and not report.errors:
  for target,shape in zip(targets,shapes):
   if target in report.selected_files:continue
   if shape[2] and target not in report.collected_files:
    # Pytest imports a script but does not execute its __main__ guard.
    try:runpy.run_path(str(target),run_name="__main__")
    except BaseException as exc:
     if isinstance(exc,SystemExit) and exc.code in (None,0):report.passed+=1;continue
     report.errors+=1;status=1
     if report.exception is None:report.exception=(exc,exc.__traceback__)
    else:report.passed+=1
   else:
    sys.stderr.write("NO_TESTS_COLLECTED_IN_TARGET:"+str(target)+"\n")
    report.errors+=1;status=1
  if status==5 and report.passed and not report.errors:status=0
 if status==0 and report.passed==0:
  sys.stderr.write("NO_PASSING_TESTS_EXECUTED\n")
  status=1;report.errors+=1
 if status and not (report.failed or report.errors):report.errors+=1
 # Collection, teardown and no-passing-oracle failures can add suite-level
 # errors beyond the number of collected test nodes.
 count=max(len(report.nodes),report.passed+report.failed+report.errors+report.skipped)
 sys.stderr.write("Ran %d test%s in %.3fs\n\n"%(count,"" if count==1 else "s",time.monotonic()-started))
 parts=[]
 if report.failed:parts.append("failures=%d"%report.failed)
 if report.errors:parts.append("errors=%d"%report.errors)
 if report.skipped:parts.append("skipped=%d"%report.skipped)
 sys.stderr.write(("FAILED" if status else "OK")+(" ("+", ".join(parts)+")" if parts else "")+"\n")
 if status:
  if report.exception:
   exc,tb=report.exception
   _brain_reraise_failure(exc,tb)
  raise RuntimeError("PYTEST_EXECUTION_FAILED:"+str(status))

def _brain_run_suites(targets):
 targets=[pathlib.Path(t).resolve() for t in targets]
 if not targets:raise RuntimeError("NO_TESTS_COLLECTED")
 shapes=[_brain_suite_shape(t) for t in targets]
 try:has_pytest=importlib.util.find_spec("pytest") is not None
 except (ImportError,ValueError):has_pytest=False
 if any(shape[1] for shape in shapes) and not has_pytest:
  raise RuntimeError("PYTEST_REQUIRED:"+", ".join(str(t) for t,s in zip(targets,shapes) if s[1]))
 if has_pytest and any(shape[0] or shape[1] for shape in shapes):
  _brain_run_pytest(targets,shapes);return
 errors=[]
 for target,shape in zip(targets,shapes):
  try:_brain_run_stdlib(target,shape[2])
  except BaseException as exc:errors.append(exc)
 if errors:_brain_reraise_failure(errors[0],errors[0].__traceback__)

def _brain_run_suite(target):
 _brain_run_suites([target])
'''


SUITE_ENTRY = (
    "import pathlib,sys\n"
    "_brain_run_suites([pathlib.Path(_t).resolve() for _t in sys.argv[1:]])\n"
)


def argv_names_a_target(argv: Any) -> bool:
    """True when a command line actually names a test suite to run.

    The runner ``suite_argv`` generates reads its targets from ``sys.argv[1:]``,
    so ``[executable, "-c", script]`` names no suite. An older runner returned
    zero for that command, causing a false BASELINE_ALREADY_PASSES result. The
    runner now fails closed, and this check also lets callers derive the actual
    discovered targets instead of retaining an empty command.

    Targets follow the ``-c`` script when there is one; otherwise any non-flag
    element after the executable is treated as a target.
    """
    items = [str(x) for x in (argv or [])]
    if not items:
        return False
    if "-c" in items:
        return len(items) > items.index("-c") + 2
    return any(not item.startswith("-") for item in items[1:])


def argv_or_derived(supplied: Any, executable: Any, *targets: Any) -> list[str]:
    """The caller's command line when it names a suite, otherwise the derived one.

    The derivation is not a fallback for a missing value only.  An argv that is
    present but empty of targets is worse than a missing one, because it looks
    bound: the missing value takes the derived path, while the empty one used to
    win and silently run nothing.  Both must derive.
    """
    if argv_names_a_target(supplied):
        return [str(x) for x in supplied]
    return suite_argv(executable, *targets)


def suite_argv(executable: Any, *targets: Any) -> list[str]:
    """Run named suites with the applicable framework and a counted result.

    Unittest suites and simple bare functions retain a stdlib-only path. When
    installed, pytest collects pytest-style suites together, including fixtures,
    parametrization and project configuration. Without pytest, suites requiring
    it fail explicitly instead of skipping cases and reporting success. A file
    without tests or an explicit script oracle and a command with no targets
    fail closed. Failures retain their tracebacks for localization.
    """
    return [str(executable), "-c", SUITE_RUNNER + SUITE_ENTRY] + [str(x) for x in targets]


def _source_env(*paths: Any) -> dict[str, str]:
    """PYTHONPATH extended with the directories holding the code under repair.

    A test suite normally imports the module it tests. The bound executor calls every adapter
    with the REPOSITORY ROOT as ``root`` and the subprocess inherits that as its working
    directory, so a sibling ``import calc`` dies with ModuleNotFoundError before any assertion
    runs - and then the baseline and every candidate score identically, so a search that only
    accepts a STRICT improvement reports no candidate for any bug. Adding the source directory to
    PYTHONPATH makes the module importable without changing the working directory the caller
    chose, so no other caller's relative paths change meaning.
    """
    dirs: list[str] = []
    for raw in paths:
        q = pathlib.Path(str(raw))
        d = q if q.is_dir() else q.parent
        if str(d) not in dirs:
            dirs.append(str(d))
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        dirs.append(existing)
    return {"PYTHONPATH": os.pathsep.join(dirs)}


def _byte_offset(lines: list[bytes], lineno: int, col: int) -> int:
    return sum(len(x) for x in lines[:lineno-1]) + col

def _render_candidate(source_text: str, key, replacer) -> str|None:
    tree=ast.parse(source_text)
    target=None
    for node in ast.walk(tree):
        if _node_key(node)==key:
            target=node
            break
    if target is None:
        return None
    if None in (
        getattr(target,"lineno",None),getattr(target,"col_offset",None),
        getattr(target,"end_lineno",None),getattr(target,"end_col_offset",None)
    ):
        return None
    replacement=replacer(target)
    ast.fix_missing_locations(replacement)
    replacement_text=ast.unparse(replacement)
    raw=source_text.encode("utf-8")
    lines=raw.splitlines(keepends=True)
    start=_byte_offset(lines,target.lineno,target.col_offset)
    end=_byte_offset(lines,target.end_lineno,target.end_col_offset)
    candidate=raw[:start]+replacement_text.encode("utf-8")+raw[end:]
    return candidate.decode("utf-8")

def _purge_source_bytecode(source: pathlib.Path) -> None:
    try:
        cache=pathlib.Path(importlib.util.cache_from_source(str(source)))
    except (NotImplementedError, ValueError):
        return
    try:
        cache.unlink()
    except FileNotFoundError:
        pass

def _diff(rel: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(True),after.splitlines(True),
        fromfile="a/"+rel,tofile="b/"+rel
    ))

def run(args: Mapping[str, Any], root: str|os.PathLike[str]) -> dict[str, Any]:
    repo=pathlib.Path(root).resolve()
    if not isinstance(args,Mapping):
        raise PatchSearchError("ARGS_NOT_OBJECT")
    source=_safe_file(repo,args.get("source_path"),suffix=".py")
    tests_raw=[x for x in (args.get("test_paths") or []) if str(x).strip()]
    if not isinstance(tests_raw,list):
        raise PatchSearchError("TEST_PATHS_REQUIRED")
    if not tests_raw:
        # This capability names a single SOURCE file, so the corpus is the tree
        # that file lives in -- the smallest scope in which its tests can be.
        from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import discover_test_paths
        try: tests_raw=discover_test_paths(source.parent)
        except FileNotFoundError: raise PatchSearchError("NO_TEST_FILES_UNDER_SOURCE_ROOT")
    if not tests_raw:
        raise PatchSearchError("TEST_PATHS_REQUIRED")
    tests=[_safe_file(repo,x,suffix=".py") for x in tests_raw]
    argv=args.get("test_argv")
    if argv is None:
        argv=suite_argv(sys.executable,*tests)
    if not isinstance(argv,list):
        raise PatchSearchError("TEST_ARGV_INVALID")
    argv=[str(x) for x in argv]
    timeout_s=max(1,min(int(args.get("timeout_s",60)),300))
    max_candidates=max(1,min(int(args.get("max_candidates",2000)),20000))
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output==repo or repo not in output.parents:
        raise PatchSearchError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    from canonical.runtime.write_authority_v1 import check_report
    check_report(repo, output, [source, *tests])
    original_bytes=source.read_bytes()
    try:
        source_text=original_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchSearchError("SOURCE_NOT_UTF8") from exc
    env=_source_env(source,*tests)
    baseline=_run_tests(repo,argv,timeout_s,env)
    if baseline["returncode"]==0:
        raise PatchSearchError("BASELINE_ALREADY_PASSES")
    if baseline["timed_out"]:
        raise PatchSearchError("BASELINE_TIMEOUT")
    nums,strings=_test_literals(tests)
    tree=ast.parse(source_text,filename=str(source))
    attempts=[]
    winner=None
    tested=0
    try:
        for key,desc,replacer in _candidate_specs(tree,nums,strings):
            if tested>=max_candidates:
                break
            candidate=_render_candidate(source_text,key,replacer)
            if candidate is None or candidate==source_text:
                continue
            tested+=1
            source.write_text(candidate,encoding="utf-8")
            _purge_source_bytecode(source)
            result=_run_tests(repo,argv,timeout_s,env)
            source.write_bytes(original_bytes)
            _purge_source_bytecode(source)
            attempts.append({
                "index":tested,
                "mutation":desc,
                "candidate_sha256":_sha(candidate.encode("utf-8")),
                "returncode":result["returncode"],
                "timed_out":result["timed_out"],
                "elapsed_s":result["elapsed_s"],
            })
            if result["returncode"]==0 and not result["timed_out"]:
                replay=[]
                ok=True
                for _ in range(2):
                    source.write_text(candidate,encoding="utf-8")
                    _purge_source_bytecode(source)
                    rr=_run_tests(repo,argv,timeout_s,env)
                    source.write_bytes(original_bytes)
                    _purge_source_bytecode(source)
                    replay.append({
                        "returncode":rr["returncode"],
                        "timed_out":rr["timed_out"],
                        "elapsed_s":rr["elapsed_s"],
                    })
                    ok=ok and rr["returncode"]==0 and not rr["timed_out"]
                if ok:
                    winner=(candidate,desc,replay)
                    break
    finally:
        source.write_bytes(original_bytes)
        _purge_source_bytecode(source)
    rel=str(source.relative_to(repo)).replace("\\","/")
    result={
        "schema":SCHEMA,
        "status":"PASS__VERIFIED_CANDIDATE_PATCH_FOUND" if winner else "OPEN__NO_VERIFIED_CANDIDATE_IN_BOUNDED_SEARCH",
        "pass":winner is not None,
        "source_path":rel,
        "source_sha256":_sha(original_bytes),
        "test_paths":[str(p.relative_to(repo)).replace("\\","/") for p in tests],
        "test_sha256":{str(p.relative_to(repo)).replace("\\","/"):_sha(p.read_bytes()) for p in tests},
        "baseline_returncode":baseline["returncode"],
        "tested_candidate_count":tested,
        "max_candidates":max_candidates,
        "candidate_generator":"DETERMINISTIC_SINGLE_AST_MUTATION_PLUS_TEST_LITERAL_SUBSTITUTION",
        "model_dependency_count":0,
        "external_capability_provider_count":0,
        "incremental_spend_usd":0,
        "source_restored":source.read_bytes()==original_bytes,
        "attempts":attempts,
        "patches":[],  # candidate patches: the machine-readable promised artifact
        "hard_nonclaims":[
            "NO_UNIVERSAL_PATCH_SEARCH_COMPLETENESS",
            "NO_MULTI_EDIT_COMPLETENESS",
            "NO_NON_PYTHON_SUPPORT",
            "NO_SEMANTIC_CORRECTNESS_BEYOND_BOUND_TEST_ORACLE",
            "NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY",
            "NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"
        ],
    }
    if winner:
        candidate,desc,replay=winner
        patch=_diff(rel,source_text,candidate)
        result.update({
            "winning_mutation":desc,
            "candidate_source_sha256":_sha(candidate.encode("utf-8")),
            "verification_replays":replay,
            "unified_diff":patch,
            "patches":[{
                "source_path":rel,
                "winning_mutation":desc,
                "candidate_source_sha256":_sha(candidate.encode("utf-8")),
                "verification_replays":replay,
                "unified_diff":patch,
            }],
        })
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    result["output_path"]=str(output.relative_to(repo)).replace("\\","/")
    result["output_sha256"]=_sha(raw)
    result["output_verified"]=True
    return result
