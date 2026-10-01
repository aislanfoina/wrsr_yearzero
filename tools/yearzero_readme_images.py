"""The README's pictures and the Workshop items' preview images for Republic in Ruins.

    python tools/yearzero_readme_images.py            # render (Blender, tools/yearzero_readme_scene.py), then compose
    python tools/yearzero_readme_images.py compose    # compose from build/yearzero_readme only

Writes docs/yearzero_images/*.jpg (docs/images in the repository) and build/yearzero_previews/<item>.png,
which tools/yearzero_workshop.py packs as each item's previewimage.png. Renders are mirrored the way
the game shows models. Set BLENDER if Blender is not in its default folder.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = os.environ.get('BLENDER', r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
RENDERS = os.path.join(ROOT, 'build', 'yearzero_readme')
IMAGES = os.path.join(ROOT, 'docs', 'yearzero_images')
PREVIEWS = os.path.join(ROOT, 'build', 'yearzero_previews')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yearzero_workshop as W  # noqa: E402  (the kit and vehicle lists)

KIT_OBJECTS = {'madmax_kit': ['mm_scrap_wall', 'mm_wall_tower', 'mm_watchtower', 'mm_shanty', 'mm_fuel_depot', 'mm_wreck_yard',
                              'mm_ruin_block', 'mm_road_wreck', 'mm_totem', 'mm_windpump', 'mm_barricade', 'mm_skull_gate'],
               'trade_post': ['trade_post'], 'goods_post': ['goods_post'], 'junk_post': ['junk_post'],
               'scrap_center': ['scrap_center'], 'scrap_dock': ['scrap_dock'],
               'survivors_kit': ['mercenary_camp', 'distress_beacon', 'survivor_shelter'],
               'fallout_kit': ['dtf_station', 'radiology_board', 'recovery_center']}
RUST = (196, 92, 48)
INK = (236, 228, 214)
BG = (24, 22, 20)


def mirrored(name):
    """A render as the game shows it: the game draws models mirrored left to right."""
    return Image.open(os.path.join(RENDERS, name)).convert('RGB').transpose(Image.FLIP_LEFT_RIGHT)


def font(size, bold=True):
    for f in (('segoeuib.ttf', 'arialbd.ttf') if bold else ('segoeui.ttf', 'arial.ttf')) + ('DejaVuSans-Bold.ttf',):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def save(im, name, width=1600):
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(os.path.join(IMAGES, name), quality=84, optimize=True, progressive=True)
    print('%-16s %4d x %-4d %4d KB' % (name, im.width, im.height, os.path.getsize(os.path.join(IMAGES, name)) // 1024))


def name_of_building(kit, obj):
    for line in open(os.path.join(ROOT, 'mod', 'buildings', kit, obj, 'building.ini'), encoding='utf-8', errors='replace'):
        if line.startswith('$NAME_STR'):
            return line.split('"')[1]
    return obj


def name_of_vehicle(key):
    man = json.load(open(os.path.join(ROOT, 'build', 'vehicles', key, 'manifest.json')))
    return man.get(key, man).get('name', key)


def card(size, title, sub):
    """A title tile for the grid's spare cell."""
    im = Image.new('RGB', size, BG)
    d = ImageDraw.Draw(im)
    f1, f2 = font(int(size[1] * 0.16)), font(int(size[1] * 0.07), bold=False)
    lines = title.split('\n')
    y = size[1] * 0.5 - len(lines) * size[1] * 0.09
    for ln in lines:
        w = d.textlength(ln, font=f1)
        d.text(((size[0] - w) / 2, y), ln, fill=RUST, font=f1)
        y += size[1] * 0.18
    w = d.textlength(sub, font=f2)
    d.text(((size[0] - w) / 2, y + size[1] * 0.02), sub, fill=INK, font=f2)
    return im


