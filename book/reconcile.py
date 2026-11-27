#!/usr/bin/env python3
"""Reconcile every number in the built book against the library page it came from.
Usage: reconcile.py <repo> <book_map> <out_dir>   (run after build_book.py)
For each chapter: every number in the PDF must appear in the library source (kept sections) at least as
often. Any number in the book that the source does not hold is a STOP. Numbers in the kept source that are
missing from the book are listed with the reason (library codes such as OI-116 are removed by design)."""
import sys, re, os
from collections import Counter
from bs4 import BeautifulSoup, Comment
import pypdfium2 as pdfium
repo, bookmap, out = sys.argv[1:4]
reg = open(os.path.join(repo, 'LC76_Library_Register.txt'), encoding='utf-8').read()
RFILE = {m.group(1): m.group(2) for m in re.finditer(r'^\s+(R\d+)\s+(\S+\.html)', reg, re.M)}
NUM = re.compile(r'\d+(?:[.,]\d+)*')
CODE = re.compile(r'\b(?:(?:OI|RA|EX)-\d+|(?<!Rimula )R\d{1,2})\b(?![,.]\d)|§\s*\d+(?:\.\d+)*|\bS\d+[a-z]?\b|\bE[1-5]\b')
_T = {}
def page_title(f):
    if f not in _T:
        s = BeautifulSoup(open(os.path.join(repo, f), encoding='utf-8'), 'lxml')
        t = s.find(class_=['std-title', 'mh-title'])
        _T[f] = t.get_text(' ', strip=True) if t else (s.title.get_text(strip=True) if s.title else f)
    return _T[f]
def toks(t):
    out = []
    for n in NUM.findall(t):
        parts = n.split(',')
        # '47,64' is two footnote marks, '1,500' is one number: a thousands group has exactly three digits
        if len(parts) > 1 and not all(len(x) == 3 and x.isdigit() for x in parts[1:]): out += [x for x in parts if x]
        else: out.append(n)
    return out
def nums(t): return Counter(toks(t))
chs = []
for line in open(bookmap, encoding='utf-8'):
    line = line.strip()
    if not line or line.startswith('#'): continue
    c = [x.strip() for x in line.split('|')]
    if c[0] == 'PART': continue
    fl = c[3:]; get = lambda n: next((f.split(':', 1)[1] for f in fl if f.startswith(n + ':')), '')
    trim = {f[5:].split('=')[0]: int(f[5:].split('=')[1]) for f in fl if f.startswith('trim:')}
    chs.append(dict(r=c[0], title=c[1], keep=[x for x in get('keep').split(',') if x], drop=[x for x in get('drop').split(',') if x], trim=trim, num=get('num')))
# source text, kept sections only (same rules as the build)
HERE = os.path.dirname(os.path.abspath(__file__))
def source(ch):
    r, sec = (ch['r'].split('#', 1) + [None])[:2]
    path = (os.path.join(HERE, 'introduction.html') if r == 'INTRO' else
            os.path.join(repo, RFILE[r] if r in RFILE else r))
    s = BeautifulSoup(open(path, encoding='utf-8'), 'lxml')
    for c in s.find_all(string=lambda x: isinstance(x, Comment)): c.extract()
    for t in s.find_all(['script', 'style', 'nav', 'button', 'noscript']): t.decompose()
    bar = s.find(class_='status-bar'); bartxt = bar.get_text(' ') if bar else ''
    sb = s.find(class_=['std-sub', 'mh-sub']); subtxt = sb.get_text(' ') if sb else ''   # the chapter subtitle prints under the title
    main = s.find('main') or s.find(class_=['content', 'main']) or s.body   # same rule as the build
    if sec:   # one section only
        main = s.find(id=sec); bartxt = ''
        for x in main.find_all(class_='section-head', limit=1): x.decompose()
        for x in main.find_all(class_='section-intro'):
            if 'Controlled Duplication' in x.get_text() or 'owning document' in x.get_text(): x.decompose()
    for d in ch['drop']:
        e = main.find(id=d)
        if e is not None and e.name != 'h2': e.decompose()
    def secn(h):
        n = [h]
        for sib in h.find_next_siblings():
            if sib.name == 'h2': break
            n.append(sib)
        return n
    for h in main.find_all('h2'):
        if h.get('id') in ch['drop'] or (ch['keep'] and h.get('id') not in ch['keep']):
            for x in secn(h): x.decompose()
    for sid, k in ch['trim'].items():
        h = main.find(id=sid); seen = 0
        for x in secn(h)[1:]:
            for card in (x.find_all(class_='card') if 'card' not in (x.get('class') or []) else [x]):
                seen += 1
                if seen > k: card.decompose()
    # step numbers are list markers in the book: left out of the count on both sides
    for st in main.find_all(class_='procedure-step'):
        f = st.find('strong')
        if f and re.fullmatch(r'\s*\d+[.)]\s*', f.get_text()): f.decompose()
    for x in main.find_all(class_=['step-num', 'flow-num', 'proto-num', 'cause-num', 'step-stop', 'fix-num']): x.decompose()
    keys = [[li.get('value') for li in ol.find_all('li', recursive=False)] for ol in main.find_all('ol', class_='rig-key')]
    # a library code is printed as its page title (R43 -> 'IsatPhone 2 Operating Guide'): count the title's numbers
    titles = ' '.join(page_title(RFILE[r]) for r in re.findall(r'(?<!Rimula )\b(R\d{1,2})\b(?![,.]\d)', main.get_text(' ')) if r in RFILE)
    aria = ' '.join(sv.get('aria-label', '') for sv in main.find_all('svg'))   # figure captions come from here
    txt = bartxt + ' ' + subtxt + ' ' + main.get_text(' ') + ' ' + aria + ' ' + titles
    return txt, keys
