#!/usr/bin/env python3
"""LC76 Field Handbook (Volume II) — build the print PDF from the live library, in ONE fixed template.
Usage: build_book.py <repo_dir> <book_map> <out_dir> <fonts_dir>

Template v2 (24 Nov 2026). No library page CSS is carried into the book. Every element of a
library page is turned into one of the template blocks in template.css:
  opener · h2 · h3 · h4 · paragraph · bullet list (plain / ✓✗ / decision flow) · numbered steps ·
  notice (DANGER / WARNING / CAUTION / NOTICE / NOTE) · table · checklist · spec rows · fault card · figure
Anything the converter cannot place is written to unplaced.txt for the owner — never given a style of its own.

Book map line:  source | title in the book | edge-tab colour | flags
  source  R-number, R29#section-id, a library filename, INTRO, or PART
  flags   drop:id,id   keep:id,id (only these sections)   trim:id=N (first N cards of a section)
          num:N (chapter number to print)   small (8.5pt)   nonotes
Outputs: <out>/LC76_Field_Handbook.pdf, book.html, conversion_report.txt, unplaced.txt,
         notices.txt (every notice and the signal word it got), numbers.txt (every number vs its source).
Nothing in the library is changed."""
import sys, re, os, subprocess, datetime, html as H
from collections import Counter
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

repo, bookmap, out, fonts = sys.argv[1:5]
HERE = os.path.dirname(os.path.abspath(__file__))
reg = open(os.path.join(repo, 'LC76_Library_Register.txt'), encoding='utf-8').read()
RFILE = {m.group(1): m.group(2) for m in re.finditer(r'^\s+(R\d+)\s+(\S+\.html)', reg, re.M)}
report, unplaced, notices_log, removed = [], [], [], []

def load(f):
    return BeautifulSoup(open(f, encoding='utf-8'), 'lxml')

def page_title(f):
    s = load(os.path.join(repo, f))
    t = s.find(class_=['std-title', 'mh-title'])
    return t.get_text(' ', strip=True) if t else (s.title.get_text(strip=True) if s.title else f)

# ---------------- book map ----------------
chapters = []
for line in open(bookmap, encoding='utf-8'):
    line = line.strip()
    if not line or line.startswith('#'): continue
    cols = [x.strip() for x in line.split('|')]
    r, title, colour = cols[:3]
    flags = cols[3:]
    def flag(name):
        return next((f.split(':', 1)[1] for f in flags if f.startswith(name + ':')), None)
    if r == 'PART':
        chapters.append(dict(r=r, title=title, colour=colour, part=True, num=flag('num'))); continue
    sec = None
    if '#' in r: r, sec = r.split('#', 1)
    f = RFILE.get(r) or (r if r.endswith('.html') else None)
    trim = {}
    for f2 in flags:
        if f2.startswith('trim:'):
            k, v = f2[5:].split('='); trim[k] = int(v)
    chapters.append(dict(r=r, title=title, colour=colour, file=f, section=sec,
                         drop=(flag('drop') or '').split(',') if flag('drop') else [],
                         keep=(flag('keep') or '').split(',') if flag('keep') else [],
                         trim=trim, num=flag('num'), small='small' in flags, nonotes='nonotes' in flags,
                         sheet='sheet' in flags, prose='prose' in flags, nobanner='nobanner' in flags))
chs_only = [c for c in chapters if not c.get('part')]
for i, c in enumerate(chs_only):
    c['n'] = i + 1
    c['label'] = c['num'] or str(i + 1)
INBOOK = {c['r']: c['n'] for c in chs_only if not c.get('section')}
BYN = {c['n']: c for c in chs_only}
TITLES = {}
def rtitle(r):
    if r not in TITLES:
        TITLES[r] = page_title(RFILE[r]) if r in RFILE and os.path.exists(os.path.join(repo, RFILE[r])) else 'the live library'
    return TITLES[r]

# ---------------- text cleaning (library codes -> plain words) ----------------
EMOJI = re.compile('[\U0001F000-\U0001FAFF☀-⛿✀-➿⬀-⯿️‍⌀-⏿]')
KEEP_SYM = {'✓': '✓', '✔': '✓', '✅': '✓', '❌': '✗', '✗': '✗', '✘': '✗', '✕': '✗'}
# symbols that carry meaning in the library (checked across every page, 24 Nov 2026); everything else in the
# emoji ranges is decoration and is dropped
MEAN_SYM = {'☐': '<span class="sym">☐</span>', '★': '<span class="sym star">★</span>', '⚠': '<span class="sym">⚠</span>',
            '🟢': '<span class="sym dot" style="color:#15803D">●</span>', '🟡': '<span class="sym dot" style="color:#CA8A04">●</span>',
            '🟠': '<span class="sym dot" style="color:#EA580C">●</span>', '🔴': '<span class="sym dot" style="color:#DC2626">●</span>',
            '🔵': '<span class="sym dot" style="color:#2563EB">●</span>'}
MEAN_LIST = list(MEAN_SYM)
def clean_text(t, ch):
    o = t
    # governance-only brackets go: owner-ruling dates, evidence grades, session tags
    t = re.sub(r'\s*\(owner(?:\s+rulings?)?(?:,\s*\d{1,2}\s+[A-Z][a-z]+\s+\d{4})?\)', '', t)
    t = re.sub(r'\(owner(?:\s+rulings?)?,\s*\d{1,2}\s+[A-Z][a-z]+\s+\d{4};\s*', '(', t)   # '(owner, 18 Nov 2026; Facts §8)' -> '(Facts §8)'
    t = re.sub(r'\s*\((?:E[1-5](?:/E[1-5])*|S\d+[a-z]?)\)', '', t)
    # a bracket that also says something keeps its words; only the codes come out
    def par(m):
        inner = re.sub(r'(?<=:)\s*\b(?:OI|RA)-\d+\b', ' not yet confirmed', m.group(2))
        inner = re.sub(r'\s*[—–,;]?\s*\b(?:OI|RA)-\d+\b(?:\s+verification)?', '', inner)
        inner = re.sub(r'\s*\bEX-\d+\b', '', inner).strip(' ,;—–')
        if inner != m.group(2): removed.append(f'{ch["r"]}: ({m.group(2)})  ->  ' + (f'({inner})' if inner else '[removed]'))
        return f'{m.group(1)}({inner})' if inner else ''
    t = re.sub(r'(\s*)\(([^()]*\b(?:OI|RA|EX)-\d+[^()]*)\)', par, t)
    def rref(m):
        r = m.group(1)
        if r not in RFILE: return m.group(0)
        sec = re.sub(r'[^\d.]', '', m.group(2) or '')
        if r in INBOOK: return f'‹{r}›' + (f', section {sec}' if sec else '')   # a section pointer is kept: 'R40 §8' -> chapter (p. n), section 8
        return f'{rtitle(r)}' + (f', library section {sec}' if sec else '')
    t = re.sub(r'(?<!Rimula )\b(R\d{1,2})\b(?![,.]\d)(\s*§\s*[\d.]+)?', rref, t)   # never a rand amount (R30,000), never the oil 'Shell Rimula R4 X'
    # the library sometimes names the page after its code: 'R17 (Health & Hygiene)' would print the title twice
    for r in set(re.findall(r'(?<!Rimula )\b(R\d{1,2})\b(?![,.]\d)', o)):
        if r in RFILE and r not in INBOOK:
            ti = re.escape(rtitle(r))
            t = re.sub(r'(' + ti + r')\s*\(\s*' + ti + r'\s*\)', r'\1', t)
            t = re.sub(r'(' + ti + r')\s+' + ti + r'\b', r'\1', t)
    t = re.sub(r'\bis RA-\d+\b', 'is still to do', t)
    t = re.sub(r'\s*\bRA-\d+\b', '', t)
    t = re.sub(r'\((E[1-5](?:/E[1-5])*),\s*', '(', t)
    t = re.sub(r'\bOI-\d+\b', 'not yet confirmed', t)
    t = re.sub(r'\s*\bEX-\d+\b', '', t)
    t = re.sub(r'§\s*(\d+)', r'section \1', t)
    if t != o:
        for code in set(re.findall(r'\b(?:R\d{1,2}(?![,.]\d)|OI-\d+|RA-\d+|EX-\d+)\b', o)):
            report.append(f'{ch["r"]}: replaced {code}')
    return t

def text_of(s, ch):
    s = str(s)
    s = re.sub('[' + ''.join(KEEP_SYM) + ']', lambda m: '\x00' + ('Y' if KEEP_SYM[m.group(0)] == '✓' else 'N') + '\x01', s)
    s = re.sub('|'.join(MEAN_LIST), lambda m: f'\x00M{MEAN_LIST.index(m.group(0))}\x01', s)
    s = EMOJI.sub('', s)
    s = re.sub(r'[ \t\r\n]+', ' ', s)
    s = H.escape(clean_text(s, ch), quote=False)
    s = s.replace('\x00Y\x01', '<span class="sym">✓</span>').replace('\x00N\x01', '<span class="sym">✗</span>')
    return re.sub('\x00M(\\d+)\x01', lambda m: MEAN_SYM[MEAN_LIST[int(m.group(1))]], s)

INLINE_KEEP = {'strong': 'strong', 'b': 'strong', 'em': 'em', 'i': 'em', 'sup': 'sup', 'sub': 'sub', 'br': 'br'}
def inline(node, ch):
    """Inline content -> text + strong/em/sup/sub/br only."""
    outp = []
    for k in node.children:
        if isinstance(k, Comment): continue
        if isinstance(k, NavigableString): outp.append(text_of(k, ch)); continue
        if not isinstance(k, Tag): continue
        if k.name in ('input', 'svg', 'script', 'style', 'button'): continue
        if k.name == 'br': outp.append('<br>'); continue
        if k.name == 'cite': outp.append(f'<br><span class="cite">— {squash(inline(k, ch))}</span>'); continue
        cls = k.get('class') or []
        if any(c in ('status-critical', 'status-warn', 'status-ok') for c in cls):
            t = k.get_text(strip=True)
            if t in KEEP_SYM or EMOJI.sub('', t) == '':
                outp.append(text_of(t, ch)); continue
            tag = {'status-critical': 'crit', 'status-warn': 'warn', 'status-ok': 'ok'}[next(c for c in cls if c.startswith('status-'))]
            outp.append(f'<span class="{tag}">{text_of(t, ch)}</span>'); continue
        # a label span run straight into its note span ('...water.</span><span>They...') reads as one word: keep a space
        gap = ' ' if any(c.endswith('label') for c in cls) and isinstance(k.next_sibling, Tag) else ''
        if gap:
            outp.append(squash(inline(k, ch)) if k.name not in INLINE_KEEP else f'<{INLINE_KEEP[k.name]}>{inline(k, ch)}</{INLINE_KEEP[k.name]}>')
            outp.append(gap); continue
        if k.name in INLINE_KEEP:
            t = INLINE_KEEP[k.name]; inner = inline(k, ch)
            outp.append(f'<{t}>{inner}</{t}>' if inner.strip() else inner)
        else:
            outp.append(inline(k, ch))
    return ''.join(outp)

def squash(h):
    h = re.sub(r'\s+', ' ', h).strip()
    h = re.sub(r'^(?:\s*<br>)+|(?:<br>\s*)+$', '', h)
    return h

# ---------------- blocks ----------------
# a block is (html, kind) — kind: 'wide' (full width), 'head' (heading; stays with what follows), 'body'
NOTICE_CLASSES = {'danger-box': 'warning', 'warning-box': 'warning', 'warn-box': 'warning', 'rule-warn': 'warning',
                  'highlight-box': 'note', 'tip-box': 'note', 'info-box': 'note', 'note-box': 'note', 'rule-info': 'note',
                  'ok-box': 'note', 'rule-ok': 'note', 'rule-note': 'note',
                  'comp-warn': 'warning', 'fix-warn': 'warning', 'how-warn': 'warning', 'comp-card-note': 'note',
                  'alert-warn': 'warning', 'alert-info': 'note', 'alert-note': 'note', 'alert-ok': 'note'}
WORDS = {'DANGER': 'danger', 'WARNING': 'warning', 'CAUTION': 'caution', 'NOTICE': 'notice', 'NOTE': 'note'}
PEOPLE = re.compile(r'\b(kill|death|die|dies|died|fatal|injur|hurt|burn|person|people|anyone|bystander|crew|hand|finger|body|head|eye|breath|bleed|life|lives|casualty|patient|you)\w*', re.I)

def notice(node, ch, kind):
    for hdr in node.find_all(class_='rule-hdr'):
        hdr.name = 'strong'; hdr.attrs = {}
        if hdr.next_sibling is not None and not str(hdr.next_sibling).startswith((' ', '\n')): hdr.append(' ')
    txt = node.get_text(' ', strip=True)
    word = None
    m = re.match(r'^\W*(DANGER|WARNING|CAUTION|NOTICE|NOTE)\b\s*[:—–-]?', txt, re.I)
    body_nodes = [k for k in node.children if not (isinstance(k, NavigableString) and not k.strip()) and not isinstance(k, Comment)]
    html_parts, run = [], []
    def flush_run():
        if run:
            frag = BeautifulSoup('<x>' + ''.join(str(r) for r in run) + '</x>', 'lxml').x
            t = squash(inline(frag, ch))
            if t.strip(' .,;:'): html_parts.append(f'<p>{t}</p>')
            run.clear()
    for k in body_nodes:
        if isinstance(k, Tag) and k.name in ('p', 'ul', 'ol', 'div', 'table'):
            flush_run(); html_parts += [b[0] for b in blocks(k, ch)]
        else:
            run.append(k)
    flush_run()
    body = ''.join(html_parts)
    body = re.sub(r'^(<p>(?:<strong>)?)\s*<span class="sym">⚠</span>\s*', r'\1', body)
    if m:
        word = WORDS[m.group(1).upper()]
        # remove the signal word the library wrote in the text: the bar carries it
        body = re.sub(r'^(<p>)(?:<strong>)?\s*' + m.group(1) + r'\s*[:—–-]?\s*(?:</strong>)?\s*[:—–-]?\s*', r'\1', body, count=1, flags=re.I)
        body = re.sub(r'^<p><strong>\s*</strong>\s*', '<p>', body)
    else:
        word = kind
    src = 'library wrote ' + m.group(1).upper() if m else f'from box class ({node.get("class")[0]})'
    flagtxt = ''
    if word in ('danger', 'warning') and not PEOPLE.search(txt):
        flagtxt = '  << about the vehicle only? owner to rule: WARNING or NOTICE'
    notices_log.append(f'{ch["r"]}  {word.upper():8} {src:32} {txt[:110]}{flagtxt}')
    sym = '<span class="sym">⚠</span>' if word in ('danger', 'warning', 'caution') else ''
    return f'<div class="notice n-{word}"><div class="nbar">{sym}{word.upper()}</div><div class="nbody">{body}</div></div>'

def table(node, ch):
    rows = node.find_all('tr')
    ncols = max((len(r.find_all(['th', 'td'])) for r in rows), default=0)
    outp = ['<table>']
    th = node.find('thead')
    for r in rows:
        cells = r.find_all(['th', 'td'])
        tag_row = ''.join(f'<{c.name}{" colspan=" + chr(34) + c["colspan"] + chr(34) if c.get("colspan") else ""}>{squash(inline(c, ch))}</{c.name}>' for c in cells)
        if th is not None and r.find_parent('thead') is th:
            outp.append(f'<thead><tr>{tag_row}</tr></thead>')
        else:
            outp.append(f'<tr>{tag_row}</tr>')
    outp.append('</table>')
    return ''.join(outp), ('wide' if ncols >= 3 else 'body')

def li_html(li, ch):
    parts = []
    for k in li.children:
        if isinstance(k, Tag) and k.name in ('ul', 'ol'):
            parts.append(list_html(k, ch))
        elif isinstance(k, Tag) and k.name in ('p', 'div'):
            parts.append(squash(inline(k, ch)) + ' ')
        elif isinstance(k, Comment): continue
        elif isinstance(k, Tag): parts.append(inline(BeautifulSoup(f'<x>{k}</x>', 'lxml').x, ch))
        else: parts.append(text_of(k, ch))
    return squash(''.join(parts))

NUMCLS = re.compile(r'(^|-)num$')
def numbered_li(li):
    """An <li> that carries its own number in a *-num element (cause-list, checklist and the like)."""
    return li.find(class_=lambda c: c and NUMCLS.search(c)) is not None
