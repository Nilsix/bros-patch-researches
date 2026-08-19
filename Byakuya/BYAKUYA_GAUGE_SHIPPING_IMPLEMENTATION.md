# Byakuya base-form stance gauge — shipping implementation

**Date:** 2026-08-19
**Game:** BLEACH Rebirth of Souls 1.3.0.0 (`BLEACH_Rebirth_of_Souls.exe`, md5 `7b21356622f2fe8d4a1733e74634abd8`)
**Character:** Byakuya, `pl022`, chara id `0x16`, uiId 22
**Status:** working in game, validated 2026-08-19 23:20

This is the engineering record of how the gauge described in
[`BROS-BYAKUYA-TIMER-STANCE-GAUGE.md`](BROS-BYAKUYA-TIMER-STANCE-GAUGE.md) went from three
hand-toggled Cheat Engine scripts plus a loose Python script in the game folder, to something
the launcher ships. That doc stays the reference for *why* each address is what it is; this one
covers *how it is delivered*, what was measured, and what not to do.

---

## 1. What the feature needs, and where each half now lives

The gauge is two independent halves. Neither works alone.

| Half | What it is | Delivered by |
|---|---|---|
| UI assets | 12 files giving Byakuya gauge geometry cloned from pl038 | `GameVersions/<version>/Overlay/` in the dev environment |
| Runtime patches | one table byte + two inline hooks | `dinput8.dll` (built from `dinput8_proxy.c`) |

Before this work: the assets were produced by running `clone_gauge_pl038_to_pl022.py --apply`
by hand in the Steam folder, and the runtime patches were three CE scripts toggled by hand in
a fixed order. Nothing was reproducible and nothing shipped.

---

## 2. Half one — UI assets, split per GameVersion

### 2.1 The problem

`clone_gauge_pl038_to_pl022.py` lives in the **game folder**, outside every repo. Its `--apply`
overwrites 12 of Byakuya's UI files with pl038's, and stashes the originals in sibling
`.bak_gauge` files. That meant the only copy of the vanilla bytes sat in throwaway files next to
the game's own, invisible to the launcher and destroyed by a Steam verify-integrity.

### 2.2 The 12 files

```
ui/script/scene/ActionUniquePl022_0.bin        ui/script/scene/ActionUniquePl022_1.bin
ui/script/anim/ActionUniquePl022_0.bin         ui/script/anim/ActionUniquePl022_1.bin
ui/ui_ActionUniquePl022_0_mot.cat              ui/ui_ActionUniquePl022_1_mot.cat
ui/ui_ActionUniquePl022_0_fnt.cat              ui/ui_ActionUniquePl022_1_fnt.cat
00HIGH/ui/ui_ActionUniquePl022_0_mdl.cat       00HIGH/ui/ui_ActionUniquePl022_1_mdl.cat
01MIDDLE/ui/ui_ActionUniquePl022_0_mdl.cat     01MIDDLE/ui/ui_ActionUniquePl022_1_mdl.cat
```

10 of the 12 actually differ between vanilla and patched. The two `*_fnt.cat` are byte-identical
in both sets; they are shipped anyway so each version is self-contained.

### 2.3 How both sets were captured

Not by reasoning about the script — by running it and hashing every state:

1. `--inspect` to confirm the 12 pairs and the `Pl038` → `Pl022` substitution sites.
2. Snapshot the 12 live files (**vanilla**).
3. `--apply`, snapshot the 12 live files (**patch**).
4. Verify the 12 `.bak_gauge` backups match the vanilla snapshot exactly.
5. `--revert`, verify the game folder is byte-identical to the vanilla snapshot.

A later cross-check confirmed the vanilla set is genuine stock: six stale `.pre_gaugebar_bak`
files left in the game folder by an earlier tool are byte-identical to it.

### 2.4 Where they live

```
GameVersions/Bleach Rebirth of Souls/Overlay/…                  <- vanilla bytes
GameVersions/Bleach Rebirth of Souls Community Patch/Overlay/…  <- pl038 clone
```

`Overlay/` is the launcher's existing mechanism for loose files that live among the game's own
(already used by the Zangetsu + Hiyori version for pl005/pl009 models). It installs the chain's
files, records every write, restores the stock file from `_launcher_vanilla_backup` when a
version no longer wants it, and children inherit from parents via `base.txt` — so CRE and
Zangetsu + Hiyori get the patched gauge for free.

### 2.5 Why Overlay rather than dropping files in `00HIGH/ui` directly

