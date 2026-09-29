#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, pathlib, shutil, signal, subprocess, sys, time, traceback

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import auto_apt_cli_acquisition
import executor_broker

SPEC=ROOT/"canonical/astra_runtime/missions/XAPIAN_APT_E2E_INTEGRATION_HELDOUT_004.json"
EVID=ROOT/"canonical"/"astra_runtime"/"evidence"
RESULT=EVID/"XAPIAN-APT-E2E-INTEGRATION-HELDOUT-004__RESULT.json"
START=EVID/"XAPIAN-APT-E2E-INTEGRATION-HELDOUT-004__EXECUTION_START.json"
PNG_MAGIC=bytes.fromhex("89504e470d0a1a0a")
WORKER_ENV="PROJECT_BRAIN_XAPIAN_APT_E2E_HELDOUT_004_WORKER"
START_MONOTONIC_NS_ENV="PROJECT_BRAIN_XAPIAN_APT_E2E_HELDOUT_004_START_MONOTONIC_NS"
RESULT_SENTINEL="PROJECT_BRAIN_XAPIAN_APT_E2E_HELDOUT_004_RESULT_B64="
REFERENCE_ACQUISITION=ROOT/"canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__AUTO_APT_CLI_ACQUISITION.json"
EXECUTOR_ATTESTATION_ENV="PROJECT_BRAIN_XAPIAN_APT_E2E_HELDOUT_004_EXECUTOR_ATTESTATION_JSON"


def git_blob_sha(path: pathlib.Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def _write_result_exclusive(payload):
    EVID.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(payload,indent=2,sort_keys=True)+"\n").encode("utf-8")
    try:
        fd=os.open(str(RESULT),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o644)
    except FileExistsError:
        raise SystemExit("TERMINAL_RESULT_ALREADY_EXISTS")
    with os.fdopen(fd,"wb") as fh:
        fh.write(raw)


def terminal_result(payload, rc):
    if os.environ.get(WORKER_ENV)=="1":
        compact=json.dumps(payload,separators=(",",":"),sort_keys=True).encode("utf-8")
        print(RESULT_SENTINEL+base64.b64encode(compact).decode("ascii"),flush=True)
        raise SystemExit(rc)
    _write_result_exclusive(payload)
    print(json.dumps(payload,indent=2,sort_keys=True))
    raise SystemExit(rc)


def _load_fresh_spec():
    spec=json.loads(SPEC.read_text(encoding="utf-8"))
    vid=spec["validation_id"]
    if vid!="XAPIAN-APT-E2E-INTEGRATION-HELDOUT-004":
        raise SystemExit("VALIDATION_ID_MISMATCH")
    freshness=spec.get("freshness") or {}
    if freshness.get("state")!="UNSPENT" or int(freshness.get("execution_count") or 0)!=0:
        raise SystemExit("HELDOUT_NOT_FRESH")
    return spec,vid


def _start_t0():
    raw=os.environ.get(START_MONOTONIC_NS_ENV)
    if raw:
        return int(raw)/1_000_000_000
    return time.monotonic()


def _admit_executor_before_start(spec):
    raw=os.environ.get(EXECUTOR_ATTESTATION_ENV)
    if not raw:
        raise SystemExit("EXECUTOR_ATTESTATION_REQUIRED_BEFORE_START")
    try:
        att=json.loads(raw)
    except Exception as exc:
        raise SystemExit("EXECUTOR_ATTESTATION_INVALID_JSON:"+type(exc).__name__) from exc
    if not isinstance(att,dict):
        raise SystemExit("EXECUTOR_ATTESTATION_OBJECT_REQUIRED")
    if att.get("user_device_used") is not False:
        raise SystemExit("USER_DEVICE_EXECUTOR_FORBIDDEN")
    provider=str(att.get("provider") or "").strip().lower().replace("_"," ").replace("-"," ")
    if provider in {"val","val town","valtown"}:
        raise SystemExit("VAL_TOWN_EXECUTOR_FORBIDDEN")
    evidence=att.get("hard_zero_evidence")
    if not isinstance(evidence,dict):
        raise SystemExit("HARD_ZERO_EVIDENCE_REQUIRED")
    if not str(evidence.get("source_class") or "").strip() or not str(evidence.get("reference") or "").strip():
        raise SystemExit("HARD_ZERO_EVIDENCE_REFERENCE_REQUIRED")
    selected=executor_broker.select_executor(spec,[att])
    normalized=json.dumps(att,separators=(",",":"),sort_keys=True).encode("utf-8")
    return selected,hashlib.sha256(normalized).hexdigest(),evidence


