# FIND EVIL — Architecture Diagram (Deliverable 3)

**Architectural pattern:** *Custom MCP Server (Approach #2)* from the Find Evil!
brief — typed, schema-validated MCP tools instead of `execute_shell_cmd`, with
server-side output parsing before anything reaches the LLM. The brief calls this
"the most sound architecture in the evaluation… also the most work." FIND EVIL
has done that work.

The single most important property: **the LLM is never in the containment
decision path.** Deterministic Dempster–Shafer fusion decides; the ledger
records; only then does the LLM explain. Hallucination cannot cause a wrong
mitigation because the LLM has no authority to mitigate.

---

## System overview

```mermaid
flowchart TB
    subgraph SIFT["SANS SIFT Workstation (local, air-gappable)"]
        direction TB

        subgraph SENSORS["Evidence sources"]
            MEM["Memory image\n(Volatility 3)"]
            DISK["Disk image\n(Sleuth Kit)"]
            NET["PCAP / Zeek / tshark"]
            YARA["YARA scans"]
            CTI["TAXII 2.1 CTI feed\n(FOR578)"]
        end

        subgraph MCP["MCP Blackboard — fastmcp 2.x (Approach #2)"]
            direction TB
            TOOLS["60 typed tool shims\nvolatility.* tsk.* yara.* zeek.*\nbulk_extractor.* taxii.* diamond.*\n(reference-resolved exhibit IDs;\nNO arbitrary shell)"]
            RES["bb:// resources\nledger/tip · ioc/* · cti/diamond"]
        end

        subgraph HOT["HOT PATH — deterministic, NO LLM"]
            direction TB
            ING["Bytewax ingest\ndual-clock, watermarks"]
            DS["Dempster–Shafer fusion\nBelief / Plausibility / conflict_K"]
            PHER["Pheromone field (Valkey)\nstigmergic suspicion state"]
            THR["Threshold evaluator\nobserve / mitigate / conflict / escalate"]
        end

        subgraph LEDGER["Forensic ledger — the deliverable"]
            LED["SQLite WAL · UUIDv7\nBLAKE3 hash chain · Ed25519\nMerkle batches → Sigstore Rekor"]
        end

        subgraph REASON["REASONING PLANE — LLM, OFF the hot path"]
            direction TB
            FRACTAL["Fractal pivot agents\ndepth≤3 width≤16\noutlines-constrained JSON"]
            NARR["Prosecutor / Defense / Judge\ndebate narrator\nZheng-2023 position-swap"]
        end

        subgraph RESP["Response & interop"]
            CACAO["CACAO 2.0 playbooks\nsafe-mode executor · JWS signed"]
            EXPORT["STIX 2.1 · OCSF 2004\nDiamond Model graph"]
            DASH["FastAPI + HTMX/SSE\nsix-pane live dashboard"]
        end
    end

    MEM & DISK & NET & YARA --> TOOLS
    CTI -->|pheromone priors| PHER
    TOOLS --> ING
    ING --> DS --> PHER --> THR
    THR -->|every decision| LED
    THR -->|consensus fires| CACAO
    LED -.read-only.-> FRACTAL
    LED -.read-only.-> NARR
    THR -->|high-interest artifact| FRACTAL
    THR -->|conflict / escalate| NARR
    FRACTAL -->|new finding| LED
    NARR -->|verdict| LED
    LED --> EXPORT
    LED --> DASH
    RES -.subscribe.-> DASH
```

---

## Guardrails: architectural vs prompt-based

The brief specifically asks submissions to **distinguish prompt-based guardrails
from architectural guardrails.** This is FIND EVIL's strongest differentiator.

```mermaid
flowchart LR
    subgraph ARCH["ARCHITECTURAL guardrails (cannot be prompted away)"]
        direction TB
        A1["Typed MCP tools only —\nno execute_shell_cmd exists.\nThe agent CAN'T run arbitrary commands."]
        A2["Reference-resolved exhibit IDs —\ntools act on registered evidence\nhandles, not free-form paths."]
        A3["LLM excluded from decision path —\nD-S math decides mitigation\nBEFORE any model is consulted."]
        A4["outlines / xgrammar FSM —\nagent output is schema-constrained\nJSON; malformed text can't parse."]
        A5["BLAKE3 + Ed25519 ledger —\nany tampering breaks the chain;\nverify is independent of the LLM."]
        A6["Citation validation —\nfabricated exhibit refs are rejected\nbefore reaching downstream."]
    end

    subgraph PROMPT["PROMPT-BASED guardrails (defense in depth, not relied upon)"]
        direction TB
        P1["Narrator role instructions\n(prosecutor / defense / judge)"]
        P2["Zheng-2023 position-swap\nto reduce ordering bias"]
        P3["System-prompt scope limits\nfor pivot agents"]
    end

    ARCH -->|"primary integrity guarantee"| TRUST["Evidence a SOC can trust"]
    PROMPT -->|"quality / readability only"| TRUST
```

**The line that matters:** if every prompt-based control failed simultaneously —
the model ignored every instruction — FIND EVIL would still produce a correct,
signed, tamper-evident decision, because the decision was never the model's to
make. Prompt guardrails here improve *explanation quality*, not *evidence
integrity*.

---

## How this maps to the 4 supported approaches

| Approach | What it is | FIND EVIL |
|---|---|---|
| #1 Prompt-only | Tell the model to be careful | rejected — not enforceable |
| **#2 Custom MCP Server** | **Typed tools, server-side parsing, ref-resolved IDs** | **this is FIND EVIL** |
| #3 Wrapper/proxy | Filter an `execute_shell_cmd` server | weaker than #2 |
| #4 Fine-tune | Train a bespoke model | out of scope for local DFIR |

## Relationship to Protocol SIFT

Protocol SIFT is a **Claude Code skill-file + permissions configuration** for a
SIFT workstation (behavioral rules, `settings.json` allow-lists, a `Stop` audit
hook). It is *prompt-and-permission* tuning of a general agent. FIND EVIL is a
**standalone Custom MCP Server** that runs **alongside** Protocol SIFT: a judge
can point any MCP-capable agent (Claude Code included) at FIND EVIL's blackboard
on `127.0.0.1:9310/mcp` and get deterministic fusion + a signed ledger that
Protocol SIFT's skill layer does not itself provide. The two are complementary —
Protocol SIFT shapes *how the agent thinks*; FIND EVIL constrains *what the
agent can do and proves what it did.* See [try-it-out.md](try-it-out.md).