Two reasons, one of them decisive:

- **8 of the 12 files live in the game root's `ui/`, which nothing injects.** The launcher only
  copies `Script`, `Motion`, `00HIGH` and `01MIDDLE`. `GameVersions/*/ui/` folders exist but are
  read by no code. Putting files there does nothing, so new injection code was needed regardless.
- **The other 4 could go in directly, but they would leak.** `00HIGH`/`01MIDDLE` are injected with
  `copytree(dirs_exist_ok=True)` — a pure merge, no deletion, no backup, no tracking. Launch the
  patch, then launch `Bros 1.0` or `Bros 1.40` (which ship no such files) and the patched Byakuya
  files stay behind. Overlay reverts them.

### 2.6 Launcher changes

- The **main launcher** already supported `Overlay/`. No change was needed.
- Both **Quick Launch** scripts had no overlay support at all. The mechanism was added to each,
  sharing the main launcher's `launcher_patch_state.json` so the launchers cannot desync.
- `.gitattributes`: `*.cat` and `*.bin` marked `binary`. `core.autocrlf` is `true` on the lead's
  machine, these files had no explicit attribute, and the launcher distributes them by `git pull`
  — a CRLF conversion on a `.cat` is a crash. Verified after committing: all 24 blobs survive the
  git round-trip byte-exact.

Verified end to end: patch → vanilla → patch → vanilla, all four transitions byte-exact.

---

## 3. Half two — the three CE scripts, ported into `dinput8_proxy.c`

### 3.1 Anchors, verified against the shipping exe before writing anything

RVA → file offset via the PE section table, bytes read from the real executable:

| RVA | File offset | Bytes | Role |
|---|---|---|---|
| `0x21FF64` | `0x21F364` | `09` | switch B — class selection, `09` → `17` |
| `0x21D9A8` | `0x21CDA8` | `09` | switch A — layout name, **must stay `09`** |
| `0x92790` | `0x91B90` | `48 8B 02 48 89 01` | handle copy constructor |
| `0x48C390` | `0x48B790` | `48 8B C4 55 53` | enhance update, `rcx = Chara*` |
| `0x1440678` | `0x143F078` | → VA `0x1402065C0` | Pl22 vtable slot 22 (the shared form-getter) |

### 3.2 The design decision: both hook sites are function *entries*

The 16 bytes before each site were checked for `CC` padding:

- `0x92790` is preceded by `48 83 C4 20 5B C3 CC CC CC CC` — `add rsp,20; pop rbx; ret`, then
  four INT3. The code at the site is a field-by-field copy (`mov rax,[rdx]; mov [rcx],rax;
  mov rax,[rdx+8]; mov [rcx+8],rax; …`). It is a function entry — a copy constructor.
- `0x48C390` is preceded by `C3 CC CC CC …` and opens with the classic big prologue
  (`mov rax,rsp`, eight pushes, `lea rbp,[rax-4C8]`, `sub rsp,588`). Also a function entry.

**This is what makes the port safe and readable.** At a function entry only the ABI argument
registers are live; everything else is caller-saved and dead. So instead of transcribing ~200
bytes of hand-assembled x64 (scripts 2 and 3 are large, and a single wrong `rel8` is a silent
crash), the logic lives in ordinary C and a small standard trampoline calls it.

### 3.3 The trampoline

Identical shape for both sites, built at runtime:

```
push rbp / mov rbp,rsp
push rcx, rdx, r8, r9, r10, r11, rax     ; 7 pushes
and rsp,-16 / sub rsp,0x60               ; align + 0x20 shadow + 0x40 xmm
movups [rsp+20..50], xmm0..xmm3
mov rcx,<arg>                            ; site 2 only: mov rcx,rdx
movabs rax,<C payload> / call rax
movups xmm0..xmm3, [rsp+20..50]
lea rsp,[rbp-0x38]                       ; undo the 7 pushes
pop rax, r11, r10, r9, r8, rdx, rcx / pop rbp
<stolen prologue, verbatim>
jmp <site + stolen>
```

Disassembled with capstone and checked before shipping:

- net stack delta returns to **exactly 0** before the stolen bytes — critical for site 3, whose
  prologue is `mov rax,rsp` and would otherwise capture a shifted stack pointer;
- `rsp % 16 == 0` at the `call`, as the ABI requires;
- return targets land on `site+6` and `site+5` respectively;
- 105 and 101 bytes, inside the 160-byte build buffer and the 256-byte allocation.

