# Byakuya (pl022) — unique stance icon kept visible in evo

> ## ⚠️ v2.1 CORRECTION (2026-07-22) — the getter is SHARED; patch it Pl22-only
>
> The in-place byte patch at RVA `0x2065DD` documented in §4/§5 below shipped and worked for Byakuya
> but **broke Aizen (pl020) and Stark (pl033)** — their unique icons flickered on/off. Cause: the form
> getter at VA **`0x1402065C0`** is **NOT** "Byakuya's own class method." It is a **shared base-class
> method — vtable slot 22 of 27 different `ActionCharaUniqueUI_PlXX` classes** (Pl22 Byakuya, Pl20 Aizen,
> Pl33 Stark, Pl16, Pl26, Pl29, … plus the `...UIBase/UICom/UIGauge/UIComIcon` bases). Byte-patching its
> body forces form=0 for every inheriting class; characters with form-dependent icons (Aizen has two
> icon assets `fire00`/`eye00`; Stark has form states) then render the wrong state.
>
> **Correct fix — Pl22-only vtable repoint (no shared code touched):**
> Give only Byakuya's class a private copy of the getter that returns form 0, and repoint just his
> vtable slot. The getter is 40 bytes and fully relocatable (two intra-function `je`s, no rip-relative
> or absolute refs), so the copy is verbatim with one instruction swapped:
> - Byakuya Pl22 UI vtable = VA `0x1414405C8`; **slot 22 = +0xB0 = VA `0x141440678` (RVA `0x1440678`)**.
> - stub = the 40 bytes at `0x1402065C0` with `mov eax,[rax+0x1094]` (`8B 80 94 10 00 00`) replaced by
>   `xor eax,eax; nop*4` (`31 C0 90 90 90 90`).
> - loader: `VirtualAlloc` RX → write stub → `VirtualProtect` the slot → write the stub pointer in.
>   Guard: only act if the slot still points at `mod+0x2065C0` and the getter bytes match.
>
> Result: Byakuya keeps his evo icon; Aizen, Stark and the other 24 classes are untouched.
>
> **General rule (add to the dev guide):** before an in-place patch of a vtable method, search the exe
> for the 8-byte function pointer and count how many vtables reference it. If >1, repoint the specific
> class's slot instead of editing the shared body.
>
> The loader `patch_byakuya_evo_icon()` and the shipped `.c`/`.dll` now use this repoint. Everything in
> §1–§3 (recon, state-machine analysis) remains correct; only §4's "not shared" claim and the in-place
> method are superseded by this block.



Second proven exe patch after Yamamoto's self-cost. Same method, same loader, no modified exe on
disk. Written so any dev can repeat or re-derive it after a game update.

**Result shipped:** in evo (Senkei), Byakuya's unique icon no longer vanishes. It stays on screen
and seals/unseals with the stance exactly like in base form — sword = sealed, petals = unsealed.

---

## 0. The problem

Vanilla + rework behaviour: the unique icon (Senbonzakura, chained/sealed art) is drawn in base
form and **disappears entirely on awakening**. Players had no on-screen way to tell which stance
Byakuya was in during evo — the whole reason the aura VFX line (v16 → v45) existed as a workaround.

Goal: make the icon behave in evo like it does in base.

## 1. Confirm it's exe-side (§2 of the dev guide)

Checked before touching the exe:

- `pl022.tact/tadj/tcmb` contain **no reference** to the UI strings at all.
- `ui/script/scene|anim/ActionUniquePl022_0.bin` / `_1.bin` — the `_0`/`_1` split is **player
  slot** (left/right of screen), *not* form. Both load the same `ui_pl022_unique_icon00`.
- Prior attempts that swapped the whole UI class (1-byte `09`→`0C` to borrow Toshiro's, and the
  pl022→pl026 reskin) **crashed at battle load** — expected, since `Pl26` hardcodes its own assets.
  Those crashes are what made the icon look untouchable; they are a different (much riskier)
  operation than what is done here.

Conclusion: rendering/gating lives in the compiled class `ActionCharaUniqueUI_Pl22`. Exe wall.

## 2. Static recon

Exe: `BLEACH_Rebirth_of_Souls.exe`, PE32+ x64, 9 sections, **ImageBase `0x140000000`**.

### 2.1 The class (RTTI → vtable)

```
.?AVActionCharaUniqueUI_Pl22@@   file 0x1930E68
TypeDescriptor                   VA 0x141932658
Complete Object Locator          VA 0x1414E6D80
vtable                           VA 0x1414405C8   (24 virtual methods)
```

Methods that matter:

| slot | VA | what |
|---|---|---|
| vt[3]  | `0x140205D40` | per-frame child update/draw dispatcher (iterates the element vector at `[this+8]+0x48..0x50`, calls each element's `vtable+0x18`) |
| vt[21] | `0x1402065B0` | form setter (`mov [rax+0x44], edx`) |
| **vt[22]** | **`0x1402065C0`** | **form getter — the patch target** |
| vt[23] | `0x14020F8A0` | init / descriptor builder (registers the icon by name) |

### 2.2 There is only ONE icon asset (important)

All icon-frame strings present for pl022:

```
ui_pl022_unique_icon00   VA 0x14143DD98      the icon
unique_icon00            VA 0x14143DC61
unique_icon_base         VA 0x14143DC09      background plate
unique_icon_L00 / _R00                        left/right PLAYER copies (not form frames)
```

For contrast Aizen (Pl20) has both `unique_icon_fire00` and `unique_icon_eye00`. Byakuya does not.
So a separate "sword symbol" texture **does not exist** — sealed vs unsealed are two display
states of the same icon, not two assets. This killed the "import two symbols" idea early and saved
a pointless asset-injection project.

Icon plumbing (init only, not per-frame):
- name registration site `0x140206BCE`; LEA of the icon string at `0x14020F8C4` / `0x14020F9C2`
- register helper `0x140206A30` → `0x140206610` → create-by-name+index `0x1402373B0`
- UI factory `0x140220030`

The name is resolved **once** at init; per-frame drawing uses a cached handle plus a state index.
That's why grepping the icon string leads nowhere near the draw path.

### 2.3 The two state fields

Found via the engine's reflection field-token table (dev guide §3.2). The condition token
`ENHANCED` sits at VA `0x141458248`, right next to `UNIQUE_0/1/2` (`0x141458278/68/58`) — i.e. the
same variables tadj record conditions use.

Its two code refs (`0x14039F82A`, `0x140474975`) straddle accesses to one member:

```
0x14039F813   mov  ebx, [rsi+0x1098]      ; read, mirrored to [r13+0x5C0], then named "ENHANCED"
0x140474961   mov  [rsi+0x1098], edi      ; write, then named "ENHANCED"
```

So:

| field | meaning |
|---|---|
| `[combat_obj + 0x1094]` | **form enum** — 0 = base, 1 = evo, 2 = reverse (compared to 0/1/2/4 across the exe) |
| `[combat_obj + 0x1098]` | **ENHANCED / 固有強化 stance flag** — bit 0 |

`+0x1098` is read all over the exe as `test byte ptr [reg+0x1098],1` — the signature of a per-object
state bitfield checked by every move handler, matching how `ENHANCED==1` conditions get evaluated.

### 2.4 The icon state machine already does what we want

The UI "value by selector" function (`~0x140204060`) reads an anim-node id from `[obj+0xC00]` and
computes a display state per node. Node `0x14`:

```
0x140204258   cmp   ecx, 0x14
0x14020425D   movzx ebx, byte ptr [rax+0x1098]   ; stance flag
0x140204264   and   ebx, 1                       ; bit 0
0x140204267   shl   ebx, 5                       ; -> 0 or 32
```

Neighbour node `0x13` is gated on `cmp dword ptr [rax+0x1094], 1` (evo) plus `[rax+0x11F0]`.

**Cross-check with the data files** (`pl022.tadjpkg`): conditions used are only `ENHANCED==0` (×4)
and `ENHANCED==1` (×466) — strictly binary, no bitfield. `Enhance` records carry
`enhance_start=1` (petals on) / `=0` (off). Combined with the tcmb gating
(base `start_lo` → `atk_lo01` at enh=-1, `atk_lo04` at enh=1) and lo1-3 = sword / lo4-6 = petals:

```
ENHANCED = 0  ->  SWORD stance   ->  icon state 0   (sealed)
ENHANCED = 1  ->  PETALS stance  ->  icon state 32  (unsealed)
```

i.e. **the sealed/unsealed↔stance mapping is already correct and already wired**. Nothing to author.
The only defect is that the icon is gated off in evo, so node `0x14` is never reached.

## 3. Runtime pin (Cheat Engine)

Static recon gave the offsets; CE confirmed them live and produced the module base.

Setup: launch via the patch launcher (starts `BLEACH_Rebirth_of_Souls.exe` **directly**, so EAC
doesn't block the injected dinput8), CE with **VEH debugger** + hardware breakpoints, training mode,
offline only.

**Do NOT use "Unknown initial value" on this game** — it returns ~5M+ hits per pass and freezes the
machine. Two freezes cost an hour. Use exact-value scans with `Fast Scan 4` + `Pause the game while
scanning`; optionally restrict Start/Stop to the heap range seen in results.

Two separate hunts, because the two flags are independent:

1. **Form flag** — Byakuya in evo, scan `1` (4 Bytes); back to base, scan `0`; alternate.
   Converged to 17 candidates.
2. **Stance flag** — **stay in evo the whole time**, only toggle sword↔petals: scan `0` / `1`
   alternating. Converged to 6 candidates.
   (Byakuya has both stances in base too, so a base↔evo scan mechanically *eliminates* the stance
   flag. That mistake cost a detour — hunt each flag with only its own variable moving.)

The pair fell out immediately:

```
271DB5EC044   toggles with FORM    -> +0x1094
271DB5EC048   toggles with STANCE  -> +0x1098      (4 bytes apart, same object)
combat_obj base = 271DB5EAFB0
```

**Module base**, via a known static instruction seen in "find out what accesses":
`7FF7E419F813 = mov ebx,[rsi+00001098]` = static `0x14039F813` → **base `0x7FF7E3E00000`**.
Sanity check: `0x7FF7E40065DD − 0x2065DD` = same base. Both captures agree.

Finding the gate: "find out what accesses" on the **form** flag surfaced

```
7FF7E40065DD - mov eax,[rax+00001094]      = RVA 0x2065DD, count ~4253 (per-frame)
```

which is the form read **inside Pl22's own UI getter** (vt[22]). Meanwhile, nothing in the icon
code region ever showed up in the *stance* flag's access list — direct evidence that the icon node
is not evaluated at all during evo.

## 4. The patch

`ActionCharaUniqueUI_Pl22::vt[22]`, VA `0x1402065C0`:

```
0x1402065C0   mov rax,[rcx+8]
0x1402065C4   mov rcx,[rax+0x110]      ; guard
0x1402065CB   test rcx,rcx / je …
0x1402065D0   cmp dword ptr [rcx+8],0 / je …
0x1402065D6   mov rax,[rax+0xF0]
0x1402065DD   mov eax,[rax+0x1094]     <-- force to 0
0x1402065E3   ret
```

Force the getter to always report form 0 (base) → the unique UI keeps drawing the icon after
awakening; sealed/unsealed then follows the stance by itself through node `0x14`.

```
RVA        0x2065DD        (VA 0x1402065DD, file offset 0x2059DD)
orig       8B 80 94 10 00 00     mov eax,[rax+00001094]
repl       31 C0 90 90 90 90     xor eax,eax ; nop*4
```

Same length (6 bytes). **Blast radius:** the getter is a Pl22 vtable method, i.e. Byakuya's own UI
class — not shared with other characters. Confirmed in game: icon returns in evo, seals/unseals
with the stance, base form and the rest of the HUD unaffected.

Test-first-in-CE recipe (Memory View → Tools → Auto Assemble → File → Assign to current cheat
table, then tick Active):

```
[ENABLE]
BLEACH_Rebirth_of_Souls.exe+2065DD:
  db 31 C0 90 90 90 90

[DISABLE]
BLEACH_Rebirth_of_Souls.exe+2065DD:
  db 8B 80 94 10 00 00
```

## 5. Ship it (loader)

Added to `Files/Matchmaking/dinput8_proxy.c` as `patch_byakuya_evo_icon()`, called from `worker()`,
same guard discipline as `patch_yamamoto_selfcost()` (memcmp guard, same length, logged).

```c
unsigned char* p = mod + 0x2065DD;
static const unsigned char orig[6] = {0x8B,0x80,0x94,0x10,0x00,0x00};
static const unsigned char repl[6] = {0x31,0xC0,0x90,0x90,0x90,0x90};
```

Rebuild:
```
python -m ziglang cc -shared -target x86_64-windows-gnu -O2 -o dinput8.dll dinput8_proxy.c
```
Commit **both** `.c` and `.dll` — the launcher's `setup_matchmaking()` only copies the DLL.

Log line to verify (`patch_ranked.log`, next to the game exe):
```
BYAKUYA_ICON: stance icon kept visible in evo (RVA 0x2065DD)
```
If it says `bytes not at expected RVA 0x2065DD (game updated?) -- skipped`, the game updated and the
patch safely no-ops; re-derive §2.4/§3.

Live vs dev: the live build ships this patch **without** the Yamamoto self-cost (still in balance
testing). Keep the Byakuya patch in the dev source too, otherwise a later dev→live push silently
removes the icon.

## 6. Pitfalls / lessons

- **Two prior crashes were class swaps, not this.** Swapping a whole `ActionCharaUniqueUI_PlXX`
  crashes because each class hardcodes its own assets. Patching a single field read inside the
  class the character already owns does not.
- **Grepping an asset string finds init, not draw.** Names are resolved once; the per-frame path
  uses a cached handle and a state index. Follow the vtable, not the string.
- **Hunt one variable at a time.** Scanning base↔evo eliminates the stance flag, because stance
  exists in both forms.
- **Never `Unknown initial value` on this game.** Exact-value scans only.
- **Adjacent offsets are a free confirmation.** Once one flag is found, its neighbour ±4 is often
  the related one; toggling only the second variable proves the structure in seconds.
- **Data files answered a question the disassembly couldn't**: the tadj `ENHANCED==0/==1` census
  proved the flag is strictly binary (no bitfield), which validated plain 0/1 scanning.

## 7. Open items

- **2P side**: the icon has `_L00`/`_R00` player variants — verify the patched behaviour on the
  right-hand player in a room match.
- **Reverse form**: `+0x1094` is `2` in reverse; the patch forces 0 there too. Confirm the icon
  behaves sensibly (or gate the patch on form != 2 if it doesn't).
- If a genuinely different **petals vs katana artwork** is ever wanted, that is a separate and much
  larger job: author + inject a second icon texture into `ui_ActionUniquePl022_*_mdl/.cat`
  (BC7 → PNG → re-encode, PZZE zlib + 24B header, same container tooling as the pl015 roster art),
  register it as a second element index at init (or hook `0x140206A30`), then select by stance.
  Not needed for the current goal.
