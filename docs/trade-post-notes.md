# Survival Trade Post - design notes

These notes used to live as `;` comments inside `building.ini`. **They cannot go
back there.**

## Why: building.ini has no comment syntax

WRSR's building parser scans the whole file for `$DIRECTIVE` tokens wherever
they appear. It does not recognise `;`, `#`, `//` or anything else as a comment,
and it does not require a directive to start the line. Prose containing a `$`
word is therefore executed.

Proof, from the game's own `log.html`:

    ResourceGet - not found plus
    ResourceGet - not found lacks

against these two comment lines in the old file:

    ;   restock rule   $PRODUCTION plus $WORKERS_NEEDED - so many workers make so
    ; $TYPE_FACTORY with a $PRODUCTION lacks one: 0 of 345. The salvage handover is

`$PRODUCTION plus` looked up a resource called "plus", got null, and the build
menu dereferenced it the instant the item was moused over. The building loaded
fine; only hovering it touched the bad pointer.

Corroborating: **0 of 798** `building.ini` files installed on this machine - 488
base game, 310 Workshop - contain a single `;` line. Not one. The convention is
not stylistic; the format has no comments.

## The precise rule

The parser splits on whitespace and treats **any token beginning with `$` as a
directive, wherever in the file it appears**. There is no line-level comment
syntax; `;` does nothing.

That is why `; $PRODUCTION plus` fired: the `;` is its own token, and
`$PRODUCTION` is the next one, so it parsed as a directive with the argument
"plus".

Vanilla does annotate its files - 34 base-game `building.ini` files carry `//`
comments and 74 use `--` - but always with the marker **glued directly to the
`$`**, never separated by a space:

    //$WORKERS_NEEDED 13                 disabled, 152 lines like this in vanilla
    --$CONSUMPTION_PER_SECOND eletric 10.55
    // Live connections                  prose, contains no $ token

Across all 488 base-game building inis there is **not one** comment line with a
space before a `$`. That is the whole convention.

## What is safe

- Prose comments are fine, as long as no whitespace-delimited word starts with
  `$`. Write `PRODUCTION` or `"the production directive"`, not `$PRODUCTION`.
- To disable a directive, glue the marker to it: `//$PRODUCTION gravel 0.60`.
- Anything else that must mention a directive by name belongs in this file.
- Symptom to recognise: `ResourceGet - not found <an English word>` in
  `log.html` means the parser is reading prose. Search the ini for that word.

## Original notes, preserved

 A trade post built as an ordinary FACTORY rather than a customs house.

 The customs house turned out to be a black box: goods are minted from nothing,
 never appear in any storage, and are billed continuously by a function that
 cannot be safely hooked. Four separate attempts to measure how much was bought
 failed because of it.

 A factory has none of that opacity. Goods really sit in its storage, the
 vanilla UI shows them, and the amount goes DOWN when a truck loads - which is
 the signal the customs house never gave us.

 So the whole mechanic falls out of vanilla data:

   restock rule   $PRODUCTION plus $WORKERS_NEEDED - so many workers make so
                  many tonnes a day, exactly like any other factory
   stock          the real storage contents, visible in the building window
   runs out       when the storage is empty there is nothing to load

 The only thing a plugin has to add is that the goods must be PAID FOR on the
 way out, instead of being free like a normal factory's output.
 Trade is a few people negotiating, not a production line.
 THE RESTOCK RULE.

 The goods arrive from a settlement you have made contact with, bought with
 salvage rather than manufactured. Output is deliberately slow. Everything
 here is a tonne-per-day figure and is the main balance lever of the whole mod:
 too generous and scavenging is pointless, too mean and the republic starves.
 A $TYPE_FACTORY MUST declare a $CONSUMPTION. Checked against every building
 installed here - 310 Workshop items plus the whole base game - and not one
 $TYPE_FACTORY with a $PRODUCTION lacks one: 0 of 345. The salvage handover is
 the trade fiction (you pay the settlement in scrap) and also what keeps the
 building structurally legal. It needs a matching import storage, exactly as
 brick_factory pairs $CONSUMPTION coal with $STORAGE_IMPORT_SPECIAL.
 A little power, so a trade post needs infrastructure to work.
 One storage per product, as the oil refinery does it. These capacities are the
 stock the post can hold - it fills up while you are not buying and drains when
 you are.
 NO $RESOURCE_VISUALIZATION HERE, DELIBERATELY.

 A bare "$RESOURCE_VISUALIZATION 0" used to sit above this line and it crashed
 the game the instant the item was moused over in the Workshop list. The
 directive is a HEADER, not a flag: every one of the 654 occurrences across the
 base game and all 310 installed Workshop items is followed by its own block -
     positon <x> <y> <z> / rotation / scale / numstepx / numstept
 - and the parser reads that block unconditionally. With nothing to read it
 walks into whatever follows, and the pile renderer dereferences the result.
 The donor zoll_sahy has no $RESOURCE_VISUALIZATION at all, which is why the
 customs house never hit this. Re-add it only WITH a full block.
 Two truck bays, unchanged from the donor so the geometry still matches the mesh.
 $TYPE_* MUST SIT HERE, after the storages and the vehicle stations, exactly
 where the donor zoll_sahy.ini put $TYPE_CUSTOMHOUSE.

 Declaring it earlier - immediately after the cost block, which reads far more
 naturally - crashed the game the moment the item was moused over in the
 Workshop list. Proven by bisection: an otherwise byte-identical file with
 $TYPE_FACTORY in this position works, and with it moved up seven lines it
 crashes. The directive order in this file is load-bearing; keep the donor's.
