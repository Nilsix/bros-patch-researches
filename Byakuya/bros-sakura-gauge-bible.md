---
node_type: memory
title: Byakuya Sakura Gauge — complete reference
date: 2026-08-17
status: WORKING — bar renders and tracks the resource in both stances
supersedes: bros-sakura-gauge-session, BYAKUYA_SAKURA_GAUGE_state
related: bros-byakuya-rework-project, bros-gauge-mechanism, ZANGETSU_MASTER_GUIDE, bros-file-formats
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


# Byakuya Sakura Gauge — complete reference

Everything established across the whole investigation. Written to be dropped
into a knowledge base and consumed by other Claude instances working on this
codebase.

Markers: `[V]` = byte-verified against the shipping exe or measured in game.
`[I]` = inferred but not directly proven. `[?]` = open question.

Target binary: `BLEACH_Rebirth_of_Souls.exe` 1.3.0.0, 28,283,464 bytes,
md5 `7b21356622f2fe8d4a1733e74634abd8` — clean Steam build, no patches on disk.
ImageBase `0x140000000`. `.text` file offset = RVA − 0xC00. `[V]`

---

## PART 0 — WHAT WORKS, IN ONE PAGE

Byakuya now has a working unique gauge:

- renders on screen in **both** stances (petal and sword)
- **petal light attacks** drain it (−0.10 per hit)
- **sword light attacks** fill it (+0.25 per hit)
- at zero it **forces sword stance**
- at zero the bar stays **visible but empty** (does not vanish)
- no crash on the stance-change SP1

It takes **two data-side changes** and **four Cheat Engine scripts**. There is
no single "aha" — every one of the six pieces is load-bearing, and removing any
one of them breaks or crashes the build. That is the single most important
thing to know before touching it.

---

## PART 1 — THE SOLUTION

### 1.1 Data side — UI asset clone pl038 → pl022 `[V]`

Byakuya's own UI containers only ever held `ui_pl022_unique_icon00`. The generic
gauge controller binds `ui_cha_unique_gauge00_L` and `ui_gauge_line00`; if those
logical names are not in **his** resource group the lookup returns an empty
handle and the game null-derefs at RVA `0x2072D2` during match load.

Twelve files copied, **six** in-place substitutions total (three per side):

```
ui/script/scene/ActionUniquePl022_{0,1}.bin        <- ActionUniquePl038_*
ui/script/anim/ActionUniquePl022_{0,1}.bin         <- idem
ui/ui_ActionUniquePl022_{0,1}_{mot,fnt}.cat        <- idem
00HIGH/ui/ui_ActionUniquePl022_{0,1}_mdl.cat       <- idem
01MIDDLE/ui/ui_ActionUniquePl022_{0,1}_mdl.cat     <- idem
```

**The substitution rule is load-bearing:**

| token | meaning | action |
|---|---|---|
| `Pl038` uppercase | container identity (`ui_ActionUniquePl038_0_mdl`) | **substitute** |
| `pl038` lowercase | internal asset name (`ui_pl038_unique_icon_L00`) | **preserve** |

The lowercase form appears in the `.cat`'s plaintext CSV manifest at offset
`0x22f` and names the geometry stored inside the container. Renaming it makes
the manifest advertise a name the container does not hold → empty handle →
crash. This is the same reason Bergen's shipped pl005 assets still carry
pl038-named icon nodes (ZANGETSU_MASTER_GUIDE §5.4).

`"ActionUniquePl038_0"` and `"ActionUniquePl022_0"` are both 19 chars, so the
edit is length-preserving. `ActionUniqueCom_0` (17 chars) would not have been —
that is why pl038 is the donor and not the generic Com set.

No `Fnames/filename.bin` or `file_exist.htable` work is needed: Byakuya's
containers are already registered, only their **contents** change.

Tool: `clone_gauge_pl038_to_pl022.py --inspect | --apply | --revert`.

**Hard dependency:** the cloned files and the `db 17` patch go together, always.
Either one alone crashes:

| files | `db 17` | result |
|---|---|---|
| cloned | active | works |
| original | active | crash `0x2072D2` at match load |
| cloned | inactive | crash — Pl22 class looks for its now-missing icon |
| original | inactive | vanilla, icon visible |

### 1.2 Data side — tadjpkg `[V]`

`pl022.tadjpkg`, 1,492,899 bytes, 212 entries. **One** edit from Nils's original
(md5 `ee327f85817c9adec89f4ae5dcda7ca2`): petal attacks `-0.25000` → `-0.10000`
(both 8 chars, in place, no offset rebuild).

The `max_val = "1340.000000"` timers are left **untouched**.

Relevant records:

