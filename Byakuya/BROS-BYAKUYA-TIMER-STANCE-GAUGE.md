# BYAKUYA — BASE FORM STANCE GAUGE

**Game:** BLEACH Rebirth of Souls 1.3.0.0
**Character:** Byakuya, `pl022`, chara id `0x16`
**Status:** working, validated in game

---

## 1. What this setup does

| Situation | Gauge |
|---|---|
| Base form, sword stance (not enhanced) | hidden |
| Base form, petal stance (enhanced) | full |
| Evo form, either stance | native timer, untouched |

No icon is displayed. That is a deliberate choice, not a limitation of the setup — see §7.

---

## 2. Origin of the problem

The mod starts from a `pl038 → pl022` UI asset clone that gives Byakuya a unique gauge he does not have in vanilla. That clone is **destructive**: Byakuya's UI containers are replaced by pl038's, and the lowercase `pl038` logical names are preserved inside them.

Direct consequence: `ui_pl022_unique_icon00` no longer exists in his resource group. His vanilla icon can therefore never be displayed, whatever controller class is selected.

The second problem is that the UI controller class is chosen **once only, at match load**, by a 51-byte table indexed by `uiId - 2`. Byakuya has `uiId` 22, so index 20, whose vanilla value is `0x09`. There is no mid-match switch without rebuilding the object.

---

## 3. The controller classes involved

Three table cases matter here. Their identity is readable in the RTTI, at address `vtable - 8`.

| Case | vtable | RTTI class | Contents |
|---|---|---|---|
| `0x09` | `0x1414405C8` | `ActionCharaUniqueUI_Pl22` | icon only |
| `0x12` | `0x14143FB78` | `ActionCharaUniqueUI_Pl38` | gauge **and** icon |
| `0x17` | `0x14143FA50` | `ActionCharaUniqueUICom` | gauge only |

`Com` and `Pl38` share the same 36-method layout and the same element vector. `Pl22` is a 24-method class with a 0x50-byte sub-object at `+0x10` — a runtime switch to it is out of the question.

### Why `Com` and not `Pl38`

`Pl38` is tempting: it displays a gauge **and** an icon, and the cloned assets already carry the `ui_pl038_unique_icon_L00 / _R00` names it looks up. Tested in game, it works — pl038's icon appears, the gauge follows the stance.

It was nevertheless dropped, for a precise reason. Compare slot `0x50` (`SetRate`, the entry point of the native timer):

```
Com::SetRate  (0x1402089B0)          Pl38::SetRate (0x140208360)
  call [rax+D0]   ; writes the value    mov rax,[rcx]
  call [rax+88]   ; predicate            xor r8d,r8d
  call [rax+60] / [rax+68]              jmp [rax+D0]   ; and nothing else
  mov byte [rcx+98],0
  jmp [rax+118]   ; HIDE
     ... or ...
  jmp [rax+100]   ; SHOW
```

`Com::SetRate` handles the automatic display of the gauge. `Pl38::SetRate` is a bare thunk that writes the value and nothing more. Switching to case `0x12` means the evo timer keeps pushing its ratio into the element — but nothing ever makes the gauge visible again. **The evo timer disappears.**

This is fixable in the script (a visibility branch for evo) or by repointing `exe+143FBC8` to `0x1402089B0`, but as long as no icon is wanted, `Com` does the job for free.

---

## 4. Target data structure

```
g_battleUi[slot]                 exe+1CDE758, indexed by [Chara+0xC20]
  +0x200  -> UI controller
              +0x00  vtable
              +0x10  -> element vector   [begin, end]
                          element[0]  stride 0x240
```

Useful fields of `element[0]`:

| Offset | Type | Role |
|---|---|---|
| `+0x90` | dword | display mode — `1` visible, `5` hidden |
| `+0x9A` | byte | refresh flag, set to `1` when showing |
| `+0x9C` | float | current value |
| `+0xA0` | float | maximum value |

Fields read from the `Chara`:

| Offset | Role |
|---|---|
| `+0xC00` | chara id — `0x16` for Byakuya |
| `+0xC20` | player slot — only `0` and `1` are processed |
| `+0x1094` | form — `0` in base, non-zero in evo |
| `+0x1098` | bit 0 — stance, `1` = petals, `0` = sword |

The value `3F7D70A4` is `0.99f`. It is preferred over `1.0f`: it visually saturates the bar while staying below the maximum, which avoids clamping edge cases.

---

## 5. Hook sites

