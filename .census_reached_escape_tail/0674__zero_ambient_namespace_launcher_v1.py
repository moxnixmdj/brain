from __future__ import annotations
import hashlib, json, math, os, pathlib, shutil, socket, subprocess, tempfile, threading, time
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA='PROJECT_BRAIN_ZERO_AMBIENT_NAMESPACE_LAUNCHER_V1'
_ALLOWED_ENV={'LANG','LC_ALL','TZ','PYTHONHASHSEED','PYTHONDONTWRITEBYTECODE'}

class NamespaceConfinementError(ValueError): pass

def _inside_mounts(path:pathlib.Path)->list[str]:
    target=str(path.resolve()); hits=[]
    try: raw=pathlib.Path('/proc/self/mountinfo').read_text()
    except Exception: raise NamespaceConfinementError('MOUNTINFO_UNAVAILABLE')
    for line in raw.splitlines():
        parts=line.split()
        if len(parts)<5: continue
        mountpoint=parts[4].replace('\\040',' ')
        try: mp=str(pathlib.Path(mountpoint).resolve())
        except Exception: continue
        if mp!=target and mp.startswith(target.rstrip('/')+'/'): hits.append(mp)
    return sorted(set(hits))

def canonical_policy(policy:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(policy,Mapping): raise NamespaceConfinementError('POLICY_NOT_OBJECT')
    argv_raw=policy.get('argv')
    if not isinstance(argv_raw,Sequence) or isinstance(argv_raw,(str,bytes)) or not argv_raw:
        raise NamespaceConfinementError('ARGV_REQUIRED')
    argv=[str(x) for x in argv_raw]
    if any((not x or '\x00' in x) for x in argv): raise NamespaceConfinementError('ARGV_INVALID')
    if not (argv[0].startswith('/usr/') or argv[0].startswith('/bin/') or argv[0].startswith('/input/')):
        raise NamespaceConfinementError('ARGV0_MUST_BE_SYSTEM_OR_INPUT_PATH')
    input_dir=pathlib.Path(str(policy.get('input_dir') or '')).expanduser().resolve()
    if not input_dir.is_dir(): raise NamespaceConfinementError('INPUT_DIR_REQUIRED')
    nested=_inside_mounts(input_dir)
    if nested: raise NamespaceConfinementError('INPUT_DIR_HAS_NESTED_MOUNTS:'+','.join(nested))
    env_raw=policy.get('env') or {}
    if not isinstance(env_raw,Mapping): raise NamespaceConfinementError('ENV_NOT_OBJECT')
    env={}
    for k0,v0 in env_raw.items():
        k=str(k0); v=str(v0)
        if k not in _ALLOWED_ENV: raise NamespaceConfinementError('ENV_NAME_NOT_ALLOWLISTED:'+k)
        if '\x00' in v or len(v)>512: raise NamespaceConfinementError('ENV_VALUE_INVALID:'+k)
        env[k]=v
    lim=policy.get('limits') or {}
    if not isinstance(lim,Mapping): raise NamespaceConfinementError('LIMITS_NOT_OBJECT')
    pids=int(lim.get('pids',32)); memory_mb=int(lim.get('memory_mb',256)); cpu_seconds=int(lim.get('cpu_seconds',2))
    wallclock_s=int(lim.get('wallclock_s',10)); scratch_mb=int(lim.get('scratch_mb',32)); max_file_mb=int(lim.get('max_file_mb',8))
    nofile=int(lim.get('nofile',32)); broker_max_bytes=int(lim.get('broker_max_bytes',8_000_000))
    ranges=[('pids',pids,1,128),('memory_mb',memory_mb,64,4096),('cpu_seconds',cpu_seconds,1,300),('wallclock_s',wallclock_s,1,600),('scratch_mb',scratch_mb,8,1024),('max_file_mb',max_file_mb,1,1024),('nofile',nofile,8,256),('broker_max_bytes',broker_max_bytes,1,8_000_000)]
    for name,v,lo,hi in ranges:
        if not lo<=v<=hi: raise NamespaceConfinementError(name.upper()+'_LIMIT_INVALID')
    host_uid=policy.get('host_uid'); host_gid=policy.get('host_gid')
    if os.geteuid()==0:
        if host_uid is None or host_gid is None: raise NamespaceConfinementError('ROOT_PARENT_REQUIRES_NONROOT_HOST_UID_GID')
        host_uid=int(host_uid); host_gid=int(host_gid)
        if host_uid<=0 or host_gid<=0: raise NamespaceConfinementError('HOST_UID_GID_MUST_BE_NONROOT')
    else:
        if host_uid is not None and int(host_uid)!=os.geteuid(): raise NamespaceConfinementError('HOST_UID_MUST_EQUAL_CURRENT_NONROOT_UID')
        if host_gid is not None and int(host_gid)!=os.getegid(): raise NamespaceConfinementError('HOST_GID_MUST_EQUAL_CURRENT_NONROOT_GID')
        host_uid=os.geteuid(); host_gid=os.getegid()
    return {'schema':SCHEMA,'argv':argv,'input_dir':str(input_dir),'env':dict(sorted(env.items())),'host_uid':host_uid,'host_gid':host_gid,'limits':{'pids':pids,'memory_mb':memory_mb,'cpu_seconds':cpu_seconds,'wallclock_s':wallclock_s,'scratch_mb':scratch_mb,'max_file_mb':max_file_mb,'nofile':nofile,'broker_max_bytes':broker_max_bytes},'authority':{'network':'PRIVATE_NAMESPACE_LOOPBACK_ONLY','host_filesystem':'READ_ONLY_SYSTEM_AND_SINGLE_INPUT_BIND_ONLY','linux_capabilities':'DROPPED_BEFORE_WORKLOAD','privilege_escalation':'DENY_NO_NEW_PRIVILEGES','host_pid_namespace':'DENY','host_ipc_namespace':'DENY','host_uts_namespace':'DENY','mutable_storage':'READ_ONLY_PRIVATE_ROOT_PLUS_WRITABLE_PRIVATE_TMPFS_TMP_AND_WORK_ONLY','material_effect_channel':'ONE_INHERITED_BROKER_FD_ONLY'}}

def policy_sha256(policy:Mapping[str,Any])->str:
    p=canonical_policy(policy)
    return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()

_SETUP=r'''set -euo pipefail
ROOT="$1"; INPUT="$2"; BROKER="$3"; MEM_KB="$4"; CPU_S="$5"; FILE_KB="$6"; NOFILE="$7"; PIDS="$8"; SCRATCH_MB="$9"; shift 9
mount --make-rprivate /
mount -t tmpfs -o size=64m,nosuid,nodev tmpfs "$ROOT"
mkdir -p "$ROOT/usr" "$ROOT/bin" "$ROOT/lib" "$ROOT/lib64" "$ROOT/tmp" "$ROOT/work" "$ROOT/input"
for d in /usr /bin /lib /lib64; do
  [ -e "$d" ] || continue
  base="${d#/}"
  if [ -L "$d" ]; then rm -rf "$ROOT/$base"; ln -s "$(readlink "$d")" "$ROOT/$base"; fi
done
mount --bind "$ROOT" "$ROOT"
mount -o remount,bind,ro "$ROOT"
for d in /usr /bin /lib /lib64; do
  [ -e "$d" ] || continue
  [ -L "$d" ] && continue
  mount --bind "$d" "$ROOT$d"
  mount -o remount,bind,ro,nosuid,nodev "$ROOT$d"
done
mount --bind "$INPUT" "$ROOT/input"
mount -o remount,bind,ro,nosuid,nodev "$ROOT/input"
mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev,noexec tmpfs "$ROOT/tmp"
mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev tmpfs "$ROOT/work"
IP_BIN="$(command -v ip)"; CHROOT_BIN="$(command -v chroot)"
"$IP_BIN" link set lo up
ulimit -t "$CPU_S"; ulimit -v "$MEM_KB"; ulimit -f "$FILE_KB"; ulimit -n "$NOFILE"; ulimit -u "$PIDS"
exec "$CHROOT_BIN" "$ROOT" /usr/bin/env -i PATH=/usr/bin:/bin HOME=/tmp PROJECT_BRAIN_BROKER_FD="$BROKER" "$@"
'''

def run_confined(policy:Mapping[str,Any])->dict[str,Any]:
    p=canonical_policy(policy); lim=p['limits']
    required_names=['unshare','mount','chroot','setpriv','ip','bash','env']
    resolved={name:shutil.which(name) for name in required_names}
    missing=[name for name,path in resolved.items() if not path]
    if missing: raise NamespaceConfinementError('HOST_PRIMITIVE_MISSING:'+','.join(missing))
    root=tempfile.mkdtemp(prefix='brain-ns-membrane-'); os.chown(root,p['host_uid'],p['host_gid'])
    parent,child=socket.socketpair(); broker=[]; overflow=[False]
    def reader():
        total=0
        try:
            while True:
                b=parent.recv(65536)
                if not b: break
                total+=len(b)
                if total>lim['broker_max_bytes']:
                    overflow[0]=True
                    try: parent.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
                    break
                broker.append(b)
        except OSError: pass
    th=threading.Thread(target=reader,daemon=True); th.start()
    env={'BROKER_FD':str(child.fileno()),'PYTHONDONTWRITEBYTECODE':'1'}
    for k,v in p['env'].items(): env[k]=v
    cmd=[resolved['unshare'],'--user','--map-root-user','--mount','--net','--pid','--fork','--ipc','--uts',resolved['bash'],'-c',_SETUP,'_',root,p['input_dir'],str(child.fileno()),str(lim['memory_mb']*1024),str(lim['cpu_seconds']),str(math.ceil(lim['max_file_mb']*1024)),str(lim['nofile']),str(lim['pids']),str(lim['scratch_mb']),resolved['setpriv'],'--no-new-privs','--bounding-set=-all','--inh-caps=-all','--ambient-caps=-all',resolved['env'],'-i','PATH=/usr/bin:/bin','HOME=/tmp','PYTHONDONTWRITEBYTECODE=1','PROJECT_BRAIN_BROKER_FD='+str(child.fileno())]
    for k,v in p['env'].items(): cmd.append(k+'='+v)
    cmd += p['argv']
    popen_kw={'stdin':subprocess.DEVNULL,'stdout':subprocess.DEVNULL,'stderr':subprocess.DEVNULL,'pass_fds':(child.fileno(),),'env':env,'start_new_session':True}
    if os.geteuid()==0: popen_kw.update(user=p['host_uid'],group=p['host_gid'],extra_groups=[])
    started=time.monotonic(); timed_out=False
    try:
        proc=subprocess.Popen(cmd,**popen_kw); child.close()
        try: rc=proc.wait(timeout=lim['wallclock_s'])
        except subprocess.TimeoutExpired:
            timed_out=True
            try: os.killpg(proc.pid,9)
            except ProcessLookupError: pass
            rc=proc.wait(timeout=5)
        th.join(timeout=2)
    finally:
        try: child.close()
        except OSError: pass
        try: parent.close()
        except OSError: pass
        shutil.rmtree(root,ignore_errors=True)
    raw=b''.join(broker); status='CHILD_EXITED'
    if timed_out: status='WALLCLOCK_LIMIT_EXCEEDED'
    elif overflow[0]: status='BROKER_OUTPUT_LIMIT_EXCEEDED'
    return {'schema':SCHEMA,'status':status,'policy_sha256':policy_sha256(p),'returncode':rc,'wallclock_ms':round((time.monotonic()-started)*1000,3),'broker_bytes':len(raw),'broker_sha256':hashlib.sha256(raw).hexdigest(),'broker_payload':raw,'material_effects_committed':0,'execution_authority':False,'promotion_authority':False,'fresh_reality_authority':False}
