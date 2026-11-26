#!/usr/bin/env bash
# Blind producer process for a local, synchronous experiment, not a desktop
# sandbox. stdin/out are its ONLY fixture connection. No games, ORM, API keys,
# checker, engine library, report tree, /proc, or host home in the new root.
set -euo pipefail
[[ $$ = 1 && $(id -u) = 0 ]] || exit 2
root=$1; src=$2
case ${3:-screen} in screen) worker=screen_port_worker_v1;; cue) worker=cue_port_worker_v1;; *) exit 2;; esac
mount --make-rprivate /
for p in usr bin lib lib64; do
  if [[ -L /$p ]]; then ln -s "$(readlink "/$p")" "$root/$p"; continue; fi
  [[ -d /$p ]] || continue
  mkdir "$root/$p"; mount --bind "/$p" "$root/$p"; mount -o remount,bind,ro,nosuid,nodev "$root/$p"
done
mkdir "$root"/{src,tmp}
mount --bind "$src" "$root/src"; mount -o remount,bind,ro,nosuid,nodev "$root/src"
ulimit -t 90; ulimit -v 1000000; ulimit -f 10000
exec chroot "$root" /usr/bin/setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all \
  /usr/bin/env -i HOME=/tmp LC_ALL=C.UTF-8 PATH=/usr/bin:/bin /usr/bin/python3 -I -S -B "/src/canonical/tools/$worker.py"