| entry | idx | add | is_val_set | is_start_timing | is_end_reset | writes to |
|---|---|---|---|---|---|---|
| `1_normal_ct_ct_evolve` (+`_cos1`) | 1 | +1.000 | see note | 1 | 0 | see note |
| `2_evo_attack_evo_atk_lo01/02/03` | 1 | −0.100 | 0 | 1 | 0 | `chara+0x1A40` |
| `2_evo_attack_evo_atk_lo04/05/06` | 1 | +0.250 | 0 | 1 | 0 | `chara+0x1A40` |

**`is_val_set` selects the destination bank** `[V]` — established by live
measurement, not by reading the handler:

- `is_val_set = 1` → writes `chara+0x1A34`
- `is_val_set = 0` → writes `chara+0x1A40`

Note on `ct_evolve`: the current shipped file has `is_val_set = 0`, so it
accumulates `+1.0` into `1A40` rather than setting `1A34`. Since FEED 1 clamps
`1A40` to `[−1, 0]`, that `+1.0` is immediately clipped to zero and does
nothing. The baseline of `1.0` comes from FEED 1 forcing `1A34 = 1.0` every
frame instead. It works, but by accident rather than by design — worth
normalising if the tadj is ever regenerated.

**None of the eight `AddUniqueVal` records carry a condition.** No `str_a`
gate, no `ENHANCED` check. They fire unconditionally whenever their action
plays. The stance distinction lives entirely in the tcmb (see §3.4).

### 1.3 SCRIPT 1 — the controller switch byte

```
[ENABLE]
BLEACH_Rebirth_of_Souls.exe+21FF64:
  db 17

[DISABLE]
BLEACH_Rebirth_of_Souls.exe+21FF64:
  db 09
```

### 1.4 SCRIPT 2 — resource-handle guard (mandatory)

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
> | guard | result |
> |---|---|
> | on, `+0x38` and `+0x40` cleared | `0xC0000005` at `0x8B06D0` **leaving a mode** |
> | off | `0xC0000005` at `0x927E6` on SP1 |
> | on, `+0x40` only | neither — shipped in `8a44ba7`, confirmed in game |
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

### 1.5 FEED 1 — function entry (must be enabled BEFORE feed 2)

```
[ENABLE]
alloc(sgcode,1000,BLEACH_Rebirth_of_Souls.exe+48C390)
alloc(sgdata,400)
label(sg_done)
label(sg_nozero)
label(sg_x5)
label(sg_x6)
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
  dd (float)-1.0
  dd 0
  dd 0
  dd 0
  dd 0
  dd 0
  dd 0
  dd 0
  dd 0
  dd 0
  dd 0
  dd 0

sgcode:
  push rax
  push rcx
  push rdx
  push r10
  pushfq
  sub rsp,40
  movups [rsp+00],xmm3
  movups [rsp+10],xmm4
  movups [rsp+20],xmm5

  mov r10,sgdata
  mov eax,[rcx+00000C00]
  mov [r10],eax
  cmp eax,16
  jne sg_done
  mov eax,[rcx+00000C20]
  cmp eax,2
  jae sg_done
  inc dword ptr [r10+04]
  mov [r10+24],rcx

  movss xmm3,[rcx+00001A40]
  movss xmm4,[r10+20]
  maxss xmm3,xmm4
  xorps xmm5,xmm5
  minss xmm3,xmm5
  movss [rcx+00001A40],xmm3

  mov dword ptr [rcx+00001A34],3F800000
  movss xmm3,[rcx+00001A34]
  addss xmm3,[rcx+00001A40]
  xorps xmm4,xmm4
  maxss xmm3,xmm4
  movss xmm4,[r10+10]
  minss xmm3,xmm4
  movss [r10+0C],xmm3

  xorps xmm4,xmm4
  comiss xmm3,xmm4
  ja sg_nozero
  and byte ptr [rcx+00001098],FE
sg_nozero:
  movss xmm4,[r10+14]
  maxss xmm3,xmm4

  mov rdx,rcx
  lea rax,[BLEACH_Rebirth_of_Souls.exe+1CDE758]
  movsxd rcx,dword ptr [rdx+00000C20]
  mov rcx,[rax+rcx*8]
  test rcx,rcx
  je sg_done
  mov rcx,[rcx+00000200]
  test rcx,rcx
  je sg_done
  mov rax,[rcx+00000010]
  test rax,rax
  je sg_x5
  mov rdx,[rax]
  test rdx,rdx
  je sg_x5
  mov rcx,[rax+08]
  sub rcx,rdx
  mov [r10+40],ecx
  cmp rcx,240
  jb sg_x6

  mov [r10+48],rdx
  inc dword ptr [r10+08]
  movss [rdx+0000009C],xmm3
  jmp sg_done

sg_x5:
  inc dword ptr [r10+38]
  jmp sg_done
sg_x6:
  inc dword ptr [r10+3C]

sg_done:
  movups xmm5,[rsp+20]
  movups xmm4,[rsp+10]
  movups xmm3,[rsp+00]
  add rsp,40
  popfq
  pop r10
  pop rdx
  pop rcx
  pop rax

  mov rax,rsp
  push rbp
  push rbx
  jmp BLEACH_Rebirth_of_Souls.exe+48C395

BLEACH_Rebirth_of_Souls.exe+48C390:
  jmp sgcode

[DISABLE]
BLEACH_Rebirth_of_Souls.exe+48C390:
  db 48 8B C4 55 53

unregistersymbol(sgdata)
unregistersymbol(sgcode)
dealloc(sgdata)
dealloc(sgcode)
```

