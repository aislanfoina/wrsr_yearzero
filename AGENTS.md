# AGENTS.md - Republic in Ruins (context for AI agents)

Read this before changing anything. It condenses the working knowledge of the sessions that built
this mod: what exists, how it is built and tested, the engine facts it relies on, the dead ends and
the traps. `README.md` is the player-facing page; `docs/development-notes.md` is the long handoff
with the full test history; `docs/feasibility.html` the original analysis; `docs/contamination-design.md`,
`docs/customs-house-notes.md`, `docs/trade-post-notes.md`, `docs/trade-post-handoff.md` the details.

---

## 1. What this is

A post-apocalyptic survival overhaul for **Workers & Resources: Soviet Republic 1.1.1.9**
(`SOVIET64.exe`, image base 0x140000000; every address below is an RVA valid for this build only).
Mechanics: contamination instead of crime, survivors instead of bought immigrants (mercenaries paid
in goods), survival trade posts as the scarce border, vehicle blueprints learnt at the scrapyard,
salvageable ruins; art: 8 building kits (23 buildings) and 19 welded-up vehicles; words: the game's
English text re-themed. It was built around **Korea Year Zero**, a post-strike start converted from
BATON's North Korea workshop map (3753525456) - the converter is here, the map is **not published**
(it is BATON's work, on World Maps DLC terrain).

Runs on **Republic Mod Loader (RML)**, Workshop item 3787969749, which hosts TesmioLoader-API
plugins (API 3/4). Four plugins (C++, MSVC x64, /MT): `fallout`, `scrap_center`, `survivors`,
`trade_post`.

Status (2026-10-01): everything loads; Korea Year Zero has run in short sessions (loads in ~10 s,
autosave OK, contamination ticking). Not on the Steam Workshop yet. Several pieces have never been
seen working in the engine - see section 11.

## 2. Ground rules

- **Branches:** commit only to `unstable`. `dev` takes pull requests from `unstable` (two
  approvals); `main` takes pull requests from `dev` (code-owner approval, @aislanfoina). The owner
  may merge with admin bypass. Never push to `dev`/`main` directly.
- **Origin of this repo:** exported from a private mixed workspace (`wrsr`, which also holds the
  Space Race mod) by `tools/export_yearzero.py`; the export replaces everything except `.git`. If you
  work here directly, say so in the commit so the workspace can be synced.
- **Commits** are authored as the owner, with a `Co-Authored-By:` line for the AI.
- **Never** enter Steam or other credentials, never change the owner's RML configuration without
  asking, never publish to the Workshop without an explicit go, never publish the converted map.
- `.gitattributes` is `* -text`: ini/script files are CRLF and models binary; keep them byte-exact.

## 3. Repository map

```
mod/plugins/fallout/        contamination (fallout.cpp) + crashlog.cpp (vectored exception logger: module+offset of hard faults)
mod/plugins/scrap_center/   blueprint learnt when a scrapyard disassembles a vehicle
mod/plugins/survivors/      survivors settle, immigrant purchase blocked, distress trickle, mercenaries paid in goods
mod/plugins/trade_post/     trade posts bill what trucks load; trade_post.ini (prices, multiplier, currency, rates)
mod/packages/republic_in_ruins/   the plugins' Workshop item (9000090)
mod/buildings/<kit>/        madmax_kit (12 wasteland pieces), fallout_kit (DTF station, radiology board, recovery
                            center), survivors_kit (mercenary camp, distress beacon, survivor shelter), trade_post,
                            goods_post, junk_post, scrap_center, scrap_dock (all generated)
mod/vehicles/<key>/         19 vehicles (vanilla meshes + welded add-ons + skins)
mod/text/survivors_text/    TEXT item: media_soviet.zip with a re-themed sovietEnglish.btf; mod/text/vfs/ same file for TesmioLoader's VFS
tools/                      generators (Blender + Python), map converter, Workshop packer, RE helpers
tools/dev/                  helpers that drive and read a running game
data/yearzero/              the converter's prepared inputs (donor building records, road points, model bounds)
docs/                       design notes, feasibility study, development notes (test history), images/
vendor/TesmioLoader/        API headers (GPL-3.0)
```

## 4. Build, install, run

- **Build:** `.\build.ps1` compiles every `mod/plugins/*` (finds MSVC and the SDK itself, sets
  INCLUDE/LIB directly - do NOT use `vcvars64.bat`, it breaks when `%ProgramFiles(x86)%` is missing,
  i.e. any shell started from Git Bash). `-Install` (needs Python 3): runs
  `tools/stamp_production.py` (trade posts' production rates from `trade_post.ini` into their
  building.ini), `tools/yearzero_workshop.py` (packs the four Workshop items into `build/workshop`),
  then deploys them into `<game>\media_soviet\workshop_wip\<id>`, adding the DLLs, inis and
  `rml.json` of every plugin whose `package.txt` says `republic_in_ruins`. `-Game`/`WRSR_GAME` set
  the game folder; tools also read `WRSR_WORKSHOP` (Steam's `workshop\content\784150`).
- **Workshop items (packed):** plugins 9000090 (SCRIPT), buildings 9000050 (BUILDING: all 23, one
  shared `material/` - the kits' `tp_*` textures are identical), vehicles 9000051 (VEHICLE: all 19),
  words 9000005 (TEXT). Workshop types are registered as `<item id>/<object>`, so packing changed
  every ident; older per-kit dev items (9000001-9000042) may still sit in `workshop_wip` from earlier
  installs and then duplicate everything in the build menus.
- **RML:** development items default to off (enable them and the plugins in RML's UI;
  `Development inventory: local=N enabled=M` in the log). RML holds `previewimage.png` open - close
  it before installing. Do not install DLLs into RML's own `rml\plugins` (one switch for all, wiped
  on RML updates).
- **Launching for a test:** start RML via Explorer (from a sandboxed shell the game says "STEAM
  ERROR"): `Start-Process explorer.exe -ArgumentList '"<RML>\RepublicModLoader.exe"'`, then
  `python tools/dev/rml_launch.py`. A Steam "Refresh Sign In" prompt destroys the game window while
  the process lives on; only the owner can sign in.
- **Logs:** RML `rml\logs\rml-runtime.log` (lines tagged `[Tesmio:<plugin id>]`, `crashlog
  exception` lines, `WRSR process exit ... code=`); the game's `log.html` (`IO_Building_Read
  BuildingType is NULL - <ident>` = a map references a type that is not loaded).
- **Game settings the mechanics need:** Crime & justice: Enabled (contamination), Waste management:
  Waste + Demolition (salvage).

## 5. Architecture

| Plugin | Hook(s) | What it does |
|---|---|---|
| `fallout` | TickAllBuildings `0x139A70` (post; prologue `48 8B C4 55 41 54 41 55 41 56 41 57 48 8D A8 78 FA FF FF`, 19 bytes) | every 40 ticks: three crater zones decay (half-life; cleanup factor = live `mm_*` ruins in the zone / initial); waste stored within 500 m of a crater radiates; writes the radiation grid; doses citizens in buildings inside the field via the crime status; above 0.85 erodes health; 15 % of newcomers at a customs house arrive with a 0.35-0.75 dose. Zone coordinates = Korea Year Zero's strike points (top of fallout.cpp) |
| `scrap_center` | ScrapyardTick `0x14B920` (post) | sets the blueprint flag (vehicle type +0x9C88 = 1) of the type being disassembled (building +0x11C8); works for every scrapyard, ships included. Airplanes cannot be scrapped by the engine |
| `survivors` | CustomsHouseTick `0x1854E0` (post), SpawnPerson `0x823330` (pre), PersonBoards `0x831120` (wrap), StorageTick `0x1CADC0` (post) | each tourist returning home (building+0x1230 delta) spawns a citizen instead (one in five with higher education); immigrant purchase blocked (ctx+0x13690/0x13698 = 0); 2 newcomers per 120-unit cycle at borders with the distress call (tourist visa) researched, x2 during the broadcast (ad campaign); foreign workers paid from a Mercenary Camp (food 0.06, meat 0.03, clothes 0.02, alcohol 0.02 per arrival and departure; camp found by storage fingerprint), no camp = none |
| `trade_post` | FactoryTick `0x1D1E80` (post; free, unclaimed) | a trade post is a worker-free `$TYPE_FACTORY` producing goods from nothing at configured rates; when its storage drops (only a loading vehicle does that) it charges `resource+0x64` x multiplier; adoption by fingerprint (exports 3+ of the nine billed goods); `trade_post.ini` read from the DLL's folder |

The **text overlay** (`tools/survivors_text.py`, merging `tools/fallout_text.py`) rewrites ~170
English strings in the game's `sovietEnglish.btf` (`tools/btf.py`: big-endian format, round-trips all
7,906 strings; `tools/en.json` is the full text, a searchable index of game features).

**Korea Year Zero converter** (`tools/yearzero.py`, formats in `tools/mapio.py`): copies BATON's map,
repaints the mask with scorch/dust rings around three strikes (capital -3709,-3717; east port
3940,758; north gate town 2400,-5207), thins/retypes trees to dry species, replaces huts inside the
inner radii in place by `mm_*` ruins (no index shifts), appends a start kit cloned from donor records
(`data/yearzero/donors`, from `tools/donors.py`), writes `pollution.bin`, and a scenario `yearzero`
(`start.txt`: no immigrant/vehicle purchase, blueprints for the war rig and raider and the rest
only from scrapping, border prices x4, 120k RUB / 4k USD, three wrecks in the motor pool
(`VEHICLES_IN_DEPOT`), objectives, a reunification watch: average
`fStatusSoviet` > 0.75 wins) auto-started by the map's `stats.ini` (`$ScenarioAutoStart yearzero
yearzero`). Output: `workshop_wip/9000007` (map) and `9000008` (scenario), also installed to
`media_soviet/scenarios/yearzero`. Run it after `build.ps1 -Install` (it resolves our idents from the
installed items) and `tools/wasteland_tiles.py`.

## 6. Engine facts used (1.1.1.9)

```
game object = exe+0x9D4F10 (global)
  +0x580 USD balance (double)  +0x588 RUB balance (double)
  +0xC2C8 the `workers` resource (wage price +0x5C RUB / +0x58 USD)
  +0x11767/8 visa researched, +0x11769/A ad campaign active
  +0x120A8 radiation/pollution grid: 100x100 cells of 12 bytes {radioactivity, pollution, tag}, x-major (index xi*h+zi), 200 m cells, decays 0.005 per update
  +0x126A8 persons vector
  +0x13690/+0x13698 immigrant purchase allowed RUB/USD, +0x1369C price multiplier
building  +0x318 type descriptor (ident "<item>/<object>" at +0; BUILDINGTYPE at +0x360)
          +0x320 C3D_NODE (position via C3DDLL64 C3D_NODE::GetPosition)
          +0x970 std::vector<Storage> stride 0xE0 (storage +0/+8 slot vector of {resource*, float content, float limit};
                 +0x8C capacity, +0x90 transport class)
          +0x9EC border a customs house faces  +0xFC0 tick accumulator  +0x1230 tourists returned this cycle
          +0x11B0 pollution  +0x11B4 radioactivity (living buildings, sampled from the grid)
          +0xC70/+0xC78 vector<Vehicle*> at this building   +0x11C8 VehicleTypes* being scrapped
person    +0x40 building it is in now (never home)   +0x58 customs house it immigrated through (NOT its location)
          +0x80 workplace  +0xA8 education  +0xD4 age  +0xD8.. ten status floats: +0xE0 health, +0x10C crime (= dose)
          +0x5A0 C3D_NODE  +0x71C tourist flag  +0x748 foreign-worker nationality (1 soviet, 2 western)
resource  +0x00 32-byte name  +0x58 live price  +0x5C = x0.75  +0x60 = +0x58 x 1.105  +0x64 SHOWN AND CHARGED
VehicleTypes  stride 0x9F08 (0x1FEFF0 = base + i*0x9F08): +0x200 ident  +0x294 nVehicleType
          +0x85BC/+0x85C0 cost USD/RUB  +0x8600 resource type  +0x8604 capacity  +0x9C88 bBlueprintPurchased
BUILDINGTYPE_FACTORY 6, CUSTOMHOUSE 20, SCRAPYARD 109
0x139A70 per-building tick dispatcher (arms: factory 0x13DD69 -> 0x1D1E80, customs 0x13E2FA -> 0x1854E0, scrapyard 0x13E1BA)
0x185100 tourists per batch (NOT immigration)   0x1561C0 construction supply planner (customs short-circuits to 250.0)
0x424430 how much a building can supply          0x2AA830 ResourceGet(name)
0x3DED90 remove a vehicle   0x1AEDA0 scrap credit   0x1F0BE0 IO_Building_Read   0x1EDC40 Building::Write
0x11D800 LoadBuildingType (sprintf "%llu/%s" for workshop types)
```

Map/save format (details in `docs/development-notes.md`, `tools/mapio.py`): folder format version 124;
`buildings.bin` = per type name[0x40] + n fragments of 0x46 bytes (pos, rotation step of 128, world
AABB); `buildings_game.bin` = records with a 0x548 header (ident, city, pos, rotation, fragment index)
and a tail whose layout depends on `$TYPE`; `trees.bin`; mask channels R,G,B = tiles 2,3,4; pixel
mapping col = (x+10000)/20000*2047 without flips.

## 7. Content pipeline

- `tools/nmf.py` reads/writes `.nmf` and round-trips every vanilla file byte for byte. Conventions:
  Blender -> game is a -90 deg X rotation (game Y up, Z forward = road side); counter-clockwise is the
  front face; UV `v = 1 - v_blender`; per-face plane normal `(p2-p0)x(p1-p0)`; u16 indices (<= 65535
  vertices per node); a model's material list must match its `.mtl` **by name and order**.
- `tools/mmkit.py` is the shared Blender toolbox (primitives, composites, export, previews);
  `tools/build_madmax.py` runs textures -> vehicle skins -> wasteland kit -> vehicles -> previews
  (`MM_ONLY=a,b` builds a subset). Kits: `tradepost_scene.py`, `survivors_scene.py`,
  `fallout_scene.py`, `scrap_center_scene.py`, `scrap_dock_scene.py` (commands in README). The goods
  post and junkyard post reuse the trade post's and the Scrap Center's models.
- Vehicles: vanilla mesh + add-on nodes; vanilla LODs/spec/normal maps referenced by media path;
  paint variants through the game's own `material_N.mtl` + `preview_N.dds`; `vehicle_skins.py`
  paints skins from the UV islands; `keep_skill` keeps police/prison-bus skills for the Geiger patrol
  and the quarantine bus.
- Wasteland pieces are `$TYPE_MONUMENT` with `$COST_RESOURCE_AUTO wall_concrete / wall_steel`, so
  demolishing them yields construction waste and scrap.
- README pictures: `tools/yearzero_readme_images.py` (Blender scenes in `yearzero_readme_scene.py`,
  helpers in `readme_scene.py`); Workshop pages and previews: `tools/yearzero_workshop.py`.

## 8. Saves and compatibility

- Workshop types are `<item id>/<object>` inside maps, saves and scripts. A map referencing a type
  that is not loaded dies with `BuildingType is NULL`. The map must be regenerated whenever item ids
  change (packing, publishing).
- Cloned map records: the donor must have the target's `$TYPE` and **no external references** (header
  words +0x408/+0x40C/+0x414 must be 0; one donor with a +0x880 list crashed the autosave in
  Building::Write at SOVIET64+0x1F001B); trim a trailing fragment-less `temp` record from donor blobs.
- Lessons from the sister mod (Space Race): a save that holds a good the game no longer knows loads,
  but the save writer crashes on that slot.

## 9. Testing

- Offline: map files are validated by re-reading with `tools/mapio.py` (records split and match their
  fragments, tree types exist in `treetypes.ini`); VM calls checked against
  `media_soviet/scripts/SOVIETInstructions.txt`; `tools/rehelp.py`/`pe.py`/`customs_sites.py` for
  disassembly (capstone).
- In game (Windows, 5120x1440 primary monitor, physical pixels): `tools/dev/gdrive.py
  shot|crop|click|move|key|type|hold` (camera keys need scan codes - `hold()` uses SendInput with
  KEYEVENTF_SCANCODE). Main menu: Custom Game (1960,723), map pages ">>" (2757,1294), Load Game
  (1960,777), confirm (3117,1300); in game: settings icon (40,167) -> save-as (207,293) -> "Create
  new save" (3000,965) -> confirm (2700,733); load (287,293). ESC opens nothing. Autosaves overwrite
  their slots within minutes. A DirectX window cannot be captured with GDI on a locked desktop.
- Memory: `tools/dev/memprobe.py`, `memscan.py` (read-only), `recsizes.py` (record sizes per type).

## 10. Traps and dead ends

1. The game shows **every model mirrored** left-right versus Blender. Lettering must be built
   mirrored (`mmkit.Builder.text` and `tradepost_scene.text` do since 2026-09-30; the kits were
   regenerated). README renders are flipped to match.
2. `building.ini` has **no comment syntax**: any `$` token is a directive anywhere (a comment
   mentioning `$PRODUCTION` crashed a session). Symptom: `ResourceGet - not found <word>`.
3. Plugin inis: read them from the DLL's folder (module path); RML's `configInt` resolves elsewhere
   and only code defaults apply.
4. `TsmHost::log` is not printf: width specifiers break argument consumption - format into a buffer.
5. Hooks shared with other plugins: present the live bytes when a target is already patched so the
   loader chains; RML chains legacy inline hooks (`[HOOK CHAINED]`). Enhanced Storage Management,
   ForceNodes and ParallelUtilities also hook 0x139A70.
6. Batch files need CRLF; the Bash tool mangles backslashes in heredocs - write scripts to files.
7. **Customs-house purchase tracking is a dead end**: the border bills continuously per unit, there
   is no purchase event (hooking 0x68B330, price drift, base price +0x78 and storage flow all failed;
   `docs/customs-house-notes.md`). That is why the trade post exists.
8. `mod/plugins/customs_*` were retired for breaking construction supply or border sales; don't
   revive them.

## 11. Status and open items

Verified in game: the trade post mechanic (a worker-free factory restocks on power, a truck loads,
money is billed); Korea Year Zero loads, runs and autosaves with all plugins; the contamination
plugin ticks with all ruins counted; hook chaining with other mods.

Not verified: survivors settling and mercenaries (no log lines checked yet); the Scrap Center
granting a blueprint; contamination thresholds (0.33/0.66/0.85 are guesses); the scenario VM reading
`Person` fields; the packed four-item layout; the mirrored signs; the TEXT item honoured from
`workshop_wip`.

**Known bug:** `fallout.cpp` uses `PER_BUILDING 0x58` as "the building the person is in", but
person+0x58 is the customs house they immigrated through; the current building is **+0x40**
(verified 2026-09-29 by reading the running game). Contamination doses are therefore applied by the
wrong building until this is fixed and retested.

Next steps: install the packed items, remove the old per-kit dev items, rebuild the map, check the
signs and the mechanics above in game; then Workshop: create the four items in the game (main menu ->
Workshop -> Your items (WIP) -> green +; the form wants a preview PNG under 1 MB, a name and a UTF-8
TXT description; creating gives Steam ids and `workshop_wip/<id>` folders), put the ids into
`tools/yearzero_workshop.py` `ITEMS`, `build.ps1 -Install`, upload each from its Edit item page as
**Unpublished** (`$VISIBILITY 0`: the game's values are 0 unpublished, 1 friends only, **2 public** -
not Steam's enum), set Required Items (buildings, vehicles, words, RML) on the plugins page, go
public. The upload is the page's green check ("Save changes"); there is no other upload button.
Alternative without the game: `python tools/workshop_upload.py republic_in_ruins create` creates
the items that still have local ids (private, with the game's type tag: Script / Building / Vehicle /
Text modification) and prints their ids; then `... content visibility` and `... required` (see the
tool's docstring and the Space Race AGENTS.md). It talks to the signed-in Steam client and must run
outside any sandbox. Its `--check` works against Steam (2026-10-05); `create` has not run yet.
Upload the **plugins item** from a game started straight from Steam (no RML) after a fresh
`build.ps1 -Install`: with RML its DLLs are loaded and plugins may write into the folder, and Steam
fails the upload with "Unknown Error (Error code 2)" (seen with the Space Race, 2026-10-05). The map stays unpublished unless BATON agrees.

## 12. Links

- RML: https://steamcommunity.com/sharedfiles/filedetails/?id=3787969749 -
  https://github.com/Ultimate-Universe/WRSR-RepublicModLoader
- TesmioLoader: https://github.com/MaxLegend/TesmioLoader (branch `master`)
- BATON's map: https://steamcommunity.com/sharedfiles/filedetails/?id=3753525456
- Sister mod (same toolchain): https://github.com/aislanfoina/wrsr_spacerace
