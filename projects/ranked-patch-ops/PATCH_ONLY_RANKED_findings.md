# Patch-Only Ranked / Free Match — Feasibility Findings

**Question:** Can ranked/free match be made to automatically queue patched players only with other patched players (so vanilla ↔ patch never match and desync)?

**Verdict: Yes. It is feasible, and there is a clean way to do it that fits your existing injection setup.** Details, evidence, and the recommended method below.

---

## 1. How matchmaking actually works in this game

Ranked and Free Match are built on **Steam lobby matchmaking** (`ISteamMatchmaking`, interface `SteamMatchMaking009`). The flow is the standard Steam pattern:

- A player who hosts a session **creates a lobby and tags it** with a set of metadata keys (`SetLobbyData`).
- A player who is searching **builds a list-request with filters** (`AddRequestLobbyListNumericalFilter` / `...StringFilter`), then calls `RequestLobbyList`, gets back only lobbies that match **all** filters, and joins one (`JoinLobby`).

The whole thing is driven by a small set of lobby-data keys. I found the three generic dispatchers in the exe that read/write/filter them (in `NetworkLib\...\Matching.cpp`):

| Function | RVA | Steam call it makes |
|---|---|---|
| Get lobby data | `0x140A73920` | `GetLobbyData` (vtbl+0x98), `GetLobbyMemberData` (vtbl+0xC0) |
| **Set lobby data (host tags lobby)** | `0x140A73AD0` | `SetLobbyData` (vtbl+0xA0), `SetLobbyMemberData` (vtbl+0xC8) |
| **Add search filter (searcher)** | `0x140A73CB0` | `AddRequestLobbyListStringFilter` (vtbl+0x28), `AddRequestLobbyListNumericalFilter` (vtbl+0x30) |

The keys they operate on: `world`, `lobby`, `flag`, `issuer`, and indexed slots `i00–i08`, `b00–b01`, `m00–m01`.

## 2. What decides "who can match whom"

When a client searches (function at `~0x140A76E40`), it adds these filters right before `RequestLobbyList`:

- a dynamic list of `i / b / m` slot filters (mode/rules from the room config),
- **`world`** — numeric, **Equal** — value from the match request (`[req+8]`),
- **`issuer`** — numeric, **Equal** — value computed from the Steam branch (see below),
- a result-count cap (50).

The host side (function at `~0x140A75360`) tags its lobby with the **same** `world` and `issuer` values via `SetLobbyData`.

Steam returns a lobby only if it satisfies **every** filter (logical AND). So two players can only meet in the queue if their **`world` AND `issuer` values are identical**. These two integers are the entire "matchmaking pool" identity.

### `issuer` = your Steam beta branch
`issuer` is computed by the function at `0x140A785E0`. It calls `ISteamApps::GetCurrentBetaName` (verified: `ISteamApps` vtbl+0x78 = method index 15; the exe imports `STEAMAPPS_INTERFACE_VERSION008`), uppercases the branch name, and maps it to a bucket:

- branch starting `AQ_` → **8**
- no beta / public branch (empty name) → **0x100**
- any other branch name → **1**

It is **always set and always filtered** (never the "skip" value), so it is a permanent, symmetric gate.

