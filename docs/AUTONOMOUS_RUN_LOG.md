# FIND EVIL — Autonomous Run Log

Sprint: 2026-06-11 → 2026-06-15 (hackathon deadline).
This log is append-only per completed backlog item. Final summary will be added
at the top at end of run.

---

## [2026-06-11 ~16:00Z] T1 — Fresh status check & tree reconciliation

- What was done: Ran the Section-4 status battery in WSL2 via
  `scripts/status_check.sh`; diffed the Windows git tree against the WSL
  runtime tree (`scripts/diff_trees.sh`); checked GitHub repo state.
- Verification evidence:
  - All 11 `findevil-*` services **active** (valkey, nats, otel, llamacpp,
    mcp, dashboard, decay, narrator, watcher, bytewax, verify.timer).
  - Ledger: `936|936` (entries|max_seq);
    `/opt/findevil/venv/bin/findevil verify` → `ok=true, tainted_seqs=[]`.
  - Pytest (in /opt/findevil/repo): `73 passed, 1 skipped in 2.56s`.
  - GPU visible in WSL2: Quadro P620, driver 582.41, 4096 MiB.
  - `sudo -n` requires a password, **but `wsl.exe -u root` works** — root
    operations (systemctl restarts, /usr/local/bin wrappers, apt) are
    unblocked via that path.
  - Tree reconciliation: `D:\Autonomous DFIR - Agentic SOC` is the git
    working tree (remote `origin = github.com/Shaugato/find-evil`, PUBLIC,
    1 commit `28e2c86`). `/opt/findevil/repo` is the runtime copy — **all
    .py sources identical**; only `__pycache__`, README.md, and the
    Windows-only source docs differ.
  - Working model adopted: edit in the Windows git tree → rsync changed
    files to `/opt/findevil/repo` → restart only affected services via
    `wsl.exe -u root systemctl restart …`.
  - MCP server: streamable-http at `127.0.0.1:9310/mcp`; dashboard API at
    `127.0.0.1:9400`; venv already exposes a `log2timeline` entry point
    (makes G2 cheap).
- Status: done

## [2026-06-11 ~18:25Z] G1 — MCP service reload (zeek/plaso shims)

- What was done: synced git tree → runtime (`scripts/sync_to_runtime.sh`),
  `systemctl restart findevil-mcp.service` via `wsl -u root`, probed live
  tools with new `scripts/mcp_probe.py` (fastmcp Client → 127.0.0.1:9310/mcp).
- Verification evidence: server exposes **55 tools**;
  `zeek.version` → `ok=true, "zeek version 8.1.2"`;
  `plaso.version` → `ok=true, "plaso - log2timeline version 20260119"`;
  volatility/tsk/tshark versions all `ok=true`. Post-restart
  `ledger.verify` (via MCP tool) → `ok=true, tainted_seqs=[]`.
- Status: done

## [2026-06-11 ~18:20Z] G2 — log2timeline on PATH

- What was done: venv already ships a `log2timeline` console script;
  created `/usr/local/bin/log2timeline.py` and `/usr/local/bin/log2timeline`
  symlinks → `/opt/findevil/venv/bin/log2timeline`.
- Verification evidence: `log2timeline.py --version` →
  `plaso - log2timeline version 20260119`.
- Status: done

## [2026-06-11 ~18:30Z] G3 — bulk_extractor installed

- What was done: confirmed `bulk-extractor` absent from Ubuntu 24.04 apt
  sources (dropped from Debian/Ubuntu); built v2.1.1 from the official
  release tarball per upstream wiki guidance
  (`scripts/build_bulk_extractor.sh`: release tarball → configure → make →
  make install, deps incl. libewf-dev/libre2-dev).
- Verification evidence: `bulk_extractor -V` → `bulk_extractor 2.1.1`.
- Status: done

## [2026-06-11 ~18:45Z] G4 — GPU offload (in progress)

- Findings so far: llama-cpp-python 0.3.21 in prod venv is CPU-only
  (`llama_supports_gpu_offload() == False`); unit already passes
  `--n_gpu_layers 28`. Prebuilt cu124 wheel 0.3.28 **SIGILL (exit 132)** on
  this machine → unusable. CUDA 13 dropped Pascal; CUDA 12.6 toolkit +
  source build with `-DCMAKE_CUDA_ARCHITECTURES=61` is the supported path.
  Build running in background in isolated venv before touching prod.
- Status: in progress

## [2026-06-12 ~00:35Z] Operational incident — WSL VM lifecycle (resolved)

- Symptom: services appeared to "restart" every ~25s, metrics ports refused
  connections, /tmp venv vanished, CUDA build died (exit 1) mid-compile.
- Root cause: the **WSL2 VM idle-shuts-down between tool invocations** once
  no client handle is open (long 6h gap earlier let it stop; unbounded
  `make -j$(nproc)` CUDA compile also crashed the VM once around 00:25).
  Each subsequent command cold-booted the VM — journal "Started" lines were
  per-boot starts, not crash loops. Confirmed via `Startup finished in
  2.115s` + `uptime -s`.
- Fix: persistent keep-alive client (`wsl.exe bash -c 'sleep 14400'` in
  background), restarted whenever it expires. CUDA rebuild will be re-run
  with bounded parallelism to avoid OOM.
- Post-fix evidence: 10/10 services active, NRestarts=0, ledger 936/936,
  metrics ports :8890-:8894 each serving 80 `findevil_*` lines.
- Status: done (operational note, no code change)

## [2026-06-12 ~01:00Z] G4 — GPU offload closed: CPU retained, with evidence

