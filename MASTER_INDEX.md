# BROS Modding — Master Memory Index

Consolidated recovery of all Bleach: Rebirth of Souls modding research, assembled 2026-07-16 after the Claude projects were lost. Start with **`CORE_ENGINE_KNOWLEDGE.md`** (the reusable engine layer). Per-project detail below.

## Projects

### Byakuya Rework (pl022) — ACTIVE
Stance-based awakening: **Senkei** (melee, default) ⇄ **Scattered** (petals, timed ~20 s). Ported sword moveset into evo, Senka custom move, timed-stance system, pink stance aura (`P022_tm_PtlAura00` hijack), Fighting-Spirit tuning.
- `projects/byakuya-rework/bros-byakuya-rework-project.md` — full version history v1→v103, design, status
- `projects/byakuya-rework/bros-file-formats.md` — tadj/tcmb/tact/vfxb layouts, sword-in-evo breakthrough
- `projects/byakuya-rework/bros-gauge-mechanism.md` — gauge arc CLOSED (exe wall); timed-stance resolution
- `projects/byakuya-rework/bros-fighting-spirit-params.md` — FS param map, per-form death-FS recipe
- *Current task:* Scattered-timer-end indicator + Senkei purple body hue + Scattered wing/petal-ring effect (kikon cutscene effects).

### Uryū DP Rework (pl003)
Convert sp_atk02 counter into a true DP. Speed mechanics (WorldSpeedChange vs ObjectSpeedChange), Protect/invuln vocabulary, whiff-vs-hit branching, hit-only install gating.
- `projects/uryu-dp-rework/uryu-dp-rework-state.md` — full DP findings + version history
- `projects/uryu-dp-rework/tadjpkg-format.md` — early tadj/tcmb byte-layout reference (pl003)
- `projects/uryu-dp-rework/tooling-scripts/` — the referenced blueprint patchers (`add_speed_sp_atk02_1.py`, `add_tadj_record.py`, `diag_hit_install.py`)

### Yamamoto Kikon (pl016)
Sublimation-Kikon soul damage (5→4) + remove the 2-konpaku self-cost. Half data-editable, half exe wall. Sublimation→awakening reroute test (the Shinji recipe in reverse).
- `projects/yamamoto-kikon/V1_FINDINGS_kikon_self_damage.md` — kikon mechanics, `kikon_ex`, exe-wall confirmation
- `projects/yamamoto-kikon/V2_sp_atk02_grab_whiff_fix.md`
- `projects/yamamoto-kikon/V3_reroute_sublimation_to_evo_kikon.md` — node-rename reroute recipe
- `projects/yamamoto-kikon/V4_README.md`

### Aizen Flame Cost (pl020)
Make SP1 cost flames (1 base / 3 evo). Proven exe-only (`ActionUniquePl20`); V1–V4 data attempts failed; V5 = static recon + Cheat Engine plan for the hook DLL.
- `projects/aizen-flame-cost/V1_README.md` … `V4_README.md`
- `projects/aizen-flame-cost/V5_EXE_ROUTE_PLAN.md` — vtable VAs, CE workflow, hook design

### Yhwach Reverse (pl052)
Unlock Reverse Action at Kaiser level 0. Exe wall (`ActionUniquePl52`, Kaiser = `UNIQUE_2`); tcmb `unique_combo` level gates mapped; one-compare exe hook plan.
- `projects/yhwach-reverse/V1_FINDINGS_reverse_unlock.md`

### Shinji Patch (pl032) — research survives only by reference
Original findings file lost. The **Kikon-identity rule** it established survives inside the Yamamoto V3/V4 docs (see Core Knowledge §3). Vanilla pl032 files still present at `Claude/Projects/Shinji Patch/vanilla Shinji files/`.

### Yumichika Roster-Add (pl015)
Make the story-mode-only Yumichika a fully playable roster slot (after pl052). Diagnosed every missing select-screen/battle-flow file (menu tactpkg, lobby/icon/pic cat, pic banners, battle_setting lds, 18× tdemopkg cinematics) and cloned from Yhwach. Includes BC7/PZZE art-swap workflow.
- `projects/yumichika-roster-add/pl015_roster_fix_README.md`

### Community Patch Balance
The live community-patch balance data (universal Fighting-Spirit/Reverse changes + per-character edits).
- `projects/community-patch-balance/LatestChanges.txt` (866 lines) + `changelog.txt`

### Ranked Patch Ops
Community-patch matchmaking/install/loader operations (not character research).
- `projects/ranked-patch-ops/` — PATCH_ONLY_RANKED_findings, DIAGNOSIS_AND_FIX, INGAME_LOADER, INSTALL_AND_TEST, START_HERE, MATCHMAKING_CHANGES

### Loose notes
- `loose-notes/aizen-sp2-balance-notes.md` — SP2 radius/damage/homing/FS-threshold balance scratch

## Original backups (as recovered)
- `original-backups/byakuya_memory.rar` �