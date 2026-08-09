# BRoS — How we edit values locked in the .exe (dev team guide)

The "exe wall" is broken. This is the reproducible method the team can use to find and ship changes to
things that live in `BLEACH_Rebirth_of_Souls.exe` (self-costs, gauges, gating, HUD, thresholds) — the
stuff that isn't in any tadj/tcmb/fsv data file. First proven on Yamamoto's sublimation-Kikon self-cost
(2 konpaku → 0) and shipped online. Written so any dev can repeat it.

---

## 0. Mental model

- All game logic is compiled into the 28 MB exe (Tamsoft `tam_sys`, not Unreal). Data files only
  *parameterize* it. If a thing is a number on screen / a state flip / a cost and it appears in **no**
  data field, it's exe logic — an "exe wall".
- Each "special" character has a compiled class **`ActionCharaUniqueUI_PlXX`** (findable by RTTI) that
  owns their unique state/UI/costs. That's usually where the wall is.
- We do **not** ship a modified .exe (EAC integrity + updates). We patch **process memory at load** via
  the community-patch loader DLL. On-disk exe stays vanilla.

## 1. Toolchain (one-time)

- Python + `pip install capstone pefile ziglang` (capstone = disassembler, pefile = PE parser,
  ziglang = Windows C compiler for the loader; no Visual Studio/mingw needed).
- Cheat Engine (with its VEH debugger — see §4).
- The exe is standard MSVC x64, **ImageBase `0x140000000`**. A file offset ↔ virtual address (VA) map is
  in `Patched Yamamoto/V5/exe_patch_tool.py` — reuse it.
- Terms: **VA** = address in the loaded image (what Ghidra/our scripts show). **RVA** = VA − ImageBase
  (module-relative; what we bake into the loader). **file offset** = where the byte sits in the .exe on
  disk (for static byte-patches). The tool converts between all three.

## 2. Confirm it's really exe-side (don't skip)

Grep every data surface first. For a per-move thing, dump the tadj records for that action and diff
against a sibling that lacks the behavior (e.g. `evo_ct_sp_break02` vs `evo_ct_sp_break01`). If there is
no field for it (no `self`/`cost`/`konpaku`/etc.), it's exe. (Yamamoto: triple-confirmed clean.)

## 3. Static recon — find the class and the value

Reusable pattern (see the Yamamoto scripts in `Patched Yamamoto/V5`–`V7`):

1. **Find the class by RTTI.** Search the exe bytes for `.?AVActionCharaUniqueUI_PlXX@@`. The type
   descriptor starts 16 bytes before that name; find the u32 RVA of the descriptor → that's referenced by
   the **Complete Object Locator** (COL: `signature=1` at −12, self-ref at +8); an 8-byte pointer to the
   COL is immediately followed by the **vtable**. The vtable's methods that sit in a tight address cluster
   are the class's own overrides.
2. **Find the field.** The engine has a named battle-state field table (reflection). Search for the field
   name string (`konpaku`, etc.); each field has an accessor whose getter encodes the **struct offset**.
   Yamamoto: konpaku is a `float32` at `[combat_obj + 0x10C0]`.
3. **Disassemble** the class methods / the action handler and look for the arithmetic. Tell-tale: a
   `subss`/`movss` on the field, or a helper called with the magic constant. If the value is written
   through a pointer (`lea reg,[obj+off] … movss [reg]`) there's no static xref — go to §4.

## 4. Runtime capture (Cheat Engine) — the reliable pin

Static often can't pin the exact write (pointer indirection). CE's "find what writes" does — but note:

- **Launch offline bypassing EAC** (`BLEACH_Rebirth_of_Souls.exe` directly, Steam running). Software
  breakpoints (`0xCC`) trip EAC/anti-tamper and crash; the exe's own anti-debug is trivial (CRT only).
