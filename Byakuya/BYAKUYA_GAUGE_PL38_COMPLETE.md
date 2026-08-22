# Byakuya — base-form stance gauge, his own icon, and a pink bar

**Game:** BLEACH: Rebirth of Souls
**Character:** Byakuya, `pl022`, chara id `0x16`
**Exe this was derived and verified against:** 28,283,464 bytes
**Status:** shipping. Gauge, icon and colour all validated in game.

> Every address below was read off the **shipping executable**, not from the
> DataChakka Ghidra corpus. That corpus is a *different build* — the shift on
> `.text` is roughly +0x1300 to +0x1540 — so its addresses do **not** transfer.
> Anything quoted here was re-derived by byte pattern or by walking the vtables
> in the live image.

---

## 1. What ships

| Situation | Bar | Icon |
|---|---|---|
| Base form, sword stance | hidden | Senbonzakura |
| Base form, petal stance | full, sakura pink | Senbonzakura |
| Evo (Senkei) | native timer | Senbonzakura |

Three things had to be solved, and they are independent:

1. **Getting a gauge at all** — Byakuya's vanilla UI class draws an icon and no
   bar. Solved by moving him to a class that draws both.
2. **Getting the bar to be pink** — the colour lives in the element, but under
   the new class *nothing reads it*. This is the subtle one, §4.
3. **Getting his own icon back** — the asset clone that gave him a gauge was
   destructive and took his icon with it. Solved in data, §6.

---

## 2. The two class-selection bytes

There are **two** switches, and confusing them is what caused the original SP1
crash on this feature.

| RVA | what it selects | value |
|---|---|---|
| `0x21FF64` | **switch B** — the controller class | `09` → **`12`** |
| `0x21D9A8` | **switch A** — the layout name, i.e. the resource group | **must stay `09`** |

Switch A decides the layout name, which decides which resource group the
controller looks in. Resources are keyed by `hash(groupName, logicalName)`, so
moving switch A repoints Byakuya's whole group and every lookup that still
expects `UIActionUniquePl022_0` misses → unpopulated handle → crash on SP1.
(A *cleanly empty* handle is safe — the copy ctor at `0x92790` has a null test for
exactly that. What crashes is a handle whose control block is stale rather than
zero; see §7.)

Both tables are indexed by `uiId - 2`. Byakuya's `uiId` is 22, so index 20, so
**one byte** in each. A neighbouring byte is a different character's entry.

---

## 3. The controller classes

Identity is readable from RTTI at `vtable - 8`.

| case | vtable | class | contents |
|---|---|---|---|
| `0x09` | `0x1414405C8` | `ActionCharaUniqueUI_Pl22` | icon only — 24 methods |
| `0x12` | `0x14143FB78` | `ActionCharaUniqueUI_Pl38` | gauge **and** icon |
| `0x17` | `0x14143FA50` | `ActionCharaUniqueUICom` | gauge only |
| — | `0x14143FDC8` | Com-family, gauge + `ui_com_unique_icon00` | not reachable from the factory |

`Pl22` is a 24-method class with a 0x50-byte sub-object at `+0x10`; a runtime
switch to it is out of the question. `Com`, `Pl38` and the `0x14143FDC8` class
all share the same 36-method layout and the same element vector.

**`Com` (`0x17`) is not enough** — it is gauge-only, so Byakuya loses his icon
entirely. **`Pl38` (`0x12`) is the one to use**: it draws a gauge and an icon,
and the cloned assets already carry the `ui_pl038_unique_icon_L00 / _R00` names
its `Init` looks up.

### Full vtable diff, Com vs Pl38

Slots that differ: **0, 1, 2, 3, 9, 10, 23, 25, 26, 36-39**. Everything else is
shared. Two of those differences have to be undone.

---

## 4. The two vtable repoints

Both slots live in the **Pl38 vtable, which is Grimmjow's too** (`pl038` is
Grimmjow, Impulse Gauge). His controller takes the same path afterwards.

### 4.1 Slot `0x50` — `SetRate`

```
Pl38 0x140208360  ->  Com 0x1402089B0        (RVA 0x143FBC8)
```

