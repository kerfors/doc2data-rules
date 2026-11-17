# Walkthrough: one objective from the printed page to USDM and back

doc2data in one example, on a protocol anyone can download: the CDISC Pilot study, Xanomeline (LY246708) Protocol
H2Q-MC-LZZT(c). The PDF is published by data4knowledge (usdm_data) and by CDISC (DDF-RA), each next to a USDM build of
the study; every page prints "Copyright © 2006 Eli Lilly and Company". This repository quotes two of its 97 pages and does
not copy the PDF. Run it all with `bash run_lzzt.sh` after the downloads in `tests/lzzt-layer1/README.md` and
`tests/lzzt-usdm/README.md`.

The object we follow is the first primary objective, printed on page 7 under "2.1. Primary Objectives".

## 0. The document has an identity before anything is read from it
The register (`register/register-collections.trig`) holds the protocol as a Work (w0006), a version as an Expression
(e0006) and the PDF as a Manifestation, named by its sha256 (`dbadb370…a040`). Its identifiers (H2Q-MC-LZZT, LZZT) come
from a pinned record, the soa2usdm-collections workbook, not from the document; the register check then finds them
printed on the pages. Everything below hangs off these IRIs.

## 1. Layer 1 — the transcript: what the page prints, no decisions
`tests/lzzt-layer1/transcript.trig` holds element `s2.1.list.1`, a `d2d:ListItem` in the list of section `s2.1`
("2.1." "Primary Objectives"), with the printed text:

> To determine if there is a statistically significant relationship (overall Type 1 error rate, α=.05) between the
> change in both ADAS-Cog (see Attachment LZZT.2) and CIBIC+ (see Attachment LZZT.3) scores, and drug dose (0, 50 cm2
> [54 mg], and 75 cm2 [81 mg]).

Its anchor points to page 7 with that exact text. Three checks hold the transcript to the source: `verbatim` (every text
is in the page's text layer, and the anchor's page is the element's page), `structure` (section numbers before their
headings, list order as printed), `register` (the identifiers are printed). A person compared the 17 elements with the
two pages; the run record names the transcriber and the checker. Nothing here says "objective" or "primary": that is
reading, and reading is layer 2.

## 2. Layer 2 — a decided mapping row, and a rule that joins to it
The decision is one row of mapping data, not code (`tests/lzzt-usdm/lv.sssom.tsv`):

| record | subject | subject_label | predicate | object | object_label |
|---|---|---|---|---|---|
| lv:1 | `s2.1` | Primary Objectives | skos:relatedMatch | NCIT:C85826 | Primary Objective |

with the codelist (C188725), the CT package the label is taken from (2026-09-25), and who decided it (reviewer_id). The
`drift` check fails if the printed heading ever stops being "Primary Objectives".

The rule is generic (`tests/lzzt-usdm/rules.trig`, O1 and O2): *a printed list item under a section that has a level
row becomes an Objective with the item's text; its level Code comes from the row.* The rule names no code, no label and
no level. Remove the row and the rule builds nothing for that section; the coverage report shows the items as not used.

## 3. Layer 3 — the output, validated, with provenance
`tests/lzzt-usdm/out/usdm.ttl`:

```turtle
<urn:jt:expr/e0006/usdm/Objective_2.1.1> a usdm:Objective ;
    usdm:SyntaxTemplate-text "To determine if there is a statistically significant relationship (overall Type 1 error rate, α=.05) …" ;
    usdm:SyntaxTemplate-name "" ;
    usdm:Objective-extensionAttributes <…/ExtensionAttribute_Objective_2.1.1_name> ;   # not stated in protocol: name
    usdm:Objective-level <…/Code_Objective_2.1.1_level> .
<…/Code_Objective_2.1.1_level> a usdm:Code ;
    usdm:Code-code "C85826" ; usdm:Code-decode "Primary Objective" ;
    usdm:Code-codeSystem "http://www.cdisc.org" ; usdm:Code-codeSystemVersion "2026-09-25" .
```

- The node IRI is ours to mint (base + USDM id); the id says where it is printed. USDM's `name` is required but not
  printed, so it is "" with the not-stated marker, never a made-up value.
- No Endpoints: section 2 prints none, and USDM 4.0 allows an Objective without them.
- `shape`: the output graph conforms to the usdm-rdf SHACL shapes (and its CT shapes). `ct`: code, decode, codelist and
  version are all in the pinned DDF CT package.
- Provenance is kept apart from the output (`out/prov.ttl`): the Objective derives from `s2.1.list.1` and from lv:1; the
  Code from `s2.1` and lv:1. From the USDM node you get back to the row that decided its level and to the printed text on
  page 7.

## 4. The same objective in a build someone else published
DDF-RA's JSON has the same objective as `Objective_1`, and usdm-rdf's minimal instance is cut from it:

| | DDF-RA build | this build |
|---|---|---|
| text | "… (overall Type 1 erroralpha=0.05) between the change in both the ADAS-Cog (11) and CIBIC+ scores …" | as printed (above) |
| name | "OBJ1" | "" + not stated |
| level | C85826 "Primary Objective" | C85826 "Primary Objective" |
| codeSystemVersion | 2024-09-27 | 2026-09-25 |
| endpoints | 2 (ADAS-Cog (11) at Week 24; CIBIC+ at Week 24) | 0 |

What each difference means:
- **Text:** the published build is an edited text; ours is the page. Neither is wrong as USDM; only one can be checked
  against the source.
- **Name and endpoints:** the published build fills what the page does not say ("OBJ1"; endpoints composed from other
  sections). Here a value that is not printed is either built from another printed place by its own rule and row, in a
  later stage (efficacy measures, section 3.9.1.1), or marked as not stated.
- **Version and decode:** in the 2024-09-27 DDF package the submission value of C85826 is "Study Primary Objective";
  "Primary Objective" is the value from 2026-09-25. The published build pairs a label from one release with the date of
  another. The `ct` check would catch that here.

`tests/lzzt-usdm/out/ddfra_usdm_compare.tsv` has the full comparison: 6 objectives and 4 titles, 82 rows.

## What this example does not show yet
One study, two pages. The later stages are in the same example: arms (3.1), interventions (3.6), efficacy measures as the
printed source for endpoints (3.9.1.1), the SoA pages (53–54, in soa2usdm-collections) joined on shared page IRIs, and
d4k's USDM build as a second comparison. IRIs are `urn:jt:` for now (provisional).
