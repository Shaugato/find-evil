"""Find the most recent cacao_executed ledger entry and show its signature fpr."""
import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:9400/api/ledger/recent?n=80", timeout=10) as r:
    rows = json.loads(r.read())

found = None
for row in rows:
    e = row.get("entry") or {}
    if e.get("agent_id", "").startswith("cacao") or "cacao" in str(e.get("primary_artifact_key", "")):
        found = row
        break
    for ref in e.get("evidence_refs", []) or []:
        extra = ref.get("extra") or {}
        if "signature_fpr" in extra and "playbook_id" in extra:
            found = row
            break
    if found:
        break

if not found:
    print("NO cacao_executed entry found in recent 80")
    raise SystemExit(1)

e = found["entry"]
ref0 = (e.get("evidence_refs") or [{}])[0]
extra = ref0.get("extra") or {}
print(f"seq={found['seq']} agent={e.get('agent_id')} severity={e.get('severity')}")
print(f"artifact={e.get('primary_artifact_key')}")
print(f"playbook_id={extra.get('playbook_id')}")
print(f"signature_fpr={extra.get('signature_fpr')}")
print(f"status={extra.get('status')} steps_ran={str(extra.get('steps_ran'))[:80]}")
signed = bool(extra.get("signature_fpr")) and extra.get("signature_fpr") != "0" * 64
print(f"=== CACAO playbook signed+executed: {'PASS' if signed else 'UNSIGNED'} ===")
raise SystemExit(0 if signed else 1)
