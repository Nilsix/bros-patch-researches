# BLEACH: Rebirth of Souls — Core Engine Knowledge (cross-project synthesis)

Consolidated from every modding project so far (Byakuya, Uryū, Yamamoto, Aizen, Yhwach, Shinji, ranked patch). This is the reusable engine layer — the character-specific state files live under `projects/`. Engine = Tamsoft proprietary **tam_sys** (NOT Unreal, no scripts); all game logic compiled into `BLEACH_Rebirth_of_Souls.exe` (~28 MB). Data files only *parameterize* that logic.

---

## 1. File formats

**`.tadjpkg` (action adjust package)** — per-move properties. Magic `actadj_pkg`; u32 entry count @0x20; 72-byte entry table @0x24 (64-byte Shift-JIS name + u32 offset + u32 size); then contiguous blobs. Blob = `adjb` + 3 null-terminated strings (path, entry name, action name — the 3rd can differ and is what resolves the tact motion) + 17 fixed bytes + u32 record_count + records + small footer (keep verbatim). Record = `u32 uid | tag\0 | 14-byte middle (u32 0, u8 0, f32 start-frame, f32 end-frame, u8 0) | u32 param_count | param_count × (key\0 value\0)`, floats as `%.6f` Shift-JIS. **Conditioned records** replace the flag byte with a condition z-string (e.g. `ENHANCED==1`), leaving a 13-byte middle. Record types: Attack_Melee, Attack_Bullet, ComboStart, CancelTiming, Enhance, AddUniqueVal, SE_OneShot, Effect_Loop/OneShot, Warp, SuperArmor, Protect, WorldSpeedChange, ObjectSpeedChange, Visible, etc. **The 14 mandatory middle bytes are load-bearing** — a 13-byte version desyncs the stream and crashes at character load. Some record variants (certain Attack_Bullet, Warp, CameraFixedAngle, some Effect_OneShot) have extra layout; when surveying, grep raw bytes rather than full-parse, and **insert new records at the front + bump the count** to avoid parsing hard variants. Editing = extract all blobs, verify contiguity, splice, rebuild every offset.

**`.tcmbpkg` (combo/branch graph)** — Shift-JIS JSON-ish, trailing commas. Header + variable defs + parallel tables: `combo` (base), `evo_combo` (awakening), `rev_combo` (reawakening/reverse). Nodes: `_uniqueID`, `input_text` (Pad_R_Left=lo, _Up=hi, _Right=ex, _Down=step-atk, R1=grab/clash, R2=overatk/spbreak), `input_event` (SoulBreaking, RecvEvent+hitDamage, AutoCombo…), `access_text` (entry point), `nexts` (uid list), and a **23-slot `variables` array**. Known slots: **idx1** `in_powerup` (1=only while SP trigger held), **idx2** `cost` (reishi/HP), **idx6** `enhance` (−1 only-when-off / +1 only-when-on / 0 ignore), **idx7** `reiryoku_cost` (SP bar), **idx8** `kikon_ex` (sublimation-state flag: 0=ignore, 1=only in Kikon-Sublimation), **idx16** `unique_combo` (required unique-level, e.g. Yhwach Kaiser level gate). `_uniqueID` namespace is **per-table** (names/ids repeat across base/evo/rev — always search within the correct table segment). Node key-name = the action it runs (`evo_ct_<name>`), so renaming a node re-points which action fires.

**`.tactpkg` (action/motion package)** — outer `PZZEtact` header: magic(8) + u32 decompressed size @8 + … + zlib stream @0x18. Decompresses (~70 MB) to `actmng_pkg`, same 72-byte entry table, entries = JSON-ish `act_data` mapping component slots (body, weapon0_0…, head, hair) to `tmo_name` (motion) / `tmv_name` (weapon motion), plus start/end/play/fusion frames and `next_flow`/`next_name`. Four entries named `pl0XX` are nested sub-packages (acttmo = all motions, one shared pool; acttmv = weapon motions; actmtl; motblend) — **never rebuild these by name; use index** (one is a ~38–68 MB motion blob).

**`.fsv` / `.cat` `_cso_` cipher (CRACKED)** — format `_cso_1_<seed>\n` + ciphertext; repeating 8-byte SUB key, `plain = (cipher − key) & 0xFF` per position. Recover key per-column by maximizing printable/CSV chars. Decodes to `_csv0,<cols>`. Keys are per-file: **CharaStatus.fsv** key `4814609486b4b60b`; **CommonParam.fsv** key `98e7508d44109cf4`. `.lds`/`.tactpkg`/`.tadjdbpkg` use zlib@0x18 instead. Official codec = game's `Script/fsv2csv.py`.

