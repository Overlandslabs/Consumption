"""Find section headings (h2, and module heads) left at a page foot apart from their content; optionally
force them to the next page. Usage: orphans.py book.html [out.pdf]"""
import sys, re, os
from weasyprint import HTML
src = open(sys.argv[1], encoding='utf-8').read()
def walk(b):
    yield b
    for c in getattr(b, 'children', []) or []: yield from walk(c)
def find(doc_html):
    d = HTML(string=doc_html, base_url=os.environ.get('BOOK_REPO', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))).render()
    first = {}
    for i, pg in enumerate(d.pages):
        for b in walk(pg._page_box):
            el = getattr(b, 'element', None)
            if el is not None and id(el) not in first: first[id(el)] = (i, el)
    P = {}
    for _, e in first.values():
        for c in e: P[id(c)] = e
    orph = []
    for i, el in list(first.values()):
        hid = el.get('id') or ''
        unit = None
        if el.tag == 'h2' and hid.startswith('hd'): unit = el
        elif el.tag == 'div' and el.get('class') == 'mhead': unit = el
        if unit is None: continue
        par = P.get(id(unit))
        if par is None: continue
        kids = list(par); k = next(j for j, x in enumerate(kids) if x is unit)
        nxt = iter(kids[k + 1:]); sib = next(nxt, None)
        while sib is not None and ((sib.tag == 'p' and any(c in (sib.get('class') or '') for c in ('h2sub', 'lead'))) or sib.get('class') == 'mhead'):
            sib = next(nxt, None)
        if sib is None or id(sib) not in first: continue
        if first[id(sib)][0] > i:
            h = unit if unit.tag == 'h2' else next((c for c in unit if (c.get('id') or '').startswith('hd')), None)
            if h is not None: orph.append((i + 1, h.get('id'), ''.join(h.itertext())[:50]))
    return d, orph
d, orph = find(src)
print('orphan headings:', len(orph)); [print(' p.', p, i, t) for p, i, t in orph]
if len(sys.argv) > 2 and orph:
    css = ''.join(f'#{i}{{break-before:page}}' for _, i, _ in orph)
    src2 = src.replace('</style>', css + '</style>', 1)
    d2, orph2 = find(src2)
    print('after fix:', len(orph2)); [print(' p.', p, i, t) for p, i, t in orph2]
    d2.write_pdf(sys.argv[2]); open(sys.argv[1].replace('.html', '_fixed.html'), 'w', encoding='utf-8').write(src2)
    print('pages', len(d2.pages))
