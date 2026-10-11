"""Decode Godot 3.x StreamTexture (.stex) top mip level to a PIL image."""
import struct, io, math
from PIL import Image

def _dds(data, w, h, fourcc):
    hdr = struct.pack('<4sIIIIIII44s', b'DDS ', 124, 0x1007 | 0x80000, h, w, len(data), 0, 1, b'\0' * 44)
    hdr += struct.pack('<II4sIIIII', 32, 0x4, fourcc, 0, 0, 0, 0, 0)
    hdr += struct.pack('<IIIII', 0x1000, 0, 0, 0, 0)
    im = Image.open(io.BytesIO(hdr + data)); im.load(); return im

def decode(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'GDST', path
    w, cw, h, ch, flags, fmt = struct.unpack('<4H2I', d[4:20])
    W, H = cw or w, ch or h
    f = fmt & 0xFFFFF
    if fmt & (3 << 20):  # lossless / lossy: embedded PNG/WEBP mips
        n, size = struct.unpack_from('<II', d, 20)
        blob = d[28:28 + size]
        tag, payload = blob[:4], blob[4:]
        im = Image.open(io.BytesIO(payload)); im.load()
    else:
        raw = d[20:]
        if f in (17, 19, 20, 21):  # DXT1, DXT5, RGTC_R, RGTC_RG
            bw, bh = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
            bsize = 8 if f in (17, 20) else 16
            data = raw[:bw * bh * bsize]
            fourcc = {17: b'DXT1', 19: b'DXT5', 20: b'ATI1', 21: b'ATI2'}[f]
            im = _dds(data, w, h, fourcc)
            if f == 21:  # normal map stored as RG: rebuild blue channel
                r, g = im.convert('RGB').split()[:2]
                px = []
                for x, y in zip(r.getdata(), g.getdata()):
                    nx, ny = x / 127.5 - 1, y / 127.5 - 1
                    px.append(int(round((math.sqrt(max(0.0, 1 - nx * nx - ny * ny)) + 1) * 127.5)))
                b = Image.new('L', im.size); b.putdata(px)
                im = Image.merge('RGB', (r, g, b))
        elif f == 0: im = Image.frombytes('L', (w, h), raw[:w * h])
        elif f == 1: im = Image.frombytes('LA', (w, h), raw[:w * h * 2])
        elif f == 4: im = Image.frombytes('RGB', (w, h), raw[:w * h * 3])
        elif f == 5: im = Image.frombytes('RGBA', (w, h), raw[:w * h * 4])
        elif f == 6:  # RGBA4444
            px = struct.unpack('>%dH' % (w * h), raw[:w * h * 2])
            out = bytearray()
            for p in px:
                for s in (12, 8, 4, 0): out.append(((p >> s) & 0xF) * 17)
            im = Image.frombytes('RGBA', (w, h), bytes(out))
        else:
            raise ValueError('unsupported stex format %d in %s' % (f, path))
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    return im
