# Handover — Build "The History of the Land Cruiser"

**For:** a new chat in the LC76 Overland Library project (Opus-class, per PI §9: new document build)
**Prepared:** 28 September 2026
**Owner:** Neil
**Status:** scope, research and owner rulings are complete. This pack is the change spec (PI §9), so the build session executes it without re-asking, except the one confirmation in §3.

---

## 1. What to build

One new **Philosophy-family** library document on the history of the Toyota Land Cruiser. It is written for reading and learning, not for field use.

- **File name (proposed):** `LC76_History_of_the_Land_Cruiser.html`. This mirrors the existing `LC76_History_of_Overlanding.html`.
- **Content source:** `claude/LC76_LandCruiser_History_Research_Dossier.md` in project knowledge (33,661 bytes, 28 Sep 2026). **Read it in full before writing anything.** Every fact in the new document must come from the dossier and keep its source.
- **Layout source:** `LC76_History_of_Overlanding.html`. Fetch it live, pinned to the commit ID (PI §4), and copy its structure, CSS, sticky masthead + TOC unit, TOC script and print block. Change only the content.

---

## 2. Owner rulings (28 Sep 2026) — binding

1. **Scope**
   - The Prado is a side branch.
   - Cover up to the latest models (300 Hybrid, 250, Land Cruiser FJ).
   - Cover all markets. The document is for history and education, not for our trip or for parts.
2. **Toyota War (Chad–Libya, 1986–87): INCLUDED.**
   - Write it as plain, sourced history (dossier §9).
   - Do NOT call the Chadians "outnumbered" at Fada; they were the larger force in that battle.
   - Libyan loss figures appear only as "according to American sources".
3. **No prices anywhere.**
4. **Layout:** copy a Philosophy-section document (see §1).
5. **No general document template exists** (only the country-profile template). The owner has decided NOT to pursue one. Do not raise it again.
6. **Language:** the owner wants plain English, no unexplained abbreviations or jargon (project preference, 24 Sep 2026).
   - Explain every model code and engine code the first time it appears.
   - Keep the reading level of *The History of Overlanding*.

---

## 3. One thing to confirm with Neil at the start

Confirm `LC76_History_of_Overlanding.html` as the layout source. If he names a different Philosophy document, use that one instead. Ask this in a single line, then proceed.

---

## 4. Numbering and masthead

- **No R-number.** Philosophy documents are unnumbered (Library Register, PHILOSOPHY & ETHOS). R44 stays the next free reference number; PI §2 does not change on this point.
- **Masthead** (Design Guidelines S10, v1.9), six slots plus the philosophy gloss:
  - back-link ⌂ Index;
  - eyebrow `Philosophy · Land Cruiser` (a new eyebrow word; see §7);
  - title `The History of the Land Cruiser`;
  - subtitle, ~12 words or fewer;
  - italic gloss line (`.std-local`) BELOW the subtitle, for example "A companion to the Manifesto — the vehicle we chose, and where it came from";
  - the invariant identity line, word for word;
  - `Last updated: 28 September 2026`, or the build date.
- **Footer:** none (philosophy family).

---

## 5. Proposed structure (dossier §11 — adjust only if the content demands it)

1. Why this history matters
2. Origins — the BJ and the 20 Series
3. The workhorses — 40 and 70 Series
4. The station wagons — 55 to 300
5. The Prado — a side branch
6. The Land Cruiser FJ
7. The engines — families, what each was, where it went
   - A table is expected. It must include the 1HZ, the 1HD-T / FT / FTE line and the 1VD.
8. Around the world — country variants, local assembly, the Toyota War
9. Reading a model code (HZJ76, VDJ79 …)
10. Where our 76 sits
    - A pointer to `LC76_Facts.txt` ONLY; no figures about our vehicle.
11. Sources, and where the sources disagree
    - Carry the dossier §8 conflict table and the §10 source list.

**Keep the TOC labels short.** The TOC is one row at every width (PI §7); the h2 carries the full title.

---

## 6. Content rules that apply to this build

- **Numeric traceability** (PI §5)
  - Every figure carries its source.
  - Where sources disagree, say so (dossier §8); never pick one quietly.
  - Do not add any figure that is not in the dossier. If one seems needed, research and source it first.
