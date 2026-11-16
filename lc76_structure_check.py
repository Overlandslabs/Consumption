#!/usr/bin/env python3
"""LC76 STRUCTURE CHECK — the page-structure checks of PI §8 as one script
(added 16 Nov 2026, owner ruling on proposal P2: the checks run by themselves
on every commit).

WHY. Until now the depth walk, the duplicate-id check and the script syntax
check were written afresh in each session's working folder and their result
was reported in the session notes. A check that lives in a session is not
re-runnable by anyone else. This file puts them in the repo.

WHAT IT DOES, for every library page (*.html):
  1. DEPTH WALK. Strips <script>, <style> and HTML comments, then walks the
     <div> and <span> tags. FAIL if the depth ever goes below zero or does
     not end at zero.
  2. DUPLICATE IDS. FAIL if the same id="..." appears twice in the static
     page (scripts and comments stripped).
  3. SCRIPT SYNTAX. Runs `node --check` on every inline <script> that is
     JavaScript. FAIL on a syntax error. Skipped with a note if node is not
     installed.
A page/check pair listed in lc76_structure_baseline.txt with a count is
accepted up to that count — every baseline line needs a note saying why.

Exit code 1 on FAIL, 0 on PASS.

HONEST LIMIT. It checks SHAPE, not RESULT: two tag errors that cancel still
pass the walk (the margin check looks at the result). It does not check the
TOC index contract, which differs by page and is still checked in session.

USAGE
  python3 lc76_structure_check.py            every *.html in this folder
  python3 lc76_structure_check.py F.html ... the named pages only
Governance tool — NOT precached, no CACHE bump.
"""
import glob, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, 'lc76_structure_baseline.txt')
SCRIPT = re.compile(r'<script\b([^>]*)>(.*?)</script\s*>', re.S | re.I)
STRIP = re.compile(r'<script\b.*?</script\s*>|<style\b.*?</style\s*>|<!--.*?-->', re.S | re.I)
TAG = re.compile(r'<(/?)(div|span)\b[^>]*?(/?)>', re.I)
IDS = re.compile(r'<[a-zA-Z][^>]*?\sid\s*=\s*["\']([^"\']+)["\']', re.S)


def load_baseline():
    base = {}
    if os.path.exists(BASELINE):
        for ln in open(BASELINE, encoding='utf-8'):
            ln = ln.strip()
            if not ln or ln.startswith('#'):
                continue
            parts = [p.strip() for p in ln.split('::')]
            if len(parts) >= 3:
                base[(parts[0], parts[1])] = int(parts[2])
    return base


def walk(static, tag):
    depth = low = 0
    for m in TAG.finditer(static):
        if m.group(2).lower() != tag or m.group(3):
            continue
        depth += -1 if m.group(1) else 1
        low = min(low, depth)
    return depth, low


def check(path, have_node):
    """Return a dict: check name -> number of problems found."""
    raw = open(path, encoding='utf-8', errors='replace').read()
    static = STRIP.sub('', raw)
    out = {}
    for tag in ('div', 'span'):
        end, low = walk(static, tag)
        out['walk-' + tag] = (1 if end != 0 else 0) + (1 if low < 0 else 0)
    seen, dup = set(), set()
    for i in IDS.findall(static):
        (dup if i in seen else seen).add(i)
    out['dup-id'] = len(dup)
    bad = 0
    if have_node:
        for attrs, body in SCRIPT.findall(raw):
            a = attrs.lower()
            if 'src=' in a or not body.strip():
                continue
            if 'type=' in a and not re.search(r'type\s*=\s*["\']?(text/javascript|module)', a):
                continue  # JSON, templates
            ext = '.mjs' if 'module' in a else '.js'
            with tempfile.NamedTemporaryFile('w', suffix=ext, delete=False, encoding='utf-8') as f:
                f.write(body)
            r = subprocess.run(['node', '--check', f.name], capture_output=True)
            os.unlink(f.name)
            bad += 1 if r.returncode else 0
    out['script'] = bad
    return out


def main(argv):
    pages = argv or sorted(glob.glob(os.path.join(HERE, '*.html')))
    if not pages:
        print('STRUCTURE CHECK: FAIL — no pages found (a probe that reads nothing has found nothing)')
        return 1
    have_node = shutil.which('node') is not None
    if not have_node:
        print('note: node not installed — script syntax NOT checked')
    base = load_baseline()
    fails = accepted = 0
    for p in pages:
        name = os.path.basename(p)
        for chk, n in check(p, have_node).items():
            if n == 0:
                continue
            allowed = base.get((name, chk), 0)
            if n > allowed:
                fails += 1
                print(f'  FAIL {name}: {chk} = {n} (baseline allows {allowed})')
            else:
                accepted += 1
    verdict = 'FAIL' if fails else 'PASS'
    print(f'STRUCTURE CHECK: {verdict} ({len(pages)} pages, {fails} fail(s), {accepted} accepted by baseline)')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
