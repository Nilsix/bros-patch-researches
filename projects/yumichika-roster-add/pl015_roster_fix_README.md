# pl015 (Yumichika) → playable roster slot after pl052 (Yhwach)

## What was actually wrong

Your `modified_CharaSelect.bin` was already correct — byte-for-byte identical to what this
fix regenerates. pl015 is appended **after pl052** in both character sections (the game's
grid just fills that diagonal layout in its own order, so slot #38 lands where you saw it —
that position is computed by the game, not by the file).

The real problem: **pl015 was never finished as a playable character.** He's a story-mode
opponent, so the devs only shipped his battle kit. Everything the *select screen and battle
flow* needs is missing (his mono art is literally watermarked "Dummy pl015"). Comparing his
files against pl052's:

| Missing file | Role | Symptom it caused |
|---|---|---|
| `menu_pl015.tactpkg` | select-screen animations (`select_1p/2p` + head/hair) | model stuck after hovering him; freeze after confirm (no "selected"/face-off anim to play) |
| `lobby_pl015.cat` | roster grid / lobby face portrait | blank slot in the grid |
| `icon_pl015.cat` | character emblem (crest shown in UI) | missing emblem |
| `pic_pl015.cat` | wide face banner (loading/VS bars) | missing |
| `pl015_pic1/2.lds` | glitch banner variants (awakened/reverse) | missing (he only had pic0) |
| `battle_setting_pl015.lds` | in-battle HUD texture sheet | battle HUD would have nothing to load |
| 18× `pl015_*.tdemopkg` | system cinematics: intro (`ct_start`), win (`ct_win_y`), shunpo counter, Reverse set, awakening set, non-max Kikon fallback | battle flow hangs whenever one is requested |

## Install

Copy every file from this folder to wherever the game reads the character files from
(same place the `pl052_*` / `pl015_*` files live in your setup), and use this folder's
`CharaSelect.bin` as your modified one (or keep yours — it's identical).
Nothing here overwrites an original game file except your own CharaSelect edit;
`pl015_ct_sp_break01_maxout.tdemopkg` (his real Kikon cinematic) is deliberately NOT
included because the game already ships it.

## Test in this order

1. Select screen: slot should show his glitch-art face; hovering him then moving away
   should now correctly switch models (menu tactpkg fixes that).
2. Confirm him + confirm opponent: face-off should proceed (menu tactpkg + pic banner).
3. Battle start: intro cinematic plays (`ct_start` clone — Yhwach's choreography on
   Yumichika's skeleton; expect jank, not a crash).
4. In battle: base kit (his real moveset — it's complete, he's a functional boss).
   His Kikon at max gauge uses HIS own cinematic.
5. Risky, test last: Awakening and Reverse. The cloned cinematics prevent hangs, but his
   moveset data (`pl015.tactpkg`) has no `2_evo` folder — awakened state may misbehave.

## Placeholders you may want to improve later

`icon_pl015.cat` and `battle_setting_pl015.lds` still show **Yhwach's** art (crest + HUD
portraits). If another playable Squad-11 character (Kenpachi/Ikkaku) has an
`icon_plXXX.cat`, clone it the same way for the proper division crest. All cloned
`tdemopkg` intros/wins are Yhwach's motions — replacing them properly means authoring new
demo packages, which is a bigger project.

To swap any art: decode BC7 with `texture2ddecoder`, edit the PNG, re-encode with
`etcpak`, keeping identical dimensions — or just re-run `build_pl015_roster.py` after
editing the crops in `try_custom_art()`. Containers are `PZZE` = zlib with a 24-byte
header (magic + uncompressed size + data offset); the script handles all of it.

## Known leftovers (not fixed here, all cosmetic-or-silent)

His soundbank (`pl015.bnk`) has no `chara_select` / win-quote events → those moments will
be silent (Wwise ignores unknown events). The S3 section of CharaSelect.bin (per-character
hash/value pairs, likely Kikon UI info) is zeroed for him — vanilla records use zero pairs
as terminators, so an empty list is structurally valid. If anything still hangs, the next
suspects are global tables outside these zips — grab any file near CharaSelect.bin that
looks like a character list/param DB and we can check it.