def grid(items, cols, title, sub, tile=(400, 256), label=30):
    """(render file, caption) tiles in a grid, the title card in the last cell."""
    rows = (len(items) + 1 + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tile[0], rows * (tile[1] + label)), BG)
    d = ImageDraw.Draw(sheet)
    f = font(15)
    for i, (render, caption) in enumerate(items):
        x, y = (i % cols) * tile[0], (i // cols) * (tile[1] + label)
        im = mirrored(render)
        s = max(tile[0] / im.width, tile[1] / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        ox, oy = (im.width - tile[0]) // 2, (im.height - tile[1]) // 2
        sheet.paste(im.crop((ox, oy, ox + tile[0], oy + tile[1])), (x, y))
        w = d.textlength(caption, font=f)
        d.text((x + (tile[0] - w) / 2, y + tile[1] + 6), caption, fill=INK, font=f)
    i = len(items)
    sheet.paste(card((tile[0], tile[1] + label), title, sub), ((i % cols) * tile[0], (i // cols) * (tile[1] + label)))
    return sheet


def preview(tiles, title):
    """A 512 x 512 Workshop preview: four renders and a title band."""
    im = Image.new('RGB', (512, 512), BG)
    for i, render in enumerate(tiles[:4]):
        t = mirrored(render)
        s = max(256 / t.width, 256 / t.height)
        t = t.resize((round(t.width * s), round(t.height * s)), Image.LANCZOS)
        ox, oy = (t.width - 256) // 2, (t.height - 256) // 2
        im.paste(t.crop((ox, oy, ox + 256, oy + 256)), ((i % 2) * 256, (i // 2) * 256))
    return band(im, title)


def band(im, title):
    d = ImageDraw.Draw(im)
    f = font(40)
    d.rectangle((0, 432, 512, 512), fill=BG)
    d.rectangle((0, 432, 512, 436), fill=RUST)
    w = d.textlength(title, font=f)
    d.text(((512 - w) / 2, 448), title, fill=INK, font=f)
    return im


def main():
    if 'compose' not in sys.argv[1:]:
        r = subprocess.run([BLENDER, '-b', '--python', os.path.join('tools', 'yearzero_readme_scene.py'), '--', RENDERS], cwd=ROOT)
        if r.returncode:
            sys.exit('Blender failed')
    os.makedirs(IMAGES, exist_ok=True)
    os.makedirs(PREVIEWS, exist_ok=True)
    outpost = mirrored('outpost.png')
    save(outpost, 'outpost.jpg')
    blds = [('b_%s.png' % o, name_of_building(k, o)) for k in W.KITS for o in KIT_OBJECTS[k]]
    save(grid(blds, 6, 'REPUBLIC\nIN RUINS', '%d buildings' % len(blds)), 'buildings.jpg')
    vehs = [('v_%s.png' % v, name_of_vehicle(v)) for v in W.VEHICLES]
    save(grid(vehs, 5, 'THE MOTOR\nPOOL', '%d vehicles' % len(vehs)), 'vehicles.jpg')
    # the four Workshop items' preview images
    side = min(outpost.size)
    sq = outpost.crop(((outpost.width - side) // 2, 0, (outpost.width + side) // 2, side)).resize((512, 512), Image.LANCZOS)
    band(sq.copy(), 'REPUBLIC IN RUINS').save(os.path.join(PREVIEWS, 'republic_in_ruins.png'))
    band(sq.copy(), 'WORDS').save(os.path.join(PREVIEWS, 'words.png'))
    preview(['b_trade_post.png', 'b_scrap_center.png', 'b_dtf_station.png', 'b_mm_watchtower.png'], 'BUILDINGS').save(
        os.path.join(PREVIEWS, 'buildings.png'))
    preview(['v_warrig.png', 'v_interceptor.png', 'v_warloco.png', 'v_rustbarge.png'], 'VEHICLES').save(
        os.path.join(PREVIEWS, 'vehicles.png'))
    print('previews ->', PREVIEWS)


if __name__ == '__main__':
    main()