`Pl38::SetRate` is a bare thunk: it writes the value and returns. Nothing ever
makes the bar visible again, so **the evo timer disappears**. `Com::SetRate`
carries the whole show/hide machine:

```
call [rax+0xD0]          ; write the rate into the element
call [rax+0x88]          ; predicate  = byte [[this+8]+0x3C]
  false -> call [rax+0x60]   ; getter A = [elem+0xA0]  (the max)
           == 0 -> HIDE
call [rax+0x88]
  true  -> SHOW
  false -> call [rax+0x68]   ; getter B = [elem+0x9C]  (the current value)
           != 0 -> SHOW
           == 0 -> HIDE
HIDE = jmp [rax+0x118] -> 0x1402086D0 : mov [elem+0x90], 5
SHOW = jmp [rax+0x100] -> 0x1402085C0 : mov [elem+0x90], 1
```

Note that `[rax+0xD0]` **rewrites `[elem+0x9C]` before the test**, so the value
the decision sees is always the one the caller just supplied, never one written
from outside.

### 4.2 Slot `0x10` — the update. This is the one that fixes the colour.

```
Pl38 0x140215510  ->  ComIcon 0x140208EC0    (RVA 0x143FB88)
```

This took the longest to find, so the chain is worth writing down in full.

- The element carries the bar's colour at `+0xB0`. **Writing it changes nothing
  on its own** — it is a source, not the drawn value.
- What copies it to the sprite is `0x1402075A0`. It reads
  `element + 0xB0 + 16*i` (R as a raw dword, G and B as floats) and writes them
  into the sprite's material parameters at
  `[[element+0x20] + 0x19B0] + 32*paramIdx + 0x10 / 0x14 / 0x18`.
- `0x1402075A0` has **exactly one caller in the whole image**: `0x140207548`,
  inside `Com::slot2` = `0x140207490`.
- **`Pl38::slot2` (`0x140215510`) replaces that update wholesale.** Verified
  across the entire function, `0x140215510..0x140215B97`: it calls neither
  `0x140207490` nor `0x1402075A0`. It only does icon-animation work
  (`0x1401CC2D0`, `0x1402278B0`, `0x14022A4B0`, `0x140224520`).

So under `Pl38` the palette is **data nobody reads**, and the bar keeps
Grimmjow's blue no matter what is written to it or how often.

`ComIcon::slot2` (`0x140208EC0`, from the unreachable `0x14143FDC8` class) is
the missing combination: it calls **both** `Com::slot2` — hence the palette push
— **and** the icon animation helpers. Repointing only slot `0x10` leaves
`Pl38::Init` in place, so the `ui_pl038_unique_icon_L00` binding still resolves
and the icon art still loads.

---

## 5. Anatomy of a gauge element

```
g_battleUi              exe+0x1CDE758, indexed by [chara+0xC20]  (0 = P1, 1 = P2)
  +0x200   -> controller
              +0x10 -> pointer to {begin, end, cap}   the element vector
                       element stride 0x240 (576 bytes)
```

Within one element:

| offset | meaning |
|---|---|
| `+0x00` | slot 1 → `ui_cha_unique_gauge00_L`, 0x48 bytes, object pointer at slot+0x20 |
| `+0x20` | the gauge sprite object (slot 1's object) |
| `+0x48` | slot 2 → `ui_gauge_line00` |
| `+0x90` | **mode: 1 = visible, 5 = hidden** |
| `+0x94` | **colour-dirty dword** — `Com::slot2` tests it before calling the push |
| `+0x98` | flags, observed `0x101` |
| `+0x9A` | per-sub-block flag the push at `0x1402075A0` consumes and clears |
| `+0x9C` | **the displayed value** |
| `+0xA0` | the max / reference, init 1.0 |
| `+0xB0 … +0xFC` | **five RGBA presets**, see below |

### The five colour presets

`Com`'s element init at `0x140207050` copies them in from `xmm8..xmm12`:

| offset | RGBA | |
|---|---|---|
| `+0xB0` | 0.133, 0.733, 0.773, 1.0 | cyan |
| `+0xC0` | 0.133, 0.384, 0.773, 1.0 | blue — Grimmjow's |
| `+0xD0` | 0.871, 0.839, 0.298, 1.0 | gold |
| `+0xE0` | 0.902, 0.427, 0.212, 1.0 | orange |
| `+0xF0` | 0.686, 0.000, 0.561, 1.0 | magenta |

Which preset is drawn is chosen inside the push from stack locals, not by
anything reachable from outside. **Paint all five** rather than guess.

Both dirty flags must be re-armed *after* the colour is written, and **every
frame** — the push consumes them, so a one-shot write is dropped the moment
anything re-runs.

### The shipped colour

Sakura pink, authored as **RGB(248, 182, 230)**, validated in game 2026-08-21.
Each channel is `value / 255` as an IEEE-754 float — the push reads R as a raw
dword and G/B as floats, so all three are stored identically in the element:

| channel | value | float | dword |
|---|---|---|---|
| R | 248 | 0.972549 | `0x3F78F8F9` |
| G | 182 | 0.713725 | `0x3F36B6B7` |
| B | 230 | 0.901961 | `0x3F66E6E7` |
| A | 255 | 1.000000 | `0x3F800000` |

Written into **all five** preset slots, then both dirty flags re-armed, every
frame.

---

## 6. The icon art — a data problem, not an exe one

The gauge came from a `pl038 → pl022` UI asset clone, and that clone is
**destructive**: Byakuya's UI containers are replaced by Grimmjow's wholesale.
Proof, on any install:

```
00HIGH/ui/ui_ActionUniquePl022_0_mdl.cat            1,558,291 B
00HIGH/ui/ui_ActionUniquePl038_0_mdl.cat            1,558,291 B   identical
ui_ActionUniquePl022_0_mdl.cat.pre_gaugebar_bak        93,015 B   the real Byakuya
```

So `ui_pl022_unique_icon00` no longer exists in his resource group. **No exe
patch can bring it back** — repointing the name from code resolves to nothing,
which leaves the handle unpopulated, which is the SP1 crash class. Note the
distinction that §7 turns on: zero is safe, stale is not.

### Container format

`ui_*_mdl.cat` is `PZZE` + zlib. Header:

```
u32 version, members, 0, header_len(=256), payload_len, 1, nameCount+1, 0
0x200  the manifest: CRLF-separated, comma-terminated PLAIN TEXT,
       zero-padded to 0x300 where the payload begins
0x300  payload
```

The manifest is **not** a fixed-offset table — Byakuya's original leaves 156 free
bytes and the clone 114, so names can grow freely. The "22 characters against
24" obstacle earlier notes worried about does not exist.

### The splice

Renaming is the wrong move anyway. Keep the manifest untouched and swap only the
pixels:

- Textures are DX10 DDS, `dxgi=98` (BC7_UNORM), payload at **+148**
  (128 DDS header + 20 DX10 header).
- **DDS #6 is the "off" icon (portrait) and #7 the "on" icon (square)**, at every
  LOD — 108×136 / 148×148 in `00HIGH`, 56×68 / 76×76 in `01MIDDLE`, index-parallel
  halving.
- Byakuya's own Senbonzakura art is **DDS #4, 116×116, at offset `0x4C2CC`** in
  the 93 KB `.pre_gaugebar_bak`. Seven of his nine textures are byte-identical to
  the clone's — those are shared UI assets; only #4 and #5 (the `pl017` chain
  frame) are his.
- **BC7 is a fixed 16 bytes per 4×4 block**, so re-encoding at the *same*
  dimensions produces a byte-identical payload length. The splice needs no
  offset fixups and no directory edit. Re-deflate, keep `raw[:0x18]` — the PZZE
  header carries the *inflated* size, so the compressed length may change freely.

Two traps worth knowing: `bros_bc7dec.dds_payload()` returns a **tuple**
`(payload, w, h)`, not bytes — feeding it straight to `decode()` yields a silently
black image. And `bros_bc7.encode_image_bc7(img, w, h)` takes a **PIL Image**,
not bytes.

