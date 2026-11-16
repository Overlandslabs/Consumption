#!/usr/bin/env python3
"""lc76_ask.py — find where the library answers a question. READ-ONLY.

  python3 lc76_ask.py wheel nut torque
  python3 lc76_ask.py --max 12 "cholera zambia"

Prints, for each hit: the page, its 'Last updated' date, the section the
text sits under, and the text itself. It searches the library pages, the
fact store (LC76_Facts.txt) and the OPEN part of the Open Items Register.
It edits nothing. It finds words; it does not judge the answer — read the
hit on the page before quoting it. Used by the skill lc76-ask.
"""
import glob, html, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Pages that are records about the library, not the library's guidance.
SKIP = ('LC76_Library_Audit_', 'LC76_PI_SessionB_Diff', 'LC76_Profile_TEMPLATE',
        'LC76_Design_Guidelines', 'LC76_Open_Items_Dashboard')
SITE = 'https://overlandslabs.github.io/Consumption/'
MAIN = 'sec-header|section-head|section-header|sec-head'
HEADS = MAIN + '|subsec-title'

def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()

def page_blocks(path):
    raw = open(path, encoding='utf-8', errors='replace').read()
    title = clean((re.search(r'<title>(.*?)</title>', raw, re.S) or [0, ''])[1])
    date = (re.search(r'Last updated:?\s*(?:</[^>]+>\s*)?(\d{1,2} \w+ \d{4})', raw) or [0, 'no date on page'])[1]
    body = re.sub(r'<!--.*?-->|<script.*?</script>|<style.*?</style>', ' ', raw, flags=re.S)
    section = sub = ''
    # Pages mark sections with classes, not always with h2: cut at those too.
    for part in re.split(r'(?i)(?=<h[1-4][\s>])|(?=<[a-z0-9]+[^>]*class="(?:%s))|</h[1-4]>|</p>|</li>|</tr>|</div>|<br\s*/?>' % HEADS, body):
        if not part:
            continue
        m = re.match(r'(?is)<([a-z0-9]+)([^>]*)>(.*)', part)
        text = clean(part)
        if not text:
            continue
        if m and (re.match(r'h[23]$', m.group(1), re.I) or re.search(r'class="(?:%s)' % MAIN, m.group(2))):
            section, sub = text[:110], ''
            continue
        if m and (m.group(1).lower() == 'h4' or 'subsec-title' in m.group(2)):
            sub = text[:90]
            continue
        yield title, date, (section + (' > ' + sub if sub else '')) or '(top of page)', text

def text_blocks(path, label, stop=None, by_entry=False):
    """Fact store: one block a line. Register: one block an open item."""
    section, buf = '(top)', []
    for line in open(path, encoding='utf-8', errors='replace'):
        if stop and line.startswith(stop):
            break
        t = line.strip()
        if re.match(r'(§\d|▌|OI-\d+ )', t):
            section = t[:110]
        if by_entry:
            if t:
                buf.append(t)
            elif buf:
                yield label, '', buf[0][:110], ' '.join(buf); buf = []
        elif t:
            yield label, '', section, t
    if buf:
        yield label, '', buf[0][:110], ' '.join(buf)

def main(argv):
    n = 8
    if argv[:1] == ['--max']:
        n, argv = int(argv[1]), argv[2:]
    words = [w.lower() for w in ' '.join(argv).split() if len(w) > 1]
    if not words:
        print(__doc__); return 2
    hits = []
    sources = []
    for p in sorted(glob.glob(os.path.join(HERE, '*.html'))):
        f = os.path.basename(p)
        if f.startswith(SKIP):
            continue
        sources.append((f, page_blocks(p)))
    sources.append(('LC76_Facts.txt', text_blocks(os.path.join(HERE, 'LC76_Facts.txt'), 'Fact store')))
    sources.append(('LC76_Open_Items_Register.txt',
                    text_blocks(os.path.join(HERE, 'LC76_Open_Items_Register.txt'), 'Open Items Register (open items)', 'CLOSED LOG', True)))
    for f, blocks in sources:
        for title, date, section, text in blocks:
            t_low, s_low, p_low = text.lower(), section.lower(), title.lower()
            in_text = sum(1 for w in words if w in t_low)
            got = sum(1 for w in words if w in t_low or w in s_low or w in p_low)
            if in_text and len(text) >= 20 and (got == len(words) or (len(words) > 2 and got >= len(words) - 1)):
                score = (0 if 'changelog' in s_low else 5) + 10 * in_text + 3 * sum(1 for w in words if w in p_low) + 2 * sum(1 for w in words if w in s_low)
                hits.append((-(got == len(words)), -score, len(text), f, title, date, section, text))
    hits.sort()
    print('QUESTION WORDS: %s   |   pages searched: %d   |   hits: %d (showing %d)'
          % (' '.join(words), len(sources), len(hits), min(n, len(hits))))
    for full, _, _, f, title, date, section, text in hits[:n]:
        print('\n%s%s' % ('' if full else '[partial match] ', title))
        print('  file: %s   last updated: %s' % (f, date or 'see file header'))
        if f.endswith('.html'):
            print('  link: %s%s' % (SITE, f))
        print('  section: %s' % section)
        print('  text: %s' % (text if len(text) < 700 else text[:700] + ' …'))
    if not hits:
        print('\nNOTHING FOUND for these words. Try other words before saying the library does not cover it.')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
