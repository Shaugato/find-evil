"""Tool registry bootstrap + lookup sanity."""

from __future__ import annotations

from findevil.tools.registry import bootstrap, registered, resolve


def test_bootstrap_registers_known_tools():
    bootstrap()
    names = set(registered())
    # A stable subset (every Appendix C entry we implemented)
    required = {
        "yara.scan",
        "yara.quarantine_file",
        "yara.block_hash",
        "zeek.query",
        "zeek.x509_extract",
        "suricata.query",
        "rita.analyze",
        "volatility.malfind",
        "volatility.ldrmodules",
        "volatility.hollowfind",
        "volatility.handles",
        "pescan.static",
        "capa.analyze",
        "floss.extract",
        "ole.analyze",
        "regripper.run",
        "evtxecmd.parse",
        "mftecmd.parse",
        "memprocfs.mount",
        "edr.kill_process",
        "edr.network_isolate",
        "edr.block_domain",
        "edr.block_url",
        "edr.sinkhole",
        "edr.snapshot_disk",
        "edr.remove_persistence",
        "edr.delete_scheduled_task",
        "edr.reenable_defender",
        "iam.disable_account",
        "iam.force_reset",
        "ledger.verify",
        "ledger.recent",
        "ledger.tip",
        "stix.bundle",
        "ocsf.finding",
        "findevil.end",
        "analyst.review",
    }
    missing = required - names
    assert not missing, f"missing tools: {missing}"


def test_resolve_returns_callable():
    r = resolve("findevil.end")
    assert callable(r)
