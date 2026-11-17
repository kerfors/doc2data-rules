# Walkthrough: one objective from the printed page to USDM and back

doc2data in one example, on a protocol anyone can download: the CDISC Pilot study, Xanomeline (LY246708) Protocol
H2Q-MC-LZZT(c). The PDF is published by data4knowledge (usdm_data) and by CDISC (DDF-RA), each next to a USDM build of
the study; every page prints "Copyright © 2006 Eli Lilly and Company". This repository quotes two of its 97 pages and does
not copy the PDF. Run it all with `bash run_lzzt.sh` after the downloads in `tests/lzzt-layer1/README.md` and
`tests/lzzt-usdm/README.md`. Sections 1–4 are stage 1 (`tests/lzzt-layer1`, `tests/lzzt-usdm`); section 5 is stage 2a
(`tests/lzzt-endpoints`); section 6 is where soa2usdm fits.

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
- No Endpoints from section 2: it prints none, and USDM 4.0 allows an Objective without them. They come from
  section 3.9.1.2, in stage 2a (section 5).
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
| endpoints | 2 (ADAS-Cog (11) at Week 24; CIBIC+ at Week 24) | 2 (ADAS-Cog (11); video-referenced CIBIC+), from 3.9.1.2 (section 5) |

What each difference means:
- **Text:** the published build is an edited text; ours is the page. Neither is wrong as USDM; only one can be checked
  against the source.
- **Name and endpoints:** the published build fills what the page does not say ("OBJ1"; endpoint texts with a time
  point). Here a value that is not printed next to the objective is either built from another printed place by its own
  rule and row (the endpoints, from 3.9.1.2: section 5), or marked as not stated (the name).
- **Version and decode:** in the 2024-09-27 DDF package the submission value of C85826 is "Study Primary Objective";
  "Primary Objective" is the value from 2026-09-25. The published build pairs a label from one release with the date of
  another. The `ct` check would catch that here.

`tests/lzzt-usdm/out/ddfra_usdm_compare.tsv` has the full comparison: 6 objectives and 4 titles, 82 rows.

## 5. Stage 2a — the objective's endpoints, from where the protocol prints them
Section 2 prints objectives only. Section 3.9.1.2 Efficacy Criteria (page 29) names the instruments and their level:

> The ADAS-Cog (11) and the video-referenced CIBIC+ will serve as the primary efficacy instruments. Secondary efficacy
> instruments will include the DAD, the NPI-X, and the ADAS-Cog (14).

The same pattern as before, one level down (`tests/lzzt-endpoints`):
- **Layer 1:** the whole section is transcribed (heading and 7 sentences) and checked against page 29.
- **Layer 2:** two kinds of row. A level row per criteria sentence (el:1 sentence 2 → C94496 "Primary Endpoint"), a
  decision. An endpoint row per named instrument, pointing to the objective that prints the same instrument. Four of
  them print the same string on both sides ("NPI-X" in the sentence and in objective 2.2.1): lexical matches, no
  reviewer needed. One is a decision: eo:1 says that "ADAS-Cog (11)" in sentence 2 belongs to objective 2.1.1, which
  prints only "ADAS-Cog". The drift check verifies the shared string on both sides for all five. Rules E1 and E2 build
  the Endpoint inside that Objective and its level Code; they name no instrument and no objective.
- **Layer 3:** objective 2.1.1 now has two Endpoints, "ADAS-Cog (11)" and "video-referenced CIBIC+", both Primary;
  2.2.1–2.2.3 one Secondary Endpoint each (NPI-X, DAD, ADAS-Cog (14)); 2.1.2 and 2.2.4 none, because 3.9.1.2 names no
  instrument for them. The whole output still conforms; each Endpoint is in exactly one Objective.

What the page does not give, the build does not have: no time point (Week 24 is printed in section 3.1, a later reading
with its own row), no "change from baseline" in the endpoint text (sentence 1 of 3.9.1.2 says it for the group of primary
parameters; not read in this stage, and listed in coverage). The published build has 11 endpoints for the same study:
3 pair with ours, 3 are placeholders, 3 are safety measures 3.9.1.2 does not name, 2 repeat ADAS-Cog (11) and CIBIC+ "at
Weeks 8 and 16" under the behaviour objective. Ours has 2 the published build lacks: DAD and ADAS-Cog (14), both named
as secondary instruments on page 29 (`tests/lzzt-endpoints/out/ddfra_endpoints_compare.tsv`).

## 6. Where soa2usdm fits
One protocol, two readers. [soa2usdm](https://github.com/kerfors/soa2usdm-collections) reads the Schedule of Activities
(pages 53–54, Attachment LZZT.1) and owns everything about activities: their grain, routing, test identity. doc2data
reads the rest of the document. Neither re-reads the other's pages; a third step joins them.

They can be joined because they agree on identity: soa2usdm's record for this study pins the same PDF (sha256
`dbadb370…a040`, register e0006) and the same page numbers, so both sides can name page 53 the same way. In soa2usdm's
SoA for LZZT, ADAS-Cog, CIBIC+ and DAD are marked at visits 1, 3, 8, 10, 12, ET and RT, and NPI-X at every visit. The next
stage (2b) links each Endpoint here to its SoA activity by a decided row, lists the visits, and runs a first
cross-check: the text (3.1, 3.9.1.1) prints "At Visits 3, 8, 10, and 12" for ADAS-Cog, CIBIC+ and DAD; the SoA also marks
Visit 1 and ET/RT. Such findings are reported, not resolved. That link is design-relationship data, not USDM: USDM has no
place for "this endpoint is measured by this activity at these visits".

## What this example does not show yet
One study, three pages so far. The later stages are in the same example: the SoA link (2b), arms (3.1), interventions
(3.6), and d4k's USDM build as a second comparison. IRIs are `urn:jt:` for now (provisional).
