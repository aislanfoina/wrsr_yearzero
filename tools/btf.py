"""Read/write Workers & Resources: Soviet Republic .btf localisation files.

Format (all big-endian):
    u32 entryCount
    u32 fileSizeBytes
    u32 blobLengthChars
    entryCount * { u32 stringId; u32 charOffset; u16 charLength }
    UTF-16BE string blob (entries are NUL-separated)
"""
import struct, sys, json

HDR = struct.Struct('>III')
ENT = struct.Struct('>IIH')


def load(path):
    d = open(path, 'rb').read()
    cnt, _size, _chars = HDR.unpack_from(d, 0)
    base = 12 + cnt * ENT.size
    out = {}
    for i in range(cnt):
        sid, off, ln = ENT.unpack_from(d, 12 + i * ENT.size)
        out[sid] = d[base + off * 2: base + (off + ln) * 2].decode('utf-16-be')
    return out


def save(path, strings):
    items = sorted(strings.items())
    blob = bytearray()
    index = bytearray()
    for sid, text in items:
        enc = text.encode('utf-16-be')
        index += ENT.pack(sid, len(blob) // 2, len(enc) // 2)
        blob += enc + b'\x00\x00'          # NUL terminator
    size = 12 + len(index) + len(blob)
    open(path, 'wb').write(HDR.pack(len(items), size, len(blob) // 2) + index + blob)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'dump'
    if cmd == 'dump':
        s = load(sys.argv[2])
        json.dump({str(k): v for k, v in sorted(s.items())},
                  open(sys.argv[3], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{len(s)} strings -> {sys.argv[3]}')
    elif cmd == 'build':
        s = json.load(open(sys.argv[2], encoding='utf-8'))
        save(sys.argv[3], {int(k): v for k, v in s.items()})
        print(f'{len(s)} strings -> {sys.argv[3]}')
