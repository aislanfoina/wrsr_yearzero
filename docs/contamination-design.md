# Fallout instead of crime: the Contamination & Quarantine system

Design proposal, 2026-09-22. Replaces the vanilla "Crime & Justice" layer of
*Workers & Resources* with radiation contamination, on top of the Korea Year Zero
map. Everything below that is stated as a vanilla fact was checked against the
game files (buildings_types, sovietEnglish.btf, SOVIETInstructions.txt, exe strings).

## 1. The idea

The bombs did not only flatten three towns. They left three glowing zones, and
every truckload of rubble the survivors pull out of them is hot. People who live,
work or scavenge in the zones pick up a dose. A dose is invisible until somebody
measures it, and it spreads: through the salvage they carry home, through the
crops from a field in the fallout ring, through the newcomers who walk in from the
wastes. The republic answers with a chain that the vanilla game already simulates
under another name:

| Vanilla | Year Zero | What it is now |
|---|---|---|
| citizen crime level | **dose** | accumulated exposure, per citizen |
| minor / medium / serious crime | **exposure / radiation sickness / acute syndrome** | dose classes that raise a "case" |
| police station, police cars | **Decontamination Task Force (DTF)**, Geiger patrols | drives to the case, screens the household |
| courthouse, judges | **Radiology Board**, physicians | decides the quarantine length from the dose |
| prison, wardens, prison bus | **Recovery Center**, medics, convalescent crews | quarantine with a capacity, containment level and work crews |
| secret police | **Reunification Office** | keeps its loyalty-survey job (see section 5) |
| orphanage | **Children's shelter** | takes the children of quarantined parents, unchanged |
| criminality statistics | **contamination report** | the same graphs, renamed |

The point is not the names. The point is that the *sources* of the problem are
tied to the survival economy (the ruins are the ore, and the ore is hot), and that
the *cure* is the same buildings the player already needs to clean the map.

## 2. What the vanilla game gives us (verified)

- Each citizen has `fStatusCrime`, `fStatusHealth`, `fStatusHappiness` and the
  needs; the scripting VM exposes them read-only (`Person` struct). The game also
  keeps "Radiation statistics: maximum / average radiation" per republic and a
  per-building `fPollution_RadioactivityAroundBuildingCurrent`.
- Crime pipeline: crimes are generated in three classes (`Crime_mild`,
  `Crime_medium`, `Crime_serious`); a police car must first *come to the scene*
  (`Crime_police_not_come`), then *investigate* (`Crime_police_not_investigated`,
  "Collect crime evidence"); the court must *issue a verdict*
  (`Crime_court_no_verdict`, "Court overwhelmed", judges = professors); the prison
  holds convicts ("Serving a sentence", "Prison security", escapes when wardens are
  short, `$CITIZEN_ABLE_SERVE 3`, `$QUALITY_OF_LIVING 0.5`, food and meat demand),
  prisoners can be bussed to work, and there is an execution counter
  (`Crime_Executed_`). Unsolved cases raise the crime level of the whole building
  or area ("too many criminals living in this residential building or area").
- The map keeps a pollution grid in `pollution.bin`: 100 x 100 cells of 200 m,
  12 bytes per cell (three 32-bit values; column 1 is the pollution seen at a
  cement plant, column 0 is zero in every save on this machine and is the
  candidate for radioactivity, column 2 looks like bookkeeping).
- Sickness is its own system: water quality, epidemics
  (`GlobalEvent_StartEpidemy`), hospitals; sick workers do not work and have fewer
  children. Radiation already feeds into health in vanilla (nuclear waste).
- Demolition offices turn a building's construction materials into *construction
  waste*; the gravel recycling plant makes gravel from it, the steel recycling
  plant makes steel from scrap, the scrapping facility takes vehicles. Waste
  needs a destination (dump, storage) that the player sets.
- The game must be started with "Crime & Justice: Enabled" and "Waste
  management: Waste + Demolition" for any of this to exist.

## 3. Sources of dose

1. **Living in a zone.** The three craters carry a radiation field that falls off
   with distance and decays with a half-life of about eight game years. Every
   resident of a hut inside the field gains dose per day proportional to the
   field at the hut.
2. **Working in a zone.** Workers of a building inside the field gain dose during
   shifts (the salvage office, the crusher and the dump are the usual suspects,
   because the player will put them next to the ruins).
3. **Hot salvage.** A building that *stores* construction waste or scrap that came
   out of a zone radiates a halo until the material is processed. Dumps and the
   crusher yard become small zones of their own; the smelter and crusher outputs
   (gravel, steel) are clean. Process fast or store far away.
4. **Hot crops.** A field inside the fallout ring produces contaminated crops:
   everyone who eats from that harvest gains a small dose. Farms outside the ring
   are the incentive to spread out.
5. **Newcomers.** Survivors settling through the Screening Gate (the customs
   house, already re-themed by the survivors plugin) arrive with a random dose;
   a share of them are cases on arrival. The Distress Beacon brings people *and*
   contamination, so the DTF must cover the gate town.

Dose is written straight into the citizen's crime level. Vanilla crime growth
from unmet needs is overridden (the plugin sets the value, it does not add to it),
so a well-fed citizen far from the zones has a zero crime level and nothing happens
to them, exactly like a good republic in vanilla.

## 4. The response chain, with its twists

- **Cases.** When a citizen's dose crosses a class threshold a case is raised at
  their home, the vanilla "crime" with its scene and its class. Mild cases are
  cheap and quick; acute cases block the citizen from working immediately.