`sgdata` layout:

| offset | contents |
|---|---|
| `+0x00` | last character id seen |
| `+0x04` | frames processed |
| `+0x08` | writes performed |
| `+0x0C` | computed value (what gets displayed) |
| `+0x10` | clamp high = 1.0 |
| `+0x14` | epsilon = 0.001 |
| `+0x20` | clamp low = −1.0 |
| `+0x24` | `Chara*` |
| `+0x38` | exit count: element vector null |
| `+0x3C` | exit count: vector smaller than one element |
| `+0x40` | vector byte size |
| `+0x48` | **element pointer, handed to FEED 2** |

### 1.6 FEED 2 — rewrite after the native push

```
[ENABLE]
alloc(sg2code,400,BLEACH_Rebirth_of_Souls.exe+48CC5B)
label(sg2_done)
registersymbol(sg2code)

sg2code:
  push rax
  push rdx
  pushfq
  mov rax,sgdata
  mov rdx,[rax+48]
  test rdx,rdx
  je sg2_done
  mov eax,[rax+0C]
  mov [rdx+0000009C],eax
sg2_done:
  popfq
  pop rdx
  pop rax
  mov dword ptr [rsp+30],0
  jmp BLEACH_Rebirth_of_Souls.exe+48CC63

BLEACH_Rebirth_of_Souls.exe+48CC5B:
  jmp sg2code
  nop
  nop
  nop

[DISABLE]
BLEACH_Rebirth_of_Souls.exe+48CC5B:
  db C7 44 24 30 00 00 00 00

unregistersymbol(sg2code)
dealloc(sg2code)
```

### 1.7 Why TWO feeds — the crux of the whole problem

This is the single least obvious part of the solution and the thing that cost
the most time.

**FEED 1 at `0x48C390`** is the entry of the per-frame enhance update function.
It runs every frame **regardless of stance**. It does the maths, forces sword at
zero, and writes the value.

**But in petal stance it is not enough.** When the enhance bit is set, the
native loop further down the same function runs and calls `SetRate` at
`0x48CC58`, which overwrites `elem+0x9C` with the timer ratio. Our value from
the function entry is clobbered ~2000 instructions later in the same frame.

**FEED 2 at `0x48CC5B`** sits immediately after that native `call` and writes
our value again. Now we are last.

The mirror image explains the symptom history exactly:

| stance | enhance bit | native loop | who writes last |
|---|---|---|---|
| sword | 0 | **skipped** (guard `test [rsi+0x1098],ebx`) | FEED 1 → correct |
| petal | 1 | runs, calls `SetRate` | without FEED 2: the timer; with FEED 2: us |

Every intermediate build had exactly one of the two stances working, and we
kept diagnosing it as a rendering problem.

### 1.8 Enable order and verification

**Order matters:** script 1 → handle guard → FEED 1 → FEED 2. FEED 2 references
the `sgdata` symbol that FEED 1 creates; enabling it first fails with
`This instruction can't be compiled` on `mov rax,sgdata`.

```lua
local mb = getAddress("BLEACH_Rebirth_of_Souls.exe")
print(string.format("48C390=%02X (E9)  48CC5B=%02X (E9)  92790=%02X (E9)  21FF64=%02X (17)",
  readBytes(mb+0x48C390,1,true)[1], readBytes(mb+0x48CC5B,1,true)[1],
  readBytes(mb+0x92790,1,true)[1], readBytes(mb+0x21FF64,1,true)[1]))
```

**`E9` matters.** An unconstrained `alloc` makes CE emit a 14-byte `FF 25`
indirect jump that silently destroys the following instructions. Every `alloc`
in these scripts passes a near-address for exactly this reason. This bit us
once: the first DebugPrint probe was posted as `FF 25`, destroying two
instructions, and would have crashed on its first invocation — it never fired,
which is the only reason it went unnoticed.

### 1.9 Live telemetry

```lua
LOGPATH = "D:\\sakura.txt"
if kTimer then kTimer.destroy(); kTimer = nil end
local b = getAddressSafe("sgdata")
if not b then print("sgdata absent"); return end
local f = io.open(LOGPATH, "a")
f:write("\n== session ==\n"); f:flush()
local prev
print("Sonde active. Log : " .. LOGPATH)
kTimer = createTimer(nil)
kTimer.Interval = 25
kTimer.OnTimer = function()
  local ok, rsi = pcall(readQword, b + 0x24)
  if not ok or not rsi or rsi == 0 then return end
  local a40 = readFloat(rsi + 0x1A40)
  local bm  = readInteger(rsi + 0x1098)
  local val = readFloat(b + 0x0C)
  local key = string.format("%.3f|%d|%.3f", a40, bm, val)
  if prev ~= key then
    prev = key
    local l = string.format("f=%d  ecr=%d  1A40=%.3f  bm=%X  val=%.3f  vec=%d",
      readInteger(b+4), readInteger(b+8), a40, bm, val, readInteger(b+0x40))
    f:write(l.."\n"); f:flush(); print(l)
  end
end
```

