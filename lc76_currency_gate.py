#!/usr/bin/env python3
"""
lc76_currency_gate.py — content-currency rejecter for the LC76 library.

Reads lc76_supersessions.txt and greps every library HTML file for any retired
term still present outside its documented exemptions.  It is DRIVEN BY THE LOG,
not by a list baked into this script: a new real-world change is caught the
moment its old->new row is added to the log, which is the same act as recording
the change.  See the log header for the design and its honest limit.

  FAIL-tier hit  -> printed as VIOLATION, gate exits non-zero.
  WARN-tier hit  -> printed as REVIEW, does not fail the gate.

Usage:  python3 lc76_currency_gate.py [--log lc76_supersessions.txt] [glob ...]
        default glob = *.html in cwd.  Governance/audit .txt are not scanned
        (they legitimately narrate history); audit HTML is skipped globally.
"""
import sys, re, glob, os

GLOBAL_SKIP = ("LC76_Library_Audit_2026",)  # historical audit snapshots

def load(log):
    rows=[]
    for ln in open(log,encoding="utf-8"):
        ln=ln.rstrip("\n")
        if not ln.strip() or ln.lstrip().startswith("#"): continue
        parts=[p.strip() for p in ln.split(" :: ")]
        if len(parts)<7: continue
        old,new,tier,as_of,ef,el,note=parts[:7]
        rows.append(dict(old=old,new=new,tier=tier,as_of=as_of,
                         ef=[x for x in ef.split("|") if x and x!="-"],
                         el=None if el in("-","") else re.compile(el,re.I),
                         note=note))
    return rows

def main():
    args=sys.argv[1:]; log="lc76_supersessions.txt"
    if "--log" in args: i=args.index("--log"); log=args[i+1]; del args[i:i+2]
    files=[f for g in (args or ["*.html"]) for f in glob.glob(g)]
    files=sorted(set(f for f in files if not any(s in f for s in GLOBAL_SKIP)))
    rows=load(log)
    viol=[]; rev=[]
    for r in rows:
        pat=re.compile(r["old"],re.I)
        for f in files:
            if any(s in os.path.basename(f) for s in r["ef"]): continue
            for n,line in enumerate(open(f,encoding="utf-8",errors="replace"),1):
                if not pat.search(line): continue
                if r["el"] and r["el"].search(line): continue      # legitimate use
                snip=re.sub(r"\s+"," ",line).strip()
                m=pat.search(line); s=max(0,m.start()-18)
                snip=snip[:120]
                (viol if r["tier"]=="fail" else rev).append(
                    (f, n, r["new"], snip))
    print(f"CURRENCY GATE — {len(files)} files, {len(rows)} supersessions")
    if viol:
        print(f"\n*** {len(viol)} VIOLATION(S) — stale term must be current ***")
        for f,n,new,snip in viol: print(f"  FAIL {os.path.basename(f)}:{n}  (-> {new})\n       {snip}")
    if rev:
        print(f"\n{len(rev)} REVIEW item(s) (warn-tier — confirm legitimate):")
        for f,n,new,snip in rev: print(f"  warn {os.path.basename(f)}:{n}  (-> {new})")
    if not viol and not rev: print("CLEAN — no retired terms outside exemptions.")
    print(f"\nGATE: {'FAIL' if viol else 'PASS'}  ({len(viol)} violation, {len(rev)} review)")
    sys.exit(1 if viol else 0)

if __name__=="__main__": main()
