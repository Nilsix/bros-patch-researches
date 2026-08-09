---
name: bros-fighting-spirit-params
description: "BRoS fighting spirit (awakening gauge) parameter map — global death gain, per-form rates/capacities, per-attack gains; per-form death-FS solution"
metadata: 
  node_type: memory
  type: reference
  originSessionId: aacd8670-a45f-4e0c-96e7-529021d493dc
---

Fighting Spirit (FS) system fully mapped (2026-07-07). Berg's balance patch nerfed FS-on-death 80% (lose-to-win fix); wants death FS high in base, low in evo — SOLVED, all data-side.

**CommonParam.fsv** (global; _cso_ SUB cipher, key `98e7508d44109cf4` — NOT the CharaStatus key; recover per-file by printable-maximization): `fightingDamagedSoul=0.5` (flat FS to the DYING player per konpaku lost — the nerfed value), `fightingDamageRate=1.75`, `fightingSuccessAtkRate=1.5`, `fightingBlockAtkRate=1.25`, `fighting_MoveToRival=0.0012` (passive proximity), `fightingSuccessJustSyunpo=0.2`, `fightingOnBreak`, `fight_up_rate_hp_low=2` (low-HP players gain FS ×2 = lose-to-win contributor), `fight_up_rate_quarter/half_reishi=1`.

**CharaStatus.fsv** (per char; key `4814609486b4b60b`): cols 19-21 `fighting_param/evo_fighting_param/rev_fighting_param` = gauge CAPACITY per form (base/awake/reawake; Byakuya 3/3/2, Unohana evo 17.5 = slow reawaken lever), cols 67-68 `evo_fight_rate/rev_fight_rate` = FS-gain MULTIPLIER in that form (ALL chars evo=0.5; base implicit 1.0; rev mostly 1.2).

**tadjpkg per attack**: `fighting_base` + `fighting_recv_rate` params (Byakuya: 125 in 1_normal, 89 in 2_evo entries) = per-hit FS gain, per-form for free since entries are form-split.

**Per-form death-FS recipe**: raise fightingDamagedSoul back up; scale evo down with factor r either via `evo_fight_rate: 0.5→0.5r` (if the death event routes through form rate — TEST: set 0, die in evo) or via capacity `evo_fighting_param ×(1/r)` (guaranteed, denominator). Either way, cancel combat-gain collateral by multiplying evo attacks' `fighting_base ×(1/r)` in tadj. Residual collateral: MoveToRival/just-syunpo/break gains shrink in evo (small).

See [[bros-file-formats]], [[bros-byakuya-rework-project]].
