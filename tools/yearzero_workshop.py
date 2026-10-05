"""Republic in Ruins on the Steam Workshop: four items instead of one per kit and per vehicle.

    python tools/yearzero_workshop.py        # -> build/workshop/<item>/, ready for build.ps1 -Install

  republic_in_ruins   the plugins (build.ps1 adds the DLLs, their inis and rml.json)  WORKSHOP_ITEMTYPE_SCRIPT
  buildings           every building of the eight kits, one shared material folder    WORKSHOP_ITEMTYPE_BUILDING
  vehicles            all nineteen vehicles                                           WORKSHOP_ITEMTYPE_VEHICLE
  words               the English text overlay                                        WORKSHOP_ITEMTYPE_TEXT

The kits and vehicles stay separate in mod/ (each generator writes its own); this only packs
them. A building or vehicle is registered in game as '<item id>/<object>', so packing them
together changes those idents - the Korea Year Zero converter reads them from the installed
items (tools/yearzero.py wip_index), so install before converting.

Publishing (the game's uploader: main menu -> Workshop): create each item in the game first to
get its Steam id, put the ids in ITEMS, run build.ps1 -Install, then upload. $VISIBILITY is
the game's, not Steam's: 0 unpublished, 1 friends only, 2 PUBLIC.
"""
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'build', 'workshop')
PREVIEWS = os.path.join(ROOT, 'build', 'yearzero_previews')      # made by tools/yearzero_readme_images.py
OWNER = 76561198165729857
VISIBILITY = 0                  # unpublished; switch to public on Steam once the items are checked
REPO = 'https://github.com/aislanfoina/wrsr_yearzero'
RML = 'https://steamcommunity.com/sharedfiles/filedetails/?id=3787969749'
BATON = 'https://steamcommunity.com/sharedfiles/filedetails/?id=3753525456'

KITS = ['madmax_kit', 'fallout_kit', 'survivors_kit', 'trade_post', 'goods_post', 'junk_post', 'scrap_center', 'scrap_dock']
VEHICLES = ['interceptor', 'nux', 'buzzard', 'warrig', 'raider', 'warbus', 'geiger', 'quarantine',
            'warloco', 'shunter', 'warflat', 'warhopper', 'wartank', 'warbox', 'prisoncar',
            'rustbarge', 'guzzotanker', 'raidership', 'skimmer']

# key: (item id, item type, name, sources). Local development ids until the items exist on Steam.
ITEMS = {
    'republic_in_ruins': (9000090, 'WORKSHOP_ITEMTYPE_SCRIPT', 'Republic in Ruins [1.1.1.9]', ['mod/packages/republic_in_ruins']),
    'buildings': (9000050, 'WORKSHOP_ITEMTYPE_BUILDING', 'Republic in Ruins: Buildings', ['mod/buildings/' + k for k in KITS]),
    'vehicles': (9000051, 'WORKSHOP_ITEMTYPE_VEHICLE', 'Republic in Ruins: Vehicles', ['mod/vehicles/' + v for v in VEHICLES]),
    'words': (9000005, 'WORKSHOP_ITEMTYPE_TEXT', 'Republic in Ruins: Words', ['mod/text/survivors_text']),
}

FOOTER = '''[h2]LICENCE AND CREDITS[/h2]
GPL-3.0, source code on GitHub: [url=%(repo)s]%(repo)s[/url]. The plugins build against TesmioLoader by MaxLegend and run on [url=%(rml)s]Republic Mod Loader[/url] by UltimateUniverse. The vehicles are the game's own models with welded-on scrap; the look is inspired by the Mad Max films, and this mod is not affiliated with their makers.

Workers & Resources: Soviet Republic is (c) 3Division. This is an independent fan-made mod, not affiliated with or endorsed by 3Division or Hooded Horse.''' % {'repo': REPO, 'rml': RML}

