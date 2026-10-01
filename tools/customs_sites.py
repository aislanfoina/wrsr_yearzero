"""Find every place the game special-cases a customs house with a constant.

The pattern that matters looks like this (0x1566A7 in 1.1.1.9):

    mov     rax, [rdx + 0x318]        ; building -> type descriptor
    cmp     dword [rax + 0x360], 0x14 ; BUILDINGTYPE_CUSTOMHOUSE
    jne     normal_path               ; every other building computes the answer
    movaps  xmm6, xmm9                ; a customs house just uses a constant
    jmp     done

That constant IS the infinite border supply. Anywhere the same shape occurs is a
place finite stock has to be injected, so this enumerates them rather than
relying on having spotted them by eye.
"""
import os
import re, struct, sys, bisect

sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

EXE = os.path.join(os.environ.get('WRSR_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\SovietRepublic').rstrip('/\\'), 'SOVIET64.exe')
RIP = re.compile(r'rip \+ (0x[0-9a-f]+)')


def const_at(pe, rva):
    raw = pe.read(rva, 4)
    if len(raw) != 4:
        return None
    return struct.unpack('<f', raw)[0], struct.unpack('<I', raw)[0]


def main():
    pe = PE(EXE)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    name, va, vsz, raw, rawsz = [s for s in pe.sections if s[0] == '.text'][0]
    blob = pe.data[raw:raw + rawsz]
    starts = [b for b, _ in pe.pdata]

    def owner(r):
        i = bisect.bisect_right(starts, r) - 1
        if i < 0:
            return None
        b, e = pe.pdata[i]
        if not (b <= r < e):
            return None
        while i > 0 and pe.pdata[i - 1][1] == b:
            i -= 1
            b = pe.pdata[i][0]
        return b

    # every `cmp [reg+0x360], 0x14`
    sites = []
    i = 0
    while True:
        i = blob.find(b'\x60\x03\x00\x00', i)
        if i < 0:
            break
        for back in (2, 3):
            op = i - back
            if op < 0:
                continue
            opc = blob[op + 1] if back == 3 else blob[op]
            modrm = blob[op + 2] if back == 3 else blob[op + 1]
            if opc in (0x83, 0x81) and ((modrm >> 3) & 7) == 7 and (modrm >> 6) == 2:
                if back == 3 and not (0x40 <= blob[op] <= 0x4F):
                    continue
                imm = blob[i + 4] if opc == 0x83 else int.from_bytes(blob[i + 4:i + 8], 'little')
                if imm == 0x14:
                    sites.append(va + op)
                break
        i += 1

    print(f'{len(sites)} customs-house type checks\n')
    hits = 0

    for site in sites:
        # Disassemble the check plus the ~0x28 bytes the taken branch runs into.
        window = pe.read(site, 0x40)
        insns = list(md.disasm(window, 0x140000000 + site))
        consts, moves, jcc = [], [], None

        for ins in insns[:12]:
            rva = ins.address - 0x140000000
            if ins.mnemonic.startswith('j') and jcc is None and ins.mnemonic != 'jmp':
                jcc = ins.mnemonic
                continue
            if jcc is None:
                continue
            m = RIP.search(ins.op_str)
            if m and ins.mnemonic in ('movss', 'movsd', 'comiss', 'mov'):
                c = const_at(pe, rva + ins.size + int(m.group(1), 16))
                if c and (0.0 < abs(c[0]) < 1e9):
                    consts.append(f'{ins.mnemonic} {c[0]:g}')
            if ins.mnemonic in ('movaps', 'movss', 'movsd') and 'xmm' in ins.op_str:
                moves.append(f'{ins.mnemonic} {ins.op_str}')
            if ins.mnemonic == 'mov' and re.search(r', 0x[0-9a-f]{2,}$', ins.op_str):
                moves.append(f'{ins.mnemonic} {ins.op_str}')

        if not (consts or moves):
            continue
        o = owner(site)
        hits += 1
        print(f'0x{site:08X}  in fn 0x{o:08X}' if o else f'0x{site:08X}')
        for t in (consts + moves)[:4]:
            print(f'              {t}')

    print(f'\n{hits} sites take a shortcut worth looking at')


if __name__ == '__main__':
    main()
