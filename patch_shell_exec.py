import pathlib

BS = chr(92)   # backslash
Q = chr(34)    # double quote
NL = BS + "n"  # literal backslash-n sequence used in the raw setup string

p = pathlib.Path("canonical/runtime/root3_confined_shell_executor_v1.py")
t = p.read_text()

# 1) header: add ALIAS positional
h_old = 'SCRATCH_MB=' + Q + '${10}' + Q + '; shift 10'
h_new = 'SCRATCH_MB=' + Q + '${10}' + Q + '; ALIAS=' + Q + '${11}' + Q + '; shift 11'
assert h_old in t, 'head'
t = t.replace(h_old, h_new, 1)

# 2) alias mount block right after the RWSUB block's closing fi
anchor = 'fi' + NL + 'mount -t tmpfs -o size=' + Q + '${SCRATCH_MB}m' + Q + ',nosuid,nodev,noexec tmpfs ' + Q + '$ROOT/tmp' + Q
assert anchor in t, 'anchor'
alias_lines = [
    'if [ ' + Q + '$ALIAS' + Q + ' != ' + Q + '-' + Q + ' ]; then',
    '  mkdir -p ' + Q + '$ROOT$ALIAS' + Q,
    '  mount --bind ' + Q + '$INPUT' + Q + ' ' + Q + '$ROOT$ALIAS' + Q,
    '  mount -o remount,bind,ro,nosuid,nodev ' + Q + '$ROOT$ALIAS' + Q,
    '  if [ ' + Q + '$RWSUB' + Q + ' != ' + Q + '-' + Q + ' ]; then',
    '    mkdir -p ' + Q + '$ROOT$ALIAS/$RWSUB' + Q,
    '    mount --bind ' + Q + '$INPUT/$RWSUB' + Q + ' ' + Q + '$ROOT$ALIAS/$RWSUB' + Q,
    '    mount -o remount,bind,nosuid,nodev ' + Q + '$ROOT$ALIAS/$RWSUB' + Q,
    '  fi',
    'fi',
]
alias_block = NL.join(alias_lines) + NL
t = t.replace(anchor, 'fi' + NL + alias_block + anchor[len('fi' + NL):], 1)

# 3) launcher argv: alias positional after scratch_mb
o3 = '        str(lim[' + Q + 'scratch_mb' + Q + ']),\n        resolved[' + Q + 'setpriv' + Q + '],'
n3 = ('        str(lim[' + Q + 'scratch_mb' + Q + ']),\n'
      '        (str(policy.get(' + Q + 'alias_dir' + Q + ')) if policy.get(' + Q + 'alias_dir' + Q + ') else ' + Q + '-' + Q + '),\n'
      '        resolved[' + Q + 'setpriv' + Q + '],')
assert o3 in t, 'argv'
t = t.replace(o3, n3, 1)

p.write_text(t)
print('applied')
