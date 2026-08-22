---
node_type: memory
title: Byakuya Sakura Gauge — working state + open blocker (sword-form bar)
date: 2026-08-14
status: bar visible, driven by attacks, no crash — sword-form display unresolved
related: bros-byakuya-rework-project, bros-gauge-mechanism, ZANGETSU_MASTER_GUIDE
---

> **SUPERSEDED IN PART — 2026-08-22.** This document describes the **`Com` `0x17`**
> configuration. That is no longer what ships. The shipped config is **`Pl38` `0x12`**
> at `exe+0x21FF64` plus two vtable repoints (`exe+0x143FBC8` -> `exe+0x2089B0`,
> `exe+0x143FB88` -> `exe+0x207490`).
>
> **`BYAKUYA_GAUGE_PL38_COMPLETE.md` in this folder is authoritative** for the class
> byte, the vtable slots and the handle guard. Everything here about the element
> layout, the `_cso_` and UI formats, the stance driver and the research history
> still stands.
>
> Two traps if you work from this file: the handle guard must clear `+0x40`
> **only** (see the correction further down), and the update slot must **never**
> point at `exe+0x208EC0` -- that corrupts the heap, `0xC0000374` at teardown.


# Byakuya Sakura Gauge — handover

`[V]` = byte-verified against the shipping exe or measured in game this session.
`[I]` = inferred. `[?]` = open.

Target: `BLEACH_Rebirth_of_Souls.exe` 1.3.0.0, 28,283,464 bytes,
md5 `7b21356622f2fe8d4a1733e74634abd8` (clean Steam, no patches on disk).
ImageBase `0x140000000`. `.text` file offset = RVA − 0xC00.

---

## 0. TL;DR

A visible unique gauge for Byakuya now works. It is driven by his own Sakura
resource, it depletes on petal attacks, it does not follow the enhance timer
visually, and it forces sword at zero. **One thing remains broken: the bar's
on-screen value does not refresh while in sword stance.**

Three CE scripts + a data-side asset clone. All addresses below verified.

---

## 1. THE THREE SCRIPTS (current working set)

All three must be active together. Order of activation does not matter, but
`sgdata`/`hdata` symbols must exist before any Lua reads them.

### 1.1 SCRIPT 1 — the switch byte

```
[ENABLE]
BLEACH_Rebirth_of_Souls.exe+21FF64:
  db 17

[DISABLE]
BLEACH_Rebirth_of_Souls.exe+21FF64:
  db 09
```

**Do NOT also patch `exe+21D9A8` (switch A).** See §3.

### 1.2 SCRIPT 2 — resource-handle guard (required, prevents the SP1 crash)

> ### CORRECTION — 2026-08-22: clear `+0x40` ONLY
>
> `exe+0x92790` is a `shared_ptr` copy constructor. `+0x40` is the control block
> (refcount at `+0xC`), `+0x38` is the payload, and its own empty test reads
> `+0x40` and nothing else:
>
> ```
> 927CE  cmp qword [rdx+40],rax   ; control block null?
> 927D4  je  927EA                ; yes -> copy nothing, return
> 927E6  lock inc dword [rax+0c]  ; refcount++   <-- the SP1 fault
> ```
>
> Clearing `+0x40` makes the engine take its own `je` path: no copy, no refcount
> increment, a well-formed empty handle. Clearing `+0x38` as well leaves that
> contract -- it wipes a live payload pointer, and the fault moves to the
> teardown destructor at `exe+0x8B0530`, faulting at `0x8B06D0`.
>
> > **UPDATE — 2026-08-22.** An online match with **Byakuya in both slots** crashed at
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
> |---|---|
> | on, `+0x38` and `+0x40` cleared | `0xC0000005` at `0x8B06D0` **leaving a mode** |
> | off | `0xC0000005` at `0x927E6` on SP1 |
> | on, `+0x40` only | neither locally — but see the 2026-08-22 update above |
>
> Note the vocabulary trap elsewhere in these docs: a *cleanly zeroed* handle is
> the **safe** case. What crashes is a **stale** one.
>
> Rarity: 3 neutralisations in 27 million copies.