- Use CE's **VEH debugger** + **hardware breakpoints** (Settings → Debugger Options). Scan the value as
  **Float** for konpaku-type stats. Right-click → **Find out what writes to this address**, trigger the
  move, and the instruction that fires once is the write.
- **Convert runtime → RVA.** Copy the instruction bytes; find that unique byte pattern in the exe with a
  script to get its VA/RVA; the module base = runtime_addr − RVA (sanity-checks all other captures).
- Beware **decoys**: `exe+0x1CE72C8` looked like konpaku but was the *training-mode* `HP_1P` setting.
  Static xref (only touched by the training-menu registrar) exposed it. Always confirm what you found.

## 5. Decide the patch (keep it surgical)

Prefer the smallest same-length, in-place edit that changes only the target, and **verify the call graph**
(single caller? in a vtable?) so you don't hit shared code.
- Yamamoto: the self-cost routine `0x1404EB980` is called from exactly one site that loads the amount
  `xmm1 = 2.0` at RVA `0x5311FC`. We replaced `movss xmm1,[2.0]` (`F3 0F 10 0D 5C F1 F8 00`) with
  `xorps xmm1,xmm1` + NOPs (`0F 57 C9 90 90 90 90 90`) → cost 0. We did **not** touch the shared `2.0`
  constant, and did **not** NOP the call (the routine also builds the cutscene). Result: cost gone,
  cutscene intact, nothing else affected.
- Options in order of preference: neutralize an argument (load 0), NOP an operation, flip a `jz/jnz`,
  change an immediate. Never patch a shared constant or a multi-caller helper without a guard.

## 6. Ship it online (the loader)

The injected loader `Patch_Dev_Environment/Files/Matchmaking/dinput8_proxy.c` already memory-patches the
title string; add your patch the same way. Template (`patch_*()` called from `worker()`):

```c
static void patch_my_thing(void){
    unsigned char* mod = (unsigned char*)GetModuleHandleA(NULL);
    if(!mod) return;
    unsigned char* p = mod + 0xRVA;
    static const unsigned char orig[N] = { ... };   /* current bytes */
    static const unsigned char repl[N] = { ... };   /* patched bytes, SAME length */
    if(memcmp(p,orig,N)!=0){ log_line("MYTHING: bytes moved (game update?) -- skipped"); return; }
    DWORD old;
    if(VirtualProtect(p,N,PAGE_EXECUTE_READWRITE,&old)){
        memcpy(p,repl,N); VirtualProtect(p,N,old,&old);
        FlushInstructionCache(GetCurrentProcess(),p,N);
        log_line("MYTHING: applied at RVA 0xRVA");
    }
}
```
Rules: always the `memcmp` guard (so a game update skips instead of corrupting), always same-length,
always log. Rebuild:
```
zig cc -shared -target x86_64-windows-gnu -O2 -o dinput8.dll dinput8_proxy.c
```
The DLL must export `DirectInput8Create` only. The launcher installs it for non-vanilla launches and
removes it for vanilla, so **vanilla stays pristine** and the patch is memory-only (gone on exit).

## 7. Safety / etiquette

- Stage in `Patch_Dev_Environment`, test with a second dev in a room match, then `ShipChanges`.
- Keep `.bak` of every edited file; the launcher's **Repair** restores from a clean backup.
- Offline-only for any debugging/EAC-bypass; never a modified on-disk exe online.
- Bigger changes than same-length edits ARE possible (allocate memory, write a detour/trampoline, hook a
  function) — same loader, same guard discipline. That's the path for adding new logic/HUD, not just
  tweaking constants.

## 8. Reference: files from the Yamamoto proof
- `Patched Yamamoto/V5` — static recon + `exe_patch_tool.py`.
- `Patched Yamamoto/V6` — runtime findings, EAC diagnosis, CE guide.
- `Patched Yamamoto/V7_NOSELFCOST` — the located patch (`0x5311FC`) + offline test exe.
- `Patched Yamamoto/V8_ONLINE_STAGED` — the loader integration + soul-damage data edit.
