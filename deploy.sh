#!/usr/bin/env bash
# Test-gated deploy: pytest + node -> rsync -> systemd restart -> health check.
set -euo pipefail

PI_HOST="${PI_HOST:-raspberrypi.local}"
PI_USER="${PI_USER:-pi}"
APP_DIR="${APP_DIR:-/home/pi/english-cockpit}"
UNIT_NAME="${UNIT_NAME:-english-cockpit}"
PORT="${PORT:-8000}"

if [[ ! -x ./.venv/bin/python ]]; then
  echo "ERROR: ./.venv not found — set up the venv first (see README 'Run locally')." >&2
  exit 1
fi

echo "==> Backend tests"
./.venv/bin/python -m pytest -q

echo "==> Frontend tests"
npm test

echo "==> Syncing to ${PI_USER}@${PI_HOST}:${APP_DIR}"
rsync -az --delete \
  --exclude '.venv/' \
  --exclude '.git/' \
  --exclude 'node_modules/' \
  --exclude 'data/' \
  --exclude 'tests/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.mypy_cache/' \
  --exclude '.ruff_cache/' \
  --exclude '.env' \
  ./ "${PI_USER}@${PI_HOST}:${APP_DIR}/"

if [[ "${INSTALL_DEPS:-0}" == "1" ]]; then
  echo "==> Installing dependencies on the Pi"
  ssh "${PI_USER}@${PI_HOST}" \
    "cd '${APP_DIR}' && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
fi

if [[ "${INSTALL_UNIT:-0}" == "1" ]]; then
  echo "==> Installing systemd unit"
  scp deploy/english-cockpit.service "${PI_USER}@${PI_HOST}:/tmp/${UNIT_NAME}.service"
  ssh "${PI_USER}@${PI_HOST}" \
    "sudo mv /tmp/${UNIT_NAME}.service /etc/systemd/system/${UNIT_NAME}.service \
     && sudo systemctl daemon-reload && sudo systemctl enable '${UNIT_NAME}'"
fi

echo "==> Restarting ${UNIT_NAME}"
ssh "${PI_USER}@${PI_HOST}" "sudo systemctl restart '${UNIT_NAME}'"

echo "==> Waiting for /healthz"
for _ in $(seq 1 30); do
  if ssh "${PI_USER}@${PI_HOST}" "curl -fsS 'http://127.0.0.1:${PORT}/healthz'" >/dev/null 2>&1; then
    echo "==> Deploy complete (healthy)"
    exit 0
  fi
  sleep 0.5
done

echo "ERROR: /healthz did not respond within 15s" >&2
exit 1