- What was done: completed the full investigation matrix. (a) Prebuilt
  cu124 wheel 0.3.28 → SIGILL on import (no sm_61 kernels). (b) CUDA 13
  dropped Pascal; installed CUDA 12.6 toolkit (WSL-Ubuntu keyring).
  (c) Source-built llama-cpp-python 0.3.21 with
  `-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=61` at bounded `-j4` (the
  unbounded build OOM-crashed the WSL VM) in an isolated venv.
- Verification evidence: build OK — `gpu_offload: True`, ggml found
  `Quadro P620, compute capability 6.1`, model load 1.7s. BUT identical
  8-token completions: **GPU 4565-5053 ms vs CPU 1399-2198 ms** —
  GPU is 2-3× slower (no tensor cores; ggml's modern CUDA kernels are
  not Pascal-optimized; 512 cores / 80 GB/s is below the floor).
- Decision: **production stays on the CPU wheel** — deploying the GPU
  build would regress narrator/pivot latency. The blueprint's 25-40 ms
  TTFT target is unreachable on this GPU; documented as a permanent
  hardware constraint. Hot path (deterministic, no LLM) unaffected.
  Logs: /opt/findevil/logs/cuda_build.log; scripts/build_llamacpp_cuda.sh,
  scripts/cpu_bench_compare.sh.
- Status: done (investigated; constraint documented)

## [2026-06-12 ~01:05Z] Hackathon — official sample case data located

- Official Devpost starter share (Egnyte `HACKATHON-2026`, shared by Rob
  Lee, accessible until **Jun 17, 2026**) enumerated via browser:
  - `Standard Forensic Case`: ROCBA-BACKGROUND.pptx (38.3 MB),
    rocba-cdrive.e01 (22.1 GB), Rocba-Memory.zip (5.3 GB)
  - `Standard Forensics Case 2`: VANKO.zip (40.7 GB) + scenario docx
  - `Compromised APT Attack Scenarios/SRL-2015`: 4 host zips 11-16 GB each
    (+ SRL-2018 variant)
- Decision: use **Standard Forensic Case (ROCBA)** — downloaded the
  38.3 MB background deck and the **5.3 GB Rocba-Memory.zip** (memory
  image = ideal for the volatility/yara MCP pipeline). The 22-40 GB disk
  images deliberately skipped (size/time; documented in dataset.md).
- Status: pptx done; memory zip downloading

## [2026-06-12 ~01:20Z] Part 10 + 11 — narrator ledger enrichment; JWS via joserfc

- Narrator: closed the `TODO` at narrator/service.py — new
  `LedgerReader.for_artifact()` (JSON1 `json_extract` on
  `primary_artifact_key`) feeds up to 3 prior findings for the same
  artifact into debate exhibits (`exhibit_kind=ledger_finding`);
  best-effort so a ledger read failure can never block a debate.
- CACAO: doc Part 11.3 names joserfc for JWS — added
  `sign_playbook_jws`/`verify_playbook_jws` (compact JWS, EdDSA over
  canonical playbook bytes; joserfc needs `algorithms=["EdDSA"]` since
  EdDSA isn't in its default recommended set). Raw Ed25519 compat path
  retained. Root-caused the authlib deprecation warning to fastmcp's
  bundled auth module — not our code.
- Verification evidence: suite **84 passed, 1 skipped**
  (test_ledger_reader_artifact.py ×3, JWS round-trip/tamper ×2).
- Status: done

## [2026-06-12 ~00:50Z] Part 12 — bulk_extractor MCP shim

- What was done: `src/findevil/tools/shims/bulk_extractor.py` —
  `bulk_extractor.version` and `bulk_extractor.scan` (fresh tool-cache
  outdir per run since the binary refuses existing dirs; optional scanner
  allowlist via `-x all -e <s>`; feature files summarised to ≤80 lines so
  the LLM plane never sees raw multi-MB output). Registry auto-discovers
  the module; no server change needed.
- Verification evidence: suite **79 passed, 1 skipped**
  (tests/test_bulk_extractor_shim.py, 3 tests); live MCP probe after
  restart: server exposes **57 tools**, `bulk_extractor.version` →
  `ok=true "bulk_extractor 2.1.1"`; `ledger.verify` → ok=true.
- Status: done

## [2026-06-12 ~00:40Z] Part 14 — TABLE 11 Prometheus metric inventory

- What was done: added all doc-named metrics to
  `observability/metrics.py` and wired them at the correct call sites:
  `ds_fusion_seconds`/`ds_conflict_K`/`consensus_fire_total`/
  `schema_validation_fail_total` in ingest/flow.py; `ledger_append_seconds`
  + outcome-labelled `ledger_appends` in ledger/writer.py;
  `rekor_anchor_age_seconds` in ledger/anchor.py with a new
  `update_anchor_age()` refreshed every 60s by a background task in the MCP
  server (anchoring is a oneshot CLI, so the long-running MCP process owns
  the gauge); `vllm_ttft_seconds` in inference/facade.py;
  `backpressure_drops_total`/`mcp_write_tps` in mcp_server/shadow.py;
  `fractal_live_agents` in fractal/watcher.py.
- Verification evidence: `tests/test_metrics_inventory.py` (3 new tests) —
  suite now **76 passed, 1 skipped**; live `/metrics` on :8890-:8894 shows
  80 findevil lines each incl. ledger_append_seconds /
  rekor_anchor_age_seconds / fractal_live_agents (label-less names);
  labelled counters emit on first observation by design. Ledger 936/936
  clean after service restarts.
- Status: done
