# Patched Aizen — V3: SP1 gated like SP2 (unique_combo experiment)

## What this tests
A different lever than V2. In the tcmbpkg, each node has a `unique_combo` ID interpreted by
Aizen's compiled class. Vanilla: SP2 (`sp_atk02`, the flame-consuming Kurohitsugi) = `1`,
SP1 (`sp_atk01`) = `8`. V3 sets SP1's `unique_combo` **8 → 1** on both base (node uid 20) and
evo (node uid 117). Everything else byte-identical (2-byte change, tadjpkg = vanilla).

## Install
Replace `Script/Action/pl020.tcmbpkg` with this file and **restore the vanilla
`pl020.tadjpkg`** (don't stack with V1/V2 — one experiment at a time).

## Possible outcomes
- SP1 becomes unusable at 0 flames but castable with ≥1 → `unique_combo=1` is a "requires
  flames" gate. Check whether casting SP1 also *consumes* flames (all? none?).
- SP1 behaves exactly as before → the gate/consume logic is keyed to the action name, not
  the node ID; this lever is dead.
- SP1 breaks entirely → ID 1 carries SP2-specific exe logic; revert.

If V2 works, combine later: V2's tadjpkg (exact cost) + V3's tcmbpkg (can't cast at 0 flames)
= gated, exact-cost SP1. If the gate turns out to consume all flames by itself, we can instead
compensate by *refunding* flames via AddUniqueVal (e.g. consume-all + add back "flames − X").
