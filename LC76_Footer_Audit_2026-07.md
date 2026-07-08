# LC76 OVERLAND REFERENCE LIBRARY — FOOTER AUDIT

**Scope:** All 61 HTML files on GitHub at HEAD `c54cc21`  
**Date:** 8 July 2026  
**Auditor:** Claude (Opus) against live repo  
**Objective:** Catalogue every footer pattern, identify redundancy, and propose a clean-up spec for owner approval.

---

## 1 · METHODOLOGY

Every HTML file linked from `index.html` (plus `index.html` itself, the two audit reports, and `LC76_Design_Guidelines.html`) was fetched SHA-pinned and inspected for:

- Any `<footer>` element or `<div>` with a class containing "footer" (`footer`, `doc-footer`, `page-footer`).
- The **content** of that footer — what information it carries.
- Whether that information is **already present** elsewhere in the same file (masthead identity line, body alerts, section text, cross-reference bars).
- Whether the footer carries **unique functional value** that would be lost if removed.

The audit also checked for orphaned CSS — files that define `.doc-footer` styling but contain no actual footer `<div>` in the body.

---

## 2 · FINDINGS — NINE FOOTER PATTERNS FOUND

### Pattern A — "LC76 Overland Series" legacy (6 files)

**Files:** R12 Water · R13 Drivetrain · R14 Tyre · R15 Border · R16 Comms · R17 Health

Structure (3-line `<footer>` tag):
```
Line 1: LC76 Overland Series · R## · [Title]
Line 2: Vehicle spec OR context string
Line 3: Cross-ref instruction ("Print this guide and keep with R9 & R10")
         OR caveat ("planning tool, not legal advice")
```

**Redundancy assessment:**
- Line 1 (title + R-number): **Fully redundant** — duplicates the masthead eyebrow and title.
- Line 2 (vehicle spec): **Fully redundant** — duplicates the masthead identity line, sometimes with extra drivetrain codes (R151F, HF1A) that add nothing for the field user.
- Line 3 (cross-refs / caveats): **Mixed.** The cross-reference instructions ("keep with R4") are genuinely useful field advice — they tell the user which documents to print and bundle together. However, four of the six files also carry an inline cross-reference bar elsewhere, partially duplicating this. The R15 legal caveat and R17 medical caveat are useful but also appear in the body text (Angola profile has the "verify" warning 3 times).

**Footer branding note:** These six files use the older "LC76 Overland Series" name rather than "Overland Reference Library" — the known footer-branding inconsistency logged in the PI.

---

### Pattern B — "Overland Reference Library" footer (5 files)

**Files:** R8 Service History · R9 Recovery · R10 Emergency · R23 Pre-Trip Prep · R26 Electrical

Structure (varies: `<footer>`, `div.footer`, or `div.doc-footer`; 1–3 lines):

| File | Content |
|------|---------|
| R8 | Single amber line: "LC76 Overland Reference Library" |
| R9 | Same as R8 |
| R10 | Same as R8 |
| R23 | R-number + title + vehicle code + odometer + date + URL |
| R26 | R-number + title + version + date + vehicle identity + URL |

**Redundancy assessment:**
- R8/R9/R10: The single-line "LC76 Overland Reference Library" is pure branding — **fully redundant** with the masthead.
- R23: Odometer reading and date duplicate the masthead. Vehicle code (HZJ76R-RKMRS) is in the identity line. URL is the only non-duplicated element.
- R26: Version number (v2.0) is in the masthead subtitle. Vehicle identity and date duplicate the masthead. URL is the only non-duplicated element.

---

### Pattern C — Long provenance/scope footer (5 files)

**Files:** R34 Brakes · R35 Security & Fire · R36 Wildlife & Camp · R38 Operations Plan · R39 Documentation & Money

Structure (`div.footer`, 3 lines with `<br>` breaks):
```
Line 1: LC76 OVERLAND REFERENCE LIBRARY · R## · [TITLE]
Line 2: Long description of what the document covers (30–60 words)
Line 3: Scope boundaries and cross-references + compilation date
```

