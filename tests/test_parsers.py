"""Parser unit tests for ingest pipeline."""

from __future__ import annotations

from findevil.ingest.events import RawEvent
from findevil.ingest.parsers import parse


def test_sysmon_process_create_extracts_sha256():
    raw = RawEvent(
        source="sysmon",
        sensor="sysmon-01",
        ts_ns=0,
        host_id="h1",
        body={
            "event_id": 1,
            "event_data": {
                "Image": "C:/Windows/System32/cmd.exe",
                "ProcessId": 1234,
                "Hashes": "SHA256=" + "a" * 64,
                "ParentImage": "C:/Windows/System32/explorer.exe",
                "CommandLine": "cmd.exe /c whoami",
            },
        },
    )
    out = parse(raw)
    assert len(out) == 1
    assert out[0].kind == "proc_create"
    assert out[0].sha256 == "a" * 64
    assert out[0].process_image == "C:/Windows/System32/cmd.exe"


def test_zeek_conn_extracts_dst_ip():
    raw = RawEvent(
        source="zeek",
        sensor="zeek-01",
        ts_ns=0,
        host_id="h1",
        body={
            "kind": "conn",
            "id.orig_h": "10.0.0.1",
            "id.resp_h": "203.0.113.5",
            "id.resp_p": 443,
            "proto": "tcp",
        },
    )
    out = parse(raw)
    assert out[0].ip == "203.0.113.5"
    assert out[0].kind == "conn"


def test_yara_strong_tag_lifts_confidence():
    raw = RawEvent(
        source="yara",
        sensor="yara-01",
        ts_ns=0,
        host_id="h1",
        body={
            "sha256": "b" * 64,
            "rule": "APT_Loader_Foo",
            "tags": ["apt", "loader"],
        },
    )
    out = parse(raw)
    assert out[0].confidence >= 0.8


def test_unknown_source_drops():
    raw = RawEvent(
        source="unknown",
        sensor="?",
        ts_ns=0,
        host_id="h1",
        body={"kind": "mystery"},
    )
    assert parse(raw) == []


def test_flat_synthetic_indicator_contract_parses_process():
    raw = RawEvent(
        source="sysmon",
        sensor="sysmon",
        event_time_ns=123,
        ingest_time_ns=456,
        host_id="host-a",
        body={
            "indicator_key": "proc://powershell-obfuscated-4521",
            "confidence": 0.78,
            "artifact_type": "process",
            "mitre_technique": "T1059.001",
            "process_name": "powershell.exe",
        },
    )

    events = parse(raw)

    assert len(events) == 1
    assert events[0].indicator_key == "proc://powershell-obfuscated-4521"
    assert events[0].pid == 4521
    assert events[0].confidence == 0.78
    assert events[0].attack_techniques == ("T1059.001",)


def test_raw_event_dual_clock_alias_keeps_legacy_ts():
    raw = RawEvent(
        source="zeek",
        sensor="zeek-01",
        ts_ns=123,
        host_id="h1",
        body={"kind": "conn"},
    )
    assert raw.timestamp_ns == 123
    raw2 = RawEvent(
        source="zeek",
        sensor="zeek-01",
        event_time_ns=456,
        ts_ns=123,
        host_id="h1",
        body={"kind": "conn"},
    )
    assert raw2.timestamp_ns == 456
