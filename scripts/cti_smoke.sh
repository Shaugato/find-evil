#!/usr/bin/env bash
# Live smoke: taxii.ingest (offline bundle) must deposit a pheromone prior
# readable back through the MCP blackboard resource.
set -euo pipefail

# MCP service runs with PrivateTmp=true — the bundle must live under
# /opt/findevil/data (in the unit's ReadWritePaths), not /tmp.
BUNDLE_DIR=/opt/findevil/data/cti
mkdir -p "$BUNDLE_DIR"
chown findevil:findevil "$BUNDLE_DIR" 2>/dev/null || true
cat > "$BUNDLE_DIR/cti_test_bundle.json" <<'EOF'
{
  "type": "bundle",
  "id": "bundle--cti-smoke-0001",
  "objects": [
    {
      "type": "indicator",
      "spec_version": "2.1",
      "id": "indicator--cti-smoke-0001",
      "created": "2026-06-01T00:00:00.000Z",
      "modified": "2026-06-01T00:00:00.000Z",
      "name": "FIND EVIL CTI smoke C2",
      "confidence": 85,
      "pattern_type": "stix",
      "pattern": "[ipv4-addr:value = '203.0.113.250']",
      "valid_from": "2026-06-01T00:00:00Z"
    }
  ]
}
EOF

cd /opt/findevil/repo
/opt/findevil/venv/bin/python scripts/mcp_probe.py taxii.ingest \
  --args '{"taxii.ingest": {"commands": [{"target": {"bundle_path": "/opt/findevil/data/cti/cti_test_bundle.json"}}]}}'
echo "--- valkey state ---"
redis-cli -h 127.0.0.1 -p 6379 hgetall pher:ip:203.0.113.250