| Address | Role | Original bytes |
|---|---|---|
| `exe+21FF64` | table byte selecting the class | `09` |
| `exe+92790` | handle copy constructor | `48 8B 02 48 89 01` |
| `exe+48C390` | enhance update, `rcx = Chara*` | `48 8B C4 55 53` |

`exe+21D9A8` carries the same value in a second table. **It must stay at `09`** — that one selects the layout name, and therefore Byakuya's resource group.

File offset of `exe+21FF64` for a `dinput8.dll` proxy port: `0x21F364`.

---

## 6. The three scripts

Mandatory activation order **1 → 2 → 3**. Script 1 must be active **before the match loads**: the controller factory runs only once.

Check once all three are on: `exe+21FF64 = 17`, `exe+92790 = E9`, `exe+48C390 = E9`, `exe+21D9A8 = 09`.

### Script 1 — class switch

Moves Byakuya from `Pl22` (icon only) to `Com` (gauge only).

```
[ENABLE]
BLEACH_Rebirth_of_Souls.exe+21FF64:
  db 17

[DISABLE]
BLEACH_Rebirth_of_Souls.exe+21FF64:
  db 09
```

### Script 2 — handle guard

Fixes the crash on SP1 activation. The handle copy constructor receives a source whose `+0x38` and `+0x40` fields are invalid; they are neutralised instead of being dereferenced. Validity criteria: non-null, 8-byte aligned, above `0x100000`, and no high bits beyond bit 47.

```
[ENABLE]
alloc(hcode,1000,BLEACH_Rebirth_of_Souls.exe+92790)
alloc(hdata,400)
label(h_ok)
label(h_kill)
registersymbol(hdata)
registersymbol(hcode)

hdata:
  dq 0        // +00 passes
  dq 0        // +08 handles neutralised
  dq 0        // +10 last offending handle
  dq 0        // +18 return address
  dq 0        // +20 rdx at rejection time
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
  mov [rdx+38],rax
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

### Script 3 — stance driver

The core of the setup. Filters on Byakuya and on player slots, computes the wanted mode into `r11d`, resolves the controller, then writes the element.

The early exit on petals + evo is the important part: nothing is touched, and `Com::SetRate` keeps driving its timer.

```
[ENABLE]
alloc(sqcode,1000,BLEACH_Rebirth_of_Souls.exe+48C390)
alloc(sqdata,100)
label(sq_go)
label(sq_show)
label(sq_wshow)
label(sq_whide)
label(sq_done)
registersymbol(sqcode)
registersymbol(sqdata)

sqdata:
  dq 0        // +00 frames processed
  dq 0        // +08 hides performed
  dq 0        // +10 last element pointer
  dq 0        // +18 shows performed

sqcode:
  push rax
  push rcx
  push rdx
  push r10
  push r11
  pushfq

  mov r10,sqdata

  mov eax,[rcx+00000C00]
  cmp eax,16
  jne sq_done
  mov eax,[rcx+00000C20]
  cmp eax,2
  jae sq_done

  xor r11d,r11d
  test byte ptr [rcx+00001098],01
  jz sq_go
  cmp dword ptr [rcx+00001094],0
  jne sq_done
  mov r11d,1

sq_go:
  inc qword ptr [r10]

  mov rdx,rcx
  lea rax,[BLEACH_Rebirth_of_Souls.exe+1CDE758]
  movsxd rcx,dword ptr [rdx+00000C20]
  mov rcx,[rax+rcx*8]
  test rcx,rcx
  je sq_done
  mov rcx,[rcx+00000200]
  test rcx,rcx
  je sq_done
  mov rax,[rcx+00000010]
  test rax,rax
  je sq_done
  mov rdx,[rax]
  test rdx,rdx
  je sq_done
  mov rcx,[rax+08]
  sub rcx,rdx
  cmp rcx,240
  jb sq_done

  mov [r10+10],rdx
  test r11d,r11d
  jnz sq_show

  cmp dword ptr [rdx+0000009C],0
  jne sq_whide
  cmp dword ptr [rdx+00000090],05
  je sq_done
sq_whide:
  mov dword ptr [rdx+0000009C],00000000
  mov dword ptr [rdx+00000090],00000005
  inc qword ptr [r10+08]
  jmp sq_done

sq_show:
  cmp dword ptr [rdx+0000009C],3F7D70A4
  jne sq_wshow
  cmp dword ptr [rdx+00000090],01
  je sq_done