```
[ENABLE]
alloc(hcode,1000,BLEACH_Rebirth_of_Souls.exe+92790)
alloc(hdata,400)
label(h_ok)
label(h_kill)
registersymbol(hdata)
registersymbol(hcode)

hdata:
  dq 0
  dq 0
  dq 0
  dq 0
  dq 0
  dq 0
  dq 0
  dq 0

hcode:
  push rax
  push r10
  pushfq
  mov r10,hdata
  inc qword ptr [r10]
  mov rax,[rdx+40]
  test rax,rax
  je h_ok
  mov r10,rax
  shr r10,2F
  test r10,r10
  jnz h_kill
  mov r10,rax
  and r10,7
  jnz h_kill
  cmp rax,100000
  jb h_kill
  mov r10,[rdx+38]
  test r10,r10
  je h_kill
  mov r10,r10
  shr r10,2F
  test r10,r10
  jnz h_kill
  jmp h_ok
h_kill:
  mov r10,hdata
  inc qword ptr [r10+08]
  mov [r10+10],rax
  mov rax,[rsp+18]
  mov [r10+18],rax
  mov [r10+20],rdx
  xor rax,rax
  // CONTROL BLOCK ONLY. Clearing [rdx+38] as well crashes when LEAVING a
  // mode -- see the 2026-08-22 correction below.
  mov [rdx+40],rax
h_ok:
  popfq
  pop r10
  pop rax
  mov rax,[rdx]
  mov [rcx],rax
  jmp BLEACH_Rebirth_of_Souls.exe+92796

BLEACH_Rebirth_of_Souls.exe+92790:
  jmp hcode
  nop

[DISABLE]
BLEACH_Rebirth_of_Souls.exe+92790:
  db 48 8B 02 48 89 01

unregistersymbol(hdata)
unregistersymbol(hcode)
dealloc(hdata)
dealloc(hcode)
```

Measured: ~142M calls in one session, **1** handle neutralised, no crash. `[V]`

### 1.3 SCRIPT 3 — the feed

```
[ENABLE]
alloc(sgcode,1000,BLEACH_Rebirth_of_Souls.exe+48CC5B)
alloc(sgdata,400)
label(sg_done)
label(sg_nozero)
label(sg_loop)
label(sg_cnt)
registersymbol(sgdata)
registersymbol(sgcode)

sgdata:
  dd 0
  dd 0
  dd 0
  dd 0
  dd (float)1.0
  dd (float)0.001
  dd 0
  dd 0
  dq 0
  dd 0
  dd (float)-1.0
  dd 0
  dd 0
  dd 0
  dd 0
  dd 0

sgcode:
  push rax
  push rcx
  push rdx
  push r8
  push r9
  push r10
  push r11
  sub rsp,28

  mov r10,sgdata
  mov eax,[rsi+00000C00]
  mov [r10],eax
  cmp eax,16
  jne sg_done
  mov eax,[rsi+00000C20]
  cmp eax,2
  jae sg_done
  inc dword ptr [r10+04]
  mov [r10+20],rsi

  mov eax,[rsi+00001A40]
  mov [r10+40],eax
  mov eax,[rsi+00001A34]
  mov [r10+44],eax

  movss xmm3,[rsi+00001A40]
  movss xmm4,[r10+2C]
  maxss xmm3,xmm4
  xorps xmm5,xmm5
  minss xmm3,xmm5
  movss [rsi+00001A40],xmm3

  movss xmm3,[rsi+00001A34]
  addss xmm3,[rsi+00001A40]
  xorps xmm4,xmm4
  maxss xmm3,xmm4
  movss xmm4,[r10+10]
  minss xmm3,xmm4
  movss [r10+08],xmm3

  xorps xmm4,xmm4
  comiss xmm3,xmm4
  ja sg_nozero
  and byte ptr [rsi+00001098],FE
sg_nozero:

  movss xmm4,[r10+14]
  maxss xmm3,xmm4

  lea rax,[BLEACH_Rebirth_of_Souls.exe+1CDE758]
  movsxd rcx,dword ptr [rsi+00000C20]
  mov rcx,[rax+rcx*8]
  test rcx,rcx
  je sg_done
  mov rcx,[rcx+00000200]
  test rcx,rcx
  je sg_done
  mov rax,[rcx+00000010]
  test rax,rax
  je sg_done
  mov rdx,[rax]
  test rdx,rdx
  je sg_done
  mov r8,[rax+08]
  sub r8,rdx
  mov [r10+3C],r8d
  cmp r8,240
  jb sg_done

  mov r9d,1
  cmp r8,480
  jb sg_cnt
  mov r9d,2
  cmp r8,6C0
  jb sg_cnt
  mov r9d,3
  cmp r8,900
  jb sg_cnt
  mov r9d,4
sg_cnt:
  mov [r10+38],r9d

  xor r11d,r11d
sg_loop:
  movss [rdx+0000009C],xmm3
  mov dword ptr [rdx+000000A0],3F800000
  mov dword ptr [rdx+00000090],1
  add rdx,240
  inc r11d
  cmp r11d,r9d
  jb sg_loop

  inc dword ptr [r10+18]

sg_done:
  add rsp,28
  pop r11
  pop r10
  pop r9
  pop r8
  pop rdx
  pop rcx
  pop rax
  mov dword ptr [rsp+30],0
  jmp BLEACH_Rebirth_of_Souls.exe+48CC63

BLEACH_Rebirth_of_Souls.exe+48CC5B:
  jmp sgcode
  nop
  nop
  nop

[DISABLE]
BLEACH_Rebirth_of_Souls.exe+48CC5B:
  db C7 44 24 30 00 00 00 00

unregistersymbol(sgdata)
unregistersymbol(sgcode)
dealloc(sgdata)
dealloc(sgcode)
```

