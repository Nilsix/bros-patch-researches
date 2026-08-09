# Yhwach (pl052) — "Unlock Reverse Action at Kaiser Level 0" — Recon / Feasibility

**Goal:** Yhwach gains a Kaiser level each time he casts `sp_atk01`. Reverse Action
(boost / atk_boost / blk_boost) currently unlocks at Kaiser **level 1**. We want it
available at **level 0** (from match start).

**Short answer:** This is *not* achievable by editing the data files
(`pl052.tcmbpkg`, `pl052.tadjpkg`, `CharaStatus`). The level-2→9 *move* gates are
data-driven and editable, but the specific "reverse becomes usable at level 1"
comparison is **not stored in any data file** — it lives in the exe (the
`ActionUniquePl052` class). Same wall we hit on Aizen's flame-consume. The working
route is an exe hook, and it's a *small* one. Details + exact CE plan below.

---

## How Yhwach's Kaiser system is actually stored

### 1. Kaiser level = runtime register `UNIQUE_2`
The only unique-register condition in Yhwach's entire tadj is a single line:

```
NOW_UNIQUE_2 == 9999999      (in blob 3_rev_ct_rev_ct_reset, gating the P052_Inverse00 visual)
```

So the Kaiser counter is **UNIQUE register index 2** — a runtime value the exe owns
(exactly like Aizen's flame counter was a UNIQUE register the exe wrote to). Data can
*read* it in conditions; data does not *set* its start value or its gate thresholds.

### 2. `sp_atk01` is the level-up ("Unlock") trigger
`1_normal_attack_sp_atk01` fires motion trigger `31:T31_Unlock`
(evo + rev variants fire the same). `atk_hi03` fires `T31_UnlockLoop`. These are the
"raise Kaiser level" events. The increment logic itself is exe-side.

### 3. The level 2→9 moves ARE data — via `unique_combo` in the tcmb
`pl052.tcmbpkg` is JSON (three parallel movesets: `combo` = base, `evo_combo`,
`rev_combo`). Each node carries a 23-slot `variables` array. Slot 16 = `unique_combo`.
The gated attacks carry exactly these values:

| Node (base/evo table) | unique_combo | = required Kaiser level |
|---|---|---|
| atk_hi03 | 2 | 2 |
| atk_ex01 / atk_ex01_combo | 3 | 3 |
| atk_ex02 | 4 | 4 |
| atk_ex03 | 5 | 5 |
| sp_atk02_1 | 6 | 6 |
| sp_atk02_2 | 7 | 7 |
| sp_atk02 | 8 | 8 |

That's the "level 2→9 moves noted in the .tcmb" you described. (Ceiling lines up with
`soul_num = 9` in CharaStatus.) In `rev_combo` these same nodes have `unique_combo`
stripped to 0 — i.e. once you're already in Reverse, the per-level gate is lifted.

**Note there is deliberately no `unique_combo = 1` anywhere.** The level-0→1 unlock is
not expressed as a per-move gate, which is exactly why you couldn't find it in the tcmb.
It's a state flip ("reverse now available"), not a move requirement.

### 4. The reverse trigger moves themselves carry no gate
`boost` / `atk_boost` / `blk_boost` exist in the tadj only as sound/voice adjustment
blobs (`1_normal_*boost_snd` → `SE_OneShot` + `pl052_*_boost_vo`). No condition, no
level field. Other reverse tokens are unrelated to the unlock:
- `can_reverse_sift` — uniform `0` on 51 attacks = reverse-cancel-window flag.
- `ReverseLimit` (limit_target = "opponent") — limits the *opponent's* reverse during
  your moves, not your unlock.
- `OffReverse` / `P052_Inverse00` — visual effect records.

### 5. CharaStatus has no Kaiser config either
pl052 row: `soul_num = 9` (the level ceiling) and **all `unique_val1..12` = 0**. So the
"unlock at level 1" threshold is not a config constant we can drop to 0.

---

## Why data-side can't do it (and why that's consistent with Aizen)

The engine treats "am I allowed to enter Reverse?" as an exe-internal check inside
`ActionUniquePl052`, comparing the live Kaiser register (UNIQUE_2) against a hardcoded
`1`. Nothing in the shipped data files feeds that constant. This is the same class of
wall as Aizen's flame *consume* (`Pl20` class) — per-move data was editable, the state
logic was compiled in.

Confirmed exe target present:
- Class symbol: **`ActionUniquePl052`** (+ `action_unique_pl52_l/r`).
- Kaiser UI: `ui_pl052_unique_icon00` / `ui_pl052_unique_icon_eye00`.
- Reverse visual: `P052_Inverse00`.

---

## The route that works: one-compare exe hook (needs a CE address from you)

This is a *smaller* patch than the Aizen cost hook — it's a single threshold flip, not
arithmetic. Two ways to skin it:

**Option A – flip the compare (cleanest).** Find the instruction in
`ActionUniquePl052` that gates reverse: it compares the Kaiser register to `1`
(`cmp <reg>, 1` / `jl`/`jb` "reverse locked"). Change the immediate `1`→`0`, or NOP the
branch so reverse is always permitted. Reverse unlocks at level 0; the 2→9 move gates
(driven by tcmb `unique_combo`) stay intact.

**Option B – start the register at 1.** Force UNIQUE_2's initial value to 1 at match
start. Reverse is then "unlocked at level 0" from the player's view. Downside: the level
readout / move gates would also see 1, so his level-1 moves would be live at match start
too — probably *not* what you want. Option A is the surgical one.

### Cheat Engine steps to get me the address (same workflow as Aizen)
1. Start a match as Yhwach. His Kaiser level is on-screen → CE scan for it
   (it's UNIQUE_2; try Float first, then 4-byte Int) and lock the address.
2. Right-click that address → **"Find out what accesses this"**, then attempt a Reverse
   Action at level 0 (it'll be blocked) and again after reaching level 1 (it works). The
   instruction that reads the register right before the reverse succeeds/fails is the
   gate.
3. Send me: that instruction's bytes + module offset (RVA from
   `BLEACH_Rebirth_of_Souls.exe` base), and a couple of instructions around it.

With that I'll write the Koaloader/PolyHook DLL (your existing `version.dll` +
EAC-neutralized injection chain already loads online) to flip the compare — output will
land in `Patched Yhwach/V2/`.

**Fallback if you'd rather stay data-side:** we can't unlock reverse early, but we *can*
retune the level-2→9 move gates (lower every `unique_combo` in the tcmb so his stronger
moves come online sooner). That's a genuine tcmb edit and testable immediately — say the
word and I'll build it.

---

*Files inspected: `Script/Action/pl052.tcmbpkg`, `Script/Action/pl052.tadjpkg`,
`Patch/FileInjector/CharaStatus.csv`, `BLEACH_Rebirth_of_Souls.exe` (string/RTTI pass).
No game files were modified in V1 — this is recon only.*
