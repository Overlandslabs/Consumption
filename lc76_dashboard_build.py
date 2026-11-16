#!/usr/bin/env python3
"""LC76 DASHBOARD BUILD — the Open Items Dashboard is built from the register
(added 16 Nov 2026, OI-133).

WHY. LC76_Open_Items_Dashboard.html is a derived view of
LC76_Open_Items_Register.txt, but the script that first built it was never
kept, so cards and counters were patched by hand each session and drifted
from the register (a missed date; card text reworded; annotations left out).
A derived view that is typed is a second, unmaintained home for every status
(PI §4 mastership map; PI §5 G5 — checking must be systemic).

WHAT IT DOES. Register in, dashboard out. It rewrites ONLY the parts of the
page that sit between marker comments (<!-- gen:NAME --> ... <!-- /gen:NAME -->):
  head      the 'Register of <date> · N open items' line in the masthead
  summary   the five counters and the filter chips
  safety    one card per open item in the Safety band
  live      one card per open item in the Live band
  waiting   one card per open item in the Waiting band
  prov      the source lines in 'About This View'
Everything else — styles, layout, script, the About wording — is the page's
own and is edited there. The output is a pure function of the register and
the page: no clock is read, so the same register always gives the same page.

RULES (derived, never typed — if a call looks wrong, fix the register entry):
  open item   every 'OI-n Title' entry in sections A–E above the CLOSED LOG
  heading     the entry's WHAT line; the technical title sits under it
  who/when/source   the OWNER · GATE · SOURCE line, split at ' · '
  confirmed/next    the CONFIRMED ... · NEXT-DUE: ... line
  detail      the whole of the entry's status text, word for word, in the
              register's order; a new paragraph starts at each dated note
  band        Waiting if the status line starts WAITING-DATE or STANDING;
              Safety if the status line's first sentence says '(safety)';
              otherwise Live
  tags        neil      the owner field names NEIL or MARY-ANN
              claude    the owner field names CLAUDE, or the item is in
                        section B (chartered Claude workstreams)
              workshop  the owner field says 'workshop'
              decision  the item is in section D (decisions pending), or its
                        title, WHAT line, owner line or opening status
                        paragraph uses the word 'decision' (later dated
                        notes are not read for this)

USAGE
  python3 lc76_dashboard_build.py           rebuild the dashboard in place
  python3 lc76_dashboard_build.py --check   exit 1 if the dashboard on disk
                                            is not what the register gives
  python3 lc76_dashboard_build.py --list    print id, band and tags per item
Governance tool — NOT precached, no CACHE bump.
"""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER = os.path.join(HERE, 'LC76_Open_Items_Register.txt')
DASHBOARD = os.path.join(HERE, 'LC76_Open_Items_Dashboard.html')

# A dated note starts a new paragraph. Two shapes, both at the start of a line:
#   a date, with or without a short label and a bracket, then a colon —
#     '4 Nov 2026 (S37):', 'PROGRESS, 16 Nov 2026:', 'Owner, 4 Nov 2026 (E4):'
#   a capitals label, a date, then an opening bracket —
#     'ANNOTATED 25 Oct 2026 (ninety-seventh session ...'
# A sentence that merely wraps onto a date ('... adopted / 23 Jul 2026 (R29
# §6, layer 3). If ...') matches neither. A note the rule misses stays joined
# to the paragraph before it: nothing is ever dropped.
_D = r"\d{1,2} [A-Z][a-z]{2} 20\d\d"
NOTE = re.compile(r"^(?:[A-Z][A-Za-z' \-]{0,40},? )?" + _D + r"(?: \([^)]*\))?:"
                  r"|^[A-Z][A-Z' \-]+,? " + _D + r"\s*\(")
STATUS_WORDS = ('OPEN', 'WAITING-DATE', 'STANDING', 'DONE-PENDING-EVIDENCE')


class BuildError(Exception):
    pass