def cause_list(node, ch):
    items = []
    for li in node.find_all('li', recursive=False):
        n = li.find(class_=lambda c: c and NUMCLS.search(c))
        nv = n.get_text(strip=True) if n else ''
        if n is not None: n.extract()
        # every word of the item is kept: the label in bold, then everything after it (a note span or loose text)
        for lab in li.find_all(class_=['cause-label', 'cl-label']):
            lab.name = 'strong'; lab.attrs = {}
            nx = lab.next_sibling
            if nx is not None and not (isinstance(nx, NavigableString) and str(nx)[:1].isspace()): lab.append(' ')
        t = squash(inline(li, ch))
        items.append(f'<li value="{nv}">{t}</li>' if nv.isdigit() else f'<li>{t}</li>')
    return '<ol>' + ''.join(items) + '</ol>'

def list_html(node, ch):
    lis = node.find_all('li', recursive=False)
    if 'cause-list' in (node.get('class') or []) or (lis and all(numbered_li(li) for li in lis)): return cause_list(node, ch)
    if node.name == 'ol':
        oc = node.get('class') or []
        cls = ' class="key"' if 'rig-key' in oc else (' class="refl"' if 'reflist' in oc else '')
        items = ''.join(f'<li{" value=" + chr(34) + li["value"] + chr(34) if li.get("value") else ""}>{li_html(li, ch)}</li>' for li in node.find_all('li', recursive=False))
        return f'<ol{cls}>{items}</ol>'
    items = []
    for li in node.find_all('li', recursive=False):
        t = li_html(li, ch)
        sub = re.match(r'^(?:<em>|<strong>)?\s*[—–]\s', t)   # the library marks a sub-item with a typed dash
        if 'uppercase' in (li.get('style') or '') and not li.find(True):   # a group label inside the list (R11 open questions)
            items.append(f'<li class="gh">{t}</li>'); continue
        items.append(f'<li class="sub">{t}</li>' if sub else f'<li>{t}</li>')
    return '<ul>' + ''.join(items) + '</ul>'

PRINT_COLOURS = {'#2a2f3a': '#ffffff', '#1c2030': '#f4f5f7', '#a8b0bc': '#0d0e12', '#6a7080': '#4a505c', '#e07800': '#b86800'}
def figure(svg, ch):
    cap = svg.get('aria-label') or ''
    r0 = svg.find('rect')
    if r0 is not None and (r0.get('fill') or '').lower() in ('#2a2f3a', '#0d0e12', '#1c2030'):
        # a drawing made for a dark screen: printed on white with dark text (template rule: no light text on dark);
        # every line, box and label is kept, only the colours change
        for x in svg.find_all(True):
            a = 'fill' if x.name in ('rect', 'text', 'tspan') else None
            if a and (x.get(a) or '').lower() in PRINT_COLOURS: x[a] = PRINT_COLOURS[x[a].lower()]
        report.append(f'{ch["r"]}: dark-background drawing recoloured for print: {cap[:60]}')
    for a in list(svg.attrs):
        if a.startswith('on') or a in ('class', 'style', 'role'): del svg[a]
    vb = (svg.get('viewbox') or svg.get('viewBox') or '').split()
    tall = ''
    if len(vb) == 4 and float(vb[2]) >= 480 and float(vb[3]) > float(vb[2]):   # a large upright plan (R11 layouts): its labels need the height
        svg['style'] = 'max-height:165mm'; tall = ' tall'
    return f'<div class="figure{tall}">{svg}' + (f'<div class="cap">{text_of(cap, ch)}</div>' if cap else '') + '</div>'

def legend(node, ch):
    parts = []
    for sp in node.find_all('span', recursive=False):
        i = sp.find('i'); st = i.get('style', '') if i else ''
        st = '; '.join(x for x in st.split(';') if x.strip().split(':')[0].strip() in ('background', 'height', 'width', 'border', 'border-radius'))
        parts.append(f'<span><i style="{H.escape(st)}"></i>{text_of(sp.get_text(" ", strip=True), ch)}</span>')
    return '<div class="legend">' + ''.join(parts) + '</div>'

STEP_NUM = re.compile(r'^\s*(\d+)[.)]\s*')
def group_steps(divs, ch):
    texts = [squash(inline(d, ch)) for d in divs]
    plain = [re.sub(r'<[^>]+>', '', t) for t in texts]
    if all(STEP_NUM.match(p) for p in plain):
        items = []
        for t, p in zip(texts, plain):
            n = STEP_NUM.match(p).group(1)
            t = re.sub(r'^(?:<strong>)?\s*' + n + r'[.)]\s*(?:</strong>)?\s*', '', t)
            items.append(f'<li value="{n}">{t}</li>')
        return '<ol>' + ''.join(items) + '</ol>'
    items = []
    for t, p in zip(texts, plain):
        mm = re.match(r'^\s*(↓|→)\s*', t)
        if mm:
            g = mm.group(1); t = t[mm.end():]
            items.append(f'<li class="{"out" if g == "→" else "dn"}"><span class="mk">{g}</span>{t}</li>')
        else:
            items.append(f'<li><span class="mk"></span>{t}</li>')
    return '<ul class="flow">' + ''.join(items) + '</ul>'

def group_marks(ps, ch):
    items = []
    for p in ps:
        t = squash(inline(p, ch))
        mm = re.match(r'^(<strong>)?\s*<span class="sym">(✓|✗)</span>\s*', t)
        if not mm:
            unplaced.append(f'{ch["r"]}: mark paragraph not parsed: {t[:80]}'); items.append(f'<li><span class="mk"></span>{t}</li>'); continue
        g = mm.group(2); t = (mm.group(1) or '') + t[mm.end():]
        items.append(f'<li><span class="mk {"yes" if g == "✓" else "no"}">{g}</span>{t}</li>')
    return '<ul class="mark">' + ''.join(items) + '</ul>'

BULLET_P = re.compile(r'^\s*[•·▪‣]\s+')
def is_bullet_p(k):
    return isinstance(k, Tag) and k.name == 'p' and bool(BULLET_P.match(k.get_text()))

def group_bullets(ps, ch):
    items = []
    for p in ps:
        t = squash(inline(p, ch))
        t = re.sub(r'^((?:<strong>|<em>)?)\s*[•·▪‣]\s+', r'\1', t, count=1)
        items.append(f'<li>{t}</li>')
    return '<ul>' + ''.join(items) + '</ul>'

def group_check(divs, ch):
    return '<ul class="check">' + ''.join(f'<li><span class="box"></span>{squash(inline(d, ch))}</li>' for d in divs) + '</ul>'

def is_mark_p(k):
    if not (isinstance(k, Tag) and k.name == 'p'): return False
    first = next((c for c in k.children if not (isinstance(c, NavigableString) and not c.strip())), None)
    if first is None: return False
    t = first.get_text(strip=True) if isinstance(first, Tag) else str(first).strip()
    return any(t.startswith(s) for s in KEEP_SYM)

WRAPPERS = {'card-grid', 'two-col', 'three-col', 'card-body', 'grid', 'sa', 'diag-group', 'matrix-scroll',
            'table-wrap', 'tbl-wrap', 'smoke-grid', 'use-row', 'content', 'main', 'section', 'refs-block',
            'principle-grid', 'terrain-grid', 'table-scroll', 'three-q', 'risk-band', 'sensor-grid', 'grid2', 'check-steps',
            'flow-steps', 'material-grid', 'tree-indent', 'diag-group', 'stat-row', 'p-body', 'q-note', 'tree-wrap',
            # batch 4 (Part 3) wrappers: grids and bodies whose children are mapped one by one
            'components-grid', 'comp-body', 'comp-desc-block', 'comp-tip-block', 'comp-content', 'comp-grid', 'protocol-list',
            'ss-fig', 'how-grid', 'how-scroll', 'how-diagram', 'intro-panel', 'info-grid', 'info-body', 'rule-body',
            'weak-grid', 'qual-grid', 'fix-grid', 'fix-body', 'chem-grid', 'sym-grid', 'formula-strip', 'soc-container',
            'ohm-desc', 'ohm-rule', 'fluid-table-section', 'ref-section', 'ohm-tri', 'diagram-wrap',
            # batch 5 (Part 4) wrappers
            'container', 'task-list', 'decision-grid', 'prov-grid', 'proto-steps', 'stack-wrap', 'checklist', 'scope', 'cal-scroll',
            'inline-grid-2col', 'inline-grid-3col', 'cascade-body', 'cc-body', 'fluid-grid', 'zone-grid'}
