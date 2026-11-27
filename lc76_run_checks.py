#!/usr/bin/env python3
"""LC76 RUN CHECKS — every standing check, one command (added 16 Nov 2026,
owner ruling on proposal P2: the checks run by themselves on every commit).

WHY. The checks used to run only when a session remembered to run them, and
their result was reported in the session's own notes. PI §5 G5: checking must
be systemic, never dependent on someone remembering. This script is the one
entry point. GitHub runs it on every commit and pull request
(.github/workflows/lc76-checks.yml); a session runs the same command before
it delivers. Same command, same answer, whoever runs it.

WHAT IT RUNS, in this order:
  1. Fact store        LC76_Fact_Validator.py     the store is well formed
  2. Fact copies       lc76_fact_gate.py          every tagged copy = the store
  3. Stale terms       lc76_currency_gate.py      no retired term on a page
  4. Open items        LC76_OIR_Validator.py      register schema; next-free
  5. Laden pressures   lc76_laden_check.py        calculator copy = R14
  6. Page structure    lc76_structure_check.py    tags, ids, script syntax
  7. Dashboard         lc76_dashboard_build.py    dashboard = the register
  8. Screen margins    lc76_margin_check.py       nothing runs to the edge
  9. Negative claims   lc76_basis_scan.py         REPORT ONLY — never blocks
 10. Printed book      book/lc76_book_check.py    REPORT ONLY — lists chapters changed since
                                                 the printed edition was built (27 Nov 2026)
Each check's own output is printed in full, then one summary table.

Exit code 1 if any of checks 1–8 fails, or cannot run. A check that cannot
run is a FAIL, not a skip: a probe that reads nothing has found nothing.

ONE STANDING EXCLUSION. The stale-terms check is run without
LC76_PI_SessionB_Diff.html. That page is a frozen governance snapshot which
quotes retired terms on purpose (three fail-tier hits, all in that file, at
HEAD 9946fba, 16 Nov 2026). Run lc76_currency_gate.py on its own to see them.

HONEST LIMIT. These checks catch SHAPE and DRIFT, not TRUTH: an invented
figure in a well-formed sentence passes all nine. The TOC index contract,
the colour-PDF print check and reading a changed page by eye are still done
in session. --fast leaves out the margin check (the only one that needs a
browser, about a minute) and says so in the summary.

USAGE
  python3 lc76_run_checks.py          all nine
  python3 lc76_run_checks.py --fast   without the margin check
Governance tool — NOT precached, no CACHE bump.
"""
import glob, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = 'LC76_PI_SessionB_Diff.html'


def pages():
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, '*.html')))


def checks(fast):
    html = pages()
    out = [
        ('Fact store', ['LC76_Fact_Validator.py', 'LC76_Facts.txt'], True),
        ('Fact copies', ['lc76_fact_gate.py', 'LC76_Facts.txt'] + html, True),
        ('Stale terms', ['lc76_currency_gate.py'] + [h for h in html if h != SNAPSHOT], True),
        ('Open items', ['LC76_OIR_Validator.py', 'LC76_Open_Items_Register.txt',
                        'LC76_Project_Instructions.txt'], True),
        ('Laden pressures', ['lc76_laden_check.py'], True),
        ('Page structure', ['lc76_structure_check.py'], True),
        ('Dashboard', ['lc76_dashboard_build.py', '--check'], True),
    ]
    if not fast:
        out.append(('Screen margins', ['lc76_margin_check.py'], True))
    out.append(('Negative claims', ['lc76_basis_scan.py'], False))
    out.append(('Printed book', ['book/lc76_book_check.py'], False))
    return out


def main(argv):
    fast = '--fast' in argv
    if not pages():
        print('RUN CHECKS: FAIL — no pages found in', HERE)
        return 1
    rows, failed = [], 0
    for name, cmd, blocking in checks(fast):
        print('\n' + '=' * 70 + f'\n{name}  ({cmd[0]})\n' + '=' * 70, flush=True)
        if not os.path.exists(os.path.join(HERE, cmd[0])):
            print('script not found')
            code = 127
        else:
            code = subprocess.run([sys.executable] + cmd, cwd=HERE).returncode
        if not blocking:
            verdict = 'REPORT'
        elif code == 0:
            verdict = 'PASS'
        else:
            verdict = 'FAIL'
            failed += 1
        rows.append((name, verdict, code))
    print('\n' + '=' * 70 + '\nSUMMARY\n' + '=' * 70)
    for name, verdict, code in rows:
        print(f'  {verdict:<7} {name}' + (f'  (exit {code})' if verdict == 'FAIL' else ''))
    if fast:
        print('  NOT RUN Screen margins  (--fast)')
    print(f'\nRUN CHECKS: {"FAIL" if failed else "PASS"}'
          + (f' — {failed} check(s) failed' if failed else '')
          + (' — margin check not run' if fast else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
