#!/usr/bin/env python3
"""lc76_fact_gate.py — session-close / pre-commit gate.
FAILS (exit 1) if: (a) any <span data-fact="id"> text != the store display;
(b) any derived slot != its recomputed formula display (subsumed by (a), checked
independently). WARN tier (c) drift-catcher: any known NON-EVENT fact value that
appears in prose UNTAGGED (a hand-typed copy). EVENT mileages are whitelisted
(they legitimately appear untagged as historical figures).
Usage: lc76_fact_gate.py <facts.txt> <html...>"""
import sys, re
from lc76_facts_lib import parse_store, display_of, value_of, SPAN, TXTFACT, FACT_LINE

def main(argv):
    if len(argv) < 2:
        print("usage: lc76_fact_gate.py <facts.txt> <html...>"); return 2
    facts, ferr = parse_store(open(argv[0], encoding='utf-8').read())
    fails, warns = list(ferr), []
    # whitelist: EVENT values (grouped) may appear untagged in prose
    event_vals = {f"{value_of(facts,fid):,}" for fid,f in facts.items() if f.get('kind')=='EVENT'}
    live_vals  = {f"{value_of(facts,fid):,}": fid for fid,f in facts.items()
                  if f.get('kind')!='EVENT' and ('value' in f or 'derived' in f)}
    for path in argv[1:]:
        src = open(path, encoding='utf-8').read()
        # (a)/(b): tagged slots must equal store display
        for m in SPAN.finditer(src):
            fid, cur = m.group(1), m.group(2)
            if fid not in facts:
                fails.append(f"{path}: slot '{fid}' has no store entry"); continue
            disp = display_of(facts, fid)
            if cur != disp:
                fails.append(f"{path}: slot {fid} '{cur}' != store '{disp}'")
        for m in TXTFACT.finditer(src):
            fid, cur = m.group(1), m.group(2)
            if fid not in facts:
                fails.append(f"{path}: <fact:{fid}> has no store entry"); continue
            disp = display_of(facts, fid)
            if cur != disp:
                fails.append(f"{path}: <fact:{fid}> '{cur}' != store '{disp}'")
        # (c) drift-catcher: strip tagged spans, then look for live values untagged
        stripped = SPAN.sub('', src)
        stripped = TXTFACT.sub('', stripped)
        stripped = FACT_LINE.sub('', stripped)   # the store itself is not 'prose'
        for val, fid in live_vals.items():
            if val in event_vals:            # ambiguous with a historical figure
                continue
            if re.search(r'(?<!\d)'+re.escape(val)+r'(?!\d)', stripped):
                warns.append(f"{path}: live value '{val}' ({fid}) appears UNTAGGED in prose")
    # (d) OVERRUN check: a derived km-since fact that meets/exceeds its service interval
    for fid,ff in facts.items():
        if 'derived' in ff and 'interval' in ff:
            try:
                v=value_of(facts,fid); iv=int(str(ff['interval']).replace(',',''))
                if v>=iv:
                    warns.append(f"OVERRUN: {fid} at {v:,} km >= interval {iv:,} km (+{v-iv:,}) — review conclusions in docs that cite it")
            except Exception: pass
    for w in warns: print("WARN:", w)
    if fails:
        for x in fails: print("FAIL:", x)
        print(f"\nFACT GATE: FAIL ({len(fails)} error(s), {len(warns)} warn(s))"); return 1
    print(f"FACT GATE: PASS ({len(warns)} warn(s))"); return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