def worker_main():
    spec,vid=_load_fresh_spec()
    if not START.exists():
        raise SystemExit("EXECUTION_START_MISSING")

    t0=_start_t0()
    observed_runtime={}
    try:
        integ=spec["runtime_integrity"]
        for rel,expected in (integ.get("immutable_baseline_blobs") or {}).items():
            actual=git_blob_sha(ROOT/rel)
            observed_runtime[rel]=actual
            if actual!=expected:
                raise RuntimeError("IMMUTABLE_RUNTIME_BLOB_MISMATCH:"+rel+":"+actual)
        if not shutil.which("apt-cache") or not shutil.which("sudo"):
            raise RuntimeError("FAITHFUL_APT_EXECUTION_SURFACE_REQUIRED")
        if not shutil.which("zbarimg"):
            raise RuntimeError("EXTERNAL_QR_ORACLE_MISSING")

        mission_rel=str(SPEC.relative_to(ROOT))
        goal=spec["frozen_goal"]
        dispatch=auto_apt_cli_acquisition.dispatch(
            goal,vid,mission_rel,ROOT,discovery=None
        )
        pending_path=ROOT/dispatch["pending_binding_path"]
        pending=json.loads(pending_path.read_text(encoding="utf-8"))
        supplier=pending.get("selected_supplier") or {}
        if dispatch.get("status")!="ACQUISITION_DISPATCHED":
            raise RuntimeError("DISPATCH_NOT_COMPLETED")
        if supplier.get("discovery_source")!="APT_FULL_METADATA_XAPIAN":
            raise RuntimeError("WRONG_DISCOVERY_SOURCE:"+str(supplier.get("discovery_source")))
        if supplier.get("binding_kind")!="apt":
            raise RuntimeError("WRONG_BINDING_KIND:"+str(supplier.get("binding_kind")))
        if supplier.get("zero_cost_eligible") is not True:
            raise RuntimeError("SUPPLIER_NOT_ZERO_COST_ELIGIBLE")

        reference=json.loads(REFERENCE_ACQUISITION.read_text(encoding="utf-8"))
        reference_supplier=(reference.get("selected_supplier") or {}).get("name")
        current_supplier=supplier.get("name")
        if not reference_supplier or not current_supplier:
            raise RuntimeError("ORTHOGONAL_SUPPLIER_EVIDENCE_MISSING")
        if current_supplier==reference_supplier:
            raise RuntimeError("ORTHOGONAL_SUPPLIER_ECOSYSTEM_NOT_DIFFERENT")

        verify_rel=str(pending["verification_result_path"])
        verify_cmd=[
            sys.executable,
            str(ROOT/"canonical"/"runtime"/"verify_pending_cli_binding.py"),
            str(pending_path.relative_to(ROOT)),
            verify_rel,
        ]
        remaining=max(1,int(spec["acceptance"]["hard_validation_wall_s"]-(time.monotonic()-t0)))
        proc=subprocess.run(verify_cmd,text=True,capture_output=True,cwd=ROOT,timeout=remaining)
        verify_path=ROOT/verify_rel
        verify=json.loads(verify_path.read_text(encoding="utf-8")) if verify_path.exists() else None
        if proc.returncode!=0:
            raise RuntimeError("EXISTING_INDEPENDENT_VERIFIER_FAILED:"+proc.stderr[-3000:])
        if not isinstance(verify,dict) or verify.get("status")!="VERIFIED" or verify.get("independent_verified") is not True:
            raise RuntimeError("EXISTING_INDEPENDENT_VERIFICATION_NOT_PROVEN")

        output_path=ROOT/spec["real_effect"]["output_path"]
        raw=output_path.read_bytes()
        if not raw or not raw.startswith(PNG_MAGIC):
            raise RuntimeError("OUTPUT_NOT_VALID_PNG")
        oracle=subprocess.run(
            ["zbarimg","--quiet",str(output_path)],
            text=True,capture_output=True,cwd=ROOT,timeout=30
        )
        oracle_stdout=oracle.stdout.strip()
        expected=spec["acceptance"]["external_semantic_oracle"]["expected_stdout_exact"]
        if oracle.returncode!=0 or oracle_stdout!=expected:
            raise RuntimeError("EXTERNAL_SEMANTIC_ORACLE_MISMATCH:"+json.dumps({
                "returncode":oracle.returncode,
                "stdout":oracle_stdout,
                "stderr":oracle.stderr[-1000:],
                "expected":expected,
            },sort_keys=True))

        total=time.monotonic()-t0
        passed=total<=float(spec["acceptance"]["hard_validation_wall_s"])
        result={
            "schema":"PROJECT_BRAIN_XAPIAN_APT_E2E_INTEGRATION_HELDOUT_RESULT_V1",
            "validation_id":vid,
            "acceptance_gate_pass":passed,
            "dispatch":dispatch,
            "selected_supplier":supplier,
            "orthogonality":{
                "reference_domain":"ONE_DIMENSIONAL_RETAIL_BARCODE",
                "new_domain":"TWO_DIMENSIONAL_QR_MATRIX_CODE",
                "domain_materially_different":True,
                "reference_supplier":reference_supplier,
                "selected_supplier":current_supplier,
                "supplier_ecosystem_materially_different":current_supplier!=reference_supplier,
                "material_dimensions_proven":2,
            },
            "verification_result":verify,
            "external_semantic_oracle":{
                "returncode":oracle.returncode,
                "stdout":oracle_stdout,
                "expected":expected,
                "verified":oracle_stdout==expected and oracle.returncode==0,
            },
            "output_sha256":hashlib.sha256(raw).hexdigest(),
            "output_bytes":len(raw),
            "observed_runtime_blobs":observed_runtime,
            "total_wall_s":round(total,6),
            "hard_validation_wall_s":spec["acceptance"]["hard_validation_wall_s"],
            "package_hints_used_by_runtime":False,
            "prebound_registry_route_used":False,
            "promotion_authorized":False,
            "required_next_action":"RECONCILE_FIRST_TERMINAL_RESULT__NO_REPLAY_BEFORE_RECONCILIATION",
        }
        terminal_result(result,0 if passed else 2)
    except Exception as exc:
        total=time.monotonic()-t0
        failure={
            "schema":"PROJECT_BRAIN_XAPIAN_APT_E2E_INTEGRATION_HELDOUT_RESULT_V1",
            "validation_id":vid,
            "acceptance_gate_pass":False,
            "error":type(exc).__name__+":"+str(exc),
            "traceback":traceback.format_exc(),
            "observed_runtime_blobs":observed_runtime,
            "total_wall_s":round(total,6),
            "hard_validation_wall_s":spec["acceptance"]["hard_validation_wall_s"],
            "package_hints_used_by_runtime":False,
            "prebound_registry_route_used":False,
            "promotion_authorized":False,
            "required_next_action":"RECONCILE_FIRST_TERMINAL_RESULT__NO_REPLAY_BEFORE_RECONCILIATION",
        }
        terminal_result(failure,2)