def blocks(node, ch, alert=False):
    """Return a list of (html, kind) for a block-level node."""
    if isinstance(node, Comment): return []
    if isinstance(node, NavigableString):
        t = text_of(node, ch).strip()
        return [(f'<p>{t}</p>', 'body')] if t else []
    cls = set(node.get('class') or [])
    name = node.name
    if name in ('script', 'style', 'button', 'input', 'nav', 'noscript'): return []
    if name == 'h2':
        t = text_of(node.get_text(' ', strip=True), ch).strip()
        m = re.match(r'^(\d+)\.\s*(.*)$', t)
        pend = ch.pop('pending_num', None)          # a 'Section 3' label printed above this h2
        num, title = (m.group(1), m.group(2)) if m else (pend, t)
        res = [(f'<h2><span class="h2-n">{num}</span>{title}</h2>' if num else f'<h2 class="non">{title}</h2>', 'wide')]
        psub = ch.pop('pending_sub', None)   # the label's own words ('§1 Engine · Oil-Sealing Surfaces')
        if psub and psub.lower() != re.sub(r'<[^>]+>', '', title).strip().lower():   # never the heading's own words again
            res.append((f'<p class="h2sub">{psub}</p>', 'wide'))
        return res
    if name == 'h3' and cls & {'how-h', 'sub-head', 'fixhead'}:   # fixhead: a library h3 naming the untitled card under it   # R4 section 0, R21 section 1: numbered sub-sections ('0.2', '1.6')
        return [(f'<h3>{squash(inline(node, ch))}</h3>', 'head')]
    if name in ('h3', 'h4', 'h5'):
        return [(f'<h4>{squash(inline(node, ch))}</h4>', 'head')]
    if cls & {'section-head', 'sec-header'}:
        num = node.find(class_='sec-num'); title = node.find(class_='sec-title')
        subl = node.find(class_=['sec-sub', 'sec-era'])
        nt = num.get_text(strip=True) if num else ''
        tt = squash(inline(title, ch)) if title else squash(inline(node, ch))
        m = re.match(r'^(\d+)\s*[—–.-]\s*(.*)$', tt) if not num else None
        if m: nt, tt = m.group(1), m.group(2)
        nt = '' if nt in ('§', '') else nt
        res = [(f'<h2><span class="h2-n">{text_of(nt, ch)}</span>{tt}</h2>' if nt else f'<h2 class="non">{tt}</h2>', 'wide')]
        if subl: res.append((f'<p class="h2sub">{squash(inline(subl, ch))}</p>', 'wide'))
        return res
    if 'sub-head' in cls:
        return [(f'<h3>{squash(inline(node, ch))}</h3>', 'head')]
    if 'section-intro' in cls:
        if 'Controlled Duplication' in node.get_text() or ('owning document' in node.get_text() and 'assumption' not in node.get_text()): return []
        return [(f'<p class="lead">{squash(inline(node, ch))}</p>', 'wide')]
    if name == 'p' and 'epigraph' in cls:
        return [(f'<p class="quote">{squash(inline(node, ch))}</p>', 'wide')]
    if name == 'p' and 'lead' in cls:
        return [(f'<p class="lead">{squash(inline(node, ch))}</p>', 'wide')]
    if name == 'p' and 'intro-sign' in cls:
        return [(f'<p class="signoff">{squash(inline(node, ch))}</p>', 'wide')]
    if 'essay-kicker' in cls:
        return [(f'<p class="kicker">{squash(inline(node, ch))}</p>', 'body')]
    if 'closing-banner' in cls and ch.get('nobanner'):   # (owner, 27 Nov 2026: p. 38) the closing banner alone on a page: not printed
        report.append(f'{ch["r"]}: closing banner not printed (owner ruling): {node.get_text(" ", strip=True)[:60]}'); return []
    if 'closing-banner' in cls:
        big = node.find(class_='big-line'); sg = node.find(class_='sign')
        return [(f'<div class="closing"><div class="cl-big">{squash(inline(big, ch)) if big else ""}</div>'
                 f'<div class="cl-sign">{squash(inline(sg, ch)) if sg else ""}</div></div>', 'wide')]
    if cls & {'thinkers', 'note'} and name == 'div':
        lab = node.find(class_=['thinkers-label', 'note-label'])
        lines = node.find_all(class_=['thinker', 'note-line'])
        return [('<div class="aside">' + (f'<div class="as-label">{squash(inline(lab, ch))}</div>' if lab else '')
                 + '<ul>' + ''.join(f'<li>{squash(inline(l, ch))}</li>' for l in lines) + '</ul></div>', 'body')]
    if cls & {'tension', 'callout', 'use-block'}:
        hd = node.find(['h4', 'h3'], recursive=False)
        inner = ''
        if hd: inner += f'<div class="as-head">{squash(inline(hd, ch))}</div>'; hd.extract()
        kids = [k for k in node.children if not (isinstance(k, NavigableString) and not k.strip())]
        if any(isinstance(k, Tag) and k.name in ('p', 'ul', 'ol', 'table') for k in kids):
            inner += ''.join(h for h, _ in children_blocks(node, ch))
        else:
            inner += f'<p>{squash(inline(node, ch))}</p>'
        return [(f'<div class="aside">{inner}</div>', 'body')]
    if 'refs' in cls:
        out_ = []
        for k in node.children:
            if not isinstance(k, Tag): continue
            kc = set(k.get('class') or [])
            if 'ref' in kc:
                nm = k.find(class_='ref-name'); bd = k.find(class_='ref-body')
                out_.append(f'<p class="ref"><strong>{squash(inline(nm, ch)) if nm else ""}</strong> {squash(inline(bd, ch)) if bd else squash(inline(k, ch))}</p>')
            elif 'refs-group' in kc: out_.append(f'<h4>{squash(inline(k, ch))}</h4>')
            else: out_ += [h for h, _ in blocks(k, ch)]
        return [('<div class="refs">' + ''.join(out_) + '</div>', 'body')]
    # ---- batch 2 components (field chapters) ----
    if 'section-num' in cls:   # 'Section 3' printed above an h2: the number goes into the h2 bar
        m = re.search(r'(\d+)', node.get_text()); ch['pending_num'] = m.group(1) if m else None
        return []
    if 'tree-wrap' in cls and node.find(class_='tree-row'):   # one decision tree = one panel, drawn like the library's
        # (owner, 25 Nov 2026: 'it should look and feel more like the one in the library'): each question a box,
        # its branches indented under it as coloured outcome boxes, a down-arrow to the next question, the key at the foot
        def tn(x):
            k = [c for c in (x.get('class') or []) if c in ('start', 'ask', 'stop', 'fix', 'limp')]
            return f'<span class="tn {k[0] if k else "plain"}">{squash(inline(x, ch))}</span>'
        tt = node.find(class_='tree-title')
        out_ = ['<div class="dtree">'] + ([f'<div class="dt-title">{squash(inline(tt, ch))}</div>'] if tt else [])
        rows = node.find_all(class_='tree-row')
        for ri, row in enumerate(rows):
            nodes = row.find_all(class_='tree-node')
            out_.append('<div class="dt-step"><div class="dt-q">' + ' <span class="dt-arr">→</span> '.join(tn(n) for n in nodes) + '</div>')
            ind = row.find_next_sibling(class_='tree-indent')
            down = ''
            if ind is not None:
                for br in ind.find_all(class_='tree-branch'):
                    lab = br.find(class_='tree-branch-label'); nd = br.find(class_='tree-node')
                    lt = text_of(lab.get_text(' ', strip=True), ch) if lab else ''
                    if nd is None:
                        down = lt; continue
                    out_.append(f'<div class="dt-b"><span class="dt-l">{lt}</span>{tn(nd)}</div>')
            out_.append('</div>')
            if ri < len(rows) - 1:
                out_.append(f'<div class="dt-down"><span class="dt-l">{down or "↓"}</span></div>')
        keys = [x for x in node.find_all(class_='tree-node') if not x.find_parent(class_=['tree-row', 'tree-branch'])]
        if keys:
            out_.append('<div class="dt-key">' + ''.join(tn(x) for x in keys) + '</div>')
        out_.append('</div>')
        return [(''.join(out_), 'wide')]
    if 'tree-title' in cls:
        return [(f'<h4>{squash(inline(node, ch))}</h4>', 'head')]
    if 'diag-group-title' in cls:
        return [(f'<h3>{squash(inline(node, ch))}</h3>', 'head')]
    if 'diag-card' in cls:   # fault card: the symptom as a heading with its action badge, then the body
        sym = node.find(class_='diag-symptom'); badge = node.find(class_='diag-badge')
        bcls = ''
        if badge:
            bc = badge.get('class') or []
            bcls = 'stop' if 'badge-stop' in bc else 'caution' if 'badge-caution' in bc else 'ok'
        head = (f'<h4 class="fault">{squash(inline(sym, ch)) if sym else ""}'
                + (f' <span class="fbadge {bcls}">{text_of(badge.get_text(" ", strip=True), ch)}</span>' if badge else '') + '</h4>')
        bodyn = node.find(class_='diag-body')
        hdr = node.find(class_='diag-header'); extra = []
        if hdr is not None:   # a sub-line under the symptom ('Hierarchy of choices when…') is kept as the card's 'why' line
            for x in hdr.find_all(class_=['diag-symptom', 'diag-badge', 'diag-arrow']): x.extract()
            t_ = squash(inline(hdr, ch))
            if t_.strip(' ▼'): extra = [(f'<p class="why">{t_.strip(" ▼")}</p>', 'body')]
        return [(head, 'head')] + extra + (children_blocks(bodyn, ch) if bodyn else [])
    if cls & {'terrain-card', 'material-card'}:
        nm = node.find(class_=['tc-name', 'mat-name']); tag = node.find(class_=['tc-tag', 'mat-tag'])
        tc = ' '.join(tag.get('class') or []) if tag else ''
        lvl = 'stop' if 'tag-high' in tc else 'caution' if 'tag-med' in tc else 'ok' if 'tag-low' in tc else 'plain'
        head = (f'<h4 class="fault">{squash(inline(nm, ch)) if nm else ""}'
                + (f' <span class="fbadge {lvl}">{text_of(tag.get_text(" ", strip=True), ch)}</span>' if tag else '') + '</h4>')
        res = [(head, 'head')]
        for b in node.find_all(class_=['tc-body', 'mat-cap', 'mat-limit']):
            t = squash(inline(b, ch))
            if t: res.append((f'<p{" class=" + chr(34) + "limit" + chr(34) if "mat-limit" in (b.get("class") or []) else ""}>{t}</p>', 'body'))
        return res
    if cls & {'principle-card', 'q-card', 'data-card'}:
        lab = node.find(class_=['p-num', 'q-num']); hd = node.find(class_=['p-title', 'q-text']) or node.find('h4')
        inner = (f'<div class="as-label">{squash(inline(lab, ch))}</div>' if lab else '') + (f'<div class="as-head">{squash(inline(hd, ch))}</div>' if hd else '')
        for x in (lab, hd):
            if x is not None: x.extract()
        inner += ''.join(h for h, _ in children_blocks(node, ch))
        return [(f'<div class="aside">{inner}</div>', 'body')]
    if 'rb-card' in cls:
        lab = node.find(class_='rb-label'); txt = node.find(class_='rb-text')
        lv = 'r-high' if 'rb-high' in cls else 'r-med' if 'rb-med' in cls else 'r-low'
        return [(f'<div class="aside {lv}"><div class="as-head">{squash(inline(lab, ch)) if lab else ""}</div>'
                 f'<p>{squash(inline(txt, ch)) if txt else ""}</p></div>', 'body')]
    if 'signal-chain' in cls:
        parts_ = [x for x in node.find_all(class_=lambda c: c and c.startswith('sc-') and c != 'sc-arrow') if not x.find_parent(class_=lambda c: c and c.startswith('sc-'))]
        if not node.find(class_='sc-step') and parts_:   # coloured step boxes: drawn as the decision-tree boxes
            return [('<p class="chain">' + ' <span class="sym arr">→</span> '.join(
                f'<span class="tn {"stop" if "sc-stop" in (x.get("class") or []) else "plain"}">{squash(inline(x, ch))}</span>' for x in parts_) + '</p>', 'body')]
        # every step in order, a highlighted step (sc-key, e.g. the LSPV in the bleed order) in bold
        steps = [(f'<strong>{squash(inline(x, ch))}</strong>' if 'sc-key' in (x.get('class') or []) else squash(inline(x, ch)))
                 for x in node.find_all(class_=['sc-step', 'sc-key'])]
        plain = [re.sub(r'<[^>]+>', '', t) for t in steps]
        if steps and all(STEP_NUM.match(p) for p in plain):
            return [('<ol>' + ''.join(f'<li value="{STEP_NUM.match(p).group(1)}">{re.sub(r"^\s*\d+[.)]\s*", "", t)}</li>' for t, p in zip(steps, plain)) + '</ol>', 'body')]
        return [('<p class="chain">' + ' <span class="sym arr">→</span> '.join(f'<span class="cstep">{t}</span>' for t in steps) + '</p>', 'body')]
    if cls & {'stat-grid'}:
        rows = ''.join(f'<tr><td class="k">{text_of(st.find(class_="stat-label").get_text(" ", strip=True), ch)}</td>'
                       f'<td class="v">{text_of(st.find(class_="stat-val").get_text(" ", strip=True), ch)}</td></tr>'
                       for st in node.find_all(class_='stat') if st.find(class_='stat-label') and st.find(class_='stat-val'))
        return [(f'<table class="spec">{rows}</table>', 'body')]
    if 'sensor-card' in cls:
        tt = node.find(class_='sensor-title')
        rows = ''
        for r_ in node.find_all(class_='sensor-row'):
            k = r_.find(class_='sensor-key'); v = r_.find(class_='sensor-val')
            bad = ' bad' if v is not None and 'sensor-bad' in (v.get('class') or []) else ''
            rows += f'<tr><td class="k">{squash(inline(k, ch)) if k else ""}</td><td class="v2{bad}">{squash(inline(v, ch)) if v else ""}</td></tr>'
        return [(f'<h4>{squash(inline(tt, ch)) if tt else ""}</h4>', 'head'), (f'<table class="spec">{rows}</table>', 'body')]
    if 'smoke-card' in cls:
        hd = node.find(class_='smoke-header'); bd = node.find(class_='smoke-body')
        hc = ' '.join(hd.get('class') or []) if hd else ''
        sw = {'smoke-black': '#0d0e12', 'smoke-white': '#ffffff', 'smoke-blue': '#2f5d8a', 'smoke-grey': '#8a8f9a'}
        col = next((v for k, v in sw.items() if k in hc), '#8a8f9a')
        return [(f'<h4><span class="swatch" style="background:{col}"></span>{squash(inline(hd, ch)) if hd else ""}</h4>', 'head'),
                (f'<p>{squash(inline(bd, ch)) if bd else ""}</p>', 'body')]
    if 'subsec' in cls and node.find(class_='subsec-title'):
        tt = node.find(class_='subsec-title'); tg = node.find(class_='subsec-tag')
        return [(f'<h3>{squash(inline(tt, ch))}' + (f' <span class="h3tag">{squash(inline(tg, ch))}</span>' if tg else '') + '</h3>', 'head')]
    if 'tree' in cls and node.find(class_='tree-q'):
        items = ''.join(f'<li><strong class="tq">{squash(inline(r_.find(class_="tree-q"), ch))}</strong><br>{squash(inline(r_.find(class_="tree-a"), ch))}</li>'
                        for r_ in node.find_all(class_='tree-row') if r_.find(class_='tree-q'))
        return [(f'<ul class="qa">{items}</ul>', 'body')]
    # ---- batch 3 components ----
    if 'card-block' in cls and node.find(class_='row'):   # a spec card: name (and sub-line) as h4, then spec rows
        nm = node.find(class_='card-name'); sb = node.find(class_='card-sub')
        rows = ''.join(f'<tr><td class="k">{squash(inline(r_.find(class_="row-label"), ch))}</td>'
                       f'<td class="v2">{squash(inline(r_.find(class_="row-value"), ch))}</td></tr>'
                       for r_ in node.find_all(class_='row') if r_.find(class_='row-label') and r_.find(class_='row-value'))
        head = f'<h4>{squash(inline(nm, ch)) if nm else ""}' + (f' <span class="h3tag">{squash(inline(sb, ch))}</span>' if sb else '') + '</h4>'
        return [(head, 'head'), (f'<table class="spec">{rows}</table>', 'body')]
    if 'calc-block' in cls:   # a titled run of numbered steps
        tt = node.find(class_='calc-title'); res = []
        if tt: res.append((f'<h4>{squash(inline(tt, ch))}</h4>', 'head'))
        items = []
        for st in node.find_all(class_='calc-step'):
            n_ = st.find(class_='calc-num'); b_ = st.find(class_='calc-body')
            nv = n_.get_text(strip=True) if n_ else ''
            t_ = squash(inline(b_, ch)) if b_ else ''
            items.append(f'<li value="{nv}">{t_}</li>' if nv.isdigit() else f'<li>{t_}</li>')
        return res + [('<ol>' + ''.join(items) + '</ol>', 'body')]
    if 'dodont' in cls:   # 'reach for this when' pairs: each card a heading and its list
        res = []
        if not node.find(class_=['do-card', 'dont-card'], recursive=False):   # R5: numbered questions straight in the panel
            for it in node.find_all(class_=['do-item', 'dont-item'], recursive=False):
                ic = it.find(class_=['do-icon', 'dont-icon']); lab = it.find(class_='di-label'); nt = it.find(class_='di-note')
                res.append((f'<h4>{text_of(ic.get_text(strip=True), ch) + " " if ic else ""}{squash(inline(lab, ch)) if lab else ""}</h4>', 'head'))
                if nt is not None: res += parasplit(children_blocks(nt, ch))
            return res
        for card in node.find_all(class_=['do-card', 'dont-card'], recursive=False):
            do = 'do-card' in (card.get('class') or [])
            hd = card.find(class_=['do-head', 'dont-head'])
            if hd: res.append((f'<h4>{squash(inline(hd, ch))}</h4>', 'head'))
            items = []
            for it in card.find_all(class_=['do-item', 'dont-item']):
                ic = it.find(class_=['do-icon', 'dont-icon'])
                g = ic.get_text(strip=True) if ic else ''
                if ic is not None: ic.extract()
                lab = it.find(class_='di-label'); nt = it.find(class_='di-note')
                t_ = (f'<strong>{squash(inline(lab, ch))}</strong> ' if lab else '') + (squash(inline(nt, ch)) if nt else '')
                if do or g in KEEP_SYM:
                    mk = 'yes' if KEEP_SYM.get(g, '✓') == '✓' else 'no'
                    items.append(f'<li><span class="mk {mk}">{KEEP_SYM.get(g, "✓")}</span>{t_}</li>')
                else:
                    items.append(f'<li><span class="mk arw">{H.escape(g)}</span>{t_}</li>')
            res.append(('<ul class="mark">' + ''.join(items) + '</ul>', 'body'))
        return res
    if 'sources' in cls and name == 'div':   # a reference list: heading, then each source as a reference line
        res = []
        for k in node.children:
            if not isinstance(k, Tag): continue
            if k.name in ('h2', 'h3', 'h4'): res.append((f'<h3>{squash(inline(k, ch))}</h3>', 'head'))
            elif k.name == 'p': res.append((f'<p class="ref">{squash(inline(k, ch))}</p>', 'body'))
            else: res += blocks(k, ch)
        return res
    # ---- batch 5 components (Part 4, before we go) ----
    if cls & {'progress-bar-wrap', 'filter-bar', 'print-bar', 'confirm-overlay', 'sec-sep'}:   # web controls: not printed
        if node.get_text(strip=True): report.append(f'{ch["r"]}: web control not printed: {node.get_text(" ", strip=True)[:60]}')
        return []
    if cls & {'sec-label'}:   # 'Section 1' above an h2 (R11): the number goes into the h2 bar
        m = re.search(r'(\d+)', node.get_text()); ch['pending_num'] = m.group(1) if m else None
        return []
    if cls & {'section-strip', 'part-banner'}:   # a band naming the block below it (R1, R38, R39)
        return [(f'<h2 class="non{" pb" if "part-banner" in cls else ""}">{squash(inline(node, ch))}</h2>', 'wide')]
    if 'zone-header' in cls:   # R2 walk-around zone: letter, name, item count
        bd = node.find(class_='zone-badge'); nm = node.find(class_='zone-name'); ct = node.find(class_='zone-count')
        return [(f'<h3>{text_of(bd.get_text(strip=True), ch) + " — " if bd else ""}{squash(inline(nm, ch)) if nm else ""}'
                 + (f' <span class="h3tag">{squash(inline(ct, ch))}</span>' if ct else '') + '</h3>', 'head')]
    if 'zone-body' in cls:
        return children_blocks(node, ch)
    if 'cc' in cls and node.find(class_='cc-hdr'):   # R15 country card: name and visa badge, then its rows
        nm = node.find(class_='cc-name'); vs = node.find(class_='cc-visa')
        vc = ' '.join(vs.get('class') or []) if vs else ''
        lvl = 'ok' if 'free' in vc else 'caution' if ('arrival' in vc or 'evisa' in vc or 'e-visa' in vc) else 'stop' if 'req' in vc else 'plain'
        res = [(f'<h4 class="fault">{squash(inline(nm, ch)) if nm else ""}' + (f' <span class="fbadge {lvl}">{squash(inline(vs, ch))}</span>' if vs else '') + '</h4>', 'head')]
        rows = ''.join(f'<tr><td class="k">{squash(inline(r_.find(class_="cc-label"), ch))}</td><td class="v2">{squash(inline(r_.find(class_="cc-val"), ch))}</td></tr>'
                       for r_ in node.find_all(class_='cc-row') if r_.find(class_='cc-label') and r_.find(class_='cc-val'))
        if rows: res.append((f'<table class="spec wide-k">{rows}</table>', 'body'))
        for x in node.find_all(class_=['cc-note', 'verified']):
            res.append((f'<p class="{"ref" if "verified" in (x.get("class") or []) else "limit2"}">{squash(inline(x, ch))}</p>', 'body'))
        return res
    if 'd-card' in cls:   # a decision card (R23): coloured head, its list — as a card
        hd = node.find(class_='d-card-head'); bd = node.find(class_='d-card-body')
        return [(f'<div class="cardc"><div class="as-head">{squash(inline(hd, ch)) if hd else ""}</div>'
                 + (''.join(h for h, _ in children_blocks(bd, ch)) if bd else '') + '</div>', 'card')]
    if 'zone-card' in cls:   # a packing zone (R11): its name and list — as a card
        lb = node.find(class_='zone-label')
        if lb is not None: lb.extract()
        return [(f'<div class="cardc"><div class="as-head">{squash(inline(lb, ch)) if lb else ""}</div>'
                 + ''.join(h for h, _ in children_blocks(node, ch)) + '</div>', 'card')]
    if cls & {'brief-block', 'predep', 'section-note'}:   # a boxed brief or note: aside
        tt = node.find(class_='brief-block-title')
        inner = f'<div class="as-head">{squash(inline(tt, ch))}</div>' if tt else ''
        if tt is not None: tt.extract()
        kids = [k for k in node.children if isinstance(k, Tag) and k.name in ('p', 'ul', 'ol', 'table', 'div')]
        inner += ''.join(h for h, _ in children_blocks(node, ch)) if kids else f'<p>{squash(inline(node, ch))}</p>'
        return [(f'<div class="aside">{inner}</div>', 'body')]
    if cls & {'gear', 'clocks', 'breaker', 'owns'} or (name == 'div' and cls == {'foot'}):   # a line led by a bold label
        bl_ = labelled([(f'<p>{squash(inline(node, ch))}</p>', 'body'), ('<p><strong>x:</strong></p>', 'body')])[:-1]
        return bl_ if 'foot' not in cls else [(f'<p class="ref">{squash(inline(node, ch))}</p>', 'body')]
    if 'legend' in cls and node.find(class_='badge'):   # a status key (R37): small reference line
        return [(f'<p class="ref">{squash(inline(node, ch))}</p>', 'body')]
    if 'prov-card' in cls:   # a provider or device (R29): heading with its status tag, then labelled lines
        hd = node.find(class_='prov-card-head'); tg = hd.find(class_='prov-tag') if hd else None
        tc = ' '.join(tg.get('class') or []) if tg else ''
        if tg is not None: tg.extract()
        lvl = 'stop' if ('bad' in tc or 'red' in tc or 'no' in tc.split('-')) else 'caution' if 'warn' in tc else 'ok' if 'ok' in tc else 'plain'
        res = [(f'<h4 class="fault">{squash(inline(hd, ch)) if hd else ""}' + (f' <span class="fbadge {lvl}">{squash(inline(tg, ch))}</span>' if tg else '') + '</h4>', 'head')]
        bd = node.find(class_='prov-card-body')
        return res + (labelled(children_blocks(bd, ch)) if bd else [])
    if 'stack-layer' in cls:   # one layer of the rescue stack (R29): number, title and description, its status
        n_ = node.find(class_='stack-num'); tt = node.find(class_='stack-title'); ds = node.find(class_='stack-desc'); gp = node.find(class_='stack-gap')
        gc = ' '.join(gp.get('class') or []) if gp else ''
        lvl = 'ok' if 'gap-ok' in gc else 'caution' if 'amber' in gc else 'stop'
        nv = n_.get_text(strip=True) if n_ else ''
        return [(f'<ol class="stack"><li value="{nv}"><strong>{squash(inline(tt, ch)) if tt else ""}</strong>'
                 + (f' <span class="fbadge {lvl}">{squash(inline(gp, ch))}</span>' if gp else '') + (f'<br>{squash(inline(ds, ch))}' if ds else '') + '</li></ol>', 'body')]
    if 'cascade' in cls and node.find(class_='cascade-hdr'):   # a failure cascade (R41): code and title, the path, then its orders
        hd = node.find(class_='cascade-hdr'); cid = hd.find(class_='cascade-id'); ct = hd.find(class_='cascade-title'); cs = hd.find(class_='cascade-sys')
        res = [(f'<h3>{squash(inline(cid, ch)) + " · " if cid else ""}{squash(inline(ct, ch)) if ct else ""}' + (f' <span class="h3tag">{squash(inline(cs, ch))}</span>' if cs else '') + '</h3>', 'head')]
        bd = node.find(class_='cascade-body')
        return res + (children_blocks(bd, ch) if bd else [])
    if name == 'ul' and 'chain' in cls and node.find(class_='ord'):   # 1st / 2nd / 3rd order: each with its label
        items = []
        for li in node.find_all('li', recursive=False):
            o = li.find(class_='ord'); ot = o.extract().get_text(' ', strip=True) if o else ''
            items.append(f'<li><span class="cnum">{text_of(ot, ch)}</span>{squash(inline(li, ch))}</li>')
        return [('<ul class="orders">' + ''.join(items) + '</ul>', 'body')]
    if 'wb-outer' in cls:   # the measured weight bar (R11): its words, in the warning colour
        return [(f'<p class="limit"><strong>{squash(inline(node, ch))}</strong></p>', 'body')]
    if name == 'div' and cls == {'wt'}:
        return [(f'<p><strong>{squash(inline(node, ch))}</strong></p>', 'body')]
    # ---- batch 4 components (Part 3, the vehicle) ----
    if 'section-header' in cls:   # '00 How the 1HZ Works' / '1 — CRITICAL Critical Engine Spares': an h2 with its number
        num = node.find(class_='section-num'); nm = node.find(class_='section-name'); ds = node.find(class_='section-desc')
        nt_ = num.get_text(' ', strip=True).lstrip('§ ') if num else ''
        if nm is None and num is not None:   # '<span class=section-num>§2</span> Recovery Skills' (R37): the title is the rest
            num.extract(); nm = node
        m = re.match(r'^\s*(?:SECTION\s+)?(\d+[A-Z]?)\s*(?:[—–-]\s*(.*))?$', nt_)
        n_, tag = (m.group(1), (m.group(2) or '').strip()) if m else ('', nt_)   # a word label ('FIELD FIXES') goes in the sub-line
        title = squash(inline(nm, ch)) if nm else ''
        res = [(f'<h2><span class="h2-n">{n_}</span>{title}</h2>' if n_ else f'<h2 class="non">{title}</h2>', 'wide')]
        sub_ = ' · '.join(x for x in (text_of(tag, ch), squash(inline(ds, ch)) if ds else '') if x)
        if sub_: res.append((f'<p class="h2sub">{sub_}</p>', 'wide'))
        return res
    if 'section-label' in cls:   # '00 — Overview' above an h2: the number goes into the h2 bar
        # '07 — §6 Transfer Case HF1A': the atlas section (§6, which its cards 6.1… and other chapters' 'R20 §6' use) goes
        # in the bar; a label with no § ('00 — Overview') gets a plain bar. The label's words print as the sub-line.
        m = re.match(r'^\s*\d+\s*[—–-]?\s*(?:§\s*(\d+)\s*)?(.*)$', node.get_text(' ', strip=True))
        ch['pending_num'] = (m.group(1) or '') if m else None
        if m and m.group(2): ch['pending_sub'] = text_of(m.group(2), ch).strip()
        return []
    if cls & {'ref-hdr', 'fluid-table-hdr'}:   # a table's own title bar: h2 and its sub-line
        h = node.find('h2'); sp = node.find('span')
        res = [(f'<h2 class="non">{squash(inline(h, ch)) if h else ""}</h2>', 'wide')]
        if sp: res.append((f'<p class="h2sub">{squash(inline(sp, ch))}</p>', 'wide'))
        return res
    if 'component' in cls and 'how' in cls:
        return children_blocks(node, ch)
    if 'component' in cls:   # an engine part or a spare: number and name as the module heading, its tag, its location
        idx = node.find(class_='comp-num'); nm = node.find(class_='comp-name'); code = node.find(class_='comp-code')
        loc = node.find(class_='comp-location')
        head = (f'<h3>{text_of(idx.get_text(" ", strip=True), ch) + " " if idx else ""}{squash(inline(nm, ch)) if nm else ""}'
                + (f' <span class="h3tag">{squash(inline(code, ch))}</span>' if code else '') + '</h3>')
        res = [(head, 'head')]
        if loc: res.append((f'<p class="why">{squash(inline(loc, ch))}</p>', 'head'))
        hdr = node.find(class_='comp-header')
        for x in ([y for y in hdr.find_all(True, recursive=False) if not set(y.get('class') or []) & {'comp-name', 'comp-code'}] if hdr else []):
            t_ = squash(inline(x, ch))   # e.g. the Toyota part number and its 'verify' flag
            if t_: res.append((f'<p class="why">{t_}</p>', 'head'))
        glyph = node.find(class_='comp-glyph')   # the index chip's caption repeats the name in capitals: report, don't print
        if glyph is not None: report.append(f'{ch["r"]}: index caption not printed (repeats the heading): {glyph.get_text(" ", strip=True)}')
        for x in node.find_all(class_=['comp-index', 'comp-header', 'comp-location']): x.decompose()
        return res + children_blocks(node, ch)
    if 'block-label' in cls:
        return [(f'<h4>{squash(inline(node, ch))}</h4>', 'head')]
    if 'fix-card' in cls:   # a field fix: its title as the module heading, then numbered steps and warnings
        tt = node.find(class_='fix-title'); res = []
        if tt: res.append((f'<h3>{squash(inline(tt, ch))}</h3>', 'head')); tt.extract()
        return res + children_blocks(node, ch)
    if 'fix-carry' in cls:
        return [(f'<p>{squash(inline(node, ch))}</p>', 'body')]
    if 'seal-card' in cls:   # a seal: name and priority badge as a fault heading, location, then its labelled fields
        nm = node.find(class_='sc-name'); pill = node.find(class_='sc-pill'); loc = node.find(class_='sc-loc')
        pc = ' '.join(pill.get('class') or []) if pill else ''
        lvl = 'stop' if 'pill-red' in pc else 'caution' if 'pill-amb' in pc else 'ok' if 'pill-grn' in pc else 'plain'
        res = [(f'<h4 class="fault">{squash(inline(nm, ch)) if nm else ""}'
                + (f' <span class="fbadge {lvl}">{text_of(pill.get_text(" ", strip=True), ch)}</span>' if pill else '') + '</h4>', 'head')]
        if loc: res.append((f'<p class="why">{squash(inline(loc, ch))}</p>', 'body'))
        for fl in node.find_all(class_='sc-field'):
            lb = fl.find(class_='sc-label'); tx = fl.find(class_='sc-text')
            res.append((f'<p><strong>{squash(inline(lb, ch)) if lb else ""}</strong> {squash(inline(tx, ch)) if tx else ""}</p>', 'body'))
        return res
    if 'check-list' in cls:   # a numbered inspection checklist
        res = []
        for k in node.children:
            if not isinstance(k, Tag): continue
            if k.name in ('h3', 'h4', 'h5'): res.append((f'<h4>{squash(inline(k, ch))}</h4>', 'head'))
        items = []
        for it in node.find_all(class_='check-item'):
            n_ = it.find(class_='check-num'); tx = it.find(class_='check-text')
            items.append(f'<li><span class="box"></span><span class="cnum">{text_of(n_.get_text(strip=True), ch) if n_ else ""}</span>{squash(inline(tx, ch)) if tx else ""}</li>')
        return res + [('<ul class="check">' + ''.join(items) + '</ul>', 'body')]
    if 'comp-card' in cls:   # a component card: name and status tag as the module heading, then its body
        hd = node.find(class_='comp-card-head'); tag = hd.find(class_='comp-tag') if hd else None
        if tag is not None: tag.extract()
        res = []
        if hd:
            res.append((f'<h3>{squash(inline(hd, ch))}' + (f' <span class="h3tag">{squash(inline(tag, ch))}</span>' if tag else '') + '</h3>', 'head'))
            hd.extract()
        return res + parasplit(children_blocks(node, ch))
    if 'comp-card-body' in cls:
        return parasplit(children_blocks(node, ch))
    if cls & {'weak-card', 'qual-card'}:   # a weak point or a fuel fault: heading with its risk badge
        tt = node.find(class_=['weak-title', 'qual-title']); bd = node.find(class_='risk-badge')
        bc = ' '.join(bd.get('class') or []) if bd else ''
        lvl = 'stop' if 'high' in bc else 'caution' if 'med' in bc else 'ok' if 'low' in bc else 'plain'
        res = [(f'<h4 class="fault">{squash(inline(tt, ch)) if tt else ""}'
                + (f' <span class="fbadge {lvl}">{text_of(bd.get_text(" ", strip=True), ch)}</span>' if bd else '') + '</h4>', 'head')]
        body_ = node.find(class_=['weak-body', 'qual-body'])
        if body_ is None: return res
        kms = [x.extract() for x in body_.find_all(class_=['weak-km', 'qual-km'])]
        res += parasplit(children_blocks(body_, ch))
        res += [(f'<p><em>{squash(inline(x, ch))}</em></p>', 'body') for x in kms]
        return res
    if cls & {'curious', 'how-curious'}:   # 'for the curious' side note
        tt = node.find(class_=['curious-title', 'how-curious-t'])
        inner = f'<div class="as-head">{squash(inline(tt, ch))}</div>' if tt else ''
        if tt is not None: tt.extract()
        return [(f'<div class="aside">{inner}' + ''.join(h for h, _ in children_blocks(node, ch)) + '</div>', 'body')]
    if cls & {'how-card', 'info-card'}:
        tt = node.find(class_=['how-card-t', 'info-title']); res = []
        if tt: res.append((f'<h4>{squash(inline(tt, ch))}</h4>', 'head')); tt.extract()
        return res + children_blocks(node, ch)
    if 'how-card-b' in cls:
        return children_blocks(node, ch)
    if 'egt-band-wrap' in cls:   # the EGT colour band: each band and its range as a spec row
        segs = node.find_all(class_='egt-seg'); labs = node.find_all(class_='egt-seg-label')
        tone = ['ok', 'warn', 'crit']
        rows = ''.join(f'<tr><td class="k"><span class="{tone[min(i, 2)]}">{text_of(s_.get_text(" ", strip=True), ch)}</span></td>'
                       f'<td class="v2">{text_of(l_.get_text(" ", strip=True), ch)}</td></tr>' for i, (s_, l_) in enumerate(zip(segs, labs)))
        return [(f'<table class="spec">{rows}</table>', 'body')]
    if 'diagram-wrap' in cls and not node.find('svg'):   # a diagram drawn in characters: printed as a figure, spacing kept
        tt = node.find(class_='diagram-title')
        nt = next((k for k in node.find_all('div', recursive=False) if k is not tt), None)
        cap = ' — '.join(x for x in ((squash(inline(tt, ch)) if tt else ''), (squash(inline(nt, ch)) if nt else '')) if x)
        for x in (tt, nt):
            if x is not None: x.extract()
        for b_ in node.find_all('br'): b_.replace_with('\n')
        lines = [ln.rstrip() for ln in node.get_text().split('\n')]
        lines = [ln for ln in lines if ln.strip()]
        ind = min(len(ln) - len(ln.lstrip(' ')) for ln in lines) if lines else 0
        body_ = '\n'.join(H.escape(clean_text(ln[ind:], ch), quote=False) for ln in lines)
        wmax = max((len(ln) - ind for ln in lines), default=1)
        fs = min(6.4, 160 / (wmax * 0.602 * 0.3528))   # monospace: the longest line fits the 160 mm inside the frame
        return [(f'<div class="figure"><pre class="tdiag" style="font-size:{fs:.2f}pt">{body_}</pre>' + (f'<div class="cap">{cap}</div>' if cap else '') + '</div>', 'wide')]
    if cls & {'sym-grid', 'formula-strip', 'chem-grid'}:   # (owner, 26 Nov 2026: 'maybe cards will be better') a grid of cells = cards
        cells = [c_ for c_ in node.find_all('div', recursive=False) if set(c_.get('class') or []) & {'sym-cell', 'fc', 'chem-cell'}]
        cards = []
        for c_ in cells:
            cc = set(c_.get('class') or [])
            if 'sym-cell' in cc:
                sy = c_.find(class_='sym-symbol'); full = c_.find(class_='sym-full'); nm = c_.find(class_='sym-name')
                ds = c_.find(class_='sym-desc'); fm = c_.find(class_='sym-formula')
                cards.append('<div class="cardc">' + (f'<div class="as-label">{squash(inline(nm, ch))}</div>' if nm else '')
                             + f'<div class="as-head"><span class="sbig">{squash(inline(sy, ch)) if sy else ""}</span>{squash(inline(full, ch)) if full else ""}</div>'
                             + (f'<p>{squash(inline(ds, ch))}</p>' if ds else '') + (f'<p class="feq">{squash(inline(fm, ch))}</p>' if fm else '') + '</div>')
            elif 'fc' in cc:
                nm = c_.find(class_='f-name'); eq = c_.find(class_='f-eq'); ex = c_.find(class_='f-exp'); eg = c_.find(class_='f-ex')
                cards.append('<div class="cardc">' + f'<div class="as-head">{squash(inline(nm, ch)) if nm else ""}</div>'
                             + (f'<p class="feq big">{squash(inline(eq, ch))}</p>' if eq else '') + (f'<p>{squash(inline(ex, ch))}</p>' if ex else '')
                             + (f'<p class="fex"><em>{squash(inline(eg, ch))}</em></p>' if eg else '') + '</div>')
            else:
                nm = c_.find(class_='chem-name'); bd = nm.find(class_='chem-badge') if nm else None
                if bd is not None: bd.extract()
                lvl = 'ok' if 'best' in cc else 'stop' if 'avoid' in cc else 'caution'
                items = ''.join(f'<li>{x.strip()}</li>' for pr in c_.find_all(class_='chem-prop') for x in re.split(r'<br>', squash(inline(pr, ch))) if x.strip())
                cards.append(f'<div class="cardc">' + (f'<div class="as-label"><span class="fbadge {lvl}">{text_of(bd.get_text(" ", strip=True), ch)}</span></div>' if bd else '')
                             + f'<div class="as-head">{squash(inline(nm, ch)) if nm else ""}</div><ul>{items}</ul></div>')
        n_ = 3 if len(cells) == 3 else 2
        return [(f'<div class="cards c{n_}">' + ''.join(cards) + '</div>', 'wide')]
    if 'sym-cell' in cls:   # an electrical unit: its name and symbol, what it means, its formula
        full = node.find(class_='sym-full'); nm = node.find(class_='sym-name'); ds = node.find(class_='sym-desc'); fm = node.find(class_='sym-formula')
        res = [(f'<h4>{squash(inline(full, ch)) if full else ""}' + (f' <span class="h3tag">{squash(inline(nm, ch))}</span>' if nm else '') + '</h4>', 'head')]
        if ds: res.append((f'<p>{squash(inline(ds, ch))}</p>', 'body'))
        if fm: res.append((f'<p><strong>{squash(inline(fm, ch))}</strong></p>', 'body'))
        return res
    if 'fc' in cls and node.find(class_='f-eq'):   # a formula: name, the formula, how to use it, an example
        nm = node.find(class_='f-name'); eq = node.find(class_='f-eq'); ex = node.find(class_='f-exp'); eg = node.find(class_='f-ex')
        res = [(f'<h4>{squash(inline(nm, ch)) if nm else ""}</h4>', 'head'), (f'<p><strong>{squash(inline(eq, ch))}</strong></p>', 'body')]
        if ex: res.append((f'<p>{squash(inline(ex, ch))}</p>', 'body'))
        if eg: res.append((f'<p><em>{squash(inline(eg, ch))}</em></p>', 'body'))
        return res
    if 'chem-cell' in cls:   # a battery chemistry: heading with its verdict badge, then its properties as a list
        nm = node.find(class_='chem-name'); bd = nm.find(class_='chem-badge') if nm else None
        if bd is not None: bd.extract()
        lvl = 'ok' if 'best' in cls else 'stop' if 'avoid' in cls else 'caution'
        res = [(f'<h4 class="fault">{squash(inline(nm, ch)) if nm else ""}'
                + (f' <span class="fbadge {lvl}">{text_of(bd.get_text(" ", strip=True), ch)}</span>' if bd else '') + '</h4>', 'head')]
        for pr in node.find_all(class_='chem-prop'):
            items = [x for x in re.split(r'<br>', squash(inline(pr, ch))) if x.strip()]
            res.append(('<ul>' + ''.join(f'<li>{x.strip()}</li>' for x in items) + '</ul>', 'body'))
        return res
    if 'ohm-box' in cls:   # Ohm's law triangle: the three boxes as the library sets them, V above I and R
        tt = node.find(class_='ohm-title')
        def cell(c_):
            x = node.find(class_=c_)
            if x is None: return ''
            sb = x.find(class_='ohm-sub'); st = sb.extract().get_text(' ', strip=True) if sb else ''
            return f'<span class="tn">{text_of(x.get_text(" ", strip=True), ch)} {text_of(st, ch)}</span>'
        note = [d for d in node.find_all('div', recursive=False) if not d.get('class')]   # 'Cover what you want to find'
        return [(f'<div class="aside"><div class="as-head">{squash(inline(tt, ch)) if tt else ""}</div>'
                 f'<p class="tri">{cell("ohm-top")}<br>{cell("ohm-bl")} {cell("ohm-br")}</p>'
                 + ''.join(f'<p class="tri">{squash(inline(d, ch))}</p>' for d in note) + '</div>', 'body')]
    if 'soc-card' in cls:   # state-of-charge: the bar as coloured boxes, then each zone with its colour dot
        hd = node.find(class_='soc-head'); res = [(f'<h4>{squash(inline(hd, ch)) if hd else ""}</h4>', 'head')]
        segs = node.find_all(class_='soc-segment')
        tone = {'seg-red': 'stop', 'seg-yellow': 'limp', 'seg-lime': 'plain', 'seg-green': 'fix'}
        if segs:
            res.append(('<p class="chain">' + ' '.join(
                f'<span class="tn {next((v for k_, v in tone.items() if k_ in (s_.get("class") or [])), "plain")}">{text_of(s_.get_text(" ", strip=True), ch)}</span>'
                for s_ in segs) + '</p>', 'body'))
        items = []
        for zr in node.find_all(class_='soc-zone-row'):
            dot = zr.find(class_='soc-dot'); col = re.search(r'background:\s*(#[0-9A-Fa-f]{3,6})', dot.get('style', '')) if dot else None
            lb = zr.find(class_='soc-zone-label'); ds = zr.find(class_='soc-zone-desc')
            items.append(f'<li>' + (f'<span class="sym dot" style="color:{col.group(1)}">●</span> ' if col else '')
                         + f'<strong>{squash(inline(lb, ch)) if lb else ""}</strong> {squash(inline(ds, ch)) if ds else ""}</li>')
        if items: res.append(('<ul class="zones">' + ''.join(items) + '</ul>', 'body'))
        return res
    if 'stats' in cls and node.find(class_='sbadge'):   # battery readings: each badge, its value and what it means
        cards = []   # (owner, 26 Nov 2026) stat boxes as cards: the badge, the value large, then what it means
        for sc_ in node.find_all(class_='sc', recursive=False):
            bg = sc_.find(class_='sbadge'); sv = sc_.find(class_='sv'); sl = sc_.find(class_='sl')
            for u in sc_.find_all(class_='u'): u.insert_before(' ')
            cards.append('<div class="cardc">' + (f'<div class="as-label">{squash(inline(bg, ch))}</div>' if bg else '')
                         + (f'<p class="feq big">{squash(inline(sv, ch))}</p>' if sv else '') + (f'<p>{squash(inline(sl, ch))}</p>' if sl else '') + '</div>')
        n_ = 3 if len(cards) % 3 == 0 else 2
        return [(f'<div class="cards c{n_}">' + ''.join(cards) + '</div>', 'wide')]
    if name == 'div' and cls == {'p'}:   # a closing notes line
        return [(f'<p class="ref">{squash(inline(node, ch))}</p>', 'body')]
    if 'refs-note' in cls:
        return [(f'<p class="ref">{squash(inline(node, ch))}</p>', 'body')]
    if name == 'p':
        t = squash(inline(node, ch))
        return [(f'<p>{t}</p>', 'body')] if t else []
    if name in ('ul', 'ol') or 'cause-list' in cls: return [(list_html(node, ch), 'body')]
    if name == 'table':
        cap = node.find('caption'); res = []
        if cap is not None:
            res.append((f'<h4>{squash(inline(cap, ch))}</h4>', 'head')); cap.extract()
        h, k = table(node, ch); return res + [(h, k)]
    if name == 'svg': return [(figure(node, ch), 'wide')]
    if 'rig-legend' in cls: return [(legend(node, ch), 'wide')]
    for c, kind in NOTICE_CLASSES.items():
        if c in cls: return [(notice(node, ch, kind), 'body')]
    if 'card' in cls:
        res = []
        title = node.find(class_='card-title'); why = node.find(class_='card-why')
        a = 'alert' in cls
        if title and ch.get('sheet'):   # a spec sheet (R1): each group is a small heading in one flowing pair of columns
            res.append((f'<h4 class="sg">{squash(inline(title, ch))}</h4>', 'head'))
        elif title:
            res.append((f'<h3{" class=" + chr(34) + "alert" + chr(34) if a else ""}>{squash(inline(title, ch))}</h3>', 'head'))
        if why:
            res.append((f'<p class="why">{squash(inline(why, ch))}</p>', 'head'))
        bodyn = node.find(class_='card-body')
        if bodyn is None:
            bodyn = node; [x.extract() for x in node.find_all(class_='card-header')]
        res += labelled(children_blocks(bodyn, ch)) if not title else children_blocks(bodyn, ch)
        return res
    if name in ('div', 'section', 'main', 'article', 'span', 'header') and (not cls or cls & WRAPPERS or name in ('section', 'main', 'article')):
        return children_blocks(node, ch)
    unplaced.append(f'{ch["r"]}: <{name} class="{" ".join(cls)}"> {node.get_text(" ", strip=True)[:90]}')
    return children_blocks(node, ch)

