# Republic in Ruins — handoff

Read this first. It is written for a fresh Claude Code session on a different
machine, and for you six weeks from now.

**The project:** a DLC-scale total conversion turning *Workers & Resources:
Soviet Republic* into a post-apocalyptic survival city builder. Target mechanics:
more disaster types, immigrants who arrive over time instead of on a click,
finite/random border trade, scavengeable map resources to bootstrap industry,
and post-apocalyptic building art.

**Game build:** `SOVIET64.exe` **1.1.1.9**, sha256 `296644a9f2…6841b8`, image
base `0x140000000`. Every address in these docs is an RVA — add
`TsmHost::exeBase`. **They are valid for this build only.**

---

## 1. Set up the new machine

1. **Game + Republic Mod Loader.** RML is Steam Workshop item `3787969749`.
   Its plugin folder — where everything here installs — is:
   ```
   <Steam>\steamapps\workshop\content\784150\3787969749\rml\plugins
   ```
2. **MSVC x64 build tools.** Any recent Visual Studio with the C++ workload.
   `build.ps1` finds the toolset itself and sets `INCLUDE`/`LIB` directly —
   **do not route it through `vcvars64.bat`**, see §5.
3. **Python 3 + capstone**, only for the reverse-engineering tools:
   `pip install capstone`
4. **The vendored SDK is in the package** (`vendor/TesmioLoader/src` and `docs`); re-clone only if you want the rest (excluded to save space, and
   our plugins `#include` its header):
   ```
   git clone --depth 1 https://github.com/MaxLegend/TesmioLoader.git vendor/TesmioLoader
   ```
5. **Fix the paths.** `build.ps1` and `tools/*.py` hardcode this machine's Steam
   location. Grep for `Program Files (x86)\Steam` and adjust.

Note (2026-09-22): on the other machine the hardcoded Steam paths were correct as shipped; no edit was needed.

## 2. Build and install

```powershell
.\build.ps1                              # build every plugin
.\build.ps1 -Install -Only trade_post     # install ONE plugin + all buildings
.\build.ps1 -Log                          # pull our lines out of RML's log
```

`-Only` matters. RML groups every DLL in `rml\plugins` under one Workshop item,
so they **cannot be enabled individually in its UI** — the folder is the switch.
It also stops two of our own plugins racing for the same hook, where whichever
loads first wins and the other silently refuses.

Buildings deploy to `media_soviet\workshop_wip\<numeric id>`. RML only
enumerates **numerically named** folders there, hence `$ITEM_ID 9000001`.

## 3. Where things stand

### Working and proven

| Thing | State |
|---|---|
| **Price control** | Solved. Writing `resource+0x64` changes the price shown *and charged*. Verified by pinning gravel to 999 and reading `Gravel - 999.00 P / 1t` off the screen. |
| **`.btf` localisation** | Format cracked; `tools/btf.py` round-trips all 7,906 strings byte-identically. `tools/en.json` is the full English text and doubles as a searchable index of what the game implements. |
| **PE tooling** | `tools/pe.py` reads sections and `.pdata`; with capstone it recovers the entire building-type dispatch table in seconds. That is the fastest route into any per-building behaviour. |
| **Survival Trade Post** | Building + plugin, **tested and working** in the other session (goods load, money drops; log `trade_post ... sold N t for M RUB`). Two more posts: goods post (9000041) and junkyard post (9000042). See §4h. |

### Abandoned, with reasons

- `mod/plugins/customs_stock` — **disabled, do not re-enable.** Redirects the
  construction planner's hardcoded `250.0`. It does not cap quantity or
  eligibility, but it *does* break construction supply: trucks under-load and
  building sites refuse deliveries.
- `mod/plugins/customs_market` — the border price model. Superseded by the trade
  post. Its stock-drain never worked; see the dead ends below.
- `mod/plugins/customs_probe` — the investigation probe. Read-only, useful for
  future digging. Its `0x68B330` hook is **disabled**: that function is 55 KB
  and cannot be forwarded from a C detour, and hooking it stopped the customs
  house selling anything at all.

## 4. The next step

**Test the Survival Trade Post.** It is your design: an ordinary `$TYPE_FACTORY`
that makes goods from nothing at a worker-driven rate (`$PRODUCTION` +
`$WORKERS_NEEDED` — the restock rule), holds them in real storages (the stock),
and runs dry when drained. The only code is `mod/plugins/trade_post`, which hooks
`FactoryTick` (`0x1D1E80`, free and unclaimed) and **charges money when a
storage's contents go down**, because only a loading vehicle does that.

Place it inland with road and power, staff it, let it produce, send a truck.
Watch your money and the log:

```
trade_post  adopted building 000001... with 5 tradeable slots
trade_post  000001... sold 12.40 t for 158 RUB so far
```

Things that may need fixing on first contact: a factory with no `$CONSUMPTION`
may refuse to run; the two `RESOURCE_TRANSPORT_OPEN` storages may merge instead
of staying per-resource; and `+0x64` may not be the right price column for a
non-customs building.

## 4b. The trade post model (Apocalypseburg / Mad Max)

The building now has its own mesh instead of the borrowed customs house:
`mod/buildings/trade_post/trade_post/` holds `model.nmf` (13 nodes, one per
material, 15.9k triangles), 13 DXT1 textures with mip chains, both `.mtl`
sets (the `_e` one lights the sign and lamps at night), a per-node
`building.bbox`, `building.fire` (fuel tank, drums, crane) and the icon.
**Everything is generated from the repo - no downloaded art:**

```
python tools/tradepost_textures.py build/textures
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --python tools/tradepost_scene.py -- build/textures mod/buildings/trade_post/trade_post build
```

The second command builds the compound procedurally, writes the NMF through
`tools/nmf.py`, and renders `build/tradepost_preview.png` / `_gate` / `_night`.
Layout is in game coordinates at the top of `build()`: road at +Z, gate opening
x -7.4..8.4, truck bays under the canopy. The dead square in `building.ini`
was widened to the whole footprint.

