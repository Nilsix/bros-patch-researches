# Ranked/Online segregation — why it failed, how to verify, and the fix

## Short answer: it was almost certainly NOT active during your test

The module logic is correct (verified), but on your test machines the DLL
most likely never loaded, so the game used its normal matchmaking. Here's the
tell: **two patched-but-unhooked clients still match each other**, because with
no hook both fall back to the game's default `issuer` value (256). So "we
matched" did NOT prove the hook worked — you'd match anyway. The thing that
proved it was off is exactly what you saw: you also matched a vanilla player.

Why it didn't load: your launcher only mirrors the `Script` data folder and then
starts the game. It never installs the matchmaking DLL. Koaloader (your
`version.dll`) auto-loads *recognised* unlocker DLLs like `SmokeAPI64.dll`, but
**not an arbitrary DLL** like `patch_ranked64.dll`. With no Koaloader config
listing it, it just sat there unused.

## How to check it LIVE (do this first)

The DLL now writes a timestamped log next to the game exe: **`patch_ranked.log`**.

1. Launch the game. Open `patch_ranked.log` in the game folder.
   - If the file **doesn't exist** → the DLL isn't loading. That's the whole bug.
   - If it exists you'll see:
     ```
     [hh:mm:ss] ==== patch_ranked64 v2 loaded ====
     [hh:mm:ss] match code 314159 loaded
     [hh:mm:ss] HOOKS INSTALLED -- pool code 314159, join-guard ON (vtable ...)
     ```
2. Now start a **ranked/free search** and watch the log update in real time:
   - `SEARCH: filtering issuer 256 -> 314159 (our pool)` ← your search is being restricted to your pool.
   - `HOST: tagging issuer ... -> 314159` ← when you host/are matched into, your lobby is tagged.
   - `JOIN OK: lobby issuer 314159 matches our code` ← you joined a same-pool lobby.
   - `JOIN BLOCKED: lobby issuer 256 != our code 314159 ... refusing` ← the backstop stopped a cross-match (this is the desync that can no longer happen).

If you see those SEARCH/HOST lines during a ranked queue, the hook is genuinely
active. If you then still can't desync with vanilla, it's working.

## What changed in this build (v2)

1. **Loud live logging** (above) so you can verify instead of guessing.
2. **Join guard** — a third defense. Even if a wrong lobby slips through the
   search filter, before actually joining, the DLL reads that lobby's `issuer`
   and refuses to join if it isn't your code. This directly targets the
   "matched a vanilla and desynced" case. (Create an empty
   `patch_ranked_logonly.txt` next to the exe to make the guard log-only while
   diagnosing.)
3. **`Koaloader.config.json`** now ships in the game folder and explicitly lists
   both `SmokeAPI64.dll` and `patch_ranked64.dll`, so the module is
   **guaranteed** to load (this is the real fix for what went wrong).

## The real fix for your community: install via the launcher

Manually copying files won't scale — most users will end up like your test
(module not loaded). Integrate it into the launcher you push on GitHub so every
player gets it automatically. See `LAUNCHER_matchmaking_integration.py` for a
drop-in function. It does three things on every launch:

- copies `patch_ranked64.dll` into the game folder,
- writes `patch_ranked.txt` with a match code **derived from the patch version**
  (git snapshot) — so everyone on the current build shares one pool, and vanilla
  players *and older patch builds* are excluded (that also kills version-mismatch
  desyncs), and
- ensures `Koaloader.config.json` loads both modules.

To deploy: add `patch_ranked64.dll` to your repo at `Files/Matchmaking/`, paste
the function into the launcher, and call `setup_matchmaking(game_path)` in
`launch()` right before `open_file("steam://rungameid/1689620")`. Push to
GitHub; users get it on next launch.

## Definitive re-test (this is the only test that proves it)

The pass/fail signal is the vanilla case, not the patched-vs-patched case.

1. **Both patched, hooks confirmed** (both logs show `HOOKS INSTALLED`, same
   code): queue together → should match. Log shows `JOIN OK`.
2. **You patched, partner vanilla** (partner removes the DLL or runs vanilla):
   queue at the same time, repeatedly, for a few minutes.
   - **Expected now:** you never connect. If a vanilla lobby is ever evaluated,
     your log shows `JOIN BLOCKED: lobby issuer 256 != our code ...`.
   - This is the case that failed before; it must hold now.
3. **Play a full match** (both patched, same build) → no desync.

If step 2 ever connects you to a vanilla player **while the log shows hooks
installed and the SEARCH/JOIN lines firing**, send me `patch_ranked.log` — that
would mean a ranked-specific path bypasses the filter, and the join-guard log
will show exactly what happened so I can close it.

## Note on anti-cheat
Everything here rides in the same injected space your patch already uses
(`version.dll` + SmokeAPI). If a future game/EAC update ever blocks that
injection, both SmokeAPI and this module would stop loading together — the log
simply won't appear, which is your signal.
