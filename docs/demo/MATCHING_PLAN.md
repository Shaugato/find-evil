# Stigmergy — Assembly / Matching Plan

> The map for laying each voiceover clip under its matching screen segment. Follow
> the table top‑to‑bottom; the running total stays under 5:00 (target ~4:30).

## Assembly table
| Part | Voiceover file | Video segment | Source (screen) | Target | Running total |
|---|---|---|---|---|---|
| 1 | `vo_01_problem.wav` | `seg_01_problem.mp4` | Title card / boot, field behind | 0:25 | 0:25 |
| 2 | `vo_02_overview.wav` | `seg_02_overview.mp4` | Dashboard: **swarm ops/s ticking** → blackboard → field | 0:35 | 1:00 |
| 3 | `vo_03_live_rocba.wav` | `seg_03_live_rocba.mp4` | **Terminal**: `demo_rocba_carve.sh` (18G image → live carve → 142.250.64.106) + `findevil verify` | 0:55 | 1:55 |
| 3B | `vo_03b_mcp.wav` | `seg_03b_mcp.mp4` | **Terminal**: `demo_mcp_tools.sh` (62 typed tools → **GUARDRAIL ✓ no execute_shell**) | 0:15 | 2:10 |
| 4 | `vo_04_self_correction.wav` | `seg_04_self_correction.mp4` | **Terminal**: `demo_rocba_conflict.py` (tip moves → conflict_K 0.354 → conflict_ledger) + fractal‑pivot note → **Debate tab** ⚖ verdict on 142.250.64.106 | 0:45 | 2:55 |
| 5 | `vo_05_field.wav` | `seg_05_field.mp4` | Field orbit → hover → double‑click atom → blackboard ring | 0:30 | 3:25 |
| 6 | `vo_06_graph.wav` | `seg_06_graph.mp4` | Threat Graph scrubber → kill‑chain node detail | 0:30 | 3:55 |
| 7 | `vo_07_mitre_ledger.wav` | `seg_07_mitre_ledger.mp4` | MITRE 13→1 (PID 6201) → Merkle Ledger forensic block (+ optional Rekor C7) | 0:35 | 4:30 |
| 8 | `vo_08_close.wav` | `seg_08_close.mp4` | Field orbit / website / title hold | 0:20 | **4:50** |

**Hard cap 5:00 — you have ~10 s of margin.** If you run over: trim PART 1 (drop the
second sentence), use the snappier carve (`ROCBA_COUNT_MIB=200`) for PART 3, or drop
the optional CACAO/Rekor line in PART 7. **Never cut PARTS 3, 3B, or 4** — the live
ROCBA real‑data run, the MCP architectural guardrail, and the self‑correction are the
hackathon's highest‑value beats.

## If you recorded ONE continuous take
Instead of `seg_*` files, keep a timestamp log of where each PART starts in
`stigmergy_screen_master.mp4`, e.g.:
```
P1 0:00  P2 0:25  P3 1:00  P3B 1:55  P4 2:10  P5 2:55  P6 3:25  P7 3:55  P8 4:30
```
Claude Code (or you) cuts the master at those marks and aligns each `vo_NN` clip.
The voiceover clip is the source of truth for each segment's final length — trim
the video to the audio, not the other way around.

## Which editor (simplest for audio‑under‑video)
- **CapCut (desktop, free)** — easiest drag‑and‑drop; great if you're new to editing.
  Recommended for this job.
- **Clipchamp** (ships with Windows 11) — fine, fully built‑in, no install.
- **DaVinci Resolve (free)** — most powerful (and free), slightly steeper; use it
  if you want precise control or to add lower‑thirds/titles.

Any of the three handles "voiceover under screen recording" easily. **CapCut** is
the fastest path here.

## One‑paragraph how‑to (CapCut / Clipchamp)
Create a 1920×1080 project at the same fps you recorded. Drag your screen
recording(s) onto the **video track**. Drag the eight `vo_*.wav` clips onto an
**audio track** beneath, in order (1→8). For each part, **slide the video segment
so its action lines up with its voiceover** — the voiceover is the spine; stretch
or trim the *video* (not the audio) so the on‑screen action lands while the words
are spoken (e.g. the `findevil verify` result is visible exactly when PART 3 says
"it returns ok"). Mute the screen recording's own audio track. Add a 0.3–0.5 s
cross‑fade between segments and a short fade‑in/out on the first/last clip. Watch
once end‑to‑end, confirm total ≤ 5:00, then **Export → 1080p MP4**.

## Sanity checks before export
- [ ] Each `vo_NN` sits under the matching `seg_NN` action (live carve, conflict_K
      0.354, ⚖ verdict, green popup, MITRE 13→1, ledger crypto block land on their words)
- [ ] Terminal segments show the WSL2 prompt (`shaugato@AetherX`), not PowerShell
- [ ] **Real case data shown live** — the 18G ROCBA image carved on camera,
      142.250.64.106 extracted live — *mandatory*
- [ ] **MCP architectural guardrail shown** — the 62 typed tools + **GUARDRAIL ✓ no
      execute_shell**, narrated as "Approach #2 … architectural, not a prompt" (PART 3B)
- [ ] **Self‑correction shown live** — conflict_K 0.354 → `conflict_ledger` on the
      carved IP, then the signed ⚖ verdict on the Debate tab — *mandatory*
- [ ] **Speed/no‑LLM** point landed (PART 2 narration: "under a millisecond, no LLM
      in the loop"); **swarm visibly ticking** (PART 2); **fractal pivots** named and
      kept distinct from the 60 sensors (PART 4)
- [ ] No flicker in the 3‑D field (it's fixed; confirm in the recording)
- [ ] Total runtime ≤ 5:00 (target 4:50)
