from __future__ import annotations

import pytest

from findevil.ingest import flow
from findevil.ingest.events import ParsedEvent
from findevil.swarm.ds_fusion import AgentReport


@pytest.mark.asyncio
async def test_process_window_persists_actual_sensor_diversity(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeValkey:
        def __init__(self) -> None:
            self.hset_mapping: dict[str, str] = {}
            self.sadd_values: tuple[str, ...] = ()

        async def hgetall(self, _key: str) -> dict[bytes, bytes]:
            return {}

        async def deposit(self, *_args, **_kwargs) -> float:
            return 0.9

        async def _connect(self):  # noqa: ANN202, SLF001
            return self

        async def sadd(self, _key: str, *values: str) -> None:
            self.sadd_values = values

        async def hset(self, _key: str, *, mapping: dict[str, str]) -> None:
            self.hset_mapping = mapping

    fake_vc = FakeValkey()

    async def fake_get_valkey() -> FakeValkey:
        return fake_vc

    def fake_threshold(_events):
        return {
            (None, None, "a" * 64, None): [
                AgentReport("edr/a", 0.9, 0.8, sensor="edr-a"),
                AgentReport("yara/b", 0.9, 0.8, sensor="yara-b"),
            ]
        }

    def fake_action(_reports, *, pheromone_tau: float, sensor_diversity: int):
        return {
            "action": "observe",
            "belief_evil": 0.8,
            "plausibility_evil": 0.9,
            "uncertainty": 0.1,
            "conflict_K": 0.2,
            "pheromone_tau": pheromone_tau,
            "sensor_diversity": sensor_diversity,
        }

    monkeypatch.setattr(flow, "get_valkey", fake_get_valkey)
    monkeypatch.setattr(flow, "threshold_evaluate", fake_threshold)
    monkeypatch.setattr(flow, "evaluate_action", fake_action)

    out = await flow._process_window(
        (None, None, "a" * 64, None),
        [
            ParsedEvent(
                ts_ns=1,
                source="edr",
                sensor="edr-a",
                host_id="h",
                kind="edr_event",
                sha256="a" * 64,
            )
        ],
        bus=None,
    )

    assert out is not None
    assert out["sensor_diversity"] == 2
    assert fake_vc.hset_mapping["sensor_diversity"] == "2"
    assert fake_vc.hset_mapping["sensor"] == "edr-a,yara-b"
    assert fake_vc.sadd_values == ("edr-a", "yara-b")


def test_consensus_frame_to_pivot_spawn_contract() -> None:
    frame = {
        "pher_key": "pher:hash:" + "b" * 64,
        "kind": "hash",
        "tau": 0.9,
        "sensor_diversity": 2,
        "reports": [
            {
                "agent_id": "edr/a",
                "confidence": 0.9,
                "sensor": "edr-a",
                "attack_techniques": ["T1059.001"],
            }
        ],
        "action": "conflict_ledger",
        "belief_evil": 0.7,
        "plausibility_evil": 0.9,
        "uncertainty": 0.2,
        "conflict_K": 0.5,
    }

    spawn = flow.consensus_frame_to_pivot_spawn(frame)

    assert spawn["spawn_id"]
    assert spawn["seed_technique"] == "T1059.001"
    assert spawn["depth"] == 0
    assert "Parent pheromone: pher:hash:" in spawn["scoped_prompt"]
    assert any(e["exhibit_kind"] == "consensus_frame" for e in spawn["exhibits"])


def test_architecture_indicator_schemes_keep_native_pheromone_keys() -> None:
    assert flow._pher_key_for((None, None, None, "__raw__:user://CORP\\jsmith")) == (
        "pher:user://CORP\\jsmith"
    )
    assert flow._pher_key_for((None, None, None, "__raw__:reg://HKCU\\Run\\evil")) == (
        "pher:reg://HKCU\\Run\\evil"
    )
    assert flow._pher_key_for((None, None, None, "__raw__:task://\\Microsoft\\evil")) == (
        "pher:task://\\Microsoft\\evil"
    )