`bm` is the stance tell: `1` = petal (enhanced), `0` = sword.

---

## PART 2 — ARCHITECTURE

### 2.1 The two-switch unique-UI system `[V]`

There are **two independent switches**, both indexed by `uiId`, both with
identical 51-entry byte tables, index = `uiId − 2`. Byakuya is `uiId 22` →
index `0x14`.

| | function | byte table | Byakuya's byte | selects |
|---|---|---|---|---|
| A | `0x14021CD90` | VA `0x14021D994`, RVA `0x21D9A8` | `0x09` | **layout name** |
| B | `0x14021EE30` | VA `0x14021FF50`, RVA `0x21FF64` | `0x09` | **controller class** |

- case `0x09` = the `Pl22` icon-only class
- case `0x17` = the **default** case: generic gauge controller
  (vtable `0x14143FA50`, 36 methods) + `ActionUniqueCom_` layout
- 28 of 51 characters sit on case `0x17`, including Unohana (pl019)

Switch B dispatch, decoded:

```
0x14021EE95  lea eax,[rcx-2]                    ; rcx = uiId
0x14021EE98  cmp eax,0x32
0x14021EE9B  ja  0x14021FE63                    ; out of range -> DEFAULT
0x14021EEAA  movzx eax,byte [rdx+rax+0x21FF50]  ; byte table
0x14021EEB2  mov   ecx,dword[rdx+rax*4+0x21FEF0]; jump table
0x14021EEBC  jmp   rcx
```

The factory returns **one** object, stored in a single pointer:

```
0x14021E17D  call 0x14021EE30
0x14021E185  mov [rcx+0x200],rax     ; no list
```

**`uiId` is not the fighter id** `[V]` (also Bergen §3.1):

```
0x14021DAF5  movsxd rax,[obj+0x1F0]              ; fighter id
             mov    eax,[table + rax*0x50 + 0x38]
             mov    [obj+0x1F8],eax              ; uiId <- what both switches index
```

For pl005 and pl022 the two happen to coincide. Do not assume it in general.

**Only switch B may be patched for Byakuya.** Patching switch A renames his
layout to `ActionUniqueCom_`, so his resource group becomes
`UIActionUniqueCom_0`; resources are keyed by `hash(groupName, logicalName)`, so
everything still resolving under `UIActionUniquePl022_0` returns an empty
handle → hard crash on the SP1. Verified the hard way. `[V]`

This is also why Byakuya needs none of pl005's 25th-case work: pl005 sat on the
**default** case in switch A and had no layout of his own, which is why Bergen
had to relocate a dword table into a cave. Byakuya already owns a layout.

### 2.2 The gauge IS the enhance timer `[V]`

The single most reframing discovery, and the reason every data-only attempt
failed for weeks.

Function `0x14048C390`; loop region `0x14048CBD8`–`0x14048CCED`, **3 iterations**
(one per enhance level):

```
0x48CBD8  mov ebx,1                    ; loop top
0x48CBDD  lea rdi,[rsi+0x1A10]         ; rsi = Chara
0x48CBF0  movss xmm0,[rdi+0xC]         ; max; if <= 0 -> skip level entirely
0x48CBFE  test  [rsi+0x1098],ebx       ; level bit; if clear -> SKIP
0x48CC0A  cmp   [rsi+0xC00],4          ; fighter id 4 excluded from HUD push
0x48CC17  divss xmm6,xmm0              ; ratio = remaining / max
0x48CC22  mov rcx,[r15+r12*8+0x1CDE758]; g_battleUi[ [rsi+0xC20] ]
0x48CC32  call [rax+0x48]              ; predicate on the HUD object
0x48CC46  mov rcx,[rcx+0x200]          ; the gauge controller
0x48CC58  call [rax+0x50]              ; SetRate(ratio)  <- native push
0x48CC5B  mov dword [rsp+0x30],0       ; <- FEED 2 HOOK SITE
0x48CC87  movss [rdi],xmm0             ; remaining -= dt
0x48CCD6  call [rax+0x50] with 0.0     ; on hitting zero: push 0 ...
0x48CCDE  call 0x140474890             ; ... then ClearEnhance
```

Consequences that shaped everything:

- **`max_val = -1` kills the tick, the native push and the auto-hide at once**,
  but also means `ClearEnhance` never fires
- **the bar is invisible until an enhance level is armed** — this is why
  Unohana's bar only appears in evo once she has generated blood; not a bug
