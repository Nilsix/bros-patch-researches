# Patched Aizen — V2: SP1 flame cost, corrected register index

## Why V1 failed (hypothesis)
`AddUniqueVal`'s `unique_type_idx` appears to be **1-based** while record conditions
(`UNIQUE_0`, `UNIQUE_1`) are **0-based**. Evidence from Unohana (pl019): her attacks write
registers via `unique_type_idx=1/2` and the same entries carry records gated on
`UNIQUE_0<=0.0` — i.e. idx=1 ↔ UNIQUE_0. So V1's `idx=1` hit `UNIQUE_0` (the register
Aizen's dash attack reads), not the flame register `UNIQUE_1`.

## Change vs V1
Identical to V1 except `unique_type_idx=2` (targets `UNIQUE_1` = flame register):
- `1_normal_attack_sp_atk01`: AddUniqueVal uid `0xA12E0003`, add `-1.000000`
- `2_evo_attack_evo_sp_atk01`: AddUniqueVal uid `0xA12E0004`, add `-3.000000`
- `is_start_timing=1, is_val_set=0 (add), is_end_reset=0`, frames 1→2. Rev untouched.

## Install
Replace `Script/Action/pl020.tadjpkg` (uses vanilla tcmbpkg — remove V3's tcmb if installed).

## Test
1. Build flames, cast SP1 in base → HUD should drop 1 flame; evo → drop 3.
2. Cast SP1 at 0 flames → check for negative-register weirdness (Kurohitsugi tiers whiffing).
3. Kurohitsugi power tier should match remaining flames.
4. Also confirm dash attack behaves normally again (V1 may have been corrupting UNIQUE_0).

## If V2 also fails
The flame counter is exe-internal (register 1 only receives a copy when Kurohitsugi fires,
same wall as the Byakuya gauge arc). Then V3's consume-all gate is the remaining data-side design.