`sgdata` layout: `+04` frame count, `+08` pushed value, `+10` clamp hi (1.0),
`+14` epsilon, `+18` write count, `+20` `Chara*`, `+2C` clamp lo (−1.0),
`+38` element count, `+3C` vector byte size, `+40` raw `1A40`, `+44` raw `1A34`.

### 1.4 Sanity check (Lua, run before playing)

```lua
local mb = getAddress("BLEACH_Rebirth_of_Souls.exe")
local f = readBytes(mb + 0x48CC5B, 1, true)[1]
local s = readBytes(mb + 0x92790, 1, true)[1]
local b = readBytes(mb + 0x21FF64, 1, true)[1]
print(string.format("feed=%02X  handles=%02X  switchB=%02X", f, s, b))
print((f==0xE9 and s==0xE9 and b==0x17) and "  OK" or "  BAD: expect E9 E9 17")
```

**`E9` matters.** Unconstrained `alloc` makes CE emit a 14-byte `FF 25` jump
that silently destroys following instructions. All three `alloc` calls pass a
near-address for this reason.

---

## 2. DATA-SIDE SETUP (required, not optional)

### 2.1 UI asset clone pl038 → pl022 `[V]`

Byakuya's own containers only ever held `ui_pl022_unique_icon00`. The generic
gauge controller asks for `ui_cha_unique_gauge00_L` and `ui_gauge_line00`; if
they are not in **his** group the lookup returns an empty handle and the game
null-derefs at RVA `0x2072D2` during match load.

Twelve files, **six** in-place substitutions total (three per side):

```
ui/script/scene/ActionUniquePl022_{0,1}.bin        <- ActionUniquePl038_*
ui/script/anim/ActionUniquePl022_{0,1}.bin         <- idem
ui/ui_ActionUniquePl022_{0,1}_{mot,fnt}.cat        <- idem
00HIGH|01MIDDLE/ui/ui_ActionUniquePl022_{0,1}_mdl.cat
```

Rule, and it is load-bearing:

| case | meaning | action |
|---|---|---|
| `Pl038` uppercase | container name (`ui_ActionUniquePl038_0_mdl`) | **substitute** |
| `pl038` lowercase | internal asset (`ui_pl038_unique_icon_L00`) | **preserve** |

The lowercase one appears in the `.cat`'s plaintext CSV manifest at `0x22f` and
names the geometry inside the container. Renaming it makes the manifest
advertise something the container does not hold. Same reason pl005's shipped
assets still carry pl038-named nodes (ZANGETSU_MASTER_GUIDE §5.4).

`"ActionUniquePl038_0"` and `"ActionUniquePl022_0"` are both 19 chars, so the
edit is length-preserving. `Com` (17) would not have been.

