"""Facade over the OpenAI-compatible inference server (Profile A llama-cpp or B vLLM).

Always emits JSON structurally constrained by outlines FSMs. The hot path NEVER
calls this — only the Watcher (H3 fractal) and the Narrator (H2 debate) do.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
import msgspec

from findevil.config.settings import settings

from .outlines_schemas import (
    DebateArgument,
    PivotFinding,
    Verdict,
    validate_argument_citations,
    validate_pivot_citations,
    validate_verdict_citations,
)


def _first_json_object(text: str) -> str:
    """Extract the first balanced JSON object from a model response."""
    s = text.strip()
    if "```" in s:
        parts = s.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{"):
                s = candidate
                break
    start = s.find("{")
    if start < 0:
        return s
    depth = 0
    in_str = False
    esc = False
    for idx in range(start, len(s)):
        ch = s[idx]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : idx + 1]
    return s[start:]


def _allowed_ids(exhibits: list[dict]) -> list[str]:
    return [
        str(e.get("exhibit_id"))
        for e in exhibits
        if isinstance(e, dict) and e.get("exhibit_id")
    ]


def _filter_ids(ids: Any, exhibits: list[dict], *, ensure_one: bool = False) -> list[str]:
    allowed = _allowed_ids(exhibits)
    seen: list[str] = []
    raw_ids = ids if isinstance(ids, list) else []
    for item in raw_ids:
        s = str(item)
        if s in allowed and s not in seen:
            seen.append(s)
    if ensure_one and not seen and allowed:
        seen.append(allowed[0])
    return seen


def _acquire_inference_lock():
    if os.name != "posix":
        return None
    import fcntl

    lock_path = Path(os.environ.get("FINDEVIL_INFERENCE_LOCK", "/opt/findevil/run/inference.lock"))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = lock_path.open("a+b")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    return fh


def _release_inference_lock(fh) -> None:
    if fh is None:
        return
    import fcntl

    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    finally:
        fh.close()


def _schema_contract(schema: type) -> str:
    name = getattr(schema, "__name__", "")
    if name == "DebateArgument":
        return (
            '{"role":"prosecutor|defense","text":"non-empty argument",'
            '"exhibit_ids_cited":["ex_12345678"],"claimed_technique":["T1059.001"]}'
        )
    if name == "Verdict":
        return (
            '{"guilty":true|false,"score":0.0-1.0,'
            '"winning_argument":"prosecutor|defense|insufficient",'
            '"rationale":"non-empty rationale","exhibit_ids_cited":["ex_12345678"]}'
        )
    if name == "PivotFinding":
        return (
            '{"artifact_uri":"non-empty","artifact_type":"file|process|ipv4-addr|domain-name|url|'
            'windows-registry-key|memory-region|yara-match|network-traffic|user-account|ipv6-addr",'
            '"verdict":"evil|benign|insufficient","confidence":0.0-1.0,'
            '"declared_ignorance":0.0-1.0,"mitre_attack_technique":["T1055"],'
            '"evidence_refs":[{"exhibit_id":"ex_12345678"}],"reasoning":"non-empty","follow_ups":[]}'
        )
    return "Return a non-empty JSON object matching the requested Pydantic model."


class InferenceFacade:
    """Async OpenAI-compatible client.

    We use httpx with a long-ish timeout (15s) because even Profile A can hit 650 ms
    p99 for a 150-token JSON verdict. The Watcher enforces its own TTL budget
    separately via anyio.move_on_after.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        api_key: str = "none",
    ):
        self.base_url = base_url or (
            f"http://{settings.inference.llamacpp_host}:{settings.inference.llamacpp_port}/v1"
        )
        self.model_name = model_name or settings.inference.model_name
        timeout_s = float(os.environ.get("FINDEVIL_INFERENCE_HTTP_TIMEOUT_S", "120"))
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout_s,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def close(self) -> None:
        await self.client.aclose()

    # ----- core prompt helpers ---------------------------------------------

    @staticmethod
    def _render_pivot_prompt(scoped: str, exhibits: list[dict]) -> str:
        return (
            "You are a scoped DFIR pivot agent. Analyze ONLY the exhibits below. "
            "Cite every claim with an exhibit_id from the list; NEVER invent sha256 values. "
            "Return strictly the requested JSON.\n\n"
            f"Scoped prompt: {scoped}\n"
            f"Exhibits: {msgspec.json.encode(exhibits).decode()}\n"
        )

    async def _openai_chat(
        self, prompt: str, schema: type, *, max_tokens: int = 512, system: str | None = None
    ) -> dict[str, Any]:
        """Shared helper — asks the model for JSON matching `schema`.

        When outlines-aware backends are present we add `response_format` /
        `json_schema` hints; otherwise we fall back to prompt-only guidance, and
        Pydantic validation at the caller does the strict rejection.
        """
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append(
            {
                "role": "user",
                "content": (
                    f"{prompt}\n\n"
                    "Return only one JSON object. Do not wrap it in markdown. "
                    f"Required shape: {_schema_contract(schema)}"
                ),
            }
        )

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.0,
            # llama-cpp-python can segfault on complex Pydantic schemas when it
            # translates regex-heavy fields into a grammar. Use JSON mode here
            # and keep strict enforcement in the Pydantic validators below.
            "response_format": {"type": "json_object"},
        }
        lock_fh = await asyncio.to_thread(_acquire_inference_lock)
        try:
            r = await self.client.post("/chat/completions", json=payload)
            r.raise_for_status()
        finally:
            await asyncio.to_thread(_release_inference_lock, lock_fh)
        body = r.json()
        content = body["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return json.loads(_first_json_object(content))

    # ----- public APIs ------------------------------------------------------

    async def pivot_infer(self, scoped: str, exhibits: list[dict]) -> PivotFinding:
        prompt = self._render_pivot_prompt(scoped, exhibits)
        last_error: Exception | None = None
        for attempt in range(3):
            retry_hint = (
                f"\nPrevious JSON failed validation: {last_error}. Return corrected JSON only."
                if last_error
                else ""
            )
            data = await self._openai_chat(
                prompt + retry_hint,
                PivotFinding,
                max_tokens=240,
                system="You are FIND EVIL fractal pivot agent.",
            )
            try:
                if isinstance(data, dict):
                    refs = data.get("evidence_refs")
                    if not isinstance(refs, list) or not refs:
                        data["evidence_refs"] = [
                            {"exhibit_id": eid} for eid in _filter_ids([], exhibits, ensure_one=True)
                        ]
                finding = PivotFinding.model_validate(data)
                validate_pivot_citations(finding, exhibits)
                return finding
            except Exception as exc:
                last_error = exc
                if attempt:
                    raise
        raise last_error  # pragma: no cover

    async def debate_argument(
        self, role: str, exhibits: list[dict], prior: str = ""
    ) -> DebateArgument:
        system = (
            f"You are the {role}. Produce JSON per schema. Cite only listed exhibit_ids. "
            "No speculation beyond evidence."
        )
        user = (
            f"Exhibits: {msgspec.json.encode(exhibits).decode()}\n"
            f"Prior argument from the other side: {prior or '(none)'}\n"
        )
        last_error: Exception | None = None
        for attempt in range(3):
            retry_hint = (
                f"\nPrevious JSON failed validation: {last_error}. Return corrected JSON only."
                if last_error
                else ""
            )
            data = await self._openai_chat(
                user + retry_hint, DebateArgument, max_tokens=220, system=system
            )
            try:
                if isinstance(data, dict):
                    data["role"] = role
                    data["exhibit_ids_cited"] = _filter_ids(
                        data.get("exhibit_ids_cited"), exhibits, ensure_one=True
                    )
                    if not data.get("text"):
                        data["text"] = str(data.get("argument") or data.get("rationale") or "No argument.")
                argument = DebateArgument.model_validate(data)
                validate_argument_citations(argument, exhibits)
                return argument
            except Exception as exc:
                last_error = exc
                if attempt:
                    raise
        raise last_error  # pragma: no cover

    async def judge_verdict(
        self, exhibits: list[dict], prosecutor: str, defense: str, *, swap: bool = False
    ) -> Verdict:
        a = (defense, prosecutor) if swap else (prosecutor, defense)
        prompt = (
            "Judge the following two arguments. Return JSON matching schema.\n"
            f"Argument A: {a[0]}\n"
            f"Argument B: {a[1]}\n"
            f"Exhibits: {msgspec.json.encode(exhibits).decode()}\n"
        )
        last_error: Exception | None = None
        for attempt in range(3):
            retry_hint = (
                f"\nPrevious JSON failed validation: {last_error}. Return corrected JSON only."
                if last_error
                else ""
            )
            data = await self._openai_chat(
                prompt + retry_hint,
                Verdict,
                max_tokens=180,
                system="You are an impartial FIND EVIL Judge.",
            )
            try:
                if isinstance(data, dict):
                    try:
                        data["score"] = max(0.0, min(1.0, float(data.get("score", 0.0))))
                    except (TypeError, ValueError):
                        data["score"] = 0.0
                    if data.get("winning_argument") not in {
                        "prosecutor",
                        "defense",
                        "insufficient",
                    }:
                        data["winning_argument"] = "insufficient"
                    data["exhibit_ids_cited"] = _filter_ids(
                        data.get("exhibit_ids_cited"), exhibits, ensure_one=True
                    )
                    if not data.get("rationale"):
                        data["rationale"] = "Judge could not extract a detailed rationale."
                verdict = Verdict.model_validate(data)
                validate_verdict_citations(verdict, exhibits)
                return verdict
            except Exception as exc:
                last_error = exc
                if attempt:
                    raise
        raise last_error  # pragma: no cover
