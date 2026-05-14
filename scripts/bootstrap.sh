#!/usr/bin/env bash
# FIND EVIL bootstrap — idempotent setup for /opt/findevil on WSL2 + SIFT.
#
# Assumes the repo has been cloned to /opt/findevil/repo. Creates the runtime dirs,
# installs the Python package in editable mode, generates signing keys, seeds the
# genesis ledger entry, and prints post-install next steps.

set -euo pipefail
IFS=$'\n\t'

ROOT="${FINDEVIL_ROOT:-/opt/findevil}"
REPO="${ROOT}/repo"
PYTHON="${PYTHON:-python3.12}"
VENV="${ROOT}/venv"

msg() { printf '\033[1;34m[bootstrap]\033[0m %s\n' "$*"; }

msg "ensuring findevil service account"
sudo groupadd --system findevil 2>/dev/null || true
sudo useradd --system --home "${ROOT}" --shell /usr/sbin/nologin --gid findevil \
    findevil 2>/dev/null || true
sudo usermod -aG findevil "$USER" 2>/dev/null || true

msg "creating layout under ${ROOT}"
sudo install -d -m 0755 -o root -g root "${ROOT}"
sudo install -d -m 0755 -o "$USER" -g findevil "${ROOT}/bin" "${VENV}"
sudo install -d -m 0770 -o findevil -g findevil \
    "${ROOT}/data" "${ROOT}/data/ledger" "${ROOT}/data/calibrators" \
    "${ROOT}/data/quarantine" "${ROOT}/data/yara-rules" "${ROOT}/data/models" \
    "${ROOT}/logs" "${ROOT}/run" "${ROOT}/run/zmq" "${ROOT}/run/otel"
sudo install -d -m 0750 -o root -g findevil "${ROOT}/etc" "${ROOT}/etc/findevil.d"
sudo install -d -m 0750 -o findevil -g findevil "${ROOT}/etc/keys"

msg "python venv in ${VENV}"
if [[ ! -x "${VENV}/bin/python" ]]; then
    "${PYTHON}" -m venv "${VENV}"
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
"${VENV}/bin/pip" install --upgrade pip wheel setuptools
"${VENV}/bin/pip" install -e "${REPO}[dev]"

msg "generating Ed25519 keys (idempotent)"
"${VENV}/bin/python" "${REPO}/scripts/keygen.py" all || true

msg "seeding genesis ledger entry"
"${VENV}/bin/python" "${REPO}/scripts/seed_genesis.py" || true

msg "normalizing runtime ownership"
sudo chown -R findevil:findevil \
    "${ROOT}/data" "${ROOT}/logs" "${ROOT}/run" "${ROOT}/etc/keys"
sudo chmod 0750 "${ROOT}/etc/keys"
sudo find "${ROOT}/etc/keys" -type f -name '*.sk' -exec chmod 0600 {} +
sudo find "${ROOT}/etc/keys" -type f -name '*.pk' -exec chmod 0644 {} +

msg "copying daemon configs into ${ROOT}/etc"
sudo install -m 0640 -o root -g findevil "${REPO}/etc/valkey.conf"      "${ROOT}/etc/valkey.conf"
sudo install -m 0640 -o root -g findevil "${REPO}/etc/nats-server.conf" "${ROOT}/etc/nats-server.conf"
sudo install -m 0640 -o root -g findevil "${REPO}/etc/otel-config.yaml" "${ROOT}/etc/otel-config.yaml"
if [[ ! -f "${ROOT}/etc/.env" ]]; then
    sudo install -m 0640 -o root -g findevil "${REPO}/etc/.env.example" "${ROOT}/etc/.env"
    msg "created ${ROOT}/etc/.env from template — edit secrets before boot"
else
    sudo chown root:findevil "${ROOT}/etc/.env"
    sudo chmod 0640 "${ROOT}/etc/.env"
fi

msg "copying systemd units to /etc/systemd/system (requires sudo)"
sudo install -m 0644 "${REPO}/etc/systemd/"findevil-*.service /etc/systemd/system/
sudo install -m 0644 "${REPO}/etc/systemd/"findevil-*.timer /etc/systemd/system/
sudo install -m 0644 "${REPO}/etc/systemd/"findevil.target /etc/systemd/system/
sudo install -m 0644 "${REPO}/etc/systemd/valkey-findevil.service" /etc/systemd/system/
sudo install -m 0644 "${REPO}/etc/systemd/nats-findevil.service" /etc/systemd/system/
sudo install -m 0644 "${REPO}/etc/systemd/findevil.tmpfiles.conf" /etc/tmpfiles.d/findevil.conf || true
sudo systemd-tmpfiles --create /etc/tmpfiles.d/findevil.conf || true
sudo systemctl daemon-reload

msg "done. Next:"
echo "  sudoedit ${ROOT}/etc/.env                       # set NATS passwords, inference URL, etc."
echo "  sudo systemctl enable --now valkey-findevil.service nats-findevil.service"
echo "  ${VENV}/bin/findevil nats-setup                  # create guide-mandated JetStream streams"
echo "  sudo systemctl enable --now findevil.target"
echo "  sudo systemctl enable --now findevil-verify.timer"
echo "  ${VENV}/bin/findevil status"
