# Trade Post — session export

Written 2026-09-22, to be merged into another working conversation.
Read this alongside `HANDOFF.md`, which is **older than this document and wrong
in places**; section 10 lists exactly what to correct in it.

Everything here was verified in the running game unless explicitly marked
untested.

---

## 1. Status: the core mechanic works

Handoff section 4 ("test the Survival Trade Post") is **done**. The post
produces goods, a truck loads them, and the player's money goes down. Observed
in `rml-runtime.log`:

```
trade_post  adopted building 00000172DAF57F60 with 4 tradeable slots
trade_post  00000172DAF57F60 sold 1.32 t for  73 RUB so far
trade_post  00000172DAF57F60 sold 5.05 t for 210 RUB so far
```

Confirmed by the player watching their balance drop while collecting material.
Both the construction post and the consumer-goods post were tested this way.

---

## 2. What exists now

### Three buildings, all TYPE_FACTORY, all worker-free

| Item id | Folder | Sells | Donor mesh |
|---|---|---|---|
| 9000001 | `mod/buildings/trade_post` | gravel, bricks, boards, steel, cement | `zoll_sahy` (customs house) |
| 9000030 | `mod/buildings/goods_post` | food, alcohol, clothes, eletronics | `zoll_sahy`, `zoll_siatre` icon |
| 9000031 | `mod/buildings/junk_post` | gravel, bricks, boards, steel, cement | `waste_steelrecycling` (scrap yard) |

All three have no worker requirement line, draw `eletric 0.02` per second, and
have no consumption input. They run on power alone.

### The plugin

`mod/plugins/trade_post/trade_post.cpp` builds `trade_post.dll`, version 1.0.
It hooks `FactoryTick` and charges money whenever a watched storage's contents
go down, because only a loading vehicle does that.

### Config: `mod/plugins/trade_post/trade_post.ini`

Installed beside the DLL at `rml\plugins\trade_post.ini`.

```ini
[general]
price_multiplier = 1.35     ; multiple of normal market price
currency         = RUB      ; RUB or USD
usd_rate         = 1.0      ; roubles per dollar, used only when currency = USD

[price]                     ; optional per-resource overrides of the global
; eletronics = 2.00

[production]                ; tonnes/day; applied at INSTALL time, not runtime
gravel = 0.60 ... eletronics = 0.05
```

`[general]` and `[price]` are read by the plugin at game start.
`[production]` is stamped into each `building.ini` by `build.ps1 -Install`,
because a production rate lives in `building.ini` and only the game's own parser
reads that file.

---

## 3. THE BIG ONE: building.ini has no comment syntax

**This cost roughly a dozen test launches. Do not rediscover it.**

The parser splits on whitespace and treats **any token beginning with a dollar
sign as a directive, wherever in the file it appears.** There is no line
comment. A semicolon does nothing.

An early `building.ini` carried explanatory semicolon comments. Two of them
mentioned directives by name, with a space before the dollar sign — so the game
parsed `PRODUCTION plus` and `PRODUCTION lacks` as real directives.
`ResourceGet("plus")` returned null and the build menu dereferenced it the
instant the item was moused over. The building loaded fine; only **hovering**
touched the bad pointer.

The game logged it plainly in `SovietRepublic/log.html`, from the very first
run:

```
ResourceGet - not found plus
ResourceGet - not found lacks
```

**Recognise this symptom:** `ResourceGet - not found <an English word>` means
the parser is reading prose. Search the ini for that word.

### What is actually safe

Vanilla does annotate — 34 base-game inis use `//`, 74 use `--` — but always
with the marker **glued directly to the dollar sign**, never separated by a
space:

```
//$WORKERS_NEEDED 13                      disabled directive; 152 such lines in vanilla
--$CONSUMPTION_PER_SECOND eletric 10.55   same thing
// Live connections                       prose, contains no directive token
```

Across all 488 base-game building inis there is **not one** comment line with a
space before a dollar sign. Ours had a space. That is the whole difference.

So prose comments are fine as long as no whitespace-delimited word starts with a
dollar sign. Write `PRODUCTION`, not the directive form. All three shipped
buildings carry `//` comments written to that rule and verified clean.

### Corollary trap, hit once

Donor files contain **disabled** lines that look live if read carelessly.
`waste_steelrecycling` ships its electricity draw disabled with a `--` prefix.
The junkyard post inherited it, so with workers also removed it would have
produced goods needing neither staff nor power. Caught before shipping; power
re-enabled at `0.02`.

---

## 4. Other verified facts about this game's data format

- **A RESOURCE_VISUALIZATION header is always followed by its own block**
  (`positon` / `rotation` / `scale` / `numstepx` / `numstept`). 654 of 654
  occurrences across vanilla plus 310 Workshop items. A bare header with no
  block is unlike anything in the corpus. Removing a bare one did **not** fix
  our crash — the comments did — but do not leave one.
