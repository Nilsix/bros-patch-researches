# The Zangetsu Master Guide

**Adding a new playable character to BLEACH: Rebirth of Souls, end to end.**
pl005 "Old Man Zangetsu" — the Character Roster Extension build.

---

## What this document is

This is the complete build record for pl005. Every subsystem that had to be understood, every
move that was added and how, every bug and crash and silent misfire, what each one actually turned
out to be, and what the fix was. It exists so that nobody — us or anyone else on the patch — has to
rediscover any of it.

Two things about how it is written.

**Failures are recorded as carefully as successes, and so are wrong theories.** A theory that was
believed, acted on and disproved is worth as much as a fix, because the next person will find the
same evidence and reach the same wrong conclusion unless it is written down. Sections marked ✗ are
retracted findings. Do not reopen them without new evidence.

**Numbers are exact and are not rounded.** Addresses, frame counts, struct offsets, field names,
hashes and file names are reproduced as measured. Where a note is thin, contradictory, or was never
verified in game, it says so rather than smoothing it over.

The base form is covered exhaustively. Evo and rev are placeholders at the time of writing and are
covered only where their state affects the base build — see [Part 13](#part-13--what-is-left-evo-and-rev).

---

## The shape of the problem

pl005 was a **boss slot**, not an empty one. He shipped as a clone of `sp000`, the story-mode
Zangetsu, and almost every bug in this document traces to the same root: **a boss inherits a boss's
data, and every table that was never adjusted for playable use is a landmine.** The size class that
picked the wrong camera rig, the step timings that were boss timings, the model scale, the combo
graph that was a boss graph, the fighting-spirit meter caps — each was correct for what he was and
wrong for what he became.

The second recurring theme is **identity binding**. This engine resolves things by internal name and
by hash, almost never by the name you can see in a file listing. An archive entry's name, a package
key, a graph node's id, a group name in `filename.bin` — get any of them wrong and the failure is
usually *silent*: the move simply does not come out, the gauge simply stays empty, the cutscene
simply does not play. There is no error. [Part 3](#part-3--the-moveset) covers this in full and it
is the single most important thing in the guide.

---

## The build at a glance

| Layer | Files |
|---|---|
| Combo graph | `Script/Action/pl005.tcmbpkg` |
| Tuning | `Script/Action/pl005.tadjpkg` + `pl005_modded.tadjpkg` (⚠ two copies, both must be kept in step) |
| Actions and clips | `Motion/pl005.tactpkg` |
| Stats | `Script/CharaStatus.fsv` + `CharaStatus_modded.fsv`, `Script/CharaModelVisible.fsv` |
| Registration | `Fnames/filename.bin`, `Fnames/file_exist.htable` |
| Text | `Text/CommonText.cat` |
| Cutscenes | `Demo/pl005_*.tdemopkg` |
| UI | `00HIGH|01MIDDLE/ui/ui_ActionUniquePl005_*.cat` |
| Audio | `Sound/{English(US),Japanese(JP)}/pl005.bnk` |
| Executable | `BLEACH_Rebirth_of_Souls.exe` — caves in `.text` and `.rdata`; ships as `Exe/exe_patch.recipe` |

**Reference characters.** pl052 (Yhwach) is the size and camera reference — tall male build, scale
1.13 against pl005's native 1.136. pl000 (Ichigo) is the reference for standard-action tuning and
canonical node ids. pl035 (Halibel) supplied several cutscene animations. sp000 is his own boss
original and the source of most of what had to be undone.

---

## How to read this

Parts 1–6 are the subsystems, roughly in the order they had to be solved. Parts 7–10 are the work
that finished the base form. Part 11 is the set of rules that generalise beyond this character — if
you read only one part, read that one. Part 12 indexes the tooling.

- [Part 1 — Making the slot exist](#part-1--making-the-slot-exist)
- [Part 2 — Identity, assets and the model](#part-2--identity-assets-and-the-model)
- [Part 3 — The moveset](#part-3--the-moveset)
- [Part 4 — Movement, steps and animation](#part-4--movement-steps-and-animation)
- [Part 5 — SP2, the kikon, and cutscenes](#part-5--sp2-the-kikon-and-cutscenes)
- [Part 6 — The unique gauge and the enhance state](#part-6--the-unique-gauge-and-the-enhance-state)
- [Part 7 — SP1 "Arterie" and the enhanced moveset](#part-7--sp1-arterie-and-the-enhanced-moveset)
- [Part 8 — The fighting-spirit lock](#part-8--the-fighting-spirit-lock)
- [Part 9 — Model scale and cutscene framing](#part-9--model-scale-and-cutscene-framing)
- [Part 10 — Release, the dev build, and the recipe debt](#part-10--release-the-dev-build-and-the-recipe-debt)
- [Part 11 — The rules](#part-11--the-rules)
- [Part 12 — Tooling](#part-12--tooling)
- [Part 13 — What is left: evo and rev](#part-13--what-is-left-evo-and-rev)

---


---

## Part 1 — Making the slot exist

Everything below is about one question: what has to be true, in the executable and in the two Fnames registries, before the engine will draw a 40th cell on the character-select diamond, let you move a cursor onto it, and load a fight from it. None of it is data-only. The roster grid is a compile-time-fixed object, the panel widgets behind its cells are a fixed-count set baked into a UI scene, and the file registries are two independent gates that both have to say yes.

Terminal state: build **D10 `c7dffb3107341f4f06e410f79c0cc6be`** is the 39-cell build (37 base + pl005 Zangetsu + random), complete and bug-free offline. The shipping build is the 40-cell exe **`c360f4b98c9dd8fd5228a81cbc16426d`** (37 base + pl005 cell 37 + pl009 Hiyori cell 38 + random pushed back to cell 39), with `CharaSelect.bin` S1/S3 at 39 entries and the tail `…pl052, pl005, pl009`.

### The prerequisite that is not in the exe

Before any grid work: **use a reserved slot in the range 0–52.** `pl053` and above are a dead T-pose. `pl005` was reserved (documented as "EMPTY" in an ID map that is now stale) and holds Zangetsu, cloned from the `sp000` boss.

Adding entries to `Script/CharaSelect.bin` alone is proven and scales — the live file reached 39 entries with no crash, so there is **no hardcoded roster cap at 38**. The roster *vector* grows freely from that file. What does not grow is the grid. Header byte 0 of `CharaSelect.bin` is the entry count: pristine `0x25` = 37 characters, `0x26` = 38 with pl005 added; the game then appends random, so a 38-character file produces a 39-element vector and needs a 39-cell grid.

The per-character rows a new slot needs before it will even load and animate (`CharaStatus.fsv` + `_modded`, `CharaModelVisible.fsv`, `WepBind.fsv`, `WepVisible.fsv`, `parry_bind_hit_effect.fsv`, `CharaActCmbHead.fsv`, `Physics/chara/plXXX_*.cphy`, sound banks, adv_motion, `Script/CharaNameTextID.fsv`) belong to the data-side chapters; without them a new slot freezes, T-poses, or has no model even with a perfect grid.

### The char-select grid object

The grid is a single heap object constructed at `0x140263E90` with vtable `0x141442C10` (7 methods: `0x264640`, `0x255B10`, `0x258B10`, `0x258920`, `0x25BDB0`, `0x25BDE0`, `0x25A270`), allocated at **`0x1930` bytes** from the size site at `0x14026382A` and freed by a sized delete whose immediate lives at `0x26465A` (**not** `0x264659` — that off-by-one cost a build).

| field | meaning |
|---|---|
| `this+0x70` | live cell count = `min(roster_vec_size, 38)` |
| `this+0x88` | per-player selection block, stride `0x10` |
| `this+0x8C` | hovered character index for player *n* at `player*0x10 + 0x8C` |
| `this+0xF0` | 7 columns |
| `[0x2E8, 0xD98)` | **the cells** — 38 × `0x48` bytes |
| `this+0x1910` / `+0x1918` | diamond nav table begin / end pointers |

Cell layout that matters: `cell+0x00` is the panel widget shared-pointer (written by the struct-copy at `0x140095410`), `cell+0x20` (grid displacement `0x308`) is the field the builder reads back at `0x255D05` (`mov rbx,[rdi+rbx*8+0x308]`, 8 bytes) and hands to `0x1408B3070`, which dereferences `[rcx+0x258]`.

The 38-cell cap is enforced by three constants plus the object size:

| site (VA of instruction) | immediate at | value | role |
|---|---|---|---|
| `0x255BD3` | `0x255BD4` | `0x26` (38) | count clamp into `this+0x70` |
| `0x255D7C` | `0x255D7E` | `0x26` (38) | grid-build loop bound (`83 F8 26`) |
| `0x2561D9` | `0x2561DC` | `0xAB0` | cell-array span (38 × `0x48`) |
| `0x263F97` | — | `0xAB0` | ctor memset span |
| `0x263FBB` | — | `0xDE` | ctor construct count (`lea r8d,[rdx-0x22]`) |
| `0x25B0AD` | `0x25B0AF` | `0x25` (37) | value gate |
| `0x25E5E0` | `0x25E5E2` | `0x25` (37) | value gate |
| `0x25EDB7` | `0x25EDB9` | `0x25` (37) | icon-builder value gate (`83 F8 25`) |
| `0x26382A` | `0x26382B` | `0x1930` | object allocation |
| — | `0x26465A` | `0x1930` | sized delete |

**★ The rule that separates them, and that took several crashed builds to state correctly:** `0x26` (38) immediates are **cell-count bounds** and must be bumped (39 cells → span `0xAB0` → `0xAF8`, ctor count `0xDE` → `0xDF`). `0x25` (37) immediates are **value gates** on the per-cell value stored at `[cell+0x8C]` and must **stay at 37** — the random cell's stored value is the character count (38), so `> 37` correctly routes it to special handling. Bumping the gates made random be treated as a nonexistent `char[38]`, producing a null icon.

The random cell is not positionally hardcoded. Function `0x258340` scans the `0xE0`-byte-element slot→ID vector for the sentinel **ID 999 (`0x3E7`)** — `cmp [rax+r9],0x3E7` at `0x258491` — so random logic finds the cell wherever it lands. `0x258340` is also the only writer of the hovered index at `grid+0x8C` (stores at `0x25858E` and `0x258599`). Earlier recon recorded the mapper as `0x14018B010` with singleton pointer `exe+0x1CDE6E0` and predicate `0x14025FE40`; the later, working description gives the singleton as `0x1A86380`. **The notes disagree on that singleton address**; the `0x258340` / `0x1A86380` pair is the one that was used to reason about the shipped fix.

### Expanding the grid: four failed approaches and one that held

| approach | scope | md5 | outcome |
|---|---|---|---|
| v1 insert-gap | 113 edits, 10 functions | — | crashed during select-screen **load** — missed the ctor `0x140263E90` and 5 other vtable methods |
| v2 insert-gap complete | 263 edits, 19 functions | — | applied 263/263 verified; superseded |
| v3 cell-array-to-tail | 53 edits | `af539ad80492` | structurally applied, then **abandoned** — see below |
| E, single-member move | 36 edits (33 shipped) | `6b289f7f198f` / `094945558682` | **the working direction** |

v1 and v2 inserted a `0x48` gap after cell[37] and shifted every `this`-relative access with effective offset ≥ `0xD98` by `+0x48` (106 then 422 displacement sites), deliberately **excluding** `0x1758` (the roster-vector field) and `0x16B8` (a loaded sub-object). Authoritative offsets came from Ghidra SSA (`dump_grid.java` → `grid_dump.txt`, `dump_grid2.java` → `grid_sites.txt`, `dump_grid5.java` → `grid_sites5.txt`; note Ghidra 12 needs `.java`, not `.py`, because PyGhidra was not enabled); capstone located the literal displacement bytes. Interior-pointer cases were included (`r12 = this+0x90` → patch the literal `+0x48`).

v3 moved the whole 38-cell array from `0x2E8` to the object tail at `0x1930` (delta `+0x1648`), growing the object to `0x2480`. Two real bugs were found and fixed inside it — index-form accesses like `[r12+rdi+0x308]` where `this` is the *index* register, not the base (that was the fault at `0x255EF2`), and the discovery that `0x263A50` constructs a **separate `0x4A0`-byte sibling object** that happens to share the `+0x2E8` layout (allocation sites distinguish them: `mov ecx,0x4A0; call 0x263A50` vs `mov ecx,0x1930; call 0x263E90`); relocating the sibling's fields to `0x1930+` overran it and corrupted the heap.

**v3 was abandoned for a structural reason worth keeping.** The cells are read by many scattered functions — cursor code, character preview, weapon/mask/blindfold loaders, VS-transition draw — that fetch the grid pointer *indirectly*. They are invisible to static analysis, and runtime tracing was unavailable (a constructor breakpoint yields the wrong grid instance; Berg confirmed Cheat Engine "find what accesses RCX+offset" was consistently empty). Symptoms of moving the cells: a deterministic roster "split" that persisted into battle load, intermittent heap crashes on re-entering select (from the un-memset old region), and missing cursor, weapons and masks. Zeroing the vacated region (memset base `0x2E8`, size `0x20F8`) removed the crashes but broke rendering — which **proved** hidden cell readers exist and null-check. Conclusion: never move the cells.

**Approach E** keeps the cells at `0x2E8`, grows them in place to 39 (`[0x2E8, 0xDE0)`), and relocates only the member that cell[38] would collide with — a font/resource struct — to the object tail. That member has 7 accessors, all reached through `this = rcx` grid code (ctor `0x263E90` ×13, builder `0x255B10` ×1 `lea`, dtor `0x264680` ×1, plus font helpers `0x25BE10` / `0x25C170` / `0x25C6E0` / `0x25CC90`, all called from grid function `0x25A6F0`) — findable and containable in a way the cells were not.

### Heap sizing: the member's true extent

Approach E's first form assumed the relocated member was `0x48` bytes because a cell is `0x48`. **It is not.** Reading the constructor's initialiser run gives the real layout:

```
[0xD98, 0xDE0)   0x48   struct A  (9 qwords)
[0xDE0, 0xE30)   0x50   struct B  (2 dwords + 9 qwords)
[0xE30, 0xE80)   0x50
```

Relocating only `[0xDE0, 0xE28)` split struct B, with two consequences: the ctor's initialisation of its last field (`mov [rsi+0xE28],rbp`) still wrote the **old** address, leaving the relocated `+0x48` qword uninitialised; and `lea rbx,[rdi+0xDE8]` — which after relocation resolves to `0x1980` — is passed to a helper that writes `dest+0x00..0x40`, i.e. up to `0x19C8`, past the end of a `0x19C0`-byte object. That is an 8-byte heap overflow on **every grid build**, faulting or not depending on heap churn, which is exactly why the bug looked online-only, then intermittent, then moved to select re-entry.

Final, correct sizing for the 40-cell build: treat `[0xD98, 0xE30)` as **one range** and shift both structs by `+0xB98` — struct A to `[0x1930, 0x1978)`, struct B to `[0x1978, 0x19C8)` — and grow the object `0x1930` → `0x1978` → **`0x1A00`** at `0x14026382B` (alloc) and `0x14026465A` (sized delete). 48 relocation sites.

**★ General rule: derive a member block's true extent from the constructor's initialiser run, never from a neighbouring array's stride, and size the object for the whole struct — because a `lea` of its base gets handed to helpers that touch `base+0x00..0x40`.**

**★ Completeness guard (keep it in the builder):** never trust a hand-maintained function list. Sweep every function in the select cluster `0x140250000–0x140270000` (boundaries from `int3` padding), disassemble each, and fail the build if any access with a displacement inside the struct span and a base other than `rsp`/`rbp`/`rip` is not in the patch set. It currently reports "12 functions touch the struct, all relocated". A raw whole-`.text` byte scan is useless here — hundreds of `rbp` stack frames collide with these displacements — and byte-scan hits are often reported one byte late because of the REX prefix, so cross-check by disassembling.

The functions the inherited "11 grid functions" list was missing, all found by crash: **`0x14025C8A0`** (a 12th grid function; it does `mov rax,[rcx+0xE28]; test rax,rax; jne; cmp [rax+8],0` at the *old* address), `0x14025CA20`, `0x14025E050` and `0x14025E300` (cursor prev/next, indexing `[rdi+rsi*4+0xDE0]`), the three `0xE28` sites at `0x14025CDEB` / `0x14026408F` / `0x14026476D`, and three sites approach E itself missed — `0x14025C337`, `0x14025C461`, `0x14025C58F`, all `lea rsi,[rdi+0xD98]` inside function `0x14025C170`, handing out a pointer to struct A's vacated address. That last one was **latent corruption in the 39-cell Zangetsu builds too**, and it is why the pre-fix launcher versions are marked do-not-ship.

### The panel-widget wall — the deepest layer, and the actual reason cells stopped at 38

Every count bump, in every approach, ended at the same fault: **`0x8B3092`**, inside `0x1408B3070`, which does `mov rax,[rcx+0x258]` on a null pointer. This is the single most expensive bug in the project's history and it survived at least four wrong explanations.

The grid builder `0x140255B10`'s first loop (`0x255CB0`–`0x255D7F`) calls `0x14024C1D0(base_name, index)`, which appends `"_" + index` (format string at `0x141424B98`) to a base name and looks the result up. The base names are `"ui_char_panel_layout00"`, `"ui_char_panel_column00"` and `"ui_char_select_panel00"` (VAs `0x141442538` / `0x141442558` / `0x141442570`, referenced at `0x255BEB` / `0x255C44` / `0x255CB4`), plus `"char_random"`, `"mono_char_"` and `"icon_m"`. The lookup is `0x140237260`, a pure hash-map find keyed `(name, index)` against the scene resource map (buckets at `[map+0x28]`, mask at `+0x40`, end at `+0x18`).

Instrumentation (`build.log`, hooking `0x14024C1D0`'s entry) captured the builder requesting `"ui_char_select_panel00"` for indices 0..37 (0..38 without the clamp) against one scene map holding `ui_char_bg(-1)`, names (0–1), 7 columns (0–6) and **38 panels (0–37)**. `grid.log` (hooking the read at `0x255D05`) then proved that for cell 38 **both `cell+0x00` and `cell+0x20` were zero** — the lookup misses, `0x140237260` silently zeroes its out-parameter, the cell is null, and `0x1408B3070` faults.

The wrong hypotheses, in order, each of which produced a crashed build:

1. **"Raise both grid constants by N."** Tested live 2026-07-23, crashed at +1. Root cause: the grid object is compile-time fixed with no count-based sizing anywhere; cell #38 overwrote the field at `+0xD98`.
2. **"The `0x25` gates need to become `0x26`."** They do not — see the count-vs-gate rule above. Reverting them (build `094945558682`, 33 edits) still crashed at `0x8B3092`, which is what proved the gate question was moot against a deeper wall.
3. **"Clamp the panel index."** A cave at `0x140B04ADA` hooked at `0x255CB0` did `cmp al,0x26; jne; dec eax`. Same crash. Disassembly of the builder's store function `0x140095410` showed why: it is a struct copy writing only `dest+0x00/+0x08/+0x10/+0x18` and refcounting a pointer at `+0x38`/`+0x40` — **it never writes `+0x20`**, so clamping the panel-create path could not affect the field that faults. (The clamp also had to reproduce the awkward `lea r9,[rip+0x11EC89D]` panel-name instruction and was probably mis-encoded.)
4. **"The 38 is a count in the `.cat`."** Partly true, but not as a bumpable number — see below.

**The fix that worked (route 1, shared widget):** a cave at `0x1416C0A00` hooked at **`0x255CBE`** — chosen because it only has to reproduce a trivial `rbp`-relative `lea rdx,[rbp+0x5C0]` — clamps the panel index at `[rsp+0x20]` from 38 to 37 for the 39th cell only, so the lookup returns panel 37's widget instead of null. Result, confirmed by Berg on two screenshots: no crash, all 38 characters plus random render, every character including Zangetsu selectable and fightable. `grid.log` confirmed `cell38.widget == cell37.widget == 0x2EDCC150A98`. Live md5 `15EC68F48CB8`; the clean logger-free build was `619F597F96AC`.

The clamp's cost is the **shared-widget wall**: the random cell piggybacks on Zangetsu's widget, so navigating to it shows Zangetsu, mouse hover triggers a random pick and preview but confirm does nothing, and keyboard nav loops Zangetsu↔Unohana, skipping the "?" cell.

**Where the 38 actually lives.** An exhaustive search ruled the exe out: `"ui_char_select_panel00"` is referenced only by the builder, the widget find/create map `0x1402657A0` is an unbounded FNV-1a `std::unordered_map`, and the builder contains **no `cvtsi2ss`**, so cell positions are not computed from the index in code. The `.cat` was then examined at length:

- `ui/ui_Character_Select_fnt.cat` (1.16 MB, md5 `470a51fb02`) and `_mot.cat` (774 KB, md5 `fc9e0e0bff`). Header at 0: `[1,1,0,0x100 data start, data size, ver, section count]`; offset table at `0x11C` with the size table following; comma+CRLF name table around `0x300`–`0x850` (~26 widget templates, referenced by **index**, not offset — panel = 19, column = 15, layout = 16); then sections. `fnt.cat` has 61 sections, of which 55 are **JSON** styling blobs (`BodyColor`, `GradeColor0/1`, `LineColor`, `BodyAlpha`, `Alpha`, `LineAlpha`; array length is animation-frame count 11..81, *not* panel count) plus `FontSet` dicts. `mot.cat` is 31 `tmo1` motion sections (header: magic, size at `+4`, sub-struct offset at `+0xA` as a word, params at `+0x30/34/38/3C/44`), parser at `0x1409DB650`, reached only via vtable.
- `"ui_char_select_panel00"` appears **6 times** in `fnt.cat` — its six animation states (base, `_grayout_loop`, `_out`, `_select_in`, `_select_loop`, `_select_on`) — and **once** in `mot.cat`. It is a template, not 38 records. The only `0x26` dword in the file (at `0xB429C`) is animation data; a 26→41 count difference found by `cat_diff.py` across versions was a keyframe count, not a panel count.
- **The decisive experiment:** Berg supplied the official *BRoS Ichibei* (36 characters, pl000–051) and *BRoS Yhwach* (37 characters, +pl052) patches. Their `ui_Character_Select_fnt.cat` **and** `_mot.cat` are byte-identical to each other and to the live file. Adding a real official character changed the char-select layout by **zero bytes**. The grid is a fixed 38-panel layout (37 roster + random) baked in early; official roster additions just fill an already-existing empty panel. **There is no official panel-add recipe and no diff can produce one.**

**The breakthrough (2026-07-25):** the panels are not in the `.cat` as an editable count — they are child node-defs of the char-select scene root, created at scene load. Hooking the generic node factory `0x140233ED0` at `0x140233F47` and walking the children vector at `[node+0x110]+0x28` found a root with **child_count = 114**: 38 `ui_char_select_panel00` + 7 `ui_char_panel_column00` + 1 `ui_char_panel_layout00` + 12 `cos_panel` + others. Capacity is **141**, so there are 27 spare slots and an append needs no reallocation. Entries are `std::shared_ptr` pairs `{q0 = def (= ctrl+0x10), q1 = ctrl}`.

The panel node-def, from a `0x100`-byte dump:

```
+0x00  std::string name  "ui_char_select_panel00"  (heap, size 22, cap 31)
+0x20  u32 INDEX         sequential 0..37   <- the (name,index) key
+0x28  SSO string        "default"          (state)
+0x48  another string
+0x6E  SSO string        "j_panel_0X"       (row name, X = 1..6)
+0x77  the row digit
```

There is **no baked position** — the varying bytes at `+0xAA..+0xBD` are garbage and pointers, not clean floats — so positions are computed. Column membership is encoded by **child-list order**, not a field: the list runs `[layout, col0, 4 panels, col1, 6 panels, …, col6, 4 panels]`, which is the `[4,6,6,6,6,6,4]` diamond, and a panel belongs to the column that precedes it.

The injection, built as a cave on the factory hook: allocate `0x100`, `memcpy` panel #37's def, set `+0x20 = 38` and `+0x77 = '5'` (so it lands in `j_panel_05`), append an aliasing `shared_ptr {new_def, ctrl37}` with an increment of the refcount at `[ctrl37+8]`, and bump the vector end by `0x10` and the count to 115. The copy leaks rather than risking a double free. Because col6 is the last column, an append lands in col6 row5. First build `4B1E937ED7DE`. The 40-cell release does this **twice** — the cave map records "grid clones C/D" as a `cre_exe_caves.py` window, and the launcher notes explicitly that the 40-cell exe **requires both pl005 and pl009 to exist because it injects two extra panels**. Build D10 is described as having "a real independent random cell", i.e. the injection route landed; the memory does not record a separate pass/fail note for `4B1E937ED7DE` itself.

**★ The addref rule** that came out of the clone work: the clone was addref'ing the wrong field (`+8` instead of `+0xC`), leaving the refcount genuinely unbalanced. The fix is to addref **both**.

### The diamond navigation table

Directional input runs through **`0x14025EB30(rcx = grid, edx = player, r8d = dx, r9d = dy)`**, which **tail-jumps** at `0x14025EC70` into the cursor setter `0x14025EC80` — so probing the setter reports the caller's *caller*, which is a real trap when instrumenting. The four direction branches live in `0x25A6F0` and call with `(+1,0)`, `(−1,0)`, `(0,−1)`, `(0,+1)`; their return addresses `0x14025B35A / 0x14025B371 / 0x14025B38A / 0x14025B3A0` identify which direction fired.

The algorithm: the table runs from `[grid+0x1910]` to `[grid+0x1918]`, is **dwords, 8 per row**, and uses `-1` for empty. It linear-searches for the current index (`grid[player*0x10+0x8C]`) to recover `(row, col)`; then `col' = col + dx` wrapping `<0 → 7` and `>7 → 0`, `row' = row + dy` wrapping `<0 → 6` and `>6 → 0`; `idx = col' + row'*8`; **while `table[idx] == -1`, keep stepping in the same direction** (loop at `0x14025EC10`); finally `setcursor(grid, player, table[idx])`.

**★ Orientation, which was recorded backwards once:** the table's *row* is the diamond's **column** (7 of them, wrap at 6), and that row's 8 entries are **positions within** the column (wrap at 7). So `dx` moves vertically on screen and `dy` moves horizontally. The evidence: the `dx=+1` handler moved 36→37 and then wrapped 37→34, which is travelling down a visible column.

**If the current cell is not in the table**, the not-found path at `0x14025EBBF` falls through with `row=0, col=0` and steps from the table's origin. That is precisely why, before the fix, mousing onto cell 38 and then pressing a direction jumped to an arbitrary cell.

**The fix**: a cave on `0x14025EB30`'s entry, written to be **idempotent** so it self-heals on every grid rebuild and needs no knowledge of who populates the table. It bails if the table is missing or short; bails if 38 is already present; finds cell 37's slot; steps `+1` within the same row, stopping at the row boundary (`slot & 7 == 0`), to the first `-1`; and writes 38 there. Log tag 11 emits `(slot_of_37, slot_written, count)` and tag 12 dumps the pristine table, 4 slots per record.

### Why the mouse worked before any of this

A separate system entirely. `0x140236E40` walks a vector of **`0x120`-byte records at `[obj+0xA8]`** — the same vector the grid builder fills per cell, whose bound approach E had already widened to 39. It hit-tests via `[rec+0x110]` and on a hit calls the focus listener at `[rec+0x90]` (`0x140257C60`, reached through adjustor thunk `0x1402667E0` in vtable `0x141442B90`), which reads the focused widget's stored name (flag at widget `+0x88`, inline at `+0x89`, heap pointer at `[+0x98]`), matches `"panel_<i>"` over the live cell count, and calls the setter. Cell 38's widget carries `panel_38` because `0x1408B3070` stores the name on a lookup miss, at `0x1408B311A`. There are only two callers of the list accessor `0x14023BA00` — this dispatch and a copy constructor — and that is what proved the keyboard path was something else entirely.

### The cell icon

The builder's second loop constructs `"mono_char_" + id` (base string `0x1414425B0`, `%02d`), resolves it in resource category **`chara_icon`** via `0x14024B880`, and binds it into the widget slot `icon_m` through the panel widget's vtable at `+0x370`. **The id is the pl number** — log tag 6 shows cell 37 → 5 and cell 38 → 999.

`ui/swap/chara_icon.cat` (identical in `00HIGH` and `01MIDDLE`, original md5 `a50422f349d16367b051315b8f7d7231`):

```
+0x10   data size = filesize - 0x100
+0x18   section count + 1        (0x98 -> 151 sections)
0x118   offset table
0x378   size table
0x600   name table (comma + CRLF): char_1p_*, char_2p_*, mono_char_*   name[i] <-> section[i]
        each section: 16-byte header {0x10, 1, dds_size, 0} at off+0x100, DDS at off+0x110
```

A texture's payload spills roughly `0x44` bytes into the next section's padding, so **restitch header-to-header, never block-by-block**. Reserved-empty pl slots ship as **24×24 placeholders (`0x2E4` bytes)** rather than 200×148 (`0x7444`) — that was the blank white cell, with blanks at k=5 and k=9 (reserved pl005 and pl009).

Applied fix: grow sections 5, 54 and 103 to full size, rewrite both tables and the header (file grows by `0x15600`); art from `Zangetsu Patch/Zangetsu Icon/3JfJ6zWy5Ec-HD.png` upscaled to 200×148 with each slot's own alpha silhouette taken from its `_06` neighbour; encode **BC3/DXT5 keeping the donor's DX10 header and flipping `dxgiFormat` 98 → 77**, which is payload-size-identical so no offset table needs rebuilding. Builder `~/bros/build_icon.py`, originals in `Zangetsu Patch/icon_backup/`.

**Recorded error worth repeating:** an early note asserted that DDS #5 was Urahara and therefore not blank. **Urahara is pl006.** That off-by-one is why an earlier attempt wrote the icon onto pl000.

### The playable-character gate

`cre_exe_caves.py` relocates an `IsPlayableCharacter` stub into the cave window **`0x1411B4D60`–`0x1411B4D8B`** (44 bytes), and the builder is parameterised by a `NEW_IDS` tuple — `NEW_IDS=(5,)` for a Zangetsu-only 39-cell build, `(5, 9)` for the shipped 40-cell one. **The notes do not record the stub's original address or its exact rewritten predicate**, only the cave window, the owner script and the parameter name.

Its three matchmaking callers were investigated during the Hiyori crash hunt and **ruled out** as a crash cause: they only set an "invalid character" flag at `[rbx+0x68D]`. That finding is explicitly marked do-not-re-litigate, alongside `SRankMatch`-vs-`SRoomMatch` call-graph differences.

For context on why any of this is hardcoded at all: `cmp [rax+0xC00], <id>` — the fighter struct's character id at `+0xC00` — is how *all* per-character logic is written in this exe, and per-character behaviours are registered from a table keyed by id string (pl020's slot is `0x1418E1130`). A brand-new id inherits nothing from either.

### `filename.bin` and `file_exist.htable`

**These are two independent gates, and a file needs both.** This single sentence would have saved months.

`Fnames/filename.bin` is the engine's **logical-name → path registry**. Rows are `(L1 group, L2 directory, basename, extension, LOGICAL NAME)`; the runtime key is `hash(group, logical)` computed by `0x1408A4F40`. The table is built by `0x140699070` from `TAppRootTask::InitFileNameInfo` (`0x1408564E0`) into the `std::map` at `.data 0x141CF2B68`. The resolver chain is `0x14069ACF0` → `0x14069A410` → `0x140698A70` → `0x140698130`, the last picking a quality tier from `0x141CDEBEC`. **A miss returns an empty string, silently.** It is also *the only place some strings exist anywhere in the game* — `MapAssetCat` is not in the exe at all. Critically, it is a **list of groups**: registering a file under the wrong group is a silent miss with no crash, which is why pl005's unique gauge never drew.

`Fnames/file_exist.htable` is the **existence set**. A stock `filename.bin` entry only proves the developers reserved the *name*; only the htable says a file was ever shipped. It is consulted through `0x140893EF0` → path split `0x14069D5A0` → CRC → hash-map find `0x140896D20` (FNV-1a over a u32 key). The literal string `file_exist.htable` appears nowhere in the exe because the binary has an EasyAntiCheat `.bind` section and some strings only exist at runtime.

**The attack wall is the canonical demonstration.** `Script/Action/pl005.tcmbpkg` — the combo graph, i.e. every attack route — was on disk *and* in `filename.bin` (`pl005_combo` → `Script\Action\pl005.tcmbpkg`) but **absent from `file_exist.htable`**, so the engine never opened it. The classifier is perfect 48/48: `Script\Action\plNNN.tcmbpkg` is missing from the htable for exactly **pl005, pl009, pl028, pl030, pl034, pl040, pl041** — precisely the seven reserved slots that load, move and animate but cannot attack. Every playable, plus pl015/021/043/044, has it. `.tadjpkg` and `Motion\plNNN.tactpkg` *are* registered for all seven, which is why the model, skeleton and non-attack motion work.

The code path: the per-character package loader `0x1404D4699` runs a 32-iteration loop (`r15d` 0→`0x20`), one asset class per iteration. For `_combo` it joins `"pl005" + "_combo"` (`0x140090010` at `0x1404D57D5`), then at `0x1404D5822` calls `0x140893D40(this, name, category="", -1)`. On **false**, `0x1404D5838` does `mov rdx, r14` (r14 = the empty string at `0x14140BDC7`) and calls `0x14008AF00` — **the package name is blanked**. Movement, dash, reverse and grab-chase survive because they live in the shared `plcom` package; nothing character-specific can dispatch for player or AI, and the input never becomes an attack command, so the Hi/Lo indicators stay dark.

The fix was one htable entry: `crc("Script\Action\pl005.tcmbpkg") = 0xCDB8D7A8` under directory crc `crc("Script\Action") = 0xEA72B6CA`, inserted next to pl004's so the directory grouping holds (`Zangetsu Patch/fix_attacks.py`). The shareable pl009 equivalent is `crc("Script\Action\pl009.tcmbpkg") = 0x2B8C24BC`, anchored next to pl008 (`Zangetsu Patch/pl009_attack_fix.zip`). No exe change, no manifest change, no new files.

**This retired two earlier conclusions, both artefacts of the same hidden variable.** The "exe-side, index-keyed attack gate" rested on a Nel clone on pl009 failing while pl042 worked — but pl009's `.tcmbpkg` is missing from the htable too, and there is no index-keyed attack gate in the exe, which is why every search for one (per-id table, bitmask, runtime-built set) found nothing. And "the donor moveset exonerates the data" was predetermined: swapping the *bytes* of a file whose path is never opened cannot matter.

#### Rules for editing the two registries

- **Never install a `filename.bin` or `file_exist.htable` from someone else's drop.** They are whole-registry files and would wipe our own rows.
- **Patch the current tables incrementally; never rebuild from an `.orig_bak` with hardcoded lists.** `fix_attacks.py` rebuilds from `file_exist.htable.orig_bak` and replays 13 online-fix entries — after the pl036 costume registrations landed on 2026-07-26 it became unsafe to re-run as-is, because it would drop them. Use the `register_costume_models.py` pattern instead. `Zangetsu Patch/fnames_patch.py` has the identical defect against `filename.bin.orig_bak`: re-running it silently deletes the stage rows *and* any hand-added `<id>_CAT`. This is the same stale-source class as the stale `Overlay/` tree and the four divergent DLL sources.
- Registering a model needs **both manifest triples** (`.tmd2` → `_mdl` and `.gnf` → `_tex`) plus **4 htable keys per model**.
- A registration is only worth trusting once its directory's path formulation hits **100 % on all 37 playables** — 8 directories qualified under that test, which is how `Motion/Menu/menu_pl005.tactpkg` and `Sound/Japanese(JP)/pl005.bnk` were found to be missing too.
- Some absences are correct: `00HIGH/Model/chara/pl005_*` and `Physics/chara/pl005_*` are unregistered on purpose, because `CharaModelVisible` points pl005 at `sp000_*`.
- Verified good state, 2026-07-26: Fnames hashes `216ede9b` and `4bfbd163`.

#### The sibling case: new stage ids, which nails the semantics

Brand-new stage ids need exactly two things, and only one of them is in the exe. **Gate 1** is a hardcoded whitelist: `ActionSceneBase::LoadBattleArea()` at `0x1406A42F0` linear-searches a **71-row table** at `.data 0x1418EDF00` (rows are `{const char* label; const char* id;}`, bound `cmp esi,0x47` at `0x1406A4421`); on a miss the `je` at `0x1406A448B` jumps past the entire field load to `0x1406A488C`. The fix is a same-length nop, no cave: `0F 84 FB 03 00 00` → `66 0F 1F 44 00 00` at RVA `0x6A448B` / file `0x6A388B`. Correlation was 56/56 (all 32 roster ids and all 19 working "adopted" story ids are in the table; `bg005_00`, `bg005_01`, `bg004_04`, `bg004_05`, `bg000_99` are not). Story mode was never affected — the ADV dispatcher `0x1407099C0` calls `FieldSetup::Load` directly.

**Gate 2 was the real blocker and it was a missing `filename.bin` row.** `BuildMap::LoadProject` (`0x140662610`) does:

```
path = "MapEdit/testmap_00.tmeproj"   // hard-coded default
r    = resolve("<id>_project")
if (r.size()) path = r                // MISS -> the default is kept
```

so a new id silently builds the arena from **testmap_00**'s object list against the new id's archive, and every subsequent resource lookup misses. Because `.tmeast` (MEA1) is the only thing naming both the meshes and the collision `.tch`, no tmeast means **no geometry and no floor** — players fall through while the intro still runs, since camera, spawn, HUD and BGM do not come from the map. That symptom pair is the signature of this bug. `Zangetsu Patch/stage_fnames_project.py` appends 5 rows per id (`_project`, a `Model\MapAsset\<id>\` directory node, `_FOG`, `_REFLECTION`, `_GI`, `_AdvDemo`).

**★ This corrects an earlier note of ours** which recorded that "`filename.bin` is NOT a blanket load gate" because `tex0.lds` and stage thumbnails load without a row. That is true for **direct-path** loads and false for **anything resolved by logical name**. `file_exist.htable` is irrelevant to the MapEdit loader specifically, because it uses plain `fopen`.

### The exe cave map

**⚠ `.text` is full.** 30,346 `int3` runs totalling 350 KB, and the largest single run is **22 bytes**. The tail beyond `0x1411B4000` is the only usable `.text` space and it is crowded and shared. Anything new goes in the `.rdata` run, which `ui_ctrl_v1_ownlogic.py` flipped from `R--` to `R-X` by writing `0x40000040` → `0x60000040` at **file offset `0x2D4`**.

| VA range | owner | contents |
|---|---|---|
| … `0x1411B4BAD` | `cre_exe_caves.py` | char-select cave |
| `0x1411B4BB0`–`0x1411B4C30` | `move_names_own_entry.py` | 128 B of cave code |
| `0x1411B4C30`–`0x1411B4C50` | *(slack, 32 B)* | was the in-`.text` name table |
| `0x1411B4C50`–`0x1411B4CCC` | `ui_gauge_v6_ownslot.py` | pl005's unique-gauge switch **case body** (124 B) |
| `0x1411B4CD0`–`0x1411B4D34` | `ui_gauge_v6_ownslot.py` | the relocated **25-entry dword table** |
| `0x1411B4D60`–`0x1411B4D8B` | `cre_exe_caves.py` | relocated `IsPlayableCharacter` stub |
| `0x1411B4DA0`–`0x1411B4EAB` | `cre_exe_caves.py` | **grid clones C/D** |
| `0x1411B4EB0`–`0x1411B4FB0` | `cre_exe_caves.py` | **diamond nav table** |
| `0x1411B4FB0`–`0x1411B4FC3` | `ui_gauge_v6_ownslot.py` | the string `ActionUniquePl005_` |
| `0x1413A2300`–`0x1413A2700` | `ui_ctrl_v1_ownlogic.py` | gauge driver + guard (`.rdata`) |
| `0x1413A2700`–`0x1413A2B00` | `move_names_own_entry.py` | move-name table, relocated 2026-08-10 |
| `0x1413A2B00`–`0x1413A3000` | `fight_gate2.py` | 11 fighting-spirit stubs, 99 B stride, 1089 of 1280 B used |
| `0x1413A3000`–`0x1413A304E` | `fight_gate3.py` | the adder gate, 78 B |
| `0x1413A3200`–`0x1413A42D8` | *free* | ~4.2 KB left of the 8,211-byte `.rdata` zero run |

Two hazards inside that table. **`fight_gate2.py --revert` zeroes its whole `cave_len` window**, not just the bytes it wrote — which is why `fight_gate3.py` starts exactly one byte past its end. When two patches share a reserved block, make the boundary exact and put nothing of yours below it. And both stub sizes have already grown as their conditions gained clauses (81→99 B, 60→78 B), so budget for growth and re-check the table after any rebuild.

**★ Never hardcode a section's file offset from memory.** `.rdata` is VA `0x1411B5000` / file `0x11B4400` / raw `0x505E00`. `fight_gate3.py`'s first draft carried `0x1412D6000` / `0x12CD800` from recollection — wrong by `0x121600`, which would have written 60 bytes of stub into live read-only data. Parse the section table and look the VA up; `fight_gate3.py:sections()` is a 12-line copy-paste. For `.text`, `file = va - 0x140000C00`.

`.pdata` (VA `0x141D0B000`, file `0x198F600`, size `0xB37A8`) holds 61,262 twelve-byte `{Begin, End, Unwind}` RVA records — sort by `Begin` and bisect for function bounds, which is far better than a linear sweep that runs into the next function and produces convincing nonsense. **⚠ A `.pdata` record is not always a whole function.** Long functions get chained records, so a record can begin mid-function with no prologue and no callers: `0x14046C327` looked for an hour like an orphan function that writes the meter and nobody calls, and is the second unwind record of `0x14046C2E0`. Tell-tales are a range starting with `movaps [rsp+..], xmm` instead of a prologue, an RVA appearing only inside `.pdata`, and the preceding bytes falling through into it. Conversely `0x14046C230` has **no** record at all — a leaf that never touches the stack needs none — so absence of a record is not absence of a function.

When the device bridge is down, `DataChakka/uploads/_slice.bin` and `_slice2.bin` are two 5 MiB raw dumps covering file `0x100000`–`0x600000` = VA `0x140100C00`–`0x140600C00`. Their base is written down nowhere and was recovered by searching both for a 16-byte signature whose VA was already known. **⚠ They are different builds** from each other and from ours — 160 diff runs, 322 bytes, including struct-offset shifts — so read logic from them offline and re-verify every address against the live exe.

### Cave discipline

- **rip-relative only, no absolute image addresses.** `DllCharacteristics 0x8160` = DYNAMIC_BASE + HIGH_ENTROPY_VA. Use `lea reg,[rip+disp]`; the builder now hard-fails on any `movabs` whose immediate falls in the image range.
- **Assemble in the cloud container** (`pip install keystone-engine capstone`) and emit a `*_blob.json` sidecar of the finished bytes, because the desktop VM has no network and therefore no assembler. Two-pass trick for rip-relative operands: assemble with a sentinel displacement, find the 4-byte field, rewrite it as `target - (at + off + 4)` — every rip instruction worth using ends with its displacement, so the encoding cannot change length.
- **keystone has no label support.** Hand-encode `jcc rel8` and back-patch by label *name*. For a small stub skip keystone entirely — `fight_gate3.py:build_stub()` hand-encodes all 78 bytes, so the installer is one self-contained file.
- **Every hook site's instruction must be ≥ 5 bytes**, asserted with capstone. Bug D4 hooked `0x140255DE2`, a 4-byte `mov [rsp+0x60],eax`, and the 5-byte `jmp` clobbered the following instruction.
- **Spill anything live across a `call`** — `rcx/rdx/r8/r9/r10/r11/rax` are all volatile, and a called logger will destroy them. Bug D9 kept a dump loop's counter in `rdx`; the symptom was a **freeze**, not a crash.
- **Write the stub before the detour, and clear the detour before the stub.** Never leave a live jump into a blank cave, in either direction.
- **The mount refuses `O_TRUNC`** — write with `r+b` plus `truncate`, or seek-and-write in place.
- **Every cave script must publish its window in the map above and assert on its neighbours' start addresses.**
- **Register every span in the recipe in the same commit.** A patch that does not register itself does not exist.

**★★ Better than a backup: reconstruct the original.** `fight_gate2.py` writes 5-byte detours and keeps *no* backup file, because a site's stock bytes are derivable — `E8` + `helper - (site + 5)` — so both install and revert verify against a computed value rather than a sidecar that can go stale. ⚠ Site discovery must recognise **both** shapes: an installed site is `E9 <cave>`, not `E8 <helper>`. Matching only `E8` made `--revert` a no-op that cheerfully reported "nothing installed" while ten detours were live. `fight_gate3.py`'s variant is stricter still: refuse to patch unless a **25-byte window** around the hook matches stock, not just the 6 bytes being replaced, so a future build that shifts one instruction in that block cannot get half-matched and silently mispatched.

### Observation method: instrument, do not debug

**Runtime debugging is blocked.** x64dbg attaches but the game has anti-debug and anti-tamper: software breakpoints never fire (a code checksum detects the `0xCC`), hardware breakpoints do not fire either (debugger-presence detection), pausing crashes the game, and Cheat Engine produced nothing usable. ScyllaHide did not change this.

**The insight that unlocked everything:** an on-disk code patch is not debugging. No attach, no `0xCC`, no pause — so the anti-debug is blind to it. Every approach's patches ran fine right up to their crash. So observation is done with a **logging code cave baked into the exe**, using the game's own imported `CreateFileA` / `WriteFile` / `SetFilePointer` / `CloseHandle` (IAT entries `0x1411B5600` / `0x1411B5338` / `0x1411B5608` / `0x1411B55F8`).

The first such stub was 245 bytes hooking the builder's read at `0x255D05` and logging a 32-byte record `[rdi (grid), rbx (= counter*9), cell+0x00, cell+0x20]`. Stub, name, record and handle live in the file-backed zero region of `.data` at `0x1416C0000` / `0x1416C0800` / `0x1416C0900` / `0x1416C0940`, with `.data`'s characteristics OR'd with `0x20000000` (EXECUTE) so DEP allows it — **no new PE section** (there was only 12 bytes of header room, and the EAC `.bind` section made that route hostile) and no header shift. Log tag 9 emits the runtime address of the `log` cave (static VA `0x1411B45B0`) once per scene load, so `base = logged − 0x11B45B0`; observed bases include `0x7FF67E140000`, `0x7FF6CD7E0000` and `0x7FF6EBC44000`. Image bases are 64 KB-aligned, which is enough to reconstruct one from a single return address when tag 9 is absent.

The escalation, added for the Hiyori crashes, is a **VEH crash reporter**. `AddVectoredExceptionHandler` is not imported, so it is resolved at runtime via `GetModuleHandleA` (`0x1411B5630`) and `GetProcAddress` (`0x1411B5170`) and registered once from the node-factory hook. It is not a debugger, so the anti-debug never sees it. On `0xC0000005` it logs at most 4 times and returns `EXCEPTION_CONTINUE_SEARCH`: tag `29` cookie, `30` (fault RVA, Rcx, Rbx), `31` (Rax, Rdx, Rdi), `32` (Rsi, R8, R9), `34` (Rbp, R12, R13), `33` (return RVA, stack slot) up to 16 deep. Scratch at `VEH_INIT 0x1416C2050` / `VEH_CNT 0x1416C2058`. **Strip it for release.**

**⚠ Do not file-log a hot path.** Logging the icon builder `0x25ED40` at `0x25EDAF` — a per-frame function — crashed or hung the game, apparently timing-related anti-cheat. The grid builder `0x255B10` runs once per load and is safe.

**Meta-lesson, stated in the notes after the Hiyori work:** three plausible theories all survived static reasoning and all were wrong; one VEH run settled it. When static analysis stops converging, instrument.

### Crash and failure catalogue

| fault | build/context | wrong hypothesis | real cause | fix |
|---|---|---|---|---|
| **`0x8B3092`** (in `0x1408B3070`, `mov rax,[rcx+0x258]`) | every count bump, all approaches | in order: bump the `0x25` gates; clamp the panel index at `0x255CB0`/`0x140B04ADA`; an exe-side panel count; a bumpable `0x26` in the `.cat` | the scene resource map contains panel widgets for indices **0–37 only**; index 38 misses, `0x140237260` zeroes its out-param, `cell+0x00` and `cell+0x20` are both null | interim: clamp cave at `0x255CBE` → cell 38 shares panel 37's widget. Real: inject a 39th panel node-def at the factory hook `0x140233F47` |
| **`0x255EF2`** | v3 cell-array-to-tail | — | index-form accesses `[r12+rdi+0x308]`, where `this` is the **index** register not the base, were not detected | detect `this` as base **or** index |
| heap corruption, intermittent | v3 | that `0x263A50` was a grid function | `0x263A50` builds a **separate `0x4A0`-byte sibling** sharing the `+0x2E8` layout; relocating its fields past `0x1930` overran it | exclude it; distinguish by allocation size at the call site |
| roster "split" into battle load + intermittent crashes on re-entry + missing cursor/weapons/masks | v3 | that static analysis had found all cell readers | many scattered functions (cursor, preview, weapon/mask/blindfold loaders, VS-transition draw) fetch the grid pointer **indirectly** and read cells | abandon cell relocation entirely; move a single member instead |
| crash during select-screen **load** | v1 (113 edits) | that 10 functions were the complete set | missed the grid constructor `0x140263E90` and 5 other vtable methods | enumerate ctor + all 7 vtable methods + non-virtual callers (v2, 263 edits) |
| **RVA `0x9546C`** (`0x140095410+0x5C`, `lock xadd [rcx+0xC],-1`) | 40-cell build | a refcount/control-block bug | VEH caught `Rcx = 0x203A22656D616E5F` = ASCII `_name": `, a `.cat` JSON fragment in freed heap — the read was **out of bounds**. The relocated struct is `0x50` bytes, not `0x48`; splitting it left the last field uninitialised and let a helper write to `0x19C8` in a `0x19C0` object | relocate `[0xD98,0xE30)` as one range, `+0xB98`; grow the object to `0x1A00` |
| **RVA `0x25C8C2`** | 40-cell build | — | `0x14025C8A0` is a **12th** grid function absent from the inherited list, reading `[rcx+0xE28]` at the vacated old address | add it plus `0x14025CA20`, `0x14025E050`, `0x14025E300`; add the automated completeness sweep |
| latent (no fault recorded) | 39-cell Zangetsu builds | — | three `lea rsi,[rdi+0xD98]` sites in `0x14025C170` (`0x14025C337/461/58F`) handed out a pointer to struct A's vacated address — cell 38's own address | relocate them; this is why the pre-fix launcher versions are marked do-not-ship |
| **fault offset `0x11B4C50`**, every launch, at battle load | after `move_names_own_entry.py` moved its table to `.rdata` | — | that script had `CAVE_END_VA = 0x1411B4C58` and blanks `co..CAVE_END_VA` — **eight bytes past the start of the gauge case body**, zeroing the first instruction of the case the UI factory jumps to for pl005. It hid for weeks because the old 4-row table ended at exactly `0x1411B4C58`, so its terminator sat on the case body and whoever wrote last won | `CAVE_END_VA = 0x1411B4C50` plus a hard `GAUGE_CASE_VA` guard in `_fit()` |
| **fault offset `0x13A2C36`**, on attacking, inside our own cave | `fight_gate_v1.py` | that `rdi` was the fighter — "proved" by `movsxd rax,[rdi+0x1094]` at `0x1403C2D74`, **13 KB later inside a 21 KB function**, applied to a site at `0x1403BF480`; the installer then "verified" that signature function-wide and reported green | `rdi` is the attack-parameter reader's **second argument** (`mov rdi, rdx` in its prologue) and is reassigned later | patch where the value is an **argument**: `fight_gate3.py` hooks inside `0x14046C2E0`, whose own first parameter is the fighter, and every `fight_gate2.py` stub reads `rcx` at a call boundary |
| crash at `0x16C1000` | logger builds, on scene **backout** only | — | the `.data`-cave logger stub at `0x1416C1000` was clobbered during backout | load-time capture still works; deprioritised |
| crash/hang from instrumentation | logging `0x25ED40` at `0x25EDAF` | — | it is a per-frame function; file I/O there trips timing anti-cheat | only instrument once-per-load functions |
| clobbered next instruction (D4) | nav work | — | hooked `0x140255DE2`, a 4-byte instruction, with a 5-byte `jmp` | assert hook-site instruction length ≥ 5 via capstone |
| boot crash (v1) and mouse crash (D5) | nav work | — | `movabs r11, 0x1416C2000` — an absolute image address under ASLR | `lea reg,[rip+disp]`; builder rejects in-image `movabs` |
| **freeze**, not crash (D9) | nav work | — | a dump loop kept its counter in `rdx`, which the logger destroys, so it never terminated | save every volatile the helper touches |
| refcount imbalance | panel clone | — | the clone addref'd `+8` instead of `+0xC` | addref **both** |
| **room-match disconnect** on selecting Zangetsu | online | the patched exe; EAC | `Script/Costume/cos_pl005.fsv` did not exist — all 39 playables have one, pl005 was the only gap; a room match must publish character + costume, the lookup failed, the session dropped him | build it from `cos_pl052.fsv` |
| **no attacks** on seven reserved slots | pre-2026-07-25 | an "exe-side, index-keyed gate"; then "the donor moveset exonerates the data" | `plNNN.tcmbpkg` missing from `file_exist.htable` | one htable entry per character |
| **silent revert** of pl005 work after a "community patch" install | 2026-07-30 | that the community patch installer was the culprit | a stale 234-file `Overlay/` snapshot from Jul 26 09:44 in the dev build; 232 of 234 files were byte-identical to live and the two that differed were `Fnames/file_exist.htable` (837,156 B) and `Fnames/filename.bin` (1,672,069 B) — the exact size and mtime of the rolled-back live files | rebuild `Overlay/` before every release |
| **broken roster** after a wipe (Zangetsu absent, Hiyori icon blank) | 2026-07-26 | that the raw payload folders were a valid rebuild source | `Zangetsu Patch/Files/` and `Hiyori PL009/` carry 39-cell-era `CharaSelect.bin`, `icon_list.bin` and `chara_icon.cat` | Berg's packaged install is the base of truth; our fix files are an overlay on top |

**★★★ Lessons, in the order they would have saved time**

1. An unexplained md5 is a bug, not noise.
2. To find who jumps to address X, **search for X as data, not as a branch.** No rel32 pointed at `0x1411B4C50`; the RVA as a dword found it instantly, in a jump table.
3. A backup only restores what it contains — check its date against the *writer* of the region.
4. **Locality beats volume of evidence.** The `0x13A2C36` crash had *more* supporting evidence than the six correct stubs — just evidence about the wrong address. A signature that is not local to the patch site proves nothing about the site, and such a check is worse than none because it manufactures confidence.
5. **Prefer a branch the game already takes.** `fight_gate3.py` jumps to `0x14046C3A6`, the same "do not accrue" exit three shipped conditions use, so no register, stack or xmm state has to be reasoned about.
6. When one condition needs two flavours, **vary the stub, not the site list** — emit variants from one generator and lay them out on a `max(len)` stride so index arithmetic never depends on which variant a site got.
7. When you cannot tell *which* call site does something, ask **when** instead — look for a state flag the engine already keeps for its own per-character rules.
8. **The fighter is not reached the same way at every site.** Component → fighter is `+0x500`, guarded by a weak-ref control block at `+0x520`; fighter → rival is `+0x5D0`, object at `+0x5F0`, control at `+0x610`. Both guards check the block non-null **and** the refcount at `+8` non-zero before dereferencing — copy what the engine does rather than settling for a null test.

### Packaging and delivery

#### How the launcher installs a version

Read from the launcher source, `launch()` at roughly line 735:

1. `version_chain(v)` walks `base.txt` upward to produce `[root, …, v]`, cycle-safe and missing-parent-safe.
2. **The chain root is mirrored** — `injectFolder(root, "Script"/"Motion")` uses `robocopy /MIR`, and `00HIGH`/`01MIDDLE` are merged. **Every child is merged, not mirrored.** This is precisely why an add-on ships only the handful of files it changes, and why `Script` and `Motion` revert cleanly when switching versions: the mirror wipes whatever is not in the base.
3. `install_overlay(v)` merges `<version>/Overlay/**` onto the game root, parents first so a child wins. Each write is recorded in `launcher_patch_state.json`. On revert, a file the launcher **created** is deleted; a stock file it **overwrote** is restored from `_launcher_vanilla_backup/`, captured the first time that path is touched — and deliberately *not* re-captured if the path was in the previous version's list, so our own file never gets mistaken for the player's.
4. `setup_exe(v)` walks the chain and uses the **last** `<version>/Exe/exe_patch.recipe` found, so a child's recipe overrides its parent's. With no recipe anywhere in the chain it restores the exe backup — that is how reverting to vanilla works.
5. The version dropdown is just `os.listdir(GameVersions)`, so a new folder appears automatically.

**⚠ Rebuild `Overlay/` before every release.** The dev build's `Overlay/` is a snapshot, and a stale one silently rolls the live install back. It also currently ships three stray `.pre*_bak` files to end users. What the 2026-07-30 rollback destroyed and how each item was recovered:

| file | recovered from |
|---|---|
| `Fnames/file_exist.htable` | live was an exact ordered **subset** of `.presp2_bak` — 3 missing, **0 live-only**, i.e. the community patch contributed nothing. Re-added 7 entries → 104,651 |
| `Fnames/filename.bin` | exact ordered subset of the dev copy — 1 triple missing, 0 live-only. Re-added `('pl005_pic2', '.lds', 'pl005_pic2')` → 28,606 triples |
| `Script/Action/pl005.tcmbpkg` | node `sp_atk02` id 73 gone and `start_sp_atk02` (19) emptied → `restore_sp2_routing.py` |
| `Sound/{English(US),Japanese(JP)}/pl005.bnk` | select-voice line gone; dev copy (identical to live `sp000.bnk`) |
| `Demo/pl005_ct_evolve`, `_ct_revolut`, `_evo_ct_revolut`, `_ct_sp_break01_maxout` | retarget and camera work gone; dev copies |

Survived intact: `pl005.tadjpkg` (226 entries, *ahead* of dev — it holds Berg's hand-tuned 68-block SP2), `pl005.tactpkg`, `CharaStatus.fsv`, `WepVisible.fsv`, `chara_bgm.tbl`, `cos_pl005.fsv`, `bgm.bnk` and its 8 `.wem`, `Text/CommonText.cat`, all UI/icon/banner assets, all `Model/chara`.

The repair scripts are deliberately narrow: `restore_sp2_routing.py` touches **tcmb only** and specifically does not re-run `build_sp2.py`, which would rebuild the tadj entry from pl052 and destroy Berg's tuning. `restore_fnames_registrations.py` re-adds the menu, `pic2` and sp2-effect registrations with `--dry`/`--revert` and `.prerestore_bak` backups.

**★ Rule: never assemble a version by diffing the live game against the base.** The live `Script/Action` holds `.tadjpkg` files that differ for unrelated reasons — balance drift, other people's reworks — and a diff-based copy imports all of it silently. **List files explicitly.** The same trap bit the Hiyori packaging from the other direction: an installer built by walking the staged tree swept in an *older* `chara_icon.cat` and would have reverted the select-grid icon. Package from an explicit whitelist of files actually modified.

`sync_to_dev.py` has known gaps: its `ROOTS` omits `00HIGH|01MIDDLE/Model` and `Effect`, so model and effect edits are invisible to it, and `Script/chara_bgm.tbl` and `Script/Costume/cos_pl005.fsv` have no backup sibling, so future edits to them are not detected. It identifies modified files by their `.pre*_bak` sibling, which means files we **created** have no backup and must be listed in its `CREATED` set.

#### The exe recipe

`Exe/exe_patch.recipe` is zlib-compressed JSON:

```
{grow_at, grow, sec_hdr:[[hdr_off, val], …], ops:[[file_off, "hex"], …],
 md5,                                        <- what a correct replay must produce
 src_md5, src_size, alt_sources:[{name, md5, size, ops}]}   <- accepted starting binaries
```

Replay (`cre_exe_caves.py:do_recipe`, around line 735): pick a source whose md5 matches `src_md5` or an alt; apply that alt's normalising ops; insert `grow` zero bytes at `grow_at`; write `sec_hdr`; apply `ops`; compare against the live exe and **fail fatally on any undeclared divergence**. The launcher always rebuilds **from the verified backup, never from the live exe**, and md5-checks both ends.

**Always carry `alt_sources` forward into a new recipe**, or every teammate with an unmodified exe is rejected. It normalises a player's stock Steam binary up to the project's reference build so everyone lands on a byte-identical exe and therefore shares a matchmaking pool:

```json
{"name":"stock Steam v1.3.0.0",
 "md5":"7b21356622f2fe8d4a1733e74634abd8",
 "size":28283464,
 "ops":[[5441020,"0f57c99090909090"]]}
```

That single op is the one hand edit the reference build carries: `movss xmm1,[..]` → `xorps xmm1,xmm1` plus NOPs, at file offset `0x5305FC` (= 5,441,020 decimal).

Known binaries and hashes:

| artefact | md5 / size |
|---|---|
| stock Steam v1.3.0.0 | `7b21356622f2fe8d4a1733e74634abd8`, 28,283,464 B |
| reference build | `b505c023f0c3…` |
| D10, 39 cells, offline-complete | `c7dffb3107341f4f06e410f79c0cc6be` |
| 40-cell shipping exe | `c360f4b98c9dd8fd5228a81cbc16426d` |
| live exe as of 2026-08-10 | `56fae3f6…`, 28,286,024 B (= stock + `grow` 2560) |
| recipe's own recorded md5 as of 2026-08-06 | `eb74030d…` |
| "fully reverted" checkpoint | `f084d7b9b7c15141a187fb3a4e37af9d` |
| superseded Zangetsu-solo recipe | `0fc6e4aaa5e1…` |

**⚠ Contradiction in the notes.** The launcher note (2026-07-26) records `_launcher_vanilla_backup/…exe` **and** `…exe.pre_gridpatch_bak` as the reference build `b505c023f0c3`, with `Patch_Dev_Environment/Clean_EXE/…exe` as stock Steam `7b213566`. The cave note (2026-08-10) records `BLEACH_Rebirth_of_Souls.exe.pre_gridpatch_bak` (along with `.prestagegate_bak` and `.selftest`) as **stock Steam** `7b21356622f2fe8d4a1733e74634abd8`, 28,283,464 B. These cannot both be true of the same file; verify the hash before trusting either as a replay source.

**⚠⚠ Open as of 2026-08-10: three exe patches are not in the recipe.** The dev build does not ship an exe at all — `sync_to_dev.py` skips `.exe` entirely and the release carries only `Exe/exe_patch.recipe`, which the launcher replays onto the player's own binary. Recorded ops stop at 2026-08-06. Missing, in order: `ui_ctrl_v1_ownlogic.py` (the `.rdata` R-X flip at file `0x2D4`, the gauge driver and guard at `0x1413A2300`–`0x1413A2700`, and its hooks), `fight_gate2.py` (11 × 5-byte detours plus 1089 B of cave at `0x1413A2B00`), and `fight_gate3.py` (one 6-byte detour at `0x14046C30E` plus 78 B of cave at `0x1413A3000`). None of the three calls `do_recipe`. The scripts that do — `cre_exe_caves`, `aizen_counter_cost`, `grid_cells_40_41`, `grid_heapfix`, `move_names_own_entry`, `stage_new_id_gate` — are the pattern to copy; `_recipe_put` (line 620) already handles patch-into, supersede and append correctly, so a catch-up script only has to hand it the spans. ⚠ `do_recipe`'s `allow` dict hardcodes the three `aizen_counter_cost` spans as known-divergent, so a catch-up must declare its own spans the same way or the verifier will call them undeclared. **Do not ship a release believing the fighting-spirit work is in it until this is closed.** (The notes name `grid_cells_40_41.py` and `grid_heapfix.py` as recipe-registering scripts but do not document their internals beyond that.)

Since the exe is 28 MB and the device commit cap is 20 MB, **recipe-on-device is the delivery path** — self-contained installers rebuild the exe from `.pre_gridpatch_bak` with md5 guards rather than shipping a binary.

#### The shipping version, built 2026-07-26

`GameVersions/Bleach Rebirth of Souls Community Patch + Zangetsu + Hiyori`, `base.txt` → `Bleach Rebirth of Souls Community Patch` — deliberately **not** the "+ Zangetsu" version. Three files are **roster-wide**, not per-character: `Script/CharaSelect.bin`, `Fnames/filename.bin`, `Fnames/file_exist.htable`. A chain would have the child wholly replace all three anyway, buying nothing while creating a parent that is only valid in combination. Shipping both characters from one version also keeps the exe honest, because the 40-cell build **requires** both pl005 and pl009 to exist. Balance still inherits from the Community Patch and so can never fork.

Contents: 29 Script/Motion files plus 221 Overlay files, 183 MB, all verified byte-identical to the live game. Assembled by `Zangetsu Patch/assemble_zangetsu_hiyori_version.py <gamedir>`, which is idempotent by size and mtime (deletion is unavailable on the dev mount), uses explicit file lists, writes `Overlay/_overlay_manifest.json`, and reports missing files without failing. Expected "missing": `Script/AiParam/AiParam_pl005.fsv` (never created for Zangetsu) and `Script/Action/pl009_modded.tadjpkg` (only pl005 has a `_modded` variant).

**⚠ Superseded, do not ship:** `Bleach Rebirth of Souls Community Patch + Zangetsu` (recipe → `0fc6e4aaa5e1…`) and `Zangetsu DEBUG (probe build)` predate the relocation-completeness work — their 39-cell exe is missing the three `lea rsi,[rdi+0xD98]` relocations in `0x14025C170`, i.e. latent heap corruption, plus the wrong-field clone addref. Their data files also must not simply be refreshed from the live game, because the live `CharaSelect.bin` now has 39 roster entries, which would overrun a 39-cell grid. Keeping a Zangetsu-solo option means rebuilding a corrected **39-cell** recipe (approach E plus the 3 missed sites, object stays `0x1978`, one clone, nav id 38, `NEW_IDS=(5,)`) *and* a 38-entry `CharaSelect.bin` with pl009-free Fnames. Not done — retire them or ask Berg.

#### The runtime patcher, and where the exe changes are heading

The community patch applies gameplay changes at runtime through **`dinput8.dll`**, a proxy the game loads because it statically imports `dinput8.dll!DirectInput8Create`. The installer copies `Files/Matchmaking/dinput8.dll` into the game directory. Canonical source is `<repo>/Files/Matchmaking/dinput8_proxy.c`, 26,435 B, with six components: the matchmaking hook, `patch_version_string`, `patch_yamamoto_selfcost`, `patch_byakuya_evo_icon`, `patch_aizen_kikon_counter`, `patch_aizen_flamecost`.

**★★ The 2026-08-05 lesson generalises to any binary deliverable:** four divergent copies of the `.c` existed and each was missing patches the others had, but the real defect was that the **shipped `.dll` was older than all of them**, containing only `VERSION` and `BYAKUYA_ICON`. Two separately reported bugs had that one cause. **Check the binary, not the source** — `strings dinput8.dll | grep -E 'SELFCOST|AIZEN|BYAKUYA'` lists what it actually contains. A related trap: `patch_byakuya_evo_icon`'s call had been commented out in the dev build, so a dev→live push would have silently dropped Byakuya's icon.

Also from that merge: a guard that only recognises the *pristine* form of an instruction can never match on a machine where the patch is already baked in, and will print a misleading "(game updated?)". **Guards must be idempotent** and recognise the already-patched form. And there is a stale separate clone at `<gamedir>/Bleach-Rebirth-of-Souls-Community-Patch/` (Jul 14–21) holding the oldest 76 KB DLL — the same silent-revert hazard as the stale `Overlay/`.

**Hard constraint (Berg):** the Steam matchmaking hook — the issuer tag/filter plus join guard that keeps patched players in their own pool — **must stay**; unpatched and patched clients desync, so it is a correctness requirement, not a convenience.

Build note: the shipped DLL is Mingw-w64 (its `.rdata` carries "Mingw-w64 runtime failure:" and it has a `.buildid` section). There is no mingw in the sandbox, but `pip install ziglang` then `zig cc -target x86_64-windows-gnu` works. A zig-built candidate sits at `Patch_Dev_Environment/Files/Matchmaking/dinput8.dll.zigbuild-candidate`, deliberately **not** placed over the shipped DLL, because it is untested and every player loads that file.

**Pending direction:** Berg wants the gameplay patches moved from DLL injection into the `Exe/exe_patch.recipe` mechanism ahead of the DLC release, keeping matchmaking in the DLL. Not started. The online notes record the opposite decision for the *roster* changes — port the exe changes **into** `dinput8.dll` as runtime memory patches so the on-disk exe stays vanilla and survives Steam verify — with `apply_D10.py` kept as the dev-loop tool. **These two decisions point in opposite directions and the notes do not record which supersedes the other.**

### Online and room match

Measured symptoms, before the fix: in **room match**, the instant Zangetsu is selected the client is disconnected from the room, and it **persists** — the pick is saved to the profile, so re-entering a room disconnects again until the player changes character in ranked or free battle. In **ranked**, selecting him does not disconnect (matchmaking never started) but the ranked character portrait never loads. Picking any normal character in the same flow is fine, which is what cleared the patched exe of suspicion.

**Root cause: missing per-character files.** A file-existence diff of every `pl052` asset against its `pl005` twin found the decisive gap — `Script/Costume/cos_pl005.fsv` did not exist, and all 39 playables have one. A room match has to publish character *and* costume for each player; the costume lookup failed and the session dropped him.

Also missing and now filled: `00HIGH/ui/swap/spirit_chara_icon/pl005_pic1.lds` (the **ranked portrait**; `pic1` is present for every real character, `pic2` is optional — pl016 and pl050 lack it), `01MIDDLE/ui/swap/spirit_chara_icon/pl005_pic0.lds` and `pl005_pic1.lds`, and `01MIDDLE` + `02LOW` `Graphics/chara/pl005_edited_graphics.fsv`. Still missing at lower priority: `Script/AiParam/AiParam_pl005.fsv` (AI only — `AiActList_pl005.fsv` exists; `filename.bin` already lists `ai_param_pl005`, so once the file exists only an htable entry is needed), alternate-costume models (`cos00_01`, `face01`, `doll`, `wep02/03`) with their `.cphy` files, and `Effect/spfx/pl005`.

The costume file itself is `_cso_`-ciphered CSV — decode and encode with `Script/fsv2csv.py` (`decode_cso_bytes` / `encode_cso_bytes`). Structure: a long header row (`_csv0,name_00,mission_only,dlc_id,DBodyYure,DHairYure,cos_type,body_00,hair_00,face_00,weapon_00_00…`), one row per costume (`cos_00`, `cos_01`, `awk_01`, `cos_02`, …), then a trailing junk/footer line — **work on bytes, not decoded text, to preserve that footer.** Blank fields on `cos_00` mean "use the defaults from `CharaModelVisible`". `cos_pl005.fsv` was built from `cos_pl052.fsv` by keeping the header, keeping the `cos_00` row with `pl052` → `pl005`, **dropping the `cos_01` row** (it would reference a `pl005_cos00_01` model that does not exist), and keeping the footer. Round-trip verified.

How the game does online, from the launcher source: `setup_matchmaking()` writes `patch_ranked.txt` containing `100000 + crc32("<git short sha>|<gameVersion>") % 800000`, so the same build and version share a pool; `read_loaded_code()` confirms it from `match code <n> loaded` in `patch_ranked.log`. `launch_patched()` starts the **raw exe directly** so EasyAntiCheat cannot block the injected DLL — meaning **EAC is not gating patched online play**, and a modified on-disk exe was never the disconnect cause. (`version.dll` / Koaloader only ever reached the EAC launcher, which is why `dinput8.dll` is the injection vector.)

Online class surface, recorded in case instrumentation is needed again: `OOnlinePlayable` `0x14142C178`, `OnlineRoomManager` `0x141486F48`, `SRoomMatch` `0x1414A4A80`, `RoomMatchUiCtrl` `0x14144AA98`, `NetworkManager` `0x141486E38`. Session-state strings are packed at `0x141486C00`+ (`Disconnect`, `CreateSession`, `CreateSessionWait`, `SearchSessionError`, `JoinSessionOtherResponsibility`, `NotFound`), referenced rip-relatively with no pointer table. `RoomMatchUiCtrl::ChangeRoomType() eType Error. %d` is at `0x141449F40`.

**Untested:** a match against a real opponent. When that happens, the opponent needs the identical file set — a peer without pl005's assets is a **separate failure mode** from this one.

### Restore point and recovery

**★ The rule, learned the hard way on 2026-07-26:** when the install is wiped, **do not rebuild the roster from `Zangetsu Patch/Files/` + `Hiyori PL009/`**. Those payload folders carry 39-cell-era `CharaSelect.bin`, `icon_list.bin` and `chara_icon.cat`, and produce a broken roster — Zangetsu absent, Hiyori icon blank, both observed. **Berg's packaged install is the base of truth; our fix files are an overlay on top of it.**

The snapshot is `<gamedir>/_BACKUP_Zangetsu_Working_2026-07-26/` — 262 files, 212 MB, mirroring the game tree, containing its own `RESTORE.md`. Restore by copying its contents over the game folder. It includes the exe, Fnames, both characters' models, motion, sound, costume and UI, and all our fixes.

The upstream copy lives at `Patch_Dev_Environment/GameVersions/Bleach Rebirth of Souls Community Patch + Zangetsu + Hiyori/` with layout `Script/` (Action/, Costume/, AiParam/ plus shared tables) · `Motion/` · `Overlay/` (00HIGH, 01MIDDLE, 02LOW, adv_motion, AiAttackData, Demo, Fnames, Physics, Sound — game-relative) · `Exe/` · `base.txt`. Note that `Script/Action/pl005_modded.tadjpkg` was byte-identical to `pl005.tadjpkg`, so both take our build; old versions are kept as `*.pre_spstep_bak`. Sibling directories `Patch/` and `Bleach-Rebirth-of-Souls-Community-Patch/` are the same repo, and `Patch/GameVersions/Bleach Rebirth of Souls/` is a pristine vanilla reference tree, useful for diffs.

**⚠ Location change, 2026-08-08:** the dev environment moved out of the game folder to the git repo at `C:\Users\ramig\Documents\GitHub\Bleach-Rebalance-Of-Souls-Dev-Environment\GameVersions\<version>`; `Patch_Dev_Environment/` is now a stale copy. `sync_to_dev.py` owns `REPO_ROOTS` and `DEV_NAMES`, and nine other scripts import `dev_rel` / `resolve_dev` from it. **Dry-run it first — "N new" on an established tree means it resolved the wrong root.**

The fix set — the only files to re-apply after a wipe:

| file | hash | carries |
|---|---|---|
| `Script/Action/pl005.tcmbpkg` | `be3b7e96` | `sp_step` nodes 105–109, SYU flags on `hi03_1` + `da01` |
| `Script/Action/pl005.tadjpkg` (+ `pl005_modded.tadjpkg` in the dev build) | `9135237e` | `sp_step` 00–02 and `lo03` enders, perfect hoho (`syunpo_out_just`, `syunpo_in_act`/`JustAvoidTiming`), syunpo travel damping, walk 2.5, front step 42→30, `SoulRebootTiming` on hi01/02/03/hi03_1/da01, blur, slow-motion and hitstun tuning |
| `Motion/pl005.tactpkg` | `3ba26cc7` | `sp_step` acts and clips, Kenpachi u01, Halibel hoho swing and pose, Yhwach hoho cutscene body, Yhwach walk clips |
| `Demo/pl005_ct_syunpo_out_just.tdemopkg` | `bef0fb0d` | perfect-hoho cutscene + Yhwach camera |
| `Demo/pl005_ct_sp_break01_maxout.tdemopkg` | `dcab14fb` | kikon cutscene camera |
| `Script/CharaStatus.fsv` + `_modded.fsv` | edit in place | `def_atk_size` 中→小 — **re-derive from the current file, never overwrite**; the package already carries the locomotion, guard_hp and kyokaku fixes |
| banner | copy | that LOD's `ui/swap/spirit_chara_icon/sp000_pic0.lds` → `pl005_pic0.lds` **and** `pl005_pic1.lds`, in **both** LODs (00HIGH art `84f354a4`, 01MIDDLE `4e2aac8a` — they differ by design) |

Verified 2026-07-26 in both the live game and the dev build: ours as above, `def_atk_size = 小`, banner in both LODs. Base untouched and matching between live and dev: Fnames `216ede9b` + `4bfbd163`, `CharaSelect.bin` `c6351f7d`, `icon_list.bin` `2bfd2466`, `chara_icon.cat` `5a4d4ca7` (40-cell), pl009 action files, `cos_pl005` `3b915c5d`, `WepBind` `be6bdb22` (pl005 = `weapon_R`).

**⚠ Gotcha when verifying:** `_cso_` files re-encrypt with a **random key on every save**, so identical content yields different bytes and different file sizes. Always compare **decoded payloads**, never file hashes, for those.agentId: a54ecddab48af7428 (use SendMessage with to: 'a54ecddab48af7428', summary: '<5-10 word recap>' to continue this agent)
<usage>subagent_tokens: 128031
tool_uses: 19
duration_ms: 662587</usage>


---

## Part 2 — Identity, assets and the model

Everything in this section answers one question: what makes pl005 read as Old Man Zangetsu rather than as `sp000`, the story boss he was cloned from. The engine resolves a character's name, moves, voice, models, textures and portraits through five independent lookup systems — a length-seeded CRC map for text, an FNV-1 hash space for audio, two `.fsv` stem tables for geometry, a filename-plus-internal-id scheme for UI textures, and a per-form float in `CharaModelVisible.fsv` for size. Each was cracked separately, and the recurring failure mode across all five is the same: the port inherits the donor's identity in a table nobody thought to look at.

---

## 1. Text and strings

### 1.1 What is and is not covered

The notes fully document two string systems: **move names** (solved, shipped, extensible) and **costume names** (`cos_name_*`, still borrowed from a donor). They document the container format, `Text/CommonText.cat`, in enough detail to append arbitrary records.

The **character's own display name** is thin in the notes. `Script/CharaNameTextID.fsv` appears exactly once — in the `.fsv` structural sweep that hunted the weapon bug (Section 6), where it is listed as a table carrying bare-LF endings but intact content. No note records how pl005's roster name string was chosen or written. Treat the character-name path as undocumented rather than solved.

### 1.2 Move names are a hash→hash map, not a table

The single finding that made this tractable: **the map's value is a hash, not a string id and not an index.**

```
crc32_lenseeded(slot key)  ->  crc32_lenseeded(CommonText key)
```

Both sides use the same length-seeded CRC-32 that `fnames_patch.build_crc` implements, table at `0x1414172C0`. The confirming datum is `crc("BASE_ACT_SPI_UNIQUE2") == 0x783C57BC == T2[4088]` in `CommonText.cat`. **The exe only ever compares hashes, never strings — so keys are forgeable.** That is what permits inventing a brand-new key like `skillNamePl005_02` and having the engine resolve it.

### 1.3 The resolution chain

| step | function / address | behaviour |
|---|---|---|
| 1 | `ActionUI` `sub_1401E4D70` | switches on skill kind: **8** = SP1, **9** = SP2, **0xa** = Reverse, **0xb** = Hohou |
| 2 | `sub_140204320`, branch at `0x1402045A0` | stores a hard-coded default, `BASE_ACT_SPI_UNIQUE1` / `UNIQUE2` |
| 3 | `sub_140203D70` | composes `"pl%03d" + (_nml\|_tra\|_ura\|_htr) + (_kik_\|_spc_) + i + "_" + j` (e.g. `pl018_nml_spc_1_0`), CRCs it, looks it up in the `unordered_map<u32,u32>` at **`0x141CFAC18`**. Hit replaces the default; miss leaves it |
| 4 | `sub_140201220` | builds the map from **291 baked `.rdata` literals**; the first 260 are paired positionally with `SKILL_SPECIAL_ACT1..260`. Writes `crc32("SKILL_SPECIAL_ACT"+n)` to `node+0x14` |
| 5 | `sub_140204320` at `0x1402047CB` → `sub_14059DB40` | reads that hash back and hands it to the CommonText resolver |

### 1.4 The shipped solution: `Zangetsu Patch/move_names_own_entry.py`

Route (a) was chosen: a `.text` **code cave that appends rows to the engine's own map after it is built**, rather than growing the baked `.rdata` literal set.

- Cave VA `0x1411B4BB0` / file offset `0x11B3FB0`, **168 bytes used** in the zero tail of the existing char-select cave — **~936 bytes free, roughly 120 more rows.**
- Hook VA `0x1401F7DC3` / file offset `0x1F71C3`. The 7-byte `lea rax,[rbx+0x2c98]` is replaced with `jmp cave` plus 2 `nop`s. That site is **after both `sub_140201220` calls**, so the map is fully built when the cave runs. The cave re-executes the stolen `lea` and returns to `0x1401F7DCA`.
- Guarded with `test`/`je` so it never inserts into an unbuilt map. **No absolute image addresses — ASLR-safe.**

Shipped content: pl005's SP2 is **"Schattenmond"**, carried by a new `.cat` record `skillNamePl005_02` (key hash `0xB36444F2`) in all 15 languages. `BASE_ACT_SPI_UNIQUE2` was **restored byte-for-byte to the shipped generic text**, so no other character is affected by the change.

`Exe/exe_patch.recipe` was updated, and **recipe replay from the stock Steam binary reproduces the live exe byte-for-byte**; the recipe was verified clean beforehand (no unrecorded hand edits had accumulated). The exe md5 moved `c360f4b9…` → **`8ff2546318d21a7e8636208348f166ef`**, at the same 28286024 bytes.

> **`move_names.py` is SUPERSEDED — DO NOT RUN.** It predates the banner work and would clobber it. Its `.cat` parser is still imported and used by the successor script, so do not delete the file.

### 1.5 One row per character

Adding a future character's move names is a single edit to the `ROWS` list, then a re-run:

```python
dict(pl=9, kind='spc', i=0, j=0, key='skillNamePl009_00', name='<Hiyori SP1>'),
dict(pl=9, kind='spc', i=1, j=0, key='skillNamePl009_01', name='<Hiyori SP2>'),
dict(pl=9, kind='kik', i=0, j=0, key='skillNamePl009_10', name='<Hiyori kikon>'),
```

`i` selects the move: `0` = SP move 1, `1` = SP move 2. `kind='kik'` names the kikon instead of a special. `forms` defaults to all four (`_nml/_tra/_ura/_htr`) at **8 cave bytes each**. `langs=None` writes all 15 locales.

The `skillNamePl<NNN>_<NN>` namespace is free for ids **005, 009, 015, 021, 028, 030, 034, 040, 041, 043+**.

**pl005's SP1 still displays "Spiritual Pressure Move 1"** — no row exists for it yet, pending a finalised sp1.

### 1.6 `Text/CommonText.cat` — records can be appended

The container is PZZE wrapping **one raw zlib stream**; re-deflate at **level 1** so the stream still begins `78 01`. The payload is:

```
u32 3 | u32 N | u32 0
u32 T0[N]  record offset
u32 T1[N]  stride
u32 T2[N]  key hash
u32 T3[N]  all 1
then N records:
  +0x08  key hash
  +0x18  blockSize
  +0x20  langCount = 15
  +0x24  key NUL, then (lang NUL value NUL) x 15, UTF-8
  stride == 0x20 + blockSize
```

Appending grew all four tables by one and shifted every prior `T0` by `+16`; **no existing index moved** (9338 → 9339 records). This is safe because **T2 is unsorted** — nothing binary-searches it — and because shipped `.cat` files across the game range from `N=3` to `N=9436` with an identical layout, so nothing is hard-coded to a particular size.

The earlier costume note recorded CommonText writing as blocked ("WRITING needs hash/index reversal"); that block was cleared by the move-names work of 2026-08-01. The two notes are chronological, not contradictory. What the notes do **not** record is any `cos_name_*` record actually being written — that remains the open item.

> The launcher overlay does **not** manage `Text/`. Verify persistence of any `.cat` edit through a launcher cycle before relying on it.

### 1.7 Verification and the untested edges

An exhaustive CRC-collision sweep of **all 7680** composable slot keys (pl000–079 × 4 forms × kik/spc × i0–3 × j0–2) found **no collision**. The `.cat` diff was 1 record added, 1 changed, 9337 byte-identical. `--revert` round-trips to the exact original md5s and re-application is idempotent.

Nothing has been run in game. The failure modes are asymmetric and worth knowing before a test:

- **Hook misfire** ⇒ pl005's SP2 reads "Spiritual Pressure Move 2". Cosmetic, not a crash, and it would surface at **battle start**, not in menus.
- **Bad `.cat` record** ⇒ loud and global; all UI text breaks. `--revert` fixes it instantly.
- `_htr` form selection (`j & 0x20`) and the 2-bit `j` suffix are **derived from disassembly, not observed**.

### 1.8 What breaks when a string is missing

Missing strings in this engine degrade rather than crash, which is why several of them survived for weeks:

| missing string | visible result |
|---|---|
| move-name map row | falls back to the hard-coded `BASE_ACT_SPI_UNIQUE1/2` generic text ("Spiritual Pressure Move 1/2") |
| `cos_name_pl005_*` / `cos_name_pl009_*` | do not exist; both ports borrow `cos_name_pl000_*`, and **`cos_name_pl000_*` is Yhwach's text** — labels are wrong but harmless |
| `CharaSelect.bin` S3 payload left as the donor's | the select screen prints the donor's Kikon text. Hiyori's payload was byte-identical to Rukia's (pl010), which is exactly why the screen listed "Somenomai. Tsukishiro" |
| `CharaSelect.bin` S3 payload zeroed | no move text shown at all — this is Zangetsu's state and is the correct default for an added character |
| `Script/Skill_list.fsv` row | the pause-menu **Skills page** has nothing to show. 246 columns, one row per playable, and **pl005 has no row at all.** Separate table, separate job, still open |

> Text-id numbering does not follow pl numbering. `cos_name_pl000_*` mapping to Yhwach is the proof. **Verify every label in-game rather than assuming the index.**

---

## 2. Voice

### 2.1 What a playable carries and what pl005 had

Playable characters carry **138–458 voice lines (median 236)**, **11 `chara_select` events**, and roughly 80 `plNNNsys00NNN` system lines. **pl005 has 83 lines and zero of either category** — and so do pl009 and every reserved slot. All 83 are combat vocalisations (attack, parry, guardbreak, step, plus one cutscene pair); **none are speech**, because a story boss never needed a menu voice. Median line length 0.95 s.

### 2.2 `pl005.bnk` is `sp000.bnk`, byte-identical

Only the companion `.txt` was renamed to `pl005_*`. **Every object ID inside is still hashed from an `sp000_*` name**, which is why his tuning-adjust `Voice` blocks correctly name `sp000_atk_lo_vo`. Resolve anything in this bank by its **sp000** name; the pl005 names are cosmetic.

### 2.3 Wwise bank format (bank version 150)

A `.bnk` is a sequence of 4-character tag + `u32` size chunks: `BKHD | DIDX | DATA | HIRC`. **HIRC is last, so appending objects is safe** — fix the object count at `HIRC+0` and the chunk size at `HIRC−4`.

```
HIRC object:  u8 type | u32 size | u32 id | body
  Event  (4, 9B)   u32 id | u8 action_count | u32 action_id[]
  Action (3, 22B)  u32 id | u16 type (0x0403=Play) | u32 target
                   | u8 bIsBus | u8 props | u8 ranges | u8 flags | u32 bank_id | u32
  Sound  (2)       u32 id | u32 plugin_id | u8 stream_type | u32 source_id  ← offset 9
```

**Event and Action IDs are FNV-1 32-bit over the lowercased name** (offset basis 2166136261, prime 16777619). Verified against shipped data: `pl000_chara_select` = 4199199434 and `pl000_chara_select_Stop` = 1789707001. **Sound object IDs are authoring GUIDs, not hashes** — only `source_id` (the wem) is derivable.

> **TRAP:** a line name appears in **two** sections of the companion `.txt` with different IDs — the Event section (name hash) and In Memory Audio (wem id). Reading the file top-down gets the wrong one. Because **every line has its own Event**, the reliable resolution is to follow `Event(fnv(sp000act00NNN)) → Action → target` rather than hunting `source_id`.

### 2.4 Bug: the select voice event did not fire (pass 2, 2026-07-27)

**Symptom.** A structurally correct `pl005_chara_select` Event → Action → Sound chain was written into `pl005.bnk` and produced no audio in game.

**What was checked and eliminated.** The chain was verified correct in both language banks. `Sound/*/pl005.bnk` **is** registered in the htable. There are **no hardcoded event IDs in the exe**, so the name must be built at runtime — `_chara_select` exists as a literal inside a UI-name cluster. Structurally the new event is identical to pl000's working one except that pl000's Play action carries one extra property, **id `0x39`, value 750** (a delay). A `_Stop` event is **not** required for Play to work.

**Leading hypothesis (unconfirmed).** pl005 loads **`sp000.bnk`, not `pl005.bnk`** — his models resolve to `sp000_*` via `CharaModelVisible`, and every `Voice` block in his tuning names `sp000_*` events.

**Actions taken.**

1. The event was **also written into `sp000.bnk`**, both languages. Since `pl005.bnk` is a byte-identical copy, covering both costs nothing and the extra event is inert for the story boss.
2. **`Motion/Menu/menu_pl005.tactpkg` was registered** (`register_menu_pkg.py`, crc `0x40658204`, dir `0x326a9f45`, inserted after `menu_pl004`). It was **missing from the htable** — the select-screen pose/weapon package, part of the same seven-slot omission family, held back behind `fix_attacks.py --all` and never applied, even though the `.bnk` entries from that same list *were*. Entry count 104644 → 104645.
3. `add_select_voice.py` now takes a bank list, and `--revert` covers all four files.

**Status: still untested.** If it stays silent, the remaining suspects are **bus/state routing** (his lines sit under battle-voice mixers) or **the select screen not loading a per-character bank at all**.

> **Registration rule (applies project-wide):** patch the **current** htable incrementally. Re-running `fix_attacks.py` would drop the pl036 costume registrations, exactly as re-running `fnames_patch.py` would.

### 2.5 What shipped

```
pl005_chara_select = 1101277789
  -> action 4118577550
  -> Sound 736697221
  -> pl005act00281  ( = sp000act00281 )
```

`sp000act00281` is his high guard-break, **2.30 s JP / 2.11 s EN** — his longest deliberate vocalisation, chosen because none of the 83 lines is speech. Written to both the `Japanese(JP)` and `English(US)` banks; each grew **316 → 318 HIRC objects** and the object walk closes clean. Berg's word for it: "placeholder."

**No `_Stop` event was written.** This bank has no Stop action to copy — all 103 actions are `0x0403` Play — and fabricating one is guesswork. If the line overlaps itself when scrolling the roster quickly, that is the cause.

Untested in game. One unverified assumption underpins it: that the engine builds the event name by concatenating the character id. This is near-certain, since all 39 playables follow `plNNN_chara_select`.

### 2.6 Audio decoding — blocked, needs external tooling

The wems are **Wwise Vorbis (codec `0xFFFF`, 48 kHz mono)** with stripped headers and packed codebooks, so **ffmpeg cannot read a `.wem`**. The sandbox has no `vgmstream-cli` (no root for apt, nothing on PyPI), and Berg's Windows box has **neither `vgmstream-cli` nor ffmpeg** — checked 2026-07-27 by running `Zangetsu Voice/CONVERT_VOICE.bat` through File Explorer; Python 3.11 and 3.14 are present.

All 83 lines are extracted to `Zangetsu Patch/Zangetsu Voice/{JP,EN}/`, named `<role>__<line>.wem`, alongside `CATALOGUE.md` carrying exact durations computed as `data_size / avg_bytes_per_sec`. **To audition them, drop `vgmstream-cli.exe` beside the `.bat` and re-run it** — it converts to wav+mp3 automatically. `DataChakka-main/bros_audio.py` wraps the same pipeline.

Tooling: `Zangetsu Patch/voice_extract.py` (extract, catalogue, roster survey) and `add_select_voice.py` (add the event; idempotent, writes `.preselect_bak`, supports `--dry` and `--revert`).

> **Running scripts on Berg's PC:** terminals are tier-"click" under computer use, so no typing is possible there. The working pattern is to write a `.bat` into the mounted game folder, open File Explorer, navigate via the address bar (Explorer is full tier, so typing a path works), double-click the batch file, then read its log back through the mount.

---

## 3. Costumes and the costume-slot system

### 3.1 Status

Solved end-to-end and **verified in game on 2026-07-26**. Berg's from-scratch pl036 costume set (`_02` variant, all three forms) works in a brand-new slot after the full pipeline: models placed, `_mdl` + `_tex` triples and htable keys registered, `.fsv` wired with `cos_02` / `awk_02` / `ura_02`. The pl005 menu test and the `_tex` crash fix are both in-game confirmed.

### 3.2 Confirmed behaviour

The costume menu appears **iff there are ≥2 selectable rows in `cos_plXXX.fsv`**. There is no flag and no exe-side cap.

### 3.3 Bug: unregistered model name = instant crash

**Symptom.** `0xc0000005` on selecting or loading the costume.
**Cause.** A costume row references a model name that is not registered in the manifest/htable.
**Fix.** Register it. The useful diagnostic corollary: a model **renamed over an already-registered vanilla name works**, which makes it a cheap way to test whether new art loads at all before touching registration.

### 3.4 Bug: the `_tex` lesson

**Symptom.** Mesh loads, then the game crashes at **`exe+0x982788` (build 1.3.0)**.
**Wrong assumption.** That one manifest triple per model was enough.
**Real cause.** Every model needs **two** manifest triples: `(base, .tmd2, base_mdl)` **and** `(base, .gnf, base_tex)`. The `.gnf` extension is translated by the engine to the on-disk `.lds`. With `_tex` missing, the mesh resolves but the texture pointer is null.
**Fix.** Emit both triples. **The htable wants TRANSLATED paths only** — `.lds` and `.tmd2` across `00HIGH` and `01MIDDLE`, and **no `.gnf` keys**.

### 3.5 The shipped toolkit

Located in `Zangetsu Patch/`, share-ready, also bundled as `BRoS_costume_toolkit.zip`:

- **`register_costume_models.py <gamedir> plNNN VV --src <folder> [--sibling SS] [--dry|--revert]`** — standalone, with the game CRC-32 and the manifest/htable codecs embedded. Copies `plNNN_cosFF_VV` `.lds`/`.tmd2` into both LOD `Model/chara` directories, swaps `chara_type.cat` from `--src` if present (with backup), adds the `_mdl` and `_tex` triples **anchored in the directory node CONTAINING the sibling** — roughly **77 same-named `Model/chara` nodes exist**, so the anchor matters — and adds 4 htable keys per form. Idempotent, and validated by re-deriving the live working tables **byte-exactly** from pre-patch state.
- **`add_costume_slot.py <gamedir> plNNN [--clone cos_01] [--id/--name/--body/--hair/--face] [--awk MODEL] [--ura MODEL] [--count N] [--dry|--revert]`** — `--awk`/`--ura` clone the source costume's variant rows, and weapon overrides carry over. Validated byte-exact against the live `.fsv`.
- **`COSTUME_SLOTS_GUIDE.md`** — the complete shareable writeup including a crash-triage table.

**Order matters: register the models FIRST, then wire the slot.**

### 3.6 Format facts

`cos_plXXX.fsv` is a `_cso_` ciphered CSV with **CRLF** endings, a terminator row, and **16 raw footer bytes that must be preserved verbatim**. Modern files have **154 columns**; older files lack `cos_type`, so **index by header name, never by position**. Rows are named `cos_NN` / `awk_NN` / `ura_NN`. `mission_only` and `dlc_id` are ordinary columns — DLC costumes are plain rows. **An empty cell means "use the default asset."**

Model naming is `plNNN_cosFF_VV`, where `FF` is the form (`00`/`01`/`02` = normal/awakened/reverse) and `VV` the variant. **`.cphy` is per-FORM and shared by all variants of that form.** `chara_type.cat` (under `ui/swap`, identical in both LODs) is the thumbnail atlas; it is pre-registered, so overwrite it and keep a backup.

Weapon columns are `weapon_<slot>_<sub>`, a 12×12 grid of 144 cells whose values are full model names. **`null` is a real, meaningful value** — Tosen uses `weapon_04_00 = null` to remove a slot for a costume. That mechanism was applied to pl005's `cos_01` as `weapon_01_00 = null` to drop the visor.

The runtime slot array has **stride `0xE50`**, a field at `/0x18`, and UTF-16 strings; it is **allocated from the `.fsv` row count**, which is why runtime injection crashes. Edit the files.

### 3.7 Bug: pl005's two costumes were identical

**Symptom.** The costume menu appeared with two entries that looked the same.
**Cause.** `cos_00` is the default look, and later rows are expected to name **only what differs** (e.g. `body_00 = pl027_cos00_01`). Zangetsu had **every cell blank on both rows**, so both resolved to `sp000_cos00_00`.
**Fix.** Populate the differing cells, plus `null` for the visor removal described above.

### 3.8 Live state and cautions

pl005 has 2 slots, default look, Yhwach-text labels; the menu works. pl036 has a 3rd slot carrying Berg's new costume, all forms working. Backups: `*.precos036_bak` (Fnames, `.fsv`, `chara_type`) plus `*.precosadd_bak` / `*.precosreg_bak` written by the scripts.

Recorded hashes at that snapshot: `filename.bin` `8f6b7ea1…` (1,671,636 B), `file_exist.htable` `dc07e5eb…` (**104,494 entries**), `cos_pl036.fsv` `b6310b2f…`. Note this htable count predates the voice-pass registration, which recorded 104644 → 104645; the two figures are separate points in time, not a contradiction, but neither note states what happened in between.

> **`fnames_patch.py` (the pl005-era script) rebuilds from `.orig_bak` using hardcoded lists — NEVER re-run it as-is.** It would drop the pl036 registrations. Use `register_costume_models.py`, which patches the current tables incrementally.

> **ONLINE CAUTION:** costume data is per-machine, so rooms desync against unmodified opponents.

---

## 4. Donor assets — the finding that explains "my edits do nothing"

### 4.1 The finding (2026-07-26)

`Script/CharaModelVisible.fsv` and `Script/WepVisible.fsv` define **which model stems a character actually loads**. For the ported characters, they still name the **donor's** assets.

| char | CharaModelVisible (cosA / faceA / hairA) | WepVisible (wep ids) |
|---|---|---|
| pl009 Hiyori | **en013**_cos00 / en013_face00 / en013_hair00 | **en013**_wep00/01/02 |
| pl005 Zangetsu | **sp000**_cos00 / sp000_face00 / sp000_hair00 | **sp000**_wep00/01 |
| pl027 Kenpachi (vanilla) | pl027_cos00 / pl027_face00 / pl027_hair00 | pl027_wep00 |

**Consequence: the `pl009_*` and `pl005_*` model and texture files on disk are never read.** A developer editing `pl009_cos00_00.lds` sees no change in game because the engine loads `en013_cos00_00.lds`. This was reported independently as "texture changes to pl009 … nothing changed in game," and it is the root cause of the whole "costume edits do nothing" class across the project.

### 4.2 Registration status

Checked via `file_exist.htable`:

- **`pl009_*`** — fully registered in both LODs, so repointing to them will work immediately.
- **`pl005_*`** — **not registered at all** (40 files). Only the `sp000_*` set is registered.
- Character `.lds` files are a **`PZZElds\0` container** (PZZE + zlib), **not a raw DDS** — edits must round-trip the container.

### 4.3 Bug (open): Zangetsu's visor missing on the character-select screen

**Symptom.** The visor renders in battle but is absent on the select screen.
**Asset.** The visor is weapon slot 1, `sp000_wep01_00_00`, 5 KB, with `WepBind bind1_0 = head`.
**Hypothesis (not yet confirmed).** In battle the model resolves through the `WepVisible` stem and works. If the **select screen resolves models by the character id** — i.e. looks for `pl005_wep01_00_00` — the lookup fails because the `pl005_*` set is unregistered.
**Supporting evidence.** Tosen pl025 has a head-mounted mask under **native `pl025_*` names** and works everywhere, which is consistent with the theory.
**Proposed test.** Ask whether **Hiyori shows her weapon on the SELECT screen**. She is en013-backed exactly as Zangetsu is sp000-backed; if her weapon is missing there too, the theory is confirmed.
**Possibly related, unverified.** The voice pass separately discovered that `Motion/Menu/menu_pl005.tactpkg` — described in the notes as *the select-screen pose/weapon package* — was missing from the htable and registered it on 2026-07-27. No note claims this fixed the visor, and the two investigations were not linked at the time. Re-check the visor after that registration before spending effort on the repointing work.

### 4.4 The fix to push

Repoint the ported characters at their own asset names, so that edits take effect and the donor NPC stays clean:

1. `CharaModelVisible.fsv`: pl009 → `pl009_cos00` / `pl009_face00` / `pl009_hair00`, **keeping `scaleA`**. pl005 → `pl005_*` **only after registering the pl005_* models** — they already exist on disk as byte-identical copies of `sp000_*`; use `register_costume_models.py`, and remember **both** manifest triples (`.tmd2 → _mdl`, `.gnf → _tex`) plus 4 htable keys per model.
2. `WepVisible.fsv`: the same substitution for the weapon ids.
3. Keep each costume row's explicit model names consistent with the new stems.

**Alternative quick fix for a texture artist:** edit the donor-named files (`en013_*`, `sp000_*`) directly — but that also changes the donor enemy/boss wherever they appear in the game.

---

## 5. Hair colour

### 5.1 Solved

Hair colour is **two literal float RGB triples in the `.tmd2` material float-param table**. It is not a texture, not a shader index, and not in the exe.

Tool: `Zangetsu Patch/tmd2_hair_color.py`, with subcommands `show`, `scan <dir>`, `copy <src> <dst> <out>`, `set <file> #RRGGBB <shadow|auto> <out>`. It repacks at zlib level 1 to preserve the `78 01` header.

### 5.2 tmd08 container layout

After PZZE inflation the magic is `tmd0`; the "8" is byte 4 of a per-file `u32`. There are **16 `u32` offsets at `0x28..0x67`**, paired index-wise with **16 `u32` counts at `0x68..0xA7`**. Sections are 16-byte aligned, and `align16(off + cnt*stride) == next offset` — that identity is the structural verifier.

```
0x34 / ----  render command list
0x38 / 0x78  material table      (stride 20 B)
0x3C / 0x7C  float params        (stride  8 B: u32 0 + f32)
0x40 / 0x80  string table
0x48 / 0x88  submesh
0x4C         index buffer
0x50         vertex declaration
0x58         texture bindings
0x5C         vertex buffer
```

A material entry is:

```
u32 name-hash   (3F8BE019 = "hair")
char[4] shader tag
u16 tex0 | u16 texCount | u16 paramBase | u16 paramCount
u32 FFFFFFFF
```

### 5.3 The field

For any material whose **shader tag starts with `BH`** — observed tags `BHA0`, `BHA1`, `BHB1`, `BHG0`, `BHG1`, `BHH1`; the non-hair tags are `BGH0`, `BGH1`, `BSS1`, `HBD1` — with `p = paramBase`:

- `param[p+9 .. p+11]` = **light / base colour RGB** (linear float)
- `param[p+12 .. p+14]` = **shadow colour RGB**
- byte offset = `tmd08[0x3C] + 8*(p+k) + 4`

### 5.4 Correlation evidence

The correlation **passed 20/20 named characters and all 92 hair meshes**. Gin reads `#F3F7FB` (cool white) against Shinji's `#F7F1CD` (warm yellow), both at offset `0x18C`. Two unseeded confirmations landed after the rule was fixed: **pl039 Szayelaporro is literally pink at `#FADBE5`** — which independently matches another modder's report that "Szayel's hair on Gin makes Gin pink" — and **pl042 Nelliel is green at `#DBF4D8`**. Byakuya and Zaraki are **byte-identical** at `(0.142, 0.159, 0.229)` despite carrying *different* shader tags: same colour, same stored value. The proving mesh swap changed **exactly 6 float32 slots** — `0x18C`, `0x194`, `0x19C`, `0x1A4`, `0x1AC`, `0x1B4` — and nothing else.

### 5.5 Cautions

- Params `[1..3]` are an **ambient/SSS tint and are NOT the hue driver** — Harribel's is bluish and does not match her hair.
- **Patch BOTH LODs.** `01MIDDLE` carries an identical copy with identical values.
- **Alt-costume hair needs the same edit per file**: `hair01_00`, `hair02_00`, `hair03_00` (pl000 has three).

### 5.6 Dead ends — never re-run these

1. **`.lds` textures: fully eliminated in-game.** Every surface was painted and tested. The 8×8 DXT1 chips had **no effect despite a genuine 12/12 colour correlation** — they are an LOD placeholder, and that false correlation is what made them look like the answer. The 1024×256 / 2048² / 4096² DXT1 surfaces are mask and normal maps. The 8×8 BC7 had no effect. The 1024×4 BC7 moved hue and detail, but it decodes `#C5C5C5` → black **byte-identically across all characters** — it is a shared greyscale shading gradient, not a per-character colour.
2. **`BLEACH_Rebirth_of_Souls.exe` has no colour table.** Decoys eliminated: `0x018c8bf8` and `0x018c7a1c` are **gamma curves**; the `#00FF00` run at `0x0141a760` is a block of `(0,1,0)` **up-vectors**.
3. **`_edited_graphics.fsv` is definitively not the source** — it is keyed by character id, which never changed during the proving experiment. Its parser is still broken and now irrelevant.
4. **Vertex colours ruled out** at both `u8` and `f16` (numpy `<f2`, strides 8–70, all even bases).
5. **There are no material or shader NAME strings in the `.tmd2`** — every string in the string table is a bone name.

### 5.7 Tooling and open item

`pip install texture2ddecoder --break-system-packages` provides BC1/3/4/5/6/7 decoding, including `decode_bc7`. Written en route and still useful: `hair_color.py` (chip read/write plus `--survey`), `hair_probe.py` (rainbow surface identifier), `hair_ramp.py` (verified BC7 mode-6 solid writer).

**OPEN:** Gin is currently set to green `#00E63C` in both LODs as the confirming test. Backups are `.prehaircol_bak`. **Revert once Berg confirms.**

---

## 6. Model scale per form

Tool: `Zangetsu Patch/set_model_scale.py` (writes `.prescaleA_bak`, supports `--revert`).

### 6.1 The field

`Script/CharaModelVisible.fsv` carries **`scaleA` / `scaleB` / `scaleC` / `scaleD`** — the per-character model render scale, **one per FORM**: A = base, B = evo, C = reverse. Across the roster the values span **0.727** (pl026 Hitsugaya) to **1.35** (pl023 Komamura).

### 6.2 Final values for pl005 (2026-08-10)

| field | form | value | why |
|---|---|---|---|
| `scaleA` | base | **1.13** | pl052 Yhwach's value exactly. His native was 1.136, so a 0.5% change keeps his size while every pl052-authored camera frames him |
| `scaleB` | evo | **1.0** | **ad017's own scale.** The evo model is `cosB = ad017_cos00` |
| `scaleC` | rev | **1.0** | **en028's own scale.** The rev model is `cosC = en028_cos00` |

Reference rows: `sp000` A=1.136 · `en028` A=1 · `ad017` A=1 · `ad018` A=1.047 · `pl001` A=1 B=1 C=1.047 · `pl002` 1.041 · `pl000` 1.0.

⚠ An intermediate pass had these as en028 (evo) and ad018 (rev), from a stale index line — see
Part 13. `scaleB = 1.0` was right regardless, since ad017 and en028 are both 1.0; `scaleC = 1.047`
was ad018's and was wrong, and is what made the rev cutscene aim above the character. The `cos`
columns in the same file name the model per form and remove the guesswork entirely.

### 6.3 Bug: all three forms set to 1.13

**Symptom.** Berg reported the **evo and rev models looked scaled up** to match the base form.
**Wrong model of the field.** The earlier pass treated `scaleA/B/C` as "how big is this character" and set all three to 1.13.
**Real cause.** The field means "how big is *this form's model*," and each form uses a **different donor's** geometry — `cosB = ad017_cos00` for evo, `cosC = en028_cos00` for reverse.
**Fix.** **Read the donor character's own row and copy that, per form.** ★ And take the donor from the `cos` column beside the scale, not from a summary line elsewhere — a first attempt used en028 and ad018, which are the *original plan's* assignment and not the shipped one.

### 6.4 Bug: cutscene framing misdiagnosed as a camera-offset problem

**Symptom (Berg's original report).** *"Out of focus / wrong zoom during the first third, on the ground during the second third, wrong offset during the last third."*
**Wrong hypothesis.** That the cutscene camera needed `pos` / `rot` offsets, i.e. work in `demo_cam.py`.
**Real cause.** A cutscene camera is a **baked path**. Playing it against a model roughly 9% off the size it was authored for produces a framing error that is **proportional to camera distance** — severe in a close-up, mild in a wide. A `pos`/`rot` offset shifts the shot by a **fixed** amount, so correcting the close-up necessarily wrecks the wide.
**Fix.** Correct the form's scale.

> **Rule: a framing error that CHANGES across a cutscene is a SCALE mismatch, not an offset one. Check the form's scale before touching `demo_cam.py`.**

**Scale and donor choice must be decided together.** Getting `scaleB = 1.0` right is precisely what makes en028's own maxout cutscene frame correctly once it has been retargeted onto pl005 — the two fixes only work as a pair. Pick the donor whose row you are matching, then set that form's scale to that donor's value.

### 6.5 `CharaModelVisible.fsv` has three file traps at once

1. It is `_cso_` ciphered with a **negative key (`-1251322551`)** — signed, arithmetic shift.
2. It uses **bare-LF endings** (136 LF against 1 CRLF), so splitting on `\r\n` yields one giant line.
3. The decoded payload is **not valid UTF-8** — there is a `0xCC` byte in the trailing footer row, line 137, which is also legitimately ragged. A decode/re-encode round-trip destroys it. This is the same failure class as the `WepVisible.fsv` shredding in Section 7.

**Therefore: edit the decoded bytes in place and re-encipher. Never re-serialise.** `set_model_scale.py` pads the replacement to the old field width where it can, and reports when a row length changes — which is safe, since the CSV is not fixed-width.

Note that hitboxes are world-unit `coll_radius` values and do **not** scale with the model.

---

## 7. The weapon / accessory bug

### 7.1 Solved (2026-07-26)

**Symptom.** In the Zangetsu + Hiyori build, a large set of characters lost weapons and accessories: **Shikai Ichigo pl000, Halibel pl035, Nnoitora pl037 and Yhwach pl052 swung empty-handed**, and **Tosen pl025 lost his mask/glasses**. Kenpachi pl027 was fine. pl005 and pl009 themselves looked normal, which is why the ports were not initially suspected.

**Real cause.** The build shipped a corrupted `Script/WepVisible.fsv`. Whatever tool added the pl005/pl009 rows re-saved the file with **bare-LF line endings** and, worse, **injected a newline inside the multi-byte character 態** — UTF-8 `E6 85 8B`, where the trigger is its third byte **`0x8B`**. Every row is cut at that point, so all weapon slots defined after the first `通常状態` / `覚醒状態` value are lost. **164 malformed rows, 44 characters affected.**

The damage pattern follows directly from the gating values:

- Weapon slot 0 gated by `通常状態` → the row dies before the weapon is defined ⇒ pl000, pl035, pl037, pl052 empty-handed.
- Tosen pl025: slot 0 is `常に`, which survives, but slot 1 onward (`通常状態` = mask/glasses) is cut ⇒ accessories missing.
- Characters using only `常に` are untouched ⇒ pl027 fine, and pl005/pl009's own rows survived (both `常に`), which is exactly why the ports themselves looked correct.

**Fix.** `WepVisible.fsv` was rebuilt as the community patch's correct file (**CRLF, 136 rows × 73 columns**) plus the pl005/pl009 rows lifted intact from the broken file (`sp000_wep00/01`, `en013_wep00/01/02`). Written and verified in three places:

- live `Script/WepVisible.fsv`
- `Patch_Dev_Environment/GameVersions/Bleach Rebirth of Souls Community Patch + Zangetsu + Hiyori/Script/WepVisible.fsv`
- the backup snapshot `_BACKUP_Zangetsu_Working_2026-07-26/`

Old copies kept as `*.prewepfix_bak`.

### 7.2 How it was found

Berg bisected by folder: **Motion ✓, Overlay ✓, Script ✗** (bug returns). Diffing the Zangetsu build's `Script` tree against the community patch's showed 14 replaced tables. A structural sweep counting columns per row then found **`WepVisible` was the only file with malformed rows** — every other table had correct column counts.

### 7.3 Sweep results across both Script trees

Only `WepVisible` had short rows. `CharaActCmbHead`, `CharaHitColl`, `CharaLockon`, `CharaModelVisible`, `CharaNameTextID`, `CharaStatus` (both stock and modded), `parry_bind_hit_effect` and `WepBind` all carry **bare-LF endings but intact content** — the game tolerates LF, so **leave them alone**.

Two false positives worth recording so nobody re-flags them: `additional_status_effect.fsv` is **legitimately ragged**, and `cos_pl005.fsv` has a **binary 16-byte footer on the terminator row by design**.

Also noted: the Zangetsu+Hiyori build drops the **pl053** row from `CharaHitColl` and `CharaLockon`. Harmless so far — pl053 is the old Zangetsu-base slot.

### 7.4 Rule for all future `.fsv` edits

**Never let a toolkit or CSV round-trip re-save an `.fsv` containing 態.** After *any* tool touches an `.fsv`, verify three things: (a) every row has the header's column count; (b) `t.count(b'\n') == t.count(b'\r\n')`, i.e. no bare LF; (c) the decoded payload is valid UTF-8. Our own edits stay safe because we patch the decoded bytes in place and re-encipher, with no text-mode round-trip.

> **`_cso_` files re-encrypt with a RANDOM key on every save**, so identical content produces different file bytes. **Always compare DECODED payloads, never file hashes.**

---

## 8. Icons, banners and portrait art

### 8.1 The asset map

Confirmed by decoding pl005's set and matching Berg's screenshots. This map applies to any added character.

| file | size (00HIGH / 01MIDDLE) | what it actually is |
|---|---|---|
| `ui/swap/icon/lobby_plNNN.cat` | 452×724 | room-match **portrait card** (the big one mid-screen) |
| `ui/swap/icon/icon_plNNN.cat` | 384×460 / 192×232 | character **emblem** (Zangetsu's is a hollow mask) |
| `ui/swap/icon/pic_plNNN.cat` | 512×136 / 256×68 | **header banner**, face close-up (also the in-battle top banner) |
| `ui/swap/battle_setup_chara/chara_mono_plNNN.lds` | 848×424 / 424×212 | **room member-row face icon** — high-contrast MONOCHROME face in the right ~60% |
| `ui/swap/battle_setting_chara/battle_setting_plNNN.lds` | 2264×2496 / 1132×1248 | room-match **splash art** |
| `ui/swap/spirit_chara_icon/plNNN_pic0/1.lds` | 1132×212 / 568×104 | **in-battle HUD name banner** (top-left/right of the fight screen) — stylised MONOCHROME glitch-art, *not* a colour portrait |
| `ui/swap/chara_icon.cat` sections | 200×148 ×3 | select-**grid** icon (`char_1p_NN`, `char_2p_NN`, `mono_char_NN`) |

**Every one of these uses real alpha** — the character is cut out and the UI composites over black. Berg's instruction that "the background should be black" means *ship alpha*, never flatten onto white.

### 8.2 `.cat` container format

```
PZZE 'cat' ->
  payload:
    256 B head      u32s: 1, 1, 0, offset=256, size, fmt=6, 2, ...
    528 B sub-header
    DDS             DX10 header, BC7_UNORM (dxgiFormat 98)
    92 B tail       after the main surface
```

`.lds` files are simpler: a **16-byte header followed by the DDS**.

### 8.3 Bug: the `.cat` identity trap

**Symptom.** Hiyori's portrait kept showing Yhwach no matter what pixels were written.
**Wrong hypothesis.** That the encoding or the cutout was wrong, or that the wrong LOD was being loaded.
**Real cause.** **A `.cat` carries its own name INSIDE the payload, and the atlas binds on THAT name, not on the filename.** All three of Hiyori's `.cat` files (`lobby_`, `icon_`, `pic_pl009.cat`) internally identified as **`pl052`**, so no pixel edit could ever appear.
**Fix.** Replace `pl052` → `pl009` in `payload[:dds_offset]` **only**. Never blind-replace across the whole payload — the byte pattern can legitimately occur inside compressed pixel data.
**Verification.** Decompress, then `re.findall(rb'(?:lobby|icon|pic)_pl\d{3}', payload[:dds_off])`.

`chara_mono_plNNN.lds` and the `.lds` strips carry **no internal id** — filename is sufficient there. Detect a donor copy in those by md5 instead.

### 8.4 Two encoders, two eras

The notes contain what looks like a contradiction but is chronological. On **2026-07-26** (the Hiyori art pass) there was **no BC7 encoder available**, so art was encoded as **BC3/DXT5 via Pillow** and the DX10 header's `dxgiFormat` was flipped **98 (BC7) → 77 (BC3)**. This works because BC7 and BC3 are both 16 bytes per 4×4 block, so the payload length is unchanged and every section offset/size table stays valid.

On **2026-07-27** a **BC7 mode-6 encoder was written** (numpy, roughly 60 lines) and **validated lossless against the original banner at MSE 0.0** — which incidentally proved that **the game's own `pic` textures are BC7 mode-6**. The pl005 banner therefore ships as true BC7; Hiyori's earlier assets ship as the BC3 substitution.

**Recipe, either era:** decompress PZZE (or use RAW as-is) → find `DDS ` → read width/height from the header → render at those exact dimensions → encode → splice the blocks in place → fix `dxgiFormat` if substituting → re-wrap PZZE (recompress and update the uncompressed size at `+8`) or leave RAW if the original was RAW. Always back up (`*.preart_bak`).

### 8.5 The shipped Zangetsu "glitchy" battle banner

The requested art was identified as `Zangetsu Patch/Zangetsu Icon/Zangetsu_Room_Match_Icon.png` — red glitch streaks and torn black flames, 828×467, **no alpha, solid white background**.

Pipeline, built in-session and reusable:

1. **Border flood-fill white-key** (preserves interior whites, which a global threshold would eat).
2. Compose to 512×136 — crop `(45, 40, 614, 191)`, face right of centre, opaque black background, per the banner convention.
3. **BC7 mode-6 encode** (validated lossless as above).
4. Splice the DDS main surface, keeping the **148-byte header and 92-byte tail**.
5. Reassemble as `payload[:784] + new DDS`, then PZZE re-wrap.

**LIVE:** HIGH `6991bdd4`, MID `54185827`, with encode MSE 11.5 / 17.8 — clean. Backups `.preglitch_bak` on both LODs. Older art variants survive as the `pic` `.art_bak` / `.name_bak` chain plus the `zang_art` zips.

**Banner framing convention:** face at roughly 65% across the x axis, art bleeding across the full strip, black background.

> **`battle_setting_pl005.lds` is stored RAW (un-PZZE'd, 5.6 MB) while vanilla is PZZE'd.** It apparently loads that way, but wrap it if it is ever touched.

The UI texture pipeline is now general: **any `pic`/`icon`/`lobby` `.cat` and any `.lds` can be viewed and replaced.** `texture2ddecoder` decodes; the mode-6 encoder writes.

### 8.6 Bug: an installer built by directory walk reverted the grid icon

**Symptom.** A packaged installer would have reverted the select-grid icon to an older state.
**Cause.** The installer was built by **walking the staged upload tree**, which accumulates files across sessions; it swept in an *older* `chara_icon.cat`.
**Fix.** **Always package from an explicit whitelist of the files actually modified**, never from a directory walk of the staging area.

### 8.7 Bug: overwriting art the porter had already authored

**Symptom.** A replacement HUD banner looked clearly worse than what shipped in the port.
**Cause.** Berg's pl009 port already contained a **proper Hiyori spirit strip** — the monochrome glitch-art HUD banner matching the game's own style — and it was replaced with a colour face crop from his reference image.
**Fix.** Reverted 2026-07-26 from `*.preart_bak`, both LODs.
**Prevention — the cheap test:** md5 the port's asset against the donor's (`pl052`). **Identical ⇒ placeholder donor art, safe to replace. Different ⇒ the porter authored it, leave it alone.** On that port: `pic_pl009.cat == pic_pl052.cat` (donor, replaced), `chara_mono_pl009.lds == chara_mono_pl052.lds` (donor, replaced), but `pl009_pic0/1.lds` differed — **her own art, kept**.

### 8.8 Cutout pipeline (source image → alpha)

Flatten onto white → near-white threshold → `scipy.ndimage.label` → treat components touching the border as background → keep the largest remaining component → `binary_fill_holes` → slight gaussian feather. **Threshold 120 was required** for Berg's Hiyori source to absorb light-grey bedsheet folds; a tighter threshold leaves fabric streaks. Interior white (her shirt) survives because the fill is border-seeded. The bright pink/white bloom on her chest is genuine source art, not an artifact.

For `chara_mono`: greyscale → normalise over the opaque region → `clip((g-118)*3.4+128)` → near two-tone, preserving the cutout alpha → composite into the right ~60% of the canvas.

---

## 9. Hiyori (pl009) — the same pipeline, second slot

Secondary to Zangetsu, but she shares every system above, and her crash work produced the general rule for member relocation.

### 9.1 Result

40 cells = 37 base + pl005 Zangetsu (cell 37) + pl009 Hiyori (cell 38) + random (cell 39, pushed back). `CharaSelect.bin` S1/S3 hold 39 entries with the tail `…pl052, pl005, pl009`. Deployed 2026-07-26 on exe `c360f4b98c9dd8fd5228a81cbc16426d` with the complete 48-site relocation and the full art set. Offline, Room Match and Ranked were all confirmed working by Berg. (That md5 was later superseded by the move-names patch — see §1.4.)

### 9.2 Crash 1 — RVA `0x9546c`

**Symptom.** `0xC0000005` at `0x140095410 +0x5c`, on `lock xadd [rcx+0xc],-1`. It looked online-only at first, then intermittent, then moved to select-screen re-entry.
**Wrong hypotheses tried and kept but not causal.** (a) A **clone addref on the wrong field** (`+8` vs `+0xc`) — genuinely unbalanced and fixed by addref'ing **both**, but not the crash. (b) **De-whitelisting Hiyori online** — it only avoided the heap churn that exposed the real bug; reverted.
**How it was actually settled.** The VEH crash reporter caught `Rcx = 0x203a22656d616e5f`, which is ASCII **`_name": `** — a `.cat` JSON fragment sitting in freed heap. So the "control block" was never a pointer; the code was reading **out of bounds**. The stack chain (log tag 33) put the immediate caller at RVA `0x2565d8`, inside grid builder `0x140255b10`.
**Real cause.** **The relocated struct is 0x50 BYTES, not 0x48.** The constructor's initialiser run gives the true layout: `[0xD98, 0xDE0)` = 0x48 (9 qwords), **`[0xDE0, 0xE30)` = 0x50** (2 dwords + 9 qwords), `[0xE30, 0xE80)` = 0x50. A *cell* is 0x48, so cell 39's range covers only *part* of that struct. Relocating just `[0xDE0, 0xE28)` split it, with two consequences: (a) the ctor init of the last field, `mov [rsi+0xE28],rbp`, still wrote the **OLD** address, so the relocated `+0x48` qword was never initialised; (b) `lea rbx,[rdi+0xDE8]` yields `0x1980`, which is passed to a helper that writes `dest+0x00..0x40` — up to `0x19C8`, past the `0x19C0`-byte object. **An 8-byte heap overflow on every grid build.** Whether it faulted depended on heap churn, which explains the shifting symptom.

### 9.3 Crash 2 — RVA `0x25c8c2`

**Symptom.** A second `0xC0000005` after the first fix.
**Real cause.** `0x14025c8a0` is a **12th grid function**, absent from the inherited "11 grid functions" list. It executes `mov rax,[rcx+0xE28]; test rax,rax; jne; cmp [rax+8],0` **at the OLD address**, which after relocation is vacated and uninitialised, so it dereferences garbage.

### 9.4 The fix — 48 relocation sites

Relocate the **whole span**. Struct A `[0xD98, 0xDE0)` → `[0x1930, 0x1978)` and struct B `[0xDE0, 0xE30)` → `[0x1978, 0x19C8)`; **both shift by `+0xB98`**, so treat them as ONE range `[0xD98, 0xE30)`. The object was grown `0x1978` → **`0x1A00`** (allocation at `0x14026382b`, sized delete at `0x14026465a`).

Newly added beyond the original list: the three `0xE28` sites (`0x14025cdeb`, `0x14026408f`, `0x14026476d`); four whole functions `0x14025c8a0`, `0x14025ca20`, `0x14025e050`, `0x14025e300` (the last two are cursor prev/next, indexing `[rdi+rsi*4+0xDE0]`); **and three sites that `memberE` itself missed** — `0x14025c337`, `0x14025c461`, `0x14025c58f` (`lea rsi,[rdi+0xD98]` inside function `0x14025c170`), which handed out a pointer to struct A's vacated address = **cell 38, Hiyori's own cell**. That last one was a **latent corruption in the 39-cell Zangetsu builds too**.

**Completeness guard, kept in the builder:** never trust a hand-maintained function list. Sweep every function in the select cluster `0x140250000–0x140270000` (boundaries taken from `int3` padding), disassemble each, and **fail the build** if any access with a displacement inside the struct span and a base other than `rsp`/`rbp`/`rip` is not in the patch set. It currently reports "12 functions touch the struct, all relocated." A raw whole-`.text` byte scan is useless here — hundreds of `rbp` stack frames collide with these displacements — and byte-scan hits are often reported one byte late because of the REX prefix; always cross-check by disassembling.

**The general rule:** derive a member block's TRUE extent from the **constructor's initialiser run**, never assume it equals a cell's 0x48, and size the object for the whole struct, because a `lea` of its base gets passed to helpers touching `base+0x00..0x40`.

*Meta-lesson recorded in the notes: three plausible theories all survived static reasoning and all were wrong; one VEH run settled it. When static analysis stops converging, instrument.*

### 9.5 Ruled out — do not re-litigate

Hiyori's spirit portraits (structurally perfect — and note that **pl005's `01MIDDLE` is malformed and he works fine**, so malformed portraits are not a crash source); missing per-character files; the three `IsPlayableCharacter` matchmaking callers (they only set an "invalid character" flag at `[rbx+0x68d]`); and `SRankMatch` vs `SRoomMatch` call-graph differences.

### 9.6 Instrumentation (still in the build — strip for release)

A VEH crash reporter. `AddVectoredExceptionHandler` is not imported, so it is resolved at runtime via `GetModuleHandleA` (`0x1411b5630`) and `GetProcAddress` (`0x1411b5170`), registered once from the node-factory hook. It is not a debugger, so it is invisible to the anti-debug that defeats x64dbg and Cheat Engine. On `0xC0000005` it logs at most 4 times and then returns `EXCEPTION_CONTINUE_SEARCH`:

```
29  cookie
30  fault RVA, Rcx, Rbx
31  Rax, Rdx, Rdi
32  Rsi, R8, R9
34  Rbp, R12, R13
33  return RVA, stack slot   (up to 16 frames)
```

Scratch space: `VEH_INIT 0x1416c2050`, `VEH_CNT 0x1416c2058`. Log snapshots: `zang_pre_diag.log` (18112 bytes) and `zang_pre_boundsfix.log` (19136 bytes).

### 9.7 Art

Source: Berg's `character_hiyori_01.png`, 750×1400. The `.cat` identity trap (§8.3) was the real reason her portrait stayed Yhwach, and it cost a whole round.

Shipped for pl009 as of 2026-07-26: grid icon, lobby card, emblem, header banner, splash (**character at 60% after Berg asked for −40%**), and the `chara_mono` room-row face. **The HUD banner is her port's original art, restored after the replacement was rejected.** The S3 movelist was cleared. 12 files patched, backups `*.preart_bak`. All of this is mirrored into the launcher version — **re-run the assembler after any art change**.

### 9.8 `CharaSelect.bin` S3 = the movelist / Kikon text

64-byte records: a 32-byte id followed by a 32-byte payload. **Hiyori's payload was byte-identical to Rukia's (pl010)**, which is exactly why the select screen listed "Somenomai. Tsukishiro." Zangetsu's is all zeros, so no move text is shown.

**Zero the 32-byte payload for any added character** unless you have real Kikon ids. A ported package will silently carry the donor's.

### 9.9 Select-screen model framing — the 12 floats at S1 `+88..+132`

This is the **only** per-character select data that exists. `CameraDistRate.fsv` is uniform for every character; `CameraParam.fsv` has a single `pl000` row; `CharaModelVisible.fsv` carries only cos/face/hair/spare and `scaleA` — which is the true character size used in battle as well (pl026 0.727, pl010 0.923, pl009 0.858, pl005 1.136 at the time of writing), **so do not abuse it for framing**.

The block is four float triplets. T2 and T4 are near-constant across characters; T1 and T3 are per-character and **unit-length for almost everyone** (pl016 Yamamoto is the outlier at |v| > 1), which suggests they encode **directions rather than positions**.

**Sequence of attempts.** Hiyori's floats were cloned from **Rukia**; they were replaced with **Hitsugaya's (pl026, the shortest playable)** plus **+0.14 on the y components at `+92` and `+116`**. That produced **no visible change**. The y components were then pushed to **0.55** with each triplet renormalised to stay unit-length. Backups: `CharaSelect.bin.premodelpos_bak`, then `.pretune_bak`.

**STILL UNVERIFIED.** `tune_hiyori_model.py <gamedir> [show | y <v> | copy <plNNN> | revert]` was shipped so the value can be dialled in live. If `+y` moves her the wrong way, try negative.

**If this turns out not to be the lever at all,** the next suspect is `Motion/Menu/menu_plNNN.tactpkg`: Zangetsu's was **cloned from a playable (pl052)** and frames correctly, whereas Hiyori kept her own story-character menu motion, which may place the model much closer to the camera. Note the tension with §2.4 — `menu_pl005.tactpkg` was found *unregistered* in the htable a day after this was written, so "Zangetsu's frames correctly" was observed while his menu package was not registered. The notes do not reconcile this; re-observe before building on it.

### 9.10 Install and revert

Self-contained installers live in the game root and run as `python3 <script> <gamedir>`: `hiyori_install.py` (data + Fnames + exe), `hiyori_icons_install.py` (grid icon), `hiyori_art_install.py` (12 UI assets), `hiyori_reloc_complete.py` (current exe). Each rebuilds the exe from `.pre_gridpatch_bak` with md5 guards. The 28 MB exe exceeds the 20 MB commit cap, so **recipe-on-device is the delivery path**. Backups: `*.prehiyori_bak`, `*.preart_bak`, `CharaSelect.bin.premodelpos_bak`. Builder: `/root/work/build_hiyori40.py` plus `/root/bros/caveasm.py`.

---

## 10. Crash and defect triage table

| symptom | real cause | fix |
|---|---|---|
| `0xc0000005` on costume load | costume row names an unregistered model | register the model (`register_costume_models.py`) |
| crash at `exe+0x982788` (1.3.0), mesh resolves but texture null | missing `(base, .gnf, base_tex)` manifest triple | emit **both** `_mdl` and `_tex` triples, 4 htable keys per form, translated paths only |
| two costumes look identical | every cell blank on both rows ⇒ both resolve to `sp000_cos00_00` | name only what differs; `null` removes a weapon slot |
| texture/model edits to `plNNN_*` have no effect | `CharaModelVisible.fsv` / `WepVisible.fsv` still name the donor stems (`sp000_*`, `en013_*`) | repoint the stems (register `pl005_*` first) or edit the donor files |
| visor missing on select screen only | **open** — suspected id-based lookup of `pl005_wep01_00_00`, which is unregistered | test Hiyori's weapon on select; re-check after `menu_pl005.tactpkg` registration |
| weapons/accessories missing on 44 characters | `WepVisible.fsv` re-saved with a newline injected inside 態 (`E6 85 8B`, trigger byte `0x8B`) — 164 malformed rows | rebuild from the community patch file (CRLF, 136×73) + lift the pl005/pl009 rows |
| evo/rev models too large | `scaleA/B/C` set to 1.13 for all three forms | copy each **donor's own** scale: 1.13 / 1.0 / 1.047 |
| cutscene framing wrong, and wrong *differently* in each third | model scale mismatch against a baked camera path | fix the form's scale; offsets cannot correct a distance-proportional error |
| portrait shows the donor no matter what pixels are written | the `.cat` payload's internal id is `pl052`; the atlas binds on it | replace `pl052`→`pl009` in `payload[:dds_offset]` only |
| select screen shows the donor's Kikon moves | S3 32-byte payload carried over byte-identical from the donor | zero the payload |
| move name reads "Spiritual Pressure Move N" | no row in the map for that slot key | add a `ROWS` entry, re-run `move_names_own_entry.py` |
| all UI text broken | malformed appended `CommonText.cat` record | `--revert` |
| select voice silent | **open** — chain is correct; suspected wrong bank, or bus/state routing, or no per-character bank on the select screen | event written to `sp000.bnk` as well; `menu_pl005.tactpkg` registered; untested |
| installer reverts an already-shipped asset | packaged by walking the staging tree, which accumulates old files | package from an explicit whitelist |
| replacement art looks worse than the port's | the porter had authored real art for that slot | md5 against the donor's file before replacing; revert from `*.preart_bak` |
| `.fsv` file hashes differ with no content change | `_cso_` re-encrypts with a random key each save | compare **decoded payloads**, never file hashes |
| re-running an old script drops unrelated registrations | `fnames_patch.py` / `fix_attacks.py` rebuild from hardcoded lists | patch the **current** tables incrementally |agentId: a450dc569d704b287 (use SendMessage with to: 'a450dc569d704b287', summary: '<5-10 word recap>' to continue this agent)
<usage>subagent_tokens: 87060
tool_uses: 15
duration_ms: 500786</usage>


---

## Part 3 — The moveset

### The three-file architecture

A character's fighting behaviour is spread across three packages. Nothing about an attack lives in one place: the graph decides *when* a move is legal, the tuning decides *what it does*, and the action package decides *what plays*.

| File | Path | Contents | Keys on |
|---|---|---|---|
| `.tcmbpkg` | `Script/Action/plNNN.tcmbpkg` | The combo graph — nodes, inputs, routes, per-route variables | `_uniqueID` (per-file), node **name** for by-name entry |
| `.tadjpkg` | `Script/Action/plNNN.tadjpkg` | Per-action tuning — hitboxes, damage, effects, voice, cancel and combo windows, warps | the blob's internal **node name** |
| `.tactpkg` | `Motion/plNNN.tactpkg` | `act_data` (rig-target → clip map), the nested clip archive, and `motblend_file` | the blob's internal **JSON key** (`category\motion`) |

Note the split: the action package is under `Motion/`, not `Script/Action/`. Two of the three files sit in one directory and the third does not, which is a recurring source of wrong paths in tooling.

`.tactpkg`, `.tadjpkg` and the archives nested inside them share one flat container format, cracked and round-trip byte-exact in `Zangetsu Patch/actpkg.py`:

```
0x00   magic, NUL-padded to 0x1C   actmng_pkg | actadj_pkg | acttmo_pkg |
                                   acttmv_pkg | actmtl_pkg | motblend_file
0x1C   u32 hash                    opaque; carry it through unchanged
0x20   u32 count N
0x24   N × 0x48                    { name[0x40], u32 offset, u32 size }
...    blobs, contiguous
```

Every stored blob size is a multiple of 16. A top-level file is *not* padded; an archive embedded as a blob *is*. `.tactpkg` is PZZE + zlib; `.tadjpkg` is raw. `actpkg.Pkg.build()` recomputes every offset, so blob lengths may change freely — but appending a new entry to a `.tactpkg` must respect that the nested motion archive stays last, whereas a `.tadjpkg` has no such constraint and appending is unconditionally safe.

Inside the `.tactpkg`, each `act_data` blob is JSON mapping a rig target to `tmo_name` / `tmv_name` / `mtl_name` / `cmp_*`. **`tmo_name` is fully qualified** (`pl052_sp_walk_f`), which is the single fact that makes transplants cheap: clips carry their donor's name and resolve to whatever package they are sitting in, so nothing needs renaming when they move. A `tmo_name` that does not correspond to a clip is a *blend-set* name, defined in `motblend_file` — a plain CSV under the key `_csv0` (not `_cso_`), with columns `accessN, motion_name, tmo_file0..4, blend_rateX/Y, frame_start/end`.

Consequently a locomotion transplant needs **four** things, and three is not enough: the `act_data` entry, the `BLEND_*` act, the `motblend` row, and that row's clips.

`act_data` holds **no routing whatsoever** — it is purely a rig→clip map. Every question of "what comes next" is answered by the tadj and the tcmb.

#### Resolution at runtime

```
input / prior action
   ↓  (tcmb: node's input_text + ComboStart window + variables)
combo node  ──────────── matched by NODE NAME ────────────▶  .tadjpkg blob
                                                                 ↓  MOTION NAME
                                        .tactpkg blob whose inner JSON key is
                                        "<category>\<MOTION NAME>"
                                                                 ↓  per rig target
                                        tmo_name → clip in the nested acttmo_pkg
                                                   (or a blend set in motblend_file)
```

Two independent name lookups, neither of which is the archive entry name.

---

### ★ Action identity: an archive entry's name is not what the engine binds on

This is the most important rule in the project. Both packages are archives of *named blobs*, and **the archive entry name is decoration**. Each blob carries its own identity inside its payload:

```
.tadjpkg blob   'adjb' + <category>\0 + <NODE NAME>\0 + <MOTION NAME>\0 + <the rest>
.tactpkg blob   {"kind":"act_data", "<category>\<MOTION NAME>": { ... }}
```

* The combo node is matched against the tadj blob's **node name**.
* The motion is resolved by the tadj blob's **motion name** against the tact blob's **inner JSON key**.

⇒ **Building a move by copying one and renaming the archive entry renames nothing the engine sees.** The result is a dead node: no crash, no log entry, the string simply stops one hit early. Every tool that lists package contents lists the *names*, so the file looks perfectly correct.

Our own `sp1_v7_twins.py` survived this trap only because its `rehead()` rewrites the blob header's node name rather than the entry name — right by construction rather than by understanding, until the rule was found on 2026-08-09 while debugging another dev's pl015 (Yumichika) build.

#### The pl015 case, as the canonical pattern

`atk_lo03_d01` and `atk_lo03_u01` had been copied from `atk_lo01_d01` / `_u01` with only the entry names changed:

```
ARCHIVE ENTRY                        NODE NAME       MOTION NAME
1_normal_attack_atk_lo03_d01         atk_lo01_d01    atk_lo01_d01
1_normal_attack_atk_lo03_u01         atk_lo01_u01    1_normal\attack\atk_lo01_u01
(tact) both                          inner key       ...\atk_lo01_[du]01
```

Those two are the enders of two *different* strings — `sp_step_atk02 → them` and `atk_lo02 → them` — so the step string and the light string both ran and both stopped dead one hit early. Fixed with four length-preserving `lo01 → lo03` edits. The `se_name*` strings were deliberately left alone: those are sound-effect asset names, not identity.

#### The audit

`Zangetsu Patch/Other devs work/pl015_stepchain_fix.py --check plNNN` reports every `attack` / `move` entry whose inner identity disagrees with its own entry name. It returns **0 mismatches on pl000, pl020, pl032 and stock pl015** — shipped data is always self-consistent, so any hit is the modder's own.

⚠ A regex detail that cost a round: the tact inner key contains **one** literal backslash (`1_normal\attack\atk_lo03_d01`). In a raw Python string that is `\\`, not `\\\\`.

#### The entry-name convention

The tadj entry name is `category` with `\` → `_`, plus `_`, plus the node name:

```
1_normal\attack  +  atk_lo01       →  1_normal_attack_atk_lo01
2_evo\attack     +  evo_atk_lo01   →  2_evo_attack_evo_atk_lo01
```

⚠ The evo form's **tcmb node is named `atk_lo01` but its tadj node is `evo_atk_lo01`** — the form prefix lives on the tadj side only. This asymmetry is invisible unless you look inside both files.

#### ★★ Twins: a variant action needs no tact entry and no combo node

Measured on pl005 on 2026-08-10 while building the enhanced SP2 ender. Four facts, each checked against shipped data:

1. **A twin shares its source's clip by keeping the MOTION string and changing only the NODE string.** Because the clip resolves through `cat + '\' + motion`, a twin resolves to its source's tact entry and needs none of its own. Proof: **111 of pl005's 241 tadj actions have no tactpkg entry at all** — every `_a` twin (`atk_hi01_a`, `atk_lo01_d_a`, …), every `_act`, every `_snd`. `atk_hi01_a` is node `atk_hi01_a` with motion `1_normal\attack\atk_hi01`, and no tact entry exists for it. Renaming the motion as well is precisely the silent-dead-action failure: it sends the engine looking for a tact key that does not exist.
2. **The motion string is sometimes a full path and sometimes bare** — `1_normal\attack\atk_gr01` vs `sp_atk02_2`. Bare means "relative to my own category". Never rewrite it; copy it verbatim.
3. **A `my_action` latch target needs no tcmb node** — 73 of the game's 78 latch targets have none.
4. **`my_action` is the only field in the entire tadj that names another action.** Scanning every field of every block of all 241 pl005 blobs for a value matching a node name returns `my_action` and nothing else. "Who can reach this action?" is therefore answerable exhaustively and cheaply: grep `my_action` across the tadj, plus the node names in the tcmb, and that is the complete set. Running that check on pl005 proved `sp_atk02_1b` frame 9 is the *sole* route into `sp_atk02_2`, which is what made a caller-side fork safe. `my_action` may be bare (`sp_atk02_2`, resolved in the caller's own category) or a full `cat\node` path (pl020 uses `1_normal\attack\sp_atk02_1`); bare is the norm.

#### ★★ The `b` suffix: a continuation the engine derives, with no data behind it

pl005's SP2 runs `sp_atk02` →(latch)→ `sp_atk02_1` →**?**→ `sp_atk02_1b` →(latch)→ `sp_atk02_2` →**?**→ `sp_atk02_2b`. The two `?` steps have **no reference of any kind**: no `my_action`, no tcmb node, no act_data routing (act_data holds none). Both work in game. By elimination, the engine appends `b` to the node name when an action plays out.

Neither `_1b` nor `_2b` exists in vanilla pl005 or in the donor pl052 (which ships `sp_atk02`, `_1`, `_2`, `_3`) — we invented both and both work, so the derivation is engine-side and general.

⇒ **When you clone an action X that has an Xb, clone Xb too.** `sp_atk02_2a` alone sends the engine looking for `sp_atk02_2ab`. `sp_atk02_2b` is the *out* — `OffReverse`, `RotateSpeed`, `SlowMotionRate`, `CancelTiming` f4, `ComboStart` f4 — the block set that returns control to the player. Losing it on whiff is not cosmetic. The twin costs 7 blocks / ~6 KB and is inert if the derivation later turns out to be something else.

⚠ *Flagged as thin:* the `b` derivation is established by elimination, not by disassembly. It is load-bearing for the SP2 work and should be confirmed against the exe before it is relied on for anything new.

#### The clone recipe (used twice: pl005 `sp_break01_maxout`, pl050 `atk_lo0N_1`)

Copy the blob; rewrite **only** the node string in the head (`\0old\0` → `\0new\0`); `build_padded`; insert next to the original. **Leave the motion string alone** — it still points at the original `act_data`, so there is no `.tactpkg` work at all and animation, hitbox, damage and timing are identical by construction. Verified block-for-block byte-identical. No `filename.bin` or htable work is needed, because no new file is created.

---

### The `.tadjpkg` block format

Blob head, then a block list:

```
'adjb'
<category>\0
<NODE NAME>\0
<MOTION NAME>\0
f32 -1.0 ; u32 0xFFFFFFFF ; u32 0 ; f32 1.0 ; u8 ; u32 block_count
```

Each block:

```
u32   per-instance id     NOT a name hash — differs per action, so a verbatim copy stays valid
name\0                    "Attack_Melee", "ComboStart", "Effect_OneShot", …
str_a\0                   usually empty; a boolean gate expression when present
f32 × 3                   (unused, frame_start, frame_end)
memo\0        ★           a NUL-terminated LABEL — "01HIT目", "02HIT目", "head", "ankle_R"
u32   field_count
field_count × (key\0, value\0)
```

Nothing inside a blob stores an offset into it, so appending blocks and lengthening or shortening value strings are all safe; re-pad the blob to 16 afterwards.

Block types observed: `Attack_Melee`, `Attack_Bullet`, `SE_OneShot`, `SE_Loop`, `Voice`, `Effect_OneShot`, `Effect_Loop`, `ComboStart`, `CancelTiming`, `Afterimage`, `Protect`, `HeightHoming`, `OffReverse`, `MotionMoveRate`, `PointLight`, `WorldSpeedChange`, `Warp`, `SoulRebootTiming`, `SlowMotionRate`, `RotateSpeed`, `AddUniqueVal`, `PointWind`, `WeakPoint` (boss-only).

#### `str_a` is a boolean expression, read by the generic dispatcher

`str_a` is evaluated by the block dispatcher, not per block type — the same string vocabulary appears on `Warp` (70 uses), `Effect_OneShot` (66), `Afterimage` (50), `MotionMoveRate` (12), `Attack_Bullet` (10) and six more types.

`Attack_Melee` is gated only **6 times in 855** across the first eight playables, so its absence from any single character proves nothing. One of those six is a same-action, same-frame, mutually exclusive pair, which is the shipped idiom for a conditional hit:

```
pl001  1_normal_attack_atk_hi02   Attack_Melee f43  ENHANCED=0
pl001  1_normal_attack_atk_hi02   Attack_Melee f43  ENHANCED>0
```

Duplicate the block, gate the pair, change one field on the copy.

⚠ The block `id` is a large opaque u32, not an index, and **28 of pl005's 241 blobs already contain duplicate ids** — the engine plainly does not key on it. Give a duplicated block a fresh id anyway: unique is safe whether or not the engine dedupes; identical is only safe if it doesn't.

#### `tadj_lib.py` supersedes the `dash_fix.py` walker

`Zangetsu Patch/tadj_lib.py` exposes `parse` / `build` (byte-exact, preserving trailing padding junk) / `build_padded` (for length-changing edits: drops junk, re-pads to 16) / `blocks_named` / `field` / `set_field`. Validation across every `pl*.tadjpkg` plus `plcom.tadjpkg`: **8149 / 8173 blobs parse and rebuild byte-exact.** The only 24 failures are in `pl029_minion00.tadjpkg`, which has a different header, is not a playable, and was not chased.

Multi-hit attacks became editable per hit — damage, guarantee, blur and hitstun independently on hit 1 versus hit 3 — which is what turned the light-string damage standardisation into a mechanical job instead of a hex edit.

---

### The combo graph (`.tcmbpkg`)

JSON5-ish text. **Decode as cp932 *before* parsing**: SJIS trail bytes are frequently `0x5C`, which a UTF-8 or Latin-1 read turns into spurious backslash escapes. ⚠ A *strict* cp932 decode fails mid-file on **every** character including pl000 — this is pre-existing in shipped data, so use `errors='replace'`.

A file header carries `version`, `max_next_id` and `max_variables`; pl015 and the pl030 boss graph it replaced both read `version 103 / max_next_id 4 / max_variables 22`.

A node carries:

| Field | Meaning |
|---|---|
| `_uniqueID` | The engine's key. **Per-file, not global.** |
| `input_text` | What triggers it — `Pad_R1`, `Pad_R_Left`, `Pad_R_Down`, `AutoCombo`, `RecvEvent` |
| `nexts` | Routes out. **Key omitted entirely = terminal.** |
| `access_text` | Access/group label |
| `variables` | 22 for pl005 and pl020, 23 for pl052 — **remap by NAME, never by index** |

Variables that carry weight:

* `is_before_hit` — 1 means the route is allowed before the hit lands, i.e. on whiff.
* `hit_combo_stop` / `guard_combo_stop` — the route survives a hit / a block. **These gate *entry into the node they sit on*.**
* `sp_over_atk_short_cut`, `atk_syunpo_short_cut` — the *source* node offers that shortcut.
* `charge_rate` — 1.0 is a full-charge gate.
* `act_frame_min` / `act_frame_max` — 発動に有効なアクションフレーム範囲, a hard input-acceptance window.
* `reiryoku_cost` — 50 = Signature 1, 100 = Signature 2. **Read-only** (see the Ichibei rule below).
* `clash_parry_type` — 1 / 2 mark grab-clash nodes.
* `combo_route_id` — non-zero on **6 nodes roster-wide, all on ported slots** (pl005, pl009, pl015, pl030). Donor residue, not design. Do not read meaning into it.

#### ★★ Node names are not unique. Address by `_uniqueID`.

**pl005 ships 5 duplicated node names; pl000 fifteen; pl001 ten.** The engine keys on `_uniqueID` and the name is a label. pl005 has **two `atk_hi01` nodes, ids 9 and 85**. Only 85 is referenced by the graph (from `start_hi`, `atk_lo01_d`, `atk_lo01_u`). A name-based `re.search` finds id 9 first, so the first light-string build silently rewired the wrong node.

Other pl005 duplicates: `atk_hi03` 87/7 · `atk_gr02_1` 76/75 · `atk_gr01` 74/5 · `sp_break01_out` 56/89/90.

**`combo_patch.py`'s `node_blocks()` returns a dict, so it silently drops all but the last block of every duplicated name.** The same latent bug lives in any dict-keyed helper. `light_string.py` provides `node_spans()` — a list of `(name, uid, start, end)` — and that is the one to use.

#### ★★★ `ComboStart` and `AfterComboReset`, corrected

**A `ComboStart` window means "input is resolved against this node's `nexts`". `AfterComboReset` only decides whether taking that route resets the combo counter — it does not switch the lookup away from `nexts`.**

The proof is a population fact: **18 pl050 nodes carry `nexts` together with a `/1` window and no `/0` at all** — `atk_gr01` (75,75)→gr_chain, `atk_hi02_1` (54,92)→hi02_2, `sp_overatk01_d1` (40,84)→break_in, `sp_atk01_3` (100,149)→sp_atk01_4. **Outside every window, input falls through to the neutral machine** (`start_lo` → lo01).

| Window | Meaning |
|---|---|
| `ComboStart` with `AfterComboReset = 0` | chain / cancel — same combo continues |
| `ComboStart` with `AfterComboReset = 1` | link — combo counter resets, route still taken |
| no window at all | input falls through to neutral |

★ The corollary that solved the Ichibei job: **a node with an empty `nexts` and a one-frame `/1` point sends every follow-up input to neutral. That is a loop generator, not a terminator.**

This supersedes the looser reading recorded in the pl005 pass-14 notes. The symptom there ("lo03 swallowed a fresh lo01") was a **window with no matching route in `nexts`** — the input was captured and found nothing — not "the reset ate it."

#### Orphans: which ones are legitimate

Not every unreferenced node or dangling edge is a defect, and the project has burned time in both directions.

* **A dangling `nexts` is not automatically a bug.** pl052 ships one on its own break loop; pl001's ids 88/89/92/97 dangle too.
* **`sp_step_atk00` and `sp_step_atk01` have empty `nexts` in every shipped character** (pl000, pl020, pl032, pl005), and nothing points at `01` or `02` either. **The chain advances on the `AutoCombo` input, not through the combo graph.** Only `02`'s `nexts` matters, and even that is optional — pl020 has none. The first `HOHO_FOLLOWUP_GUIDE.md` instructed another dev to wire `00 → 01 → 02`; that was wrong, and both copies on Berg's disk have been revised.
* **`sp_overatk01_d` / `_u` with empty `nexts` is normal** (pl020, pl032). The over-attack graph is easy to second-guess and is usually already correct: `start_sp_break → sp_overatk01_d/_u`, and every attack or chain → `sp_overatk01_d1/_u1`. All four nodes share one motion, `sp_overatk01`.
* **An unreferenced node is not necessarily dead** — it may be entered *by name*. This is the mechanism behind the `jump_*` nodes and behind pl005's `atk_hi01` id 9, and it is why "nothing points at it" is not a licence to ignore it.
* **An orphan `AutoCombo` node is a real bug.** An `AutoCombo` node that nothing points at is *globally* eligible and fires off any `ComboStart` in the entire moveset. `sp2_v15_autocombo.py` added one and had to undo it.

---

### Building Zangetsu's moveset

#### v2 (applied 2026-07-25) — the first real transplant

`v2_build.py <gamedir>` rebuilds all three packages from backups; it is idempotent, supersedes v1, and supports `--revert`. **Order matters: `v2_build.py` first, then `grab_warp.py`** — `grab_warp` backs up to `.pregrab_bak` from whatever tadj is current, so re-running `v2_build` afterwards discards the grab edit.

* **tactpkg** — walk + `BLEND_blend_walk` + the blend row + 4 clips, and `sp_overatk01/02`, from **pl052**; `syunpo_out_just` and `ct_syunpo_out_just` from **pl020**.
* **tadjpkg** — only the 4 pl052 overatk entries (they carry the hitboxes; donor strings blanked), plus a `1_normal_attack_sp_break01_maxout` **cloned from his own `sp_break01_out`** with the motion field still pointing at his own animation. No walk tadj, no step tadj, no syunpo tadj.
* **tcmbpkg** — 4 overatk nodes plus `sp_break01_maxout` (`charge_rate` 1.0 → `sp_break01_1` → chain); `sp_break01_loop` → maxout; overatk offered from `atk_hi01`, `atk_hi02`, `atk_lo01_d01`, `atk_lo01_u01` with `sp_over_atk_short_cut` + `atk_syunpo_short_cut` + `hit_combo_stop` + `guard_combo_stop` set on each; `start_hi` → `atk_hi01`; `start_gr` cleaned.
* **grab** — pl003's `OffReverse` + `HeightHoming` pair (`HomingAngle` 90, `IsModelRotate` 1, `ModelRotate_Start/EndFrame` 180) appended verbatim to `1_normal_attack_atk_gr01`, taking it from 9 to 11 blocks.

⚠ **Count reconciliation, flagged:** the v2 notes record "tactpkg 77 actions / 67 clips", "tadjpkg 42" and "tcmbpkg 49 nodes", while the 2026-07-27 live measurement records **tact 87 acts / 90 clips, tcmb 42,764 B / 65 node blocks**, and the 2026-08-10 identity survey counts **241 tadj actions on pl005**. The tact figures reconcile (84 entries is *vanilla*, 87 is live-modded). The tadj figure 42 and the node count 49 → 65 do not reconcile with the work described. Treat each as a dated snapshot and re-measure before relying on any of them.

#### The KEY LESSON: transplant motion only

v1 injected the donor's walk *tadj* entry alongside the motion. The base walk stayed wrong while **evo looked perfect**. The cause: pl005 has no `2_evo` actions at all, so evo fell through to the injected `1_normal_move_walk` act_data with no tadj in the way, while base went through the donor tadj entry and did not. The tadj is also where donor SE, VFX and voice live.

**Rule: port `act_data` + clips (+ the blend row); never the donor's tadj — except for attacks, where the tadj carries the hitbox.** For attacks, strip `pl0NN_*` and `P0NN_*` strings so that only shared `COM_*` effects survive.

#### The light string (2026-07-27, `Zangetsu Patch/light_string.py`)

Built to Berg's spec; idempotent, `.prelight_bak` on all four files, `--dry` and `--revert`.

| node | id | motion | source |
|---|---|---|---|
| `atk_lo01` | **0** | `sp000_atk_lo01_d` | his own opener (previously `atk_lo01_u`) |
| `atk_lo02` | **1** | `pl012_atk_lo02` | **Rangiku** base lo02 |
| `atk_lo03` | **2** | `sp000_atk_lo01_u01` | his own ender, 14 warp-FX blocks kept |

Ids 0/1/2 were free — the exact holes the standard chain had been deleted from.

The lo02 donor went through two passes: pl016 Yamamoto first (it swung right, but Berg preferred Rangiku's). pl012's is the cleaner donor — 13 blocks, no gimmick, `ComboStart` 17–25 / cancel 43, damage already 450. It needs **both** clips, `pl012_atk_lo02` *and* `pl012_atk_lo02_wp00` (the weapon track; a missing weapon clip shows as an invisible sword mid-swing). Scrub: voice → `sp000_atk_lo_vo`, drop `pl012_ktn_lo`.

The earlier pl016 scrub is worth recording as the template: dropped the 2nd `Attack_Melee` (memo 豪炎, his flame hit), `AddUniqueVal` (which gates it), `PointWind`, `P016_com_fire`, and cue `pl016_atk_add_lo`; voice → `sp000_atk_lo_vo`. **Kept free:** Yamamoto's low already uses `COM_tm_AtkLow00` and `COM_tm_AtkDistortion` — the same two shared trails Zangetsu's own low uses. 18 → 13 blocks, zero donor strings remaining.

Routing was copied from **pl001** with pl005 ids: `start_lo→(6,0)` · `lo01→(79,70,32,1)` · `lo02→(79,70,32,2)` · `lo03→(79,32)` · `lo_chain(32)→(102,103)` overatk pair · `hi01(85)` and `da01(6)` both gained `+lo02`. Variables escalate as pl001 does: lo02 adds `hit_combo_stop`/`guard_combo_stop`; lo03 adds `atk_syunpo_short_cut`/`sp_over_atk_short_cut`. pl001's dangling 88/89/92/97 were dropped (they dangle there too — normal). The old `atk_lo01_d/_u/_d01/_u01` were left in place unreferenced, per Berg.

#### Hitbox geometry — range-matching a donor from a smaller character

The `Attack_Melee` fan is `coll_shape` 扇, `coll_radius` (reach), `coll_height`, `coll_pos`, `coll_angle`, `size_kind`.

Zangetsu's own normals: **1.80** lo01 / **2.00** lo03 / **2.50** hi01, all height 2.00, origin y 0.75 z 0, `size_kind` デフォルト. Donors use 小 / 極小 and smaller boxes. A mid-chain lo02 is normally the *widest* normal in a kit (pl000 2.80, pl016 2.50). Rangiku's is 2.20 × 1.50 pulled back to z −0.20 — generous on her, short on him. Forced to **radius 2.40, height 2.00, pos (0, 0.75, 0), デフォルト** via the `GEOMETRY` table in `light_string.py`, which is the one dial if it still under- or over-reaches.

#### Damage standardisation

Target: pl000 (Shikai Ichigo) minus 10%.

| move | before | after |
|---|---|---|
| lo01 | 350 | **315** |
| lo02 | 500 | **450** |
| lo03 | 500 | **450** |
| hi01 (pass 13) | 900 | **720** |
| hi02 (pass 13) | 700 / 800 | **560 / 640** |

`damage_guarantee` is 0 throughout (pl000's lo chain is 0; hi01/hi02 both 0 = no minimum). An earlier pass (`stepatk_damage.py`) set `sp_step_atk01` 900→450/225, `sp_step_atk02` 200→270/135 ×3, `lo03_d01` 500→540/270, `lo03_u01` 400→540/270.

**Still open:** pl000 runs these at `base_damage_rate` 1.0 where pl005 runs 0.7–0.8, so matched raw damage still will not total the same across a combo. `--match-rate` on `stepatk_damage.py` aligns it.

#### What to keep and what to take when swapping an animation

Established on the grab-confirm graft and correcting the lo02 instinct of keeping "properties" wholesale:

* **Keep the character's** — `damage`, `damage_guarantee`, soul/guard damage, `base_damage_rate`, and the whole `coll_*` box plus `size_kind`. Those are *balance*.
* **Take the donor's** — `fix_time`, `guard_fix_time`, `hit_stop_time`, `hit_shake_blur`, cancel and combo windows, effects. Those are *authored against the animation*.

Concretely: pl051's grab confirm recovers at frame **81** where pl005's did at 46. Pairing that recovery with Zangetsu's 30-frame hitstun would let the opponent act roughly 50 frames before he does — punishable off a **landed** grab. pl051's `fix_time` 60 is matched to its own recovery, so it came along.

#### Tuning passes 13–16

⚠ **Pass 14 onward patches the LIVE files, not backups.** Berg hand-tunes between passes: after pass 13 he changed lo02 `CancelTiming` 39→**45** and lo03 `SlowMotionRate` 1.2→**2.0**. `light_string.py` and `tune_pass13.py` both rebuild from their own backups and would discard that. Diff live-versus-backup before assuming what is present.

**Pass 13** (`tune_pass13.py`) — hi damage as tabled above; lo03 cancel 79→**63** (−20% recovery) plus `SoulRebootTiming (41,63)` **and a matching `ComboStart (41,63)/0`** (SRT alone does nothing — the `/0` window is what opens the by-name chain) plus `SlowMotionRate (0,63) = 1.2`, leaving its inherited `Warp@13 pos 0,0,−1` untouched; lo links −10% "snappier" — lo01 cancel 42→**38**, lo02 43→**39**, with each `/1` `ComboStart` tracking its cancel frame (lo03 excluded as the string ender); and the grab warp described below.

**Pass 15** (`tune_pass15.py`) — grab warp −2 → **−1** behind; `atk_gr01` `HomingAngle` 90 → **40**; `atk_lo03` `fix_time` (hitstun) 35 → **25**, because the shortened recovery from pass 13 had opened an infinite.

**Pass 16** (`tune_pass16.py`) — the warp/homing collision and the grab-whiff graft, both below.

#### ★★ The whiff-cancel leak — three layers, all required

Symptom: openers cancel into overatk or EX on whiff. The analysis lives in `whiff_fix.py`, was proven in game, and was then **lost when the graph was rebuilt from the clean baseline** — a process hazard worth as much as the fix.

The engine reaches specials **by name via the jump nodes**, not only through the `nexts` walk, so neither removing edges nor gating the destination is sufficient alone: a buffered input enters *before the parent attack resolves*, at which point `hit_combo_stop` / `guard_combo_stop` have no outcome to evaluate.

1. **Drop the special ids from the openers' `nexts`** — `hi01(85)` → `[hi02, hi_chain, lo02]`; `lo01(0)` → `[hi02, lo_chain, lo02]`.
2. **Clear `atk_syunpo_short_cut` / `sp_over_atk_short_cut` on the opener.** pl000 puts these on the 2nd or 3rd hit of a string, never the first.
3. **Set `hit_combo_stop = guard_combo_stop = 1` on `jump_sp_atk`(27), `jump_sp_break`(28) and `jump_ex`(45).** ★ pl000 ships exactly this; **pl005 had all three ungated**, inherited from the sp000 boss file. This is the layer that actually closes the leak, and it is why the EX became whiff-cancellable the instant it was wired into the string. (pl001 leaves them open.)

Already correct on pl005: `sp_overatk01_d1` / `_u1` (102/103) carry `hit_combo_stop`/`guard_combo_stop`, so `lo01 → lo_chain → overatk` is destination-gated, the same as pl000 and pl001. The **base** `_d` / `_u` pair stays ungated on every character — that is the neutral R2 overatk and it is meant to be open.

#### The grab family

| node | ids | shape | what it is |
|---|---|---|---|
| `atk_gr01` | 5 (`Pad_R1`), 74 (**`RecvEvent`**) | HIT @6, **dmg 0**, cancel 55 | the catch attempt |
| `atk_gr02` | — | HIT @36, **dmg 1000**, cancel 46 | the confirm attack |
| `atk_gr02_1` | 75, 76 (`Pad_R1`) | 4 blocks, **no hit**, `clash_parry_type` 1 and 2 | the grab **clash**, not the whiff |

**`atk_gr01` is what plays on a miss**: when the catch connects at frame 6 the engine hands straight to `atk_gr02`, so anything scheduled later than frame 6 in `atk_gr01` fires *only on a whiff*. **Rule: on a grab, put follow-up behaviour on gr02, not gr01.**

The grab confirm was grafted from **pl051 = Ichigo (TYBW)** — the four Ichigos are pl000 Shikai, pl001 Bankai, pl002 Final Getsugatensho and pl051 TYBW (`DataChakka-main/GAME_CATALOG.md` names them all). An unusually clean donor: it already uses **`COM_sp_Atk_yl`**, Zangetsu's own yellow arc, and **14 `COM_tm_Syunpo00` flashes at frames 10 and 22**, so the warp-behind at frame 22 lands on its own second flash burst. It also brings `WorldSpeedChange (24,30)` — impact framing pl005's confirm lacked and which pl000 and pl012 both have. Only 2 donor strings needed handling (`pl051_atk_gr02_vo` → `sp000_atk_gr02_vo`; `pl051_ktn_hi_R` dropped). 21 → 35 blocks. Script: `graft_gr02.py`, live-patching.

The whiff (`atk_gr01`) was then grafted wholesale from pl051 as well. Why his read as violent, visible directly in the data:

| | HeightHoming | HomingAngle | **ModelRotate** | cancel |
|---|---|---|---|---|
| pl005 | (0,6) | 40 | **180** = half-turn spin | 55 |
| pl051 | (0,10) | 10 | **90** | 75 |

11 → 8 blocks, voice → `sp000_atk_gr01_vo`, zero donor strings remaining. Zangetsu's `coll_radius` **0.5** was kept over pl051's 0.75 per the keep-balance rule — but he is the bigger character, so that is a candidate dial if the grab starts whiffing.

#### Method transfer: capping the Ichibei loop (pl050, 2026-07-31)

`Zangetsu Patch/ichibei_one_loop.py`; idempotent, `.preloop_bak` on tcmb **and** tadj, with `--base-only`, `--dry`, `--revert`. pl050 = HUOUSUBE = Ichibei. Live hashes tcmb `75ae10ece9608d8d`, tadj `dd9686cffc4866c3`; backups `73990f47dcc7d2a6` / `c20ea05da4849a4f`.

`atk_lo03`(85) → `sp_atk01`(104) is Ichibei-only; pl000 and pl052 stop lo03 at the overatk or the chain hub. Node 104 is the *combo* Ichimonji: 1500 damage, `damage_action` のけぞり小 (small flinch, where his other three sp1s blow away), `fix_time` 58, `CancelTiming` 108, `ComboStart (108,108) /1`, **`nexts` empty**. The hit ends on frame 60 so hitstun runs to about 118, but he acts at 108 — any light input then falls through to `start_lo` → lo01 → … → sp1 again. Evo is worse: the last hit ends at 102, `fix_time` **70** (raised from 58 post-CP), recovery 150, giving +22. Pass count was bounded only by the Reiryoku gauge: `CommonParam.fsv` `buff_range_reiryoku_0/1/2` = 3 segments, every Signature 1 costs 50 and every Signature 2 costs 100 → 150/50 = **three passes**. Nothing in the graph counted them.

The shipped fix is a private second light string — not removing anything, but widening the window `sp_atk01` already has and giving it somewhere to go:

```
lo01 → lo02 → lo03 → sp1 → lo01_1 → lo02_1 → lo03_1 → (no sp1)
```

| target | change |
|---|---|
| `sp_atk01`(104) | `ComboStart /1 (108,108) → (108,120)`; `nexts` [] → **[126, 117, 118]** |
| `sp_atk01`(274) | `ComboStart /1 (150,150) → (150,174)`; `nexts` [] → **[302, 282, 231]** |
| new base nodes | `atk_lo01_1` 126→[127,32] · `atk_lo02_1` 127→[128,32] · `atk_lo03_1` 128→[117,118,32] |
| new evo nodes | `atk_lo01_1` 302→[303,232] · `atk_lo02_1` 303→[304,232] · `atk_lo03_1` 304→[282,231,232] |

The window end equals the end of hitstun, so a light pressed *after* it still falls through to the normal lo01 — it just no longer combos. One loop, then a clean neutral reset.

★ **The second string is deliberately CLOSED.** lo01 and lo02 normally also offer `atk_hi02` and `atk_ex02`, and both lead back to the *original* `atk_lo03`, which has sp1. Every cross-cancel was dropped; only `atk_lo_chain` (sp2 + overatk) and the overatk pair remain. Verified by walking the graph: from 126 → 22 reachable nodes, from 302 → 34, **zero `sp_atk01` variants, and the original lo03 unreachable**. Any future "alternate string" graft needs this same closure check — **the leak is never the direct edge, it is the hi/EX cross-cancel two hops later.**

**Not closed:** `atk_hi01`(9) → `atk_lo02`(95) → lo03(85) → sp1 is a second path to the same sp1, and `atk_hi02_2`(107) → `sp_atk01_1`(105) is a third. Capping those is the same graft one level up.

---

### Two ways a port loses its combo graph

#### 1. The graph is never opened — the attack wall

`Script/Action/pl005.tcmbpkg` was **absent from `Fnames/file_exist.htable`**. It *is* in `filename.bin` (`pl005_combo` → `Script\Action\pl005.tcmbpkg`) and it *is* on disk, but those are two independent gates and a file needs both. A perfect 48/48 classifier: the `.tcmbpkg` entry is missing from the htable for exactly **pl005, pl009, pl028, pl030, pl034, pl040, pl041** — precisely the seven reserved slots that load, move and animate but cannot attack. `.tadjpkg` and `Motion\plNNN.tactpkg` *are* registered for all seven, which is why models, skeletons and non-attack motion work.

The fix is one htable entry: `crc("Script\Action\pl005.tcmbpkg") = 0xCDB8D7A8` under directory crc `0xEA72B6CA`. This is registration-table material and is covered in full elsewhere; it matters here only because it establishes that **no amount of moveset data can matter until the graph is opened** — and it retired two earlier conclusions that were artefacts of the same hidden variable (see the catalogue).

#### 2. The graph is a boss's — total input lockout

**Proven in game 2026-08-06 on Barragan (pl030, ported from boss en036).** The character kept **every** input dead: could not walk, run, hoho or attack. Only being hit, a reverse action, or a forced state exit produced a single action, then it locked again.

**The cause was `pl030.tcmbpkg` being a copy of the donor boss's combo graph.**

**The fix: replace a boss donor's `.tcmbpkg` with a playable character's graph.** Action names are generic (`atk_lo01`, `ntrl_in`, …), so a playable graph resolves against the port's own act_data. For pl030 the donor was **pl015 (Yumichika)** — identical shape to the boss graph it replaced: **50 nodes, header `version 103 / max_next_id 4 / max_variables 22`**. Barragan's own `tactpkg` and `tadjpkg` were kept; only the graph changed, and he moved immediately. **Match on node count plus header when choosing the donor graph.**

Symptom signature: total input lockout, where the only things that move the character are damage, a reverse action, or a forced state exit, and each buys exactly **one** action before re-locking. If a port shows that, go straight to the graph.

⚠ *Flagged as unproven:* the mechanism is suspected but not demonstrated — boss `move00`/`move01` nodes bound to player buttons (pl030's id 74 was `move01` on `Pad_R_Left`), or a root that never yields. The fix does not depend on knowing which.

Residual work on pl030 after the swap: 19 pl015 node names have no matching `act_data` on pl030 — mostly `*_chain` terminals (likely harmless) plus `atk_lo01_d/_u/_d01/_u01`, `sp_atk01_1`, `sp_break01_1`. Either add act_data or prune the nodes. ★ **Missing act_data = frozen in place.**

---

### Bug catalogue

Every entry states the symptom, the wrong hypothesis where one was recorded, the real cause, and the fix. The retracted theories are here on purpose.

#### The `memo` field: a string read as one byte

**Symptom.** Blobs "left unexplained non-zero bytes after the last block"; `dash_fix.py` declared them unparseable and refused to edit them. On pl005 that put `atk_hi02`, `atk_lo01_d01` and `atk_lo01_u01` off-limits.
**Wrong hypothesis.** "The tadj sub-block framing model is incomplete" — carried as an open item in the moveset notes and in the blueprint's §8.3 for weeks, with a guard in `grab_warp.py` refusing any blob that did not walk clean.
**Real cause.** `dash_fix.py`'s walker skipped a **fixed 1 byte** where `memo` sits (`i += 14` = 1 + 12 + 1). That is correct only when the memo is empty, which is the common case. Any block carrying a memo desynchronised the walk, and the casualties were exactly the interesting blocks: **every multi-hit `Attack_Melee`** (hits are labelled `01HIT目`, `02HIT目`, …) and **every per-joint `Effect_OneShot`** (`head`, `thorax`, `knee_R`, …). The walk was ending early, so the remainder of the blob looked like tail junk. **The framing model was never incomplete — it was being read wrong.**
**Fix.** `memo` parsed as a NUL-terminated string; `Zangetsu Patch/tadj_lib.py` replaces the walker. 8149/8173 blobs across the whole roster parse and rebuild byte-exact.

#### Copy-and-rename produces a silent dead node

**Symptom.** Two independent strings on pl015 ran and then stopped dead one hit early. No crash, no log.
**Real cause.** `atk_lo03_d01` / `_u01` were copies of `atk_lo01_d01` / `_u01` with only the *archive entry* names changed. The engine binds on the blob's internal node name and motion name, so both entries still identified as `atk_lo01_*`.
**Fix.** Four length-preserving `lo01 → lo03` edits inside the blobs, leaving `se_name*` alone. Audit added: `pl015_stepchain_fix.py --check plNNN`.

#### The inverse: renaming the motion too

**Symptom.** A silent dead *action* — the node is reached but nothing plays.
**Real cause.** The motion string is the key into the `.tactpkg` inner JSON. Rewriting it sends the engine looking for a tact key that does not exist.
**Fix.** When cloning, rewrite **only** the node string; copy the motion string verbatim, whether it is a full path (`1_normal\attack\atk_gr01`) or bare (`sp_atk02_2`).

#### The backslash-count regex

**Symptom.** An identity audit that matched nothing.
**Real cause.** The tact inner key holds **one** literal backslash. In a raw Python string that is `\\`, not `\\\\`.
**Fix.** Corrected the pattern. Cost one round.

#### The first light-string build rewired a dead node

**Symptom.** Graph edits applied cleanly and had no effect in game.
**Real cause.** **tcmb node names are not unique.** pl005 has two `atk_hi01` nodes, ids 9 and 85; only 85 is referenced. A name-based `re.search` finds id 9 first.
**Fix.** Address nodes by `_uniqueID`. `light_string.py` uses `node_spans()` (a list) rather than a dict.

#### `combo_patch.py` silently drops duplicated nodes

**Symptom.** Edits to some nodes vanished with no error.
**Real cause.** `node_blocks()` returns a dict keyed by node name, so all but the last block of every duplicated name is discarded. Latent in any dict-keyed helper.
**Fix.** Replaced with the list-returning `node_spans()`.

#### hi01 → lo02 "very inconsistent and extremely tight"

**Symptom.** Berg reported the transition worked only on a narrow, unreliable timing.
**Wrong hypothesis (implicit).** A `ComboStart` window problem.
**Real cause.** `atk_hi01` (id 85) carried `act_frame_min` 18 / `act_frame_max` 30 — 発動に有効なアクションフレーム範囲, a hard 12-frame input-acceptance window. **pl000 and pl001 both leave hi01 at 0/0.** Cloning from `atk_hi01` drags 18/30 along; the dash attack had hit the identical trap.
**Fix.** Cleared to 0/0. **Rule: whenever a transition feels like a timing trick, check `act_frame` before `ComboStart`.**

#### "Insane knockback, launches the opponent too far"

**Symptom.** lo03 launched instead of flinching.
**Wrong hypothesis (implicit).** A knockback magnitude to tune down.
**Real cause.** A reaction **class**, not a number: `damage_action = 吹き飛び` (blow away) with `blow_power = 吹き飛び小` and `move_rate 1.0`. Every standard lo03 uses `のけぞり小(方向参照)` (small flinch) with `blow_power 無し`.
**Fix.** Copied pl052 Yhwach's lo03 four knockback fields **verbatim as bytes** — `blow_power`, `damage_action`, `damage_move_rate`→0.0, `blow_dir`→(0, −0.5, 1) — rather than hardcoding cp932 literals. **Generalises: if a move launches wrongly, check `damage_action` before touching any number.**

#### Invisible sword mid-swing

**Symptom.** The weapon disappears during a transplanted animation.
**Real cause.** A donor lo02 needs **both** clips: `pl012_atk_lo02` *and* `pl012_atk_lo02_wp00`, the weapon track.
**Fix.** Bring both.

#### `SoulRebootTiming` did nothing

**Symptom.** Adding `SoulRebootTiming (41,63)` to lo03 had no observable effect.
**Real cause.** SRT alone does nothing; the matching `ComboStart (41,63)` with `AfterComboReset = 0` is what opens the by-name chain.
**Fix.** Added the paired `/0` window.

#### lo03 swallowed a fresh lo01

**Symptom.** After lo03, pressing light did nothing at all until he moved or guarded.
**Wrong hypothesis, later corrected.** Recorded first as "`AfterComboReset = 1` is the combo RESET point and must be a POINT, not a window" — pl000 (54,54)/cancel 54, pl001 (46,46)/46, pl012 (52,52)/52, pl052 (64,64)/64, and pl005's own lo02 already at (39,39). lo03 had inherited a **window** (44,63) from `atk_lo01_u01`.
**Real cause (corrected by the pl050 work).** The window was capturing the input and **finding no matching route in `nexts`** — lo03's `nexts` held the EX and the chain hub, and no lo route. `AfterComboReset` does not switch the lookup away from `nexts`; it only decides whether the combo counter resets. Moving or guarding reset the state by other means.
**Fix.** Converted to a point at 63, which stops the input being eaten (it still does not *combo* into lo01). The corrected model — window ⇒ resolve against `nexts`; no window ⇒ fall through to neutral — supersedes the original write-up.

#### The whiff gate worked on one hi01 and not the other

**Symptom.** Pass 13's whiff gating held on some routes and leaked on others.
**Real cause.** There are **two `atk_hi01` nodes**. Pass 13 gated id 85 (what `start_hi` points at) and left id 9 holding `atk_ex01` in its `nexts` with no hit/guard gate. Nothing in the graph references id 9 — which is exactly the signature of a node entered **by name**, the same reason the ungated `jump_*` nodes leaked. The id is not canonical (hi01 is 103 on pl000, 9 on pl001), so id 9 could not be written off as dead.
**Fix.** Made both identical: EX dropped, `atk_lo02` added, `hit_combo_stop`/`guard_combo_stop` = 1. **Generalises: when a fix "works on one move but not its twin", count the nodes with that name.**

#### Gating the opener was wrong — pass 14 retracted by pass 15

**Symptom.** After pass 14, "can't press hi01 until I hit" — the opener locked out following a whiff.
**Wrong hypothesis.** That `hit_combo_stop` / `guard_combo_stop` on hi01 would prevent cancelling *out of* hi01 on whiff.
**Real cause.** On a node those variables gate **entry into that node**. Neither reference character gates hi01: pl000 (id 103) and pl001 (id 9) both carry all-zero variables.
**Fix.** Cleared on both ids. **Whiff protection belongs on the destination, never on the opener.**

#### The overatk leak survived, because EX and overatk take different routes

**Symptom.** After the EX leak was closed, the overatk was still cancellable on whiff.
**Real cause.**

```
pl005  atk_hi01 -> atk_hi_chain(33) -> jump_sp_break(28) -[by name]-> start_sp_break
                                    -> sp_overatk01_d/_u     ← the BASE pair, UNGATED
pl000  atk_hi01 -> atk_lo_chain(32) -> sp_overatk01_d1/_u1   ← GATED
```

pl005's `atk_hi_chain` is a **pure jump hub** — its only exits are `jump_sp_atk` and `jump_sp_break` — where pl000's goes straight to the gated `_1` pair, and pl000 only reaches `atk_hi_chain` from `atk_hi02`, never from the opener. The by-name route terminates on the **base** `_d` / `_u` pair, which is ungated on every character by design because it is the neutral R2 overatk from idle. Gating the jump node did not hold: a buffered R2 enters before the parent attack resolves.
**Fix.** Swap `atk_hi_chain`(33) → `atk_lo_chain`(32) in hi01's `nexts`, on **both** ids. That reproduces pl000's shape.

#### The grab warp fired only on a miss

**Symptom.** The teleport-behind never appeared on a successful grab.
**Wrong hypothesis.** That `atk_gr01` is the grab, so follow-up behaviour belongs there. Pass 13 put the `Warp` in `atk_gr01` at frame 12.
**Real cause.** `atk_gr01` is the *attempt*: the catch connects at frame 6 and the engine hands straight to `atk_gr02`, so anything after frame 6 in `atk_gr01` fires only on a whiff.
**Fix.** Moved to `atk_gr02` at frame 22 (before the confirm hit at 36), plus 4 `Afterimage` blocks. **Rule: on a grab, put follow-up behaviour on gr02, not gr01.**

#### "Warps behind, then snaps back to the front"

**Symptom.** Exactly that.
**Wrong hypothesis.** Overshoot — the warp distance was too large. Pass 15 had already pulled `pos` from −2 to −1 and the symptom persisted.
**Real cause.** A **block collision**. `atk_gr02` has `HeightHoming (10,30)` and the `Warp` was firing at **22, inside that window**. The warp placed him behind; homing then ran 8 more frames and dragged him back onto the target. Distance was never the issue.
**Fix.** Moved the `Warp` to frame **31** — after homing closes at 30, before the hit at 36. **Rule: a `Warp` must sit outside every `HeightHoming` / homing window in the same action, or it gets undone.** Residual drift after this would be the animation's own root motion, which no block controls directly; `MotionMoveRate` from the warp frame is the next lever.

#### The grab reads as a teleport / "waay too intense"

**Symptom.** Berg on the missed grab: an enormous rotation.
**Real cause.** `HomingAngle` 90 on `atk_gr01`, inherited from pl003, with `ModelRotate_Start/EndFrame` 180 (a half-turn spin). **pl000 ships `HomingAngle` 10.** The wide angle is what reads as a teleport in the first place — that was the *desired* effect on the v2 grab warp and the *undesired* one on a miss.
**Fix.** 90 → **40** in pass 15 (keeps tracking without the lurch), then the whole action grafted from pl051 (`HeightHoming` (0,10), `HomingAngle` 10, `ModelRotate` 90, cancel 75) in pass 16.

#### `atk_gr02_1` is not the whiff

**Symptom.** The name suggests a grab whiff and invites edits.
**Real cause.** Nodes 75/76 carry `clash_parry_type` 1 and 2 — this is the grab *clash*.
**Fix.** Left alone.

#### lo03 opened an infinite

**Symptom.** lo03 loopable into itself after pass 13.
**Real cause.** Pass 13 cut lo03's cancel from 79 to 63, shortening his own recovery while the opponent's hitstun stayed at 35.
**Fix.** `atk_lo03` `fix_time` 35 → **25**.

#### `sp_step_atk` is not the shunpo

**Symptom.** Wiring it to `Pad_R_Down` stole the dash button.
**Wrong hypothesis.** That `sp_step_atk` is Zangetsu's shunpo.
**Real cause.** It is a reverse-meter combo extension that follows hi/lo/overatk and teleports onto or behind the target. The real shunpo is L2 then X; the **perfect** shunpo (`syunpo_out_just`) is that done just before an incoming hit, and that is the animation Berg wanted.
**Fix.** `sp_step_atk` fully removed from the v2 build; it needs a bespoke animation set in its own session.

#### `HOHO_FOLLOWUP_GUIDE.md` told another dev to wire `00 → 01 → 02`

**Symptom.** N/A — caught in review before it broke anything, but it was published guidance.
**Wrong hypothesis.** That the hoho follow-up chain advances through `nexts`.
**Real cause.** `sp_step_atk00` and `sp_step_atk01` have **empty `nexts` in every shipped character** (pl000, pl020, pl032, pl005), and nothing points at `01` or `02`. **The chain advances on the `AutoCombo` input.** Only `02`'s `nexts` matters, and even that is optional (pl020 has none).
**Fix.** Both copies of the guide on Berg's disk revised.

#### The orphan `AutoCombo` node

**Symptom.** A newly added `AutoCombo` node fired off unrelated moves throughout the kit.
**Wrong hypothesis.** That a `my_action` latch target needs a matching tcmb node.
**Real cause.** **73 of the game's 78 latch targets have no tcmb node.** An `AutoCombo` node that nothing points at is *globally* eligible and fires off any `ComboStart` in the moveset.
**Fix.** `sp2_v15_autocombo.py` undid the addition.

#### The v1 walk transplant: base wrong, evo perfect

**Symptom.** After v1, the base-form walk was still wrong while the evo-form walk looked flawless.
**Real cause.** v1 injected the donor's walk *tadj* entry alongside the motion. pl005 has no `2_evo` actions at all, so evo fell through to the injected `1_normal_move_walk` act_data with no tadj in the way, while base went through the donor tadj entry and did not.
**Fix.** **Transplant motion only** — act_data + clips + blend row. Never the donor's tadj, except for attacks where the tadj carries the hitbox; for those, strip `pl0NN_*` / `P0NN_*` strings so only shared `COM_*` effects survive.

#### `reiryoku_cost` retuning — rejected after it worked

**Symptom.** None — the build functioned exactly as intended.
**What was done.** The first Ichibei build raised node 104's `reiryoku_cost` from 50 to 100 so the gauge could only pay for one pass.
**Why it was rejected.** Berg: *"changing the sp_cost would break the game's rules."* 50 = Signature 1 and 100 = Signature 2 is a game-wide convention (the maximum cost anywhere in `pl*.tcmbpkg` is 100); a character-specific price breaks the shared language players read off the UI.
**Fix / rule.** Treat `reiryoku_cost`, and the 50/100 tiers generally, as **read-only**. Limit a route by graph shape or frame data, never by repricing it. The same instinct applies to any other game-wide constant (damage tiers, gauge segment sizes). Also note the scope reading: "loop only once" meant *one loop*, not zero — killing the follow-up entirely via a knockdown reaction or longer recovery would also have been wrong.

#### "A `.tcmbpkg` contains attack routing only" — the claim that cost four passes

**Symptom.** pl030 Barragan had every input dead, including walking.
**Wrong hypothesis, asserted confidently after a population survey.** *"A `.tcmbpkg` contains attack routing only — neutral, walk, run, step, guard and damage have no nodes in any character's graph, so a boss graph cannot stop a character walking."*
**Real cause.** False. The boss graph demonstrably locks everything. The claim ruled out the real cause early and sent four passes into motion, act_data and tuning instead.
**Fix.** Replace the boss graph with a playable's. **Method lesson: wholesale substitution, then bisect.** Eight passes of field-by-field comparison against working playables found real bugs and never the cause, because *conformance checks tell you a file looks right, not that it is right.* The procedure that worked: (1) byte-copy a known-good playable's `tactpkg` + `tadjpkg` + `tcmbpkg` over the port's — `tmo_name`s are fully qualified, so clips resolve to the donor's package with no renaming; (2) test — he moved, which cleared the slot, registration, tables and exe in one shot; (3) restore the port's own files one at a time, testing after each. Three tests isolated it. Backups in `Zangetsu Patch/_pl030_bisect_bak/`.

#### The attack wall retired two earlier conclusions

**Retired: "there is an exe-side, index-keyed attack gate."** It rested on a Nel clone on pl009 failing while pl042 worked. pl009's `.tcmbpkg` is missing from the htable too. There is no index-keyed attack gate in the exe — which is why every search for one (per-id table, bitmask, runtime-built set) found nothing.
**Retired: "the donor moveset exonerates the data."** Swapping the *bytes* of `Script/Action/pl005.tcmbpkg` cannot matter when that path is never opened. The result was predetermined.
**Rule.** `filename.bin` and `file_exist.htable` are independent gates. A stock `filename.bin` entry only proves the devs reserved the *name*; only `file_exist.htable` says a file was ever shipped. When an added file does nothing, check the existence table **before** reading more disassembly.

#### Auditing the wrong copy of another dev's work

**Symptom.** A wrong conclusion about the other dev's Yumichika build, later reversed.
**Real cause.** The audit ran against the **live game files** instead of Berg's upload folder.
**Fix / rule.** **Always check `<gamedir>/CRE Placeholders/` — that is where other devs' handoffs live.**

#### "pl030 is a misfiled Yumichika, it just needs a rename"

**Symptom.** `pl030.tcmbpkg` is md5-identical to `pl015.tcmbpkg`, which reads as a filing mistake.
**Wrong hypothesis (Berg's).** That the dev put Yumichika's files under pl030 instead of pl015 and only a rename is required.
**Real cause.** It is **one file**, it is **deliberate**, and renaming it back would restore en036's boss graph and re-lock every input. Evidence that pl030 is Barragan and pl015 is Yumichika, both correctly placed: `pl030.tadjpkg` effect banks include `E036` ×7 and voices `en036` ×2 (the Barragan boss donor) plus pl016/pl050 borrowings, while `pl015.tadjpkg` is COM effects only with `pl015` voices ×19; `pl030.tactpkg` has 190 entries and 253 `pl030_*` clips plus evo/rev, where `pl015.tactpkg` has 68 entries, `pl015_*` clips and no evo/rev; pl030 has its own `pl030_cos00/cos01/face00` models; `BROS_CHARACTER_ID_MAP.md` lists pl015 = YUMICHIKA, PLAYABLE and pl030 = EMPTY; and `cre_tables.py` registers CRE's Yumichika as **pl015** (`('pl015','pl016',…) # Yumichika -- Ruri'iro Kujaku`) — an existing playable being *extended*, not a new slot.

#### The *other* dev's Yumichika genuinely is misfiled — and a file rename is not enough

**Symptom.** `CRE Placeholders/Yumichika/pl030.{tactpkg,tadjpkg,tcmbpkg}` is Yumichika's data under the pl030 name.
**Real cause.** He set the character id to pl030 in his authoring tool, which stamped both the output filenames **and the tactpkg's nested motion-archive entry name**. The payload stayed Yumichika because he was editing Yumichika. Proof: **0 occurrences of the string `pl030` inside any of the three files**; `pl015` appears 38× in the tadjpkg; clips are `pl015` ×108 + `blend` ×17 + `pl000` ×3; voices `pl015` ×19 + `pl000` ×6. The content is live pl015 **plus** work: tactpkg +3 actions (`sp_overatk01`, `sp_step_atk01`, `sp_step_atk02`), tadjpkg +7 entries (`sp_overatk01_d/_d1/_u/_u1`, `sp_step_atk00/01/02`), tcmb +7 nodes (ids 98–104, same names), 50 → 57 nodes.
**Fix.** Rename the three files `pl030.*` → `pl015.*` **and** rename the inner tactpkg entry `pl030` → `pl015`. ⚠ Dropping this on pl015 overwrites vanilla Yumichika, which is presumably intended. ⚠ Also check before shipping: `sp_overatk01_d/_d1/_u/_u1` and `sp_step_atk00` have **tadj tuning but no act_data entry** — missing act_data means frozen in place.

#### `BLEND_*` wrappers on the wrong rig target

**Symptom.** Found during the pl030 investigation; a genuine defect, not the cause.
**Real cause.** 26 `BLEND_*` wrappers on rig target `character_body`. **0 shipped playables use that target; all 5 reserved slots do** — pre-release template residue.
**Fix.** `character_body` → `body`.

#### Torn animation chains

**Symptom.** Five multi-segment chains broken.
**Real cause.** A multi-segment chain shares one clip, so a successor's `start_frame` must equal its predecessor's `end_frame`. An earlier pass moved `end_frame` alone.
**Fix.** 12 `start_frame` seam repairs.

#### Empty attack entries

**Symptom.** pl030 attacks that did nothing.
**Real cause.** 19 of 40 attack entries had no `ComboStart` / `CancelTiming` at all. The shipped population has **1 such entry in 2893**.
**Fix.** Added to 22 entries. (Hitboxes on those 19 remain open.)

#### `--probe ntrl` froze the build by construction

**Symptom.** The probe harness produced a frozen character every time.
**Real cause.** It parked actions in `ntrl_in`, which is itself in the `ntrl` group.
**Fix.** Harness repaired to park in `ntrl_loop`.

#### Population tallies inflated by the template slots

**Symptom.** Population surveys returning misleading consensus.
**Real cause.** The four other reserved slots (pl028, pl034, pl040, pl041) share one pre-release template and therefore co-vote as if they were four independent observations. pl030 is a real port (201 KB tadj / 25 MB tact) where those four are untouched template (~98 KB / ~16 KB).
**Fix.** Exclude them from any population count.

#### Refuted along the way — do not re-walk

* **The boss-break / Respira mechanic did not transplant.** pl030's tuning has **0 block types and 0 (block, field) pairs** that no shipped playable has (584 blocks compared against 38 playables). `WeakPoint` — the boss-break block — was never copied.
* **The break gauge lives in `CharaStatus.fsv`** (`rate_max_kyokaku`, `rate_add_kyokaku_frame`, `kyokaku_breakback_frame`). All 55 `en*`/`sp*`/`ad*` rows carry it; all 48 `pl*` rows are blank. It is enabled by the **destination** row, so no donor asset can carry it in.
* **`sp000` has the break gauge too** (`0.60 / 0.001 / 300`), so "Zangetsu's donor lacks the boss mechanic" is false and the correlation that theory rested on never existed.

#### Tooling hazards

* **`attack_test.py restore` would overwrite the transplanted files** with pre-everything `.zangetsu_orig` copies. Use each script's own `--revert`.
* **`fix_attacks.py` rebuilds from `file_exist.htable.orig_bak` with hardcoded lists.** After the pl036 costume registrations (2026-07-26) it is **unsafe to rerun as-is** — it would drop them. Patch current tables incrementally instead (the `register_costume_models.py` pattern).
* **Rebuild-from-backup scripts discard later work.** `light_string.py` rebuilds from `.prelight_bak` and discards `tune_pass13.py`; `v2_build.py` discards `grab_warp.py`. Correct order: `v2_build` → `grab_warp`; `light_string` → `tune_pass13`; everything from pass 14 onward is **incremental against the live files** because Berg hand-tunes between passes.
* **`recon.py`'s `xref_rip`** can report a mid-instruction match one byte late — cross-check with `dis`.

---

### State, dials and open items

**Live hashes (2026-07-27):** `pl005.tadjpkg` = `pl005_modded.tadjpkg` = **5be2eca065ccf53c**; tcmb 42,764 B / 65 node blocks / valid JSON; tact 87 acts / 90 clips. pl050: tcmb `75ae10ece9608d8d`, tadj `dd9686cffc4866c3` (backups `73990f47dcc7d2a6` / `c20ea05da4849a4f`).

**One-value dials already identified:** lo02 `coll_radius` 2.40 (`GEOMETRY` in `light_string.py`); grab `HomingAngle` (pl000 ships 10, we run 40); grab `coll_radius` 0.5 versus pl051's 0.75, kept per the balance rule but a candidate since Zangetsu is the larger character; Ichibei's window ends `(108,120)` / `(150,174)` — widen if the second string does not come out on a buffered press, shrink if non-light inputs feel eaten in that stretch.

**Open:**

1. **Standardisation scope is unresolved and needs Berg's decision before anything is applied.** Overatk already equals pl000 exactly (1200/600, 600/180) — does −10% apply to it? **EX has no reference at all**: pl000 has no `atk_ex01`, pl001's has no attack block, and pl005's is 1500/600 inherited from pl000's `sp_atk01_2`. The hi chain is far off pl000 (hi01 900 vs 500, hi03_1 1000 vs 450, da01 400 vs 200×2), so including it in "whatever else" would be a large nerf.
2. `base_damage_rate` mismatch — pl000 runs 1.0, pl005 0.7–0.8, so matched raw damage will not total the same in a combo. `--match-rate` on `stepatk_damage.py` aligns it.
3. `sp_step_atk` follow-up — needs its own animation set (Berg: "original creations").
4. **EX identification** — still unidentified; leave it alone.
5. Ichibei's high string is **not** capped: `atk_hi01`(9) → `atk_lo02`(95) → lo03(85) → sp1, and `atk_hi02_2`(107) → `sp_atk01_1`(105).
6. Most of the above is **untested in game**. The v2 build (walk, overatk gating, break chain, perfect-shunpo, grab warp), passes 13–16, and the Ichibei loop cap were all recorded as awaiting Berg's in-game test.

**Berg's standing corrections, carried forward:** do not import donor effects, VFX or voice — identity must stay Zangetsu's; the universal break chain is *overatk → charge → break → break-with-soul-damage on hit*; his lo chain was originally non-standard (lo01 plus a lo01 follow-up, no lo02/lo03) and he liked it, which is why the standard chain was rebuilt rather than assumed; and **there is no intensity dial for an animation — an over-done pose must be swapped, not tuned.**agentId: a9eefa4b85d024c1f (use SendMessage with to: 'a9eefa4b85d024c1f', summary: '<5-10 word recap>' to continue this agent)
<usage>subagent_tokens: 85667
tool_uses: 12
duration_ms: 457812</usage>


---

## Part 4 — Movement, steps and animation

This section covers everything that moves pl005 — the locomotion speed columns, the step system and its four timing gates, the dash attack, the `sp_step` / hoho work, homing and tracking, the EX move, and the `tmo1` animation container that all of it ultimately drives. Where two notes disagree, the disagreement is called out rather than smoothed over.

---

### Root motion: what has it and what does not

This is the single fact that makes the rest of the section legible, and it is easy to get wrong because **walk and steps are both dialled with `MotionMoveRate`** while only one of them is actually a clip multiplier.

**Walk has no root motion.** `pl052_sp_walk_f` is a 100-frame clip whose only translating node drifts **0.0007 units in total** — the walk clips are in-place cycles. What actually moves the character is the **`walk_speed` column in `Script/CharaStatus.fsv`**; `MotionMoveRate` is a multiplier layered on top of that column. The same conclusion is corroborated independently from the animation side: the `tmo_lib` validation pass reconstructs `sp000_run_f` as a textbook run cycle — feet planted at 0.015 and lifted to 0.10, head bob 1.547–1.590, feet in antiphase at ±0.45 — and explicitly **in place**. So run clips are in-place too, and `run_speed` is the lever there.

**Steps do carry root motion.** Step clips physically travel, so a step's `MotionMoveRate` is a true multiplier on the clip. The consequence is that **a cross-character step rate is a meaningless anchor** — 1.40 on pl005 and 1.40 on pl000 are only comparable if the two clips are the same clip. The only meaningful comparison for a step rate is against the same character's own previous numbers.

**Attacks carry root motion too**, which is why the measuring rule below (see *Homing and tracking*) exists.

#### The `CharaStatus.fsv` speed columns

```
                walk_speed  evo_walk_speed  run_speed  evo_run_speed  dash_speed
pl000 Ichigo-1  0.03        0.03            0.06       0.065          0.145
pl001 Ichigo-2  0.03        0.03            0.045      0.045          0.155
pl002 Dangai    0.02        0.02            0.035      0.035          0.145
pl005 Zangetsu  0.03        0.03            0.06       0.065          0.145
pl020           0.02        0.0225          0.0225     0.0225         0.14
pl052 Yhwach    0.03        0.03            0.03       0.03           0.13
```

Decode the file with `status_patch.py`'s `_cso_` cipher (`decode` / `encode` are importable). 72 columns, header on row 0.

Three consequences worth internalising:

* **No shipped character has a walk `MotionMoveRate` row at all.** Polled across pl000–pl006, pl015, pl020, pl052: zero. Everyone walks at exactly `1.0 × their own column`. Any walk rate row in the build is therefore **ours**, and a rate of 2.5 means the character walks at 2.5× *the entire roster*, not 2.5× some notional "normal".
* **Walk speed barely varies.** 0.03 is the common value and 0.02 (Dangai, pl020) is the floor. Yhwach and Ichigo-shikai-in-evo are literally the same number, so if a request names two characters as walk references, verify they actually differ before building around the contrast.
* **Run speed is where characters separate** — Yhwach at 0.03 against Ichigo's 0.06 is a clean 2×. When someone describes a character as "much slower", they are almost certainly seeing the run, not the walk.

pl005 shares Yhwach's walk animation outright (`blend_walk` = `pl052_sp_walk_f/r/l/b`), so at rate 1.0 he is **frame-identical** to Yhwach, not merely similar.

#### pl005's current move-rate shape (`move_rates_v1.py`, 2026-08-10)

```
                        ENHANCED<2              ENHANCED>=2
walk                    0.666667 -> 0.02        1.000000 -> 0.03
step_f_act              0.980000                1.400000
step_l_act / step_r_act 1.008000                1.584000
step_b_act  f0-24       0.656250                0.937500
step_b_act  f25+        0.100000                0.100000
```

The design was deliberately inverted. A flat 2× buff read "waaay too strong" — it put buffed walk at 0.15, **above every character's dash**. So the previously tuned neutral set became the *enhanced* set and neutral dropped 30% beneath it. Enhanced now buys +43% forward, +57% sideways, +43% back and +50% walk (1.400/0.980, 1.584/1.008, 0.9375/0.65625, 0.03/0.02 respectively).

Two notes on that table. The forward and back enhanced values are straight carry-overs of the 2026-07-25 tuned numbers (1.40 and 0.9375); the **sideways enhanced value is not** — 1.584 is 1.10× the 1.44 that pass shipped, so the l/r row picked up an extra bump. And the claim recorded as "no value exceeds a shipped number" only holds in the sense that survives the notes' own rules: the walk column at 0.03 is a genuine shipped roster value, whereas the step rates are clip-relative and cannot be compared across characters at all (pl000 ships sidestep 1.200 / backstep 1.250 **with no forward row**, against clips that are not pl005's).

`move_rates_v1.py` writes **absolute** values from a table keyed by `(entry, gate, frame)` and asserts every edit is length-preserving, so re-running it is a no-op and it cannot compound.

#### `StepDashAddMove` — thin

`StepDashAddMove` appears in the project notes **only** as a named fallback lever for the movement buff, with no recorded semantics, no shipped values and no polled distribution. Treat everything about it as unestablished; the field name is the entire content of the note.

#### Bug — the gated movement buff could not be felt

*Symptom:* `MotionMoveRate` gated on `ENHANCED==2` / `ENHANCED<2` at a 2× diagnostic value, and in play the difference was imperceptible. *Real cause (cross-referenced, from the enhance-state / unique-gauge internals notes):* the enhance level lives in a **bitmask at `chara+0x1098`**, and `ENHANCED` *is that bitmask*, not a level ordinal. **`ENHANCED==2` therefore means "only level 2 is alive", not "level 2 is the highest active level"** — no gate anywhere computes a highest-active-level; highest-wins is a HUD-only behaviour. With levels 1 and 2 both alive the bitmask is 3 and the `==2` branch never fires. *Fix:* not recorded as resolved; the gate semantics are the correction to apply, with `StepDashAddMove` held as the fallback lever.

*Contradiction to flag:* the index records the 2× gated rate as something Berg **could not feel**, while the locomotion note records a flat 2× buff as **"waaay too strong"**. These can be reconciled — the flat 2× is too strong *on the numbers* (walk 0.15, above every dash), while the *gated* 2× may never have evaluated true in play — but that reconciliation is an inference, not something the notes state.

#### Bug — a rebuild-from-backup script that would have silently erased unrelated work

*Symptom:* none yet; caught by inspection on 2026-08-10 before the script was ever run. *Wrong pattern:* `sp1_motion_v1_aterie.py` rebuilt its action from `pl005.tadjpkg.preaterie_bak` so its knobs would stay absolute across re-runs — correct intent — but it did `actpkg.load(BACKUP)`, edited one entry, and wrote **the whole package** back. *Real cause:* whole-file restore against a shared package. Every unrelated edit made to that tadjpkg since the backup was taken would have vanished with no error — at the moment it was caught that meant the entire `ENHANCED>=2` movement gate set and the whole enhanced-SP2 ender. *Fix:* entry-scoped rebuild.

```python
live, rewrap = actpkg.load(path)             # write target = the LIVE package
bp, _ = actpkg.load(path + BAK)
pristine = bp.get(ENTRY)                     # pull ONE entry from the backup
d = tadj_lib.parse(pristine)
... edit ...
live.set(ENTRY, tadj_lib.build_padded(d))
```

The same applies to `--revert`: restore the **entry**, not the file. `pl005.tadjpkg` and `pl005.tactpkg` now have half a dozen scripts writing into them, so **whole-file restore is only ever correct for a file one script owns outright.** This is the third time this class has bitten — the `0xc0000005` crash came from restoring an exe backup that predated the gauge work, and one `--revert` on an early script silently rolled back four passes. Assume any `*_bak` older than today predates work you care about.

---

### The step system: four timing blocks

Every step in the tadj carries up to four timing blocks, whose frames are `f[1]`, `f[2]`. They are routinely confused with each other; they are not interchangeable.

| Block | What it gates |
|---|---|
| `ComboStart` | When an attack may be buffered out of the step — the general combo gate. |
| `CancelTiming` | When the step ends and control returns. **This is "recovery".** |
| `DashLoopCancelTiming` | The **dash-game** gate — the dash-attack window specifically. |
| `StepCancelTiming` | **Step-into-step**, not the attack window. |

`DashLoopCancelTiming` is the one that decides whether a dash attack is reachable from a given step. pl000 puts it on `step_f` / `step_l` / `step_r` but **not on `step_b`** — that is the built-in, deliberate reason a backstep cannot reach a dash attack. Opening it at frame 1 makes the dash attack need no timing at all, while leaving `ComboStart` later is what still keeps a plain hi/lo out of the first frames of a step.

`StepCancelTiming` wants to stay narrow. pl000 keeps it to a **4-frame sliver at the very end** (24–28 with the cancel at 28). Widening it makes steps endlessly spammable. The rule of thumb is `cancel-4 .. cancel`.

#### The `step_b` two-block trap

`step_b_act` carries **two** `MotionMoveRate` rows per gate: a burst over `f0–24` and a slow tail from `f25` on, the tail sitting at **0.1** in every state. **Scale only the burst** — the block whose window starts at frame 0.

*Bug — the shortened backstep drifts and feels floaty.* *Symptom:* scaling the backstep down made it drift rather than simply travel less. *Real cause:* the `f25+` tail is **deceleration**, and scaling it down stretches the settle. *Fix:* scale only the `f0–24` block. Patch **per block index, back to front** — patching by name alone rewrites the first block twice.

#### Bare entries versus `_act` entries

Playables leave the **bare** `1_normal_move_step_f/b/l/r` entries to `plcom` and carry only per-character `..._act` entries, which hold the timing, the `MoveRate` and the cancel windows.

*Bug — pl005's steps used boss timings.* *Symptom:* step recovery felt wrong and unlike any playable. *Real cause:* pl005 inherited sp000's **bare** entries (boss cancels 45 / 60 / 45 against pl000's 28 / 42 / 30) and had **no `_act` entries at all**. *Fix:* clone pl000's four `_act` entries **and** retime the bare ones to match, so the result is correct whichever layer wins. The `_act` / `_snd` split — `_act` carrying mechanics, `_snd` carrying sound — is the general playable scheme; pl005 had only the bare boss form of it.

#### pl005's step numbers (2026-07-25 pass, `dash_fix.py`)

```
step_f   cancel 42   rate 1.40      da window 1-42   step-into-step 38-42
step_b   cancel 37   burst 0.9375   tail 0.1         no da window
step_l/r cancel 35   rate 1.44      da window 1-35
```

`dash_fix.py` is idempotent, rebuilds from `*.predash_bak`, and supports `--revert`.

*Open:* the backstep **recovery animation** still reads clunky and floaty and does not blend into steps or runs — Berg's words, "rigid and floaty, doesn't fit him". The rate-tail fix may address it; if not, the fault is the sp000 clip itself and would need a `BLEND_` / transition or a borrowed `step_b` clip.

---

### The dash attack: two gates that both look like "the move doesn't come out"

#### Gate 1 — `_uniqueID` is canonical for the standard action set

The engine keys standard actions on their **id**, not their name. A node called `atk_da01` sitting on any other id is not a dash attack, and the light button just produces `lo`.

```
atk_lo01  0     atk_gr01  5     atk_da01  6     atk_hi03  7
start_lo  14    start_sp_atk 17 sp_atk01  20    atk_da_chain 31
atk_lo02  1     atk_lo03  2     atk_hi_chain 33 atk_lo01_u 52
atk_lo01_d 78   atk_ex01  79    sp_step_atk00 105
```

`atk_da01` is id **6** in pl000, pl020 *and* pl052; `atk_da_chain` is **31** everywhere. Character-specific variants are free-numbered by contrast — `atk_hi01` is 9 / 85 / 103 across different characters.

pl005's graph is the standard graph with nodes **deleted**: he keeps 5 and 7 with 0/1/2/6 empty, which is exactly the set of moves he lacks. **Restoring a standard move to a trimmed character means giving it its canonical id.**

*Flag:* the dash note lists `atk_gr01` as canonical id **5** and states pl005 keeps id 5, while the tracking note records pl005 holding `atk_gr01`(**74**, a `RecvEvent` node) as a roster-normal orphan. Both may be true (a canonical grab node plus a separate event-driven node sharing the name), but the notes do not reconcile them and the point is unverified.

#### Gate 2 — `act_frame_min` / `act_frame_max`

Memo: 発動に有効なアクションフレーム範囲最小値/最大値 — "the action-frame range in which activation is valid". It is a hard **input-acceptance window**. pl000 and pl020 both leave the dash attack at **0/0 = unrestricted**.

*Bug — the dash attack came out inconsistently, and more reliably against a blocking opponent.* *Symptom:* the move needed suspiciously precise timing, and felt more consistent on block than on whiff. *Real cause:* the node was cloned from `atk_hi01`, which dragged in `act_frame_min/max = 18/30` — turning the move into a 12-frame timing trick — and also dragged in `hit_combo_stop` / `guard_combo_stop = 1`, which is exactly why a *blocking* opponent behaved differently from a whiff. *Fix:* **a transplanted node's `variables` must match the reference character's values for that node, not the node it was cloned from.** pl000's and pl020's dash attack is everything zero except `in_stepdash = 1` (memo: `0無視、ダッシュ中のみ有効` — 0 = ignore, anything else = valid only during a dash).

#### Entry wiring and the run-into-dash-attack path

pl020 uses `start_lo -> ['6','89']` (dash attack first, then `atk_lo01`). pl000 and pl052 leave `start_lo -> 0` and still work, so a second entry path exists, but the pl020 form is sufficient.

*Bug — the dash attack after a run fired roughly 1-in-20 times.* *Symptom:* the move was reliable out of a step but almost never came out after running. *Real cause:* the "da after running" gate does not live on the step at all — it lives in **`dash_f_out`**. sp000's `1_normal_dash_dash_f_out` shipped `ComboStart (0,12)`, a 12-frame sliver; pl000 leaves it open for the whole action. *Fix:* pl000's values — `ComboStart (1,-1)`, `CancelTiming (12,100)`.

#### Attack trail effects

`atk_hi01` fires `COM_sp_Atk_yl` (thick yellow arc); `atk_lo01` uses `COM_tm_AtkLow00` (thin white) plus `COM_tm_AtkDistortion`. **Keep the donor motion's own `start_trigger`** when swapping an effect: the dash attack plays hi01's motion, which fires `1:T01_Slash`, so lo's `1:T01_Slash00` would never fire at all.

#### pl005's dash attack as built

`atk_da01`: id **6**, input **Pad_R_Left**, variables identical to pl000's, `nexts [31, 70]`. `act_data` cloned from his own `atk_hi01` (so it plays `sp000_atk_hi01`); tadj cloned from `atk_hi01` with reach 2.5 → **2.2**, damage 900 → **400**, trail switched to `COM_tm_AtkLow00`, and windows replaced with pl000's dash-attack values (`ComboStart` 22–28, `CancelTiming` 47).

*Flag — the two records of `start_lo` disagree, and the later one is authoritative.* The 2026-07-25 dash pass records `start_lo -> [6,78,52]`. The 2026-08-08 orphan sweep records pl005's `start_lo` as `["6","0"]` before its fix and `["6","0","78","52"]` after. The graph therefore changed between those dates — consistent with the revert incident documented below — and the current value is **`["6","0","78","52"]`**.

---

### The `sp_step_atk` chain

#### ★★ How the chain actually advances — a correction to the project's own guide

**`sp_step_atk00` and `sp_step_atk01` have empty `nexts` in every shipped character** (verified on pl000, pl020, pl032 and pl005), and nothing points at `01` or `02` either. **The chain advances on the `AutoCombo` input, not through the combo graph.** Only `02`'s `nexts` matters, and even that is optional — pl020 has none.

The first `HOHO_FOLLOWUP_GUIDE.md` told another dev to wire `00 → 01 → 02`. That was **wrong**; the guide has been revised (both copies on Berg's disk).

`sp_step_atk00` is an **orphan by design** — every character has one, with a `Pad_R_Down` input and no referrer. pl005 keeps it at node **105**. Do not "fix" it. The general orphan diagnostic (list nodes with a non-empty `input_text` that appear in no other node's `nexts`) should return exactly `sp_step_atk00` plus one `RecvEvent` maxout/counter node — 38 of 39 characters have that second one, and pl005's is `atk_gr01`(74). Anything beyond those two is a live exploit. Similarly, `start_*` nodes have **no referrers in any character** — they are reached by the by-name `access_text` jump, not by an edge.

#### The string shape as shipped for pl005

```
00  warp + pin @14
01  lo03 slash, 900/300, COM_sp_Atk_yl, slowmo 1.5, blur LARGE,
    hitstun 52, RushDistanceAjust (2 / 5.0 / 2 / 0.5), handoff @63
02  evo_hi02, 3 hits, blur SMALL, hit_stop 8/8/16, slowmo 1.5
    -> atk_lo03_d01 (pl033) or atk_lo03_u01 (pl027) by elevation, both blur LARGE
```

`sp_step_atk02` also carries `SlowMotionRate (0,60)` at rate **1.5**.

#### `RushDistanceAjust` — the gap-close dial, and the mash-fix trail

*Bug — the `sp_step` warp misbehaved after an over-attack.* Four attempts are recorded, three of them failures:

1. Warp placed inside `sp_step_atk01` — ✗, warps in place.
2. Warp at frame 21 — ✗, broke the move.
3. A late `SoulRebootTiming` window — ✗.
4. **`RushDistanceAjust`** — ✓.

Within the working fix there was still a tuning trail: pl052's aggressive profile `(2, 10, 2, 2)` fixed the over-attack case but **yanked the previously perfect non-over-attack cases**; pl000's `(2, 3.5, 2, 0.5)` fixed the stiffness but under-reached. Shipping value is `(2, **5.0**, 2, 0.5)` — `max_dist` 3.5 → 5.0 with `add_dist` left at 0.5, per Berg's "increase it so it reaches".

Semantics, measured across the roster: long rushes use default 10–14, max 20–40, min 5; close-range moves use default ≈ min ≈ 2–2.2, max 3.5–10, add 0.5–2.

#### The identity trap that makes a step chain stop one hit early

The `sp_step_atk02` enders are `atk_lo03_d01` / `atk_lo03_u01`, and those are exactly the entries that broke on another dev's pl015 build. **An archive entry's name is not what the engine binds on.** A `.tadjpkg` blob carries `'adjb' + <category>\0 + <NODE NAME>\0 + <MOTION NAME>\0 + ...`; a `.tactpkg` blob carries `{"kind":"act_data", "<category>\<MOTION NAME>": {...}}`. The combo node matches the tadj blob's **node name**, and the motion resolves via the tadj blob's **motion name** against the tact blob's **inner JSON key**.

*Bug — the step string and the light string both stopped dead one hit early on pl015.* *Symptom:* no crash, no log, both strings simply ended early; every tool that lists package contents showed correct names. *Real cause:* `atk_lo03_d01` / `atk_lo03_u01` had been built by copying `atk_lo01_d01` / `_u01` and renaming only the **archive entry**, so the inner node and motion names still said `atk_lo01_*`. Those two nodes are the enders of *two different* strings (`sp_step_atk02 →` them and `atk_lo02 →` them), which is why both broke together. *Fix:* four length-preserving `lo01 → lo03` edits to the inner identity strings. Leave `se_name*` strings alone — those are sound-effect assets. The auditor is `Zangetsu Patch/Other devs work/pl015_stepchain_fix.py --check plNNN`, which reports every `attack`/`move` entry whose inner identity disagrees with its own name; it finds **0 mismatches on pl000, pl020, pl032 and stock pl015**, so shipped data is always self-consistent and any hit is the modder's. Regex note that cost a round: the tact inner key holds **one** literal backslash (`1_normal\attack\atk_lo03_d01`), which in a raw Python string is `\\`, not `\\\\`.

---

### `sp_step` / hoho, and the camera-framing root cause

#### ★★ pl005 was in the boss size class

*Symptom:* Berg — "other characters' `sp_step_atk` feel way better framed — does `sp_step` have its own camera motion?"

*Wrong hypothesis:* that `sp_step` carries its own camera motion. It does not. There are **zero** `CameraFixedAngle` / `CameraLookAtChange` blocks on **any** character's `sp_step` entries — surveyed pl000, pl003, pl020, pl027, pl033, pl035, pl052. Camera blocks exist only on `ct_*` cutscene actions.

*Real cause:* the framing difference comes from the camera **preset**, and the preset is chosen by **size class**.

```
Script/CameraParam.fsv rows: playable / medium / large (+ per-character overrides: pl000, en005, ...)
  playable  base_pos 0.5, 0.9, 2    fcs -1.25, 0.85, 0
  medium    base_pos 2,   1.2, 2    fcs -2,    0.4,  0
```

The medium rig sits 1.5 units to the side and focuses lower and further out — it is authored to frame a big enemy. `CharaStatus.def_atk_size` splits the roster exactly **49 (小 = every playable)** against **53 (中 = enemies and bosses)**, and **pl005 shipped 中, the same as sp000**. The same field also feeds the `TARGET_SIZE<=1` / `>=2` conditions on `Warp` blocks, so opponents were additionally warping to him on the big-target branch.

*Fix:* `def_atk_size` 中 → 小, one row each in `CharaStatus.fsv` **and** `CharaStatus_modded.fsv`, same byte length. **These files are UTF-8, not cp932** (小 = `e5 b0 8f`, 中 = `e4 b8 ad`) — check encoding before editing, because cp932 is used elsewhere in the project. Backups: `Script/CharaStatus*.fsv.presize_bak`. Only the base form was wrong; the evo and rev columns already matched the playable convention (中 / 大). Note that `status_patch.py`'s KEEP list describes `def_atk_size` as "his identity" — **that judgement is superseded.**

#### `SoulRebootTiming` and `JustAvoidTiming`

* **`SoulRebootTiming` (SRT)** is the hoho / `sp_step` follow-up window **on attacks**. It must sit on the node **the player is actually in** — `atk_hi03` needed it on the ender `atk_hi03_1`, not on `atk_hi03`.
* **`JustAvoidTiming`** is the perfect-hoho window and lives on **`syunpo_in_act` only**.
* A **`ComboStart` window with `/0`** is what opens by-name special chains.

pl005's SRT sources: `hi01 (24,44)`, `hi02 (46,90)`, `hi03 (25,60)`, `hi03_1 (31,64)`, **`da01 (22,40)`**, over-attack ×4 `(40,82)`. Slow-motion rates across the same set: hi02 1.5, hi03 and hi03_1 1.20, `sp_step_atk01` 1.5, `sp_step_atk02` 1.5, `u01` 1.15.

#### Routing the dash attack into `sp_step` (pass 11)

`atk_da01`'s `ComboStart (22,28)/1` became `(22,28)/**0**`, plus a new `(47,47)/1` reset — this is the `atk_hi01` recipe — plus **`SoulRebootTiming (22,40)`**. In the tcmb, `atk_da01` gained `atk_syunpo_short_cut = 1`.

Related, worth checking before debugging a string that "refuses to end": **every shipped character with `atk_syunpo_short_cut` on `atk_hi02` also has `hit_combo_stop = 1` and `guard_combo_stop = 1` there.**

#### Perfect hoho — "looks perfect" (Berg, pass 10)

| Piece | Donor |
|---|---|
| just-avoid window (`syunpo_in_act`) | authored — f0 30, `JustAvoidTiming (0,14)` |
| cutscene pose / body (`ct_ct_syunpo_out_just` act) | pl035 Halibel |
| cutscene camera + timeline (demo) | pl052 Yhwach, retargeted |
| counter swing (`move_syunpo_out_just`) | pl035 Halibel |

Demo recipe: decode `_demo_csv`, replace **all** `plNNN` → `pl005`, re-cipher, rename the `_demo_cam` entry. The camera fine-tune dial, if needed, is the `evt`-row pos/rot in `_demo_csv`.

#### Supporting vocabulary

`Attack_Melee` key/values: `fix_time` = hitstun, `guard_fix_time` = blockstun, `hit_stop_time` = contact freeze. `hit_shake_blur` tiers are `MINIMUM / SMALL / MEDIUM / LARGE / BIGLARGE / OVERATK / KIKONIMPACT` — there is **no "HIGH"**; Berg's "high" means `LARGE`. `SlowMotionRate` is the actor's animation rate, `WorldSpeedChange` is the world's, and `RushDistanceAjust` is the gap-close.

Character ids used throughout: Ichigo = pl000, Uryū = pl003, pl020, Kenpachi = pl027, Starrk = pl033, Halibel = pl035, Yhwach = pl052.

#### Pass 11 state — committed and hash-verified (2026-07-26)

```
pl005.tadjpkg  448e9b28      pl005.tcmbpkg  be3b7e96      pl005.tactpkg  3ba26cc7
CharaStatus.fsv  8b6819c5    CharaStatus_modded.fsv  b2ae937c
Demo/pl005_ct_syunpo_out_just.tdemopkg  bef0fb0d
Cloud: /tmp/zang/pl005_spstep11.*, build_spstep_v11.py
```

*Open:* the `u01` (Kenpachi) branch is unverified; the `lo` pair has no SRT pending the lo rework; `2_evo` parity for the whole string is outstanding.

*Process note:* verify staged files with `sha256` via `device_bash` before trusting them — staging staleness has bitten.

---

### Homing and tracking

**Vertical tracking is `HeightHoming`.** pl005 had 40 blocks but **none on his bread-and-butter string** — all 40 were donor-inherited, sitting on grabs, over-attacks and steps at coarse angles (20 / 30 / 90). Fixed 2026-08-07 by `Zangetsu Patch/pl005_tracking.py` (`--dry` / `--revert` / `--show`; appends only; 19 blocks across 17 entries). Base melee coverage went **34% → 76%** against a roster average of 61%.

#### The block, and the field that was missed

```
HomingAngle   IsModelRotate   ModelRotate_StartFrame   ModelRotate_EndFrame
```

**The block also has its own active window in the block's own `f[start..end]`, and *that* is what does the tracking.** `ModelRotate_*Frame` is a separate sub-dial governing when the model visually pitches. This is easy to miss and **it was missed on the first pass of the brief**.

Across 581 polled blocks (all playables; reserved slots pl028 / pl030 / pl034 / pl040 / pl041 excluded): `IsModelRotate = 1` in **562/581**, and `ModelRotate_End == Start` in **566/581**, i.e. a single frame. **563 of 930 base-form melee actions carry the block = 61%.**

#### ★★ 3.0 is a false mode — poll per action name

The global "`3.0` × 212" figure is **inflated by the over-attack family**, where 33 characters sit at exactly 3.0. Polled per action name, the normal string votes **5.0 every time**: lo01 5×12, lo02 5×11, lo03 5×5, hi01 5×15, hi02 5×10, hi03 5×16, da01 5×9. **Default to 5.0, not 3.0.**

pl000's own values were copied where they exist, per Berg's instruction: lo01 **1.0**, lo02 3.0, hi01 3.0, hi02 **2.0 with rot 0**, hi03 5.0, da01 4.0, sp_atk01 4.0. ⚠ **pl000 is a timid reference on two rows** — `1.0` appears **three times in the entire game and all three are pl000's**, while the roster mode for lo01 is 5.0 (12/25) and for hi02 is 5.0 (10/23).

#### Frames must be re-derived, never copied

A ported character's actions come from many different donors, so hitbox frames do not line up with the reference character's. Take pl000's **offset** (`hit1 − ModelRotate_Start`) and apply it to the target's own first `Attack_Melee`. pl000's offsets are **4, 3, 11, 7, 10, 6** — in every case the rotate lands in the wind-up.

#### Where the roster deliberately does not track

* **The light-string finisher.** Coverage falls lo01 64% → lo02 51% → lo03 **36%**: the game stops homing on the ender. pl000 has none on `atk_lo03`. Hence `INCLUDE_LO03 = False`.
* **Directional variants** (`atk_lo01_d/_u/_d01/_u01`, `atk_lo03_d01/_u01`): **6 of 84 = 7%**. The paired test settles it — **18 characters carry homing on the parent and not on the variant, against 2 that carry both.** pl009 and pl015 are the only other owners and are 0/8.
* Rejected on evidence, using the rule "same-name coverage ≥ 50% and n ≥ 5": `rev_atk_da01` 0/6, `rev_atk_gr02` 0/7, `rev_sp_atk02` 1/4, `evo_atk_gr02` 2/33, `evo_sp_atk02` 6/13.
* Grabs are written but switched off (`INCLUDE_GRABS`) — grab reach is a balance question, not a feel question.

#### ★★ `atk_hi02` is the canonical `IsModelRotate = 0`

That single action supplies **9 of the 19 zeros in the entire roster** (on `atk_hi02` alone the split is 1×16 against 0×9). It is not an accident: pitching the model while its forward root push runs would drive the character through the floor. **Follow pl000 here, against the 97% rule.**

#### ★★ Measure root motion before copying a `move_rate`

*Bug — pl005's `atk_hi02` last hit dropped short.* *Symptom:* the final hit of hi02 whiffed. *Wrong fix considered:* copy pl000's shipped `MotionMoveRate 2.000000` over `f30..45` verbatim, since pl005 had **no `MotionMoveRate` at all** there. *Real cause and why the obvious fix was wrong:* the two clips travel by very different amounts. Read out of the clips with `tmo_lib` (root node 0, hash `99dc9c9c`, Z axis) over f30..45:

```
pl000_atk_hi02  0.329 -> 0.642   raw +0.313   x2.00 = +0.626
sp000_atk_hi02  0.649 -> 1.618   raw +0.969   x1.00 = +0.969   <- pl005 ALREADY 3.1x the raw travel
```

pl005's clip already travels 3.1× pl000's raw distance, so 2.0 would have massively overshot. *Fix:* shipped **`MotionMoveRate 1.250000` over `f30..45`** — which is also the commonest speed-up in the game (30 of the 87 rates above 1.0; the next most common is 2.0 at 17). Dials are `HI02_RATE` / `HI02_SPAN`; for reference 1.5 gives +1.454 and 2.0 gives +1.938. The window was verified against pl005's own clip: the root advances across exactly f30..45 then plateaus (1.653 by f60); its second hitbox is f40..42 and `ComboStart` is f46.

⚠ **Do not use `ObjectSpeedChange` for this** — it is root motion too, and its dominant shipped value of 0.001 **plants** the character.

#### ⚠ pl005 tadj padding gotcha

**117 of pl005's 229 entries do not match `tadj_lib.build_padded()`** — their 16-byte tail holds tool junk rather than NULs. They match **`build()`** byte-for-byte, so the block model is exact. When checking round-trip on untouched entries, assert `build(d) == blob`, **not** `build_padded`.

#### Also carried in the tracking notes

Two further bodies of measured data live in `roster-add-tracking.md` and belong to the attack-tuning sections, but the headline numbers are recorded here so they are not lost. **Combo/cancel window norms** (114 shipped `atk_lo01/02/03` polled): `CancelTiming` end `-1` "never closes" in 123/134 — **`-1` is the norm, do not "fix" it**; two `ComboStart` blocks per action in 132/136; first `ComboStart` length 6f ×94 / 8f ×24 / 10f ×13; first `ComboStart` start at `lasthit_end +2` ×52 / `+4` ×35 / `+0` ×12; `AfterComboReset` `('0','1')` in 111/111 two-block actions. pl005 ran **22 frames** on lo01 and lo03, outside the entire shipped range, and that one number explained both of Berg's symptoms; fixed to length **6** at `lasthit_end + 2`. **`扇` (fan) collision semantics**: `coll_angle` is an angular **spread**, not a size — 26 distinct values, all round degree counts, including **360 ×145** — so **never scale it**; `coll_radius` (reach) and `coll_height` (vertical extent) are independent; a fan's apex sits at `coll_pos`, so radius alone buys reach, unlike a sphere which is centred on `coll_pos`.

---

### Movement-adjacent cancel bugs

These two are recorded under tracking but are movement bugs in substance — both are about getting out of an action early by moving.

#### ★★★ The lo03 walk-cancel infinite — an orphaned node with a *button* input

**This bug class has now cost multiple passes twice. Check it first.**

*Symptom:* Berg — "I can hold my joystick to the left or right and then press lo01 after lo03 and it comes out earlier than it should… infinite and plus on block… **if I just spam the lo button it works right**."

*Wrong hypotheses:* two earlier passes chased **timing** — `SlowMotionRate`, then `ComboStart` length. Both failed, because the exploit never went through the timed path at all.

*The tell:* that it needs a **held direction**. A held direction runs the *directional variants* `atk_lo01_u` (52) / `atk_lo01_d` (78), not plain `atk_lo01` (0).

*Real cause:* **nothing in pl005 referenced 52 or 78.** An unreferenced node that has an input is gated by nothing, so any open combo window anywhere in the moveset fires it — bypassing lo03's `ComboStart` entirely. Plain light was fine precisely because `atk_lo01`(0) *is* referenced (`<- 14`).

*Fix (`pl005_graph_orphans.py`): re-parent, do not delete.* `atk_lo01_u/_d` exist only on pl009 and pl015, and both wire them at the same node id — `start_lo`(14) → `["78","52"]`. pl005's `start_lo` was `["6","0"]`. **Append, never replace** — pl009 and pl015 reach their plain lo01 by another route, so copying them literally would delete pl005's dash attack and his whole light string from neutral. Result: **`["6","0","78","52"]`**.

*Same class, found in the same sweep:* **`start_sp_atk`(17) was empty** in pl005 (pl000 `["108","20"]`, pl001 `["96","20"]`, pl009 `["20"]`), leaving `sp_atk01`(20) an orphan — SP1 castable from anywhere. Wired to `["20"]`.

*General rule:* if a cancel or link happens **earlier than any window allows**, stop tuning frames and go looking for an orphan.

#### ★★ `SlowMotionRate` on an attack makes authored frames ≠ real frames

*Symptom:* Berg — "I can ever so slightly move forward to cancel lo03's recovery and link into another lo string… spamming the lo button works right." He had already correctly ruled out `fix_time` and `guard_fix_time`.

*Real cause:* `atk_lo03` carried **`SlowMotionRate rate 2.0` over f0..63** — a double-speed action clock.

```
              hitbox ends      CancelTiming opens     REAL gap
atk_lo01      f11              f38                    27
atk_lo02      f15              f45                    30
atk_lo03      f36 -> real 18   f63 -> real 31.5       13.5   <- 6.5 below the roster MINIMUM
```

Walking is simply the first thing available once `CancelTiming` opens, so a half-length recovery means micro-walk out, restart the string, infinite.

**Authored tadj frames *are* clip frames** — proven 3/3 on pl005's lights (clips of 80 / 100 / 110 frames against highest authored events of 79.6 / 80.3 / 103.9). One clock drives both animation and events, so a rate multiplier desynchronises authored from real and **the real gap must be computed by hand**.

**0 of 115 shipped playable lights carry `SlowMotionRate`.** The widest sweep (444 actions ending in `atk_lo01/02/03` across every `.tadjpkg`) finds 17, of which **15 are `en0NN` boss/NPC packages** and the other 2 are pl005's own. ⚠ **It is not donor residue** — `sp000`'s own `atk_lo01_u01`, which is lo03's clip source, has none. An earlier pl005 build added it, predating all the SP2 work.

*Shipped precedent for the fix:* **pl036 `atk_lo03_u01`** has the same shunpo shape (`Visible` f6..22, `Warp` f18, hitbox f32..34) with `SlowMotionRate 2.0` over **f0..8 only**, so its real gap equals its authored gap.

*Fix (`pl005_lo03_recovery.py`, dial `SMR_END`):* window `f0..63 → f0..36`, rate untouched. **One byte.** Startup, active frames and shunpo are unchanged to the frame; the real gap goes **13.5 → 27.0**, exactly lo01's value. ⚠ Halving the frames instead (deleting the multiplier and retiming) would fire the blade at clip frame 17 of 110 — **mid-shunpo** — and would need a `tmo_lib` re-bake. Don't.

Roster poll of `CancelTiming.start − last_hitbox_end` (n=110, bare `pl0NN`): min 20, **median 28**, mean 28.2, max 36, 10th–90th percentile **23..32**. **`CancelTiming` has no cancel-property flag** — its field set is `mind_leep` alone in **146/146** shipped light blocks. Cancellability is purely timing.

*Related, and not a bug:* **pl005's `atk_lo03` f34 startup is a shunpo, not a defect** — the entry carries `Visible f12..26` plus `Warp f13` (`pos 0,0,-1`, target-relative): vanish at f12, warp behind, reappear f26, strike f34. Only one other light in the game has a `Warp` (pl020's lo03, which strikes at f14). Retiming it is a clip-level `tmo_lib` re-bake touching **22 of its 35 blocks** plus the tactpkg `end_frame` — not a tuning edit.

---

### Verification hygiene: two failures that cost passes

#### ⚠⚠ Before diagnosing "the fix didn't work", verify the fix is in the live file

*Symptom:* on 2026-08-08 Berg tested **two rounds of lo03 fixes that were never in his build**, and both parties concluded the diagnosis was wrong when the diagnosis was fine. *Real cause:* a `--revert` on an **early** script restores a backup that predates every **later** pass — **one revert silently rolled back four passes** (tracking, reach_links, lo03_recovery). Live turned out to be `pretrack_bak` plus exactly three hand edits. *Diagnostic that found it in one command:* md5 the live file against every `*_bak`, then per-entry diff against the closest match. It printed exactly `lo03 fix_time 24→26`, `guard_fix_time 20→22`, `sp_atk02_2 fighting_base 0.15→0.12` — Berg's own hand edits and nothing else. *Fix:* re-apply by **archiving the stale backups first** (`mv x_bak x_bak.stale<date>`) so each script snapshots the current hand-tuned live file. All three of Berg's edits survived the re-run.

#### ⚠⚠ The two tadjpkg copies diverge

*Symptom:* pl005's hi02 hitbox ended up far larger than intended. *Real cause:* `pl005.tadjpkg` was reverted but **`pl005_modded.tadjpkg` was not**, and Berg's hand edits only ever existed in the main file. Archiving the modded backup removed `pl005_reach_links.py`'s anti-compounding guard, so hi02 was scaled **twice** — `coll_radius` 2.0 → 2.4 → **2.88**, effect `scl` 1.2 → **1.44**. *Fix:* corrected surgically. **Always check both copies after any revert, and re-verify scale-type edits for compounding whenever a backup has been moved.** For reference the intended hi02 edit was first-hit only, +20%: effect `scl` 1.0 → 1.2, `coll_radius` 2.0 → 2.4, `coll_height` 2.0 → 2.4, with angle and `coll_pos` untouched and the second hit at f40 untouched; measured margin over hi01's max range went **+0.10 → +0.50** units, and 2.4 is the commonest fan radius in the game (420 blocks).

---

### The EX move: `atk_ex01`

Built 2026-07-27 at ~02:21 and confirmed by Berg the same day — "works fine", visuals "it's done". The session that built it was archived and lost; everything below was **reconstructed by diffing the live files against the `.preex*_bak` chain**, so it is recovered evidence rather than a contemporaneous log.

`atk_ex01` is a **projectile** — an `Attack_Bullet`, not an `Attack_Melee` — on input **Pad_R_Right**. It is a three-file build:

| Layer | Source | Detail |
|---|---|---|
| tcmb node `atk_ex01` | authored | `_uniqueID` **79** — the id `start_ex` already pointed at, per the canonical-id rule. `nexts: 33` (= `atk_hi_chain`). Variables all 0 except `combo_route_id` = 4 |
| tadj `1_normal_attack_atk_ex01` | **pl000 `sp_atk01_2`** | the Getsuga-class bullet, retimed and identity-scrubbed |
| tact act + clip | **pl016 Yamamoto** `pl016_atk_lo03_u01` | the only clip added; `act_data` body points at that tmo |

`combo_route_id` non-zero appears on **6 nodes roster-wide, all on ported slots** (pl005, pl009, pl015, pl030). It is **donor residue, not design** — read no meaning into the 4.

Entry wiring: `start_ex -> 79` now resolves, **and** `atk_hi01` / `atk_hi02` gained `79` at the end of their `nexts` (`102, 103, 70, 33, **79**`), so EX is also a chain ender off the high string.

#### Version trail (all on the tadj blob; tcmb and tact unchanged after 01:44)

* **v2**, 01:37 — verbatim pl000 clone, 31 blocks. Bullet at f45, `ComboStart` / `Cancel` at 60, `Effect_Loop` 1–45 and 45–70. Donor identity still present: `pl000_sp_atk01_2_charge`, `pl000_sp_atk01_2_vo`, `pl000_ktn_ex_last_big`, `plcom_sp_atk_fx`.
* **v3**, 01:56 — retimed: bullet at **f34**, `ComboStart` / `Cancel` / `ReverseLimit` at **88**, `Effect_Loop` 1–34 and 34–60. Identity scrubbed to `act_com_overatk`, **`sp000_sp_atk01_vo`** (his own voice), `act_com_last_swing`. Added `SlowMotionRate (0,70)` at 0.8.
* **v4**, 02:02 — `SlowMotionRate` 0.8 → **1.5**.
* **Current**, 02:21, 31 blocks — `SlowMotionRate` → **1.2**; `ObjectSpeedChange` speed 0.001 → **1.0**; **removed** the `plcom_sp_atk_fx` SE, `ReverseLimit` and `OffReverse`; **added** `SoulRebootTiming (40,88)` plus a second `ComboStart (40,88)/0` — the hoho / `sp_step` follow-up recipe. Dropping `OffReverse` / `ReverseLimit` is the matching half of that recipe.

#### Live hashes (sha256 head, 2026-07-27)

```
pl005.tadjpkg  f4037664e10c29ad   (== pl005_modded.tadjpkg, identical)
pl005.tcmbpkg  115fd390a73d8dfb
pl005.tactpkg  491c0984b513460a
backup chain:  .preex_bak -> .preexv2_bak -> .preexv3_bak -> .preexv4_bak -> live
```

#### Bullet parameters (`Attack_Bullet`, inherited from pl000 unless noted)

damage **1000** (+bomb 500), `guard_damage` 90, `damage_guarantee` 600, `base_damage_rate` 0.6, `atk_strength` 3, `hit_shake_blur` **LARGE**, `fix_time` 30 / `guard_fix_time` 22, `hit_stop_time` 14, `fire_offset_pos` `0,1.5,1.5`, `fire_shot_speed` `0,0,0.5`, `limit_distance` **5.0**, `collision_size` `0.85,7,2`, `use_homing` 0, `use_bomb` 0, `bind_se` `sp000_sp_break00`.

#### ★ Resolved risk — spfx resolve globally by name

*Recorded risk:* effects live in `00HIGH/Effect/spfx/<owner>/`, and **`P000_ss1_00.vfxb` is in `pl000/`**. Zangetsu's own folder, `00HIGH/Effect/spfx/en/sp000/`, contains exactly **one** file, `sp000_sp_break00.vfxb`. Every other effect in pl005's entire tadj is a shared `COM_*` asset (`COM_sp_Atk_yl`, `COM_tm_AtkLow00`, `COM_tm_Ignition01`, `COM_sp_HitStrike_00`, `COM_sp_SmokeMove_00`, `COM_sp_SmokeStomp_00`, `COM_tm_AtkDistortion`), so `P000_ss1_00` is the **only foreign-character effect he references**. The open question was whether spfx are loaded globally by name or preloaded per character — if the latter, the bullet would be invisible while still landing. Effect names are **not literals in `filename.bin`**, so the two-table audit does not apply here.

*Resolution:* `P000_ss1_00` **loads fine from pl000's folder**, so **spfx resolve globally by name and are not preloaded per character**. That is reusable: **any character can reference any `P0NN_*` effect.** The standing "no donor VFX, identity stays Zangetsu's" rule is therefore a **judgement call per move, not a technical constraint** — here Berg chose to keep Ichigo's Getsuga.

#### Collateral from the same lost session

The `pl005.tactpkg` backup chain shows that between 23:09 and 23:56 the build **dropped 5 acts** (`1_normal_damage_blown_dam_blown_*`, the enemy-only knockdown chain), then the current build has them back plus `atk_ex01`. Net: **84 acts / 89 clips**. Recovery-bug videos (pl000 versus pl005 side by side) are in `Zangetsu Patch/Recovery_bug/`.

---

### The `tmo1` animation format

**The animation format is cracked.** `Tmo(blob).build() == blob` on **15,909 / 15,909** blobs — all 10,666 clips in `Motion/*.tactpkg` plus all 5,243 in `Demo/*.tdemopkg` under 6 MB — with **zero exceptions**. Library: `Zangetsu Patch/tmo_lib.py` (`info` / `dump` / `verify`). Team write-up: `Zangetsu Patch/ANIMATION_FORMAT.md`.

`_demo_cam` and `_demo_mot` are **nested actpkg archives**, one `tmo1` per rig part (`<name>`, `_hd`, `_hr`, `_wp00`, `_obj_a`, …). Use `actpkg.py` for every enclosing layer.

#### Container layout

```
+0x00 'tmo1'  +0x04 u32 hdrsize (0x10 char / 0x60 camera)
+0x08 u16 ver=1  +0x0A u16 flags (0=character, 0x10=camera)
bank at hdrsize, 12 u32:
  [0]=1 [1]=off_info [2..5]=0 [6]=off_names [7]=track_count
  [8]=off_tracks [9]=key_count [10]=off_keys(0 if none) [11]=0
off_info   -> u16 frame_count; u16 node_count     (track_count == node_count*9)
off_names  -> node_count x u32 name hash
off_tracks -> track_count x {u32 first_key; u32 count; u32 max(last_frame,0)}
off_keys   -> key_count   x {i16 frame; u16 flags; f32 value}
```

Sections run names → info → tracks → keys, 16-byte aligned, with the keys running to EOF. The whole layout is implied by `(node_count, key_count)`. There is **no checksum**, everything is variable-size, and it rebuilds cleanly.

#### Node and channel ordering

**Nine channels per node, in fixed order: 0–2 translate XYZ, 3–5 rotate XYZ, 6–8 scale XYZ**, hence `track_count == node_count * 9`. Node order is the order of the name-hash array. The `i16 frame` field is **signed** — pre-roll keys at frame −20 exist in shipped data.

#### ★ Interpolation is hold-previous, and the data is a lossless RLE of a per-frame bake

Across **8,220,138** consecutive key pairs, **not one repeats a value**. Testing hold-previous against ground truth gives a **0.00004° aim error**; linear interpolation gives **1.74°**. The consequence is the important one: **write one key per frame and every interpolation rule reproduces the animation exactly.** There is nothing lossy to preserve.

#### Measured conventions

* **Translation is in metres and is ADDITIVE on the model's rest translation.** Treating it as absolute puts the character 1.03 m underground; additive puts the toes at y = +0.015.
* **Rotation is in radians with `R = Rz·Ry·Rx`, i.e. Blender's default XYZ Euler.** Across 60 cameras, XYZ gives 0.0069° mean / 0.032° max error; every other order gives 14–26°.
* **Node names are an engine length-seeded CRC-32** — the same hash as `file_exist.htable` (`fnames_patch.build_crc`). The hash is **one-way**, so you need a name dictionary or you work in hash space.
* **Cameras are 3 nodes all named `came`**: node 0 is the camera (which looks down **−Z**), node 1 is the aim target, node 2 is an unidentified scalar.

#### Validation

`pl005_ct_sp_break01_maxout`'s camera reconstructs as a smooth dolly-in from (−0.83, 1.43, 4.17) m at 4.3 cm/frame, with acceleration 15× below the step size. `sp000_run_f` reconstructs to a textbook run cycle — feet planted at 0.015 and lifted to 0.10, head bob 1.547–1.590, feet in antiphase at ±0.45, and in place.

#### ★★ The joint table, and the Blender add-on

`Zablender` — `Zangetsu Patch/blender/io_bros_anim.py` — is a single stdlib-only file with a README, doing both import and export. Self-test: `python io_bros_anim.py selftest "<gamedir>"` → **31/31 pass**.

The skeleton hierarchy and rest pose are **not in the animation**. They live in `00HIGH/Model/chara/*.tmd2` (PZZE → `tmd0`), and the joint table sits **past** that model's 16-offset / 16-count bank:

```
+0xAC u32 joint table offset (stride 24)   +0xBC u32 joint count
+0xA8 u32 bind matrices (stride 64, count at +0xB8)
joint := u32 hash ; f32 x,y,z ; i32 parent ; u32 (name_offset << 16)
```

★ That trailing u32's **high half is the joint name's byte offset into the string table** at `0x40` / `0x80` — so **real bone names come straight out of the model and no reverse-hash dictionary is needed**. Verified across **1851/1851** chara `.tmd2`: every table parses, every parent tree is valid (root −1, parents always precede children), and **141826/141826** names hash back via `build_crc`. Body, hair, face and weapon each have their own table; motion nodes resolve by hash — for sp000, 228/228, 115/115, 114/114 and 17/17 respectively.

*Flag:* the tmo note's own "OLD GAP" paragraph and the MEMORY index line ("only the `tmd0` joint table left") are both **stale** — the same file's later section closes that gap.

Sandbox test results: archive + `tmo1` round-trip byte-identical (305 + 953 blobs); the export path (bake → RLE → rebuild) byte-identical including 158 camera blobs; whole-file write-then-reload across 40 packages / 168 entries / 0 diffs; `sp000_run_f` reproduces the documented run-cycle numbers exactly; camera aim error 0.00002° mean.

Two export quirks are handled by `match_source_encoding()`: **camera per-key flags are garbage**, and **some channels' first key is later than frame 0**, with values holding *backwards* from it. Rig mounting: hair and face part rigs are standalone tables with a zero-rest stub chain, mounted via a Child Of constraint on the body's `neck`.

**Untested = the bpy glue only** — Blender cannot run in the sandbox. Most likely first-run fixes, in order: (1) Blender 4.4+ **slotted actions** in `_new_action()`; (2) `keyframe_points.foreach_set("interpolation", …)` int enums; (3) the Child Of identity inverse matrix; (4) the rest-orientation assumption — bones are built along game +Y with roll 0 so the rest matrix is identity, which is what makes pose values map 1:1. That last one **raises a clear error** rather than silently posing wrong, and the exporter handles non-identity rest generically via `R0·basis·R0⁻¹`.

**Non-blocking unknowns:** the per-key `u16` flags (`0x0103` in ~99.9% of character keys, garbage in cameras, so the runtime evidently ignores it — just write `0x0103`); the camera header unit vector at `+0x10`; camera node 2's channel; and fractional-frame interpolation during slow-motion, which is moot if everything is baked per frame.

**Next, if Blender authoring is wanted:** (1) parse the `tmd0` joint table, (2) build the Blender importer (armature from the joint table, tmo tracks as F-curves), (3) the exporter (bake per frame, hash names, emit `tmo1`, repack), (4) a joint-name dictionary by harvesting mesh string tables and hashing forward. **Do the importer first**, so the rest pose and rotation order can be eyeballed before any exporter exists.


---

## Part 5 — SP2, the kikon, and cutscenes

### 1. What the move is

`sp_atk02` — "Schattenmond" — is pl005's second Super. It is bound to **Pad_R_Right**, requires `in_powerup 1`, costs **100** meter, and is neutral-only. It was never authored: it is a two-stage assembly welded out of three donors' animation and one donor's effect bank.

The V1.1 shape, and the shape everything after argues about:

| graph node | id | role | clip source |
|---|---|---|---|
| `start_sp_atk02` | 19 | entry | — |
| `sp_atk02` | 73 | SP2_1, the travel/lunge | `pl039_atk_ex01` (Szayelaporro) |
| `sp_atk02_1` | 80 | SP2_1 hit | `pl039_atk_ex01_1` |
| `sp_atk02_2` | 81 | the burst — 18 shadow waves | `pl052_sp_atk02` (Yhwach) |

The burst blob was **moved, never rebuilt**: all 68 tadj blocks were carried across intact and only three header strings changed. That distinction is load-bearing — `build_sp2.py` (the original construction script) rebuilds the tadj entry from pl052 and destroys every hand-tune since. ⚠ **`build_sp2.py` must never be re-run.** The same applies to `sp2_rim.py`, superseded at V1.2 (it would rewrite the rim back to an invisible colour).

Script inventory, roughly chronological: `build_sp2.py`, `sp2_burst.py`, `restore_sp2_routing.py`, `sp2_fix_act.py`, `sp2_rim.py`, `sp2_v11.py`, `sp2_v12.py`, `sp2_hitconfirm.py`, `sp2_hybrid.py`, `sp2_v14.py`, `sp2_v15_autocombo.py`, `sp2_v16_purple.py`, `sp2_v17.py`, `sp2_v18.py`, `sp2_v19_cast.py`, `sp2_v20_continuity.py`, `sp2_v19_cost.py`, `sp2_v21_killfade.py`, `sp2_v22_redesign.py`, `sp2_v23_fill.py`, `sp2_v24_softparticle.py`, `sp2_v25_restore_look.py`, `sp2_v26_*`, `sp2_planC.py`, `sp2_pureblack.py`, `sp2_v28_pureblack.py`, `sp2_v29_parts.py`, `sp2_v31_body.py`, `sp2_bisect.py`. Demo-side: `demo_cam.py`, `graft_kikon_demo.py`, `add_ct_stub.py`, `try_ct_node.py`, `tune_pass17.py`.

### 2. The four-file model, and the freeze bug that proved it

A playable action in BRoS is four files deep, and the SP2 work found each layer the hard way:

- **`Script/Action/pl005.tcmbpkg`** — the combo graph. Nodes, ids, `input_text`, `nexts` edges.
- **`pl005.tadjpkg`** (and `pl005_modded.tadjpkg`) — the tuning timeline: `Attack_Melee`, `Protect`, `Effect_Loop`, `SlowMotionRate`, `ComboStart`, `CancelTiming`, `BlackOutAtmosphere` blocks, all in **action-local frames**.
- **`Motion/pl005.tactpkg`** — `act_data` entries that bind action → clip, with `start_frame`, `end_frame`, `fusion_frame`, `next_flow`/`next_name`, `play_frame`.
- the nested **`acttmo_pkg`** — the animation clips themselves.

**★★ THE FREEZE BUG — a missing `act_data` entry means the state never ends.**
*Symptom:* cast the move and you are **locked in place; no move works except `overatk`, until an incoming hit ejects you.**
*Diagnosis path:* the tcmb node was correct, the 68-block tadj was correct, and the clip `pl052_sp_atk02` (200 f) was present in the nested `acttmo_pkg`.
*Real cause:* the **5,808-byte `act_data` entry that binds action → clip was missing** from `Motion/pl005.tactpkg` — `build_sp2.py`'s motion half had been lost in the Overlay rollback (§10). With no `act_data`, the state is entered, the tadj timeline runs against no motion, and **no animation ever ends**. `overatk` escapes only because it is a global reverse cancel, not a `nexts` edge.
*Fix:* `sp2_fix_act.py`, which re-adds the entry.
★ **Detection tip:** an added act costs ~5.9 KB. The live `tactpkg` was only **117 B** above dev's — that delta alone was the tell.

⚠ **Retracted alongside it:** the routing theory that `sp_atk02`(73) → `sp_atk_k_chain`(48) was wrong. It is the **majority convention — 14 characters** (including donor pl052) route 73→48, against only **2** on 73→35 (pl000, pl013); `48 → 28` also ships verbatim on pl009/pl021. Node 48 is only entered when the kikon chain actually fires, so it cannot affect a plain cast. Do not re-chase it.

### 3. Version ledger

Every version below either fixed something or taught something. Versions are grouped by what they were solving.

| ver | script | what it changed | what it taught |
|---|---|---|---|
| V1.1 | `sp2_v11.py` | two-stage assembly, 14→18 hits, white effect clone, rim `#2A0A3A` | there is no crumble enum; `add_element 崩し` is the unblockable flag; `my_action` is the hit-confirm mechanism |
| V1.2 | `sp2_v12.py` | knockback fix, purple hunt #1, startup 71 f, `scl` dial | `reishi_blow_power` breaks a multi-hit string; purple had 3 sources, none in `.vfxb` colour paths |
| V1.3 | `sp2_hitconfirm.py`, `sp2_hybrid.py` | deleted `73→80`, split SP2_1 into two actions | a gate queried at `ComboStart` reads *before* the hit resolves |
| V1.4 | `sp2_v14.py` | `end_frame -1 → 114`, rim → white | splitting an action makes a previously unreachable tail reachable |
| V1.5 | `sp2_v15_autocombo.py` | deleted nodes 80 and 81, re-parented 48 onto 73 | an **orphaned `AutoCombo` node is globally eligible** |
| V1.6 | `sp2_v16_purple.py` | BC7 texture whitened, full re-time, damage 4570 | the purple was a block-compressed texture; solve a spec as intervals, not absolute frames |
| V1.7 | `sp2_v17.py` | `TPlt` palettes re-hued, rim `#B026FF`, cancel to f199 | a `.vfxb` `Unit` has **four** colour paths; no block type grants hard recovery — placement is the mechanism |
| V1.8 | `sp2_v18.py` | killed `hit_effect` spawns, split burst at f195 | `Attack_Melee.hit_effect`/`hit_trigger` is a **fifth** spawn path; Uryu's two-action recovery recipe |
| V1.9 | `sp2_v19_cast.py` | cast 18 → 41 blocks | `BlackOutAtmosphere.end == CancelTiming.start`; "timestop" is not a block |
| V2.0 | `sp2_v20_continuity.py` | blackout on every segment, stinger/voice de-duped | a multi-segment SP carries blackout on **every** segment (61/62 chains); the field is `se_name1` |
| V2.1 | `sp2_v19_cost.py` | texture stubbing, per-block windows, `scl.z` 1.8→1.4 | ~82–108 draws per wave, not 1; we were spawning a boss-tier bank like a projectile |
| V2.2 | `sp2_v21_killfade.py` | `end_trigger` → `32:T32_Kill&Fade` | `T31_Unlock` releases an effect, it does not kill it |
| V2.3 | `sp2_v22_redesign.py` | lifetimes halved, `GeIC` 6/8/12→3/4/6, `TDs1/Pow` → 0 | **`Effect_Loop` windows are not particle lifetimes** |
| V2.4 | `sp2_v23_fill.py` | `scl` → .6/.6/1.4, `GeIC` → 2/2/3, `TDs1` deleted, `bSfP` → 0 | **cost is draws × area**; the clean build had *more* draws than the laggy one |
| V2.5 | `sp2_v24_softparticle.py` | `bSfP` restored to 1 | `bSfP` is the wave's *shape*, not an optimisation knob |
| V2.6 | `sp2_v25_restore_look.py` | `TDs1` restored by rebase, `scl` → .740/.740/1.150 | **removing a slot re-purposes a `Ptcl` pass, it does not disable it** |
| V2.7 | `sp2_v26_*` | `Brig` 2.0 → 1.0, `DwSz` aspect held constant | over-1.0 `Brig` + a saturated palette = **hue shift by clamping** |
| Plan C | `sp2_planC.py` | five "unreachable" ramps blackened | `TgUI` reachability is not proof; believe the screen |
| V2.8 | `sp2_pureblack.py`, `sp2_v28_pureblack.py` | 45 textures × 2 tiers, zero tinted | **`Tbl` is the texture binding index**; pure black is encodable where desaturation is not |
| V2.9 | `sp2_v29_parts.py` | `GeIC` 6/8/12 → 4/5/8 (26 → 17 parts) | the quad's plane is `x × y`; cost = `parts × scl.x × scl.y` |
| V3.1–V3.8 | `sp2_v31_body.py`, `sp2_bisect.py` | the measured build; **shipped 2026-08-09** | the whole earlier fill model was fitting the test protocol, not the builds |

### 4. Timing, damage and the hit schedule

**Acceleration could not be done with `hit_wait`.** `hit_wait` is structurally one constant between repeats of a *single* block, so it cannot express a decaying gap. A `SlowMotionRate` ramp is the wrong axis: tadj frames are **action** frames, so slowing them slows animation and effects together and leaves the *spacing* identical. The only mechanism is per-hit frame placement. V1.1's first schedule, 14 → **18 hits**:

```
hit    1   2   3   4   5   6 ...18
frame  20  40  55  66  74  79 ... 139   (gaps 20,15,11,8,5,5...)
```

The acceleration *curve* was later lifted verbatim from **pl002** — Dangai Ichigo, resolved properly through `CharaNameTextID.csv` → `Text/CommonText.cat` (pl000 "Ichigo Kurosaki", pl001 "(Bankai)", **pl002 "(Final Getsugatensho)"**, pl051 "(TYBW)"; corroborated because pl002 is the only Ichigo with no `2_evo_*` entries). His `sp_step_atk02` gaps are `14 16 12 8 6 2 2 2 1 1 1 1 1 1` then **10** into the launcher — it *slows* (14→16) before accelerating, then falls off a cliff. Block spans are `3 / min(2,gap) / 3`.

**★ SP2_2's startup is 71 frames**, measured two independent ways: Yhwach's own first `Attack_Melee` on that clip is f71, and the 25-block Afterimage trail ends f72. V1.1 fired its first hit at **f20**, i.e. 51 frames *into* the wind-up. Later, "the hand's motion" was measured directly: baking `pl052_sp_atk02` with `tmo_lib` and summing |Δ| over all 123 keyed nodes puts per-frame energy at **9.20 on f70**, the highest in the whole 200-frame clip. The wave leaves at **f71**.

V1.6's schedule (18 hits, pl002 shape × 1.2): `89 106 125 139 149 156 158 160 162 163 164 165 166 167 168 169 170` + **185 launcher**. Body `fix_time` 60 → **90**; h18 stays 60. **Damage total 4570** = 17×250 + 320. ⚠ The earlier "raw damage 2140 → 2700" figure is superseded.

V1.8 then found that **hitboxes lagged the visual by `BURST_LEAD`**: at lead 18, each wave spawned 18 action frames before its own hitbox, and *that gap was the lag players felt*. `BURST_DELAY`/`BURST_LEAD` were moved **18 → 5 in lockstep** so `wave_i = 71 + cumgap_i` stayed pinned — waves at 71/88/107/121/131/138/144/147/150/167, with h01 still alone for 17 frames (Berg's requested "singular wave"). Travel was video-measured: stage luminance 60.2 → 44.8 over video f205 → f210, so the wave crosses in **3–4 real frames**; 5 action frames at the 1.5 rate is 3.33 real. Final hits: `76 93 112 126 136 143 145 147 149 150 151 152 153 154 155 156 157` + **172**. Damage 4570 kept.

**★ Solve a spec as intervals, not absolute frames.** Berg's feedback arrives as global video frames; converting them via `real = action / slow_motion_rate` and matching *intervals* is immune to the unknowns (how much `hit_stop_time` lands on the attacker's clock, how `fusion_frame` is charged). Errors came out ≤2.9 real frames across all four of his windows.

**Slow-motion population.** Across 33 playables / 160 blocks (reserved slots excluded) the **minimum shipped `SlowMotionRate` is 0.200**; `0.5` is the workhorse (54/160) and the only sub-1.0 rate ever used for a long window. V1.1's `0.1` for f0–12 and the burst's `0.1` for f0–71 were both below anything shipped. The burst went `0.1 → 0.5` (precedent: pl020 `rev_sp_step_atk03`, a 70-frame window at 0.5), travel `0.1 → 0.45` (pl022 `evo_atk_ex04`, same length) — wind-up **11.83 s → 2.37 s**. V1.4 raised the burst to **0.8** on "too fast" (between pl007 `sp_step_atk02`'s 0.75 and 1.0; wind-up 71 f ≈ 1.48 s). ⚠ **Berg hand-edited it to 1.200 himself** between V1.4 and V1.6 — the `.bak` at 00:49 holds our 0.8, live held 1.2. **Preserved, not reverted**, per house rule 1.

**★ There is no animation-freeze block.** All **7811** shipped `act_data` have `play_frame = 1.000000`. `ObjectSpeedChange` is **root motion** (dominant value 0.001, ×574 = a planted character), not a time dial. The only true freeze is `is_loop = 1` over a 1-frame window (`sp_break01_loop`, start 100 / end 101, on every playable) — but a looping action has no self-terminating end and would need a new exit edge, so it was rejected as a lock risk. The shipped floor, `0.2`, was used instead.

Other tuning constants that were resolved from population rather than taste: `MotionMoveRate.move_rate` 0.5 → 1.3 (shipped 10×, range 0.0–7.0) → **1.5** (shipped 47×); `hit_shake_blur` tiers are **MINIMUM < SMALL < MEDIUM < LARGE < BIGLARGE < KIKONIMPACT**.

### 5. Routing and graph: four bugs from two mechanisms

**★★ There is no crumble enum.** The game has exactly **four** `damage_action` values. The collapse-in-place look was assembled as のけぞり大 + `blow_power 無し` + `damage_move_rate 0.0` + `fix_time 90`.

**★★ `add_element 崩し` is the guard-break/unblockable property** — it appears on every `atk_gr01`. Setting it to `無し` also required deleting its two tells: `Effect_OneShot COM_tm_EnemyFlash00` and `SE_OneShot act_com_cantguard`. ⚠ Consequence on the watch list: SP2_1's travel hitbox now does 0 damage and is dead weight.

**★★ Hit confirm is `Attack_Melee.my_action` + `my_action_timing = 当たった瞬間`.** This is how all **98** shipped `atk_gr01 → atk_gr02` chains work, and it **needs no `nexts` edge** — pl000 has no `atk_gr02` node at all. It does not fire on block or whiff. ★ Only `当たった瞬間` is proven; the other enum `アクション終了時` has an **empty `my_action` in all 16 shipped instances** and was never observed driving a transition. ⚠ `my_guarded_action` was left EMPTY (only **8 / 5970** shipped `Attack_Melee` set it), so a *blocked* SP2 stops after the travel — one field if that turns out wrong.

**★★★ Bug: the auto-cast. A gate queried at `ComboStart` reads *before* the hit resolves.**
*Symptom:* "SP2 starts blasting if I miss an attack or I'm put in recovery; auto-casts and I'm stuck in a loop."
*Wrong hypothesis:* that the gate fields were missing. Node 80 **already had** `hit_combo_stop = guard_combo_stop = 1` (the tcmb's own Japanese header: 通常ヒットで派生 / ガードヒットで派生).
*Real cause:* `sp_atk02`'s `ComboStart` opens at **f20 — the same frame its only `Attack_Melee` (f20..22) goes live.** The `AutoCombo` edge is taken before contact can resolve, so both stops read "no outcome" and pass. ⚠ `is_before_hit = 1` is the same query at the same moment — **gating cannot fix this.**
*Fix:* delete the `nexts` edge and let the `my_action` latch be the only path in. `73`'s `Attack_Melee` f20..22 took `my_action = sp_atk02_1`.
★ **This mechanism has now bitten three times** — see also `whiff_fix.py` v4 (a buffered R2 during startup enters the pair pre-resolution) and `byakuya_petal_form.py` (the same query reading false on a kill). **If a conditional branch fires when it shouldn't, check whether its frame equals the hitbox frame.**
★ It was **not a graph cycle** — the whole table from node 19, including the by-name `jump_X → start_X` hop, has zero cycles. The "loop" *feel* was `SlowMotionRate 0.1 × 71 f` under `BlackOutAtmosphere 0..190` = **~11.8 s of blacked-out, uninterruptible near-freeze**.

**★★★ Bug: the whiff loop — an *orphaned* `AutoCombo` node is globally eligible.**
*Symptom:* "I don't mean when missing the `sp_atk02`, I meant missing **ANY** move. If I miss a hi attack, I enter a loop of casting the sp_atk."
*Real cause:* V1.3's fix deleted the `73 → 80` edge but left node 80 with `input_text = "AutoCombo"` and nothing referencing it. `AutoCombo` means no button is needed, so with no predecessor gating it, **any `ComboStart` anywhere in the moveset** finds it eligible and fires it — then it re-arms. The latch half of V1.3 was right; deleting the edge was not.
*Population proof* (42 playables, reserved slots and pl005 excluded):

```
my_action targets in the whole game        78
  ... with NO tcmb node at all             73  (94%)   <- the norm
  ... with a node                           5
      input_text AutoCombo                  4
      ORPHANED AutoCombo                    0   <- ZERO. Nowhere in the game.
```

*Fix:* **delete the nodes; do not re-add the edge and do not gate it.** `sp_atk02_1`(80) and `sp_atk02_2`(81) were deleted (65 → 63 nodes) — a latch target needs no node. Deleting 81 would have orphaned `sp_atk_k_chain`(48), so 48 was re-parented onto **node 73 (`sp_atk02`, `Pad_R_Right`) → 48, the 15-character majority** (pl001/008/012/014/018/023/026/031/033/038/039/052…); `sp_atk02_1 AutoCombo → 48` is only 4 characters and `sp_atk02_2 AutoCombo → 48` only 1. ⚠ **`73 → 48` is not the edge V1.3 deleted** (that was `73 → 80`, into the attack itself); 48 is the kikon chain and cannot cast the move. ⚠ `sp_atk01_1`(88) carries the same illegal shape on SP1 and was left alone (`ALSO_SP1`).

**★★ Bug: the 106-frame dead tail — "it redoes the motion at the end."**
*Real cause:* V1.3's split gave `sp_atk02_1b` = `pl052_sp_atk02_2` with `start_frame 61` and **`end_frame -1`** on a **220-frame** clip, licensing 159 frames of playback where the authored content stops at **f53** (last hitbox f9, SoulReboot → f21, ComboStart/Cancel f41, last `Effect_Loop` f53). The only things in the back half were **3 stray `SE_OneShot` at f70/88/116** — Yhwach's own follow-through sounds dragged over the seam by the frame shift, and audible proof the tail was playing.
★ **Why V1.3 created it and V1.2 didn't:** pre-hybrid `sp_atk02_1` also ran to `end_frame -1`, but its only exit was the `my_action` latch, which fires on contact and *abandons* the action — the tail was unreachable. Splitting the action gave the second half a reachable end.
*Fix:* `end_frame -1 → 114` (a **clip** frame; with `start_frame 61` that is action f53) plus dropping the 3 strays. ⚠ This changes the **whiff path only** — on a connect the f9 latch leaves long before f53. ⚠ `CancelTiming f41..-1` now closes at 53 (a 12-frame window); dial `CANCEL_OPEN`.
★ **Ruled out for the "replay", do not re-walk:** the combo graph has no path from `sp_atk02_2`(81) back to 80 or 73 (walked 81→48→28→18→the whole R2 family, 15 nodes); there is exactly **one** entry point to each action in the entire tadj (`sp_atk02`'s f20 latch → `sp_atk02_1`; `1b`'s f9 latch → `sp_atk02_2`) and exactly one `next_name` → `sp_atk02_1b`; all four clips are valid lengths (120/150/200/220), so no `start_frame` is out of range.
⚠ **Parser trap:** `nexts` in the tcmb is a **bare string** (`"nexts": "73"`) for single successors and an array only for multiple. A `\[([^\]]*)\]` regex silently reads every single-successor node as EMPTY.

**⚠⚠ Crash: `pl005.tcmbpkg` truncated to 0 bytes.** `light_string.tcmb_read()` returns `(text, NUL_TAIL)` and **the second value is *bytes*, not a rewrap callable**. Calling it as a function raised inside the write expression, and because `open(p,'wb')` truncates at open, the file was already empty. *Fix:* write back with `text.encode('latin1') + tail`; **serialise to a `blob` first, write to `.tmp`, then `os.replace`.** Recovered from `.presp2v15_bak`, which the script had just made — this is why the backup rule exists.

### 6. The hybrid split, recovery, and chain presentation

**★★ The hybrid SP2_1 is two actions, not a spliced clip.** The two rigs differ (124 vs 253 nodes, 95 shared), so a clip splice was impossible. Split frames were **measured** off the clips with `tmo_lib` (Σ|Δrot| + |Δtrans| per keyed node) and each was corroborated by the donor's own tadj:

- `pl039_atk_ex01_1` wind-up ends **f19**, strike f20 (first `Attack_Melee` f20; `ObjectSpeedChange 0.1` holds f1..19). **SPLIT_A = 20.**
- `pl052_sp_atk02_2` f40..60 is a flat hold (root `ido` z = 0 — he is *not* dashing); launch begins **f61**, impact **f70** (swing SE f59.6/62.4, slash `Effect_Loop`s f62, `PointLight` f70, `Attack_Melee` f70..78). **LAUNCH_B = 61, IMPACT_B = 70.**
- ★ **Zero root translation on both sides of the seam**, so the join cannot teleport him; the only discontinuity is an upper-body pose, blended by `fusion_frame 5`.

```
sp_atk02_1   pl039_atk_ex01_1  f0..20   -> next_name "sp_atk02_1b"    9 blocks, no hitbox
sp_atk02_1b  pl052_sp_atk02_2  f61..end -> ntrl_in           [NEW]   16 blocks
```

Frame map `B = A − 17`. The lead was **solved, not chosen**: `LEAD = (70−61) − (26−20) = 3`, so hit 2 (`my_action = sp_atk02_2`) lands at f9 = Yhwach's own impact. Damage, radius, hitstop and `fix_time` were carried verbatim; the 3 white `Effect_Loop`s spanning the seam are carried into **both** halves. The mechanisms used were all polled first: `end_frame != -1` (1961 uses), `next_flow 1 + next_name` (3664; 270 of them attack→attack), `start_frame != 0` (1591), and tadj frames confirmed action-local on 30 samples. ⚠ **Yhwach's launch is a lunge** — root travel 2.01 units vs Szayelaporro's 0.35; at `move_rate 1.3` that is ~2.6 forward where it was ~0.45. Dial `B_MOVE_RATE`; it may overshoot into a whiffed burst.

**★★ No block type grants hard recovery — placement is the whole mechanism.** Of 74 block names, the only candidate is `NonInput`, and all **57** of its uses are `f0..10` at the head of a `ct_ct_evolve`/`ct_ct_sp_break01` (it swallows the button that bought the counter). `StepCancelTiming`/`DashLoopCancelTiming` only narrow specific cancels. Of 2209 shipped actions with an `Attack_Melee`, 87 have no `ComboStart` and 111 no `CancelTiming` — pl005's own `sp_atk02_1` is already one. Across the 57 shipped `sp_atk02*` the cancel opens a **median ~40 action frames after the last hitbox; pl005 opened at 7.**

The V1.7 arithmetic: `f185→195 @0.2 = 50.0 real` + `f195→200 @0.5 = 10.0` = **60.0 real = 1.000 s @60 fps** — the tail was already right, the window just opened 50 real frames in. `ComboStart`/`CancelTiming` moved f195 → **f199**; lockout 50 → 58 real frames, cancellable window 10 → 2 real. ★ A compounding cause: because V1.5 deleted node 81, `sp_atk02_2` has **no tcmb node**, so `ComboStart` resolves against nothing and **falls through to neutral** — literally "I can step forward."

**★★ Uryu's recovery recipe (pl003) — the shipped way to lock a move.** The *hitting* action carries **no `ComboStart` and no `CancelTiming` at all**; a **second action continues the same clip** and owns the cancel window at its own end:

```
pl003 sp_atk02_1  pl003_sp_atk02_1 f0..-1   lasthit f24  ** NO CANCEL BLOCKS **
pl003 sp_atk02_2  pl003_sp_atk02_1 f43..-1  no hits      ComboStart f67, CancelTiming f67..-1
```

Applied to pl005 at split **f195** (audited: only `SlowMotionRate f195..-1` / `ComboStart` / `CancelTiming` cross it; `OffReverse` + `RotateSpeed` f0..-1 copied to both; nothing cut in two):

```
sp_atk02_2   pl052_sp_atk02 [0..195]   fus 10 -> sp_atk02_2b   cancel blocks DELETED
sp_atk02_2b  pl052_sp_atk02 [195..-1]  fus 1  -> ntrl_in       ComboStart f4, CancelTiming f4..-1
```

Seam verified `end_frame == start_frame == 195`. ★ `sp_atk02_2b` deliberately gets **no tcmb node** — the same shape `sp_atk02_1b`/`sp_atk02_2` already ship; adding an orphaned node is exactly what caused the V1.5 whiff loop. Lockout from the last hit (f172): `172→185 @0.7 = 18.6` + `185→195 @0.2 = 50.0` + `2b f0→4 @0.5 = 8.0` = **76.6 real frames = 1.28 s**, then 2 free frames. ⚠ Watch item: if the engine *does* need a tcmb node for `sp_atk02_2b`, the character **freezes at f195**; `sp2_v18.py --revert` recovers. ⚠ `sp2_v17.py` can no longer run afterwards — it asserts exactly one `ComboStart`/`CancelTiming` on the burst, and both now live on `sp_atk02_2b`.

**Cast presentation (V1.9).** TYBW Ichigo is **pl051** (pl000/001/002/051 = ICHIGO_1..4). pl005's cast was 18 blocks against pl051's 44. ★★ **The rule found: `BlackOutAtmosphere.end == CancelTiming.start`** — polled across 90 shipped SP-cast actions: **agree 65 / disagree 15** (10 lack one), corroborated by pl051 `sp_atk02` 144/144, pl051 `sp_atk01` 113/113, pl005 `sp_atk01` 110/110, and by pl005's cast already shipping `OffReverse f0..56` against `CancelTiming f56`. Added, 18 → **41 blocks**, with **every donor cloned from pl005 itself** so no field could be subtly wrong: `BlackOutAtmosphere f0..56`, `ReverseLimit f0..56`, `HealingReverse f0..13`, `Voice f1` (`sp000_sp_atk01_vo` — the cast had no voice at all), `Afterimage ×19` f0..54 stride 3.

★ **"Timestop" is not a block.** pl051's `sp_atk02` has **no `SlowMotionRate` at all**, while pl005's cast already ran 0.405/0.450 — pl005 was already *slower* than the reference. The freeze reads as `BlackOutAtmosphere` (world darkens) plus the actor's own rate; pl005 had the second half and none of the first, so the blackout was the whole fix.

⚠⚠ **Three pl051 blocks were deliberately not copied**, each polled first: `Protect` (only **20/90 casts, 22%** — a per-character *balance* choice, not a presentation standard; ships OFF via `ADD_PROTECT` because Berg tunes balance himself); `CounterHitFrame` (**14/90, 16%** — gameplay, not presentation); and ★ `ObjectSpeedChange` (**root motion**, dominant value 0.001 in **78/90** casts = a planted character — copying it would have destroyed the travel Berg tuned via `MotionMoveRate 1.5`).

**Chain continuity (V2.0).** ★★ **A multi-segment SP must carry `BlackOutAtmosphere` on *every* segment.** Across all 62 shipped multi-segment SP chains: **every segment 61 / first only 0 / gappy 1** (pl014 `sp_atk01`). Berg's alternative ("or only the `_1`") does not exist anywhere in the game. `ReverseLimit` travels with it — **172 of 179** shipped blackout blocks have one alongside (96%). Where each segment's blackout ends, over 117 mid/last segments: `== CancelTiming.start` **106**, fixed-but-different 10, no-cancel 1 — the same rule V1.9 found for the head. Where a segment has no `CancelTiming`, use the `act_data` `end_frame`.

```
sp_atk02    f0..56   CancelTiming        sp_atk02_2   f0..195  end_frame
sp_atk02_1  f0..20   end_frame           sp_atk02_2b  f0..4    CancelTiming
sp_atk02_1b f0..41   CancelTiming
```

⚠ Blackout stopping before the action ends is **correct, not a gap**: `CancelTiming` is where the player regains control. **Committed = dark, free = lit.**

★★ **`plcom_sp_atk_fx` (the "an SP went off" stinger) is on segment 0 in all 62 chains** — 87 instances total, 62 on segment 0 (every chain without exception), 25 repeated later. **pl005 had it only on `sp_atk02_2` and never on the cast — exactly inverted.** Moved to the cast at f0 and the `_2` copy deleted per Berg ("the sound should only be played at the very initial cast"; 37/62 chains don't repeat it either). The same applied to the voice: `sp000_sp_atk01_vo` was firing **twice** (cast f1 from V1.9 + `_2` f0.3 original); **38 of 62 chains never repeat a voice line within the chain**, so the `_2` copy was deleted. ⚠ `sp_atk02_1`'s `sp000_atk_hi_vo` is a *different* line (a generic attack grunt), not a repeat — left in place. ⚠ **The SE name field is `se_name1`, not `se_name`** (keys: `bind_comp, bind_joint, bind_follow, se_name1..3`); a `se_name` lookup silently returns nothing and makes a population poll read zero.

### 7. The effect banks: private clones, shared banks, and five spawn paths

Four banks are in the live chain. Two are **our own private clones** and may be edited freely; two are **shared vanilla assets** that must never be edited in place.

| bank | status | provenance | role |
|---|---|---|---|
| `P039_zw1_00` | **private clone** | `P039_sk1_00` (Szayelaporro), 15 units forced to 1,1,1 | the white hit/splash effects on SP2_1 |
| `P039_zw2_00` | **private clone** | `COM_sp_Shockwave_00` | the white shockwave flash |
| `P020_zan_blk_00` | **private clone** | `P020_com_atk_00` — Aizen's violet EX shockwave, verbatim | the burst wave itself (trigger `07`) |
| `COM_sp_SmokeMove_00` | **shared vanilla** | — | audited (70 of 72 textures L8, the other two white ramps; `T06_DashStepM` reaches no hued value). **Not touched, no clone needed.** |
| `P039_sk1_00` | **shared vanilla** | — | ⚠ **standing lead never taken**: whitening its `Tex[0]`/`Tex[6]` would fix a purple, but would also whiten Szayelaporro's own `atk_ex01` |

**★ Why cloning was necessary at all.** `COM_sp_Shockwave_00` is **colour-indexed by trigger**: 24 of its 32 triggers are named `T<nn>_<S|M|L>_<bl|gr|lb|or|pk|pu|rd|yl>`, and each `Txx` unit's single `Col/Rgba/Key` tints everything it spawns. `T05_S_pk` is pink and **no white trigger exists** — hence `P039_zw2_00`.

★ **Effects are not in `filename.bin`** (zero `vfx*`/`spfx` strings) — **`file_exist.htable` is the gate.** ★ `Overlay/` has no `Effect/` tree at all. ★ `02LOW` is a non-issue: `02LOW/Effect/` does not exist, vanilla ships no effect banks at that tier, so `QUALITIES = ('00HIGH','01MIDDLE')` is correct and should not be "fixed". ★ Each file keeps its **own deflate level** — `.vfxb` is `78 da`, `.vfxt` is `78 01`. Read it, don't guess. ⚠ Dead leftover to ignore: `P020_zan_blk_00_desktop.vfxt` (underscore instead of dot, 1.49 MB × 2 tiers), a `build_sp2.py` naming artefact never in the htable and never loaded.

**★★★ There are five spawn paths for an effect, and every one has hidden a bug:**

1. `Effect_Loop.eff_name` + trigger
2. `Effect_OneShot.eff_name` + trigger
3. **`Attack_Melee.hit_effect` + `hit_trigger`** — found only at V1.8, after six passes of colour hunting had enumerated only 1 and 2
4. `search_effect_name` (projectile path) — never audited
5. `search_shot_effect_name` (projectile path) — never audited

★ **Check all five on any future recolour.**

**★ The effect size dial is the `Effect_Loop` block's own `scl` field** (per-spawn, in our tadj; it scales the whole trigger group), **not** the per-unit `Scl` in the bank.

**★ How recolouring actually works — a `.vfxb` `Unit` has four colour paths:**

| path | what it is | notes |
|---|---|---|
| `Unit/Col` | flat unit colour | zeroed by `build_sp2.py` |
| `Unit/Ptcl/DwCl` | draw colour, `Rgba/Key` RGB **and** `Red`/`Gree`/`Blue` `Cons` multipliers | both halves had to be restored — `build_sp2.py` zeroed both |
| `DatP/FrC*` \| `Col*` | measured clean throughout |
| **`Unit/Ptcl/TPlt`** | **a palette** — a 128×4 BGRA colour-over-life ramp, addressed by a `Tbl` chunk | found only at V1.7. **Check `TPlt` first on any recolour.** |

Multiplied on top of all of these is **`Brig`**, and the interaction is a trap in its own right (§8).

**★★★★ `Tbl` is the texture binding index — this retires all the guesswork.** A `Tbl` chunk inside a `TPlt` / `TCo1..3` / `TDs1` slot is a **`u16` array of 0-based indices into the `.desktop.vfxt`'s `Tex` order.** Proof: `07_shok4/Ptcl/TPlt` reads `Tbl = 6`, and Tex7 (1-based) is a 128×4 RAW32 ramp — a palette — while Tex6 is a 512×512 L8 mask and the slot's `bL8` is 0. Every slot in all four banks agrees. "Which asset does this effect sample?" goes from a six-pass guess to a five-minute lookup. **It supersedes the old "`TgUI` reachability is not proof" workaround — `Tbl` *is* proof.**

**Texture format census** (every texture, every format, every mip, all four live banks): `P039_zw1_00` 11 textures → 0 tinted; `P039_zw2_00` 18 → 0; `COM_sp_SmokeMove_00` 72 → 0; **`P020_zan_blk_00` 45 → 13 tinted**. Every `Tex` in the game is **DX10-BC7, RAW32 BGRA, or RAW8 L8** — no DXT/BC1/BC3, no BC4/5/6.

**The emitter tree** (verified; `GeIC` = instance count):

```
07_E_point_shok -> u30 parts1 | u35 parts2 | u36 parts3 | u37 glow | u38 RingAura
07_E_point_partsN -> u31 07_shok | u32 07_Spark | u33 07_shok4
```

`6× parts1 + 8× parts2 + 12× parts3 + 1× glow + 3× RingAura`, and **each of the 26 parts emitters spawns `07_shok` + `07_Spark` + `07_shok4`** = **108 draws / 26 refractive per spawn**. ⚠ A shallow parse returns `1/3/1` — that is the **leaf** level; the counts live one node up. ⚠⚠ **`GeUI` edges must be keyed by (parent unit, TARGET unit).** Every emitter carries several `GeUI` edges, each with its own `GeIC`; keying on the parent alone silently hits the **last** edge. This was got wrong once — `2/2/3` was written into the `parts→shok4` **leaves**, leaving 13 parts each drawing `shok4` 2–3× (worse than the build it was meant to reproduce). **Caught before shipping only by asserting `parts_total == 7`.** ★ **Always assert the derived total, not the individual fields.**

★ `07_shok4` carries **two `Ptcl` chunks** — `#1 DPri 5` (TCo1/2/3 + TPlt) and `#2 DPri 10` with **`TDs1`**, the refraction pass, whose strength is `TDs1/Pow/Cons/CoVl` (a float; Aizen's `21_SubAura` uses 0.15).

★ `Life` in a `.vfxb` unit is a **`u32` reinterpreted as float** — `8.408e-44` decodes to **60**, `5.605e-44` to **40**. It is per-particle, not per-emitter. ★ The bank's trigger table is readable from `NM<nn>` chunks; `P020_zan_blk_00` names 1–7, 21, 31, 32 and leaves the rest `------`.

### 8. The colour hunt: nine hiding places for one purple

The wave was meant to be black with a neon purple rim. It came out purple, then magenta, then pink, and finding out why consumed roughly ten passes. Each hiding place, in order of discovery:

1. **`PointLight.color = 1.0,0.1,0.8`** (magenta) on both PointLights in `sp_atk02_1`. This is a **tadj** field, so no `.vfxb` edit could ever reach it. ★ **Always check `PointLight` when a recolour "fails".**
2. **Trigger-indexed colour** — `COM_sp_Shockwave_00`'s `T05_S_pk` (§7). Fixed by cloning to `P039_zw2_00`.
3. **Uncompressed gradient LUTs in the `.desktop.vfxt`** — `Tex1`/`Tex7`, 128×4 BGRA colour-over-lifetime ramps, violet (168,101,255 / 219,77,255). **White vertex colour × a violet ramp is still violet.** V1.1 had copied the texture pack verbatim.
4. **Our own deliberate rim.** V1.4 measured all three documented hiding places clean (`P039_zw1_00`: 0 tinted keys in 72,472 B, both 128×4 LUTs solid 255,255,255; `P039_zw2_00`: 24 `Txx` trigger keys all white, LUTs greyscale at spread 0.004 — *and the vanilla donor measures the same, so they were never violet*; every `PointLight` in `sp_atk02_1`/`_1b` already 1,1,1). The only tinted thing left was **V1.2's own `07_RingAura` = `#6E1FA0` @ `Brig 2.0`**, set because "the edge highlight isn't visible" had been read as a request for a *coloured* rim. V1.4 set the rim white and kept `Brig 2.0` — brightness was what made it visible, hue was never asked for.
5. **A BC7-compressed texture.** ★★★ Every earlier pass had read `.vfxb` colour paths and the two *uncompressed* 128×4 LUTs. Nobody decoded the **block-compressed** textures. `P039_zw2_00.desktop.vfxt` **Tex9** (0-based 8), 128×128 BC7/DX10: RGB **(0.542, 0.542, 1.000)**, max channel spread **0.780** — R 56–207, G 72–225, **B pinned 253–255**. A cloud/noise **colour map** tinted blue by pulling R and G down = (138,138,255), hue 240°, saturation 46% — Berg's "washed purple", derived from bytes rather than from his words. *Provenance:* all 18 texture md5s matched `COM_sp_Shockwave_00`, because `sp2_v12.py` clones the `.vfxt` with a plain `copyfile` and only ever edits the `.vfxb`. *Fix:* a hand-rolled **BC7 mode-6 encoder** — `R=G=B=max(R,G)` per pixel, alpha untouched, **all 8 mips, both tiers**, each block asserted by decoding back with `texture2ddecoder`. Verified independently: spread **0.780 → 0.000**, RGB (0.612,0.612,0.612), Tex9 the only texture changed and the other 17 byte-identical. ⚠⚠ **`sp2_v12.py` re-copies the vanilla texture pack over the clone on every run — v12 must run FIRST and the purple pass LAST, always.**
6. **The `TPlt` palettes** (V1.7, the fourth colour path). Changed, 1-based Tex index (the tooling report is 0-based, so ±1):

```
07_shok4    Tex7  #FF2FED->blk | Tex9  flat #6E45FF | Tex43 #391878->wht   -> ALL BLACKED
07_RingAura Tex16 blk->#EA35FF | Tex27 #941BA0->blk                        -> RE-HUED #B026FF
```

7. **`Attack_Melee.hit_effect`** (V1.8, the fifth spawn path). `sp_atk02_1b`'s two hitboxes carried `hit_effect P039_zw1_00` on `1:T01_Water` / `2:T02_Water_Hit` — Szayelaporro's **Water** triggers, different from the `T03_SubHit`/`T04_handLight` ones V1.1/V1.2 had whitened, firing exactly at impact. ★ `hit_trigger 2:T02_Water_Hit` is **dangling**: the 32-slot trigger table has `NM02`, but a trigger spawns its root emitter plus that emitter's `Emit/GeUI/TgUI` closure, and the bank has **no `02_`-prefixed unit** (`TL02 = 10` is stale editor metadata, like `TL31`/`TL32`). *Supporting measurement:* a per-frame hue histogram of Berg's video (HUD excluded) showed two distinct purple events — **f101–119 at hue 288–307** (dense magenta spray at contact) and **f121–137 at hue 274–284, 2000–4150 px against a 7 px baseline** (large soft splash sheets). Both match **vanilla `P039_sk1_00`**: `Tex[0]` head `#A865FF` = hue 277, `Tex[6]` head `#DB4DFF` = hue 294. ⚠ **Our `P039_zw1_00` clone is provably clean** (Tex0/Tex6 white on all 8 mips, every `Unit/Col` Rgba = 1,1,1, `01_*` units have no `Ptcl/DwCl`, the only saturated texture is a hue-178 cyan **distortion** map on `TDs1`, registered in the htable on both tiers, internal `Name` correct) — **yet the runtime rendered sk1's pixels anyway, and why was never settled.** The fix deliberately does not depend on the answer: *delete the spawn, then no bank can render.* Both hits' `hit_effect`/`hit_trigger` were cleared, hit 2's `hit_shake_blur` went KIKONIMPACT → BIGLARGE, and **the two `3:T03_SubHit` `Effect_Loop`s were deleted** from `_1` (f5..20) and `_1b` (f3..43) — that last part matters, because only 4 units carry a `TPlt` (2 `01_Impact`, 7+9 `01_Water3`, 12 `01_Water4`); clearing `hit_effect` kills 2/7/12 via `T01_Water`, but **unit 9 hangs off `03_E_point` = `T03_SubHit`** and would have kept spawning splash sheets for 40 frames. Kept: `4:T04_handLight` (root 5 → unit 6, no `TPlt`, white `Col` — the white hand light), `5:T05_S_pk` on the white zw2 clone, and `07_RingAura`'s `#B026FF`.
8. **`Brig` clamping — our own multiplier, not any asset.** ★★★ Berg: *"still overly purple/pink instead of black. It's supposed to be black with slight neon purple highlights."* `07_RingAura` is the **only** unit with no `Unit/Col`, so `Ptcl/DwCl` is its entire colour path, and it carried white RGB × `Brig 2.0` in front of V1.7's `#B026FF` palette:

```
white x 2.0 x #B026FF = raw (1.380, 0.298, 2.000) -> R and B CLAMP -> #FF4CFF  HOT PINK
white x 1.0 x #B026FF =                                               #B026FF  neon purple
```

   `Brig 2.0` had been V1.2's rescue for a rim that was then `#2A0A3A` and too dark to see; V1.4 whitened the keys and V1.7 brightened the palette, and **nobody ever took the multiplier back down**. The donor ships 1.0, and 1.0 is the modal value in the game (5602/10974 = 51%). ★ **Over-1.0 `Brig` + a saturated palette = hue shift by clamping** — channels clip at 1.0, so the smallest channel is crushed relative to the others. **Check `Brig` before hunting for a coloured asset.** ⚠ Note the corollary recorded later: because `#B026FF` already has B = 1.0, *any* `Brig > 1.0` clamps; when the rim is invisible the lever is **coverage or draw order, never `Brig`** — which is why `Ptcl/DPri` went **1 → 3**, above the black sheets it was buried under.
   ★ Falsified in the same pass and **not to be re-run: the `TCo*` colour-map theory.** All 8 maps the trigger-07 tree reaches, both tiers, every mip, all 3 formats: **worst saturation 0.003** (V1.7's threshold is 0.02; the real culprit elsewhere measured 0.458). **`Tex[4]`, the wave body, is RAW8 L8 — single-channel, colourless by construction**, so the body can never be tinted by its texture; the shared `TCo1 [5]` is L8 too, so the "which unit owns it" conflict never existed. Nothing was whitened; `.vfxt` md5s unchanged.
9. **The five ramps V1.7 dismissed as unreachable (Plan C).** Another dev, **Kovacd70**, opened `P020_zan_blk_00.desktop.vfxt` in a VFX tool and listed **seven gradient ramps: magenta, light purple, purple, GREEN, purple, hot pink, pink** — a 1:1 match with this file's seven coloured 128×4 BGRA ramps:

```
Tex2  #941BA0   Tex12 #CC7DFA   Tex25 GREEN   Tex31 #FF25DE   Tex37 pink   -> BLACKENED
Tex16 #B026FF   Tex27 #B026FF   = 07_RingAura, the rim Berg wants          -> KEPT
```

   ★★★ **V1.7 had found all seven and dismissed five as "unreachable"**, having derived a reachability set for trigger 07 from `Emit/GeUI/TgUI` (units 30–38). **The inference was wrong and it cost six passes of fixes aimed everywhere else.** ★★ **Lesson: `TgUI` reachability is not proof a texture is unused. When something is demonstrably on screen and a static trace says it cannot be, believe the screen.** In a bank you own, neutralise **every** tinted asset, not only the ones a trace calls live — it costs nothing. Blackening was RGB→0 on **every mip with alpha untouched**, so each ramp keeps its fade curve and only loses hue; both tiers; the `.vfxb` was not opened.

**★★★★ The final answer, and it was never a texture.** Trigger `7:T07_shok_ex02` reaches **9 units binding 14 textures**, and exactly one carried colour:

```
07_RingAura  TPlt -> Tex27 + Tex16  (RAW32 128x4, #B026FF)   +  DwCl Rgba (1,1,1)  x  Brig 2.0
    white x 2.0 x #B026FF = raw (1.380, 0.298, 2.000) -> R,B CLAMP -> #FF4CFF  HOT MAGENTA
```

★★★ **Why five passes failed: they hunted "tinted textures in the bank" instead of "tinted textures the trigger BINDS."** Cross-referenced through `Tbl`: **Tex13** (100% magenta) → `03_HandElek`, trigger 03, never spawned. **Tex15** → bound by nothing. **Tex19** → triggers 02/03. **Tex38** and **Tex4** → `TDs1`, which is a **displacement/offset field, not a colour**. Four unreachable, two vector fields — every one a red herring. ★★ Berg's own theory, *"maybe the attack's own texture is faulty"*, is **ruled out from the bytes**: the wave body `07_shok:TCo1` = Tex5 is RAW8 L8.

**★★★★ Pure black — the finished recipe.** Berg: *"remove every single magenta in the attack. Let it be pure black."* Final audit: **45 textures × 2 tiers, zero tinted.** Blackened: ramps **Tex16, Tex27** (the old `#B026FF` rim) plus BC7 sheets **Tex4, 13, 15, 19, 38**; all 71 hued `Rgba` triples in `P020_zan_blk_00`; and `07_RingAura`'s `DwCl` keys. ⚠ In the final state `TDs1` textures (Tex4, Tex38) are **deliberately kept** — zeroing an RG offset field flattens the refraction pass, and Tex4 is now the only thing giving the black wave shape against a dark stage. ★ `P039_zw2_00`'s one hued key (`L_Shokwave2_bl`) went **white, not black** — `sp_atk02_1` is the flash Berg signed off as "PURE WHITE".
★ **Why the rim had to go too:** once Plan C blackened the seven ramps, the wave *body* went black-on-black, leaving `07_RingAura` — literally a ring — as the only coloured thing, and the move read as "a tilted circle". **Dimming the rim (`Brig` 2.0 → 1.0) made it worse**, because it removed what little competed with the ring rather than the ring itself.
★★ **Pure black is encodable where desaturation is not.** Greying a big BC7 sheet fails: mode 6 fits **one colour line per 4×4 block**, and `Tex13` (1024×2048) round-tripped at **rgb err 59 / alpha err 50**. Forcing RGB to a *constant* collapses the colour spread to zero, so RGB comes back within **1/255** and only alpha rides the index (worst 8). ⚠ Assert `rgb_err <= 2`, **not `== 0`** — BC7 endpoints are 7-bit + p-bit, so exact 0 is not always representable.
★★ **A mean is the wrong test for "is this tinted."** `Tex4`/`Tex19` have mean channel spread 0.001/0.005 and passed every audit, but their **worst opaque pixel** spread is 0.54/0.58. **Always measure max-over-opaque-texels, never the mean.** That mistake hid two assets to the very end.
⚠ Performance note on tooling: 1024×2048 BC7 encoding in pure Python takes ~2 min per tier (run it with `nohup` and poll). A later **numpy rewrite does the same image in 0.08 s** and is asserted byte-identical to the original on six shapes every run.

**Also cleared en route, do not re-investigate:** the 25 `Afterimage` blocks are `color_type 0` = `after_image_color.tbl` row 0 = **(2.8, 1.2, 0.1) GOLD** (not black; `AFTER_COLOR_TYPE` is the dial if that reads wrong on a shadow move); `effect_rim.fsv` has no per-character rows; `BlackOutAtmosphere` has **zero fields** on all 497 shipped instances; `COM_sp_SmokeMove_00`'s trigger carries no colour and all 72 textures are neutral. ★ `P020_zan_blk_00`'s `07_*` units (trigger `T07_shok_ex02`) are pure **black (0,0,0)**; the tinted units in that bank (0.294,0.255,0.267 dark mauve; 1.255,1.336,1.418 HDR blue) all belong to *other* triggers (`01_*`/`02_*`/`03_*`/`04_*`/`21_*`) and never spawn.

**⚠ Superseded but recorded:** the Sankt dome. **It was never removed.** Seven `P052_Sankt00` blocks sit in `1_normal_attack_sp_atk02_2` and are present unchanged in **every** backup (`presp2hitconfirm` / `presp2v12` / `presp2hybrid` / LIVE, all 7/91): 5 × `Effect_Loop 3:T03_Number` f12..62 (the finger domes) + `Effect_OneShot 1:T01_Sanktzwinger` + `4:T04_wave`, both f20. Nothing regressed — the removal simply never happened (the earlier "we removed it" was the *move name*, via `move_names_own_entry.py`). All seven are pure cosmetics — no `Attack_*`, no `my_action` — so removing them cannot touch the tuned 18-hit schedule. ⚠ The same seven blocks exist in `2_evo_attack_evo_sp_atk02` and `3_rev_attack_rev_sp_atk02` and were **left alone** (still Yhwach's move, not in scope); dial `EVO_REV_TOO`.

### 9. ★ The performance/cost model

This is the headline finding of the whole SP2 effort, and it took **seven wrong models** to reach. The move lagged Berg's PC *and other testers'*, so it was a real cost problem, not a machine problem.

#### 9.1 The models that were wrong, in order

| pass | model | what it predicted | why it was wrong |
|---|---|---|---|
| V2.1 | bank size / concurrency | 13.29 Mtexel bank spawned 6× is too heavy | true, but not the binding constraint |
| V2.1 | draws per wave = 1 | — | **real figure was ~82–108 draws per spawn** |
| V2.2 | `RUNo = -1` = infinite emitters leaking | ten released emitters run forever | **false: `RUNo = -1` is on 18,115 of 18,222 units in the game.** Emitters are bounded by `Unit/Life` |
| V2.1–V2.3 | peak concurrency = overlap of the ten tadj `Effect_Loop` windows | peak 3 waves | **a window bounds the EMITTER, not the particles** — true peak was 9 |
| ≤V2.3 | cost = draw count | 972 → 336 draws should fix it | **the clean build had 964 draws; the laggy one 379** |
| V2.4 | quad plane = `y × z` (because `07_shok` is `BAxs = 1`) | V2.8's `scl` change is +7% | **the plane is `x × y`** — the same change was +50% |
| V3.0 | a six-datum fill model in `sp2_v31_body.py` | various | **the model was fitting the test protocol, not the builds** |

Three wrong diagnoses were shipped off that last model — *accumulation across casts*, *`T31_Unlock` leakage*, and *`hit_shake_blur`/hit-stop* — **before anyone measured.**

#### 9.2 The intermediate discoveries that were right

**★★★ `Effect_Loop` windows are not particle lifetimes.** This is the single most important effect-cost fact in the project. A tadj window only says how long the **emitter** runs; a particle already emitted lives out its own `GeUI.Lif + LifR` regardless. In the 07 group the lifetimes are **3–10× the longest window**:

```
07_shok            Lif 25+10 =  25-35 f      window 33 or 11
07_Spark           Lif 90+30 =  90-120 f     window 33 or 11
07_shok4           Lif 80+40 =  80-120 f     window 33 or 11
07_E_point_parts1  Lif 200               <-  window 33 or 11
```

★★ **Measure peak on `GeUI.Lif + LifR` in real frames, never on tadj block overlap**, converting spawn frames through the entry's own `SlowMotionRate` blocks first.

**★★ The 3-second tail, accounted to the frame.** Berg after V2.1: *"still big fps drops AND screen flickering that goes away only after +/- 3 seconds **after the attack has ended**."* ★★ *"After the attack ended" is the diagnostic* — overdraw during a move cannot outlive the move. The last wave spawns at real f183; `Spark`/`shok4` live to f303 and `parts1`'s `Lif 200` to **f383 = 2.07 s past the action end (f258)**; on top of that `T32_Kill&Fade` carries **`TL32 = 61` frames of fade** (against `T31_Unlock`'s `TL31 = 3`). 2.07 + 1.0 ≈ **3.1 s**, exactly what was reported. ⚠ This also explains the "if not worse" report after V2.2: swapping `Unlock → Kill&Fade` traded a 3-frame release for a **61-frame fade × 10**. Kill&Fade is still right on roster evidence (`Effect_Loop` `end_trigger` across the roster: **Kill family 1926 / Unlock family 412 / none 3388**, so Kill wins ~4.7:1 wherever an explicit end is given) — it just was not the fix. ★ `T31_Unlock` **releases / un-parents an effect; `T32_Kill&Fade` terminates it.** ⚠ Aizen uses `T31_Unlock` on this same bank and trigger — Unlock is not "wrong" for the bank, and copying him is not the answer. **The difference is arithmetic: he fires it once (peak 1–2), we fired it ten times. One released emitter is a garnish; ten is a leak.**

**★ Check `OvLf` before editing a `GeUI` `Lif`.** V2.3's `Lif 200 → 60` on the root→`parts1` edge was **inert**: that edge carries `OvLf = 0`, so the edge's `Lif` is ignored, and `07_E_point_parts1`'s own `Unit/Life` was already 60 in `.presp2v22_bak`. What actually killed the tail was the `07_Spark`/`07_shok4` halving (those edges are `OvLf = 2`).

**★ Emission is one-shot.** The whole 35-field `GeUI` struct has no rate or interval: `GeIP` is **100 on 16,982 of 16,992** enabled edges game-wide (a constant, not a period), and `GeSD` = 0.

**★ Blend mode is alpha, not additive.** `DMod = 1` on all six `07_*` passes. Calibrated on 16,133 shipped `Ptcl`: name matching "smoke" → DMod 1 by 219:7; name matching "add" → DMod 2 by 139:111. **The additive-overdraw theory is dead.** The flicker candidates that remained were (a) **transparency sort instability** — 91 coincident alpha quads all at `DPri 2` with `DTst 1`, reduced to 49 — and (b) the refraction pass.

**★ Shipped cost envelope**, measured across all 733 banks / 3901 roots under `00HIGH/Effect/spfx`: refractive draws per spawn median 2, p90 10, **p99 61**; total draws median 6, p90 20, **p99 108**. pl005's T07 sat **exactly at p99 on both**, and every shipped root above it is a `_cs_` cutscene or `ss1` ultimate at **peak 1**. No shipped gameplay effect stacks a p99 root nine deep.

**★ Not implicated, do not re-open:** `Afterimage` (roster peak-concurrency median 2, p90 4, max 27; pl005's 25 blocks peak at only **5** and are temporally disjoint from the waves — 3-frame stride f0–72, first wave f71); the 10 `PointLight` (single-frame, `life 2`, colour 0,0,0).

#### 9.3 The fill model (V2.4 → V2.9)

Berg's own datum broke it open: *"it wasn't laggy when the `scl` was reduced in an earlier version"* — that was V1.2's `0.6,0.6,0.6`.

```
build                                        peak draws   fill   x clean
V1.2  26 parts, Lif 90+30/80+40, scl .6 uni      964      1441    1.00  <- CLEAN
V1.7  26 parts,                  scl .9/.9/1.8   964      6485    4.50
V2.3  13 parts, Lif 45+15,       scl .9/.9/1.4   379      2449    1.70  <- was LIVE, laggy
      13 parts,                  scl .6/.6/1.4   379      1633    1.13  <- XY alone NOT enough
V2.4   7 parts, scl .6/.6/1.4, TDs1 deleted      217       980    0.68  <- shipped at the time
```

★★ **The clean build had *more* draws (964) than the laggy one (379). Draw count is not the binding constraint — screen coverage is. Always cost `Σ draws × scl-area`.**

★★ **The 1-in-20 inconsistency is the signature of sitting *on* the threshold, not a state bug.** Nothing is stateful (emission is one-shot), but the effect **randomises its own area**: `07_shok`'s `Unit/Scl` carries `CoRG` random gains of **+1.0 on Y and +1.0 on Z** over bases 1.5/3.5, giving a per-particle area range of about **2.1×**; all three lifetimes carry `LifR`; `DwRt.Z` is a random 2π roll. A build 70% over the line falls under it on a lucky roll. **The fix for intermittency is margin, not a state hunt.** Hits 4–6 (f126/136/143) are exactly where wave concurrency goes 3–4 → 6–7, matching "lag from hits 4–6 on"; a duplicated cast is 2× on top.

#### 9.4 ★★★ The geometry, settled by the lag itself

Two readings of `07_shok`'s geometry stayed open for an entire session because `x` and `y` had only ever been moved *together*:

```
plane = x*y, normal = z   (DwSz.Z is a flat constant; DwRt rolls 2pi on Z)   <- CORRECT
plane = y*z, normal = x   (07_shok is BAxs=1, so z looked like a screen axis) <- WRONG
```

V2.8 moved `scl` from `0.8/1.0/1.4` to `1.0/1.2/1.25`. Under `y·z` that is **+7%**; under `x·y` it is **+50%**. Berg ran 1.40 clean and 1.50 lagged. **A 7% rise cannot do that; 50% obviously can.**

⇒ **The cost model is `parts × scl.x × scl.y`.** Reference points: `26 × (0.8·1.0) = 20.8` ran clean; `26 × (1.0·1.2) = 31.2` lags; `17 × (1.0·1.2) = 20.4` was shipped by V2.9.

★★ **Particle count is the only lever that has ever bought framerate without changing the look.** `scl`, texture stubbing, `TDs1` deletion, `bSfP`, `Brig` and the `DwSz` curves all altered the appearance and each cost a round trip. The sheets overlap heavily, so cutting the stack thins the pile, not the silhouette. V2.9 therefore took `GeIC` **6/8/12 → 4/5/8** (26 → 17 parts, ~65% of each so proportions hold) and left `scl` at Berg's requested `1.0/1.2/1.25`. **Colour and cost are now fully decoupled.** ★ `GeIC` and `scl.x`/`scl.y` trade against each other at identical cost — prefer moving `GeIC`, since `scl` is the one Berg has opinions about.

For the record, the earlier and now-superseded geometry claim (V1.7) was **"Z is travel, X/Y are thickness"**, itself measured twice: (a) `Attack_Melee.coll_pos` on the root across 41 playables — **4146 blocks, 2946 offset along Z, 1199 centred, exactly one along X** (mean |Z| 0.757 vs |X| 0.001); (b) the 240 shipped non-uniform `Effect_*` `scl` values are dominated by **X == Y with Z free** — `0.6,0.6,0.9` (×14, the commonest non-uniform value in the game) and `1.0,1.0,3.0` (×13), with the bank agreeing (`07_shok` is `Scl 1.5/1.5/3.5`). That evidence is about *authoring convention*, and it is compatible with the final answer; what was wrong was V2.4's inference that `BAxs = 1` made `z` a *screen* axis.

#### 9.5 ★★★★★ RULE ZERO and the bisect campaign (V3.x)

**The move lagged on a random ~50% of casts, so any verdict from a handful of casts is noise.** Six such verdicts had been used to build and validate the fill model in `sp2_v31_body.py`; **the model was fitting the test protocol, not the builds.**

★ **A performance verdict is worthless without the cast count. Ask for it every time.**
★ **Never tune this move from an impression. Use `sp2_bisect.py`.**

**The apparatus.** The obvious experiment is impossible: `sp_atk02`'s lunge carries the `my_action` latch, so **the burst only exists when the lunge connects** — there is no whiff case and no blocked case (`my_guarded_action` is empty), and the opponent is always point-blank and in hitstun. **So vary the BUILD instead.** `Zangetsu Patch/sp2_bisect.py` snapshots both `tadjpkg` files **and both tiers' `.vfxb`**; every mode re-applies from that snapshot so modes cannot compound; `--restore` was verified byte-exact. Modes: `--a-nowaves --b-noblur --c-nostop --d-nobodyhits --e-sheetonly --f-halfwaves --g-fewsheets --h-smallsheets --restore`.

**★★★★ The measured curve** (fill = sheets × sheet-area; 1.00 = the laggy baseline):

```
A    no waves, everything else identical      20 casts / 3 sessions   0%    -> waves are ALL of it
E    07_Spark + 07_shok4 suppressed            5 casts               60%    -> NO CHANGE: it is
     (~80% of draws incl. the refraction pass)                                 07_shok ALONE
-    baseline 13 sheets @ .540/.648  fill 1.00 ~20 casts             ~50%
G    3 sheets @ .540/.648            fill 0.23  6 casts               0%
H    13 sheets @ .270/.324           fill 0.25  6 casts               0%
V3.4 6 sheets @ .540/.648            fill 0.46 15 casts              27%
V3.5 6 sheets, constant 1.450x1.658  fill 0.32 11 casts               9%  + "I like the look"
V3.7 same + burst homing deleted     fill 0.32  5 casts               0%  SHIPPED
```

★★★ **The hit path is FREE.** 18 `hit_shake_blur`, 85 frames of hit-stop, defender hit sparks, 25 Afterimages, 10 PointLights: **zero measurable cost.**
★★★ **G and H cut fill by the same factor on different axes and both hit 0% ⇒ count and area trade freely.** Rate is roughly linear in fill; 0% wants **≲ 0.32**.
★★★ Mode E is the decisive one: suppressing `07_Spark` and `07_shok4` removes ~80% of the draws *including the entire refraction pass* and **changed nothing**. The cost is **`07_shok` alone** — the big sheets.

★ **Killed hypotheses — do not re-open:** hit-stop, `hit_shake_blur`, per-hit work, accumulation across casts, `T31_Unlock` leakage, camera distance, connect count, the refraction pass, `07_Spark`, `07_shok4`, the texture pack, the `.desktop.vfxt`.

#### 9.6 ★★★ Lower the peak, not the mean

Lag is a **threshold crossing**, so a cast is decided by its **worst** frame. `07_shok` randomised its own size per particle — `Unit/Scl.X 1.500 + CoRG 0.500`, `Y 1.500 + CoRG 1.000` ⇒ per-sheet area **2.25 … 5.00, worst 43% over the mean**. Replacing that with a **constant 1.450 × 1.658** (area 2.404) drops the mean 31% but **the worst case 52%**, and the spread to zero. Aspect 1.143 was preserved to 3 dp. ★ `Scl.Z` keeps its `+1.000` gain: Z is the travel axis, costs no fill, and is the only variety left.

★ The other real variance source was **the character's aim** — a wave angled 10° differently covers different screen. Deleting the burst's `HeightHoming` took the failure rate 9% → 0%.

#### 9.7 ★★ The tilt, and why `IsModelRotate = 0` was not enough

The wave has `rot = 0,0,0` and never aims itself; it binds `bind_comp = body` with `bind_follow_rot = 1`, so it inherits the **character's** rotation.
★★ **`HeightHoming` tracks over its own frame window regardless — `ModelRotate_*` is only a sub-dial for whether the model visibly turns.** Setting `IsModelRotate = 0` (V3.6) left the block live over `f0..78` and the wave still landed off-level. **Delete the block (V3.7).**
After that the burst has zero rotation authority: `RotateSpeed speed_rate = 0.000000` over f0..-1 pins his facing, `ObjectSpeedChange`/`OffReverse` are root motion, and the `Attack_Melee` `search_*` homing family is inert on a melee.
⚠ The lunge keeps `IsModelRotate = 1` so it still aims and connects. ⚠ `sp_atk02_1b` is left flat on purpose — `ModelRotate_StartFrame = 0` means its pitch is still on him when the waves spawn. ⚠ **Never set `bind_follow_rot → 0`** — the wave would ignore his facing and fire on a fixed world axis, broken on the P2 side. ⚠ `HomingAngle → 0` would kill the vertical tracking too.

#### 9.8 ★★ Aspect is free, area costs

Fill is `x·y`; shape is `y/x`. **Hold the product, move the ratio.** `07_shok` is `BAxs = 1` (axis-aligned, **not** camera-facing; 122 units out of 18,222 across 857 banks, where the 98.8% default is `BAxs = 2`; its `RotO` is 3 where all five siblings are 4), so **its literal rectangle is the silhouette**: elongated reads as a ripple, near-square reads as "a tilted circle". V3.1 collapsed the extension aspect **2.88 → 1.25** and Berg called it a tilted circle immediately. **V2.5 had drawn the identical complaint from `bSfP = 0` — two different fields, same symptom.**

**★★★ `bSfP` is the wave's shape, not an optimisation knob.** After V2.4 killed the lag ("that did not lag"), Berg reported *"instead of a wave/ripple, it was a tilted circle-ish."* **Cause: one field from V2.4's own escalation list — `07_shok` `Ptcl/bSfP` 1 → 0.** `bSfP` is **soft particle**: on, the quad's alpha fades where it approaches intersecting scene geometry, so a flat card reads as a volumetric ripple over the floor and the opponent; off, you see the literal quad, and because `07_shok` is `BAxs = 1`, a hard quad seen from the battle camera is exactly "a tilted circle". **The two compound: `BAxs 1` makes the wave *travel* right, `bSfP 1` stops that same quad looking like a card.** It is the shipped norm anyway — `bSfP = 1` on **6498** units. Restored; 1 byte per tier at **`0x8D2BC`**. Affordable, too: it costs a per-pixel depth sample on **7** quads, where the "ran clean" V1.2 build had it on with **26**.

**★★ Thinness = the two `DwSz` easing curves drifting apart.** `07_shok`'s X grows 1.67× while Y grows 3.0× over its life, so each sheet becomes **1.80× more elongated and is thinnest exactly when it is biggest**. Holding the aspect constant across the expansion — spawn/extension aspect `0.750/0.417` → `0.800/0.800` — gives quad area **+67% at spawn, −23% at extension**, and **peak `07_shok` fill −8.0%**. Adding `Unit/Rot/X/Cons/CoRG` **15° → 30°** fans the 7 coplanar sheets in pitch; a tilted quad's projected area is `A·cos θ`, so it **cannot** raise coverage. ★ **`scl.x` is not a free depth axis** — `07_shok`'s `DwSz.Z` is a flat constant while X and Y are animated, and `DwRt` is a 2π random roll **on Z**, so the quad's plane is X×Y and its normal is Z; raising `scl.x` is a straight fill increase.

#### 9.9 ★★ Removing a slot re-purposes a `Ptcl` pass

Berg, with three screenshots (laggy / V2.4 / V2.5): *"the move lost its mostly black and the purple got much stronger … the shape is different … revert it to how it looked before (without the lag)."* The laggy shot is near-black; V2.4 and V2.5 wash the whole floor bright magenta.

★★★ **Cause: V2.4 deleted `07_shok4`'s 332-byte `TDs1` chunk. The pass survived and merely lost the slot that made it refractive** — so it became a **second colour pass**, drawing that unit's magenta `TPlt` palette twice:

```
pre-V2.4   Ptcl DPri=5  7608 B  TCo1,TCo2,TCo3,TPlt          <- colour
           Ptcl DPri=10 7764 B  TCo1,TCo2,TCo3,TDs1,TPlt     <- REFRACTION
V2.4/V2.5  Ptcl DPri=10 7424 B  TCo1,TCo2,TCo3,TPlt          <- a 2nd COLOUR pass!
```

★ **A `Ptcl` pass is defined by the slots it carries.** To drop one, remove the **whole `Ptcl` chunk** or neutralise it in place (V2.3's `TDs1/Pow = 0` was the right shape of that idea). ⚠ Related shipped-value note: `TDs1/Pow = 0` is legitimate (6 slots ship it) but **`bEbl = 0` is not** — all 11,897 `TCo1`, 3,848 `TDs1` and 8,168 `TPlt` slots in the game ship `bEbl = 1`.

★★ V2.4 also changed the **aspect**, not just the size: the liked build `0.9,0.9,1.4` is y:z **1:1.56**, while V2.4 shipped `0.6,0.6,1.4` = **1:2.33** — much longer relative to its thickness, i.e. "wrong the way it expands when fully extended". The aspect was restored **at the proven fill** by scaling both axes: `z²/1.5556 = 0.84` ⇒ **`0.740,0.740,1.150`**, footprint 0.851 = **101.3%** of the no-lag V2.5 build. Built by **rebasing the `.vfxb` on `.presp2v23_bak`** (pre-V2.4: `TDs1` intact, `bSfP 1`, V2.3 lifetimes) and re-applying only the density cut — safe only because **the `.vfxb` holds no hand-tuning by Berg**; the `.vfxt` (palettes, BC7 fix, 1024² Tex[4]) was not touched.

#### 9.10 The shipped build and its dials

```
v31 lifetimes 45+15 · 00HIGH Tex5 2048² -> 01MIDDLE's own 1024² chunk verbatim
    · rim DwCl white, Brig 2.0 -> 1.0, Tex16/Tex27 -> #B026FF
v32 artist's DwSz (X .75/1.25, Y 1.00/3.00) + 15° pitch · scl 0.540/0.648/1.250 · rim DPri 1 -> 3
v33 all 14 Effect_* end on their own bank's Kill trigger (12 were Unlock)
v34 GeIC 3/4/6 -> 1/2/3  = 6 sheets
v35 constant sheet 1.450 x 1.658 (CoRG cleared) · pos lift
v36 IsModelRotate 0 across the chain · lift 0.25
v37 burst HeightHoming DELETED · lunge IsModelRotate back to 1
v38 fighting_base halved per file (0.460->0.230, 4.500->2.250)
```

**SP2 shipped 2026-08-09 — no lag, no flicker, look approved. Live == dev, 191 files identical, `Overlay/` 234 files 0 stale.**

Headroom if the wave should be denser again: `GeIC` 1/2/3 → **2/2/3 = fill 0.37**, still under the last laggy point. If it ever drags again: → **1/1/2 = 4 sheets, fill 0.21**, below both proven points. Longer-standing escalation list, ranked, from V2.9: lifetimes 45+15 → 30+10 (peak 6→4, −30%); `GeIC` → 1/1/2; `07_shok` `DwSz.Y` end 3.0 → 2.0 (−17%; **the quad triples in Y over 30 f** and nobody had looked); `scl.z` 1.4 → 1.0 (costs the length Berg asked for); drop `07_Spark` (`PrV2 9` = an untextured trail, longest life, near-invisible on a black wave).

★ **Texture stubbing, for the record (V2.1):** the `.vfxb` addresses textures **by position**, so deleting one renumbers ~38 `Tbl` entries. **Downsize, don't delete** — all 31 unreachable textures became **4×4 3-mip stubs** keeping their slot, index, format, `Hash` and `Lbl`. ⚠ **The reachable set is 14, not 10** — a slot-name whitelist (`TCo1..3`/`TPlt`) misses **`TDs1`, the distortion slot**; collect **every `Tbl` chunk** instead. Safe because the `.vfxb` is md5-identical across tiers whose `.vfxt` differ in size. Bank cost went 13.29 → 5.26 → 2.12 Mtexels across V2.1/V2.3, with a further 2.12 → 1.86 available and **not taken** (VRAM, not fill).

#### 9.11 ⚠⚠ The two `tadjpkg` diverge — and a guard caught it

`pl005.tadjpkg` and `pl005_modded.tadjpkg` differ in **exactly two entries**: `1_normal_attack_atk_lo03` and `1_normal_attack_sp_atk02_2`. On the burst, `fighting_base` was **17 × 0.020 + 1 × 0.120 = 0.460** in the base file but a uniform **18 × 0.250 = 4.500** in `_modded` (a deliberate balance choice by someone else). V3.8's hardcoded-total guard **refused to halve `_modded`** rather than silently mangling it.
★ **Halve or scale per file from its own snapshot, never from a shared assumed value.** Result: 0.460 → 0.230 and 4.500 → 2.250.
★ Only **7 characters** have a `_modded` variant at all: pl001, pl005, pl007, pl018, pl029, pl035, pl036.
⚠ The same class of drift bit once before: at V2.8 `pl005` held `scl 0.8/1.0/1.4` (Berg's own tuning) while `pl005_modded` was stale at `0.6/0.6/1.4`. **Always read both before assuming a shared value.**

#### 9.12 Script-order landmines

⚠⚠ **`sp2_v12.py` rewrites `scl` and both frame ends on every run**, and re-copies the vanilla texture pack over the clone. It was edited in lockstep with each later pass (`BURST_SCL`, `BURST_LEN_CLUSTER`/`BURST_CLUSTER`, `RIM_BRIG`) or a re-run would revert V1.7/V1.9/V2.1.
⚠⚠ **Landmine found (pre-existing):** `sp2_v12.py` and `sp2_v19_cost.py` still held V2.4's `BURST_SCL = 0.6,0.6,1.4` while V2.6 shipped `0.740/0.740/1.150` — **a re-run of either would have silently reverted the aspect Berg had approved.**
⚠ `sp2_v25_restore_look.py` **rebases** the `.vfxb`, so a v25 re-run wipes V2.7's six fields — re-run v26 after it.
⚠ `sp2_v17.py` can no longer run after V1.8 without `sp2_v18.py --revert` first.
**Run order, as last recorded: `v12 → v17 → v16 → v19 → v21 → v22 → v23`**, with v22 strictly before v23 (v23 takes `GeIC` past v22's target), and v19's `EXPECT_REACH` accepting 13 **or** 14 (Tex[3] was reachable only via `TDs1`). ⚠ **Thin/contradictory:** the file records three successive run orders (`v12 → v16 → v17 → v18`, then `v12 → v16 → v19 → v21 → v22 → v23`, then the above). Treat the last as current and re-derive before any replay.

#### 9.13 ⚠⚠⚠ Reverting: use **git**, not `.bak` names

Berg: *"Something else got changed that you're not properly reverting. What are you not doing properly?"* Three real failures:

1. **Reverted file-by-file, picking backups by NAME as a proxy for chronology.** The `.vfxb` and `.desktop.vfxt` are a **matched pair**, and they were restored from snapshots ~14 h apart. A mismatched pair renders wrong **and** cheap — i.e. "looks wrong, no lag", which is a diagnostically poisonous state.
2. ★★ **Ignored the git history.** The dev environment is a repo, and commit **`15d48cd` "CRE update"** is a full authoritative snapshot of every one of these files. `git show 15d48cd:<path>` settled in one command what hours of `.bak` archaeology could not. **Revert from git first.**
3. ★ **Never verified that the files being edited are the files the game loads.** This produced its own contradiction, recorded in both directions: an earlier alarm said the launcher's `injectEffects()` copies only `Effect/spfx/`**`com`**, so `Effect/spfx/pl020` is in neither it nor `Overlay/_overlay_manifest.json` and the burst bank would never reach a clean install. That alarm was later **corrected**: `injectFolder(..., fullFolder=False)` copies `<version>/00HIGH|01MIDDLE` wholesale, so **the launcher does ship the effect banks** and no `CREATED`/htable work was needed. ⚠ A related caveat is still recorded as unresolved: `00HIGH/Effect/**` is in the version tree but **not** in `Overlay/_overlay_manifest.json`, so fresh-install delivery of the bank was called unproven. **These notes conflict; verify against the current launcher before release.**

### 10. The Overlay rollback incident

**2026-07-30: a "community patch" install silently reverted pl005 work. The community patch was not the culprit.**

The cause was `Patch_Dev_Environment/GameVersions/Bleach Rebirth of Souls Community Patch + Zangetsu + Hiyori/Overlay/` — a **stale 234-file release snapshot from Jul 26 09:44** that gets copied over the install on every deploy.

*Proof:* **232 of its 234 files were byte-identical to the live game directory.** The two that were not were `Overlay/Fnames/file_exist.htable` (837,156 B) and `Overlay/Fnames/filename.bin` (1,672,069 B) — **the exact size and mtime of the rolled-back live files.**

⚠ **Standing rule: rebuild `Overlay/` before every release or it re-inflicts this.** It also currently ships three stray `.pre*_bak` files to end users.

| destroyed | recovered from |
|---|---|
| `Fnames/file_exist.htable` | live was an exact ordered **subset** of `.presp2_bak` (3 missing, **0 live-only** — the community patch contributed nothing). 7 entries re-added → 104,651 |
| `Fnames/filename.bin` | exact ordered subset of dev's copy (1 triple missing, 0 live-only). Re-added `('pl005_pic2','.lds','pl005_pic2')` → 28,606 triples |
| `Script/Action/pl005.tcmbpkg` | node `sp_atk02` id 73 gone, `start_sp_atk02`(19) empty, sp1 un-benched → `restore_sp2_routing.py` |
| `Sound/{English(US),Japanese(JP)}/pl005.bnk` | select-voice line gone; dev copy (== live `sp000.bnk`) |
| `Demo/pl005_ct_evolve`, `_ct_revolut`, `_evo_ct_revolut`, `_ct_sp_break01_maxout` | retarget + camera work gone; dev copies |

**Survived intact:** `pl005.tadjpkg` (226 entries, *ahead* of dev — it held Berg's hand-tuned 68-block SP2), `pl005.tactpkg`, `CharaStatus.fsv`, `WepVisible.fsv`, `chara_bgm.tbl`, `cos_pl005.fsv`, `bgm.bnk` + the 8 `.wem`, `Text/CommonText.cat`, all UI/icon/banner assets, all `Model/chara`.

Repair scripts: `restore_sp2_routing.py` (**tcmb only** — it deliberately does not re-run `build_sp2.py`, which would rebuild the tadj entry from pl052 and destroy Berg's tuning) and `restore_fnames_registrations.py` (menu + pic2 + sp2-effect registrations, `--dry`/`--revert`, backups `.prerestore_bak`).

**⚠ It happened a second time.** V1.3 found `P039_zw1_00`/`zw2_00` **on disk but absent from `file_exist.htable`** — i.e. **V1.2's entire white-effect pass had never been loading.** Same cause: the dev build's stale `Overlay/Fnames/file_exist.htable` copying back over live. 8 rows were restored, and `register()` now re-anchors zw1 on a vanilla pl039 bank (`P039_ss2_00`).

**`sync_to_dev.py` gaps found in the same investigation:** `ROOTS` omits `00HIGH|01MIDDLE/Model` and `Effect`, so **model and effect edits are invisible to it** (hair colour, the sp2 `P020_zan_blk_00` particle files); and `Script/chara_bgm.tbl` and `Script/Costume/cos_pl005.fsv` have **no backup sibling**, so future edits to them will not be detected.

**⚠⚠ A third failure mode in the same tool — a hardcoded per-session mount path.** `REPO_ROOTS` carried `/sessions/zealous-ecstatic-pascal/mnt/...`. **The Cowork mount path contains a per-session id**, so in a new session `gv_root()` fell through to the in-game legacy copy and a dry run reported **"191 new, 0 updated"** — one `--apply` away from pouring the whole build into the dead `Patch_Dev_Environment/`. It now globs `/sessions/*/mnt/Bleach-Rebalance-Of-Souls-Dev-Environment`.
★ **Always dry-run it: "N new" on an established tree means the wrong root.**
★ It runs fine from the Linux VM — python3.10 is present, the mount is read-write, and scripts can be `device_commit_files`'d in and run directly. No `.bat`/click workflow is needed any more.

### 11. The `.tdemopkg` cutscene format

Tool: `Zangetsu Patch/demo_cam.py` (read/set camera offsets, backups `.precamoff_bak`, `--revert`).

**A `.tdemopkg` holds exactly eight entries:**

```
_demo_csv     the whole cutscene script, _cso_-ciphered
_demo_mdltex / _demo_vis / _demo_mtl    48-byte stubs, usually empty
_demo_mot     embedded character motion (tmo) for the cutscene — the ANIMATION
_demo_cam     a baked tmo1 camera motion (keyframes + FOV/near/far; its header shows
              540/960 screen centre and 1.778 aspect)
demo_listevt0 / demo_act0
```

`_demo_csv` decodes to **five CSV sections**: `_csv0` header (`demo_frame` = the cutscene length), `_csv1` cast, `_csv2`/`_csv3` event **schema**, `_csv4` event **instances** (`evt0`, `evt1`, …).

#### 11.1 The `_cso_` cipher, and the signed-key trap

```
header  _cso_<ver>_<key>\n
k[i]    = (i + (key >> 4i)) & 0xFF        i in 0..7
decode  plain = cipher - k[i&7] if k&1 else cipher + k[i&7]   (mod 256)
```

★★ **The header key can be negative** — e.g. `_cso_6_-1499435279`. Two traps, both of which corrupt silently:

1. A `(\d+)` regex **does not match the minus sign**, so `decode()` returns the payload **still enciphered**, and every downstream check quietly works on garbage.
2. Masking the key to unsigned breaks **`k[7]` only**, because the shift is **arithmetic on a signed 32-bit int**: `-1499435279 >> 28` = **−6**, not 10. Slots 0–6 agree either way, so the damage looks like a handful of wrong bytes (`demo_frame` → `dUmo_framU`) rather than noise — which is exactly why it survives a casual eyeball.

**Correct:** `key = int(m.group(2))` **unmasked**, `k[i] = (i + (key >> 4i)) & 0xFF`.
**Verified across all 1154 demos in the game: decode + re-encode byte-exact, zero failures.**
★ When a key misbehaves, **derive the schedule from known plaintext** (`_csv0`, `demo_frame`, `bg_swap`, …) — that is how this was found.

#### 11.2 ★ Edit `_cso_` payloads as bytes, never via decode/re-encode

The payload contains sequences **cp932 cannot represent**. `decode(errors='replace')` followed by `encode()` destroys them — either a `UnicodeEncodeError` or silent corruption. This is the same class of bug as the `WepVisible.fsv` shredding. **Split on `b'\r\n'`, splice the ASCII fields, rejoin** — the CSV is not fixed-width, so length changes are fine. **Keep the original key** so that an unchanged re-encode is byte-identical and diffs stay meaningful.

#### 11.3 ★ The CameraMotion pos/rot aiming dial

`_csv4` holds a **`CameraMotion`** event with `mot_name` (column 63), **`pos` (65)**, **`rot` (66)** and `scl` (67). `pos` and `rot` are **offsets applied on top of the baked motion** — the intended aiming dial. On pl005 they had always been `0,0,0`, which is why the camera looked un-aimed. **Re-authoring the `tmo1` is unnecessary.**

The subject shifts **opposite** to a camera translation: a subject high-and-left is centred by moving the camera **up and left**. ⚠ Sign conventions are undocumented — confirm with one launch.

**pl005's maxout camera, diagnosed 2026-07-27.** `_demo_cam` hash **`dd9a138125e5`** is **unchanged across every backup and matched by none of the 136 other demos** ⇒ it is his own camera, authored for sp000 as a boss, **not** a bad retarget. Berg's screenshot showed his head pinned to the top-left corner where Hiyori's is centred on her face. First correction applied: **`pos = -0.80, 0.45, 0`** (camera left + up). **Untested.**

### 12. Retargeting a demo from a donor

The planned and then executed retarget was **pl035 (Halibel) → pl005**. `pl035_ct_sp_break01` is **270 frames, 81 events, single cast `access0`**.

★★ **pl035 tokens in the CSV fall into two classes that must be treated differently:**

- **cast / model** — `pl035_cos01_00`, `_face00_00` (+ `_objects_a..e`), `_hair00_00`, `_wep00_00_00`/`_01`. These must become `pl005_*` so that **Zangetsu's model** is cast. Note that Halibel is `cos01` where he is `cos00`, and she has **two weapons** where he has a sword plus a visor (`wep00_00` / `wep01_00`) — **the mapping is not 1:1.**
- **motion / camera / voice** — `pl035_ct_sp_break01`(`_cam.tcm`), `pl035_ct_sp_break01_2_vo`/`_3_vo`. The motion and camera live **inside** the package (`_demo_mot`, `_demo_cam`), so rename the **inner entries and the CSV references together**: the package then carries **her animation under his names**, which is exactly the shape pl005's existing connect demo already has. Her `_vo` events do not exist for him; his are `sp000_ct_sp_break01_vo_1` / `_vo_2`.

⚠ **Unregistered model names are the classic `0xc0000005` crash** — verify every renamed cast name exists in `filename.bin` **and** `file_exist.htable` before launching.

**The graft, done 2026-07-27** (`graft_kikon_demo.py`, backups `.prekikon_bak`). `pl005_ct_sp_break01.tdemopkg` is now pl035's 270-frame cutscene cast with Zangetsu's model. Verified: **8 entries, zero `pl035` bytes left anywhere**, cam entry `pl005_ct_sp_break01_cam`, motions renamed, cipher round-trips.

★★ **The key enabler — the cast-row rule.** pl035's cast row and pl005's **already-working** `ct_syunpo_out_just` cast row are **structurally identical**: same ten slots, same bind joints. That makes the retarget a **field-for-field substitution against a layout proven to load for him**. ★ **Always diff the donor's cast row against a working row of the target's before writing names.**

Mapping actually applied:

| donor slot | donor value | pl005 value |
|---|---|---|
| costume | `pl035_cos01_00` | `pl005_cos00_00` |
| face / hair / `objects_a`–`e` | — | straight across |
| weapon (sword) | `pl035_wep00_00_00` | `pl005_wep00_00_00`, joint `weapon_R` |
| slot 9 | `weapon0_1` / `pl035_wep00_00_01` @ `thorax_weapon` | `weapon1_0` / `pl005_wep01_00_00` @ `weapon_R` |
| `_2_vo` / `_3_vo` | Halibel voice events | blanked |

Her second weapon slot is an **off-hand blade**; his is the head-mounted **visor** — hence the joint change.

★ **`pl035` → `pl005` is length-preserving**, so `_demo_mot`, `_demo_cam` and `demo_act0` take a **blanket byte replace** safely (fixed-width name fields, no offsets shift).

Alongside the graft, `sp_break01_1` was re-timed: six hits **38–44 → 259–265** (soul at 265), `Protect(0,265)`, `Cancel(272,-1)`, `ComboStart(272,272)/1`. **No combo-graph changes** at that point. Status recorded as **untested**, with the expectation that her camera would frame him badly the way the maxout one did — same `demo_cam.py` dial.

**Where the soul damage fires.** `1_normal_attack_sp_break01_1` has **39 blocks**: `Protect(0,100)`, `Cancel(100,-1)`, `ComboStart(100,100)/1`, and **six `Attack_Melee`** — the soul-damage one at **frame 44 with `soul_damage = 2`**, the other five at 38–42 with soul 0. To play a cutscene "before the soul damage", the action is re-timed so the demo overlays it and the soul hit lands at the demo's end. Hiyori's shape, quoted as the model: 300 f action, `Protect(0,170)`, `Attack@170`, `ComboStart(240,240)/1`, `Cancel(240,300)`.

**⚠ Re-timing without a working cutscene breaks the move.** Shifting `sp_break01_1`'s hits to 259–265 for a 270-frame demo that never plays put them **past the end of a ~100-frame action** → "the second hit missed and did no damage". **Reverted** to hits 38–44, `Protect(0,100)`, `Cancel`/`ComboStart` 100. ★ **Re-time only *after* a cutscene is confirmed playing.**

⚠ **Thin/contradictory note:** the memory file's "WHERE THE SOUL DAMAGE FIRES" section ends by stating that `pl005_ct_sp_break01` "is 300 frames today and **still references `pl052`** for its cast models" and that "no graph changes [are] needed". Both statements are contradicted by later, dated entries in the same file — the graft made it a 270-frame package with zero donor bytes, and the graph rename turned out to be required. Treat that paragraph as **stale**, retained only for the `soul_damage = 2` @ frame 44 datum and the Hiyori timing shape.

### 13. What actually makes a connect cutscene play

#### 13.1 The observation

Tested 2026-07-27: the Halibel demo was grafted correctly and **no cutscene played** — just the raw attack. The cause was found by diffing the two characters' break flows:

| | flow | id 50 node | its action |
|---|---|---|---|
| pl035 | `sp_break01_maxout`(56) → **`ct_sp_break01`**(50/51, AutoCombo) → `sp_break01_chain`(34) | `ct_sp_break01` | **`1_normal_ct_ct_sp_break01`** (category `ct`) |
| pl005 | `sp_break01_out`(56/89) → **`sp_break01_1`**(50, AutoCombo) → `sp_break01_chain`(34) | `sp_break01_1` | `1_normal_attack_sp_break01_1` (category `attack`) |

**Same id 50, same AutoCombo input, same predecessor and successor** — pl005's node simply sat in the `attack` category where pl035's is a `ct` one. **The engine resolves the action from the node name**, so a demo file with no matching `ct_` action is never reached.

pl035's `1_normal_ct_ct_sp_break01` contains: `Protect(0,170)`, `Attack_Melee(280,285)`, `Cancel(380)`, `ComboStart(380)`, `BlackOutAtmosphere(0,370)`, 3 `Effect_Loop`, and **2 `CameraFixedAngle`**. `CameraFixedAngle` only ever appears on `ct_*` actions, which is the signature of a cutscene action. pl005 had `1_normal_ct_ct_sp_break01_maxout` (so the *maxout* cutscene works) but **no plain `ct_sp_break01`**.

#### 13.2 Theory 1 — "a `ct` action needs no graph node" (tried, insufficient)

The evidence for it was genuinely good. Digging for the older v8–v14 failures on 2026-07-27 found that **no copy of those builds survives anywhere on disk** (every backup was overwritten; the oldest, `Zangetsu Patch/Files/.../pl005.tcmbpkg` dated 2026-07-23, predates them). But the backup chain showed something better:

- `pl005.tcmbpkg.pre_spstep_bak` contains a **`ct_sp_break01_maxout` NODE**; every version after it has **zero** — the node was deleted in the spstep pass.
- `1_normal_ct_ct_sp_break01_maxout` (the **action**) still exists and is a **one-block stub**: a single `Voice`, node `ct_sp_break01_maxout`, motion `1_normal\ct\ct_sp_break01_maxout`.
- **That cutscene still plays** — proven independently, because editing `pl005_ct_sp_break01_maxout.tdemopkg`'s camera visibly changed what Berg sees in game.

⇒ the inference: **the demo is bound to the `ct` ACTION by name, and the action is entered by engine event, not by graph traversal.** (pl035's own `ct_sp_break01_maxout` node is input `RecvEvent`, referenced by nobody — the same signature.) The visuals live entirely in the `.tdemopkg`; the `ct` action is just a hook.

**The low-risk experiment that followed** (`add_ct_stub.py`, backups `.prectstub_bak`): add `1_normal_ct_ct_sp_break01` as a **stub action** — act_data + clips + a minimal tadj modelled on the maxout stub — and **change nothing in the graph**, matching the Hiyori playbook's "NO graph changes". Two entries were added and **`.tcmbpkg` was never opened**:

- **tact act** `1_normal_ct_ct_sp_break01` = pl035's act with only its JSON key rewritten, so it keeps referencing `pl035_ct_*` clips (5 transplanted). *Precedent:* pl005's already-working `1_normal_ct_ct_syunpo_out_just` references `pl035_ct_sp_step_just` the same way — **`tmo_name` is fully qualified, so donor clips need no renaming.**
- **tadj** `1_normal_ct_ct_sp_break01` = a clone of pl005's own **maxout stub** (one `Voice` block, `sp000_ct_sp_break01_vo_1`), with `node`/`motion` retargeted.

⚠ pl035's **full** `ct` tadj was deliberately **not** imported: it carries its own `Protect(0,170)` + `Attack_Melee(280,285)` + cameras, which would have doubled up with `sp_break01_1`'s damage.

**Result: still no cutscene; damage played normally.** Then Berg confirmed **Hiyori (pl009) has no connect cutscene either.**

★★ **That killed the premise the whole plan rested on.** `roster-add-strings`'s "KIKON REDO PLAYBOOK" says to follow Hiyori — "NO ct nodes/entries … connect cutscene overlays it". **Hiyori was never actually verified to play one, and she does not.** A character with no `ct_` node in the graph cannot play a connect cutscene, full stop. **pl009's shape is not a working model; it is the same broken state pl005 was in.** That playbook section is **retracted**. The stub was reverted at Berg's call, leaving a clean baseline: tadj 59 entries / tact 87 acts / 93 clips, `sp_break01_1` hits 38–44.

**Eliminated along the way — all verified, do not re-test:**

- **The `.tdemopkg` file itself** — correct, and both pl005 and pl009 ship the **full** demo library (`ct_sp_break01`, `evo_ct_*`, `rev_ct_*`).
- **No tadj block type triggers a demo.** Every `ct_sp_break01` string in tuning data across all 40+ characters is an SE or voice name. **The binding is not in the tuning layer.**
- **The `ct_` action alone** — insufficient, even named and motioned correctly.
- The maxout/connect asymmetry (maxout plays with an action and no node; connect does not, with an action and no node) is best explained by the **maxout being fired by a hardcoded charge-complete event**, while the connect is reached only through the graph.

#### 13.3 ★★★ The solution — a `ct_` NODE

`try_ct_node.py` + `tune_pass17.py`, 2026-07-27. Berg: **"that worked. and it deals the soul damage."** This broke the v8–v14 wall.

**1. Rename graph node 50 `sp_break01_1` → `ct_sp_break01`.** Everything else about the node is untouched: `AutoCombo`, `nexts` 34, `is_before_hit` 1. pl035 has `ct_sp_break01` at the same id in the same slot.

**2. ★ THE TRAP: the rename changes which ACTION the node dispatches to.** `ct_sp_break01` resolves to `1_normal_ct_ct_sp_break01`, **not** `1_normal_attack_sp_break01_1` — so a bare stub would have played the cutscene and **silently deleted the soul damage**. The `ct` action must therefore be a **clone of `sp_break01_1`'s own tuning** (all six `Attack_Melee`, `Protect`, his voice) re-timed to the demo's end: hits 38–44 → **259–265** (soul at 265), `Protect(0,265)`, `Cancel`/`ComboStart` **272**. The donor supplies only the *animation* (its act, referencing `pl035_ct_*` clips).

**3. ✗ `CameraFixedAngle` is NOT the cutscene camera — tried and retracted.** The reasoning had been that every other character's `ct_sp_break01` carries them (pl000 has 4, pl003 has 4, most have 2) and pl005's had none. pl035's two were added — **no change at all** ("acts the same way as before") — and the counter-evidence was already on hand: **pl005's own working maxout cutscene has ZERO `CameraFixedAngle` blocks** (its `ct` action is a single `Voice`). They were removed again. They remain only-ever-found on `ct_*` actions, but they are not what makes a demo camera work. **The demo's own `CameraMotion` event is the camera.**

**4. The old `1_normal_attack_sp_break01_1` act + tadj were deleted** — unreachable after the rename, and leaving it is exactly the **stale-twin clash** that broke the hi01 whiff gate.

⚠ **Thin/contradictory note:** the memory file's heading for this section reads "A CONNECT CUTSCENE NEEDS A `ct_` **NODE**, AND A CAMERA BLOCK", but its own point 3 retracts the camera-block half. **The heading is stale relative to its body; the node rename is the whole fix.**

#### 13.4 The TCMB clash purge (same pass)

Removed orphan duplicates: **`atk_hi01` id 9**, **`atk_hi03` id 87** (orphaned once 9 went — 9 was its only referrer), **`atk_gr02_1` id 76**. **Zero dangling next targets** verified afterwards.

**Kept deliberately:**
- **`atk_gr01` id 74** — an orphan, but input **`RecvEvent`**, entered by engine event rather than by reference, and **pl000 ships the identical pair**. ★ **`RecvEvent` + orphan is the normal event-entered pattern. Do not "clean" those.**
- **`sp_break01_out` 56 / 89 / 90** — all referenced; 56 and 89 differ only in `push` (2 vs 4, two input variants), and 90 routes elsewhere.

**Clash audit** (Berg's ask, after the `atk_hi01` twin): pl005 has **no duplicate tadj or tact entry names**. The tcmb duplicates and their status: `atk_gr01` 74 (RecvEvent, orphan) / 5 · `atk_gr02_1` 76 (orphan) / 75 · `atk_hi01` 9 (orphan) / 85 · `atk_hi03` 87 / 7 · `sp_break01_out` 56 / 89 / 90 (all referenced). The genuinely stale ones were `atk_hi01` 9 and `atk_gr02_1` 76; hi01 id 9 had already been brought in line in pass 15.

### 13b. Kikon soul damage — one number per action, and the pair the player sees

`soul_damage`, on the `Attack_Melee` / `Attack_Bullet` block inside a `*sp_break*` action, is how many
konpaku a landed kikon takes. **There is one authored number and the player sees a pair: `n` on cast
and `n + 1` on soulbreak.** The engine adds the +1 itself.

The proof is in the project's own history rather than in theory. `BalanceChanges/LatestChanges.txt`
records for Yamamoto:

> Kikon soul damage : 5/6 -> 4/5 (cast / soulbreak), matching the normal Kikon tier

and diffing the two shipped game versions shows exactly what that edit was — one field:

```
GameVersions/Bleach Rebirth of Souls            pl016 2_evo_ct_evo_ct_sp_break02  soul_damage 5
GameVersions/…Community Patch                   pl016 2_evo_ct_evo_ct_sp_break02  soul_damage 4
```

★ **The other two soul fields are dead across the entire roster.** `charge_soul_damage` is `"0"` on
all 7659 occurrences and `enhance_soul_damage` is `"0.000000,0.000000,0.000000"` on all 7659. Do not
go looking for a soulbreak field; there isn't one.

Roster convention: base kikon 2, evo kikon 3, evo sublimation (`sp_break02`) 4, rev 4. Outliers are
rare — pl019 has a 6, pl027 a 5, pl002 a 99 on his `sp_break03_evo`.

**pl005's five soul-bearing blocks**, which is more than the "one per form" the convention suggests:

| form | entry | block | shipped | now |
|---|---|---|---|---|
| base | `1_normal_attack_sp_break01_1` | 1 `Attack_Melee` | 2 | **3** (3/4) |
| evo | `2_evo_ct_evo_ct_sp_break01` | 3 `Attack_Bullet` | 3 | **1** (1/2) |
| evo | `2_evo_ct_evo_ct_sp_break02` | 7 `Attack_Melee` | 4 | **1** (1/2) |
| rev | `3_rev_ct_rev_ct_sp_break01` | 3 `Attack_Melee` | 4 | **4** (4/5) |
| rev | `3_rev_attack_rev_sp_break01_1` | 3 `Attack_Bullet` | 2 | **4** (4/5) |

★ **pl005's base kikon is `1_normal_attack_sp_break01_1`, not `1_normal_ct_ct_sp_break01`.** Most of
the roster puts base soul damage on the `ct` action; pl015 (Halibel), which is where pl005's base
kikon was grafted from, puts it on the `attack` action. Searching for the `ct_` name finds nothing
and looks like the field is missing.

Both tiers of a form get that form's number, so "evo deals 1-2" is true of the sublimation kikon as
well as the normal one — otherwise evo's *best* kikon would out-damage base's, which inverts the
gameplan the whole fighting-spirit lock exists to protect. Everything in evo and rev here is still
Yhwach's (pl052) donor data; only the numbers are chosen.

`soul_damage_v1.py` applies it, entry-scoped against the live tadj, both `pl005.tadjpkg` and
`pl005_modded.tadjpkg`. Every value is one character wide so the blob length never changes and
`tadj_lib.build()` stays byte-exact; the script asserts that rather than assuming it.

### 14. Bug ledger

| # | symptom | wrong hypothesis | real cause | fix |
|---|---|---|---|---|
| 1 | Cast SP2 → locked in place, only `overatk` escapes | tcmb routing (`73→48` vs `73→35`) | missing 5,808-byte `act_data` entry in `Motion/pl005.tactpkg`; timeline runs against no motion | `sp2_fix_act.py` re-adds it |
| 2 | Mid-string hits whiff after an early hit | — | `reishi_blow_power 吹き飛び中` cloned from the hit-14 finisher onto **all 18 hits**; fires on reishi guard break → launch. Also `blow_free_speed +1.0` and `damage_move_rate 1.0/0.5` | 0.1 / −1.0 / 無し on all body hits |
| 3 | "SP2 auto-casts if I miss an attack; stuck in a loop" | gate fields missing | `ComboStart` at f20 == the `Attack_Melee` frame; `hit_combo_stop`/`guard_combo_stop` read "no outcome" | delete `73→80`, latch via `my_action` |
| 4 | "If I miss **any** move I enter a loop of casting sp_atk" | leftover of bug 3 | node 80 left as an **orphaned `AutoCombo`** — globally eligible from any `ComboStart` | delete nodes 80 and 81; re-parent 48 onto 73 |
| 5 | "It redoes the motion at the end" | a graph cycle / replay path | `end_frame -1` on a 220 f clip from f61 gave `sp_atk02_1b` a 106-frame dead tail with 3 stray SEs; V1.3's split made it reachable | `end_frame -1 → 114`, drop the 3 SEs |
| 6 | "I can step forward" during the burst tail | — | node 81 deleted ⇒ `ComboStart` resolves against nothing and falls through to neutral; cancel opened 7 f after last hitbox vs a shipped median ~40 | `ComboStart`/`CancelTiming` f195 → f199; later, Uryu's two-action recipe |
| 7 | `pl005.tcmbpkg` truncated to 0 bytes | — | `light_string.tcmb_read()`'s 2nd return is **bytes**, not a callable; `open(p,'wb')` had already truncated | `text.encode('latin1') + tail`; serialise → `.tmp` → `os.replace`; restored from `.presp2v15_bak` |
| 8 | White effect pass had no visible effect | recolour maths wrong | `P039_zw1_00`/`zw2_00` on disk but **absent from `file_exist.htable`** — stale Overlay copy-back | 8 rows restored; `register()` re-anchors on `P039_ss2_00` |
| 9 | Move is purple, not black | (nine successive hypotheses) | see §8 — `PointLight` tadj field, trigger-indexed colour, uncompressed LUTs, our own rim, a **BC7** colour map, `TPlt` palettes, `hit_effect` spawns, `Brig` clamping, five ramps wrongly called unreachable | terminal fix: pure black, 45 textures × 2 tiers, zero tinted |
| 10 | Big FPS drops | draw count / bank size | screen **fill** = sheets × sheet-area, driven by `07_shok` alone | §9.5 measured curve; `GeIC` + constant sheet size |
| 11 | Flicker + FPS drop persisting ~3 s after the move | "we released ten infinite emitters" (`RUNo = -1`) | particle **lifetimes** (`GeUI.Lif + LifR`) far exceed the emitter windows; plus `TL32 = 61` fade ×10 | halve `07_Spark`/`07_shok4` lifetimes; `TDs1` neutralised |
| 12 | Wave became "a tilted circle-ish" | — | `bSfP` 1 → 0 removed soft-particle fade on a `BAxs = 1` quad | restore `bSfP = 1` (1 byte per tier at `0x8D2BC`) |
| 13 | "Lost its mostly black, purple got much stronger" | a colour asset regressed | deleting the `TDs1` **slot** turned the refraction `Ptcl` pass into a **second colour pass** | rebase `.vfxb` on `.presp2v23_bak`; restore aspect at proven fill |
| 14 | Rim reads hot pink | a magenta texture somewhere | `white × Brig 2.0 × #B026FF` clamps R and B → `#FF4CFF` | `Brig` → 1.0 |
| 15 | Wave reads thin/flat | `scl` too small | `DwSz` X and Y easing curves diverge (1.67× vs 3.0×), so the sheet is thinnest when biggest | hold aspect: 0.750/0.417 → 0.800/0.800 |
| 16 | Density edit made it *worse* than the build it copied | — | `GeIC` written into the `parts→shok4` **leaves** instead of the three edges out of `07_E_point_shok` | key `GeUI` by (parent, **target**); assert `parts_total == 7` |
| 17 | Reverts didn't restore the look | "something else got changed" | `.bak` names used as a chronology proxy; `.vfxb` and `.vfxt` restored ~14 h apart → mismatched pair renders wrong *and* cheap | revert from **git** (`15d48cd` "CRE update") |
| 18 | Whole pl005 build silently reverted after a "community patch" install | the community patch | stale 234-file `Overlay/` snapshot from Jul 26 09:44 copied over the install | rebuild `Overlay/` before every release |
| 19 | Dry run reports "191 new, 0 updated" on an established tree | — | `sync_to_dev.py`'s `REPO_ROOTS` hardcoded a **per-session** Cowork mount id; `gv_root()` fell through to the dead legacy copy | glob `/sessions/*/mnt/...`; always dry-run |
| 20 | `_cso_` payload decodes to garbage, or to near-plaintext with a few wrong bytes | key format assumed unsigned | key is **signed**; `(\d+)` misses the minus, and masking breaks `k[7]` because `>>` is arithmetic | `int(m.group(2))` unmasked |
| 21 | Kikon demo grafted correctly, no cutscene plays | the `ct_` **action** alone suffices (from the maxout precedent); then `CameraFixedAngle` is the camera | node 50 sat in the `attack` category; the engine resolves the action from the **node name** | rename node 50 → `ct_sp_break01` + clone the real tuning into the `ct` action |
| 22 | "The second hit missed and did no damage" | — | hits re-timed to 259–265 for a 270 f demo that was not playing, on a ~100 f action | revert to hits 38–44 until a cutscene is confirmed |
| 23 | `0xc0000005` on launch (class of failure) | file corruption | unregistered model names in a retargeted cast row | verify every name in `filename.bin` + `file_exist.htable` first |

### 15. Retracted theories, consolidated

Each of these was believed, acted on, and disproved. None should be re-opened.

- **Routing:** that `sp_atk02`(73) → `sp_atk_k_chain`(48) was wrong. It is the 14-character majority and cannot affect a plain cast.
- **Gating the auto-cast:** `is_before_hit = 1` cannot fix a branch whose query frame equals the hitbox frame.
- **`RUNo = -1` = infinite emitters.** It is on **18,115 of 18,222** units game-wide; emitters are bounded by `Unit/Life`.
- **`Lif 200 → 60` on root→`parts1`** was **inert** (`OvLf = 0`; that unit's own `Life` was already 60). The tail died from the `07_Spark`/`07_shok4` halving.
- **Draw count as the cost metric.** The clean build had 964 draws, the laggy one 379.
- **`scl.z` as a screen axis / plane = `y × z`.** The plane is `x × y`; settled by V2.8's +50% change producing lag where +7% could not.
- **The `TCo*` colour-map theory.** Worst saturation 0.003 across all 8 maps, both tiers, every mip, all 3 formats; `Tex[4]` is RAW8 L8 and colourless by construction.
- **`TgUI` reachability as proof of non-use.** Five "unreachable" ramps were on screen. `Tbl` is the actual proof.
- **The additive-overdraw theory.** `DMod = 1` (alpha) on all six `07_*` passes.
- **Accumulation across casts / camera distance / connect count / hit-stop / `hit_shake_blur` / per-hit work / `T31_Unlock` leakage** as lag drivers — all killed by `sp2_bisect.py`.
- **"We removed the Sankt dome."** Never happened; the earlier removal was the *move name*, via `move_names_own_entry.py`.
- **The Hiyori kikon playbook** ("NO ct nodes/entries … the connect cutscene overlays it"). pl009 has no connect cutscene; her shape is the broken state, not the model.
- **`CameraFixedAngle` as the cutscene camera.** Adding pl035's two changed nothing; pl005's working maxout has zero.
- **"`injectEffects()` only copies `com`, so the bank never ships."** Later corrected — `injectFolder(..., fullFolder=False)` copies `00HIGH`/`01MIDDLE` wholesale. ⚠ The `_overlay_manifest.json` gap note was never reconciled with this.

### 16. Open items and untested state

**Untested / watch list (SP2):**
1. **Hit confirm is the one unproven mechanism** — `my_action` had only ever been observed on grabs. Fallback: set `HIT_CONFIRM='autocombo'` in `sp2_v11.py`. Failure is clean — SP2_1 ends in neutral, no lock. ⚠ Note this entry predates V1.5's node deletions, which removed node 81; the fallback as written assumes it still exists.
2. **SP2_1 has no `Protect`** (pl039's EX carries only `OffReverse`) — fully vulnerable throughout the wind-up. The biggest balance consequence.
3. SP2_1's travel hitbox does **0 damage** with 崩し removed — dead weight.
4. Hitstop budget ~**85 f** of freeze across 144 f.
5. `Afterimage` still ends at **f72** — the back half has no smear (cosmetic).
6. If the engine turns out to require a tcmb node for `sp_atk02_2b`, the character **freezes at f195**; `sp2_v18.py --revert` recovers.

**Superseded but retained — Berg's frame-by-frame spec** (global frames, ±3), kept because several later measurements are anchored to it:

```
f1    activation OK. wants slow_motion_rate +10% and MORE travel distance
f75   PURPLE APPEARS  (maps to ~burst action f5 once travel 0.45/0.5 + _1 20f + 1b 9f is unwound)
f103  purple at peak size — "washed purple", must be REMOVED or BRIGHT WHITE
f178  the multi-hit shadow attack should START here (delayed vs the hand motion)
f190  first hit connects — ONE wave only, then the rest one by one ACCELERATING, high stun
f389  attack should END -> ~60f recovery, hand held extended, last ~10f the retraction plays.
      INSTEAD a second sp_atk02_1-looking attack launches here. Pose must extend f190 -> f439.
```

★ The f75 purple is **not** the burst bank and **not** Sankt; the suspects were the `1b`/`_1` `Effect_Loop`s (`P039_zw1_00` `T03_SubHit`/`T04_handLight`, `P039_zw2_00` `T05_S_pk`), which start at f3 and are authored to f23/f43/f53 — they **outlive the 9-frame latch and keep growing**, matching "appears at f75, peaks at f103" exactly. This was later corroborated by timing: `P039_zw2_00` is fired by exactly two blocks, `sp_atk02_1` f0..20 and `sp_atk02_1b` f3..23, the second landing at **real f71.7** (Berg: appears f75), and `1b`'s f9 latch firing a 32-frame hitstop at **real f97.7**, so the shockwave keeps expanding through the freeze and peaks mid-hold (Berg: peak f103).

**Demo-side, still open:** the pl005 maxout camera correction `pos = -0.80, 0.45, 0` is **untested**, and the grafted Halibel camera is expected to frame him badly with the same dial available.

**Cross-project, still open:** the other dev's `Fnames` registers **121 model keys** for costume variants (`pl015_cos00_01`, `pl030_cos00_01` + weapons, `pl031_cos00_02`, `pl042_cos00_02`/`cos01_02`) whose **files do not exist on Berg's disk** — his crash was **version skew, not corruption**. ⚠ **Do not copy his file over ours:** we hold **30 keys + 9 manifest rows** he lacks, all pointing at files that **do** exist here, including `menu_pl005.tactpkg` (the select voice), `pl005_pic2` (the rev banner) and the whole `bg005_00` stage registration. A merge-and-verify tool was offered and **not yet built**.

**Sync state of record:** SP2 synced to dev 2026-08-06 (5 files: `pl005.tcmbpkg`, `.tadjpkg`, `_modded.tadjpkg`, `.tactpkg`, `Fnames/file_exist.htable`, plus a refreshed Overlay; MD5 live == dev == overlay; nothing new for `CREATED`, since the new action lives inside existing packages, and `CREATED` already includes the four `P039_zw1_00` assets). Effect banks synced 2026-08-08 (4 files: `P020_zan_blk_00.vfxb` × 2 tiers, `pl005.tadjpkg`, `pl005_modded.tadjpkg`). **Final ship 2026-08-09: 191 files identical, `Overlay/` 234 files, 0 stale.**

⚠ **Duplication note for future editors:** the source memory file contains **two near-identical copies of the V2.4 section** ("THE COST IS DRAWS × AREA" / "EFFECT COST IS `draws × AREA`"), with the same tables and the same conclusions. They do not conflict; they are one finding recorded twice.


---

## Part 6 — The unique gauge and the enhance state

pl005's HUD meter is the intersection of three systems that look like one and are not: a generic per-fighter float bank (`AddUniqueVal` / `UNIQUE_n`), a UI controller class family (`ActionCharaUniqueUI*`) driven entirely from the exe, and the engine's enhance (buff) timer. The single most expensive misconception in this area was assuming that the first of these feeds the second. It does not — **the enhance countdown drives the unique gauge**, and the `AddUniqueVal` meter is a parallel, purely data-side counter that nothing in the UI unit reads.

---

## 1. The generic unique-value system

### 1.1 The counters

Three generic floats exist on every fighter, exposed to the script layer as `UNIQUE_0/1/2` (tadj condition context) and `NOW_UNIQUE_0/1/2` (state context):

| symbol | fighter offset |
|---|---|
| `UNIQUE_0` | `+0x1A34` |
| `UNIQUE_1` | `+0x1A38` |
| `UNIQUE_2` | `+0x1A3C` |

The symbols are registered at `0x14039F42D` (tadj conditions, `UNIQUE_n`) and `0x14048F769` (state context, `NOW_UNIQUE_n`), alongside `MY_SIZE`, `TARGET_SIZE` and `ENHANCED`. Registration is not usage: DataChakka's corpus audit found **`MY_SIZE` occurs in no shipped `.tadjpkg` at all**, and two shipped typos that can never fire — `ARGET_SIZE` ×3 and `ENHANCDE` ×1.

### 1.2 The writer: the `AddUniqueVal` tadj block

Handler `0x1403B2A00`. It ships verbatim in `pl019.tadjpkg` (249 instances), e.g. in action `1_normal_attack_atk_da01`:

```
"AddUniqueVal"  str_a=""  f=(0.0, 12.0, 15.0)  memo=""  nfields=5
  unique_type_idx=1  add_unique_val=0.075  is_start_timing=1  is_val_set=1  is_end_reset=1
```

`f[1]`/`f[2]` are the active frame window. ⚠ DataChakka's audit warns that tadj's `f32×3` is **not** cleanly `[?, start, end]`: the first word is a `u32` flag (0, rarely 1), and 18.3 % of pairs have `end < start` beyond the −1 sentinel — so do not treat the triple as a guaranteed frame range when parsing other blocks.

**The 1-based index quirk.** `unique_type_idx` is 1-based. The handler accepts 1..11 and stores at `base + 0x1A40 + 4*(idx-1)`. Only indices 1, 2 and 3 are readable from script, and they read back as `UNIQUE_0`, `UNIQUE_1`, `UNIQUE_2` — so authoring index **1** and reading symbol **0** is correct and looks like a bug every time.

⚠ **The handler NEVER CLAMPS.** An unguarded `AddUniqueVal` counts unbounded, in both directions.

> **⚠ CONTRADICTION IN THE NOTES — unresolved.** `roster-add-unique-meter` and `bros-engine-offsets` both record `UNIQUE_0/1/2` at `+0x1A34/38/3C` *and* the handler's store at `+0x1A40 + 4*(idx-1)` — i.e. `unique_type_idx = 1` writes `+0x1A40`, twelve bytes past `UNIQUE_0`. Both cannot be literally true of the same base pointer. Three candidate reconciliations: (a) the handler's `base` is not the fighter base used elsewhere; (b) one displacement was transcribed one array off — this neighbourhood is a run of parallel 3-float arrays spaced `0xC` apart (`+0x1A10` remaining time, `+0x1A1C` configured max time, `+0x1A28` per-level max value, `+0x1A34` per-level current value, so `+0x1A40` is simply the next one in the series); (c) both are right and `AddUniqueVal` writes an array the `UNIQUE_n` symbols do not read, which would break the read-back plan outright. Weak corroboration for `+0x1A40` being a real base: pl020's once-per-match counter flag sits at `+0x1A5C` = `+0x1A40 + 4*7`, i.e. exactly `unique_type_idx = 8`, inside the handler's 1..11 range (this arithmetic is my observation, not something the notes assert). **No note in this set records the read-back proof ever being run in game**, so this is genuinely open.

### 1.3 The reader: `str_a` on any tadj block

`str_a` was documented in earlier project notes as "usually empty" and treated as a spare field. **It is a full boolean expression** evaluated as a gate on the block. Observed operators: `<  <=  ==  >=  >  &&`, with `||` in the wider gate corpus (53 distinct gate strings across the roster, 14 predicate tokens).

Shipped examples worth copying:

```
pl020  StepDashAddMove   0<=UNIQUE_0&&UNIQUE_0<1
                         1<=UNIQUE_0&&UNIQUE_0<4
                         4<=UNIQUE_0&&UNIQUE_0<=5
                         UNIQUE_0>=6                  <- four dash distances off one counter
pl016  AddUniqueVal      UNIQUE_1<1                   <- ★ THE SHIPPED CLAMPING IDIOM
```

Because the handler never clamps, pl016's pattern — gating the `AddUniqueVal` block itself on the counter's own value — is the only bounded-counter idiom the game ships. pl016 also ships `add_unique_val = -0.025`, which only makes sense as accumulate rather than assign.

⚠ **`is_val_set` polarity is uncertain.** A static read says `1` = assign, but every shipped block uses `1` and pl016's negative delta implies accumulate. **Do not reason about it — copy the shipped five-field set verbatim and change only `unique_type_idx` and `add_unique_val`.** (DataChakka's newly identified `.tadjdbpkg` = `AdjDataBase` is the schema `.tadjpkg` is written against, carrying every enum a tuning field can take plus a Japanese memo per value; it is the obvious place to settle this, and the notes do not record it having been consulted for `is_val_set`.)

pl005 already carries a leftover from the Yhwach graft: an `Effect_OneShot` gated `NOW_UNIQUE_2==9999999`. Harmless — permanently false.

### 1.4 Other readers

`Script/BattleFlowCondition.fsv` exposes `GUAGE_RATE,<player>,<source 4|5|6>,<min>,<max>`; the gauge-source switch at `0x140124B24` cases 4/5/6 read those three offsets. AI code at `0x140532DA0` and `0x140534E80` reads `+0x1A34` with `cvttss2si`, i.e. as integer stacks. **Both the 0..1 rate convention and the 0..6 integer convention are shipped and valid** — the counter has no canonical scale.

### 1.5 Yhwach is not a reusable recipe

`pl052.tadjpkg` contains **zero** `AddUniqueVal`. Kaiser points are `ActionCharaUniqueUI_Pl52` plus bespoke exe code, the same pattern as Aizen (`0x1401EEC25`: `cmp [rax+0xC00], 0x14`). What *is* reusable is the generic system twenty other characters use. Two adjacent dead ends, recorded so nobody re-walks them: `CharaStatus.fsv` columns 34–45 (`unique_val1..12`) exist for exe-hardcoded logic and are **all zeros for both pl052 and pl005**; `Script/Unique_pl039Param.fsv` (Szayel) is the only bespoke per-character table and is loaded by a hardcoded name.

---

## 2. `ActionCharaUniqueUI*`, fully reversed

Four parallel RE passes on 2026-08-10, all read out of the shipped exe (image base `0x140000000`, `.text` VA = file offset + `0xC00`). Long-form write-up lives at `Zangetsu Patch/Zangetsu Documentation/UNIQUE_GAUGE_UI_REVERSED.md`.

### 2.1 Hierarchy (from RTTI)

```
ActionCharaUniqueUIBase      vft 0x14143FEF0   24 slots   sizeof 0x10   { vptr; Work* }
  ActionCharaUniqueUIGauge   vft 0x14143F230   36 slots   sizeof 0x18   { +0x10 vector<Elem>* }
    ActionCharaUniqueUI_Pl38 vft 0x14143FB78              sizeof 0x20   { +0x18 icon ObjRef* }
  ActionCharaUniqueUICom     vft 0x14143FA50   (case 23, the default; Init 0x1402086F0)
  ActionCharaUniqueUIComIcon vft 0x14143FDC8   (discrete stack icons; Pl03/04/16/29)
```

`ActionCharaUniqueUIComIcon` has a generic art fallback at `0x140208DAD`, so a character landing on it gets neutral art rather than another character's face.

⚠ **`[this+0x10]` is a vector header, not the gauge.** The element array is `gauge = *(Elem**)(this+0x10)` = `&elem[0]`, stride **`0x240`**. Element count comes from `initParam+0x30`, which is **always 0 ⇒ exactly one element for every character**.

### 2.2 `Work` — 0x118 bytes at `[this+8]`

Populated by `Base::Init 0x140205740` straight from the init param: `Work[0x00] = param[0x08]` (owner, the side HUD object) · `Work[0x08] = param[0x00]` (**side**) · `Work[0x40] = param[0x10]` (**chara id**). Also `+0x34/38` max/value · `+0x3C` visible · `+0x44` form fallback · `+0x68` layout ObjRef · `+0xB0` attach bone · `+0xD0` fighter ObjRef · `+0xF0` cached `Chara*` · `+0x110` its control block.

⚠ **`Base::Init` does not store a chara pointer, and vtable slots 20/21/22 have zero direct callers** (they are only ever reached virtually). `Work+0xF0` must be treated as unavailable. The dependable fields are `Work+0x08` (side) and `Work+0x40` (chara id). The side HUD object carries `+0x1F0` chara id, `+0x1F8` uiId, `+0x200` controller — **there is no `Chara*` anywhere on the UI side**. ★ This single fact dictated the whole pl005 design: to reach the fighter from a controller you must go the other way and hook the enhance timer, which has the chara in `rsi`.

### 2.3 `Elem` — 0x240 bytes

| offset | field |
|---|---|
| `+0x00` | bar ObjRef |
| `+0x20` | node ptr |
| `+0x48` | line ObjRef |
| `+0x90` | mode (1 = show, 5 = hide) |
| `+0x94` | state (0 idle → 1 begin → 2 loop → 3 full-in → 4 full-loop → 5 out) |
| `+0x98` | **full / hold flag** |
| `+0x99` | allow-flourish |
| `+0x9A` | **colour-dirty flag** |
| `+0x9C` | value |
| `+0xA0` | max (1.0) |
| `+0xA4` | cached `(int)value` |
| `+0xB0 .. +0x130` | **nine RGBA float4 colour slots** |
| `+0x140 .. +0x23F` | four SE cues — `gauge_in` `+0x178`, `gauge_out` `+0x1B8`, `gauge_full_in` `+0x1F8`, release `+0x238` |

Ikkaku's second bar segment writes its colour at `gauge+0x2F0`, which is `0x240 + 0xB0` — element 1's slot 0.

### 2.4 ★★ How the bar colour is chosen — draw push `0x1402075A0`

```
iv = (int)value
k1 = clamp(iv-1, 0, 8) -> material "gauge01" (earned backdrop) takes colour[k1].rgb
k2 = clamp(iv,   0, 8) -> material "gauge02" (partial overlay) takes colour[k2].rgb
fill: "gauge01".param[8] = (1-clamp(value,0,1))*0.5 ; "gauge02" likewise on the fraction
pushed only when (int)value CHANGED or +0x9A is set; then +0x9A is cleared (0x140207DB1)
```

Only `.rgb` is read — **alpha never is**. With `max = 1.0` the value stays in `[0,1]`, so `k1 = k2 = 0` and **only colour slot 0 is ever visible**. Raising `max` (via slot 24, `0x140208300`) unlocks slots 1..8: **segments = max, one colour per segment** — that is how Ikkaku gets a two-segment bar. ⇒ Per-frame colour control is the *intended* protocol: write `gauge+0xB0`, set `gauge+0x9A = 1`. pl038's `Update` does exactly that every frame (`0x1402156BE` / `0x1402156CC`).

`Base::Init` preloads five slots: cyan `#22BBC5`, blue `#2262C5`, yellow `#DED64C`, orange `#E66D36`, magenta `#AF008F` — which is why any character on the generic controller reads blue in every state. Grimmjow's `Init` (`0x140215390`, case 18) instead writes two float4s and the custom-colour byte:

```
+0xB0  (0.1176, 0.3922, 0.6863, 1.0)  #1E64AF  BLUE
+0xC0  (0.8627, 0.2353, 0.2039, 1.0)  #DC3C34  RED
+0x9A  colour-dirty / use-custom-colour
```

⚠ Grimmjow's red flip is gated on the element's **full flag (`+0x98`), not the enhance level**. The red constant is loaded from `[0x1414C2220]`.

### 2.5 Vtable — 36 slots (Base / Gauge / Pl38)

```
 0 dtor           0x140205640 / 0x140206F80 / 0x140215210
 1 Init           0x140205740 / 0x140207050 / 0x140215390
 2 Update(float in xmm1 — DEAD, nothing reads it)
                  0x140205CF0 / 0x140207490 / 0x140215510
 3 Term           0x140205D40
 4/5  appear / disappear          6/7  aux float
 8 SetMax         9 SetValue
10 SetRate(0..1)  0x140205EA0 / 0x140208360     <- what the enhance timer calls
11 IsFull        12-15 getters   16/17 visible
18 node setup     0x140205FE0
19 GetCharaId    20 SetCharaRef 0x140206560    21 SetFormFallback
22 GetForm        0x1402065C0
23 GetNodeNameRemapTable  0x140206B40 / 0x1402152D0   (the L->R mirror list)
24-31  the indexed …At(v,i) forms  0x140208300 … 0x140208560
32/33/34/35  ShowAt / ShowNowAt / ShowNow / HideAt
```

**pl038 overrides exactly six slots: 0, 1, 2, 23, 25, 26.** `Pl38::SetValueAt 0x140215790` is the freeze (frozen while `+0x98`; only an exact `0.0f` clears it, without writing). `Pl38::SetRateAt 0x1402157E0` calls the base implementation unconditionally, then clears `+0x98` on `0.0f`.

`pl038::Update 0x140215510` in full — the template every custom controller copies:

```
rdx = *(void**)( [this+0x10] )                 ; gauge elem
if ([rdx+0x98] == 0) goto notfull
   icon = LockHandle(&tmp, [this+0x18])
   if (IsAnim(icon->node, "loop1"))  PlayAnim(icon->node, "level_up")
   ... release, then movaps xmm0,[0x1414C2220] (red) -> gauge+0xB0, +0x9A = 1
notfull:
   if (IsAnim(icon->node, "level_up")) PlayAnim(icon->node, "loop1")
   ... blue
tail 0x140215718:
   if (AnimFinished && IsAnim("level_up")) PlayAnim("loop2")
```

### 2.6 Lifecycle

`0x14021DC20` (called from `0x1401F8A5B`) walks the two side objects in the 2-entry array `g_battleUi` at `0x141CDE758`. For each: `charaId = [obj+0x1F0]` → a stride-`0x50` table lookup at field `+0x38` yields the **uiId**, stored at `[obj+0x1F8]`. That uiId is what **both switches** index. The factory result (`0x14021EE30`) is stored at `[obj+0x200]` by `0x14021E185`. Teardown is `0x1401F8A90` (slot 3, slot 0, then `[obj+0x200] = 0`).

InitParam is 0x38 bytes at `rbp-0x40`: `+0x00` side (XOR the swap flag at `0x141CDE72D`) · `+0x08` owner · `+0x10` charaId · `+0x18` `"ui_reiryoku_L00"` · `+0x20` variant 0 · `+0x28` `"j_unique_gauge00"` · `+0x30` elemCount ptr (always 0 ⇒ 1).

pl038's factory case body runs `0x14021FB1C`–`0x14021FBA8`: `new(0x20)` → `Base::ctor 0x140205540` → install Gauge vft → `new(0x18)` vector → install Pl38 vft → `new(0x48)` icon ObjRef → a **direct, non-virtual** `call 0x140215390`.

### 2.7 ★★★ The call vocabulary a controller has

| VA | primitive |
|---|---|
| `0x140206A30` | **`FindNode(this, out, &std::string name, uint32 index)`** — ★ the index argument is how Yhwach gets nine icon slots and Aizen/Starrk five from one name; applies the side mirror via slot 23 |
| `0x140095410` / `0x140092790` | AssignHandle / LockHandle (validity `[ref+0x40] && [[ref+0x40]+8]`; node ptr `[ref+0x20]`; release `lock xadd [ctrl+0xC],-1`) |
| `0x1401CC2D0` | IsAnim |
| `0x1402278B0` | PlayAnim |
| `0x1401FE4B0` | ★ **`PlayIfNotCurrent(ObjRef*, anim, variant)`** — the one-call primitive most classes use (⚠ consumes a locked ref) |
| `0x14022A4B0` / `0x14022A180` | SetFlag (CRC maps at `obj+0x1B38` / `+0x1B28`; `"Normal"`, `"Demo"`, `"ScreenEffect"`, `"Wipe"`, `"BottomL/R"`) |
| `0x140224520` | AnimFinished |
| `0x1402243A0` | GetAnimFrame |
| `0x1401FEBD0` | ★ **`SetTextureByName(node, tex)`** — Hisagi cycles four icon textures; Aizen uses `pl020_ex_L00..05` |
| `0x140222510` | ★ **`FindMaterialParam(node, name)`** → slot index; write floats at `[buf+idx+8]` |
| `0x140224700` | ★ **`SetMaterialColorRGB(node, index, r,g,b)`** — ints 0–255 ÷ 255, writes `[obj+0x19b0] + index*32 + 0x10`, bounds-checked |
| `0x1402213C0` | MatrixExtractScale |
| `0x1401FE7E0` | ApplyJointTransform |
| `0x1400F2AD0` | number → string |

Node vtable: `+0x128` named-joint matrix, `+0x318`/`+0x328` commit after SetAnim, `+0x370` child texture.

**Animation alphabet across the 23 classes:** `in/in1/in2`, `on`, `out`, `loop`, `loop1/2/3`, `loop30/60/100`, `gray_loop`, `normal_loop`, `level_up`, `level_max(_loop)`, `gauge_full_in`, `full_charge_loop1`, `count_up(30/60/100)`, `shake`, `ura_in/out/shake`, `mayu_in/out/shake/loop`, `release_in/loop`, `almighty_in/loop`, `weapon{1,2}_color{1,2}_loop`, `weapon_change`, `loop_on/off`. Variant is always `"Normal"`. ★ pl024 (Kyoraku) drives `loop1`/`loop2`/`loop3` on one node, so three states per node is shipped — but ⚠ per-element, verify before relying on it (see the `loop2` bug below).

Capabilities proven by the 23 shipped classes: multi-instance nodes from one name (Yhwach 9, Aizen/Starrk 5) · runtime texture swap (Hisagi, Aizen) · runtime material tint and shader constants (Aizen `rei_gauge01`; Nelliel four thresholds on `j_gauge_LL1..4`; Harribel `[node+0x4C] = 1/2/3`) · extra segments (Ikkaku) · two custom colours · digit readouts (`%02d` into `num00`/`num01`) · form gating (Aizen `form==2` → `ura_*` vs `mayu_*`) · an extra vtable slot (Yhwach alone, slot 24 `0x14021C910`).

---

## 3. The asset side: twelve files, two groups

Every character with a unique gauge owns two `filename.bin` groups, one per side (`_0` = LEFT/P1, `_1` = RIGHT/P2):

```
UIActionUniquePlNNN_0
    ui\                ui_ActionUniquePlNNN_0_fnt .cat      284 B
    ui\                ui_ActionUniquePlNNN_0_mot .cat      ~20 KB
    00HIGH/ui\         ui_ActionUniquePlNNN_0_mdl .cat      ~1.5 MB
    ui/script\scene\   ActionUniquePlNNN_0 .bin   "Scene"   366 B   node tree
    ui/script\anim\    ActionUniquePlNNN_0 .bin   "Anim"    503 B   which anim each node plays
UIActionUniquePlNNN_1   ... identical, side 1
```

Five registered entries per side = ten registered, **twelve files on disk** — the `01MIDDLE` mdl pair exists on disk but is deliberately **not** registered, because the quality tier is substituted at lookup time (which is also why only `00HIGH` ever appears in the manifest). 47 such groups ship; pl005's two make 49.

DataChakka's `UiScreenLayout.h` says a UI screen is up to **seven** files — the four above plus `ui/script/event/<S>.bin` (28 ship) and `ui/script/variable/<S>.bin` (18 ship). No `ActionUnique*` screen has either, so a gauge clone needs only five.

★ **A clone is only three renames per side.** The scene `.bin` opens with the three resources it needs (`_mdl`, `_mot`, `_fnt`); rewrite those three references and nothing else. The anim `.bin` contains no character name at all. ⚠ **Leave `ui_plNNN_unique_icon_L00`/`R00` alone** — those are hardcoded string literals in the exe (file offsets `0x143D1E0` / `0x143D200` for pl038) that the *controller class* binds its icon by, so renaming them breaks the binding.

### 3.1 The two switches, and the data-driven id in front of both

```
switch A  fn 0x14021CD90   byte tbl fo 0x21CD94   dword tbl fo 0x21CD34 (24 entries) -> LAYOUT NAME
switch B  fn 0x14021EE30   byte tbl fo 0x21F350   dword tbl fo 0x21F2F0             -> CONTROLLER CLASS
```

The byte tables are **byte-identical**, 51 entries, indexed `uiId - 2`; `0x17` (23) is the default (`ActionUniqueCom_` / `ActionCharaUniqueUICom`), `0x16` (22) is pl052. pl005's byte sits at **fo `0x21CD97`** in switch A and **fo `0x21F353`** in switch B. **Patch both or you get one character's art driven by another's behaviour.**

Each dword table butts directly against its byte table (`0x21F2F0` → `0x21F350` is 0x60 = 24 entries), so a 25th case must relocate the dword table into a cave and repoint one `disp32`: `mov ecx,[r8+rax*4+0x21D934]` at `0x14021CDDB` for switch A (note `0x21CD34 + 0xC00 = 0x21D934`, i.e. the displacement is the RVA of the same table), and the equivalent at `0x14021EEB2` for switch B. `ui_gauge_v6_ownslot.py` is the worked example.

★ **`uiId` is not the fighter id.** At `0x14021DAF5`:

```
movsxd rax, [obj+0x1F0]                 ; chara id on the side HUD object
mov    eax, [table + rax*0x50 + 0x38]   ; per-character table, stride 0x50, field +0x38
mov    [obj+0x1F8], eax                 ; <- the uiId both switches index
```

(`roster-add-unique-gauge-ui` writes this as `fighter+0x1F0`; `bros-unique-gauge-ui-internals` corrects the object to the side HUD object at `g_battleUi`.) So there is a **data-side lever** for redirecting a character's entire unique UI without touching `.text` — the source file backing that stride-0x50 table has not been traced. For pl005 the value is 5, proved by patching `byte_table[3]`.

`0x14021DA90..` stores the layout name at `uiScene+0x68` for each player; `0x14021DC20` composes the group name as **`"UI"` + layoutName + side** and walks the group's entries, dispatching on the triple's third column (`"Scene"`, `"Anim"`, `"Variable"`). Each resource is looked up in `AVResourceManager` by `0x140898EE0`; on a miss `0x1401135C0` logs **`"resource not loaded in this scene [%s]"`** and returns an empty handle — a second silent, crash-free failure layer stacked on top of the manifest's.

### 3.2 The `.cat` container and its contents

`PZZE` + `cat` + zlib — the same container as `.vfxb`, so `actpkg.unwrap` already reads it. The section table is relative to `0x100`; the manifest is two lists in different orders, which is why 76 names map onto 326 textures. The texture manifest is plain CSV. Material tint lives in slot-5 params in the asset; `_mot.cat` animates joint SRT only, with no colour tracks. (DataChakka: `.cat` is **three unrelated formats discriminated by `+0x0C`**.)

```
manifest  pl038_0:  ui_cha_unique_gauge00_L, ui_gauge_line00, ui_pl038_unique_icon_L00
          Com_0:    ui_gauge_line00, ui_cha_unique_gauge00_L, ui_com_unique_icon00
layers    gauge_base  gauge_base_efe00  gauge_gray  gauge01  gauge02  gauge03_efe
          gauge04_scr_efe  full_efe00  gauge_efe00/01/02  gauge_in_efe  glitch_add
          line_b  line_f0  line_f1  line_f2
joints    j_hp_top  j_gauge_LL  j_gauge_LR  j_icon00  j_icon01  j_full_efe00
          j_full_u  j_full_d  j_gauge_in_efe  j_glitch  j_p011_top
          j_gauge_01 .. j_gauge_11            <- per-segment addressing, already built in
anims     default  pers  gauge_full_in  loop1  full_charge_loop1  gauge_in  gauge_out  loop
          level_up                              <- ONLY pl011 / pl038 / pl050
```

★ **The bar and the segment lines are shared assets; the only per-character piece is the icon.** In pl038's set the string `pl038` appears at just six byte offsets in the 11.5 MB payload — `0x22f`, `0x25c`, `0x27d80`, `0x27d8a`, `0x27d94`, `0x27dfb` — all length-matched to `pl005`, so a repaint-free clone is a six-site in-place swap. The eleven `j_gauge_NN` joints plus the `gauge_gray` layer make this widget the natural home for a segmented Complete Moon stack display.

⚠ `ui_reiryoku_buff_L/R` — the small bar on the reishi gauge, in the 266 MB shared `ui_Action` package, bound under `ui_reiryoku_L00` at joint `j_buff` — has only ONE anim state (`buff_loop`), so it cannot be recoloured per character, and renaming its manifest entry **crashes the game (0xc0000005)** because it is live and looked up by name.

---

## 4. ★★★ The `filename.bin` group-key finding

This cost a full day and is the headline lesson of the whole gauge build.

### 4.1 The real format

DataChakka had it written down cold in `decomp/formats/FnamesVfs.h`:

```
file      := u32 groupCount; group[groupCount]
group     := str name;  u32 dirCount;  directory[dirCount]
directory := str name;  u32 fileCount; triple[fileCount]
triple    := str basename; str extension; str LOGICAL NAME
str       := u32 len; char text[len]; NUL
```

**There is no 13-byte header.** What the project's `fnames_patch.parse_manifest` called a header is `groupCount` (4 bytes) + group 0's empty name (5 bytes) + group 0's own `dirCount` (4 bytes). Group 0 is the empty-named group and holds **248 of the 3,555 directories and 24,673 of the 28,586 entries** — every stage and character asset. That is why every caller passes `""` as the group and why a flat, group-blind reading works for almost everything.

### 4.2 The key is `hash(groupName, logicalName)`

Entries are inserted by `0x140699070`, called from `TAppRootTask::InitFileNameInfo`, into the map at `.data 0x141CF2B68`. Resolution runs `0x14069ACF0` → `0x14069A410` → `0x140698A70` → `0x140698130` (directory + basename + extension, with the quality tier substituted at the very end — which is why only `00HIGH` is ever registered). **A miss returns the empty string, silently. No crash, no log.**

⇒ **Registering a file in the wrong group is, on disk, indistinguishable from registering it right.** There is no validation pass, no assertion, no warning. The only observable difference is that the asset never appears.

### 4.3 What that looked like in practice

pl005's twelve UI files spent a day registered inside **pl038's** groups, because `add_file` locates a directory node *by name* and there are **91 different nodes called `ui\`** — one per group. The in-game symptom was *"the buff and cooldown work, no gauge appears, no crash"*, which is exactly and only what a silent name-resolution miss looks like.

### 4.4 Adding a group (first time on this project)

`ui_gauge_v8_package.py` is the worked example. The invariants it asserts, which held on stock and after the change:

```
u32 @0  == 1 + (number of named groups)      # groupCount; 1154 stock -> 1156 with pl005's two
u32 @9  == number of group-0 directories     # 248 stock, 249 live (an earlier pass added one)
```

Adding two groups means **bumping `u32 @0` by two**. Every earlier pass only ever appended triples to existing directories, so that word had never had to move, and nothing in `fnames_patch.py` touches it.

`file_exist.htable` needs no change when only the grouping changes — it gates **paths**, and the paths do not move. **The two tables are not interchangeable:** `file_exist.htable` grants a path's existence, `filename.bin` resolves a logical name to a path, and a file needs **both**.

This reconciles a DataChakka audit correction that had previously looked like a contradiction: *"`Fnames/filename.bin` is NOT a blanket load gate"* — directly tested, `tex0.lds` and stage thumbnails have no entry and load fine. The reconciliation: **assets resolved by logical name need the manifest; assets loaded by direct path do not. `file_exist.htable` is the real existence gate.**

### 4.5 The lesson

Three rounds were spent proving the exe patch was correct — disassembling every rel32, checking section flags, confirming only one instruction reads the switch table — when the patch had never been in doubt and the *registration* had. **When a change is "correctly applied and does nothing", check the consumer's data model before re-verifying the producer.** And check DataChakka's `decomp/formats/*.h` first: `FnamesVfs.h`, `UiScreenLayout.h`, `UiIconRegistry.h`, `PzzeContainer.h` and `CsoTable.h` are decoded, verified against this install, and would have answered this in ten minutes.

---

## 5. Why pl005 owns his gauge, and what the borrowed path would have been

### 5.1 The two-byte version that was planned first

The original plan (from `roster-add-unique-meter`) was to hand pl005 Yhwach's entire unique-meter UI by writing `0x16` over `0x17` at file offsets `0x21CD97` and `0x21F353` — two single bytes, both `.cat` containers already existing and already registered, so no `filename.bin` or `htable` work at all. A useful de-risking observation supported it: **pl003/004/016/029 all have an `ActionUniquePlNNN_` layout name with no container shipped, so a missing container is tolerated, not a crash.**

### 5.2 The risk that was flagged, and how it actually resolved

The plan carried an explicit kill risk: **no read of `+0x1A34/38/3C` exists anywhere in the `ActionCharaUniqueUI` unit** (`0x140205000`–`0x140222000` scanned across all six displacements, zero hits). The fear was that a borrowed HUD would render and sit at zero.

It renders and it is *not* zero — but it is not the `AddUniqueVal` meter either. See §7.2: the gauge is fed by the enhance countdown. **The `UNIQUE_n` meter and the unique gauge are unrelated systems that happen to share a name.**

### 5.3 Why borrowing was abandoned

Three independent reasons, all recorded:

1. **Behaviour.** pl038's `Update` has exactly two states, chosen from the element's **full flag** (`+0x98`), not the enhance level. "Blue while buffed, red during cooldown" is not expressible with borrowed logic. `level_up` is referenced by only pl011, pl038 and pl050 at all — it is an exe capability, not a data one.
2. **Ownership.** Berg wanted pl005 to own his gauge (blue buff bar, red cooldown bar, and later Complete Moon stacks in evo/rev), which means his own `UIActionUniquePl005_0/_1` groups and his own art, not pl038's containers.
3. **Coupling.** Borrowing forces both switches onto another character's case, and the icon node name is a hardcoded exe literal, so the borrowed character's name has to stay embedded in pl005's assets.

### 5.4 ✅ What actually shipped (2026-08-10)

pl005 has his own layout and his own gauge logic, confirmed working in game. The split is deliberate and asymmetric:

* **Switch A got a real 25th case** (relocated dword table into a cave, one `disp32` repointed) so pl005 resolves his own layout name and therefore his own two asset groups.
* **Switch B was left pointing at pl038's controller class**, and the behaviour was replaced by hooking pl038's `Update` and guarding on chara id. *"We did not need it"* — a second table relocation was cheaper to avoid than to do. **Consequence: pl005's shipped gauge assets still carry pl038-named icon nodes internally**, because pl038's `Init` still runs and binds by that literal.

`ui_ctrl_v1_ownlogic.py`:

| item | value |
|---|---|
| `.rdata` characteristics | `R--` → `R-X`, `0x40000040` → `0x60000040` at fo `0x2D4` |
| cave | 1 KB at fo `0x13A1700` / VA `0x1413A2300`, inside the 8,211-byte zero run at `0x13A16C5` |
| hook 1 | fo `0x48BFD8` — 5 bytes over `mov ebx,1` (VA `0x14048CBD8`, the enhance-timer loop top) |
| hook 2 | fo `0x214910` — 7 bytes over pl038's `Update` prologue (VA `0x140215510`) |
| driver | 589 bytes at cave + `0xC0` |
| guard | 37 bytes at cave + `0x340` |
| bar colours | neutral `#FFFFFF`, enhanced `#78BEFF`, cooldown `#DC3C34` |

Hook 1 is the load-bearing one, because the chara pointer is in `rsi` there and the UI side has no `Chara*` at all. Inside the cave: save volatiles, `and rsp,-16; sub rsp,0xC0`, guard `[rsi+0xC00] == 5`, bounds-check `[rsi+0xC20] < 2`, walk `g_battleUi[slot] → [0x200]`, read `[rsi+0x1098] & 7`, pick state (bit1 → 1 enhanced, bit0 → 2 cooldown, else 0), ⚠ **spill the state to `[rsp+0xB0]` — `r10`/`r11` are volatile and do not survive the calls** — write `movups [elem+0xB0], colour[state]` and `[elem+0x9A] = 1`, rebase `[chara+0x1A1C] = 1200.0` while in state 2, reproduce pl038's three-way icon logic, restore, `mov ebx,1; jmp 0x14048cbdd`.

Hook 2 is guarded on `[[rcx+8]+0x40] == 5` (that is `Work+0x40`, the chara id) so Grimmjow keeps his exact behaviour.

Project exe-patch discipline applies throughout: every operation is recorded in `Patch_Dev_Environment/.../Exe/exe_patch.recipe` (100 ops), **replaying the recipe from the stock Steam binary must reproduce the live exe byte-for-byte**, caves use rip-relative addressing only (no absolute image addresses, ASLR-safe), the pre-existing cave at VA `0x1411B4BB0` / fo `0x11B3FB0` (~936 B, used by the move-name patch) must not be collided with, and ⚠ the mount refuses `O_TRUNC` on the exe — write in place with `r+b` seek-and-write.

---

## 6. The moon icon

Done 2026-08-09 immediately after the gauge started drawing. Brief: replace Grimmjow's face with Zangetsu's moon, white / blue / red, *"as if Tamsoft made it"*. Shipped as `ui_icon_v2_moon.py`, then `ui_icon_v4_moon.py`.

### 6.1 The container

```
ui/…/ui_ActionUniquePlNNN_S_mdl.cat
  = "PZZE" + "cat\0" + u64 decompSize + u64 dataOff(24) + zlib stream
```

⚠ **Repack at zlib level 1** — that is what the game ships (`78 01`); default gives `78 9C` and level 9 gives `78 DA`. `bros_gamedata.pack_pzze` does exactly this.

Payload header: `1, 1, 0, headerLen=256, payloadLen=size-256, countA, memberCount`. At `+0x100` the member table repeats those, then ascending member offsets, then the name list, then the members. pl005's gauge has **3 members** (bar, line, icon — the three scene elements) and **24 DDS on side 0, 25 on side 1**.

Every texture in these containers is **DXGI format 98 = `BC7_UNORM`, mips = 1**, and the DDS `pitch` field holds the linear size. The DDS + DX10 header is 148 bytes.

### 6.2 ★ Two length-preserving rewrites

**Textures.** BC7 is fixed-rate — 16 bytes per 4×4 block — so **a same-dimension re-encode is byte-length identical**. A texture swap is therefore a pure in-place splice: keep the 148-byte header, overwrite `payload_off .. payload_off + linearSize`, repack. **Nothing in the section/offset table has to move.** That is the entire reason the repaint was a one-evening job and why *adding* a texture is not.

**Meshes.** The moon already filled 96 % of its texture, so "make it bigger" had nowhere to go in the image. Size lives in the geometry, and the `tmd0` meshes sit in the same container, **index-parallel with the name list** (gauge, line, icon):

```
tmd0 header   0x10 bbox min (3f)      0x1C bbox max (3f)
              0x5C vtx_start, 0x60 vtx_end   (BLOCK-relative)
              0x9C vertex count      stride = (end-start)/count   (32 here)
vertex        position = first <3f>;  uv = last <2f> (stride-8)
```

Multiply every vertex's **x and y** (leave z — it is depth, not size) and the two bbox corners. Pure float rewrite, no length change, the container never reshapes. Verified: icon half-width 72.74 → 87.28 at ×1.20. `bros_model.py` documents the same header offsets and is the reference. ⚠ **Assert that every vertex lands inside the declared bbox before writing** — that is what proves you found the position buffer and not the UVs. ★ Always rebuild from the `.pre*_bak` original so a scale knob is **absolute, not cumulative**.

### 6.3 The icon slot map

The widget is three nodes: `ui_cha_unique_gauge00_L` (bar), `ui_gauge_line00` at `j_gauge_LR`, `ui_plNNN_unique_icon_L00` at `j_icon00`. The icon node carries **two** face textures:

| slot | 00HIGH | 01MIDDLE | anim state | measured in game on pl005 |
|---|---|---|---|---|
| portrait | 108×136 | 56×68 | `loop1` | neutral **and** cooldown |
| square | 148×148 | 76×76 | `level_up` | enhanced |

Side 1 ships a **third** face texture (a second square one, mirrored for the right-hand player) — that is why side 0 has 24 DDS and side 1 has 25. ★ **Match slots by dimensions, not by index** — dimensions are unique within each file and stable across tiers (`01MIDDLE` is `00HIGH` halved, in the same order).

⚠ **The state is chosen in code**, not in data: pl038's `Update` reads `Elem+0x98` and plays `level_up` or `loop1`. Nothing data-side makes it read the enhance level.

### 6.4 The repeated hunt for leftover icon geometry

The notes record the endpoints of this hunt rather than each intermediate pass, and there is a **gap: `ui_icon_v3_*` is never mentioned** — v1 is marked superseded, v2 is the shipped repaint, v4 is the final. What the versions changed:

* **v1** copied Grimmjow's white rim stroke drawn *outside* the outline. Dropped — it was half of the pale-fringe problem (§6.6).
* **v2** shipped the repaint of the face textures.
* **v4** finished the job across **all four containers — `00HIGH` and `01MIDDLE` × sides 0 and 1** — and moved from texture work to geometry: the neutral quad was left at its stock 76×96, while the **enhanced state's quads, `pl038_01L` *and* its `_efe` companion, were scaled ×0.80 to 83.2×83.3**.

Two structural facts explain why leftovers kept turning up. First, the enhanced state is not one quad but a quad plus an `_efe` effect quad — scaling or repainting one and not the other leaves a visibly mismatched remnant. Second, the icon element has **17 submeshes, only two of which are the face**, and the `01MIDDLE` tier holds its own copies of everything, so any pass that touched only the obvious slot in the obvious container left stale geometry live at another tier or in the other player's container. The resolution was to treat the unit of work as *all four containers × both enhanced quads*, matching slots by dimension, and to preview by decoding back out of the patched container.

★ Two things make a genuine third state cheaper than expected if it is ever revisited: the icon node's anim script **already declares three states** (`loop1`, `level_up`, `loop2`) and each is only a frame range into the element's single `tmo1` (`level_up` = f60–110, `loop2` = f120–200), so a third state costs no new file; and 15 of the 17 submeshes are not the face, so there is room without growing the container. ⚠ But on *this* element `loop2` is not a third look — see the bug ledger.

### 6.5 Encoding

DataChakka vendors richgel999/bc7enc at `bc7/` with a whole-image ctypes wrapper (`bc7wrap.cpp`) and `scripts/bros_bc7.py`. ★ Their `build.sh` only ever produced a **`.dylib`**, so `available()` returned False on Linux and Windows despite the source being right there. Built and left in place:

```
g++ -O3 -fPIC -shared -o bc7/libbros_bc7.so bc7/bc7wrap.cpp     # the name bros_bc7.py looks for
```

`scripts/bros_texture.replace_texture(path, index, image, out_path)` performs the whole splice properly, and `replace_texture_tiers` walks the tiers; `_encode_dds_payload` reconstructs a mip chain empirically by halving until the length matches the slot. ★ `ui_icon_v2_moon.py` **bakes the BC7 payloads in as base64**, so it needs no Pillow, no encoder and no network on the target machine — worth copying as a pattern for any art shipped as a patch.

### 6.6 Art recipe — the two things that actually mattered

1. **Alpha = everything not connected to the white outside.** Flood-fill from all four corners **and** the four edge midpoints. Seeding from one corner only yields 5.4 % coverage, because an inscribed circle cuts the outside into four separate components.
2. ★★ **The bleed fix.** Outside the shape the RGB was still white paper, and every resample and every BC7 block straddling the edge mixes it in — that is the cheap-looking pale fringe. Flood the **nearest opaque colour outward past the alpha edge** (a distance transform) so RGB is continuous across the boundary, and keep the alpha a hard mask **area-averaged down (`Image.BOX`), never blurred**.

Then: levels-stretch to kill JPEG ringing → map luminance through a three-stop ramp → **redraw the outer border at FINAL resolution**, not on the master. An 8 px outline at 2048 becomes 0.4 px at 108 and disappears; darkening the outermost ~2.5 % of the shape as a *solid band* (`clip(d-px+1)`, not a linear ramp) keeps the border at the same visual weight at every size.

Ramps that read correctly at HUD size after the BC7 round trip:

```
white  #0C0E12 -> #8E939D -> #FFFFFF
blue   #02143A -> #0A84FF -> #6ED2FF     bright/neon, pairs with the blue bar
red    #180201 -> #C21A12 -> #FF4A3A     a real red, not salmon
```

Do **not** mirror art for side 1 unless it is a face. Grimmjow's is mirrored so he looks inward; a moon mirrored just puts the craters on the wrong side.

---

## 7. The enhance state

### 7.1 Where it lives

| offset | meaning |
|---|---|
| `+0x1098` | ★ **enhance level BITMASK** — bit0 = lvl1, bit1 = lvl2, bit2 = lvl3 |
| `+0x1A10 + 4*(lvl-1)` | remaining time, float, 60 fps frames |
| `+0x1A1C + 4*(lvl-1)` | configured max time (the `Enhance` block's `max_val`) |
| `+0x1A28 + 4*(lvl-1)` | per-level max value from `init_val` |
| `+0x1A34 + 4*(lvl-1)` | per-level current value from `init_val` — **the `UNIQUE_0/1/2` floats** |
| `+0x1094` | **form** (0 = base) — what `GetForm()` returns. **NOT** the enhance level |
| `+0xC00` | chara id |
| `+0xC20` | player / HUD slot, indexes `g_battleUi` |

No accessor exists: all 16 read sites are inline `mov eax,[rcx+0x1098]; and eax,7`, and the effective level is the highest set bit + 1. Writers are `SetEnhance 0x140474590` and `ClearEnhance 0x140474890`, both reached from the `Enhance` block handler `0x1403B37F0`, selected by `enhance_start`.

Note the collision worth keeping in view: `+0x1A34..3C` is simultaneously the `UNIQUE_n` script bank and the enhance blocks' per-level current values. Anything writing `init_val` on an `Enhance` block and anything writing `UNIQUE_n` are aiming at the same three floats.

### 7.2 ★★★ The finding that reframes everything

The per-frame chara timer `0x14048C390`, loop body `0x14048CBD8`–`0x14048CCED`, is reached by **straight fall-through with no guard**, so it runs every frame for every character:

```
for i in 0..2:
    max = [chara+0x1A1C+4i];  if max <= 0: continue        ; max_val = -1 => never ticks
    if !(chara[0x1098] & (1<<i)): continue
    if chara[0xC00] == 4: skip the HUD push                ; id 4 is specially excluded
    ratio = [chara+0x1A10+4i] / max
    ui = g_battleUi[ chara[0xC20] ]                        ; 2-entry array at 0x141CDE758
    if ui && ui->vtbl[0x48]() { p = ui->[0x200]; if (p) p->vtbl[0x50](ratio); }
    [chara+0x1A10+4i] -= dt ;  on reaching 0 -> ClearEnhance(chara, 1<<i), pushes 0.0 first
```

`ui->[0x200]` is exactly where `0x14021E185` stored the unique-gauge controller, and `vtbl[0x50]` is slot 10, `SetRate(float 0..1)`. ⇒ **The gauge *is* the enhance timer.** Two consequences fall straight out: the loop runs ascending with last-write-wins, so the HUD shows the **highest live level**; and because levels 1 and 2 each keep their own clock, level 1's bar surfaces already part-drained the instant level 2 expires. `max_val = -1` (run until cleared) also means the level never ticks and never shows a bar.

### 7.3 The in-game evidence, and the correction it needed

Three runs during the pl005 SP1 (Aterie) build, 2026-08-09:

| run | arms | in-game result |
|---|---|---|
| probe 2 | mode 1 (900 f) armed FIRST, mode 2 (2100 f) SECOND | level 2 for the whole 35 s |
| V1 | mode 2 (2100 f) armed FIRST, mode 1 (900 f) SECOND | level 2 for the whole 35 s |
| V2 | mode **1** = 2100 f, mode **2** = 900 f | **2222 → 1111 → 315** ✔ |

Reversing arm order changed nothing, killing both "last write wins" and "first write wins". The V2 ladder — the long clock on the *low* level — produced the three-stage readout that proved levels are independent and simultaneous.

The conclusion drawn at the time was *"`ENHANCE` is a level, not a bitmask; the effective level is the highest one currently running."* **The first half of that is wrong and was overturned by the RE pass on 2026-08-10:**

* `+0x1098` is a **bitmask**, and `ENHANCED` / `NOW_ENHANCED` are script variables holding the **decimal value of that bitmask**, not a level. `ENHANCED==3` means levels 1 **and** 2 are alive — which is precisely why shipped scripts are written `ENHANCED==1||ENHANCED==3`.
* **No gate anywhere computes "highest active level."** `enhance_active = 1` passes whenever bit 0 is set, even with level 2 running (`0x1403F213D`), and `enhance_damage` adds **every** set bit's slot (`0x1403D2534`).
* **"Highest wins" is true only of the HUD**, as an emergent property of the ascending, last-write-wins timer loop.

The independent-timers half of the original finding survives intact and is confirmed by the code. ⚠ The two runs that read "level 2 for the whole 35 s" are *not* evidence against the bitmask model — with both bits set, both the `1` and the `2` hitbox variants are live, and the project's own later warning applies: **overlapping hitboxes on the same frame produce one hit, so a same-frame readout tells you which variant wins a race, not which variants are live.** The notes do not explicitly join these two observations; this reconciliation is mine, and it is the only reading under which all three runs and all three code sites agree.

Related mislabels corrected in the same pass: `bros-engine-offsets` records `+0x1098` bit0 as "some lockout" (superseded — Aizen's kikon-counter gate requiring `+0x1098 & 1 == 0` is therefore "level 1 not active"), and `roster-add-unique-gauge-ui` proposed keying bar colour off `GetLevel (0x1402065C0)` — that function is **`GetForm`**, vtable slot 22, reading `+0x1094`, and would never have returned an enhance level.

### 7.4 The authoring vocabulary

```
Enhance block   enhance_start=1  enhance_mode=<level>  max_val=<FRAMES @60fps>  init_val=auto
                max_val = -1  -> runs until cleared (and never ticks, so no HUD bar)
                max_val =  0  with enhance_start=0 -> CLEARS it
```

⚠ Four characters ship the clearing form on `ct_revolut_rev` — **reversing may wipe a buff**; check it for any timed-buff move.

Real shipped durations: 900 = 15 s (pl014, pl038), 1200 = 20 s (pl006), 1800 = 30 s (pl003), 495 = 8.25 s (pl004), 1828 = 30.5 s (pl018), 2100 = 35 s (ours).

**Three independent, native ways to read the state:**

1. **`enhance_active`**, a field on every `Attack_Melee` / `Attack_Bullet` / `Attack_LaserBullet`:

| value | meaning | shipped count |
|---|---|---|
| `0` | always (the default) | 4,321 |
| `1` | only at level 1 | 362 |
| `2` | only at level 2 | 67 |
| `-1` | only UNENHANCED — **no level running at all** | 363 |

2. **`str_a` gate expressions** — 53 distinct across the roster, 14 predicate tokens: `ENHANCED ==1 ==2 ==3 ==7 ==10 ==0 !=0 >0 <1 <2 <=1` with `&&`/`||` compounds; `UNIQUE_n` / `NOW_UNIQUE_n` full ranges (`1<=UNIQUE_1&&UNIQUE_1<2`, `4<=UNIQUE_0&&UNIQUE_0<=5`); plus `TARGET_SIZE`, `BLEND_X`, `BLEND_Y`, `STEPDASH`, `GROUND`. ★ **`ENHANCED<2` + `ENHANCED==2` is the safe complementary pair** (pl037 ships both, ×32 / ×35): `<2` covers unenhanced *and* the level-1 tail, so gated blocks never fall through a hole. `!=2` is not shipped — do not invent it.

3. **Node-level gate** — the tcmb variable `enhance` (index 6 of pl005's 22): `0` = ignore, `+N` = require level N, **`-anything` = "no level active at all"**.

### 7.5 Damage without twin actions

`Attack_Melee` also carries **`enhance_damage = "A,B,C"`** — bonus damage, one slot per level, and the handler adds **every set bit's slot**.

★ **pl004's SP1 is a shipped +20 % timed damage buff**: `Enhance mode 1, max_val 495`, then `enhance_damage` slot 1 across his whole moveset at exactly +20 % (400→+80, 550→+110, 900→+180, 2800→+560). The grab is a deliberate exception (750→+500).

★ **pl001's `atk_da01` is a shipped multi-hit variant in one action, with no twin nodes:**

```
enhance_active = -1   f14..18   225 dmg   guard 250   fighting 0.020     normal
enhance_active =  1   f14..16   100 dmg   guard 125   fighting 0.010     enhanced
enhance_active =  1   f16..18   175 dmg   guard 125   fighting 0.010     275 = +22 %
```

Guard damage and `fighting_base` are both halved so the totals stay flat while the hit count doubles. **158 actions ship the `-1`/`1` pair.** Shinji's `evo_atk_da02` is the four-hit version: 400 ×1 → 120 ×4 = +20 %, with `hit_stop_speed` 0.05 → **0.20**.

### 7.6 Architecture correction: twin actions beat in-place variants

`roster-add-enhance-state` concludes that enhanced movesets need no twin actions, no twin nodes and no `nexts` reordering. **That works, but twin-ACTION + twin-NODE is better and is what most of the roster actually does** — pl032 `atk_hi02`/`atk_hi02_1`, pl031 `atk_da01`/`_1`, pl038 `atk_hi01`/`_1`/`_2` (one twin per level), pl022 `sp_overatk01_*` vs `sp_overatk02_*`.

```
twin node      enhance = 2   listed FIRST in nexts   -> wins while the buff level is up
original node  enhance = 0   listed after            -> "ignore"; the fallback in cooldown AND neutral
```

The originals are never touched, the twin can differ in *anything* (frames, cancels, effects, sound, motion), and it is purely additive — a wrong edge means "the enhanced version does not come out", never "he lost a move". ★ **A twin needs no motion work**: pl038's `atk_hi02_a` carries `motion = 'atk_hi02'` and has no `.tactpkg` entry, because the `motion` field *is* the clip lookup key. ⚠ Name twins **`_a`**, not `_1` — pl005 already ships real moves called `atk_hi03_1`, `atk_lo01_d01`, `atk_lo01_u01`; `_a`/`_b` is pl038's own escape hatch for exactly this.

### 7.7 Aterie's shipping assignment

```
Enhance mode 1  max_val 2100  (35 s)   the LOCK / cooldown tail   -> enhance_active = 1
Enhance mode 2  max_val  900  (15 s)   the BUFF                   -> enhance_active = 2
node sp_atk01 (uid 20) enhance = -1    locked until every clock expires = 15 + 20
```

Both `Enhance` blocks sit in ONE action (`1_normal_attack_sp_atk01`, at f10 and f40). Two blocks with *different* modes in one entry is not shipped anywhere in the game (pl043 ships two same-mode blocks in one entry) — but it **works**, verified in game.

Scripts, all in `Zangetsu Patch/`: `sp1_survey.py` (read-only inventory), `sp1_probe.py` (v1, aura readout — the wrong instrument), `sp1_probe2.py` (damage-number readout — the right one), `sp1_v1_neutral.py` (strips the SP1 to a neutral cast, harvests the warp idiom to `sp1_warp_idiom.json`, heal 500), `sp1_v2_ladder.py` (the arm swap that settled it), `sp1_v3_lock_move.py` (node lock + gated `MotionMoveRate`).

---

## 8. General fighter struct offsets worth knowing

| offset | what | source / status |
|---|---|---|
| `+0x9A8` | rival "mid-Kikon" flag (non-zero while a kikon plays) | verified |
| `+0xC00` | **character id** — `cmp [rax+0xC00], <id>` is how ALL per-character hardcoded logic is written in this exe | verified |
| `+0xC20` | player / HUD slot; indexes `g_battleUi` (2 entries, `0x141CDE758`) | verified |
| `+0x1094` | **form** (0 = base); what `GetForm 0x1402065C0` returns | verified — **not** the enhance level |
| `+0x1098` | **enhance level bitmask** (`& 7`) | corrected; earlier labelled "bit0 = some lockout" |
| `+0x10B0` | **reverse gauge MAX** | verified |
| `+0x10B4` | **reverse gauge VALUE** | verified |
| `+0x1A10 + 4i` | enhance level *i+1* remaining time (frames) | verified |
| `+0x1A1C + 4i` | enhance level *i+1* configured max time | verified |
| `+0x1A28 + 4i` | enhance level *i+1* max value | verified |
| `+0x1A34/38/3C` | `UNIQUE_0/1/2` — the generic unique-meter floats, = enhance per-level current value | verified |
| `+0x1A40 + 4*(n-1)` | where `AddUniqueVal` stores `unique_type_idx` n (1-based, accepts 1..11, **never clamps**) | ⚠ see the §1.2 contradiction |
| `+0x1A5C` | pl020's once-per-match counter flag | verified |

**The reverse gauge**, for orientation: `reverse` is the **gauge**, `ura` (裏) is the **transform it pays for** — two different things. Canonical mutator `0x14046AD30` (add, clamp to `[0,max]`, fire `sys_reverse_max`); getter `0x14046ABED`; HUD widget `0x1401EED50`, drawn from sprites `rebirth_gauge1/2/3` (up to three segments, what players call "bars"); the debug menu (`0x1404BC635`) shows it as a **0–100 percentage of max**, which is where "100 reverse" as a unit comes from. ⚠ `0x1401EED50` is **event-driven, not a per-frame resync** — stopping a deduction without also stopping the HUD call empties the displayed gauge while the value stays full.

**★★ The per-character behaviour slot table** is the fastest route to isolate anything character-specific: behaviours are registered from a table keyed by id string (pl020's slot is `0x1418E1130`; the literal `"pl020"` is written at `0x14051AE5D`, the slot pointer at `0x14051AE70`). Walk callers back to a vtable, back to its construction site, back to the slot — if it lands in one character's block, the behaviour is that character's alone.

---

## 9. DataChakka

**What it is.** The team's internal BRoS asset decompiler and viewer, written by another dev. Repo `C:\Users\ramig\Documents\GitHub\DataChakka` (request via `request_cowork_directory`; bash mount `/sessions/<id>/mnt/DataChakka`). Python plus a web UI; CLI entry `scripts/bros.py`, Windows shims `datachakka.cmd` / `bros.cmd`; `Start DataChakka.cmd` is a thin launcher over `scripts/bootstrap.py`, which auto-detects the install via registry + `libraryfolders.vdf` + `appmanifest_1689620.acf` and validates with `bros_gamedata._GAME_MARKERS`. Catalogue staleness is answered by the filename itself being a sha256 fingerprint of the exe (`catalog-<sha>.sqlite`). Key data: `catalog.sqlite`, `asset_names.json`, `asset_tags.json`, `character_db.json`, `decomp/**`, `guides/**`.

**What is trustworthy, and what this section leaned on.**

* `decomp/formats/*.h` — format documentation, decoded and verified against this install. `FnamesVfs.h` (which had the `filename.bin` group model exactly right), `UiScreenLayout.h` (the seven-file UI screen model), `UiIconRegistry.h`, `PzzeContainer.h`, `CsoTable.h`. **Unaffected by the address-space problem below.** Check these first.
* `decomp/ghidra/0x*.c` — 61,240 per-function decompilations. Good for **logic**.
* `ghidra_mine.sqlite` — indexes string refs, file refs, vtables and the call graph by VA.
* Tooling used directly here: `bros_gamedata.pack_pzze` (PZZE at level 1), `scripts/bros_texture.replace_texture` / `replace_texture_tiers`, `bros_model.py` (the `tmd0` header reference), `bc7/` (vendored richgel999/bc7enc + `bc7wrap.cpp`) with `scripts/bros_bc7.py`.

**⚠ THE STANDING WARNING — the Ghidra corpus is a DIFFERENT BUILD.** VAs are offset from our exe by a **non-uniform delta**: 0 below roughly `0x1401C0000`, **`+0x280`** through the `0x1402xxxxx`–`0x1403xxxxx` range, and larger above. **Function boundaries there are wrong too.** For a VA *X* in the UI region, read `decomp/ghidra/0x<X-0x280>.c`. **Use it for logic, never for addresses.** Every address in this section was read out of our own shipped exe.

**Corrections in DataChakka's own notes that bear on this area.** Their `filename.bin` model is authoritative (§4). Their audit also established that **`MY_SIZE` occurs in no shipped `.tadjpkg`** (plus the dead typos `ARGET_SIZE` ×3 and `ENHANCDE` ×1); that **tadj `f32×3` is not cleanly `[?, start, end]`** (first word is a `u32` flag, 18.3 % of pairs have `end < start`); that tadj `memo` is a NUL-terminated string, not a `u8` flag (re-parsing took the component walk from 83.3 % to 93,018/93,018); that `.cat` is **three unrelated formats discriminated by `+0x0C`**; and that `ui/script/variable`, `ui/script/event` and four `Script/*.bin` tables are all **the same serialiser** (`u32 count` then records; every string `u32 len; chars; NUL`, length excluding the NUL — ★ **a zero-length string is still five bytes**, and `ui/script/variable` has no header at all). The newly identified `.tadjdbpkg` (`AdjDataBase`) is the schema `.tadjpkg` is written against and is the right place to settle open field semantics such as `is_val_set`.

★ One of their late findings is directly relevant to the icon-tint failure: **`.tmd2` submesh→material binding is the render command list (bank 3)** — a u16 state machine (`0x60nn` bind material, `0x40nn` bind palette, `0x30nn` draw submesh, `0x1000` end), where the material in force at a draw *is* that submesh's material, and there is **no parallel static mapping**. The old ordinal guess (`submesh i → material min(i, n-1)`) was **wrong on 32.4 % of submeshes**. That is the offline route to the icon face's real material index (the notes do not record it being used for this; the in-exe route is `FindMaterialParam 0x140222510`).

Their generalisable tricks that earned their keep here: *the consumer may not be the CPU*; *a big blob's directory is often a small sibling file*; *linear re-tiling beats tree-walking as proof*; *when counts stop adding up, suspect deduplication or sharing, not a decode error*.

⚠ Known tooling breakage, both fixed: `bc7/build.sh` produced only a `.dylib` (see §6.5), and `bros_re.record_exe_fingerprint` **did not exist**, so every committed `datachakka build` died with an `AttributeError` on its last line, leaving an unstamped catalogue and exit 1.

---

## 10. Bug and correction ledger

### 10.1 Registration and assets

**The wrong-group registration (the day-long one).** *Symptom:* the buff and the cooldown behaved correctly in game, but no gauge ever appeared, with no crash and no log line. *Wrong hypothesis:* the exe switch patch was wrong — three rounds were spent disassembling every rel32, checking section flags and confirming that only one instruction reads the switch table. *Real cause:* the twelve pl005 UI files were registered into **pl038's** groups, because `add_file` locates a directory node by name and there are 91 distinct nodes named `ui\`, one per group; the runtime key is `hash(groupName, logicalName)`, and a miss returns the empty string silently. *Fix:* `ui_gauge_v8_package.py` creates pl005's own two groups and bumps `u32 @0` from 1154 to 1156. *Lesson:* when a change is "correctly applied and does nothing", check the consumer's data model before re-verifying the producer.

**The phantom 13-byte header.** *Symptom:* none visible — `fnames_patch.parse_manifest` worked for every previous patch. *Wrong hypothesis:* `filename.bin` is a flat list behind a 13-byte header. *Real cause:* the "header" is `groupCount` (4) + group 0's empty name (5) + group 0's own `dirCount` (4); the flat reading works only because group 0 holds 24,673 of 28,586 entries. *Fix:* parse per the `FnamesVfs.h` grammar; treat `u32 @0` and `u32 @9` as the two invariants.

**"`filename.bin` is a blanket load gate."** *Symptom:* conflicting evidence — the rev banner demonstrably needed a `filename.bin` entry, yet DataChakka tested `tex0.lds` and stage thumbnails as having no entry and loading fine. *Real cause:* two different loading paths. *Resolution:* assets resolved **by logical name** need the manifest; assets loaded **by direct path** do not. `file_exist.htable` is the real existence gate, and a logical-name asset needs both tables.

**Renaming `ui_reiryoku_buff_L/R`.** *Symptom:* hard crash, `0xc0000005`. *Real cause:* that entry is live and looked up by name at runtime. *Fix:* leave it alone; it also has only one anim state (`buff_loop`), so it cannot be recoloured per character anyway. Same class of hazard as `ui_plNNN_unique_icon_L00/R00`, which are hardcoded exe literals at fo `0x143D1E0` / `0x143D200`.

**Empty-looking `ActionUnique*` screens.** *Symptom:* texture scans found nothing in most sprite containers. *Wrong hypothesis:* the screens genuinely contain no textures. *Real cause:* 65 of 82 sprite containers are PZZE-compressed and 17 are not; a scanner that does not check the magic sees only the uncompressed ones. That hid **1,670 of 2,820 DDS surfaces**. *Fix:* check the `PZZE` magic and decompress first.

### 10.2 Controller and hooks

**The frozen 100 % bar.** *Symptom:* after installing hook 2 on pl038's `Update`, the gauge sat at 100 % and never depleted. *Wrong hypothesis (implicit):* a bare `ret` is a safe bail-out for a non-pl005 character. *Real cause:* `Gauge::Update 0x140207490` **is** the element state machine and the draw push; skipping it means nothing ever advances `Elem+0x94` and nothing is ever pushed. *Fix:* the guard path must `sub rsp,0x28; call 0x140207490; add rsp,0x28; ret`.

**The moon that would not tint.** *Symptom:* `SetColorByIndex(node, 0, r, g, b)` (`0x140224700`) had no visible effect; the icon stayed white in all three states, with no crash and no error. *Wrong hypothesis:* material index 0 is the icon face. *Real cause:* index 0 is some other material on this element, and the call is bounds-checked so an out-of-range or wrong index silently no-ops. The three-state **bar** colour works because it is a completely different mechanism (`Elem+0xB0` + `Elem+0x9A`). *Fix / resolution:* Berg accepted white-throughout as final — the bar colour plus the `loop1`/`level_up` animation already read the state. **The tint call in the shipped driver is dead code**; strip it or keep it as a one-line switch. If revisited: find the real index with `FindMaterialParam (0x140222510)` against the icon's material name rather than guessing, or swap the texture with `SetTextureByName (0x1401FEBD0)` the way Hisagi and Aizen do.

**`loop2` as a third visual state.** *Symptom:* a planned third icon look never materialised as a distinct appearance. *Wrong hypothesis:* the icon's anim script declares `loop1`, `level_up` and `loop2` as three frame ranges into one `tmo1` (`level_up` = f60–110, `loop2` = f120–200), so a third state costs no new file. *Real cause:* pl038's `Update` tail at `0x140215718` does `if (AnimFinished && IsAnim("level_up")) PlayAnim("loop2")` — `loop2` is `level_up`'s **resting loop, same art**. No animation state gives a third colour on this element. *Fix:* none needed for shipping; note that pl024 (Kyoraku) *does* drive `loop1`/`loop2`/`loop3` as three genuine states on one node, so the capability exists per-element and must be verified per-element.

**`[this+0x10]` treated as the gauge.** *Symptom:* would have read garbage. *Real cause:* it is a `vector<Elem>` header; the element array is `*(Elem**)(this+0x10)`, stride `0x240`. *Fix:* dereference once more. (`initParam+0x30` is always 0, so there is always exactly one element.)

**Reaching the fighter from the UI.** *Symptom:* no way to read the enhance level inside a controller. *Wrong hypothesis:* `Work+0xD0` (fighter ObjRef) / `Work+0xF0` (cached `Chara*`) are populated. *Real cause:* `Base::Init 0x140205740` never stores a chara pointer, and slots 20/21/22 have zero direct callers; the side HUD object carries only chara id, uiId and controller pointer. *Fix:* invert the direction — hook the enhance timer at `0x14048CBD8`, where the chara is in `rsi`, and push into the UI from there.

**`GetLevel` at `0x1402065C0`.** *Symptom:* a plan to key bar colour on the enhance level via a vtable call. *Real cause:* that function is **`GetForm`** (slot 22), reading `+0x1094`, which is the form and is 0 in base. *Fix:* the shipped driver reads `[chara+0x1098] & 7` in the timer hook instead.

**Volatile registers across calls in the cave.** *Symptom:* corrupted state selection. *Real cause:* `r10`/`r11` are volatile and do not survive the intervening calls. *Fix:* spill the chosen state to `[rsp+0xB0]`.

**The cooldown bar starting at ~57 %.** *Symptom:* Berg — *"a new gauge popped up instead filled halfway through, at 50 %."* *Initial reading:* a second, new timer. *Real cause:* it is the same level-1 clock becoming visible with 20 of its 35 seconds already spent (20/35 = 1200/2100 ≈ 57 %), because each enhance level keeps its own countdown and the HUD shows the highest live one. *Fix:* the driver rebases `[chara+0x1A1C] = 1200.0` while in state 2, so the cooldown bar starts full.

### 10.3 Meter and enhance semantics

**"The unique gauge shows the `UNIQUE_n` meter."** *Symptom:* the risk that a borrowed HUD would render and read zero. *Wrong hypothesis:* the `ActionCharaUniqueUI` classes read `+0x1A34/38/3C`. *Real cause:* they read nothing of the kind — a scan of `0x140205000`–`0x140222000` across all six displacements found zero hits. The gauge is fed by the enhance-timer loop at `0x14048CBD8`–`0x14048CCED` calling `SetRate` (vtable slot 10) with `remaining / max`. *Fix:* pl005's gauge is driven from the enhance state; the `AddUniqueVal` meter remains a separate, data-only counter.

**"`ENHANCED` is a level."** *Symptom:* gates and hitboxes behaving as though more than one level were active. *Wrong hypothesis:* `ENHANCE` is a level and the effective level is the highest running one, for everything. *Real cause:* `+0x1098` is a bitmask; `ENHANCED`/`NOW_ENHANCED` carry its decimal value (`==3` = levels 1 and 2 both alive, hence shipped `ENHANCED==1||ENHANCED==3`); `enhance_active=1` passes on bit 0 regardless of level 2 (`0x1403F213D`), and `enhance_damage` sums **every** set bit's slot (`0x1403D2534`). "Highest wins" is an artefact of the HUD's ascending last-write-wins push only. *Fix:* author gates against the bitmask, and note that the independent-per-level-timer half of the original finding is confirmed.

**The `-1` moveset-deleting trap.** *Symptom:* the base 315-damage hitbox never appeared during either gauge. *Wrong hypothesis:* `enhance_active = -1` means "not at this level". *Real cause:* it means "no level running **at all**". *Fix:* if you flip a hitbox to `-1` you must author a variant for **every** level the fighter can be in, or the move is gone for the whole duration. The safe alternative for `str_a` gates is the shipped complementary pair `ENHANCED<2` / `ENHANCED==2`.

**Reverse wiping buffs.** *Symptom:* not observed on pl005, recorded as a hazard. *Real cause:* `max_val = 0` with `enhance_start = 0` clears the level, and four characters ship exactly that on `ct_revolut_rev`. *Fix:* check `ct_revolut_rev` for any timed-buff move.

**Auras as the state readout.** *Symptom:* `sp1_probe.py` produced nothing usable — the auras never rendered. *Real cause:* wrong instrument. *Fix:* `sp1_probe2.py` reads the state off the **damage number** in training mode: three hitboxes at `-1`/`1`/`2` with wildly different damage values decode the state in one light attack.

**Same-frame diagnostic hitboxes.** *Symptom:* a readout that appears to say "only level 2 is active." *Real cause:* overlapping hitboxes on the same frame produce **one** hit, so a same-frame readout reports which variant wins a race, not which variants are live. *Fix:* measure damage with a **single** move, never a chain, and put diagnostic variants on **different frames**.

**Unbounded counters.** *Symptom:* would be a meter that never stops climbing. *Real cause:* `AddUniqueVal`'s handler never clamps. *Fix:* the shipped idiom — gate the `AddUniqueVal` block on its own counter, as pl016 does with `str_a = "UNIQUE_1<1"`.

**Yhwach as a template.** *Wrong hypothesis:* Kaiser points are a reusable `AddUniqueVal` recipe. *Real cause:* `pl052.tadjpkg` contains zero `AddUniqueVal`; Kaiser points are `ActionCharaUniqueUI_Pl52` plus bespoke exe code. *Fix:* use the generic system that twenty other characters use. Also confirmed dead: `CharaStatus.fsv` cols 34–45 (all zeros for pl052 and pl005) and `Script/Unique_pl039Param.fsv` (Szayel-only, hardcoded name).

**Multi-hit knockback.** *Symptom:* victims sent across the map and follow-ups whiffing. *Real cause:* every hit of a multi-hit was given the original launch values; **only the LAST hit of a multi-hit should knock back**. *Fix:* pl001's shipped pattern — earlier hits zero `damage_move_rate` and `blow_dir` and run `hit_stop_time = 2`.

### 10.4 Art

**The pale fringe.** *Symptom:* the icon read cheap and washed-out at HUD size. *Wrong hypothesis (v1):* it needed a white rim stroke outside the outline, copying Grimmjow's icons. *Real cause:* outside the shape the RGB was still white paper, and every resample and every BC7 block straddling the alpha edge mixed it in; the added rim stroke was the other half of the problem. *Fix:* distance-transform the nearest opaque colour outward past the alpha edge so RGB is continuous across the boundary, keep alpha a hard mask area-averaged with `Image.BOX` and never blurred, and drop the rim stroke.

**5.4 % alpha coverage.** *Symptom:* almost the entire image came out transparent. *Real cause:* the background flood-fill was seeded from one corner, and an inscribed circle cuts the outside into four disconnected components. *Fix:* flood from all four corners **and** the four edge midpoints.

**Salmon red.** *Symptom:* the "red" state read as salmon. *Wrong hypothesis:* put the tint in the craters and keep the light end near white (`#FFA893`). *Real cause:* the disc body is luminance 1.0, so the **top** of the ramp *is* the icon's colour. *Fix:* the three-stop ramps in §6.6, with the tint at the light end. ⚠ Always preview by decoding back out of the patched container, never from the source PNG.

**The vanishing outline.** *Symptom:* the border disappeared at HUD size. *Real cause:* an 8 px outline at 2048 becomes 0.4 px at 108. *Fix:* redraw the border **at final resolution**, as a solid band (`clip(d-px+1)`, not a linear ramp) darkening the outermost ~2.5 % of the shape, so it holds the same visual weight at every size.

**Leftover icon geometry.** *Symptom:* repeated passes kept leaving stale or mismatched icon art. *Real cause:* the work unit is larger than it looks — **four containers** (`00HIGH`/`01MIDDLE` × sides 0/1), the enhanced state is **two quads** (`pl038_01L` and its `_efe` companion), the icon element has 17 submeshes of which only two are the face, and side 1 carries a third (mirrored square) face texture. *Fix:* `ui_icon_v4_moon.py` treats all four containers and both enhanced quads as one operation (neutral quad left at stock 76×96, enhanced quads ×0.80 → 83.2×83.3) and matches texture slots **by dimensions, not index**. ⚠ The notes never mention a `v3`; the intermediate step between v2 and v4 is unrecorded.

**Cumulative scaling.** *Symptom:* a scale knob that compounds across runs. *Fix:* always rebuild from the `.pre*_bak` original so the knob is absolute.

**Wrong buffer identified as positions.** *Symptom:* would be silently corrupted UVs. *Fix:* assert that every vertex lands inside the declared bbox (`tmd0+0x10` / `+0x1C`) before writing — that is the proof you found the position buffer.

**Wrong zlib level on repack.** *Symptom:* a container that differs from stock at the byte level (`78 9C` or `78 DA` instead of `78 01`). *Fix:* repack at level 1, as `bros_gamedata.pack_pzze` does.

**Mirroring side 1.** *Wrong hypothesis:* mirror everything for the right-hand player, as Grimmjow's set does. *Real cause:* Grimmjow's is mirrored so his **face** looks inward. *Fix:* do not mirror non-face art — a mirrored moon just puts the craters on the wrong side.agentId: a6431d39e6307f693 (use SendMessage with to: 'a6431d39e6307f693', summary: '<5-10 word recap>' to continue this agent)
<usage>subagent_tokens: 105464
tool_uses: 8
duration_ms: 603175</usage>


---

## Part 7 — SP1 "Arterie" and the enhanced moveset

SP1 is the feature that turns Zangetsu from a moveset into a character. It is a neutral-cast buff
that swaps a large part of his kit for a stronger version for a fixed time, and it is the reason the
unique gauge, the enhance state and the twin-action architecture in Parts 3 and 6 all exist.

### What it does

Cast from neutral. On cast it heals **500**, applies a **15-second buff**, and starts a **20-second
lock** before it can be cast again. While the buff is up, movement is gated to a faster profile and
twelve actions are replaced by stronger variants.

The move is named **Arterie**. It shipped briefly as "Aterie" — a transliteration slip — and was
renamed through `move_names_own_entry.py`, which is a `CommonText.cat`-only change: the exe md5 is
unchanged by it (`f084d7b9b7c15141a187fb3a4e37af9d` before and after). See Part 2 for why move names
are a hash→hash map and therefore renameable without touching any binary.

### ★★ The architecture: twin actions and twin nodes, not in-place swaps

The obvious way to build an enhanced moveset is to gate the *contents* of an action on the enhance
state — put both versions of a hitbox in one entry, each with a `str_a` condition. That was the
original plan and it is wrong at scale.

What shipped instead (`sp1_v10_final.py`) is **12 twin actions and 12 twin nodes**: each enhanced
move is a complete, separate action with its own graph node, and the enhance state selects between
the twins. The suffix convention is `_a` — `atk_hi01` / `atk_hi01_a`.

Two things make this the right shape. First, an action's *timings* differ between versions, not just
its damage, and a single entry cannot hold two timelines. Second, it keeps the enhanced version
inspectable and tunable in isolation: `hi_recovery_v1.py` in Part 4 sets four entries — `atk_hi01`,
`atk_hi01_a`, `atk_hi02`, `atk_hi02_a` — and the twin structure is what makes "all variants of it"
a well-defined set rather than a hunt.

⚠ The gating condition itself is the trap, and it is documented in full in Part 6: **`ENHANCED` is a
bitmask, not a level.** `ENHANCED==2` means "only level 2 is alive", not "level 2 is the highest
active level". A gate written as `ENHANCED==2` never fires while level 1 is also up. This is why an
early 2× movement buff could not be felt in play.

### Supporting work that shipped with it

* **His own UI asset groups** (`ui_gauge_v8_package.py`) rather than borrowing pl052's — see Part 6
  for why the borrowed HUD was abandoned and what the `filename.bin` group key has to do with it.
* **His own gauge logic** (`ui_ctrl_v1_ownlogic.py`) — two exe hooks plus an `.rdata` cave, with
  white/blue/red keyed on the enhance bitmask. This is one of the three exe patches currently
  missing from the release recipe; see Part 10.
* **The moon icon** in all four containers (`ui_icon_v3_moon.py`, then a long resize thread ending
  in `ui_icon_v6_purge.py`) — Part 6.
* **SP1 recovery** cut by 30 frames (`sp1_motion_v1_aterie.py --hold 30 --end 120 --cancel 120`).
  Berg's note was that being stuck looking down for a full second read badly.

### ⚠ The bug that was caught before it ran

`sp1_motion_v1_aterie.py` rebuilt its action from `pl005.tadjpkg.preaterie_bak` so its knobs would
stay absolute across re-runs. The intent was right; the implementation loaded the **whole package**
from the backup, edited one entry, and wrote the whole thing back.

At the moment this was spotted, that backup predated both the entire `ENHANCED>=2` movement gate set
and the enhanced SP2 ender. Running it would have deleted both, silently, with no error.

The fix is entry-scoped rebuild — load the **live** package as the write target and pull only the
one entry from the backup:

```python
live, rewrap = actpkg.load(path)        # write target = LIVE
bp, _ = actpkg.load(path + BAK)
pristine = bp.get(ENTRY)                # ONE entry from the backup
live.set(ENTRY, tadj_lib.build(edit(pristine)))
```

`--revert` needs the same treatment: restore the entry, not the file. This is the third instance of
the same class in the project — see Part 11.

### Left on the SP1 thread

Uryū's evo aura as the buff's visual (`pl003_ct_evolve` f0–120 of 600 for the motion,
`P003_cs_trn_evo_00` for the effect; 465 KB / 36 units, so it wants a trimmed private clone).
pl005's `additional_status_effect.fsv` row is empty, which is the clean route for a
buff-duration aura. Also outstanding: the grey-out of the SP1 icon during cast and cooldown (pl020
does this with the node variable `unique_combo`), and a name entry at `skillNamePl005_00`, which is
free.

---

## Part 8 — The fighting-spirit lock

The last mechanic the base form needed, and the one that took the most builds to get right: **while
the opponent is still in base form, Zangetsu gains no fighting spirit from anything.** Once they
evolve, everything reverts to stock behaviour. It affects Zangetsu and nobody else.

### The system, as reversed

The meter is an **array of five floats** at `fighter + idx*4 + 0x1110`, capped by a parallel array at
`+0x10FC`, with a global suppression flag at `+0x12B5`. The five caps are copied out of the
character's `CharaStatus.fsv` row by `0x140462E50` — the columns are `fighting_param`,
`evo_fighting_param`, `rev_fighting_param`, `evo_kikonsyouka_param`, `rev_kikonsyouka_param`, read by
name at `0x1404D9BC0`. So the five meters are base→evo, evo→…, rev→…, and the two kikon-sublimation
tracks.

**The index selector, `0x14046C230`.** `rcx` = fighter, returns the live meter index or **−1 meaning
"no meter"**. It has no `.pdata` record because it is a leaf that never touches the stack.

```
movsxd r8, [rcx+0xC00]     character id
mov    edx, [rcx+0x1094]   form: 0 base / 1 evo / 2 rev
cmp    r8d, 2 -> evo branch    ★ pl002 has no evo, so the game already hard-codes an exception here
form 0 -> 0 | form 1 -> 3 or 1 | form 2 -> 4 or 2 | otherwise -> -1
```

★ **−1 is the engine's own "do not accrue".** Every consumer already handles it. That is the lever:
no invented suppression path, no half-applied state, no new failure mode.

**There are two accrual shapes.** Some callers add to the meter *inline* — recognisable by a meter
store inside the caller's own `.pdata` bounds. Others hand the amount to a **shared adder at
`0x14046C2E0`** (`rcx` = recipient, `xmm1` = amount, `r8d` = index, `r9b` = curve flag) and have no
store of their own. That distinction is the whole story of why the first working build was
incomplete.

### ★★★ The game already ships this feature for two other characters

Inside the adder:

```
0x14046C2FF  jne 0x14046C3A6      suppression flag +0x12B5   -> no accrual
0x14046C308  je  0x14046C3A6      index == -1                -> no accrual
0x14046C30E  mov eax, [rcx+0xC00]
0x14046C314  cmp eax, 8
0x14046C319  cmp eax, 0x17
0x14046C31E  cmp dword [rcx+0x1094], 1   ★ characters 8 and 0x17, while in EVO form...
0x14046C325  je  0x14046C3A6             ★ ...gain nothing.
0x14046C327  <accrue>
```

"This character gains no fighting spirit under condition X" is **a table the engine already keeps**.
pl005 is one more row, with the form read off the *rival* instead of the holder. Finding this turned
the feature from an invention into an extension, and it is why the final patch is 78 bytes.

### What shipped

Two independent patches, one condition.

```
suppress if   self == pl005
           && rival alive        ([rcx+0x610] non-null, [ctrl+8] non-zero)
           && NOT the Dangai escape
           && rival.form == 0
```

**`fight_gate2.py`** wraps every `call 0x14046C230` whose owning function also stores to the meter,
forcing the return to −1 when the gate holds. 11 sites, 99-byte stride, cave `0x1413A2B00`, 1089 of
1280 bytes. It **discovers its own sites** by scanning `.text`, resolving owners from `.pdata`, so
the list cannot go stale. The 8 reader-classified sites (HUD, debug menu, the adder's own callers)
are left alone — forcing −1 at a reader would blank pl005's gauge instead of suppressing a gain.

**`fight_gate3.py`** replaces the 6-byte `mov eax,[rcx+0xC00]` at `0x14046C30E` with a jump to a stub
at `0x1413A3000`, which either jumps to `0x14046C3A6` (the adder's own no-accrual exit) or back to
`0x14046C314`. `rcx` needs no proof here: it is the adder's own first argument.

The adder's five callers, none of which the wrapper could reach:

```
0x14049131C / 0x1404914A2   owner 0x1404907B0   vtable sibling of the stock-loss slot (Δ0x138);
                                                grants only while meter/cap is under a threshold
0x140516698                 owner 0x140516340   computes its index INLINE, never calls the selector
0x14052FF19                 owner 0x14052FEC0   tail jump (E9)
0x14052FFA4                 owner 0x14052FF30
```

### ⚠⚠ Why the wrapper alone missed the hit path

The installer classified sites by asking "does the owning function store to the meter?" Functions
that delegate to the adder **don't**, so they were filed as harmless readers and skipped. Landing
hits and taking hits were in that set, and `0x140516340` would have escaped no matter how the
classifier was written, because it never calls the selector at all.

★ **Classifying call sites by what the caller does is a proxy, and proxies leak.** Enumerate the
*writers* of the state you care about and cover every one. The audit that closed it was a byte scan
for the meter displacement across `0x140460000..0x140540000`:

```
0x14016E900 gated   0x140176980 gated   0x140467B60 gated (stock loss)   0x14046C39F ★ the ADDER
0x140475775 / 0x14047598A / 0x140475A9B gated (blue / yellow / white reverse passives)
0x140492E1C / 0x140492F2B / 0x14049325C gated (the three reverse bursts)
0x1404BC6D8 gated   0x1404F9136 gated
0x140471D73  bulk `movups [rsi+0x1110], xmm0` — resets all five cells, not an accrual
0x14047D593  `mov [rdx+0x1110], r8d` — setter
```

### The six wrong builds, and what each one proved

Every one of these was a real measurement. Together they are why the final shape is right.

1. **v1 — crash, fault `0x13a2c36`.** `cmp dword [rdi+0xC00], 5` in all seven stubs. `rdi` is not
   the fighter at that site: the attack-parameter reader's prologue does `mov rdi, rdx`, so rdi is
   its *second argument*, and it is reassigned later. **The bad reasoning is worth naming:** rdi was
   "proved" to be the fighter from `movsxd rax,[rdi+0x1094]` at `0x1403C2D74` — 13 KB later inside a
   21 KB function — and the installer then "verified" that same signature function-wide and reported
   everything green. A signature that is not local to the patch site proves nothing about the site,
   and such a check is worse than none because it manufactures confidence.
2. **v2 — crash, fault `0x13a2caf`.** `[rsi+0x500]`, but `mov rsi,[rsp+0x58]` at `0x1403C078C`
   reassigns `rsi` to `this`, and every piece of supporting evidence sat downstream of that. Same
   error, different register.
3. **v3 — silent no-op.** `[rdi+0x5D0]` is the *base of a weak-ref struct*, not the rival pointer.
   The object is at `+0x5F0` (base+0x20) and the control block at `+0x610` (base+0x40), derived from
   the engine's own use of the lock's output at `0x140492FE1` / `0x140493024`.
4. **v4 keyed to the attacker, v5 keyed to the receiver** — mirror-image symptoms. Together they
   proved **`fighting_base` is a single pot paying BOTH fighters for one hit**, so no key on that
   value can ever separate the sides. This killed the entire "neutralise the amount" family and
   forced the move to "suppress the recipient".
5. **v6** — `fighting_recv_rate` does not feed the receive gain either; it is a multiplier on
   `fighting_base`. That is why zeroing `fighting_base` in the diagnostic killed both directions.

★ **The diagnostic that unlocked it** (`fight_diag_v1.py`): replace a 5-byte
`call <named-float accessor>` with `0f 57 c0 90 90` — `xorps xmm0,xmm0; nop; nop` — so the following
`movss` stores 0.0. Same length, no cave, position-independent, reversible from constants, and it
answered in one launch two questions static analysis could not settle, because the vtable slot is
shared across classes.

★★ **The rule all six failures reduce to: patch where the value is an ARGUMENT.** `fight_gate3.py`
hooks inside a function whose own first parameter is the fighter; every `fight_gate2.py` stub reads
`rcx` at a call boundary. Four builds were lost to register provenance, and the fix in the end was
not better proof — it was choosing sites where provenance is not a question.

### ★★★ The Dangai (pl002) matchup — four builds, two informative negatives

Dangai never leaves base form. He advances through three **"conclusion"** levels, one per kikon
landed. The first two deal **no soul damage** and instead hand the opponent enough fighting spirit to
force their next transformation; the third transforms him mid-cutscene and deals 9 konpaku damage,
ignoring revives. A gate keyed on "rival in base" is therefore permanently on against him, which
would leave Zangetsu leashed for the entire match.

| build | Dangai clause | measured in game |
|---|---|---|
| 1 | stock-loss path pays vs pl002 | kikons 1+2 **nothing**; kikon 3 (9 soul damage) paid a little |
| 2 | anything pays while pl002 is mid-kikon (`byte [rival+0x9A8]`) | kikons 1+2 **nothing** |
| 3 | pl002 exempt outright | works — full stock behaviour in that matchup |
| 4 | leash until `[rival+0x1A40] != 0` | ✓ shipped — kikon 1 gives evo immediately |

Build 1's split result is the informative one: it pins the stock-loss path as **strictly
damage-proportional**, so zero soul damage means zero spirit — and it positively confirmed the stub,
the weak-ref chain and the pl005-only scoping all worked. Build 2 ruled out the kikon window,
which means the payout most likely lands the instant the attack *connects*, before the cutscene
raises the flag. **Build 3 is the one that mattered**: taking the leash off entirely proved that
*our own hooks* were what blocked the grant. Had it failed, the block would have been somewhere
never examined and every refinement would have been wasted.

**Conclusion level is `fighter + 0x1A40`, a float**, found at:

```
0x14014B583  cmp dword [rdx+0xC00], 2        ; owner 0x14014ABD0
0x14014B590  movss xmm0, [rdx+0x1A40]        ★ the conclusion level
0x1406B1630  cmp dword [rdi+0xC00], 2 ; cmp dword [rdi+0x1094], 1 ; movss xmm0, [rdi+0x1A40]
```

It is the base of the `AddUniqueVal` array, inside the `+0x1A10..+0x1A74` block that `0x140460A24`
bulk-zeroes at init — so it starts at 0 and is exe-written, which is the shape a per-match
progression counter has to have. ⚠ It is **not** `UNIQUE_1`/`UNIQUE_2` (`+0x1A38`/`+0x1A3C`), which
were the obvious guess: those gate his `atk_hi03_1`/`atk_hi03_2` melee blocks and are the only two
condition strings in his entire `.tadjpkg`. pl002 has no `AddUniqueVal` blocks and all-zero
`unique_val1..12` in `CharaStatus.fsv`, so the exe writes `+0x1A40` directly.

Both Dangai behaviours ship in one installer, selected with `--dangai exempt | conclusion`. Because
they lay out on the same stride the detours are byte-identical between them, so switching rewrites
only the cave — no revert cycle and no window where a live detour points at a half-written stub.

### ⚠ One behaviour worth putting in the test notes

The gate keys on the **opponent's** form, not Zangetsu's. In real matches that is indistinguishable
from "base only", because he cannot reach evo without them evolving first (or via Dangai's kikon).
But in training mode, forcing Zangetsu to evo against a base-form opponent leaves him gaining
nothing. That is the rule as written, not a defect — but it will be reported as one.

---

## Part 9 — Model scale and cutscene framing

### ★★★ Scale is per FORM, and it is the root cause of every framing failure

`Script/CharaModelVisible.fsv` carries `scaleA` / `scaleB` / `scaleC` / `scaleD` — the model render
scale, **one per form**: A = base, B = evo, C = reverse. The roster spans 0.727 (pl026) to 1.35
(pl023).

A cutscene camera is a **baked path**. Play it against a model even 9% off the size it was authored
for and the framing error is **proportional to camera distance** — severe in a close-up, mild in a
wide. That is why a `pos`/`rot` offset can never fix it: an offset shifts the shot by a fixed
amount, so correcting the close-up wrecks the wide.

★ **A framing error that changes across a cutscene is a scale mismatch, not an offset one.** Check
the form's scale before touching `demo_cam.py`.

pl005 shipped at **1.136 — byte-identical to sp000's**, inherited from the boss and never adjusted.
The final values:

| field | form | value | why |
|---|---|---|---|
| `scaleA` | base | **1.13** | pl052's exactly. His native 1.136 is a 0.5% change, so he keeps his size and every pl052-authored camera frames him |
| `scaleB` | evo | **1.0** | **ad017's own scale.** The evo model is `cosB = ad017_cos00` |
| `scaleC` | rev | **1.0** | **en028's own scale.** The rev model is `cosC = en028_cos00` |

⚠ An earlier pass set all three to 1.13, treating the field as "how big is this character" rather
than "how big is *this form's model*". **Read the donor character's own row and copy it, per form.**

⚠⚠ **And read the right donor.** The first correction pass used en028 for evo and ad018 for rev,
taken from a stale index line (see Part 13). `scaleB = 1.0` happened to be right anyway — ad017 and
en028 are both 1.0 — but `scaleC = 1.047` was ad018's, and that mismatch is what made the rev
cutscene aim above the character with the wrong zoom. `CharaModelVisible.fsv`'s `cos` columns name
the model per form and settle it in one query:

```
pl005  cosA=pl005_cos00 scaleA=1.13   cosB=ad017_cos00 scaleB=1.0   cosC=en028_cos00 scaleC=1.0
en028  scaleA=1     ad017 scaleA=1     ad018 scaleA=1.047     sp000 scaleA=1.136
```

### The max-charge kikon cutscene

The demo that plays on fully charging a maxed kikon was Yhwach's. Confirmed by hashing every entry
with the id token normalised out: `pl005_ct_sp_break01_maxout` was **identical to
`pl052_ct_sp_break01_maxout`**, and had been since the earliest backup on disk.

Base now uses **`sp000_ct_sp_break01_maxout`**, his own from story mode. Evo uses
**`en028_ct_sp_break01_maxout`** — en028 *is* his evo model, so that is the authentic one rather
than a borrow.

★ **Scale and donor choice are one decision, not two.** en028's camera was baked against a 1.0
model, so it only frames correctly because `scaleB` is now 1.0. Either fix alone would have looked
wrong.

⚠ The first evo attempt carried **Yhwach's `wep01`/`wep02` slots** over from the placeholder it
replaced — `retarget_demo.py` fills empty cast slots from the existing destination, which is correct
when the destination is the character's own file and wrong when it is a placeholder. Redone from a
clean slate.

### ★★★ When NOT to rename the cast — the rev misframing

`retarget_demo.py` renames every id token in the package, cast included, so the demo casts
`pl005_cos00_00` / `pl005_face00_00` / `pl005_hair00_00`. **That is only correct when the form's
model is the same body as pl005's base.**

```
base   cosA=pl005_cos00   pl005's base IS sp000's model     -> rename correct
evo    cosB=ad017_cos00   ad017 is the same Zangetsu body   -> rename correct
rev    cosC=en028_cos00   a different build entirely        -> rename WRONG
```

Symptom, filmed side by side against the story-mode original: the camera starts correctly on the
face — so the camera path is right — and the character then **sinks out of the bottom of the frame**,
leaving several seconds aimed at empty scenery. The head is simply not where a camera baked around
en028's proportions expects it.

★ The diagnosis came from one fact, not from reading camera data: after the retarget the evo and rev
packages were **byte-identical** (`md5 d2880f87…` both), yet evo framed correctly and rev did not.
Two identical files cannot render differently, so the fault had to be in the form — and the only
per-form inputs are the model, the scale (both 1.0) and the weapon gates. **When two identical
inputs give different outputs, stop reading the input.**

**Fix: copy `en028_ct_sp_break01_maxout.tdemopkg` to `pl005_rev_ct_sp_break01_maxout.tdemopkg`
verbatim, renaming nothing.** The package is then self-consistent by construction — camera
reference matches its entry, cast names are en028's own — and en028's models are already fully
registered in `filename.bin` and `file_exist.htable` because it is a shipped story character. A
demo casting another character's models is normal: pl020's rev loads pl021's whole model, and
pl005's shipped rev demos cast pl052's.

⚠ Corollary for the remaining rev work: **do not "fix" the pl052 cast rows in the other rev demos
by renaming them to `pl005_*`.** That would introduce this same bug everywhere. They want en028's
names, or a slot-by-slot map — never a blanket rename. Both demos now audit clean: every cast name resolves to a file that exists, no stray
ids. Rev's maxout was a pl052 placeholder until the form assignment was corrected; it now uses
`en028_ct_sp_break01_maxout`, its own character's. See Part 13.

### ★★ The dangling camera reference — 27 demos, one silent cause

A `.tdemopkg` names its camera **twice**: once as an entry inside the `_demo_cam` archive, and once
as a `CameraMotion` `mot_name` in `_demo_csv`. They have to agree.

An earlier pass renamed pl005's demos from their pl052 donor with a **blanket byte replace over the
whole package**. That works on `_demo_mot`, `_demo_cam` and `demo_act0`, which are plain with
fixed-width name fields. It does nothing at all to `_demo_csv`, because **that entry is
`_cso_`-ciphered and the literal bytes are not in there to replace.**

```
pl005_rev_ct_sp_break01_maxout
   csv asks for : pl052_rev_ct_sp_break01_maxout_cam.tcm    <- never renamed
   package has  : pl005_rev_ct_sp_break01_maxout_cam
```

The engine finds no camera and falls back to an unaimed one — the symptom is a cutscene that plays
correctly while the camera stares at the ground or the sky. It is completely silent: nothing errors,
and every tool that lists package contents shows a correctly-named camera.

`demo_camref_fix.py` repaired **16 files / 19 references**, rewriting a reference only where the
package demonstrably contains that camera under the pl005 name. It deliberately does not touch the
cast rows — pl005's rev demos legitimately cast pl052 models, and renaming them would point at
`pl005_face01_00` and `pl005_wep02/03_00_00`, none of which exist on disk, which is the classic
`0xC0000005`.

**Eight demos remain unfixable by rename** — the four base and four evo `ct_stage_*_out` transitions
have an **empty `_demo_cam` archive**, so they reference a camera the file does not contain at all.
pl000's equivalent ships one. That is missing content and needs a donor, not a reference repair.

---

## Part 10 — Release, the dev build, and the recipe debt

### How the build reaches players

`Zangetsu Patch/sync_to_dev.py <gamedir> --apply` pushes to the dev environment at
`Bleach-Rebalance-Of-Souls-Dev-Environment/GameVersions/<version name>`. It finds modified files by
their `.pre*_bak` sibling, so a file we *edited* is detected automatically and a file we *created*
has to be listed in `CREATED`.

⚠ **Always dry-run first. "N new" on an established tree means it resolved the wrong root.** That is
not hypothetical: `REPO_ROOTS` once carried a hardcoded per-session mount path, and because the
Cowork mount path contains a per-session id, a later session fell through to a dead legacy copy and
reported "191 new, 0 updated" — one `--apply` away from pouring the entire build into the wrong
tree. It now globs `/sessions/*/mnt/...`.

⚠ **`Overlay/` is a release snapshot that is copied over the live install on every launch.** A stale
one silently rolls the build back — this cost a full day once, and the community patch was blamed
for it before the real cause was found. `sync_to_dev.py` now reports and refreshes stale Overlay
copies as part of the sync.

**A fix applied in this pass:** the scan was shipping `.pre*_bak` files to end users. `ui_bak_arrowfix.py`
had edited a backup in place and left a backup *of the backup* beside it, so the scanner treated the
backup as a live deliverable. `find_modified` now skips anything that is itself a backup.

### ✅ CLOSED 2026-08-10: the exe recipe debt, and the tool that keeps it closed

**The dev build does not ship an exe.** `sync_to_dev.py` skips `.exe` entirely; the release carries
`Exe/exe_patch.recipe`, and the launcher's `setup_exe()` replays it onto the player's own stock
binary and refuses to launch unless the result matches `R['md5']`. **A byte that is not in the recipe
does not exist for anyone but its author.**

The recipe is zlib-compressed JSON:

```
{grow_at, grow, sec_hdr:[[hdr_off,val],…], ops:[[file_off,"hex"],…],
 md5,                                     <- what a correct replay must produce
 src_md5, src_size, alt_sources:[{name, md5, ops}]}   <- accepted starting binaries
```

Replay: pick a source matching `src_md5` or an alt, apply the alt's normalising ops, insert `grow`
zero bytes at `grow_at`, write `sec_hdr`, apply `ops` in list order.

#### What was missing

Five scripts wrote the exe and none of them recorded: `ui_ctrl_v1_ownlogic.py`,
`ui_gauge_v5_classslot.py`, `ui_gauge_v6_ownslot.py`, `fight_gate2.py`, `fight_gate3.py`. Replaying
the recipe and diffing against the live exe found **235 divergent spans, 1905 bytes**:

| owner | spans | bytes | what |
|---|---|---|---|
| `fight_gate2` | 113 | 954 | 11 x 5-byte detours + the 1280 B cave at `0x1413A2B00` |
| `ui_ctrl_v1_ownlogic` | 71 | 578 | `.rdata` R-X flip at file `0x2D4`, two hooks, the 1024 B driver cave at `0x1413A2300` |
| `ui_gauge_v6_ownslot` | 36 | 207 | switch-A case 24, relocated dword table, `ActionUniquePl005_` string |
| `fight_gate3` | 12 | 66 | the adder hook at `0x14046C30E` + the 78 B Dangai-aware stub at `0x1413A3000` |
| `move_names_own_entry` | 3 | 99 | its table moved from `.text` to `.rdata` after its op was last written |
| `ui_gauge_v5_classslot` | 1 | 1 | switch-B byte table -> case 18 |

A tester's build therefore had **no fighting-spirit lock, no Dangai carve-out and no unique-gauge
logic**, and nothing about it looked broken — so the report would have come back as "your gate
doesn't work".

#### Two things that were actually wrong, not merely unrecorded

**`move_names_own_entry`'s op was eight bytes too long.** It was recorded when its cave ended at
`0x1411B4C58`; `ui_gauge_v6_ownslot`'s case body starts at `0x1411B4C50`. A replay wrote the tail of
one over the head of the other — a jump into the middle of an instruction. This is rule 30 caught in
the act, in the recipe rather than in the exe.

**A dead op at file `0x11B4058` blanked 132 bytes of `ui_gauge_v6`'s case body.** It is
`cre_exe_caves.py`'s char-select clone at its *old* `TAIL_VA` (`0x1411B4C58`, before the clone grew
to 131 bytes and moved to `0x1411B4DA0`). `build()` no longer emits it, so it survived only as a
leftover — and only worked because it happened to sit earlier in the ops list than the gauge would
have. `_recipe_put` exists precisely so replay never depends on that ordering.

#### `exe_recipe_sync.py`

The fix is one tool rather than five copies of a recording routine, because five copies means five
chances to skip it:

```
python exe_recipe_sync.py <gamedir>            # audit, exit 1 if the recipe is behind
python exe_recipe_sync.py <gamedir> --apply
python exe_recipe_sync.py <gamedir> --spans    # list the declared windows
```

It replays, diffs, and then **attributes every divergent byte to a declared window in its `OWNERS`
table — a byte with no owner is a FATAL, never something to launder into the recipe.** That is the
whole safety property: a stray hand edit or a half-reverted experiment is caught here instead of
shipping. Attribution is byte-by-byte, not span-by-span, because `move_names`' cave ends exactly
where `ui_gauge_v6`'s case body begins and a 45-byte run straddles the seam.

Two more properties worth copying:

* **Windows are declared wider than the bytes that currently differ** — a whole cave, not the used
  part. The recorded span then stays correct when a stub gets longer or shorter, and a later re-run
  of the owning script hits `_recipe_put`'s patch-in-place path instead of its partial-overlap fatal.
* **Each declared hook is checked to be a real `jmp` into its own owner's cave** before anything is
  written. That caught nothing this time, and would have caught a mis-declared table instantly.

Acceptance: all six recipe-aware scripts were re-run afterwards and each independently verified
"replay from stock reproduces the live exe byte for byte". `ops` 166 -> 190; the recipe now builds
`56fae3f6e2131f4a0fede0ea9433eddf`, the live exe.

★ **`fight_gate3.py --show` mislabels the installed stub.** It printed "69 B exempt stub" against a
live cave holding the 78-byte conclusion variant (`cmp eax,5 / jne +0x3e`, and the
`cmp [rdx+0x1A40],0` clause). The bytes on disk are right; the label is not. Do not use `--show` to
decide which Dangai mode is installed — read the stub length.

### ⚠⚠ Only four folders reach a player

`injectFolder` in the launcher copies exactly **`Script`, `Motion`, `00HIGH`, `01MIDDLE`**.
Everything else — `Demo/`, `Sound/`, `Text/`, `Fnames/`, `ui/`, `adv_motion/`, `Physics/`,
`AiAttackData/` — reaches a player **only** through `Overlay/`, which `install_overlay` merges file
by file.

So a file written to `<version>/ui/…` and nowhere else is installed on nobody's machine while
sitting in the repo looking shipped. `sync_to_dev.py`'s "never create a new `Overlay/` entry" rule is
the right default — creating one changes what the version installs — but taken literally it makes
any genuinely new file outside those four folders undeliverable. `OVERLAY_NEW` is now the listed
exception: each entry names a file that must start being installed, and why.

**What this hid: pl005's entire unique-gauge asset package.** `ui_gauge_v8_package.py` registers the
groups `UIActionUniquePl005_0/_1` in `Fnames/filename.bin`, and `filename.bin` *was* being shipped
because it has a backup beside it. The eight files those groups point at were created outright, so
they have no `*_bak` sibling and `find_modified` never saw them:

```
ui/ui_ActionUniquePl005_{0,1}_{fnt,mot}.cat
ui/script/scene/ActionUniquePl005_{0,1}.bin
ui/script/anim/ActionUniquePl005_{0,1}.bin
```

A registered group whose members are absent **misses silently and returns the empty string**
(DataChakka `FnamesVfs.h`), so the symptom was not a crash — it was the gauge not drawing, on a build
where the exe patch, the switch case and the layout name were all correct. The `_mdl.cat` halves live
under `00HIGH/ui` and `01MIDDLE/ui` and *did* ship, which is what made it so easy to miss: half the
package was there.

★ The general check is worth keeping: for every live file matching the character id, classify it as
**vanilla-same / modified / new** against `_launcher_vanilla_backup`, then require everything that is
not vanilla-same to be present and byte-identical in the dev build. It found ten gaps in a tree that
`sync_to_dev` had just reported as fully in step. pl005's models, physics, sounds and AI data are all
*vanilla* — pl005 is a base-game slot that CRE made playable, which is why `IsPlayableCharacter` has
to admit id 5 — so they correctly do not ship, and only a content-level comparison can tell the two
cases apart.

### ⚠ Backups were shipping to players

Thirteen `*_bak` files were sitting inside the shipped tree — six in `Overlay/`, seven in `Script/`
and `Motion/` — totalling 3.8 MB copied into every player's install on every launch. `find_modified`
learned to skip backups; the ones already in the version folder from before that fix stayed, and
`check_overlay` never flagged them because the same backups exist in the live game, so they matched.
Nothing loads them (the game binds on exact filenames) but a backup in a shipped tree is always a
mistake. `sync_to_dev.py` now walks `Overlay/`, `Script/`, `Motion/`, `00HIGH/` and `01MIDDLE/` and
reports any it finds.

The Overlay manifest had also drifted — 222 entries against 234 real files. Nothing reads it
(`_overlay_pairs` walks the directory), but it is the human-readable record of what a version
installs, so it is regenerated from the tree.

---


---

## Part 11 — The rules

These are the findings that generalise past pl005. Most were bought with a crash or a wasted test
cycle. If you read one part of this document, read this one.

### On identity and binding

**1. The name you can see is not the name the engine binds on.** This is the single most expensive
lesson in the project and it recurred in four different file formats. A `.tadjpkg` blob carries its
own category, node and motion strings; a `.tactpkg` blob carries its own inner JSON key; a
`.tdemopkg` camera is named once in an archive entry and again inside a ciphered CSV; a
`filename.bin` row is keyed by hash(group, logical name). Renaming the container never renames the
binding. Every failure of this class is **silent** — the move does not come out, the gauge stays
empty, the camera points at the sky — and every listing tool shows the correct name.

**2. Standard actions are keyed by id, not by name.** A node called `atk_da01` sitting on any id but
6 is not a dash attack. Restoring a standard move to a trimmed character means giving it its
canonical id.

**3. A transplanted node's variables must match the reference character's values for that node, not
the node it was cloned from.** The dash attack came out inconsistently for weeks because it carried
`act_frame_min/max = 18/30` and `hit_combo_stop = 1` inherited from `atk_hi01`.

**4. If a cancel or link happens earlier than any window allows, stop tuning frames and go looking
for an orphan.** An unreferenced node that still has an input is gated by nothing, so any open combo
window anywhere in the moveset can fire it. Two separate infinites came from this. The diagnostic is
one query: list nodes with a non-empty `input_text` that appear in no other node's `nexts`. The
answer should be exactly `sp_step_atk00` plus one `RecvEvent` node — anything else is a live exploit.
⚠ And `RecvEvent` + orphan is the *normal* event-entered pattern. Do not "clean" those.

### On patching the executable

**5. Prove the register at the address you are patching.** Two `0xC0000005`s came from signatures
found thousands of bytes away inside very large functions. A signature that is not local to the
patch site proves nothing about the site — and a check like that is worse than none, because it
manufactures confidence.

**6. Better still, patch where the value is an argument.** Four builds were lost to register
provenance. The fix in the end was not better proof; it was choosing a site — inside a shared
routine, at a call boundary — where provenance is not a question.

**7. Prefer a branch the game already takes.** The fighting-spirit gate jumps to the same
"do not accrue" exit that three shipped conditions already use, so nothing about register, stack or
xmm state had to be reasoned about. Look for an existing per-character exception before inventing a
mechanism; this engine writes them as `cmp [reg+0xC00], <id>` and there are dozens.

**8. When you cannot tell *which* call site does something, ask *when* instead.** Look for a state
flag the engine already keeps for its own rules.

**9. A `.pdata` record is not always a whole function.** Long functions get chained records, so a
record can start mid-function with no prologue and no callers. Absence of a record is not absence of
a function either — a leaf that never touches the stack needs none.

**10. Never hardcode a section's file offset from memory.** Parse the section table. One draft was
wrong by `0x121600` and would have written a stub into live read-only data.

**11. Derive the original rather than keeping a backup, where you can.** If the bytes you replace
are a fixed-length instruction with a computable operand, both install and revert can verify against
a computed value instead of a sidecar that can go stale.

**12. Site discovery must recognise the patched shape as well as the stock one.** Matching only `E8`
made a `--revert` a no-op that cheerfully reported "nothing installed" while ten detours were live.

**13. A patch that does not register itself in the release recipe does not exist.** See Part 10.

### On data files

**14. `_cso_` keys are signed.** A `(\d+)` regex silently fails to match the minus sign and returns
the payload still enciphered; masking the key to unsigned breaks only `k[7]`, because the shift is
arithmetic. The damage looks like a handful of wrong bytes rather than noise, which is exactly why it
survives an eyeball.

**15. Edit ciphered payloads as bytes, never via decode/re-encode.** The payloads contain sequences
cp932 cannot represent, and a round-trip destroys them.

**16. Several `.fsv` files have bare-LF endings and are not valid UTF-8.** Split on the right
terminator, edit the decoded bytes in place, and never re-serialise.

**17. pl005 has two tadjpkg copies** — `pl005.tadjpkg` and `pl005_modded.tadjpkg`. Both must be kept
in step. A revert that touched only one caused a scale edit to compound to +44% instead of +20%.

**18. Check what a field actually means before scaling it.** `coll_angle` is an angular spread, not
a size — 360 appears 145 times. Never scale it.

### On measurement

**19. Poll the roster before choosing a number, and poll per action name.** A global mode is often an
artefact of one family. "3.0" looked like the homing default until the over-attack family was
excluded and every normal-string action voted 5.0.

**20. Measure root motion before copying a move rate.** Two clips that look alike can travel 3× apart.
Copying pl000's `2.0` verbatim would have massively overshot; the correct value was 1.25.

**21. A rate multiplier desynchronises authored frames from real ones.** `SlowMotionRate 2.0` over an
action's whole length halves its real recovery, and the authored numbers keep looking correct. Compute
the real gap by hand.

**22. Check the clip length before moving a frame number outward.** Hitboxes re-timed past the end of
an action simply do nothing, and a cancel frame past the end leaves the character with nowhere to
finish. This is why hi02's recovery is 66 and not the 76 the brief asked for.

### On process

**23. Before diagnosing "the fix didn't work", verify the fix is in the live file.** Two rounds of
testing were spent on a build that never contained the change. One `--revert` on an early script
restores a backup that predates every later pass — one revert silently rolled back four of them.
The one-command diagnostic is: md5 the live file against every `*_bak`, then diff per entry against
the closest match.

**24. Whole-file restore is only ever correct for a file one script owns outright.** Once half a
dozen scripts write into one package, rebuild **entry-scoped**: load the live package as the write
target and pull the single pristine entry from the backup. `--revert` needs the same treatment. This
class has bitten three times, and the third was caught only by reading the script before running it.

**25. Assume any `*_bak` older than today predates work you care about.** When re-applying a chain of
passes, archive the stale backups first (`mv x_bak x_bak.stale<date>`) so each script snapshots the
current file.

**26. An unexplained md5 is a bug, not noise.** Two hashes differing after a "restore" differed by
exactly the eight damaged bytes.

**27. Ship the widest version that is guaranteed to work when a narrow fix keeps failing for unclear
reasons.** It is both a fix and the only clean experiment that separates "our patch is wrong" from
"our patch is innocent" — and it leaves something playable while the refinement is built. Build 3 of
the Dangai carve-out is the example: it worked, and in working it proved the block was ours.

**28. Record retracted theories as carefully as fixes.** The next person will find the same evidence.
The SP2 colour thread alone burned nine hypotheses, and the connect-cutscene thread two, before
landing.

**29. When two patches share a reserved cave block, make the boundary exact.** One installer zeroes
its whole window on revert, which will blank a neighbour's live stub. Put nothing of yours below the
line.

**30. Publish every cave window in the cave map, and assert on your neighbours' starts.** The
`0x11b4c50` crash was one script's end-of-region constant overlapping another's case body by eight
bytes, and it hid for weeks because the two writers happened to alternate.

**31. Only four folders reach a player.** `injectFolder` mirrors `Script`, `Motion`, `00HIGH` and
`01MIDDLE`. Everything else is installed only if it has an `Overlay/` entry. A file in the version
folder outside those four and outside the Overlay is shipped to nobody while looking shipped.

**32. A file that was created rather than edited is invisible to `sync_to_dev`.** The scan finds work
by its `*_bak` sibling, and a new file has none. Eight files of pl005's unique-gauge package sat
unshipped for three weeks that way, with `filename.bin` registering the groups that pointed at them.
Anything created outright must be listed in `CREATED`, and if it lives outside the four mirrored
folders, in `OVERLAY_NEW` as well.

**33. Prove a file is modified before assuming it must ship, and prove it is unmodified before
assuming it must not.** Comparing the live game against `_launcher_vanilla_backup` splits every file
into vanilla-same / modified / new. pl005's models, physics, sounds and AI data are all vanilla — he
is a base-game slot CRE made playable — so they correctly do not ship, and only a content comparison
tells that apart from a genuine gap.

**34. Attribute every divergent byte to a declared owner before recording it.** A catch-up that
simply records whatever differs will happily launder a stray hand edit or a half-reverted experiment
into the release. `exe_recipe_sync.py` goes fatal on an unowned byte instead, which is the only
reason it is safe to run unattended.

**35. A backup inside a shipped tree ships.** Thirteen `*_bak` files, 3.8 MB, were being copied into
every player's install. `check_overlay` had never flagged them because the same backups exist in the
live game, so they compared equal. Compare against what *should* be there, not only against what is.

---


---

## Part 12 — Tooling

Every script named anywhere in this guide, with the part that explains it. All of them live in
`Zangetsu Patch/` unless noted. Most support `--dry`, `--show` and `--revert`; the ones that write
the exe derive and verify their own stock bytes rather than keeping a backup.

| script | described in |
|---|---|
| `actpkg.py` | Part 3, Part 4 |
| `add_costume_slot.py` | Part 2 |
| `add_ct_stub.py` | Part 5 |
| `add_select_voice.py` | Part 2 |
| `apply_D10.py` | Part 1 |
| `assemble_zangetsu_hiyori_version.py` | Part 1 |
| `attack_test.py` | Part 3 |
| `bootstrap.py` | Part 6 |
| `bros.py` | Part 6 |
| `bros_audio.py` | Part 2 |
| `bros_bc7.py` | Part 6 |
| `bros_model.py` | Part 6 |
| `build_hiyori40.py` | Part 2 |
| `build_icon.py` | Part 1 |
| `build_sp2.py` | Part 1, Part 5 |
| `build_spstep_v11.py` | Part 4 |
| `byakuya_petal_form.py` | Part 5 |
| `cat_diff.py` | Part 1 |
| `caveasm.py` | Part 2 |
| `combo_patch.py` | Part 3 |
| `cre_exe_caves.py` | Part 1, Parts 7-10 |
| `cre_tables.py` | Part 3 |
| `dash_fix.py` | Part 3, Part 4 |
| `demo_cam.py` | Part 2, Part 5, Parts 7-10 |
| `demo_camref_fix.py` | Parts 7-10 |
| `fight_diag_v1.py` | Parts 7-10 |
| `fight_gate2.py` | Part 1, Parts 7-10 |
| `fight_gate3.py` | Part 1, Parts 7-10 |
| `fight_gate_v1.py` | Part 1 |
| `fix_attacks.py` | Part 1, Part 2, Part 3 |
| `fnames_patch.py` | Part 1, Part 2, Part 6 |
| `fsv2csv.py` | Part 1 |
| `grab_warp.py` | Part 3 |
| `graft_gr02.py` | Part 3 |
| `graft_kikon_demo.py` | Part 5 |
| `grid_cells_40_41.py` | Part 1 |
| `grid_heapfix.py` | Part 1 |
| `hair_color.py` | Part 2 |
| `hair_probe.py` | Part 2 |
| `hair_ramp.py` | Part 2 |
| `hi_recovery_v1.py` | Parts 7-10 |
| `hiyori_art_install.py` | Part 2 |
| `hiyori_icons_install.py` | Part 2 |
| `hiyori_install.py` | Part 2 |
| `hiyori_reloc_complete.py` | Part 2 |
| `ichibei_one_loop.py` | Part 3 |
| `io_bros_anim.py` | Part 4 |
| `light_string.py` | Part 3 |
| `move_names.py` | Part 2 |
| `move_names_own_entry.py` | Part 1, Part 2, Part 5, Parts 7-10 |
| `move_rates_v1.py` | Part 4 |
| `pl005_graph_orphans.py` | Part 4 |
| `pl005_lo03_recovery.py` | Part 4 |
| `pl005_reach_links.py` | Part 4 |
| `pl005_tracking.py` | Part 4 |
| `pl015_stepchain_fix.py` | Part 3, Part 4 |
| `recon.py` | Part 3 |
| `register_costume_models.py` | Part 1, Part 2, Part 3 |
| `register_menu_pkg.py` | Part 2 |
| `restore_fnames_registrations.py` | Part 1, Part 5 |
| `restore_sp2_routing.py` | Part 1, Part 5 |
| `retarget_demo.py` | Parts 7-10 |
| `set_model_scale.py` | Part 2 |
| `sp1_motion_v1_aterie.py` | Part 4, Parts 7-10 |
| `sp1_probe.py` | Part 6 |
| `sp1_probe2.py` | Part 6 |
| `sp1_survey.py` | Part 6 |
| `sp1_v10_final.py` | Parts 7-10 |
| `sp1_v1_neutral.py` | Part 6 |
| `sp1_v2_ladder.py` | Part 6 |
| `sp1_v3_lock_move.py` | Part 6 |
| `sp1_v7_twins.py` | Part 3 |
| `sp2_bisect.py` | Part 5 |
| `sp2_burst.py` | Part 5 |
| `sp2_fix_act.py` | Part 5 |
| `sp2_hitconfirm.py` | Part 5 |
| `sp2_hybrid.py` | Part 5 |
| `sp2_planC.py` | Part 5 |
| `sp2_pureblack.py` | Part 5 |
| `sp2_rim.py` | Part 5 |
| `sp2_v11.py` | Part 5 |
| `sp2_v12.py` | Part 5 |
| `sp2_v14.py` | Part 5 |
| `sp2_v15_autocombo.py` | Part 3, Part 5 |
| `sp2_v16_purple.py` | Part 5 |
| `sp2_v17.py` | Part 5 |
| `sp2_v18.py` | Part 5 |
| `sp2_v19_cast.py` | Part 5 |
| `sp2_v19_cost.py` | Part 5 |
| `sp2_v20_continuity.py` | Part 5 |
| `sp2_v21_killfade.py` | Part 5 |
| `sp2_v22_redesign.py` | Part 5 |
| `sp2_v23_fill.py` | Part 5 |
| `sp2_v24_softparticle.py` | Part 5 |
| `sp2_v25_restore_look.py` | Part 5 |
| `sp2_v28_pureblack.py` | Part 5 |
| `sp2_v29_parts.py` | Part 5 |
| `sp2_v31_body.py` | Part 5 |
| `stage_fnames_project.py` | Part 1 |
| `status_patch.py` | Part 4 |
| `stepatk_damage.py` | Part 3 |
| `sync_to_dev.py` | Part 1, Part 5, Parts 7-10 |
| `tadj_lib.py` | Part 3 |
| `tmd2_hair_color.py` | Part 2 |
| `tmo_lib.py` | Part 4 |
| `try_ct_node.py` | Part 5 |
| `tune_hiyori_model.py` | Part 2 |
| `tune_pass13.py` | Part 3 |
| `tune_pass15.py` | Part 3 |
| `tune_pass16.py` | Part 3 |
| `tune_pass17.py` | Part 5 |
| `ui_bak_arrowfix.py` | Parts 7-10 |
| `ui_ctrl_v1_ownlogic.py` | Part 1, Part 6, Parts 7-10 |
| `ui_gauge_v6_ownslot.py` | Part 1, Part 6 |
| `ui_gauge_v8_package.py` | Part 6, Parts 7-10 |
| `ui_icon_v2_moon.py` | Part 6 |
| `ui_icon_v3_moon.py` | Parts 7-10 |
| `ui_icon_v4_moon.py` | Part 6 |
| `ui_icon_v6_purge.py` | Parts 7-10 |
| `v2_build.py` | Part 3 |
| `voice_extract.py` | Part 2 |
| `whiff_fix.py` | Part 3, Part 5 |


---

## Part 13 — What is left: evo and rev

Base is finished. Evo and rev are placeholders, and this part exists so the next stage starts from
what is known rather than from scratch.

### What the forms are

**Evo is ad017**, a model-only NPC. **Rev is en028**, "Zangetsu (Fused)" — a full story fighter with
a complete moveset. Both models are already in the game.

⚠⚠ **This was recorded backwards for months.** `roster-add-evo-rev.md` documented Berg's
2026-07-27 swap in its body, but its frontmatter description still advertised the *original* plan
(evo = en028, rev = ad018) — and that description is what appears in the memory index. On
2026-08-10 the stale line was read and acted on: evo was given en028's cutscene and `scaleC` was set
to ad018's value, which misframed the rev cutscene. ★ **An index line can be stale relative to
the body it summarises. When a fact drives a change, confirm it against the data.** Two queries
settle it: `CharaModelVisible.fsv`'s `cosB`/`cosC` columns, and the fact that pl005's `3_rev_*`
actions reference `en028_atk_hi01`/`en028_atk_hi02` motions while his `2_evo_*` actions reference
pl052's.

The two forms are not equally far along. Evo has a full set of `2_evo_*` actions carried over from
the port, including `evo_atk_hi01` / `evo_atk_hi02` with real timings (recovery 29 and 83
respectively). Rev has `3_rev_*` entries of the same shape (36 and 40). What neither has is tuning
that anyone chose on purpose — they are donor values that happen to load.

### What is already correct

* **Model scale** is now per form and right: `scaleB = 1.0` (ad017's own) and `scaleC = 1.0`
  (en028's own). Part 9.
* **The max-charge cutscenes** are assigned: base `sp000`, evo `en028`, rev `en028`. Rev gets it
  because rev *is* en028; evo keeps it because ad017 ships no demo and en028's camera was baked at
  scale 1.0, which is also ad017's — so it frames correctly.
* **The unique gauge and enhance state** are form-agnostic and already work.
* **The fighting-spirit lock keys on the opponent's form**, so it needs no per-form work. Note the
  training-mode caveat in Part 8.
* **16 of the 27 dangling camera references** are repaired, including every evo and rev cutscene
  that had a camera to point at.

### What is known to be wrong or missing

**Rev's maxout cutscene is now en028's** — its own character's, since rev *is* en028. Evo keeps
en028's as well: ad017 ships no demo at all, and en028's camera was baked at scale 1.0 which is also
ad017's, so it frames correctly. Berg on the evo result: "works wonder… it's original and looks
great on him."

**Every rev demo casts pl052 models.** `pl005_rev_ct_*` cast rows are Yhwach's costume, face, hair
and four weapons. That is the shipped placeholder state, not a bug introduced here — but it means the
rev form currently appears as Yhwach inside its own cutscenes. ⚠ Renaming those rows is **not** a
rename job: `pl005_face01_00`, `pl005_wep02_00_00` and `pl005_wep03_00_00` do not exist on disk, and
an unregistered model name is the classic `0xC0000005`. The cast has to be mapped slot by slot
against a row that is proven to load for him, exactly as the Halibel kikon graft was done in Part 5.

**Eight stage-transition demos have no camera at all** — the four base and four evo
`ct_stage_*_out` files have an empty `_demo_cam` archive while their scripts reference a camera by
name. pl000's equivalents ship one. That is missing content and needs a donor.

**`scaleD`** is still empty, and the notes never establish what the fourth slot is for.

**Evo and rev movesets are untuned.** None of the work in Parts 3, 4 and 11 — canonical ids, homing
coverage, combo-window norms, the recovery poll, root-motion measurement — has been applied to
`2_evo_*` or `3_rev_*`. The `sp_step_atk` string in particular has no evo parity, which was already
flagged as outstanding when the base string shipped.

### The order that will probably hurt least

The base build's history suggests a sequence. Registration and identity first, because those failures
are silent and poison every later test: verify every `2_evo_*` / `3_rev_*` cast name and asset
resolves in `filename.bin` and `file_exist.htable` before touching tuning. Then the graph — canonical
ids and an orphan sweep, since an orphaned node with an input is an exploit that no amount of frame
tuning will fix. Then tuning, using the polls in Part 4 rather than eyeballed numbers. Cutscenes
last, as they already are on the base form, because they depend on scale and cast being settled.

The recipe debt in Part 10 is closed, and `exe_recipe_sync.py` keeps it closed — run it after any
exe work, before syncing.