- **the loop is skipped entirely when the level bit is clear** — which is what
  made a hook at `0x48CC5B` stop running in sword stance

### 2.3 Memory map — Chara `[V]`

| offset | meaning |
|---|---|
| `+0x0C00` | character id (Byakuya = 22 / `0x16`) |
| `+0x0C20` | HUD slot (0 or 1) |
| `+0x1094` | **evo flag**, NOT stance — reads `1` in both petal and sword |
| `+0x1098` | enhance bitmask, bit0 = level 1 — **this IS the stance tell**: `1` = petal, `0` = sword |
| `+0x1A10 + 4i` | enhance level *i* remaining |
| `+0x1A1C + 4i` | enhance level *i* max (`1340` for pl022) |
| `+0x1A34` | `AddUniqueVal` bank when `is_val_set = 1` |
| `+0x1A40` | `AddUniqueVal` bank when `is_val_set = 0` — attacks land here |

Displayed value = `clamp(0,1)( [0x1A34] + clamp(−1,0)([0x1A40]) )`.

### 2.4 Memory map — gauge object chain `[V]`

```
g_battleUi        = 0x141CDE758, 2 entries, indexed by [chara+0xC20]
gauge controller  = [ g_battleUi[slot] + 0x200 ]      single pointer
element vector    = [ controller + 0x10 ]             std::vector begin/end/cap
element stride    = 0x240
measured size     = 576 bytes = EXACTLY ONE element
```

Within one element, from the init at `0x140207050`:

```
element+0x00   slot 1 -> ui_cha_unique_gauge00_L   (attach at 0x140207226)
element+0x48   slot 2 -> ui_gauge_line00           (attach at 0x14020728E)
element+0x68   = 0x48 + 0x20 = slot 2's object pointer
element+0x90   state: 1 = normal, 5 = hidden (written by vtbl[0x118])
element+0x98   flags, observed 0x101
element+0x9C   *** THE DISPLAYED RATE — this is what to write ***
element+0xA0   reference/max, init 1.0, read by vtbl[0xD0]
element+0xB0..0xFC   RGBA colour blocks
```

Slot layout is `0x48` bytes with the real object pointer at slot+`0x20`;
`0x140095410` is the attach helper (copies fields `0x00..0x40`, releases the
previous occupant).

### 2.5 `SetRate` internals `[V]`

`vtbl[0x50]` = `0x1402089B0`. **Not a plain setter.**

```
vtbl[0xD0]  -> reads [elem+0xA0] and MULTIPLIES
vtbl[0x88]  -> predicate = [ [this+8] + 0x3C ]
vtbl[0x118] -> writes [elem+0x90] = 5  (hidden)  when the rate is zero
```

Instrumented capture of a live `SetRate` (copy of the whole element before and
after the native call) showed it modifies **exactly one field**: `elem+0x9C`.
That single measurement is what unlocked the direct-write approach.

`vtbl[0xC0]` = `0x140208300` is the raw writer used by the factory:
`movss [elem_base + idx*0x240 + 0xA0], xmm1`.

### 2.6 Controller classes `[V]`

| vtable | slot 1 (init) | creates |
|---|---|---|
| `0x14143FA50` | `0x1402086F0` | gauge only — **this is case 0x17** |
| `0x14143FDC8` | `0x140208BD0` | gauge **+ `ui_com_unique_icon00`** — not reachable from the factory |

Both have 36 methods. `Pl22`'s vtable `0x1414405C8` has only 24, which is why
`+0xC0` fell outside it — the original "no setter" blocker, now moot.

Logical names bound by each case:

| case | asks for |
|---|---|
| `0x12` (pl038) | `ui_cha_unique_gauge00_L`, `ui_gauge_line00`, **`ui_pl038_unique_icon_L00`** |
| `0x17` (default) | `ui_cha_unique_gauge00_L/_R`, `ui_gauge_line00` — **shared names only** |

Case `0x17` was chosen precisely because it binds no per-character literal, so
there is no coupling of the kind Bergen warns about in §5.3.

---

## PART 3 — THE tcmb, AND WHERE STANCE ACTUALLY LIVES

### 3.1 Format `[V]`

`pl022.tcmbpkg` is **plain JSON**, not a packed binary — unlike `.tadjpkg` and
`.tactpkg`. Two quirks make naive parsing fail:

- **trailing commas** before `}` and `]` (strip with
  `re.sub(r",(\s*[}\]])", r"\1", text)`)
- **cp932 encoding**, not UTF-8

Root keys: `header`, `variable`, `combo`. `combo` contains two tables: `combo`
(base form) and `evo_combo`.

### 3.2 DUPLICATE JSON KEYS — critical parsing trap `[V]`

