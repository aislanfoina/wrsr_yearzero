"""Build every Mad Max asset: textures, vehicle skins, the map kit, the vehicles.

    python tools/build_madmax.py            # everything
    python tools/build_madmax.py kit        # one stage: textures | skins | kit | vehicles | previews | deploy
"""
import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
WIP = os.path.join(os.environ.get('WRSR_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\SovietRepublic').rstrip('/\\'), 'media_soviet', 'workshop_wip')
PY = sys.executable


def run(cmd):
    print('>', ' '.join(cmd))
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        sys.exit('failed: %s' % cmd[0])


def stage_textures():
    run([PY, 'tools/tradepost_textures.py', 'build/textures'])


def stage_skins():
    run([PY, 'tools/vehicle_skins.py', 'build/vehicles'])


def stage_kit():
    run([BLENDER, '-b', '--python', 'tools/madmax_kit_scene.py', '--', 'build/textures', 'mod/buildings/madmax_kit', 'build/kit'])


def stage_vehicles():
    run([BLENDER, '-b', '--python', 'tools/madmax_vehicles.py', '--', 'build/textures', 'build/vehicles', 'mod/vehicles', 'build/vehicles'])


def stage_previews():
    """Vehicle previews: PNG renders -> the DXT5 .dds the purchase UI wants."""
    from PIL import Image
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import tradepost_textures as tt
    for key in sorted(os.listdir(os.path.join(ROOT, 'mod/vehicles'))):
        itemdir = os.path.join(ROOT, 'mod/vehicles', key, key)
        pdir = os.path.join(ROOT, 'build/vehicles', key)
        if not os.path.isdir(itemdir):
            continue
        for png in glob.glob(os.path.join(pdir, 'preview*.png')):
            name = os.path.basename(png)[:-4]
            im = Image.open(png).convert('RGBA')
            size = (256, 128) if name.endswith('_side') else (256, 256)
            im = im.resize(size, Image.LANCZOS)
            dds = name.replace('preview_', 'preview_').replace('_side', '') if False else name
            # preview_N_side -> preview_side_N, as vanilla names them
            if name.endswith('_side'):
                core = name[:-5]
                dds = 'preview_side' + core[len('preview'):]
            tt.save_dds_mips(im, os.path.join(itemdir, dds + '.dds'), 'DXT5')
        print('previews ->', itemdir)


def stage_deploy():
    for kind in ('buildings', 'vehicles', 'text'):
      for cfg in glob.glob(os.path.join(ROOT, 'mod', kind, '*', 'workshopconfig.ini')):
        src = os.path.dirname(cfg)
        item = None
        for line in open(cfg, encoding='utf-8', errors='ignore'):
            if line.startswith('$ITEM_ID'):
                item = line.split()[1]
        if not item or item == '0':
            continue
        dst = os.path.join(WIP, item)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print('deployed %s -> %s' % (os.path.relpath(src, ROOT), dst))


STAGES = {'textures': stage_textures, 'skins': stage_skins, 'kit': stage_kit, 'vehicles': stage_vehicles,
          'previews': stage_previews, 'deploy': stage_deploy}

if __name__ == '__main__':
    names = sys.argv[1:] or ['textures', 'skins', 'kit', 'vehicles', 'previews']
    for n in names:
        STAGES[n]()