### The encoder had to be built

`DataChakka/bc7/` ships `bc7enc.c` and `bc7wrap.cpp` but only a macOS `.dylib`,
so `bros_bc7.available()` is False on Windows:

```
python -m ziglang c++ -O3 -shared -target x86_64-windows-gnu \
    -o bros_bc7.dll bc7wrap.cpp
```

### Where it has to be applied

The game folder is not enough — the launcher injects from the Overlay and would
overwrite it. Four files, in the **root** Community Patch version so that CRE and
`+Zangetsu+Hiyori` inherit through `base.txt`:

```
GameVersions/Bleach Rebirth of Souls Community Patch/Overlay/00HIGH/ui/ui_ActionUniquePl022_{0,1}_mdl.cat
GameVersions/Bleach Rebirth of Souls Community Patch/Overlay/01MIDDLE/ui/ui_ActionUniquePl022_{0,1}_mdl.cat
```

The vanilla GameVersion keeps the untouched 93 KB containers.

⚠ `install_overlay` backs up the stock file **the first time** it overwrites it.
If the game folder already holds a modified file when the Overlay is first
installed, that modified file is captured as if it were stock and the revert path
is poisoned. Always restore the game folder before populating an Overlay.

---

## 7. The three runtime hooks

| RVA | what | stolen |
|---|---|---|
| `0x92790` | resource-handle copy ctor — the guard | 6 |
| `0x48C390` | enhance update, `rcx = Chara*` — the stance driver | 5 |

Both are function entries (each preceded by `CC` padding), which is what makes
an inline hook safe there: only the ABI argument registers are live.

**The guard** exists because `0x92790` is a `shared_ptr` copy constructor, generic
and shared by the whole game, and the Pl22 -> Pl38 move very occasionally hands it
a handle whose control block is garbage. Its own empty test reads the control
block and nothing else:

```
927C8  mov  [rcx+0x38],0            ; dest starts empty
927CC  mov  [rcx+0x40],0
927CE  cmp  qword [rdx+0x40],rax    ; rax==0: source control block null?
927D4  je   927EA                   ; yes -> copy nothing, return
927D6  mov  rax,[rdx+0x38]          ; no  -> copy payload
927DE  mov  rax,[rdx+0x40]          ;        copy control block
927E6  lock inc dword [rax+0xc]     ; refcount++
```

So `+0x40` is the control block (refcount at `+0xC`) and `+0x38` is the payload.
When the source fails a sanity check (`[rdx+0x40]` non-canonical, misaligned, or
below `0x100000`, or `[rdx+0x38]` null) the guard clears **`+0x40` and only
`+0x40`**. That makes the engine take its own `je` path: no copy, no refcount
increment, a well-formed empty handle.

Clearing `+0x38` as well — which the first version did — goes outside that
contract. It wipes a live object's payload pointer, and the teardown destructor at
`0x8B0530` then faults at `0x8B06D0` (`lock xadd [rbx+8]`, then `call [rax]` on a
vtable that is no longer there). The three states are cleanly separable:

> **UPDATE — 2026-08-22.** An online match with **Byakuya in both slots** crashed at
> `exe+0x8B06D0` again, on a client running this fix. So the `+0x40`-only guard
> made the teardown crash **rarer, not gone**, and the row below overstates it.
>
> Two things follow. The mirror match is a configuration that was never tested
> before shipping. And the guard cannot be the cause of *this* fault: it only ever
> **skips** a decrement, which leaves a refcount too high — a leak, never a
> premature free. The `0x8B0530` teardown walks a `weak_ptr` at `this+0x18` and a
> `shared_ptr` at `this+8`, and the fault is the strong count reaching 0 with the
> control block already freed. Root cause still open.
>
| guard | result |
|---|---|
| on, `+0x38` and `+0x40` cleared | `0xC0000005` at `0x8B06D0` when leaving a mode |
| off | `0xC0000005` at `0x927E6`, `lock inc` on a garbage control block, on SP1 |
| on, `+0x40` only | neither locally — but see the 2026-08-22 update above |

