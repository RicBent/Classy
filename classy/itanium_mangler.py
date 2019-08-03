# If you want to stay sane, better close this file ;)

PREFIX = '_Z'

DECORS = {
    '*': 'P',
    '&': 'R',
    'const': 'K'
}

MULTI_SEGMENT_TYPES = [
    ['signed', 'char'],
    ['unsigned', 'char'],
    ['signed', 'short'],
    ['unsigned', 'short'],
    ['signed', 'int'],
    ['unsigned', 'int'],
    ['signed', 'long'],
    ['unsigned', 'long'],
    ['long', 'long'],
    ['signed', 'long', 'long'],
    ['unsigned', 'long', 'long'],
]
MULTI_SEGMENT_TYPES.sort(key=len, reverse=True)

BUILTIN_TYPES = {
    'void': 'v',
    'wchar_t': 'w',
    'bool': 'b',
    'char': 'c',
    'signed_char': 'a',
    'unsigned_char': 'h',
    'short': 's',
    'signed_short': 's',
    'unsigned_short': 't',
    'int': 'i',
    'signed_int': 'i',
    'unsigned_int': 'j',
    'long': 'l',
    'signed_long': 'l',
    'unsigned_long': 'm',
    'long_long': 'x',
    'signed_long_long': 'x',
    'unsigned_long_long': 'y',
    'float': 'f',
    'double': 'd',
}

CTOR_TYPES = [
    '',
    '',
    ''
]


def encode_seqid(seqid):
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    if seqid == 0:
        return 'S_'

    seqid -= 1
    base36 = ''

    while seqid:
        seqid, i = divmod(seqid, 36)
        base36 = alphabet[i] + base36

    return 'S' + (base36 or '0') + '_'


def check_identifier(ident):

    if len(ident) == 0:
        return False

    for c in ident:
        if not c.isalnum() and not c == '_':
            return False

    if ident[0].isdigit():
        return False

    return True


def brace_split(txt, char=' ', remove_empty=True):

    braces = {
        '(': ')',
        '<': '>'
    }

    brace_stack = []

    segs = []
    curr_seg = ''

    for c in txt:
        if len(brace_stack):
            if c == brace_stack[-1]:
                brace_stack.pop()

        if c in braces.keys():
            brace_stack.append(braces[c])

        if not len(brace_stack) and c == char:
            if not remove_empty or curr_seg:
                segs.append(curr_seg)
                curr_seg = ''
        else:
            curr_seg += c

    if curr_seg or (not remove_empty and len(segs)):
        segs.append(curr_seg)

    if len(brace_stack):
        raise ValueError('Mismatched braces')

    return segs


def len_encode(ident):
    return "%u%s" % (len(ident), ident)


def apply_typedefs(segs, typedefs):
    idx = 0
    while idx < len(segs):
        s = segs[idx]
        if s in typedefs:
            del segs[idx]
            new_segs = typedefs[s].split()
            while len(new_segs):
                segs.insert(idx, new_segs.pop(0))
                idx += 1
        else:
            idx += 1


def fix_multi_seg_types(segs):
    for l in range(len(segs)):
        for mst in MULTI_SEGMENT_TYPES:
            r = l + len(mst)
            if mst == segs[l:r]:
                del segs[l:r]
                segs.insert(l, '_'.join(mst))
                break


def mangle_type(txt, pre_and_postfix=True):

    if txt in BUILTIN_TYPES.keys():
        return BUILTIN_TYPES[txt]

    segs = txt.split('::')

    if len(segs) == 1:
        return len_encode(segs[0])

    ret = 'N' if pre_and_postfix else ''
    for s in segs:
        ret += len_encode(s)
    if pre_and_postfix:
        ret += 'E'

    return ret


def add_to_subs(subs, sub):
    if sub in subs:
        raise ValueError('Substitution "%s" is already registered' % sub)
    subs[sub] = encode_seqid(len(subs))


