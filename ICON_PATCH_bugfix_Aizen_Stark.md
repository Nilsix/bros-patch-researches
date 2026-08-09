# Byakuya evo-icon patch — Aizen/Stark bug FIXED (2026-07-22)

## The bug
The shipped `patch_byakuya_evo_icon()` byte-patched the form read at **RVA `0x2065DD`** in place. That
instruction lives inside the getter at **VA `0x1402065C0`**, which the research doc assumed was
"Byakuya's own UI class method, not shared." **It is not.** `0x1402065C0` is a **shared base-class
form-getter that is vtable slot 22 of 27 different `ActionCharaUniqueUI_PlXX` classes**:

Pl22 (Byakuya), **Pl20 (Aizen)**, **Pl33 (Stark)**, Pl16, Pl26, Pl29, Pl02/03/04/11/13/14/17/23/24/32/
35/37/38/39/42/50/52, plus the base classes (`...UIBase`, `...UICom`, `...UIGauge`, `...UIComIcon`).

Forcing that read to 0 made **every** inheriting class believe it was in base form. Most characters'
icons look identical in base/evo so nothing showed — but **Aizen has two icon assets
(`unique_icon_fire00`/`eye00`) and Stark has form-dependent icon states**, so their icons rendered the
wrong state and flickered on/off. That was the reported bug.

## The fix (Pl22-only vtable repoint)
Leave the shared method **completely untouched** (all 26 other classes work again). Instead give **only
Byakuya's class** its own private copy of the getter that always returns form 0, and repoint **just his
vtable slot**:
- Byakuya Pl22 UI vtable `0x1414405C8`; **slot 22 = +0xB0 = VA `0x141440678` (RVA `0x1440678`)**.
- The getter is 40 bytes and fully relocatable (two intra-function `je`s, no rip-relative/absolute refs),
  so the copy is the verbatim bytes with `mov eax,[rax+0x1094]` → `xor eax,eax; nop*4`.
- Loader allocates the stub (`VirtualAlloc` RX), writes it, and repoints the one vtable pointer
  (`VirtualProtect` the slot). Guarded: only acts if the slot still points at the shared getter and the
  getter bytes match; otherwise skips (game-update safe).

Net: Byakuya keeps his evo icon; Aizen, Stark, and every other character get their correct, untouched
form-getter back.

## What was changed
- `Patch/Files/Matchmaking/dinput8_proxy.c` — `patch_byakuya_evo_icon()` rewritten (live source).
- `Patch/Files/Matchmaking/dinput8.dll` — **rebuilt** (zig) and deployed; also copied to the game-folder
  `dinput8.dll`. Old DLL backed up as `dinput8.dll.prebug.bak`.
- `Patch_Dev_Environment/Files/Matchmaking/dinput8_proxy.c` — corrected function added (dev previously
  had **no** Byakuya patch; this closes the live/dev divergence so a future push can't drop it).

## To deploy / verify
1. Relaunch through the patch launcher (it copies `Patch/Files/Matchmaking/dinput8.dll` into the game).
2. Check `patch_ranked.log`:
   `BYAKUYA_ICON: Pl22-only form getter repointed (icon in evo; Aizen/Stark/others unaffected)`.
3. Confirm: Byakuya icon still shows/seals correctly in evo; **Aizen and Stark icons behave normally
   again** (no flicker).
4. Commit **both** the `.c` and the rebuilt `.dll` (launcher only copies the DLL).

## Note for the research doc
`BYAKUYA_EVO_ICON_exe_patch.md` §4 says the getter "is not shared with any other character" — that line
is the incorrect assumption that caused this. It should read: the getter is a **shared base-class method
(slot 22 of 27 UI vtables)**; the safe patch is a **Pl22-only vtable-slot repoint**, not an in-place body
patch. (General lesson for the dev guide: before an in-place patch to a vtable method, count how many
vtables reference that pointer — if >1, repoint the specific slot instead.)