pdf = pdfium.PdfDocument(os.path.join(out, 'LC76_Field_Handbook.pdf'))
pages = [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
MM = 72 / 25.4
def content_text(i):   # the text block only: running heads and page numbers sit in the margins
    pg = pdf[i]; W, Hh = pg.get_size()
    return pg.get_textpage().get_text_bounded(0, 17.5 * MM, W, Hh - 16.5 * MM)
bookhtml = BeautifulSoup(open(os.path.join(out, 'book.html'), encoding='utf-8'), 'lxml')
starts = []
for ch in chs:
    n = ch['num'] or str(len(starts) + 1)
    lab = re.compile(r'^\s*C\s*H\s*A\s*P\s*T\s*E\s*R\s*' + r'\s*'.join(n) + r'\s*$', re.M)
    starts.append(next(i for i, p in enumerate(pages) if lab.search(p)))
starts.append(len(pages))
lines, stop = [], 0
for k, ch in enumerate(chs):
    sec = bookhtml.find(id=f'ch{k+1}')
    for x in sec.find_all(class_=['ch-num', 'ch-big']): x.decompose()   # chapter number labels are not library numbers
    for x in sec.select('span.mk.lbl'): x.decompose()                  # step labels: left out on both sides, as above
    book = sec.get_text(' ')
    pdftext = '\n'.join(content_text(i) for i in range(starts[k], starts[k + 1]))
    pdftext = re.sub(r'^\s*C\s*H\s*A\s*P\s*T\s*E\s*R[\s\d]*$', '', pdftext, count=1, flags=re.M)
    src, keys = source(ch)
    b = nums(book); s = nums(src); s_nocode = nums(CODE.sub(' ', src)); ex = Counter()
    # figure keys: the numbers must match the drawing, list by list
    lines.append(f'== {ch["r"]} {ch["title"]}  (book pages {starts[k]+1}-{starts[k+1]})')
    bh = BeautifulSoup(open(os.path.join(out, 'book.html'), encoding='utf-8'), 'lxml').find(id=f'ch{k+1}')
    bkeys = [[li.get('value') for li in ol.find_all('li', recursive=False)] for ol in bh.find_all('ol', class_='key')]
    lines.append(f'  figure keys: {len(keys)} lists in the library, {len(bkeys)} in the book, ' + ('identical' if keys == bkeys else 'DIFFERENT — STOP'))
    if keys != bkeys: stop += 1
    for n in sorted(b, key=lambda x: (len(x), x)):
        have = s[n] + ex[n] + (1 if n == (ch['num'] or '') else 0)
        mark = 'ok' if b[n] <= have else 'STOP — not in the library source this often'
        if mark != 'ok':
            # section numbers printed in headings ("1", "10") and list numbers are explained by the source h2 text
            stop += 1
        lines.append(f'  {n:>12}  book {b[n]:>3}  library {s[n]:>3}  {mark}')
    pc = nums(pdftext)
    # a footnote mark printed straight after a number is read out of the PDF as one token ('1954' + '2' -> '19542')
    # a footnote mark printed against a number is read out of the PDF as one token ('1954' + '2' -> '19542');
    # this check is for clipped or lost lines, so a number found inside a longer digit run counts as printed
    lost = [n for n in b if pc[n] < b[n] and len(re.findall(re.escape(n), pdftext)) < b[n]]
    lines.append('  PDF against book text: ' + ('every number printed' if not lost else 'MISSING IN PDF — STOP: ' + ', '.join(lost)))
    stop += len(lost)
    missing = [n for n in s_nocode if s_nocode[n] > b[n]]
    if missing:
        lines.append('  numbers in the library section text but fewer times in the book:')
        for n in sorted(missing, key=lambda x: (len(x), x)):
            lines.append(f'  {n:>12}  library {s_nocode[n]:>3}  book {b[n]:>3}')
open(os.path.join(out, 'numbers.txt'), 'w').write('\n'.join(lines) + f'\n\nSTOPs: {stop}\n')
print('STOPs:', stop)
