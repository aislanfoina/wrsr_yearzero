# Customs house — reverse engineering notes

Target: `SOVIET64.exe` **1.1.1.9**, image base `0x140000000`, sha256
`296644a9f2…6841b8`. All addresses below are RVAs; add `TsmHost::exeBase`.

Where a TesmioLoader doc address (written against 1.1.1.7) is quoted for
comparison it is marked as such. **Nothing here was copied from those docs
without being re-derived against this build.**

## Verified

| RVA | What | How confirmed |
|---|---|---|
| `0x139A70` | Building tick dispatcher, 20964 bytes | `.pdata` extent is exactly the 20964 the 1.1.1.7 notes give; RML's own compatibility report observes plugin hooks at this RVA |
| `0x13E2FA` | The `BUILDINGTYPE_CUSTOMHOUSE` (20) arm of that dispatcher | Disassembled; 1.1.1.7 notes put it at `0x13E30A`, exactly `0x10` higher, the same delta as the dispatcher itself |
| `0x1854E0` | `CustomsHouseTick(context, building)`, 514 bytes | Call target of the arm above |
| `0x185100` | Immigration step, 991 bytes | Called in a loop from the tick; see below |
| `0x2AA830` | `ResourceGet`, 735 bytes | RML symbol cache reports this RVA and size; our `.pdata` parse agrees exactly — this is the calibration that validates the PE reader |
| `building+0x970` | `std::vector<Storage>`, stride `0xE0`, with begin/end/capacity | **Observed in game.** Two customs houses reported 14 and 15 records, matching their `$STORAGE` lists. The 1.1.1.7 offset carried over unchanged |

### The dispatcher arm

```
0013E2F3  mov  rax, [r8 + 0x318]        ; building -> type descriptor
0013E2FA  cmp  dword [rax + 0x360], 0x14
0013E301  jne  skip
0013E303  mov  rdx, r8                  ; arg2 = building
0013E306  mov  rcx, rsi                 ; arg1 = context
0013E309  call 0x1854E0
```

Every type arm has this shape, so the same technique locates the handler for any
`BUILDINGTYPE`. `tools/pe.py` plus capstone reproduces the full table in seconds.

### The tick

`0x1854E0` accumulates elapsed time into `building+0xFC0` and, while that
exceeds successive multiples of a fixed interval, calls `0x185100`. Its first 15
bytes are a clean hook site — no rip-relative operands, ends on an instruction
boundary:

```
48 8B C4              mov  rax, rsp
48 89 58 18           mov  [rax+0x18], rbx
56                    push rsi
48 81 EC 90 00 00 00  sub  rsp, 0x90
```

## Established negative — `0x185100` is immigration, not trade

Worth writing down because it is the obvious wrong turn. `0x185100` reads a
**game-level** vector of 1024-byte records (`game+0x11728` begin, `game+0x11730`
end), gates on `building+0x9EC` being 3 or 4 against flags at `game+0x11767` /
`+0x11768`, and weights three counters at `game+0x11624` / `+0x1162C` /
`+0x11634` by **1, 10 and 5**.

Those weights match the three invitation buttons exactly — *invite 10 from the
Soviet bloc*, *invite 10 from the third world*, *invite 5 experts*. So this is
the hook site for the **immigration** half of the overhaul (phase 5), and the
resource trade lives elsewhere.

It also iterates only the last 15 records of that vector (`count - 15`), which
is unexplained and worth a second look when immigration comes up.

## Still unknown

The resource purchase path. `cmp [reg+0x360], 20` occurs in **80+ functions**
across the binary, so reading outward from the type check does not converge.
Candidates worth attention, by size and position:

- `0x1561C0` (10885 b, 9 customs sites) — the densest cluster anywhere
- `0x173320` (6145 b, 3 sites)
- `0x1AAD70` (1297 b, 3 sites)
- `0x769300` (3693 b, 4 sites) — likely UI, four sites in a small function
- `0x831120` (1495 b, 4 sites)

## The storage record — solved in game

`building+0x970` is `std::vector<Storage>`, stride `0xE0`. Within one record:

| Offset | Field | Evidence |
|---|---|---|
| `+0x00` / `+0x08` | begin/end of a nested **slot vector**, stride 16 | record 0 spanned `0xC0` = 12 slots. The dwords at `+0x0C` reading `443`/`444` are the *high halves* of those pointers (`0x1BB`, `0x1BC`), matching the observed heap addresses |
| `+0x8C` | capacity, float | reads exactly **1.000**, matching `$STORAGE RESOURCE_TRANSPORT_* 1` in `zoll_*.ini`; one record reads `0.120`, matching the waste storage |
| `+0x90` | transport class, int | observed `2,1,0,3,4,5,6,15,16,17,17,17,17,17,10` — four 17s, matching the four `$STORAGE*_WASTE` lines |

**And the decisive negative:** across two 105 t purchases of `fertiliser_liquid`,
not one storage record changed. Capacity is 1 tonne. The customs house does not
hold traded goods — they are minted elsewhere.

## THE INFINITE BORDER — found at `0x1561C0`

`0x1561C0` (10885 b) is the **construction supply planner**. Its prologue
resolves twelve resources by name through `ResourceGet` (`0x2AA830`):

    gravel  bricks  steel  boards  prefabpanels  concrete
    cement  asphalt  mcomponents  ecomponents  bitumen  workers

which is exactly the construction cost set, and is what identifies it. Six times
inside, this shape appears (`0x1566A7` shown):

```
001566A7  cmp     dword ptr [rax + 0x360], 0x14   ; BUILDINGTYPE_CUSTOMHOUSE
001566AE  jne     0x1401566b9                     ; anything else computes it
001566B0  movaps  xmm6, xmm9                      ; a customs house uses a constant
001566B4  jmp     0x14015679d
```

`xmm9` is loaded once, at the top of the function:

```
00156447  F3 44 0F 10 0D 68 49 7B 00
          movss xmm9, dword ptr [rip + 0x7B4968]   -> .rdata:0x90ADB8 = 250.0f
```

**Every customs house reports 250 t of every construction material, forever, to
every construction office.** It is not a stock that depletes; it is a literal.

Only that one instruction references `0x90ADB8` in the surrounding 16 KB, so
rewriting its four displacement bytes to point at plugin-owned memory changes
this call site and nothing else — no inline hook, no trampoline, no hook chain.
That is what `mod/plugins/customs_stock` does.

## The customs house holds nothing, ever

The slot dump (probe v0.3, resource names read from the record each slot points
at) gives the complete trade catalogue of a road customs house — 15 storages,
one per transport class:

| class | resources |
|---|---|
| 2 | gravel, rawgravel, coal, rawcoal, iron, rawiron, bauxite, rawbauxite, uranium, waste_gravel, waste_steel, waste_aluminium |
| 1 | steel, aluminium, prefabpanels, bricks, wood, boards, yellowcake, waste_plastic |
| 0 | plants, chemicals, fabric, alcohol, food, clothes, ecomponents, mcomponents, plastics, eletronics, explosives |
| 3 | oil, bitumen, fuel, fertiliser_liquid |
| 4 | cement, alumina |
| 5 | meat |
| 6 | livestock |
| 15, 16 | water, usagewater |
| 17 (×5) | waste_gravel, waste_steel, waste_aluminium, waste_plastic, waste_bio, fertiliser, waste_burnable, waste_toxic, waste_other, waste_ash |
| 10 | vehicles |

**Every slot reads content 0.000 and limit 0.000, and storage capacity is
1.000 t.** Nothing is ever stocked there.

Note what is *absent*: **asphalt and concrete have no slot at all**, yet a truck
was observed loading 9.8 t of asphalt at a customs house. Goods that cannot be
stored are still sold, which is decisive — the customs house is a source, not a
store, and the goods are minted at load time.

## Confirmed at runtime (probe v0.4)

