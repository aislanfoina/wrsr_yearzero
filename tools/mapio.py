"""Readers/writers for the parts of a WRSR map (= save) folder that the
post-apocalypse converter edits. Formats were recovered from C3D_FOREST::Import,
C3D_BUILDING::Import (C3DDLL64.dll) and Building::Read (SOVIET64.exe 0x1F0BE0),
save format version 124.

buildings.bin      u32 ntypes, u32 declared_size, then per type: char name[0x40],
                   u32 n, n x FRAG(0x46), then a trailing u32.
                   FRAG: 16 junk | float3 pos @0x10 | u8 rotstep @0x1C |
                   float6 aabb @0x1D | u8 flag @0x35 | float4 extra @0x36
buildings_game.bin u32 count, then count self-describing records, each starting
                   with a 0x548 header: char ident[0x20] @0, float3 pos @0x34C
                   and @0x39C, float rot @0x3AC, u32 fragment index @0x3D8,
                   u32 rotstep @0x3DC.
trees.bin          u32 ntypes, u32 declared_size, per type: char name[0x40],
                   u32 n, n x 17 bytes (float3 pos, u32 quadtree node, u8 var).
namepoints.bin     u32 n, n x 500 bytes (float3 pos, then a wchar name).
*.dds layers       128-byte DDS header + raw pixels (heightmap r32f, mask/
                   resourcemap BGRA8, 2048^2 / 1024^2).
"""
import os
import re
import struct
import collections

FRAG = 0x46
TYPEHDR = 0x44
TREE_REC = 17


class Frag:
    __slots__ = ('junk', 'pos', 'rot', 'aabb', 'flag', 'extra')

    def __init__(self, raw=None):
        if raw is None:
            raw = (b'\0' * 0x10 + struct.pack('<3f', 0, 0, 0) + b'\0'
                   + struct.pack('<6f', 0, 0, 0, 0, 0, 0) + b'\1' + struct.pack('<4f', 0, 0, 0, 0))
        self.junk = bytes(raw[:0x10])
        self.pos = list(struct.unpack_from('<3f', raw, 0x10))
        self.rot = raw[0x1c]
        self.aabb = list(struct.unpack_from('<6f', raw, 0x1d))
        self.flag = raw[0x35]
        self.extra = list(struct.unpack_from('<4f', raw, 0x36))

    def pack(self):
        return (self.junk + struct.pack('<3f', *self.pos) + bytes([self.rot])
                + struct.pack('<6f', *self.aabb) + bytes([self.flag]) + struct.pack('<4f', *self.extra))


def read_buildings(path):
    d = open(path, 'rb').read()
    n, declared = struct.unpack_from('<II', d, 0)
    o = 8
    types = collections.OrderedDict()
    for _ in range(n):
        name = d[o:o + 0x40].split(b'\0')[0].decode()
        cnt = struct.unpack_from('<I', d, o + 0x40)[0]
        o += TYPEHDR
        types[name] = [Frag(d[o + i * FRAG:o + (i + 1) * FRAG]) for i in range(cnt)]
        o += cnt * FRAG
    trailer = d[o:]
    return types, trailer


def write_buildings(path, types, trailer=b'\0\0\0\0'):
    body = b''
    for name, frags in types.items():
        body += name.encode().ljust(0x40, b'\0') + struct.pack('<I', len(frags)) + b''.join(f.pack() for f in frags)
    # the engine declares the size with 0x4C per fragment (its in-memory stride); mirrored here
    declared = sum(TYPEHDR + 0x4C * len(f) for f in types.values())
    open(path, 'wb').write(struct.pack('<II', len(types), declared) + body + trailer)


class Rec:
    """One game-side building record (raw bytes) with the header fields decoded."""
    IDENT = 0x0
    POS1 = 0x34C
    POS2 = 0x39C
    ROTF = 0x3AC
    FRAGIDX = 0x3D8
    ROTSTEP = 0x3DC

    def __init__(self, raw):
        self.raw = bytearray(raw)

    @property
    def ident(self):
        return bytes(self.raw[:0x20]).split(b'\0')[0].decode()

    @ident.setter
    def ident(self, v):
        b = v.encode()
        assert len(b) < 0x20, v
        self.raw[:0x20] = b.ljust(0x20, b'\0')

    def u32(self, off):
        return struct.unpack_from('<I', self.raw, off)[0]

    def set_u32(self, off, v):
        struct.pack_into('<I', self.raw, off, v)

    def f32(self, off):
        return struct.unpack_from('<f', self.raw, off)[0]

    def set_f32(self, off, v):
        struct.pack_into('<f', self.raw, off, v)

    @property
    def pos(self):
        return list(struct.unpack_from('<3f', self.raw, self.POS1))

    def set_pos(self, xyz):
        struct.pack_into('<3f', self.raw, self.POS1, *xyz)
        struct.pack_into('<3f', self.raw, self.POS2, *xyz)

    @property
    def fragidx(self):
        return self.u32(self.FRAGIDX)

    def set_fragidx(self, v):
        self.set_u32(self.FRAGIDX, v)

    @property
    def rotstep(self):
        return self.u32(self.ROTSTEP)

    def set_rot(self, step, rotf):
        self.set_u32(self.ROTSTEP, step)
        self.set_f32(self.ROTF, rotf)


