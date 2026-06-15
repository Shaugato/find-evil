# Stigmergy — Demo Video Script (Deliverable 2)

> **▶ Final video (published, ≤5 min): https://youtu.be/4xOz7jFWh9s**
> Live ROCBA carve on the real 18 GB memory image → a real self-correction
> (Yager conflict → signed verdict) → the MCP typed-tool guardrail → the
> dashboard. The script below is the production reference used to record it.

## Pre-flight (before recording — do NOT film this)

```bash
# everything green and the ledger clean
bash scripts/preflight.sh                 # services active, verify ok=true
# carve output already present from the real run:
ls /opt/findevil/data/cases/rocba/be_out/run1/   # ip.txt domain.txt ...
# dashboard open in a browser tab at http://127.0.0.1:9400
```

Have two windows ready: a **terminal** and the **dashboard browser tab**.

---

## Scene 1 — The thesis (0:00–0:35)

**On screen:** the architecture diagram ([architecture-diagram.md](architecture-diagram.md)) or the website hero.

**Narration:**
> "AI attacks now move 47 times faster than human responders. The obvious fix —
> point an LLM agent at 200 forensic tools — has a fatal flaw: it hallucinates.
> Stigmergy solves that architecturally. Math decides, a signed ledger records,
> and the LLM only explains *after the fact*. A hallucination can't cause a
> wrong containment, because the model was never in the decision path."

## Scene 2 — The guardrail that matters (0:35–1:15)

**On screen:** terminal.

```bash
python scripts/mcp_probe.py volatility.version yara.version bulk_extractor.version
```

**Expected:** three `ok:true` version strings.

**Narration:**
> "This is a Custom MCP Server — Approach #2 in the brief. Sixty *typed* tools.
> There is no `execute_shell_cmd`. The agent literally cannot run an arbitrary
> command; it can only call schema-validated forensic tools on reference-resolved
> evidence. That's an architectural guardrail, not a prompt that says 'please be
> careful.'"

## Scene 3 — Real data in (1:15–2:30)

**On screen:** terminal.

```bash
# the official SANS ROCBA memory image; carving recovered real indicators
python scripts/real_data_carve_run.py \
    --be-dir /opt/findevil/data/cases/rocba/be_out/run1 \
    --export docs/hackathon/execution-logs/rocba_carve_run.json
```

**Expected:** prints carved public IPs + domains, "publishing N real-indicator
events", then "new ledger rows: N".

**Narration:**
> "Here's the official hackathon ROCBA memory image. The download had a corrupt
> block that broke Volatility's kernel parsing — so we used bulk_extractor, which
> carves indicators from raw bytes and doesn't care about corruption. These are
> *real* IPs and domains out of the real image. Watch them flow through live
> Dempster–Shafer fusion into the signed ledger."

## Scene 4 — The self-correction (2:30–3:40)

**On screen:** split — terminal output + dashboard ledger pane updating.

**Narration:**
> "Now the part that matters for trust. We feed conflicting evidence on one real
> IP — one sensor screams malicious, another says benign. The deterministic
> engine detects the Yager conflict and *refuses to auto-mitigate* — it routes to
> the prosecutor/defense/judge narrator instead. The judge weighs both sides,
> with a position-swap to cancel ordering bias, and writes a reasoned verdict to
> the ledger. The system corrected its own first impression — and every step is
> signed."

**On screen:** point to the highlighted conflict → narrator verdict entries.

## Scene 5 — Prove it wasn't tampered (3:40–4:20)

**On screen:** terminal.

```bash
findevil verify
```

**Expected:** `{"ok": true, "tainted_seqs": []}`

**Narration:**
> "Every decision — the real-data findings, the conflict, the narrator's verdict —
> is in a BLAKE3 hash chain with Ed25519 signatures, Merkle-anchored to Sigstore
> Rekor. One command re-verifies the entire chain. If anything had been altered,
> this would name the tainted entry. It's clean."

## Scene 6 — Close (4:20–4:50)

**On screen:** dashboard six panes live; then the GitHub repo + website URL.

**Narration:**
> "Local, defensive, reproducible. The hot path runs in under a millisecond with
> no LLM. The evidence is cryptographically provable. And the agent's
> hallucinations are structurally inert. That's Stigmergy — find evil at machine
> speed, and prove it."

---

## Shot list / asset checklist for the editor

| # | Shot | Source |
|---|---|---|
| 1 | Architecture diagram | `docs/hackathon/architecture-diagram.md` rendered, or website hero |
| 2 | `mcp_probe` output | terminal |
| 3 | `real_data_carve_run.py` output | terminal |
| 4 | Dashboard ledger + MITRE panes updating | browser `:9400` |
| 5 | Conflict → narrator verdict | `docs/hackathon/execution-logs/` + dashboard |
| 6 | `findevil verify` → ok=true | terminal |
| 7 | Repo + live website URL | browser |

**Tip:** if Scene 4's narrator step is slow (CPU inference, ~seconds per turn),
pre-run it once so the verdict is already in the ledger, then *show* the ledger
entry rather than waiting live. The execution-log JSON has the exact seqs to
scroll to.