`tools/nmf.py` is the format. It round-trips every vanilla file byte for byte
(`python tools/nmf.py <files>`), so trust it over any forum post. Conventions
that bit: Blender -> game is a -90 deg X rotation (Y up, Z toward the road);
counter-clockwise is the front face; UV `v = 1 - v_blender`; the per-face plane
normal is `(p2-p0)x(p1-p0)`, i.e. *against* the face normal; indices are u16,
so a node holds at most 65535 vertices (the exporter splits per material).
3DIVISION's own Blender exporter (Dropbox "EXPORTER BLENDER", a Blender 5.2
beta included) writes the same layout, if you would rather model by hand.

**Not yet seen in the engine.** The workstation was locked when the model was
finished, and `ModelViewer.exe` (in-app buttons: Load NMF / Import OBJ / Save
NMF, DirectInput, no command line) cannot be driven or captured on a locked
desktop. First thing on a live machine: open ModelViewer, `Load NMF` on
`workshop_wip\9000001\trade_post\model.nmf`, and check the sign faces the
road. If a texture is missing the game's `log.html` says
`Load2DFromFileInMemory: FAILED`. To screenshot a DirectX window from a script,
GDI capture shows only the wallpaper; use `dxcam` (DXGI duplication) outside
the sandbox.

## 4c. The Mad Max vehicles and the map kit

One command rebuilds all of it (textures, skins, kit, vehicles, previews):

```
python tools/build_madmax.py            # everything
python tools/build_madmax.py deploy     # copy every mod item into workshop_wip
```

**Vehicles** (`mod/vehicles/<key>/`, workshop item ids 9000011-9000016) are
vanilla vehicles with welded-on scrap and new paint, each a complete
`WORKSHOP_ITEMTYPE_VEHICLE` item:

| key | vanilla | film look-alike |
|---|---|---|
| interceptor | S110R coupe | the Interceptor: supercharger, side pipes, bull bar, ducktail |
| nux | GZ M21 | Nux's coupe: roof cage, spare, fuel tanks, exhaust stacks, skull |
| buzzard | Trabi 601 | Buzzard spike car: spikes everywhere, plow |
| warrig | T815 cistern + trailer | the War Rig: plow, stacks, crow's nest, armoured trailer |
| raider | GZ66 covered | War Boys' raid truck: turret ring, plates, roof rack |
| warbus | Ikr 55 | war bus: barred windows, roof fighting platform, plow |

**Rail** (`trains/` in media, item ids 9000021-9000027): Iron Hog Locomotive
(M62: plow, armoured cab, roof cage, stacks), Scrap Shunter (CME3), Battle
Flatcar (gun nest, chained wreck, sandbags), Armoured Hopper, Guzzoline Tank
Car (catwalk cage, skulls, hazard band), War Boy Boxcar (plates, firing
slits, roof platform), Prison Car (barred windows). Wagons keep their
`$TRAINGROUP_*` and couple to anything.

**Ships** (`ships/`, ids 9000031-9000034): Rust Barge (bow ram, gunwale
spikes, caged wheelhouse), Guzzoline Tanker (Type-587: bow skull, hull
plates, nest on the bridge, deck cage), Raider Freighter (Ighnatov: deck
watchtower, spiked bow, wrecks on deck), Wasteland Skimmer (Meteor hydrofoil).
Bow is +Z on every vanilla ship (the `$WAVEPOINTFRONT` position), so the same
vehicle-space add-on toolbox applies.

`main.nmf` (and `joint.nmf` for the rig) is the vanilla mesh plus add-on
nodes; the vanilla LODs, spec and normal maps are referenced by media path,
so only the skins and a few kit textures ship. Paint variants use the game's
own `material_N.mtl` + `preview_N.dds` scheme: `wasteland` (rust, dust),
`warboy` (chalk, skull, V8, tallies), `black` (matte, the Interceptor).

- `tools/vehicle_skins.py` makes the skins. It rasterises the mesh's UV
  islands by face direction, so decals land on hoods/doors and the black
  glass is never rusted. Regions are found automatically; nothing is
  hand-placed.
- `tools/madmax_vehicles.py` (Blender) probes the body for hood/roof heights
  and welds the add-ons on in vehicle space (x right, y up, z forward).
