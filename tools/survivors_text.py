"""Re-theme the game's own words: tourists are survivors, immigrants are
recruits, foreign workers are mercenaries, tourism research is the distress
call. Produces a WORKSHOP_ITEMTYPE_TEXT item (the type the UI-reskin mods use:
a media_soviet.zip overlaying files under media_soviet) carrying a modified
sovietEnglish.btf, and the same file for TesmioLoader's VFS.

    python tools/survivors_text.py
"""
import os
import shutil
import sys
import zipfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import btf  # noqa: E402
from fallout_text import FALLOUT  # noqa: E402

MEDIA = os.environ.get('WRSR_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\SovietRepublic').rstrip('/\\') + '/media_soviet/'
ROOT = os.path.dirname(TOOLS)
OUT = os.path.join(ROOT, 'mod', 'text', 'survivors_text')

REPLACE = {
    # tourists -> survivors
    37500: 'Survivors', 37611: 'Survivor', 37554: 'Refuge', 40119: 'Refuge',
    37550: 'Sheltered survivors', 37576: 'Survivors heading for the republic', 37577: 'Survivors who reached the republic',
    37578: 'Survivors who gave up on the way', 37579: 'Survivors who settled', 37580: 'Survivors who died',
    37581: 'Refuge score', 37582: 'Survivors from the East', 37583: 'Survivors from the West',
    37614: 'Survivor spend', 37633: 'Refuge income', 37555: 'Spending by survivors from the East', 37556: 'Spending by survivors from the West',
    37630: 'Few survivors: word of the refuge is poor', 37631: 'Few survivors due to the epidemic',
    37635: 'Research the distress call to reach survivors', 20104: 'Max. survivors',
    2373: 'Where should the survivors go?', 2387: 'You can only send survivors to transit platforms',
    # research
    11155: 'Distress Signal Study', 11156: 'Rig a transmitter from salvage. Our first step towards calling survivors in from the wastes.',
    11157: 'Fortified Shelters', 11158: 'Study how the old hotels were built, so our shelters can hold more people in something like comfort.',
    11159: 'Distress Call: Western Wastes', 11160: 'Broadcast toward the western wastes. Survivors out there will start heading for our border.',
    11161: 'Distress Call: Eastern Wastes', 11162: 'Broadcast toward the eastern wastes. Survivors out there will start heading for our border.',
    11163: 'Distress Broadcast (West)', 11164: 'Run the beacon day and night toward the west for a while. Twice the survivors answer while it lasts.',
    11165: 'Distress Broadcast (East)', 11166: 'Run the beacon day and night toward the east for a while. Twice the survivors answer while it lasts.',
    # foreign workers -> mercenaries
    57110: 'Mercenaries', 57111: 'Mercenaries from the West', 57112: 'Mercenaries from the East',
    # immigrants -> recruits (buying is blocked by the plugin; the words still show in statistics)
    1206: 'Recruits', 1660: 'Recruitment',
    2325: 'Recruit 10 survivors from the East', 2326: 'Recruit 10 survivors from the far wastes', 2327: 'Recruit 5 skilled survivors from the East',
    433: 'Auto-recruit survivors for rubles', 434: 'Auto-recruit survivors for dollars',
    37004: 'Nobody sells people in the wasteland. Survivors come on their own - shelter them and they stay.',
    37005: 'Nobody sells people in the wasteland. Survivors come on their own - shelter them and they stay.',
}


def main():
    src = os.path.join(MEDIA, 'sovietEnglish.btf')
    strings = btf.load(src)
    missing = [k for k in list(REPLACE) + list(FALLOUT) if k not in strings]
    if missing:
        print('WARNING ids not in the game file:', missing)
    words = dict(REPLACE)
    words.update(FALLOUT)
    for k, v in words.items():
        if k in strings:
            strings[k] = v
    os.makedirs(OUT, exist_ok=True)
    work = os.path.join(ROOT, 'build', 'text')
    os.makedirs(work, exist_ok=True)
    out_btf = os.path.join(work, 'sovietEnglish.btf')
    btf.save(out_btf, strings)
    # round-trip check
    back = btf.load(out_btf)
    assert all(back[k] == v for k, v in words.items() if k in strings), 'round trip mismatch'
    assert len(back) == len(strings)
    with zipfile.ZipFile(os.path.join(OUT, 'media_soviet.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(out_btf, 'sovietEnglish.btf')
    open(os.path.join(OUT, 'workshopconfig.ini'), 'w', newline='').write('\r\n'.join([
        '$ITEM_ID 9000005', '', '$ITEM_TYPE WORKSHOP_ITEMTYPE_TEXT', '', '$VISIBILITY 2', '',
        '$ITEM_NAME "Year Zero words - survivors and contamination"', '',
        '$ITEM_DESC "Tourists are survivors, foreign workers are mercenaries, tourism research is the distress call; crime is contamination, the police are the Decontamination Task Force, the court is the Radiology Board, the prison is the Recovery Center. English text only."', '', '$END', '']))
    # the VFS form, for TesmioLoader users
    vfs = os.path.join(ROOT, 'mod', 'text', 'vfs', 'media_soviet')
    os.makedirs(vfs, exist_ok=True)
    shutil.copy(out_btf, os.path.join(vfs, 'sovietEnglish.btf'))
    print('%d strings replaced; %s and the VFS copy written' % (len(words) - len(missing), OUT))


if __name__ == '__main__':
    main()
