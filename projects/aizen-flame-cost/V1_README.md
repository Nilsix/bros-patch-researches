# Patched Aizen — V1: SP1 costs flames

## What this does
Makes Aizen's sp_atk01 consume flames on cast: **1 flame in base**, **3 flames in evo**. Rev untouched.

## How it works
Aizen's flame count is stored in unique register **1** — proven by his Kurohitsugi followup
(`sp_atk02_1` / `evo_sp_atk02_1`), whose 5 attack variants are gated on record conditions
`UNIQUE_1==1` … `UNIQUE_1==5`. Vanilla Aizen has zero `AddUniqueVal` records (flame gain/spend
is exe-side), but the engine-generic `AddUniqueVal` record (Unohana/Ichigo use it) writes to
those same registers from a tadjpkg record.

V1 inserts one `AddUniqueVal` record at the front of each SP1 entry:

| Entry | uid | Params |
|---|---|---|
| `1_normal_attack_sp_atk01` (26 records, was 25) | `0xA12E0001` | `unique_type_idx=1, add_unique_val=-1.000000, is_start_timing=1, is_val_set=0, is_end_reset=0`, frames 1→2 |
| `2_evo_attack_evo_sp_atk01` (24 records, was 23) | `0xA12E0002` | same but `add_unique_val=-3.000000` |

`is_val_set=0` = ADD (subtract), applied ~frame 1 of the cast. All other 210 entries are
byte-identical to vanilla; offset table rebuilt (file grows 1,169,956 → 1,170,204).

## Install
Replace `Script/Action/pl020.tadjpkg` (back up the original first).

## What to test in-game
1. Build some flames, cast SP1 in base → flame HUD should drop by 1.
2. Cast SP1 at 0 flames → does the register clamp at 0, or go negative? (If negative,
   Kurohitsugi's `UNIQUE_1==N` variants may whiff until flames rebuild past 0.)
3. Evo: SP1 should drop 3 flames (test at 3+, and at 1–2 to see partial behavior).
4. Kurohitsugi (SP2) afterwards still picks the right power tier for the remaining flame count.

## Knobs for V2+
- Cost values: the `add_unique_val` strings (`-1.000000` / `-3.000000`).
- Timing: record frames (f32 pair, currently 1.0/2.0) — move later (e.g. to the active frames)
  if cost-on-whiff/cancel feels wrong.
- No data-side way to *gate* the cast below X flames — the castability check (`unique_combo`
  tcmb var, Aizen SP1=8, SP2=1) is interpreted by his compiled class. If a hard gate is wanted,
  trying `unique_combo` values on the sp_atk01 tcmb node is the next experiment (SP2's `1`
  likely means "requires ≥1 flame", but it may also trigger consume-all).