No `filename.bin` / `file_exist.htable` work: Byakuya's containers are already
registered, only their contents change.

Tooling: `clone_gauge_pl038_to_pl022.py --inspect / --apply / --revert`.

### 2.2 tadjpkg

`pl022.tadjpkg`, 1,492,899 bytes, 212 entries. Only edit made: petal attacks
`-0.25000` → `-0.10000` (both 8 chars, in place).

Relevant records `[V]`:

| entry | idx | add | is_val_set | writes to |
|---|---|---|---|---|
| `1_normal_ct_ct_evolve` (+`_cos1`) | 1 | +1.000 | **1** | `chara+0x1A34` |
| `2_evo_attack_evo_atk_lo01/02/03` | 1 | −0.100 | 0 | `chara+0x1A40` |
| `2_evo_attack_evo_atk_lo04/05/06` | 1 | +0.250 | 0 | `chara+0x1A40` |

All eight carry `is_start_timing=1`, `is_end_reset=0`.

**`is_val_set` selects the bank.** `1` → `0x1A34`, `0` → `0x1A40`. Confirmed by
in-game measurement, not by reading the handler. Setting `ct_evolve` to
`is_val_set=0` to unify the banks was tried and **broke the attack writes
entirely** — do not repeat it.

Also do not set `max_val` to `"-1.00000000"` (11 chars): tested, crashes. The
engine writes `"-1.000000"` (9 chars) everywhere else. `"99999999.00"` is the
length-matched candidate if the timer ever needs killing from data.

---

## 3. WHY ONLY SWITCH B

Two independent switches, identical 51-entry byte tables, index = `uiId − 2`,
Byakuya `uiId 22` → index `0x14`: `[V]`

| | function | byte table | selects |
|---|---|---|---|
| A | `0x14021CD90` | VA `0x14021D994` (RVA `0x21D9A8` for pl022) | **layout name** |
| B | `0x14021EE30` | VA `0x14021FF50` (RVA `0x21FF64` for pl022) | **controller class** |

Case `0x09` = the Pl22 icon-only class. Case `0x17` = default = generic gauge
controller (vtable `0x14143FA50`, 36 methods), which binds only shared logical
names — no per-character literal, so no coupling.

**Patching switch A crashes the game** on the stance-change SP1: it renames
Byakuya's layout to `ActionUniqueCom_`, so his resource group becomes
`UIActionUniqueCom_0`, and everything still resolving under
`UIActionUniquePl022_0` returns an empty handle. Resources are keyed by
`hash(groupName, logicalName)`. `[V]`

This is also why Byakuya needs none of pl005's 25th-case / relocated-dword-table
work: pl005 sat on the **default** case in switch A and had no layout of his
own. Byakuya already has one.

---

## 4. VERIFIED MEMORY MAP

### Chara struct `[V]`
| offset | meaning |
|---|---|
| `+0x0C00` | character id (Byakuya = 22 / `0x16`) |
| `+0x0C20` | HUD slot (0 or 1) |
| `+0x1094` | **evo flag**, NOT stance — 1 in both petal and sword |
| `+0x1098` | enhance bitmask (bit0 = level 1) |
| `+0x1A10 + 4i` | enhance level *i* remaining |
| `+0x1A1C + 4i` | enhance level *i* max (`1340` for pl022) |
| `+0x1A34` | `AddUniqueVal` bank when `is_val_set=1` — init lands here |
| `+0x1A40` | `AddUniqueVal` bank when `is_val_set=0` — attacks land here |

Displayed Sakura value = `clamp(0,1)( [0x1A34] + clamp(−1,0)([0x1A40]) )`.

### Gauge object chain `[V]`
```
g_battleUi        = 0x141CDE758, 2 entries, indexed by [chara+0xC20]
gauge controller  = [ g_battleUi[slot] + 0x200 ]     single pointer, no list
element vector    = [ controller + 0x10 ]            std::vector, begin/end/cap
element stride    = 0x240
measured size     = 576 bytes = EXACTLY ONE element
```

