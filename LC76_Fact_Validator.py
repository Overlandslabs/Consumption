#!/usr/bin/env python3
"""LC76_Fact_Validator.py — the fact analogue of LC76_OIR_Validator.py.
FAILS loudly (exit 1) on: malformed fact line; missing grade; duplicate id;
derived formula referencing an unknown id; a derived fact carrying a stored
value= result; an EVENT fact whose value differs from the committed baseline
(immutability) or a baseline EVENT deleted. WARNS (non-blocking) on: a fact
with no owner. Usage: LC76_Fact_Validator.py <facts.txt> [--baseline <old.txt>]"""
import sys, re
from lc76_facts_lib import parse_store, value_of

def main(argv):
    if not argv:
        print("usage: LC76_Fact_Validator.py <facts.txt> [--baseline <old>]"); return 2
    path = argv[0]
    base = argv[argv.index('--baseline')+1] if '--baseline' in argv else None
    text = open(path, encoding='utf-8').read()
    facts, fails = parse_store(text)          # fails already holds malformed/dup
    warns = []
    for fid, f in facts.items():
        if 'grade' not in f:
            fails.append(f"{fid}: missing grade")
        if 'derived' in f and 'value' in f:
            fails.append(f"{fid}: derived fact carries a stored value= (must be recomputed, never stored)")
        if 'owner' not in f:
            warns.append(f"{fid}: no owner (WARN)")
    # resolve every derived value once — surfaces unknown-id refs / cycles as FAIL
    for fid, f in facts.items():
        if 'derived' in f:
            try: value_of(facts, fid)
            except Exception as e: fails.append(f"{fid}: {e}")
    # EVENT immutability against a committed baseline
    if base:
        bfacts, _ = parse_store(open(base, encoding='utf-8').read())
        for fid, bf in bfacts.items():
            if bf.get('kind') == 'EVENT':
                if fid not in facts:
                    fails.append(f"EVENT {fid} deleted vs baseline (history is immutable)")
                elif str(facts[fid].get('value')) != str(bf.get('value')):
                    fails.append(f"EVENT {fid} changed {bf.get('value')} -> {facts[fid].get('value')} (immutable)")
    for w in warns: print("WARN:", w)
    if fails:
        for x in fails: print("FAIL:", x)
        print(f"\nFACT VALIDATOR: FAIL ({len(fails)} error(s), {len(warns)} warn(s)) — {len(facts)} facts parsed")
        return 1
    print(f"FACT VALIDATOR: PASS — {len(facts)} facts, {len(warns)} warn(s)")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
