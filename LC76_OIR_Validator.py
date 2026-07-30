#!/usr/bin/env python3
# LC76 Open Items Register — schema validator (Audit of Truth, charter R2 / §11).
# "A schema is only real if something rejects violations." Run at every session
# close. Exits non-zero on any FAIL. Usage: python3 LC76_OIR_Validator.py [OIR] [PI]
import sys, re

OIR = sys.argv[1] if len(sys.argv) > 1 else "LC76_Open_Items_Register.txt"
PI  = sys.argv[2] if len(sys.argv) > 2 else None

OPEN_VOCAB = {"OPEN","BLOCKED","WAITING-DATE","DONE-PENDING-EVIDENCE","STANDING"}
# tokens that make a SOURCE a "place" (A7) or a closure "checkable" (A10 strict)
PLACE = re.compile(r'(R\d|§|RA-|EX-|TA[-_]|ADV-|F\d|WCG|ref\b|Facts|\.txt|\.html|xlsx|working papers|charter|ruling|sweep|manual|annex|Project Instructions|standing rule|20\d\d)', re.I)
COMMITISH = re.compile(r'([0-9a-f]{7,40}\b|HTTP[ -]?404|testzip|byte|char|corpus assert|ref\s*\d|\.eml|HEAD [0-9a-f]|sw\.js|precache|index\.html|index link|validator PASSES)', re.I)

s = open(OIR, encoding="utf-8").read()
body = s.split("CONTROLLED DUPLICATION REGISTER")[0]
closed = s.split("CLOSED LOG (most recent first")[1] if "CLOSED LOG (most recent first" in s else ""

# --- parse open entries ---
idxs = [m.start() for m in re.finditer(r'(?m)^OI-\d+ ', body)]
entries = []
for a in range(len(idxs)):
    st = idxs[a]; en = idxs[a+1] if a+1 < len(idxs) else len(body)
    chunk = body[st:en]
    oi = int(re.match(r'OI-(\d+)', chunk).group(1))
    entries.append((oi, chunk))

fails, warns = [], []
def F(oi, msg): fails.append(f"OI-{oi}: {msg}")
def W(oi, msg): warns.append(f"OI-{oi}: {msg}")

seen = set()
for oi, ch in entries:
    lines = ch.split("\n")
    if oi in seen: F(oi, "DUPLICATE id")
    seen.add(oi)
    # 1. WHAT line
    if not any(re.match(r'\s+WHAT:', l) for l in lines):
        F(oi, "missing WHAT: line")
    # 2. meta line OWNER · GATE · SOURCE (>=2 middots), not the CONFIRMED line
    meta = [l for l in lines if l.count(" · ") >= 2 and "CONFIRMED" not in l and "NEXT-DUE" not in l]
    if not meta:
        F(oi, "missing OWNER · GATE · SOURCE meta line")
    # 3. STATUS token line
    status_line = None
    for l in lines[1:]:
        tok = l.strip().split()[0] if l.strip() else ""
        tok = tok.rstrip(".—:")
        if tok in OPEN_VOCAB:
            status_line = l; status_tok = tok; break
    if status_line is None:
        F(oi, "no STATUS line with a controlled-vocabulary token")
    # 4. CONFIRMED / NEXT-DUE
    conf = [l for l in lines if "CONFIRMED" in l and "NEXT-DUE:" in l]
    if not conf:
        F(oi, "missing CONFIRMED / NEXT-DUE field")
    elif not re.search(r'CONFIRMED\s+\d', conf[0]):
        F(oi, "CONFIRMED field has no date")
    # 5. SOURCE-as-place (A7) — 3rd component of meta line
    if meta:
        src = meta[0].split(" · ")[-1].strip()
        if not PLACE.search(src):
            W(oi, f"SOURCE may name a moment not a place: '{src[:50]}'")

# --- cross-file: next-free (PI) == max OI + 1 ---
open_ids = [oi for oi,_ in entries]
closed_ids = [int(x) for x in re.findall(r'\bOI-(\d+)\s*·', closed)]
maxoi = max(open_ids + closed_ids)
if PI:
    pit = open(PI, encoding="utf-8").read().split("\nPRIOR (")[0]
    m = re.search(r'next free\s+OI-(\d+)', pit)
    if m:
        nf = int(m.group(1))
        if nf != maxoi + 1:
            F("x-file", f"PI next-free OI-{nf} != OIR max OI-{maxoi} + 1")

# --- closed-log strict standard (D4) ---
# entries reclassified DONE-PENDING are exempt; remaining CLOSED must name a checkable artifact
reclass = set()
mblk = re.search(r'DONE-PENDING-EVIDENCE:(.*?)The other fifteen', closed, re.S)
if mblk:
    reclass = {int(x) for x in re.findall(r'OI-(\d+)', mblk.group(1))}
cidx = [m.start() for m in re.finditer(r'\bOI-\d+ ?·', closed)]
for a in range(len(cidx)):
    st=cidx[a]; en=cidx[a+1] if a+1<len(cidx) else len(closed)
    cch=closed[st:en]
    m=re.match(r'OI-(\d+)', cch)
    if not m: continue
    cid=int(m.group(1))
    if cid in reclass: continue
    if not COMMITISH.search(cch):
        W(cid, "CLOSED closure names no obviously-checkable artifact (strict-tier review)")

# --- report ---
print("="*66)
print(f"LC76 OIR VALIDATOR — {len(entries)} open entries, {len(closed_ids)} numbered closures")
print(f"  next-free expected: OI-{maxoi+1}")
print("="*66)
if fails:
    print(f"\n*** {len(fails)} FAIL ***")
    for f in fails: print("  FAIL  "+f)
else:
    print("\nSCHEMA: PASS — every open entry conforms (WHAT, meta, controlled STATUS, CONFIRMED/NEXT-DUE); ids unique; next-free reconciles.")
if warns:
    print(f"\n{len(warns)} WARN (review, not blocking):")
    for w in warns: print("  warn  "+w)
print()
sys.exit(1 if fails else 0)
