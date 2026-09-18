"""LC76 fact-store parsing + derivation. Shared by validator / release / gate.
Line-start anchored parsing (OIR-validator lesson: never split on a phrase that
can occur in prose). A fact line is:  [fact:<id>] key=val key="quoted val" ...
Derived facts carry derived="<expr over fact ids>" and NEVER a value= result."""
import re

FACT_LINE = re.compile(r'(?m)^\s*\[fact:([A-Za-z0-9_]+)\]\s*(.*)$')
TOKEN     = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')
IDENT     = re.compile(r'[A-Za-z_]\w*')
SPAN      = re.compile(r'<span\s+data-fact="([A-Za-z0-9_]+)"\s*>(.*?)</span>', re.S)
TXTFACT   = re.compile(r'<fact:([A-Za-z0-9_]+)>(.*?)</fact>', re.S)  # .txt readable-line tag

def parse_store(text):
    """Return {id: {attrs...}} and a list of parse errors (malformed lines)."""
    facts, errors, seen = {}, [], set()
    for m in FACT_LINE.finditer(text):
        fid, rest = m.group(1), m.group(2)
        toks = {m.group(1): (m.group(2) if m.group(2) is not None else m.group(3))
                for m in TOKEN.finditer(rest)}
        if not toks:
            errors.append(f"[fact:{fid}] has no key=value tokens")
            continue
        if fid in seen:
            errors.append(f"duplicate id: {fid}")
        seen.add(fid)
        toks['_id'] = fid
        facts[fid] = toks
    return facts, errors

def _num(facts, fid, stack=None):
    """Numeric value of a fact (recursively for derived). Detects cycles."""
    stack = stack or []
    if fid in stack:
        raise ValueError(f"cycle through {fid}")
    f = facts[fid]
    if 'value' in f:
        return int(str(f['value']).replace(',', ''))
    if 'derived' in f:
        expr = f['derived']
        if not re.fullmatch(r'[A-Za-z0-9_+\-*/(). ]+', expr):
            raise ValueError(f"illegal chars in formula for {fid}")
        ns = {}
        for ident in set(IDENT.findall(expr)):
            if ident not in facts:
                raise ValueError(f"{fid} formula references unknown id: {ident}")
            ns[ident] = _num(facts, ident, stack + [fid])
        return int(eval(expr, {"__builtins__": {}}, ns))
    raise ValueError(f"{fid} has neither value= nor derived=")

def value_of(facts, fid):
    return _num(facts, fid)

def display_of(facts, fid):
    f = facts[fid]
    if 'derived' in f:
        val = _num(facts, fid)
        unit = f.get('unit', '')
        s = f"{val:,}"
        if f.get('approx') == 'yes':
            s = "~" + s
        return (s + (" " + unit if unit else "")).strip()
    return f.get('display', str(f.get('value', '')))
