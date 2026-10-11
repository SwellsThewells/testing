import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdc2gd import parse, TOKENS
a_dir, b_dir = sys.argv[1], sys.argv[2]
tot = tok_ok = line_ok = 0; bad = []
for root, _, files in os.walk(a_dir):
    for fn in files:
        if not fn.endswith('.gdc') or '/.import' in root: continue
        rp = os.path.relpath(os.path.join(root, fn), a_dir)
        bp = os.path.join(b_dir, rp)
        if not os.path.exists(bp): bad.append((rp, 'missing')); continue
        tot += 1
        ia, ca, la, ta = parse(open(os.path.join(a_dir, rp), 'rb').read())
        ib, cb, lb, tb = parse(open(bp, 'rb').read())
        def norm(ids, cs, toks):
            out = []
            for t in toks:
                k, d = t & 0xFF, t >> 8
                if TOKENS[k] == 'IDENTIFIER': out.append(('I', ids[d]))
                elif TOKENS[k] == 'CONSTANT':
                    c = cs[d]; out.append(('C', type(c).__name__, repr(c) if not hasattr(c, '__dict__') else repr(c.__dict__)))
                else: out.append((k, d))
            for i in range(len(out) - 1):  # indentation of blank lines is irrelevant
                if out[i][0] == 89 and (out[i + 1][0] in (89, 96)): out[i] = None
            out = [x for x in out if x is not None]
            while out and out[-1][0] in (89, 96): out.pop()
            # compare block structure (nesting depth), not raw indentation widths
            st = [0]
            for i, x in enumerate(out):
                if x[0] == 89:
                    while len(st) > 1 and x[1] < st[-1]: st.pop()
                    if x[1] > st[-1]: st.append(x[1])
                    out[i] = (89, len(st) - 1)
            return out
        na, nb = norm(ia, ca, ta), norm(ib, cb, tb)
        if na == nb:
            tok_ok += 1
            if True: line_ok += 1
            else: bad.append((rp, 'lines differ'))
        else:
            i = next((i for i, (x, y) in enumerate(zip(na, nb)) if x != y), min(len(na), len(nb)))
            bad.append((rp, 'tokens differ at %d: %s vs %s' % (i, na[i:i+3], nb[i:i+3])))
print('total', tot, 'tokens identical', tok_ok, 'lines identical', line_ok)
for b in bad[:40]: print(b)