- **Unconfirmed items** (dossier §11 item 6)
  - Re-check them, or present them as "reported".
  - The items: Bandeirante as the first Toyota built outside Japan; the GXL 105 with the 1HD-FTE; the ADE-engined South African 75; Gibraltar Stockholdings; the Fuji climb month and driver; the Australian 70th-anniversary numbers.
- **1HZ = interference engine** (PI §6). If the document mentions the timing belt, say so consistently.
- **Excluded source:** enginecode.uk. Do not use it.
- **Toyota's first common-rail diesel** was the 1CD-FTV (1999), not the 1KD-FTV. Say "the first common-rail diesel in a Land Cruiser".

---

## 7. Knock-on changes (same session — ownership-first, PI §5)

1. **sw.js** — this is a LIBRARY file, and the philosophy documents are precached.
   - Add the new file to PRECACHE next to `./LC76_History_of_Overlanding.html` (checked 28 Sep 2026: PRECACHE line 66).
   - **Bump CACHE `lc76-library-v28` → `v29`.**
2. **index.html** — add a card in section 7, Philosophy & Ethos (`<div class="card-grid sec-philosophy-g">`, near line 749), after the History of Overlanding card (near line 768).
   - Inspect that card's markup first.
   - Plain field voice, one or two sentences, no codes, no figures.
   - Bump the header "Last Updated".
3. **LC76_Library_Register.txt** — add an entry to the PHILOSOPHY & ETHOS block, in the same format as the other four.
4. **LC76_Design_Guidelines.html** — S10:
   - the collection table row currently reads `· Manifesto | Commentary | History | Systems` / "The 4 philosophy docs": add the new eyebrow word and make it 5;
   - the "four philosophy documents" wording near line 904 becomes five.
   - This is a governance/infrastructure file: no CACHE effect of its own.
5. **LC76_Project_Instructions.txt**
   - §2 CACHE constant → v29, with the reason;
   - a new header block for this session, per header housekeeping (current + two priors; the oldest prior moves verbatim to LC76_Session_History.txt);
   - "Last updated" bumped;
   - the full file delivered, and also for pasting into the project field.
6. **LC76_Session_History.txt** — receives the moved header block and gets its archive-index line.
7. **Open Items Register**
   - No item is expected to open or close.
   - Re-date the header only if the file is touched.
   - Confirm next free OI-113 still matches.

---

## 8. Validation before delivery (PI §8)

- Depth walk on the new HTML with scripts and comments stripped: final depth 0, minimum depth 0.
- `node --check` on every inline script.
- TOC index contract:
  - `len(sectionIds) == len(tocLinks)`;
  - every id resolves to an element;
  - the pairing is in order;
  - the toggle expression has been read;
  - zero targets counts as a probe failure.
- Anchor and id uniqueness.
- Mobile pattern: html/body `overflow-x:clip`, the `::before` slab, the print guard.
- The identity line matches the other files byte for byte.
- A sweep of the new file for:
  - any `R` followed by digits used as a price (should be zero);
  - `enginecode`;
  - "outnumbered" near "Fada";
  - any figure that has no source.
- Governance files: whole-file delivery, count==1 anchors plus an absence check, encode before write, a roll-forward reconciliation.
- Presence is not visibility: open the finished page and check that the masthead, gloss line and TOC highlighting actually render correctly.

---

## 9. Deliverables (whole files, never patches)

1. `LC76_History_of_the_Land_Cruiser.html` (new)
2. `sw.js` (v29)
3. `index.html`
4. `LC76_Library_Register.txt`
5. `LC76_Design_Guidelines.html`
6. `LC76_Project_Instructions.txt` (also paste into the project field)
7. `LC76_Session_History.txt`

**Size note:** the dossier is large and the finished page will likely exceed 80 KB. Build in stages on disk: skeleton and CSS first, then sections, then concatenate. Deliver ONE complete file.

---

## 10. Suggested opening message for the new chat

> Build the new Philosophy document "The History of the Land Cruiser" per the handover `claude/LC76_LandCruiser_History_Build_Handover.md` and the research dossier `claude/LC76_LandCruiser_History_Research_Dossier.md` (both in project knowledge). Fetch everything live, pinned to the commit ID. Confirm the layout source with me, then build.
