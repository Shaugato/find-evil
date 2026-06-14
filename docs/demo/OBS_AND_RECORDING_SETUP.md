# Stigmergy — OBS & Recording Setup

> Practical, do‑this checklist for recording the screen with **OBS Studio** using
> **Display Capture**. You already recorded the voiceover separately; this pass is
> the **screen only** (you can mute the mic — audio comes from the `vo_*.wav` clips).

## Why Display Capture (not Window Capture)
Window Capture **black‑screens on Windows Terminal** (a known GPU‑rendering /
hardware‑acceleration conflict). **Display Capture** grabs the whole monitor and
avoids it. The trade‑off: everything on that monitor is visible — so clean the
screen (below) before recording.

## OBS settings
- **Source:** add a single **Display Capture** source for your primary monitor.
  (If you have a second monitor, put OBS/notes there and capture only the clean one.)
- **Base (Canvas) Resolution:** `1920×1080`
- **Output (Scaled) Resolution:** `1920×1080`
- **FPS:** `60` (or `30` if your machine struggles — the field is stable at both now).
- **Settings → Output → Recording:**
  - Format: **MP4** (simplest for editing) — or MKV then "Remux to MP4" if you fear crashes.
  - Encoder: **NVENC H.264** if you have an NVIDIA GPU (low CPU cost); else **x264**, preset `veryfast`, CBR ~12–16 Mbps.
- **Settings → Video:** Downscale filter **Lanczos** (sharpest text).
- Mic: you can **mute** the OBS mic track (voiceover is separate). Leave desktop
  audio off too unless you want UI clicks.

## Clean the screen (for Display Capture)
- Close every other window (Slack, mail, browsers you aren't using).
- **Hide the taskbar:** Taskbar settings → "Automatically hide the taskbar."
- **Hide desktop icons:** right‑click desktop → View → uncheck "Show desktop icons."
- **Silence notifications:** turn on **Focus Assist / Do Not Disturb** (Win+A → Focus,
  or Settings → System → Notifications → off).
- Set a plain dark wallpaper (in case the desktop peeks through).
- Close the system tray clock pop‑ups; don't hover the tray during recording.

## Browser (dashboard) setup
- Use **Chrome/Edge**, **F11 full‑screen** so the dashboard fills the frame (no
  tabs/address bar).
- **Zoom: 100%** (Ctrl+0). The dashboard is designed for 1080p; if text feels
  small on your panel, try **90%** so more of the 3‑D field is visible — but keep
  the MITRE/ledger text legible. Don't exceed 100% (the layout reflows).
- Confirm the **Pheromone Field** shows atoms (not "idle") and they're **stable —
  no flicker** (the cooling fix is in; if you ever see jitter, hard‑refresh with
  Ctrl+Shift+R to clear the cached old JS).
- Mouse: move **slowly and deliberately** — fast cursor jumps look bad on video.

## Terminal (WSL2) window setup
- Open **Windows Terminal → the Ubuntu/WSL profile** (dropdown ▾ or Ctrl+Shift+5).
  Prompt must read **`shaugato@AetherX`** — **NOT** `PS C:\>` (PowerShell).
- **Font size 18–20 pt** (Settings → Profiles → Ubuntu → Appearance → Font size).
- Color scheme: a dark, high‑contrast theme (e.g. "One Half Dark").
- Size the window to roughly the left two‑thirds of the screen, or full‑screen it
  for the terminal segments (PART 3 & 4) — full‑screen reads best.
- Run the **C0** setup (`source … activate`; restart dashboard) **before** you
  start recording, so the recorded segments are clean.

## Recording order (matches the PARTS)
Record as **one continuous take** if you can (easier than stitching), pausing
between PARTS. Or record per‑segment files. Suggested approach:

1. Start OBS recording.
2. **PART 1–2** — browser full‑screen on the Pheromone Field (title/overview).
3. **PART 3 (LIVE ROCBA carve)** — Alt+Tab to the **WSL2 terminal** (full‑screen);
   run **C1** (`demo_rocba_carve.sh` — the 18G image carved live) then **C2**
   (`findevil verify`). Narrate over the ~10–16 s carve.
4. **PART 4 (self‑correction)** — still in the terminal, run **C3**
   (`demo_rocba_conflict.py` — conflict_K 0.354 → conflict_ledger), then **Alt+Tab
   to the browser → Adversarial Debate tab** and click the 142.250.64.106 ⚖ card.
5. **PART 5–7** — in the **browser**: field dive + blackboard ring, threat‑graph
   scrubber, MITRE per‑artifact (13→1 on PID 6201), ledger forensic block.
6. **PART 8** — end on the title/field (or the website).
7. Stop recording.

> **Pre‑warm the carve** (do it once before recording, off camera): run
> `bash /opt/findevil/repo/scripts/demo_rocba_carve.sh` once so the OS file cache is
> warm — the on‑camera carve then runs at the snappy end (~10 s). See
> [LIVE_SEGMENT_NOTES.md](LIVE_SEGMENT_NOTES.md).

> Leave **~2 s of stillness** at the start and end of each PART's actions — it gives
> the editor clean cut points to align the voiceover.

## File naming
- **One continuous take:** name it `stigmergy_screen_master.mp4` and keep a quick
  **timestamp log** (a sticky note) of when each PART starts, e.g.
  `P3 terminal @ 0:58`, `P5 field @ 2:10` — Claude Code uses it to cut segments.
- **Per‑segment files:** name them so they sort in order and map 1:1 to voiceover:
  ```
  seg_01_problem.mp4
  seg_02_overview.mp4
  seg_03_live_exec.mp4
  seg_04_self_correction.mp4
  seg_05_field.mp4
  seg_06_graph_debate.mp4
  seg_07_mitre_ledger.mp4
  seg_08_close.mp4
  ```
- Put recordings in `D:\Autonomous DFIR - Agentic SOC\docs\demo\video\` and audio in
  `…\docs\demo\audio\`.

## Pre‑record checklist (tick before hitting Record)
- [ ] WSL2 tab open, prompt `shaugato@AetherX`, venv activated, font 18–20 pt
- [ ] ROCBA live segment ready: `Rocba-Memory.raw` (18G) present, `demo_rocba_carve.sh`
      + `demo_rocba_conflict.py` in `/opt/findevil/repo/scripts/`, carve pre‑warmed once
- [ ] Dashboard restarted (per‑artifact MITRE live); field shows stable atoms
- [ ] Browser full‑screen, 100% zoom, on the Pheromone Field tab
- [ ] Taskbar hidden, desktop icons hidden, Focus Assist ON, notifications off
- [ ] OBS: Display Capture, 1920×1080, 60 fps, MP4
- [ ] All 8 `vo_*.wav` clips recorded and in `…/audio/`
- [ ] You've skimmed [RECORDING_GUIDE.md](RECORDING_GUIDE.md) once end‑to‑end
