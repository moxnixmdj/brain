#!/usr/bin/env bash
# Setup script for GitHub Actions self-hosted runner on WSL2 (Ubuntu).
# Run inside WSL2 after: wsl --install (Windows 11) + reboot.
# Prerequisites: Ubuntu WSL distro, internet access, GitHub repo admin.
set -euo pipefail

echo "=== 1. Update system ==="
sudo apt-get update -qq
sudo apt-get install -y -qq curl wget git build-essential

echo "=== 2. Install heartbeat dependencies ==="
sudo apt-get install -y -qq jq pandoc poppler-utils qrencode sqlite3 tesseract-ocr zbar-tools zint weasyprint python3-docx python3-openpyxl python3-xlsxwriter 2>/dev/null || true
python3 -m pip install --quiet pillow sympy python-docx openpyxl xlsxwriter pypdf pyyaml msgpack pymongo yq weasyprint 2>/dev/null || true

echo "=== 3. Download GitHub Actions runner ==="
RUNNER_VERSION="2.321.0"
RUNNER_DIR="$HOME/actions-runner"
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"
curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz -L \
  "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
tar xzf actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

echo "=== 4. Configure runner ==="
echo "You will be prompted for:"
echo "  - GitHub repo URL: https://github.com/moxnixmdj/brain"
echo "  - Runner token: get from GitHub repo Settings -> Actions -> Runners -> New self-hosted runner"
echo "  - Runner name: brain-tuf-a15"
echo "  - Labels: self-hosted,linux,x64,brain-regression"
echo ""
./config.sh --url https://github.com/moxnixmdj/brain \
  --token "${RUNNER_TOKEN:-}" \
  --name brain-tuf-a15 \
  --labels self-hosted,linux,x64,brain-regression \
  --work _work

echo "=== 5. Install as service (optional, auto-start on boot) ==="
echo "To install as a service: sudo ./svc.sh install && sudo ./svc.sh start"
echo "To run manually: ./run.sh"

echo "=== Done ==="
echo "Start the runner: cd $RUNNER_DIR && ./run.sh"
