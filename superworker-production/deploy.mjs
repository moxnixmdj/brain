import { writeFileSync, unlinkSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const token = process.env.CONTROL_TOKEN;
if (!token) {
  console.error('CONTROL_TOKEN build secret is required.');
  process.exit(2);
}

const secretPath = '.runtime-secrets.json';
try {
  writeFileSync(secretPath, JSON.stringify({ CONTROL_TOKEN: token }), { mode: 0o600 });
  const r = spawnSync(
    process.platform === 'win32' ? 'npx.cmd' : 'npx',
    ['wrangler', 'deploy', '--secrets-file', secretPath],
    { stdio: 'inherit', env: process.env }
  );
  process.exitCode = r.status ?? 1;
} finally {
  try { unlinkSync(secretPath); } catch {}
}