LAB = re.compile(r'^<p><strong>(.+?)</strong>\s*(.*)</p>$', re.S)
STEPLAB = re.compile(r'^Step\s+(\d+)\s*[—–:-]\s*(.*)$', re.S)
def labelled(bl):
    """(owner, 26 Nov 2026: field fixes 'dumped in text') a card of paragraphs led by a bold label is set for reading:
    'Step N — …' paragraphs become numbered steps, 'Carry:' a tinted kit line, any other 'Label:' a small label on its
    own line above its text. Words are not changed."""
    labs = [LAB.match(h) for h, _ in bl]
    if sum(1 for m in labs if m) < 2: return bl
    res, steps = [], []
    def flush():
        if steps: res.append(('<ol class="fsteps">' + ''.join(steps) + '</ol>', 'body')); steps.clear()
    for (h, k), m in zip(bl, labs):
        if not m: flush(); res.append((h, k)); continue
        lab, rest = m.group(1).strip(), m.group(2).strip()
        sm = STEPLAB.match(lab)
        if sm:
            steps.append(f'<li class="v" value="{sm.group(1)}"><strong>{sm.group(2).strip()}</strong> {rest}</li>'); continue
        flush()
        colon = lab.endswith(':') or rest.startswith(':')
        if not colon:   # a bold opening phrase, not a label: the paragraph stays as it is
            res.append((h, k)); continue
        name = lab.rstrip(':').strip(); rest = rest.lstrip(':').strip()
        cls = 'carry' if name.lower() in ('carry', 'tools', 'spares') else 'lab'
        res.append((f'<p class="{cls}"><span class="fl">{name}</span>{rest}</p>', k))
    flush()
    return res
