---
name: bros-gauge-mechanism
description: "How BRoS builder/spender gauges work — arc CLOSED: attack-driven gauge is executable-gated, not achievable via data files"
metadata: 
  node_type: memory
  type: reference
  originSessionId: e121d2e9-65cd-4e71-85e1-27f580179750
---

Goal was a "Senkei/Sakura Gauge" for Byakuya (attacks build/deplete → auto stance switch). **ARC CLOSED — NOT ACHIEVABLE via file editing. Do NOT re-chase with more reference characters.** Full proof chain below.

**Engine primitives (data-driven, in tadjpkg):** `AddUniqueVal` record modifies per-char register `unique_type_idx` (params: unique_type_idx, add_unique_val, is_start_timing, is_val_set 0=add/1=set, is_end_reset). `Enhance` record: enhance_start (1=on/0=off), enhance_mode (1/2), max_val (fill cap), init_val (auto or number), enhance_active=0. **KEY LEVER: init_val=auto→max_val acts as TIMER on enhanced state; init_val=NUMBER→Ichigo budget style (but tested: no end trigger without his char-specific Revolut record).**

**Reference chars:** Ichigo pl001 (AddUniqueVal on every attack, Enhance init_val=1200 number); Grimmjow pl038 (mode1 max_val=1200 init_val=auto charge; fills 12-100/hit; tcmb enhance var supports -2..2); Toshiro pl026 (76 AddUniqueVal fractional 0.04-1.5, is_val_set=1 is_end_reset=1, ZERO Enhance records — gauge sets enhance state directly IN HIS EXE); Unohana pl019 (83 NEGATIVE AddUniqueVal — deplete exists; 4 registers idx 1,2,3,8; deeply exe-specific).

**Test chain (2026-07-02..04), all on Byakuya evo:** v7 max_val=800 → auto-revert works but is a ~12s TIMER, not fill. v8/v9: AddUniqueVal +2000 on hit ≠ instant flip → AddUniqueVal does NOT feed enhance gauge (separate register, Enhance has no idx param). v10A mode2 = dud (SP1 dead). v10B Ichigo-style init_val=1000 max_val=-1 = stuck ON forever. v11 Toshiro-style fills = nothing. v12 Toshiro CharaStatus unique_val transplant + fills = nothing. v15: Enhance{start=0,max_val} on ct_evolve = null → default (petal) state CANNOT be timed; only the deliberately-entered enhanced state can. Full oscillation impossible.

**CharaStatus.fsv + CommonParam.fsv** (in project root, _cso_ cipher, 8-byte SUB key 4814609486b4b60b, round-trips safely; decode latin1). CharaStatus 72 cols × 104 rows keyed plXXX. Cols [31-33] enhance_max_time1/2/3, [34-45] unique_val1-12. Byakuya pl022: emt=0/0/0, uval=[180,0...]. Toshiro: emt=1200, uval=[-0.0005,150,0,1.1,1.1,0...]. Ichigo: emt=1000, uval1=50. Grimmjow: emt=0, uval=[600,0.00015...]. Interpretation is per-char compiled code (v12 proved transplant inert).

**★ DEFINITIVE PROOF (2026-07-04, full game dir analyzed):** Tamsoft proprietary engine (tam_sys), NOT Unreal, no scripts; all logic in BLEACH_Rebirth_of_Souls.exe (28MB). RTTI: each special char has own compiled class `ActionCharaUniqueUI_PlXX` (Pl22=Byakuya stance, Pl26=Toshiro gauge). Data files only parameterize these classes. Unique-UI factory switch @func 0x14021ee30; byteTable @RVA 0x21ff50 maps charIdx→case (Byakuya file offset 0x21F364 = case 9). **1-byte patch 09→0C (give Byakuya Toshiro's gauge class) TESTED → CRASHES at battle load** (Pl26 init 0x1402130e0 hardcodes ui_pl026 assets + Toshiro context). Full 275-file pl022→pl026 rename reskin ALSO crashes. Debugger wall reached; EAC risk noted. Gauge is genuinely out of reach.

**Resolution:** (A) TIMED Senkei via Enhance max_val on the SP1 that activates the state (800≈12s, ~67/sec: 530=8s, 670=10s, 1000=15s) — CHOSEN, in FINAL_v13; or (B) manual toggle only (max_val=-1). CharaStatus enhance_max_time is an alternative timer knob (untested on Byakuya).

**HUD/gauge-bar hunt:** bars are NOT in character files; menu_plXXX.tactpkg = char-select assets, not battle HUD. Bar rendering + value binding is exe-side. Visual-indicator alternative = v16_aura (Effect_Loop condition ENHANCED==1 on run/dash, eff COM_tm_SpCharge00).
