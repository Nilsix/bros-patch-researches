# In-game matchmaking loader (dinput8.dll) — install & test

## Why the earlier attempt did nothing
The hook has to run inside the **game** process. The old setup loaded via
`version.dll`/Koaloader, but only `start_protected_game.exe` (the EAC launcher)
imports `version.dll` — so the module loaded into the *launcher*, never the game.
That's why no `patch_ranked.log` appeared and you still matched normally.

## The fix
`BLEACH_Rebirth_of_Souls.exe` statically imports **`dinput8.dll`**. So a
`dinput8.dll` in the game folder is loaded directly into the **game**. This new
`dinput8.dll` forwards all input to the real system dinput8 (input works exactly
as before) and installs the matchmaking hook where it belongs.

## Install (already done on your machine)
In the game folder (next to `BLEACH_Rebirth_of_Souls.exe`) you now have:
- `dinput8.dll`  ← the in-game loader
- `patch_ranked.txt`  ← your match code (currently `314159`)

Nothing else is needed — no Koaloader, no config. (You can ignore/delete the old
`patch_ranked64.dll` and `Koaloader.config.json`; they're no longer used.)

## STEP 1 — confirm it's actually in the game (do this first, alone)
1. Launch the game normally.
2. Open **`patch_ranked.log`** in the game folder. You want:
   ```
   ==== dinput8 proxy loaded INTO GAME (pid ####) ====
   match code 314159 loaded
   HOOKS INSTALLED (in game) -- pool code 314159, join-guard ON
   ```
   - If you see that, the hook is finally running in the game. 
   - If the log still doesn't appear, tell me (and note whether the game
     started normally). If the game refuses to start or kicks you, remove
     `dinput8.dll` to instantly revert — that would mean anti-cheat blocked the
     DLL and we'll change approach.
3. Start a ranked/free search and watch the log update live:
   `SEARCH: filtering issuer 256 -> 314159` appears each time you search.

## STEP 2 — the real segregation test (with your partner)
Same match code on both (`patch_ranked.txt` = `314159`):
- **Both patched** → should match; log shows `JOIN OK`.
- **You patched, partner vanilla** (partner has no `dinput8.dll`) → must NOT
  match. If a vanilla lobby is ever reached you'll see
  `JOIN BLOCKED: lobby issuer 256 != our code 314159`.
- **Play a full match** (both patched, same build) → no desync.

The pass signal is the vanilla case: you must be unable to connect to a
non-patched player.

## Rollback
Delete `dinput8.dll`. Everything returns to stock instantly.

## Rolling it out to everyone
Right now only your machine has `dinput8.dll`. For the community, install it via
the launcher (see `LAUNCHER_matchmaking_integration.py`): commit
`dinput8.dll` to the repo under `Files/Matchmaking/`, and have `launch()` copy it
in and write a version-derived match code on every launch. Then every player is
in the same pool automatically, and vanilla/older builds are excluded.
