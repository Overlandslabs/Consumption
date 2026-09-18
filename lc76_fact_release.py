#!/usr/bin/env python3
"""lc76_fact_release.py — reads the fact store, computes derived values, and
BAKES each fact's display value into every <span data-fact="id"> in the given
HTML files (print-safe: the number is written into the file, not a runtime
token). Idempotent; reports every slot changed; never edits untagged text.
Usage: lc76_fact_release.py <facts.txt> <file1.html> [file2.html ...]"""
import sys, re
from lc76_facts_lib import parse_store, display_of, SPAN, TXTFACT

def main(argv):
    if len(argv) < 2:
        print("usage: lc76_fact_release.py <facts.txt> <html...>"); return 2
    facts, ferr = parse_store(open(argv[0], encoding='utf-8').read())
    if ferr:
        for e in ferr: print("STORE ERROR:", e)
        print("release aborted — store does not parse cleanly"); return 1
    changed = miss = 0
    for path in argv[1:]:
        src = open(path, encoding='utf-8').read()
        rep = []
        def sub(m):
            nonlocal changed, miss
            fid, cur = m.group(1), m.group(2)
            if fid not in facts:
                miss += 1; rep.append(f"  ? unknown fact id '{fid}' — left as-is")
                return m.group(0)
            disp = display_of(facts, fid)
            if cur != disp:
                changed += 1; rep.append(f"  ~ {fid}: '{cur}' -> '{disp}'")
            return f'<span data-fact="{fid}">{disp}</span>'
        out = SPAN.sub(sub, src)
        def tsub(m):
            nonlocal changed
            fid, cur = m.group(1), m.group(2)
            if fid not in facts: return m.group(0)
            disp = display_of(facts, fid)
            if cur != disp: changed += 1; rep.append(f"  ~ {fid}: '{cur}' -> '{disp}'")
            return f'<fact:{fid}>{disp}</fact>'
        out = TXTFACT.sub(tsub, out)
        if out != src:
            b = out.encode('utf-8')            # encode-before-truncate
            open(path, 'wb').write(b)
        print(f"{path}: {len([r for r in rep if r.strip().startswith('~')])} slot(s) updated")
        for r in rep: print(r)
    print(f"\nRELEASE: {changed} slot(s) changed, {miss} unknown id(s)")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