PACKAGE = '''[h1]COMRADE, THE REPUBLIC IS IN RUINS.[/h1]
The five-year plan has been interrupted by a nuclear exchange. The Central Committee is unavailable for comment. The Ministry of Construction is a crater.

Your citizens are few, contaminated and hungry. The border is a rumour. The only industry left is the one you can dig out of the rubble.

[b]DO NOT DESPAIR, COMRADE. THE PLAN HAS BEEN AMENDED.[/b]

[b]Republic in Ruins[/b] turns Workers & Resources into a post-apocalyptic survival city builder: salvage the ruins, trade for scraps, take in survivors, keep the radiation off your people and rebuild the republic from what is left.

[h2]WHAT SURVIVED[/h2]
[list]
[*][b]Contamination instead of crime.[/b] Three strike zones decay over the years; citizens in buildings inside the field take up a dose, and a high dose costs them their health. The police are now the Decontamination Task Force, the court is the Radiology Board, the prison is the Recovery Center, patrol cars carry Geiger counters. Clearing the ruins lowers the field.
[*][b]Survivors instead of immigration.[/b] Nobody can be bought across the border any more. Survivors wander in like tourists; the ones you shelter and look after stay. A distress broadcast brings a trickle of newcomers. Mercenaries still come, but they want food, meat, clothes and alcohol from a Mercenary Camp, not money.
[*][b]Survival Trade Posts.[/b] Scarce goods appear at a trade post at their own pace and your trucks buy them there, one load at a time. When the shelves are empty, they are empty.
[*][b]Blueprints from the scrapyard.[/b] Send a vehicle to the Scrap Center (or a ship to the Ship Breakers) and your engineers learn to build it: take apart what you find, build what you learn.
[*][b]Salvage.[/b] Twelve pieces of wasteland decoration - scrap walls, watchtowers, shanties, wreck yards, fuel depots, a skull gate - and ruins that give construction waste and scrap when your salvage crews tear them down.
[*][b]Nineteen vehicles[/b] welded together from what was left: road raiders, a war rig, rail war trains and river ships, each in wasteland, war-boy and black paint.
[/list]

[h2]HOW TO SURVIVE[/h2]
[olist]
[*]Subscribe to this item and the Required Items on this page (the buildings, the vehicles, the words), and to [url=%(rml)s]Republic Mod Loader[/url].
[*]Run Republic Mod Loader, enable the Republic in Ruins items and their plugins (fallout, scrap_center, survivors, trade_post), and launch.
[*]Contamination needs [b]Crime & justice: Enabled[/b]; salvage needs [b]Waste management: Waste + Demolition[/b].
[/olist]
Requires Workers & Resources: Soviet Republic [b]1.1.1.9[/b]: the plugins patch this exact build.

[h2]THE MAP[/h2]
The mod was made for [b]Korea Year Zero[/b], a post-strike start converted from BATON's [url=%(baton)s]North Korea map[/url]: craters, ruins where the towns stood, a salvage kit by the roads and a scenario with no immigrant or vehicle purchases. The converted map is not on the Workshop, because it is built from BATON's work; the converter is on GitHub for anyone who owns their map. The contamination zones sit where that map's strikes fell.

[h2]STATUS[/h2]
Early access. Everything loads in the game and the Korea Year Zero start has been played in short sessions; nobody has rebuilt a republic with it yet. Reports are welcome, especially from comrades who survived the first winter.

[h2]REPORTING A PROBLEM[/h2]
Tell us what happened, what you were doing, and attach the Republic Mod Loader log.

''' % {'rml': RML, 'baton': BATON} + FOOTER + '''

[b]Dig. Trade. Shelter. Rebuild. The Republic is not dead, Comrade. It is merely resting in pieces.[/b]'''

BUILDINGS = '''[h1]COMRADE, REBUILD WITH WHAT IS LEFT.[/h1]
Every building of [b]Republic in Ruins[/b] in one item:
[list]
[*][b]Wasteland kit[/b] (twelve decorations, placeable anywhere): scrap wall, wall tower, watchtower, shanty cluster, fuel depot, wreck yard, ruined block, road wreck, skull totem, junk windpump, tyre barricade, skull gate. Torn down by a salvage office, they give construction waste and scrap.
[*][b]Trade[/b]: the Survival Trade Post, the Survival Goods Post and the Junkyard Trade Post.
[*][b]Salvage[/b]: the Scrap Center (vehicles in, blueprints out) and the Ship Breakers.
[*][b]Survivors[/b]: the Mercenary Camp, the Distress Beacon and the Survivor Shelter.
[*][b]Contamination[/b]: the Decontamination Task Force station, the Radiology Board and the Recovery Center.
[/list]
They work as ordinary buildings on their own; their wasteland jobs need the Republic in Ruins plugins. See that item for how to play.

''' + FOOTER

VEHICLES_DESC = '''[h1]COMRADE, THE MOTOR POOL HAS BEEN IMPROVED.[/h1]
Nineteen vehicles of the Republic's own make, with scrap welded on and new paint in three schemes (wasteland rust, war-boy chalk, matte black):
[list]
[*][b]Road[/b]: Wasteland Interceptor, War Boy Coupe, Buzzard Spike Car, War Rig (with its tanker), Raider Truck, Wasteland War Bus, Geiger Patrol, Quarantine Bus.
[*][b]Rail[/b]: Iron Hog Locomotive, Scrap Shunter, Battle Flatcar, Armoured Hopper, Guzzoline Tank Car, War Boy Boxcar, Prison Car.
[*][b]Water[/b]: Rust Barge, Guzzoline Tanker, Raider Freighter, Wasteland Skimmer.
[/list]
Each keeps its base vehicle's job, so they work in any republic. With the Republic in Ruins plugins, a Scrap Center teaches you to build them from the wrecks you find.

''' + FOOTER