| Field | Meaning | Evidence |
|---|---|---|
| `slot+0x08` | content, float | observed moving: `alcohol 0 -> 0.695`, `oil 1.351 -> 3.429` |
| `storage+0x80` | storage total content | moves in lockstep with its slots, clamps at the `+0x8C` capacity |
| `building+0x0A58` | two per-station busy flags (word) | `0 -> 1 -> 257 (0x0101) -> 0` around each load |
| `building+0x0A78`, `+0x0A80` | pointers to the vehicle docked at station 0 / 1 | set on dock, cleared on departure; high dword `474` = `0x1DA`, a live heap address |
| `building+0x1158` | waste-handling flags (word) | written by `0x190090`, which loops storages of class 17 and **skips customs houses** |
| `building+0xFC0`, `+0x1268` | tick accumulators | move every report |

**But the purchases still do not appear.** Two trucks bought 10 t of gravel and
8.9 t of asphalt; neither the gravel nor the asphalt slot moved at all. The only
slot movement was sub-tonne dribbles of alcohol, food and oil on the *other*
customs house — unrelated traffic through a 1 t buffer.

So the goods a purchasing vehicle receives never pass through the customs
house's storages. Combined with asphalt having no slot at all, the conclusion is
firm: **the customs house is not where bought goods come from.**

## The reframing: the border is not a quantity

A second special-case was found in `wrsr.building.assignment_target_select`
(`0x2B78B0`, an RML-resolved symbol — its entry fingerprint matches RML's
report exactly). At `0x2B858B`:

```
002B858B  cmp    dword ptr [rax + 0x360], 0x14        ; target is a customs house?
002B8592  jne    normal_path
002B8594  mov    rax, [r15 + 0x10]
002B8598  mov    dword ptr [rax + 4], r13d            ; r13d = 0  (xor r13d,r13d)
002B85A0  mov    dword ptr [rax + 0xCC], 0x3F7D70A4   ; = 0.99f
002B85AA  jmp    done
002B85AC  ; every other building computes both from locals at [rbp-0x68]/[rbp-0x64]
```

So in the vehicle assignment path a customs house is forced to `0.0` and `0.99`
— a near-perfect score, always. Same shape as the construction planner forcing
`250.0`.

**Taken with everything else, the conclusion is that the game does not model
border supply as a quantity at all.** There is no stock, no limit and no
capacity anywhere: the customs house holds nothing (all slots 0.000, capacity
1 t), goods that cannot even be stored there are still sold, and every path that
asks "can this building supply X?" answers with a hardcoded constant rather than
a number that could run down.

### What that means for finite trade

Capping an existing number cannot work, because there is no such number. Finite
stock has to be **added**:

1. the plugin keeps its own per-resource stock;
2. when stock for a resource is exhausted, make the customs house score as
   unavailable for it — patching exactly the constants above, which is the
   lever the game already provides;
3. decrement the stock when a request is granted.

Step 3 still needs the transfer point, or an approximation from the requested
amount, which may be reachable in the assignment record at `[r15+0x10]`.

This also predicts the observed behaviour that a construction office still drew
7.8 t of gravel while `customs_stock` was set to 1 t: the constant is a
selection score, not a cap, so lowering it changes *whether* the border is
chosen, never *how much* is taken.

## Tested and rejected

**`customs_stock` does not work and should be deleted.** With the border
constant set to `0.001 t`, a construction office still drew 7.8 t of gravel from
a customs house. So `250.0` at `0x156447` governs neither the quantity taken nor
whether the border is chosen.

The disassembly explains it: on the non-customs path `0x1561C0` calls
**`0x424430`** — the real "how much can this building supply" routine — and the
customs branch *skips that call entirely*. Patching the constant changes a value
on the branch that bypasses the computation.

`0x424430` (3640 b) is therefore the function that actually answers the supply
question, and is a better target than anything reached through the type check.

## Every per-vehicle symbol is already hooked

Both attempts to hook a vehicle function were refused by the `expect` check,
because two installed mods own them. **Read RML's compatibility report by SYMBOL
NAME, not by RVA** — the resolved symbols are listed separately from raw
addresses, which is how this was missed the first time:

```
wrsr.vehicle.task_advance        | SHARED | helicopter_distribution_office, RollingStockRoadTransport
wrsr.vehicle.compatibility_check | SHARED | helicopter_distribution_office, RollingStockRoadTransport
```