`evo_combo` contains **103 entries but only 83 unique names**. Twenty names are
duplicated: `atk_lo01`, `atk_lo02`, `atk_hi01`, `atk_hi03`, `atk_hi04`,
`atk_ex01`, `atk_ex02`, `atk_ex04`, `atk_gr01`, `atk_gr02_1`, `sp_atk01`,
`sp_atk03`, `ct_sp_break01`, `ct_sp_break02`, `sp_break01_maxout`,
`sp_break02_maxout`, `atk_hi03_1`, `atk_hi03_2`, `sp_overatk01_d1`,
`sp_overatk01_u1`.

`json.loads` silently keeps only the **last** one. This produced two wrong
conclusions before it was caught — including a patch script that edited the
wrong node.

**Always parse with `object_pairs_hook=lambda p: p`** to preserve duplicates.
Nodes are identified by `_uniqueID`, not by name.

A second trap: a naive text search for `"atk_lo01": {` finds the node in the
**`combo`** (base form) table first, because it appears earlier in the file.
Scope any text search to after the `"evo_combo"` marker.

### 3.3 The `enhance` variable — stance gating `[V]`

Variables are declared in `variable` and referenced **positionally** in each
node's `variables` array. Declaration order (index):

```
0 in_stepdash        1 in_powerup          2 cost                3 is_before_hit
4 check_high_area    5 charge_rate         6 enhance             7 reiryoku_cost
8 kikon_ex           9 clash_parry_type   10 is_vaild_bomb      11 combo_route_id
12 act_frame_min    13 act_frame_max      14 hit_combo_stop     15 guard_combo_stop
16 unique_combo     17 no_reaction_reject 18 chara_combo_id     19 story_combo_id
20 atk_syunpo_short_cut  21 sp_over_atk_short_cut  22 reverse_mode
```

**`enhance` semantics** (from the memo, corroborated by the data):

| value | meaning |
|---|---|
| `0` | no condition — always available |
| `1` | available **only in the enhanced state** |
| `-1` | available **only in the non-enhanced state** |

It is a **filter**, not an action. Changing it cannot set or clear any state,
and therefore cannot cause a stance change by itself.

### 3.4 The two parallel move sets `[V]`

The mod already implements stance as two gated move sets:

| `enhance = 1` (petal) | `enhance = -1` (sword) |
|---|---|
| `atk_da01` (52) | `atk_da02` (172) |
| `atk_hi01` (163), `atk_hi02` (86) | `atk_hi04` (171), `atk_hi05` (181) |
| `atk_ex01` (159) | `atk_ex04` (182) |
| `sp_atk01` (117), `sp_atk02` (127) | `sp_atk03` (169), `sp_atk05` (178) |
| `sp_step_atk01` (150) | `sp_step_atk03` (173) |
| `atk_lo01` (**63**) | `atk_lo04` (165) |
| | `atk_gr07` (177) |

And the light-attack routing:

```
start_lo (62) ──┬── atk_lo01 (63)   enhance = 1   -> lo01 -> lo02 (83) -> lo03 (105)
                └── atk_lo04 (165)  enhance = -1  -> lo04 -> lo05 (166) -> lo06 (167)

atk_lo01 (161)  enhance = 0   <- reachable only from atk_ex01 (72) / atk_ex02 (138)
atk_lo02 (162)  enhance = 0   <- chain resumption after an EX, deliberately ungated
```

**The tcmb routing is correct as shipped.** Only the chain-entry node carries
the gate; downstream nodes inherit reachability through `nexts`. The duplicate
ungated `atk_lo01` (161) is not a bug — it is the post-EX chain resumption,
intentionally available in both states.

This was misdiagnosed twice: once as "the tcmb never routes to lo04", once as
"lo01 is ungated and always wins". Both came from reading the JSON with
duplicate keys collapsed.

---

## PART 4 — CRASH CATALOGUE

Every crash seen, with cause where known. Fault offsets are RVAs, straight from
the Windows Application event log.

| RVA | code | trigger | cause |
|---|---|---|---|
| `0x2072D2` | `C0000005` | match load | `ui_gauge_line00` not in Byakuya's resource group. `0x140237260` zero-fills the 0x48-byte handle on a name miss (`0x14023733A..0x140237359`), leaving a null object pointer at slot+0x20. Fixed by the pl038 clone. |
| `0x927E6` | `C0000005` | stance SP1 | `lock inc dword ptr [rax+0xc]` in the engine-wide resource-handle **copy constructor** `0x140092790`, with `rax = -1`. The function already guards the NULL case but not an INVALID one. Contained by SCRIPT 2. Also the guaranteed result of patching switch A. |
| `0x227980` | `C0000005` | intermittent, SP1 | virtual call on an object whose vtable is dead. Never root-caused; disappeared with the current build. |
| `0x1CC33C` | `C0000005` | after a `SetRate` with a real value | CRC name-hash reading `[r12+0x1B38]` with `r12` invalid. `SetRate` triggers resource work when the rate is non-trivial; it did nothing while we were pushing a 0.02 floor. |
| `0x22A547` | `C0000005` | own bug | same name-hash function; caused by a bad `div` clobbering `rax` in one of my scripts. |
| `0xA75E60` | `C0000005` | reproducible | `SteamInternal_ContextInit` returns a context whose interface pointer is null. Almost certainly the launcher starting the exe outside Steam. **Never confirmed** — the control test was never run. `[?]` |
| `0x10CA21D` | `C0000409` | various | `int 0x29` with `ecx = 7` = `__fastfail` = plain `abort()`. Not a memory bug; a consequence of something upstream. Present in logs predating all of this work. |
| `0x207510` | `C0000005` | SP1 | caused by writing `[chara+0x1A1C] = 0` from the hook: forcing the enhance max to zero mid-transition tears down the UI while it is being rebuilt. |
| `0x8D4650` | `C0000005` | unknown | never investigated. |
| `0x7FF6387B0133` | `C0000005` | "module: unknown" | execution left every loaded module — a script of mine dereferenced the quotient of a `div` as a pointer. |

