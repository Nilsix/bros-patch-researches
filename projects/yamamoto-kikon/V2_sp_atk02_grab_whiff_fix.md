# Yamamoto (pl016) — sp_atk02 "whiffs vs a point-blank grab" fix

**Date:** 2026-07-14
**File:** `Patched Yamamoto/V2/pl016.tadjpkg` (drop-in replacement for `Script/Action/pl016.tadjpkg`)
**Status:** candidate fix, ready to test. This is the known issue Nilsix flagged in LatestChanges.txt:
*"his SP2 can whiff up close against someone grabbing at the same time."*

---

## What sp_atk02 actually is

sp_atk02 is a reversal/counter. Its damaging part is a fire **projectile** (`Attack_Bullet` record),
followed by a melee finisher (`sp_atk02_1`, an `Attack_Melee` fan at the body). The bug is entirely in
the **bullet** phase. Relevant bullet params (base `1_normal_attack_sp_atk02`, identical in
`2_evo_attack_evo_sp_atk02`):

| Param | Value | Meaning |
|-------|-------|---------|
| `fire_offset_pos` | `0, 0.75, 3.5` | bullet spawns **3.5 m in front** of Yamamoto |
| `collision_size`  | `2.75, 2.75, 2.75` | spherical hitbox radius 2.75 m |
| `fire_shot_speed` | `0, 0, 0.02` | almost no self-travel — it's a near-stationary sphere |
| `use_homing` / `homing_range -1` / `homing_speedX/Y 10` | homes onto the target, unlimited range |
| `limit_time` | `30` | bullet lives 30 frames |

## Root cause — a point-blank dead zone

The bullet is essentially a hit-sphere **placed 3.5 m ahead** that then homes. Do the geometry:

```
sphere center = 3.5 m ahead,  radius = 2.75 m
covered zone  = 3.5 - 2.75  ..  3.5 + 2.75   =  0.75 m .. 6.25 m in front
```

Anything **closer than 0.75 m is in a dead zone** — the bullet spawns *past* it. Because the bullet
barely moves on its own and relies on homing, a target sitting *behind* the spawn point would need the
bullet to U-turn 180°, which it can't do inside 30 frames at homing speed 10. So it flies forward and
misses.

Normally the opponent isn't that close. But a **grab lunges them to point-blank** at the exact moment
the reversal fires — dropping them into that sub-0.75 m dead zone / behind the spawn point — so the
thrown bullet sails past. That's the "whiffs up close vs a simultaneous grab" bug exactly. (The melee
follow-up `sp_atk02_1` is a radius-4 fan anchored at the body, so it never has this problem — which is
why only the bullet portion whiffs.)

## The fix in V2

Move the bullet's spawn point back to Yamamoto so a point-blank opponent is always **in front of** the
bullet instead of behind it:

```
fire_offset_pos :  0, 0.75, 3.5   ->   0, 0.75, 1.0
```

Now the initial sphere covers `1.0 - 2.75 .. 1.0 + 2.75` = **-1.75 m .. 3.75 m**, i.e. it already
overlaps a point-blank (even slightly-behind) grabber on frame 1, and homing still carries it out to
far opponents. Because `homing_range` is unlimited, **reach against distant opponents is unchanged** —
this only *adds* the missing close coverage, it doesn't shorten the move.

Applied to both `1_normal_attack_sp_atk02` and `2_evo_attack_evo_sp_atk02`.

### Edit is byte-safe
Same-length ASCII value swap (`3.500000`→`1.000000`), done in place. Verified:
- file size identical (772,412 bytes), only **4 bytes** changed;
- entry table (all offsets/sizes) byte-for-byte identical — no offset rebuild, no crash risk;
- exactly the two intended bullet records touched, nothing else.

## How to test / revert
- **Test:** copy `Patched Yamamoto/V2/pl016.tadjpkg` over `Script/Action/pl016.tadjpkg`, launch, and try
  sp_atk02 as a reversal against an opponent mashing grab up close (base and evo). It should now catch them.
- **Revert:** `Script/Action/pl016.tadjpkg.bak` is the vanilla file; the Community Patch launcher also
  robocopy /MIRs the official file back, so this is a safe, disposable test.

## If V2 under-fixes (fallback lever, V3)
If a grab that lunges *even further* still slips through, also enlarge the bullet so its near edge
reaches fully behind Yamamoto (same-length edit):

```
collision_size :  2.75, 2.75, 2.75   ->   3.60, 3.60, 3.60   (or 4.0)
```

Stacking the two guarantees frame-1 point-blank coverage. I kept V2 to the single spawn-offset change so
the test result is unambiguous; say the word and I'll ship the stacked V3.

## File references
- `Script/Action/pl016.tadjpkg` — entry `1_normal_attack_sp_atk02` / `2_evo_attack_evo_sp_atk02`,
  `Attack_Bullet` record, field `fire_offset_pos` (and `collision_size` for the fallback).