The trampoline is allocated with `VirtualAlloc` scanning outward from the hook site so the `E9`
stays inside its ±2GB reach — the same reason the CE scripts say `alloc(name,size,exe+RVA)`.
The C payload is called through `movabs rax,imm64`, so the DLL itself can sit anywhere.

### 3.4 Install order is inverted on purpose

The CE workflow requires enabling 1 → 2 → 3 by hand, and **enabling 1 without 2 crashes on SP1**.
The DLL does the reverse: it installs the guard hook, then the driver hook, and flips the class
byte **only if both succeeded**. If either hook fails the byte stays at `09`, so a partial install
leaves a vanilla-safe game rather than a crash-prone one. A guard hook on its own is inert.

Every anchor is verified before anything is written, so a game update produces a clean skip with
a log line, never a half-patched process.

### 3.5 `patch_byakuya_evo_icon()` — from commented-out call to a real flag

It was sitting in `worker()` as `/*patch_byakuya_evo_icon();*/`, which the file's own rule at the
top forbids ("gate with a flag, never a commented-out call, so the log always says what shipped").
It is now `ENABLE_BYAKUYA_EVO_ICON 0`, with `ENABLE_BYAKUYA_GAUGE 1` beside it.

The two are mutually exclusive by construction: the icon patch repoints **Pl22's** vtable slot 22,
while the gauge moves Byakuya off the Pl22 class entirely, which makes that repoint inert *for
him* (it still, correctly, touches no other class). Ship one or the other.

---

## 4. Cross-character safety — the thing to actually check

`ICON_PATCH_bugfix_Aizen_Stark.md` records the rule this project paid for once already: the form
getter at `0x1402065C0` is **vtable slot 22 of 27 different `ActionCharaUniqueUI_PlXX` classes**,
and patching its body forced form 0 on all 27, breaking Aizen's and Stark's icons. The rule it
produced: *before an in-place patch to a vtable method, count the vtables that reference it; if
more than one, repoint the slot instead.*

**None of the three sites here patches a vtable method body.** They are a different class of
patch, and each was checked separately:

| Site | Scope | Can it reach another character? |
|---|---|---|
| `0x21FF64`, one byte `09`→`17` | table indexed by `uiId - 2`; Byakuya is uiId 22 → index 20 | **No.** A neighbouring byte is a different character's class and is not touched. |
| `0x21D9A8` | switch A, picks the layout/resource group | **Not written.** The DLL refuses to install if it is not still `09`. |
| `0x48C390`, driver | runs for every fighter | Filter is the first thing in the payload: `chara id != 0x16` returns immediately. The stolen prologue is re-executed verbatim, so every other character runs the original code with the original register state. |
| `0x92790`, guard | **genuinely shared** — every resource-handle copy in the game | See below. |

The guard is the only site that touches shared machinery. It writes **only** when the source
handle is already invalid — null-but-nonzero, misaligned, below `0x100000`, or carrying bits above
bit 47 — i.e. exactly the shapes that would fault on the next instruction. A legitimate handle
takes the early exit and nothing is written.

That was the argument. Here is the **measurement**, from a real session:

```
[23:22:15.447] BYAKUYA_GAUGE: guard neutralised 1 of 17348000 handle copies;
               driver 1596 frames (1 shows, 2 hides)
```

**One neutralisation in 17,348,000 copies.** The guard is a no-op for essentially the entire game
and fires only on the single broken handle Byakuya's Com-class lookup produces. The counters are
logged every minute whenever they change, so if this ever climbs while Byakuya is not in the match,
it shows up in `patch_ranked.log` instead of being guessed at.

---

## 5. Building and shipping the DLL

The `.c` change is inert until compiled — **the launcher copies the `.dll`, not the `.c`**. Commit
both, always; a `.c`-only commit silently ships nothing.

Built 2026-08-19 with the pip-packaged zig (note `python -m ziglang`, not a `zig` on PATH):

```
python -m ziglang cc -shared -target x86_64-windows-gnu -O2 -o dinput8.dll dinput8_proxy.c
```

`build_dinput8.bat` documents the mingw-w64 route instead
(`x86_64-w64-mingw32-gcc -shared -O2 -municode -DNDEBUG …`), which keeps the same binary shape as
the historical builds. Either works.

### Verifying a build

Launch and read `patch_ranked.log` next to the exe. A good install is four lines:

```
BYAKUYA_GAUGE/guard: hooked RVA 0x92790, 6 bytes stolen
BYAKUYA_GAUGE/driver: hooked RVA 0x48C390, 5 bytes stolen
BYAKUYA_GAUGE: installed -- uiId 22 moved Pl22 -> Com by ONE byte at RVA 0x21FF64;
               layout byte 0x21D9A8 still 0x09; no vtable method body patched, so
               Aizen/Stark and the other 26 UI classes are unaffected
BYAKUYA_ICON: DISABLED at build time -- superseded by BYAKUYA_GAUGE
```

No `BYAKUYA_GAUGE` line at all means the DLL in the game folder is an older build.

---

## 6. Gotchas

**Do not run `clone_gauge_pl038_to_pl022.py --apply` by hand any more.** It writes the same paths
the Overlay owns, and whichever ran last wins. Worse, a hand-applied clone can be captured into
`_launcher_vanilla_backup` as if it were stock, which poisons every later revert. Change the bytes
in the `Overlay/` folders instead. `--inspect` is still fine.

**CE scripts do not survive a relaunch.** They are runtime patches on one process. After any new
launch they must be re-attached, and script 1 must be active *before the match loads* — the
controller factory runs once. This is exactly what the DLL removes.

**Checking that no loose script is still applied.** The game folder accumulates one-off Python
tools, and two of them have an apply/revert pair that leaves a marker behind. Each declares its
own `BAK` suffix, so the presence of that suffix *is* the applied flag:

| Script | Marker | Applied if present |
|---|---|---|
| `clone_gauge_pl038_to_pl022.py` | `.bak_gauge` | overwrites the same 12 files the Overlay owns |
| `swap_pl022_ui_scene.py` | `.bak_sakura` | a rival donor — copies the **common** scene rather than pl038's |

Audited 2026-08-19: **zero of each**, so neither is applied and the Overlay is the sole owner of
the 12 files (verified 12/12 against the patched set). Other backups in the folder are harmless:
the `.bak` / `.prepetal_bak` files under `Script/Action/` and `Motion/` are shipped by the repo
itself, the five `dinput8.dll.pre_*_bak` are old DLL copies, and the six `.pre_gaugebar_bak` are
stale leftovers from a retired tool — byte-identical to true vanilla, so they are dead weight
rather than a live patch.

**Base form + sword stance shows no bar, by design.** Per §1 of the reference doc: base + sword is
hidden, base + petals is full, evo is the untouched native timer. "No bar in base" is only a bug
if Byakuya is in petal stance.

### A diagnostic that cost time — worth not repeating

Mid-work, the gauge appeared in evo but not in base, and the packaging was suspected. It was ruled
out by measurement, not argument:

- the 12 files during the failing session were **12/12 identical** to what `--apply` produces;
- the whole `ui/` folder was **384/384 identical** between the Overlay path and the known-good
  state;
- the DLL binary and its runtime log lines were identical across all five launches.

No game file differed. The cause was on the runtime side — script 1 active without 2 and 3, the
signature of which is precisely "no bar in base, crash on the evo transition". When a symptom
looks like a file problem, hash the files first; it is a two-minute check that ends the argument.

---

## 7. File inventory

**Dev environment** (`Bleach-Rebalance-Of-Souls-Dev-Environment`)

```
Files/Matchmaking/dinput8_proxy.c            +342 lines (688 -> 1039)
Files/Matchmaking/dinput8_proxy.c.pregauge_bak   pre-change backup
Files/Matchmaking/dinput8.dll                    rebuilt — must ship with the .c
Quick Launch Community Patch.py                  Overlay support
Quick Launch Bros Vanilla.py                     Overlay support
.gitattributes                                   *.cat, *.bin -> binary
GameVersions/Bleach Rebirth of Souls/Overlay/                  12 vanilla files
GameVersions/Bleach Rebirth of Souls Community Patch/Overlay/  12 patched files
```

New symbols in `dinput8_proxy.c`, in definition order: `gauge_handle_guard`,
`gauge_stance_driver`, `gauge_alloc_near`, `gauge_install_hook`, `gauge_stats_thread`,
`patch_byakuya_gauge`.

**Research** — this file, alongside `BROS-BYAKUYA-TIMER-STANCE-GAUGE.md` (the address-level
reference), `ICON_PATCH_bugfix_Aizen_Stark.md` (the shared-vtable rule), and
`BYAKUYA_EVO_ICON_exe_patch.md`.
