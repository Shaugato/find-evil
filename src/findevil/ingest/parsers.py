"""Source-specific parsers → ParsedEvent (blueprint Part 8.3).

Each function takes a RawEvent and returns zero or more ParsedEvent. Parsers are
conservative: unknown/malformed records drop silently and increment a metric — we
never let a parser kill the stream.
"""

from __future__ import annotations

import re
from typing import Iterable

from .events import ParsedEvent, RawEvent

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MITRE_RE = re.compile(r"^T\d{4}(?:\.\d{3})?$")


def _safe_str(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _ts(raw: RawEvent) -> int:
    return int(raw.timestamp_ns or 0)


def _techniques(*values) -> tuple[str, ...]:
    out: list[str] = []
    for value in values:
        if value is None:
            continue
        items = value if isinstance(value, (list, tuple, set)) else [value]
        for item in items:
            s = str(item).strip()
            if _MITRE_RE.match(s) and s not in out:
                out.append(s)
    return tuple(out)


def _indicator_parts(indicator_key: str | None) -> dict:
    """Decode the flat synthetic indicator URI contract into ParsedEvent fields."""
    if not indicator_key:
        return {}
    key = indicator_key.strip()
    if key.startswith("ipv4-addr://"):
        return {"ip": key.removeprefix("ipv4-addr://")}
    if key.startswith("domain://"):
        return {"domain": key.removeprefix("domain://")}
    if key.startswith("domain-name://"):
        return {"domain": key.removeprefix("domain-name://")}
    if key.startswith("hash://sha256:"):
        sha = key.removeprefix("hash://sha256:").lower()
        return {"sha256": sha if _SHA256_RE.match(sha) else None}
    if key.startswith("sha256://"):
        sha = key.removeprefix("sha256://").lower()
        return {"sha256": sha if _SHA256_RE.match(sha) else None}
    if key.startswith("proc://"):
        proc = key.removeprefix("proc://")
        # Keep the opaque process key for ledger/UI fidelity, and best-effort
        # extract a PID for tools that can use one.
        m = re.search(r"(\d+)(?!.*\d)", proc)
        return {"pid": int(m.group(1)) if m else None}
    return {}


def parse_flat_synthetic(raw: RawEvent) -> Iterable[ParsedEvent]:
    """Parse safe local validation JSON published directly to find.<sensor>.

    The implementation guide's internal producers wrap source records in
    RawEvent.body. The white-hat validation runbook also publishes flat JSON
    with source, event_time_ns, indicator_key, confidence, and artifact_type.
    Treat that as a first-class input contract so validation exercises the live
    pipeline instead of a separate harness.
    """
    b = raw.body
    indicator_key = _safe_str(b.get("indicator_key"))
    if indicator_key is None:
        return []
    parts = _indicator_parts(indicator_key)
    conf = float(b.get("confidence", 0.0))
    conf = max(0.0, min(1.0, conf))
    kind = _safe_str(b.get("event_type")) or _safe_str(b.get("artifact_type")) or "synthetic"
    yield ParsedEvent(
        ts_ns=_ts(raw),
        ingest_time_ns=raw.ingest_time_ns,
        source=raw.source,
        sensor=raw.sensor,
        host_id=raw.host_id,
        kind=kind,
        indicator_key=indicator_key,
        ip=parts.get("ip"),
        domain=parts.get("domain"),
        sha256=parts.get("sha256"),
        pid=parts.get("pid"),
        process_image=_safe_str(b.get("process_name") or b.get("image")),
        confidence=conf,
        attack_techniques=_techniques(b.get("mitre_technique"), b.get("techniques")),
        attrs={k: v for k, v in b.items() if k not in {"source", "event_time_ns", "ingest_time_ns"}},
    )


def parse_zeek_conn(raw: RawEvent) -> Iterable[ParsedEvent]:
    b = raw.body
    ip = _safe_str(b.get("id.resp_h") or b.get("dest_ip") or b.get("dst"))
    yield ParsedEvent(
        ts_ns=_ts(raw),
        ingest_time_ns=raw.ingest_time_ns,
        source="zeek",
        sensor=raw.sensor,
        host_id=raw.host_id,
        kind="conn",
        ip=ip,
        attrs={
            "src": b.get("id.orig_h"),
            "port": b.get("id.resp_p"),
            "proto": b.get("proto"),
            "duration": b.get("duration"),
            "orig_bytes": b.get("orig_bytes"),
            "resp_bytes": b.get("resp_bytes"),
        },
        confidence=0.05,  # a conn alone barely moves the needle
    )


def parse_zeek_dns(raw: RawEvent) -> Iterable[ParsedEvent]:
    b = raw.body
    dom = _safe_str(b.get("query") or b.get("answer"))
    yield ParsedEvent(
        ts_ns=_ts(raw),
        ingest_time_ns=raw.ingest_time_ns,
        source="zeek",
        sensor=raw.sensor,
        host_id=raw.host_id,
        kind="dns",
        domain=dom,
        attrs={"qtype": b.get("qtype"), "answers": b.get("answers")},
        confidence=0.05,
    )


def parse_zeek_ssl(raw: RawEvent) -> Iterable[ParsedEvent]:
    b = raw.body
    yield ParsedEvent(
        ts_ns=_ts(raw),
        ingest_time_ns=raw.ingest_time_ns,
        source="zeek",
        sensor=raw.sensor,
        host_id=raw.host_id,
        kind="ssl",
        ip=_safe_str(b.get("id.resp_h")),
        attrs={
            "server_name": b.get("server_name"),
            "issuer": b.get("issuer"),
            "validation_status": b.get("validation_status"),
            "ja3": b.get("ja3"),
            "ja3s": b.get("ja3s"),
        },
        confidence=0.1 if b.get("validation_status") not in (None, "ok") else 0.05,
    )


def parse_suricata_alert(raw: RawEvent) -> Iterable[ParsedEvent]:
    b = raw.body
    alert = b.get("alert", {}) if isinstance(b.get("alert"), dict) else {}
    sev = alert.get("severity", 3)
    # Suricata severity: 1 high -> 4 informational. Map inverse to 0..1.
    conf = {1: 0.85, 2: 0.55, 3: 0.3, 4: 0.1}.get(int(sev), 0.3)
    yield ParsedEvent(
        ts_ns=_ts(raw),
        ingest_time_ns=raw.ingest_time_ns,
        source="suricata",
        sensor=raw.sensor,
        host_id=raw.host_id,
        kind="alert",
        ip=_safe_str(b.get("dest_ip")),
        attrs={
            "signature_id": alert.get("signature_id"),
            "signature": alert.get("signature"),
            "category": alert.get("category"),
            "severity": sev,
        },
        confidence=conf,
    )


def parse_sysmon(raw: RawEvent) -> Iterable[ParsedEvent]:
    b = raw.body
    eid = int(b.get("event_id") or b.get("EventID") or 0)
    data = b.get("event_data", {}) if isinstance(b.get("event_data"), dict) else b
    img = _safe_str(data.get("Image"))
    pid = data.get("ProcessId")
    try:
        pid_i = int(pid) if pid is not None else None
    except (ValueError, TypeError):
        pid_i = None

    if eid == 1:  # process create
        hashes = _safe_str(data.get("Hashes")) or ""
        sha = None
        for frag in hashes.split(","):
            frag = frag.strip()
            if frag.startswith("SHA256="):
                cand = frag[len("SHA256=") :].lower()
                if _SHA256_RE.match(cand):
                    sha = cand
        yield ParsedEvent(
            ts_ns=_ts(raw),
            ingest_time_ns=raw.ingest_time_ns,
            source="sysmon",
            sensor=raw.sensor,
            host_id=raw.host_id,
            kind="proc_create",
            pid=pid_i,
            process_image=img,
            sha256=sha,
            attrs={
                "parent_image": data.get("ParentImage"),
                "command_line": data.get("CommandLine"),
                "user": data.get("User"),
            },
            confidence=0.25,
        )
    elif eid == 11:  # file created
        yield ParsedEvent(
            ts_ns=_ts(raw),
            ingest_time_ns=raw.ingest_time_ns,
            source="sysmon",
            sensor=raw.sensor,
            host_id=raw.host_id,
            kind="file_create",
            pid=pid_i,
            process_image=img,
            attrs={"target_filename": data.get("TargetFilename")},
            confidence=0.1,
        )
    elif eid in (12, 13, 14):  # reg create / set / rename
        yield ParsedEvent(
            ts_ns=_ts(raw),
            ingest_time_ns=raw.ingest_time_ns,
            source="sysmon",
            sensor=raw.sensor,
            host_id=raw.host_id,
            kind="reg_set",
            pid=pid_i,
            process_image=img,
            registry_key=_safe_str(data.get("TargetObject")),
            attrs={"details": data.get("Details"), "event_id": eid},
            confidence=0.2,
        )
    elif eid == 3:  # network connect
        yield ParsedEvent(
            ts_ns=_ts(raw),
            ingest_time_ns=raw.ingest_time_ns,
            source="sysmon",
            sensor=raw.sensor,
            host_id=raw.host_id,
            kind="proc_net",
            pid=pid_i,
            process_image=img,
            ip=_safe_str(data.get("DestinationIp")),
            attrs={
                "dest_port": data.get("DestinationPort"),
                "dest_hostname": data.get("DestinationHostname"),
            },
            confidence=0.15,
        )


def parse_yara(raw: RawEvent) -> Iterable[ParsedEvent]:
    b = raw.body
    sha = _safe_str(b.get("sha256"))
    if sha is not None:
        sha = sha.lower()
        if not _SHA256_RE.match(sha):
            sha = None
    rule = _safe_str(b.get("rule")) or ""
    # YARA hits have a tag that hints severity (apt, ransomware, trojan...)
    tags = tuple(b.get("tags", []))
    strong_tags = {"apt", "ransomware", "trojan", "implant", "loader", "stealer"}
    conf = 0.85 if any(t.lower() in strong_tags for t in tags) else 0.55
    yield ParsedEvent(
        ts_ns=_ts(raw),
        ingest_time_ns=raw.ingest_time_ns,
        source="yara",
        sensor=raw.sensor,
        host_id=raw.host_id,
        kind="yara_hit",
        sha256=sha,
        attrs={"rule": rule, "tags": list(tags), "namespace": b.get("namespace")},
        confidence=conf,
    )


def parse_edr(raw: RawEvent) -> Iterable[ParsedEvent]:
    """Generic EDR event — a telemetry stream-of-events with verdicts.

    Expected envelope {verdict, score, indicators:{ip,sha256,...}, techniques:[...]}.
    """
    b = raw.body
    inds = b.get("indicators", {}) or {}
    sha = _safe_str(inds.get("sha256"))
    if sha is not None:
        sha = sha.lower()
        if not _SHA256_RE.match(sha):
            sha = None
    score = float(b.get("score", 0.2))
    yield ParsedEvent(
        ts_ns=_ts(raw),
        ingest_time_ns=raw.ingest_time_ns,
        source="edr",
        sensor=raw.sensor,
        host_id=raw.host_id,
        kind=_safe_str(b.get("kind")) or "edr_event",
        ip=_safe_str(inds.get("ip")),
        domain=_safe_str(inds.get("domain")),
        sha256=sha,
        pid=inds.get("pid"),
        process_image=_safe_str(inds.get("image")),
        attack_techniques=tuple(b.get("techniques", [])),
        attrs={"verdict": b.get("verdict"), "raw_score": score},
        confidence=max(0.0, min(1.0, score)),
    )


PARSER_TABLE = {
    ("zeek", "conn"): parse_zeek_conn,
    ("zeek", "dns"): parse_zeek_dns,
    ("zeek", "ssl"): parse_zeek_ssl,
    ("suricata", "alert"): parse_suricata_alert,
    ("sysmon", ""): parse_sysmon,
    ("yara", ""): parse_yara,
    ("edr", ""): parse_edr,
}


def parse(raw: RawEvent) -> list[ParsedEvent]:
    if isinstance(raw.body, dict) and raw.body.get("indicator_key"):
        try:
            return list(parse_flat_synthetic(raw))
        except Exception:
            return []
    kind = raw.body.get("kind") if isinstance(raw.body, dict) else None
    fn = PARSER_TABLE.get((raw.source, kind or "")) or PARSER_TABLE.get(
        (raw.source, "")
    )
    if fn is None:
        return []
    try:
        return list(fn(raw))
    except Exception:
        return []