def _anchor_valid(g, off, name, types):
    """A real record start has, at +0x3D8, a fragment index into its type's
    fragment list (or the MIRRORZ_ variant) whose position equals the float3 at +0x34C."""
    if off + 0x548 > len(g):
        return False
    idx = struct.unpack_from('<I', g, off + Rec.FRAGIDX)[0]
    p = struct.unpack_from('<3f', g, off + Rec.POS1)
    for tn in (name, 'MIRRORZ_' + name):
        fr = types.get(tn)
        if fr and idx < len(fr) and all(abs(a - b) < 0.05 for a, b in zip(p, fr[idx].pos)):
            return True
    return False


def split_records(game_path, types, strict=True):
    """Split buildings_game.bin into records using the ident strings as anchors,
    validated against the engine fragments. `types` is the OrderedDict from
    read_buildings (or a list of names when strict=False validation is not wanted).
    strict=True  -> every record must be found and validated, else ValueError.
    strict=False -> returns only records whose start is validated and whose extent
                    reaches the next anchor of any kind (safe for donor extraction);
                    each Rec gets .safe=False when an unvalidated anchor sits inside."""
    g = open(game_path, 'rb').read()
    cnt = struct.unpack_from('<I', g, 0)[0]
    names = list(types)
    tmap = types if isinstance(types, dict) else None
    hits = {}
    for name in names:
        pat = re.escape(name.encode()) + rb'\x00'
        for m in re.finditer(pat, g):
            # keep the longest ident when one ident is a suffix of another at the same end
            if m.start() not in hits or len(name) > len(hits[m.start()]):
                hits[m.start()] = name
    # a suffix match ("x/foo" vs "foo") lands inside the longer ident; drop hits that are
    # covered by an earlier hit's ident buffer
    offs = sorted(hits)
    if tmap is not None:
        valid = {o: _anchor_valid(g, o, hits[o], tmap) for o in offs}
    else:
        valid = {o: True for o in offs}
    good = [o for o in offs if valid[o]]
    if strict:
        if len(good) != cnt or (good and good[0] != 4) or len(offs) != cnt:
            raise ValueError('record split failed: %d anchors (%d validated) for %d records' % (len(offs), len(good), cnt))
    recs = []
    for i, off in enumerate(offs):
        if not valid[off]:
            continue
        end = offs[i + 1] if i + 1 < len(offs) else len(g)
        r = Rec(g[off:end])
        r.safe = (i + 1 >= len(offs)) or valid[offs[i + 1]]
        recs.append(r)
    return recs


def write_records(path, recs):
    with open(path, 'wb') as f:
        f.write(struct.pack('<I', len(recs)))
        for r in recs:
            f.write(bytes(r.raw))


def read_trees(path):
    d = open(path, 'rb').read()
    n, declared = struct.unpack_from('<II', d, 0)
    o = 8
    types = collections.OrderedDict()
    for _ in range(n):
        name = d[o:o + 0x40].split(b'\0')[0].decode()
        cnt = struct.unpack_from('<I', d, o + 0x40)[0]
        o += TYPEHDR
        types[name] = bytearray(d[o:o + cnt * TREE_REC])
        o += cnt * TREE_REC
    return types


def write_trees(path, types):
    body = b''
    declared = 0
    for name, recs in types.items():
        cnt = len(recs) // TREE_REC
        body += name.encode().ljust(0x40, b'\0') + struct.pack('<I', cnt) + bytes(recs)
        declared += TYPEHDR + 20 * cnt
    open(path, 'wb').write(struct.pack('<II', len(types), declared) + body)


def tree_positions(recs):
    import numpy as np
    a = np.frombuffer(bytes(recs), dtype=np.uint8).reshape(-1, TREE_REC)
    return np.ascontiguousarray(a[:, :12]).view('<f4').reshape(-1, 3)


def read_dds_raw(path):
    d = open(path, 'rb').read()
    h, w = struct.unpack_from('<II', d, 12)
    bpp = struct.unpack_from('<I', d, 88)[0]
    fourcc = d[84:88]
    return d[:128], d[128:], h, w, fourcc, bpp


def write_dds_raw(path, header, pixels):
    open(path, 'wb').write(header + pixels)


def read_namepoints(path):
    d = open(path, 'rb').read()
    n = struct.unpack_from('<I', d, 0)[0]
    return [bytearray(d[4 + i * 500:4 + (i + 1) * 500]) for i in range(n)]


def write_namepoints(path, entries):
    open(path, 'wb').write(struct.pack('<I', len(entries)) + b''.join(bytes(e) for e in entries))


def read_mtl(path):
    return open(path, 'rb').read().decode('utf-8', 'replace').replace('\r\n', '\n')


def set_textures(mtl_text, mapping):
    out = []
    for line in mtl_text.split('\n'):
        m = re.match(r'\$TEXTURE (\d+) (\S+)', line)
        if m and int(m.group(1)) in mapping:
            line = '$TEXTURE %s %s' % (m.group(1), mapping[int(m.group(1))])
        out.append(line)
    return '\r\n'.join(out)
