# Yamamoto (pl016) — Kikon Sublimation self-damage investigation

**Date:** 2026-07-14
**Status:** V1 = recon only. No game files modified.
**Goal (Rami):** (1) bring his sublimation-Kikon soul damage down from 5-6 to the normal 4-5, and
(2) remove the drawback where he loses 2 of his own konpaku when he does it.

---

## 0. ID confirmation

`pl016 = Yamamoto Genryusai`. Verified three ways:
- Exe name string `COMMON_CHARANAME_YAMAMOTO` sits in a descending-order roster block anchored by known IDs
  (`ICHIGO_1=021, AIZEN=020, UNOHANA=019, GIN=018, SUIFENG=017, YAMAMOTO=016`).
- pl016 effects are fire (`P016_com_fire`, `P016_Evo_Fire2D`); CharaStatus attribute = 炎 (flame).
- Exe has a Yamamoto-only unique class `.?AVActionCharaUniqueUI_Pl16@@` / `ActionUniquePl016_`.

(My earlier note had pl020 = Aizen, which is correct and unrelated — different character.)

---

## 1. What "sublimation Kikon" is, in the files

"Sublimation" = **毀魂昇華 (Kikon Shouka / Kikon Sublimation)**. It is a state flag the engine
exposes to the combo tables as the variable **`kikon_ex`**:

> tcmb variable idx 8 `kikon_ex` — memo: "0無視、1毀魂昇華状態の時のみ有効"
> ("0 = ignore, 1 = only valid while in Kikon Sublimation state")

Yamamoto's Kikon that is gated behind this state is **`sp_break02` / `ct_sp_break02_maxout`**,
whose combo node carries `input_event: "SoulBreaking"` and `kikon_ex = 1`. In the move package these
appear only in the evo/rev movesets (`2_evo_attack_evo_sp_break02_*`, `2_evo_ct_evo_ct_sp_break02_*`),
i.e. the sublimation Kikon is an awakened-form move. This is the move you're describing.

**Important:** the Kikon-Sublimation *state* itself is NOT unique to Yamamoto. Most of the roster has
2 `kikon_ex` nodes (pl000, pl001, pl004, pl006, pl016, pl018, pl022, pl024, pl050, pl052, ...).
Unohana (pl019) has 22. So the state is a shared engine mechanic; only Yamamoto's *penalty* is special.

---

## 2. The soul damage he DEALS (the easy half — data-editable)

Kikon soul damage is stored per hit-record in the tadj as the field **`soul_damage`** (integer,
paired with `damage = 0.000000`, because the Kikon strips souls rather than dealing HP).

Distinct Kikon `soul_damage` tiers, pl016 vs baselines:

| Character | Kikon soul_damage tiers |
|-----------|-------------------------|
| pl000 Ichigo (baseline) | 2 / 3 / **4** |
| pl022 Ichigo alt        | 2 / 3 / **4** |
| pl016 **Yamamoto**      | 2 / 3 / **5** |
| pl019 Unohana           | 1 / 2 / 3 / 6 |

So Yamamoto's top Kikon tier is **5 vs the normal 4** — exactly your "he deals 5-6 instead of 4-5."
This half is a clean data edit: change the top-tier `soul_damage` record from `5` to `4` in
`Script/Action/pl016.tadjpkg` so his Kikon matches the field. (I have the exact record isolated and
can do this edit as a V2 when you want it.)

---

## 3. The 2 konpaku he LOSES himself (the hard half — exe-internal)

I searched every editable data surface for a self-directed soul cost and found **none**:

- **tcmb combo nodes (23-var schema):** the only cost fields are idx2 `cost` (spends 霊子/HP),
  idx7 `reiryoku_cost` (spends SP/reiryoku), and idx8 `kikon_ex` (state flag). There is **no** "soul"
  or "konpaku" cost variable at all. On Yamamoto's `sp_break02` / `ct_sp_break02_maxout` nodes,
  `cost = 0` and `reiryoku_cost = 0` — the move charges him nothing in the data.
- **tadj hit records:** his soul_damage tiers (2/3/5) are all ordinary opponent hits
  (`damage_action = 吹き飛び` blow-away, standard direction). No record targets self; no negative
  soul_damage; no `self` / `自分` / `自身` / `own_soul` / `soul_cost` field exists anywhere in his
  tadj, tcmb, or AiAttackData bins.
- **CharaStatus:** pl016's Kikon-scaling params sit in the normal band and are **not** outliers —
  `fighting_param 3.5`, `evo_fighting_param 3.75`, `evo_kikonsyouka_param 2.5`, `rev_kikonsyouka_param 4`
  (the last is `4` for essentially the entire roster). None of his `unique_val1..12` equals 2 or
  otherwise encodes a "-2." Since these params are shared semantics used by every character, they
  cannot be the source of a Yamamoto-only self-penalty.
- `SoulRebootTiming` / `buffered_soulreboot_input_frame` / `soulreboot_reiryoku_add` looked promising
  but are a **general** soul subsystem — `SoulRebootTiming` appears in every character's tadj
  (pl000=31, pl016=32, pl019=57, pl020=51 occurrences). Not the culprit.

**Conclusion:** the self-loss of 2 konpaku is implemented in Yamamoto's compiled exe class
**`ActionUniquePl016_`** (RTTI `ActionCharaUniqueUI_Pl16`), the same architecture as:
- Aizen `ActionUniquePl020_` — flame-consume proven exe-hardcoded (that project, V1-V4 data edits all failed).
- Yhwach `ActionUniquePl052_` — Kaiser/reverse gate proven exe-hardcoded.

There is no data-side lever for the 2-konpaku self-cost. It is the same exe wall we hit twice before.

---

## 4. Recommended path

**Part 1 (deal 4-5 like everyone):** data edit, doable now. Lower the top Kikon `soul_damage`
5 → 4 in `pl016.tadjpkg`. Low risk, reversible (`.bak` already present). → deliver as `Patched Yamamoto/V2/`.

**Part 2 (stop losing 2 konpaku):** exe hook, needs one address from you via Cheat Engine, exactly like
the route we settled on for Aizen. Concretely:
1. In a match, get Yamamoto into his sublimation Kikon and watch your own konpaku/soul count.
2. CE: scan your soul count (Int4, then narrow), then "find what writes to this address" and fire the
   sublimation Kikon — the instruction that subtracts 2 is inside `ActionUniquePl016`.
3. Send me that instruction's bytes + RVA. I'll write a Koaloader/PolyHook DLL that NOPs (or zeroes)
   the self-subtraction, clamped so nothing underflows — reusing the existing `version.dll` load chain
   that already works online with EAC neutralized.

I can locate the `ActionUniquePl016` vtable/xrefs statically in the exe to narrow the CE hunt if you
want a head start — say the word and I'll run the capstone/pefile pass (same tooling as the Aizen recon).

---

## 5. Exact file references

- `Script/Action/pl016.tadjpkg` — Kikon hit records (`soul_damage` tiers 2/3/5), sp_break02 entries.
- `Script/Action/pl016.tcmbpkg` — combo nodes; `SoulBreaking` node + `kikon_ex=1` gating on sp_break02.
- `Patch/FileInjector/CharaStatus.csv` — pl016 row (params above; human-readable decoded stats).
- `BLEACH_Rebirth_of_Souls.exe` — `ActionUniquePl016_`, `.?AVActionCharaUniqueUI_Pl16@@` (self-cost logic).
