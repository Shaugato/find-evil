#!/usr/bin/env bash
echo "=== NATS streams + subjects ==="
/opt/findevil/venv/bin/python - <<'PY'
import asyncio, nats
async def main():
    nc = await nats.connect("nats://127.0.0.1:4222", user="findevil_writer", password="change-me")
    js = nc.jetstream(domain="findevil")
    try:
        infos = await js.streams_info()
        for s in infos:
            print("STREAM", s.config.name, "subjects=", s.config.subjects, "msgs=", s.state.messages)
    except Exception as e:
        print("streams_info err:", e)
    await nc.drain()
asyncio.run(main())
PY
echo "=== publish a test event to find.raw.rocba.case and recount ==="
/opt/findevil/venv/bin/python - <<'PY'
import asyncio, json, time, nats
async def main():
    nc = await nats.connect("nats://127.0.0.1:4222", user="findevil_writer", password="change-me")
    js = nc.jetstream(domain="findevil")
    ack = await js.publish("find.raw.rocba.case", json.dumps({"source":"edr","sensor":"diag","event_time_ns":time.time_ns(),"ingest_time_ns":0,"host_id":"diag","body":{"kind":"behavior","verdict":"malicious","score":0.95,"techniques":["T1059.001"],"indicators":{"ip":"203.0.113.99"}}}).encode())
    print("publish ack stream/seq:", ack.stream, ack.seq)
    await nc.drain()
asyncio.run(main())
PY
echo "=== bytewax: is it consuming? (process + any log file) ==="
systemctl is-active findevil-bytewax
ls -la /opt/findevil/logs/ 2>/dev/null | grep -iE 'bytewax|ingest' || echo "(no bytewax log file)"
journalctl -u findevil-bytewax -n 15 --no-pager 2>&1 | tail -15
echo "=== unit ExecStart ==="
grep ExecStart /etc/systemd/system/findevil-bytewax.service