def parasplit(bl):
    """A paragraph the library broke with a blank line (<br><br>) prints as two paragraphs."""
    res = []
    for h, k in bl:
        if h.startswith('<p>') and re.search(r'<br>\s*<br>', h):
            for part in re.split(r'\s*<br>\s*<br>\s*', h[3:-4]):
                if part.strip(): res.append((f'<p>{part.strip()}</p>', k))
        else: res.append((h, k))
    return res
def is_task(x):
    return isinstance(x, Tag) and 'task' in (x.get('class') or [])
def group_tasks(tasks, ch):
    """Maintenance tasks: a tick box, how often, the task in bold, then what to do (and what a fault looks like)."""
    items = []
    for t_ in tasks:
        fq = t_.find(class_='freq'); nm = t_.find(class_='task-name'); dt = t_.find(class_='task-detail'); sp = t_.find(class_='task-spec')
        items.append('<li><span class="box"></span>' + (f'<span class="cnum">{squash(inline(fq, ch))}</span>' if fq else '')
                     + f'<strong>{squash(inline(nm, ch)) if nm else ""}</strong>' + (f'<br>{squash(inline(dt, ch))}' if dt else '')
                     + (f'<br><em>{squash(inline(sp, ch))}</em>' if sp else '') + '</li>')
    return '<ul class="check">' + ''.join(items) + '</ul>'
def is_task_row(x):
    return isinstance(x, Tag) and bool(set(x.get('class') or []) & {'task-row', 'cl-row', 'check-item'})
BADGE = {'b-demo': 'ok', 'b-refresh': 'caution', 'b-sched': 'plain', 'b-out': 'stop'}
def group_task_rows(rows, ch):
    """Checklist rows (R23 tasks, R2 departure checks, R37 skills): tick box, category label, the item in bold, its
    badge (CRITICAL / status), then the detail, the status line and any sign-off line."""
    items = []
    for r_ in rows:
        cat = r_.find(class_=['task-cat', 'cl-cat']); nm = r_.find(class_=['task-name', 'cl-item-name', 'check-name'])
        badges = []
        for b in (nm.find_all(class_='badge') if nm else []) + r_.find_all(class_='crit-badge'):
            bc = set(b.get('class') or [])
            lvl = 'stop' if 'crit-badge' in bc else next((v for k_, v in BADGE.items() if k_ in bc), 'plain')
            badges.append(f' <span class="fbadge {lvl}">{text_of(b.get_text(" ", strip=True), ch)}</span>'); b.extract()
        who = nm.find(class_='who') if nm else None
        wt = who.extract().get_text(' ', strip=True) if who is not None else ''
        rest = []
        for d in r_.find_all(class_=['task-detail', 'cl-detail', 'check-detail', 'task-spec', 'signoff']):
            c_ = set(d.get('class') or [])
            t_ = squash(inline(d, ch))
            rest.append(f'<em>{t_}</em>' if c_ & {'task-spec', 'signoff'} else t_)
        items.append('<li><span class="box"></span>' + (f'<span class="cnum">{squash(inline(cat, ch))}</span>' if cat else '')
                     + f'<strong>{squash(inline(nm, ch)) if nm else ""}</strong>' + ''.join(badges)
                     + (f' <span class="cnum">{text_of(wt, ch)}</span>' if wt else '') + ''.join(f'<br>{t}' for t in rest) + '</li>')
    return '<ul class="check rows">' + ''.join(items) + '</ul>'
def is_kv_row(x):
    return isinstance(x, Tag) and bool(set(x.get('class') or []) & {'row', 'fluid-item', 'wt-row'}) and not x.find(class_='cc-label')
def group_kv_rows(rows, ch):
    """Label / value rows (R1 reference card, R1 fluids, R11 zone weights) as spec rows."""
    out_ = ''
    for r_ in rows:
        c_ = set(r_.get('class') or [])
        if 'fluid-item' in c_:
            k = r_.find(class_='f-label'); v = ' · '.join(squash(inline(x, ch)) for x in r_.find_all(class_=['f-spec', 'f-cap']))
        elif 'wt-row' in c_:
            k = r_.find(class_='wt-zone'); vv = r_.find(class_='wt-kg'); v = squash(inline(vv, ch)) if vv else ''
        else:
            k = r_.find(class_='row-label'); vv = r_.find(class_=['row-val', 'row-value']); v = squash(inline(vv, ch)) if vv else ''
        out_ += f'<tr><td class="k">{squash(inline(k, ch)) if k else ""}</td><td class="v2">{v}</td></tr>'
    return f'<table class="spec">{out_}</table>'
def is_info_row(x):
    return isinstance(x, Tag) and 'info-row' in (x.get('class') or [])
def group_info_rows(rows, ch):
    out_ = ''
    for r_ in rows:
        k = r_.find(class_='info-key'); v = r_.find(class_='info-val'); vc = ' '.join(v.get('class') or []) if v else ''
        tone = ' bad' if 'val-stop' in vc else ' warnv' if 'val-warn' in vc else ' okv' if 'val-ok' in vc else ''
        out_ += f'<tr><td class="k">{squash(inline(k, ch)) if k else ""}</td><td class="v2{tone}">{squash(inline(v, ch)) if v else ""}</td></tr>'
    return f'<table class="spec">{out_}</table>'
INLINE_TAGS = {'strong', 'b', 'em', 'i', 'a', 'span', 'br', 'sup', 'sub', 'code', 'small', 'abbr', 'cite'}
def is_inline(k):
    if isinstance(k, NavigableString): return True
    if not isinstance(k, Tag) or k.name not in INLINE_TAGS: return False
    kc = set(k.get('class') or [])
    return not (kc & {'subsec', 'section-num', 'diag-symptom'})   # spans that carry structure are handled as blocks
def group_inline(nodes, ch):
    frag = BeautifulSoup('<x>' + ''.join(str(n) for n in nodes) + '</x>', 'lxml').x
    t = squash(inline(frag, ch))
    return f'<p>{t}</p>' if t.strip(' .,;:') else ''
def is_check_step(x):
    return isinstance(x, Tag) and bool(set(x.get('class') or []) & {'check-step', 'flow-step', 'proto-step', 'fix-step'})
def group_check_steps(steps, ch):
    nums, texts = [], []
    for st in steps:
        nn = st.find(class_=['step-num', 'flow-num', 'proto-num', 'step-stop', 'fix-num'])
        num = nn.get_text(strip=True) if nn else ''
        if nn is not None: nn.extract()
        for tt in st.find_all(class_=lambda c: c and c.endswith('-title')):   # the step's title in bold, a space after it
            tt.name = 'strong'; tt.attrs = {}; tt.append(' ')
        nums.append(num); texts.append(squash(inline(st, ch)))
    if all(re.fullmatch(r'\d+', n) for n in nums):
        return '<ol>' + ''.join(f'<li value="{n}">{t}</li>' for n, t in zip(nums, texts)) + '</ol>'
    return '<ul class="flow">' + ''.join(f'<li><span class="mk lbl">{text_of(n, ch)}</span>{t}</li>' for n, t in zip(nums, texts)) + '</ul>'
def is_tree_part(x):
    return isinstance(x, Tag) and bool(set(x.get('class') or []) & {'tree-row', 'tree-indent', 'tree-branch', 'tree-node'}) and not x.find(class_='tree-q')
def group_tree(parts, ch):
    items = []
    def walk(x):
        xc = set(x.get('class') or [])
        if 'tree-row' in xc:
            nodes = [squash(inline(n, ch)) for n in x.find_all(class_='tree-node')]
            items.append('<li class="q">' + ' <span class="sym arr">→</span> '.join(f'<strong>{n}</strong>' if i else n for i, n in enumerate(nodes)) + '</li>')
        elif 'tree-node' in xc:   # an end node standing on its own line
            items.append(f'<li class="q"><strong>{squash(inline(x, ch))}</strong></li>')
        elif 'tree-branch' in xc:
            lab = x.find(class_='tree-branch-label'); nd = x.find(class_='tree-node')
            items.append(f'<li class="out"><span class="mk lbl">{squash(inline(lab, ch)) if lab else ""}</span>{squash(inline(nd, ch)) if nd else ""}</li>')
        else:
            for y in x.find_all(True, recursive=False): walk(y)
    for p_ in parts: walk(p_)
    return '<ul class="flow tree">' + ''.join(items) + '</ul>'

def children_blocks(node, ch):
    return gather_cards(children_blocks0(node, ch))
def gather_cards(bl):
    """Consecutive card blocks (R23 decision cards, R11 packing zones) form one grid of cards."""
    res, run = [], []
    def flush():
        if run: res.append((f'<div class="cards c{3 if len(run) == 3 else 2}">' + ''.join(run) + '</div>', 'wide')); run.clear()
    for h, k in bl:
        if k == 'card': run.append(h); continue
        flush(); res.append((h, k))
    flush()
    return res