---

## PART 5 — EVERYTHING THAT FAILED

Kept in full because re-trying these is the main way to waste a day.

| attempt | outcome |
|---|---|
| Patch switch A as well as B | crash `0x927E6` on the SP1 — group/hash mismatch |
| Copy `ActionUniqueCom_*` over Byakuya's scene files | cannot work: the scene's internal refs (`ui_ActionUniqueCom_0_mdl` etc.) resolve inside *his* group, where they do not exist |
| `max_val = "-1.00000000"` in the tadj | crash. The engine writes `"-1.000000"` (9 chars) everywhere; the 11-char form is not parsed. `"99999999.00"` is the length-matched alternative if the timer ever needs killing from data |
| `ct_evolve` `is_val_set` 1 → 0 to unify the banks | attack writes stopped entirely |
| Write `[elem+0xA0]` with no bounds check | **heap corruption**. Crashes appeared at four different addresses across *later* sessions and created a convincing illusion of regression. The vector can be empty with a perfectly valid `begin` pointer; always check `end - begin >= 0x240` |
| Write `[chara+0x1A10] = value × max` | the native loop overwrites `remaining` two instructions later |
| `mov dword [rcx+0x1A1C],0` to kill the timer | crash `0x207510` during the SP1 |
| `call vtbl[0xC0]` instead of `vtbl[0x50]` | no display change |
| `and [rsi+0x1098],FE` every frame while the value is zero | erases the enhance bit the SP1 has just set — evo never engages. Only safe once `1A34` is force-armed to 1.0 so the sum is non-zero until the bar is genuinely empty |
| Gate the hook on `cmp ebx,1`, believing `ebx` was the level counter | `ebx` is not the level counter at `0x48CC5B`; crashed |
| Hook at `0x48CC5B` only | works in petal, dead in sword — the loop is skipped when the enhance bit is clear |
| Hook at `0x48C390` only | works in sword, overwritten by the native `SetRate` in petal |
| DebugPrint probe at `0x140090840` (150 call sites) | **zero** records in both a healthy and a crashing session. Not a failure — it eliminated every *signalled* failure mode at once |
| CE breakpoints | unusable. `406D1388` thread-naming exceptions flood the VEH debugger during load; the game also dies if paused |

---

## PART 6 — METHODOLOGY, LEARNED THE HARD WAY

**Heap corruption does not surface in the session that causes it.** One
unbounded `movss [rax+0xA0]` produced crashes at four unrelated addresses across
later sessions and made a working checkpoint look broken. When a crash looks
inexplicable, close the game *and* Cheat Engine before concluding anything.

**The launcher rewrites the environment on every run.**
`Quick_Launch_Community_Patch.py` does `git fetch` + `reset --hard origin/main`
+ `clean -fd`, then copies `Files/Matchmaking/dinput8.dll` into the game folder.
A locally built DLL is silently replaced; local edits vanish.
`BalanceLeadTools/DevToken.txt` bypasses the git half. To work on a branch,
also set `branch.<name>.remote = .` and `branch.<name>.merge =
refs/heads/<name>` so the launcher's `git pull` is a harmless no-op.

**Two `GameVersions` trees exist**: `Community Patch` and `Community Patch CRE`.
The launcher reads the **former**. Editing the latter silently tests nothing.

**The Windows Application event log is the fastest crash oracle on this game.**
`Fault offset` is the RVA directly. It resolved `0x2072D2` and `0x927E6` in
seconds after breakpoints had wasted an hour. Always check the **timestamp** —
re-reading a stale entry sent us chasing a crash that had not happened.

**Measure between changes, one variable at a time.** The worst stretches came
from changing the tadj and the hook offset in the same round, then being unable
to attribute the result. The instrumented element dump settled in one run what
four consecutive guesses had not.

**Prefer reading the source of truth to inferring from symptoms.** Bergen's
guide gave the two-switch architecture in one section. The tcmb gave the stance
gating in one query. Both were asked for far too late — hours were spent
inferring what a file would have stated outright.