# Oh boy, this hurts... This is literally the WORST function I ever wrote in my life. CLEAN IT UP
# Todo: Allow templates
def mangle_decorated_type(txt_decors, type_txt, subs=None):
    if subs is None:
        subs = {}

    type_segs = type_txt.split('::')
    if not len(type_segs):
        raise ValueError('Type is empty')

    decors = []
    for d in txt_decors:
        try:
            decors.append(DECORS[d])
        except KeyError:
            raise ValueError('Invalid decor "%s"' % d)
    decors.reverse()


    if type_segs[-1] in BUILTIN_TYPES:
        if len(type_segs) > 1:
            raise ValueError('Builtin type may not be namespaced!')
        ret = BUILTIN_TYPES[type_segs[-1]]

        for i in range(len(decors) + 1):
            curr_mangled_nosubs = ''.join(decors[i:]) + ret
            # print('Testing for ' + curr_mangled_nosubs)

            start_backtrack = False

            if i == len(decors):        # No substitutions found
                start_backtrack = True
            if curr_mangled_nosubs in subs:
                # print('Found ' + curr_mangled_nosubs + ' as ' + subs[curr_mangled_nosubs])
                ret = subs[curr_mangled_nosubs]
                start_backtrack = True

            if start_backtrack:
                while i:
                    # print('Backtracking ' + decors[i - 1])
                    ret = decors[i - 1] + ret
                    curr_mangled_nosubs = decors[i - 1] + curr_mangled_nosubs
                    add_to_subs(subs, curr_mangled_nosubs)
                    # print(subs)
                    i -= 1
                break

        return ret


    type_mangled_stripped = mangle_type(type_txt, False)

    if type_mangled_stripped in subs:
        for i in range(len(decors) + 1):
            # print('Testing for decors ' + ''.join(decors[i:]))
            curr_mangled = ''.join(decors[i:]) + type_mangled_stripped
            if curr_mangled in subs:
                # print('Found ' + curr_mangled + ' as ' + subs[curr_mangled])
                ret = subs[curr_mangled]
                while i:
                    ret = decors[i-1] + ret
                    curr_mangled = decors[i-1] + curr_mangled
                    add_to_subs(subs, curr_mangled)
                    # print(subs)
                    i -= 1
                break
        return ret


    curr_mangled = ''
    curr_mangled_nosubs = ''

    # New found names are added to substitution from the left
    for i in reversed(range(len(type_segs) + 1)):
        curr_mangled_nosubs = ''.join(len_encode(ts) for ts in type_segs[:i])
        # print('Testing for names ' + '::'.join(type_segs[:i]) + ' (' + curr_mangled_nosubs + ')')

        if not curr_mangled_nosubs or curr_mangled_nosubs in subs:
            if curr_mangled_nosubs:
                # print('Found ' + curr_mangled_nosubs + ' as ' + subs[curr_mangled_nosubs])
                curr_mangled = subs[curr_mangled_nosubs]
            else:
                curr_mangled = ''
                # print('Did not find any substitution')
            while i < len(type_segs):
                curr_mangled += len_encode(type_segs[i])
                curr_mangled_nosubs += len_encode(type_segs[i])
                add_to_subs(subs, curr_mangled_nosubs)
                # print(subs)
                i += 1
            break

    if len(type_segs) == 1:
        ret = curr_mangled
    else:
        ret = 'N' + curr_mangled + 'E'

    for d in reversed(decors):
        ret = d + ret
        curr_mangled = d + curr_mangled
        curr_mangled_nosubs = d + curr_mangled_nosubs
        add_to_subs(subs, curr_mangled_nosubs)
        # print(subs)


    return ret