- Material lists are kept identical between `main.nmf`, `joint.nmf` and every
  `.mtl` **in the same order**: the engine matches by name but falls back to
  index (the M21's mesh says `wire_087225087`, its .mtl `lambert1`).

**Map kit** (`mod/buildings/madmax_kit/`, item 9000002): twelve `$TYPE_MONUMENT`
decorations - scrap wall, wall tower, watchtower, shanty cluster, fuel depot,
wreck yard, ruined block, road wreck, skull totem, junk windpump, tyre
barricade, skull gate - all in one item sharing `material/`, as the big port
mods do. Monuments place anywhere in the editor, need no workers, do nothing.
`tools/madmax_kit_scene.py` builds them from `tools/mmkit.py`, the shared
primitive/composite toolbox; adding an asset is one function.

Renders of everything are in `build/kit/_kit_sheet.png`,
`build/vehicles/_vehicles_sheet.png`, `_trains_sheet.png`, `_ships_sheet.png`,
`_previews_sheet.png`.
Like the trade post, none of it has been seen in the engine yet (locked
desktop); the vehicle purchase list is the quickest check - the previews are
rendered from the very meshes and skins the game loads.

## 4d. The Scrap Center: disassemble a vehicle, learn its blueprint

**Why it is built this way.** Vanilla already has a vehicle scrapyard
(`$TYPE_SCRAPYARD`, "Send to scrapyard" on any vehicle, "Current scrapped
vehicle", scrap metal into its storages) and a blueprint licence system that
the campaign can grant for free (`Scenario_AddRoadVehicleBlueprint`). The
Scrap Center joins them: it *is* a scrapyard, and `mod/plugins/scrap_center`
marks the blueprint of whatever it is disassembling as owned. The game handles
the part that is hard to hook - pathing the vehicle in, removing it, producing
the scrap. Forbid buying blueprints in the scenario with
`Permissions_BlueprintAllowUSD/RUB` and scrapping becomes the only source.

**Data** (`mod/buildings/scrap_center/`, item 9000003): road bays for
vehicles that drive in, a pass-through rail siding (`$CONNECTION_RAIL_ALLOWPASS`
pair) for trains, and `$STORAGE_IMPORT RESOURCE_TRANSPORT_VEHICLES` for
vehicles delivered as cargo - the same intake set as the vanilla large
scrapping facility. Model: `tools/scrap_center_scene.py`.

**Ships: the Ship Breakers** (`mod/buildings/scrap_dock/`, item 9000004,
`tools/scrap_dock_scene.py`) is the dock variant: `$TYPE_SCRAPYARD` +
`$SUBTYPE_SHIP` in the vanilla ship-scrapping facility's exact frame - land
at -X, quay edge at x 27, three 233 m berths along +X at z 0/+-60, truck bays
on the quay, `$HARBOR_OVER_WATER_FROM -22` / `$HARBOR_OVER_TERRAIN_FROM -10`
copied verbatim. Two hulks hauled up the beach being cut open (outside the
berth lanes), jetties with derricks between the berths, the cutting hall and
blueprint office on the quay. The same plugin grants the blueprint - it hooks
every scrapyard, whatever its subtype.

**Airplanes cannot be scrapped by the engine at all**; hand those blueprints
out with the scenario instruction instead.

**Plugin facts (1.1.1.9):**

```
BUILDINGTYPE_SCRAPYARD = 109        "$TYPE_SCRAPYARD" parser branch at 0x10F4B2
0x14B920   ScrapyardTick(context, building), dispatcher arm at 0x13E1BA
           prologue 48 8B C4 57 41 54 41 55 41 56 41 57 48 81 EC 50 01 00 00
building+0x11C8   VehicleTypes* being disassembled; set from vehicle+0x1708
                  when a vehicle is accepted (vehicle destroyed right then by
                  0x3DED90), cleared when 0x1B07A0's progress reaches 1.0
building+0xC70/0xC78   vector<Vehicle*> of vehicles at this building
VehicleTypes   stride 0x9F08, contiguous; 0x1FEFF0 = base + i*0x9F08
  +0x200   ident (folder name)        +0x294   nVehicleType
  +0x85BC  nCostUSD   +0x85C0 nCostRUB   +0x8600 nResourceType   +0x8604 fResourceCapacity
  +0x9C88  bBlueprintPurchased  (VM Add/Remove handlers 0x5AD20A/0x5AD3AC,
           purchase button 0x812A40; followed by nBrandNewSoldForRUB/USD,
           nBuiltInProductionLine as the VM declares them)
```

The vehicle parser fills a stack-local descriptor at `rbp+0x200`
(`0x3EB870`); every VehicleTypes offset above is "local minus 0x200".

**The ranged variant you asked about** ("one building with a radius that
consumes vehicles parked in any depot/dock/hangar nearby") is feasible but
was not built, for one reason: there is no *intent* signal. The primitives
all exist - a depot's parked vehicles are its `+0xC70` vector, the game's
own removal is `0x3DED90(ctx, vehicle, 0, 0, 0, 0, 0.0f)`, the scrap credit
is `0x1AEDA0(ctx, building, type, 0.0f)`, the flag is `+0x9C88` - and the
repair office shows the range shape (`$REPAIR_AREA`). But "every vehicle
parked in range" would eat the player's fleet, and vanilla offers no
per-vehicle checkbox we can read without more reverse engineering. The one
signal worth chasing is the vehicle's **sell** state (`vehicle_buttonsell`
exists; find the state enum the button sets): "sold" in range of a Scrap
Center = disassembled for its blueprint instead of driven to the border.
That is the natural next step if the drive-in mechanic proves too slow.

**Not yet seen in the engine** (locked desktop again). First check: build the
Scrap Center, send any vehicle to it, watch the RML log for
`scrap_center  disassembling '<ident>' (blueprint NOT owned yet)` then
`learned blueprint '<ident>'`, and open a production line - the type should
be selectable without buying.

## 4e. Survivors: population without recruitment

**The idea, mapped onto vanilla.** Three engine systems already move people
across the border; `mod/plugins/survivors` re-purposes all three and lets the
game keep doing the pathing, housing and bookkeeping:

| Vanilla | Wasteland | How |
|---|---|---|
| Tourists arrive at a customs house on a timer scaled by visa research, an ad campaign and last cycle's satisfied returns | **Survivors.** Player picks them up, shelters them (hotels), they visit attractions. When one reaches a customs house to go home, a new citizen is spawned there instead: the survivor stayed. Vanilla's feedback loop then raises next cycle's arrivals - word spreads | post-hook on `CustomsHouseTick 0x1854E0`: delta of `building+0x1230` (returned this cycle) -> that many `SpawnPerson(immigrant)` |
| Immigrants bought for money | **Blocked** (`ctx+0x13690/0x13698 = 0`, the same bytes `Permissions_ImmigrantAllowPurchase*` sets). A free trickle of 2 per 120-unit cycle arrives at every customs house whose border has the distress call (tourist visa) researched, x2 while the distress broadcast (ad campaign, `ctx+0x11769/A`) runs | same hook, on the `+0xFC0` accumulator wrap |
| Foreign workers paid in money each time one boards home, at the live price of the `workers` resource (`ctx+0xC2C8`; `+0x5C` RUB soviet, `+0x58` USD western) | **Mercenaries** paid in kind from a Mercenary Camp (food 0.06 t, meat 0.03, clothes 0.02, alcohol 0.02 per arrival and per departure). No camp, or an empty one: nobody comes | pre-hook on `SpawnPerson 0x823330` (arg 6 = foreign worker), wrap of `PersonBoards 0x831120` pinning the four price columns to 0 around the call, camp adoption on `StorageTick 0x1CADC0` by storage fingerprint |

`SpawnPerson(ctx, building, expert, immigrantRUB, immigrantUSD, foreign)` is
the routine everything funnels through - the tick calls it for tourists (all
false) and foreign workers, the invite buttons after charging money. Calling it
directly is free. `0x185100` is NOT immigration: it is tourists-per-batch (the
"immigration step" note from the first session was wrong).

**Buildings** (`mod/buildings/survivors_kit`, item 9000006): Mercenary Camp
(`$TYPE_STORAGE` for the four wage goods), Distress Beacon (`$TYPE_BROADCAST`
`$SUBTYPE_RADIO`, 12 workers - a radio station in a wasteland skin, so vanilla
loyalty broadcasting applies), Survivor Shelter (`$TYPE_HOTEL`).
`tools/survivors_scene.py`.

**Words** (`mod/text/survivors_text`, item 9000005, `WORKSHOP_ITEMTYPE_TEXT`):
`tools/survivors_text.py` rewrites 47 English strings - tourists are
survivors, foreign workers mercenaries, the tourism research line is the
distress call/broadcast, and the "immigrants prevented" notice explains the
rule - into a `media_soviet.zip` with `sovietEnglish.btf`, which is exactly
what the UI-reskin TEXT items on the workshop ship. `mod/text/vfs/` holds the
same file for TesmioLoader's VFS. Whether the game honours a TEXT item from
`workshop_wip` is untested; if not, the VFS route or a published item.

**Scenario side** (for your map): `Permissions_ImmigrantAllowPurchaseUSD(0, 1)`
and `..RUB(0, 1)` belt-and-braces with the plugin; the tourism researches stay
as the distress-call tree. `Scenario_AddRoadVehicleBlueprint` for airplanes,
which the scrapyard cannot eat.

**Log lines to expect:** `survivors  customs ...: N survivors settled, M
arrived on their own`, `mercenary camp adopted ...`, `mercenaries: hired /
paid off / turned away`. Not yet seen in the engine.

## 4f. Korea Year Zero: the post-strike map (2026-09-21)

**Source:** BATON's "North Korea map - Early start version" (workshop 3753525456,
a rework of the World Maps DLC `dlc4/terrains/northkorea`; 638 buildings, 617 of
them DLC2 wooden huts, 517k trees, save-format version 124). The Kiev map
(1992286405) was not tried; the converter is map-agnostic except for the strike
coordinates and zone bearings at the top of `tools/yearzero.py`.

**Output:** `media_soviet/workshop_wip/9000007` (LANDSCAPE item "Korea Year
Zero"), a scenario in `media_soviet/scenarios/yearzero` (also mirrored as
workshop_wip/9000008), debug plot `build/yz_layout.png`, layout table
`build/yearzero_layout.json`.

**Formats decoded** (all in `tools/mapio.py`, details in the memory note
`wrsr-map-format`): engine fragments in `buildings.bin` (0x46 bytes: pos,
rotation step of 128, world AABB), game records in `buildings_game.bin`
(self-describing, header 0x548 with ident/city/pos/rot/fragment index), trees,
mask channels (R,G,B = tiles 2,3,4), pixel mapping without flips, rotation
convention verified against 638 placed huts to 0.0 m error.

**What the converter does**
1. Terrain: three custom tiles (`tools/wasteland_tiles.py`: dead grass, fallout
   dust, scorched) shipped inside the map folder and referenced as
   `workshop_wip/9000007/tiles/...` (texture paths resolve relative to
   media_soviet). Mask repainted with scorched (G) and dust (R) rings around three
   ground zeros (capital -3709,-3717; east port 3940,758; north gate town
   2400,-5207) with ragged noisy edges. Heightmap only flattened under kit
   buildings; `collision.dta` deleted so the engine regenerates it.
2. Trees: cleared inside the scorch radius, 80% removed in the fallout ring,
   globally thinned and retyped to the dry afghan_* species (226k of 517k left).
3. Huts inside each inner radius (120/75/65 m, 154 huts) are replaced *in place*
   by Mad-Max ruin pieces (mm_road_wreck, barricade, scrap wall, wreck yard,
   shanty, ruin block, fuel depot, totem) on the hut's position and rotation. In
   place means no record index shifts: the ruin record is a clone of the map's
   own transformer record with a new ident, and the hut's fragment is removed
   from its type list with the remaining fragment indices renumbered.
4. Start kit appended as new records cloned from donor records pulled out of the
   user's own saves (`tools/donors.py`, read-only on `media_soviet/save`):
   motor pool (muddy_depot), vehicle repair yard (DLC3_h_repair_station),
   salvage office (muddy_demolition), rubble crusher/scrap smelter
   (waste_gravelrecycling/steelrecycling), dump, open+gravel storage, Scrap
   Center, Survival Trade Post, Mercenary Camp, Distress Beacon, Survivor
   Shelter, farm + 2 fields, food plant, distillery, slaughterhouse, clothing
   workshop, woodcutters. They are laid out along the three roads leaving the
   capital (NE industrial, SE town, S farm), on the side away from the crater,
   rotated so the `$CONNECTION_ROAD` stub faces the road, 6 m off the road
   centreline; road positions come from float3 triples in `road.bin` that sit on
   the terrain (`build/nk_roadpts.npy`). Kit buildings whose class has no donor
   use a FACTORY/STORAGE/worker-building donor of the nearest class.
5. Scenario `yearzero`: no immigrant purchase, no vehicle purchase, blueprints
   only from the scrap center, border purchases at 4x, 120k RUB / 4k USD,
   warrig+raider blueprints, three wrecks (warrig, raider, buzzard) put into the
   motor pool by `Scenario_AddRoadVehicleToBuilding`, an opening window.
   `$AVAILABLE_ON_ALL_MAPS` because the workshop map name matching is unverified.

**Known gaps / risks**
- Cloned records keep the donor's road connections and any vehicle references;
  the loader's post-load fixups may or may not re-link them. Expect to build a
  short road stub to each kit building; if a clone crashes the load, drop that
  entry from KIT and rerun.
- 3 of 22 kit buildings did not fit on the roads in the last run (industrial 7/9,
  farm 8/9); widen the zone bands or add a zone.
- Loyalty per citizen: resident data sits inside hut records (+0x48C is a count
  correlated with size) but the person layout is not decoded; not touched.
- In-game verification: see the test log below.

**Test log**
- 2026-09-22 (Steam signed in, all plugins active): the first load died in
  "Import - Buildings game" with `IO_Building_Read BuildingType is NULL -
  mm_barricade`, then thousands of `GetFragmentByIndexAndType returns NULL`
  and exit 0xC0000409 after 5 min. Three root causes, all fixed:
  1. **Workshop building/vehicle types are registered as `<item id>/<object>`**
     (`9000002/mm_barricade`, `9000014/warrig`; SOVIET64 LoadBuildingType
     0x11D800 does `sprintf("%llu/%s")`; the user's saves confirm it with
     `1873180745/Transformer`, `2976295075/QuadBus`). `tools/yearzero.py` now
     renames every WIP ident at write time (`game_ident()`, built from
     workshop_wip/*/workshopconfig.ini) in both buildings.bin and
     buildings_game.bin and in the scenario's vehicle calls; the fallout plugin
     matches `mm_` on the part after the last `/`. **The map must be regenerated
     once the items have their real Steam ids.**
  2. **A record's layout is per `$TYPE`** (`build/recsizes.py`), so a donor must
     have the target's type: ruins/decor now clone `MIRRORZ_DLC4_monument`
     (TYPE_MONUMENT, 173 KB each, buildings_game.bin 42 -> 68 MB), the Scrap
     Center clones `CWC_scrapping_facility1` (TYPE_SCRAPYARD), the Distress
     Beacon clones `rozhlas_v2` (TYPE_BROADCAST, added to `tools/donors.py`).
  3. **Scenario auto-start**: no scenario picker exists in the Custom Game UI;
     the map's `stats.ini` line `$ScenarioAutoStart yearzero yearzero` starts
     `media_soviet/scenarios/yearzero/yearzero` on load (how campaign1 does it).
     `yearzero.py` writes it and installs the scenario copy.
  After the fixes the map loads in ~20 s: opening window, 120k RUB / 4k USD,
  1,341 citizens, wasteland tiles, ruins in the craters; fallout logs
  `zones 1.00/1.00/1.00 (ruins 87/87, 38/38, 29/29)`. Two follow-ups: the
  repair-station donor carried a trailing fragment-less `temp` helper record
  ("Missing workshop item(s): 1 Building(s) deleted"; `load_donor()` now trims
  it), and the game died with 0xC0000005 about 2.5 min after init while the
  camera was panned east towards the kit - no dump anywhere, so
  `mod/plugins/fallout/crashlog.cpp` (vectored exception logger) was added to
  get module+offset on the next run.
- 2026-09-22, run 2 (no interaction): same crash, now located: `SOVIET64.exe+
  0x1F001B` in Building::Write (0x1EDC40, called per building by the save loop
  "Write build %d" at 0x42E7C4) - i.e. the **autosave** ~2.5 min after init.
  It walks the pointer list at building+0x880 (count in the record header at
  +0x414; the reader at 0x1F4530 resolves each stored index through a global
  table with no bounds check) and one pointer is NULL. Only one donor carried
  entries there: `DLC3_distillery_small` from save b31 (10 entries at +0x880,
  8 at +0x718) - the trade post, distillery, animal pens and slaughterhouse
  were cloned from it. Rule: **a donor must carry no external references**
  (header words +0x408/+0x40C/+0x414 must be 0; `build/recsizes.py` and the
  header dump in the transcript). Those four now clone `DLC3_clothing_factory`.
  `tools/donors.py` now skips candidates with those counts and trims the `temp`
  tail itself.
- 2026-09-22, run 3: **loads in ~10 s, runs, and the autosave succeeds**
  (`media_soviet/save/autosave2` written; no crashlog line; population 1,341
  -> 1,372 from arrivals in 5 min; fallout ticking 1.00/1.00/1.00 with all
  154 ruins counted). Driving the camera needs scan-code key input
  (`build/gdrive.py hold()`, SendInput with KEYEVENTF_SCANCODE): the game reads
  the keyboard through DirectInput and ignores plain virtual-key events.
  Not yet seen with my own eyes: the kit buildings east of the capital and the
  ruin pieces close up (the camera tour never reached them before the session
  ended; the user's evening session then overwrote all five autosave slots, so
  the game's re-serialisation of our map is gone too).
- 2026-09-24, offline only (user tests in-game manually from here):
  pollution grid orientation confirmed x-major against three real saves
  (`pollution.bin` peaks 19/70/137 m from the strike points); all 18 VM calls in
  `start.txt` exist in `media_soviet/scripts/SOVIETInstructions.txt`; generated
  fragments match the game's conventions (the 16 header bytes and the float4 at
  0x36 are junk the game rewrites; the byte at 0x35 varies per instance, 1 is
  what the map's own huts carry). Archives refreshed (`wrsr-mod.zip`,
  `wrsr-handoff.zip`).
  **Manual test checklist:** Custom Game -> page 6 -> "Korea Year Zero" (WIP
  item) -> Crime & justice *Enable*, Waste management *Waste + Demolition* ->
  start. Expect the "Year Zero" window, 120,000 RUB / 4,000 USD, no "Missing
  workshop item(s)" dialog. On screen the river lies south of the capital ring
  (the camera looks along +z). The start kit: industrial across the river on the
  hill to the lower right (motor pool with 3 wrecks at x -3159 z -4220, Scrap
  Center at -3201/-4154), town kit to the right (trade post -3203/-3411 ...
  shelter -3197/-3246), farm kit further right/up (fields around -3478/-3094 and
  -3426/-2953); see `build/nk_capital_terrain.png`. Let it run past 3 minutes
  (autosave) and check `rml-runtime.log` for `crashlog  exception` lines; then
  click the trade post / mercenary camp and watch for `trade_post  adopted` and
  `survivors  mercenary camp adopted` in the log.
- 2026-09-21: not loaded in-engine yet. Every launch (RML or direct exe) shows
  the game window for ~2 s and then destroys it while the process keeps running;
  a passive window watcher (`build/winwatch.py`) caught the reason: at the same
  moment Steam pops a **"Refresh Sign In"** prompt. Steam's session on this PC
  needs a manual re-login (the account was also in use on another PC, which
  Steam offered to stream from). Once Steam is signed in again: open
  RepublicModLoader.exe, Launch, New game -> map "Korea Year Zero" (workshop_wip
  9000007), pick the "Korea Year Zero" scenario, and check `rml/logs/rml-runtime.log`
  plus `SovietRepublic/log.html` for load errors. Capture with
  `python tools/gamectl.py shot out.png` (the game runs borderless 5120x1440).
- The generated files pass the offline checks: 662 records split and validate
  against their fragments, every fragment has a record, all tree types exist in
  treetypes.ini (`tools/yearzero.py` run, verified by re-reading with mapio).

## 4g. Contamination instead of crime (2026-09-22)

Design: `docs/contamination-design.md`. Implemented pieces:

- **Plugin `mod/plugins/fallout`** (post-hook on `TickAllBuildings` 0x139A70,
  the game's once-per-tick walk over every building, rcx = game object). Every
  40 ticks it: recomputes three crater zones (half-life in ticks, cleanup factor
  = live `mm_*` ruins inside the zone / initial), scans buildings for waste
  stored within 500 m of a crater (hot-salvage halos), writes the field into the
  game's radiation grid (game+0x120A8, 12-byte cells, x-major, column 0 =
  radioactivity; the game samples it into living buildings' +0x11B4 and decays
  it 0.005 per pollution update), and doses every citizen standing in a building
  inside the field: `person+0x10C` (fStatusCrime) grows with the field, decays
  without exposure, and above 0.85 erodes `person+0xE0` (health). A newcomer first
  seen at a customs house has a 15% chance to arrive with a 0.35-0.75 dose.
  Offsets came from the scripting VM's accessors (Person 30000 at 0x5BE480,
  Building 10000 at 0x5B3950): person statuses are 10 floats from +0xD8, crime
  is the 13th float (+0x10C); building position is the C3D_NODE at +0x320 read
  through the DLL's `C3D_NODE::GetPosition`; persons vector game+0x126A8.
  Tuning constants sit at the top of `fallout.cpp`; the zone coordinates are the
  Korea Year Zero strike points and must change with the map.
- **Words**: `tools/fallout_text.py` (about 120 ids) merged into the single TEXT
  overlay by `survivors_text.py` (item 9000005 + VFS copy). Police station ->
  Decontamination Task Force, court -> Radiology Board, prison -> Recovery Center,
  secret police -> Reunification Office, police car -> Geiger patrol car, prison
  bus -> quarantine bus, crime classes -> exposure / radiation sickness / acute
  syndrome, and all the notifications and statistics.
- **Buildings**: `tools/fallout_scene.py` -> `mod/buildings/fallout_kit` (item
  9000009): `dtf_station` ($TYPE_POLICE_STATION, 4 patrol stations),
  `radiology_board` ($TYPE_COURT_HOUSE), `recovery_center` ($TYPE_PRISON, 2 bus
  stations, prison demands). Functional keys copied from police_small,
  court_small and prison.
- **Vehicles**: `geiger` (skin of z_police_vz2109, item 9000017) and `quarantine`
  (z_police_b1000_prison, 9000018); `keep_skill=True` keeps `$SKILL_POLICECAR` /
  `$SKILL_POLICEBUS`. Build only these with `MM_ONLY=geiger,quarantine`.
- **Ruins are ore**: the mm_* pieces now carry `$COST_RESOURCE_AUTO wall_concrete`
  / `wall_steel` (0.05-0.9), so demolishing them through the salvage office yields
  construction waste and scrap for the crusher and smelter, and each ruin removed
  lowers its zone (the plugin counts them).
- **Map**: `tools/yearzero.py` now writes `pollution.bin` with the initial field
  and the scenario carries four objectives plus a reunification watch (average
  `Person.fStatusSoviet` over a 1-in-7 sample every 30 s; above 0.75 the win
  window fires). Requires "Crime & Justice: Enabled" and "Waste + Demolition".

Unverified in-engine (Steam sign-in still pending): the tick-dispatcher hook,
that column 0 is read as radioactivity by the game, the crime thresholds that
raise a case (0.33/0.66/0.85 are assumptions to tune), and whether the scenario
VM accepts `defineVariable(Person, p)` with `p.GetDataByIndex(i)`.

## 4h. Trade post: merged from the other session (2026-09-22)

The other session (its export is `docs/TRADE-POST-HANDOFF.md`) verified the
mechanic in the running game: a worker-free `$TYPE_FACTORY` with no consumption
line produces at the configured rate on power alone, a truck loads it, and the
`FactoryTick` post-hook bills the drop in storage at `resource+0x64` times the
multiplier. Its three buildings used vanilla donor meshes and ids 9000001,
9000030, 9000031; **here 9000031-34 are the ships**, so the extra posts are
9000041 (goods post: food, alcohol, clothes, eletronics) and 9000042 (junkyard
post) and keep the Mad-Max models. Their files were not on this machine; the
merge re-creates them from the description and applies the findings:

- `building.ini` has **no comment syntax**: the parser reads every
  whitespace-separated token beginning with `$`, anywhere. Our trade post ini
  carried exactly the comment that crashed the other session
  (`$PRODUCTION plus $WORKERS_NEEDED`); all inis are now scanned and clean, and
  the bare `$RESOURCE_VISUALIZATION 0` headers were removed (a header is always
  followed by a block in vanilla). Symptom: `ResourceGet - not found <word>` in
  `SovietRepublic/log.html`.
- Posts are worker-free (`$WORKERS_NEEDED` removed), `eletric 0.02`, no input.
- `trade_post.dll` 1.0 reads `trade_post.ini` from its own folder (module path,
  not the host config API): price multiplier, currency RUB/USD, per-resource
  overrides; bills nine goods, fingerprint = exports 3+ of them.
  `[production]` is stamped into the posts' building.ini by
  `tools/stamp_production.py` at install time.
- RML: **development items must be ticked** or nothing under `workshop_wip` is
  loaded (`Development inventory: local=N enabled=M` in rml-runtime.log; it was
  enabled=0 here until this merge set them in config.json). RML holds
  `previewimage.png` open while running, so install with RML closed.
- Known chain: Enhanced Storage Management, ForceNodes and ParallelUtilities
  also hook the tick dispatcher 0x139A70; RML chains legacy inline hooks
  ("[HOOK CHAINED]"), which is what the fallout plugin relies on.
- Every item now carries `$OWNER_ID` and a `previewimage.png` (the convention
  of all 55 installed items).

**Delta zip merged (2026-09-22, second pass).** The other session's actual files
arrived afterwards: `trade_post.cpp` is now that verified source verbatim (Config
struct, 32 named price overrides, USD via usd_rate, quiet logging), the ini is its
richer one (goods rates food 0.40, alcohol 0.15, clothes 0.12, eletronics 0.05),
`tools/dump.py` is in, and the posts took its storage sizes plus
`$WASTE_PRODUCTION_DISABLE` / `$HEATING_DISABLE`. Not taken: its meshes (vanilla
zoll_sahy and waste_steelrecycling copies; ours stay Mad-Max), its ids
9000030/31 (ours 9000041/42), `$OWNER_ID 0` / `[dev]` names, and the junkyard's
`$RESOURCE_PRICE_CALCULATION_*` flags (its own comment says unused). Its
`build.ps1` matched ours feature for feature except the try/catch around the
staged swap, which was adopted.

- Still outstanding from that session: the "Importing House" naming for the
  general game (this playground keeps the survival names), runtime production
  rates, and `tools/dump.py` (minidump parser, not useful for this game).

## 4h2. Publishing Republic in Ruins (2026-09-30)

- **GitHub:** https://github.com/aislanfoina/wrsr_yearzero, mirrored from this workspace by
  `python tools/export_yearzero.py` (repo-only files in `repo_yearzero/`). Branches as for the
  Space Race: commit to `unstable`; `dev` (two approvals) and `main` (code owner) by pull request.
- **Workshop:** four items instead of one per kit and per vehicle - plugins 9000090, buildings
  9000050 (the eight kits share one `material/`; their `tp_*` textures are identical), vehicles
  9000051, words 9000005. `tools/yearzero_workshop.py` packs them into `build/workshop` and holds
  the Steam pages; the repo's `build.ps1 -Install` deploys them. Packing changes the idents to
  `<item>/<object>` of the merged items, so the map converter must run after that install.
- **Not published:** the Korea Year Zero map (BATON's map and the World Maps DLC terrain under it).
  The converter falls back to `data/yearzero/` (donor records, road points, model bounds) when
  `build/` lacks them; the tools take `WRSR_GAME` / `WRSR_WORKSHOP` for other Steam libraries.
- **Signs were mirrored in game.** The engine shows every model mirrored (Space Race kit,
  2026-09-29), and `mmkit.Builder.text` / `tradepost_scene.text` built lettering as authored, so
  TRADE POST, SHELTER, BEACON, DTF, SCRAP CENTER... read backwards. Both now mirror it (like
  `srkit.mtext`); the five sign-carrying kits were regenerated and only their models, bounding
  boxes and icons taken (plus the survivors kit's material files, which the generator had moved on
  to). The goods post and the junkyard post reuse the trade post's and the Scrap Center's models.
  Not yet seen in game.
- README pictures: `python tools/yearzero_readme_images.py` (renders on wasteland terrain with
  `tools/yearzero_readme_scene.py`, mirrored as the game shows them, plus the Workshop previews).

## 4i. Space Race (second mod, 2026-09-29)

A separate mod in the same repo: the Soviet space programme as a research
branch, a 16-building kit, five rockets, an expert education tier and a
programme scenario that starts itself in ordinary games. Design, build status
and the manual test checklist: `docs/space-race-design.md` (section 10). Build
with `python tools/build_space.py`; plugins `spacerace` and `experts` build with
the rest in `build.ps1` and install disabled by default.

## 5. Traps that cost real time

- **Workshop types are named `<item id>/<object>` inside maps, saves and
  scripts** (`9000002/mm_barricade`, `9000014/warrig`), never the bare folder
  name. A map that references a bare WIP ident kills the load with
  `BuildingType is NULL`. Anything that compares idents (plugins) must look at
  the part after the last `/`. Regenerate the map after publishing, when the
  ids change.
- **Donor records must match the target's `$TYPE`.** The building record tail
  is type-specific; a transformer-sized blob under a monument ident misaligns
  every record after it. `build/recsizes.py` lists target vs donor types.
- **Donor blobs can hide a trailing `temp` helper record** (fragment index
  0xFFFFFFFF, no fragment) that the anchor splitter cannot see; the game reads
  it as one more building. `load_donor()` trims it.
- **The Bash tool mangles backslashes inside heredocs** (`'\\r\\n'` arrives as
  a real CR LF and breaks the Python file it patches). Write patch scripts with
  the Write tool; text-mode `open(p, 'w')` on Windows also turns LF files CRLF.
- **`building.ini` comments can execute.** Any token starting with `$` is a
  directive wherever it sits; `;` means nothing. Write directive names without
  the dollar in prose, or glue `//`/`--` to the `$` to disable a line. Cost the
  other session a dozen launches.
- **Added goods are invisible to scenario scripts (2026-09-29).** `Resources.*FromBuilding` places a good via 0x59B3F0(vm, name), a string-compare chain over the base game's names that returns 0 - the `workers` field - for anything else, so a mod good read by a script silently lands in `res.workers`. The spacerace plugin hooks it and maps its `vm_goods` to `_Resources_reserved_16_..19_`. The VM also cannot take goods out of a building (`AddFromBuilding` only reads); a plugin must.
- **Never change a mission script that saves are running (2026-09-29).** A save keeps the running programme's state in `runningScripts.bin` (its texts and data), so a changed `programme.txt` under an existing save risks restoring state into code that no longer matches. A rewrite gets a new mission folder (`tools/space_scenario.py` MISSION, now `race`; spacerace.ini `mission`), and the old folder stays frozen in `mod/plugins/spacerace/legacy/` and is copied in beside it, so old saves keep the old programme. Since 2026-09-30 the programme is a template the plugin renders into `race_<hash>` per set of settings; never delete those folders from media_soviet.
- **A save holding an unknown good crashes the save writer (2026-09-30).** Loading works (the name is skipped with "ResourceGet - not found"), but the next save dies with 0xC0000005 on the empty slot. The resources plugin with `new_goods = 0` therefore aliases the six goods to their stand-ins in ResourceGet. Any other mod that drops goods has the same trap.
- **Building construction costs in memory (2026-09-30):** type (table [0x9E6A30], stride 0xBE8) +0x370/+0x378 = phase records (0x21B8 bytes), each with a std::vector of {Resource*, float, pad}. `python build/costdump.py kit` (or any idents) prints what the game made of auto costs.
- **Game UI for saving/loading while driving the game (5120x1440):** settings icon (40,167); in its panel save-as (207,293), load (287,293). Save-as list: "Create new save" (3000,965), then confirm (2700,733) (the name field keeps "My republic" - typing did not reach it). In-game load: pick the row, load (2950,960), confirm (2700,733). Main menu Load Game (1960,777), confirm (3117,1300). ESC does not open a menu in game. Red rows in the load list are autosaves, not incompatible saves.
- **Building ini direction and layout rules (2026-09-29, space kit test).** `$CONNECTION_ROAD` and `$CONNECTION_PEDESTRIAN` list the outside point first and the lot-edge point second (vanilla `kino.ini`); reversed, the arrow points into the building and no path can connect. Truck bays (`$VEHICLE_STATION`) must run through open yard: `python tools/space_layout.py` draws each kit lot with its bays and connections and fails on a bay through tall geometry. The scenario VM has no `>=`, `<=`, `==` or `!=`.
- **Plugins ship in packages, not `rml\plugins` (2026-09-29).** RML attributes every DLL in `rml\plugins` to its own workshop item (3787969749) and toggles them as one, so our plugins were all-or-nothing. A plugin with `package.txt` (naming a folder in `mod\packages`) is now installed by `build.ps1 -Install` into that package's development item (`workshop_wip\<id>\plugins`, WORKSHOP_ITEMTYPE_SCRIPT), which RML switches with the item: Space Race = 9000100 (spacerace, experts), Republic in Ruins = 9000090 (fallout, scrap_center, survivors, trade_post). Stale copies are removed from `rml\plugins`. `-Only` is obsolete.
- **`build.ps1 -Install -Only X` removes every other plugin** from `rml\plugins` (it treats the folder as the only switch). Reinstall with a plain `-Install` afterwards, or do not use `-Only` for installs.
- **Retired 2026-09-22:** the three customs_* plugins moved to `attic/plugins` and were removed from `rml\plugins`; two of them hooked CustomsHouseTick ahead of the survivors plugin and made its install refuse, which under the loader's fail-closed rule aborts the whole game launch. Plugins now present the live bytes when a target is already patched, so sharing a target with another mod chains instead of refusing.
- **RML development items default to off.** `Development inventory: enabled=0`
  means your workshop_wip work is not loaded at all.
- **RML holds previewimage.png open** while its launcher runs; installing over
  a deployed item then half-deletes it. Close RML first.

- **`vcvars64.bat` is broken** on VS 2026 Build Tools: it expands
  `%ProgramFiles(x86)%` unquoted inside a parenthesised block, so the `(x86)`
  closes the block early. Fails whenever that variable is missing — which is any
  shell started from Git Bash. `build.ps1` bypasses it entirely.
- **Plugin `.ini` files are never read through `configInt`** (it resolves against
  `TsmHost::baseDir`, which under RML's compatibility host is neither
  `rml\plugins` nor the workshop item's folder. **Only the code defaults apply.**
  Anything a plugin must do has to be a default.
- **`TsmHost::log` is not printf.** `%s`, `%p`, `%llu`, `%X` work; width-modified
  conversions like `%-24s` do not — the literal is printed and *no argument is
  consumed*, so everything after it reads the wrong stack slot. Format into a
  local buffer and pass a single `%s`.
- **Check RML's compatibility report by SYMBOL NAME, not RVA.** Resolved symbols
  are listed separately from raw addresses. Both `wrsr.vehicle.task_advance` and
  `wrsr.vehicle.compatibility_check` are already hooked by
  `helicopter_distribution_office` and `RollingStockRoadTransport`.
- **Batch files need CRLF** or `goto` misbehaves silently.
- **Steam wipes `rml\plugins` when RML updates.** Re-run `-Install`.

## 6. Dead ends — do not repeat these

The customs house cannot be made to report how much was bought. Four approaches
failed, each for a different and now-understood reason:

| Approach | Why it failed |
|---|---|
| Intercept the goods flow at `0x68B330` | 55 KB function with stack arguments; a C detour cannot preserve the caller's frame. Hooking it stopped all border sales. Needs an assembly thunk. |
| Live price `+0x58` drift as a volume proxy | It is the world market simulation, not the player. Untraded resources drift ±0.5% in both directions at the same timestamps; three trainloads of gravel moved it +0.4%. Signal is below noise. |
| Base price `+0x78` | **Zero for every construction resource.** Only populated for some (waste_toxic has it). |
| Storage slot flow | Goods never pass through. A customs house holds nothing — every slot reads 0.000 with a 1 t capacity, and asphalt is sold there despite having *no slot at all*. |

**The underlying reason:** WRSR has **no border purchase transaction.** The
border bills continuously per unit as goods flow — measured as a smooth drain of
~490 RUB over four seconds with no discrete jump in 370 samples. There is no
event to catch, which is why every gate and pricing hook sat silent.

**This is exactly why the trade post exists.** A factory's storage is real and
observable, so the sale is a subtraction.

## 7. Key addresses

Full detail with disassembly is in `docs/customs-house-notes.md`. The essentials:

```
0x139A70   building tick dispatcher (20964 b) — the way into any per-building behaviour
0x13E2FA   its BUILDINGTYPE_CUSTOMHOUSE (20) arm -> calls 0x1854E0
0x1854E0   CustomsHouseTick(context, building)   — reliable hook, never failed
0x13DD69   its BUILDINGTYPE_FACTORY (6) arm     -> calls 0x1D1E80
0x1D1E80   FactoryTick(context, building)       — free, unclaimed, what trade_post uses
0x185100   immigration step (NOT trade) — weights 1/10/5 match the invite buttons
0x1561C0   construction supply planner; customs houses short-circuit to 250.0
0x424430   the REAL "how much can this building supply" routine
0x2AA830   ResourceGet(name)

game object = exe+0x9D4F10 (a global, so offsets are stable)
  game+0x580   USD balance (double)
  game+0x588   RUB balance (double)

building+0x318   type descriptor; +0x360 within it is BUILDINGTYPE
building+0x970   std::vector<Storage>, stride 0xE0
building+0x9EC   which border a customs house faces (3 or 4)
building+0xFC0   tick accumulator

storage+0x00/+0x08  begin/end of a slot vector, stride 16
storage+0x8C        capacity (float)
storage+0x90        transport class (int)
slot                { resource*, float content, float limit }

resource+0x00   32-byte NUL-terminated name
resource+0x58   live price          +0x5C = x0.75
resource+0x60   = +0x58 x 1.105     +0x64 = SHOWN AND CHARGED
```

## 8. The wider plan

`docs/feasibility.html` is the full analysis. The short version: four of the five
target mechanics are already half-built in vanilla — immigrants are a real
first-class category, the `waste_gravel -> gravel` / `waste_steel -> steel`
recycling chains already exist, price-shock events are already resource-generic,
and deposits can already be made finite by TesmioLoader's depletion plugin.

**Phase 2 remains unblocked and needs no reverse engineering at all:** a custom
map with pre-placed ruins plus a demolition office in the starting kit gives the
entire scavenging opening using vanilla mechanics. If the trade post stalls,
that is where to go next — it is the part players actually feel.
