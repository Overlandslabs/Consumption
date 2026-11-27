#!/usr/bin/env python3
"""Is the printed Field Handbook behind the library?

The book is a snapshot: build_book.py copies the library pages listed in volume-2.txt
into one PDF. Nothing updates the book when a page changes. This check compares every
source page with the fingerprint recorded in edition.txt when the current edition was
built, and lists the chapters whose page has changed since.

  python3 book/lc76_book_check.py            report (exit 0 always — it never blocks)
  python3 book/lc76_book_check.py --record "Draft 2" <commit> <pages>
                                             write edition.txt after a new edition is built

Run by lc76_run_checks.py as a REPORT line. Standard library only, no git history needed
(the GitHub check runs on a shallow copy). Governance tool, not a library file.
Added 27 Nov 2026 (owner: 'Agree with your proposals')."""
import hashlib, os, re, sys, datetime

BOOK = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BOOK)
EDITION = os.path.join(BOOK, 'edition.txt')


def sources():
    reg = open(os.path.join(REPO, 'LC76_Library_Register.txt'), encoding='utf-8').read()
    rfile = {m.group(1): m.group(2) for m in re.finditer(r'^\s+(R\d+)\s+(\S+\.html)', reg, re.M)}
    out, n = [], 0
    for line in open(os.path.join(BOOK, 'volume-2.txt'), encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'): continue
        c = [x.strip() for x in line.split('|')]
        if c[0] == 'PART': continue
        n += 1
        src = c[0].split('#')[0]
        path = 'book/introduction.html' if src == 'INTRO' else rfile.get(src, src)
        out.append((n, c[1], path))
    return out


def sha(path):
    p = os.path.join(REPO, path)
    if not os.path.exists(p): return 'MISSING'
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def record(label, commit, pages):
    lines = [f'edition: {label}', f'built: {datetime.date.today().isoformat()}',
             f'library commit: {commit}', f'pages: {pages}', '']
    chaps = {}
    for n, title, path in sources():   # a page used by two chapters (R29: chapters 2 and 42) is listed with both
        chaps.setdefault(path, []).append(f'{n} {title}')
    seen = set(chaps)
    for path, cs in chaps.items():
        lines.append(f'{sha(path)}  {path}  | {" · ".join(cs)}')
    open(EDITION, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(f'edition.txt written: {len(seen)} source pages')


def report():
    if not os.path.exists(EDITION):
        print('No edition recorded (book/edition.txt missing): the book has not been built from this library.')
        return
    head, rows = {}, []
    for line in open(EDITION, encoding='utf-8'):
        m = re.match(r'^([a-z ]+): (.*)$', line.strip())
        if m: head[m.group(1)] = m.group(2); continue
        m = re.match(r'^(\S+)  (\S+)  \| (.*)$', line.strip())
        if m: rows.append(m.groups())
    print(f"Printed edition: {head.get('edition', '?')}, built {head.get('built', '?')} "
          f"from library commit {head.get('library commit', '?')[:7]}, {head.get('pages', '?')} pages.")
    recorded = {p for _, p, _ in rows}
    changed = [(chap, p) for h, p, chap in rows if sha(p) != h]
    added = [(f'{n} {t}', p) for n, t, p in sources() if p not in recorded]
    if not changed and not added:
        print('BOOK CURRENT — no source page has changed since this edition was built.')
        return
    print(f'BOOK BEHIND THE LIBRARY — {len(changed) + len(added)} chapter(s) changed since this edition:')
    for chap, p in changed: print(f'  chapter {chap}  ({p})')
    for chap, p in added: print(f'  chapter {chap}  ({p}) — new in the book map, not in this edition')
    print('Rebuild before printing or before a trip (book/README.md).')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--record':
        record(*sys.argv[2:5])
    else:
        report()
    sys.exit(0)
