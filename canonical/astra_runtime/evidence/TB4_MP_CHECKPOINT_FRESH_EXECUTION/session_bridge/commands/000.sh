set -e
echo "===== /app TREE ====="
ls -la /app
find /app -maxdepth 3 -type f -printf '%p %s bytes\n' | sort
echo "===== PYTHON / TORCH ====="
python3 -c "import sys, torch, safetensors, numpy; print('py', sys.version.split()[0]); print('torch', torch.__version__); print('safetensors', safetensors.__version__); print('numpy', numpy.__version__)"
echo "===== SHARD FILES ====="
ls -la /app/checkpoints
echo "===== SHARD CONTENTS ====="
python3 - <<'PY'
import torch, glob, os, json
files = sorted(glob.glob('/app/checkpoints/*'))
print('n files', len(files))
summary = {}
for f in files:
    try:
        d = torch.load(f, map_location='cpu', weights_only=False)
    except Exception as e:
        print(os.path.basename(f), 'LOAD ERR', repr(e)); continue
    if not isinstance(d, dict):
        print(os.path.basename(f), 'not a dict:', type(d)); continue
    row = {}
    for k, v in d.items():
        if torch.is_tensor(v):
            row[k] = [list(v.shape), str(v.dtype), v.numel()]
        else:
            row[k] = [type(v).__name__, repr(v)[:120]]
    summary[os.path.basename(f)] = row
    print('---', os.path.basename(f))
    for k, v in row.items():
        print('    ', k, '->', v)
print('===== SUMMARY JSON =====')
print(json.dumps(summary, indent=1))
PY
echo "===== REFERENCE OUTPUT ====="
ls -la /app/reference_output
python3 - <<'PY'
import torch, json
li = torch.load('/app/reference_output/input_ids.pt', map_location='cpu')
lg = torch.load('/app/reference_output/logits.pt', map_location='cpu')
print('input_ids', tuple(li.shape), li.dtype)
print('  values', li.flatten()[:24].tolist())
print('logits', tuple(lg.shape), lg.dtype, 'dtype-sum', float(lg.float().sum()))
ek = json.load(open('/app/reference_output/expected_keys.json'))
print('expected_keys count', len(ek), type(ek).__name__)
keys = ek if isinstance(ek, list) else sorted(ek)
for k in keys:
    print('  KEY', k)
PY
echo "===== FRAMEWORK SOURCE ====="
find /app/framework /app/reference_model -type f | sort
echo "===== OUTPUT DIR ====="
ls -la /app/output
echo "===== HOST RESOURCES ====="
df -h /app /tmp | tail -3; free -m | head -2; nproc
