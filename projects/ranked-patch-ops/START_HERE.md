# BLEACH: Rebirth of Souls — Patch-Only Matchmaking Test Kit

Goal of this test: the two of us queue online and confirm that (1) we match
**each other**, (2) we match **only** each other (no strangers, no vanilla
players), and (3) we can play a full match on the patch **without desync**.

This works by adding one small module (`patch_ranked64.dll`) to the patch. It
tags our Steam matchmaking lobby with a shared **match code** and filters for
that same code, so only clients using the same code can find each other. It
changes nothing else and touches no game files.

---

## Who needs what

Both people need:
- The game on Steam.
- Berg's patch already working (the launcher that installs/reverts the patch).
  If you can currently play the patch online, you're set.
- The four files in this kit.

**The `patch_ranked.txt` match code MUST be identical for both of us.** It ships
set to `314159`. Keep it as-is (we both use this kit) — that is what makes the
pool private to just us.

---

## Install (do this once, with the PATCH installed)

1. Use the launcher to **install/enable the patch** (the state where you can
   play online). Fully close the game.
2. Copy these files into your **game folder** (the folder that contains
   `BLEACH_Rebirth_of_Souls.exe` and `version.dll`):
   - `patch_ranked64.dll`
   - `patch_ranked.txt`
3. Launch the game the normal way you launch the patch.
4. In the game folder you should now see a new file **`patch_ranked.log`**.
   Open it — you want a line like:

   ```
   match code 314159 loaded from patch_ranked.txt
   hooks installed OK -- matchmaking locked to code 314159 (vtable 000001F4...)
   ```

   If you see that, you're ready. If `patch_ranked.log` never appears, see
   **Troubleshooting** at the bottom.

---

## The test (do this together, on a voice/text call)

Pick **Free Match** for the pairing tests if possible — ranked can add
rating-based restrictions that make two specific people harder to pair. Agree on
the **same mode and region**, and start searching **at the same time** (count
down "3-2-1 search"). Steam's lobby list can take a few seconds; if you miss
each other, both cancel and retry together.

### Phase 1 — Do we match each other?
- Both: patch installed, `patch_ranked64.dll` + `patch_ranked.txt` (code 314159) in place.
- Both start searching at the same time, same mode/region.
- **Expected:** you find each other. In each `patch_ranked.log` you'll see
  `host: issuer tag ... -> 314159` and/or `search: issuer filter ... -> 314159`.
- ✅ Pass = you connect to each other.

### Phase 2 — Do we match ONLY each other? (exclusivity)
Two quick sub-tests:

- **2a (vs vanilla):** One person uses the launcher to **revert to vanilla**
  (or just deletes `patch_ranked64.dll`), relaunches, and searches. The other
  stays patched (code 314159) and searches at the same time.
  **Expected:** you do **not** match. (This is the desync case that can no
  longer happen.)
- **2b (different code):** Both patched, but one person changes line 1 of
  `patch_ranked.txt` to a different number (e.g. `271828`) and relaunches.
  Search together.
  **Expected:** you do **not** match — different codes are different pools.
  Afterward, set it back to `314159` for Phase 3.

- ✅ Pass = you fail to find each other in both 2a and 2b.

### Phase 3 — Can we play without desync?
- Both back on: patch installed, `patch_ranked64.dll` + code `314159`.
- Confirm you are both on the **same patch version** (same launcher build) — this
  is what prevents desync; the module only controls *who* you match.
- Match via Phase 1 and **play a full round to the result screen.**
- ✅ Pass = the match plays out normally, no desync/disconnect.

If all three phases pass, patch-only matchmaking works: we match, only us, and we
can actually play.

---

## Turn it off / roll back
Delete `patch_ranked64.dll` (and `patch_ranked.txt`). Revert the patch with the
launcher as usual. Nothing else was changed.

## Troubleshooting
- **No `patch_ranked.log` appears:** your Koaloader may not be auto-loading the
  new DLL. Rename `Koaloader.config.OPTIONAL.json` to exactly
  `Koaloader.config.json`, then relaunch. (If you already have your own
  `Koaloader.config.json`, instead add `{ "path": "patch_ranked64.dll" }` to its
  `modules` list.)
- **Log says `no patch_ranked.txt found`:** the txt isn't next to the game exe.
  Put `patch_ranked.txt` in the same folder as `BLEACH_Rebirth_of_Souls.exe`.
- **Log says code `invalid`:** line 1 of `patch_ranked.txt` must be a plain
  number and not 0, 8, 1, or 256 (those are reserved/vanilla values).
- **We still don't match in Phase 1:** make sure both logs show the *same* code,
  you're on the same region/mode, and you're searching at the same time. Try
  Free Match. Also confirm you can normally play the patch online at all.

## What's in this kit
- `patch_ranked64.dll` — the matchmaking module (x64).
- `patch_ranked.txt` — the shared match code (line 1). Keep both copies equal.
- `Koaloader.config.OPTIONAL.json` — only needed if auto-load doesn't pick up the DLL.
- `patch_ranked64.c` — the module's source code, for transparency / rebuilding.