Any future vehicle hook must either pick an address neither mod uses, or those
mods must be disabled for the test.

## The plugin .ini is never read

`TsmHost::configInt` resolves its file name against `TsmHost::baseDir`, and
under Republic Mod Loader's compatibility host that is neither `rml\plugins`
nor `<workshop item>\plugins` — copies were placed in both and neither was
found. Proven by `[MAP]` running while `[FIND]` did not: the only difference is
a setting that exists in the ini but defaults to 0 in code.

**Only the code defaults have ever applied.** Anything a probe needs to do must
be a default, not an ini value, until baseDir is identified.

## The financial ledger at game+0xC608

The inventory found an object whose fields are category *names*, not resources:

```
[MAP] game+0x0C608 inline span=3328  res: audio@+0x48, roads@+0x1E8,
      construction@+0x250, importexport@+0x2B8, various@+0x2C0, vehicles@+0x320
```

`importexport` is a spending category, so a border purchase — if it is booked
anywhere — is booked here. This is the closest thing to a transaction record
found so far, and unlike everything reached through the customs house it sits on
a **global**, so its offset is stable.

Also of note: `game+0x1140`/`+0x1148` hold a table of resource-record pointers
at 8-byte stride (`workers`, `gravel`, `asphalt`, `concrete`, … through
`waste_mixed`, `service_material`) — the engine's resource registry.

## The game object is a global

The probe reported it at `00007FF64D914F10` = **`exe + 0x9D4F10`**, inside
`.data`. So offsets into it are stable across runs and worth recording once
found — unlike the heap addresses everything else has produced.

Its vector at `+0x11728` holds **1 record of 1024 bytes**, with no storage
vector and no resource pointers. It is not the vehicle list.

## FOUND — money, and the trade gate

Money was located by telling the probe a balance known from outside the process
and scanning `.data` around the game global. It is a **`double`**:

| Global | Meaning |
|---|---|
| `game+0x578` | int flag read just before the balance comparison |
| `game+0x580` | **USD balance**, double |
| `game+0x588` | **RUB balance**, double — absolute `exe+0x9D5498` |

Only 32 instructions in the whole executable reference the RUB global, and one
of the functions containing them also tests for `BUILDINGTYPE_CUSTOMHOUSE`:

### `0x1AAD70` — `bool CanTrade(game, a2, building, flag)`

```
001AADE1  cmp    [rax+0x360], 0x14      ; source is a customs house?
001AADFC  call   0x3E3F40               ; -> bool, fills a local
001AAE31  cmp    [rax+0x360], 0x14      ; target is a customs house?
001AAE45  call   0x3F7CE0               ; compute cost
001AAE5C  call   0x3F79E0               ; compute cost (game object)
001AAE86  movsd  xmm3, [game+0x588]     ; RUB balance
001AAE8E  movsd  xmm2, [game+0x580]     ; USD balance
001AAEBE  comisd xmm3, xmm0             ; balance >= cost?
001AAEC2  jb     fail
...
001AB264  call   0x1AAAA0               ; accept -> PERFORM THE TRANSFER
001AB26B  xor    al, al                 ; refuse -> return false
```

**This is the affordability gate for a customs-house trade, and it is where
finite stock belongs.** Returning false is the path the game already takes when
the player cannot afford something, so a refused purchase needs no new failure
handling anywhere.

`0x1AAAA0` is the transfer itself, called only on the accept path.

Hook site: 20 bytes of home-space spill (`4C 89 4C 24 20 …`), no rip-relative,
ends on an instruction boundary at `0x1AAD84`. Four register arguments, so a C
detour can forward them safely. Not in RML's taken list.

### Design

1. hook `0x1AAD70`;
2. identify the resource and amount from the arguments (what the observe-only
   build is for);
3. refuse when the mod's own stock for that resource is exhausted;
4. decrement stock when the original returns true.

## THE ANSWER: there is no purchase transaction

Sampling the ruble balance across a truckload settled eighteen sessions of dead
ends. Drain rate over one session, in two-second buckets:

```
 t(s)    RUB/sec  samples
    0      -7.26       28   ##                 <- baseline (wages, upkeep)
    2     -13.77       47   ####
    4    -186.70      110   ############################   <- the purchase
    6     -73.61       73   ########################
    8      -8.19       30   ##                 <- back to baseline
```

**~490 RUB billed continuously over about four seconds, with no discrete jump
anywhere in 370 samples** (max single delta -6.83).

**WRSR does not have a border purchase event.** The border bills per unit as
goods flow. That single fact explains everything that failed:

- no stock or limit field exists, because there is no order to limit;
- the customs house never accumulates goods, because they stream through;
- `0x1AAD70` (the affordability gate) and `0x3F79E0` (the pricing routine) never
  fire on a truck load, because neither is on a per-unit flow path;
- the storages never move, because the goods are not stored.

### `0x68B330` — the border trade processor

Four of the nine ruble writes are here, each with the same shape:

```
00692E78  movsd [USD], xmm1            ; USD adjusted
00692E80  cmp   dword [r12+0x9EC], 4   ; the customs house border field
00692E89  jne   skip
00692E96  subsd xmm1, xmm0
00692E9A  movsd [RUB], xmm1            ; RUB adjusted
```

Mixing `addsd` and `subsd` across the four sites — buy and sell, both currencies
— all gated on `building+0x9EC`. This function also holds the **most `+0x9EC`
references in the executable (46)** and **21 customs-house type checks**.

Hookable: 19-byte prologue ending at `push rbp`, four register arguments and
**no stack arguments** (verified — no early reads of `[rsp+0x28..]`), so a C
detour forwards it safely. Ten direct callers.

### Confirmed in game: purchase billing is identifiable by argument

Hooking `0x68B330` and logging every call that moved money gave 2181 calls
across one session with a truck load. Grouping by the first argument:

| `a` pointer | calls | behaviour |
|---|---|---|
| `…599ED790` | 1259 | upkeep, ~0.075 RUB per call |
| `…599EBCB0` | 787 | upkeep, ~0.075 RUB per call |
| `…29358370` | **135** | **2–5.5 RUB per call, only during the truck load** |

and separately, *calls moving more than 0.5 RUB: **135***. An exact match.

**So `0x68B330(a, …)` is called per billed entity, and border purchases arrive on
their own object.** Signature confirmed as four register arguments with `b` and
`c` null in every observed call; `flag` was always 0; `ret` was 0 or 1.

The billing object is not a building (`+0x318` does not resolve to a type
descriptor) and carried no resource pointer in its first `0x600` bytes.

### What finite stock now means

Not capping an order, and not blocking a transaction. **Throttling a flow**:
while the mod's stock for a resource is positive let the processor run; when it
is exhausted, stop it for that building. The truck simply stops filling, which
is behaviour the game already produces when a source runs dry.

## Next step

Identify the resource from the billing object. The probe is staged to dump it
(`[BILL]` lines: a `0x2000`-byte resource-pointer scan, a storage-vector probe,
and a raw `0x140` window) the first few times a purchase bills.

- **If a resource is reachable** → per-resource stock: skip the billing call for
  a resource whose stock is dry, and the flow stops.
- **If not** → an all-or-nothing border throttle is still available, which is a
  usable survival mechanic (the border supplies only N tonnes per month total),
  just coarser.

## SOLVED: resource prices, and how to control them

Confirmed by matching a number read off the screen. Dumping hazardous waste took
its displayed price from **-793.79 to -409.61**; the probe recorded:

```
waste_toxic  +0x058   -957.600  -> -494.115
waste_toxic  +0x05C   -718.200  -> -370.605
waste_toxic  +0x060  -1058.400  -> -546.127
waste_toxic  +0x064   -793.800  -> -409.616     <- the displayed price
waste_toxic  +0x078      99.178 ->   99.433     <- base price, barely moves
```

### The price block in a resource record