- **`eletric` and `eletronics`** are the game's own spellings, both missing a
  letter. `electric` and `electronics` do not exist. A mismatch fails silently.
- **Directive order does not matter.** `brick_factory` declares its type near
  the top of the file; `zoll_sahy` declares its type near the bottom. Both work.
  An earlier theory that order was load-bearing was **falsified by test**.
- **A TYPE_FACTORY produces with no workers at all**, at the full configured
  rate, as soon as it has power. Verified in game. Both an absent
  `WORKERS_NEEDED` and an explicit `0` worked; absence is used because that is
  what vanilla does (farms, wind turbines, the water well) and **no base-game
  file sets it to zero**.
- Worker-free *whole-rate* production is otherwise a property of certain types.
  `water_well_small` is `TYPE_MINE_WATER` and its own file carries the comment
  `production for water well is not per worker, but whole`. Mine types are
  **not usable here**: they need the resource underneath (groundwater, a
  deposit), and they never reach `FactoryTick`, so billing would stop.
- Every Workshop building item needs `previewimage.png` at the item root and an
  owner id in `workshopconfig.ini` — 55 of 55 installed items have both. Adding
  them did not fix our crash, but they are the convention.
- A dev item under `media_soviet\workshop_wip\<numeric id>` must be **ticked in
  RML's Development list** or it is never loaded. RML logs
  `Development inventory: local=N enabled=M`. If `enabled=0`, nothing you change
  in that building is being tested. This wasted several launches.

---

## 5. Method: what actually found the bug

Reasoning from corpus statistics ("0 of 345 vanilla factories do X") produced
**four wrong diagnoses in a row**, one of them exactly inverted. What worked:

1. **Deploy an unmodified vanilla building through the identical pipeline** as a
   control. Ours (`brick_factory`) worked, which instantly exonerated
   `workshopconfig.ini`, `previewimage.png`, the icon convention, renderconfig
   style and RML's dev-item handling, and proved the fault was in our content.
2. **Bisect with variants, several per launch.** Half-and-half splits (our
   economy on their shell, their economy on our shell) narrowed it fastest.
3. **Build *up* from something that works**, not down from something broken.
   Removing things from the broken file never converged; adding one trait at a
   time to a working file did.
4. **State the prediction before the test.** A positive control that was
   supposed to crash and didn't is what killed a plausible-looking theory.

Do this before theorising. It is much cheaper than it looks.

### Reading a crash

`SOVIET64.exe` imports `SetUnhandledExceptionFilter` and swallows its own
exceptions, so **Windows WER never writes a minidump** — enabling LocalDumps for
it produces nothing. RML records only the exit code (`0xC0000005`) plus a
support zip of logs in `rml\crash-archives\`. The game's own
`SovietRepublic\log.html` is the best evidence available and is written up to
the moment of the crash. **Read it first.**

`tools/dump.py` was written to parse a minidump without a debugger (none is
installed) and is validated against a real dump — but it is useless for this
game for the reason above. Keep it for other processes.

---

## 6. Plugin internals

```
kGoods[] = gravel, bricks, boards, steel, cement,
           food, alcohol, clothes, eletronics        (9 resources)