### Element fields `[V]` (dumped live)
| offset | observed |
|---|---|
| `+0x90` | state, `1` normally, `5` = hidden (written by `vtbl[0x118]`) |
| `+0x98` | flags, `0x101` |
| `+0x9C` | rate — read by `vtbl[0x68]`, this is what we now write |
| `+0xA0` | reference/max — read by `vtbl[0xD0]`, init `1.0` |
| `+0xB0..0xFC` | RGBA colour blocks |

### Native gauge loop `[V]`
Function `0x14048C390`; loop `0x14048CBD8`–`0x14048CCED`. Runs **3 iterations**
(one per enhance level).
```
0x48CBF0  movss xmm0,[rdi+0xC]      ; max; <=0 -> skip entirely
0x48CBFE  test  [rsi+0x1098],ebx    ; level bit
0x48CC17  divss xmm6,xmm0           ; ratio = remaining/max
0x48CC58  call  [rax+0x50]          ; SetRate(ratio)   <- native push
0x48CC5B  ...                       ; <- OUR HOOK, after the native push
0x48CC87  movss [rdi],xmm0          ; remaining -= dt
0x48CCDE  call  0x140474890         ; ClearEnhance at zero
```

### `SetRate` = `vtbl[0x50]` = `0x1402089B0` `[V]`
Not a plain setter. It calls `vtbl[0xD0]` (which reads `[elem+0xA0]` and
**multiplies**), then a predicate `vtbl[0x88]` = `[[this+8]+0x3C]`, and on a
zero rate takes `vtbl[0x118]` which writes `[elem+0x90] = 5` (hidden).
`vtbl[0xC0]` = `0x140208300` is the raw writer: `movss [elem+idx*0x240+0xA0]`.

---

## 5. WHAT IS FIXED

- **Bar renders** for Byakuya. `[V]`
- **Bar is driven by the Sakura resource**, not the enhance timer. `[V]`
- **Petal attacks deplete it** −0.10 each. `[V]`
- **`0x1A40` is clamped to `[−1, 0]`** so it cannot run away (it reached −1.55
  before this and left the bar permanently pinned at zero). `[V]`
- **Forced sword at zero** works (`and byte [rsi+0x1098],FE`). `[V]`
- **SP1 crash contained** — `0xC0000005 @ 0x927E6` gone via the handle guard. `[V]`
- **Bar no longer disappears at zero** (epsilon `0.001` keeps `SetRate` off its
  hide path). `[V]`

A DLL port of scripts 1 and 2 exists in `dinput8_proxy.c` as
`patch_byakuya_gauge_switch()` and `patch_byakuya_handle_guard()`, gated behind
`ENABLE_BYAKUYA_GAUGE`, with `patch_byakuya_evo_icon()` made mutually exclusive.
Not yet shipped.

---

## 6. THE BLOCKER

**The on-screen bar does not refresh while in sword stance.**

The value itself is correct and the write happens — this was measured, not
assumed:

```
valeur          : 0.700
elem+9C         : 0.700     <- our write lands
elem+90         : 1         <- state is "visible", not 5
elem+98         : 0x101
ecritures       : 485       <- hook runs every frame in sword too
taille vecteur  : 576       <- one element, we write to the right one
nb elements     : 1
```

So: the hook runs, computes the right number, writes it into the element that
the gauge object owns, the element is not flagged hidden — and the screen does
not follow. Everything up to the last step is verified.

### Important correction to the framing `[V]`

Sword *light* attacks do **not** add to the bar. The stance-change log shows:

```
f=1319  1A40=-0.400  bitmask=1     end of petals
f=1356  1A40=-0.400  bitmask=0     SP1: bit drops
f=1356  1A40=-0.150  bitmask=0     +0.25 applied HERE
f=1357  1A40=-0.150  bitmask=1     bit back
f=1481  1A40=-0.250  bitmask=1     then -0.10
f=1567  1A40=-0.350  bitmask=1     -0.10
f=1653  1A40=-0.450  bitmask=1     -0.10
```

The `+0.25` fires **once, on the SP1 transition itself**. Every light attack
applies `−0.10` regardless of stance — `evo_atk_lo01/02/03` are played in both
stances, and `lo04/05/06` are never reached by normal light attacks.

This reconciles the in-game impression that "sword raises the bar": doing
petals → SP1 → sword → SP1 → petals collects two `+0.25` (one per transition),
which can outweigh a few `−0.10`. It is the transitions crediting, not the
sword attacks.

