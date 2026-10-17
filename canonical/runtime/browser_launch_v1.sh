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
LD_LIBRARY_PATH="$PWD/sw:$PWD/al/lib" \
VK_ICD_FILENAMES="$PWD/sw/vk_swiftshader_icd.json" \
  nohup ./chromium --headless=new --no-sandbox --disable-setuid-sandbox \
    --disable-dev-shm-usage --disable-gpu \
    --remote-debugging-port="$PORT" about:blank >/tmp/chromium_cdp.log 2>&1 &
# Wait for the endpoint rather than guessing at a sleep.
i=0; while [ $i -lt 60 ]; do
  if curl -sf "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    echo "Chromium ready on port $PORT"; exit 0
  fi
  i=$((i+1)); sleep 1
done
echo "Chromium did not become ready; see /tmp/chromium_cdp.log" >&2; exit 1