The condition is rare — 3 neutralisations in 27 million handle copies — which is
why it only ever surfaced on SP1 and on leaving a mode, never in normal play.

**The stance driver** filters on `[chara+0xC00] == 0x16` and `[chara+0xC20] < 2`,
then reads:

- `[chara+0x1098] & 1` — the enhanced (petal stance) bit
- `[chara+0x1094]` — non-zero in evo; the driver hands off so the native timer runs

Volatile-register trap, learned the hard way on an earlier prototype: `r10` and
`r11` survive a hook only as long as it contains **no call**. The moment an engine
function is called they must be saved. A hook that calls into the engine also
needs the stack 16-byte aligned *before* the call, 32 bytes of shadow space, and
`xmm0`–`xmm5` preserved.

---

## 8. Install order

Hooks and repoints first, the class byte **last**. The byte alone is what crashes
on SP1; the hooks and repoints are inert until something selects the class. That
ordering means a partial install can never leave a crashing game behind.

```
guard hook -> stance driver -> SetRate repoint -> update repoint -> class byte
```

The shipping loader verifies every anchor *before* writing anything and logs a
skip instead of half-installing, so a game update degrades to "feature absent",
never to a broken client.

---

## 9. Verified addresses

| what | RVA / VA |
|---|---|
| class byte (switch B) | `0x21FF64` — `09` → `12` |
| layout byte (switch A) | `0x21D9A8` — must stay `09` |
| handle copy ctor (hook) | `0x92790` |
| enhance update (hook) | `0x48C390` |
| `g_battleUi` | `0x1CDE758` |
| Pl38 vtable slot `0x50` | `0x143FBC8` → `exe+0x2089B0` (was `exe+0x208360`) |
| Pl38 vtable slot `0x10` | `0x143FB88` → `exe+0x208EC0` (was `exe+0x215510`) |
| `Com::SetRate` | `0x1402089B0` |
| `Com::slot2` (update) | `0x140207490` |
| palette push | `0x1402075A0`, sole caller `0x140207548` |
| `ComIcon::slot2` | `0x140208EC0` |
| element init (five presets) | `0x140207050` |
| SHOW / HIDE | `0x1402085C0` / `0x1402086D0` |
| Pl22 / Pl38 / Com / ComIcon vtables | `0x1414405C8` / `0x14143FB78` / `0x14143FA50` / `0x14143FDC8` |

---

## 10. Reproducing the analysis

```python
# the five colour presets, from the element init
#   disassemble 0x140207050 and resolve the rip-relative xmm8..xmm12 loads

# who reads the palette, and who calls it
#   scan .text 0x140205000..0x140218000 for reads with displacement 0xB0..0xFC
#   then walk back from 0x140207C60 to its function start (CC CC padding)

# the vtable diff
import struct
COM, PL38 = 0x14143FA50, 0x14143FB78
for i in range(40):
    a, b = qword(COM + i*8), qword(PL38 + i*8)
    if a != b: print(i, hex(i*8), hex(a), hex(b))

# the icon containers
import bros_cat, bros_bc7dec
d, _ = bros_cat.payload(path)          # PZZE -> inflated
print(d[0x200:0x300])                  # the manifest, as plain text
# DDS payload is at +148 from each "DDS " magic; BC7 block count = ceil(w/4)*ceil(h/4)
```

---

## 11. Open items

- **The bar stays visible and empty when the evo timer reaches zero.** The native
  hide is reached only when `Com::SetRate`'s predicate `[[this+8]+0x3C]` is false
  *and* the value it just wrote is exactly `0.0`; neither condition has been
  confirmed to hold at expiry. Cosmetic, and the gauge is correct everywhere else.
- Both repointed slots are in Grimmjow's vtable. His Impulse Gauge now takes the
  `Com` path for `SetRate` and the `ComIcon` path for the update. No problem has
  been observed, but it has not been deliberately tested either.
- The icon's `"Normal"` / `"loop1"` clips are never toggled during a match —
  `Init` plays `"Normal"` once and nothing returns to it. Driving that toggle from
  the stance would need a small animation driver on the `0x48C390` hook.