def children_blocks0(node, ch):
    res, kids = [], [k for k in node.children if not isinstance(k, Comment) and not (isinstance(k, NavigableString) and not k.strip())]
    i = 0
    while i < len(kids):
        k = kids[i]
        if is_inline(k):   # a run of loose text and inline tags is one paragraph
            j = i
            while j < len(kids) and is_inline(kids[j]): j += 1
            h = group_inline(kids[i:j], ch)
            if h: res.append((h, 'body'))
            i = j; continue
        for test, grp in ((is_check_step, group_check_steps), (is_tree_part, group_tree), (is_task, group_tasks), (is_info_row, group_info_rows), (is_task_row, group_task_rows), (is_kv_row, group_kv_rows),
                          (lambda x: isinstance(x, Tag) and 'procedure-step' in (x.get('class') or []), group_steps),
                          (lambda x: isinstance(x, Tag) and 'checklist-item' in (x.get('class') or []), group_check),
                          (is_mark_p, group_marks), (is_bullet_p, group_bullets)):
            if test(k):
                j = i
                while j < len(kids) and test(kids[j]): j += 1
                res.append((grp(kids[i:j], ch), 'body')); i = j; break
        else:
            res += blocks(k, ch); i += 1
    return res

def spec_rows(bar, ch):
    rows = []
    for it in bar.find_all(class_='status-item'):
        v = it.find(class_='status-value'); l = it.find(class_='status-label')
        if v and l: rows.append(f'<tr><td class="k">{text_of(l.get_text(" ", strip=True), ch)}</td><td class="v">{text_of(v.get_text(" ", strip=True), ch)}</td></tr>')
    if not rows: return ''
    k = (len(rows) + 1) // 2   # two halves, one per column, so the panel is as short as it can be
    return ('<table class="spec">' + ''.join(rows[:k]) + '</table>'
            + ('<table class="spec colbrk">' + ''.join(rows[k:]) + '</table>' if rows[k:] else ''))

import itertools as _it
CLC = _it.count(1)
# ---------------- page layout: the modular rule ----------------
# Researched 25 Nov 2026 (owner: "better rules for handling the use of columns"). Newspaper modular design: every
# story is a rectangle and its headline covers all of its own columns; typesetting keeps a heading with the text
# under it. Here a MODULE is an h3 and everything under it until the next h3 or h2.
#   1 A module never runs from one column into the other beside a different module. Either the module is short and
#     stands whole in ONE column (heading on top), or it is long and gets the full page width: heading across the
#     page, then its own two balanced columns, read down the left then down the right.
#   2 Wide items (tables of 3+ columns, drawings) stay inside their module and split its columns; the columns above
#     are balanced, so the reading order is left column, right column, then the table.
#   3 Clear space separates one column block from the next table, heading or column block (template: .cols margin).
#   4 One short block alone is set full width; a long single block keeps two columns (line length).
BOXED = ('<div class="dtree', '<div class="notice', '<div class="aside', '<table', '<ul class="flow', '<ul class="check', '<ul class="qa')
SHORT = 1100          # characters of text: a module this short stands whole in one column
LONE = 700            # a lone block shorter than this goes full width
def tlen(h): return len(re.sub(r'<[^>]+>', '', h))
def flow(bl):
    """Blocks of one module: runs of body blocks go into balanced columns; wide blocks span the page.
    A heading directly before a wide block goes with it; a heading never ends a run."""
    parts, run, carry = [], [], []
    def flush():
        while run and run[-1][1] == 'head':
            carry.insert(0, run.pop())
        if len(run) == 1 and (tlen(run[0][0]) < LONE or run[0][0].startswith(BOXED)):
            parts.append('<div class="one">' + run[0][0] + '</div>')
        elif 2 <= len(run) <= 3 and all(h.startswith('<div class="aside">') for h, _ in run):
            # (owner, 26 Nov 2026: p. 62) two or three side boxes alone stand as a row of cards, not unequal columns
            parts.append(f'<div class="cards c{len(run)}">' + ''.join(h.replace('<div class="aside">', '<div class="cardc">', 1) for h, _ in run) + '</div>')
        elif 2 <= len(run) <= 3 and any(h.startswith(BOXED) and tlen(h) > .5 * sum(tlen(x) for x, _ in run) for h, _ in run):
            # (owner, 26 Nov 2026: pp. 61-62) a short text beside one long box that cannot break leaves a column half
            # empty: the blocks stand one under the other across the page instead
            parts.append(''.join('<div class="one">' + h + '</div>' for h, _ in run))
        elif run: parts.append(f'<div class="cols" id="cl{next(CLC)}">' + ''.join(h for h, _ in run) + '</div>')
        run.clear()
    for h, kind in bl:
        if kind == 'wide':
            carry.clear(); flush()
            if carry: parts.append('<div class="wide">' + ''.join(x for x, _ in carry) + '</div>')
            carry.clear()
            parts.append(h)
        else:
            run.append((h, kind))
    carry.clear(); flush()
    if carry: parts.append('<div class="wide">' + ''.join(x for x, _ in carry) + '</div>')
    return ''.join(parts)
SECTION_WIDE = ('<h2', '<p class="h2sub"', '<p class="lead"', '<p class="quote"', '<p class="signoff"', '<div class="closing"')
def layout(bl):
    parts, mods = [], []
    def is_short(m):
        return not any(k == 'wide' for _, k in m) and sum(tlen(h) for h, _ in m) <= SHORT
    def emit_long(m):
        i = 0
        while i < len(m) and m[i][1] == 'head' and not m[i][0].startswith('<h4 class="fault"'): i += 1
        head = ''.join(h for h, _ in m[:i])
        if head and m[0][0].startswith('<h3'):
            grp = ' class="grp"' if i < len(m) and m[i][0].startswith('<h4 class="fault"') else ''
            parts.append(f'<div class="mhead" id="mh{next(CLC)}">' + head.replace('<h3', f'<h3{grp} data-m="1"', 1) + '</div>'); body = m[i:]
        else:
            body = m
        # fault cards inside a module follow the same rule one level down: each card is a module of its own
        cuts = [j for j, (h, _) in enumerate(body) if h.startswith('<h4 class="fault"')]
        if not cuts:
            parts.append(flow(body)); return
        if cuts[0] > 0: parts.append(flow(body[:cuts[0]]))
        subs = [body[a:b] for a, b in zip(cuts, cuts[1:] + [len(body)])]
        group = []
        for sm in subs:
            if is_short(sm): group.append(sm); continue
            if group: emit_shorts(group, sub=True); group = []
            parts.append(f'<div class="mhead" id="mh{next(CLC)}">' + sm[0][0].replace('<h4', '<h4 data-m="1"', 1) + '</div>'); parts.append(flow(sm[1:]))
        if group: emit_shorts(group, sub=True)
    def emit_shorts(group, sub=False):
        if len(group) == 1:
            if not sub: emit_long(group[0]); return
            parts.append(f'<div class="mhead" id="mh{next(CLC)}">' + group[0][0][0].replace('<h4', '<h4 data-m="1"', 1) + '</div>'); parts.append(flow(group[0][1:])); return
        parts.append(f'<div class="cols mods" id="cl{next(CLC)}">' + ''.join(
            f'<div class="mod" id="md{next(CLC)}">' + ''.join(h for h, _ in m) + '</div>' for m in group) + '</div>')
    def flush():
        group = []
        for m in mods:
            if m and m[0][0].startswith('<h3') and is_short(m): group.append(m)
            else:
                if group: emit_shorts(group); group = []
                emit_long(m)
        if group: emit_shorts(group)
        mods.clear()
    for h, kind in bl:
        if kind == 'wide' and h.startswith(SECTION_WIDE):
            flush(); parts.append(h); continue
        if h.startswith('<h3') or not mods: mods.append([])
        mods[-1].append((h, kind))
    flush()
    return ''.join(parts)