**Redundancy assessment:**
- Line 1: **Fully redundant** — title + R-number are in the masthead.
- Lines 2–3: **Substantially redundant.** These are scope abstracts that duplicate the document's own introduction sections. R34 describes "Front disc / rear drum · tandem master..." which is the document's technical content. R35 lists "Part A security... + Part B fire..." which mirrors its own TOC. R38 describes "Part A running the expedition... + Part B ending it well..." — again, its own TOC. The cross-reference information ("Comms hardware owned by R16; medevac & insurance by R29") is genuinely useful for navigation but duplicates existing cross-reference bars or inline references in the body.
- Compilation dates: **Redundant** — now in the masthead "Last updated" line.

---

### Pattern D — Profile footer (8 files)

**Files:** 001 Angola · 002 Namibia · 003 Botswana · 004 Zambia · 005 Kalahari · 006 Tanzania · 007 Mozambique · 008 Malawi

Structure (`div.doc-footer`, 5 lines):

| Line | Content | Redundant? |
|------|---------|------------|
| 1 | Profile title + number + library name | Yes — masthead |
| 2 | Vehicle identity OR exchange rates | Vehicle: yes (masthead). Rates: **unique** for 001–005 |
| 3 | Compiled date + sources list | Date: yes (masthead). **Sources: unique** |
| 4 | "Verify all fees..." warning | **Duplicated** — appears in body alert strips (Angola has it 3×) |
| 5 | overlandslabs.github.io/Consumption URL | **Unique** but minor |

**Key observation:** The **source attributions** (Line 3: "Sources: iOverlander · Tracks4Africa · NWR...") are the only genuinely unique, non-duplicated content in these footers. Exchange rates for older profiles (001–005) are also unique to the footer. The "verify before travel" warning is already in the body alert sections.

---

### Pattern E — No footer (24 files)

**Files:** R1 Reference Card (empty `page-footer` div) · R2 Departure Checklist · R3 Spares & Tools · R11 Packing · R18 Troubleshooting · R21 Turbo · R22 Cooling · R24 Fuel System · R25 Suspension · R27 Bush Mechanics · R28 Driving Conditions · R29 Insurance · R30 Cross-Ref Index · R31 Upgrade Assessment · R37 Crew Register · Service Checklist · 009 Zimbabwe · 010 Kenya · Manifesto · Commentary · Design Guidelines · Audit Jun 2026 (has internal governance footer — separate category) · Audit Jul 2026 (ditto)

These files have no footer content in the body. Some (R1, Zimbabwe, Kenya, Manifesto, Commentary) have orphaned `.doc-footer` CSS rules defined in `<style>` but no corresponding HTML element — dead code.

---

### Pattern F — Custom one-off footer (4 files)

| File | Footer content |
|------|----------------|
| R4 Engine Training | "HZJ76R-RKMRS FIELD TRAINING MANUAL" + full drivetrain spec string + "10 Sections + 75 Components + Rev 3.0" |
| R5 Battery Training | "Lithium Battery Systems Training Guide · LC76 SW · Southern Africa Overland · July 2026" + "Victron Energy Ecosystem · LiFePO4 Focus" |
| R7 LiFePO4 Report | "LC76 SW · LiFePO4 System Report · Southern Africa Overland · 1 July 2026" + "Victron Energy · Enertec Power+ · Hardkorr 200W Solar" |
| R20 Seal & Gasket Atlas | "LC76 Overland Reference Library · R20 — Seal & Gasket Atlas · 1HZ · R151F · HF1A · Updated June 2026" |

**Redundancy assessment:** All four are **fully redundant** with their mastheads. R4's drivetrain spec string ("Safari Snorkel · Terrain Tamer 5th Gear & Clutch · R151F 5-Speed Manual · Part-Time 4-Wheel Drive") is not in the masthead but is thoroughly covered in the body. R5/R7 component names are body content. R20's drivetrain codes are body content.

---

