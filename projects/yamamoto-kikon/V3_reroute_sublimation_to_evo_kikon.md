# Yamamoto (pl016) V3 — reroute sublimation Kikon → evo (awakening) Kikon, to drop the 2-stock cost

**Date:** 2026-07-14
**Base:** your latest uploaded `pl016.tadjpkg` (identical to the live game file; already carries the community-patch edits).
**Contains two changes:**
1. `pl016.tadjpkg` — the sp_atk02 grab-whiff fix from V2, re-applied to your current file (`fire_offset_pos` 3.5→1.0 on base + evo).
2. `pl016.tcmbpkg` — the Kikon reroute described below.

This is the Shinji recipe **run in reverse**, using what we learned on Shinji.

---

## Yamamoto's Kikon layout (evo form)

He has two evo Kikon slots, and — unlike Shinji — **no `break02_1`** decoupling entry:

| Slot | Connect cutscene node | Soulbreak (kill) handler | Behavior |
|------|----------------------|--------------------------|----------|
| **break01** = evo / awakening Kikon | `ct_sp_break01` (uids 102,103) | `ct_sp_break01_maxout` (uid 153, kikon_ex 0) | no self-cost |
| **break02** = 毀魂昇華 sublimation Kikon | `ct_sp_break02` (uids 101,104) | `ct_sp_break02_maxout` (uid 154, kikon_ex 1) | **costs you 2 konpaku** |

From the Shinji work we established the governing rule for this engine: a Kikon's **{cutscene, special effect, soul value} are one identity bound to the slot**, and you re-point a Kikon by **renaming its tcmb connect/soulbreak node** (the node's key name = the action it runs, `evo_ct_<name>`). On Shinji, renaming the awakening node to a sublimation-family name *added* the sublimation grant to it — so renaming a sublimation node to the awakening name should *strip* the sublimation effect (the 2-stock cost) from it.

## What V3 does

In `pl016.tcmbpkg`, renamed the sublimation payoff nodes to the awakening actions (same-length byte edits, file size unchanged, braces balanced):

```
"ct_sp_break02"        -> "ct_sp_break01"          (both connect nodes, uids 101 & 104)
"ct_sp_break02_maxout" -> "ct_sp_break01_maxout"   (soulbreak/kill handler, uid 154)
```

Now, when you fire the Kikon in sublimation state, the **payoff runs the evo/awakening Kikon action** (`evo_ct_sp_break01`) instead of the sublimation one. The sublimation *wind-up* (the sp_break02 charge) is left intact, so you keep the charge feel; only the final cutscene resolves as the awakening Kikon. Nothing about the real awakening Kikon or any other move is touched.

## Predicted outcomes (this is the test)

**If the 2-stock cost is bound to the sublimation action/slot** (the likely case, by analogy to Shinji's grant):
- ✅ no more 2-konpaku self-loss;
- the payoff plays the **awakening cutscene** (not the sublimation one) and deals the awakening Kikon's soul damage.

**If the cost is instead bound to the 毀魂昇華 *state* itself** (checked by the exe when any Kikon fires while the state is active):
- ❌ you still lose 2 — which would tell us it's the same exe wall as the earlier finding (`ActionUniquePl016`), not fixable by routing.

Either way the test is decisive about *where* the cost lives.

## About keeping the sublimation cutscene

This is the same wall Shinji hit: because the effect rides on the sublimation cutscene identity, "keep the exact sublimation cutscene **and** drop the cost" probably isn't achievable data-side — and Yamamoto has no `break02_1` escape hatch that let Shinji thread that needle. So V3 deliberately trades the cutscene to guarantee the cost is gone (your stated priority). If V3 confirms the cost is gone, the follow-ups to try to win back the look are:
- **V4 (reskin):** give the awakening connect the sublimation cutscene's motion/demo while keeping break01 identity. ⚠️ On Shinji the reskin *dragged the coupled behavior along with the visuals* — for us that risks pulling the 2-stock cost back in. Worth one test, low expectations.
- Or accept the awakening cutscene as the cost of a cost-free Kikon.

## How to test / revert
- **Test:** copy both files from `Patched Yamamoto/V3/` over `Script/Action/pl016.tadjpkg` and `pl016.tcmbpkg`. Enter 毀魂昇華, fire the Kikon, watch your konpaku count and which cutscene plays. Also confirm the *real* evo awakening Kikon and sp_atk02 grab-catch still behave.
- **Revert:** `pl016.tadjpkg.bak` is vanilla; the launcher also restores official files on relaunch.

## Exact references
- `Script/Action/pl016.tcmbpkg` — evo_combo nodes uids 101/104 (`ct_sp_break02`→`ct_sp_break01`), uid 154 (`ct_sp_break02_maxout`→`ct_sp_break01_maxout`).
- `Script/Action/pl016.tadjpkg` — sp_atk02 / evo_sp_atk02 `Attack_Bullet` `fire_offset_pos` (grab-whiff fix, carried from V2).