**Instrumentation over breakpoints, always, on this title.** Write to an
allocated ring buffer and drain it from a CE Lua timer to disk every 25 ms; the
log then survives the crash. Never call game functions from a probe if a plain
memory read will do.

**Watch out for a compromised probe.** Adding registers to save, or a `div` that
clobbers `rax`, turned two diagnostic scripts into the crash they were meant to
observe. A probe that only reads and writes to its own buffer is almost
impossible to get wrong.

---

## PART 7 — STILL OPEN

1. **The enhance timer still runs internally.** `max_val = 1340` is untouched,
   so `ClearEnhance` should still fire at ~22 s and flip the stance. FEED 2
   masks it visually. Not re-tested since the final build. `[?]`
2. **The handle guard is containment, not a fix.** Something still produces a
   dead resource handle on the stance-change path. Instrumentation caught it
   being copied from RVA `0x20FC4A`, a directly-called animation trigger. Some
   asset silently fails to load. `[?]`
3. **Performance.** The guard sits on an engine-wide hot path — 142M calls
   measured in one session, 1 handle neutralised. Frame-time impact has never
   been measured. **Do that before shipping.**
4. **DLL port.** `patch_byakuya_gauge_switch()` and
   `patch_byakuya_handle_guard()` exist in `dinput8_proxy.c` behind
   `ENABLE_BYAKUYA_GAUGE`, with `patch_byakuya_evo_icon()` made mutually
   exclusive. The two feeds are **not** ported. Note that Bergen's
   `exe_patch.recipe` already writes a hook at fo `0x48BFD8` = RVA `0x48CBD8` —
   the enhance-loop top — for pl005. Our sites (`0x48C390`, `0x48CC5B`) do not
   collide, and neither do our switch bytes (index `0x14`) with his (index 3),
   but this must be re-checked before shipping.
5. **The twelve cloned UI files must be committed** under `GameVersions/...` or
   every player who picks Byakuya crashes at match load.
6. **Desired behaviour not yet implemented:** entering evo should put Byakuya
   directly into petal stance with a full bar.
7. **Balance:** petal drain is `-0.10` (10 hits to empty), sword gain `+0.25`.
   Both are plain ASCII in the tadj and length-editable (`-0.10000`,
   `0.250000` — keep the character count identical).

---

## PART 8 — QUICK REFERENCE

```
exe                 BLEACH_Rebirth_of_Souls.exe 1.3.0.0
                    md5 7b21356622f2fe8d4a1733e74634abd8, 28,283,464 bytes
.text file offset   RVA - 0xC00

switch A byte tbl   VA 0x14021D994   Byakuya RVA 0x21D9A8   *** NEVER PATCH ***
switch B byte tbl   VA 0x14021FF50   Byakuya RVA 0x21FF64   09 -> 17
switch A fn         0x14021CD90
switch B fn         0x14021EE30
jump table (B)      0x14021FEF0
default case        0x14021FE63

g_battleUi          0x141CDE758  (2 entries, index = [chara+0xC20])
generic vtable      0x14143FA50  (36 methods)
Pl22 vtable         0x1414405C8  (24 methods)
SetRate             vtbl[0x50] = 0x1402089B0
raw writer          vtbl[0xC0] = 0x140208300
hide routine        vtbl[0x118]
init with gauge     0x140207050
gauge helper        0x1402086F0
create element      0x140206A30
attach (destructive)0x140095410
name lookup         0x140237260 / 0x1402373B0
handle copy ctor    0x140092790   crash at +0x56 = 0x927E6
AddUniqueVal write  0x1403B2BB3   (handler 0x1403B2AD0)
enhance update fn   0x14048C390   loop 0x48CBD8..0x48CCED
DebugPrint          0x140090840   (150 call sites)

HOOK SITES USED
  0x48C390   5 bytes   48 8B C4 55 53              FEED 1
  0x48CC5B   8 bytes   C7 44 24 30 00 00 00 00     FEED 2
  0x92790    6 bytes   48 8B 02 48 89 01           handle guard

CHARA OFFSETS
  +0xC00   character id (Byakuya = 0x16)
  +0xC20   HUD slot
  +0x1094  evo flag (NOT stance)
  +0x1098  enhance bitmask — bit0: 1 = petal, 0 = sword
  +0x1A10  enhance remaining
  +0x1A1C  enhance max
  +0x1A34  AddUniqueVal bank, is_val_set = 1
  +0x1A40  AddUniqueVal bank, is_val_set = 0

ELEMENT (stride 0x240, one element = 576 bytes)
  +0x00   slot 1: ui_cha_unique_gauge00_L
  +0x48   slot 2: ui_gauge_line00
  +0x90   state (1 normal, 5 hidden)
  +0x98   flags (0x101)
  +0x9C   *** displayed rate — write here ***
  +0xA0   reference/max (1.0)
```
