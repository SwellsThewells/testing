"""Godot 3.x marshalls (encode_variant) decoder and text (VariantWriter) encoder."""
import struct, math

class V:  # typed math value
    def __init__(self, name, vals): self.name, self.vals = name, list(vals)
class NodePath:
    def __init__(self, s): self.s = s
class Obj:
    def __init__(self, cls, props): self.cls, self.props = cls, props
class Pool:
    def __init__(self, name, vals): self.name, self.vals = name, vals
class F32(float): pass  # float that came from a 32-bit value

def _f32s(buf, off, n):
    return [F32(x) for x in struct.unpack_from('<%df' % n, buf, off)], off + 4 * n

def _str(buf, off):
    l, = struct.unpack_from('<I', buf, off); off += 4
    s = buf[off:off + l].decode('utf-8'); off += l
    return s, off + ((4 - l % 4) % 4)

MATH = {5: ('Vector2', 2), 6: ('Rect2', 4), 7: ('Vector3', 3), 8: ('Transform2D', 6), 9: ('Plane', 4),
        10: ('Quat', 4), 11: ('AABB', 6), 12: ('Basis', 9), 13: ('Transform', 12), 14: ('Color', 4)}

def decode(buf, off=0):
    h, = struct.unpack_from('<I', buf, off); off += 4
    t, flags = h & 0xFF, h >> 16
    if t == 0: return None, off
    if t == 1: return bool(struct.unpack_from('<I', buf, off)[0]), off + 4
    if t == 2:
        if flags & 1: return struct.unpack_from('<q', buf, off)[0], off + 8
        return struct.unpack_from('<i', buf, off)[0], off + 4
    if t == 3:
        if flags & 1: return struct.unpack_from('<d', buf, off)[0], off + 8
        return F32(struct.unpack_from('<f', buf, off)[0]), off + 4
    if t == 4: return _str(buf, off)
    if t in MATH:
        name, n = MATH[t]; vals, off = _f32s(buf, off, n); return V(name, vals), off
    if t == 15:
        l, = struct.unpack_from('<I', buf, off); off += 4
        if l & 0x80000000:
            names = l & 0x7FFFFFFF
            subs, fl = struct.unpack_from('<II', buf, off); off += 8
            if fl & 2: subs += 1
            parts = []
            for _ in range(names + subs):
                s, off = _str(buf, off); parts.append(s)
            p = '/'.join(parts[:names])
            if fl & 1: p = '/' + p
            if subs: p += ':' + ':'.join(parts[names:])
            return NodePath(p), off
        s = buf[off:off + l].decode(); off += l
        return NodePath(s), off + ((4 - l % 4) % 4)
    if t == 16: return None, off
    if t == 17:
        if flags & 1: return None, off + 8
        cls, off = _str(buf, off)
        if not cls: return None, off
        n, = struct.unpack_from('<I', buf, off); off += 4
        props = []
        for _ in range(n):
            k, off = _str(buf, off); v, off = decode(buf, off); props.append((k, v))
        return Obj(cls, props), off
    if t == 18:
        n, = struct.unpack_from('<I', buf, off); off += 4; n &= 0x7FFFFFFF
        d = []
        for _ in range(n):
            k, off = decode(buf, off); v, off = decode(buf, off); d.append((k, v))
        return dict_(d), off
    if t == 19:
        n, = struct.unpack_from('<I', buf, off); off += 4; n &= 0x7FFFFFFF
        a = []
        for _ in range(n):
            v, off = decode(buf, off); a.append(v)
        return a, off
    if t == 20:
        n, = struct.unpack_from('<I', buf, off); off += 4
        b = buf[off:off + n]; off += n + ((4 - n % 4) % 4)
        return Pool('PoolByteArray', list(b)), off
    if t == 21:
        n, = struct.unpack_from('<I', buf, off); off += 4
        return Pool('PoolIntArray', list(struct.unpack_from('<%di' % n, buf, off))), off + 4 * n
    if t == 22:
        n, = struct.unpack_from('<I', buf, off); off += 4
        v, off = _f32s(buf, off, n); return Pool('PoolRealArray', v), off
    if t == 23:
        n, = struct.unpack_from('<I', buf, off); off += 4
        a = []
        for _ in range(n):
            l, = struct.unpack_from('<I', buf, off); off += 4
            a.append(buf[off:off + l].rstrip(b'\0').decode()); off += l + ((4 - l % 4) % 4)
        return Pool('PoolStringArray', a), off
    if t in (24, 25, 26):
        k = {24: 2, 25: 3, 26: 4}[t]
        n, = struct.unpack_from('<I', buf, off); off += 4
        v, off = _f32s(buf, off, n * k)
        return Pool({24: 'PoolVector2Array', 25: 'PoolVector3Array', 26: 'PoolColorArray'}[t], v), off
    raise ValueError('unknown variant type %d' % t)

class dict_(list):
    pass

def fmt_real(x, script=False):
    if math.isinf(x): return ('-' if x < 0 else '') + 'inf' if not script else ('-INF' if x < 0 else 'INF')
    if math.isnan(x): return 'nan' if not script else 'NAN'
    if isinstance(x, F32):
        s = None
        for p in range(1, 10):
            c = '%.*g' % (p, x)
            if struct.pack('<f', float(c)) == struct.pack('<f', x): s = repr(float(c)); break
        if s is None: s = repr(float(x))
    else:
        s = repr(float(x))
    if 'e' in s:
        m, e = s.split('e'); ei = int(e)
        if '.' not in m: m += '.0'
        s = '%se%s%02d' % (m, '-' if ei < 0 else '+', abs(ei))
    return s

def fmt_num(x):  # for components inside Vector2( ... ) etc.
    s = fmt_real(x)
    if s.endswith('.0') and 'e' not in s: s = s[:-2]
    if s == '-0': s = '-0'
    return s

def esc(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

def esc_script(s):
    out = []
    for ch in s:
        o = {'\\': '\\\\', '"': '\\"', '\n': '\\n', '\t': '\\t', '\r': '\\r', '\0': '\\0',
             '\a': '\\a', '\b': '\\b', '\f': '\\f', '\v': '\\v'}.get(ch)
        out.append(o if o else ch)
    return '"' + ''.join(out) + '"'

def text(v):
    """VariantWriter (project.godot / tscn) style."""
    if v is None: return 'null'
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, int): return str(v)
    if isinstance(v, float):
        s = fmt_real(v)
        return s
    if isinstance(v, str): return esc(v)
    if isinstance(v, V): return '%s( %s )' % (v.name, ', '.join(fmt_num(x) for x in v.vals))
    if isinstance(v, NodePath): return 'NodePath(%s)' % esc(v.s)
    if isinstance(v, Obj):
        return 'Object(%s,%s)' % (v.cls, ','.join('%s:%s' % (esc(k), text(x)) for k, x in v.props))
    if isinstance(v, dict_):
        if not v: return '{\n}'
        return '{\n' + ',\n'.join('%s: %s' % (text(k), text(x)) for k, x in v) + '\n}'
    if isinstance(v, list):
        return '[ ' + ', '.join(text(x) for x in v) + ' ]' if v else '[  ]'
    if isinstance(v, Pool):
        if v.name == 'PoolStringArray': items = [esc(x) for x in v.vals]
        elif v.name in ('PoolByteArray', 'PoolIntArray'): items = [str(x) for x in v.vals]
        else: items = [fmt_num(x) for x in v.vals]
        return '%s( %s )' % (v.name, ', '.join(items))
    raise TypeError(type(v))
