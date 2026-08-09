# Patched Aizen — V5: exe-side flame cost (plan + findings)

## Honest status
The exact design (SP1 costs exactly 1 flame base / 3 evo) can only be done in the exe — data
files can't write Aizen's flame counter (V1–V4 proved this). I've done the static recon that
narrows it down, but the **final step needs a live tool (Cheat Engine / x64dbg)** on the running
game to nail two numbers. I can't run the game from here, so this is a division of labor: you
grab those two numbers with Cheat Engine (10 min, guided below), I write the hook DLL.

This is the same wall the Byakuya gauge work hit — but this time it's very tractable, because
**the flame count is a number visible on screen**, which is the ideal case for a Cheat Engine
scan.

## What I've confirmed statically (game build in this folder)
- Aizen's unique class RTTI: `.?AVActionCharaUniqueUI_Pl20@@`
  - TypeDescriptor VA `0x141932628`
  - Complete Object Locator VA `0x1414E6A48`
  - **vtable VA `0x14143FFB8`** (24 virtual methods)
  - Constructor/placement sites (lea to vtable): `0x14020D549`, `0x14021F48C`
  - Destructor (vtable[0]) `0x14020D530`; update/tick methods `0x14020D740`, `0x14020DDF0`
- This class owns the flame **UI/state**; it reads the flame value each frame to draw the meter.
  The consume happens when Kurohitsugi (SP2) fires. SP1 currently never touches it.
- Injection is already solved in this install: `version.dll` = Koaloader (ships PolyHook),
  EAC effectively neutralized, DLL hooks run in online play. So a hook DLL is the delivery vehicle.

## What Cheat Engine needs to find (the two missing numbers)
1. **Flame member offset** — where the flame count lives inside the player/character object.
2. **A stable hook point for SP1 activation** — a code address that runs once when sp_atk01
   starts, with the character object in a register.

### Step-by-step (Cheat Engine)
1. Launch the game the way you already do (modded/injected). Enter a training match as Aizen.
2. Open Cheat Engine, attach to `BLEACH_Rebirth_of_Souls.exe`.
3. Value type **Float** (flames look fractional/continuous) — if that yields nothing, retry as
   **4 Bytes**. Scan type "Exact Value".
4. Note your current flame number, scan it. Build 1 flame, next-scan the new value. Repeat
   building/spending until you're down to a handful of addresses (ideally green/static or a
   pointer path). This address = the live flame counter.
5. Right-click it → **"Find out what writes to this address."** Then cast **SP2 (Kurohitsugi)**.
   The instruction that fires is the **consume** site — copy the full instruction line and the
   address (e.g. `mov [rbx+2C],eax  —  1409ABCDE`).
6. Also do **"Find out what accesses this address"** and cast **SP1**. If anything from Aizen's
   code reads it during SP1, copy those too (helps me find a clean hook near SP1).
7. In the same dialog CE shows the register + offset (e.g. `rbx+0x2C`). **That offset is number
   #1.** Send me the offset and the instruction addresses.
8. Bonus (gets us #2 fast): with the flame address selected, note the base object register value
   at the consume site; that's the character object. I can find SP1's activation from the tadj
   action id once I know the object layout.

Paste me: the flame **offset**, the **consume instruction + address**, and any **SP1 access
instruction + address**. That's everything.

## Then I build V5
A Koaloader module (C++/PolyHook, drops into your existing config) that:
- hooks SP1 activation (or the flame-read the engine does at SP1 start),
- subtracts 1 flame in base / 3 in evo from the flame member, clamped at 0,
- leaves SP2 and everything else untouched.

Delivered as `dll_source.cpp` + build notes, matching the injection setup you already run.

## Fallback available anytime
If you'd rather have something playable immediately while we chase the exe route, say the word
and I'll ship an SP-cost version: `sp_atk01` gets a real reiryoku cost via the tcmb variable
(exact, per-form, works today — it's how Uryu's SP1 costs 50). It's an SP bar cost, not flames,
but it's a real, tunable resource cost with zero exe risk.
