#!/usr/bin/env python3
"""LC76 BASIS SCAN — the standing check for the Project Instructions §5 rule
'Negative claims and decision facts carry their basis' (adopted 14 Oct 2026).

WHAT IT DOES. Reads every library page and lists each NEGATIVE CLAIM — "not
available", "not sold", "no record", "does not exist", "none found", "cannot be
sourced" and their kin — then compares the list with lc76_basis_baseline.txt,
where every claim already reviewed carries one class:
    BASED   the claim states its search or source and date
    LEDGER  a "no record" about the vehicle's own history; the basis is the
            service ledger
    OUT     not an absence claim about the world (doctrine, "if unavailable…",
            an owner ruling on kit not carried, a "plan as if" stance)
    OPEN    a real absence claim still without a basis — fix when the page is
            next edited
Anything not in the baseline is reported as NEW and must be reviewed at
session close: give it a basis, or accept it into the baseline with a class.

IT DOES NOT BLOCK. Like the currency gate's warn tier it surfaces claims for a
person to judge; a sentence can carry a date and still state no search.

HONEST LIMIT. It finds the listed wordings only. "Hard to find", "rare", "only
in Johannesburg" and other phrasings slip past. Rules (b) and (c) of the PI
rule (decision facts carry their basis; a recommendation names what would
change it) need judgement and are not scanned.

USAGE
  python3 lc76_basis_scan.py                 report NEW claims and class counts
  python3 lc76_basis_scan.py --accept CLASS  add every NEW claim to the
                                             baseline with CLASS (after review)
  python3 lc76_basis_scan.py --tsv out.tsv   also write every hit to a file
Exit code is always 0. Governance tool — NOT precached, no CACHE bump.
"""
import glob, hashlib, html, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, 'lc76_basis_baseline.txt')
CLASSES = ('BASED', 'LEDGER', 'OUT', 'OPEN')
SKIP = re.compile(r'Audit_20|Design_Guidelines|Profile_TEMPLATE|Profile_Template|'
                  r'Open_Items_Dashboard|PI_SessionB_Diff', re.I)
NEG = re.compile(
    r"\b(not (?:currently )?(?:available|sold|stocked|obtainable|carried|offered|listed|found|"
    r"imported|distributed|supplied)"
    r"|unavailable|unobtainable|no longer (?:available|sold|made|produced|stocked|supplied)|discontinued"
    r"|no (?:known |local |official )?(?:record|records|stockists?|dealers?|suppliers?|distributors?|"
    r"agents?|evidence|data|outlets?)\b"
    r"|(?:does|do) not exist|doesn['’]t exist|none (?:found|known|listed|stocked|available|exists?)"
    r"|cannot be (?:bought|obtained|sourced|found|purchased)|can['’]t be (?:bought|obtained|sourced|found)"
    r"|nowhere (?:in|on|along))", re.I)


def page_text(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    s = re.sub(r'(?is)<(script|style|svg)\b.*?</\1>', ' ', s)
    s = re.sub(r'(?s)<!--.*?-->', ' ', s)
    s = re.sub(r'(?i)<(br|/p|/li|/td|/th|/tr|/h\d|/div)\b[^>]*>', '\n', s)
    s = re.sub(r'<[^>]+>', ' ', s)
    return html.unescape(s)


def hits(repo):
    out = []
    for p in sorted(glob.glob(os.path.join(repo, '*.html'))):
        f = os.path.basename(p)
        if SKIP.search(f):
            continue
        for block in page_text(p).split('\n'):
            block = re.sub(r'\s+', ' ', block).strip()
            if not block:
                continue
            for sent in re.split(r'(?<=[.!?;])\s+(?=[A-Z(])', block):
                m = NEG.search(sent)
                if m:
                    key = hashlib.sha1((f + '|' + sent[:400]).encode('utf-8')).hexdigest()[:16]
                    out.append((key, f, m.group(0).lower(), sent[:400]))
    return out


def load_baseline():
    base = {}
    if os.path.exists(BASELINE):
        for line in open(BASELINE, encoding='utf-8'):
            if line.startswith('#') or not line.strip():
                continue
            k, cls = line.split('\t')[:2]
            base[k] = cls
    return base


def main(argv):
    accept = argv[argv.index('--accept') + 1] if '--accept' in argv else None
    tsv = argv[argv.index('--tsv') + 1] if '--tsv' in argv else None
    if accept and accept not in CLASSES:
        sys.exit('class must be one of ' + ', '.join(CLASSES))
    found = hits(HERE)
    base = load_baseline()
    new = [h for h in found if h[0] not in base]
    counts = {}
    for h in found:
        c = base.get(h[0], 'NEW')
        counts[c] = counts.get(c, 0) + 1
    print('=' * 66)
    print('LC76 BASIS SCAN — negative claims and their basis (PI §5)')
    print('=' * 66)
    print('claims found: %d   ' % len(found) + '   '.join('%s %d' % (c, counts.get(c, 0)) for c in CLASSES + ('NEW',)))
    gone = len([k for k in base if k not in {h[0] for h in found}])
    if gone:
        print('baseline entries no longer found (fixed or reworded): %d' % gone)
    if new:
        print('\nNEW — review each: give it a basis, or accept it with a class\n')
        for k, f, phrase, sent in new:
            print('  %s  %s  [%s]\n      %s' % (k, f, phrase, sent[:300]))
    else:
        print('\nNo new negative claims since the baseline.')
    if accept and new:
        with open(BASELINE, 'a', encoding='utf-8') as o:
            for k, f, phrase, sent in new:
                o.write('%s\t%s\t%s\t%s\n' % (k, accept, f, sent[:160].replace('\t', ' ')))
        print('\n%d claim(s) added to the baseline as %s.' % (len(new), accept))
    if tsv:
        with open(tsv, 'w', encoding='utf-8') as o:
            o.write('key\tclass\tfile\tphrase\tsentence\n')
            for k, f, phrase, sent in found:
                o.write('\t'.join((k, base.get(k, 'NEW'), f, phrase, sent.replace('\t', ' '))) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