WORDS = '''[h1]COMRADE, MIND YOUR LANGUAGE.[/h1]
The game's English text, re-themed for the wasteland: tourists are survivors, foreign workers are mercenaries, tourism research is the distress call; crime is contamination, the police are the Decontamination Task Force, the court is the Radiology Board, the prison is the Recovery Center, crimes are exposure and radiation sickness. About 170 lines changed; everything else is the game's own text. English only.

Part of [b]Republic in Ruins[/b]: it goes with that item's plugins, which turn those mechanics into the wasteland ones.

''' + FOOTER

DESCS = {'republic_in_ruins': PACKAGE, 'buildings': BUILDINGS, 'vehicles': VEHICLES_DESC, 'words': WORDS}
# Required Items on Steam: item -> the items (keys here, or Steam ids) a subscriber also needs
REQUIRED = {'republic_in_ruins': ['buildings', 'vehicles', 'words', 3787969749]}


def workshop_items():
    """The items as tools/workshop_upload.py reads them: key, Steam id, game item type, title,
    store page text, the game's visibility value and Required Items (Steam ids)."""
    return [{'key': k, 'id': v[0], 'type': v[1], 'title': v[2], 'description': DESCS[k], 'visibility': VISIBILITY,
             'required': [ITEMS[r][0] if r in ITEMS else r for r in REQUIRED.get(k, [])]} for k, v in ITEMS.items()]


def objects(cfg):
    out = []
    for line in open(cfg, encoding='utf-8', errors='replace'):
        t = line.split()
        if len(t) >= 2 and t[0] in ('$OBJECT_BUILDING', '$OBJECT_VEHICLE'):
            out.append('%s %s' % (t[0], t[1]))
    return out


def config(key, objs):
    item, typ, name, _src = ITEMS[key]
    desc = DESCS[key]
    assert len(desc) < 8000, '%s: Steam descriptions stop at 8000 characters (%d)' % (key, len(desc))
    assert '"' not in desc, '%s: no double quotes inside $ITEM_DESC' % key
    lines = ['$ITEM_ID %d' % item, '', '$OWNER_ID %d' % OWNER, '', '$ITEM_TYPE %s' % typ, '', '$VISIBILITY %d' % VISIBILITY, '']
    lines += objs + ([''] if objs else [])
    lines += ['$ITEM_NAME "%s"' % name, '', '$ITEM_DESC "%s"' % desc.replace('\n', '\r\n'), '', '$END', '']
    return '\r\n'.join(lines)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for key, (item, typ, name, sources) in ITEMS.items():
        dst = os.path.join(OUT, key)
        os.makedirs(dst)
        objs = []
        for src in sources:
            s = os.path.join(ROOT, src)
            objs += objects(os.path.join(s, 'workshopconfig.ini'))
            for entry in os.listdir(s):
                if entry in ('workshopconfig.ini', 'previewimage.png'):
                    continue
                p = os.path.join(s, entry)
                if os.path.isdir(p):
                    # the kits share material/: the same texture names hold the same pixels in every kit
                    shutil.copytree(p, os.path.join(dst, entry), dirs_exist_ok=True)
                else:
                    shutil.copy2(p, os.path.join(dst, entry))
        dup = sorted({o for o in objs if objs.count(o) > 1})
        assert not dup, '%s: objects in two sources: %s' % (key, dup)
        open(os.path.join(dst, 'workshopconfig.ini'), 'w', encoding='utf-8', newline='').write(config(key, objs))
        # the README renders' crops (yearzero_readme_images.py), else the item's own, else the package's
        for preview in (os.path.join(PREVIEWS, key + '.png'), os.path.join(ROOT, sources[0], 'previewimage.png'),
                        os.path.join(ROOT, 'mod', 'packages', 'republic_in_ruins', 'previewimage.png')):
            if os.path.exists(preview):
                shutil.copy2(preview, os.path.join(dst, 'previewimage.png'))
                break
        size = sum(os.path.getsize(os.path.join(b, f)) for b, _d, fs in os.walk(dst) for f in fs)
        print('%-18s %d  %-30s %3d objects  %6.1f MB  %4d chars' % (key, item, name, len(objs), size / 1e6, len(DESCS[key])))
    # the source configs of the two items that keep their folders get the same pages
    for key, rel in (('republic_in_ruins', 'mod/packages/republic_in_ruins'), ('words', 'mod/text/survivors_text')):
        open(os.path.join(ROOT, rel, 'workshopconfig.ini'), 'w', encoding='utf-8', newline='').write(config(key, []))


if __name__ == '__main__':
    main()
