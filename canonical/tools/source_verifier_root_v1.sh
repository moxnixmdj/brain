#!/usr/bin/env bash
# Grader only, never a task producer or a production sandbox. Enter with
# unshare --user --map-root-user --mount --net --pid --fork. All paths are
# fixture-owned. The script the grader executes is the upstream test.sh.
set -euo pipefail
[[ $$ = 1 && $(id -u) = 0 ]] || { echo 'private PID/user namespaces required' >&2; exit 2; }
root=$1; tests=$2; venv=$3
mount --make-rprivate /
for p in usr bin lib lib64; do
  if [[ -L /$p ]]; then ln -s "$(readlink "/$p")" "$root/$p"; continue; fi
  [[ -d /$p ]] || continue
  mkdir "$root/$p"; mount --bind "/$p" "$root/$p"; mount -o remount,bind,ro,nosuid,nodev "$root/$p"
done
mkdir -p "$root"/{dev,proc,tests,venv,tmp,etc,logs/verifier}
for p in null zero random urandom; do touch "$root/dev/$p"; mount --bind "/dev/$p" "$root/dev/$p"; done
mount -t proc -o ro,nosuid,nodev,noexec proc "$root/proc"
mount --bind "$tests" "$root/tests"; mount -o remount,bind,ro,nosuid,nodev "$root/tests"
mount --bind "$venv" "$root/venv"; mount -o remount,bind,ro,nosuid,nodev "$root/venv"
printf 'runner:x:0:0:runner:/tmp:/bin/bash\n' > "$root/etc/passwd"
printf 'runner:x:0:\n' > "$root/etc/group"
ip link set lo up
ulimit -t 180; ulimit -v 3000000; ulimit -f 100000
exec /usr/sbin/chroot "$root" /usr/bin/setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all \
  /usr/bin/env -i HOME=/tmp LC_ALL=C.UTF-8 PATH=/venv/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 \
  /bin/bash /tests/test.sh