**`+0x1094` does not distinguish stance** — it reads `1` in both. `+0x1098`
reads `1` in both except during the single transition frame. Nothing found so
far separates petal from sword at the Chara level. `[?]`

---

## 7. TRIED AND FAILED — do not repeat

| attempt | outcome |
|---|---|
| Patch switch A too | crash `0x927E6` on SP1 (group/hash mismatch) |
| Copy `ActionUniqueCom_*` over pl022 scene | cannot work: internal refs resolve in the wrong group |
| `max_val = "-1.00000000"` in tadj | crash; 11-char float format not parsed |
| `ct_evolve` `is_val_set` 1→0 | attack writes stopped entirely |
| Write `[elem+0xA0]` with no bounds check | heap corruption; crashes at random addresses in **later** sessions |
| Write `[chara+0x1A10] = value*max` | native loop overwrites it two instructions later |
| `call vtbl[0xC0]` instead of `vtbl[0x50]` | no display change |
| `and [rsi+0x1098],FE` every frame while value is 0 | erases the enhance bit the SP1 just set — evo never engages |
| Gate on `cmp ebx,1` (thought it was the level bit) | `ebx` is not the level counter at `0x48CC5B`; crashed |
| `mov dword [rsi+0x1A1C],0` to kill the timer | crash during SP1 (UI torn down mid-transition) |
| DebugPrint probe (`0x140090840`, 150 sites) | **zero** records in both healthy and crashing sessions — rules out every *signalled* failure mode |

---

## 8. OPEN LEADS

1. **What actually renders the bar.** We write `[elem+0x9C]`, which
   `vtbl[0x68]` reads, but the renderer may consume a different field or a
   cached copy elsewhere. Dumping the element every frame and diffing against a
   character whose gauge *does* animate (Unohana pl019, native case `0x17`)
   would isolate it.
2. **Find the stance discriminator.** Neither `+0x1094` nor `+0x1098`
   distinguishes petal from sword. Until one is found, `AddUniqueVal` blocks
   cannot be conditioned per stance, and `lo04/05/06` remain unreachable.
   Bergen's pl005 uses `str_a` gates `ENHANCED<2` / `ENHANCED>=2`, implying
   stance can live in the enhance **level**, not the bitmask.
3. **The enhance timer still runs.** `max_val=1340` still fires `ClearEnhance`
   at ~22 s and flips stance. Display is decoupled but the mechanic is not.
4. **Root-cause the dead handle.** The guard at `0x92790` is containment, not a
   fix. Instrumentation caught the bad handle being copied from RVA `0x20FC4A`,
   a directly-called animation trigger. Something still fails to load silently.
5. **Cost.** The guard sits on an engine-wide hot path (~142M calls/session).
   Frame-time impact never measured. Do that before shipping.

---

## 9. METHODOLOGY NOTES THAT COST US TIME

- **Heap corruption does not surface in the session that causes it.** An
  unbounded `movss [rax+0xA0]` (no check that the vector held ≥1 element)
  produced crashes at four different addresses across later sessions and
  created a false impression of regression. When a crash looks inexplicable,
  close the game *and* CE before concluding anything.
- **The launcher rewrites the environment on every run**: `git fetch` +
  `reset --hard origin/main` + `clean -fd`, then copies
  `Files/Matchmaking/dinput8.dll` into the game folder. A locally built DLL is
  silently replaced. `BalanceLeadTools/DevToken.txt` bypasses the git half.
  Work on a branch other than `main`, with
  `branch.<name>.remote = .` so the launcher's `pull` is a no-op.
- **Windows Application event log is the fastest crash oracle.** `Fault offset`
  is the RVA directly. CE breakpoints are unusable here: `406D1388`
  thread-naming exceptions flood the debugger during load.
- **Two `GameVersions` trees exist** in the repo — `Community Patch` and
  `Community Patch CRE`. The launcher reads the former. Editing the latter
  silently tests nothing.
- **Measure between changes.** Several hours went into consecutive hypotheses
  about the sword display, each plausible, none measured before the next was
  applied. The instrumented dump of the element settled in one run what four
  guesses had not.