MIN_MATCH = 3      a building is a trade post if it exports 3 or more of those
```

Identifying a post by its **exported resource set**, rather than by name or
mesh, is what lets one plugin serve all three buildings. Verified unique: no
vanilla or Workshop factory exports three or more of the nine. Shops cannot
match either — the hook only fires on the factory arm of the dispatcher.

**If you add a product to any post, add it to `kGoods[]` or it will not be
billed** — silently, with no error.

### Config loading bypasses the documented trap

`HANDOFF.md` section 5 says plugin ini files are never read: `TsmHost::configInt`
resolves against `TsmHost::baseDir`, which under RML's compatibility host is
neither `rml\plugins` nor the Workshop item folder. **Still true — do not use
the host config API.**

The plugin now reads its own ini with plain file I/O, locating it via
`GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, ...)` plus
`GetModuleFileNameA` on its own code address, then reading `trade_post.ini` from
that directory. That resolves to `rml\plugins\trade_post.ini` regardless of host
configuration. It logs which file it actually read.

### Addresses (SOVIET64.exe 1.1.1.9, sha256 296644a9f2...6841b8)

All re-verified this session against the installed binary as exact `.pdata`
function starts:

```
0x139A70  building tick dispatcher (20964 b)
0x1D1E80  FactoryTick(context, building)   <- what trade_post hooks
0x1854E0  CustomsHouseTick (26 b)
0x2AA830  ResourceGet (735 b)
0x424430  real "how much can this building supply" (3640 b)
0x68B330  goods flow, 55575 b, abandoned
game = exe + 0x9D4F10     +0x580 USD (double), +0x588 RUB (double)
resource+0x64  price shown and charged
```

**Known conflict:** `Enhanced Storage Management` (Workshop 3793101070,
priority 9000) around-hooks `0x139A70`, the dispatcher that calls our
`0x1D1E80`, and also `0x420350` and `0x422C30`. `trade_post` is priority 9800 so
it loads after. No problem observed, but it is the first thing to disable if
storage behaviour ever looks wrong.

---

## 7. Build and deploy

```powershell
.\build.ps1                            # build all plugins
.\build.ps1 -Install -Only trade_post  # install plugin + all buildings
.\build.ps1 -Log                       # this mod's lines out of RML's log
```

Three fixes made to `build.ps1` this session:

- **`-Log` was broken for this work.** It grepped for `customs_` and could never
  match `trade_post`. It now derives the filter from the folder names under
  `mod\plugins`, so new plugins are picked up automatically.
- **`-Install` could destroy the deployed item.** RML holds `previewimage.png`
  open while its launcher runs; `Remove-Item -Recurse` deletes depth-first, so
  it wiped the object subfolder and *then* failed on the locked file, leaving a
  half-installed item the game still enumerated. It now refuses to run while
  `RepublicModLoader` or `SOVIET64` is up (naming the PIDs), and stages into
  `<id>.new` before swapping. **Close RML before installing.**
- A player-edited `trade_post.ini` is never clobbered by a reinstall.

Toolchain note: this machine's VS 2026 BuildTools had the C++ workload selected
but no payloads (no `cl.exe`, no Windows SDK). Repaired by running the VS
installer elevated with `--add Microsoft.VisualStudio.Workload.VCTools
--includeRecommended --force`. Now MSVC 14.51.36231 and SDK 10.0.26100.0.

---

## 8. Design decisions already settled by the user

- Trade posts are **goods for money** — no input material. Consumption was
  removed. *Caveat: no vanilla factory produces without a consumption line — 0
  of 345 — so this is unprecedented, and it has not been confirmed to still
  produce since the change. Watch the first run.*
- `cement` restored as the fifth construction product.
- Electronics stay in the goods post despite gating: the unlock for `eletronics`
  sits behind research `electronics_1`, year 1934, which locks the **whole
  building** until then. Accepted — the scenario starts after 1960.
- The junkyard exists so the post-apocalyptic scenario has a scrap-yard look,
  distinct from the customs-house "Importing House" framing for the normal game.

---

## 9. Outstanding work

1. **Rename for the general-game framing.** The user wants these called
   **Importing House** outside the apocalypse scenario. Proposed: "Importing
   House — Construction Materials" and "— Consumer Goods", with the junkyard
   keeping a survival name. Not started.
2. **`tools/pack_mod.py`** — a distributable package. `tools/package.py` zips the
   *repo* for machine-to-machine handoff, which is a different thing. Needs the
   buildings, the DLL, the config and a README; no sources, no vendored SDK.
   Not started.
3. **Verify production still runs with no consumption line** (see section 8).
4. **Optional: runtime production rates.** `[production]` is install-time today.
   Making it runtime means the plugin restocking storages itself instead of the
   engine, which needs a reliable game-time delta — real seconds break when the
   player changes game speed. The tick accumulator at `building+0xFC0` is the
   likely route. Real reverse-engineering work; only worth it if players must
   retune without reinstalling.
5. Housekeeping: `build.ps1.bak` and `tools/__pycache__/` can be deleted.

---

## 10. Corrections needed in HANDOFF.md

It is stale. Apply these:

- **Section 3 table** — "Survival Trade Post | Building + plugin, built and
  installed, **untested**" should become tested and working, plus two more
  buildings.
- **Section 4 "The next step"** — the whole section is done. Its three predicted
  first-contact problems were all wrong: a factory with no consumption was never
  the crash; the two open-transport storages did **not** merge; `+0x64` **is**
  the right price column for a factory.
- **Section 5 traps** — add the comment-parsing rule from section 3 above. It
  belongs next to `vcvars64.bat` and `TsmHost::log`: same character, silent,
  format-level, and it cost more time than both combined. Also add that RML
  holds `previewimage.png` open, and that dev items must be enabled in RML.
- **Section 5 "Plugin .ini files are never read"** — still true of `configInt`,
  but add that the workaround is to locate the file from the DLL's own module
  path (section 6 above), so plugins *can* have config after all.
- **Section 1.4** — the vendored SDK is **not** excluded from the package; it was
  present in the zip. The `git clone` step is unnecessary.
- **Section 1.5** — the hardcoded Steam paths happened to be correct on this
  machine; no edit was needed.
