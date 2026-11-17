# Test: LZZT layers 2 and 3 — rules + mapping rows → USDM, checked, and next to the DDF-RA build

Stage 1 of the LZZT worked example (`WALKTHROUGH.md` at the repository root). It reads the checked layer-1 transcript in
`tests/lzzt-layer1/` (PDF pages 1 and 7 of the CDISC Pilot protocol H2Q-MC-LZZT(c)), joins it to three decided
mapping rows, and builds USDM v4: the objectives of section 2 with their level Codes, and the official study title
with its type Code.

## Files
- `lv.sssom.tsv`, `ti.sssom.tsv`: the mapping data, SSSOM, keyed by transcript element (so `d2d_check.py drift` checks
  each row's subject_label against the printed name). Decided by Kerstin Forsberg (reviewer_id, ORCID).
  - lv:1 `s2.1` "Primary Objectives" → NCIT:C85826 "Primary Objective"; lv:2 `s2.2` "Secondary Objectives" →
    NCIT:C85827 "Secondary Objective" (codelist C188725). skos:relatedMatch: the heading names the group of objectives
    listed under it; it is not the same concept as the level.
  - ti:1 `p1.title` → NCIT:C207616 "Official Study Title" (codelist C207419): the title printed on the title page is read
    as the official title.
  - object_label = the CDISC Submission Value in NCI EVS DDF Terminology 2026-09-25; that date is the sets'
    `object_source_version`, which the rules copy into `Code.codeSystemVersion`.
- `rules.trig`: four rules. O1 printed list item under a section with a level row → Objective; O2 its level Code; T1
  printed document title with a title row → StudyTitle; T2 its type Code. No code, decode or level is written in a rule.
  Node IRIs are base + USDM id (usdm-rdf D7), ids from the print position (`Objective_2.1.1`). `SyntaxTemplate-name` is
  not printed: the not-stated pattern (VOCABULARY.md) plus "" for minCount 1.
- `check.py`: shape (SHACL with usdm-rdf), ct (code + decode + codelist + version in the pinned DDF CT package),
  provenance, coverage (printed elements no rule used), counts. Each fails the run.
- `compare_ddfra_usdm.py`: our build next to the DDF-RA build, per value. Pairs come from layer 1
  (`tests/lzzt-layer1/out/ddfra_compare.tsv`: which element prints each DDF-RA value), not from order. Writes
  `out/ddfra_usdm_compare.tsv`, compared with `expected_ddfra_usdm.tsv`; the run fails on any difference.

## Inputs (`inputs/`, sha256 in `inputs/MANIFEST.sha256`)
- `usdm-rdf/usdm_v4.ttl`, `usdm_v4.shapes.ttl`, `usdm_v4.shapes-ct.ttl`: from kerfors/usdm-rdf at b26af25 (MIT).
- `downloaded/`: **not in this repository**. Download both NCI EVS DDF CT packages into `tests/lzzt-usdm/inputs/downloaded/`:
  ```
  curl -sS -o tests/lzzt-usdm/inputs/downloaded/DDF_Terminology_2026-09-25.txt "https://evs.nci.nih.gov/ftp1/CDISC/DDF/Archive/DDF%20Terminology%202026-09-25.txt"
  curl -sS -o tests/lzzt-usdm/inputs/downloaded/DDF_Terminology_2024-09-27.txt "https://evs.nci.nih.gov/ftp1/CDISC/DDF/Archive/DDF%20Terminology%202024-09-27.txt"
  ```
  2026-09-25 is the package our Codes use; 2024-09-27 is the version the DDF-RA build states, used only in the comparison.
- From `tests/lzzt-layer1/`: the transcript, and the DDF-RA JSON (its `inputs/downloaded/`).

## Run
From the repository root: `bash run_lzzt.sh` (layer 1 first, then this test).

## Result (2026-11-17)
- Rules: O1 +66, O2 +42, T1 +5, T2 +7 quads; output 86 triples.
- shape: conforms, 0 results. ct: 7 of 7 Codes in DDF Terminology 2026-09-25. provenance: 20 output nodes, all with
  `jt:derivedFrom`. drift: ok (3 rows).
- coverage: 15 printed elements, 9 used, 6 not used: the copyright notice, the compound line, the protocol line, the
  section 2 heading, the two lead sentences.
- counts: 6 Objectives (2 Primary, 4 Secondary), 1 StudyTitle, 7 Codes, 6 names not stated. No Endpoints: none is printed
  in section 2, and USDM 4.0 allows an Objective without Endpoints (`Objective-endpoints` has no minCount).
- Negative controls (run by Claude, not part of the run): row lv:2 removed → 4 Objectives fewer, coverage fails;
  lv:1 subject_label "Primary Objective" → drift fails; lv:1 object_label "Study Primary Objective" (the 2024-09-27
  submission value) → ct fails.
- DDF-RA vs ours: 82 rows (10 pairing rows), 28 same, 44 differ. Same: the level code and decode of all 6 objectives.
  Differ: text of objectives 1, 3, 5 and of the titles (as in layer 1); name ("OBJn" vs "" + not stated); endpoints
  (theirs 2, 3, 3, 1, 1, 1; ours 0, none printed here); codeSystemVersion (theirs 2024-09-27, ours 2026-09-25) — their
  decodes ("Primary Objective", "Secondary Objective") are not the 2024-09-27 submission values ("Study Primary
  Objective", "Study Secondary Objective"), they are those of 2026-09-25; their title type codes C99905x1/x2/x3 are in
  neither package (C207615/C207616/C207617 are); their acronym type C94108 is not in codelist C207419 in either package
  (C207646 is). The page's one title is two titles in their build (official and public, the same text); ours records it
  once, as official. The brief title and the acronym are not built here (layer 1: an interpretation of the compound
  line; the acronym only inside other text).