import itertools
HDC = itertools.count(1)
def family(hexc):
    """Colour family from the chapter colour: solid, dark (text), mid / pale / faintest tints."""
    r, g, b = (int(hexc.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    mix = lambda w, o=(255, 255, 255): '#%02x%02x%02x' % tuple(round(c * w + oc * (1 - w)) for c, oc in zip((r, g, b), o))
    return f'--ch: {hexc}; --ch-dk: {mix(.62, (10, 10, 14))}; --ch-md: {mix(.24)}; --ch-lt: {mix(.13)}; --ch-xl: {mix(.06)}'

def convert(ch):
    n = ch['n']
    path = os.path.join(HERE, 'introduction.html') if ch['r'] == 'INTRO' else os.path.join(repo, ch['file'])
    soup = load(path)
    body = soup.body
    for c in body.find_all(string=lambda x: isinstance(x, Comment)): c.extract()
    for t in body.find_all(['script', 'style', 'nav', 'button', 'noscript']):
        if t.name == 'style' and t.find_parent('svg') is not None: continue   # a drawing's own colours stay with it (R11 layouts)
        t.decompose()
    sub = soup.find(class_=['std-sub', 'mh-sub'])
    subt = sub.get_text(' ', strip=True) if sub else ''   # read now: the masthead is removed below
    bar = body.find(class_='status-bar')
    spec = spec_rows(bar, ch) if bar else ''
    for cls in ['sticky-nav-unit', 'sticky-wrap', 'toc-bar', 'xref-bar', 'lib-home-btn', 'mh-date', 'status-bar', 'ref-back']:
        for t in body.find_all(class_=cls): t.decompose()
    main = body.find('main') or body.find(class_=['content', 'main']) or body
    for d in body.find_all('div'):   # a 'Cross-Reference' bar of page buttons is a web menu, like the xref-bar: not printed
        kids = [k for k in d.children if isinstance(k, Tag)]
        if kids and kids[0].name == 'span' and kids[0].get_text(strip=True) == 'Cross-Reference' and all(k.name == 'a' for k in kids[1:]):
            report.append(f'{ch["r"]}: cross-reference button bar not printed (web menu): ' + ' · '.join(k.get_text(' ', strip=True) for k in kids[1:]))
            d.decompose()
    for sp in body.find_all('span', class_='check-note'):   # a note tucked into a checklist label: its own line, in italics
        sp.name = 'em'; sp.attrs = {}; sp.insert_before(soup.new_tag('br'))
    def section_nodes(h):
        nodes = [h]
        for sib in h.find_next_siblings():
            if sib.name == 'h2': break
            nodes.append(sib)
        return nodes
    if ch.get('section'):   # one section of a page: its own heading goes, the chapter opener carries the title
        main = body.find(id=ch['section'])
        for x in main.find_all(class_='section-head', limit=1): x.decompose()
        lib = page_title(ch['file'])
        ch['sec_of'] = lib
    for d in ch['drop']:
        e = main.find(id=d)
        if e is not None and e.name != 'h2': e.decompose()
    for h3 in main.find_all('h3'):   # a library h3 that names the untitled card under it is the module heading (field fixes)
        nx = h3.find_next_sibling()
        if nx is not None and nx.name == 'div' and 'card' in (nx.get('class') or []) and not nx.find(class_='card-title'):
            h3['class'] = (h3.get('class') or []) + ['fixhead']
    for h2 in main.find_all('h2'):
        hid = h2.get('id')
        if hid in ch['drop'] or (ch['keep'] and hid not in ch['keep']):
            for x in section_nodes(h2): x.decompose()
    for sid, nkeep in ch['trim'].items():
        h = main.find(id=sid)
        if h is None: continue
        seen = 0
        for x in section_nodes(h)[1:]:
            for card in x.find_all(class_='card', recursive=True) if 'card' not in (x.get('class') or []) else [x]:
                seen += 1
                if seen > nkeep: card.decompose()
        report.append(f'{ch["r"]}: section {sid} trimmed to its first {nkeep} cards (specimen)')
    if ch.get('section'):   # a bare '§3' inside one section of R29 means R29 section 3; 'R10 §9' is left for the code rules
        for sn in main.find_all(string=re.compile(r'§\s*\d+')):
            new = re.sub(r'(\bR\d{1,2}\s*)?§\s*(\d+)',
                         lambda m: m.group(0) if m.group(1) else f'{ch["sec_of"]}, library section {m.group(2)}', str(sn))
            if new != str(sn): sn.replace_with(new)
    bl = children_blocks(main, ch)
    htmlx = layout(bl)
    if ch.get('sheet'): htmlx = htmlx.replace('<div class="cols"', '<div class="cols sheet"')
    if ch.get('prose'):   # (owner, 27 Nov 2026: ch. 7 'too bland') long essays: columns run page to page as in any book,
        # never opened to one full-width column; a paragraph led by a bold name gets that name as a run-in heading
        htmlx = htmlx.replace('<div class="cols"', '<div class="cols prose"')
        htmlx = re.sub(r'<p><strong>((?:(?!</strong>).){2,60})</strong>', lambda m: f'<p class="runin"><strong>{m.group(1)}</strong>' if len(re.sub(r"<[^>]+>", "", m.group(1)).split()) <= 7 else m.group(0), htmlx)
    # a group heading followed straight by a fault heading is one heading unit: they never part at a page foot
    htmlx = re.sub(r'(<div class="mhead" id="mh\d+"><h3 class="grp"[^>]*>.*?</h3>)</div><div class="mhead" id="mh\d+">', r'\1', htmlx)
    htmlx = htmlx.replace('<li value="', '<li class="v" value="')   # the list shows the library's own number
    htmlx = re.sub(r'<table(?=[ >])', lambda m: f'<table id="tb{next(HDC)}"', htmlx)
    htmlx = re.sub(r'<(h2|h3|h4)(?=[ >])', lambda m: f'<{m.group(1)} id="hd{next(HDC)}"', htmlx)
    def link(m):
        r = m.group(1); k = INBOOK[r]
        return f'<a class="xref" href="#ch{k}">{BYN[k]["title"]}</a>'
    htmlx = re.sub(r'‹(R\d+)›', link, htmlx)
    segs = re.split(r'(?=<h[23][ >])', htmlx); outs = []
    for sg in segs:   # within one heading's block, only the first reference to a chapter carries its page number
        seen = set()
        def once(m):
            if m.group(1) in seen: return m.group(0).replace('class="xref"', 'class="xref again"')
            seen.add(m.group(1)); return m.group(0)
        outs.append(re.sub(r'<a class="xref" href="#(ch\d+)">', once, sg))
    htmlx = ''.join(outs)
    spec = re.sub(r'‹(R\d+)›', link, spec)
    left = sorted(set(re.findall(r'\b(?:OI|RA|EX)-\d+\b|\bR\d{1,2}\b(?=\s|§|\))', BeautifulSoup(htmlx, 'lxml').get_text())))
    if left: report.append(f'{ch["r"]}: codes still in text: {", ".join(left)}')
    notes = '' if (ch['nonotes'] or ch['r'] == 'INTRO' or ch.get('section') or ch['r'].endswith('.html')) else \
        '<div class="notes"><h2>Notes</h2>' + '<div class="nline"></div>' * 24 + '</div>'
    opener = (f'<div class="ch-open"><div class="ch-text"><div class="ch-num">Chapter {ch["label"]}</div><h1>{H.escape(ch["title"])}</h1>'
              f'<p class="ch-sub">{H.escape(subt)}</p></div>'
              f'<div class="ch-big">{int(ch["label"]):02d}</div></div>')
    return (f'<section class="chapter{" small-type" if ch["small"] else ""}{" intro" if ch["r"] == "INTRO" else ""}" id="ch{n}" style="page: ch{n}; {family(ch["colour"])}">'
            + opener + (f'<div class="cols glance">{spec}</div>' if spec else '')
            + htmlx + notes + '</section>'), bl

# ---------------- assemble ----------------
commit = subprocess.run(['git', '-C', repo, 'log', '-1', '--format=%H'], capture_output=True, text=True).stdout.strip()
today = datetime.date.today().strftime('%-d %B %Y')
parts_html, toc, pn = [], '', 0
for c in chapters:
    if c.get('part'):
        pn = int(c['num']) if c.get('num') else pn + 1   # a batch can print its part's real number (num:3)
        idx = chapters.index(c); members = []
        for c2 in chapters[idx + 1:]:
            if c2.get('part'): break
            members.append(c2)
        lst = ''.join(f'<div>{c2["label"]} · {H.escape(c2["title"])}</div>' for c2 in members)
        parts_html.append(f'<section class="part" id="part{pn}" style="background-color: {c["colour"]}"><div class="part-num">Part {pn}</div>'
                          f'<div class="part-title">{H.escape(c["title"])}</div><div class="part-list">{lst}</div></section>')
        toc += f'<li class="toc-part"><a href="#part{pn}">Part {pn} · {H.escape(c["title"])}</a></li>'
    else:
        h, bl = convert(c)
        c['blocks'] = bl
        parts_html.append(h)
        toc += f'<li><a href="#ch{c["n"]}">{c["label"]}. {H.escape(c["title"])}</a></li>'
edge = ''
for i, c in enumerate(chs_only):
    pos = ['top', 'middle', 'bottom'][i % 3]
    tab = (f'content: "{c["label"]}"; background: {c["colour"]}; color: #ffffff; font: 400 15pt Bebas; '
           'width: 9mm; height: 40mm; vertical-align: middle; text-align: center;')
    pill = (f'content: counter(page); background: {c["colour"]}; color: #ffffff; font: 600 8pt Plex; '
            'width: 10mm; height: 6mm; text-align: center; vertical-align: middle;')
    edge += (f'@page ch{i+1}:right {{ @right-{pos} {{ {tab} margin-left: 9mm; }} @bottom-right {{ {pill} }} '
             f'@top-right {{ color: {c["colour"]}; }} }}\n'
             f'@page ch{i+1}:left {{ @left-{pos} {{ {tab} margin-right: 9mm; }} @bottom-left {{ {pill} }} '
             f'@top-left {{ color: {c["colour"]}; }} }}\n')
import math, random
def contour_paths(w, h, centres, rings, seed, step):
    rnd = random.Random(seed); out = []
    for cx, cy in centres:
        a1, a2, p1, p2 = rnd.uniform(.08, .2), rnd.uniform(.04, .1), rnd.uniform(0, 6.3), rnd.uniform(0, 6.3)
        for k in range(1, rings + 1):
            r = k * step; pts = []
            for j in range(73):
                t = j / 72 * 2 * math.pi
                rr = r * (1 + a1 * math.sin(3 * t + p1 + k * .15) + a2 * math.sin(5 * t + p2))
                pts.append(f'{cx + rr * math.cos(t):.1f},{cy + rr * .72 * math.sin(t):.1f}')
            out.append('M' + ' L'.join(pts) + 'Z')
    return out
def contours_svg():
    paths = contour_paths(600, 160, [(470, 120), (90, -10)], 16, 7, 13)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 160" preserveAspectRatio="xMidYMid slice">'
            + ''.join(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-opacity=".16" stroke-width="1"/>' for d in paths) + '</svg>')
PLAN = []
if os.environ.get('BOOK_PLAN'):
    for line in open(os.environ['BOOK_PLAN'], encoding='utf-8'):
        if line.strip() and not line.startswith('#'):
            c = [x.strip() for x in line.split('|')]; PLAN.append((c[0], c[1], c[2]))
def cover_svg():
    cols = [c for _, _, c in PLAN if _ != 'PART'] or [c['colour'] for c in chs_only]
    W, Hh = 210, 297
    g = []
    # contour field
    for d in contour_paths(W, Hh, [(170, 60), (30, 250), (190, 255)], 14, 3, 7.5):
        g.append(f'<path d="{d}" fill="none" stroke="#f5a524" stroke-opacity=".13" stroke-width=".35"/>')
    # retro sun of chapter colours
    cx, cy, r = 110, 168, 60
    g.append(f'<defs><clipPath id="sun"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath></defs><g clip-path="url(#sun)">')
    sun = ['#f8c33a', '#f5a524', '#ef7d16', '#e2581a', '#d9361e', '#c81d4a', '#a21caf', '#7c3aed', '#4f46e5']
    y, i = cy - r, 0
    while y < cy + r and i < 40:
        band = 13 - i * 1.25 if i < 8 else 3.5
        gap = 0 if i < 3 else min(1.2 + (i - 3) * 1.0, 4.5)
        g.append(f'<rect x="{cx - r}" y="{y:.1f}" width="{2 * r}" height="{max(band, 2.5):.1f}" fill="{sun[min(i, len(sun) - 1)]}"/>')
        y += max(band, 2.5) + gap; i += 1
    g.append('</g>')
    # mountains
    g.append('<path d="M0,204 L20,188 L36,196 L58,172 L76,190 L94,180 L118,198 L142,168 L160,186 L178,178 L196,192 L210,186 L210,222 L0,222 Z" fill="#232733"/>')
    g.append('<path d="M0,212 L28,200 L50,207 L72,195 L98,210 L128,202 L154,211 L182,198 L210,206 L210,224 L0,224 Z" fill="#1b1e27"/>')
    # ground and tracks
    g.append('<rect x="0" y="222" width="210" height="75" fill="#15171d"/>')
    for x0, x1 in ((-30, 92), (240, 132)):
        g.append(f'<path d="M{x0},297 L{x1},222" stroke="#f5a524" stroke-opacity=".35" stroke-width="1.2" fill="none"/>')
    for d in contour_paths(W, Hh, [(105, 310)], 10, 11, 9):
        g.append(f'<path d="{d}" fill="none" stroke="#f5a524" stroke-opacity=".10" stroke-width=".35"/>')
    # the truck: a generic long-wheelbase station wagon, side view (no badge, no logo), standing on the horizon
    ink = '#0b0c10'
    body = ('M0,-13 L0,-47 L57,-47 L64,-34 L89,-32.5 L92,-31 L92,-17 L97,-17 L97,-11 L91,-11 '
            'A13,13 0 0 0 65,-11 L33,-11 A13,13 0 0 0 7,-11 L0,-11 Z '
            'M4,-44 L19,-44 L19,-35 L4,-35 Z M22,-44 L37,-44 L37,-35 L22,-35 Z M40,-44 L55.5,-44 L61,-35 L40,-35 Z')
    t = [f'<path d="{body}" fill="{ink}" fill-rule="evenodd"/>',
         f'<rect x="1" y="-52" width="56" height="2.4" fill="{ink}"/>']
    t += [f'<rect x="{x}" y="-50" width="1.8" height="3.4" fill="{ink}"/>' for x in (3, 18, 33, 48)]
    t += [f'<rect x="{x}" y="-59.5" width="7.2" height="7.5" rx=".9" fill="{ink}"/>' for x in (4, 12.6, 21.2)]
    t += [f'<rect x="31" y="-56.5" width="23" height="4.5" rx="1.2" fill="{ink}"/>',
          f'<path d="M62.5,-35 L62.5,-53 L67.5,-54.5" stroke="{ink}" stroke-width="2.2" fill="none" stroke-linecap="round"/>',
          f'<path d="M92,-30 L99,-30 L99,-13" stroke="{ink}" stroke-width="2.4" fill="none"/>',
          f'<circle cx="-2" cy="-29" r="9" fill="{ink}"/><circle cx="-2" cy="-29" r="3.2" fill="none" stroke="#f5a524" stroke-opacity=".7" stroke-width=".8"/>']
    t += [f'<circle cx="{x}" cy="-11" r="11" fill="{ink}"/><circle cx="{x}" cy="-11" r="4.6" fill="none" stroke="#f5a524" stroke-width="1.1"/>' for x in (20, 78)]
    g.append('<g transform="translate(58,222)">' + ''.join(t) + '</g>')
    # every chapter's colour along the foot
    n = len(cols); bw = W / n
    for k, col in enumerate(cols):
        g.append(f'<rect x="{k * bw:.2f}" y="284" width="{bw + .05:.2f}" height="13" fill="{col}"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {Hh}" width="{W}mm" height="{Hh}mm">' + ''.join(g) + '</svg>'
os.makedirs(out, exist_ok=True)
open(os.path.join(out, 'contours.svg'), 'w').write(contours_svg())
open(os.path.join(out, 'cover.svg'), 'w').write(cover_svg())
css = (open(os.path.join(HERE, 'template.css'), encoding='utf-8').read().replace('FONTS', fonts)
       .replace('url(CONTOURS)', 'url(file://' + os.path.abspath(os.path.join(out, 'contours.svg')) + ')')
       .replace('url(COVER)', 'url(file://' + os.path.abspath(os.path.join(out, 'cover.svg')) + ')') + edge)
if PLAN:   # contents of the whole planned book, every chapter in its colour; chapters in this build carry page numbers
    built = {(c['r'] if not c.get('section') else c['r'] + '#' + c['section']): c for c in chs_only}
    toc, pn, k = '', 0, 0
    for src, title, col in PLAN:
        if src == 'PART':
            pn += 1; toc += f'<li class="toc-part" style="color:{col}">Part {pn} · {H.escape(title)}</li>'; continue
        k += 1
        chip = f'<span class="chip" style="background:{col}">{k}</span>'
        b = built.get(src)
        toc += (f'<li><a href="#ch{b["n"]}">{chip}{H.escape(title)}</a></li>' if b else
                f'<li class="plan">{chip}{H.escape(title)}</li>')
    toc_block = f'<div class="cols-toc"><ol>{toc}</ol></div>'
else:
    toc_block = f'<ol>{toc}</ol>'
title_page = os.environ.get('BOOK_TITLE', 'LC76 Field<br>Handbook')
edition = os.environ.get('BOOK_EDITION', 'Template specimen')
doc = f'''<!DOCTYPE html><html lang="en-ZA"><head><meta charset="utf-8"><title>LC76 Field Handbook</title><style>{css}</style></head><body>
<section class="cover"><div class="cv-eyebrow">Volume II</div><div class="cv-title">LC76</div><div class="cv-title2">Field Handbook</div>
<div class="cv-sub">Land Cruiser 76 · 1HZ · on the road and in the bush</div>
<div class="cv-foot">{edition} · {today} · library commit {commit[:7]}<br>The live library on the phone is always current. Where this book and the library disagree, the library wins.<br>Printed for Neil and Mary-Ann. Not for sale.</div></section>
<section class="contents"><h2>Contents</h2>{toc_block}</section>
{''.join(parts_html)}</body></html>'''
open(os.path.join(out, 'book.html'), 'w', encoding='utf-8').write(doc)
from weasyprint import HTML
MM = 96 / 25.4
def walk(b, depth=0):
    yield b, depth
    for c in getattr(b, 'children', []) or []:
        yield from walk(c, depth + 1)
PARENT = {}
def prev_el(e):
    """Element before e among its parent's children (ElementTree has no getprevious)."""
    par = PARENT.get(id(e))
    if par is None: return None
    kids = list(par); i = next((k for k, x in enumerate(kids) if x is e), 0)
    return kids[i - 1] if i > 0 else None
def index_parents(document):
    PARENT.clear()
    root = document.pages[0]._page_box.element if hasattr(document.pages[0]._page_box, 'element') else None
    seen = set()
    for pg in document.pages:
        for b, _ in walk(pg._page_box):
            el = getattr(b, 'element', None)
            if el is None or id(el) in seen: continue
            seen.add(id(el))
            for c in el: PARENT[id(c)] = el
def layout_pass(document):
    """Headings the page put in the wrong place: an h2 bar with little room under it moves to the next page;
    a heading at the top of a column loses its top margin, so both columns start level."""
    push, flush_top, split = set(), set(), {}
    seen_cols = set()
    for pg in document.pages:
        # a two-column run that ends on a new page with everything in its left column: those last blocks go full width
        for b, _ in walk(pg._page_box):
            el = getattr(b, 'element', None)
            if el is None or not (el.get('id') or '').startswith('cl') or getattr(b, 'element_tag', '') != 'div': continue
            cid = el.get('id'); kids = getattr(b, 'children', []) or []
            if kids and all(getattr(k, 'element', None) is el for k in kids):   # this is the multicol box, kids are columns
                if cid in seen_cols and len(kids) == 1:
                    tops = [c.element for c in kids[0].children if getattr(c, 'element', None) is not None]
                    kidsel = list(el)
                    idx = [i for t in tops for i, k in enumerate(kidsel) if k is t]
                    if idx and len(set(idx)) <= 2 and min(idx) > 0: split[cid] = min(idx)
                seen_cols.add(cid)
    for pg in document.pages:
        page = pg._page_box
        bottom = page.content_box_y() + page.height
        for b, _ in walk(page):
            el = getattr(b, 'element', None)
            if el is None or getattr(b, 'element_tag', '') not in ('h2', 'h3', 'h4', 'p'): continue
            hid = el.get('id') or ''
            if b.element_tag == 'p':
                continue
            if not hid.startswith('hd'): continue
            in_mhead = el.get('data-m') == '1'
            # (owner, 25 Nov 2026) no fixed 'room left' thresholds: a heading moves only when it is actually parted
            # from its content (rule below), so a heading goes as high up the page as its content allows
            par = parent_of.get(id(b))
            if par is not None and par.children and par.children[0] is b and b.margin_top and b.margin_top > 0:
                flush_top.add(hid)
    # a section heading (with its lead) whose first content starts on a later page moves to that page
    firstpage = {}
    for i, pg in enumerate(document.pages):
        for b, _ in walk(pg._page_box):
            el = getattr(b, 'element', None)
            if el is not None and id(el) not in firstpage: firstpage[id(el)] = (i, el)
    # (owner, 25 Nov 2026: 'the rule is not followed consistently'): a heading never ends a page apart from its
    # content. Where the page still has room (over 60 mm), the content is opened up to start under its heading
    # (a block of side-by-side modules becomes modules one after another); otherwise the heading moves on.
    free = page_free(document)
    heads = [v for v in firstpage.values() if v[1].tag == 'h2' or (v[1].tag == 'div' and v[1].get('class') == 'mhead')]
    for i, el in heads:
        hid = el.get('id') or ''
        if el.tag == 'div':
            hh = next((c for c in el if (c.get('id') or '').startswith('hd')), None)
            if hh is None: continue
            hid = hh.get('id')
        elif not hid.startswith('hd'): continue
        par = PARENT.get(id(el))
        if par is None: continue
        kids = list(par); k = next((j for j, x in enumerate(kids) if x is el), None)
        if k is None: continue
        nxt = kids[k + 1:]
        firstc = next((x for x in nxt if x.tag != 'p' or 'h2sub' not in (x.get('class') or '')), None)
        body = next((x for x in nxt if not (x.tag == 'p' and any(c in (x.get('class') or '') for c in ('lead', 'h2sub')))
                     and (x.get('class') or '') != 'mhead'), None)
        for x in ([body] if body is not None else []):   # the heading's real content, past any lead
            if id(x) in firstpage and firstpage[id(x)][0] > i:
                bc = body.get('class') or '' if body is not None else ''
                if free[i] > 55 * MM and 'mods' in bc and body.get('id'):
                    unpack.add(body.get('id'))
                elif free[i] > 55 * MM and bc == 'cols' and body.get('id') and body.get('id') not in opened:
                    opened.add(body.get('id')); opencol.add(body.get('id'))   # (owner, 25 Nov 2026) text moves up under its heading, full width
                elif undone.get(hid, 0) < 3:
                    push.add(hid); hardpush.add(hid)
            break
    # (owner rule: a heading never ends a page apart from its content) a table whose header row ends a page with
    # its first row on the next: the heading above it moves with it, or the table starts the next page
    for i, el in [v for v in firstpage.values() if v[1].tag == 'table' and (v[1].get('id') or '').startswith('tb')]:
        rows = [r for r in el.iter('tr')]
        if not rows: continue
        th = [r for r in rows if any(c.tag == 'th' for c in r)]
        body_rows = [r for r in rows if not any(c.tag == 'th' for c in r)]
        if not th or not body_rows or id(th[0]) not in firstpage or id(body_rows[0]) not in firstpage: continue
        if firstpage[id(body_rows[0])][0] <= firstpage[id(th[0])][0]: continue
        tgt = el.get('id'); x = el
        while True:
            pv = prev_el(x)
            if pv is None or id(pv) not in firstpage or firstpage[id(pv)][0] != i: break
            pc = pv.get('class') or ''
            if pv.tag == 'h2': tgt = pv.get('id'); break
            if pc == 'mhead':
                hh = next((c for c in pv if (c.get('id') or '').startswith('hd')), None)
                if hh is not None: tgt = hh.get('id')
                break
            if pv.tag == 'p' or pc in ('one', 'wide'): x = pv; continue
            break
        if tgt: push.add(tgt); hardpush.add(tgt)
    # a heading dragged onto a new page together with side-by-side modules that would not fit, leaving the page
    # before over 60 mm empty: those modules are opened up, so the heading and the first module come back
    # (owner, 25 Nov 2026: pp. 57, 68, 83) any heading or column block that starts a page while the page before is
    # left over 55 mm empty: its text is opened up so it can start on that page and run on — side-by-side modules
    # become modules one after another; a two-column block becomes one full-width column that may break
    cands = heads + [v for v in firstpage.values() if v[1].tag == 'div' and (v[1].get('id') or '').startswith('cl')]
    for i, el in cands:
        if i == 0 or free[i - 1] <= 55 * MM: continue
        pv = prev_el(el)
        if pv is None or id(pv) not in firstpage or firstpage[id(pv)][0] >= i: continue
        par = PARENT.get(id(el))
        if par is None: continue
        kids = list(par); k = next((j for j, x in enumerate(kids) if x is el), None)
        if k is None: continue
        seq = [el] if el.tag == 'div' and (el.get('id') or '').startswith('cl') else kids[k + 1:]
        for x in seq:
            xc = x.get('class') or ''
            if x.tag == 'p' and any(c in xc for c in ('lead', 'h2sub')): continue
            if x.tag == 'div' and xc == 'one' and el.tag == 'h2': continue
            if 'mods' in xc and x.get('id'): unpack.add(x.get('id'))
            elif xc == 'cols' and x.get('id') and x.get('id') not in opened:
                opened.add(x.get('id')); opencol.add(x.get('id'))
            else: break
            break
    return push, flush_top, split
def frags(document):
    """Every box fragment of each id'd element, as (page index, top, height, box)."""
    f = {}
    for i, pg in enumerate(document.pages):
        for b, _ in walk(pg._page_box):
            el = getattr(b, 'element', None)
            if el is None or getattr(b, 'element_tag', '') != 'div': continue
            eid = el.get('id') or ''
            if eid.startswith(('cl', 'md')) and not getattr(b, 'is_column', False):
                lst = f.setdefault(eid, [])
                if not any(x[3] is b for x in lst) and not (lst and lst[-1][0] == i and eid.startswith('cl')):
                    lst.append((i, b.position_y, b.margin_height(), b))
    return f
def column_rules(document, doc_html):
    """(1) A two-column block that runs over a page break is set as one column across the page (owner,
    25 Nov 2026: columns split over two pages are hard to follow). (2) Short modules sharing a column block
    are packed: the order that fits the page best, each module whole in its column (owner: p. 23)."""
    f = frags(document); onecol, packs = set(), {}
    page = document.pages[0]._page_box; colh = page.height
    for eid, lst in f.items():
        if not eid.startswith('cl'): continue
        pages = sorted({x[0] for x in lst})
        total = sum(x[2] for x in lst)
        cls = (lst[0][3].element.get('class') or '')
        if len(pages) > 1 and 'sheet' in cls and total < .9 * colh:   # a spec-sheet section is never split over a page: it moves on whole
            pv = prev_el(lst[0][3].element)
            while pv is not None and pv.tag == 'p': pv = prev_el(pv)
            if pv is not None and pv.tag == 'h2' and pv.get('id'): sheetpush.add(pv.get('id'))
        if len(pages) > 1 and 'mods' not in cls and 'glance' not in cls and 'sheet' not in cls and 'prose' not in cls and total < .9 * colh:
            onecol.add(eid)
            last = [x for x in lst if x[0] == pages[-1]]
            if eid in onecols and sum(x[2] for x in last) < 16 * MM and eid not in squeezed:
                squeezed.add(eid); el = lst[0][3].element
                pv = prev_el(el)
                if pv is not None and (pv.get('id') or '').startswith('mh'):
                    squeeze_css.append(f'#{pv.get("id")}{{margin-top:1.5mm}}'); pv = prev_el(pv)
                    if pv is not None and (pv.get('id') or '').startswith('cl'):
                        squeeze_css.append(f'#{pv.get("id")}{{margin-bottom:1.5mm;line-height:1.3}}')
                squeeze_css.append(f'#{eid}{{line-height:1.3}}')
        if 'mods' in cls and len(pages) > 1 and (eid in packed or eid in nofit):   # packing (and its squeeze) is tried first
            # (owner, 25 Nov 2026: columns are never read across a page break) side-by-side modules that run onto the
            # next page are cut there: the modules already on the first page keep their block, the rest start a new one
            el = lst[0][3].element
            mids = [k.get('id') for k in el if (k.get('id') or '').startswith('md')]
            first = [m for m in mids if f.get(m) and f[m][0][0] == pages[0]]
            if first and len(first) < len(mids):
                modsplit[eid] = mids[len(first):] if mids[:len(first)] == first else None
                if modsplit[eid] is None: del modsplit[eid]
                continue
        if 'mods' in cls and eid not in packed:
            el = lst[0][3].element
            mids = [k.get('id') for k in el if (k.get('id') or '').startswith('md')]
            hs = [sum(x[2] for x in f.get(m, [])) for m in mids]
            if len(mids) < 2 or not all(hs): continue
            pg = document.pages[lst[0][0]]._page_box
            avail = pg.content_box_y() + pg.height - lst[0][1]
            best = None
            n = len(mids)
            # every arrangement is tried for a small block; a large block (over 12 modules, R20's seal cards) is split in
            # reading order only — the first k modules left, the rest right — since 2^n arrangements would never finish
            masks = range(1, 2 ** n - 1) if n <= 12 else [((1 << n) - 1) ^ ((1 << k) - 1) for k in range(1, n)]
            for mask in masks:
                c1 = [j for j in range(n) if not mask >> j & 1]; c2 = [j for j in range(n) if mask >> j & 1]
                if not c1 or not c2 or 0 not in c1: continue   # the first module keeps the top of the first column
                h1, h2 = sum(hs[j] for j in c1), sum(hs[j] for j in c2)
                order = c1 + c2
                disorder = sum(1 for a in range(n) for b in range(a + 1, n) if order[a] > order[b])
                key = (max(h1, h2) > avail - 2 * MM, disorder if max(h1, h2) <= avail - 2 * MM else 0, max(h1, h2))
                if best is None or key < best[0]: best = (key, c1, c2)
            h1_ = sum(hs[j] for j in best[1]) if best else 0; h2_ = sum(hs[j] for j in best[2]) if best else 0
            if best and not best[0][0] and min(h1_, h2_) < .6 * max(h1_, h2_) and max(h1_, h2_) - min(h1_, h2_) > 30 * MM:
                unpack.add(eid)   # (owner, 26 Nov 2026: p. 62) side-by-side modules of very unequal height: set one after another
            elif best and not best[0][0]:
                packs[eid] = ([mids[j] for j in best[1]], [mids[j] for j in best[2]])
            elif best and best[0][2] <= 1.07 * (avail - 2 * MM):   # nearly fits: tighten the lines to make it fit
                packs[eid] = ([mids[j] for j in best[1]], [mids[j] for j in best[2]])
                squeeze_css.append(f'#{eid}{{line-height:1.27}}#{eid} .mod{{margin-bottom:2mm}}')
            elif len(pages) > 1:   # (owner, 26 Nov 2026: p. 144) no arrangement fits: the block is cut at the page break next pass
                nofit.add(eid); packs[eid] = ([mids[j] for j in best[1]], [mids[j] for j in best[2]]) if best else packs.get(eid)
                if packs[eid] is None: del packs[eid]
    return onecol, packs
packed, squeezed, squeeze_css, hardpush, unpack, unpacked = set(), set(), [], set(), set(), set()
modsplit = {}
sheetpush = set()
nofit = set()
def apply_modsplit(doc):
    from bs4 import BeautifulSoup as BS
    sp = BS(doc, 'lxml'); n = 0
    for eid, rest in list(modsplit.items()):
        box = sp.find(id=eid)
        if box is None: continue
        new = sp.new_tag('div', attrs={'class': 'cols mods', 'id': f'cl{next(CLC)}'})
        for m in rest:
            mod = box.find(id=m, recursive=False)
            if mod is None: continue
            mod['class'] = [c for c in mod.get('class', []) if c != 'colbrk']
            new.append(mod.extract())
        for mod in box.find_all(class_='mod', recursive=False):
            mod['class'] = [c for c in mod.get('class', []) if c != 'colbrk']
        box.insert_after(new); packed.discard(eid); n += 1
        # (owner, 26 Nov 2026: pp. 144, 148, 151, 186) a block left with one module is not a column of its own: it opens up
        if len(new.find_all(class_='mod', recursive=False)) == 1: unpack.add(new['id'])
        if len(box.find_all(class_='mod', recursive=False)) == 1: unpack.add(eid)
    modsplit.clear()
    return str(sp), n
opened, opencol = set(), set()
def apply_unpack(doc):
    """Side-by-side short modules that cannot start on a page with room left are set one after another:
    each module's heading across the page, its text in its own columns."""
    from bs4 import BeautifulSoup as BS
    sp = BS(doc, 'lxml'); n = 0
    for eid in sorted(unpack - unpacked):
        box = sp.find(id=eid)
        if box is None: unpacked.add(eid); continue
        new = []
        for mod in box.find_all(class_='mod', recursive=False):
            kids = [k for k in mod.children if getattr(k, 'name', None)]
            if not kids: continue
            h = sp.new_tag('div', attrs={'class': 'mhead', 'id': f'mh{next(CLC)}'})
            if kids[0].name in ('h3', 'h4'):
                kids[0]['data-m'] = '1'; h.append(kids[0].extract()); kids = kids[1:]
            new.append(h)
            if kids and 2 <= len(kids) <= 3 and all(k.name == 'div' and k.get('class') == ['aside'] for k in kids):
                body = sp.new_tag('div', attrs={'class': f'cards c{len(kids)}'})   # side boxes alone: a row of cards (as in flow())
                for k in kids: k['class'] = ['cardc']
                for k in kids: body.append(k.extract())
                new.append(body); kids = []
            if kids:
                body = sp.new_tag('div', attrs={'class': 'cols', 'id': f'cl{next(CLC)}'} if len(kids) > 1 else {'class': 'one'})
                for k in kids: body.append(k.extract())
                new.append(body)
        for x in reversed(new): box.insert_after(x)
        box.decompose(); unpacked.add(eid); n += 1
    return str(sp), n
def apply_packs(doc, packs):
    from bs4 import BeautifulSoup as BS
    sp = BS(doc, 'lxml')
    for eid, (c1, c2) in packs.items():
        box = sp.find(id=eid)
        if box is None: continue   # opened up in this pass
        mods = {k.get('id'): k.extract() for k in list(box.find_all(class_='mod', recursive=False))}
        for k in mods.values():
            k['class'] = [c for c in k.get('class', []) if c != 'colbrk']
        for m in c1: box.append(mods[m])
        for j, m in enumerate(c2):
            if j == 0: mods[m]['class'] = mods[m].get('class', []) + ['colbrk']
            box.append(mods[m])
        packed.add(eid)
    return str(sp)
def split_cols(doc, split):
    from bs4 import BeautifulSoup as BS
    sp = BS(doc, 'lxml')
    for cid, k in split.items():
        c = sp.find(id=cid); kids = [x for x in c.children if getattr(x, 'name', None)]
        tail = kids[k:]
        box = sp.new_tag('div', attrs={'class': 'one' if len(tail) == 1 else 'cols'})
        for x in tail: box.append(x.extract())
        c.insert_after(box)
    return str(sp)
def build(doc):
    return HTML(string=doc, base_url=repo).render()
pushed, levelled, nopush, onecols, retried = set(), set(), set(), set(), set()
def css_fix():
    return (''.join(squeeze_css) + ''.join(f'#{h}{{columns:auto}}' for h in sorted(onecols | opencol)) +''.join(f'#{h}{{break-before:page}}' for h in sorted(pushed - nopush))
            + ''.join(f'#{h}{{margin-top:0}}' for h in sorted(levelled)))
def walk_content(page):
    """The page's own content, without its margin boxes (edge tab, page number, running head)."""
    for c in page.children:
        if type(c).__name__ == 'MarginBox': continue
        yield from walk(c)
def page_free(document):
    """Empty space at the foot of each page, in px."""
    free = []
    for pg in document.pages:
        page = pg._page_box; bottom = page.content_box_y() + page.height; low = page.content_box_y()
        for b, _ in walk_content(page):
            if type(b).__name__ in ('LineBox', 'TableRowBox') or (not getattr(b, 'children', None) and getattr(b, 'height', 0)):
                if getattr(b, 'element_tag', '') in ('@page',) : continue
                y = b.position_y + (b.margin_height() if hasattr(b, 'margin_height') else b.height)
                if y <= bottom + 1: low = max(low, y)
        free.append(bottom - low)
    return free
undone = {}
def fits_back(document, at, free):
    """(owner, 25 Nov 2026: pp. 84, 86) a heading moved to a new page goes back when the page before has room for
    the heading and the start of its content: measured, not guessed from a fixed threshold."""
    box = {}
    for i, pg in enumerate(document.pages):
        for b, _ in walk(pg._page_box):
            el = getattr(b, 'element', None)
            if el is None or id(el) in box or not hasattr(b, 'margin_height'): continue
            box[id(el)] = (i, b.position_y, b.position_y + b.margin_height(), el)
    byid = {v[3].get('id'): v for v in box.values() if v[3].get('id')}
    out_ = set()
    if os.environ.get('DBG'): print('AT', at, len(byid))
    for h, i in at.items():
        if i == 0 or undone.get(h, 0) >= 2 or h not in byid or not h.startswith('hd'): continue
        _, top, bot, el = byid[h]
        unit = el if el.tag == 'h2' else (PARENT.get(id(el)) if (PARENT.get(id(el)) is not None and PARENT[id(el)].get('class') == 'mhead') else el)
        par = PARENT.get(id(unit))
        if par is None: continue
        kids = list(par); k = next((j for j, x in enumerate(kids) if x is unit), None)
        if k is None: continue
        ut = box[id(unit)][1] if id(unit) in box else top
        need = None
        for x in kids[k + 1:]:
            if id(x) not in box or box[id(x)][0] != i: break
            xc = x.get('class') or ''
            if (x.tag == 'p' and ('lead' in xc or 'h2sub' in xc)) or xc == 'mhead': continue
            xb = box[id(x)]
            if xc == 'cols' and x.get('id') and x.get('id') not in opened and free[i - 1] > 55 * MM:
                opened.add(x.get('id')); opencol.add(x.get('id'))   # open it, so it can start on the page before
            split_ok = xc == 'cols' and (x.get('id') in onecols or x.get('id') in opencol) or x.tag in ('p', 'ol', 'ul')
            need = (min(xb[2], xb[1] + 30 * MM) if split_ok else xb[2]) - ut
            break
        if need is not None and free[i - 1] > need + 2 * MM: out_.add(h)
        if os.environ.get('DBG'): print('FB', h, i, need and need/MM, free[i-1]/MM, undone.get(h))
    return out_
def where(document, ids):
    at = {}
    for i, pg in enumerate(document.pages):
        for b, _ in walk(pg._page_box):
            el = getattr(b, 'element', None)
            if el is not None and el.get('id') in ids and el.get('id') not in at: at[el.get('id')] = i
    return at
for it in range(int(os.environ.get('BOOK_PASSES', 10))):
    fix_css = css_fix()
    document = build(doc.replace('</style>', fix_css + '</style>', 1))
    parent_of = {}
    for pg in document.pages:
        for b, _ in walk(pg._page_box):
            for c in getattr(b, 'children', []) or []: parent_of[id(c)] = b
    index_parents(document)
    # a heading moved to a new page in an earlier pass may no longer need it: the page before now has room
    free = page_free(document); at = where(document, pushed - nopush)
    stale = fits_back(document, at, free)
    push, flush_top, split = layout_pass(document)
    push -= stale
    if unpack - unpacked:
        doc, nu = apply_unpack(doc); report.append(f'{nu} module blocks opened up under their heading')
    oc, packs = column_rules(document, doc)
    if packs: doc = apply_packs(doc, packs)
    push |= sheetpush
    nsplit = 0
    if modsplit: doc, nsplit = apply_modsplit(doc)
    nsq = len(squeeze_css)
    add = (push - (pushed - nopush)) | (opencol - getattr(css_fix, 'oc', set())) | (flush_top - levelled) | (oc - onecols) | set(packs) | (unpacked - getattr(css_fix, 'up', set())) | ({'sq'} if nsq != getattr(css_fix, 'nsq', 0) else set()) | ({'ms'} if nsplit else set()) | (unpack - unpacked)
    css_fix.nsq = nsq; css_fix.up = set(unpacked); css_fix.oc = set(opencol)
    onecols |= oc
    if not add and not stale: break
    nopush -= push; nopush |= stale; pushed |= push; levelled |= flush_top
    for h in stale: undone[h] = undone.get(h, 0) + 1
    print(f'pass {it + 1}: +{len(add)} -{len(stale)}', flush=True)
    report.append(f'layout pass {it + 1}: {len(push - nopush)} headings to next page, {len(flush_top)} column-top headings levelled, {len(stale)} earlier moves undone')
fix_css = css_fix()   # the PDF is always rendered from exactly the HTML that is saved beside it
document = build(doc.replace('</style>', fix_css + '</style>', 1))
document.write_pdf(os.path.join(out, 'LC76_Field_Handbook.pdf'))
doc = doc.replace('</style>', fix_css + '</style>', 1)
open(os.path.join(out, 'book.html'), 'w', encoding='utf-8').write(doc)
open(os.path.join(out, 'conversion_report.txt'), 'w').write(f'commit {commit}\n' + '\n'.join(sorted(set(report))) + '\n')
open(os.path.join(out, 'unplaced.txt'), 'w').write('\n'.join(unplaced) + '\n')
open(os.path.join(out, 'brackets.txt'), 'w').write('\n'.join(sorted(set(removed))) + '\n')
open(os.path.join(out, 'notices.txt'), 'w').write('\n'.join(notices_log) + '\n')
print('ok', commit[:7], len(report), 'report lines', len(unplaced), 'unplaced', len(notices_log), 'notices')
