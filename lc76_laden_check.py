#!/usr/bin/env python3
"""LC76 LADEN-PRESSURE CHECK — the calculator's copy of R14's laden pressures
(PI §8, adopted 22 Oct 2026, ninety-third session, owner ruling).

WHY. The full-expedition-load tyre pressures live in TWO places: R14 §3
(LC76_Tyre_Management_Guide.html, the master — the laden rows of its pressure
table) and the Tyre Pressure Calculator (LC76_Tyre_Pressure_Calculator.html,
the LADEN_R14 table in its script and the default text of its 'Full expedition
load' box). Each names the other, but a note is not a control: a change to
R14 that misses the calculator would leave the calculator showing a pressure
R14 no longer supports. This check compares the two.

WHAT IT DOES. Reads the six laden rows of R14 §3 (tar loaded, gravel laden,
corrugated laden, rock, mud, sand soft) — front psi, front bar, rear psi,
rear bar — and the calculator's LADEN_R14 entries for the same six terrains,
plus the box's default (tar) text. Prints each pair.
    PASS   every value matches
    FAIL   any value differs, or any row / entry cannot be found (a probe
           that reads nothing has found nothing — that is never a pass)
Exit code 1 on FAIL, 0 on PASS. Runs at session close beside the currency,
fact, basis and margin checks.

HONEST LIMIT. It checks the twelve laden pairs only — not the calculator's own
light-load figures, not R14's unladen or extreme-sand rows, and not prose
elsewhere that quotes a laden figure (the currency gate and the corpus grep
cover those).

Usage: python3 lc76_laden_check.py [R14.html] [calculator.html]
"""
import re
import sys

R14 = sys.argv[1] if len(sys.argv) > 1 else 'LC76_Tyre_Management_Guide.html'
CALC = sys.argv[2] if len(sys.argv) > 2 else 'LC76_Tyre_Pressure_Calculator.html'

# R14 row label (first cell, tags stripped)  ->  calculator terrain key
ROWS = [
    ('Tar highway (loaded)',  'highway'),
    ('Gravel (firm), laden',  'gravel'),
    ('Corrugated dirt, laden', 'corrugated'),
    ('Rocky terrain (crawl)', 'rock'),
    ('Mud',                   'mud'),
    ('Sand (soft, deep)',     'sand'),
]


def cells(row_html):
    return [re.sub(r'<[^>]+>', '', c).strip()
            for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row_html, re.S)]


def r14_values(path):
    t = open(path, encoding='utf-8').read()
    found = {}
    for row in re.findall(r'<tr\b.*?</tr>', t, re.S):
        c = cells(row)
        if len(c) < 5:
            continue
        for label, key in ROWS:
            if c[0] == label:
                if key in found:
                    raise SystemExit('FAIL  R14: row "%s" appears more than once' % label)
                # Front psi, Front bar, Rear psi, Rear bar
                found[key] = (c[1], c[2], c[3], c[4])
    return found


def calc_values(path):
    t = open(path, encoding='utf-8').read()
    m = re.search(r'var LADEN_R14\s*=\s*\{(.*?)\};', t, re.S)
    if not m:
        return {}, None
    found = {}
    for k, fp, fb, rp, rb in re.findall(
            r"(\w+)\s*:\s*\[\s*(\d+)\s*,\s*'([\d.]+)'\s*,\s*(\d+)\s*,\s*'([\d.]+)'\s*\]", m.group(1)):
        found[k] = (fp, fb, rp, rb)
    d = re.search(r'id="laden-vals">Front ([\d.]+) bar \((\d+) psi\)\s*Rear ([\d.]+) bar \((\d+) psi\)</div>', t)
    default = (d.group(2), d.group(1), d.group(4), d.group(3)) if d else None
    return found, default


def main():
    r14 = r14_values(R14)
    calc, default = calc_values(CALC)
    fails = []
    print('LC76 LADEN-PRESSURE CHECK — R14 §3 (master) vs the calculator')
    print('  terrain       R14 F psi/bar  R psi/bar      calculator F psi/bar  R psi/bar')
    for label, key in ROWS:
        a = r14.get(key)
        b = calc.get(key)
        if a is None:
            fails.append('R14 row "%s" not found' % label)
        if b is None:
            fails.append('calculator LADEN_R14 entry "%s" not found' % key)
        mark = 'ok' if (a and b and a == b) else 'DIFF'
        if a and b and a != b:
            fails.append('%s: R14 %s vs calculator %s' % (key, a, b))
        fa = '%s/%s  %s/%s' % a if a else '—'
        fb = '%s/%s  %s/%s' % b if b else '—'
        print('  %-12s  %-24s  %-24s  %s' % (key, fa, fb, mark))
    extra = sorted(set(calc) - {k for _, k in ROWS})
    if extra:
        fails.append('calculator LADEN_R14 has entries this check does not know: %s' % ', '.join(extra))
    if default is None:
        fails.append("calculator 'Full expedition load' default text not found")
    elif r14.get('highway') and default != r14['highway']:
        fails.append('calculator box default text %s vs R14 tar loaded %s' % (default, r14['highway']))
    else:
        print('  box default text (tar): %s/%s  %s/%s  ok' % default)
    if fails:
        print('\nRESULT: FAIL')
        for f in fails:
            print('  ' + f)
        sys.exit(1)
    print('\nRESULT: PASS')


if __name__ == '__main__':
    main()
