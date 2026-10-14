#!/usr/bin/env python3
"""LC76 MARGIN CHECK — content that runs to the screen edge (PI §8, adopted
14 Oct 2026, eighty-second session, owner ruling).

WHY. A page's sections must sit inside its content wrapper, which gives the
side margin. In R18 a lost opening tag closed the wrapper early, so every
section after the Quick Reference ran to the screen edge; a later "repair"
deleted the wrapper's own closing tag, the tag count balanced, and the depth
walk passed 0/0 for six months. A depth walk cannot see two errors that
cancel. This check looks at the RESULT instead of the tags.

WHAT IT DOES. Opens every library page in a headless browser at 390 px (phone)
and 1280 px (desktop) and counts the visible text blocks — headings,
paragraphs, tables, cards — whose text starts within 6 px of the left screen
edge (outside the sticky header, the TOC and footers). Each page/width count
is compared with lc76_margin_baseline.txt:
    PASS   no page is flush beyond its baseline count
    FAIL   a page/width not in the baseline has flush blocks, or a baselined
           one has more than its recorded count
Exit code 1 on FAIL, 0 on PASS. Runs at session close beside the currency,
fact and basis gates.

HONEST LIMIT. It measures the LEFT edge only, at two widths, with the page
opened from file (web fonts may not load, which moves text a little but not
its left edge; web requests are refused, so it never waits on a
network). A block deliberately designed to run edge to edge is accepted
into the baseline with a note; a block that is flush on the right only, or
cramped but not flush, is not caught.

USAGE
  python3 lc76_margin_check.py            check every *.html in this folder
  python3 lc76_margin_check.py --list     also print the first flush blocks
                                          on every page that has any
  python3 lc76_margin_check.py F.html ... check the named pages only
Needs: python playwright with chromium. Governance tool — NOT precached, no
CACHE bump.
"""
import asyncio, glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, 'lc76_margin_baseline.txt')
WIDTHS = (390, 1280)
EDGE = 6  # px

JS = """(edge) => {
  const sel = 'body h1, body h2, body h3, body p, body li, body table, ' +
              'body .section-header, body .sec-header, body .zone-header, ' +
              'body .section-head, body [class*=card]';
  const skip = '.sticky-wrap, .sticky-nav-unit, #sticky-nav, header, footer, .toc-bar, nav';
  let n = 0; const ex = [];
  for (const e of document.querySelectorAll(sel)) {
    const r = e.getBoundingClientRect();
    if (r.width < 40 || r.height < 4) continue;
    const cs = getComputedStyle(e);
    if (cs.visibility === 'hidden' || cs.position === 'fixed' || e.closest(skip)) continue;
    const x = r.left + parseFloat(cs.paddingLeft) + parseFloat(cs.borderLeftWidth);
    if (x < edge) {
      n++;
      if (ex.length < 3) ex.push(e.tagName + ' "' + (e.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 40) + '"');
    }
  }
  return {n, ex};
}"""


def load_baseline():
    base = {}
    if os.path.exists(BASELINE):
        for line in open(BASELINE, encoding='utf-8'):
            if not line.strip() or line.startswith('#'):
                continue
            f, w, n = line.rstrip('\n').split('\t')[:3]
            base[(f, int(w))] = int(n)
    return base


async def measure(files):
    from playwright.async_api import async_playwright
    out = {}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context()
        # file pages only: refuse web requests (fonts, CDNs) so a run is fast
        # and the same with or without a network
        await ctx.route(re.compile(r'^https?://'), lambda route: route.abort())
        for w in WIDTHS:
            for f in files:
                pg = await ctx.new_page()
                await pg.set_viewport_size({'width': w, 'height': 900})
                await pg.goto('file://' + os.path.abspath(f))
                await pg.wait_for_timeout(300)
                out[(os.path.basename(f), w)] = await pg.evaluate(JS, EDGE)
                await pg.close()
        await b.close()
    return out


def main(argv):
    show = '--list' in argv
    names = [a for a in argv if not a.startswith('--')]
    files = names or sorted(glob.glob(os.path.join(HERE, '*.html')))
    res = asyncio.run(measure(files))
    base = load_baseline()
    fails, known = [], []
    for (f, w), r in sorted(res.items()):
        allowed = base.get((f, w), 0)
        if r['n'] > allowed:
            fails.append((f, w, r, allowed))
        elif r['n']:
            known.append((f, w, r, allowed))
    print('=' * 66)
    print('LC76 MARGIN CHECK — content at the screen edge (PI §8)')
    print('=' * 66)
    print(f'pages: {len(files)}  widths: {WIDTHS}  baseline entries: {len(base)}')
    for f, w, r, a in known:
        print(f'  baseline  {f} @{w}px: {r["n"]} flush (allowed {a})' + ('  ' + '; '.join(r['ex']) if show else ''))
    for f, w, r, a in fails:
        print(f'  FAIL      {f} @{w}px: {r["n"]} flush (allowed {a})  ' + '; '.join(r['ex']))
    print('RESULT:', 'FAIL' if fails else 'PASS')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
