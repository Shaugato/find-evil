from __future__ import annotations

import pytest

from findevil.ingest import flow
from findevil.ingest.events import RawEvent


def _raw(event_id: str | None) -> RawEvent:
    return RawEvent(
        source="sysmon",
        sensor="sysmon-lab",
        event_time_ns=123,
        ingest_time_ns=456,
        host_id="host-a",
        body={"event_id": event_id} if event_id else {},
    )


def test_raw_event_id_ignores_event_type_fields() -> None:
    raw = RawEvent(
        source="sysmon",
        sensor="sysmon-lab",
        event_time_ns=123,
        host_id="host-a",
        body={"EventID": 1, "event_guid": "{abc}"},
    )

    assert flow.raw_event_id(raw) == "{abc}"


@pytest.mark.asyncio
async def test_dedupes_same_event_id_within_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int | None, bool | None]] = []
    seen: set[str] = set()

    class FakeConn:
        async def set(self, key: str, value: bytes, *, ex: int | None, nx: bool | None):
            calls.append((key, ex, nx))
            if key in seen:
                return None
            seen.add(key)
            return True

    class FakeValkey:
        async def _connect(self):  # noqa: ANN202, SLF001
            return FakeConn()

    async def fake_get_valkey() -> FakeValkey:
        return FakeValkey()

    monkeypatch.setattr(flow, "get_valkey", fake_get_valkey)

    raw = _raw("evt-1")
    assert await flow.is_duplicate_raw_event(raw, ttl_s=300) is False
    assert await flow.is_duplicate_raw_event(raw, ttl_s=300) is True
    assert calls[0][1:] == (300, True)


@pytest.mark.asyncio
async def test_replay_after_ttl_window_can_be_processed_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeConn:
        async def set(self, _key: str, _value: bytes, *, ex: int | None, nx: bool | None):
            assert ex == 1
            assert nx is True
            return True

    class FakeValkey:
        async def _connect(self):  # noqa: ANN202, SLF001
            return FakeConn()

    async def fake_get_valkey() -> FakeValkey:
        return FakeValkey()

    monkeypatch.setattr(flow, "get_valkey", fake_get_valkey)

    assert await flow.is_duplicate_raw_event(_raw("evt-1"), ttl_s=1) is False