**`.vfxb` (effect visual)** — `PZZEvfxb` header 0x18 bytes + zlib@0x18 → SPFX chunk stream. Contains editable RGBA float32 colors in [0,1] and a `Name` chunk (`eman` + len + z-string) = **the internal effect name the engine registers by**. See §5.

---

## 2. ★ THE EXE WALL (the single most important recurring fact)

Every "special" character has an own compiled class **`ActionCharaUniqueUI_PlXX`** (RTTI) that owns their unique state/UI. Data files can *read* the runtime state (via conditions/records) but cannot *set* its initial value, thresholds, arithmetic, or costs. Confirmed hard walls, all same class of problem:

| Char | Class | Exe-locked mechanic (NOT data-editable) |
|---|---|---|
| Byakuya pl022 | `ActionUniquePl22` | stance gauge/HUD bar; unique icon lock/gating; attack-driven gauge fill |
| Toshiro pl026 | `ActionUniquePl26` | ice gauge (sets enhance state directly in exe) |
| Aizen pl020 | `ActionUniquePl20` | flame counter consume/spend |
| Yhwach pl052 | `ActionUniquePl52` | Kaiser-level (UNIQUE_2) unlock threshold compare |
| Yamamoto pl016 | `ActionUniquePl16` | 2-konpaku self-cost on sublimation Kikon |

**Tells that you've hit the wall:** the thing is a number on screen / a state flip / a resource cost, and it appears in *no* data field (searched tadj/tcmb/CharaStatus). A 1-byte exe patch to swap classes **crashes** (each class hardcodes its own `ui_plXX` assets + context — proven on Byakuya→Toshiro).

**The route that works = exe hook, split labor:**
1. Static recon (here): capstone/pefile pass finds the class RTTI, vtable VA, ctor/tick sites, and confirms which register/UNIQUE index holds the value. (Aizen: vtable `0x14143FFB8`; Yhwach: Kaiser = `UNIQUE_2`.)
2. Live step (Berg, ~10 min in Cheat Engine): scan the on-screen value → "find what writes/accesses this address" → send back the instruction bytes + RVA + register offset.
3. Delivery: a **Koaloader/PolyHook DLL** (C++) that hooks the site and flips the compare / NOPs the subtract / clamps arithmetic. Ships via the existing **`version.dll`** load chain (Koaloader, PolyHook bundled) — **EAC is effectively neutralized in this install and DLL hooks run in online play**. Output pattern: `dll_source.cpp` + build notes.