def _decode_worker_result(stdout):
    for line in reversed(str(stdout or "").splitlines()):
        if not line.startswith(RESULT_SENTINEL):
            continue
        raw=base64.b64decode(line[len(RESULT_SENTINEL):],validate=True)
        return json.loads(raw.decode("utf-8"))
    return None


def supervisor_main():
    spec,vid=_load_fresh_spec()
    if RESULT.exists():
        raise SystemExit("TERMINAL_RESULT_ALREADY_EXISTS")
    selected_executor,attestation_sha256,hard_zero_evidence=_admit_executor_before_start(spec)
    EVID.mkdir(parents=True,exist_ok=True)
    t0=time.monotonic()
    t0_ns=time.monotonic_ns()
    try:
        fd=os.open(str(START),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o644)
    except FileExistsError:
        raise SystemExit("EXECUTION_START_ALREADY_EXISTS")
    with os.fdopen(fd,"w",encoding="utf-8") as fh:
        json.dump({
            "validation_id":vid,
            "supervisor_pid":os.getpid(),
            "started_unix_ns":time.time_ns(),
            "hard_validation_wall_s":spec["acceptance"]["hard_validation_wall_s"],
            "executor_id":selected_executor.executor_id,
            "executor_provider":selected_executor.provider,
            "executor_attestation_sha256":attestation_sha256,
            "hard_zero_evidence":hard_zero_evidence,
            "user_device_used":False,
        },fh,sort_keys=True)
        fh.write("\n")

    env=os.environ.copy()
    env[WORKER_ENV]="1"
    env[START_MONOTONIC_NS_ENV]=str(t0_ns)
    proc=subprocess.Popen(
        [sys.executable,str(pathlib.Path(__file__).resolve())],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    hard_s=float(spec["acceptance"]["hard_validation_wall_s"])
    remaining=max(0.001,hard_s-(time.monotonic()-t0))
    try:
        stdout,stderr=proc.communicate(timeout=remaining)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid,signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout,stderr=proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout,stderr=proc.communicate()
        total=time.monotonic()-t0
        failure={
            "schema":"PROJECT_BRAIN_XAPIAN_APT_E2E_INTEGRATION_HELDOUT_RESULT_V1",
            "validation_id":vid,
            "acceptance_gate_pass":False,
            "error":"TimeoutError:HARD_VALIDATION_WALL_EXCEEDED",
            "total_wall_s":round(total,6),
            "hard_validation_wall_s":spec["acceptance"]["hard_validation_wall_s"],
            "worker_process_group_killed":True,
            "package_hints_used_by_runtime":False,
            "prebound_registry_route_used":False,
            "promotion_authorized":False,
            "required_next_action":"RECONCILE_FIRST_TERMINAL_RESULT__NO_REPLAY_BEFORE_RECONCILIATION",
        }
        terminal_result(failure,2)

    if stderr:
        print(stderr,end="",file=sys.stderr)
    payload=_decode_worker_result(stdout)
    if payload is None:
        total=time.monotonic()-t0
        payload={
            "schema":"PROJECT_BRAIN_XAPIAN_APT_E2E_INTEGRATION_HELDOUT_RESULT_V1",
            "validation_id":vid,
            "acceptance_gate_pass":False,
            "error":"RuntimeError:WORKER_EXITED_WITHOUT_TERMINAL_RESULT",
            "worker_returncode":proc.returncode,
            "total_wall_s":round(total,6),
            "hard_validation_wall_s":spec["acceptance"]["hard_validation_wall_s"],
            "package_hints_used_by_runtime":False,
            "prebound_registry_route_used":False,
            "promotion_authorized":False,
            "required_next_action":"RECONCILE_FIRST_TERMINAL_RESULT__NO_REPLAY_BEFORE_RECONCILIATION",
        }
        terminal_result(payload,2)
    terminal_result(payload,0 if proc.returncode==0 and payload.get("acceptance_gate_pass") is True else 2)


def main():
    if os.environ.get(WORKER_ENV)=="1":
        worker_main()
    supervisor_main()


if __name__=="__main__":
    main()