| Offset | Meaning |
|---|---|
| `+0x58` | live price, base pair, currency A |
| `+0x5C` | `= +0x58 x 0.75` — currency B |
| `+0x60` | `= +0x58 x 1.105` — other side of the spread |
| `+0x64` | `= +0x5C x 1.105` — **what the customs house UI shows** |
| `+0x78`, `+0x7C`, `+0x80`, `+0x84` | base prices; drift slowly, survive recomputation |
| `+0xA4`, `+0xC4` | multipliers, observed sitting at exactly `1.000` |

Two currencies (x0.75) and two sides of the spread (x1.105), all derived from a
base. The engine recomputes the live block from production chains, so a written
value must be re-written each tick to stay pinned.

### Getting the record list

Do NOT hunt for a registry in the game object — that produced four resources.
**Walk the customs house's own storage slots**: every slot holds a resource
record pointer, and the building covers the whole tradeable catalogue. That
yields **48 resources**, by name, in one pass.

### Why this replaces the blocking approach

Price control is a float write into a data record: no hook, no trampoline, no
stack frame to preserve, nothing that can corrupt a 55 KB function. It also
produces a better mechanic — the border never refuses, it just becomes
ruinously expensive when stock is gone, so the player chooses between paying and
scavenging.

## Still unlocated: the general cargo path

A vehicle loading a non-construction resource (the `fertiliser_liquid` test) does
not go through `0x1561C0`, and the customs house storages do not move. Ruled out
so far: `0x185100` (immigration), `0x1854E0` (tick), the storage records.

`cmp [reg+0x360], 0x14` occurs at **146 sites**; `tools/customs_sites.py`
enumerates them and flags the ones that shortcut to a constant. Functions that
also touch `building+0x9EC` (the border field) rank: `0x68B330` (55 KB, 46 refs —
probably UI), `0x173320` (6 KB, 28 refs), `0x430FC0` (36 KB, 15 refs),
`0x718FC0` (5 KB, 14 refs). `0x173320` was inspected and shows no resource-name
lookups, so it is probably not it.

## How buying actually works — and what it changes

Confirmed by playing, not by disassembly: **there is no standing order at the
customs house.** A purchase is a transaction, either driven by a consuming
building (auto-purchase against a threshold, or a manual confirm) or by a
vehicle loading at the customs house, capped by vehicle capacity, with the money
taken as it loads.

That kills the original design — there is no per-resource limit field to clamp —
and replaces it with a better one. If the customs house is an infinite *source*,
finite stock means giving it real, finite content per resource and restocking
monthly. The game's own loading logic then refuses to overdraw it for free, and
no vehicle, route or delivery behaviour has to change.

### Building-struct offsets that move on a purchase

From a run with two rail loads of ~100 t of `fertiliser_liquid`, 30 s apart.
Values were lost to a formatting bug (see below) but the offsets are good:

- `+0xFC0`, `+0x1268` — move every report. Timers; ignore.
- `+0xBC0` — moves in bursts of up to 6 consecutive dwords, and is itself a
  vector in the scan. Six dwords is begin/end/capacity all changing, i.e. the
  vector resizing — most likely the vehicle queue at the station.
- `+0x1F68`, `+0x1F88`–`+0x1F94` — event-driven, one customs house only.
- `+0x20D0`–`+0x20E4` — bursts of up to 9 consecutive dwords. Another vector
  plus counters; worth attention.

None of these is a tonnage, because **the storage records are a separate heap
allocation** — diffing the building struct alone can never see one. That was the
first probe's mistake; `StorageChanges()` now follows `+0x970`.

## Host logging gotcha

`TsmHost::log` under Republic Mod Loader is not printf. `%s`, `%p`, `%llu` and
`%X` work; **width-modified string conversions like `%-24s` do not** — the
literal text is emitted and no argument is consumed, so every conversion after
it reads the wrong stack slot and prints garbage. Format into a local buffer and
pass a single `%s`.

## Method

`tools/pe.py` reads the PE, the section table and the `.pdata` runtime-function
table. Chaining contiguous `.pdata` entries recovers whole functions (a single
entry is only a fragment). With capstone on top, scanning `.text` for
`cmp [reg+0x360], imm` recovers the entire building-type dispatch table — which
is the fastest way into any per-building behaviour in this game.