### Pattern G — Calculator footer (6 files)

**Files:** Fuel Range · Trip Fuel Planner · Fuel Log Analyser · Water Budget · LiFePO4 Calculator · Tyre Pressure

Structure (`<footer>` tag, 2–3 lines):
```
Line 1: Tool name (sometimes with "LC76 SW 1HZ")
Line 2: Live calculated values (baseline, capacity, etc.) OR cross-ref
Line 3: "Estimates only" disclaimer
```

**Redundancy assessment:**
- Tool name: **Redundant** — in the masthead.
- **Live calculated values** (e.g. "Baseline: 7.00 km/L · Total capacity: 185 L"): These are JavaScript `<span>` elements that update when the user changes inputs. **Genuinely functional** — they provide a summary readout at the bottom of the page.
- "Estimates only" disclaimer: **Useful** for field safety, though some calculators also state this in their body.
- Tyre Pressure cross-ref to R14: **Useful.**

---

### Pattern H — Itinerary footer (1 file)

**File:** Karoo Winter Loop 2026

```
LC76 OVERLAND SERIES · KAROO WINTER LOOP
3 AUG – 4 SEPT 2026 · ROUTES INDICATIVE · VERIFY BEFORE TRAVEL
```

**Redundancy:** Title and dates are in the masthead. "ROUTES INDICATIVE · VERIFY BEFORE TRAVEL" is a useful caveat but is also in the body alerts. Uses the older "LC76 OVERLAND SERIES" branding.

---

### Pattern I — Audit/governance footer (2 files)

**Files:** Audit Jun 2026 · Audit Jul 2026

Long provenance blocks with evidence trail, registration date, and caching status. These are internal governance documents with a legitimate audit-trail purpose.

**Recommendation:** Leave as-is — these are not field-reference documents and their footers serve an accountability function.

---

### Pattern J — Index footer (1 file)

**File:** index.html

Single line: `LC76 Overland Reference Library`

**Redundancy:** Pure branding, but index.html is the landing page and a minimal brand line is conventional.

---

## 3 · CLEANUP PROPOSAL

### Principle

Remove all footer content that duplicates the masthead or body text. Retain only content that provides **unique value not available elsewhere in the same file:**

- **Functional calculator readouts** (live JS values)
- **Source attributions** on profiles (provenance)
- **Cross-reference print instructions** where no inline xref bar exists
- **Audit provenance** (governance)

### Proposed actions by pattern

| Pattern | Files | Action | Rationale |
|---------|-------|--------|-----------|
| **A** Legacy R12–R17 | 6 | **Strip Lines 1–2. Keep Line 3 only where it carries a unique cross-ref or caveat not in the body.** If the file already has a cross-reference bar, remove the footer entirely. | Lines 1–2 are fully redundant with masthead. Line 3 cross-refs are the only unique content. |
| **B** Library brand R8/R9/R10 | 3 | **Remove entirely.** | Single branding line — pure duplication. |
| **B** Library + spec R23/R26 | 2 | **Remove entirely.** | All content is in the masthead; URL is low-value (users are already on the site). |
| **C** Long provenance R34–R39 | 5 | **Remove entirely.** | Scope abstracts duplicate the intro/TOC; cross-refs duplicate inline bars; dates are in masthead. |
| **D** Profile 001–008 | 8 | **Reduce to sources line only.** Remove title, vehicle, "verify" warning, and URL. Keep "Sources: ..." as a slim attribution. Move exchange rates into the body (§ Forex/Money or §01) if not already there. | Source attributions are the only unique, non-duplicated content. |
| **E** No footer | 24 | **No action needed.** Clean up orphaned `.doc-footer` CSS in R1, 009, 010, Manifesto, Commentary (5 files — dead code removal). | Already clean. |
| **F** Custom one-offs R4/R5/R7/R20 | 4 | **Remove entirely.** | All content is in masthead or body. |
| **G** Calculators | 6 | **Keep — these are functional.** Optionally standardise the wrapper class to `doc-footer` for consistency. | Live JS readout values are genuinely useful. |
| **H** Itinerary (Karoo) | 1 | **Remove entirely.** | Title/dates in masthead; caveat in body alerts. |
| **I** Audit reports | 2 | **Keep as-is.** | Governance provenance — not field docs. |
| **J** Index | 1 | **Keep as-is.** | Minimal landing-page brand line; conventional. |