### `world`
`world` is a 32-bit int from the match request. Its default is **-1**, which the code treats as "don't set / don't filter" (both the host-tag and the search-filter skip it when it's -1). So `world` is only a gate when the game gives it a real value.

## 3. Why vanilla ↔ patch desyncs today (this matches exactly what you observed)

Your patch changes **data files** (`CharaStatus.fsv`, `CommonParam.fsv`, etc.), not the game version. So a patched client and a vanilla client:

- run the **same `.exe`**, on the **same public Steam branch** → identical `issuer` (0x100),
- use the **same `world`**,
- therefore land in the **same matchmaking pool**, get matched, and then **desync during gameplay** because their data tables differ.

Critically, **the game does not checksum data files as part of matchmaking** — nothing in the lobby keys reflects file contents. That is precisely why cross-play connects and *then* falls apart instead of being blocked up front. Your room-match experience (two patched players fine, patch vs vanilla desync) is fully consistent with this.

## 4. The fix: give patched clients a unique matchmaking discriminator

Because matching requires `world` AND `issuer` to be **equal on both sides**, if patched clients use a value for one of these that vanilla clients will never use, patched players form their **own isolated pool** — automatically, in both directions:

- patched host tag = MAGIC, patched searcher filter = MAGIC → they find each other ✅
- vanilla searcher filters the normal value → never sees the patched lobby ✅
- patched searcher filters MAGIC → never sees a vanilla lobby ✅

This is exactly the "patch-only queue" you want, with no server and no changes to the queue UI.

`issuer` is the better lever than `world` because it is **always active** (no -1 skip), so it guarantees isolation in both directions regardless of what `world` happens to be.

### Recommended implementation (fits your existing setup)

You already inject code into the game: `version.dll` is **Koaloader** (a proxy-DLL loader, ships PolyHook), and `SmokeAPI64.dll` already hooks the Steam API. Add one small Koaloader-loaded module that hooks the **Steam matchmaking boundary** and rewrites only the `issuer` key:

1. Hook `ISteamMatchmaking::SetLobbyData` — when `key == "issuer"`, replace the value with a patch constant (e.g. the string form of a magic number tied to your patch version).
2. Hook `ISteamMatchmaking::AddRequestLobbyListNumericalFilter` — when `key == "issuer"`, replace the compared value with the **same** constant.

That is the whole change. It is:

- **Symmetric** (both host and searcher rewritten) → true two-way isolation.
- **Matchmaking-only** — it touches nothing but the `issuer` lobby key. (Do **not** just patch the `0x140A785E0` function directly: its result is also used at `0x140857A58` to pick an online-mode/UI configuration, so overwriting it wholesale has side effects. Rewriting at the Steam-API boundary avoids that.)
- **Version-lockable** — if you derive the magic from the patch version, different patch versions also won't match each other, which prevents patch-vs-patch desyncs when you push an update.
- **Update-resilient** — it depends on the stable Steam interface, not on internal game offsets.

### Alternatives (ranked by robustness)

- **B — `GetCurrentBetaName` hook (least effort):** Hook `ISteamApps::GetCurrentBetaName` to return a fixed string like `"PATCH"`. That maps patched clients to `issuer` bucket **1**, distinct from the public **0x100**, so they segregate. Caveat: it relies on real players being on the public branch (anyone genuinely on a non-public branch would also land in bucket 1), and it also flips the `0x140857A58` UI-mode path into its "other branch" branch — usually harmless but worth testing.
- **C — force `world` (matchmaking-only, no UI side effects):** Rewrite the `world` value on both host and search the same way. Clean, but because vanilla's `world` may be -1 ("no filter"), a vanilla *searcher* could still list a patched host. Only use `world` if you confirm ranked assigns it a real (non -1) value; otherwise it's a one-way gate. `issuer` doesn't have this problem.
- **D — static `.exe` patch:** Possible since the code section is not encrypted at rest, but EasyAntiCheat (EOS) is present and internal call sites are shared with the UI path, so this is the most fragile option. Not recommended.

## 5. Operational notes / caveats

- **Everyone must run the same segregation build** (same magic value) for it to work — it's a client-side convention, so all patch users need the module. Baking the value into the patch version handles this and self-heals cross-version mismatches.
- **EasyAntiCheat:** EAC-EOS is installed (`EasyAntiCheat/`, `start_protected_game.exe`), but your setup already runs with it effectively neutralized (modified `start_protected_game.exe`, working DLL injection, modded data in online play). The hook lives in the same injected space you already use; just keep launching the way you do now. If you ever re-enable EAC, both hooking and static patching would be at risk.
- **Scope:** This governs the automated ranked/free **queue** (the list-based search). Direct invites / room codes are a separate manual path and are unaffected — which is fine and usually desirable.
- **No data-file gate exists to exploit** — the only matchmaking identity is `world` + `issuer`, so rewriting `issuer` is the whole job. There isn't a cleaner built-in "version" field hiding elsewhere.

## 6. Suggested next step

If you want, I can write the actual hook module source (C++ against PolyHook, structured to be dropped into your Koaloader config) that rewrites `issuer` on both `SetLobbyData` and `AddRequestLobbyListNumericalFilter`, with the magic derived from a patch-version string. That would turn this from "feasible" into a drop-in.

---

### Reference — verified addresses (game build in this folder)

- Set lobby data (host tag): `0x140A73AD0`
- Add search filter: `0x140A73CB0`
- Get lobby data: `0x140A73920`
- Search-request builder (adds world+issuer+count filters): `~0x140A76E40`
- Host-tag builder (sets world/lobby/flag/issuer): `~0x140A75360`
- `issuer` = branch-bucket function: `0x140A785E0` (calls `GetCurrentBetaName`)
- `issuer` also consumed by UI-mode select: `0x140857A58` (reason not to blanket-patch the function)
- Keys: `world`=type13, `lobby`=14, `flag`=15, `issuer`=16; slots `i00–08`, `b00–01`, `m00–01`
- Steam: `SteamMatchMaking009`, `STEAMAPPS_INTERFACE_VERSION008`