**Data-side fallbacks that always exist:** real SP/reiryoku cost via tcmb `reiryoku_cost` (how Uryū's SP1 costs 50); retune per-move gates via tcmb `unique_combo`; timed states via Enhance `max_val`. These are testable immediately with zero exe risk.

---

## 3. Kikon / Sublimation (from Shinji → Yamamoto)

"Sublimation" = **毀魂昇華 Kikon Shouka**, a shared engine state exposed to tcmb as `kikon_ex` (var idx8: 1 = only valid in sublimation). It is NOT unique to one char (most roster has ≥2 `kikon_ex` nodes; Unohana 22). Kikon slots in evo form:
- **break01** = evo/awakening Kikon — connect node `ct_sp_break01` + soulbreak handler `ct_sp_break01_maxout` (`kikon_ex 0`), no self-cost.
- **break02** = sublimation Kikon — `ct_sp_break02` + `ct_sp_break02_maxout` (`kikon_ex 1`), may carry a penalty (Yamamoto: −2 konpaku).

**Governing rule (established on Shinji):** a Kikon's **{cutscene, special effect, soul value} are one identity bound to the slot**, re-pointed by **renaming the tcmb connect/soulbreak node** to another slot's action name (same-length byte edits). Renaming awakening→sublimation *adds* the sublimation grant; renaming sublimation→awakening *strips* it (and trades away the sublimation cutscene — you can't keep the exact cutscene AND drop the coupled behavior; a reskin drags the behavior back). Kikon soul damage = tadj `soul_damage` (int, paired with `damage=0` because Kikon strips souls). Whether a penalty is bound to the *action/slot* (data-reroutable) or the *state* (exe wall) is decided by testing the reroute.

---

## 4. Speed / DP / invulnerability mechanics (from Uryū)

- **`WorldSpeedChange`** (param `Speed`, world multiplier over an ANIM-frame window; real duration = span/Speed at 60 fps) — a global time-slow curve; **NOT** what true DPs use.
- **`ObjectSpeedChange`** — slows the **opponent** while you run full speed = the real DP mechanism (cloned from Ichigo pl051/pl001 byte-identically onto Uryū).
- **`SlowMotionRate`** = no-op for this purpose (retired).
- **`Protect`** (invuln) record vocabulary: `完全無敵` (full), `弾無敵` (projectile), `崩しに無敵` (grab/kuzushi), `リバースに無敵` (reverse), `通常攻撃とSP技に無敵`. Categories **stack as separate records** with independent windows; `protect_react` = ヒット判定あり/判定なし. True-DP reference pl051: `sp_atk02` = one action, `Protect 0→70 完全無敵` from frame 0 through the hit.
- **`CancelTiming`** does NOT gate the natural end-of-action return to neutral (only cancels *during* the action). The actionable end-of-move moment = motion end → `act_data next_name`.

---

## 5. Stance, Enhance & Effects (from Byakuya)

- **`Enhance` record** toggles the 固有強化 state: `enhance_start` (1 on/0 off), `enhance_mode`, `max_val` (with `init_val=auto`, `max_val` acts as a **TIMER** on the enhanced state — ~67/sec, so 670≈10 s, 1340≈20 s), `enhance_active`. `AddUniqueVal` feeds a *separate* register (`unique_type_idx`), NOT the enhance timer — an attack-driven enhance gauge is therefore not data-achievable (exe wall).
- **Conditioned effects** (`Effect_Loop` cond `ENHANCED==1/0`) are the only stance-visual lever. Engine matches a tadj entry to a tact motion by **exact full entry name**; to cover a state, synthesize an entry named identically to the tact motion (both `_in` and `_loop` where present). Effects are **strictly action-scoped** — a body-bound loop dies when its spawning action ends (persistent single-spawn = confirmed dead), and re-spawns per action. **No timer-remaining/enhance-transition/time-delayed hook exists** — the only condition variables in the whole roster are `ENHANCED==N`, `TARGET_SIZE`, `BLEND_X/Y`. So a "count down / warn before the timer ends" indicator is not data-achievable.
- **`.vfxb` recolor (proven round-trip):** decompress zlib@0x18, rewrite reddish float triplets to target color, re-zlib, prepend original 0x18 header. **Effects register by INTERNAL name** (the `eman` chunk), not filename — a brand-new name loads nothing; loose `.vfxb` files DO load, so Byakuya-only recolors require **hijacking an existing registered effect** (overwrite its file content + point records at that name). Files live in both `00HIGH/` and `01MIDDLE/Effect/spfx/` quality tiers. Only `COM_tm_SpCharge00`-class effects are proven to render as ambient body loops (petalset/petalslash/EvolveAura need spawn/anim triggers).

---

## 6. Reverse mechanics (from Yhwach)

Reverse-action availability = a state flip checked in the exe (no `unique_combo=1` gate exists). Per-move level gates ARE data (`unique_combo` idx16, stripped to 0 in `rev_combo`). `can_reverse_sift` (uniform 0 = reverse-cancel-window flag), `ReverseLimit` (limits the *opponent's* reverse during your move), `OffReverse` (removing it re-enables flashstep-followup + yellow Chain Reverse). Unlocking reverse early = exe hook (flip the `cmp UNIQUE_2, 1`).

---

## 7. Delivery / injection & recurring gotchas

- **Injection:** `version.dll` = Koaloader (ships PolyHook); EAC neutralized; DLL hooks run online. This is the delivery vehicle for every exe patch. The community-patch launcher restores official files on relaunch (keep `.bak`).
- **tcmb editor corruption:** Berg's editor mojibakes Japanese `memo` fields (harmless, engine ignores) AND **clamps the file to its original byte size**, truncating the tail (lost nodes + closing braces). Always start tcmb edits from a repaired/verified file, not the clamped one. Vanilla tcmb may contain a pre-existing malformed Shift-JIS byte the game tolerates.
- **Size-changing edits** require rebuilding the offset table ourselves (the toolkit exe only does same-length in-place edits).
- **Fighting Spirit** (awakening gauge): `CommonParam.fsv` globals (`fightingDamagedSoul`, rates, `fight_up_rate_hp_low`) + `CharaStatus.fsv` per-form capacity (`fighting_param`/`evo_`/`rev_`) & multiplier (`evo_fight_rate` = 0.5 all chars) + tadj per-attack `fighting_base`. Per-form death-FS is fully data-side.

---

*See `MASTER_INDEX.md` for the per-project file map. Character state details (exact uids, values, version history) are in `projects/<name>/`.*
