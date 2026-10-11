"""Rebuild a Godot 3.5 project from an extracted export .pck directory."""
import os, sys, re, json, shutil, struct, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gd3variant as gv
import stex
from gdc2gd import decompile

SRC, OUT, GODOT, WORK = [os.path.abspath(a) for a in sys.argv[1:5]]
TOOLS = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {'.import', 'savia_web_export'}

def rel(p): return p[6:] if p.startswith('res://') else p

def parse_import(path):
    sec, d = None, {}
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        m = re.match(r'^\[(\w+)\]$', line)
        if m: sec = m.group(1); continue
        m = re.match(r'^([\w./]+)=(.*)$', line)
        if m: d[(sec, m.group(1))] = m.group(2)
    return d

def unq(s): return json.loads(s) if s.startswith('"') else s

# ---------- 1. copy plain files, decompile scripts ----------
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
imports, report = [], {'scripts': 0, 'script_fail': []}
for root, dirs, files in os.walk(SRC):
    r = os.path.relpath(root, SRC)
    dirs[:] = [d for d in dirs if not (r == '.' and d in SKIP_DIRS)]
    for fn in files:
        sp = os.path.join(root, fn); rp = os.path.normpath(os.path.join(r, fn))
        if fn.endswith('.gdc') or rp == 'project.binary': continue
        if fn.endswith('.remap'):
            target = rel(unq(parse_import(sp)[('remap', 'path')]))
            dst = os.path.join(OUT, rp[:-len('.remap')])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if target.endswith('.gdc'):
                try:
                    open(dst, 'w', encoding='utf-8', newline='\n').write(decompile(open(os.path.join(SRC, target), 'rb').read()))
                    report['scripts'] += 1
                except Exception as e:
                    report['script_fail'].append((rp, repr(e)))
            else:
                shutil.copyfile(os.path.join(SRC, target), dst)
            continue
        if fn.endswith('.import'):
            imports.append(rp); continue
        dst = os.path.join(OUT, rp)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(sp, dst)

# ---------- 2. project.binary -> project.godot ----------
buf = open(os.path.join(SRC, 'project.binary'), 'rb').read()
assert buf[:4] == b'ECFG'
n, = struct.unpack_from('<I', buf, 4); off = 8
settings = []
for _ in range(n):
    l, = struct.unpack_from('<I', buf, off); off += 4
    key = buf[off:off + l].decode(); off += l
    vl, = struct.unpack_from('<I', buf, off); off += 4
    val, _ = gv.decode(buf, off); off += vl
    settings.append((key, val))
sections = {}
for k, v in settings:
    if k.startswith('_'):  # _global_script_classes etc. live in the (unnamed) top section
        sections.setdefault('', []).append((k, v)); continue
    s, _, kk = k.partition('/')
    sections.setdefault(s if kk else '', []).append((kk or k, v))
pg = ['; Engine configuration file.', "; It's best edited using the editor UI and not directly,",
      '; since the parameters that go here are not all obvious.', ';', '; Format:',
      ';   [section] ; section goes between []', ';   param=value ; assign values to parameters', '',
      'config_version=4', '']
top = [(k, v) for k, v in sections.pop('', []) if k != 'config_version']
for k, v in sorted(top): pg.append('%s=%s' % (k, gv.text(v)))
if top: pg.append('')
for s in sorted(sections):
    pg.append('[%s]' % s); pg.append('')
    for k, v in sorted(sections[s]): pg.append('%s=%s' % (k, gv.text(v)))
    pg.append('')
open(os.path.join(OUT, 'project.godot'), 'w', newline='\n').write('\n'.join(pg))

