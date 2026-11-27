# LC76 Field Handbook — the printed book

The Field Handbook (Volume II) is a printed copy of this library, built by script from the
library pages. **It is not a library file**: it is not precached, not on the phone library's
offline list, and never triggers a CACHE bump. The phone library is always the current
text; where the book and the library disagree, the library wins.

- **The PDF** of each edition is attached to a release on GitHub
  (github.com/Overlandslabs/Consumption/releases), tagged `handbook-…`, with the date and
  the library commit it was built from. It is not kept in the repository itself.
- **This folder** holds what is needed to rebuild it.
- **`edition.txt`** records the current edition: its name, date, library commit, page count,
  and a fingerprint of every source page.
- **Is the book behind?** The standing checks (`lc76_run_checks.py`) carry a report line,
  *Printed book*, that lists every chapter whose library page has changed since the
  edition was built. It never blocks a commit.

## Files

| File | What it is |
|---|---|
| `volume-2.txt` | The book map: chapter order, titles, edge-tab colours, flags |
| `introduction.html` | The introduction (the owners' own text) |
| `build_book.py` | Converts every library page into the one book template and lays out the pages |
| `template.css` | The book template (the only styles used; no library page CSS is carried) |
| `reconcile.py` | Checks every number in the PDF against the library page it came from — STOPs must be 0 |
| `wordcheck.py` | Counts every library word against the book, chapter by chapter |
| `orphans.py` | Finds any heading left at a page foot apart from its text and moves it on |
| `lc76_book_check.py` | The *Printed book* report, and `--record` to write `edition.txt` |

## Rebuilding an edition

Needs Python 3 with `weasyprint` (70), `beautifulsoup4`, `lxml`, `pypdfium2`, and the
fonts from fontsource 5.3.0 (Oswald, Bebas Neue, IBM Plex Mono) unpacked in one folder.

```
cd book
BOOK_PLAN=volume-2.txt BOOK_EDITION="<edition name>" python3 build_book.py .. volume-2.txt out <fonts>
python3 orphans.py out/book.html out/fixed.pdf      # then use out/fixed.pdf and out/book_fixed.html
python3 reconcile.py .. volume-2.txt out              # STOPs must be 0
python3 wordcheck.py .. volume-2.txt out              # only the known, by-design losses
python3 lc76_book_check.py --record "<edition name>" <library commit> <pages>
```

A full build is about ten layout passes of six to seven minutes. Every page is looked at
before the edition is released. Then the PDF goes up as a new release and `edition.txt`
is committed through a pull request like any other change.