def parse_register(text):
    """Return (register_date, update_label, [item dicts]) for the open items."""
    lines = text.split('\n')
    m = re.search(r'^Last updated: (\d{1,2} \w+ \d{4}) \(([a-z\-]+ update)', text, re.M)
    if not m:
        raise BuildError("register header: no 'Last updated: <date> (<n> update' line")
    reg_date, update = m.group(1), m.group(2)
    try:
        end = next(i for i, l in enumerate(lines) if l.startswith('CLOSED LOG'))
    except StopIteration:
        raise BuildError('register: no CLOSED LOG header')
    raw, sec, cur = [], None, None
    for l in lines[:end]:
        if l.startswith('▌'):
            head = l[1:].strip()
            sec = head[0] if re.match(r'[A-E]\. ', head) else None
            cur = None
            continue
        m = re.match(r'^(OI-\d+)\s+(.+)$', l)
        if m and sec:
            cur = {'id': m.group(1), 'title': m.group(2).strip(), 'sec': sec, 'body': []}
            raw.append(cur)
            continue
        if cur is not None:
            if l.strip() and not l.startswith(' '):
                cur = None            # unindented text: the entry has ended
            else:
                cur['body'].append(l)
    items = [shape(r) for r in raw]
    ids = [i['id'] for i in items]
    if len(set(ids)) != len(ids):
        raise BuildError('register: an open item id appears twice')
    if not items:
        raise BuildError('register: no open items read — a probe that reads nothing has found nothing')
    return reg_date, update, items


def shape(r):
    b = [l.strip() for l in r['body']]
    oid = r['id']
    try:
        wi = next(i for i, l in enumerate(b) if l.startswith('WHAT:'))
        oi = next(i for i in range(wi + 1, len(b)) if ' · ' in b[i])
    except StopIteration:
        raise BuildError(f'{oid}: no WHAT line, or no OWNER · GATE · SOURCE line')
    title = ' '.join([r['title']] + b[:wi])
    what = ' '.join(b[wi:oi])[len('WHAT:'):].strip()
    parts = b[oi].split(' · ')
    if len(parts) < 3:
        raise BuildError(f'{oid}: the OWNER · GATE · SOURCE line has fewer than three parts')
    who, when, source = parts[0], parts[1], ' · '.join(parts[2:])
    rest = b[oi + 1:]
    if not rest or not rest[0].startswith(STATUS_WORDS):
        raise BuildError(f'{oid}: the line after OWNER · GATE · SOURCE is not a status line')
    conf = [i for i, l in enumerate(rest) if l.startswith('CONFIRMED ') and ' · NEXT-DUE: ' in l]
    if len(conf) != 1:
        raise BuildError(f'{oid}: expected one CONFIRMED … · NEXT-DUE line, found {len(conf)}')
    ci = conf[0]
    cj = ci + 1                      # the CONFIRMED line may wrap
    while cj < len(rest) and rest[cj] and not NOTE.match(rest[cj]):
        cj += 1
    confirmed, nxt = ' '.join(rest[ci:cj])[len('CONFIRMED '):].split(' · NEXT-DUE: ', 1)
    paras, cur = [], []
    for l in rest[:ci] + [''] + rest[cj:]:
        if not l or NOTE.match(l):
            if cur:
                paras.append(' '.join(cur))
            cur = [l] if l else []
        else:
            cur.append(l)
    if cur:
        paras.append(' '.join(cur))
    status = rest[0]
    first = re.split(r'(?<=[.;:])\s', status + ' ' + ' '.join(rest[1:3]))[0]
    if status.startswith(('WAITING-DATE', 'STANDING')):
        band = 'waiting'
    elif '(safety)' in first.lower():
        band = 'safety'
    else:
        band = 'live'
    whole = ' '.join([title, what, b[oi]] + paras[:1])   # not the later notes
    tags = set()
    if re.search(r'NEIL|MARY-ANN', who):
        tags.add('neil')
    if 'CLAUDE' in who or r['sec'] == 'B':
        tags.add('claude')
    if 'workshop' in who.lower():
        tags.add('workshop')
    if r['sec'] == 'D' or re.search(r'\bdecision\b', whole, re.I):
        tags.add('decision')
    return {'id': oid, 'title': title, 'what': what, 'who': who, 'when': when,
            'source': source, 'confirmed': confirmed, 'next': nxt, 'paras': paras,
            'band': band, 'tags': sorted(tags), 'owner_line': b[oi]}


def esc(s):
    return html.escape(s, quote=True)


