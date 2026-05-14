from __future__ import annotations

import pytest

from findevil.ingest import sinks


def test_nats_json_sink_drops_publish_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingBus:
        def __init__(self) -> None:
            self.published = 0

        async def publish(self, _subject: str, _payload: dict) -> None:
            self.published += 1
            raise TimeoutError("simulated jetstream timeout")

    bus = FailingBus()

    async def fake_get_nats() -> FailingBus:
        return bus

    monkeypatch.setattr(sinks, "get_nats", fake_get_nats)

    partition = sinks._NatsPartition("consensus.v1.finding.safe-test")
    try:
        partition.write_batch([{"finding_id": "safe-test"}, None])
    finally:
        partition.close()

    assert bus.published == 1
