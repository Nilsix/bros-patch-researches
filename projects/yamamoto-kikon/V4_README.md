# Yamamoto (pl016) V4 — sublimation Kikon rerouted, no 2-stock cost, soul damage 4/5

**Date:** 2026-07-14
**Base:** your uploaded `pl016.tadjpkg` (= live game file). Supersedes V3.

V3 test result: reroute **worked** — no more 2-konpaku self-loss (confirms the cost was bound to the
sublimation *action*, not the state). The only thing left was that it dealt **3/4** (break01's value)
instead of the wanted **4/5**. V4 fixes that.

## Everything in V4

**`pl016.tcmbpkg`** — the V3 reroute (unchanged): sublimation Kikon payoff runs the awakening (break01)
action, so no self-cost.
- `ct_sp_break02` → `ct_sp_break01` (connect, uids 101/104)
- `ct_sp_break02_maxout` → `ct_sp_break01_maxout` (soulbreak/kill handler, uid 154)

**`pl016.tadjpkg`** — 3 edits vs your uploaded file (5 bytes total, size unchanged):
1. **Soul damage 3 → 4** on `evo_ct_sp_break01` (`soul_damage` 3→4) → now **4 normal / 5 soulbreak**.
2 + 3. The sp_atk02 grab-whiff fix carried from V2 (`fire_offset_pos` 3.5→1.0 on base + evo).

Measured values, for reference: break01 (awakening) was `soul_damage 3`; break02 (original sublimation)
was `soul_damage 5` + the 2-stock cost. The soulbreak/kill tier is always connect + 1, so 4 → 4/5.

## ⚠️ One coupling to be aware of

The rerouted sublimation Kikon now **shares the break01 slot with your real evo/awakening Kikon**. There
is no third cost-free slot to separate them (break02 is the only other slot and it carries the exe cost;
a cloned "break03" just falls back to break02 — proven on Shinji). So bumping break01 to 4 makes **both**
your awakening Kikon *and* your (rerouted) sublimation Kikon deal **4/5**. In practice you now effectively
have one Kikon that deals 4/5 with no self-cost whether or not you're in 毀魂昇華.

If you'd rather keep the awakening Kikon at its old 3/4 and accept the sublimation one at 3/4 too, just
skip edit #1 (use V3). There's no data-side way to make the two slots read different values while both
stay cost-free.

## Test / revert
- **Test:** copy both files over `Script/Action/`. In evo, fire the Kikon in and out of 毀魂昇華 — expect
  4 on a normal connect, 5 on a full soulbreak, no self-loss, both states. Confirm sp_atk02 still catches
  a point-blank grab.
- **Revert:** `pl016.tadjpkg.bak` is vanilla; launcher restores official files on relaunch.

## Cutscene note (unchanged from V3)
The payoff plays the **awakening cutscene**, not the sublimation cinematic — keeping the exact sublimation
cutscene while dropping the cost is the same wall Shinji hit, and Yamamoto has no `break02_1` escape hatch.
A reskin (V5) could try to restore the look but risks dragging the cost back; low expectations.