# ---------- 3. imported assets ----------
jobs, renames, post = [], {}, []
for rp in imports:
    d = parse_import(os.path.join(SRC, rp))
    importer = unq(d.get(('remap', 'importer'), '""'))
    source = rel(unq(d[('deps', 'source_file')])) if ('deps', 'source_file') in d else rp[:-7]
    if source.split('/')[0] in SKIP_DIRS: continue
    dst = os.path.join(OUT, source)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    paths = {k[1]: unq(v) for k, v in d.items() if k[0] == 'remap' and k[1].startswith('path')}
    keep_import = True
    if importer in ('texture', 'image', 'texture_array', 'texture_3d', 'texture_atlas'):
        src = paths.get('path') or paths.get('path.s3tc') or next(iter(paths.values()))
        ext = os.path.splitext(source)[1].lower()
        if ext == '.svg':
            # Vector source is not recoverable: write a PNG and point references at it.
            stem = source[:-4]
            newsrc = stem + '.png'
            if os.path.exists(os.path.join(SRC, newsrc + '.import')) or os.path.exists(os.path.join(SRC, newsrc)):
                newsrc = stem + '_svg.png'
            renames['res://' + source] = 'res://' + newsrc
            dst = os.path.join(OUT, newsrc)
            imp = open(os.path.join(SRC, rp), encoding='utf-8').read().replace(source, newsrc)
            open(dst + '.import', 'w', newline='\n').write(imp)
            keep_import = False
        if not os.path.exists(dst):  # raw copies (e.g. boot splash/icon) are already the originals
            im = stex.decode(os.path.join(SRC, rel(src)))
            if dst.lower().endswith(('.jpg', '.jpeg')):
                im.convert('RGB').save(dst, format='JPEG', quality=95)
            elif dst.lower().endswith('.webp'):
                im.save(dst, format='WEBP', lossless=True)
            else:
                im.save(dst, format='PNG')
    elif importer == 'wav':
        jobs.append({'kind': 'wav', 'src': paths['path'], 'dst': dst})
    elif importer in ('ogg_vorbis', 'mp3'):
        jobs.append({'kind': 'rawdata', 'src': paths['path'], 'dst': dst})
    elif importer == 'wavefront_obj':
        jobs.append({'kind': 'obj', 'src': paths['path'], 'dst': dst})
    elif importer == 'scene':
        # glTF source can't be rebuilt; keep the imported scene as a native .scn resource.
        newsrc = os.path.splitext(source)[0] + '.scn'
        shutil.copyfile(os.path.join(SRC, rel(paths['path'])), os.path.join(OUT, newsrc))
        renames['res://' + source] = 'res://' + newsrc
        keep_import = False
    elif importer == 'csv_translation':
        keep_import = False  # compiled .translation files are kept as-is (copied above)
    else:
        print('WARNING: unhandled importer', importer, rp)
        keep_import = False
    if keep_import:
        shutil.copyfile(os.path.join(SRC, rp), os.path.join(OUT, rp))

# extra files referenced by imported scenes (e.g. external materials)
for root, _, files in os.walk(os.path.join(SRC, '.import')):
    pass

os.makedirs(WORK, exist_ok=True)
shutil.rmtree(os.path.join(WORK, 'proj'), ignore_errors=True)
os.makedirs(os.path.join(WORK, 'proj'))
os.symlink(os.path.join(os.path.abspath(SRC), '.import'), os.path.join(WORK, 'proj', '.import'))
open(os.path.join(WORK, 'proj', 'project.godot'), 'w').write('config_version=4\n')
json.dump(jobs, open(os.path.join(WORK, 'jobs.json'), 'w'))
r = subprocess.run([GODOT, '--no-window', '--path', os.path.join(WORK, 'proj'), '-s',
                    os.path.join(TOOLS, 'convert_assets.gd'), '--jobs', os.path.join(WORK, 'jobs.json')],
                   capture_output=True, text=True, timeout=1200)
open(os.path.join(WORK, 'convert.log'), 'w').write(r.stdout + r.stderr)
print([l for l in (r.stdout + r.stderr).splitlines() if 'FAIL' in l or 'DONE' in l or 'ERROR' in l][:40])

# ---------- 4. rewrite references to renamed sources ----------
if renames:
    for root, _, files in os.walk(OUT):
        for fn in files:
            if fn.endswith(('.tscn', '.tres', '.gd', '.godot', '.cfg')):
                p = os.path.join(root, fn)
                t = open(p, encoding='utf-8').read(); t2 = t
                for a, b in renames.items(): t2 = t2.replace(a, b)
                if t2 != t: open(p, 'w', encoding='utf-8', newline='\n').write(t2)
print(json.dumps(report, indent=1)); print('renames', renames)