def card(it):
    text = ' '.join([it['what'], it['title'], it['owner_line']] + it['paras']).lower()
    detail = ''.join(f'<p>{esc(p)}</p>' for p in it['paras'])
    return f'''      <article class="oi oi-{it['band']}" data-tags="{' '.join(it['tags'])}" data-band="{it['band']}" data-text="{esc(text)}">
        <button class="oi-head" onclick="tog(this)" aria-expanded="false">
          <span class="oi-id">{it['id']}</span>
          <span class="oi-title">{esc(it['what'])}</span>
          <span class="oi-chev">+</span>
        </button>
        <div class="oi-ref">Register entry: {esc(it['title'])}</div>
        <div class="oi-meta">
          <span class="m-k">Who</span><span class="m-v">{esc(it['who'])}</span>
          <span class="m-k">When</span><span class="m-v">{esc(it['when'])}</span>
          <span class="m-k">Source</span><span class="m-v">{esc(it['source'])}</span>
          <span class="m-k">Confirmed</span><span class="m-v">{esc(it['confirmed'])}</span>
          <span class="m-k">Next</span><span class="m-v">{esc(it['next'])}</span>
        </div>
        <div class="oi-detail">{detail}</div>
      </article>'''


def regions(reg_date, update, items):
    n = len(items)
    band = lambda b: [i for i in items if i['band'] == b]
    tag = lambda t: sum(1 for i in items if t in i['tags'])
    summary = f'''  <div class="kpi">
    <div class="k-safety"><div class="n">{len(band('safety'))}</div><div class="l">Safety</div></div>
    <div class="k-live"><div class="n">{len(band('live'))}</div><div class="l">Live now</div></div>
    <div><div class="n">{len(band('waiting'))}</div><div class="l">Date-locked</div></div>
    <div><div class="n">{tag('workshop')}</div><div class="l">Workshop</div></div>
    <div><div class="n">{tag('decision')}</div><div class="l">Your call</div></div>
  </div>

  <div class="filters">
    <span class="chip on" data-f="all" onclick="filt(this)">All {n}</span>
    <span class="chip" data-f="workshop" onclick="filt(this)">Next workshop visit ({tag('workshop')})</span>
    <span class="chip" data-f="neil" onclick="filt(this)">Neil or Mary-Ann ({tag('neil')})</span>
    <span class="chip" data-f="claude" onclick="filt(this)">Library &amp; document work ({tag('claude')})</span>
    <span class="chip" data-f="decision" onclick="filt(this)">Waiting on your decision ({tag('decision')})</span>
  </div>'''
    cards = lambda b: '\n\n'.join(card(i) for i in band(b))
    return {
        'head': f'    <div class="std-vehicle">Register of {reg_date} &middot; {n} open items</div>',
        'summary': summary,
        'safety': cards('safety'),
        'live': cards('live'),
        'waiting': cards('waiting'),
        'prov': (f'    Source: LC76_Open_Items_Register.txt ({update}, {reg_date})<br>\n'
                 f'    Built by: lc76_dashboard_build.py &mdash; never edited by hand<br><br>'),
    }


def build(register_text, page):
    reg_date, update, items = parse_register(register_text)
    for name, body in regions(reg_date, update, items).items():
        pat = re.compile(r'(<!-- gen:%s -->\n).*?(\n[ \t]*<!-- /gen:%s -->)' % (name, name), re.S)
        if len(pat.findall(page)) != 1:
            raise BuildError(f"dashboard page: marker pair 'gen:{name}' not found exactly once")
        page = pat.sub(lambda m: m.group(1) + body + m.group(2), page)
    if page.count('class="oi oi-') != len(items):
        raise BuildError('dashboard page: card count does not equal the open-item count')
    return page, items


def main(argv):
    try:
        reg = open(REGISTER, encoding='utf-8').read()
        old = open(DASHBOARD, encoding='utf-8').read()
        new, items = build(reg, old)
    except (BuildError, OSError) as e:
        print('DASHBOARD BUILD: FAIL —', e)
        return 1
    if '--list' in argv:
        for i in items:
            print(f"{i['id']:<7} {i['band']:<8} {' '.join(i['tags'])}")
        return 0
    counts = ', '.join(f"{sum(1 for i in items if i['band'] == b)} {b}" for b in ('safety', 'live', 'waiting'))
    if '--check' in argv:
        if new != old:
            print('DASHBOARD CHECK: FAIL — the dashboard on disk is not what the register gives.')
            print('Run: python3 lc76_dashboard_build.py   (never edit the cards by hand)')
            return 1
        print(f'DASHBOARD CHECK: PASS — {len(items)} open items, one card each ({counts}).')
        return 0
    data = new.encode('utf-8')
    with open(DASHBOARD, 'wb') as f:
        f.write(data)
    print(f'DASHBOARD BUILD: {len(items)} cards written ({counts}).'
          + ('' if new != old else ' No change.'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
