"""Every word of the library's kept text must appear in the book: lists library words missing from the book, by chapter."""
import sys, re, collections
from bs4 import BeautifulSoup
repo, bookmap, out = sys.argv[1:4]
book = BeautifulSoup(open(out + '/book.html'), 'lxml')
reg = open(repo + '/LC76_Library_Register.txt').read()
RF = {m.group(1): m.group(2) for m in re.finditer(r'^\s+(R\d+)\s+(\S+\.html)', reg, re.M)}
W = lambda t: collections.Counter(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'’-]{3,}", t))
for line in open(bookmap):
    c = [x.strip() for x in line.split('|')]
    if not line.strip() or c[0] in ('PART', 'INTRO') or line.startswith('#'): continue
    r = c[0].split('#')[0]; f = RF.get(r, r)
    s = BeautifulSoup(open(repo + '/' + f), 'lxml')
    for t in s.find_all(['script', 'style', 'nav', 'button', 'noscript']): t.decompose()
    for cl in ['sticky-nav-unit', 'sticky-wrap', 'toc-bar', 'xref-bar', 'lib-home-btn', 'mh-date', 'ref-back']:
        for t in s.find_all(class_=cl): t.decompose()
    for d in s.find_all('div'):   # the 'Cross-Reference' button bar is not printed (same rule as the build)
        kids = [k for k in d.children if getattr(k, 'name', None)]
        if kids and kids[0].name == 'span' and kids[0].get_text(strip=True) == 'Cross-Reference' and all(k.name == 'a' for k in kids[1:]): d.decompose()
    main = s.body.find('main') or s.body.find(class_=['content', 'main']) or s.body
    if '#' in c[0]:
        main = main.find(id=c[0].split('#')[1])
        hd = main.find(class_='section-head')
        if hd: hd.decompose()
    drops = [x.split(':', 1)[1] for x in c[3:] if x.startswith('drop:')]
    for d in (drops[0].split(',') if drops else []):
        e = main.find(id=d)
        if e is not None:
            if e.name == 'h2':
                for sib in list(e.find_next_siblings()):
                    if sib.name == 'h2': break
                    sib.decompose()
            e.decompose()
    lib = W(main.get_text(' '))
    n = next(x for x in c[3:] if x.startswith('num:')).split(':')[1] if any(x.startswith('num:') for x in c[3:]) else None
    sec = [x for x in book.find_all('section', class_='chapter') if x.find('h1') and x.find('h1').get_text().strip() == c[1]]
    bk = W(sec[0].get_text(' ')) if sec else collections.Counter()
    miss = {w: k for w, k in lib.items() if bk[w] < k}
    print(f'{c[1]}: {len(miss)} words short:', ' '.join(f'{w}({lib[w]}/{bk[w]})' for w in sorted(miss))[:1500])