sq_wshow:
  mov dword ptr [rdx+0000009C],3F7D70A4
  mov dword ptr [rdx+00000090],00000001
  mov byte ptr [rdx+0000009A],01
  inc qword ptr [r10+18]

sq_done:
  popfq
  pop r11
  pop r10
  pop rdx
  pop rcx
  pop rax

  mov rax,rsp
  push rbp
  push rbx
  jmp BLEACH_Rebirth_of_Souls.exe+48C395

BLEACH_Rebirth_of_Souls.exe+48C390:
  jmp sqcode

[DISABLE]
BLEACH_Rebirth_of_Souls.exe+48C390:
  db 48 8B C4 55 53

unregistersymbol(sqcode)
unregistersymbol(sqdata)
dealloc(sqcode)
dealloc(sqdata)
```

---

## 7. What was learned along the way

### The icon is not a vector element

In `Pl38`, the icon is a **separate handle stored at `[controller+0x18]`**, whose animation object is `[[controller+0x18]+0x20]`. It cannot be driven through the `+0x90 / +0x9C` fields of the vector.

### The on/off mechanism exists and is identified

`Pl38::Init` (`0x140215390`) and `Pl22::Init` (`0x14020F900`) run exactly the same sequence:

```
call 0x140206A30(name)           ; resolves the logical name
call 0x140095410                 ; stores the handle
call 0x1401CC2D0(obj,"loop1")    ; is that anim already playing?
call 0x1402278B0(obj,"loop1")    ; if not, stop it
call 0x14022A4B0(obj,"Normal",1) ; and play "Normal"
```

Both icons therefore carry the same clips: `"Normal"` (off) and `"loop1"` (on). Strings in the exe: `"Normal"` at `exe+14295B0`, `"loop1"` at `exe+1431A88`. The playback function is `exe+22A4B0(object, name, bool)`.

No class replays that toggle during a match — `Init` sets `"Normal"` once and never returns to it. A custom driver is therefore required, and one was prototyped successfully.

### Volatile register trap

The first icon prototype crashed with `0xc0000005` and `Faulting module name: unknown` — a sign that execution was inside the Cheat Engine allocation, not inside a module. Cause: `r10` and `r11` are **volatile** in the x64 ABI. As long as the hook contains no `call` they survive from end to end; as soon as an engine function is called they must be reloaded or saved to memory.

Other constraints of that same call: stack aligned to 16 bytes **before** the `call` (hence `sub rsp,88` and not `80` after 8 `push`), 32 bytes of shadow space, and `xmm0`–`xmm5` saved since the hook sits at the host function's entry and they may carry its float arguments.

### `_L00` and `_R00` are not two states

They are the **screen-side** variants, P1 on the left and P2 on the right, exactly like `ui_cha_unique_gauge00_L / _R`. Nothing to do with stance.

---

## 8. Possible follow-up

To bring back Byakuya's icon with on/off toggling, in order:

1. Set script 1 back to `db 12` (class `Pl38`).
2. Add the evo visibility branch to script 3, or repoint `exe+143FBC8` to `0x1402089B0`, so the native timer is not lost again.
3. Transplant Byakuya's icon nodes from the `.bak_gauge` backups into the cloned containers, **renamed** to `ui_pl038_unique_icon_L00 / _R00`. The `"Normal"` and `"loop1"` clips already exist on the pl022 side, nothing to recreate. Only Byakuya's group is touched, the real pl038 stays intact.
4. Wire the animation driver back into the `exe+48C390` hook, triggered on transitions only.

Known obstacle on step 3: name length, 22 characters against 24. To be validated depending on how the `.cat` files store their name table.

---

## 9. Diagnostics

Addresses to add to the Cheat Engine list:

| Address | Expected |
|---|---|
| `sqdata+00` | climbs continuously during a match |
| `sqdata+08` | increments on every switch to sword |
| `sqdata+18` | increments on every switch to petals in base form |
| `sqdata+10` | pointer of the last element touched |
| `hdata+00` | passes through the handle guard |
| `hdata+08` | handles neutralised — should stay low |

For a crash, `Get-WinEvent` in PowerShell:

```powershell
Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000,1001} -MaxEvents 20 |
  Where-Object { $_.Message -match 'BLEACH' } |
  Format-List TimeCreated, Id, Message
```

The `Fault offset` is already an RVA, readable directly as `BLEACH_Rebirth_of_Souls.exe+<offset>`. If the faulting module is `unknown`, the crash is inside a Cheat Engine allocation, not inside the game.