# Cleans up raw txt argument: Removes the label, parses decors
def mangle_argument(txt, typedefs=None, subs=None):
    if typedefs is None:
        typedefs = {}

    if subs is None:
        subs = {}

    if '(' in txt:
        raise NotImplementedError('Function pointers are not supported')
    if '<' in txt:
        raise NotImplementedError('Templates are not supported')
    if '&&' in txt:
        raise NotImplementedError('r-value reference are not supported')

    # Prepare text for space splitting
    txt = txt.replace('&', ' & ')
    txt = txt.replace('*', ' * ')

    segs = brace_split(txt)

    apply_typedefs(segs, typedefs)

    # Fix multi segment types for easier parsing
    fix_multi_seg_types(segs)

    # Check for pre-const: Belongs to first * or &, const without * or & is omitted
    if len(segs) != 0 and segs[0] == 'const':
        idx = -1
        for i in range(1, len(segs)):
            x = segs[i]
            if x == 'const':
                raise ValueError('Multiple const')
            if x in ['*', '&']:
                idx = i
                break

        if idx != -1:
            segs.insert(idx, 'const')
        del segs[0]

    # Current segment layout: type, decors, optional label

    # Filter out label
    if len(segs) >= 2:
        if not segs[-1] in DECORS.keys():   # Already no label?
            if not check_identifier(segs[-1]):
                raise ValueError('Invalid identifier "%s"' % segs[-1])
            if segs[-1] in BUILTIN_TYPES:
                raise ValueError('Invalid identifier "%s"' % segs[-1])
            del segs[-1]

    # Check decors
    decors = segs[1:]

    if len(decors) and decors[-1] == 'const':
        del decors[-1]

    if not len(segs):
        raise ValueError('No argument type')

    return mangle_decorated_type(decors, segs[0], subs)


# Mangles the entire text inside argument braces.
def mangle_arguments(txt, typedefs=None, subs=None):
    if typedefs is None:
        typedefs = {}

    if subs is None:
        subs = {}

    args = brace_split(txt, ',', False)

    args = [a.strip() for a in args]

    # Detect void arguments
    if not len(args) or (len(args) == 1 and (not args[0] or args[0] == 'void')):
        return 'v'

    ret = ''
    for a in args:
        ret += mangle_argument(a, typedefs, subs)
    return ret


# Basically the main function of all this
def mangle_function(txt, typedefs=None, ctor_type=None, dtor_type=None):
    if typedefs is None:
        typedefs = {}

    left_brace_idx = txt.find('(')
    right_brace_idx = txt.rfind(')')

    if left_brace_idx < 0 or right_brace_idx < 0 or left_brace_idx > right_brace_idx:
        raise ValueError('Finding argument braces failed')

    # Check identifier
    pre_brace_segs = txt[:left_brace_idx].split()

    if len(pre_brace_segs) < 1:
        raise ValueError('No function identifier found')

    identifier = pre_brace_segs[-1]

    # Arguments
    arguments = txt[left_brace_idx+1:right_brace_idx]

    # Decors
    post_brace_segs = txt[right_brace_idx + 1:].split()


    subs = {}

    ret = PREFIX

    identifier_segs = identifier.split('::')
    is_cdtor = False

    # Check for ctors and dtors
    if len(identifier_segs) >= 2:
        if identifier_segs[-1] == identifier_segs[-2]:              # ctor
            if ctor_type not in [1, 2, 3]:
                raise ValueError('No or invalid ctor type given')
            identifier_segs[-1] = 'C%u' % ctor_type
            is_cdtor = True
        elif identifier_segs[-1] == ('~' + identifier_segs[-2]):    # dtor
            if dtor_type not in [0, 1, 2]:
                raise ValueError('No or invalid dtor type given')
            identifier_segs[-1] = 'D%u' % dtor_type
            is_cdtor = True

    for s in identifier_segs:
        if not check_identifier(s):
            raise ValueError('Invalid identifier "%s"' % s)

    mangled_type = ''.join(len_encode(ts) for ts in identifier_segs[:len(identifier_segs)-1])
    mangled_type += identifier_segs[-1] if is_cdtor else len_encode(identifier_segs[-1])

    if 'const' in post_brace_segs:
        if len(identifier_segs) < 2:
            raise ValueError('Function outside struct/class may not be const')
        mangled_type = 'K' + mangled_type
    if len(identifier_segs) > 1:
        mangled_type = 'N' + mangled_type + 'E'
    ret += mangled_type

    for i in range(1, len(identifier_segs)):
        add_to_subs(subs, ''.join(len_encode(ts) for ts in identifier_segs[:i]))

    ret += mangle_arguments(arguments, typedefs, subs)

    return ret
