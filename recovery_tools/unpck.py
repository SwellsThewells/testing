import struct, sys, os
src, out = sys.argv[1], sys.argv[2]
f = open(src, 'rb')
assert f.read(4) == b'GDPC'
ver, ma, mi, pa = struct.unpack('<4I', f.read(16))
f.read(64)
n, = struct.unpack('<I', f.read(4))
entries = []
for _ in range(n):
    l, = struct.unpack('<I', f.read(4))
    p = f.read(l).rstrip(b'\0').decode()
    off, size = struct.unpack('<QQ', f.read(16)); f.read(16)
    entries.append((p, off, size))
for p, off, size in entries:
    assert p.startswith('res://')
    rel = os.path.normpath(p[6:])
    assert not rel.startswith('..') and not os.path.isabs(rel)
    dst = os.path.join(out, rel)
    os.makedirs(os.path.dirname(dst) or out, exist_ok=True)
    f.seek(off); open(dst, 'wb').write(f.read(size))
    print(p, size)