### Summary count

| Action | Files |
|--------|-------|
| Remove footer entirely | 21 |
| Reduce to sources-only | 8 (profiles) |
| Keep (functional / governance / index) | 9 |
| Strip partial content (Line 3 decision) | 6 (R12–R17) |
| Dead CSS cleanup only | 5 |
| Already clean — no action | 12 |

### Branding resolution

This cleanup also resolves the logged "LC76 Overland Series" vs "Overland Reference Library" footer inconsistency — by removing the footers that carry the old branding (R12–R17, Karoo), the discrepancy is eliminated. The footer standardisation workstream logged in the PI is therefore **closed** by this work.

---

## 4 · DECISION GATES FOR OWNER

Before execution, three decisions are needed:

**Gate 1 — R12–R17 cross-reference lines.** Four of these six files carry a "Print this guide and keep with R[x]" instruction. Three options:
- **(a)** Keep only as a slim footer line (e.g. `<footer><div>Print and keep with R4 (Engine Training)</div></footer>`)
- **(b)** Move the instruction into the body (e.g. as a note in the introduction section) and remove the footer entirely
- **(c)** Remove entirely — the cross-reference bars handle navigation; the "keep with" instruction is redundant in a PWA

**Recommended default: (c) — remove.** The library is a PWA; the "print and keep together" instruction is a physical-binder concept that doesn't apply to a digital reference system. Cross-reference bars already link related documents.

**Gate 2 — Profile source attributions.** Two options:
- **(a)** Keep as a slim 1-line footer: `Sources: iOverlander · Tracks4Africa · NWR · ...`
- **(b)** Remove entirely — sources are implicit in the body text and not auditable anyway (no inline citations)

**Recommended default: (a) — keep sources as a slim footer.** Source provenance has value for credibility and for knowing when to re-verify.

**Gate 3 — Profile exchange rates (001–005 only).** Two options:
- **(a)** Move rates into the body (§ Money/Forex or §01 Overview) before removing the footer — preserves the data
- **(b)** Remove with the footer — rates are in the body text of newer profiles (006–010) and the data is date-stamped anyway

**Recommended default: (b) — remove.** The rates are date-stamped (e.g. "USD/ZAR ≈ 18.2" from April 2026) and will be stale by expedition time. Newer profiles handle forex in the body. If retained, they belong in the body, not a footer.

---

## 5 · EXECUTION PLAN

This is a content-only change across existing files — no files added, removed, or renamed. Therefore: **no sw.js cache bump required**. Each edited file gets a masthead "Last updated" bump to session date; index.html header-meta bumps once.

Execution in three tranches (manageable within session limits):

1. **Tranche 1 — Full removals** (21 files): R4, R5, R7, R8, R9, R10, R19, R20, R23, R26, R32, R34, R35, R36, R38, R39, R12–R17 (if Gate 1 = remove), Karoo. Surgical `str.replace` per file — delete the entire `<footer>` or `<div class="footer/doc-footer">` block.

2. **Tranche 2 — Profile reductions** (8 files): 001–008. Replace the 5-line `doc-footer` with a 1-line sources attribution (if Gate 2 = keep).

3. **Tranche 3 — Dead CSS cleanup** (5 files): R1, 009, 010, Manifesto, Commentary. Remove orphaned `.doc-footer` CSS rules from `<style>` blocks.

Validation after each tranche: div-depth walk, full-file branding sweep, `node --check` on inline JS.

**Estimated scope:** ~44 files touched. One session if the 80k exemption applies (masthead date bumps are surgical); otherwise split across two sessions for R4 (227k) and R8 (149k).
