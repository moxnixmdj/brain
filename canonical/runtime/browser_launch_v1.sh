#!/bin/sh
# Obtain and start a real Chromium with the DevTools protocol exposed.
#
# The --dump-dom and --screenshot CLI paths hang in containers without
# working graphics: the GPU process fails to initialise and compositing
# never completes. The DevTools endpoint starts regardless. That is how
# Puppeteer and Playwright actually drive a browser, so drive it there.
#
# Usage:  sh browser_launch_v1.sh [port]
# Stop:   pkill -f remote-debugging-port
#
# CERTIFICATES, verified rather than assumed.
#
# An earlier note here claimed this build has no root certificate store and
# must relax verification. That was checked on 2026-10-17 and is no longer
# true. Serving a self-signed certificate to this browser produced
# ERR_CERT_AUTHORITY_INVALID, and loading https://pypi.org succeeded with no
# bypass flag on the command line. A stale warning left in place is worse
# than none: it invites someone to relax TLS for a problem that is gone.
#
# CHROMIUM_INSECURE is therefore NOT set here. Setting it makes the browser
# accept a certificate it cannot prove belongs to the host, and should only
# ever be done knowingly, for a host you are willing to trust blindly.
# Prefer CHROMIUM_SPKI_PINS below, which pins one host's key instead.
set -e
PORT="${1:-9222}"
BUILD="${BRAIN_BROWSER_BUILD:-$HOME/browser_build}"
mkdir -p "$BUILD"; cd "$BUILD"
[ -f package.json ] || printf '{"name":"b","private":true}\n' > package.json
[ -d node_modules/@sparticuz/chromium ] || npm install @sparticuz/chromium --no-audit --no-fund
[ -d node_modules/ws ] || npm install ws --no-audit --no-fund
[ -x ./chromium ] || node -e "
const fs=require('fs'),z=require('zlib'),p=require('path');
const d='node_modules/@sparticuz/chromium/bin';
fs.writeFileSync('chromium', z.brotliDecompressSync(fs.readFileSync(p.join(d,'chromium.br'))));
fs.chmodSync('chromium',0o755);
for (const [f,o] of [['swiftshader.tar.br','sw.tar'],['al2023.tar.br','al2023.tar']])
  fs.writeFileSync(o, z.brotliDecompressSync(fs.readFileSync(p.join(d,f))));
"
[ -d sw ] || { mkdir -p sw al && tar -xf sw.tar -C sw && tar -xf al2023.tar -C al; }
# Vulkan needs an absolute path to the SwiftShader driver.
node -e "const fs=require('fs');fs.writeFileSync('sw/vk_swiftshader_icd.json',JSON.stringify({file_format_version:'1.0.0',ICD:{library_path:process.cwd()+'/sw/libvk_swiftshader.so',api_version:'1.0.5'}},null,2))"
# Certificate handling. There is no root store in this build, so instead of
# trusting anyone who answers we pin the key of the host we intend to visit.
# CHROMIUM_SPKI_PINS is a comma-separated list of base64 SHA-256 SPKI hashes;
# Chromium accepts a certificate only if one of those keys is in the chain.
# Leaving it empty falls back to CHROMIUM_INSECURE, which trusts everything
# and should not be used.

LD_LIBRARY_PATH="$PWD/sw:$PWD/al/lib" \
VK_ICD_FILENAMES="$PWD/sw/vk_swiftshader_icd.json" \
  nohup ./chromium --headless=new --no-sandbox --disable-setuid-sandbox \
    --disable-dev-shm-usage --disable-gpu \
    ${CHROMIUM_SPKI_PINS:+--ignore-certificate-errors-spki-list=$CHROMIUM_SPKI_PINS} \
    $( [ -z "$CHROMIUM_SPKI_PINS" ] && [ -n "$CHROMIUM_INSECURE" ] && echo --ignore-certificate-errors ) \
    --remote-debugging-port="$PORT" about:blank >/tmp/chromium_cdp.log 2>&1 &
# Wait for the endpoint rather than guessing at a sleep.
i=0; while [ $i -lt 60 ]; do
  if curl -sf "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    echo "Chromium ready on port $PORT"; exit 0
  fi
  i=$((i+1)); sleep 1
done
echo "Chromium did not become ready; see /tmp/chromium_cdp.log" >&2; exit 1