- **DTF sweep.** A Geiger patrol must reach the scene (vanilla "police did not
  come to crime scene" becomes "sweep never arrived") and screen the household
  ("collect evidence" becomes "take readings"). An unswept case keeps radiating:
  the vanilla area penalty applies, the whole hut's level climbs. A DTF station
  needs officers *and* educated staff; the small station is enough for one town.
- **Radiology Board.** Verdict = quarantine length by class. An overloaded board
  (too few physicians) drops cases: the citizen stays contaminated and keeps
  seeding the hut. Boards want professors, which makes the school chain matter
  early.
- **Recovery Center.** Capacity-limited quarantine. Medics are the wardens: too
  few and *containment* drops, and containment breaches are the vanilla escapes:
  the citizen walks home still hot and re-seeds the household. The center demands
  food and meat like a prison, and its **convalescent crews** are the prison work
  bus: quarantined citizens can be sent to work, and the twist is where. They are
  already irradiated, so the cynical move is to bus them to the hot jobs (dump,
  crusher, salvage office), keeping the clean population clean. That is a real
  Mad-Max choice: treat people as people, or as shielding.
- **Acute cases left untreated** collapse into vanilla sickness: health drops,
  the hospital chain takes over, and the death statistic is the one the game
  already shows. The vanilla execution counter is not used.
- **Children's shelter** and everything downstream (kids of quarantined parents,
  unemployment during quarantine, birth rate under sickness) is untouched vanilla.

## 5. Loyalty: the reunification layer

Loyalty stays a separate axis and keeps the vanilla machinery: the secret police
become the **Reunification Office**, whose black cars visit huts to learn each
household's loyalty, and the Distress Beacon (a real radio station) raises loyalty
while it broadcasts. Two links to contamination:

- A breach, a dropped case or an unswept scene in a hut lowers that hut's loyalty
  ("the committee failed us"); a completed case raises it. Contamination is the
  fastest way to lose the population's trust and the cheapest way to earn it.
- The scenario declares **reunification** when average loyalty passes a threshold
  with the zones below a set level: the North Koreans become united Koreans when
  the republic has both cleaned the ground and earned the people. That is the win
  condition of the map, with a research reward and a text card.

## 6. Cleanup: the ruins are the ore

The Mad-Max ruin pieces already placed in the craters get construction-material
costs (`$COST_RESOURCE_AUTO wall_concrete`, `wall_steel`, `ground_asphalt` at
sensible tonnages). Demolishing a ruin through the salvage office therefore
yields construction waste and scrap exactly like demolishing a vanilla building,
and the crusher and smelter turn it into gravel and steel. Each ruin removed from
a zone lowers that zone's field by a share, so the player cleans the map by
mining it. The hot-salvage halo (section 3.3) means the loop has a cost: the
player either accepts a dosed salvage crew, spreads the dumps out, or runs the
convalescent crews. Zones also decay on their own, slowly, so a player who ignores
them is not stuck, only poor and sick.

## 7. Implementation plan

Everything reuses the pipelines already in this playground (models, TEXT overlay,
Tesmio/RML plugin hooks on building ticks, the survivors plugin's SpawnPerson
hook, the map converter).

| Step | What | Confidence |
|---|---|---|
| A | Words: TEXT item rewriting the ~120 crime/police/court/prison strings (ids 2463, 8093-8096, 15010-15093, 28866-28897, 37800-37853, 54010-54052, 56100-56108, building names 6262-6269 / 9073-9077, vehicle names 3048, 3060, 5xxx) | certain |
| B | Buildings: DTF station (police type), Radiology Board (court type), Recovery Center (prison type), Screening Gate (customs skin) in the Mad-Max style; Geiger patrol car and quarantine bus as vehicle skins of a police car and a prison bus | certain, asset work |
| C | Radiation field: paint column 0 of `pollution.bin` around the craters in `tools/yearzero.py`; verify in-game that the game reads it as radioactivity and keeps it. Fallback: a plugin that writes each building's radioactivity field from its distance to the craters every tick | needs one in-game check |
| D | Dose engine: plugin hook after the building tick dispatcher (0x139A70) for LIVING and FACTORY buildings; iterate residents/workers and set `fStatusCrime` from dose. Person and building field offsets come from the scripting VM's accessor tables (opcodes 100 and 102), which is cleaner than guessing | medium; the offsets are the only unknown |
| E | Hot salvage halo: a storage/dump/crusher holding waste gets radioactivity proportional to stored tonnage times a "hot" flag set when the source building was inside a zone; v1 can simply treat any waste holder within 400 m of a crater as hot | medium |
| F | Screening Gate: in the survivors plugin's settle path, assign a random initial dose (10% cases) | easy |
| G | Cleanup: count live ruin fragments per zone each day and scale the field; give the ruin pieces material costs | easy |
| H | Scenario glue: objectives (first sweep, first quarantine, zone below 50%), the reunification win condition, a "hot summer" event using the epidemic trigger | easy |

Order: A+B first (they are visible immediately), C and D next (the mechanic),
then E-H. Steps C and D need the game to run, which is currently blocked by the
Steam sign-in on this PC.

## 8. Open choices for you

1. Keep the secret police as the loyalty tool (proposed) or fold surveys into the DTF?
2. Convalescent crews: allowed to work hot jobs (proposed) or only clean ones?
3. Zone decay: eight years half-life (proposed), or zones that never decay without cleanup?
4. Should dose also cut the birth rate directly, or only through vanilla sickness?
5. Executions: dropped (proposed) or kept as "written off" acute cases?
