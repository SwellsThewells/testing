"""Decompile Godot 3.5 GDScript bytecode (.gdc, version 13) back to source."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gd3variant as gv

TOKENS = """EMPTY IDENTIFIER CONSTANT SELF BUILT_IN_TYPE BUILT_IN_FUNC OP_IN OP_EQUAL OP_NOT_EQUAL OP_LESS
OP_LESS_EQUAL OP_GREATER OP_GREATER_EQUAL OP_AND OP_OR OP_NOT OP_ADD OP_SUB OP_MUL OP_DIV OP_MOD OP_SHIFT_LEFT
OP_SHIFT_RIGHT OP_ASSIGN OP_ASSIGN_ADD OP_ASSIGN_SUB OP_ASSIGN_MUL OP_ASSIGN_DIV OP_ASSIGN_MOD OP_ASSIGN_SHIFT_LEFT
OP_ASSIGN_SHIFT_RIGHT OP_ASSIGN_BIT_AND OP_ASSIGN_BIT_OR OP_ASSIGN_BIT_XOR OP_BIT_AND OP_BIT_OR OP_BIT_XOR
OP_BIT_INVERT CF_IF CF_ELIF CF_ELSE CF_FOR CF_WHILE CF_BREAK CF_CONTINUE CF_PASS CF_RETURN CF_MATCH PR_FUNCTION
PR_CLASS PR_CLASS_NAME PR_EXTENDS PR_IS PR_ONREADY PR_TOOL PR_STATIC PR_EXPORT PR_SETGET PR_CONST PR_VAR PR_AS
PR_VOID PR_ENUM PR_PRELOAD PR_ASSERT PR_YIELD PR_SIGNAL PR_BREAKPOINT PR_REMOTE PR_SYNC PR_MASTER PR_SLAVE
PR_PUPPET PR_REMOTESYNC PR_MASTERSYNC PR_PUPPETSYNC BRACKET_OPEN BRACKET_CLOSE CURLY_BRACKET_OPEN
CURLY_BRACKET_CLOSE PARENTHESIS_OPEN PARENTHESIS_CLOSE COMMA SEMICOLON PERIOD QUESTION_MARK COLON DOLLAR
FORWARD_ARROW NEWLINE CONST_PI CONST_TAU WILDCARD CONST_INF CONST_NAN ERROR EOF CURSOR""".split()
T = {n: i for i, n in enumerate(TOKENS)}

FUNCS = """sin cos tan sinh cosh tanh asin acos atan atan2 sqrt fmod fposmod posmod floor ceil round abs sign pow log exp
is_nan is_inf is_equal_approx is_zero_approx ease decimals step_decimals stepify lerp lerp_angle inverse_lerp
range_lerp smoothstep move_toward dectime randomize randi randf rand_range seed rand_seed deg2rad rad2deg linear2db
db2linear polar2cartesian cartesian2polar wrapi wrapf max min clamp nearest_po2 weakref funcref convert typeof
type_exists char ord str print printt prints printerr printraw print_debug push_error push_warning var2str str2var
var2bytes bytes2var range load inst2dict dict2inst validate_json parse_json to_json hash Color8 ColorN print_stack
get_stack instance_from_id len is_instance_valid deep_equal""".split()

TYPES = """Nil bool int float String Vector2 Rect2 Vector3 Transform2D Plane Quat AABB Basis Transform Color NodePath
RID Object Dictionary Array PoolByteArray PoolIntArray PoolRealArray PoolStringArray PoolVector2Array
PoolVector3Array PoolColorArray""".split()

BINOPS = {
    'OP_IN': 'in', 'OP_EQUAL': '==', 'OP_NOT_EQUAL': '!=', 'OP_LESS': '<', 'OP_LESS_EQUAL': '<=', 'OP_GREATER': '>',
    'OP_GREATER_EQUAL': '>=', 'OP_AND': 'and', 'OP_OR': 'or', 'OP_MUL': '*', 'OP_DIV': '/', 'OP_MOD': '%',
    'OP_SHIFT_LEFT': '<<', 'OP_SHIFT_RIGHT': '>>', 'OP_ASSIGN': '=', 'OP_ASSIGN_ADD': '+=', 'OP_ASSIGN_SUB': '-=',
    'OP_ASSIGN_MUL': '*=', 'OP_ASSIGN_DIV': '/=', 'OP_ASSIGN_MOD': '%=', 'OP_ASSIGN_SHIFT_LEFT': '<<=',
    'OP_ASSIGN_SHIFT_RIGHT': '>>=', 'OP_ASSIGN_BIT_AND': '&=', 'OP_ASSIGN_BIT_OR': '|=', 'OP_ASSIGN_BIT_XOR': '^=',
    'OP_BIT_AND': '&', 'OP_BIT_OR': '|', 'OP_BIT_XOR': '^', 'PR_IS': 'is', 'PR_AS': 'as', 'FORWARD_ARROW': '->',
    'CF_IF': 'if', 'CF_ELSE': 'else',
}
# keywords that are followed by a space and need no leading space (statement starters)
PREFIX_KW = {
    'CF_ELIF': 'elif', 'CF_FOR': 'for', 'CF_WHILE': 'while', 'CF_MATCH': 'match', 'PR_FUNCTION': 'func',
    'PR_CLASS': 'class', 'PR_CLASS_NAME': 'class_name', 'PR_EXTENDS': 'extends', 'PR_ONREADY': 'onready',
    'PR_STATIC': 'static', 'PR_EXPORT': 'export', 'PR_SETGET': 'setget', 'PR_CONST': 'const', 'PR_VAR': 'var',
    'PR_ENUM': 'enum', 'PR_SIGNAL': 'signal', 'PR_REMOTE': 'remote', 'PR_SYNC': 'sync', 'PR_MASTER': 'master',
    'PR_SLAVE': 'slave', 'PR_PUPPET': 'puppet', 'PR_REMOTESYNC': 'remotesync', 'PR_MASTERSYNC': 'mastersync',
    'PR_PUPPETSYNC': 'puppetsync', 'OP_NOT': 'not', 'CF_RETURN': 'return',
}
WORDS = {
    'SELF': 'self', 'CF_BREAK': 'break', 'CF_CONTINUE': 'continue', 'CF_PASS': 'pass', 'PR_TOOL': 'tool',
    'PR_VOID': 'void', 'PR_PRELOAD': 'preload', 'PR_ASSERT': 'assert', 'PR_YIELD': 'yield',
    'PR_BREAKPOINT': 'breakpoint', 'CONST_PI': 'PI', 'CONST_TAU': 'TAU', 'WILDCARD': '_', 'CONST_INF': 'INF',
    'CONST_NAN': 'NAN',
}
PUNCT = {'BRACKET_OPEN': '[', 'BRACKET_CLOSE': ']', 'CURLY_BRACKET_OPEN': '{', 'CURLY_BRACKET_CLOSE': '}',
         'PARENTHESIS_OPEN': '(', 'PARENTHESIS_CLOSE': ')', 'SEMICOLON': ';', 'PERIOD': '.',
         'QUESTION_MARK': '?', 'DOLLAR': '$'}
# after these tokens a +/-/~ is unary
UNARY_CTX = set(BINOPS) | set(PREFIX_KW) | {'NEWLINE', 'BRACKET_OPEN', 'CURLY_BRACKET_OPEN', 'PARENTHESIS_OPEN',
                                             'COMMA', 'COLON', 'OP_ADD', 'OP_SUB', 'OP_BIT_INVERT', 'SEMICOLON',
                                             'PR_ASSERT', None}
VALUE_END = {'IDENTIFIER', 'CONSTANT', 'SELF', 'BUILT_IN_TYPE', 'BUILT_IN_FUNC', 'BRACKET_CLOSE',
             'CURLY_BRACKET_CLOSE', 'PARENTHESIS_CLOSE', 'CONST_PI', 'CONST_TAU', 'CONST_INF', 'CONST_NAN',
             'WILDCARD', 'PR_VOID'}


def const_str(v):
    if v is None: return 'null'
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float): return gv.fmt_real(v, script=True)
    if isinstance(v, str): return gv.esc_script(v)
    return gv.text(v)


def parse(buf):
    assert buf[:4] == b'GDSC', 'not a gdc file'
    ver, nid, nconst, nlines, ntok = struct.unpack_from('<5I', buf, 4)
    if ver != 13: raise ValueError('unsupported bytecode version %d' % ver)
    off = 24
    ids = []
    for _ in range(nid):
        l, = struct.unpack_from('<I', buf, off); off += 4
        s = bytes(b ^ 0xb6 for b in buf[off:off + l]); off += l
        ids.append(s.split(b'\0', 1)[0].decode('utf-8'))
    consts = []
    for _ in range(nconst):
        v, off = gv.decode(buf, off); consts.append(v)
    lines = {}
    for _ in range(nlines):
        k, v = struct.unpack_from('<II', buf, off); off += 8
        lines[k] = v & 0xFFFFFF
    toks = []
    for _ in range(ntok):
        if buf[off] & 0x80:
            toks.append(struct.unpack_from('<I', buf, off)[0] & ~0x80); off += 4
        else:
            toks.append(buf[off]); off += 1
    return ids, consts, lines, toks


def decompile(buf):
    ids, consts, linemap, toks = parse(buf)
    out = []          # finished output lines
    cur = []          # pieces of current line
    state = {'indent_stack': [0], 'depth': 0, 'line': 1, 'cont': 0, 'nest': 0}
    prev = 'NEWLINE'
    pending_indent = 0
    line_of = 1
    dollar = False

    def text_so_far():
        return ''.join(cur)

    def sp():
        s = text_so_far()
        if s and not s.endswith(' ') and not s.endswith('(') and not s.endswith('[') and not s.endswith('{'):
            cur.append(' ')

    def flush():
        s = text_so_far().rstrip()
        out.append(('\t' * state['depth'] + s) if s else '')
        cur.clear()

    started = False
    for i, raw in enumerate(toks):
        t = raw & 0xFF
        data = raw >> 8
        name = TOKENS[t] if t < len(TOKENS) else 'ERROR'
        if i in linemap: line_of = linemap[i]
        if name == 'NEWLINE':
            pending_indent = data
            if cur:
                flush()
                state['line'] += 1
            prev = 'NEWLINE'
            dollar = False
            continue
        if name in ('EOF', 'EMPTY', 'ERROR', 'CURSOR'):
            continue
        multiline = None
        if name == 'CONSTANT' and isinstance(consts[data], str) and '\n' in consts[data]:
            nl = consts[data].count('\n')
            # the tokenizer records the line where a string ends; place it where it started
            if line_of - nl >= state['line'] + (1 if cur else 0) or (not cur and line_of - nl >= state['line']):
                multiline = consts[data]
                line_of -= nl
        if not cur:
            # beginning of a logical line: pad blank lines to keep original line numbers
            while state['line'] < line_of:
                out.append(''); state['line'] += 1
            st = state['indent_stack']
            while len(st) > 1 and pending_indent < st[-1]: st.pop()
            if pending_indent > st[-1]: st.append(pending_indent)
            state['depth'] = len(st) - 1
            state['cont'] = 0
        elif line_of > state['line']:
            # expression continued on a following source line (inside brackets or after "\")
            while state['line'] < line_of:
                s = text_so_far().rstrip()
                cur.clear(); cur.append(s + ' \\')
                flush()
                state['line'] += 1
                cur.append('\t')
            prev_tmp = prev
        # dollar path handling: $Node/Child or $"path"
        if dollar:
            if name == 'IDENTIFIER' and prev in ('DOLLAR', 'OP_DIV'):
                cur.append(ids[data]); prev = name; continue
            if name == 'CONSTANT' and prev == 'DOLLAR':
                cur.append(const_str(consts[data])); prev = name; dollar = False; continue
            if name == 'OP_DIV' and prev == 'IDENTIFIER':
                cur.append('/'); prev = name; continue
            if name == 'PERIOD' and prev == 'IDENTIFIER' and i + 1 < len(toks) and TOKENS[toks[i+1] & 0xFF] == 'PERIOD':
                pass
            dollar = False

        if name == 'IDENTIFIER' or name == 'CONSTANT' or name == 'BUILT_IN_TYPE' or name == 'BUILT_IN_FUNC' \
                or name in WORDS:
            if name == 'IDENTIFIER': s = ids[data]
            elif name == 'CONSTANT':
                if multiline is not None:
                    s = '"""' + multiline.replace('\\', '\\\\').replace('"', '\\"').replace('\r', '\\r') + '"""'
                    line_of += multiline.count('\n'); state['line'] += multiline.count('\n')
                else:
                    s = const_str(consts[data])
            elif name == 'BUILT_IN_TYPE': s = TYPES[data]
            elif name == 'BUILT_IN_FUNC': s = FUNCS[data]
            else: s = WORDS[name]
            if prev in VALUE_END or prev == 'PR_TOOL':
                sp()
            cur.append(s)
        elif name in ('OP_ADD', 'OP_SUB', 'OP_BIT_INVERT'):
            sym = {'OP_ADD': '+', 'OP_SUB': '-', 'OP_BIT_INVERT': '~'}[name]
            if name == 'OP_BIT_INVERT' or prev in UNARY_CTX:
                if prev in VALUE_END: sp()
                cur.append(sym)
            else:
                sp(); cur.append(sym + ' ')
        elif name == 'OP_ASSIGN' and prev == 'COLON' and text_so_far().endswith(': '):
            cur[-1] = cur[-1][:-2] if cur[-1].endswith(': ') else cur[-1]
            cur.append(' := ')
        elif name in BINOPS:
            sym = BINOPS[name]
            if name == 'CF_ELSE' and prev == 'NEWLINE' or not cur or text_so_far().strip() == '':
                cur.append(sym)
            else:
                sp(); cur.append(sym)
            nxt = TOKENS[toks[i + 1] & 0xFF] if i + 1 < len(toks) and (toks[i + 1] & 0xFF) < len(TOKENS) else 'NEWLINE'
            if not (name == 'CF_ELSE' and nxt == 'COLON'):
                cur.append(' ')
        elif name in PREFIX_KW:
            if prev in VALUE_END or prev == 'PR_TOOL' or prev in ('PR_EXPORT',) and False:
                sp()
            elif cur and not text_so_far().endswith((' ', '(', '[', '{', '\t')):
                sp()
            cur.append(PREFIX_KW[name])
            nxt = TOKENS[toks[i + 1] & 0xFF] if i + 1 < len(toks) and (toks[i + 1] & 0xFF) < len(TOKENS) else 'NEWLINE'
            if not (name == 'CF_RETURN' and nxt in ('NEWLINE', 'SEMICOLON', 'EOF')) and \
                    not (name == 'PR_EXPORT' and nxt == 'PARENTHESIS_OPEN'):
                cur.append(' ')
        elif name == 'COMMA':
            cur.append(', ')
        elif name == 'COLON':
            cur.append(': ')
        elif name in PUNCT:
            sym = PUNCT[name]
            if name == 'PARENTHESIS_OPEN' and prev == 'PR_EXPORT':
                pass
            elif name in ('PARENTHESIS_OPEN', 'BRACKET_OPEN', 'CURLY_BRACKET_OPEN') and prev in VALUE_END \
                    and name == 'CURLY_BRACKET_OPEN':
                sp()
            elif name == 'DOLLAR' and prev in VALUE_END:
                sp()
            if name in ('PARENTHESIS_CLOSE', 'BRACKET_CLOSE', 'CURLY_BRACKET_CLOSE', 'PERIOD', 'SEMICOLON') \
                    and text_so_far().endswith(' ') and not text_so_far().endswith(': ') or \
                    (name in ('PARENTHESIS_CLOSE', 'BRACKET_CLOSE', 'CURLY_BRACKET_CLOSE') and text_so_far().endswith(', ')):
                while cur and cur[-1].endswith(' '):
                    cur[-1] = cur[-1].rstrip(' ')
                    if not cur[-1]: cur.pop()
                    else: break
            if name == 'SEMICOLON':
                cur.append('; ')
            else:
                cur.append(sym)
            if name == 'DOLLAR': dollar = True
        else:
            raise ValueError('unhandled token %s' % name)
        prev = name
    if cur: flush()
    while out and out[-1] == '': out.pop()
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    print(decompile(open(sys.argv[1], 'rb').read()), end='')
