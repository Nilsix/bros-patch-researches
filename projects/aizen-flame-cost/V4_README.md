# Patched Aizen — V4: "SP2 always thinks 1 flame" (consumption-source test)

## What this is
Rami's hypothesis test: if the tier 2–5 Kurohitsugi variants can't fire, does SP2 only
consume 1 flame? Instead of deleting records (size changes), V4 rewrites their conditions
byte-for-byte inside `1_normal_attack_sp_atk02_1` (BASE only; evo left vanilla as control):

- `UNIQUE_1==1` → `UNIQUE_1>=1` (tier-1 records now fire at ANY flame count)
- `UNIQUE_1==2/3/4/5` → `UNIQUE_1==9` (unreachable — flames cap at 5)

File is size-identical to vanilla (1,169,956); only that one entry differs. tcmb = vanilla.

## Install
Replace `Script/Action/pl020.tadjpkg`. Restore vanilla `pl020.tcmbpkg` if V3's is still in.

## The test
Build 4–5 flames in base, land SP2, watch the flame HUD:
- **Flames drop to 0** → consumption is a compiled consume-all in Aizen's class; variant
  records only choose the visuals/damage. The trick is dead (expected outcome, honestly).
- **Flames drop by 1** → consumption is driven by the fired variant — big discovery, opens
  a real path (per-tier control of consumption via conditions).

Also note: does the weakest Kurohitsugi correctly fire at 4–5 flames (tier-1 records at any
count), and does evo SP2 (untouched) still behave vanilla?

## Status of the exact-cost-SP1 goal (V1–V3 postmortem)
- V1/V2: `AddUniqueVal` writes to registers idx 1 and 2 are ignored by Aizen's flame counter
  → the counter is internal to his compiled class; `UNIQUE_1` is only a scratch copy the exe
  writes when Kurohitsugi fires (so the followup can pick a tier).
- V3: `unique_combo` 8→1 changed nothing → SP2's flame gate/consume is keyed to the action
  itself in the exe, not the tcmb node ID.
- `poison_cost` param: Mayuri-only (pl029) mechanic, unused by every other character.

Conclusion: no data-file primitive writes Aizen's flame counter. Exact-cost SP1 via data
files alone is not achievable; see chat for the remaining options (exe patch / SP-cost
fallback / design compromises).
